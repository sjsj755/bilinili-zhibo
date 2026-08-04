"""analysis_tasks 表查询函数

纯数据访问层：仅提供 SQL 操作，不包含业务逻辑，不依赖 server 或 services 模块。
"""

import json
from typing import Optional, List

from shared.types import AnalysisTask
from ..database import getConnection
from ..schema import (
    INSERT_ANALYSIS_TASK,
    SELECT_ANALYSIS_TASK_BY_ID,
    SELECT_ANALYSIS_TASKS_BY_ROOM,
    UPDATE_ANALYSIS_TASK_STATUS_RUNNING,
    UPDATE_ANALYSIS_TASK_COMPLETED,
    UPDATE_ANALYSIS_TASK_FAILED,
    DELETE_ANALYSIS_TASK,
)


def createAnalysisTask(roomId: int, startTime: int, endTime: int) -> int:
    """创建深度分析任务（初始状态为 pending）

    Args:
        roomId: 直播间 ID
        startTime: 分析起始时间戳（秒）
        endTime: 分析结束时间戳（秒）

    Returns:
        int: 新建任务的 ID
    """
    conn = getConnection()
    params = json.dumps({"startTime": startTime, "endTime": endTime}, ensure_ascii=False)
    cursor = conn.execute(INSERT_ANALYSIS_TASK, (roomId, params, startTime, endTime))
    conn.commit()
    return cursor.lastrowid


def getAnalysisTaskById(taskId: int) -> Optional[AnalysisTask]:
    """根据任务 ID 获取任务对象

    Args:
        taskId: 任务 ID

    Returns:
        Optional[AnalysisTask]: 任务对象，不存在返回 None
    """
    conn = getConnection()
    cursor = conn.execute(SELECT_ANALYSIS_TASK_BY_ID, (taskId,))
    row = cursor.fetchone()
    return _rowToTask(row) if row else None


def getAnalysisTasksByRoom(roomId: int) -> List[AnalysisTask]:
    """获取指定房间的所有深度分析任务，按创建时间倒序

    Args:
        roomId: 直播间 ID

    Returns:
        List[AnalysisTask]: 任务列表
    """
    conn = getConnection()
    cursor = conn.execute(SELECT_ANALYSIS_TASKS_BY_ROOM, (roomId,))
    return [_rowToTask(row) for row in cursor.fetchall()]


def markTaskRunning(taskId: int) -> bool:
    """将任务状态更新为 running

    Args:
        taskId: 任务 ID

    Returns:
        bool: 是否成功更新
    """
    conn = getConnection()
    cursor = conn.execute(UPDATE_ANALYSIS_TASK_STATUS_RUNNING, (taskId,))
    conn.commit()
    return cursor.rowcount > 0


def markTaskCompleted(taskId: int, result: dict) -> bool:
    """将任务标记为已完成并写入分析结果

    Args:
        taskId: 任务 ID
        result: 分析结果字典，将序列化为 JSON 存储

    Returns:
        bool: 是否成功更新
    """
    conn = getConnection()
    resultJson = json.dumps(result, ensure_ascii=False)
    cursor = conn.execute(UPDATE_ANALYSIS_TASK_COMPLETED, (resultJson, taskId))
    conn.commit()
    return cursor.rowcount > 0


def markTaskFailed(taskId: int, errorMsg: str) -> bool:
    """将任务标记为失败并写入错误信息

    Args:
        taskId: 任务 ID
        errorMsg: 失败原因

    Returns:
        bool: 是否成功更新
    """
    conn = getConnection()
    cursor = conn.execute(UPDATE_ANALYSIS_TASK_FAILED, (errorMsg, taskId))
    conn.commit()
    return cursor.rowcount > 0


def deleteAnalysisTask(taskId: int) -> bool:
    """删除指定任务

    Args:
        taskId: 任务 ID

    Returns:
        bool: 是否成功删除
    """
    conn = getConnection()
    cursor = conn.execute(DELETE_ANALYSIS_TASK, (taskId,))
    conn.commit()
    return cursor.rowcount > 0


def _rowToTask(row) -> AnalysisTask:
    """将数据库行转换为 AnalysisTask 对象

    行字段顺序与 CREATE_ANALYSIS_TASKS_TABLE 一致：
    id, room_id, type, status, params, result_json, start_time, end_time,
    error_msg, created_at, completed_at
    """
    try:
        params = json.loads(row[4]) if row[4] else {}
    except (json.JSONDecodeError, TypeError):
        params = {}
    try:
        resultJson = json.loads(row[5]) if row[5] else {}
    except (json.JSONDecodeError, TypeError):
        resultJson = {}
    return AnalysisTask(
        id=row[0],
        room_id=row[1],
        type=row[2],
        status=row[3],
        params=params,
        result_json=resultJson,
        start_time=row[6] or 0,
        end_time=row[7] or 0,
        error_msg=row[8] or "",
        created_at=row[9] or "",
        completed_at=row[10] or "",
    )
