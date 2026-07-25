"""WebSocket 推送服务模块

提供房间订阅、弹幕广播、实时分析数据推送等能力。

对外暴露:
- wsManager: 全局连接管理器单例
- router: FastAPI WebSocket 路由
"""

from .manager import wsManager
from .route import router

__all__ = ["wsManager", "router"]
