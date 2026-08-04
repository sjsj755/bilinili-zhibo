"""深度分析任务服务层（业务编排 + 执行器注册）

职责：
- 任务 CRUD 编排
- 维护执行器注册表（register_executor）
- 异步触发任务执行（不阻塞 HTTP 请求）

解耦点：本类不依赖任何具体算法引擎，executor 由 P3-6 通过
register_executor() 注入。未注册时任务保持 pending 状态。
"""

import asyncio
import logging
from typing import Protocol, Optional, runtime_checkable

from db.queries.analysis import (
    createAnalysisTask,
    getAnalysisTaskById,
    getAnalysisTasksByRoom,
    markTaskRunning,
    markTaskCompleted,
    markTaskFailed,
    deleteAnalysisTask,
)
from shared.types import AnalysisTask

logger = logging.getLogger("analysis_service")


@runtime_checkable
class AnalysisExecutor(Protocol):
    """深度分析执行器协议（P3-6 实现 DeepAnalyzer 后注册）

    实现示例:
        class DeepAnalyzer:
            async def run(self, taskId: int, roomId: int, params: dict) -> dict:
                # 执行 TF-IDF、情感时序、热点检测、用户画像
                return {...}
    """

    async def run(self, taskId: int, roomId: int, params: dict) -> dict:
        """执行深度分析

        Args:
            taskId: 任务 ID（仅作上下文标识，不强制使用）
            roomId: 直播间 ID
            params: 任务参数字典，至少包含 startTime / endTime

        Returns:
            dict: 分析结果，将序列化为 result_json 存储

        Raises:
            Exception: 执行失败时抛出，service 会回写 failed 状态
        """
        ...


class AnalysisService:
    """深度分析任务服务（单例）

    使用示例:
        # P3-6 在 main.py lifespan 中注册执行器
        analysisService.register_executor(deepAnalyzer)

        # 路由层调用
        task = analysisService.createTask(roomId, startTime, endTime)
    """

    def __init__(self):
        self._executor: Optional[AnalysisExecutor] = None

    def register_executor(self, executor: AnalysisExecutor) -> None:
        """注册深度分析执行器（由 P3-6 调用）

        Args:
            executor: 实现 AnalysisExecutor 协议的对象
        """
        self._executor = executor
        logger.info("深度分析执行器已注册: %s", type(executor).__name__)

    def unregister_executor(self) -> None:
        """取消注册执行器"""
        self._executor = None
        logger.info("深度分析执行器已取消注册")

    def is_executor_registered(self) -> bool:
        """检查执行器是否已注册（用于调试）"""
        return self._executor is not None

    def createTask(self, roomId: int, startTime: int, endTime: int) -> AnalysisTask:
        """创建深度分析任务

        流程：
        1. 持久化任务（status=pending）到数据库
        2. 若已注册执行器，异步派发执行（不阻塞当前请求）
        3. 若未注册执行器，任务保持 pending 状态

        Args:
            roomId: 直播间 ID
            startTime: 分析起始时间戳（秒）
            endTime: 分析结束时间戳（秒）

        Returns:
            AnalysisTask: 新建的任务对象（status=pending）
        """
        taskId = createAnalysisTask(roomId, startTime, endTime)
        task = getAnalysisTaskById(taskId)

        # 异步触发执行器（如已注册），不阻塞当前请求
        if self._executor is not None:
            asyncio.create_task(self._runTask(taskId, roomId, task.params))
            logger.info("任务 %d 已派发至执行器", taskId)
        else:
            logger.warning("任务 %d 创建成功但未注册执行器（保持 pending 状态）", taskId)

        return task

    async def _runTask(self, taskId: int, roomId: int, params: dict) -> None:
        """异步执行任务：pending → running → completed/failed

        Args:
            taskId: 任务 ID
            roomId: 直播间 ID
            params: 任务参数字典
        """
        if self._executor is None:
            return

        markTaskRunning(taskId)
        logger.info("任务 %d 开始执行", taskId)

        try:
            result = await self._executor.run(taskId, roomId, params)
            markTaskCompleted(taskId, result)
            logger.info("任务 %d 执行完成", taskId)
        except Exception as e:
            markTaskFailed(taskId, str(e))
            logger.error("任务 %d 执行失败: %s", taskId, e, exc_info=True)

    def getTask(self, taskId: int) -> Optional[AnalysisTask]:
        """获取任务详情

        Args:
            taskId: 任务 ID

        Returns:
            Optional[AnalysisTask]: 任务对象，不存在返回 None
        """
        return getAnalysisTaskById(taskId)

    def listTasksByRoom(self, roomId: int) -> list[AnalysisTask]:
        """获取指定房间的深度分析任务列表

        Args:
            roomId: 直播间 ID

        Returns:
            list[AnalysisTask]: 任务列表，按创建时间倒序
        """
        return getAnalysisTasksByRoom(roomId)

    def deleteTask(self, taskId: int) -> bool:
        """删除任务

        注意：调用方需自行校验任务状态，running 状态不应允许删除。

        Args:
            taskId: 任务 ID

        Returns:
            bool: 是否成功删除
        """
        return deleteAnalysisTask(taskId)


# 全局单例（与 realtimeAnalyzer 一致的模式）
analysisService = AnalysisService()
