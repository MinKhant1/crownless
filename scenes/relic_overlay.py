import pygame

from game.relics.relic_data import RelicDef, relic_by_id
from game.run_state import RunState
from game.traits import trait_name
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import _blit_text, draw_button, get_font
from rendering.relic_card import RelicCardRenderer
from rendering.shop_layout import ShopLayout


CARD_RENDERER = RelicCardRenderer()


class RelicOverlay:
    def __init__(self) -> None:
        self.open = False
        self.armed = False
        self.picking = False
        self.choice_id: int | None = None
        self.hovered: str | None = None
        self.shop_hover = False
        self.result = None

    def button_rect(self, window: tuple[int, int]) -> pygame.Rect:
        return pygame.Rect(16, 10, 140, 36)

    def wants(self, pos: tuple[int, int], window: tuple[int, int]) -> bool:
        return self.open or self.button_rect(window).collidepoint(pos)

    def panel(self, window: tuple[int, int]) -> pygame.Rect:
        rect = pygame.Rect(0, 0, min(1180, window[0] - 48), min(820, window[1] - 48))
        rect.center = (window[0] // 2, window[1] // 2)
        return rect

    def card_rects(self, window: tuple[int, int], count: int) -> list[pygame.Rect]:
        panel = self.panel(window)
        width = min(250, max(160, (panel.w - 80) // max(1, count)))
        height = min(420, panel.h - 180)
        total = count * width + max(0, count - 1) * 18
        left = panel.centerx - total // 2
        top = panel.y + 64
        return [pygame.Rect(left + index * (width + 18), top, width, height) for index in range(count)]

    def activate_rect(self, card: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(card.x + 12, card.bottom + 8, card.w - 24, 32)

    def piece_button(self, panel: pygame.Rect, index: int) -> pygame.Rect:
        return pygame.Rect(panel.x + 28 + (index % 3) * 150, panel.y + 120 + (index // 3) * 46, 140, 38)

    def confirm_rect(self, panel: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(panel.right - 220, panel.bottom - 64, 180, 40)

    def result_button(self, panel: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(panel.centerx - 90, panel.bottom - 72, 180, 42)

    def on_motion(self, run: RunState, pos: tuple[int, int], window: tuple[int, int], shop: ShopLayout | None) -> None:
        self.hovered = None
        self.shop_hover = False
        if self.open:
            owned = run.relics.owned
            for relic, rect in zip(owned, self.card_rects(window, len(owned))):
                if rect.collidepoint(pos):
                    self.hovered = relic.relic_id
                    return
            return
        if run.phase == "shop" and shop is not None and run.shop.relic_id and shop.cards[1].collidepoint(pos):
            self.shop_hover = True

    def on_click(self, run: RunState, pos: tuple[int, int], window: tuple[int, int]) -> bool:
        button = self.button_rect(window)
        if not self.open:
            if button.collidepoint(pos):
                self.open = True
                self.picking = False
                self.result = None
                return True
            return False
        if button.collidepoint(pos):
            self._close()
            return True
        panel = self.panel(window)
        if not panel.collidepoint(pos):
            self._close()
            return True
        close = pygame.Rect(panel.right - 108, panel.y + 14, 92, 34)
        if close.collidepoint(pos):
            self._close()
            return True
        if self.result is not None:
            if self.result_button(panel).collidepoint(pos):
                self.result = None
            return True
        owned = run.relics.owned
        rects = self.card_rects(window, len(owned))
        for relic, rect in zip(owned, rects):
            definition = relic_by_id(relic.relic_id)
            if definition is not None and definition.trigger == "on_activate" and self.activate_rect(rect).collidepoint(pos):
                effect = run.relics.effect_for(relic.relic_id)
                if effect is not None and effect.can_activate(run.relics.context)[0]:
                    self.picking = True
                    self.choice_id = None
                return True
            if rect.collidepoint(pos):
                return True
        if self.picking:
            self._click_picker(run, pos, panel)
        return True

    def _click_picker(self, run: RunState, pos: tuple[int, int], panel: pygame.Rect) -> None:
        pieces = [piece for piece in run.army.pieces if piece.kind != "king"]
        for index, piece in enumerate(pieces):
            if self.piece_button(panel, index).collidepoint(pos):
                self.choice_id = piece.id
                return
        if self.confirm_rect(panel).collidepoint(pos) and self.choice_id is not None:
            effect = run.relics.effect_for("blood_contract")
            if effect is None:
                return
            self.result = effect.activate(run.relics.context, self.choice_id)
            self.picking = False
            self.choice_id = None

    def _close(self) -> None:
        self.open = False
        self.picking = False
        self.choice_id = None
        self.result = None

    def draw(self, screen: pygame.Surface, assets: AssetManager, run: RunState, shop: ShopLayout | None) -> None:
        window = screen.get_size()
        draw_button(screen, self.button_rect(window), "Relics", font_size=18)
        if not self.open:
            return
        shade = pygame.Surface(window, pygame.SRCALPHA)
        shade.fill((12, 8, 6, 220))
        screen.blit(shade, (0, 0))
        panel = self.panel(window)
        pygame.draw.rect(screen, (42, 28, 20), panel, border_radius=16)
        pygame.draw.rect(screen, (214, 170, 90), panel, width=3, border_radius=16)
        _blit_text(screen, "Relics", get_font(32, bold=True), (245, 232, 210), midleft=(panel.x + 28, panel.y + 28))
        draw_button(screen, pygame.Rect(panel.right - 108, panel.y + 14, 92, 34), "Close", font_size=16)
        if not run.relics.owned:
            _blit_text(
                screen,
                "No relics yet. The shop may offer one after a battle.",
                get_font(22),
                (236, 220, 196),
                center=panel.center,
            )
            return
        if self.result is not None:
            self._draw_result(screen, panel)
            return
        if self.picking:
            self._draw_picker(screen, run, panel)
            return
        for owned, rect in zip(run.relics.owned, self.card_rects(window, len(run.relics.owned))):
            definition = relic_by_id(owned.relic_id)
            if definition is None:
                continue
            CARD_RENDERER.draw(screen, assets, definition, rect, hovered=self.hovered == owned.relic_id, owned=True)
            self._draw_status(screen, run, definition, owned, rect)

    def _draw_status(self, screen: pygame.Surface, run: RunState, definition: RelicDef, owned, rect: pygame.Rect) -> None:
        effect = run.relics.effect_for(definition.id)
        if definition.trigger != "on_activate" or effect is None:
            label = "Passive"
            if definition.id == "conversion" and owned.state.get("used_this_battle"):
                label = "Used this battle"
            _blit_text(screen, label, get_font(14), (236, 214, 170), center=(rect.centerx, rect.bottom + 16))
            return
        allowed, message = effect.can_activate(run.relics.context)
        button = self.activate_rect(rect)
        draw_button(screen, button, "Activate", enabled=allowed, font_size=16)
        if not allowed and message:
            _blit_text(screen, message, get_font(13), (214, 120, 96), center=(rect.centerx, button.bottom + 12))

    def _draw_picker(self, screen: pygame.Surface, run: RunState, panel: pygame.Rect) -> None:
        _blit_text(screen, "Choose a piece to sacrifice", get_font(24, bold=True), (245, 232, 210), midleft=(panel.x + 28, panel.y + 78))
        pieces = [piece for piece in run.army.pieces if piece.kind != "king"]
        for index, piece in enumerate(pieces):
            rect = self.piece_button(panel, index)
            selected = piece.id == self.choice_id
            label = piece.kind.capitalize()
            if piece.trait:
                label = f"{label} {trait_name(piece.trait)}"
            draw_button(screen, rect, label, enabled=True, font_size=14)
            if selected:
                pygame.draw.rect(screen, (232, 196, 96), rect, width=3, border_radius=10)
        draw_button(screen, self.confirm_rect(panel), "Confirm", enabled=self.choice_id is not None, font_size=18)

    def _draw_result(self, screen: pygame.Surface, panel: pygame.Rect) -> None:
        result = self.result
        if result is None:
            return
        if not result.ok:
            lines = [result.message]
            title = "Cannot activate"
        else:
            title = "Blood Contract"
            lines = [
                f"Sacrificed {result.sacrificed_kind.capitalize()}",
                f"{result.target_kind.capitalize()} becomes {trait_name(result.trait_id)}",
            ]
        _blit_text(screen, title, get_font(32, bold=True), (245, 232, 210), center=(panel.centerx, panel.centery - 40))
        y = panel.centery + 10
        for line in lines:
            _blit_text(screen, line, get_font(22), (236, 220, 196), center=(panel.centerx, y))
            y += 34
        draw_button(screen, self.result_button(panel), "Close", font_size=18)
