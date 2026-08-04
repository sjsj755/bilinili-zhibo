"""danmu_records 表查询函数"""

import asyncio
from typing import Optional, AsyncIterator, List, Dict, Any

from shared.types import DanmuRecord
from ..database import getConnection
from ..schema import (
    SELECT_DANMU_BY_ROOM,
    SELECT_DANMU_BY_SESSION,
    SELECT_DANMU_BY_ROOM_AND_TIME,
    SELECT_DANMU_COUNT,
    SELECT_DANMU_COUNT_BY_ROOM_AND_TIME,
    SELECT_DANMU_STATS,
    SELECT_DANMU_PEAK_HOUR,
)


def _rowToDanmu(row) -> dict:
    return {
        "room_id": row[1],
        "session_id": row[2],
        "uid": row[3],
        "username": row[4] or "",
        "content": row[5] or "",
        "timestamp": row[6],
        "medal_level": row[7],
        "medal_name": row[8] or "",
        "user_level": row[9],
        "is_gift": bool(row[10]),
    }


def getDanmuByRoomId(roomId: int, offset: int = 0, limit: int = 50) -> list[dict]:
    conn = getConnection()
    cursor = conn.execute(SELECT_DANMU_BY_ROOM, (roomId, limit, offset))
    rows = cursor.fetchall()
    return [_rowToDanmu(row) for row in rows]


def getDanmuCount(roomId: int) -> int:
    conn = getConnection()
    cursor = conn.execute(SELECT_DANMU_COUNT, (roomId,))
    row = cursor.fetchone()
    return row[0] if row else 0


def getDanmuBySessionId(sessionId: int) -> list[dict]:
    """根据会话 ID 获取该会话的所有弹幕

    Args:
        sessionId: 会话 ID

    Returns:
        list[dict]: 弹幕列表，按时间戳正序排列
    """
    conn = getConnection()
    cursor = conn.execute(SELECT_DANMU_BY_SESSION, (sessionId,))
    rows = cursor.fetchall()
    return [_rowToDanmu(row) for row in rows]


def getDanmuStats(roomId: int) -> Optional[dict]:
    conn = getConnection()
    
    cursor = conn.execute(SELECT_DANMU_STATS, (roomId,))
    statsRow = cursor.fetchone()
    
    if not statsRow or statsRow[0] == 0:
        return None
    
    totalCount, uniqueUsers, minTime, maxTime = statsRow
    
    cursor = conn.execute(SELECT_DANMU_PEAK_HOUR, (roomId,))
    peakRow = cursor.fetchone()
    
    peakHour = peakRow[0] if peakRow else ""
    peakCount = peakRow[1] if peakRow else 0
    
    return {
        "total_count": totalCount,
        "unique_users": uniqueUsers,
        "peak_hour": peakHour,
        "peak_count": peakCount,
        "min_time": minTime,
        "max_time": maxTime,
    }


def getDanmuByTimeRange(roomId: int, startTime: int, endTime: int, 
                        limit: int = 5000, offset: int = 0) -> List[Dict[str, Any]]:
    """获取指定房间在指定时间范围内的弹幕（支持分页）
    
    Args:
        roomId: 直播间 ID
        startTime: 起始时间戳
        endTime: 结束时间戳
        limit: 每页数量
        offset: 偏移量
        
    Returns:
        List[Dict]: 弹幕列表
    """
    conn = getConnection()
    cursor = conn.execute(SELECT_DANMU_BY_ROOM_AND_TIME, 
                          (roomId, startTime, endTime, limit, offset))
    rows = cursor.fetchall()
    return [_rowToDanmu(row) for row in rows]


def getDanmuCountByTimeRange(roomId: int, startTime: int, endTime: int) -> int:
    """获取指定房间在指定时间范围内的弹幕数量
    
    Args:
        roomId: 直播间 ID
        startTime: 起始时间戳
        endTime: 结束时间戳
        
    Returns:
        int: 弹幕数量
    """
    conn = getConnection()
    cursor = conn.execute(SELECT_DANMU_COUNT_BY_ROOM_AND_TIME, 
                          (roomId, startTime, endTime))
    row = cursor.fetchone()
    return row[0] if row else 0


async def getDanmuChunkIterator(roomId: int, startTime: int, endTime: int, 
                                chunkSize: int = 5000) -> AsyncIterator[List[Dict[str, Any]]]:
    """异步迭代器，分块产出指定时间范围的弹幕（流式处理核心）
    
    Args:
        roomId: 直播间 ID
        startTime: 起始时间戳
        endTime: 结束时间戳
        chunkSize: 每块的弹幕数量
        
    Yields:
        AsyncIterator[List[Dict]]: 一个分块的弹幕列表
    """
    offset = 0
    while True:
        # 将同步的数据库查询放到线程池中执行，避免阻塞事件循环
        chunk = await asyncio.to_thread(
            getDanmuByTimeRange, roomId, startTime, endTime, chunkSize, offset
        )
        if not chunk:
            break
        yield chunk
        offset += chunkSize