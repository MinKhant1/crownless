from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 900
MIN_WINDOW_WIDTH = 960
MIN_WINDOW_HEIGHT = 720
FPS = 60

BOARD_SIZE = 6
FILES = "ABCDEF"

CURRENT_LEVEL = 1
ARMY_SIZE = 6
ARMY_CAPACITY = 6

STARTING_GOLD = 5
DEBUG_SHOP_GOLD = None  # set a number, e.g. 1000, to test the shop with lots of gold
STARTING_NON_KING_CAPACITY = 5
PIECE_PRICE = 5
RELIC_PRICE = 7
ARMY_UPGRADE_PRICE = 12
RELIC_COLLECTION_PRICE = 15
PIECE_COLLECTION_PRICE = 10
REROLL_PRICE = 2
VICTORY_GOLD = 3
GOLDEN_BONUS = 2
MAX_LEVEL = 30
VICTORY_BANNER_TIME = 0.35
VICTORY_REWARD_TIME = 0.25
SCENE_SLIDE_TIME = 0.78
SHOP_CARD_STAGGER = 0.08
LEVEL_PREVIEW_TIME = 0.65
BATTLE_START_TIME = 0.40
SHOP_PIECE_KINDS = ("pawn", "knight", "bishop", "rook", "queen")
SHOP_PIECE_TRAITS = ("golden", "wanted", "explosive", "wooden", "magnet")
STARTER_KINDS = ("pawn", "knight", "bishop", "rook", "queen", "king")
DEPLOY_ROWS = (1, 2)
ENEMY_ID_START = 10001

SHOP_SOURCE = (1024, 1535)
SHOP_BG_SOURCE = (1535, 1024)
DEBUG_SHOP_LAYOUT = False
# Shop parts in shop_bg.png pixels (image is 1535×1024): three framed offers on the top shelf,
# the relic chest in the lower middle, piece chest on the right, and reroll on the left.
SHOP_SLOT_BOUNDS = {
    "piece": (401, 336, 240, 243),
    "relic": (667, 336, 240, 243),
    "army_size": (933, 336, 240, 243),
    "relic_collection": (675, 660, 185, 185),
    "piece_collection": (991, 660, 185, 185),
}
SHOP_PRICE_TAG = (130, 46)
SHOP_REROLL_BOUNDS = (367, 686, 256, 144)
SHOP_CONTINUE_BOUNDS = (683, 906, 170, 58)
SHOP_NOTICE_BOUNDS = (627, 875, 320, 40)
CARD_SOURCE = (484, 479)
PRICE_SOURCE = (379, 133)
REROLL_SOURCE = (684, 385)
SHOP_SIDE_RESERVE = 168
SHOP_BACKGROUND_SCALE = 1.3
SHOP_CARD_WIDTH_FRAC = 0.25
SHOP_CARD_GAP_FRAC = 0.028
SHOP_CARD_CENTER_Y = 0.735
SHOP_PRICE_GAP_FRAC = 0.008
SHOP_BUY = (0.17, 0.755, 0.66, 0.16)
SHOP_ICON = (0.14, 0.06, 0.72, 0.58)
SHOP_REROLL_WIDTH_FRAC = 0.52
# parchment plate on reroll_board.png, as fractions of the board, and its lean in degrees
SHOP_REROLL_LABEL = (0.512, 0.382, 0.33, 0.16)
SHOP_REROLL_TILT = 2.8
SHOP_GOLD_WIDTH_FRAC = 0.42

PIECE_KINDS = ("pawn", "rook", "knight", "bishop", "queen", "king")
PIECE_SCALE = 0.84
PIECE_LIFT_RATIO = 0.22
PIECE_LIFT_MIN = 8
PIECE_LIFT_MAX = 18
PIECE_SELECT_SCALE = 1.07
PIECE_TILT = 3.0
PIECE_BOB_AMPLITUDE = 1.8
PIECE_BOB_SPEED = 2.4
PIECE_EASE_RATE = 16.0
PIECE_SHADOW_ALPHA = 86
PIECE_SHADOW_WIDTH = 0.33
PIECE_SHADOW_HEIGHT = 0.11
PIECE_SHADOW_LIFT_SPREAD = 0.45
PIECE_SHADOW_OFFSET = 0.30
PIECE_TRAVEL_TIME = 0.16
PIECE_IDLE_BOB = 0.0
BOARD_SHADOW_OFFSET_X = 10
BOARD_SHADOW_OFFSET_Y = 18
BOARD_SHADOW_ALPHA = 128
BOARD_THICKNESS = 12
BOARD_RECESS = 92
BOARD_INLAY = (42, 24, 12)
BOARD_INLAY_LIGHT = 30
BOARD_HIGHLIGHT = 86
BOARD_SHADE = 96
BOARD_SELECT_GLOW = 110
SPECIAL_PIECE_VISUAL_TEST = False
TRAIT_HIGH_READABILITY = True
VISUAL_TEST_ID_START = 80001
VISUAL_TEST_TRAITS = {
    "pawn": "golden",
    "knight": "wanted",
    "bishop": "explosive",
    "rook": "ghost",
    "queen": "wooden",
}
PROMOTION_KIND = "queen"

FRAME_SOURCE = 1024
FRAME_CONTENT_X = 85
FRAME_CONTENT_Y = 70
FRAME_CONTENT_W = 862
FRAME_CONTENT_H = 860

HEADER_SOURCE = (1024, 190)
STATUS_SOURCE = (1024, 100)
CROWN_SOURCE = (789, 721)

LAYOUT_SIDE_PAD = 28
LAYOUT_TOP_PAD = 12
LAYOUT_BOTTOM_PAD = 10
LAYOUT_RANK_GUTTER = 40
LAYOUT_FILE_LABEL_H = 24
LAYOUT_TURN_H = 34
LAYOUT_HEADER_STATUS_GAP = 2
LAYOUT_HEADER_WIDTH = 0.97
LAYOUT_FRAME_WIDTH = 0.92
LAYOUT_CROWN_HEIGHT = 1.30
RELIC_BAR_SLOTS = 5
RELIC_CARD_WIDTH = 96
RELIC_CARD_HEIGHT = 105
RELIC_BAR_PAD = 16

LEVEL_TEXT_X = 0.058
ARMY_TEXT_CENTER = 0.821

INITIAL_SETUP = (
    ("rook", "white", "A1"),
    ("knight", "white", "B1"),
    ("bishop", "white", "C1"),
    ("queen", "white", "D1"),
    ("king", "white", "E1"),
    ("pawn", "white", "F1"),
    ("rook", "black", "A6"),
    ("knight", "black", "B6"),
    ("bishop", "black", "C6"),
    ("queen", "black", "D6"),
    ("king", "black", "E6"),
    ("pawn", "black", "F6"),
)

HUD_FILES = {
    "background": "dark_brown_background.png",
    "frame": "board_frame.png",
    "crown": "crown.png",
    "header": "parchment_header.png",
    "status": "status_bar.png",
    "light": "light_square.png",
    "dark": "dark_square.png",
    "gold": "gold.png",
}

SHOP_FILES = {
    "shop_background": "shop_background.png",
    "shop_bg": "shop_bg.png",
    "buying_square": "buying_square.png",
    "price_tag": "price_tag.png",
    "reroll_board": "reroll_board.png",
}
SHOP_OPTIONAL_FILES = {
    "relic_chest": "relic_chest.png",
    "piece_chest": "piece_chest.png",
    "crownless_logo": "crownless_logo.png",
}

def _row(rank: int, *kinds: str) -> tuple[tuple[str, str], ...]:
    """One rank of a formation, files A-F left to right; '.' is an empty square."""
    return tuple((kind, f"{FILES[col]}{rank}") for col, kind in enumerate(kinds) if kind != ".")


_P, _N, _B, _R, _Q = "pawn", "knight", "bishop", "rook", "queen"
_PAWN_LINE = _row(5, _P, _P, _P, _P, _P, _P)

# Thirty stages. Every fifth one follows the level-design sheet; the stages between climb towards it.
# Rank 6 is the enemy's back rank, rank 5 its pawn line; you deploy on ranks 1-2.
# Every piece starts behind a pawn on its own file. Where the design sheet gives fewer pawns than pieces
# (stages 5 and 15), the most valuable pieces get the cover first: queen, then rook, then bishop and knight.
# tests/test_level_design.py checks this for every stage; docs/levels/ has the full sheet.
ENEMY_FORMATIONS = {
    1: _row(6, ".", ".", _N, ".", ".", ".") + _row(5, _P, ".", _P, ".", _P, "."),
    2: _row(6, _B, ".", _N, ".", ".", ".") + _row(5, _P, ".", _P, ".", _P, "."),
    3: _row(6, _R, ".", _B, ".", _N, ".") + _row(5, _P, ".", _P, ".", _P, "."),
    4: _row(6, ".", _B, ".", _N, ".", _R) + _row(5, ".", _P, ".", _P, ".", _P),
    5: _row(6, ".", _R, _Q, _B, _N, ".") + _row(5, ".", _P, _P, ".", ".", "."),
    6: _row(6, _R, ".", _N, _B, ".", ".") + _row(5, _P, ".", _P, _P, ".", "."),
    7: _row(6, ".", _N, ".", _Q, _N, ".") + _row(5, ".", _P, ".", _P, _P, "."),
    8: _row(6, ".", _N, ".", ".", _B, _R) + _row(5, ".", _P, ".", ".", _P, _P),
    9: _row(6, ".", _N, _Q, _N, ".", ".") + _row(5, ".", _P, _P, _P, _P, "."),
    10: _row(6, ".", ".", _N, _N, _N, ".") + _row(5, ".", _P, _P, _P, _P, "."),
    11: _row(6, ".", _B, _N, _N, _B, ".") + _row(5, ".", _P, _P, _P, _P, "."),
    12: _row(6, _R, ".", _N, _N, ".", _B) + _row(5, _P, ".", _P, _P, ".", _P),
    13: _row(6, ".", _B, _N, _Q, _B, ".") + _row(5, ".", _P, _P, _P, _P, "."),
    14: _row(6, _B, _N, ".", _N, ".", _R) + _row(5, _P, _P, _P, _P, ".", _P),
    15: _row(6, _B, _N, _B, _N, _B, _N) + _row(5, _P, ".", _P, ".", _P, "."),
    16: _row(6, ".", _N, _B, _Q, _B, _N) + _row(5, ".", _P, _P, _P, _P, _P),
    17: _row(6, _R, _N, _B, _N, _N, ".") + _row(5, _P, _P, _P, _P, _P, "."),
    18: _row(6, _B, _N, _Q, _N, _B, ".") + _row(5, _P, _P, _P, _P, _P, "."),
    19: _row(6, ".", _N, _B, _B, _N, _R) + _row(5, ".", _P, _P, _P, _P, _P),
    20: _row(6, _N, _N, _N, ".", _N, _N) + _row(5, _P, _P, _P, ".", _P, _P),
    21: _row(6, ".", _N, _Q, _B, _N, _R) + _row(5, ".", _P, _P, _P, _P, _P),
    22: _row(6, ".", _B, _N, _N, _B, _N) + _PAWN_LINE,
    23: _row(6, _R, _N, _Q, _B, _N, ".") + _PAWN_LINE,
    24: _row(6, _N, _B, ".", _N, _B, _N) + _PAWN_LINE,
    25: _row(6, _N, _B, ".", _Q, _B, _N) + _PAWN_LINE,
    26: _row(6, _N, _B, _Q, ".", _N, _R) + _PAWN_LINE,
    27: _row(6, _R, _B, _Q, ".", _N, _N) + _PAWN_LINE,
    28: _row(6, _R, _B, _Q, _Q, _N, ".") + _PAWN_LINE,
    29: _row(6, _R, _N, _Q, _Q, _B, ".") + _PAWN_LINE,
    30: _row(6, _R, _N, _Q, _Q, _B, ".") + _PAWN_LINE,
}
# Enemy special pieces: stage -> {square: trait}. The trait rules are the same as for your pieces.
ENEMY_TRAITS = {
    10: {"D6": "wooden"},
    11: {"D6": "wooden"},
    12: {"C6": "wooden"},
    13: {"C6": "wooden"},
    14: {"D6": "wooden"},
    15: {"A6": "wooden", "B6": "wanted"},
    16: {"B6": "wanted", "E6": "wooden"},
    17: {"D6": "wanted", "E6": "wooden"},
    18: {"B6": "wooden"},
    19: {"B6": "wanted", "D6": "wooden"},
    20: {"B6": "magnet", "E6": "wooden"},
    21: {"B6": "magnet", "E6": "wooden"},
    22: {"C6": "magnet", "F6": "wanted"},
    23: {"B6": "wooden", "E6": "magnet"},
    24: {"A6": "magnet", "D6": "wanted", "F6": "magnet"},
    25: {"A6": "magnet", "F6": "magnet"},
    26: {"A6": "magnet", "E6": "wooden"},
    27: {"E6": "magnet", "F6": "wooden", "D5": "wanted"},
    28: {"E6": "magnet"},
    29: {"B6": "magnet", "E6": "wooden", "C5": "wanted"},
    30: {"D6": "explosive", "E6": "wooden", "C5": "wanted"},
}
WANTED_BOUNTY = 2  # gold for capturing an enemy Wanted piece, paid when the battle is won

LIGHT_TEXT = (245, 232, 210)
DARK_TEXT = (68, 40, 26)
TURN_TEXT = (245, 230, 204)
TURN_CHECK = (214, 78, 64)
LABEL_TEXT = (236, 220, 196)
SELECT_FILL = (214, 170, 64, 100)
CHECK_FILL = (176, 36, 32, 120)
MOVE_DOT = (78, 168, 86)
MOVE_DOT_EDGE = (28, 92, 42)
CAPTURE_OUTLINE = (186, 42, 36)
SELECT_OUTLINE = (232, 196, 96)
DEBUG_PANEL = (18, 12, 9, 220)
DEBUG_TEXT = (240, 224, 196)
RESULT_TEXT = (245, 226, 196)


def opposite(color: str) -> str:
    if color == "white":
        return "black"
    return "white"


def square_name(col: int, row: int) -> str:
    return f"{FILES[col]}{row}"


def parse_square(name: str) -> tuple[int, int]:
    col = FILES.index(name[0].upper())
    row = int(name[1])
    return col, row
