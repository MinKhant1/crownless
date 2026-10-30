import pygame

from config.settings import LABEL_TEXT, LIGHT_TEXT, MOVE_DOT
from game.army_roster import ArmyEntry, listed_pieces, piece_status
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import _blit_text, draw_glass, get_font
from rendering.layout import Layout
from rendering.overlay_renderer import trait_tooltip_lines
from rendering.piece_renderer import draw_trait_sprite


RANKS = ("king", "queen", "rook", "bishop", "knight", "pawn")


class ArmyPanel:
    def __init__(self) -> None:
        self.scroll = 0
        self.hover_id: int | None = None
        self._mix: dict[int, float] = {}

    def accepts(self, run) -> bool:
        return run.phase == "deployment"

    def rows(self, run, layout: Layout) -> list[tuple[ArmyEntry, pygame.Rect]]:
        _panel_rect, view, icon, _gap, sections = self._sections(run, layout)
        placed: list[tuple[ArmyEntry, pygame.Rect]] = []
        for _kind, section, pieces in sections:
            if section.bottom <= view.top or section.top >= view.bottom:
                continue
            for index, piece in enumerate(pieces):
                rect = _icon_rect(section, icon, index)
                if rect.bottom <= view.top or rect.top >= view.bottom:
                    continue
                visible = rect.clip(view)
                if visible.w < 8 or visible.h < 8:
                    continue
                placed.append((ArmyEntry(piece, (piece,), piece_status(run, piece)), visible))
        return placed

    def icon_rects(self, run, layout: Layout) -> list[tuple[int, pygame.Rect]]:
        if not self.accepts(run):
            return []
        rects: list[tuple[int, pygame.Rect]] = []
        for entry, rect in self.rows(run, layout):
            if run.army.piece_by_id(entry.piece.id) is None:
                continue
            rects.append((entry.piece.id, rect))
        return rects

    def hover_at(self, run, layout: Layout, pos: tuple[int, int]) -> None:
        self.hover_id = None
        if not layout.right.collidepoint(pos):
            return
        for entry, rect in self.rows(run, layout):
            if rect.collidepoint(pos):
                self.hover_id = entry.piece.id
                return

    def on_wheel(self, run, layout: Layout, pos: tuple[int, int], amount: int) -> bool:
        if not layout.right.collidepoint(pos):
            return False
        self.scroll -= int(amount) * 48
        self._sections(run, layout)
        return True

    def draw(self, screen: pygame.Surface, assets: AssetManager, run, layout: Layout) -> None:
        _panel(screen, layout.right)
        _blit_text(screen, "Your Army", get_font(22, bold=True), LIGHT_TEXT, midleft=(layout.right.x + 18, layout.right.y + 22))
        _panel_rect, view, icon, _gap, sections = self._sections(run, layout)
        previous = screen.get_clip()
        screen.set_clip(view)
        tooltip: tuple[ArmyEntry, pygame.Rect] | None = None
        for _kind, section, pieces in sections:
            if section.bottom <= view.top or section.top >= view.bottom:
                continue
            _section_box(screen, section.clip(view))
            for index, piece in enumerate(pieces):
                rect = _icon_rect(section, icon, index)
                if not rect.colliderect(view):
                    continue
                entry = ArmyEntry(piece, (piece,), piece_status(run, piece))
                self._draw_icon(screen, assets, run, entry, rect)
                if self.hover_id == piece.id and piece.trait:
                    tooltip = (entry, rect)
        screen.set_clip(previous)
        if tooltip is not None:
            _tooltip(screen, tooltip[0], tooltip[1])

    def _sections(self, run, layout: Layout):
        panel = layout.right.inflate(-12, -12)
        view = pygame.Rect(panel.x, panel.y + 36, panel.w, max(1, panel.bottom - (panel.y + 36)))
        icon = min(76, max(40, (view.w - 28) // 3))
        gap = 8
        groups = {rank: [] for rank in RANKS}
        for piece in listed_pieces(run):
            if piece.kind not in groups:
                continue
            if piece_status(run, piece) in ("Deployed", "Surviving"):
                continue
            groups[piece.kind].append(piece)
        for rank in RANKS:
            groups[rank].sort(key=lambda piece: piece.id)
        content = 0
        heights: list[int] = []
        for rank in RANKS:
            count = len(groups[rank])
            if count == 0:
                heights.append(0)
                continue
            rows = (count + 2) // 3
            height = 12 + rows * (icon + 6)
            heights.append(height)
            content += height + gap
        content = max(0, content - gap)
        self.scroll = max(0, min(self.scroll, max(0, content - view.h)))
        y = view.y - self.scroll
        sections = []
        for rank, height in zip(RANKS, heights):
            if height <= 0:
                continue
            section = pygame.Rect(view.x + 4, y, view.w - 8, height)
            sections.append((rank, section, groups[rank]))
            y += height + gap
        return panel, view, icon, gap, sections

    def _draw_icon(self, screen: pygame.Surface, assets: AssetManager, run, entry: ArmyEntry, rect: pygame.Rect) -> None:
        hot = self.hover_id == entry.piece.id
        selected = run.selected_piece_id == entry.piece.id
        mix = self._mix.get(entry.piece.id, 0.0)
        mix += ((1.0 if hot or selected else 0.0) - mix) * 0.35
        self._mix[entry.piece.id] = mix
        shift = int(round(4 * mix))
        drawn = rect.move(-shift, 0)
        if entry.status == "Captured":
            fill = (186, 166, 146)
            border = (168, 64, 52)
        elif entry.status in ("Deployed", "Surviving"):
            fill = (236, 220, 196)
            border = MOVE_DOT
        else:
            fill = (226, 208, 180)
            border = (120, 86, 48)
        if hot:
            fill = (236, 220, 196)
        if selected:
            fill = (214, 186, 140)
            border = (214, 170, 90)
        pygame.draw.rect(screen, fill, drawn, border_radius=8)
        pygame.draw.rect(screen, border, drawn, width=3 if selected else 2, border_radius=8)
        icon = drawn.inflate(-8, -8)
        draw_trait_sprite(screen, assets, entry.piece, icon, max(8, icon.w - 2))


def _icon_rect(section: pygame.Rect, icon: int, index: int) -> pygame.Rect:
    column = index % 3
    row = index // 3
    return pygame.Rect(section.x + 8 + column * (icon + 6), section.y + 6 + row * (icon + 6), icon, icon)


def _section_box(screen: pygame.Surface, rect: pygame.Rect) -> None:
    draw_glass(screen, rect, radius=10)


def _tooltip(screen: pygame.Surface, entry: ArmyEntry, rect: pygame.Rect) -> None:
    lines = trait_tooltip_lines(entry.piece)
    if lines is None:
        return
    title, body = lines
    width = 230
    body_font = get_font(13, bold=False)
    wrapped = _wrap(body_font, body, width - 20)
    height = 36 + len(wrapped) * 18
    panel = pygame.Rect(rect.left - width - 10, rect.y, width, height)
    if panel.left < 8:
        panel.left = rect.right + 8
    panel.clamp_ip(screen.get_rect())
    pygame.draw.rect(screen, (42, 28, 20), panel, border_radius=8)
    pygame.draw.rect(screen, (214, 170, 90), panel, width=2, border_radius=8)
    _blit_text(screen, title, get_font(15, bold=True), (236, 210, 140), midleft=(panel.x + 10, panel.y + 16))
    y = panel.y + 36
    for line in wrapped:
        _blit_text(screen, line, body_font, LABEL_TEXT, midleft=(panel.x + 10, y))
        y += 18


def _wrap(font: pygame.font.Font, text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if font.size(trial)[0] <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _panel(screen: pygame.Surface, rect: pygame.Rect) -> None:
    draw_glass(screen, rect)
