"""数据库初始化、连接管理与弹幕批量写入"""

import asyncio
import json
import logging
import sqlite3
from pathlib import Path

from shared.types import DanmuRecord
from .schema import ALL_TABLES, INSERT_DANMU, ALTER_ROOMS_ANCHOR_NAME, ALTER_DANMU_ADD_SESSION_ID

logger = logging.getLogger(__name__)

_connection: sqlite3.Connection | None = None


def initDb(dbPath: str) -> sqlite3.Connection:
    """初始化数据库：创建连接、开启 WAL、执行建表

    可安全重复调用，已存在的表不会被覆盖。

    Args:
        dbPath: 数据库文件路径（如 "data/bilinili.db"）

    Returns:
        sqlite3.Connection: 已初始化的数据库连接
    """
    global _connection

    # 确保父目录存在
    dbFile = Path(dbPath)
    dbFile.parent.mkdir(parents=True, exist_ok=True)

    # 关闭已有连接
    if _connection is not None:
        _connection.close()

    conn = sqlite3.connect(str(dbPath), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-8000")  # 8MB 缓存

    for sql in ALL_TABLES:
        conn.execute(sql)

    try:
        conn.execute(ALTER_ROOMS_ANCHOR_NAME)
        conn.commit()
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute(ALTER_DANMU_ADD_SESSION_ID)
        conn.commit()
    except sqlite3.OperationalError:
        pass

    conn.commit()
    _connection = conn

    logger.info("数据库已初始化: %s (WAL 模式)", dbPath)
    return conn


def getConnection() -> sqlite3.Connection:
    """获取已初始化的数据库连接

    Returns:
        sqlite3.Connection

    Raises:
        RuntimeError: 数据库未初始化
    """
    if _connection is None:
        raise RuntimeError("数据库未初始化，请先调用 initDb()")
    return _connection


def closeDb() -> None:
    """关闭数据库连接"""
    global _connection
    if _connection:
        _connection.close()
        _connection = None
        logger.info("数据库连接已关闭")


class DanmuWriter:
    """弹幕批量写入器

    攒批写入 + 定时刷盘，减少 SQLite 事务频率。
    通过 asyncio.to_thread 在线程池中执行同步写入，不阻塞事件循环。

    使用示例:
        writer = DanmuWriter(batchSize=100, flushInterval=1.0)
        await writer.write(record)    # 写入缓冲区
        await writer.close()          # 关闭并最终刷盘

    Attributes:
        batchSize: 攒批条数阈值
        flushInterval: 定时刷盘间隔（秒）
        bufferSize: 当前缓冲区中待写入记录数
        totalWritten: 累计已写入记录数
    """

    def __init__(self, batchSize: int = 100, flushInterval: float = 5.0):
        self.batchSize = batchSize
        self.flushInterval = flushInterval

        self.bufferSize = 0
        self.totalWritten = 0

        self._buffer: list[tuple] = []
        self._lock = asyncio.Lock()
        self._flushTask: asyncio.Task | None = None
        self._isRunning = True

        asyncio.create_task(self._scheduledFlush())

    async def _scheduledFlush(self) -> None:
        """定时刷盘任务"""
        while self._isRunning:
            await asyncio.sleep(self.flushInterval)
            if self._buffer:
                await self.flush()

    async def write(self, record: DanmuRecord) -> None:
        """写入一条弹幕记录到缓冲区

        达到 batchSize 时自动触发刷盘。

        Args:
            record: 弹幕记录对象
        """
        row = self._recordToRow(record)

        async with self._lock:
            self._buffer.append(row)
            self.bufferSize = len(self._buffer)

            if self.bufferSize >= self.batchSize:
                # 达到阈值，在锁内取出数据，锁外执行写入
                batch = self._buffer[:]
                self._buffer.clear()
                self.bufferSize = 0
                needFlush = True
            else:
                needFlush = False

        if needFlush:
            await self._doFlush(batch)

    async def flush(self) -> None:
        """手动强制刷盘，将缓冲区中所有数据写入数据库"""
        async with self._lock:
            if not self._buffer:
                return
            batch = self._buffer[:]
            self._buffer.clear()
            self.bufferSize = 0

        await self._doFlush(batch)

    async def close(self) -> None:
        """关闭写入器：取消定时器 + 最终刷盘，可安全重复调用"""
        self._isRunning = False

        if self._flushTask and not self._flushTask.done():
            self._flushTask.cancel()
            try:
                await self._flushTask
            except asyncio.CancelledError:
                pass
        self._flushTask = None

        await self.flush()
        logger.info("DanmuWriter 已关闭，累计写入 %d 条弹幕", self.totalWritten)

    async def _doFlush(self, batch: list[tuple]) -> None:
        """实际执行数据库写入（在线程池中运行）"""
        logger.info("开始刷盘 %d 条弹幕", len(batch))
        try:
            count = await asyncio.to_thread(self._insertBatch, batch)
            self.totalWritten += count
            logger.info("刷盘成功，已写入 %d 条，累计 %d 条", count, self.totalWritten)
        except Exception as e:
            logger.error("弹幕批量写入失败: %s，丢弃 %d 条记录", e, len(batch))

    def _insertBatch(self, batch: list[tuple]) -> int:
        """同步批量插入（运行在线程池中）"""
        conn = getConnection()
        conn.executemany(INSERT_DANMU, batch)
        conn.commit()
        return len(batch)

    @staticmethod
    def _recordToRow(record: DanmuRecord) -> tuple:
        """将 DanmuRecord 转换为数据库行元组"""
        rawJson = json.dumps(record.raw_json, ensure_ascii=False) if record.raw_json else ""
        return (
            record.room_id,
            record.session_id or 0,
            record.uid,
            record.username,
            record.content,
            record.timestamp,
            record.medal_level,
            record.medal_name,
            record.user_level,
            1 if record.is_gift else 0,
            rawJson,
        )
