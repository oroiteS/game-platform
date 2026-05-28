# lobby-demo

`lobby-demo` 是平台闭环占位游戏，用于验证房间、玩家加入、断线重连、动作处理和公开状态快照的后端链路。

公开游戏 ID 使用 `lobby-demo`。Python 后端导入包使用 `games.lobby_demo`，避免连字符目录无法作为 Python 包导入的问题。

## 玩法和规则

玩家加入同一个大厅，共享一条房间消息。任意已加入玩家都可以提交新消息，后端校验后更新全房间公开快照。该 demo 没有胜负条件，主要用于验证平台最小闭环。

人数范围为 1 到 30 人。创建房间时房主仍需输入本局人数，实际加入上限以房间保存的 `capacity` 为准。

`summary` 用于 Games 目录中的简短说明；`rules` 用于规则详情，说明本 demo 的共享消息、连接状态和人数范围。

## 后端 Action

客户端发送的 action 格式：

```json
{
  "type": "set_message",
  "payload": {
    "message": "hello"
  }
}
```

`message` 必须是非空字符串。后端会先执行 `strip()`，处理后的长度不能超过 80 个字符。

未知 action 会返回 `unknown_action`，非法 message 会返回 `invalid_message`。

## 公开快照

`get_state_snapshot` 返回当前 message 和公开玩家列表：

```json
{
  "message": "hello",
  "players": [
    {
      "playerId": "p1",
      "nickname": "Ada",
      "connected": true
    }
  ]
}
```

快照不包含 `sessionToken`。

快照中的 `players` 按昵称和 `playerId` 排序，包含公开的 `playerId`、`nickname` 和 `connected` 状态，用于验证加入、断线和重连后的展示。

## 测试方式

后端测试：

```bash
cd apps/api && uv run pytest -v
```

前端构建：

```bash
cd apps/web && pnpm build
```
