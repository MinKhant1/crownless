import pygame

from config.settings import LABEL_TEXT, LIGHT_TEXT, MOVE_DOT
from game.board import Board
from game.game import Game
from game.move import Move
from game.run_state import RunState
from game.traits import trait_name
from rendering.asset_manager import AssetManager
from rendering.board_renderer import draw_board
from rendering.hud_renderer import (
    _blit_text,
    draw_background,
    draw_button,
    draw_crown,
    draw_header_and_status,
    draw_labels,
    get_font,
)
from rendering.layout import Layout, square_at
from rendering.overlay_renderer import draw_trait_tooltip
from rendering.piece_renderer import draw_pieces, draw_trait_sprite


class _Hud:
    def __init__(self, level: int, size: int, capacity: int) -> None:
        self.current_level = level
        self.army_size = size
        self.army_capacity = capacity


class DeploymentScene:
    def __init__(self) -> None:
        self.press_id: int | None = None
        self.press_pos: tuple[int, int] | None = None
        self.dragging = False
        self.drag_pos: tuple[int, int] | None = None
        self.hover: tuple[int, int] | None = None

    def panels(self, window: tuple[int, int], layout: Layout) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        left = pygame.Rect(16, layout.header.y, max(120, layout.frame.left - 56), layout.frame.h)
        tray = pygame.Rect(layout.frame.right + 16, layout.frame.y, max(120, window[0] - layout.frame.right - 28), layout.frame.h)
        button = pygame.Rect(left.x, left.bottom - 52, left.w, 46)
        return left, tray, button

    def icon_rects(self, tray: pygame.Rect, run: RunState) -> list[tuple[int, pygame.Rect]]:
        size = min(76, max(48, tray.w // 3 - 8))
        cols = max(1, (tray.w - 8) // (size + 10))
        rects: list[tuple[int, pygame.Rect]] = []
        for index, piece in enumerate(run.army.pieces):
            column = index % cols
            row = index // cols
            rect = pygame.Rect(tray.x + 6 + column * (size + 10), tray.y + 36 + row * (size + 28), size, size)
            rects.append((piece.id, rect))
        return rects

    def display_game(self, run: RunState) -> Game:
        pieces = [enemy.copy() for enemy in run.enemies]
        for piece in run.army.pieces:
            position = run.deployment.placed.get(piece.id)
            if position is None:
                continue
            clone = piece.copy()
            clone.col, clone.row = position
            pieces.append(clone)
        game = Game(Board(pieces))
        game.current_level = run.level
        game.army_size = run.deployment.non_king_count(run.army)
        game.army_capacity = run.army.capacity
        game.turns.in_check = False
        game.turns.finished = False
        game.turns.battle_state = "ongoing"
        game.legal = []
        game.hover = self.hover
        if run.phase == "deployment" and run.selected_piece_id is not None:
            selected = run.army.piece_by_id(run.selected_piece_id)
            if selected is not None:
                if selected.id in run.deployment.placed:
                    game.selected_id = selected.id
                for col, row in run.deployment.squares_for(
                    selected,
                    run.blocked_squares(),
                    run.army.capacity,
                    run.army,
                ):
                    game.legal.append(Move(0, 1, col, row))
        return game

    def on_press(self, run: RunState, pos: tuple[int, int], layout: Layout, window: tuple[int, int]) -> None:
        _left, tray, _button = self.panels(window, layout)
        self.press_pos = pos
        self.dragging = False
        self.drag_pos = pos
        self.press_id = None
        if run.phase != "deployment":
            return
        for piece_id, rect in self.icon_rects(tray, run):
            if rect.collidepoint(pos):
                self.press_id = piece_id
                return
        square = square_at(layout, pos)
        if square is None:
            return
        placed = run.deployment.piece_id_at(*square)
        if placed is not None:
            self.press_id = placed

    def on_motion(self, pos: tuple[int, int]) -> None:
        self.drag_pos = pos
        if self.press_id is None or self.press_pos is None:
            return
        if abs(pos[0] - self.press_pos[0]) + abs(pos[1] - self.press_pos[1]) > 12:
            self.dragging = True

    def on_release(self, run: RunState, pos: tuple[int, int], layout: Layout, window: tuple[int, int]) -> None:
        left, tray, button = self.panels(window, layout)
        if run.phase == "preview":
            if button.collidepoint(pos):
                run.begin_deployment()
            self._clear_press()
            return
        if run.phase != "deployment":
            self._clear_press()
            return
        if button.collidepoint(pos) and not self.dragging:
            run.start_battle()
            self._clear_press()
            return
        if self.dragging and self.press_id is not None:
            self._drop(run, pos, layout, tray)
            self._clear_press()
            return
        if self.press_id is not None and not self.dragging:
            self._click_piece(run, self.press_id)
            self._clear_press()
            return
        square = square_at(layout, pos)
        if square is not None and run.selected_piece_id is not None:
            piece = run.army.piece_by_id(run.selected_piece_id)
            if piece is not None and run.deployment.place(
                piece,
                square[0],
                square[1],
                run.blocked_squares(),
                run.army.capacity,
                run.army,
            ):
                run.selected_piece_id = None
                run.notice = ""
            elif piece is not None:
                full = (
                    piece.kind != "king"
                    and piece.id not in run.deployment.placed
                    and run.deployment.non_king_count(run.army) >= run.army.capacity
                )
                run.notice = "Army is full" if full else "Square unavailable"
        elif not left.collidepoint(pos):
            run.selected_piece_id = None
        self._clear_press()

    def _drop(self, run: RunState, pos: tuple[int, int], layout: Layout, tray: pygame.Rect) -> None:
        piece = run.army.piece_by_id(self.press_id or -1)
        if piece is None:
            return
        square = square_at(layout, pos)
        if square is not None and run.deployment.place(
            piece,
            square[0],
            square[1],
            run.blocked_squares(),
            run.army.capacity,
            run.army,
        ):
            run.selected_piece_id = None
            run.notice = ""
            return
        if tray.collidepoint(pos):
            run.deployment.remove(piece.id)
            run.selected_piece_id = None
            run.notice = ""
            return
        run.notice = "Square unavailable"

    def _click_piece(self, run: RunState, piece_id: int) -> None:
        if run.selected_piece_id == piece_id and piece_id in run.deployment.placed:
            run.deployment.remove(piece_id)
            run.selected_piece_id = None
            run.notice = ""
            return
        run.selected_piece_id = piece_id
        run.notice = ""

    def _clear_press(self) -> None:
        self.press_id = None
        self.press_pos = None
        self.dragging = False
        self.drag_pos = None

    def draw(self, screen: pygame.Surface, assets: AssetManager, run: RunState, layout: Layout) -> None:
        window = screen.get_size()
        game = self.display_game(run)
        hud = _Hud(run.level, game.army_size, game.army_capacity)
        draw_background(screen, assets)
        draw_header_and_status(screen, assets, hud, layout)
        draw_board(screen, assets, layout)
        draw_labels(screen, layout)
        draw_pieces(screen, assets, game, layout)
        draw_crown(screen, assets, layout)
        left, tray, button = self.panels(window, layout)
        self._draw_panel(screen, run, left, button)
        if run.phase == "deployment":
            self._draw_tray(screen, assets, run, tray)
        draw_trait_tooltip(screen, game, layout)
        if self.dragging and self.press_id is not None and self.drag_pos is not None:
            piece = run.army.piece_by_id(self.press_id)
            if piece is not None:
                draw_trait_sprite(
                    screen,
                    assets,
                    piece,
                    pygame.Rect(0, 0, layout.square, layout.square).move(self.drag_pos[0] - layout.square // 2, self.drag_pos[1] - layout.square // 2),
                    int(layout.square * 0.84),
                )

    def _draw_panel(self, screen: pygame.Surface, run: RunState, panel: pygame.Rect, button: pygame.Rect) -> None:
        font = get_font(26, bold=True)
        small = get_font(18, bold=False)
        title = f"Level {run.level}"
        _blit_text(screen, title, font, LIGHT_TEXT, midleft=(panel.x, panel.y + 8))
        king = run.army.king()
        king_ready = king is not None and king.id in run.deployment.placed
        lines = [
            f"Gold  {run.gold}",
            f"Army  {run.deployment.non_king_count(run.army)} / {run.army.capacity}",
            "King deployed" if king_ready else "King required",
        ]
        if run.phase == "preview":
            lines.append("Enemies are set.")
            lines.append("Deploy on ranks 1 and 2.")
        else:
            lines.append("Click a piece, then a square.")
            lines.append("Click a placed piece again")
            lines.append("to return it.")
        y = panel.y + 42
        for line in lines:
            color = (214, 92, 72) if line == "King required" else LABEL_TEXT
            _blit_text(screen, line, small, color, midleft=(panel.x, y))
            y += 26
        if run.notice:
            _blit_text(screen, run.notice, small, (214, 92, 72), midleft=(panel.x, y + 4))
        if run.phase == "preview":
            draw_button(screen, button, "Deploy")
        else:
            draw_button(screen, button, "Start Battle", enabled=run.deployment.ready(run.army))

    def _draw_tray(self, screen: pygame.Surface, assets: AssetManager, run: RunState, tray: pygame.Rect) -> None:
        _blit_text(screen, "Army", get_font(22, bold=True), LIGHT_TEXT, midleft=(tray.x + 6, tray.y + 4))
        for piece_id, rect in self.icon_rects(tray, run):
            piece = run.army.piece_by_id(piece_id)
            if piece is None:
                continue
            placed = piece.id in run.deployment.placed
            selected = run.selected_piece_id == piece.id
            fill = (92, 64, 40) if selected else (46, 32, 24)
            pygame.draw.rect(screen, fill, rect, border_radius=8)
            border = (232, 196, 96) if selected or placed else (120, 90, 60)
            pygame.draw.rect(screen, border, rect, width=2, border_radius=8)
            draw_trait_sprite(screen, assets, piece, rect, int(rect.w * 0.82))
            label = trait_name(piece.trait) if piece.trait else piece.kind.capitalize()
            caption = f"{label}" if not placed else (trait_name(piece.trait) if piece.trait else "On board")
            _blit_text(screen, caption, get_font(13, bold=False), LABEL_TEXT if not placed else MOVE_DOT, center=(rect.centerx, rect.bottom + 10))
