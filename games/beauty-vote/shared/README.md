# Beauty Vote 前后端共享协议

## Action 类型

### toggle_ready
准备阶段切换准备状态。
```json
{ "type": "toggle_ready" }
```

### submit_number
每回合提交数字。
```json
{
  "type": "submit_number",
  "payload": {
    "number": 50,
    "use_leverage": false,
    "reverse_number": null,
    "betray_target": null
  }
}
```

字段说明：
- `number` (必填): 0~100 整数，首回合不可选 0 或 100
- `use_leverage` (可选): 仅规则 6 生效时有效
- `reverse_number` (可选): 仅规则 5 生效时必填，0~100 整数
- `betray_target` (可选): 仅规则 9 生效时可选，目标玩家 ID，不可选 0/100/禁区数字

## 服务端消息类型

### room_snapshot
WebSocket 重连或广播时发送。

```json
{
  "type": "room_snapshot",
  "room": { "roomCode": "123456", "gameId": "beauty-vote", "status": "playing", "capacity": 6, "players": [] },
  "game": {
    "phase": "submit",
    "round": 3,
    "mySubmission": null,
    "players": [
      {
        "playerId": "abc",
        "nickname": "Alice",
        "score": 12,
        "alive": true,
        "ready": false,
        "lastNumber": 50
      }
    ],
    "currentT": 42.5,
    "lastT": 38.0,
    "forbiddenNumber": 38,
    "inheritedNumber": null,
    "activeRules": { "independent": [2, 4], "targetValue": null, "winLossAlt": 1 },
    "specialEvent": null,
    "winnerIds": [],
    "furthestIds": [],
    "roundLog": [],
    "ruleLog": [],
    "calculation": {
      "method": "basic",
      "label": "普通规则",
      "detail": "T = 0.8 × 均值 = 0.8 × 52.3 = 41.8"
    },
    "isFinal": false
  }
}
```

**结算阶段额外字段（reveal 最终结算）：**
```json
{
  "allSubmissions": { "playerId": 50 },
  "scoreChanges": { "playerId": -2 },
  "betrayResults": { "betrayerId": "targetId", "success": true }
}
```

### error
```json
{
  "type": "error",
  "code": "already_submitted",
  "message": "本回合已提交。"
}
```

### rule_change（规则变动公告）
```json
{
  "type": "rule_change",
  "unlocked": 5,
  "replaced": 8,
  "message": "规则5（反向投票）已解锁，规则8（双重标准）已被取代并回到规则池。"
}
```

### hidden_rule（回合上限触发）
```json
{
  "type": "hidden_rule",
  "message": "一股神秘力量笼罩了投票..."
}
```
前端收到后显示"隐藏规则"标签（不可点击查看详情），同时清空所有已生效规则展示。

## 可见性规则

| 信息 | lobby | submit | reveal（常规） | reveal（游戏结束） |
|------|-------|--------|---------------|-------------------|
| 自己数字 | - | ✓ | ✓ | ✓ |
| 他人数字 | - | ✗ | ✗ | ✓ |
| T值 | - | ✗ | ✓ | ✓ |
| 获胜者 | - | ✗ | ✓ | ✓ |
| 最远者 | - | ✗ | ✓ | ✓ |
| 扣分明细 | - | ✗ | ✓ | ✓ |
| 规则池内容 | ✗ | ✗ | ✗ | ✗ |
| 已生效规则 | ✓ | ✓ | ✓ | ✓ |
| 隐藏规则标签 | ✓ | ✓ | ✓ | ✓ |
| 隐藏规则详情 | ✗ | ✗ | ✗ | ✗ |
| 背叛结果 | - | ✗ | ✓ | ✓ |
| 计算方式 | - | ✗ | ✓ | ✓ |

## 回合阶段流转

```
lobby → submit → reveal → submit → ... → reveal → ended
         ↑_________| (循环)
```
