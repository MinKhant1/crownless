import pygame

from game.army_roster import ArmyEntry, listed_pieces, piece_status
from rendering import style
from rendering.asset_manager import AssetManager
from rendering.layout import Layout
from rendering.overlay_renderer import trait_tooltip_lines
from rendering.piece_renderer import draw_trait_sprite


RANKS = ("king", "queen", "rook", "bishop", "knight", "pawn")
GROUPS = (("reserve", "Reserve"), ("board", "On the Board"), ("fallen", "Fallen"))
HEADING = (214, 176, 104)
HEADING_H = 28
GROUP_GAP = 12


class ArmyPanel:
    def __init__(self) -> None:
        self.scroll = 0
        self.hover_id: int | None = None
        self._mix: dict[int, float] = {}

    def accepts(self, run) -> bool:
        return run.phase == "deployment"

    def rows(self, run, layout: Layout) -> list[tuple[ArmyEntry, pygame.Rect]]:
        """Reserve and fallen pieces: the rows a click or a drag can reach."""
        return [(entry, rect) for key, entry, rect in self._placed(run, layout) if key != "board"]

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
        for _key, entry, rect in self._placed(run, layout):
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
        style.draw_wood_panel(screen, layout.right, seed=2)
        title = style.title_font(22, bold=True)
        style.text(screen, "Your Army", title, style.IVORY, shadow=(8, 4, 2, 220), center=(layout.right.centerx, layout.right.y + 30))
        style.ornament_rule(screen, (layout.right.centerx, layout.right.y + 52), layout.right.w - 48, style.GOLD_DIM)
        view, icon, groups = self._sections(run, layout)
        previous = screen.get_clip()
        screen.set_clip(view)
        tooltip: tuple[ArmyEntry, pygame.Rect] | None = None
        for key, label, heading, grid, pieces in groups:
            if heading.bottom > view.top and heading.top < view.bottom:
                count = f"{label}  \u00b7  {len(pieces)}"
                style.text(screen, count, style.title_font(15, bold=False), HEADING, shadow=(8, 4, 2, 200), midleft=(heading.x + 6, heading.centery))
            for index, piece in enumerate(pieces):
                rect = _icon_rect(grid, icon, index)
                if not rect.colliderect(view):
                    continue
                entry = ArmyEntry(piece, (piece,), piece_status(run, piece))
                self._draw_icon(screen, assets, run, entry, rect, key)
                if self.hover_id == piece.id and piece.trait:
                    tooltip = (entry, rect)
        screen.set_clip(previous)
        if tooltip is not None:
            _tooltip(screen, assets, tooltip[0], tooltip[1])

    def _placed(self, run, layout: Layout) -> list[tuple[str, ArmyEntry, pygame.Rect]]:
        view, icon, groups = self._sections(run, layout)
        placed: list[tuple[str, ArmyEntry, pygame.Rect]] = []
        for key, _label, _heading, grid, pieces in groups:
            if grid.bottom <= view.top or grid.top >= view.bottom:
                continue
            for index, piece in enumerate(pieces):
                rect = _icon_rect(grid, icon, index)
                if rect.bottom <= view.top or rect.top >= view.bottom:
                    continue
                visible = rect.clip(view)
                if visible.w < 8 or visible.h < 8:
                    continue
                placed.append((key, ArmyEntry(piece, (piece,), piece_status(run, piece)), visible))
        return placed

    def _sections(self, run, layout: Layout):
        panel = layout.right.inflate(-24, -24)
        top = layout.right.y + 66
        view = pygame.Rect(panel.x, top, panel.w, max(1, panel.bottom - top))
        icon = min(76, max(40, (view.w - 28) // 3))
        buckets: dict[str, list] = {key: [] for key, _label in GROUPS}
        for piece in listed_pieces(run):
            if piece.kind not in RANKS:
                continue
            buckets[_group(piece_status(run, piece))].append(piece)
        for pieces in buckets.values():
            pieces.sort(key=lambda piece: (RANKS.index(piece.kind), piece.id))
        laid: list[tuple[str, str, int, list]] = []
        content = 0
        for key, label in GROUPS:
            pieces = buckets[key]
            if not pieces:
                continue
            rows = (len(pieces) + 2) // 3
            height = HEADING_H + rows * (icon + 6) + 4
            laid.append((key, label, height, pieces))
            content += height + GROUP_GAP
        content = max(0, content - GROUP_GAP)
        self.scroll = max(0, min(self.scroll, max(0, content - view.h)))
        y = view.y - self.scroll
        groups = []
        for key, label, height, pieces in laid:
            heading = pygame.Rect(view.x + 4, y, view.w - 8, HEADING_H)
            grid = pygame.Rect(view.x + 4, y + HEADING_H, view.w - 8, height - HEADING_H)
            groups.append((key, label, heading, grid, pieces))
            y += height + GROUP_GAP
        return view, icon, groups

    def _draw_icon(self, screen: pygame.Surface, assets: AssetManager, run, entry: ArmyEntry, rect: pygame.Rect, group: str) -> None:
        hot = self.hover_id == entry.piece.id
        selected = run.selected_piece_id == entry.piece.id
        mix = self._mix.get(entry.piece.id, 0.0)
        mix += ((1.0 if hot or selected else 0.0) - mix) * 0.35
        self._mix[entry.piece.id] = mix
        shift = int(round(4 * mix))
        drawn = rect.move(-shift, 0)
        style.drop_shadow(screen, drawn, offset=3, spread=4, alpha=110, radius=4)
        screen.blit(style.parchment(assets, drawn.size, seed=drawn.w, worn=False), drawn.topleft)
        if selected:
            border, width = style.GOLD_BRIGHT, 3
        elif hot:
            border, width = style.GOLD, 2
        elif group == "board":
            border, width = (88, 120, 70), 2
        else:
            border, width = (112, 78, 44), 2
        pygame.draw.rect(screen, border, drawn, width=width)
        icon = drawn.inflate(-8, -8)
        draw_trait_sprite(screen, assets, entry.piece, icon, max(8, icon.w - 2))
        if entry.status == "Captured":
            veil = pygame.Surface(drawn.size, pygame.SRCALPHA)
            veil.fill((40, 22, 12, 120))
            screen.blit(veil, drawn.topleft)
            pygame.draw.line(screen, (150, 46, 34), (drawn.x + 8, drawn.bottom - 9), (drawn.right - 9, drawn.y + 8), 3)


def _group(status: str) -> str:
    if status in ("Deployed", "Surviving"):
        return "board"
    if status == "Captured":
        return "fallen"
    return "reserve"


def _icon_rect(section: pygame.Rect, icon: int, index: int) -> pygame.Rect:
    column = index % 3
    row = index // 3
    inset = max(0, (section.w - (icon * 3 + 12)) // 2)
    return pygame.Rect(section.x + inset + column * (icon + 6), section.y + 4 + row * (icon + 6), icon, icon)


def _tooltip(screen: pygame.Surface, assets, entry: ArmyEntry, rect: pygame.Rect) -> None:
    lines = trait_tooltip_lines(entry.piece)
    if lines is None:
        return
    title, body = lines
    width = 230
    body_font = style.body_font(14)
    wrapped = _wrap(body_font, body, width - 20)
    height = 38 + len(wrapped) * 19
    panel = pygame.Rect(rect.left - width - 10, rect.y, width, height)
    if panel.left < 8:
        panel.left = rect.right + 8
    panel.clamp_ip(screen.get_rect())
    style.tooltip_panel(screen, assets, panel)
    style.text(screen, title, style.title_font(15, bold=True), style.INK, midleft=(panel.x + 12, panel.y + 18))
    y = panel.y + 38
    for line in wrapped:
        style.text(screen, line, body_font, style.INK_SOFT, midleft=(panel.x + 12, y))
        y += 19


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
