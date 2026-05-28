# Game Server

这里放该游戏的后端规则和事件处理。

游戏后端应该只处理游戏规则，不直接操作 WebSocket 连接。

建议实现以下概念：

```text
createInitialState
onPlayerJoin
onPlayerDisconnect
onPlayerReconnect
onPlayerLeave
handleAction
getStateSnapshot
```

