PIECE_VALUES = {
    "pawn": 1,
    "knight": 3,
    "bishop": 3,
    "rook": 5,
    "queen": 9,
    "king": 1000,
}

AI_WEIGHTS = {
    "capture_multiplier": 100,
    "danger_multiplier": 70,
    "attack_pressure": 30,
    "target_access": 20,
    "positional_bonus": 5,
    "repeat_penalty": 30,
}

AI_DIFFICULTY = {
    "easy": {"optimal_move_chance": 0.55},
    "normal": {"optimal_move_chance": 0.85},
    "hard": {"optimal_move_chance": 1.0},
}

HIGHLIGHT_SECONDS = 0.28
TRAVEL_SECONDS = 0.2

DIFFICULTY = "normal"


def set_difficulty(name: str) -> None:
    global DIFFICULTY
    if name not in AI_DIFFICULTY:
        raise ValueError(f"unknown difficulty: {name}")
    DIFFICULTY = name
