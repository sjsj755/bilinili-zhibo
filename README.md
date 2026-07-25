# BiliLive 弹幕监控系统

一个基于 Python + React 的 B 站直播间弹幕实时监控与分析系统。

## 功能特性

- 📡 **实时弹幕采集** - 通过 WebSocket 实时连接 B 站直播间，采集弹幕数据
- 📊 **实时统计分析** - 弹幕频率统计、关键词分析、情感分析
- 📈 **可视化图表** - 使用 ECharts 展示弹幕频率趋势图
- 💾 **数据持久化** - SQLite 数据库存储历史弹幕数据
- 🎨 **现代 UI** - 基于 React + TailwindCSS 的现代化界面
- 🔄 **WebSocket 通信** - 前后端实时数据同步

## 技术栈

### 后端
- Python 3.11+
- FastAPI - 高性能 Web 框架
- WebSockets - 实时通信
- SQLite - 轻量级数据库
- Pydantic - 数据验证

### 前端
- React 19
- TypeScript
- Vite - 构建工具
- TailwindCSS 3 - 样式框架
- ECharts - 图表库
- React Router - 路由管理

## 项目结构

```
bilinili-zhibo/
├── backend/              # Python 后端
│   ├── collector/        # 弹幕采集模块
│   ├── db/               # 数据库模块
│   ├── server/           # FastAPI 服务
│   ├── services/         # 业务逻辑服务
│   ├── shared/           # 共享类型定义
│   └── utils/            # 工具函数
├── data/                 # SQLite 数据库文件
├── docs/                 # 项目文档
├── frontend/             # React 前端
│   ├── src/              # 源代码
│   ├── public/           # 静态资源
│   └── package.json      # 依赖配置
├── .env                  # 后端环境变量（本地开发）
├── .env.example          # 环境变量模板
├── requirements.txt      # Python 依赖
└── README.md             # 项目说明
```

## 安装运行

### 环境要求

- Python 3.11+
- Node.js 18+
- pnpm

### 后端启动

```bash
# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置 SESSDATA（可选）
# SESSDATA=your_bilibili_sessdata_cookie

# 启动服务
python -m backend.server.main
```

后端服务将在 `http://localhost:3001` 运行。

### 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
pnpm install

# 复制环境变量模板
cp .env.example .env

# 启动开发服务器
pnpm dev
```

前端服务将在 `http://localhost:5173` 运行。

## API 接口

### 房间管理
- `GET /api/rooms` - 获取所有房间列表
- `POST /api/rooms` - 添加监控房间
- `PUT /api/rooms/{room_id}/start` - 开始监控
- `PUT /api/rooms/{room_id}/stop` - 停止监控

### 弹幕查询
- `GET /api/danmu` - 查询弹幕列表
- `GET /api/danmu/session/{session_id}` - 查询会话弹幕

### 会话管理
- `GET /api/sessions` - 获取会话列表
- `GET /api/sessions/{session_id}` - 获取会话详情

## WebSocket 接口

### 实时弹幕
- `ws://localhost:3001/ws/danmu` - 订阅实时弹幕

### 实时统计
- `ws://localhost:3001/ws/stats` - 订阅实时统计数据

## 使用说明

1. 启动后端和前端服务
2. 在前端页面添加要监控的 B 站直播间 ID
3. 点击"开始监控"按钮开始采集弹幕
4. 实时查看弹幕列表和频率图表
5. 查看历史会话记录

## 注意事项

- 建议配置 B 站 `SESSDATA` Cookie 以获取完整的用户信息
- 弹幕数据每 5 秒自动写入数据库
- WebSocket 连接断开后会自动重连
- 每个房间同一时间只能有一个采集会话

## License

MIT
