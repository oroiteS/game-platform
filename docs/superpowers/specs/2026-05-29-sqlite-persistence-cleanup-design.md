# SQLite 持久化与房间清理设计

## 目标

把平台从进程内房间状态推进到轻量 SQLite 持久化，同时保持当前单后端进程运行模型、REST API、WebSocket 消息 envelope、匿名身份模型和游戏模块契约稳定。

## 当前上下文

当前后端把所有房间保存在 `RoomManager._rooms`。`RoomManager` 负责平台规则、房间生命周期、匿名 session 校验、WebSocket 重连行为，并调用游戏模块钩子。Flask 路由和 WebSocket 代码都已经只依赖 `RoomManager` 这个边界，这个公开入口应保持不变。

当前游戏契约把 `game_state` 视为平台保存和传递的不透明数据。`lobby-demo` 的状态是 JSON 兼容结构，但平台尚未强制校验游戏状态可 JSON 序列化。

## 推荐方案

在 `RoomManager` 下方增加一个小型存储层。

`RoomManager` 继续负责：

- 游戏注册表查询。
- 昵称、房间号和容量校验。
- 创建房间、加入房间、重连、断线和游戏动作编排。
- 调用游戏模块钩子。
- 返回公开房间快照和游戏快照。

存储层负责：

- 创建 SQLite schema。
- 持久化和加载 `Room`、`Player`、`game_state`。
- 序列化和反序列化 datetime 与 JSON 游戏状态。
- 删除过期房间及其关联数据。

这样数据库细节不会进入游戏模块、Flask 路由或 WebSocket 处理器。

## 存储模型

使用 Python 标准库 `sqlite3`，不新增依赖。

表结构：

```text
rooms
  room_code text primary key
  game_id text not null
  status text not null
  capacity integer not null
  created_at text not null
  updated_at text not null
  expires_at text null

players
  player_id text primary key
  room_code text not null references rooms(room_code) on delete cascade
  nickname text not null
  session_token_hash text not null
  connected integer not null
  disconnected_at text null
  last_seen_at text not null

game_state
  room_code text primary key references rooms(room_code) on delete cascade
  state_json text not null
  updated_at text not null
```

本轮不单独创建 `sessions` 表。当前平台模型是一名匿名玩家在一个房间内绑定一个 session token hash；把 `session_token_hash` 保存在 `players` 上可以保持现有行为，也避免增加暂时没有独立职责的抽象。

不持久化：

- 明文 `sessionToken`。
- WebSocket 对象。
- `connection_id`。

## 运行配置

新增后端配置：

- `SQLITE_DB_PATH`：SQLite 数据库文件路径。开发环境默认位于 `apps/api/var/` 下。
- `ROOM_TTL_SECONDS`：房间按最后更新时间保留的默认时长。
- `EMPTY_ROOM_TTL_SECONDS`：所有玩家断线后房间继续保留的时长。
- `DISCONNECTED_PLAYER_TTL_SECONDS`：断线玩家允许恢复的时间窗口。
- `ROOM_CLEANUP_ENABLED`：预留配置，默认关闭；当前没有后台调度器自动执行清理。
- `ROOM_CLEANUP_INTERVAL_SECONDS`：预留配置，当前没有后台调度器读取该间隔。

实现优先提供可确定调用的 `cleanup_expired_rooms(now=...)` 方法并直接测试。后台清理循环暂不加入；后续如果加入，也只调用同一个确定性的清理方法。

## 重启恢复语义

后端重启后：

- 房间、玩家、session token hash 和游戏状态从 SQLite 加载。
- 所有玩家初始视为断线，因为实时 WebSocket 连接无法跨进程重启恢复。
- `connection_id` 始终为 `None`。
- 客户端可以用 `roomCode`、`playerId`、`sessionToken` 恢复匿名身份。
- 重连成功后，平台调用游戏模块 `on_player_reconnect` 钩子，并广播完整快照。

`mark_disconnected` 的旧连接保护必须保留：旧连接关闭事件不能覆盖已经由新连接接管的玩家状态。

## 清理语义

新增确定性的清理行为：

- 过期房间会从 `rooms`、`players`、`game_state` 删除。
- 所有玩家断线且超过 `EMPTY_ROOM_TTL_SECONDS` 的房间过期。
- `updated_at` 距今超过 `ROOM_TTL_SECONDS` 的房间过期。
- 最近活跃的房间和仍有在线玩家的房间保留。
- TTL 到期删除是平台级生命周期行为，本轮不调用游戏模块钩子。

这让清理策略可预测，也避免在真正有游戏需要前新增游戏生命周期契约。

## JSON 状态规则

被持久化的 `game_state` 必须可 JSON 序列化。如果游戏返回不可序列化状态，平台应在保存时快速失败，并给出清晰的存储错误。游戏契约文档需要说明：平台持久化要求游戏状态保持 JSON 兼容。

## 测试策略

实现阶段使用 TDD。

后端测试使用 pytest `tmp_path` 创建临时 SQLite 文件，避免污染项目目录。

必须覆盖：

- 创建房间会持久化房间、房主玩家、session token hash 和初始游戏状态。
- 加入房间会持久化新玩家，并保持容量限制。
- 新 `RoomManager` 使用同一个 SQLite 文件时可以加载已有房间。
- `lobby-demo` 消息历史在 manager 重启后仍存在。
- 重启后使用原客户端保存的 `sessionToken` 可以重连。
- 明文 `sessionToken` 不会被保存。
- 清理会删除过期房间及其关联数据。
- 清理会保留未过期房间和仍有在线玩家的房间。
- 现有路由、WebSocket、房间管理、session token、`lobby-demo` 测试仍通过。

验证命令：

```bash
cd apps/api && uv run pytest -v
```

## 文档更新

更新：

- `README.md`：把内存状态存储描述改为 SQLite 持久化加内存连接管理。
- `docs/architecture.md`：说明 SQLite 持久化、重启恢复、清理策略，以及仍保留单进程 WebSocket 限制。
- `docs/deployment.md`：说明 SQLite 文件路径、目录权限、备份，以及 SQLite 不解决跨进程 WebSocket 广播。
- `docs/development.md`：补充存储层和清理测试建议。
- `apps/api/README.md`：记录后端配置和验证命令。
- `packages/game-contract/README.md`：说明被持久化的游戏状态必须可 JSON 序列化。
- `docs/add-new-game.md`：说明游戏不直接访问 SQLite 或平台 session 存储。

## 非目标

- 不引入 Redis、PostgreSQL、SQLAlchemy、Celery 或消息队列。
- 不支持多个后端 worker 承载实时 WebSocket 房间。
- 不修改 REST 响应结构或 WebSocket 消息 envelope。
- 不修改前端 localStorage session 格式。
- 不增加登录或跨设备持久身份。
- 不为房间清理新增游戏生命周期钩子。
