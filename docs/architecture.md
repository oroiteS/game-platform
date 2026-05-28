# 架构说明

## 总体方向

本项目采用 Monorepo 结构，但运行时保持单体轻量部署。

```text
浏览器
  -> 静态前端资源
  -> /api 和 /ws 转发到单个 Python 后端
  -> 后端使用内存管理实时房间
  -> 第一阶段匿名 session 跟随内存房间保存
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
- 玩家断线、重连、超时清理。
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
内存 RoomManager
```

暂不引入：

- Redis
- PostgreSQL
- Celery
- 消息队列
- 多后端 worker
- 微服务
- Next.js SSR

如果房间状态保存在内存中，后端早期应只运行一个 worker。多 worker 会导致不同连接落到不同进程，房间状态不一致。

## 第一阶段限制

第一阶段采用内存 `RoomManager` 管理房间和游戏状态。`sessionToken` 只用于匿名玩家在同一房间内恢复身份，不等同于登录账号，也不提供跨设备持久身份。

当前房间状态保存在单个后端进程内存中。后端进程重启、部署替换或崩溃后，已有房间和游戏状态会丢失；玩家需要重新创建房间。早期不引入 Redis、PostgreSQL、消息队列或多 worker 来同步房间状态。

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

建议默认规则：

- WebSocket 断开后，不立刻删除玩家。
- 断线后 60 秒内，房间显示玩家掉线。
- 断线后 10 分钟内，允许原玩家恢复。
- 超过恢复窗口，平台触发正式离开。
- 所有玩家断线后，房间保留 10 到 30 分钟。
- 重连成功后，后端发送完整房间快照和游戏状态快照。

重连后优先发送完整状态，不依赖补发断线期间的每条事件。

每个 WebSocket 连接都会分配独立 `connection_id`。断线清理时，平台只在待清理的 `connection_id` 仍然等于玩家当前连接时才标记掉线；如果玩家已经用新连接重连，旧连接的关闭事件不会覆盖新连接状态。

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
