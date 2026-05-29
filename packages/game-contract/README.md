# Game Contract

本目录记录平台和游戏模块之间的契约。

当前文件是契约草案，后续实现时应将这些概念落成 TypeScript 类型和 Python 类型。

## 游戏元信息

每个游戏需要提供前端元信息：

```ts
export const gameConfig = {
  id: "example-game",
  name: "示例游戏",
  summary: "一句话说明游戏目标和体验。",
  rules: "面向玩家展示的规则说明。",
  minPlayers: 1,
  maxPlayers: 4,
  load: () => import("./web/GameApp"),
};
```

`id` 应只使用小写字母、数字和连字符。

`summary` 显示在 Games 目录和游戏列表中，应短而明确。`rules` 显示在游戏规则详情弹窗中，支持 HTML——可以直接写富文本（列表、表格、强调色等），平台用 `dangerouslySetInnerHTML` 渲染。样式默认继承平台 CSS 变量，也可以内联 style 覆盖。

## 人数和容量

平台有独立硬上限 30 人。游戏通过 `minPlayers` 和 `maxPlayers` 声明规则允许的人数范围。

创建房间时，客户端提交本局请求人数：

```json
{
  "gameId": "example-game",
  "nickname": "Ada",
  "capacity": 4
}
```

平台校验 `capacity` 是整数，且位于 `minPlayers` 到 `min(30, maxPlayers)` 之间。校验通过后，房间保存 `capacity`，后续加入人数上限以该房间值为准。

## 后端钩子

每个游戏后端需要实现以下概念：

```text
createInitialState(roomContext) -> gameState
onPlayerJoin(gameState, player) -> GameResult
onPlayerDisconnect(gameState, player) -> GameResult
onPlayerReconnect(gameState, player) -> GameResult
onPlayerLeave(gameState, player) -> GameResult
handleAction(gameState, player, action) -> GameResult
getStateSnapshot(gameState, viewer) -> dict
```

## GameResult

游戏后端处理结果建议包含：

```text
status: accepted | rejected | noop
state: unknown
errorCode: string | null
publicEvents: list
privateEvents: list
```

平台负责把结果广播给客户端，游戏模块不直接操作连接。

`status` 语义：

- `accepted`：操作有效，状态已更新或可继续广播。
- `rejected`：操作无效，平台向发起方发送错误。
- `noop`：操作有效但状态不变。

## Action

客户端发给后端的操作建议统一为：

```json
{
  "type": "action_name",
  "payload": {}
}
```

具体 `type` 和 `payload` 由每个游戏在自己的 `shared/` 和 `README.md` 中说明。

当前 WebSocket 客户端消息 envelope 已落地为：

```json
{
  "type": "game_action",
  "action": {
    "type": "action_name",
    "payload": {}
  }
}
```

平台客户端还会发送心跳消息：

```json
{
  "type": "heartbeat"
}
```

心跳只用于平台层更新玩家在线状态，不会进入游戏模块的 `handleAction`。

## Snapshot

重连后平台会调用游戏的 `getStateSnapshot`，把当前完整状态发送给客户端。

平台可能把 `gameState` 持久化到 SQLite，因此游戏状态必须保持 JSON 可序列化。游戏模块不应依赖进程内对象身份、文件句柄、连接对象或其他不可序列化状态。

快照应满足：

- 足够恢复 UI。
- 不泄露不该给当前玩家看到的信息。
- 可以被 JSON 序列化。

当前服务端消息 envelope 已落地为：

```json
{
  "type": "room_snapshot",
  "room": {
    "roomCode": "123456",
    "gameId": "example-game",
    "status": "waiting",
    "capacity": 4,
    "players": []
  },
  "game": {}
}
```

错误消息 envelope：

```json
{
  "type": "error",
  "code": "invalid_message",
  "message": "Message must be valid JSON."
}
```
