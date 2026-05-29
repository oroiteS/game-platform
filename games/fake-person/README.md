# fake-person (伪人游戏)

`fake-person` 是一款线下聚会推理游戏。公开游戏 ID 使用 `fake-person`。Python 后端导入包使用 `games.fake_person`，通过 `fake_person` 包名避免连字符路径无法作为 Python 包导入的问题。

## 玩法概要

这是一款支持 3 到 10 人的聚会推理游戏。1 名玩家担任主持人，其余玩家秘密分配人类或伪人身份。主持人抽取问题后，每位玩家轮流口头作答。伪人必须在回答中巧妙融入自己的关键词（伪装成人类），而人类则正常回答。主持人通过回答中的蛛丝马迹，猜测谁是伪人。

每轮流程：大厅准备 -> 成为主持人 -> 身份分配 -> 抽取问题 -> 玩家口头作答（离线环节）-> 主持人猜测 -> 揭示结果 -> 继续或结束。

### 人数范围

3 到 10 人（含 1 名主持人）。创建房间时房主需输入本局人数。

### 玩家角色

- **主持人**（1 名）：不参与身份分配和作答，负责出题、观察回答、猜测伪人、控制游戏流程。
- **普通玩家**（其余所有人）：秘密选择人类或伪人身份。伪人获得一个关键词，回答问题时需要自然地融入关键词；人类获得无关键词的空白身份，正常作答即可。

## 游戏流程

```
大厅 (lobby)
  |
  +-> toggle_ready (非主持人玩家准备)
  +-> become_host (条件满足时，任一玩家成为主持人)
  |
  v
身份分配 (identity_pick)
  |
  +-> pick_identity (非主持人玩家选择人类/伪人)
  +-> draw_question (主持人抽取问题，所有非主持人身份选定后可用)
  |
  v
问答阶段 (question)
  |
  |  <玩家离线口头作答>
  |
  +-> guess (主持人猜测某玩家的身份)
  |
  v
揭示阶段 (reveal)
  |
  +-> next_player (主持人进入下一轮，或所有玩家猜完回到大厅)
  +-> end_game (主持人随时结束游戏，回到大厅)
```

## Action 一览

客户端发送的 action 格式：

```json
{
  "type": "<action_type>",
  "payload": { ... }
}
```

| Action | Payload | 发送者 | 阶段 | 说明 |
|---|---|---|---|---|
| `toggle_ready` | 无 (空对象 `{}`) | 非主持人 | lobby | 切换准备状态。再次发送取消准备 |
| `become_host` | 无 (空对象 `{}`) | 任何人 | lobby | 成为主持人。条件：房间满员且全员已准备 |
| `pick_identity` | `{"role": "human" \| "fake"}` | 非主持人 | identity_pick | 选择身份。选 fake 会自动分配一个未被使用的关键词 |
| `draw_question` | 无 (空对象 `{}`) | 主持人 | identity_pick | 抽取问题。所有非主持人必须已选定身份 |
| `guess` | `{"targetPlayerId": "...", "guessedRole": "human" \| "fake"}` | 主持人 | question | 猜测目标玩家身份。不能重复猜测同一玩家 |
| `next_player` | 无 (空对象 `{}`) | 主持人 | reveal | 进入下一轮。清除当前猜测，返回问答阶段；所有非主持人被猜完后回到大厅 |
| `end_game` | 无 (空对象 `{}`) | 主持人 | 任意 | 立即结束游戏，重置到大厅 |

### 错误码

业务逻辑拒绝时会返回对应错误码：

| 错误码 | 触发条件 |
|---|---|
| `wrong_phase` | 当前阶段不允许该 action |
| `not_host` | 只有主持人能执行的操作被非主持人调用 |
| `host_cannot_ready` | 主持人试图 toggle_ready |
| `host_exists` | 已有主持人时再次 become_host |
| `not_full` | 房间未满员时 become_host |
| `not_all_ready` | 有玩家未准备时 become_host |
| `host_cannot_pick` | 主持人试图 pick_identity |
| `already_picked` | 玩家重复 pick_identity |
| `invalid_role` | role 不是 "human" 或 "fake" |
| `no_keywords_left` | 伪人关键词池已耗尽 |
| `not_all_picked` | 有非主持人未选身份时 draw_question |
| `invalid_payload` | guess 缺少 targetPlayerId 或 guessedRole |
| `invalid_target` | 猜测目标不是非主持人玩家 |
| `already_guessed` | 主持人重复猜测同一玩家 |
| `unknown_action` | 未知 action 类型 |

## 公开快照

`get_state_snapshot` 返回的快照结构因查看者角色而异：

### 公共字段（所有人可见）

```json
{
  "phase": "lobby",
  "hostPlayerId": "p1",
  "readyPlayerIds": ["p2", "p3"],
  "currentQuestion": "你最讨厌的食物是什么？",
  "guessedPlayerIds": [],
  "players": [
    {
      "playerId": "p1",
      "nickname": "主持人",
      "isHost": true,
      "ready": false
    }
  ],
  "myIdentity": null,
  "currentGuess": null,
  "allIdentities": null
}
```

- `phase`：当前游戏阶段（`lobby` / `identity_pick` / `question` / `reveal`）
- `players`：所有玩家列表，含昵称、是否主持人、是否已准备
- `readyPlayerIds`：已准备玩家的 ID 列表
- `currentQuestion`：当前问题文本（仅 `question` 和 `reveal` 阶段有值）
- `guessedPlayerIds`：已被主持人猜测过的玩家 ID 列表

### 普通玩家视角

- `myIdentity`：该玩家自己的身份信息。若已选定身份，返回 `{"role": "human"}` 或 `{"role": "fake", "keyword": "加班"}`；未选定时为 `null`
- `allIdentities`：始终为 `null`
- `currentGuess`：揭示阶段时包含当前猜测结果，包括目标玩家的 `actualRole` 和 `keyword`

### 主持人视角

- `myIdentity`：始终为 `null`（主持人无身份）
- `allIdentities`：所有非主持人玩家的完整身份信息，键为 `playerId`
- `currentGuess`：揭示阶段时包含当前猜测的完整结果

快照不包含 `sessionToken`、`roomCode` 等平台层数据。

## 关键词与问题库

游戏内置 37 个中文网络热词关键词和 20 个中文聚会问题，定义在 `shared.py` 中：
- **关键词**：如"猫"、"加班"、"内卷"、"种草"、"破防"等，伪人回答时需自然融入
- **问题**：如"你最讨厌的食物是什么？"、"如果中了 100 万你会怎么花？"等

## 测试方式

后端测试：

```bash
cd apps/api && uv run pytest tests/test_fake_person.py -v
```

前端构建：

```bash
cd apps/web && pnpm build
```
