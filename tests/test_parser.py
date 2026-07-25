"""parser.py 单元测试"""

import json
import struct
import zlib
import sys
import os
import pytest

# 将 backend 目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from collector.danmu_types import HEADER_LENGTH, OpCode, PacketHeader, ProtoVer
from collector.parser import (
    ParseError,
    _parseSubPackets,
    decode_body,
    pack_auth,
    pack_heartbeat,
    parse,
    split_messages,
    unpack_header,
)


# ==================== unpack_header ====================


class TestUnpackHeader:
    """测试二进制协议头部解析"""

    def test_valid_header(self):
        """正常解析有效的头部"""
        header = struct.pack(">IHHII", 100, 16, ProtoVer.JSON, OpCode.DANMU_MSG, 1)
        result = unpack_header(header)

        assert result.total_len == 100
        assert result.header_len == 16
        assert result.proto_ver == ProtoVer.JSON
        assert result.op == OpCode.DANMU_MSG
        assert result.seq == 1

    def test_insufficient_data(self):
        """数据不足 16 字节时抛出异常"""
        with pytest.raises(ParseError, match="数据包长度不足"):
            unpack_header(b"\x00" * 10)

    def test_unknown_proto_ver(self):
        """未知协议版本抛出异常"""
        header = struct.pack(">IHHII", 100, 16, 99, OpCode.DANMU_MSG, 1)
        with pytest.raises(ParseError, match="不支持的协议版本"):
            unpack_header(header)

    def test_unknown_opcode(self):
        """未知操作码抛出异常"""
        header = struct.pack(">IHHII", 100, 16, ProtoVer.JSON, 99, 1)
        with pytest.raises(ParseError, match="未知的操作码"):
            unpack_header(header)


# ==================== decode_body ====================


class TestDecodeBody:
    """测试 body 解码"""

    def test_json_proto_ver(self):
        """proto_ver=0 时直接返回原始数据"""
        raw = b'{"cmd":"DANMU_MSG"}'
        result = decode_body(raw, ProtoVer.JSON)
        assert result == raw

    def test_zlib_decompress(self):
        """proto_ver=2 时正确解压 zlib"""
        original = b'{"cmd":"DANMU_MSG","info":["test"]}'
        compressed = zlib.compress(original)
        result = decode_body(compressed, ProtoVer.ZLIB)
        assert result == original

    def test_zlib_bad_data(self):
        """损坏的 zlib 数据抛出异常"""
        with pytest.raises(ParseError, match="zlib 解压失败"):
            decode_body(b"not valid zlib data", ProtoVer.ZLIB)


# ==================== split_messages ====================


class TestSplitMessages:
    """测试消息分割"""

    def test_single_message(self):
        """单条 JSON 消息"""
        body = b'{"cmd":"DANMU_MSG","info":["test"]}'
        result = split_messages(body)
        assert len(result) == 1
        assert result[0]["cmd"] == "DANMU_MSG"

    def test_multiple_messages(self):
        """多条消息以 \\n 分隔"""
        body = b'{"cmd":"DANMU_MSG"}\n{"cmd":"SEND_GIFT"}\n{"cmd":"WELCOME"}'
        result = split_messages(body)
        assert len(result) == 3
        assert result[0]["cmd"] == "DANMU_MSG"
        assert result[1]["cmd"] == "SEND_GIFT"
        assert result[2]["cmd"] == "WELCOME"

    def test_empty_lines(self):
        """空行被跳过"""
        body = b'\n{"cmd":"TEST"}\n\n{"cmd":"TEST2"}\n'
        result = split_messages(body)
        assert len(result) == 2

    def test_trailing_newline(self):
        """尾部换行"""
        body = b'{"cmd":"TEST"}\n'
        result = split_messages(body)
        assert len(result) == 1
        assert result[0]["cmd"] == "TEST"

    def test_invalid_json_skipped(self):
        """无效 JSON 被跳过"""
        body = b'{"cmd":"VALID"}\nnot-json\n{"cmd":"ALSO_VALID"}'
        result = split_messages(body)
        assert len(result) == 2
        assert result[0]["cmd"] == "VALID"
        assert result[1]["cmd"] == "ALSO_VALID"


# ==================== parse ====================


class TestParse:
    """测试完整数据包解析"""

    def test_parse_json_packet(self):
        """解析 proto_ver=0 的完整数据包"""
        body = b'{"cmd":"DANMU_MSG","info":["test"]}'
        total_len = HEADER_LENGTH + len(body)
        header = struct.pack(
            ">IHHII", total_len, HEADER_LENGTH, ProtoVer.JSON, OpCode.DANMU_MSG, 42
        )
        packet = header + body

        result = parse(packet)
        assert len(result) == 1
        assert result[0]["cmd"] == "DANMU_MSG"

    def test_parse_zlib_packet(self):
        """解析 proto_ver=2 的压缩数据包"""
        body = b'{"cmd":"DANMU_MSG"}\n{"cmd":"SEND_GIFT"}'
        compressed = zlib.compress(body)
        total_len = HEADER_LENGTH + len(compressed)
        header = struct.pack(
            ">IHHII", total_len, HEADER_LENGTH, ProtoVer.ZLIB, OpCode.DANMU_MSG, 1
        )
        packet = header + compressed

        result = parse(packet)
        assert len(result) == 2
        assert result[0]["cmd"] == "DANMU_MSG"
        assert result[1]["cmd"] == "SEND_GIFT"

    def test_parse_empty_packet(self):
        """空数据包抛出异常"""
        with pytest.raises(ParseError, match="收到空数据包"):
            parse(b"")

    def test_parse_brotli_sub_packets(self):
        """proto_ver=3 brotli 解压后递归解析子包"""
        import brotli

        # 构造两个 JSON 子包拼接
        sub1_body = b'{"cmd":"DANMU_MSG"}\n'
        sub1_total = HEADER_LENGTH + len(sub1_body)
        sub1_header = struct.pack(">IHHII", sub1_total, HEADER_LENGTH, ProtoVer.JSON, OpCode.DANMU_MSG, 1)
        sub1 = sub1_header + sub1_body

        sub2_body = b'{"cmd":"SEND_GIFT"}\n'
        sub2_total = HEADER_LENGTH + len(sub2_body)
        sub2_header = struct.pack(">IHHII", sub2_total, HEADER_LENGTH, ProtoVer.JSON, OpCode.DANMU_MSG, 2)
        sub2 = sub2_header + sub2_body

        # 拼接后 brotli 压缩，外层封装
        inner = sub1 + sub2
        compressed = brotli.compress(inner)
        total_len = HEADER_LENGTH + len(compressed)
        outer_header = struct.pack(">IHHII", total_len, HEADER_LENGTH, ProtoVer.BROTLI, OpCode.DANMU_MSG, 1)
        packet = outer_header + compressed

        result = parse(packet)
        assert len(result) == 2
        assert result[0]["cmd"] == "DANMU_MSG"
        assert result[1]["cmd"] == "SEND_GIFT"


# ==================== pack_auth ====================


class TestPackAuth:
    """测试认证包构造"""

    def test_auth_packet_structure(self):
        """认证包含正确的头部和 JSON body"""
        packet = pack_auth(room_id=12345, token="test_token", uid=0, buvid="test_buvid")
        header = unpack_header(packet)

        assert header.op == OpCode.AUTH
        assert header.proto_ver == ProtoVer.HEARTBEAT

        body = packet[HEADER_LENGTH:]
        decoded = json.loads(body.decode("utf-8"))

        assert decoded["roomid"] == 12345
        assert decoded["uid"] == 0
        assert decoded["key"] == "test_token"
        assert decoded["protover"] == ProtoVer.BROTLI.value
        assert decoded["platform"] == "web"
        assert decoded["type"] == 2

    def test_auth_with_custom_uid(self):
        """使用自定义 UID"""
        packet = pack_auth(room_id=999, token="token", uid=123456, buvid="test_buvid")
        body = packet[HEADER_LENGTH:]
        decoded = json.loads(body.decode("utf-8"))

        assert decoded["uid"] == 123456
        assert decoded["roomid"] == 999


# ==================== pack_heartbeat ====================


class TestPackHeartbeat:
    """测试心跳包"""

    def test_heartbeat_packet(self):
        """心跳包使用正确的操作码"""
        packet = pack_heartbeat()
        header = unpack_header(packet)

        assert header.op == OpCode.HEARTBEAT
        assert header.total_len == HEADER_LENGTH
