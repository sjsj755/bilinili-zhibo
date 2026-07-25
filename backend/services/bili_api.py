"""B站 API 调用封装"""

import logging

import httpx

from utils.wbi import getMixinKey, signParams, generateBuvid3

logger = logging.getLogger(__name__)

ROOM_INIT_API = "https://api.live.bilibili.com/room/v1/Room/room_init"
ROOM_INFO_API = "https://api.live.bilibili.com/room/v1/Room/get_info"
ANCHOR_INFO_API = "https://api.live.bilibili.com/live_user/v1/Master/info"


async def resolveRoomId(shortId: int) -> int:
    """将短号解析为真实房间号"""
    params = {"id": shortId}

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Referer": "https://live.bilibili.com/",
    }

    async with httpx.AsyncClient(headers=headers) as client:
        resp = await client.get(ROOM_INIT_API, params=params)
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"房间号解析失败: {data.get('message', 'unknown')}")

    roomId = data.get("data", {}).get("room_id")
    if not roomId:
        raise RuntimeError("未找到房间号")

    return roomId


async def getAnchorName(uid: int) -> str:
    """通过直播用户信息接口获取主播名称（无需 WBI 签名）"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Referer": "https://live.bilibili.com/",
    }

    async with httpx.AsyncClient(headers=headers) as client:
        resp = await client.get(ANCHOR_INFO_API, params={"uid": uid})
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"获取主播信息失败: {data.get('message', 'unknown')}")

    return data.get("data", {}).get("info", {}).get("uname", "")


async def getRoomInfo(roomId: int) -> dict:
    """获取直播间详细信息（包含主播名称）"""
    mixinKey = await getMixinKey()
    params = signParams({"room_id": roomId}, mixinKey)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Referer": f"https://live.bilibili.com/{roomId}",
        "Cookie": f"buvid3={generateBuvid3()}",
    }

    async with httpx.AsyncClient(headers=headers) as client:
        resp = await client.get(ROOM_INFO_API, params=params)
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"获取房间信息失败: {data.get('message', 'unknown')}")

    roomData = data.get("data", {})
    uid = roomData.get("uid")

    if uid:
        try:
            roomData["anchor_name"] = await getAnchorName(uid)
        except Exception as e:
            logger.warning(f"获取主播信息失败: {e}")

    return roomData