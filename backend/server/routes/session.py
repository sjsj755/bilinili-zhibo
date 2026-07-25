"""会话管理 API 路由"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from db.queries.session import (
    getSessionsByRoom,
    getSessionById,
    deleteSession,
)
from db.queries.danmu import getDanmuBySessionId

router = APIRouter()


def _buildResponse(code: int, msg: str = "", data=None):
    return JSONResponse(content={"code": code, "msg": msg, "data": data})


@router.get("/{roomId}")
async def getSessions(roomId: int):
    """获取指定房间的所有采集会话列表

    Args:
        roomId: 直播间 ID

    Returns:
        会话列表，按开始时间倒序排列
    """
    sessions = getSessionsByRoom(roomId)
    return _buildResponse(0, "", sessions)


@router.get("/{roomId}/{sessionId}")
async def getSessionDetail(roomId: int, sessionId: int):
    """获取指定会话的详细信息和弹幕列表

    Args:
        roomId: 直播间 ID
        sessionId: 会话 ID

    Returns:
        会话详情和弹幕列表
    """
    session = getSessionById(sessionId)
    if session is None:
        return _buildResponse(-2, "会话不存在")

    if session["room_id"] != roomId:
        return _buildResponse(-2, "会话不属于该房间")

    danmuList = getDanmuBySessionId(sessionId)
    return _buildResponse(0, "", {
        "session": session,
        "danmuList": danmuList,
    })


@router.delete("/{roomId}/{sessionId}")
async def deleteSessionEndpoint(roomId: int, sessionId: int):
    """删除指定会话

    Args:
        roomId: 直播间 ID
        sessionId: 会话 ID

    Returns:
        删除结果
    """
    session = getSessionById(sessionId)
    if session is None:
        return _buildResponse(-2, "会话不存在")

    if session["room_id"] != roomId:
        return _buildResponse(-2, "会话不属于该房间")

    if session["status"] == "active":
        return _buildResponse(-4, "无法删除正在进行的会话")

    success = deleteSession(sessionId)
    if success:
        return _buildResponse(0, "删除成功")
    return _buildResponse(-3, "删除失败")
