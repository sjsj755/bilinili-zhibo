"""B 站弹幕二进制协议解析器

负责解析 B 站弹幕 WebSocket 的二进制数据包。
协议头部 16 字节（大端序），body 根据 proto_ver 决定编码方式：
- proto_ver=0: JSON 文本
- proto_ver=2: zlib 压缩
- proto_ver=3: brotli 压缩
"""

import json
import struct
import zlib
from typing import Any

from .danmu_types import HEADER_LENGTH, OpCode, PacketHeader, ProtoVer


class ParseError(Exception):
    """协议解析错误"""

    def __init__(self, message: str, raw_data: bytes | None = None):
        super().__init__(message)
        self.raw_data = raw_data


def unpack_header(data: bytes) -> PacketHeader:
    """解析二进制协议头部（16 字节，大端序）

    Args:
        data: 至少 16 字节的原始二进制数据

    Returns:
        PacketHeader: 解析后的包头对象

    Raises:
        ParseError: 数据不足 16 字节或头部字段非法
    """
    if len(data) < HEADER_LENGTH:
        raise ParseError(
            f"数据包长度不足，需要至少 {HEADER_LENGTH} 字节，实际收到 {len(data)} 字节",
            raw_data=data,
        )

    total_len, header_len, proto_ver, op, seq = struct.unpack(">IHHII", data[:HEADER_LENGTH])

    try:
        proto_ver = ProtoVer(proto_ver)
    except ValueError:
        raise ParseError(f"不支持的协议版本: {proto_ver}", raw_data=data)

    try:
        op = OpCode(op)
    except ValueError:
        raise ParseError(f"未知的操作码: {op}", raw_data=data)

    return PacketHeader(
        total_len=total_len,
        header_len=header_len,
        proto_ver=proto_ver,
        op=op,
        seq=seq,
    )


def decode_body(body: bytes, proto_ver: ProtoVer) -> bytes:
    """根据协议版本解码 body

    Args:
        body: 原始 body 字节数据
        proto_ver: 协议版本枚举

    Returns:
        bytes: 解码后的 UTF-8 文本字节

    Raises:
        ParseError: 解压失败
    """
    if proto_ver == ProtoVer.JSON or proto_ver == ProtoVer.HEARTBEAT:
        return body

    if proto_ver == ProtoVer.ZLIB:
        try:
            return zlib.decompress(body)
        except zlib.error as e:
            raise ParseError(f"zlib 解压失败: {e}", raw_data=body)

    if proto_ver == ProtoVer.BROTLI:
        try:
            import brotli
            return brotli.decompress(body)
        except ImportError:
            raise ParseError(
                "检测到 brotli 压缩数据，但 brotli 库未安装。请执行: pip install brotli"
            )
        except Exception as e:
            raise ParseError(f"brotli 解压失败: {e}", raw_data=body)

    raise ParseError(f"不支持的协议版本: {proto_ver}")


def split_messages(body: bytes) -> list[dict[str, Any]]:
    """将 body 文本按换行分割为多条 JSON 消息

    Args:
        body: 解码后的 UTF-8 文本字节（可能包含多条消息，以 \\n 分隔）

    Returns:
        list[dict]: 解析后的 JSON 消息列表
    """
    text = body.decode("utf-8", errors="replace")
    messages: list[dict[str, Any]] = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            messages.append(msg)
        except json.JSONDecodeError:
            # 跳过无法解析的行
            continue

    return messages


def parse(packet: bytes) -> list[dict[str, Any]]:
    """解析一个二进制数据包（含 brotli 递归解包子包）

    Args:
        packet: 完整的二进制数据包（包含头部和 body）

    Returns:
        list[dict]: 解析后的消息列表

    Raises:
        ParseError: 数据包解析失败
    """
    if not packet:
        raise ParseError("收到空数据包")

    header = unpack_header(packet)

    body_start = header.header_len
    body_end = min(header.total_len, len(packet))
    body = packet[body_start:body_end]

    decoded_body = decode_body(body, header.proto_ver)

    # brotli 解压后是多个二进制子包拼接，递归解析
    if header.proto_ver == ProtoVer.BROTLI:
        return _parseSubPackets(decoded_body)

    return split_messages(decoded_body)


def _parseSubPackets(data: bytes) -> list[dict[str, Any]]:
    """递归解析 brotli 解压后的子包拼接数据"""
    messages: list[dict[str, Any]] = []
    offset = 0

    while offset + HEADER_LENGTH <= len(data):
        sub_header = unpack_header(data[offset:offset + HEADER_LENGTH])
        sub_total = sub_header.total_len

        if sub_total < HEADER_LENGTH or offset + sub_total > len(data):
            break

        sub_body_start = offset + sub_header.header_len
        sub_body_end = offset + sub_total
        sub_body = data[sub_body_start:sub_body_end]

        decoded = decode_body(sub_body, sub_header.proto_ver)

        # 子包可能又含 brotli，递归
        if sub_header.proto_ver == ProtoVer.BROTLI:
            messages.extend(_parseSubPackets(decoded))
        else:
            messages.extend(split_messages(decoded))

        offset += sub_total

    return messages


def pack_auth(room_id: int, token: str, uid: int = 0, buvid: str = "") -> bytes:
    """构造认证包（用于向 B 站弹幕服务器发送认证请求）

    Args:
        room_id: B 站直播间 ID
        token: 从 getDanmuInfo API 获取的认证 token
        uid: 用户 UID，默认为 0（游客）
        buvid: 设备标识，必填

    Returns:
        bytes: 完整的认证二进制数据包
    """
    auth_data = json.dumps(
        {
            "uid": uid,
            "roomid": room_id,
            "protover": ProtoVer.BROTLI.value,
            "platform": "web",
            "clientver": "2.7.5",
            "type": 2,
            "buvid": buvid,
            "key": token,
        }
    ).encode("utf-8")

    total_len = HEADER_LENGTH + len(auth_data)
    header = struct.pack(
        ">IHHII",
        total_len,
        HEADER_LENGTH,
        ProtoVer.HEARTBEAT.value,  # auth 包头用 proto_ver=1
        OpCode.AUTH.value,
        1,
    )

    return header + auth_data


def pack_heartbeat() -> bytes:
    """构造心跳包

    Returns:
        bytes: 心跳二进制数据包
    """
    from .danmu_types import HEARTBEAT_PACKET

    return HEARTBEAT_PACKET
