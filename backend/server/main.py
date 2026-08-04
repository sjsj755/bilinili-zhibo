from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server.middleware.error_handler import globalExceptionHandler
from server.ws import wsManager
from collector import collectorManager
from db.database import initDb, closeDb, DanmuWriter
from db.queries.room import updateRoomStatus, getAllRooms
from db.queries.session import createSession, endSession, endAllActiveSessions
from services.segment_engine import segmentEngine
from services.sentiment_engine import sentimentEngine
from services.frequency_engine import frequencyEngine
from services.keyword_engine import keywordEngine
from services.realtime_engine import realtimeAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("collector").setLevel(logging.DEBUG)
logging.getLogger("server.ws.route").setLevel(logging.DEBUG)
logging.getLogger("server.ws.manager").setLevel(logging.DEBUG)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    dbPath = os.path.join(os.path.dirname(__file__), "../../data/bilinili.db")
    initDb(dbPath)
    logger.info("数据库初始化完成")

    danmuWriter = DanmuWriter()

    async def onDanmu(record):
        await asyncio.gather(
            danmuWriter.write(record),
            wsManager.broadcastDanmu(record.room_id, record),
            return_exceptions=True,
        )
        segmentEngine.add_danmu(record)

    async def onStatusChange(roomId, status, errorMsg):
        updateRoomStatus(roomId, status, errorMsg)
        if status == "error":
            await wsManager.broadcastError(roomId, errorMsg)

    collectorManager.setCallbacks(
            onDanmu=onDanmu,
            onStatusChange=onStatusChange,
            onCreateSession=createSession,
            onEndSession=endSession,
        )

    endedCount = endAllActiveSessions()
    if endedCount > 0:
        logger.info("已结束 %d 个未清理的活跃会话", endedCount)

    monitoringRooms = [r for r in getAllRooms() if r.status == "monitoring"]
    for room in monitoringRooms:
        logger.info("恢复房间 %d 的采集状态", room.room_id)
        asyncio.create_task(collectorManager.start_monitor(room.room_id))

    logger.info("采集管理器初始化完成")

    await wsManager.startHeartbeat()
    logger.info("WebSocket 心跳服务已启动")

    loop = asyncio.get_event_loop()

    def onAnalysisResult(stats_list):
        for stats in stats_list:
            room_id = stats.get("room_id")
            if room_id:
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        wsManager.broadcastStats(room_id, [stats]),
                        loop
                    )
                    future.result(timeout=2)
                except Exception as e:
                    logger.error(f"推送分析数据失败: {e}")

    realtimeAnalyzer.register_segment_engine(segmentEngine)
    realtimeAnalyzer.register_sentiment_engine(sentimentEngine)
    realtimeAnalyzer.register_frequency_engine(frequencyEngine)
    realtimeAnalyzer.register_keyword_engine(keywordEngine)
    realtimeAnalyzer.add_callback(onAnalysisResult)
    realtimeAnalyzer.start_all_engines()
    logger.info("实时分析引擎已启动")

    yield

    await collectorManager.stop_all()
    logger.info("所有采集任务已停止")

    await danmuWriter.close()
    logger.info("弹幕写入器已关闭")

    await wsManager.stopHeartbeat()
    logger.info("WebSocket 心跳服务已停止")

    realtimeAnalyzer.stop_all_engines()
    logger.info("实时分析引擎已停止")

    closeDb()
    logger.info("数据库连接已关闭")


app = FastAPI(
    title="BiliLini API",
    version="1.0",
    description="B站直播弹幕分析工具后端 API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, globalExceptionHandler)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "1.0"}


from server.routes.room import router as roomRouter
from server.routes.danmu import router as danmuRouter
from server.routes.session import router as sessionRouter
from server.routes.analysis import router as analysisRouter
from server.ws import router as wsRouter

app.include_router(roomRouter, prefix="/api/rooms", tags=["rooms"])
app.include_router(danmuRouter, prefix="/api/danmu", tags=["danmu"])
app.include_router(sessionRouter, prefix="/api/sessions", tags=["sessions"])
app.include_router(analysisRouter, prefix="/api/analysis", tags=["analysis"])
app.include_router(wsRouter, prefix="/ws", tags=["websocket"])