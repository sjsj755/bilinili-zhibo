from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from db.queries.danmu import getDanmuByRoomId, getDanmuCount, getDanmuStats

router = APIRouter()


def _buildResponse(code: int, msg: str = "", data=None):
    return JSONResponse(content={"code": code, "msg": msg, "data": data})


@router.get("/{roomId}")
async def getDanmu(roomId: int, page: int = 1, pageSize: int = 50):
    if page < 1:
        page = 1
    if pageSize < 1:
        pageSize = 50
    if pageSize > 200:
        pageSize = 200

    offset = (page - 1) * pageSize
    danmuList = getDanmuByRoomId(roomId, offset=offset, limit=pageSize)
    total = getDanmuCount(roomId)

    return _buildResponse(0, "", {
        "list": danmuList,
        "total": total,
        "page": page,
        "pageSize": pageSize,
    })


@router.get("/{roomId}/stats")
async def getDanmuStatsEndpoint(roomId: int):
    stats = getDanmuStats(roomId)
    if stats is None:
        return _buildResponse(0, "", {
            "total_count": 0,
            "unique_users": 0,
            "peak_hour": "",
            "peak_count": 0,
        })
    return _buildResponse(0, "", {
        "total_count": stats["total_count"],
        "unique_users": stats["unique_users"],
        "peak_hour": stats["peak_hour"],
        "peak_count": stats["peak_count"],
    })