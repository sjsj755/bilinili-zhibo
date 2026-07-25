"""BiliLini 弹幕采集 CLI 启动脚本

用法:
    python run.py <直播间ID>

示例:
    python run.py 12345
"""

import asyncio
import logging
import os
import signal
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from collector.bili_client import BiliClient
from db.database import DanmuWriter, closeDb, initDb
from db.queries.room import insertRoom, updateRoomStatus, updateRoomInfo, getRoomByRoomId
from services.bili_api import resolveRoomId, getRoomInfo
from shared.types import Room
from utils.config import loadEnv, parseUidFromSessdata

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
# 开启采集模块 DEBUG 以便诊断消息类型
logging.getLogger("collector").setLevel(logging.DEBUG)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("bilinili")


def parseArgs() -> int:
    """解析命令行参数，返回直播间 ID"""
    if len(sys.argv) < 2:
        print("用法: python run.py <直播间ID>")
        print("示例: python run.py 12345")
        sys.exit(1)

    try:
        roomId = int(sys.argv[1])
    except ValueError:
        print(f"错误: 直播间 ID 必须为整数，收到: {sys.argv[1]}")
        sys.exit(1)

    return roomId


async def run(roomId: int, config: dict[str, str]) -> None:
    """主采集流程"""
    logger.info("BiliLini 弹幕采集工具启动")

    sessdata = config.get("SESSDATA", "")
    uid = config.get("BILI_UID", "")
    if uid:
        uid = int(uid)
    elif sessdata:
        uid = parseUidFromSessdata(sessdata)

    if sessdata:
        logger.info("已加载登录 Cookie, UID=%d", uid)

    # 初始化数据库
    dbPath = "data/bilinili.db"
    initDb(dbPath)

    # 获取房间真实信息
    realRoomId = roomId
    roomName = ""
    anchorName = ""
    try:
        realRoomId = await resolveRoomId(roomId)
        roomInfo = await getRoomInfo(realRoomId)
        roomName = roomInfo.get("title", "")
        anchorName = roomInfo.get("anchor_name", "")
        logger.info("获取房间信息成功: %s - %s", roomName, anchorName)
    except Exception as e:
        logger.warning("获取房间信息失败，使用默认值: %s", e)

    # 确保房间记录存在
    existingRoom = getRoomByRoomId(realRoomId)
    if not existingRoom:
        room = Room(
            room_id=realRoomId,
            room_name=roomName,
            anchor_name=anchorName,
            status="monitoring",
        )
        insertRoom(room)
        logger.info("已创建房间记录: %d", realRoomId)
    else:
        updateRoomStatus(realRoomId, "monitoring")
        if roomName or anchorName:
            updateRoomInfo(realRoomId, roomName, anchorName)
        logger.info("房间记录已存在，状态更新为 monitoring: %d", realRoomId)

    # 创建写入器
    writer = DanmuWriter(batchSize=100, flushInterval=1.0)

    # 弹幕回调：存入数据库 + 控制台打印
    async def onDanmu(record):
        await writer.write(record)
        medalStr = f"[{record.medal_name}{record.medal_level}]" if record.medal_name else ""
        print(f"\r{medalStr} {record.username}: {record.content}")

    # 创建客户端
    client = BiliClient(room_id=roomId, onDanmu=onDanmu, sessdata=sessdata, uid=uid)

    # 注册退出信号
    loop = asyncio.get_running_loop()
    shutdownEvent = asyncio.Event()

    def signalHandler():
        logger.info("收到退出信号，正在停止采集...")
        shutdownEvent.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signalHandler)
        except NotImplementedError:
            # Windows 不支持 add_signal_handler 对 SIGTERM
            pass

    # 启动采集
    logger.info("开始采集直播间 %d 的弹幕", roomId)
    print(f"\n{'=' * 50}")
    print(f"  直播间: {roomId}")
    print(f"  数据库: {dbPath}")
    print(f"  按 Ctrl+C 停止采集")
    print(f"{'=' * 50}\n")

    try:
        # 采集主循环（含自动重连）
        await client.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error("采集异常: %s", e)
    finally:
        logger.info("正在停止采集...")
        await client.disconnect()
        await writer.close()
        updateRoomStatus(realRoomId, "idle")
        closeDb()
        logger.info("BiliLini 已退出")


if __name__ == "__main__":
    roomId = parseArgs()
    config = loadEnv()
    try:
        asyncio.run(run(roomId, config))
    except KeyboardInterrupt:
        print("\n已退出")
