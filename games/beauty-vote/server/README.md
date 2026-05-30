# Beauty Vote 服务端设计

## 核心模块

```
server/
  __init__.py           # 导出7个标准钩子
  engine.py             # 核心游戏引擎（规则、结算、回合）
  rules.py              # 10条规则的定义与判定函数
  events.py             # 特殊事件判定与应用
  settlement.py         # 结算管道（6步顺序执行）
  constants.py          # 常量定义
```

## 7个标准钩子

```
create_initial_state(room_context) → state
on_player_join(state, player) → GameResult
on_player_disconnect(state, player) → GameResult
on_player_reconnect(state, player) → GameResult
on_player_leave(state, player) → GameResult
handle_action(state, player, action) → GameResult
get_state_snapshot(state, viewer) → dict
```

## 关键内部函数

### 回合生命周期
```
_start_game(state)                      # 首次进入 submit 阶段
_start_round(state)                     # 新回合：解锁检测、特殊事件、重置提交
_end_round(state)                       # 结算、淘汰、检查游戏结束
```

### 规则管理
```
_check_unlock(state)                    # 检查淘汰数是否达标，触发解锁
_unlock_rule(state)                     # 从池中随机抽取、域替换、记录日志
_remove_domain_rules(state)             # 20回合后删除互斥域规则（保留规则3）
```

### T 值计算
```
_calculate_T(state, submissions)        # 分发到当前生效的 T 公式
_calculate_basic_T(numbers)             # T = 0.8 × mean（基础/默认）
_calculate_reverse_T(numbers, reverses) # T = 1.2 × mean - R（规则5）
_calculate_double_T(numbers)            # T1, T2（规则8）
_calculate_roulette_T(numbers)          # T = k × mean, k∈{0.6,0.8,1.0}（规则10）
```

### 胜负判定
```
_apply_win_loss_alt(state, submissions) # 检查规则1/3是否触发
_determine_winners(state, submissions, T)      # 按|num-T|排序判定获胜者
_determine_winners_double(state, submissions)  # 按D值排序（规则8）
_determine_furthest(state, submissions, T, n)  # 最远n名
_determine_furthest_double(state, submissions, n) # D值最远n名（规则8）
```

### 结算管道（顺序不可变 → ①~⑥）
```
_settle_forbidden(state, player, submission)    # ① 禁区惩罚 -3
_settle_inheritance(state, player, result)      # ② 继承减伤 固定-1
_settle_leverage(state, player, submission, won) # ③ 杠杆 +2/-1
_settle_betrayer(state, player, submission, furthest_ids, winloss_triggered) # ④ 背叛者
_settle_precision(state, winners, T, base_penalties) # ⑤ 精准奖倍率
_settle_double_points(state, penalties)         # ⑥ 双倍积分（特殊事件最后触发）
```

## 解锁频率

```python
def _unlock_threshold(state) -> int:
    alive_count = sum(1 for p in state["players"].values() if p["alive"])
    if alive_count <= 10:
        return 1   # 每淘汰1人解锁
    else:
        return 2   # 每淘汰2人解锁
```

## 游戏自动开始条件

```python
def _check_auto_start(state, room_capacity) -> bool:
    alive_count = sum(1 for p in state["players"].values() if p["alive"])
    ready_count = sum(1 for p in state["players"].values() if p.get("ready"))
    return alive_count == room_capacity and ready_count == room_capacity
```

## 回合上限（第20回合）

```python
if state["round"] >= 20 and not state.get("has_hidden_rule"):
    # 全员分数减半
    # T 永久设为 0
    # 删除全部 active_rules（所有域清空）
    # 清空 rule_pool
    # has_hidden_rule = True
    # calculation.method = "hidden", calculation.label = "隐藏规则"
    # 前端可看到"隐藏规则"标签，但不可查看详情
    # rule_log 不追加任何条目（静默删除）
```

## 前端不可见信息

- `rule_pool` — 不包含在快照中
- `has_hidden_rule` — 仅用于判断是否显示标签，不暴露规则内容
- 20回合后的规则清空 — 不写入 rule_log，前端无感知
