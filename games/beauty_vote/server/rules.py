import random
from games.beauty_vote.server.constants import (
    RULE_META,
    DOMAIN_INDEPENDENT,
    DOMAIN_TARGET_VALUE,
    DOMAIN_WIN_LOSS_ALT,
)


def get_domain(rule_id):
    return RULE_META[rule_id]["domain"]


def initial_rule_pool():
    return list(RULE_META.keys())


def empty_active_rules():
    return {
        "independent": [],
        "target_value": None,
        "win_loss_alt": None,
    }


def unlock_rule(state):
    """Draw a rule from pool, apply domain replacement."""
    pool = state["rule_pool"]
    if not pool:
        return None, None, None

    rule_id = random.choice(pool)
    pool.remove(rule_id)

    domain = get_domain(rule_id)
    active = state["active_rules"]
    replaced_id = None
    message_parts = []

    if domain == DOMAIN_INDEPENDENT:
        active["independent"].append(rule_id)
        message_parts.append(f'规则{rule_id}（{RULE_META[rule_id]["name"]}）已解锁。')

    elif domain == DOMAIN_TARGET_VALUE:
        replaced_id = active["target_value"]
        active["target_value"] = rule_id
        if replaced_id is not None:
            pool.append(replaced_id)
            message_parts.append(
                f'规则{rule_id}（{RULE_META[rule_id]["name"]}）已解锁，'
                f'规则{replaced_id}（{RULE_META[replaced_id]["name"]}）已被取代并回到规则池。'
            )
        else:
            message_parts.append(f'规则{rule_id}（{RULE_META[rule_id]["name"]}）已解锁。')

    elif domain == DOMAIN_WIN_LOSS_ALT:
        replaced_id = active["win_loss_alt"]
        active["win_loss_alt"] = rule_id
        if replaced_id is not None:
            pool.append(replaced_id)
            message_parts.append(
                f'规则{rule_id}（{RULE_META[rule_id]["name"]}）已解锁，'
                f'规则{replaced_id}（{RULE_META[replaced_id]["name"]}）已被取代并回到规则池。'
            )
        else:
            message_parts.append(f'规则{rule_id}（{RULE_META[rule_id]["name"]}）已解锁。')

    message = "".join(message_parts)
    return rule_id, replaced_id, message


def check_unlock(state):
    """Check if elimination count meets threshold for unlock. Returns (rule_id, replaced_id, message) or (None, None, None)."""
    alive_count = sum(1 for p in state["players"].values() if p.get("alive", True))
    threshold = 1 if alive_count <= 10 else 2
    eliminations = state.get("total_eliminations", 0)
    last_unlock_at = state.get("_last_unlock_at_eliminations", 0)
    if eliminations - last_unlock_at >= threshold and state["rule_pool"]:
        state["_last_unlock_at_eliminations"] = eliminations
        return unlock_rule(state)
    return None, None, None


def apply_round_20(state):
    """Silently apply hidden rule: halve scores, T=0, delete all rules, no log."""
    for pid in state["players"]:
        p = state["players"][pid]
        if p.get("alive", True):
            p["score"] = p["score"] // 2
    state["active_rules"] = empty_active_rules()
    state["rule_pool"] = []
    state["has_hidden_rule"] = True
    state["calculation"] = {
        "method": "hidden",
        "label": "隐藏规则",
        "detail": "",
    }
    state["current_T"] = 0
    state["last_T"] = 0
    state["forbidden_number"] = None


def rule_names_for_display(state):
    """Return list of {id, name, description} for currently active rules."""
    result = []
    active = state["active_rules"]
    for rid in active["independent"]:
        result.append(RULE_META[rid])
    tv = active["target_value"]
    if tv is not None:
        result.append(RULE_META[tv])
    wl = active["win_loss_alt"]
    if wl is not None:
        result.append(RULE_META[wl])
    return result
