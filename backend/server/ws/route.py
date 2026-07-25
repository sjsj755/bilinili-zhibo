"""WebSocket 端点处理

端点路径: /ws
协议: JSON 消息，type 字段区分消息类型

客户端 → 服务端:
  { "type": "subscribe", "roomId": 12345 }
  { "type": "unsubscribe", "roomId": 12345 }
  { "type": "heartbeat" }

服务端 → 客户端:
  { "type": "connected" }
  { "type": "subscribed", "roomId": 12345 }
  { "type": "unsubscribed", "roomId": 12345 }
  { "type": "danmu", "data": {...} }
  { "type": "realtime_stats", "data": {...} }
  { "type": "connection_error", "data": { "room_id": 12345, "message": "..." } }
  { "type": "heartbeat" }
  { "type": "error", "message": "..." }

设计要点:
- 单一读入口：仅主 receive 循环读取消息，避免多协程抢读
- 心跳由全局心跳任务统一发送，此处不单独启用心跳
- 自动订阅：连接时若带 roomId 查询参数则自动订阅
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from .manager import wsManager

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_CLIENT_MSG_TYPES = {"subscribe", "unsubscribe", "heartbeat"}


@router.websocket("")
async def websocketEndpoint(ws: WebSocket, roomId: int | None = Query(default=None)):
    """WebSocket 实时消息推送端点

    Args:
        ws: WebSocket 连接
        roomId: 可选查询参数，连接后自动订阅该房间
    """
    await ws.accept()
    await wsManager.connect(ws)

    try:
        await ws.send_json({"type": "connected"})

        if roomId is not None:
            await wsManager.subscribe(ws, roomId)
            await ws.send_json({"type": "subscribed", "roomId": roomId})
            logger.info("客户端自动订阅房间 %d", roomId)

        while True:
            try:
                rawText = await ws.receive_text()
            except WebSocketDisconnect:
                break

            try:
                msg = json.loads(rawText)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "消息格式错误，需要 JSON"})
                continue

            if not isinstance(msg, dict):
                await ws.send_json({"type": "error", "message": "消息必须是 JSON 对象"})
                continue

            msgType = msg.get("type")
            if msgType not in VALID_CLIENT_MSG_TYPES:
                await ws.send_json({"type": "error", "message": f"未知消息类型: {msgType}"})
                continue

            if msgType == "subscribe":
                targetRoomId = msg.get("roomId")
                if not isinstance(targetRoomId, int) or targetRoomId <= 0:
                    await ws.send_json({"type": "error", "message": "roomId 参数无效"})
                    continue
                await wsManager.subscribe(ws, targetRoomId)
                await ws.send_json({"type": "subscribed", "roomId": targetRoomId})
                logger.debug("客户端订阅房间 %d", targetRoomId)

            elif msgType == "unsubscribe":
                targetRoomId = msg.get("roomId")
                if not isinstance(targetRoomId, int) or targetRoomId <= 0:
                    await ws.send_json({"type": "error", "message": "roomId 参数无效"})
                    continue
                await wsManager.unsubscribe(ws, targetRoomId)
                await ws.send_json({"type": "unsubscribed", "roomId": targetRoomId})
                logger.debug("客户端取消订阅房间 %d", targetRoomId)

            elif msgType == "heartbeat":
                pass
    except Exception as e:
        if not isinstance(e, WebSocketDisconnect):
            logger.warning("WebSocket 连接异常: %s", e)
    finally:
        await wsManager.disconnect(ws)
        logger.info("WebSocket 连接已关闭")
