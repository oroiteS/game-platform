# Beauty Vote 前端设计

## 组件结构

```
web/
  GameApp.tsx              # 入口组件，按 phase 切换视图
  phases/
    LobbyPhase.tsx         # 准备阶段：玩家列表、准备按钮、自动开始倒计时
    SubmitPhase.tsx        # 提交阶段：数字选择 + 条件字段
    RevealPhase.tsx        # 揭晓阶段：结果展示
    GameOverPhase.tsx      # 最终结算：全部数字公开、排名
  ui/
    NumberInput.tsx        # 0-100 数字输入（滑块+输入框）
    ScoreBoard.tsx         # 实时分数排行榜
    RulePanel.tsx          # 已生效规则展示（小型可折叠组件）
    RuleBadge.tsx          # 单个规则小按钮/标签，点击展开详情
    CalculationBox.tsx     # 计算方式展示：公式 + 触发来源标签
    Timer.tsx              # 90秒倒计时
    PlayerStatusStrip.tsx  # 玩家存活/淘汰/准备状态条
    EventBanner.tsx        # 特殊事件横幅
    RuleChangeToast.tsx    # 规则变动弹窗/公告
```

## 核心 UX 规则

### 1. 规则可见性
- **规则池内容对所有玩家隐藏** — 只展示当前已生效的规则。
- 已生效规则通过 `RuleBadge` 小组件展示，每个是一个小标签/按钮。
- 点击 `RuleBadge` 弹出 Popover/弹窗显示该规则的完整说明。
- 基础规则永远可见（标注为"普通规则"）。

### 2. 规则变动提示
- 当规则被顶替时，前端收到 `rule_change` 消息。
- 以 Toast 或顶部横幅公告形式提示玩家："规则X已被规则Y取代"。
- 注意：20 回合后的规则删除**不**暴露原因。（后端不在 rule_log 中写入这些删除，前端的 ruleLog 中看不到对应条目。）

### 3. 计算方式展示
- 结算阶段（reveal）显示 `CalculationBox`：
  - 列出当前生效的计算公式。
  - 公式旁标注触发来源（如"普通规则"、"规则5：反向投票"）。
  - 显示具体数值代入过程。

### 4. 分数实时统计
- `ScoreBoard` 始终显示所有存活玩家的当前分数。
- 分数变化时播放过渡动画。
- 淘汰玩家灰显并标记。

### 5. 数字可见性
- **提交阶段**：只看到自己的数字。
- **常规 reveal**：看到T值、获胜者、最远者、自身状态。不展示其他玩家具体数字。
- **游戏结束（ended）**：展示所有玩家的每回合数字、最终排名。

### 6. 隐藏规则（回合上限）
- `has_hidden_rule === true` 时，规则面板清空所有已有规则，仅显示一个"隐藏规则"标签。
- 标签可见但**不可点击**、不可展开。
- 可配合 `hidden_rule` 消息触发一个神秘感动画/氛围效果。
- 计算方式标注为 `"隐藏规则"`，不展示具体公式。

### 7. 准备阶段（Lobby）
- 显示当前人数/房间容量。
- 显示已准备人数。
- 准备/取消准备按钮。
- 满员且全部准备时自动开始。

## Props 接口

```ts
type Props = {
  room: RoomSummary;
  gameState: unknown;    // BeautyVoteState
  playerId: string;
  onAction: (action: { type: string; payload?: unknown }) => boolean;
};
```

## 条件字段展示

| 条件 | 显示字段 |
|------|---------|
| 规则 5 生效 | 反向数字输入 |
| 规则 6 生效 | "使用杠杆"勾选框 |
| 规则 9 生效 | 背叛者目标下拉选择 |
| 规则 4 生效 | 禁区数字红色标注 |
| 规则 7 生效 | 继承数字蓝色标注 |
| 无 | 仅数字输入 |
