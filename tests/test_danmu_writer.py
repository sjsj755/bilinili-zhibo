"""DanmuWriter 单元测试"""

import asyncio
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from shared.types import DanmuRecord
from db.database import DanmuWriter, closeDb, getConnection, initDb


class TestDanmuWriter:
    """测试 DanmuWriter 批量写入"""

    def setup_method(self):
        """每个测试前初始化临时数据库"""
        self._dbFile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._dbPath = self._dbFile.name
        self._dbFile.close()
        initDb(self._dbPath)

    def teardown_method(self):
        """每个测试后清理"""
        closeDb()
        os.unlink(self._dbPath)

    def makeRecord(self, roomId: int = 1, content: str = "测试弹幕") -> DanmuRecord:
        """构造测试用 DanmuRecord"""
        return DanmuRecord(
            room_id=roomId,
            uid=100,
            username="test_user",
            content=content,
            timestamp=1700000000,
            medal_level=5,
            medal_name="测试勋章",
            user_level=10,
        )

    @pytest.mark.asyncio
    async def testWriteSingleRecord(self):
        """写入单条记录后 flush 可存入数据库"""
        writer = DanmuWriter(batchSize=10)
        record = self.makeRecord()

        await writer.write(record)
        await writer.flush()

        # 验证数据库中有数据
        conn = getConnection()
        cursor = conn.execute("SELECT COUNT(*) FROM danmu_records")
        count = cursor.fetchone()[0]
        assert count == 1
        assert writer.totalWritten == 1

    @pytest.mark.asyncio
    async def testWriteMultipleRecords(self):
        """写入多条记录后 flush"""
        writer = DanmuWriter(batchSize=10)

        for i in range(5):
            await writer.write(self.makeRecord(content=f"弹幕{i}"))

        await writer.flush()

        conn = getConnection()
        cursor = conn.execute("SELECT COUNT(*) FROM danmu_records")
        count = cursor.fetchone()[0]
        assert count == 5
        assert writer.totalWritten == 5

    @pytest.mark.asyncio
    async def testAutoFlushOnBatchSize(self):
        """达到 batchSize 时自动刷盘"""
        writer = DanmuWriter(batchSize=3)

        for i in range(3):
            await writer.write(self.makeRecord(content=f"弹幕{i}"))

        # 第 3 条触发自动刷盘
        assert writer.bufferSize == 0
        assert writer.totalWritten == 3

    @pytest.mark.asyncio
    async def testRecordFieldsCorrect(self):
        """验证写入的字段值正确"""
        writer = DanmuWriter(batchSize=1)
        record = DanmuRecord(
            room_id=999,
            uid=12345,
            username="小明",
            content="哈哈哈",
            timestamp=1700000123,
            medal_level=15,
            medal_name="舰长",
            user_level=30,
            is_gift=True,
            raw_json={"cmd": "DANMU_MSG"},
        )

        await writer.write(record)
        await writer.flush()

        conn = getConnection()
        row = conn.execute(
            "SELECT room_id, uid, username, content, timestamp, "
            "medal_level, medal_name, user_level, is_gift, raw_json "
            "FROM danmu_records WHERE room_id=999"
        ).fetchone()

        assert row[0] == 999
        assert row[1] == 12345
        assert row[2] == "小明"
        assert row[3] == "哈哈哈"
        assert row[4] == 1700000123
        assert row[5] == 15
        assert row[6] == "舰长"
        assert row[7] == 30
        assert row[8] == 1  # is_gift
        assert "DANMU_MSG" in row[9]

    @pytest.mark.asyncio
    async def testCloseFlushesRemaining(self):
        """close() 刷出剩余缓冲区数据"""
        writer = DanmuWriter(batchSize=100)

        for i in range(3):
            await writer.write(self.makeRecord(content=f"弹幕{i}"))

        assert writer.bufferSize == 3
        await writer.close()

        assert writer.bufferSize == 0

        conn = getConnection()
        cursor = conn.execute("SELECT COUNT(*) FROM danmu_records")
        count = cursor.fetchone()[0]
        assert count == 3

    @pytest.mark.asyncio
    async def testCloseIsIdempotent(self):
        """close() 可安全重复调用"""
        writer = DanmuWriter(batchSize=10)
        await writer.close()
        await writer.close()  # 不应抛异常

    @pytest.mark.asyncio
    async def testEmptyFlush(self):
        """空缓冲区 flush 不报错"""
        writer = DanmuWriter()
        await writer.flush()
        # 不抛异常即通过

    @pytest.mark.asyncio
    async def testTotalWrittenCount(self):
        """累计计数正确"""
        writer = DanmuWriter(batchSize=2)

        for i in range(5):
            await writer.write(self.makeRecord())

        await writer.flush()
        assert writer.totalWritten == 5
