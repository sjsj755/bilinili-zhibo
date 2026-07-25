"""B 站弹幕采集模块的协议类型定义"""

from dataclasses import dataclass
from enum import IntEnum


class ProtoVer(IntEnum):
    """B 站弹幕协议版本"""

    JSON = 0  # body 为 JSON 文本
    HEARTBEAT = 1  # 心跳/认证包
    ZLIB = 2  # body 为 zlib 压缩
    BROTLI = 3  # body 为 brotli 压缩


class OpCode(IntEnum):
    """B 站弹幕 WebSocket 操作码"""

    HEARTBEAT = 2  # 客户端发送心跳
    HEARTBEAT_REPLY = 3  # 服务端心跳回复（含人气值）
    DANMU_MSG = 5  # 弹幕消息
    AUTH = 7  # 客户端发送认证
    AUTH_REPLY = 8  # 服务端认证回复


@dataclass
class PacketHeader:
    """B 站弹幕协议数据包头部（16 字节，大端序）

    | 偏移 | 长度 | 字段       | 说明                              |
    |------|------|-----------|-----------------------------------|
    | 0    | 4    | total_len | 包总长度                          |
    | 4    | 2    | header_len| 头部长度（固定 16）                |
    | 6    | 2    | proto_ver | 协议版本（0=JSON, 2=zlib, 3=brotli）|
    | 8    | 4    | op        | 操作码                            |
    | 12   | 4    | seq       | 序列号                            |
    """

    total_len: int
    header_len: int
    proto_ver: ProtoVer
    op: OpCode
    seq: int


# 协议常量
HEADER_LENGTH = 16  # 头部固定 16 字节
HEARTBEAT_PACKET = b"\x00\x00\x00\x10\x00\x10\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01"
# 心跳包：total_len=16, header_len=16, proto_ver=0, op=2, seq=1
