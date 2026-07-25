"""会话数据查询模块"""

from typing import Optional, List, Dict, Any

from db.database import getConnection
from db.schema import (
    INSERT_SESSION,
    SELECT_SESSION_BY_ID,
    SELECT_SESSIONS_BY_ROOM,
    SELECT_ACTIVE_SESSION,
    UPDATE_SESSION_END,
    DELETE_SESSION,
)


def createSession(roomId: int) -> int:
    """创建新的采集会话

    Args:
        roomId: 直播间 ID

    Returns:
        int: 新建会话的 ID
    """
    conn = getConnection()
    cursor = conn.execute(INSERT_SESSION, (roomId,))
    conn.commit()
    return cursor.lastrowid


def getSessionById(sessionId: int) -> Optional[Dict[str, Any]]:
    """根据会话 ID 获取会话信息

    Args:
        sessionId: 会话 ID

    Returns:
        Optional[Dict]: 会话信息，如果不存在返回 None
    """
    conn = getConnection()
    cursor = conn.execute(SELECT_SESSION_BY_ID, (sessionId,))
    row = cursor.fetchone()
    if row is None:
        return None
    return _rowToDict(row)


def getSessionsByRoom(roomId: int) -> List[Dict[str, Any]]:
    """获取指定房间的所有采集会话，按开始时间倒序排列

    Args:
        roomId: 直播间 ID

    Returns:
        List[Dict]: 会话列表
    """
    conn = getConnection()
    cursor = conn.execute(SELECT_SESSIONS_BY_ROOM, (roomId,))
    rows = cursor.fetchall()
    return [_rowToDict(row) for row in rows]


def getActiveSession(roomId: int) -> Optional[Dict[str, Any]]:
    """获取指定房间当前活跃的采集会话

    Args:
        roomId: 直播间 ID

    Returns:
        Optional[Dict]: 活跃会话信息，如果不存在返回 None
    """
    conn = getConnection()
    cursor = conn.execute(SELECT_ACTIVE_SESSION, (roomId,))
    row = cursor.fetchone()
    if row is None:
        return None
    return _rowToDict(row)


def endSession(sessionId: int) -> bool:
    """结束指定会话，更新结束时间和弹幕数量

    Args:
        sessionId: 会话 ID

    Returns:
        bool: 是否成功更新
    """
    conn = getConnection()
    cursor = conn.execute(UPDATE_SESSION_END, (sessionId, sessionId))
    conn.commit()
    return cursor.rowcount > 0


def deleteSession(sessionId: int) -> bool:
    """删除指定会话

    Args:
        sessionId: 会话 ID

    Returns:
        bool: 是否成功删除
    """
    conn = getConnection()
    cursor = conn.execute(DELETE_SESSION, (sessionId,))
    conn.commit()
    return cursor.rowcount > 0


def endAllActiveSessions() -> int:
    """结束所有活跃会话（用于服务重启时清理）

    Returns:
        int: 结束的会话数量
    """
    conn = getConnection()
    cursor = conn.execute("""
        UPDATE sessions 
        SET end_time = datetime('now', 'localtime'), status = 'ended' 
        WHERE status = 'active'
    """)
    conn.commit()
    return cursor.rowcount


def _rowToDict(row: tuple) -> Dict[str, Any]:
    """将数据库行转换为字典"""
    return {
        "id": row[0],
        "room_id": row[1],
        "start_time": row[2],
        "end_time": row[3],
        "danmu_count": row[4],
        "status": row[5],
        "created_at": row[6],
    }
