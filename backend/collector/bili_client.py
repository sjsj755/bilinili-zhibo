"""B 站单直播间 WebSocket 客户端

负责管理与 B 站弹幕服务器的 WebSocket 连接，包括：
- 通过 B 站 API 获取弹幕服务器地址和 token
- 建立 WebSocket 连接并发送认证包
- 维持心跳（每 30 秒）
- 断线自动重连（指数退避）
- 接收弹幕数据并解析为 DanmuRecord
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

import httpx
from websockets import connect

from .parser import pack_auth, pack_heartbeat, parse, unpack_header
from .danmu_types import OpCode
from shared.types import DanmuRecord
from utils.wbi import generateBuvid3, getMixinKey, signParams

logger = logging.getLogger(__name__)

# B 站 API 地址（2025 新版端点）
DANMU_INFO_API = "https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo"
ROOM_INIT_API = "https://api.live.bilibili.com/room/v1/Room/room_init"

# 默认配置
DEFAULT_HEARTBEAT_INTERVAL = 25  # 心跳间隔（秒），B站超时约60s，25s留余量
DEFAULT_RECONNECT_BASE_DELAY = 4.0  # 重连基础延迟（秒）
DEFAULT_RECONNECT_MAX_DELAY = 30.0  # 重连最大延迟（秒）


class BiliClientError(Exception):
    """BiliClient 异常"""

    def __init__(self, message: str, room_id: int = 0):
        super().__init__(message)
        self.room_id = room_id


def extractDanmuRecord(room_id: int, msg: dict[str, Any]) -> DanmuRecord | None:
    """从 DANMU_MSG 原始 JSON 中提取 DanmuRecord

    B 站 DANMU_MSG 的 info 数组结构：
      info[0]: [模式, 字号, 颜色, 时间戳(s), ...]
      info[1]: 弹幕内容文本
      info[2]: [uid, 用户名, ...]
      info[3]: [勋章等级, 勋章名, ...]
      info[4]: [用户等级, ...]

    Args:
        room_id: 直播间 ID
        msg: parse() 返回的 JSON 消息对象

    Returns:
        DanmuRecord | None: 解析成功返回记录，字段缺失返回 None
    """
    cmd = msg.get("cmd", "")
    if not cmd.startswith("DANMU_MSG"):
        return None

    info = msg.get("info")
    if not isinstance(info, list) or len(info) < 5:
        return None

    try:
        # info[0] 是弹幕模式元数据，B站原始时间戳为毫秒，转为秒
        mode_info = info[0]
        rawTimestamp = mode_info[4] if isinstance(mode_info, list) and len(mode_info) > 4 else 0
        timestamp = rawTimestamp // 1000

        content = str(info[1]) if info[1] else ""

        # info[2] 是用户信息
        user_info = info[2]
        uid = user_info[0] if isinstance(user_info, list) and len(user_info) > 0 else 0
        username = str(user_info[1]) if isinstance(user_info, list) and len(user_info) > 1 else ""

        # info[3] 是粉丝勋章信息
        medal_info = info[3]
        medal_level = medal_info[0] if isinstance(medal_info, list) and len(medal_info) > 0 else 0
        medal_name = str(medal_info[1]) if isinstance(medal_info, list) and len(medal_info) > 1 else ""

        # info[4] 是用户等级信息
        level_info = info[4]
        user_level = level_info[0] if isinstance(level_info, list) and len(level_info) > 0 else 0

        return DanmuRecord(
            room_id=room_id,
            uid=uid,
            username=username,
            content=content,
            timestamp=timestamp,
            medal_level=medal_level,
            medal_name=medal_name,
            user_level=user_level,
        )
    except (IndexError, TypeError, ValueError) as e:
        logger.warning("解析 DANMU_MSG 失败: %s, msg=%s", e, msg)
        return None


def calcReconnectDelay(attempt: int, baseDelay: float, maxDelay: float) -> float:
    """计算指数退避重连延迟

    Args:
        attempt: 当前重连尝试次数（从 1 开始）
        baseDelay: 基础延迟（秒）
        maxDelay: 最大延迟上限（秒）

    Returns:
        float: 本次重连等待时间（秒）
    """
    delay = baseDelay * (2 ** (attempt - 1))
    return min(delay, maxDelay)


class BiliClient:
    """B 站单直播间 WebSocket 采集客户端

    内置断线自动重连（指数退避），连接断开后自动重试。

    使用示例:
        async def onDanmu(record):
            print(f"[{record.username}]: {record.content}")

        client = BiliClient(room_id=12345, onDanmu=onDanmu)
        await client.start()       # 连接 + 监听（含自动重连）
        # ... 运行中 ...
        await client.disconnect()  # 停止并断开

    Attributes:
        room_id: B 站直播间 ID
        onDanmu: 弹幕回调函数
        isConnected: 是否已连接
        isRunning: 是否正在监听
        reconnectAttempt: 当前重连次数（成功连接后重置为 0）
    """

    def __init__(
        self,
        room_id: int,
        onDanmu: Callable[[DanmuRecord], Any] | None = None,
        sessdata: str = "",
        uid: int = 0,
        heartbeatInterval: int = DEFAULT_HEARTBEAT_INTERVAL,
        reconnectBaseDelay: float = DEFAULT_RECONNECT_BASE_DELAY,
        reconnectMaxDelay: float = DEFAULT_RECONNECT_MAX_DELAY,
    ):
        self.room_id = int(room_id)
        self.onDanmu = onDanmu
        self.sessdata = sessdata
        self.uid = int(uid) if uid else 0
        self.heartbeatInterval = heartbeatInterval
        self.reconnectBaseDelay = reconnectBaseDelay
        self.reconnectMaxDelay = reconnectMaxDelay

        self.isConnected = False
        self.isRunning = False
        self.reconnectAttempt = 0

        self._buvid3 = generateBuvid3()
        self._websocket: Any | None = None
        self._heartbeatTask: asyncio.Task[Any] | None = None
        self._shouldStop = asyncio.Event()

    async def getDanmuServerInfo(self) -> tuple[str, int, str, int]:
        """从 B 站 API 获取弹幕服务器地址和 token

        2025 新版要求 WBI 签名 + buvid3 cookie。
        支持短号解析：先调用 room_init 将短号转为真实房间号。

        Returns:
            tuple[str, int, str, int]: (host, port, token, real_room_id)

        Raises:
            BiliClientError: API 请求失败或直播间不存在
        """
        try:
            cookie = f"buvid3={self._buvid3}"
            if self.sessdata:
                cookie += f"; SESSDATA={self.sessdata}"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Referer": "https://live.bilibili.com/",
                "Cookie": cookie,
            }

            async with httpx.AsyncClient(headers=headers) as client:
                resp = await client.get(ROOM_INIT_API, params={"id": self.room_id})
                resp.raise_for_status()
                data = resp.json()

                if data.get("code") != 0:
                    raise BiliClientError(
                        f"room_init API 返回错误: code={data.get('code')}, message={data.get('message', '未知错误')}",
                        self.room_id,
                    )

                room_data = data.get("data", {})
                real_room_id = room_data.get("room_id", self.room_id)
                live_status = room_data.get("live_status", 0)

                if real_room_id != self.room_id:
                    logger.info("直播间 %d 短号解析为真实房间号: %d", self.room_id, real_room_id)

                if live_status != 1:
                    logger.warning("直播间 %d 当前未开播 (live_status=%d)", self.room_id, live_status)

                mixinKey = await getMixinKey()
                params_dict: dict[str, Any] = {"id": real_room_id}
                if self.uid > 0:
                    params_dict["uid"] = self.uid
                params = signParams(params_dict, mixinKey)

                resp = await client.get(DANMU_INFO_API, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise BiliClientError(f"获取弹幕服务器信息失败: {e}", self.room_id)

        if data.get("code") != 0:
            raise BiliClientError(
                f"API 返回错误: code={data.get('code')}, message={data.get('message', '未知错误')}",
                self.room_id,
            )

        server_list = data.get("data", {}).get("host_list")
        if not server_list or len(server_list) == 0:
            raise BiliClientError("未获取到可用的弹幕服务器地址", self.room_id)

        token = data["data"].get("token", "")
        if not token:
            raise BiliClientError("未获取到认证 token", self.room_id)

        server = server_list[0]
        host = server.get("host", "")
        port = server.get("wss_port", 443)

        if not host:
            raise BiliClientError("服务器地址为空", self.room_id)

        logger.info("直播间 %d 获取到服务器: %s:%d", self.room_id, host, port)
        return host, port, token, real_room_id

    async def connect(self) -> None:
        """建立 WebSocket 连接并完成认证握手

        Raises:
            BiliClientError: 连接或认证失败
        """
        host, port, token, real_room_id = await self.getDanmuServerInfo()

        wss_url = f"wss://{host}:{port}/sub"
        logger.info("直播间 %d 正在连接 %s", self.room_id, wss_url)

        try:
            wsHeaders = {
                "Cookie": f"buvid3={self._buvid3}" + (f"; SESSDATA={self.sessdata}" if self.sessdata else ""),
            }
            self._websocket = await connect(
                wss_url,
                ping_interval=None,
                compression=None,
                user_agent_header=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                origin="https://live.bilibili.com",
                additional_headers=wsHeaders,
            )
        except Exception as e:
            raise BiliClientError(f"WebSocket 连接失败: {e}", self.room_id)

        # 发送认证包（使用真实房间号）
        auth_packet = pack_auth(real_room_id, token, uid=self.uid, buvid=self._buvid3)
        await self._websocket.send(auth_packet)

        # 等待认证回复
        try:
            auth_reply = await asyncio.wait_for(self._websocket.recv(), timeout=10)
        except asyncio.TimeoutError:
            await self._closeWebSocket()
            raise BiliClientError("认证超时：未收到服务端回复", self.room_id)

        # 解析认证回复（带异常兜底）
        try:
            messages = parse(auth_reply)
            header = unpack_header(auth_reply)
        except Exception as e:
            await self._closeWebSocket()
            raise BiliClientError(f"认证回复解析失败: {e}", self.room_id)

        if header.op != OpCode.AUTH_REPLY:
            await self._closeWebSocket()
            raise BiliClientError(
                f"认证失败: 收到非预期操作码 op={header.op}", self.room_id
            )

        # 认证回复消息体格式为 {"code": 0}，code==0 表示成功
        auth_success = any(
            isinstance(msg, dict) and msg.get("code") == 0
            for msg in messages
        )

        if not auth_success:
            await self._closeWebSocket()
            raise BiliClientError(f"认证失败: {messages}", self.room_id)

        self.isConnected = True
        self.reconnectAttempt = 0
        logger.info("直播间 %d 认证成功", self.room_id)

    async def start(self) -> None:
        """启动采集：连接 + 监听，含自动重连

        连接断开后自动以指数退避策略重连，直到调用 disconnect()。
        """
        self._shouldStop.clear()

        while not self._shouldStop.is_set():
            try:
                await self.connect()
                await self._listenLoop()
            except BiliClientError as e:
                logger.error("直播间 %d 连接失败: %s", self.room_id, e)
            except Exception as e:
                logger.error("直播间 %d 异常断开: %s", self.room_id, e)

            if self._shouldStop.is_set():
                break

            self.reconnectAttempt += 1
            delay = calcReconnectDelay(
                self.reconnectAttempt, self.reconnectBaseDelay, self.reconnectMaxDelay
            )
            logger.info(
                "直播间 %d 将在 %.1f 秒后重连（第 %d 次重试）",
                self.room_id, delay, self.reconnectAttempt,
            )
            await asyncio.wait(
                [
                    asyncio.create_task(asyncio.sleep(delay)),
                    asyncio.create_task(self._shouldStop.wait()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )

    async def _listenLoop(self) -> None:
        """内部监听循环：接收数据包 → 解析 → 回调

        持续运行直到连接断开或收到停止信号。
        """
        self.isRunning = True
        await self._cancelHeartbeat()
        self._heartbeatTask = asyncio.create_task(self._heartbeatLoop())

        totalPackets = 0
        totalMessages = 0
        danmuCount = 0

        try:
            while self.isRunning and self._websocket and not self._shouldStop.is_set():
                try:
                    raw = await asyncio.wait_for(
                        self._websocket.recv(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    if not self._shouldStop.is_set():
                        logger.warning("直播间 %d 连接断开: %s", self.room_id, e)
                    break

                if not isinstance(raw, bytes):
                    continue

                totalPackets += 1
                try:
                    messages = parse(raw)
                except Exception as e:
                    logger.warning("直播间 %d 数据包解析失败: %s", self.room_id, e)
                    continue

                totalMessages += len(messages)
                for msg in messages:
                    record = extractDanmuRecord(self.room_id, msg)
                    if record:
                        danmuCount += 1
                        if self.onDanmu:
                            try:
                                result = self.onDanmu(record)
                                if asyncio.iscoroutine(result):
                                    await result
                            except Exception as e:
                                logger.error("弹幕回调执行异常: %s", e)
        finally:
            self.isRunning = False
            self.isConnected = False
            await self._cancelHeartbeat()
            await self._closeWebSocket()
            logger.info(
                "直播间 %d 本次采集统计: %d 个数据包, %d 条消息, %d 条弹幕",
                self.room_id, totalPackets, totalMessages, danmuCount,
            )

    async def _heartbeatLoop(self) -> None:
        """后台心跳任务"""
        heartbeat_packet = pack_heartbeat()
        while self.isRunning and self._websocket and not self._shouldStop.is_set():
            try:
                await asyncio.sleep(self.heartbeatInterval)
                if self._websocket and self.isRunning and not self._shouldStop.is_set():
                    await self._websocket.send(heartbeat_packet)
                    logger.debug("直播间 %d 发送心跳", self.room_id)
            except Exception as e:
                if not self._shouldStop.is_set():
                    logger.warning("直播间 %d 心跳发送失败: %s", self.room_id, e)
                break

    async def _cancelHeartbeat(self) -> None:
        """取消心跳任务

        确保无论取消失败与否，任务引用都被清空，防止泄漏。
        """
        if self._heartbeatTask and not self._heartbeatTask.done():
            self._heartbeatTask.cancel()
            try:
                await self._heartbeatTask
            except (asyncio.CancelledError, Exception):
                pass
        self._heartbeatTask = None

    async def _closeWebSocket(self) -> None:
        """安全关闭 WebSocket 连接

        确保底层 TCP 连接完全关闭后再置空引用。
        """
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception:
                pass
            try:
                await self._websocket.wait_closed()
            except Exception:
                pass
            self._websocket = None

    async def disconnect(self) -> None:
        """停止采集并断开连接

        设置停止信号，清理心跳任务和 WebSocket 连接。
        可安全重复调用。
        """
        self._shouldStop.set()
        self.isRunning = False
        self.isConnected = False

        await self._cancelHeartbeat()
        await self._closeWebSocket()

        logger.info("直播间 %d 已断开连接", self.room_id)
