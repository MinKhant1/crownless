from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 900
MIN_WINDOW_WIDTH = 960
MIN_WINDOW_HEIGHT = 700
FPS = 60

BOARD_SIZE = 6
FILES = "ABCDEF"

CURRENT_LEVEL = 1
ARMY_SIZE = 6
ARMY_CAPACITY = 6

STARTING_GOLD = 5
STARTING_NON_KING_CAPACITY = 5
PIECE_PRICE = 5
RELIC_PRICE = 7
ARMY_UPGRADE_PRICE = 12
REROLL_PRICE = 2
VICTORY_GOLD = 3
GOLDEN_BONUS = 2
MAX_LEVEL = 5
SHOP_PIECE_KINDS = ("pawn", "knight", "bishop", "rook", "queen")
STARTER_KINDS = ("pawn", "knight", "bishop", "rook", "queen", "king")
DEPLOY_ROWS = (1, 2)
ENEMY_ID_START = 10001

SHOP_SOURCE = (1024, 1535)
CARD_SOURCE = (484, 479)
PRICE_SOURCE = (379, 133)
REROLL_SOURCE = (684, 385)
SHOP_SIDE_RESERVE = 168
SHOP_CARD_WIDTH_FRAC = 0.25
SHOP_CARD_GAP_FRAC = 0.028
SHOP_CARD_CENTER_Y = 0.735
SHOP_PRICE_GAP_FRAC = 0.008
SHOP_BUY = (0.17, 0.755, 0.66, 0.16)
SHOP_ICON = (0.22, 0.16, 0.56, 0.46)
SHOP_REROLL_WIDTH_FRAC = 0.52
SHOP_REROLL_LABEL = (0.525, 0.34, 0.335, 0.32)
SHOP_GOLD_WIDTH_FRAC = 0.42

PIECE_KINDS = ("pawn", "rook", "knight", "bishop", "queen", "king")
PIECE_SCALE = 0.84
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
LAYOUT_STATUS_FRAME_GAP = 16
LAYOUT_HEADER_WIDTH = 0.97
LAYOUT_FRAME_WIDTH = 0.92
LAYOUT_CROWN_HEIGHT = 1.30

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
}

SHOP_FILES = {
    "shop_background": "shop_background.png",
    "buying_square": "buying_square.png",
    "price_tag": "price_tag.png",
    "reroll_board": "reroll_board.png",
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
