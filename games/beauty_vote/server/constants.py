INITIAL_SCORE = 15
MIN_PLAYERS = 4
MAX_PLAYERS = 30
NUMBER_RANGE = (0, 100)
SUBMIT_TIMEOUT_SECONDS = 90
MAX_ROUNDS = 20
SPECIAL_EVENT_PROBABILITY = 0.15

FURTHEST_COUNT_DEFAULT = 3
FURTHEST_COUNT_SMALL = 1
SMALL_GAME_THRESHOLD = 5

UNLOCK_THRESHOLD_LARGE = 2
UNLOCK_THRESHOLD_SMALL = 1
UNLOCK_SMALL_GAME_THRESHOLD = 10

CONSECUTIVE_NO_ELIMINATION_LIMIT = 3

ROULETTE_COEFFICIENTS = [0.6, 0.8, 1.0]

DOMAIN_INDEPENDENT = "independent"
DOMAIN_TARGET_VALUE = "target_value"
DOMAIN_WIN_LOSS_ALT = "win_loss_alt"

RULE_META = {
    1: {
        "id": 1,
        "name": "镜面惩罚",
        "domain": DOMAIN_WIN_LOSS_ALT,
        "description": "若存在≥2人选择相同数字，这些玩家投票无效并各扣1分；其他所有玩家立即获胜，不扣分。",
    },
    2: {
        "id": 2,
        "name": "精准奖",
        "domain": DOMAIN_INDEPENDENT,
        "description": "若获胜者中有人数字=round(T)，则本轮非获胜者扣分变为2分。",
    },
    3: {
        "id": 3,
        "name": "两极跳跃",
        "domain": DOMAIN_WIN_LOSS_ALT,
        "description": "若本轮有人选0，则所有选100的玩家立即获胜，不扣分。",
    },
    4: {
        "id": 4,
        "name": "数字禁区",
        "domain": DOMAIN_INDEPENDENT,
        "description": "上回合T值四舍五入取整为本回合禁区数字，选择者立即扣3分且不能获胜。",
    },
    5: {
        "id": 5,
        "name": "反向投票",
        "domain": DOMAIN_TARGET_VALUE,
        "description": "提交时额外提交反向数字，众数R，T=1.2×均值-R。",
    },
    6: {
        "id": 6,
        "name": "分数杠杆",
        "domain": DOMAIN_INDEPENDENT,
        "description": "提交时可勾选使用杠杆。获胜+2分，未获胜-1分。",
    },
    7: {
        "id": 7,
        "name": "数字继承",
        "domain": DOMAIN_INDEPENDENT,
        "description": "上回合淘汰者所选数字均值为继承数字，选继承数字者获胜+2分，失败扣分固定为1分。",
    },
    8: {
        "id": 8,
        "name": "双重标准",
        "domain": DOMAIN_TARGET_VALUE,
        "description": "产生两个目标值T₁=0.8×均值、T₂=1.2×均值。D = (数字-T₁)² + (数字-T₂)²，D值越小越好，以此判定获胜与最远。",
    },
    9: {
        "id": 9,
        "name": "背叛者",
        "domain": DOMAIN_INDEPENDENT,
        "description": "每回合秘密指定一名存活玩家为目标。若该玩家成为本轮最远者，你免扣分且全员额外-1分；若猜错，你额外-2分。规则1/3触发时无效。",
    },
    10: {
        "id": 10,
        "name": "命运轮盘",
        "domain": DOMAIN_TARGET_VALUE,
        "description": "提交后随机抽取系数k∈{0.6,0.8,1.0}，T=k×均值。",
    },
}

SPECIAL_EVENT_TYPES = [
    "number_storm",
    "score_reset",
    "anonymity_break",
    "double_points",
    "lucky_exemption",
]
