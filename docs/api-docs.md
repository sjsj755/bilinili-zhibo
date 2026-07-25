# BiliLini API 接口文档

## 概述

本文档描述 BiliLini 后端服务的所有 API 接口。BiliLini 是一个 B 站直播弹幕分析工具，提供直播间管理、弹幕采集和数据分析功能。

***

## 数据格式约定

### 通用响应格式

所有 API 接口返回统一的 JSON 格式：

```json
{
  "code": 0,
  "msg": "",
  "data": {}
}
```

| 字段   | 类型     | 必填 | 说明                  |
| ---- | ------ | -- | ------------------- |
| code | int    | 是  | 状态码，0 表示成功，非 0 表示失败 |
| msg  | string | 是  | 提示信息，成功时为空字符串       |
| data | any    | 否  | 响应数据，具体结构根据接口而定     |

### 字符编码

- 请求编码：UTF-8
- 响应编码：UTF-8

### 日期时间格式

- 格式：`YYYY-MM-DD HH:MM:SS`
- 时区：本地时区（Asia/Shanghai）

### 状态码说明

| 状态码 | 含义    | 说明                       |
| --- | ----- | ------------------------ |
| 0   | 成功    | 操作执行成功                   |
| -1  | 参数错误  | 请求参数缺失或格式不正确             |
| -2  | 资源不存在 | 请求的资源（如房间）不存在            |
| -3  | 操作失败  | 业务逻辑执行失败（如删除失败）          |
| -4  | 状态冲突  | 当前状态不允许执行该操作（如正在采集中无法删除） |

***

## 1. 健康检查

### 1.1 检查服务状态

**接口路径**：`GET /health`

**接口描述**：检查服务是否正常运行

**请求头**：无

**请求体**：无

**响应数据**：

| 字段      | 类型     | 必填 | 说明             |
| ------- | ------ | -- | -------------- |
| status  | string | 是  | 服务状态，`ok` 表示正常 |
| version | string | 是  | API 版本号        |

**成功响应示例**：

```json
{
  "status": "ok",
  "version": "1.0"
}
```

***

## 2. 直播间管理

### 2.1 获取房间列表

**接口路径**：`GET /api/rooms`

**接口描述**：获取所有已添加的直播间列表，包含弹幕统计信息

**请求头**：无

**请求体**：无

**响应数据**：

| 字段           | 类型     | 必填 | 说明                                            |
| ------------ | ------ | -- | --------------------------------------------- |
| room\_id     | int    | 是  | B 站真实房间号                                      |
| room\_name   | string | 是  | 直播间名称                                         |
| anchor\_name | string | 是  | 主播名称                                          |
| status       | string | 是  | 房间状态：`idle`（空闲）、`monitoring`（采集中）、`error`（错误） |
| error\_msg   | string | 是  | 错误信息，无错误时为空字符串                                |
| danmu\_count | int    | 是  | 该房间累计弹幕数量                                     |
| created\_at  | string | 是  | 创建时间                                          |
| updated\_at  | string | 是  | 更新时间                                          |

**成功响应示例**：

```json
{
  "code": 0,
  "msg": "",
  "data": [
    {
      "room_id": 1016,
      "room_name": "直播标题",
      "anchor_name": "主播名称",
      "status": "idle",
      "error_msg": "",
      "danmu_count": 1234,
      "created_at": "2026-07-10 10:00:00",
      "updated_at": "2026-07-10 10:00:00"
    }
  ]
}
```

***

### 2.2 添加直播间

**接口路径**：`POST /api/rooms`

**接口描述**：添加新的直播间到监控列表，支持短号自动解析

**请求头**：

| 字段           | 类型     | 必填 | 说明                     |
| ------------ | ------ | -- | ---------------------- |
| Content-Type | string | 是  | 固定为 `application/json` |

**请求体**：

| 字段     | 类型  | 必填 | 说明                      |
| ------ | --- | -- | ----------------------- |
| roomId | int | 是  | 直播间号（支持短号，系统自动解析为真实房间号） |

**请求体示例**：

```json
{
  "roomId": 115
}
```

**响应数据**：

| 字段           | 类型     | 必填 | 说明       |
| ------------ | ------ | -- | -------- |
| room\_id     | int    | 是  | B 站真实房间号 |
| room\_name   | string | 是  | 直播间名称    |
| anchor\_name | string | 是  | 主播名称     |

**成功响应示例**：

```json
{
  "code": 0,
  "msg": "添加成功",
  "data": {
    "room_id": 1016,
    "room_name": "直播标题",
    "anchor_name": "主播名称"
  }
}
```

**房间已存在响应示例**：

```json
{
  "code": 0,
  "msg": "房间已存在",
  "data": {
    "room_id": 1016,
    "room_name": "直播标题",
    "anchor_name": "主播名称"
  }
}
```

**错误响应示例**：

```json
{
  "code": -1,
  "msg": "缺少 roomId 参数",
  "data": null
}
```

***

### 2.3 获取房间详情

**接口路径**：`GET /api/rooms/{roomId}/info`

**接口描述**：获取指定直播间的详细信息

**请求头**：无

**路径参数**：

| 字段     | 类型  | 必填 | 说明       |
| ------ | --- | -- | -------- |
| roomId | int | 是  | B 站真实房间号 |

**响应数据**：

| 字段           | 类型     | 必填 | 说明                                            |
| ------------ | ------ | -- | --------------------------------------------- |
| room\_id     | int    | 是  | B 站真实房间号                                      |
| room\_name   | string | 是  | 直播间名称                                         |
| anchor\_name | string | 是  | 主播名称                                          |
| status       | string | 是  | 房间状态：`idle`（空闲）、`monitoring`（采集中）、`error`（错误） |
| error\_msg   | string | 是  | 错误信息，无错误时为空字符串                                |
| danmu\_count | int    | 是  | 该房间累计弹幕数量                                     |
| created\_at  | string | 是  | 创建时间                                          |
| updated\_at  | string | 是  | 更新时间                                          |

**成功响应示例**：

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "room_id": 1016,
    "room_name": "直播标题",
    "anchor_name": "主播名称",
    "status": "monitoring",
    "error_msg": "",
    "danmu_count": 1234,
    "created_at": "2026-07-10 10:00:00",
    "updated_at": "2026-07-10 11:00:00"
  }
}
```

**错误响应示例**：

```json
{
  "code": -1,
  "msg": "房间不存在",
  "data": null
}
```

***

### 2.4 开始采集

**接口路径**：`POST /api/rooms/{roomId}/monitor`

**接口描述**：开始采集指定直播间的弹幕

**请求头**：无

**路径参数**：

| 字段     | 类型  | 必填 | 说明       |
| ------ | --- | -- | -------- |
| roomId | int | 是  | B 站真实房间号 |

**响应数据**：无

**成功响应示例**：

```json
{
  "code": 0,
  "msg": "开始采集",
  "data": null
}
```

**已在采集中响应示例**：

```json
{
  "code": 0,
  "msg": "已在采集中",
  "data": null
}
```

**错误响应示例**：

```json
{
  "code": -1,
  "msg": "房间不存在",
  "data": null
}
```

***

### 2.5 停止采集

**接口路径**：`POST /api/rooms/{roomId}/monitor/stop`

**接口描述**：停止采集指定直播间的弹幕

**请求头**：无

**路径参数**：

| 字段     | 类型  | 必填 | 说明       |
| ------ | --- | -- | -------- |
| roomId | int | 是  | B 站真实房间号 |

**响应数据**：无

**成功响应示例**：

```json
{
  "code": 0,
  "msg": "停止采集",
  "data": null
}
```

**当前未在采集响应示例**：

```json
{
  "code": 0,
  "msg": "当前未在采集",
  "data": null
}
```

**错误响应示例**：

```json
{
  "code": -1,
  "msg": "房间不存在",
  "data": null
}
```

***

### 2.6 删除房间

**接口路径**：`DELETE /api/rooms/{roomId}`

**接口描述**：从监控列表中删除指定直播间

**请求头**：无

**路径参数**：

| 字段     | 类型  | 必填 | 说明       |
| ------ | --- | -- | -------- |
| roomId | int | 是  | B 站真实房间号 |

**响应数据**：无

**成功响应示例**：

```json
{
  "code": 0,
  "msg": "删除成功",
  "data": null
}
```

**错误响应示例**：

```json
{
  "code": -1,
  "msg": "房间不存在",
  "data": null
}
```

```json
{
  "code": -1,
  "msg": "请先停止采集再删除",
  "data": null
}
```

***

## 3. 弹幕查询

### 3.1 获取弹幕列表

**接口路径**：`GET /api/danmu/{roomId}`

**接口描述**：获取指定直播间的弹幕记录列表，支持分页。按时间戳倒序排列（最新的在前）。

**请求头**：无

**路径参数**：

| 字段     | 类型  | 必填 | 说明       |
| ------ | --- | -- | -------- |
| roomId | int | 是  | B 站真实房间号 |

**查询参数**：

| 字段       | 类型  | 必填 | 默认值 | 说明          |
| -------- | --- | -- | --- | ----------- |
| page     | int | 否  | 1   | 页码，从 1 开始   |
| pageSize | int | 否  | 50  | 每页条数，最大 200 |

**响应数据**：

| 字段       | 类型    | 必填 | 说明   |
| -------- | ----- | -- | ---- |
| list     | array | 是  | 弹幕列表 |
| total    | int   | 是  | 总弹幕数 |
| page     | int   | 是  | 当前页码 |
| pageSize | int   | 是  | 每页条数 |

**列表项字段**：

| 字段           | 类型     | 必填 | 说明                              |
| ------------ | ------ | -- | ------------------------------- |
| id           | int    | 是  | 弹幕记录自增 ID                       |
| room\_id     | int    | 是  | B 站真实房间号                        |
| uid          | int    | 是  | 用户 ID，0 表示匿名用户                  |
| username     | string | 是  | 用户名                             |
| content      | string | 是  | 弹幕内容                            |
| timestamp    | int    | 是  | 发送时间戳（毫秒）                       |
| medal\_level | int    | 否  | 粉丝勋章等级，无勋章时为 null               |
| medal\_name  | string | 否  | 粉丝勋章名称，无勋章时为 null               |
| user\_level  | int    | 否  | 用户等级，未知时为 null                  |
| is\_gift     | bool   | 是  | 是否为礼物弹幕，默认 false                |
| created\_at  | string | 是  | 记录创建时间，格式 `YYYY-MM-DD HH:MM:SS` |

**成功响应示例**：

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "list": [
      {
        "id": 12345,
        "room_id": 1016,
        "uid": 123456,
        "username": "用户名",
        "content": "弹幕内容",
        "timestamp": 1717100000000,
        "medal_level": 10,
        "medal_name": "勋章名称",
        "user_level": 5,
        "is_gift": false,
        "created_at": "2026-07-10 10:30:00"
      }
    ],
    "total": 1000,
    "page": 1,
    "pageSize": 50
  }
}
```

**无数据响应示例**：

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "list": [],
    "total": 0,
    "page": 1,
    "pageSize": 50
  }
}
```

***

### 3.2 获取弹幕统计

**接口路径**：`GET /api/danmu/{roomId}/stats`

**接口描述**：获取指定直播间的弹幕统计信息

**请求头**：无

**路径参数**：

| 字段     | 类型  | 必填 | 说明       |
| ------ | --- | -- | -------- |
| roomId | int | 是  | B 站真实房间号 |

**响应数据**：

| 字段            | 类型     | 必填 | 说明                          |
| ------------- | ------ | -- | --------------------------- |
| total\_count  | int    | 是  | 总弹幕数                        |
| unique\_users | int    | 是  | 发送弹幕的独立用户数                  |
| peak\_hour    | string | 是  | 弹幕高峰时段（如 "20:00"），无数据时为空字符串 |
| peak\_count   | int    | 是  | 高峰时段弹幕数                     |

**成功响应示例**：

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "total_count": 10000,
    "unique_users": 500,
    "peak_hour": "20:00",
    "peak_count": 500
  }
}
```

**无数据响应示例**：

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "total_count": 0,
    "unique_users": 0,
    "peak_hour": "",
    "peak_count": 0
  }
}
```

***

## 4. WebSocket 实时消息推送

### 4.1 连接实时消息

**端点路径**：`WS /ws`

**接口描述**：建立 WebSocket 连接，实时接收弹幕、分析数据等推送消息。支持通过 `subscribe` / `unsubscribe` 消息订阅/取消订阅指定直播间，一个连接可同时订阅多个房间。

**查询参数**：

| 参数     | 类型  | 必填 | 说明                                    |
| ------ | --- | -- | ------------------------------------- |
| roomId | int | 否  | 可选，连接建立后自动订阅该房间；不传则需手动发送 subscribe 消息 |

**连接示例**：

```
ws://localhost:3001/ws
ws://localhost:3001/ws?roomId=1016
```

**连接成功响应**：

```json
{ "type": "connected" }
```

***

### 4.2 客户端 → 服务端消息

#### 4.2.1 订阅房间

订阅指定直播间的实时消息，订阅成功后该房间的弹幕、分析数据等会主动推送过来。

```json
{ "type": "subscribe", "roomId": 1016 }
```

**字段说明**：

| 字段     | 类型  | 必填 | 说明              |
| ------ | --- | -- | --------------- |
| type   | str | 是  | 固定为 `subscribe` |
| roomId | int | 是  | B 站真实房间号        |

**服务端响应**：

```json
{ "type": "subscribed", "roomId": 1016 }
```

***

#### 4.2.2 取消订阅房间

取消订阅指定直播间，取消后不再接收该房间的推送消息。

```json
{ "type": "unsubscribe", "roomId": 1016 }
```

**字段说明**：

| 字段     | 类型  | 必填 | 说明                |
| ------ | --- | -- | ----------------- |
| type   | str | 是  | 固定为 `unsubscribe` |
| roomId | int | 是  | B 站真实房间号          |

**服务端响应**：

```json
{ "type": "unsubscribed", "roomId": 1016 }
```

***

#### 4.2.3 心跳

客户端可主动发送心跳消息，服务端接收后不回复（心跳由服务端主动发送）。

```json
{ "type": "heartbeat" }
```

***

### 4.3 服务端 → 客户端消息

#### 4.3.1 连接成功

```json
{ "type": "connected" }
```

***

#### 4.3.2 订阅成功 / 取消订阅成功

```json
{ "type": "subscribed", "roomId": 1016 }
{ "type": "unsubscribed", "roomId": 1016 }
```

***

#### 4.3.3 弹幕推送

当订阅的直播间有新弹幕时推送，每秒最多推送 10 条（节流）。

```json
{
  "type": "danmu",
  "data": {
    "room_id": 1016,
    "uid": 123456,
    "username": "用户名",
    "content": "弹幕内容",
    "timestamp": 1717100000000,
    "medal_level": 10,
    "medal_name": "勋章名称",
    "user_level": 5,
    "is_gift": false
  }
}
```

**data 字段说明**：

| 字段           | 类型     | 必填 | 说明                |
| ------------ | ------ | -- | ----------------- |
| room\_id     | int    | 是  | B 站真实房间号          |
| uid          | int    | 是  | 用户 ID，0 表示匿名用户    |
| username     | string | 是  | 用户名（可能被脱敏处理）      |
| content      | string | 是  | 弹幕内容              |
| timestamp    | int    | 是  | 发送时间戳（毫秒）         |
| medal\_level | int    | 否  | 粉丝勋章等级，无勋章时为 null |
| medal\_name  | string | 否  | 粉丝勋章名称，无勋章时为 null |
| user\_level  | int    | 否  | 用户等级，未知时为 null    |
| is\_gift     | bool   | 是  | 是否为礼物弹幕，默认 false  |

***

#### 4.3.4 实时分析数据推送（P2 阶段）✅

服务端每秒推送一次实时分析数据，包含频率、情感和关键词三个维度。

```json
{
  "type": "realtime_stats",
  "data": [
    {
      "room_id": 1016,
      "timestamp": 1717100000.0,
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
        "top_k": [
          {"word": "主播", "count": 50, "frequency": 0.1},
          {"word": "弹幕", "count": 30, "frequency": 0.06}
        ],
        "total_count": 500,
        "window_start": 1599999940.0,
        "window_end": 1620000000.0
      }
    }
  ]
}
```

**data 字段说明**：

| 字段        | 类型     | 必填 | 说明       |
| --------- | ------ | -- | -------- |
| room\_id  | int    | 是  | B 站真实房间号 |
| timestamp | float  | 是  | 当前时间戳（秒） |
| frequency | object | 是  | 频率统计数据   |
| sentiment | object | 是  | 情感统计数据   |
| keywords  | object | 是  | 关键词统计数据  |

**frequency 字段说明**：

| 字段            | 类型    | 必填 | 说明         |
| ------------- | ----- | -- | ---------- |
| frequency     | float | 是  | 当前频率（弹幕/秒） |
| count         | int   | 是  | 窗口内弹幕数     |
| total\_count  | int   | 是  | 累计弹幕总数     |
| window\_start | float | 是  | 窗口起始时间戳    |
| window\_end   | float | 是  | 窗口结束时间戳    |

**sentiment 字段说明**：

| 字段              | 类型    | 必填 | 说明      |
| --------------- | ----- | -- | ------- |
| positive\_count | int   | 是  | 正面情感弹幕数 |
| negative\_count | int   | 是  | 负面情感弹幕数 |
| neutral\_count  | int   | 是  | 中性情感弹幕数 |
| total\_count    | int   | 是  | 窗口内弹幕总数 |
| positive\_rate  | float | 是  | 正面情感占比  |
| negative\_rate  | float | 是  | 负面情感占比  |
| neutral\_rate   | float | 是  | 中性情感占比  |

**keywords 字段说明**：

| 字段            | 类型    | 必填 | 说明          |
| ------------- | ----- | -- | ----------- |
| top\_k        | array | 是  | Top K 关键词列表 |
| total\_count  | int   | 是  | 窗口内分词总数     |
| window\_start | float | 是  | 窗口起始时间戳     |
| window\_end   | float | 是  | 窗口结束时间戳     |

**top\_k 列表项字段说明**：

| 字段        | 类型     | 必填 | 说明   |
| --------- | ------ | -- | ---- |
| word      | string | 是  | 关键词  |
| count     | int    | 是  | 出现次数 |
| frequency | float  | 是  | 频率占比 |

***

#### 4.3.5 连接错误通知

当某个订阅房间的采集连接发生异常时推送。

```json
{
  "type": "connection_error",
  "data": {
    "room_id": 1016,
    "message": "连接断开，正在重连..."
  }
}
```

***

#### 4.3.6 心跳

服务端每 25 秒向所有活跃连接发送心跳消息，客户端可据此判断连接是否存活。

```json
{ "type": "heartbeat" }
```

***

#### 4.3.7 错误消息

当客户端发送格式错误或未知类型的消息时，服务端返回错误提示。

```json
{ "type": "error", "message": "未知消息类型: xxx" }
```

***

### 4.4 消息类型汇总

| 类型                 | 方向        | 说明           |
| ------------------ | --------- | ------------ |
| `connected`        | 服务端 → 客户端 | 连接成功         |
| `subscribe`        | 客户端 → 服务端 | 订阅房间         |
| `subscribed`       | 服务端 → 客户端 | 订阅成功确认       |
| `unsubscribe`      | 客户端 → 服务端 | 取消订阅         |
| `unsubscribed`     | 服务端 → 客户端 | 取消订阅确认       |
| `danmu`            | 服务端 → 客户端 | 弹幕推送         |
| `realtime_stats`   | 服务端 → 客户端 | 实时分析数据推送（P2） |
| `connection_error` | 服务端 → 客户端 | 采集连接错误通知     |
| `heartbeat`        | 双向        | 心跳保活         |
| `error`            | 服务端 → 客户端 | 客户端消息错误      |

***

## 附录：房间状态说明

| 状态值        | 说明           |
| ---------- | ------------ |
| idle       | 空闲状态，未在采集    |
| monitoring | 采集中，正在接收弹幕   |
| error      | 采集出错，需检查错误信息 |

***

## 5. 采集会话管理

### 5.1 获取会话列表

**接口路径**：`GET /api/sessions/{roomId}`

**接口描述**：获取指定直播间的所有采集会话列表，按开始时间倒序排列

**请求头**：无

**路径参数**：

| 字段     | 类型  | 必填 | 说明       |
| ------ | --- | -- | -------- |
| roomId | int | 是  | B 站真实房间号 |

**响应数据**：

| 字段           | 类型     | 必填 | 说明                                  |
| ------------ | ------ | -- | ----------------------------------- |
| id           | int    | 是  | 会话自增 ID                             |
| room\_id     | int    | 是  | B 站真实房间号                            |
| status       | string | 是  | 会话状态：`active`（采集中）、`completed`（已结束） |
| start\_time  | string | 是  | 采集开始时间，格式 `YYYY-MM-DD HH:MM:SS`     |
| end\_time    | string | 是  | 采集结束时间，未结束时为空字符串                    |
| danmu\_count | int    | 是  | 该会话的弹幕数量                            |
| created\_at  | string | 是  | 记录创建时间                              |

**成功响应示例**：

```json
{
  "code": 0,
  "msg": "",
  "data": [
    {
      "id": 1,
      "room_id": 1016,
      "status": "completed",
      "start_time": "2026-07-12 22:34:00",
      "end_time": "2026-07-12 22:36:00",
      "danmu_count": 13,
      "created_at": "2026-07-12 22:34:00"
    }
  ]
}
```

***

### 5.2 获取会话详情

**接口路径**：`GET /api/sessions/{roomId}/{sessionId}`

**接口描述**：获取指定采集会话的详细信息和弹幕列表

**请求头**：无

**路径参数**：

| 字段        | 类型  | 必填 | 说明       |
| --------- | --- | -- | -------- |
| roomId    | int | 是  | B 站真实房间号 |
| sessionId | int | 是  | 会话 ID    |

**响应数据**：

| 字段        | 类型     | 必填 | 说明       |
| --------- | ------ | -- | -------- |
| session   | object | 是  | 会话详情     |
| danmuList | array  | 是  | 该会话的弹幕列表 |

**成功响应示例**：

```json
{
  "code": 0,
  "msg": "",
  "data": {
    "session": {
      "id": 1,
      "room_id": 1016,
      "status": "completed",
      "start_time": "2026-07-12 22:34:00",
      "end_time": "2026-07-12 22:36:00",
      "danmu_count": 13,
      "created_at": "2026-07-12 22:34:00"
    },
    "danmuList": [
      {
        "id": 12345,
        "room_id": 1016,
        "uid": 123456,
        "username": "用户名",
        "content": "弹幕内容",
        "timestamp": 1717100000000,
        "medal_level": 10,
        "medal_name": "勋章名称",
        "user_level": 5,
        "is_gift": false,
        "created_at": "2026-07-12 22:34:05"
      }
    ]
  }
}
```

**错误响应示例**：

```json
{
  "code": -2,
  "msg": "会话不存在",
  "data": null
}
```

***

### 5.3 删除会话

**接口路径**：`DELETE /api/sessions/{roomId}/{sessionId}`

**接口描述**：删除指定采集会话，正在进行的会话无法删除

**请求头**：无

**路径参数**：

| 字段        | 类型  | 必填 | 说明       |
| --------- | --- | -- | -------- |
| roomId    | int | 是  | B 站真实房间号 |
| sessionId | int | 是  | 会话 ID    |

**响应数据**：无

**成功响应示例**：

```json
{
  "code": 0,
  "msg": "删除成功",
  "data": null
}
```

**错误响应示例**：

```json
{
  "code": -4,
  "msg": "无法删除正在进行的会话",
  "data": null
}
```

***

### 5.4 会话状态说明

| 状态值       | 说明       |
| --------- | -------- |
| active    | 正在采集，未结束 |
| completed | 已结束，采集停止 |

***

## 6. 前端架构说明

### 6.1 技术栈

| 类别   | 技术           | 版本  | 用途           |
| ---- | ------------ | --- | ------------ |
| 框架   | React        | 18+ | UI 组件开发      |
| 语言   | TypeScript   | 5+  | 类型安全         |
| 构建工具 | Vite         | 6+  | 快速开发构建       |
| 样式   | TailwindCSS  | 3+  | CSS 样式框架     |
| 路由   | React Router | 6+  | 单页应用路由       |
| 图标   | Lucide React | -   | UI 图标组件      |
| 数据请求 | Axios        | -   | HTTP 请求      |
| 图表   | ECharts      | 5+  | 数据可视化（P2 阶段） |

### 6.2 项目结构

```
frontend/src/
├── components/          # 公共组件
│   ├── Sidebar.tsx      # 侧边栏导航 + 房间列表
│   ├── RoomList.tsx     # 房间列表容器
│   ├── RoomItem.tsx     # 单个房间项组件
│   ├── AddRoomModal.tsx # 添加房间弹窗
│   └── HistoryCard.tsx  # 采集历史卡片组件
├── hooks/               # 自定义 Hooks
│   ├── useDanmaku.ts    # 弹幕管理（WebSocket + 历史加载 + 采集会话）
│   └── useRoom.ts       # 房间管理（API + 定时刷新）
├── pages/               # 页面组件
│   ├── Dashboard.tsx    # 首页仪表盘
│   └── RoomDetail.tsx   # 直播间详情页（弹幕墙）
├── services/            # API 服务
│   ├── api.ts           # 基础请求封装
│   ├── room.ts          # 房间相关 API
│   ├── danmu.ts         # 弹幕相关 API
│   └── session.ts       # 采集会话相关 API
├── types/               # 类型定义
│   └── index.ts         # 全局类型
├── context/             # React Context
│   └── WebSocketContext.tsx # WebSocket 连接管理
└── App.tsx              # 应用入口
```

### 6.3 核心组件说明

| 组件               | 职责           | 关键特性                         |
| ---------------- | ------------ | ---------------------------- |
| **Sidebar**      | 侧边栏导航 + 房间管理 | React Router 导航、路由高亮、房间列表操作  |
| **RoomList**     | 房间列表展示       | 加载/空状态处理、滚动容器                |
| **RoomItem**     | 单个房间卡片       | 状态指示器、开始/停止/删除操作             |
| **AddRoomModal** | 添加房间弹窗       | 输入验证、错误提示                    |
| **Dashboard**    | 首页仪表盘        | 统计卡片、房间列表、图表区域               |
| **RoomDetail**   | 直播间详情        | 固定高度弹幕墙、实时/历史弹幕区分、新弹幕提示、自动滚动 |
| **HistoryCard**  | 采集历史卡片       | 会话列表、时间标注、弹幕统计、点击跳转          |

### 6.4 自定义 Hooks 说明

| Hook           | 职责     | 关键特性                                                                            |
| -------------- | ------ | ------------------------------------------------------------------------------- |
| **useDanmaku** | 弹幕数据管理 | WebSocket 连接、自动重连、节流渲染（100ms）、历史/实时弹幕区分、最大缓存 1000 条、自动订阅/取消订阅、采集会话管理、自动滚动、新弹幕提示 |
| **useRoom**    | 房间数据管理 | API 请求、5 秒定时刷新、数据深比较优化（排除 danmu\_count）、加载状态管理、操作反馈（开始/停止/删除）                   |

### 6.5 WebSocket 客户端封装

前端通过 `context/WebSocketContext.tsx` 中的 `WebSocketProvider` 封装 WebSocket 连接：

- **连接管理**：按需连接（订阅时自动连接）、断开旧连接避免重复连接、指数退避重连
- **消息处理**：弹幕消息通过回调函数分发，支持多房间独立处理
- **订阅机制**：`subscribe(roomId, callback)` / `unsubscribe(roomId, callback)`，同一房间支持多个回调
- **心跳保活**：服务端 25 秒心跳，连接断开自动重连并恢复订阅
- **开发环境**：使用相对路径 `/ws`，利用 Vite 代理配置转发到后端

### 6.6 状态管理策略

| 策略          | 应用场景   | 说明                                                  |
| ----------- | ------ | --------------------------------------------------- |
| React.memo  | 组件级优化  | Dashboard、RoomDetail、RoomItem 等组件使用，减少不必要重渲染        |
| useMemo     | 计算属性缓存 | Dashboard 统计数据、房间列表深比较                              |
| useCallback | 函数引用稳定 | 回调函数（handleDanmu、fetchRooms）稳定化，避免子组件重渲染            |
| useRef      | 回调引用存储 | useDanmaku 中使用 ref 存储 handleDanmu，避免函数引用变化导致重复订阅    |
| 节流渲染        | 弹幕列表更新 | 100ms 批量更新 DOM，避免高频率弹幕导致的卡顿                         |
| 数据深比较       | 房间列表更新 | useRoom 中使用 roomsEqual 函数深比较，排除 danmu\_count 避免频繁更新 |

### 6.7 路由配置

| 路径              | 页面         | 说明                 |
| --------------- | ---------- | ------------------ |
| `/`             | Dashboard  | 首页仪表盘              |
| `/dashboard`    | Dashboard  | 首页仪表盘（别名）          |
| `/room/:roomId` | RoomDetail | 直播间详情页（弹幕墙 + 采集历史） |

### 6.8 前端类型定义

**Room 类型**（`types/index.ts`）：

| 字段           | 类型     | 必填 | 说明                               |
| ------------ | ------ | -- | -------------------------------- |
| room\_id     | number | 是  | B 站真实房间号                         |
| room\_name   | string | 是  | 直播间名称                            |
| anchor\_name | string | 是  | 主播名称                             |
| status       | string | 是  | 房间状态：`idle`/`monitoring`/`error` |
| error\_msg   | string | 是  | 错误信息，无错误时为空字符串                   |
| danmu\_count | number | 是  | 累计弹幕数量                           |
| created\_at  | string | 是  | 创建时间                             |
| updated\_at  | string | 是  | 更新时间                             |

**DanmuRecord 类型**（`types/index.ts`）：

| 字段           | 类型     | 必填 | 说明                     |
| ------------ | ------ | -- | ---------------------- |
| id           | number | 否  | 弹幕记录自增 ID              |
| room\_id     | number | 是  | B 站真实房间号               |
| uid          | number | 是  | 用户 ID，0 表示匿名用户         |
| username     | string | 是  | 用户名                    |
| content      | string | 是  | 弹幕内容                   |
| timestamp    | number | 是  | 发送时间戳（毫秒）              |
| created\_at  | string | 否  | 记录创建时间                 |
| medal\_level | number | 否  | 粉丝勋章等级，无勋章时为 undefined |
| medal\_name  | string | 否  | 粉丝勋章名称，无勋章时为 undefined |
| user\_level  | number | 否  | 用户等级，未知时为 undefined    |

