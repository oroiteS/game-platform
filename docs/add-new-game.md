# 新增游戏指南

新增游戏时，优先只阅读本文、`games/_template/README.md` 和 `packages/game-contract/README.md`。

## 新增步骤

1. 在 `games/` 下新建目录，例如：

```text
games/guess-number/
```

2. 从模板复制结构：

```text
games/_template/
  web/
  server/
  shared/
  game.config.ts
  README.md
```

3. 修改 `game.config.ts` 中的游戏元信息。

4. 在 `web/` 内实现该游戏的前端入口。

5. 在 `server/` 内实现该游戏的后端钩子。

6. 在平台游戏注册表中添加该游戏引用。

7. 为该游戏补充 README，说明玩法、事件、状态结构和测试方式。

## 游戏目录约定

```text
games/<game-id>/
  game.config.ts       前端可读取的游戏元信息
  web/                 游戏前端入口和组件
  server/              游戏后端规则和事件处理
  shared/              该游戏前后端共享协议说明
  README.md            该游戏开发说明
```

## 新游戏不应该做的事

新增游戏时不要重复实现：

- 房间号生成。
- 创建房间接口。
- 加入房间接口。
- WebSocket 连接管理。
- 断线重连恢复。
- 匿名身份生成。
- localStorage 会话格式。
- 平台首页。

这些属于平台能力。

## 游戏需要提供的内容

每个游戏至少需要定义：

- 游戏 ID。
- 游戏名称。
- 最少玩家数。
- 最多玩家数。
- 初始状态。
- 玩家加入逻辑。
- 玩家断线逻辑。
- 玩家重连逻辑。
- 玩家离开逻辑。
- 玩家操作处理。
- 状态快照。

## 前端事件建议

游戏前端只发送“玩家意图”，不要直接发送完整状态。

示例：

```json
{
  "type": "submit_guess",
  "payload": {
    "value": 123456
  }
}
```

后端负责校验该操作是否合法，并广播新的状态快照。

## 后端事件建议

游戏后端处理事件时应返回明确结果：

```text
accepted: 操作有效，状态已更新
rejected: 操作无效，返回错误码
noop: 操作有效但状态不变
```

不要在游戏模块里直接操作 WebSocket 连接。游戏模块只返回状态变化和需要广播的事件，由平台层负责发送。

