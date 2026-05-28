# 架构说明

## 总体方向

本项目采用 Monorepo 结构，但运行时保持单体轻量部署。

```text
浏览器
  -> 静态前端资源
  -> /api 和 /ws 转发到单个 Python 后端
  -> 后端使用内存管理实时房间
  -> SQLite 保存轻量恢复信息
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
1 个 SQLite 数据库文件
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

## 房间模型

平台层建议维护如下概念：

```text
Room
  roomCode: string
  gameId: string
  status: waiting | playing | ended
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

