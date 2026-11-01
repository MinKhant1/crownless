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
DEBUG_SHOP_GOLD = 1000
STARTING_NON_KING_CAPACITY = 5
PIECE_PRICE = 5
RELIC_PRICE = 7
ARMY_UPGRADE_PRICE = 12
RELIC_COLLECTION_PRICE = 15
PIECE_COLLECTION_PRICE = 10
REROLL_PRICE = 2
VICTORY_GOLD = 3
GOLDEN_BONUS = 2
MAX_LEVEL = 5
VICTORY_BANNER_TIME = 0.35
VICTORY_REWARD_TIME = 0.25
SCENE_SLIDE_TIME = 0.78
SHOP_CARD_STAGGER = 0.08
LEVEL_PREVIEW_TIME = 0.65
BATTLE_START_TIME = 0.40
SHOP_PIECE_KINDS = ("pawn", "knight", "bishop", "rook", "queen")
SHOP_PIECE_TRAITS = ("golden", "wanted", "explosive", "ghost", "wooden")
STARTER_KINDS = ("pawn", "knight", "bishop", "rook", "queen", "king")
DEPLOY_ROWS = (1, 2)
ENEMY_ID_START = 10001

SHOP_SOURCE = (1024, 1535)
SHOP_BG_SOURCE = (1535, 1024)
DEBUG_SHOP_LAYOUT = False
# Shelf compartments in shop_bg.png pixels (image is 1535×1024).
SHOP_SLOT_BOUNDS = {
    "piece": (390, 358, 322, 182),
    "relic": (815, 358, 328, 182),
    "army_size": (364, 704, 227, 182),
    "relic_collection": (643, 704, 233, 182),
    "piece_collection": (947, 704, 227, 182),
}
CARD_SOURCE = (484, 479)
PRICE_SOURCE = (379, 133)
REROLL_SOURCE = (684, 385)
SHOP_SIDE_RESERVE = 168
SHOP_BACKGROUND_SCALE = 1.3
SHOP_RELIC_CARD_SCALE = 2.0
SHOP_CHEST_SCALE = 2.0
SHOP_CARD_WIDTH_FRAC = 0.25
SHOP_CARD_GAP_FRAC = 0.028
SHOP_CARD_CENTER_Y = 0.735
SHOP_PRICE_GAP_FRAC = 0.008
SHOP_BUY = (0.17, 0.755, 0.66, 0.16)
SHOP_ICON = (0.14, 0.06, 0.72, 0.58)
SHOP_REROLL_WIDTH_FRAC = 0.52
SHOP_REROLL_LABEL = (0.525, 0.34, 0.335, 0.32)
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
BOARD_BEVEL = 64
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
RELIC_CARD_WIDTH = 70
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

ENEMY_FORMATIONS = {
    1: (("pawn", "A5"), ("pawn", "C5"), ("pawn", "E5"), ("knight", "D6")),
    2: (("pawn", "A5"), ("pawn", "C5"), ("pawn", "E5"), ("bishop", "B6"), ("knight", "D6")),
    3: (("pawn", "B5"), ("pawn", "D5"), ("bishop", "C6"), ("knight", "E6"), ("rook", "A6")),
    4: (("pawn", "A5"), ("pawn", "C5"), ("pawn", "E5"), ("bishop", "B6"), ("knight", "D6"), ("rook", "F6")),
    5: (("king", "D6"), ("pawn", "C5"), ("pawn", "E5"), ("knight", "B6"), ("bishop", "F6"), ("rook", "A6")),
}

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
