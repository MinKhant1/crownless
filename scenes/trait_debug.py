import pygame

from game.piece import Piece
from game.run_state import RunState
from game.traits import TRAITS
from rendering.hud_renderer import _blit_text, draw_button, get_font
from rendering.layout import Layout, square_at


OPTIONS = (("None", None),) + tuple((trait.name, trait.id) for trait in TRAITS)


class TraitDebug:
    def __init__(self) -> None:
        self.enabled = False
        self.target_id: int | None = None

    def toggle(self) -> None:
        self.enabled = not self.enabled
        self.target_id = None

    def hits(
        self,
        pos: tuple[int, int],
        layout: Layout,
        window: tuple[int, int],
        icons: list[tuple[int, pygame.Rect]] | None = None,
    ) -> bool:
        if not self.enabled:
            return False
        if any(rect.collidepoint(pos) for _label, _trait_id, rect in self.entries(window)):
            return True
        if icons:
            for _piece_id, rect in icons:
                if rect.collidepoint(pos):
                    return True
        return square_at(layout, pos) is not None

    def on_click(
        self,
        run: RunState,
        pos: tuple[int, int],
        layout: Layout,
        window: tuple[int, int],
        icons: list[tuple[int, pygame.Rect]] | None = None,
    ) -> None:
        if not self.enabled:
            return
        for _label, trait_id, rect in self.entries(window):
            if not rect.collidepoint(pos):
                continue
            if self.target_id is None:
                return
            if trait_id is None:
                run.traits.remove_trait(self.target_id)
            else:
                run.traits.assign_trait(self.target_id, trait_id, overwrite=True)
            return
        if icons:
            for piece_id, rect in icons:
                if rect.collidepoint(pos):
                    self.target_id = piece_id
                    return
        square = square_at(layout, pos)
        if square is None:
            return
        piece = _piece_at(run, square)
        self.target_id = None if piece is None else piece.id

    def entries(self, window: tuple[int, int]) -> list[tuple[str, str | None, pygame.Rect]]:
        width = 148
        height = 30
        x = max(8, window[0] - width - 16)
        y = 58
        rows = []
        for index, (label, trait_id) in enumerate(OPTIONS):
            rows.append((label, trait_id, pygame.Rect(x, y + index * 34, width, height)))
        return rows

    def draw(self, screen: pygame.Surface, run: RunState) -> None:
        if not self.enabled:
            return
        rows = self.entries(screen.get_size())
        panel = rows[0][2].unionall([row[2] for row in rows]).inflate(16, 44)
        panel.top -= 28
        pygame.draw.rect(screen, (36, 24, 18), panel, border_radius=10)
        pygame.draw.rect(screen, (214, 170, 90), panel, width=2, border_radius=10)
        _blit_text(screen, "Traits", get_font(18, bold=True), (244, 226, 196), midleft=(panel.x + 10, panel.y + 16))
        current = _piece_by_id(run, self.target_id)
        caption = "Click a piece" if current is None else f"{current.kind.capitalize()}  {current.trait or 'None'}"
        _blit_text(screen, caption, get_font(13, bold=False), (226, 210, 188), midleft=(panel.x + 78, panel.y + 16))
        for label, trait_id, rect in rows:
            selected = current is not None and current.trait == trait_id
            draw_button(screen, rect, label, font_size=15)
            if selected:
                pygame.draw.rect(screen, (244, 220, 140), rect, width=2, border_radius=10)


def _piece_at(run: RunState, square: tuple[int, int]) -> Piece | None:
    if run.phase == "battle" and run.battle is not None:
        return run.battle.game.board.piece_at(*square)
    for enemy in run.enemies:
        if (enemy.col, enemy.row) == square:
            return enemy
    piece_id = run.deployment.piece_id_at(*square)
    if piece_id is None:
        return None
    return run.army.piece_by_id(piece_id)


def _piece_by_id(run: RunState, piece_id: int | None) -> Piece | None:
    if piece_id is None:
        return None
    if run.battle is not None:
        live = run.battle.game.board.piece_by_id(piece_id)
        if live is not None:
            return live
    piece = run.army.piece_by_id(piece_id)
    if piece is not None:
        return piece
    for enemy in run.enemies:
        if enemy.id == piece_id:
            return enemy
    return None
