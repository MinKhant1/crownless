from dataclasses import dataclass

import pygame

from config.settings import LIGHT_TEXT, VICTORY_GOLD
from game.battle_summary import BattleSummary, FallenGroup, RewardRow
from game.piece import Piece
from game.run_state import RunState
from game.transitions.easing import ease_out_cubic
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import _blit_text, get_font
from rendering.piece_visual_effects import figurines

INK = (62, 36, 22)
BRASS = (196, 146, 64)
PARCHMENT = (236, 220, 186)
PARCHMENT_EDGE = (92, 58, 32)
WOOD = (54, 32, 20)
WOOD_EDGE = (214, 170, 90)
CREAM = (245, 232, 210)
GOLD_BAND = (122, 74, 28)

FALLEN_HEADINGS = {
    "permanent": "Permanent Losses",
    "temporary": "Temporary Losses",
}

ROW_COLORS = {
    "normal": INK,
    "bonus": (122, 78, 24),
    "relic": (112, 68, 18),
    "warning": (122, 42, 32),
}


@dataclass(frozen=True)
class SummaryFrames:
    left: pygame.Rect
    center: pygame.Rect
    right: pygame.Rect
    button: pygame.Rect
    row_height: int


def summary_for(run: RunState) -> BattleSummary:
    if run.battle_summary is not None:
        return run.battle_summary
    return BattleSummary(
        battle_number=run.level,
        gold_before=max(0, run.gold - VICTORY_GOLD),
        gold_after=run.gold,
        army_count=sum(1 for piece in run.army.pieces if piece.kind != "king"),
        army_capacity=run.army.capacity,
        surviving=len(run.army.pieces),
        rows=(RewardRow("Battle Win", VICTORY_GOLD, "normal"),),
    )


def continue_rect(window: tuple[int, int], run: RunState) -> pygame.Rect:
    return summary_frames(window, summary_for(run)).button


def summary_frames(window: tuple[int, int], summary: BattleSummary) -> SummaryFrames:
    width, height = window
    margin = 20 if width < 1100 else 32
    gap = 14 if width < 1100 else 18
    left_w = 200 if width < 1100 else 240
    right_w = 210 if width < 1100 else 268
    center_w = 560 if width >= 1200 else 480
    while left_w + center_w + right_w + gap * 2 > width - 16:
        if center_w > 400:
            center_w -= 8
        elif right_w > 176:
            right_w -= 4
        elif left_w > 168:
            left_w -= 4
        else:
            break
    group = left_w + center_w + right_w + gap * 2
    row_h = 34 if height >= 780 else 28
    chrome = 342
    rows = max(1, len(summary.rows))
    center_h = min(height - margin * 2, chrome + rows * row_h)
    row_h = max(22, min(row_h, (center_h - chrome) // rows))
    block_h = chrome + rows * row_h
    block_h = min(block_h, height - margin * 2)
    origin_x = max(8, (width - group) // 2)
    origin_y = max(12, (height - block_h) // 2)
    left = pygame.Rect(origin_x, origin_y, left_w, block_h)
    center = pygame.Rect(left.right + gap, origin_y, center_w, block_h)
    right = pygame.Rect(center.right + gap, origin_y, right_w, block_h)
    button = pygame.Rect(0, 0, min(280, center.w - 48), 50)
    button.center = (center.centerx, center.bottom - 42)
    return SummaryFrames(left, center, right, button, row_h)


def draw_victory_summary(
    screen: pygame.Surface,
    assets: AssetManager,
    run: RunState,
    elapsed: float,
    show_button: bool,
    reward: float,
) -> None:
    summary = summary_for(run)
    frames = summary_frames(screen.get_size(), summary)
    reveal = 1.0 if elapsed >= 0.32 else ease_out_cubic(min(1.0, max(0.0, elapsed) / 0.32))
    shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    shade.fill((16, 9, 4, int(158 * reveal)))
    screen.blit(shade, (0, 0))
    _fade_panel(screen, frames.left, reveal, lambda plate: _draw_status(plate, summary))
    _fade_panel(screen, frames.right, reveal, lambda plate: _draw_fallen(plate, assets, summary))
    center = _panel_surface(frames.center)
    _draw_reward(center, summary, elapsed, show_button, reward, frames)
    _place(screen, center, frames.center, reveal)


def _fade_panel(screen: pygame.Surface, rect: pygame.Rect, reveal: float, paint) -> None:
    plate = _panel_surface(rect)
    paint(plate)
    _place(screen, plate, rect, reveal)


def _place(screen: pygame.Surface, plate: pygame.Surface, rect: pygame.Rect, reveal: float) -> None:
    if reveal >= 0.995:
        screen.blit(plate, rect.topleft)
        return
    scale = 0.94 + 0.06 * reveal
    sized = (
        max(1, int(rect.w * scale)),
        max(1, int(rect.h * scale)),
    )
    image = pygame.transform.smoothscale(plate, sized)
    image.set_alpha(int(255 * reveal))
    screen.blit(image, image.get_rect(center=rect.center))


def _panel_surface(rect: pygame.Rect) -> pygame.Surface:
    plate = pygame.Surface((max(1, rect.w), max(1, rect.h)), pygame.SRCALPHA)
    body = plate.get_rect()
    pygame.draw.rect(plate, (20, 12, 8, 90), body.move(0, 8), border_radius=18)
    pygame.draw.rect(plate, PARCHMENT, body, border_radius=16)
    pygame.draw.rect(plate, PARCHMENT_EDGE, body, width=3, border_radius=16)
    inner = body.inflate(-12, -12)
    pygame.draw.rect(plate, BRASS, inner, width=1, border_radius=12)
    return plate


def _draw_status(plate: pygame.Surface, summary: BattleSummary) -> None:
    wood = plate.get_rect().inflate(-18, -18)
    pygame.draw.rect(plate, WOOD, wood, border_radius=12)
    pygame.draw.rect(plate, WOOD_EDGE, wood, width=2, border_radius=12)
    rows = (
        ("Battle", str(summary.battle_number)),
        ("Gold", str(summary.gold_after)),
        ("Army Size", f"{summary.army_count} / {summary.army_capacity}"),
        ("Surviving", str(summary.surviving)),
        ("Fallen", str(summary.fallen_count)),
    )
    font = get_font(15, bold=False)
    value_font = get_font(22, bold=True)
    gap = 8
    row_h = max(36, (wood.h - 16 - gap * (len(rows) - 1)) // len(rows))
    y = wood.y + 8
    for label, value in rows:
        card = pygame.Rect(wood.x + 10, y, wood.w - 20, row_h)
        pygame.draw.rect(plate, (74, 44, 26), card, border_radius=8)
        pygame.draw.rect(plate, (168, 124, 64), card, width=1, border_radius=8)
        _blit_text(plate, label, font, (214, 186, 146), midleft=(card.x + 12, card.centery))
        value_w = value_font.size(value)[0]
        _blit_text(plate, value, value_font, CREAM, midleft=(card.right - 12 - value_w, card.centery))
        y += row_h + gap


def _draw_reward(
    plate: pygame.Surface,
    summary: BattleSummary,
    elapsed: float,
    show_button: bool,
    reward: float,
    frames: SummaryFrames,
) -> None:
    title = get_font(40 if plate.get_width() >= 520 else 32, bold=True)
    _blit_text(plate, "BATTLE WON", title, INK, center=(plate.get_width() // 2, 46))
    pygame.draw.line(plate, BRASS, (36, 74), (plate.get_width() - 36, 74), 2)
    band = pygame.Rect(28, 88, plate.get_width() - 56, 70)
    pygame.draw.rect(plate, GOLD_BAND, band, border_radius=12)
    pygame.draw.rect(plate, (232, 196, 110), band, width=2, border_radius=12)
    shown = summary.total_gold if show_button else int(round(summary.total_gold * min(1.0, max(0.0, reward))))
    _blit_text(plate, "Cash Out", get_font(16, bold=False), (236, 210, 160), center=(band.centerx, band.y + 20))
    _blit_text(plate, f"+{shown} Gold", get_font(32, bold=True), CREAM, center=(band.centerx, band.y + 46))
    y = band.bottom + 16
    for index, row in enumerate(summary.rows):
        amount = _row_alpha(elapsed, index)
        if amount <= 0:
            y += frames.row_height
            continue
        _draw_row(plate, row, y, frames.row_height, amount)
        y += frames.row_height
    total_alpha = _row_alpha(elapsed, len(summary.rows))
    if total_alpha > 0:
        _draw_total(plate, summary, y, total_alpha)
    footer = get_font(15, bold=False)
    foot_y = y + 70
    _blit_text(plate, f"Gold Before  {summary.gold_before}", footer, (112, 78, 52), midleft=(32, foot_y))
    after = f"Gold After  {summary.gold_after}"
    _blit_text(plate, after, footer, (112, 78, 52), midleft=(plate.get_width() - 32 - footer.size(after)[0], foot_y))
    if show_button:
        local = frames.button.move(-frames.center.x, -frames.center.y)
        _draw_continue(plate, local, frames.button)


def _draw_row(plate: pygame.Surface, row: RewardRow, y: int, height: int, alpha: float) -> None:
    font = get_font(18, bold=row.style == "relic")
    color = ROW_COLORS.get(row.style, INK)
    label = row.label if not row.source else f"{row.label}"
    amount = f"+{row.amount} rerolls" if row.source == "Shop Rerolls" else str(row.amount)
    left = 32
    if row.style == "relic":
        pip = pygame.Rect(left, y + height // 2 - 4, 8, 8)
        pygame.draw.rect(plate, BRASS, pip, border_radius=2)
        left += 16
    amount_w = font.size(amount)[0]
    right = plate.get_width() - 32
    _blit_text(plate, label, font, color, midleft=(left, y + height // 2))
    _blit_text(plate, amount, font, color, midleft=(right - amount_w, y + height // 2))
    label_end = left + font.size(label)[0] + 8
    dot_end = right - amount_w - 8
    if dot_end > label_end:
        step = 7
        dot_y = y + height // 2
        for x in range(label_end, dot_end, step):
            pygame.draw.circle(plate, (176, 146, 104), (x, dot_y), 1)
    if alpha < 0.99:
        veil = pygame.Surface((plate.get_width() - 40, height), pygame.SRCALPHA)
        veil.fill((236, 220, 186, int(255 * (1.0 - alpha))))
        plate.blit(veil, (20, y))


def _draw_total(plate: pygame.Surface, summary: BattleSummary, y: int, alpha: float) -> None:
    font = get_font(20, bold=True)
    bar = pygame.Rect(24, y + 4, plate.get_width() - 48, 36)
    pygame.draw.rect(plate, (214, 186, 140), bar, border_radius=8)
    _blit_text(plate, "Total Gold Earned", font, INK, midleft=(bar.x + 12, bar.centery))
    amount = str(summary.total_gold)
    _blit_text(plate, amount, font, INK, midleft=(bar.right - 16 - font.size(amount)[0], bar.centery))
    if alpha < 0.99:
        veil = pygame.Surface((bar.w, bar.h), pygame.SRCALPHA)
        veil.fill((236, 220, 186, int(255 * (1.0 - alpha))))
        plate.blit(veil, bar.topleft)


def _draw_continue(plate: pygame.Surface, rect: pygame.Rect, screen_rect: pygame.Rect) -> None:
    pointer = pygame.mouse.get_pos() if pygame.display.get_surface() is not None else (-1, -1)
    hovered = screen_rect.collidepoint(pointer)
    pressed = hovered and pygame.mouse.get_pressed()[0]
    drawn = rect.move(0, 2) if pressed else rect
    pygame.draw.rect(plate, (36, 20, 10), drawn.move(0, 3), border_radius=12)
    fill = (138, 84, 34) if hovered else (98, 58, 28)
    pygame.draw.rect(plate, fill, drawn, border_radius=12)
    pygame.draw.rect(plate, (232, 196, 110), drawn, width=2, border_radius=12)
    _blit_text(plate, "Continue", get_font(22, bold=True), LIGHT_TEXT, center=drawn.center)


def _draw_fallen(plate: pygame.Surface, assets: AssetManager, summary: BattleSummary) -> None:
    _blit_text(plate, "FALLEN PIECES", get_font(22, bold=True), INK, center=(plate.get_width() // 2, 36))
    pygame.draw.line(plate, BRASS, (24, 58), (plate.get_width() - 24, 58), 2)
    if summary.flawless:
        badge = pygame.Rect(20, 78, plate.get_width() - 40, 78)
        pygame.draw.rect(plate, (168, 112, 36), badge, border_radius=12)
        pygame.draw.rect(plate, (236, 206, 120), badge, width=2, border_radius=12)
        _blit_text(plate, "Flawless Victory", get_font(20, bold=True), CREAM, center=(badge.centerx, badge.y + 28))
        _blit_text(plate, "No pieces lost", get_font(16, bold=False), (255, 236, 204), center=(badge.centerx, badge.y + 52))
        return
    y = 72
    sections = _fallen_sections(summary)
    headings = len(sections) > 1
    for category, groups in sections:
        if headings or category != "permanent":
            _blit_text(plate, FALLEN_HEADINGS.get(category, category.title()), get_font(14, bold=True), (122, 78, 24), midleft=(24, y + 8))
            y += 24
        for group in groups:
            y = _draw_fallen_row(plate, assets, group, y)
            if y > plate.get_height() - 24:
                return


def _fallen_sections(summary: BattleSummary) -> list[tuple[str, list[FallenGroup]]]:
    order: list[str] = []
    for group in summary.fallen:
        if group.category not in order:
            order.append(group.category)
    return [(category, [group for group in summary.fallen if group.category == category]) for category in order]


def _draw_fallen_row(plate: pygame.Surface, assets: AssetManager, group: FallenGroup, y: int) -> int:
    icon = pygame.Rect(22, y, 36, 36)
    piece = Piece(0, group.kind, "white", trait=group.trait)
    try:
        image = figurines.image(assets, piece, 34)
        plate.blit(image, image.get_rect(center=icon.center))
    except (KeyError, pygame.error):
        pygame.draw.circle(plate, BRASS, icon.center, 10)
    font = get_font(18, bold=False)
    _blit_text(plate, group.name, font, INK, midleft=(64, icon.centery))
    count = f"×{group.count}"
    _blit_text(plate, count, get_font(18, bold=True), INK, midleft=(plate.get_width() - 24 - font.size(count)[0], icon.centery))
    return y + 42


def _row_alpha(elapsed: float, index: int) -> float:
    if elapsed >= 2.0:
        return 1.0
    start = 0.16 + index * 0.05
    return ease_out_cubic(min(1.0, max(0.0, (elapsed - start) / 0.10)))
