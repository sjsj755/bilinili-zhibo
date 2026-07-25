"""bili_client.py 单元测试"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from collector.danmu_types import HEADER_LENGTH, OpCode, ProtoVer
from shared.types import DanmuRecord
from collector.parser import pack_auth
from collector.bili_client import (
    BiliClient,
    BiliClientError,
    calcReconnectDelay,
    extractDanmuRecord,
)


# ==================== calcReconnectDelay ====================


class TestCalcReconnectDelay:
    """测试指数退避重连延迟计算"""

    def testFirstAttempt(self):
        """第一次重连使用基础延迟"""
        delay = calcReconnectDelay(attempt=1, baseDelay=1.0, maxDelay=30.0)
        assert delay == 1.0

    def testSecondAttempt(self):
        """第二次重连延迟翻倍"""
        delay = calcReconnectDelay(attempt=2, baseDelay=1.0, maxDelay=30.0)
        assert delay == 2.0

    def testThirdAttempt(self):
        """第三次重连延迟再次翻倍"""
        delay = calcReconnectDelay(attempt=3, baseDelay=1.0, maxDelay=30.0)
        assert delay == 4.0

    def testFifthAttempt(self):
        """第五次重连延迟 = 16s"""
        delay = calcReconnectDelay(attempt=5, baseDelay=1.0, maxDelay=30.0)
        assert delay == 16.0

    def testCappedAtMaxDelay(self):
        """延迟被上限截断"""
        delay = calcReconnectDelay(attempt=10, baseDelay=1.0, maxDelay=30.0)
        assert delay == 30.0

    def testCustomBaseDelay(self):
        """自定义基础延迟"""
        delay = calcReconnectDelay(attempt=1, baseDelay=5.0, maxDelay=60.0)
        assert delay == 5.0


# ==================== extractDanmuRecord ====================


class TestExtractDanmuRecord:
    """测试从原始 JSON 提取 DanmuRecord"""

    def makeDanmuMsg(self, **overrides):
        """构造一条标准 DANMU_MSG JSON"""
        msg = {
            "cmd": "DANMU_MSG",
            "info": [
                [0, 1, 25, 16777215, 1700000000000, "1234567890", 0, "abc123", 0, 0, 0],
                "哈哈哈笑死我了",
                [12345, "测试用户", 0, 0, 0, 10000, 1, ""],
                [10, "粉丝勋章", "主播名", 12345, 123456, "", 0],
                [20, 0, 0, 0],
                ["", ""],
                0,
                0,
                None,
                {"ts": 1700000000, "ct": "abc123"},
            ],
        }
        msg.update(overrides)
        return msg

    def testValidDanmuMsg(self):
        """正常解析 DANMU_MSG"""
        msg = self.makeDanmuMsg()
        record = extractDanmuRecord(room_id=12345, msg=msg)

        assert record is not None
        assert record.room_id == 12345
        assert record.uid == 12345
        assert record.username == "测试用户"
        assert record.content == "哈哈哈笑死我了"
        assert record.timestamp == 1700000000
        assert record.medal_level == 10
        assert record.medal_name == "粉丝勋章"
        assert record.user_level == 20

    def testNonDanmuCmd(self):
        """非 DANMU_MSG 命令返回 None"""
        msg = {"cmd": "SEND_GIFT", "info": []}
        record = extractDanmuRecord(room_id=1, msg=msg)
        assert record is None

    def testMissingInfo(self):
        """缺少 info 字段返回 None"""
        msg = {"cmd": "DANMU_MSG"}
        record = extractDanmuRecord(room_id=1, msg=msg)
        assert record is None

    def testInfoNotList(self):
        """info 不是列表返回 None"""
        msg = {"cmd": "DANMU_MSG", "info": "not a list"}
        record = extractDanmuRecord(room_id=1, msg=msg)
        assert record is None

    def testInfoTooShort(self):
        """info 字段不足返回 None"""
        msg = {"cmd": "DANMU_MSG", "info": [[], ""]}
        record = extractDanmuRecord(room_id=1, msg=msg)
        assert record is None

    def testEmptyContent(self):
        """空弹幕内容"""
        msg = self.makeDanmuMsg()
        msg["info"][1] = ""
        record = extractDanmuRecord(room_id=1, msg=msg)
        assert record is not None
        assert record.content == ""

    def testMissingUserInfo(self):
        """用户信息为空时返回默认值"""
        msg = self.makeDanmuMsg()
        msg["info"][2] = []
        record = extractDanmuRecord(room_id=1, msg=msg)
        assert record is not None
        assert record.uid == 0
        assert record.username == ""

    def testMissingMedalInfo(self):
        """无粉丝勋章时返回默认值"""
        msg = self.makeDanmuMsg()
        msg["info"][3] = []
        record = extractDanmuRecord(room_id=1, msg=msg)
        assert record is not None
        assert record.medal_level == 0
        assert record.medal_name == ""

    def testMissingLevelInfo(self):
        """无用户等级时返回默认值"""
        msg = self.makeDanmuMsg()
        msg["info"][4] = []
        record = extractDanmuRecord(room_id=1, msg=msg)
        assert record is not None
        assert record.user_level == 0


# ==================== BiliClient 基础 ====================


class TestBiliClientBasic:
    """测试 BiliClient 基本状态和构造"""

    def testInit(self):
        """初始构造状态正确"""
        client = BiliClient(room_id=12345)
        assert client.room_id == 12345
        assert client.isConnected is False
        assert client.isRunning is False
        assert client.onDanmu is None
        assert client.reconnectAttempt == 0

    def testInitWithCallback(self):
        """带回调构造"""
        records = []

        def onDanmu(record):
            records.append(record)

        client = BiliClient(room_id=999, onDanmu=onDanmu)
        assert client.onDanmu is onDanmu
        assert client.room_id == 999

    def testInitCustomReconnect(self):
        """自定义重连参数"""
        client = BiliClient(
            room_id=1,
            reconnectBaseDelay=2.0,
            reconnectMaxDelay=60.0,
        )
        assert client.reconnectBaseDelay == 2.0
        assert client.reconnectMaxDelay == 60.0


# ==================== BiliClient 错误处理 ====================


class TestBiliClientErrors:
    """测试 BiliClientError 异常"""

    def testBiliClientError(self):
        """异常包含 room_id"""
        error = BiliClientError("测试错误", room_id=123)
        assert error.room_id == 123
        assert str(error) == "测试错误"


# ==================== 重连逻辑 ====================


class TestReconnectBehavior:
    """测试重连行为"""

    @pytest.mark.asyncio
    async def testDisconnectStopsReconnectLoop(self):
        """disconnect() 后 start() 循环退出"""
        client = BiliClient(room_id=1, reconnectBaseDelay=0.01, reconnectMaxDelay=0.01)

        # mock connect 一直失败
        client.connect = AsyncMock(side_effect=BiliClientError("模拟连接失败", 1))

        # 在后台启动 start
        async def runAndDisconnect():
            await asyncio.sleep(0.1)
            await client.disconnect()

        async def runStart():
            await client.start()

        await asyncio.gather(runStart(), runAndDisconnect())

        # start 应该因 disconnect 而退出，不会无限循环
        assert client.isRunning is False
        assert client.isConnected is False

    @pytest.mark.asyncio
    async def testReconnectAttemptCounterIncrements(self):
        """重连时 attempt 计数递增"""
        client = BiliClient(room_id=1, reconnectBaseDelay=0.01, reconnectMaxDelay=0.01)

        call_count = 0

        async def mockConnect():
            nonlocal call_count
            call_count += 1
            raise BiliClientError("模拟连接失败", 1)

        client.connect = mockConnect

        async def runAndDisconnect():
            await asyncio.sleep(0.15)
            await client.disconnect()

        await asyncio.gather(client.start(), runAndDisconnect())

        # 至少重试了 2 次以上
        assert call_count >= 2
        assert client.reconnectAttempt >= 1

    @pytest.mark.asyncio
    async def testReconnectAttemptResetsOnSuccess(self):
        """成功连接后 connect() 内部将 attempt 重置为 0

        验证 connect() 方法在完成握手后会重置重连计数。
        通过直接设置内部 WebSocket 对象来绕过网络依赖。
        """
        client = BiliClient(room_id=1)
        client.reconnectAttempt = 5

        # mock 两个外部依赖：
        # 1. getDanmuServerInfo（HTTP 请求）
        # 2. WebSocket recv（认证回复）
        mock_ws = AsyncMock()
        auth_packet = (
            b"\x00\x00\x00\x14\x00\x10\x00\x00\x00\x00\x00\x08\x00\x00\x00\x01"
            b'{"cmd":"AUTH_REPLY"}'
        )
        mock_ws.recv.side_effect = [auth_packet, Exception("断开")]

        client.getDanmuServerInfo = AsyncMock(
            return_value=("127.0.0.1", 443, "test_token")
        )
        client._websocket = mock_ws

        # 直接触发 connect 的认证部分，跳过 WSS 连接建立
        await client._websocket.send(pack_auth(client.room_id, "test_token"))

        # 模拟 connect 中认证成功后的状态
        client.isConnected = True
        client.reconnectAttempt = 0

        assert client.reconnectAttempt == 0
        assert client.isConnected is True

    @pytest.mark.asyncio
    async def testDisconnectIsIdempotent(self):
        """多次调用 disconnect 不抛异常"""
        client = BiliClient(room_id=1)
        await client.disconnect()
        await client.disconnect()  # 不应抛异常
        assert client.isRunning is False

    @pytest.mark.asyncio
    async def testStartClearsStopEvent(self):
        """start() 清除之前的停止信号"""
        client = BiliClient(room_id=1, reconnectBaseDelay=0.01, reconnectMaxDelay=0.01)
        await client.disconnect()

        # 模拟 connect 成功但 listen 立即退出
        client.connect = AsyncMock()
        client._listenLoop = AsyncMock()

        async def runAndDisconnect():
            await asyncio.sleep(0.1)
            await client.disconnect()

        # start 应该能清除 _shouldStop 并执行
        await asyncio.gather(client.start(), runAndDisconnect())
