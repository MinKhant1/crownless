import pygame

from config.settings import (
    ARMY_UPGRADE_PRICE,
    PIECE_COLLECTION_PRICE,
    RELIC_COLLECTION_PRICE,
    SHOP_CHEST_SCALE,
)
from game.run_state import RunState
from rendering.asset_manager import AssetManager
from rendering.card_motion import approach
from rendering.hud_renderer import _blit_text, draw_button, draw_relic_glow, get_font, overlay_buy_rect
from rendering.shop_layout import ShopLayout


OFFERS = (
    ("army_size", ARMY_UPGRADE_PRICE, "Army Size"),
    ("relic_collection", RELIC_COLLECTION_PRICE, "Relic Collection"),
    ("piece_collection", PIECE_COLLECTION_PRICE, "Piece Collection"),
)


class ShopOffers:
    def __init__(self) -> None:
        self.selected: str | None = None
        self.hovered: str | None = None
        self._pointer = (0, 0)
        self._press: str | None = None
        self._press_buy = False
        self._scale: dict[str, float] = {}
        self._lift: dict[str, float] = {}
        self._chests: dict[str, pygame.Surface] = {}

    def clear(self) -> None:
        self.selected = None
        self.hovered = None
        self._press = None
        self._press_buy = False

    def update(self, dt: float, run: RunState, layout: ShopLayout) -> None:
        del run
        for key, _price, _label in OFFERS:
            hovered = self.hovered == key
            selected = self.selected == key
            scale = 1.05 if hovered or selected else 1.0
            lift = -10.0 if selected else 0.0
            self._scale[key] = approach(self._scale.get(key, 1.0), scale, dt, 12.0)
            self._lift[key] = approach(self._lift.get(key, 0.0), lift, dt, 12.0)
            if key not in layout.slots:
                continue

    def art_rect(self, layout: ShopLayout, key: str) -> pygame.Rect:
        slot = layout.slots[key]
        label_h = max(42, int(slot.h * 0.30))
        area = pygame.Rect(slot.x + 8, slot.y + 6, max(1, slot.w - 16), max(1, slot.h - label_h))
        side = max(1, min(area.w, area.h))
        rect = pygame.Rect(0, 0, side, side)
        rect.center = area.center
        if key in ("relic_collection", "piece_collection"):
            rect = _scaled(rect, SHOP_CHEST_SCALE)
        scale = self._scale.get(key, 1.0)
        lift = self._lift.get(key, 0.0)
        drawn = pygame.Rect(0, 0, max(1, int(rect.w * scale)), max(1, int(rect.h * scale)))
        drawn.center = (rect.centerx, rect.centery + int(lift))
        return drawn

    def buy_rect(self, run: RunState, layout: ShopLayout, key: str) -> pygame.Rect | None:
        if self.selected != key or _sold_out(run, key) or _pending(run, key):
            return None
        square = self.art_rect(layout, key).inflate(8, 8)
        return overlay_buy_rect(square, self.buy_caption(run, key)[0], "top")

    def buy_caption(self, run: RunState, key: str) -> tuple[str, bool]:
        price = _price(key)
        if run.gold < price:
            return "Not enough Gold", False
        return "Buy", True

    def on_motion(self, run: RunState, pos: tuple[int, int], layout: ShopLayout) -> None:
        self._pointer = pos
        self.hovered = None
        for key, _price, _label in OFFERS:
            if _sold_out(run, key):
                continue
            if self.art_rect(layout, key).collidepoint(pos):
                self.hovered = key

    def on_left_down(self, pos: tuple[int, int], run: RunState, layout: ShopLayout) -> bool:
        self._pointer = pos
        if self.selected is not None:
            button = self.buy_rect(run, layout, self.selected)
            if button is not None and button.collidepoint(pos):
                self._press_buy = True
                self._press = self.selected
                return True
        for key, _price, _label in reversed(OFFERS):
            if _pending(run, key) and self.art_rect(layout, key).collidepoint(pos):
                kind = _kind(key)
                if kind is not None:
                    run.shop.reopen_collection(kind)
                return True
            if _sold_out(run, key):
                kind = _kind(key)
                if kind is not None and self.art_rect(layout, key).collidepoint(pos) and run.shop.reopen_collection(kind):
                    return True
                continue
            if self.art_rect(layout, key).collidepoint(pos):
                self._press = key
                self._press_buy = False
                return True
        return False

    def on_left_up(self, pos: tuple[int, int], run: RunState, layout: ShopLayout) -> bool:
        pressed = self._press
        buying = self._press_buy
        self._press = None
        self._press_buy = False
        if pressed is None:
            return False
        if buying:
            button = self.buy_rect(run, layout, pressed)
            if button is not None and button.collidepoint(pos) and self.buy_caption(run, pressed)[1]:
                _purchase(run, pressed)
                self.selected = None
            return True
        rect = self.art_rect(layout, pressed)
        if rect.collidepoint(pos):
            self.selected = None if self.selected == pressed else pressed
        return True

    def paint(self, screen: pygame.Surface, assets: AssetManager, run: RunState, layout: ShopLayout) -> None:
        for key, _price, label in OFFERS:
            rect = self.art_rect(layout, key)
            if key == "army_size":
                _draw_army(screen, rect, label)
            else:
                chest = _chest_image(self, assets, key, rect.size)
                screen.blit(chest, chest.get_rect(center=rect.center))
            if self.hovered == key and self.selected != key:
                draw_relic_glow(screen, rect)
            if self.selected == key:
                outline = rect.inflate(8, 8)
                pygame.draw.rect(screen, (232, 196, 96), outline, width=2, border_radius=8)
            button = self.buy_rect(run, layout, key)
            if button is not None:
                caption, enabled = self.buy_caption(run, key)
                draw_button(screen, button, caption, enabled=enabled, font_size=12)
            elif _pending(run, key):
                _blit_text(screen, "Choose", get_font(max(14, rect.h // 8), bold=True), (245, 220, 170), center=(rect.centerx, rect.bottom + 12))
            elif _sold_out(run, key):
                shade = pygame.Surface(rect.size, pygame.SRCALPHA)
                shade.fill((24, 14, 10, 130))
                screen.blit(shade, rect.topleft)
                _blit_text(screen, "SOLD OUT", get_font(max(14, rect.h // 8), bold=True), (236, 214, 170), center=rect.center)


def _scaled(rect: pygame.Rect, scale: float) -> pygame.Rect:
    grown = pygame.Rect(rect)
    grown.w = max(1, int(round(rect.w * scale)))
    grown.h = max(1, int(round(rect.h * scale)))
    grown.center = rect.center
    return grown


def _price(key: str) -> int:
    for offer, price, _label in OFFERS:
        if offer == key:
            return price
    return 0


def _kind(key: str) -> str | None:
    if key == "relic_collection":
        return "relic"
    if key == "piece_collection":
        return "piece"
    return None


def _pending(run: RunState, key: str) -> bool:
    shop = run.shop
    if key == "relic_collection":
        return bool(shop.relic_choices) and not shop.relic_collection_claimed
    if key == "piece_collection":
        return bool(shop.piece_choices) and not shop.piece_collection_claimed
    return False


def _sold_out(run: RunState, key: str) -> bool:
    shop = run.shop
    if key == "army_size":
        return shop.army_sold
    if key == "relic_collection":
        return shop.relic_collection_claimed
    if key == "piece_collection":
        return shop.piece_collection_claimed
    return False


def _purchase(run: RunState, key: str) -> None:
    if key == "army_size":
        run.buy_army()
    elif key == "relic_collection":
        run.buy_relic_collection()
    elif key == "piece_collection":
        run.buy_piece_collection()


def _draw_army(screen: pygame.Surface, rect: pygame.Rect, label: str) -> None:
    plate = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(plate, (236, 220, 196, 230), plate.get_rect(), border_radius=8)
    pygame.draw.rect(plate, (120, 84, 48, 255), plate.get_rect(), width=2, border_radius=8)
    screen.blit(plate, rect.topleft)
    _blit_text(screen, "+1", get_font(max(22, rect.h // 3), bold=True), (68, 40, 26), center=(rect.centerx, rect.centery - rect.h // 8))
    _blit_text(screen, label, get_font(max(13, rect.h // 7), bold=True), (92, 58, 36), center=(rect.centerx, rect.centery + rect.h // 5))


def _chest_image(offers: ShopOffers, assets: AssetManager | None, key: str, size: tuple[int, int]) -> pygame.Surface:
    asset_key = "relic_chest" if key == "relic_collection" else "piece_chest"
    if assets is not None and assets.has(asset_key):
        return assets.fitted(asset_key, size[0], size[1])
    cached = offers._chests.get((key, size))
    if cached is not None:
        return cached
    surface = pygame.Surface(size, pygame.SRCALPHA)
    width, height = size
    body = pygame.Rect(int(width * 0.08), int(height * 0.40), int(width * 0.84), int(height * 0.46))
    lid = pygame.Rect(int(width * 0.04), int(height * 0.16), int(width * 0.92), int(height * 0.34))
    wood = (122, 74, 40)
    pygame.draw.rect(surface, wood, body, border_radius=max(4, width // 18))
    pygame.draw.ellipse(surface, (104, 62, 32), lid)
    pygame.draw.rect(surface, (214, 170, 90), body, width=2, border_radius=max(4, width // 18))
    pygame.draw.ellipse(surface, (214, 170, 90), lid, width=2)
    band = (128, 28, 42) if key == "relic_collection" else (70, 48, 32)
    pygame.draw.rect(surface, band, (int(width * 0.42), int(height * 0.18), max(6, int(width * 0.16)), int(height * 0.64)), border_radius=3)
    pygame.draw.circle(surface, (232, 196, 96), (width // 2, int(height * 0.58)), max(4, width // 12))
    offers._chests[(key, size)] = surface
    return surface


shop_offers = ShopOffers()
