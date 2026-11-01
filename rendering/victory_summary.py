from dataclasses import dataclass

import pygame

from config.settings import LIGHT_TEXT, VICTORY_GOLD
from game.battle_summary import BattleSummary, RewardRow
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
CREAM = (245, 232, 210)
GOLD_BAND = (122, 74, 28)

ROW_COLORS = {
    "normal": INK,
    "bonus": (122, 78, 24),
    "relic": (112, 68, 18),
    "warning": (122, 42, 32),
}


@dataclass(frozen=True)
class SummaryFrames:
    center: pygame.Rect
    button: pygame.Rect
    row_height: int
    fallen: pygame.Rect


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
    center_w = 560 if width >= 1200 else 480
    center_w = min(center_w, max(280, width - margin * 2))
    row_h = 34 if height >= 780 else 28
    chrome = 342
    rows = max(1, len(summary.rows))
    piece_count = sum(group.count for group in summary.fallen)
    piece_band = 0 if piece_count == 0 else min(120, max(72, height // 8))
    gap = 18 if piece_count else 0
    floor = 12
    room = max(1, height - margin - floor - gap - piece_band)
    center_h = min(room, chrome + rows * row_h)
    if center_h > chrome:
        row_h = max(22, min(row_h, (center_h - chrome) // rows))
    block_h = min(chrome + rows * row_h, room)
    if piece_count:
        piece_top = (height - piece_band) // 2
        panel_top = piece_top + piece_band + gap
        if panel_top + block_h > height - floor:
            panel_top = height - floor - block_h
            piece_top = max(8, panel_top - gap - piece_band)
        fallen = pygame.Rect(margin, piece_top, max(1, width - margin * 2), piece_band)
    else:
        panel_top = max(margin, (height - block_h) // 2)
        fallen = pygame.Rect(0, 0, 0, 0)
    center = pygame.Rect(max(8, (width - center_w) // 2), panel_top, center_w, block_h)
    button = pygame.Rect(0, 0, min(280, center.w - 48), 50)
    button.center = (center.centerx, center.bottom - 42)
    return SummaryFrames(center, button, row_h, fallen)


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
    center = _panel_surface(frames.center)
    _draw_reward(center, summary, elapsed, show_button, reward, frames)
    _place(screen, center, frames.center, reveal)
    _draw_fallen_images(screen, assets, summary, frames.fallen, reveal)


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


def _fallen_icons(summary: BattleSummary) -> list[tuple[str, str | None]]:
    icons: list[tuple[str, str | None]] = []
    for group in summary.fallen:
        icons.extend((group.kind, group.trait) for _ in range(max(0, group.count)))
    return icons


def _draw_fallen_images(
    screen: pygame.Surface,
    assets: AssetManager,
    summary: BattleSummary,
    band: pygame.Rect,
    reveal: float,
) -> None:
    icons = _fallen_icons(summary)
    if not icons or band.w <= 0 or band.h <= 0:
        return
    gap = 16
    box = min(band.h, 112)
    while len(icons) * box + (len(icons) - 1) * gap > band.w and box > 32:
        box -= 2
    total = len(icons) * box + (len(icons) - 1) * gap
    x = band.centerx - total // 2
    for kind, trait in icons:
        piece = Piece(0, kind, "white", trait=trait)
        try:
            image = figurines.image(assets, piece, box)
        except (KeyError, pygame.error):
            image = pygame.Surface((box, box), pygame.SRCALPHA)
            pygame.draw.circle(image, BRASS, (box // 2, box // 2), max(4, box // 5))
        dest = image.get_rect(midleft=(x, band.centery))
        _place(screen, image, dest, reveal)
        x += box + gap


def _row_alpha(elapsed: float, index: int) -> float:
    if elapsed >= 2.0:
        return 1.0
    start = 0.16 + index * 0.05
    return ease_out_cubic(min(1.0, max(0.0, (elapsed - start) / 0.10)))
