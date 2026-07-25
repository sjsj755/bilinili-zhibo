"""项目配置读取

从项目根目录 .env 文件加载配置（key=value 格式，无需第三方库）。
"""

import os
from pathlib import Path


def loadEnv() -> dict[str, str]:
    """加载 .env 配置文件

    Returns:
        dict[str, str]: 键值对字典
    """
    envPath = Path(__file__).parent.parent.parent / ".env"
    config: dict[str, str] = {}

    if not envPath.exists():
        return config

    with open(envPath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and value:
                config[key] = value

    return config


def parseUidFromSessdata(sessdata: str) -> int:
    """从 SESSDATA 中解析 UID

    SESSDATA 格式: 用户ID,过期时间戳,签名
    """
    try:
        return int(sessdata.split(",")[0])
    except (ValueError, IndexError):
        return 0
