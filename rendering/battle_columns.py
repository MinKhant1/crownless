import pygame

from config.settings import LABEL_TEXT, LIGHT_TEXT
from game.level_manager import describe_counts, formation_counts
from rendering.hud_renderer import _blit_text, draw_button, draw_glass, get_font


def draw_left_sidebar(screen: pygame.Surface, run, layout) -> None:
    rect = layout.left
    draw_glass(screen, rect)
    x = rect.x + 28
    block_h = 108
    y = rect.centery - block_h // 2
    y = min(y, layout.menu.y - 24 - block_h)
    y = max(rect.y + 28, y)
    _blit_text(screen, f"Battle: {run.level}", get_font(32, bold=True), LIGHT_TEXT, midleft=(x, y))
    coin = (x + 14, y + 48)
    pygame.draw.circle(screen, (120, 84, 32), coin, 13)
    pygame.draw.circle(screen, (232, 190, 78), coin, 10)
    _blit_text(screen, str(run.gold), get_font(28, bold=True), LIGHT_TEXT, midleft=(x + 36, coin[1]))
    deployed = run.deployment.non_king_count(run.army)
    _blit_text(
        screen,
        f"Army  {deployed} / {run.army.capacity}",
        get_font(22, bold=True),
        LIGHT_TEXT,
        midleft=(x, coin[1] + 44),
    )
    note_y = coin[1] + 76
    small = get_font(16, bold=False)
    if run.phase == "preview" and note_y < layout.menu.y - 20:
        _blit_text(screen, "Enemies", small, LABEL_TEXT, midleft=(x, note_y))
        note_y += 24
        for part in describe_counts(formation_counts(run.level)).split(", "):
            if note_y >= layout.menu.y - 16:
                break
            _blit_text(screen, part, small, LABEL_TEXT, midleft=(x, note_y))
            note_y += 22
    elif run.phase in ("battle", "victory", "defeat") and run.battle is not None and note_y < layout.menu.y - 20:
        living = sum(1 for piece in run.battle.game.board.pieces if piece.color == "white" and piece.kind != "king")
        _blit_text(screen, f"In play  {living}", small, LABEL_TEXT, midleft=(x, note_y))
        note_y += 24
    if run.notice and note_y < layout.menu.y - 16:
        _blit_text(screen, run.notice, small, (168, 64, 52), midleft=(x, note_y))
    draw_button(screen, layout.menu, "Main Menu", font_size=18)
    draw_button(screen, layout.options, "Options", font_size=18)
