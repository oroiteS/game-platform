import random
from games.beauty_vote.server.constants import SPECIAL_EVENT_PROBABILITY, SPECIAL_EVENT_TYPES


def roll_special_event():
    """15% chance to trigger a special event. Returns event dict or None."""
    if random.random() < SPECIAL_EVENT_PROBABILITY:
        event_type = random.choice(SPECIAL_EVENT_TYPES)
        event = {"type": event_type, "target_player": None}
        return event
    return None


def apply_number_storm(submissions):
    """Each number randomly +-5, clamped to 0-100. Returns new submissions dict with _original_number preserved."""
    stormed = {}
    for pid, sub in submissions.items():
        delta = random.randint(-5, 5)
        new_num = max(0, min(100, sub["number"] + delta))
        stormed[pid] = dict(sub, _original_number=sub["number"], number=new_num)
    return stormed


def apply_score_reset(state):
    """Reset all alive player scores to average (ceil, min 5). Original highest score gets +1."""
    alive = [(pid, p) for pid, p in state["players"].items() if p.get("alive", True)]
    if not alive:
        return
    avg = sum(p["score"] for _, p in alive) / len(alive)
    new_score = max(5, int(avg + 0.9999))
    max_score_before = max(p["score"] for _, p in alive)
    for pid, p in alive:
        p["score"] = new_score + (1 if p["score"] == max_score_before else 0)


def apply_lucky_exemption(state, event):
    """Pick a random alive player to be exempt from penalties this round."""
    alive_pids = [pid for pid, p in state["players"].items() if p.get("alive", True)]
    if alive_pids:
        event["target_player"] = random.choice(alive_pids)
