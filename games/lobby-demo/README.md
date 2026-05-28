# lobby-demo

`lobby-demo` 是平台闭环占位游戏，用于验证房间、玩家加入、断线重连、动作处理和公开状态快照的后端链路。

公开游戏 ID 使用 `lobby-demo`。Python 后端导入包使用 `games.lobby_demo`，避免连字符目录无法作为 Python 包导入的问题。

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
