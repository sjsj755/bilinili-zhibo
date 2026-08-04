"""深度分析任务 API 路由

提供 4 个端点用于管理深度分析任务：
- POST   /api/analysis/{roomId}/deep              创建任务
- GET    /api/analysis/{roomId}/deep/list         任务列表
- GET    /api/analysis/{roomId}/deep/{taskId}     任务详情
- DELETE /api/analysis/{roomId}/deep/{taskId}     删除任务

注意：路由顺序上 /deep/list 必须声明在 /deep/{taskId} 之前，
避免 FastAPI 把 "list" 当作 taskId 解析。
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from db.queries.room import getRoomByRoomId
from services.analysis_service import analysisService

logger = logging.getLogger("server.routes.analysis")

router = APIRouter()


class DeepAnalysisRequest(BaseModel):
    """创建深度分析任务请求体

    Attributes:
        startTime: 分析起始时间戳（秒）
        endTime: 分析结束时间戳（秒），必须大于 startTime
    """

    startTime: int
    endTime: int

    @field_validator("endTime")
    @classmethod
    def validateTimeRange(cls, endTime: int, info) -> int:
        """校验结束时间晚于开始时间"""
        startTime = info.data.get("startTime")
        if startTime is not None and endTime <= startTime:
            raise ValueError("endTime 必须大于 startTime")
        return endTime


def _buildResponse(code: int, msg: str = "", data=None):
    """构造统一响应格式 {"code":0,"msg":"","data":{}}"""
    return JSONResponse(content={"code": code, "msg": msg, "data": data})


def _taskToDict(task) -> dict:
    """将 AnalysisTask 转换为响应字典

    仅在任务状态为 completed 时返回 result 字段，避免暴露半成品数据。
    """
    return {
        "id": task.id,
        "room_id": task.room_id,
        "type": task.type,
        "status": task.status,
        "params": task.params,
        "result": task.result_json if task.status == "completed" else None,
        "error_msg": task.error_msg,
        "start_time": task.start_time,
        "end_time": task.end_time,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
    }


@router.post("/{roomId}/deep")
async def createDeepAnalysis(roomId: int, body: DeepAnalysisRequest):
    """创建深度分析任务

    Args:
        roomId: 直播间 ID
        body: 请求体 {startTime: int, endTime: int}

    Returns:
        新建的任务对象（status=pending 或 running）
    """
    if not getRoomByRoomId(roomId):
        return _buildResponse(-2, "直播间不存在")

    try:
        task = analysisService.createTask(roomId, body.startTime, body.endTime)
        return _buildResponse(0, "任务已创建", _taskToDict(task))
    except Exception as e:
        logger.error("创建深度分析任务失败: %s", e, exc_info=True)
        return _buildResponse(-3, f"创建失败: {e}")


@router.get("/{roomId}/deep/list")
async def listDeepAnalyses(roomId: int):
    """获取指定房间的深度分析任务列表

    Args:
        roomId: 直播间 ID

    Returns:
        任务列表，按创建时间倒序
    """
    if not getRoomByRoomId(roomId):
        return _buildResponse(-2, "直播间不存在")

    tasks = analysisService.listTasksByRoom(roomId)
    return _buildResponse(0, "", [_taskToDict(t) for t in tasks])


@router.get("/{roomId}/deep/{taskId}")
async def getDeepAnalysis(roomId: int, taskId: int):
    """获取指定深度分析任务详情

    Args:
        roomId: 直播间 ID
        taskId: 任务 ID

    Returns:
        任务详情对象
    """
    task = analysisService.getTask(taskId)
    if task is None:
        return _buildResponse(-2, "任务不存在")

    if task.room_id != roomId:
        return _buildResponse(-2, "任务不属于该直播间")

    return _buildResponse(0, "", _taskToDict(task))


@router.delete("/{roomId}/deep/{taskId}")
async def deleteDeepAnalysis(roomId: int, taskId: int):
    """删除指定深度分析任务

    Args:
        roomId: 直播间 ID
        taskId: 任务 ID

    Returns:
        删除结果
    """
    task = analysisService.getTask(taskId)
    if task is None:
        return _buildResponse(-2, "任务不存在")

    if task.room_id != roomId:
        return _buildResponse(-2, "任务不属于该直播间")

    if task.status == "running":
        return _buildResponse(-4, "无法删除正在执行的任务")

    success = analysisService.deleteTask(taskId)
    if success:
        return _buildResponse(0, "删除成功")
    return _buildResponse(-3, "删除失败")
