"""项目共享数据类型"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DanmuRecord:
    """解析后的弹幕记录"""

    room_id: int
    session_id: int = 0
    uid: int = 0
    username: str = ""
    content: str = ""
    timestamp: int = 0  # 秒级时间戳
    medal_level: int = 0
    medal_name: str = ""
    user_level: int = 0
    is_gift: bool = False
    raw_json: dict[str, Any] = field(default_factory=dict)


@dataclass
class Room:
    """直播间信息"""

    room_id: int
    room_name: str = ""
    anchor_name: str = ""
    status: str = "idle"
    error_msg: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class AnalysisTask:
    """深度分析任务

    Attributes:
        id: 任务 ID（数据库自增主键）
        room_id: 关联的直播间 ID
        type: 任务类型，'realtime' 或 'deep'（P3-1 仅使用 'deep'）
        status: 任务状态，'pending' | 'running' | 'completed' | 'failed'
        params: 任务参数字典，固定包含 startTime / endTime
        result_json: 分析结果字典（仅 status=completed 时有效）
        start_time: 分析起始时间戳（秒）
        end_time: 分析结束时间戳（秒）
        error_msg: 失败原因（仅 status=failed 时有效）
        created_at: 任务创建时间（本地时间字符串）
        completed_at: 任务完成时间（本地时间字符串）
    """

    id: int = 0
    room_id: int = 0
    type: str = "deep"
    status: str = "pending"
    params: dict[str, Any] = field(default_factory=dict)
    result_json: dict[str, Any] = field(default_factory=dict)
    start_time: int = 0
    end_time: int = 0
    error_msg: str = ""
    created_at: str = ""
    completed_at: str = ""
