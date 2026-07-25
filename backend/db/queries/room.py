"""rooms 表查询函数"""

from typing import Optional

from shared.types import Room
from ..database import getConnection
from ..schema import (
    SELECT_ALL_ROOMS,
    SELECT_ROOM_BY_ID,
    INSERT_ROOM,
    UPDATE_ROOM_STATUS,
    UPDATE_ROOM_INFO,
    DELETE_ROOM,
    SELECT_ROOM_DANMU_COUNT,
)


def _rowToRoom(row) -> Room:
    return Room(
        room_id=row[1],
        room_name=row[2] or "",
        anchor_name=row[3] or "",
        status=row[4] or "idle",
        error_msg=row[5] or "",
        created_at=row[6] or "",
        updated_at=row[7] or "",
    )


def getAllRooms() -> list[Room]:
    conn = getConnection()
    cursor = conn.execute(SELECT_ALL_ROOMS)
    rows = cursor.fetchall()
    return [_rowToRoom(row) for row in rows]


def getRoomByRoomId(roomId: int) -> Optional[Room]:
    conn = getConnection()
    cursor = conn.execute(SELECT_ROOM_BY_ID, (roomId,))
    row = cursor.fetchone()
    return _rowToRoom(row) if row else None


def insertRoom(room: Room) -> bool:
    conn = getConnection()
    cursor = conn.execute(INSERT_ROOM, (room.room_id, room.room_name, room.anchor_name))
    conn.commit()
    return cursor.rowcount > 0


def updateRoomStatus(roomId: int, status: str, errorMsg: str = "") -> bool:
    conn = getConnection()
    cursor = conn.execute(UPDATE_ROOM_STATUS, (status, errorMsg, roomId))
    conn.commit()
    return cursor.rowcount > 0


def updateRoomInfo(roomId: int, roomName: str, anchorName: str) -> bool:
    conn = getConnection()
    cursor = conn.execute(UPDATE_ROOM_INFO, (roomName, anchorName, roomId))
    conn.commit()
    return cursor.rowcount > 0


def deleteRoom(roomId: int) -> bool:
    conn = getConnection()
    cursor = conn.execute(DELETE_ROOM, (roomId,))
    conn.commit()
    return cursor.rowcount > 0


def getRoomDanmuCount(roomId: int) -> int:
    conn = getConnection()
    cursor = conn.execute(SELECT_ROOM_DANMU_COUNT, (roomId,))
    row = cursor.fetchone()
    return row[0] if row else 0