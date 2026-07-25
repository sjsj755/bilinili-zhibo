"""BiliLini API 服务启动脚本

用法:
    python start_server.py
    python start_server.py --port 3001
    python start_server.py --reload

示例:
    python start_server.py              # 默认端口 3001，生产模式
    python start_server.py --reload     # 开发模式，热重载
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import uvicorn
from utils.config import loadEnv


def parseArgs():
    parser = argparse.ArgumentParser(description="启动 BiliLini API 服务")
    parser.add_argument("--port", type=int, default=3001, help="服务端口，默认 3001")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址")
    parser.add_argument("--reload", action="store_true", help="开发模式，启用热重载")
    return parser.parse_args()


def main():
    args = parseArgs()
    config = loadEnv()

    port = int(config.get("SERVER_PORT", args.port))
    host = config.get("SERVER_HOST", args.host)

    print(f"\n{'=' * 50}")
    print(f"  BiliLini API 服务启动")
    print(f"  端口: {port}")
    print(f"  模式: {'开发模式（热重载）' if args.reload else '生产模式'}")
    print(f"  按 Ctrl+C 停止服务")
    print(f"{'=' * 50}\n")

    uvicorn.run(
        "backend.server.main:app",
        host=host,
        port=port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()