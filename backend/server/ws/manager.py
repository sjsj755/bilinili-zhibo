"""WebSocket 连接管理器

负责管理所有客户端 WebSocket 连接和房间订阅关系，
提供广播能力供采集层推送弹幕和分析数据。

设计要点：
- 全局单例（wsManager），严禁在处理器内部新建实例
- 反向索引：房间 → 订阅客户端集合，O(1) 广播
- 正向索引：客户端 → 订阅房间集合，断开时快速清理
- 线程安全：所有操作由 asyncio.Lock 保护
"""

import asyncio
import logging
from typing import Any

from fastapi import WebSocket
from shared.types import DanmuRecord

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 25
HEARTBEAT_MESSAGE = {"type": "heartbeat"}


class ConnectionManager:
    """WebSocket 连接管理器

    维护客户端连接与房间订阅的双向映射，
    支持弹幕、分析数据等多类型消息的房间级广播。
    """

    def __init__(self):
        self._clientRooms: dict[WebSocket, set[int]] = {}
        self._roomClients: dict[int, set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._heartbeatTask: asyncio.Task[None] | None = None
        self._isRunning = False

    async def startHeartbeat(self) -> None:
        """启动全局心跳任务

        每 HEARTBEAT_INTERVAL 秒向所有活跃连接发送心跳消息。
        可安全重复调用，已启动时直接返回。
        """
        if self._isRunning and self._heartbeatTask and not self._heartbeatTask.done():
            return

        self._isRunning = True
        self._heartbeatTask = asyncio.create_task(self._heartbeatLoop())
        logger.info("WebSocket 全局心跳已启动（间隔 %ds）", HEARTBEAT_INTERVAL)

    async def stopHeartbeat(self) -> None:
        """停止全局心跳任务

        可安全重复调用。
        """
        self._isRunning = False
        if self._heartbeatTask and not self._heartbeatTask.done():
            self._heartbeatTask.cancel()
            try:
                await self._heartbeatTask
            except (asyncio.CancelledError, Exception):
                pass
        self._heartbeatTask = None
        logger.info("WebSocket 全局心跳已停止")

    async def _heartbeatLoop(self) -> None:
        """心跳循环：向所有活跃连接发送 ping 消息"""
        while self._isRunning:
            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if not self._isRunning:
                    break

                async with self._lock:
                    clients = list(self._clientRooms.keys())

                deadClients: list[WebSocket] = []
                for ws in clients:
                    if not await self._sendSafe(ws, HEARTBEAT_MESSAGE):
                        deadClients.append(ws)

                if deadClients:
                    async with self._lock:
                        for ws in deadClients:
                            roomIds = self._clientRooms.pop(ws, set())
                            for rid in roomIds:
                                roomClients = self._roomClients.get(rid)
                                if roomClients:
                                    roomClients.discard(ws)
                                    if not roomClients:
                                        del self._roomClients[rid]
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("心跳发送异常: %s", e)

    async def connect(self, ws: WebSocket) -> None:
        """注册新的客户端连接

        Args:
            ws: WebSocket 连接对象
        """
        async with self._lock:
            self._clientRooms[ws] = set()
        logger.debug("客户端连接，当前连接数: %d", len(self._clientRooms))

    async def disconnect(self, ws: WebSocket) -> None:
        """移除客户端连接并清理所有订阅

        Args:
            ws: WebSocket 连接对象
        """
        async with self._lock:
            roomIds = self._clientRooms.pop(ws, set())
            for roomId in roomIds:
                clients = self._roomClients.get(roomId)
                if clients:
                    clients.discard(ws)
                    if not clients:
                        del self._roomClients[roomId]
        logger.debug("客户端断开，当前连接数: %d", len(self._clientRooms))

    async def subscribe(self, ws: WebSocket, roomId: int) -> None:
        """客户端订阅指定房间的弹幕

        Args:
            ws: WebSocket 连接对象
            roomId: 直播间 ID
        """
        async with self._lock:
            self._clientRooms.setdefault(ws, set()).add(roomId)
            self._roomClients.setdefault(roomId, set()).add(ws)
        logger.debug("客户端订阅房间 %d，该房间订阅数: %d", roomId, self._getRoomSubscriberCountUnsafe(roomId))

    async def unsubscribe(self, ws: WebSocket, roomId: int) -> None:
        """客户端取消订阅指定房间

        Args:
            ws: WebSocket 连接对象
            roomId: 直播间 ID
        """
        async with self._lock:
            roomIds = self._clientRooms.get(ws)
            if roomIds:
                roomIds.discard(roomId)
            clients = self._roomClients.get(roomId)
            if clients:
                clients.discard(ws)
                if not clients:
                    del self._roomClients[roomId]
        logger.debug("客户端取消订阅房间 %d，该房间订阅数: %d", roomId, self._getRoomSubscriberCountUnsafe(roomId))

    async def broadcastDanmu(self, roomId: int, record: DanmuRecord) -> None:
        """向订阅指定房间的所有客户端推送弹幕

        Args:
            roomId: 直播间 ID
            record: 弹幕记录
        """
        data = {
            "room_id": record.room_id,
            "session_id": record.session_id,
            "uid": record.uid,
            "username": record.username,
            "content": record.content,
            "timestamp": record.timestamp,
            "medal_level": record.medal_level,
            "medal_name": record.medal_name,
            "user_level": record.user_level,
            "is_gift": record.is_gift,
        }
        logger.info("准备广播弹幕 房间=%d 会话=%d 用户名=%s 内容=%s", roomId, record.session_id, record.username, record.content[:50])
        await self.broadcast(roomId, "danmu", data)

    async def broadcastStats(self, roomId: int, stats: dict[str, Any]) -> None:
        """向订阅指定房间的所有客户端推送实时分析数据

        Args:
            roomId: 直播间 ID
            stats: 实时统计数据字典
        """
        await self.broadcast(roomId, "realtime_stats", stats)

    async def broadcastError(self, roomId: int, message: str) -> None:
        """向订阅指定房间的所有客户端推送连接错误

        Args:
            roomId: 直播间 ID
            message: 错误信息
        """
        data = {"room_id": roomId, "message": message}
        await self.broadcast(roomId, "connection_error", data)

    async def broadcast(self, roomId: int, msgType: str, data: Any) -> None:
        """向指定房间的所有订阅者广播消息

        Args:
            roomId: 直播间 ID
            msgType: 消息类型
            data: 消息数据
        """
        async with self._lock:
            clients = list(self._roomClients.get(roomId, set()))

        logger.info("广播消息 类型=%s 房间=%d 订阅者数=%d", msgType, roomId, len(clients))

        if not clients:
            logger.warning("房间 %d 没有订阅者，跳过广播", roomId)
            return

        message = {"type": msgType, "data": data}
        deadClients: list[WebSocket] = []
        successCount = 0

        for ws in clients:
            try:
                await ws.send_json(message)
                successCount += 1
            except Exception as e:
                deadClients.append(ws)
                logger.warning("发送消息给客户端失败: %s", e)

        logger.info("广播完成 成功=%d 失败=%d", successCount, len(deadClients))

        if deadClients:
            async with self._lock:
                for ws in deadClients:
                    roomIds = self._clientRooms.pop(ws, set())
                    for rid in roomIds:
                        roomClients = self._roomClients.get(rid)
                        if roomClients:
                            roomClients.discard(ws)
                            if not roomClients:
                                del self._roomClients[rid]

    async def _sendSafe(self, ws: WebSocket, message: Any) -> bool:
        """安全发送消息，捕获连接异常

        Args:
            ws: WebSocket 连接对象
            message: 消息内容

        Returns:
            bool: True 表示发送成功，False 表示连接已断开
        """
        try:
            await ws.send_json(message)
            return True
        except Exception:
            return False

    async def getClientCount(self) -> int:
        """获取当前总连接数

        Returns:
            int: 活跃连接数
        """
        async with self._lock:
            return len(self._clientRooms)

    async def getRoomSubscriberCount(self, roomId: int) -> int:
        """获取指定房间的订阅数

        Args:
            roomId: 直播间 ID

        Returns:
            int: 订阅该房间的客户端数
        """
        async with self._lock:
            return self._getRoomSubscriberCountUnsafe(roomId)

    def _getRoomSubscriberCountUnsafe(self, roomId: int) -> int:
        """无锁版本的房间订阅数查询（调用方需持有 _lock）"""
        return len(self._roomClients.get(roomId, set()))

    async def getStatus(self) -> dict[str, Any]:
        """获取管理器状态快照

        Returns:
            dict: 包含总连接数和各房间订阅数的状态字典
        """
        async with self._lock:
            totalClients = len(self._clientRooms)
            roomCounts = {str(rid): len(clients) for rid, clients in self._roomClients.items()}
        return {
            "total_clients": totalClients,
            "room_subscribers": roomCounts,
            "heartbeat_interval": HEARTBEAT_INTERVAL,
        }


wsManager = ConnectionManager()
