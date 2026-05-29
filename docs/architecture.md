# 架构说明

## 总体方向

本项目采用 Monorepo 结构，但运行时保持单体轻量部署。

```text
浏览器
  -> 静态前端资源
  -> /api 和 /ws 转发到单个 Python 后端
  -> 后端使用 SQLite 持久化房间、玩家、session token hash 和游戏状态
  -> 后端使用内存 ConnectionHub 管理当前 WebSocket 连接
```

目录上区分平台和游戏，运行上不拆微服务。

## 平台职责

平台层负责所有游戏共享的能力：

- 首页和游戏入口。
- 游戏列表。
- 6 位数字房间号。
- 创建房间、加入房间、离开房间。
- WebSocket 连接管理。
- 匿名玩家身份。
- `sessionToken` 恢复。
- 玩家断线、重连、房间 TTL 清理。
- 通用错误处理。
- 调用具体游戏模块的后端钩子。

平台层不负责具体游戏规则。

## 游戏职责

每个游戏放在 `games/<game-id>/` 下，负责：

- 游戏自己的前端界面。
- 游戏自己的状态展示。
- 游戏自己的玩家操作。
- 游戏自己的规则校验。
- 游戏自己的胜负判断。
- 游戏自己的后端事件处理。
- 游戏自己的文档和测试。

游戏模块不应该直接实现房间号、WebSocket 连接生命周期或匿名身份恢复。

## 推荐运行模型

4G 内存服务器下，早期推荐：

```text
1 个静态前端构建目录
1 个 Python 后端进程
SQLite 房间存储
内存 ConnectionHub
```

暂不引入：

- Redis
- PostgreSQL
- Celery
- 消息队列
- 多后端 worker
- 微服务
- Next.js SSR

SQLite 只负责轻量持久化，不负责跨进程实时广播或连接映射。后端早期仍应只运行一个 worker，避免不同连接落到不同进程后无法通过内存 `ConnectionHub` 正确广播。

## 第一阶段限制

当前阶段采用 SQLite 持久化房间、玩家、session token hash 和游戏状态。后端进程重启后，房间和游戏状态可以从 SQLite 恢复；实时 WebSocket 连接和 connection_id 不会恢复，客户端需要用 playerId + sessionToken 重新连接。

SQLite 解决轻量持久化，不解决跨进程 WebSocket 广播或多 worker 连接映射。因此在没有 Redis、消息队列或跨进程广播层前，后端仍建议只运行一个 worker。

`sessionToken` 只用于匿名玩家在同一房间内恢复身份，不等同于登录账号，也不提供跨设备持久身份。平台只保存 `sessionTokenHash`，不保存明文 `sessionToken`。

房间清理由平台层的 `RoomManager.cleanup_expired_rooms(...)` 执行。调用该方法时，超过 `ROOM_TTL_SECONDS` 的房间会被删除；所有玩家断线且超过 `EMPTY_ROOM_TTL_SECONDS` 的房间也会被删除。TTL 删除不会调用游戏模块钩子。当前没有后台调度器自动周期调用该方法。

## 房间模型

平台层建议维护如下概念：

```text
Room
  roomCode: string
  gameId: string
  status: waiting | playing | ended
  capacity: number
  players: Player[]
  gameState: unknown
  createdAt: datetime
  updatedAt: datetime
  expiresAt: datetime

Player
  playerId: string
  nickname: string
  sessionTokenHash: string
  connectionId: string | null
  connected: boolean
  disconnectedAt: datetime | null
  lastSeenAt: datetime
  userId: string | null
```

`gameState` 由具体游戏模块创建和更新。平台只负责保存、传递和广播。

## 人数和容量

平台硬上限固定为 30 人，用于保护轻量部署的资源边界。每个游戏仍然需要声明自己的 `minPlayers` 和 `maxPlayers`，表达该游戏规则允许的人数范围。

创建房间时，房主输入本局人数 `capacity`。平台按以下条件校验：

- `capacity` 必须是整数。
- `capacity` 不能小于游戏 `minPlayers`。
- `capacity` 不能超过游戏 `maxPlayers`。
- `capacity` 不能超过平台硬上限 30。

校验通过后，平台把本局人数保存到 `Room.capacity`。后续加入房间的有效上限是房间存储的 `capacity`，不是平台硬上限，也不是游戏 `maxPlayers`。例如游戏最多 8 人、房主创建 4 人局时，第 5 个玩家应被平台拒绝。

## 匿名身份和恢复

默认不做登录。

玩家第一次加入房间时，后端生成：

- `playerId`
- `sessionToken`

前端保存到 localStorage：

```text
game-platform.sessions[roomCode] = {
  gameId,
  playerId,
  sessionToken,
  nickname
}
```

刷新、误关闭或短暂断线后，前端重新连接，并携带 `roomCode`、`playerId`、`sessionToken`。后端验证后，把新连接重新绑定到原玩家。

## 断线重连策略

当前实现：

- WebSocket 断开后，不立刻删除玩家。
- 只要房间仍存在，且 `playerId` + `sessionToken` 校验通过，原玩家可以重连。
- 前端 WebSocket 打开后会定期发送 `{"type": "heartbeat"}`；后端用心跳更新 `lastSeenAt`。
- 当后端在后续心跳处理中发现某个已连接玩家超过 `PLAYER_ONLINE_TIMEOUT_SECONDS` 未更新 `lastSeenAt`，会将该玩家标记为断线并广播房间快照。
- 所有玩家断线后，房间可由 `RoomManager.cleanup_expired_rooms(...)` 按 `EMPTY_ROOM_TTL_SECONDS` 清理。
- 重连成功后，后端发送完整房间快照和游戏状态快照。

重连后优先发送完整状态，不依赖补发断线期间的每条事件。

每个 WebSocket 连接都会分配独立 `connection_id`。断线清理时，平台只在待清理的 `connection_id` 仍然等于玩家当前连接时才标记掉线；如果玩家已经用新连接重连，旧连接的关闭事件不会覆盖新连接状态。

`DISCONNECTED_PLAYER_TTL_SECONDS` 是预留配置，当前不删除单个断线玩家；在线状态超时由 `PLAYER_ONLINE_TIMEOUT_SECONDS` 控制。

## 游戏模块契约

平台调用游戏模块的标准钩子。概念上包括：

```text
createInitialState(roomContext)
onPlayerJoin(state, player)
onPlayerDisconnect(state, player)
onPlayerReconnect(state, player)
onPlayerLeave(state, player)
handleAction(state, player, action)
getStateSnapshot(state, viewer)
```

具体接口细节记录在 `packages/game-contract/README.md`。
