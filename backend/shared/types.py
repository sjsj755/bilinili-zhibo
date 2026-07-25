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
