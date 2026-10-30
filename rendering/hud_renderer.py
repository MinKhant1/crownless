import pygame

from config.settings import (
    ARMY_TEXT_CENTER,
    DEBUG_PANEL,
    DEBUG_TEXT,
    DARK_TEXT,
    FILES,
    LABEL_TEXT,
    LEVEL_TEXT_X,
    LIGHT_TEXT,
    RESULT_TEXT,
    TURN_CHECK,
    TURN_TEXT,
    square_name,
)
from game.game import Game
from game.turn_manager import TurnManager
from rendering.asset_manager import AssetManager
from rendering.layout import Layout
from rendering.wood_swirl import wood_swirl

_FONTS: dict[tuple[int, bool], pygame.font.Font] = {}


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    size = max(10, int(size))
    key = (size, bold)
    font = _FONTS.get(key)
    if font is None:
        font = pygame.font.SysFont("georgia", size, bold=bold)
        _FONTS[key] = font
    return font


def level_text(level: int) -> str:
    return f"Lvl: {level}"


def army_text(size: int, capacity: int) -> str:
    return f"{size} / {capacity}"


def turn_text(turns: TurnManager) -> str:
    if turns.battle_state == "checkmate" and turns.winner:
        winner = "White" if turns.winner == "white" else "Black"
        return f"Checkmate - {winner} wins"
    if turns.battle_state == "stalemate":
        return "Stalemate"
    name = "White" if turns.current == "white" else "Black"
    return f"{name}'s Turn"


def draw_glass(screen: pygame.Surface, rect: pygame.Rect, radius: int = 16) -> None:
    plate = pygame.Surface((max(1, rect.w), max(1, rect.h)), pygame.SRCALPHA)
    body = plate.get_rect()
    pygame.draw.rect(plate, (255, 255, 255, 16), body, border_radius=radius)
    pygame.draw.rect(plate, (255, 255, 255, 78), body, width=1, border_radius=radius)
    screen.blit(plate, rect.topleft)


def draw_relic_glow(screen: pygame.Surface, rect: pygame.Rect) -> None:
    pad = 5
    plate = pygame.Surface((max(1, rect.w + pad * 2), max(1, rect.h + pad * 2)), pygame.SRCALPHA)
    pygame.draw.rect(plate, (232, 196, 96, 150), plate.get_rect(), width=2, border_radius=10)
    screen.blit(plate, (rect.x - pad, rect.y - pad))


def draw_button(
    screen: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    enabled: bool = True,
    font_size: int = 22,
) -> None:
    fill = (72, 42, 28) if enabled else (54, 44, 38)
    border = (214, 170, 90) if enabled else (120, 104, 84)
    text = LIGHT_TEXT if enabled else (168, 156, 142)
    pygame.draw.rect(screen, fill, rect, border_radius=10)
    pygame.draw.rect(screen, border, rect, width=2, border_radius=10)
    _blit_text(screen, label, get_font(font_size, bold=True), text, center=rect.center)


def _blit_text(
    screen: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    center: tuple[int, int] | None = None,
    midleft: tuple[int, int] | None = None,
) -> None:
    surface = font.render(text, True, color)
    rect = surface.get_rect()
    if center is not None:
        rect.center = center
    elif midleft is not None:
        rect.midleft = midleft
    screen.blit(surface, rect)


def draw_background(screen: pygame.Surface, assets: AssetManager) -> None:
    wood_swirl.ensure(assets.root / "backgrounds" / "wood_swirl.png")
    wood_swirl.draw(screen)


def draw_header_and_status(
    screen: pygame.Surface,
    assets: AssetManager,
    game: Game,
    layout: Layout,
) -> None:
    header = assets.scaled("header", (layout.header.w, layout.header.h))
    status = assets.scaled("status", (layout.status.w, layout.status.h))
    screen.blit(header, layout.header.topleft)
    screen.blit(status, layout.status.topleft)
    font = get_font(layout.status.h * 0.46, bold=True)
    _blit_text(
        screen,
        level_text(game.current_level),
        font,
        DARK_TEXT,
        midleft=(layout.status.x + int(layout.status.w * LEVEL_TEXT_X), layout.status.centery),
    )
    _blit_text(
        screen,
        army_text(game.army_size, game.army_capacity),
        font,
        LIGHT_TEXT,
        center=(layout.status.x + int(layout.status.w * ARMY_TEXT_CENTER), layout.status.centery),
    )


def draw_crown(screen: pygame.Surface, assets: AssetManager, layout: Layout) -> None:
    crown = assets.scaled("crown", (layout.crown.w, layout.crown.h))
    screen.blit(crown, layout.crown.topleft)


def draw_labels(screen: pygame.Surface, layout: Layout) -> None:
    font = get_font(max(15, layout.square // 5), bold=False)
    for col, letter in enumerate(FILES):
        rect = layout.square_rect(col, 1)
        _blit_text(screen, letter, font, LABEL_TEXT, center=(rect.centerx, layout.frame.bottom + 14))
    for row in range(1, 7):
        rect = layout.square_rect(0, row)
        surface = font.render(str(row), True, LABEL_TEXT)
        destination = surface.get_rect()
        destination.centery = rect.centery
        destination.right = layout.frame.left - 10
        screen.blit(surface, destination)


def draw_turn(screen: pygame.Surface, game: Game, layout: Layout) -> None:
    finished = game.turns.finished
    if game.turns.in_check and not finished:
        color = TURN_CHECK
    elif finished:
        color = RESULT_TEXT
    else:
        color = TURN_TEXT
    font = get_font(max(20, layout.turn.h - 8), bold=True)
    _blit_text(screen, turn_text(game.turns), font, color, center=layout.turn.center)


def _move_label(game: Game) -> str:
    move = game.last_move
    if move is None:
        return "-"
    start = square_name(move.from_col, move.from_row)
    end = square_name(move.to_col, move.to_row)
    link = "x" if game.last_capture_id is not None else "-"
    suffix = "=Q" if move.promotion else ""
    return f"{start}{link}{end}{suffix}"


def _wrap(text: str, limit: int = 36) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if len(trial) > limit:
            lines.append(current)
            current = word
        else:
            current = trial
    lines.append(current)
    return lines


def draw_debug(screen: pygame.Surface, game: Game, layout: Layout) -> None:
    selected = game.selected_piece()
    selected_name = square_name(selected.col, selected.row) if selected is not None else "-"
    if game.legal:
        move_names = " ".join(square_name(move.to_col, move.to_row) for move in game.legal)
    else:
        move_names = "-"
    if game.hover is None:
        hover = "-"
    else:
        hover = f"{square_name(*game.hover)}  col {game.hover[0]}  row {game.hover[1]}"
    lines = [
        f"Turn: {game.turns.current}",
        f"State: {game.turns.battle_state}",
        f"Selected: {selected_name}",
        "Moves:",
    ]
    lines.extend(_wrap(move_names) if move_names != "-" else ["-"])
    lines.append(f"Last: {_move_label(game)}")
    lines.append(f"Square: {hover}")
    font = get_font(16, bold=False)
    rendered = [font.render(line, True, DEBUG_TEXT) for line in lines]
    width = max(surface.get_width() for surface in rendered) + 28
    height = 16 + sum(surface.get_height() + 4 for surface in rendered)
    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    panel.fill(DEBUG_PANEL)
    y = 8
    for surface in rendered:
        panel.blit(surface, (14, y))
        y += surface.get_height() + 4
    x = layout.left.x + 10
    y_pos = max(layout.left.y + 150, layout.menu.y - height - 12)
    screen.blit(panel, (x, y_pos))
