"""多直播间采集管理器

负责管理多个 BiliClient 实例，协调采集启停，
通过回调函数将弹幕推送到数据库和 WebSocket，
并在采集状态变化时同步更新数据库。

设计要点：
- 全局单例 collectorManager，严禁在处理器内部新建实例
- 不依赖 server 模块，通过回调函数注入实现解耦
- 回调支持同步和异步两种形式
- 使用 asyncio.gather 并发写入数据库和推送 WebSocket
- 采集异常时更新房间错误信息，恢复后清除错误
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from .bili_client import BiliClient, DanmuRecord
from utils.config import loadEnv

logger = logging.getLogger(__name__)

MAX_CONCURRENT_ROOMS = 5


class CollectorManager:
    """多直播间采集管理器

    通过回调函数解耦与 server 模块的依赖，
    采集到的弹幕通过 onDanmu 回调推送到数据库和 WebSocket。

    使用示例:
        async def onDanmu(record):
            await danmuWriter.write(record)
            await wsManager.broadcastDanmu(record.room_id, record)

        async def onStatusChange(roomId, status, errorMsg):
            updateRoomStatus(roomId, status, errorMsg)

        def onCreateSession(roomId):
            return createSession(roomId)

        def onEndSession(sessionId):
            endSession(sessionId)

        collectorManager.setCallbacks(onDanmu, onStatusChange, onCreateSession, onEndSession)
        await collectorManager.start_monitor(12345)
    """

    def __init__(self):
        self._clients: dict[int, BiliClient] = {}
        self._sessionIds: dict[int, int] = {}
        self._lock = asyncio.Lock()
        self._onDanmu: Callable[[DanmuRecord], Any] | None = None
        self._onStatusChange: Callable[[int, str, str], Any] | None = None
        self._onCreateSession: Callable[[int], int] | None = None
        self._onEndSession: Callable[[int], None] | None = None
        self._env = loadEnv()
        self._sessdata = self._env.get("SESSDATA", "")
        self._uid = int(self._env.get("BILI_UID", "0"))

    def setCallbacks(
        self,
        onDanmu: Callable[[DanmuRecord], Any] | None = None,
        onStatusChange: Callable[[int, str, str], Any] | None = None,
        onCreateSession: Callable[[int], int] | None = None,
        onEndSession: Callable[[int], None] | None = None,
    ) -> None:
        """设置回调函数

        Args:
            onDanmu: 弹幕到达时的回调，支持同步和异步
            onStatusChange: 采集状态变化时的回调，支持同步和异步
            onCreateSession: 创建会话的回调，返回会话 ID
            onEndSession: 结束会话的回调
        """
        self._onDanmu = onDanmu
        self._onStatusChange = onStatusChange
        self._onCreateSession = onCreateSession
        self._onEndSession = onEndSession

    async def start_monitor(self, roomId: int) -> bool:
        """启动指定房间的弹幕采集

        Args:
            roomId: 直播间 ID

        Returns:
            bool: 是否成功启动
        """
        async with self._lock:
            if roomId in self._clients:
                client = self._clients[roomId]
                if client.isRunning:
                    logger.info("房间 %d 已在采集中", roomId)
                    return True
                await client.disconnect()
                self._clients.pop(roomId, None)

            if len(self._clients) >= MAX_CONCURRENT_ROOMS:
                logger.error("房间数量已达上限 %d，无法添加房间 %d", MAX_CONCURRENT_ROOMS, roomId)
                await self._notifyStatusChange(roomId, "error", f"房间数量已达上限 {MAX_CONCURRENT_ROOMS}")
                return False

        sessionId = 0
        if self._onEndSession:
            import db.queries.session as sessionQueries
            activeSession = sessionQueries.getActiveSession(roomId)
            if activeSession:
                logger.info("房间 %d 存在未结束的会话 %d，先结束它", roomId, activeSession["id"])
                self._onEndSession(activeSession["id"])

        if self._onCreateSession:
            sessionId = self._onCreateSession(roomId)
            logger.info("房间 %d 已创建采集会话: %d", roomId, sessionId)

        client = BiliClient(
            room_id=roomId,
            onDanmu=lambda record: self._onDanmuWrapper(record, sessionId),
            sessdata=self._sessdata,
            uid=self._uid,
        )

        async with self._lock:
            self._clients[roomId] = client
            self._sessionIds[roomId] = sessionId

        await self._notifyStatusChange(roomId, "monitoring", "")

        asyncio.create_task(self._monitorLoop(client))
        logger.info("房间 %d 采集任务已启动", roomId)
        return True

    async def stop_monitor(self, roomId: int) -> bool:
        """停止指定房间的弹幕采集

        Args:
            roomId: 直播间 ID

        Returns:
            bool: 是否成功停止
        """
        async with self._lock:
            client = self._clients.get(roomId)
            if not client:
                logger.info("房间 %d 未在采集", roomId)
                return True

            self._clients.pop(roomId, None)
            sessionId = self._sessionIds.pop(roomId, 0)

        try:
            await client.disconnect()
        except Exception as e:
            logger.warning("断开房间 %d 连接时出错: %s", roomId, e)

        if sessionId > 0 and self._onEndSession:
            self._onEndSession(sessionId)
            logger.info("房间 %d 采集会话 %d 已结束", roomId, sessionId)

        await self._notifyStatusChange(roomId, "idle", "")
        logger.info("房间 %d 采集已停止", roomId)
        return True

    async def stop_all(self) -> None:
        """停止所有房间的采集"""
        async with self._lock:
            clients = list(self._clients.values())
            sessionIds = list(self._sessionIds.values())
            self._clients.clear()
            self._sessionIds.clear()

        for client, sessionId in zip(clients, sessionIds):
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning("停止房间 %d 采集时出错: %s", client.room_id, e)

            if sessionId > 0 and self._onEndSession:
                self._onEndSession(sessionId)

        logger.info("所有房间采集已停止")

    def is_monitoring(self, roomId: int) -> bool:
        """检查指定房间是否正在采集

        Args:
            roomId: 直播间 ID

        Returns:
            bool: 是否正在采集
        """
        client = self._clients.get(roomId)
        return client is not None and client.isRunning

    async def get_status(self) -> dict[int, dict[str, Any]]:
        """获取所有房间的采集状态

        Returns:
            dict: {roomId: {status, isConnected, isRunning}}
        """
        async with self._lock:
            status = {}
            for roomId, client in self._clients.items():
                status[roomId] = {
                    "status": "monitoring" if client.isRunning else "connecting",
                    "is_connected": client.isConnected,
                    "is_running": client.isRunning,
                }
        return status

    async def _monitorLoop(self, client: BiliClient) -> None:
        """采集循环：启动客户端并处理异常

        连接断开后自动触发状态更新，由 BiliClient 内部处理重连。
        """
        roomId = client.room_id
        try:
            await client.start()
        except Exception as e:
            logger.error("房间 %d 采集循环异常: %s", roomId, e)
            await self._notifyStatusChange(roomId, "error", str(e))
        finally:
            async with self._lock:
                if self._clients.get(roomId) == client:
                    self._clients.pop(roomId, None)

    async def _onDanmuWrapper(self, record: DanmuRecord, sessionId: int) -> None:
        """弹幕回调包装器

        调用用户注册的 onDanmu 回调，支持同步和异步。
        将 sessionId 设置到弹幕记录中。

        Args:
            record: 弹幕记录
            sessionId: 会话 ID
        """
        if not self._onDanmu:
            return

        record.session_id = sessionId

        try:
            if asyncio.iscoroutinefunction(self._onDanmu):
                await self._onDanmu(record)
            else:
                self._onDanmu(record)
        except Exception as e:
            logger.error("弹幕回调执行异常: %s", e)

    async def _notifyStatusChange(self, roomId: int, status: str, errorMsg: str) -> None:
        """通知状态变化

        调用用户注册的 onStatusChange 回调，支持同步和异步。
        """
        if not self._onStatusChange:
            return

        try:
            if asyncio.iscoroutinefunction(self._onStatusChange):
                await self._onStatusChange(roomId, status, errorMsg)
            else:
                self._onStatusChange(roomId, status, errorMsg)
        except Exception as e:
            logger.error("状态变更回调执行异常: %s", e)


collectorManager = CollectorManager()
