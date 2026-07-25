"""数据库建表 SQL 常量"""

CREATE_ROOMS_TABLE = """
CREATE TABLE IF NOT EXISTS rooms (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id         INTEGER NOT NULL UNIQUE,
    room_name       TEXT DEFAULT '',
    anchor_name     TEXT DEFAULT '',
    status          TEXT DEFAULT 'idle',
    error_msg       TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT DEFAULT (datetime('now', 'localtime'))
);
"""

ALTER_ROOMS_ANCHOR_NAME = """
ALTER TABLE rooms RENAME COLUMN streamer_name TO anchor_name;
"""

CREATE_DANMU_RECORDS_TABLE = """
CREATE TABLE IF NOT EXISTS danmu_records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id     INTEGER NOT NULL,
    session_id  INTEGER DEFAULT 0,
    uid         INTEGER DEFAULT 0,
    username    TEXT NOT NULL,
    content     TEXT NOT NULL,
    timestamp   INTEGER NOT NULL,
    medal_level INTEGER DEFAULT 0,
    medal_name  TEXT DEFAULT '',
    user_level  INTEGER DEFAULT 0,
    is_gift     INTEGER DEFAULT 0,
    raw_json    TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now', 'localtime'))
);
"""

CREATE_DANMU_INDEX = """
CREATE INDEX IF NOT EXISTS idx_danmu_room_time
ON danmu_records(room_id, timestamp);
"""

CREATE_DANMU_SESSION_INDEX = """
CREATE INDEX IF NOT EXISTS idx_danmu_session
ON danmu_records(session_id);
"""

CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id     INTEGER NOT NULL,
    start_time  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    end_time    TEXT DEFAULT '',
    danmu_count INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'active',
    created_at  TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id)
);
"""

CREATE_SESSIONS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_sessions_room
ON sessions(room_id);
"""

ALTER_DANMU_ADD_SESSION_ID = """
ALTER TABLE danmu_records ADD COLUMN session_id INTEGER DEFAULT 0;
"""

# P0 阶段所有建表语句，按依赖顺序
ALL_TABLES = [
    CREATE_ROOMS_TABLE,
    CREATE_DANMU_RECORDS_TABLE,
    CREATE_DANMU_INDEX,
    CREATE_SESSIONS_TABLE,
    CREATE_SESSIONS_INDEX,
    CREATE_DANMU_SESSION_INDEX,
]

# 弹幕批量插入语句
INSERT_DANMU = """
INSERT INTO danmu_records
    (room_id, session_id, uid, username, content, timestamp,
     medal_level, medal_name, user_level, is_gift, raw_json)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

# 房间表查询语句
SELECT_ALL_ROOMS = "SELECT * FROM rooms ORDER BY created_at DESC"
SELECT_ROOM_BY_ID = "SELECT * FROM rooms WHERE room_id = ?"
INSERT_ROOM = "INSERT OR IGNORE INTO rooms (room_id, room_name, anchor_name) VALUES (?, ?, ?)"
UPDATE_ROOM_STATUS = "UPDATE rooms SET status = ?, error_msg = ?, updated_at = datetime('now', 'localtime') WHERE room_id = ?"
UPDATE_ROOM_INFO = "UPDATE rooms SET room_name = ?, anchor_name = ?, updated_at = datetime('now', 'localtime') WHERE room_id = ?"
DELETE_ROOM = "DELETE FROM rooms WHERE room_id = ?"
SELECT_ROOM_DANMU_COUNT = "SELECT COUNT(*) FROM danmu_records WHERE room_id = ?"

# 弹幕表查询语句
SELECT_DANMU_BY_ROOM = "SELECT * FROM danmu_records WHERE room_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?"
SELECT_DANMU_BY_SESSION = "SELECT * FROM danmu_records WHERE session_id = ? ORDER BY timestamp ASC"
SELECT_DANMU_COUNT = "SELECT COUNT(*) FROM danmu_records WHERE room_id = ?"
SELECT_DANMU_COUNT_BY_SESSION = "SELECT COUNT(*) FROM danmu_records WHERE session_id = ?"
SELECT_DANMU_STATS = """
SELECT 
    COUNT(*) as total_count,
    COUNT(DISTINCT uid) as unique_users,
    MIN(timestamp) as min_time,
    MAX(timestamp) as max_time
FROM danmu_records 
WHERE room_id = ?
"""
SELECT_DANMU_PEAK_HOUR = """
SELECT 
    strftime('%H:00', datetime(timestamp, 'unixepoch', 'localtime')) as hour,
    COUNT(*) as count
FROM danmu_records 
WHERE room_id = ?
GROUP BY hour
ORDER BY count DESC
LIMIT 1
"""

# 会话表查询语句
INSERT_SESSION = "INSERT INTO sessions (room_id, start_time) VALUES (?, datetime('now', 'localtime'))"
SELECT_SESSION_BY_ID = "SELECT * FROM sessions WHERE id = ?"
SELECT_SESSIONS_BY_ROOM = "SELECT * FROM sessions WHERE room_id = ? ORDER BY start_time DESC"
SELECT_ACTIVE_SESSION = "SELECT * FROM sessions WHERE room_id = ? AND status = 'active' ORDER BY start_time DESC LIMIT 1"
UPDATE_SESSION_END = """
UPDATE sessions 
SET end_time = datetime('now', 'localtime'), 
    danmu_count = (SELECT COUNT(*) FROM danmu_records WHERE session_id = ?),
    status = 'ended'
WHERE id = ?
"""
DELETE_SESSION = "DELETE FROM sessions WHERE id = ?"
