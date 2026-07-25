from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from shared.types import Room
from db.queries.room import (
    getAllRooms,
    getRoomByRoomId,
    insertRoom,
    updateRoomStatus,
    deleteRoom,
    getRoomDanmuCount,
)
from services.bili_api import resolveRoomId, getRoomInfo
from collector import collectorManager

router = APIRouter()


class RoomCreateRequest(BaseModel):
    roomId: int


def _buildResponse(code: int, msg: str = "", data=None):
    return JSONResponse(content={"code": code, "msg": msg, "data": data})


@router.get("")
async def getRooms():
    rooms = getAllRooms()
    roomList = []
    for room in rooms:
        count = getRoomDanmuCount(room.room_id)
        roomList.append({
            "room_id": room.room_id,
            "room_name": room.room_name,
            "anchor_name": room.anchor_name,
            "status": room.status,
            "error_msg": room.error_msg,
            "danmu_count": count,
            "created_at": room.created_at,
            "updated_at": room.updated_at,
        })
    return _buildResponse(0, "", roomList)


@router.post("")
async def addRoom(body: RoomCreateRequest):
    try:
        realRoomId = await resolveRoomId(body.roomId)
        roomInfo = await getRoomInfo(realRoomId)

        room = Room(
            room_id=realRoomId,
            room_name=roomInfo.get("title", ""),
            anchor_name=roomInfo.get("anchor_name", "") or roomInfo.get("uname", ""),
        )

        inserted = insertRoom(room)
        if inserted:
            return _buildResponse(0, "添加成功", {
                "room_id": realRoomId,
                "room_name": room.room_name,
                "anchor_name": room.anchor_name,
            })
        else:
            existing = getRoomByRoomId(realRoomId)
            return _buildResponse(0, "房间已存在", {
                "room_id": existing.room_id,
                "room_name": existing.room_name,
                "anchor_name": existing.anchor_name,
            })

    except Exception as e:
        return _buildResponse(-1, str(e))


@router.delete("/{roomId}")
async def deleteRoomEndpoint(roomId: int):
    room = getRoomByRoomId(roomId)
    if not room:
        return _buildResponse(-1, "房间不存在")

    if room.status == "monitoring":
        await collectorManager.stop_monitor(roomId)

    deleted = deleteRoom(roomId)
    if deleted:
        return _buildResponse(0, "删除成功")
    else:
        return _buildResponse(-1, "删除失败")


@router.post("/{roomId}/monitor")
async def startMonitor(roomId: int):
    room = getRoomByRoomId(roomId)
    if not room:
        return _buildResponse(-1, "房间不存在")

    if room.status == "monitoring":
        return _buildResponse(0, "已在采集中")

    success = await collectorManager.start_monitor(roomId)
    if success:
        return _buildResponse(0, "开始采集")
    else:
        return _buildResponse(-1, "启动采集失败")


@router.post("/{roomId}/monitor/stop")
async def stopMonitor(roomId: int):
    room = getRoomByRoomId(roomId)
    if not room:
        return _buildResponse(-1, "房间不存在")

    if room.status != "monitoring":
        return _buildResponse(0, "当前未在采集")

    success = await collectorManager.stop_monitor(roomId)
    if success:
        return _buildResponse(0, "停止采集")
    else:
        return _buildResponse(-1, "停止采集失败")


@router.get("/{roomId}/info")
async def getRoomInfoEndpoint(roomId: int):
    room = getRoomByRoomId(roomId)
    if not room:
        return _buildResponse(-1, "房间不存在")

    count = getRoomDanmuCount(roomId)
    return _buildResponse(0, "", {
        "room_id": room.room_id,
        "room_name": room.room_name,
        "anchor_name": room.anchor_name,
        "status": room.status,
        "error_msg": room.error_msg,
        "danmu_count": count,
        "created_at": room.created_at,
        "updated_at": room.updated_at,
    })