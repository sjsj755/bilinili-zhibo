# BiliLini 直播弹幕分析工具 — 项目规格文档

## 一、项目概述

基于 Python + React 的 B 站直播弹幕实时采集与分析工具，支持直播中实时轻量分析和直播回放离线深度分析两种模式。

- **使用场景**：个人单机使用
- **技术栈**：Python (FastAPI) + React + Vite + SQLite + ECharts
- **核心能力**：弹幕采集 → 实时分析 → 深度分析 → 可视化展示

---

## 二、技术栈

| 层 | 技术 | 说明 |
|---|------|------|
| 弹幕采集 | `websockets` + 自研二进制协议解析 | WebSocket 直连 B 站弹幕服务器 |
| 后端框架 | FastAPI + `websockets` | REST API + WebSocket 推送服务 |
| 前端框架 | React 18 + Vite + TypeScript | SPA 仪表盘 |
| 可视化 | ECharts + echarts-wordcloud | 图表 + 词云 |
| UI 样式 | TailwindCSS | 原子化 CSS |
| 数据存储 | SQLite (sqlite3 + SQLAlchemy) | 本地轻量数据库 |
| 中文分词 | jieba 分词 | Python 原生结巴分词 |
| 情感分析 | SnowNLP | 中文情感分析库 |
| 后端语言 | Python 3.12+ | 异步 async/await |
| 构建工具 | Vite (前端) + uvicorn (后端) | 开发热更新 |

---

## 三、系统架构

```
┌──────────────────────────────────────────────────────┐
│                  React 前端 (Vite)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │ 弹幕墙    │ │ 仪表盘    │ │ 直播间管理│ │回放分析  │ │
│  │ 实时滚动  │ │ 图表统计  │ │ 添加/切换 │ │导入/查看 │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │
└────────────────────┬─────────────────────────────────┘
          WebSocket (实时推送) + REST API
┌────────────────────┴─────────────────────────────────┐
│              FastAPI Server (:3001)                    │
│  /api/room/*       直播间管理                          │
│  /api/danmu/*      弹幕查询、统计                       │
│  /api/analysis/*   分析任务管理                         │
│  /api/replay/*     回放弹幕导入                         │
│  /ws               实时弹幕/分析数据推送                 │
└──┬───────────────────┬───────────────────────────────┘
   │                   │
┌──┴──────────┐   ┌────┴──────────────────┐
│ 采集管理器    │   │ 分析引擎               │
│ Collector    │   │ Analyzer               │
│              │   │                        │
│ • 多直播间管理│   │ • 实时分析（轻量）      │
│ • WebSocket  │   │   - 频率统计           │
│   连接池      │   │   - 关键词 Top10       │
│ • 二进制协议 │   │   - 情感正负占比        │
│   解析       │   │                        │
│ • 心跳维持   │   │ • 深度分析（离线）      │
│ • 断线重连   │   │   - TF-IDF 关键词       │
│              │   │   - 情感时间分布        │
│              │   │   - 热点时刻检测        │
│              │   │   - 用户画像            │
└──┬──────────┘   └────┬──────────────────┘
   │                   │
┌──┴───────────────────┴──────────────────────────────┐
│              SQLite (better-sqlite3)                  │
│  rooms | danmu_records | analysis_tasks | reports     │
│  replay_sessions | custom_dict                       │
└──────────────────────────────────────────────────────┘
```

---

## 四、模块设计

### 4.1 数据采集模块 (`backend/collector/`)

**文件结构：**
```
backend/collector/
├── bili_client.py      # 单直播间 WebSocket 客户端
├── parser.py           # B站二进制协议解析器
└── danmu_types.py      # 协议类型定义（ProtoVer, OpCode, PacketHeader）
```

**BiliClient 核心流程：**
1. 调用 `GET https://api.live.bilibili.com/room/v1/Room/room_init?id={roomId}` 将短号解析为真实房间号
   - 支持短号（如 1695）和长号（如 30813107）两种格式
   - 检查 `live_status`，未开播时给出警告
2. 调用 `GET https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo` 获取 token 和弹幕服务器地址列表
   - 2025 新版要求 **WBI 签名**（`w_rid` + `wts` 参数）+ **buvid3 cookie**
   - WBI 签名通过 `utils/wbi.py` 实现：获取 nav API 中的 img_key/sub_key → 混淆表生成 mixin key → 参数排序后 MD5
   - mixin key 缓存 1 小时，避免重复请求 nav API
3. 选取第一个服务器地址，通过 `websockets` 库建立连接 `wss://{host}:{wss_port}/sub`
4. 发送认证包（JSON 格式，含 uid, roomid=真实房间号, protover=3(brotli), platform, type, buvid, key）
   - buvid3 在 `BiliClient.__init__` 中生成一次并复用，避免频繁更换触发风控
5. 心跳：每 25 秒发送心跳包（16 字节固定头部，op=2）
6. 接收二进制包 → parser 解析 → 过滤 DANMU_MSG（含变体 DANMU_MSG_4_0、DANMU_MSG_5_0 等）→ 提取 DanmuRecord → 触发回调
   - 回调函数支持同步和异步两种形式（通过 `asyncio.iscoroutinefunction` 自动判断）

**认证回复判定：**
- 服务端返回 op=8 (AUTH_REPLY) 表示认证回复
- 消息体格式为 `{"code": 0}`，code==0 表示认证成功
- 认证失败时关闭 WebSocket 并抛出 `BiliClientError`
- 认证超时（10 秒未收到回复）同样关闭连接并抛出异常

**断线重连机制：**
- 连接断开后自动以指数退避策略重连（基础延迟 4s，最大 30s）
- 成功连接后重置重连计数器
- 心跳任务在监听循环启动前清理可能残留的旧任务，防止泄漏
- `_closeWebSocket` 调用 `wait_closed()` 确保底层 TCP 连接完全关闭

**协议解析 (parser.py)：**

B 站弹幕 WebSocket 协议头部 16 字节（大端序）：

| 偏移 | 长度 | 字段 | 说明 |
|------|------|------|------|
| 0 | 4 | total_len | 包总长度 |
| 4 | 2 | header_len | 头部长度（固定 16） |
| 6 | 2 | proto_ver | 协议版本（0=JSON, 2=zlib压缩, 3=brotli压缩） |
| 8 | 4 | op | 操作类型（2=客户端心跳, 3=心跳回复含人气值, 5=弹幕消息, 7=客户端认证, 8=服务端认证回复） |
| 12 | 4 | seq | 序列号 |

Body 解析：
- proto_ver=0：UTF-8 文本，可能包含多条（按 `\n` 分割）
- proto_ver=2：zlib 压缩，解压后同 proto_ver=0
- proto_ver=3：brotli 压缩，解压后同 proto_ver=0

**Manager 功能（P1 阶段实现）：**
- 维护 `Dict[int, BiliClient]` 连接池
- 提供 `start_monitor(room_id)` / `stop_monitor(room_id)` / `stop_all()`
- 统一对外回调通知弹幕事件

### 4.2 数据处理与分析模块 (`backend/services/`) ✅

**文件结构：**
```
backend/services/
├── __init__.py
├── bili_api.py              # B站 API 调用封装
├── segment_engine.py        # jieba 分词引擎（含停用词过滤、自定义词典、节流批处理）
├── sentiment_engine.py      # SnowNLP 情感分析引擎（含自定义训练、滑动窗口统计）
├── frequency_engine.py      # 滑动窗口频率统计算法
├── keyword_engine.py        # 关键词 Top K 增量更新算法（小顶堆优化）
└── realtime_engine.py       # 实时分析引擎整合（注册模式解耦）
```

#### 4.2.1 实时分析引擎（RealtimeAnalyzer）

**架构设计**：采用注册模式实现各引擎解耦，通过 `RealtimeAnalyzer` 统一管理和聚合。

```
┌─────────────────────────────────────────────────────────────────────┐
│                     RealtimeAnalyzer (统一入口)                      │
│                          │                                          │
│        ┌─────────────────┼─────────────────┐                        │
│        ▼                 ▼                 ▼                        │
│  register_segment    register_sentiment   register_frequency         │
│  register_keyword                                                   │
│        │                 │                 │                        │
│        ▼                 ▼                 ▼                        │
│  SegmentEngine    SentimentEngine    FrequencyEngine    KeywordEngine│
│        (独立)             (独立)             (独立)           (独立)  │
└─────────────────────────────────────────────────────────────────────┘
```

**核心方法**：

| 方法 | 功能 | 参数 | 返回值 |
|------|------|------|--------|
| `register_segment_engine(engine)` | 注册分词引擎 | engine: SegmentEngine | None |
| `register_sentiment_engine(engine)` | 注册情感引擎 | engine: SentimentEngine | None |
| `register_frequency_engine(engine)` | 注册频率引擎 | engine: FrequencyEngine | None |
| `register_keyword_engine(engine)` | 注册关键词引擎 | engine: KeywordEngine | None |
| `start_all_engines()` | 启动所有引擎 | - | None |
| `stop_all_engines()` | 停止所有引擎 | - | None |
| `get_analysis(room_id)` | 获取单个房间聚合分析结果 | room_id: int | 聚合数据 |
| `get_all_analysis()` | 获取所有房间聚合分析结果 | - | [聚合数据列表] |
| `get_engine_status()` | 获取引擎状态 | - | 状态字典 |

**触发方式**：每条弹幕到达时增量更新，每秒聚合推送一次。

**分析维度：**

| 维度 | 算法 | 输出 |
|------|------|------|
| 弹幕频率 | 滑动时间窗口（10秒），双端队列 | 实时频率数值（弹幕/秒） |
| 关键词 Top50 | jieba 分词 → 停用词过滤 → 哈希表词频 → 小顶堆取 Top K | 关键词排行（词频+频率占比） |
| 情感占比 | SnowNLP 情感打分 → 正/负/中 滑动窗口计数器 | 百分比分布 |

**数据结构（聚合输出）：**
```python
{
    "room_id": 12345,
    "timestamp": 1620000000.0,
    "frequency": {
        "frequency": 45.6,
        "count": 456,
        "total_count": 10000,
        "window_start": 1599999940.0,
        "window_end": 1620000000.0
    },
    "sentiment": {
        "positive_count": 200,
        "negative_count": 80,
        "neutral_count": 176,
        "total_count": 456,
        "positive_rate": 0.4386,
        "negative_rate": 0.1754,
        "neutral_rate": 0.3860
    },
    "keywords": {
        "top_k": [{"word": "主播", "count": 50, "frequency": 0.1}],
        "total_count": 500,
        "window_start": 1599999940.0,
        "window_end": 1620000000.0
    }
}
```

#### 4.2.2 深度分析引擎

**触发方式**：手动触发，指定时间范围后批量分析

**分析维度：**

| 维度 | 算法 | 说明 |
|------|------|------|
| 关键词 TF-IDF | 全量弹幕 IDF + 单条 TF，取 Top20 | 更精准的关键词 |
| 情感时间分布 | 按分钟粒度聚合情感得分 | 折线图展示情绪波动 |
| 热点时刻检测 | 弹幕密度 > 均值 * 阈值（可配，默认 3x） | 标记高潮时间点 |
| 用户画像 | 粉丝勋章等级分布 / 用户等级分布 / 活跃度 Top 用户 | 饼图 + 排行榜 |

**输出：**
```python
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class TimeRange:
    start: float
    end: float

@dataclass
class HotMoment:
    start_time: float
    end_time: float
    density: float
    peak_content: List[str]

@dataclass
class SentimentPoint:
    time: str
    score: float
    positive: int
    negative: int
    neutral: int

@dataclass
class UserProfile:
    medal_distribution: Dict[str, int]
    level_distribution: Dict[str, int]
    top_active_users: List[dict]  # [{ username, count }]

@dataclass
class DeepAnalysisResult:
    room_id: int
    time_range: TimeRange
    total_danmu_count: int
    keywords: List[dict]          # [{ word, tfidf }]
    sentiment_timeline: List[SentimentPoint]
    hot_moments: List[HotMoment]
    user_profile: UserProfile
```

#### 4.2.3 情感分析

使用 **SnowNLP** 进行中文情感分析：
- SnowNLP 基于字符级语言模型和贝叶斯分类，支持中文情感打分
- 输出 0~1 之间的概率值，> 0.6 为正面，< 0.4 为负面，中间为中性
- 对于网络用语和弹幕语境，支持通过自定义训练数据微调模型
- 实时分析时使用默认模型快速判断，深度分析时可使用微调模型提升准确率

也可结合 jieba 分词 + 情感词典作为轻量级备选方案：
- 维护正面词库（约 5000 词）和负面词库（约 5000 词）
- 每条弹幕分词后逐词匹配，正面词 +1，负面词 -1

### 4.3 API 服务模块 (`backend/server/`)

**文件结构：**
```
backend/server/
├── __init__.py
├── main.py           # FastAPI 服务入口 + 生命周期管理
├── routes/
│   ├── __init__.py
│   ├── room.py       # 直播间管理路由
│   └── danmu.py      # 弹幕查询路由
└── middleware/
    ├── __init__.py
    └── error_handler.py  # 全局异常处理
```

**API 接口设计：**

#### 直播间管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/rooms` | 获取所有直播间列表（含弹幕统计） |
| POST | `/api/rooms` | 添加直播间 `{ roomId: number }`，支持短号自动解析 |
| DELETE | `/api/rooms/{roomId}` | 删除直播间 |
| POST | `/api/rooms/{roomId}/monitor` | 开始采集 |
| POST | `/api/rooms/{roomId}/monitor/stop` | 停止采集 |
| GET | `/api/rooms/{roomId}/info` | 获取直播间详情（含弹幕计数） |

#### 弹幕查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/danmu/{roomId}` | 分页查询弹幕 `?page=&pageSize=` |
| GET | `/api/danmu/{roomId}/stats` | 获取弹幕统计（总数、独立用户数、高峰时段） |

#### 分析任务

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/analysis/:roomId/realtime` | 获取实时分析结果 |
| POST | `/api/analysis/:roomId/deep` | 创建深度分析任务 `{ startTime, endTime }` |
| GET | `/api/analysis/:roomId/deep/:taskId` | 获取深度分析结果 |
| GET | `/api/analysis/:roomId/deep/list` | 获取历史分析任务列表 |
| DELETE | `/api/analysis/:roomId/deep/:taskId` | 删除分析任务 |

#### 回放弹幕导入

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/replay/import` | 导入回放弹幕 XML/JSON 文件 |
| GET | `/api/replay/sessions` | 获取导入的回放会话列表 |
| DELETE | `/api/replay/:sessionId` | 删除回放会话 |

#### WebSocket 推送

**连接：** `ws://localhost:3001/ws`

**客户端 → 服务端：**
```json
{ "type": "subscribe", "roomId": 12345 }
{ "type": "unsubscribe", "roomId": 12345 }
```

**服务端 → 客户端：**
```json
{ "type": "danmu", "data": "...DanmuRecord..." }
{ "type": "realtime_stats", "data": "...RealtimeStats..." }
{ "type": "connection_error", "roomId": 12345, "message": "...错误信息..." }
{ "type": "heartbeat" }
```

### 4.4 数据存储模块 (`backend/db/`)

**文件结构：**
```
backend/db/
├── __init__.py
├── database.py       # 数据库初始化、连接管理、DanmuWriter 批量写入
├── schema.py         # 建表语句 + SQL 常量
└── queries/
    ├── __init__.py
    ├── room.py       # 直播间 CRUD 查询
    └── danmu.py      # 弹幕分页查询 + 统计
```

**数据库表设计：**

```sql
-- 直播间表
CREATE TABLE rooms (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id       INTEGER NOT NULL UNIQUE,   -- B站直播间ID
  room_name     TEXT DEFAULT '',            -- 直播间名称（缓存）
  anchor_name   TEXT DEFAULT '',            -- 主播名称（缓存）
  status        TEXT DEFAULT 'idle',        -- idle | monitoring | error
  error_msg     TEXT DEFAULT '',            -- 最后错误信息
  created_at    TEXT DEFAULT (datetime('now', 'localtime')),
  updated_at    TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 弹幕记录表（核心数据表）
CREATE TABLE danmu_records (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id       INTEGER NOT NULL,           -- 关联直播间 room_id
  uid           INTEGER,                    -- 用户UID（0=匿名）
  username      TEXT NOT NULL,               -- 用户名
  content       TEXT NOT NULL,               -- 弹幕内容
  timestamp     INTEGER NOT NULL,           -- 发送时间戳（毫秒）
  medal_level   INTEGER,                    -- 粉丝勋章等级
  medal_name    TEXT,                       -- 粉丝勋章名称
  user_level    INTEGER,                    -- 用户等级
  is_gift       INTEGER DEFAULT 0,          -- 是否为礼物弹幕
  raw_json      TEXT,                       -- 原始JSON（调试用）
  created_at    TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX idx_danmu_room_time ON danmu_records(room_id, timestamp);
CREATE INDEX idx_danmu_room_user ON danmu_records(room_id, uid);

-- 分析任务表
CREATE TABLE analysis_tasks (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id       INTEGER NOT NULL,
  type          TEXT NOT NULL,              -- 'realtime' | 'deep'
  status        TEXT DEFAULT 'pending',     -- pending | running | completed | failed
  params        TEXT,                       -- JSON 参数
  result_json   TEXT,                       -- JSON 结果
  start_time    INTEGER,                    -- 分析开始时间戳
  end_time      INTEGER,                    -- 分析结束时间戳
  created_at    TEXT DEFAULT (datetime('now', 'localtime')),
  completed_at  TEXT
);

CREATE INDEX idx_analysis_room ON analysis_tasks(room_id);

-- 回放会话表
CREATE TABLE replay_sessions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id       INTEGER NOT NULL,
  source_type   TEXT DEFAULT 'xml',         -- xml | json | manual
  file_name     TEXT,
  danmu_count   INTEGER DEFAULT 0,
  duration      INTEGER,                    -- 持续时长（秒）
  created_at    TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 自定义词典表
CREATE TABLE custom_dict (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  word          TEXT NOT NULL UNIQUE,
  tag           TEXT DEFAULT 'n',           -- 词性标签
  freq          INTEGER DEFAULT 1000,       -- 词频权重
  created_at    TEXT DEFAULT (datetime('now', 'localtime'))
);
```

---

## 五、前端设计

### 5.1 页面路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 仪表盘首页 | 概览，显示所有已添加直播间状态 |
| `/room/:roomId` | 直播间详情 | 实时弹幕墙 + 实时分析图表 |
| `/room/:roomId/deep` | 深度分析页 | 选择时间段，触发和分析结果展示 |
| `/replay` | 回放管理 | 导入/查看回放弹幕分析 |

### 5.2 组件树

```
App
├── Layout
│   ├── Sidebar                 # 侧边栏（直播间列表）
│   │   ├── RoomList            # 直播间列表
│   │   ├── RoomItem            # 单个房间项
│   │   └── AddRoomModal        # 添加直播间弹窗
│   └── MainContent             # 主内容区
│
├── Dashboard (/)               # 仪表盘首页
│   ├── StatusCards             # 各直播间状态卡片
│   └── GlobalStats             # 全局统计概览
│
├── RoomDetail (/room/:roomId)   # 直播间详情
│   ├── RoomHeader              # 直播间信息头部（标题、主播、采集控制）
│   ├── DanmakuContainer        # 弹幕容器（固定高度 500px）
│   │   ├── HistoryDanmaku      # 历史弹幕列表（灰色样式）
│   │   ├── Separator           # 实时/历史分隔线
│   │   └── LiveDanmaku         # 实时弹幕列表（蓝色样式）
│   ├── NewDanmakuHint          # 新弹幕提示（当用户离开底部时显示）
│   └── HistoryCard             # 采集历史卡片（右侧固定）
│       └── SessionItem         # 单个采集会话项（时间、弹幕数、状态）
│
├── DeepAnalysis (/room/:roomId/deep) # 深度分析页
│   ├── TimeRangeSelector       # 时间范围选择
│   ├── AnalysisProgress        # 分析进度
│   ├── HotMomentsTimeline      # 热点时刻时间轴
│   ├── UserProfileCharts       # 用户画像图表
│   └── SentimentTimelineChart  # 情感时间分布
│
└── ReplayManager (/replay)     # 回放管理
    ├── UploadZone              # 文件上传区域
    ├── ReplaySessionList       # 回放会话列表
    └── ReplayDetail            # 回放分析详情
```

### 5.3 数据流

```
                        React Context/State
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         REST API        WebSocket       Local State
         (查询/操作)     (实时推送)      (UI 状态)
              │               │               │
              └───────────────┼───────────────┘
                              │
                      自定义 Hook 封装
                     (useRoom, useDanmaku, useAnalysis)
```

**核心 Hooks：**
```typescript
useRoom()           // 直播间 CRUD 操作、定时刷新、状态管理
useDanmaku(roomId)  // WebSocket 连接 + 弹幕数据状态、实时/历史区分、采集会话管理
useRealtimeStats(roomId) // 实时统计数据
useDeepAnalysis(roomId)  // 深度分析任务管理
useReplay()         // 回放管理
```

**useDanmaku Hook 核心功能：**
- **采集会话管理**：`clearAndStartNewSession()` 清空列表开始新会话，`markAsHistory()` 将当前会话标记为历史
- **实时弹幕处理**：WebSocket 接收弹幕、节流渲染（100ms）、最大缓存 1000 条
- **自动滚动**：用户在底部时自动滚动到最新弹幕，离开底部时显示新弹幕提示
- **新弹幕提示**：`hasNewDanmaku` / `newDanmakuCount` 状态，点击提示跳转最新弹幕

### 5.4 界面布局示意

#### 仪表盘首页
```
┌─────────────────────────────────────────────────┐
│  🔴 BiliLini             添加直播间 [+ 输入框]   │
├─────────┬───────────────────────────────────────┤
│         │  ┌──────────┐ ┌──────────┐           │
│ 直播间A  │  │ 直播间A    │ │ 直播间B    │          │
│  ● 在线  │  │ 弹幕: 1234 │ │ 弹幕: 567  │          │
│          │  │ 今日峰值   │ │ 已暂停     │          │
│ 直播间B  │  └──────────┘ └──────────┘           │
│  ○ 离线  │                                       │
│          │  📊 全局统计                          │
│ ＋添加   │  ┌───────────────────────────────┐   │
│          │  │ 今日总弹幕: 5,432 | 分析中: 2 │   │
│          │  └───────────────────────────────┘   │
└─────────┴───────────────────────────────────────┘
```

#### 直播间详情页（实时模式）
```
┌─────────────────────────────────────────────────────────┐
│  🔴 BiliLini  > [直播间A]  主播: xxx    ▶ 开始采集      │
├─────────┬──────────────────────────────────┬───────────┤
│         │  ┌─────────────────────────────┐ │           │
│ 直播间A ●│  │ 💬 实时弹幕 (固定高度 500px) │ │ 采集历史   │
│         │  │                             │ │ ──────────│
│ 直播间B  │  │ 用户A: 哈哈哈太搞笑了        │ │ 2026/07/12│
│         │  │ 用户B: 主播看看弹幕           │ │ 22:34-22:36│
│         │  │ ─────────── 实时采集开始 ─────│ │ 13条弹幕   │
│         │  │ 用户C: 66666666 (实时)       │ │ ──────────│
│         │  │ 用户D: 主播好强               │ │ 2026/07/12│
│         │  │                             │ │ 22:45-22:46│
│         │  │                             │ │ 10条弹幕   │
│         │  └─────────────────────────────┘ │           │
│         │                                 │           │
│         │  [有 5 条新弹幕 ▼]               │           │
└─────────┴──────────────────────────────────┴───────────┘
```

**弹幕交互逻辑：**
- **自动滚动模式**：用户在底部时，新弹幕到来自动滚动，最新弹幕始终可见
- **手动浏览模式**：用户向上滚动离开底部时，停止自动滚动，显示"有 X 条新弹幕"提示
- **点击提示跳转**：点击新弹幕提示，跳转到最新弹幕，恢复自动滚动模式

#### 深度分析页
```
┌─────────────────────────────────────────────────┐
│  🔴 BiliLini  > [直播间A]    实时模式 | 深度分析  │
├─────────────────────────────────────────────────┤
│  ⏱ 时间范围: [2024-01-01 20:00] → [2024-01-01 22:00] [开始分析]
│  ────────────────────────────────────────────────
│  ┌─────────────────────────────────────────────┐
│  │ 🔥 热点时刻                                    │
│  │ ────────────●───●────────●───────────────── │
│  │              21:05 21:30 21:58               │
│  └─────────────────────────────────────────────┘
│
│  ┌──────────────┐ ┌──────────────┐ ┌──────────┐
│  │关键词 TF-IDF  │ │情感时间分布   │ │用户画像    │
│  │(柱状图)       │ │(折线图)       │ │(饼图+排行) │
│  └──────────────┘ └──────────────┘ └──────────┘
│
│  [📥 导出报告] [🗑 删除分析]
└─────────────────────────────────────────────────┘
```

---

## 六、数据流

### 6.1 实时弹幕数据流

```
B站弹幕服务器                            前端
    │                                     │
    │ WebSocket (binary)                   │
    ▼                                     │
┌─────────┐   danmu event   ┌──────────┐  │
│ BiliClient│ ─────────────→ │ Manager  │  │
└─────────┘                 └────┬─────┘  │
                                 │        │
                    ┌────────────┼────┐   │
                    ▼            ▼    │   │
              ┌──────────┐ ┌────────┐ │   │
              │ SQLite    │ │实时分析 │ │   │
              │ 写入队列   │ │增量更新 │ │   │
              └──────────┘ └───┬────┘ │   │
                               │      │   │
                               ▼      │   │
                          ┌────────┐  │   │
                          │ WS 推送 │──┼───┘
                          │ 服务    │──┼──→ WebSocket → React 组件
                          └────────┘  │
```

### 6.2 深度分析数据流

```
前端 [发起分析请求]
    │
    ▼
POST /api/analysis/:roomId/deep { startTime, endTime }
    │
    ▼
SQLite 查询时间范围内全量弹幕
    │
    ▼
┌─────────────────┐
│ 深度分析引擎      │
│ • nodejieba 分词 │
│ • TF-IDF 计算   │
│ • 情感时序聚合   │
│ • 热点检测       │
│ • 用户画像       │
└────────┬────────┘
         │
         ▼
结果写入 analysis_tasks + result_json
         │
         ▼
前端轮询 GET /api/analysis/:roomId/deep/:taskId
         │
         ▼
渲染分析结果
```

---

## 七、配置管理

项目根目录 `.env` 文件（key=value 格式）：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `SESSDATA` | B 站登录 Cookie（可选，用于登录态采集） | 空（游客模式） |
| `BILI_UID` | B 站用户 UID（可选，从 SESSDATA 自动解析） | 空 |

采集模块内置默认配置（代码常量）：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `DEFAULT_HEARTBEAT_INTERVAL` | 心跳间隔（秒） | 25 |
| `DEFAULT_RECONNECT_BASE_DELAY` | 重连基础延迟（秒） | 4.0 |
| `DEFAULT_RECONNECT_MAX_DELAY` | 重连最大延迟（秒） | 30.0 |

日志级别配置（`run.py`）：

| Logger | 级别 | 说明 |
|--------|------|------|
| `collector` | DEBUG | 采集模块详细日志 |
| `websockets` | WARNING | 仅异常时输出 |
| `httpx` | WARNING | 仅异常时输出 |

---

## 八、开发阶段

### P0 — 基础采集（核心 MVP 前置）✅ 已完成
- [x] B 站弹幕二进制协议解析器 `parser.py`（支持 JSON/zlib/brotli 三种编码，brotli 递归解包子包）
- [x] 单直播间 WebSocket 客户端 `bili_client.py`（含 WBI 签名、buvid3 缓存、认证判定、断线重连）
- [x] SQLite 数据库初始化，danmu_records 表写入（批量写入 + WAL 模式）
- [x] 启动脚本 `run.py`，验证可采集并存储弹幕

### P1 — 实时展示
- [x] FastAPI 服务骨架 + 基础路由 + CORS 中间件 + 全局异常处理
- [x] 直播间管理 API（CRUD + 采集启停）
- [x] 弹幕查询 API（分页查询 + 统计）
- [x] WebSocket 推送服务（实时弹幕 → 前端）
- [x] 多直播间采集管理器 `manager.py`
- [x] 前端工程初始化（React + Vite + TailwindCSS）
- [x] 弹幕墙组件（实时滚动渲染）
- [x] 前端 WebSocket 连接 + 弹幕实时展示

### P2 — 实时分析（MVP 完整体验）✅ 后端完成
- [x] jieba 分词集成 + 停用词库 + 自定义词典（`segment_engine.py`）
- [x] SnowNLP 情感分析集成 + 自定义训练 + 滑动窗口统计（`sentiment_engine.py`）
- [x] 实时频率统计（滑动窗口，`frequency_engine.py`）
- [x] 实时关键词 Top50 增量更新（小顶堆优化，`keyword_engine.py`）
- [x] 实时分析引擎整合（注册模式解耦，`realtime_engine.py`）
- [ ] ECharts 图表集成（频率折线图、情感饼图、关键词词云）
- [ ] 实时分析 WebSocket 推送 + 前端渲染

### P3 — 深度分析
- [ ] 深度分析 API + 任务管理
- [ ] TF-IDF 关键词提取引擎
- [ ] 情感时间分布聚合
- [ ] 热点时刻检测算法
- [ ] 用户画像统计
- [ ] 深度分析前端页面 + 图表
- [ ] 分析报告导出（JSON/HTML）

### P4 — 完善与打磨
- [ ] 回放弹幕 XML 导入功能
- [ ] 自定义词典管理界面
- [ ] 错误处理完善（连接异常、协议变更降级提示）
- [ ] 长时间运行稳定性（内存监控、定时重启）
- [ ] UI 细节打磨（加载态、空态、错误态）
- [ ] 性能优化（大量弹幕场景）

---

## 九、技术难点与对策

| 难点 | 风险等级 | 对策 |
|------|---------|------|
| **B站协议变**更 | 🔴 高 | 模块化 parser，协议变更时仅需修改解析层；考虑维护协议版本检测逻辑；增加采集失败时向用户提示"可能协议变更" |
| **高弹幕量性能** | 🟡 中 | 前端虚拟滚动（仅渲染可见区域）；SQLite 批量写入（WAL 模式 + 事务批处理）；关键词仅维护 Top K 小顶堆 |
| **jieba 网络用语分词差** | 🟡 中 | 维护自定义词典（支持用户添加）；深度分析可预留调用大模型 API 的接口 |
| **长时间运行内存泄漏** | 🟡 中 | 环形缓冲区限制内存缓存大小；定期（如每 24h）自动重启采集进程 |
| **跨平台兼容** | 🟢 低 | 全部使用跨平台 Python 方案；SnowNLP 和 jieba 均为纯 Python 实现 |
| **WebSocket 断连丢失弹幕** | 🟢 低 | 断线重连机制 + 重连间隔期间非关键，个人使用可接受 |

---

## 十、项目目录结构

```
bilinili-zhibo/
├── docs/                            # 项目文档
│   ├── spec.md                      # 本规格文档
│   ├── project-plan.md              # 项目计划书
│   └── api-docs.md                  # API 接口文档
├── backend/                         # Python 后端
│   ├── collector/                   # 弹幕采集模块
│   │   ├── __init__.py
│   │   ├── bili_client.py           # 单直播间 WebSocket 客户端
│   │   ├── parser.py                # 二进制协议解析器
│   │   └── danmu_types.py           # 协议类型定义（ProtoVer/OpCode/PacketHeader）
│   ├── db/                          # 数据存储模块
│   │   ├── __init__.py
│   │   ├── database.py              # 数据库初始化 + DanmuWriter 批量写入
│   │   ├── schema.py                # 建表语句 + SQL 常量
│   │   └── queries/
│   │       ├── __init__.py
│   │       ├── room.py              # 直播间 CRUD 查询
│   │       └── danmu.py             # 弹幕分页查询 + 统计
│   ├── server/                      # API 服务模块
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI 入口 + 生命周期管理
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── room.py              # 直播间管理路由
│   │   │   └── danmu.py             # 弹幕查询路由
│   │   └── middleware/
│   │       ├── __init__.py
│   │       └── error_handler.py     # 全局异常处理
│   ├── services/                    # 业务服务层（实时分析引擎）
│   │   ├── __init__.py
│   │   ├── bili_api.py              # B站 API 调用封装
│   │   ├── segment_engine.py        # jieba 分词引擎
│   │   ├── sentiment_engine.py      # SnowNLP 情感分析引擎
│   │   ├── frequency_engine.py      # 滑动窗口频率统计
│   │   ├── keyword_engine.py        # 关键词 Top K 增量更新
│   │   └── realtime_engine.py       # 实时分析引擎整合
│   ├── shared/
│   │   └── types.py                  # 全局类型定义（DanmuRecord, Room）
│   └── utils/                       # 工具函数
│       ├── __init__.py
│       ├── config.py                # .env 配置加载
│       └── wbi.py                   # WBI 签名 + buvid3 生成
├── data/                            # 运行时数据
│   └── bilinili.db                  # SQLite 数据库文件（运行时生成）
├── .env                             # 环境配置（SESSDATA, BILI_UID）
├── .gitignore
├── requirements.txt                 # Python 依赖清单
├── run.py                           # CLI 采集启动脚本
└── start_server.py                  # API 服务启动脚本
```
