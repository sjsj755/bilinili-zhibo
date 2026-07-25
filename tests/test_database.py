"""database 模块单元测试"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db.database import closeDb, getConnection, initDb
from db.schema import ALL_TABLES


class TestSchema:
    """测试建表 SQL 常量"""

    def testAllTablesDefined(self):
        """ALL_TABLES 包含 P0 阶段需要的表"""
        assert len(ALL_TABLES) == 3  # rooms + danmu_records + index


class TestDatabase:
    """测试数据库初始化与连接管理"""

    def teardown_method(self):
        """每个测试后清理全局连接"""
        closeDb()

    def testInitDbCreatesTables(self):
        """initDb 创建表且不报错"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            dbPath = f.name

        try:
            conn = initDb(dbPath)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='rooms'"
            )
            assert cursor.fetchone() is not None

            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='danmu_records'"
            )
            assert cursor.fetchone() is not None
        finally:
            closeDb()
            os.unlink(dbPath)

    def testInitDbIsIdempotent(self):
        """重复调用 initDb 不报错"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            dbPath = f.name

        try:
            initDb(dbPath)
            initDb(dbPath)
            conn = getConnection()
            assert conn is not None
        finally:
            closeDb()
            os.unlink(dbPath)

    def testInitDbEnablesWal(self):
        """WAL 模式已开启"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            dbPath = f.name

        try:
            conn = initDb(dbPath)
            cursor = conn.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]
            assert mode.lower() == "wal"
        finally:
            closeDb()
            os.unlink(dbPath)

    def testGetConnectionBeforeInitRaises(self):
        """未初始化时 getConnection 抛出异常"""
        closeDb()
        with pytest.raises(RuntimeError, match="数据库未初始化"):
            getConnection()

    def testGetConnectionAfterInit(self):
        """初始化后可获取连接"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            dbPath = f.name

        try:
            initDb(dbPath)
            conn = getConnection()
            assert conn is not None
        finally:
            closeDb()
            os.unlink(dbPath)

    def testCloseDb(self):
        """closeDb 正常关闭"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            dbPath = f.name

        try:
            initDb(dbPath)
            closeDb()
            with pytest.raises(RuntimeError, match="数据库未初始化"):
                getConnection()
        finally:
            os.unlink(dbPath)
