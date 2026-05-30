import random
import statistics
from collections import Counter


def calculate_T(state, submissions):
    """Calculate T based on active target value rule. Returns (T, T2_or_k, method, label, detail)."""
    numbers = [s["number"] for s in submissions.values()]
    if not numbers:
        return 0, None, "basic", "普通规则", ""

    mean_val = statistics.mean(numbers)
    active = state["active_rules"]
    target_rule = active["target_value"]

    if target_rule == 5:
        reverses = [s.get("reverse_number", 0) for s in submissions.values()]
        R = _calc_mode_or_avg(reverses)
        T = max(0.0, min(100.0, round(1.2 * mean_val - R, 1)))
        return T, None, "rule5", "规则5：反向投票", f"T = 1.2 x {mean_val:.1f} - {R} = {T}"

    elif target_rule == 8:
        T1 = round(0.8 * mean_val, 1)
        T2 = round(1.2 * mean_val, 1)
        return T1, T2, "rule8", "规则8：双重标准", f"D = (数字−{T1})² + (数字−{T2})²，D越小越好 | T₁=0.8×{mean_val:.1f}={T1}, T₂=1.2×{mean_val:.1f}={T2}"

    elif target_rule == 10:
        k = random.choice([0.6, 0.8, 1.0])
        T = round(k * mean_val, 1)
        return T, k, "rule10", "规则10：命运轮盘", f"k = {k}, T = {k} x {mean_val:.1f} = {T}"

    else:
        T = round(0.8 * mean_val, 1)
        return T, None, "basic", "普通规则", f"T = 0.8 x {mean_val:.1f} = {T}"


def _calc_mode_or_avg(values):
    """Calculate mode of values; tie -> average rounded to int."""
    counts = Counter(values)
    max_count = max(counts.values())
    modes = [v for v, c in counts.items() if c == max_count]
    if len(modes) == 1:
        return modes[0]
    return round(statistics.mean(modes))


def apply_win_loss_alt(state, submissions):
    """Check Rule 1 (mirror) or Rule 3 (polar jump). Returns (triggered, winners, penalized, method, detail)."""
    active = state["active_rules"]
    wl_rule = active["win_loss_alt"]

    if wl_rule == 1:
        num_counts = Counter(s["number"] for s in submissions.values())
        duplicated_numbers = {n for n, c in num_counts.items() if c >= 2}
        if duplicated_numbers:
            penalized = [pid for pid, s in submissions.items() if s["number"] in duplicated_numbers]
            winners = [pid for pid in submissions if pid not in penalized]
            return True, winners, penalized, "rule1", "规则1：镜面惩罚 — 存在重复数字，其他玩家获胜"

    elif wl_rule == 3:
        has_zero = any(s["number"] == 0 for s in submissions.values())
        if has_zero:
            winners = [pid for pid, s in submissions.items() if s["number"] == 100]
            return True, winners, [], "rule3", "规则3：两极跳跃 — 有人选0，选100者获胜"

    return False, [], [], "", ""


def find_extreme_duplicates(submissions):
    """Check if ALL players chose the exact same number."""
    numbers = [s["number"] for s in submissions.values()]
    return len(set(numbers)) == 1 and len(numbers) > 1


def determine_winners_furthest(submissions, T, T2, state):
    """Determine winners and furthest players. Returns (winners, furthest, method, detail)."""
    alive_pids = [pid for pid, p in state["players"].items() if p.get("alive", True)]
    alive_count = len(alive_pids)
    n_furthest = 1 if alive_count <= 5 else 3

    target_rule = state["active_rules"]["target_value"]

    if target_rule == 8 and T2 is not None:
        d_values = [(pid, (s["number"] - T) ** 2 + (s["number"] - T2) ** 2)
                    for pid, s in submissions.items() if pid in alive_pids]
        d_values.sort(key=lambda x: x[1])
        min_d = d_values[0][1]
        winners = [pid for pid, d in d_values if d == min_d]
        furthest = [pid for pid, _ in d_values[-n_furthest:]]
        return winners, furthest, "rule8", "D值判定"
    else:
        diffs = [(pid, abs(s["number"] - T)) for pid, s in submissions.items() if pid in alive_pids]
        diffs.sort(key=lambda x: x[1])
        min_diff = diffs[0][1]
        winners = [pid for pid, d in diffs if d == min_diff]
        furthest = [pid for pid, _ in diffs[-n_furthest:]]
        return winners, furthest, "normal", f"|数字 - {T}| 判定"


def settle_round(state, submissions, winners, furthest, T, winloss_triggered,
                 special_event, betray_results):
    """Run the 6-step settlement pipeline. Returns {playerId: score_delta}.

    Pipeline order: forbidden -> inheritance -> leverage -> betrayer -> precision -> double_points
    """
    alive_pids = [pid for pid, p in state["players"].items() if p.get("alive", True)]
    deltas = {pid: 0 for pid in alive_pids}
    cannot_win = set()

    forbidden = state.get("forbidden_number")

    # Build initial deltas from winner/furthest determination
    for pid in alive_pids:
        sub = submissions.get(pid)
        if not sub:
            continue

        # Step 1: Forbidden zone
        if forbidden is not None and sub["number"] == forbidden:
            deltas[pid] = -3
            cannot_win.add(pid)
            continue

        if winloss_triggered:
            # Win/loss alt handles separately - base no penalty for winners
            if pid in winners:
                pass  # 0
            else:
                # Mirror punishment: penalized players get -1
                pass  # handled below
        elif pid in winners and pid not in cannot_win:
            pass  # Winner: 0
        elif pid in furthest:
            deltas[pid] = -2
        else:
            deltas[pid] = -1

    # Step 2: Inheritance reduction (Rule 7)
    inherited = state.get("inherited_number")
    if inherited is not None and 7 in state["active_rules"]["independent"]:
        for pid in alive_pids:
            sub = submissions.get(pid)
            if sub and sub["number"] == inherited and pid not in winners and pid not in cannot_win:
                deltas[pid] = -1

    # Step 3: Leverage (Rule 6)
    if 6 in state["active_rules"]["independent"]:
        for pid in alive_pids:
            sub = submissions.get(pid)
            if sub and sub.get("use_leverage"):
                if pid in winners and pid not in cannot_win:
                    deltas[pid] += 2
                elif not winloss_triggered:
                    deltas[pid] -= 1

    # Step 4: Betrayer (Rule 9)
    if 9 in state["active_rules"]["independent"] and not winloss_triggered:
        for pid in alive_pids:
            sub = submissions.get(pid)
            if sub and sub.get("betray_target"):
                target = sub["betray_target"]
                if target in furthest:
                    betray_results[pid] = {"target": target, "success": True}
                    deltas[pid] = 0
                    for other_pid in alive_pids:
                        if other_pid != pid:
                            deltas[other_pid] -= 1
                else:
                    betray_results[pid] = {"target": target, "success": False}
                    deltas[pid] -= 2

    # Step 5: Precision prize (Rule 2)
    if 2 in state["active_rules"]["independent"] and not winloss_triggered:
        T_rounded = round(T)
        winner_numbers = [submissions[w]["number"] for w in winners if w in submissions]
        if T_rounded in winner_numbers:
            for pid in alive_pids:
                if pid not in winners and pid not in cannot_win and pid not in furthest:
                    deltas[pid] = -2

    # Step 6: Double points (special event)
    if special_event and special_event["type"] == "double_points":
        for pid in deltas:
            deltas[pid] *= 2

    # Lucky exemption
    if special_event and special_event["type"] == "lucky_exemption":
        lucky = special_event.get("target_player")
        if lucky and lucky in deltas:
            deltas[lucky] = 0

    return deltas
