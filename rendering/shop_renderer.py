import pygame

from config.settings import (
    DEBUG_SHOP_LAYOUT,
    ARMY_UPGRADE_PRICE,
    DARK_TEXT,
    LIGHT_TEXT,
    PIECE_COLLECTION_PRICE,
    PIECE_PRICE,
    RELIC_COLLECTION_PRICE,
    RELIC_PRICE,
    SHOP_REROLL_TILT,
    SCENE_SLIDE_TIME,
    SHOP_CARD_STAGGER,
    TURN_CHECK,
)
from game.traits import trait_name
from game.transitions.easing import ease_out_cubic
from game.relics.relic_data import relic_by_id
from game.run_state import RunState
from rendering.relic_card import RelicCardRenderer
from rendering.relic_flip import shop_reveal
from rendering.shop_offers import shop_offers
from rendering.shop_piece_hand import shop_piece
from rendering.shop_relic_hand import relic_offer_slot, shop_hand
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import _blit_text, draw_background, draw_button, draw_relic_glow, get_font
from rendering.shop_layout import OFFER_KEYS, ShopLayout


_CARDS = RelicCardRenderer()


def draw_shop(
    screen: pygame.Surface,
    assets: AssetManager,
    run: RunState,
    layout: ShopLayout,
    backdrop: bool = True,
    entrance: float = 1.0,
) -> None:
    if backdrop:
        draw_background(screen, assets)
    key = "shop_bg" if assets.has("shop_bg") else "shop_background"
    screen.blit(_toned(assets, key, layout.background.size), layout.background.topleft)
    _draw_frames(screen, assets, run, layout)
    shop_offers.paint(screen, assets, run, layout)
    offer_dx, offer_alpha = _card_motion(entrance, 1)
    piece_dx, piece_alpha = _card_motion(entrance, 0)
    shop_piece.prepare(assets, run, layout)
    if not (shop_reveal.face_up and shop_reveal.progress >= 1.0):
        _draw_relic_offer(screen, assets, layout.cards[1], run)
    relic_dragging = shop_hand.dragging
    if shop_piece.dragging and not relic_dragging:
        shop_hand.paint(screen, assets, run, layout, offer_dx, offer_alpha)
        shop_piece.paint(screen, piece_dx, piece_alpha, run, layout)
    else:
        shop_piece.paint(screen, piece_dx, piece_alpha, run, layout)
        shop_hand.paint(screen, assets, run, layout, offer_dx, offer_alpha)
    dx, alpha = _card_motion(entrance, 3)
    if alpha > 0:
        _draw_reroll(screen, assets, layout, dx, alpha, 0 if run.shop_rerolls > 0 else run.shop.reroll_price)
    draw_button(screen, layout.continue_button, "Continue", font_size=max(16, layout.continue_button.h // 2))
    if run.notice:
        color = TURN_CHECK if run.notice == "Not enough gold" else (236, 214, 170)
        _blit_text(screen, run.notice, get_font(18, bold=True), color, center=layout.notice.center)
    if DEBUG_SHOP_LAYOUT:
        _draw_layout_debug(screen, run, layout)


def _piece_offer_name(run: RunState) -> str:
    kind = run.shop.piece_kind.capitalize()
    name = trait_name(run.shop.piece_trait)
    return f"{name} {kind}" if name else kind


def _draw_frames(screen: pygame.Surface, assets: AssetManager, run: RunState, layout: ShopLayout) -> None:
    shop = run.shop
    names = (_piece_offer_name(run), "Relic" if shop.relic_id else "No relic", "+1 Army Size")
    sold = (shop.piece_sold, shop.relic_sold and shop.relic_id is not None, shop.army_sold)
    for key, name, gone, plaque in zip(OFFER_KEYS, names, sold, layout.buys):
        frame = layout.slots[key]
        screen.blit(assets.scaled("buying_square", frame.size), frame.topleft)
        text = "Sold" if gone else name
        font = _fit_font(text, plaque.w - 8, max(12, int(plaque.h * 0.62)), True)
        _blit_text(screen, text, font, LIGHT_TEXT, center=plaque.center)
    prices = (PIECE_PRICE, RELIC_PRICE, ARMY_UPGRADE_PRICE, RELIC_COLLECTION_PRICE, PIECE_COLLECTION_PRICE)
    hidden = (
        shop.piece_sold,
        shop.relic_sold or shop.relic_id is None,
        shop.army_sold,
        shop.relic_collection_claimed,
        shop.piece_collection_claimed,
    )
    for tag, price, gone in zip(layout.tags, prices, hidden):
        if not gone:
            _draw_price(screen, assets, tag, price, run.gold >= price)


def _draw_price(screen: pygame.Surface, assets: AssetManager, tag: pygame.Rect, price: int, affordable: bool) -> None:
    screen.blit(assets.scaled("price_tag", tag.size), tag.topleft)
    _coin_amount(screen, assets, tag, price, DARK_TEXT if affordable else (150, 64, 58))


def _coin_amount(screen: pygame.Surface, assets: AssetManager, rect: pygame.Rect, amount: int, color, height: int = 0) -> None:
    height = height or rect.h
    font = get_font(max(13, int(height * 0.62)), bold=True)
    text_w, _text_h = font.size(str(amount))
    coin = assets.fitted("gold", int(height * 0.56), int(height * 0.56)) if assets.has("gold") else None
    gap = max(3, height // 10)
    total = text_w + (coin.get_width() + gap if coin else 0)
    x = rect.centerx - total // 2
    if coin:
        screen.blit(coin, coin.get_rect(midleft=(x, rect.centery)))
        x += coin.get_width() + gap
    _blit_text(screen, str(amount), font, color, midleft=(x, rect.centery))


_TONED: dict[tuple[str, int, int], pygame.Surface] = {}


def _toned(assets: AssetManager, key: str, size: tuple[int, int]) -> pygame.Surface:
    # half desaturated and warmed, so the bright shop art sits with the muted oil-painting cards
    cached = _TONED.get((key, *size))
    if cached is None:
        cached = assets.scaled(key, size).copy()
        grey = pygame.transform.grayscale(cached)
        grey.set_alpha(165)
        cached.blit(grey, (0, 0))
        cached.fill((232, 212, 180), special_flags=pygame.BLEND_RGB_MULT)
        _TONED[(key, *size)] = cached
    return cached


def _draw_layout_debug(screen: pygame.Surface, run: RunState, layout: ShopLayout) -> None:
    colors = {
        "piece": (80, 255, 120),
        "relic": (80, 220, 255),
        "army_size": (255, 90, 90),
        "relic_collection": (255, 210, 60),
        "piece_collection": (180, 120, 255),
    }
    pygame.draw.rect(screen, (255, 255, 255), layout.background, 1)
    for key, slot in layout.slots.items():
        color = colors.get(key, (255, 255, 255))
        pygame.draw.rect(screen, color, slot, 2)
        pygame.draw.circle(screen, color, slot.center, 4)
        _blit_text(screen, key, get_font(12, bold=True), color, center=(slot.centerx, slot.y + 10))
    if layout.cards:
        piece = shop_piece.rest_rect(run, layout) if shop_piece.live(run) else None
        if piece is not None:
            pygame.draw.rect(screen, (255, 255, 255), piece, 1)
        pygame.draw.rect(screen, (255, 255, 255), layout.cards[1], 1)
    for key in ("army_size", "relic_collection", "piece_collection"):
        pygame.draw.rect(screen, (255, 255, 255), shop_offers.art_rect(layout, key), 1)


def _card_motion(entrance: float, index: int) -> tuple[int, int]:
    if entrance >= 1.0:
        return 0, 255
    portion = SHOP_CARD_STAGGER / max(0.01, SCENE_SLIDE_TIME)
    local = (entrance - index * portion) / 0.7
    local = max(0.0, min(1.0, local))
    eased = ease_out_cubic(local)
    return int((1.0 - eased) * 64), int(255 * eased)


def _draw_reroll(screen: pygame.Surface, assets: AssetManager, layout: ShopLayout, dx: int, alpha: int, price: int) -> None:
    reroll = layout.reroll.move(dx, 0)
    label = layout.reroll_label.move(dx, 0)
    target: pygame.Surface = screen
    plate = None
    origin = reroll.topleft
    if alpha < 255:
        bounds = reroll.union(label)
        plate = pygame.Surface(bounds.size, pygame.SRCALPHA)
        target = plate
        reroll = reroll.move(-bounds.x, -bounds.y)
        label = label.move(-bounds.x, -bounds.y)
        origin = bounds.topleft
    target.blit(assets.scaled("reroll_board", (layout.reroll.w, layout.reroll.h)), reroll.topleft)
    face = pygame.Surface((label.w, label.h * 2), pygame.SRCALPHA)
    _coin_amount(face, assets, face.get_rect(), price, DARK_TEXT, height=int(label.h * 1.9))
    face = pygame.transform.rotozoom(face, SHOP_REROLL_TILT, 1.0)
    target.blit(face, face.get_rect(center=label.center))
    if plate is not None:
        plate.set_alpha(alpha)
        screen.blit(plate, origin)


def _relic_slot(card: pygame.Rect) -> pygame.Rect:
    return relic_offer_slot(card)


def _draw_relic_offer(screen: pygame.Surface, assets: AssetManager, card: pygame.Rect, run: RunState) -> None:
    relic_id = run.shop.relic_id
    definition = relic_by_id(relic_id) if relic_id else None
    slot = _relic_slot(card)
    if definition is None:
        _blit_card_face(screen, assets, None, slot, False)
        return
    if not run.shop.relic_sold and shop_reveal.face_up and shop_reveal.progress >= 1.0:
        return
    _blit_card_face(screen, assets, definition, slot, shop_reveal.face_up)
    if _SHOP_HOVER and shop_reveal.face_up:
        draw_relic_glow(screen, slot)


def shop_relic_rect(layout: ShopLayout) -> pygame.Rect:
    return _relic_slot(layout.cards[1])


def shop_card_hovered() -> bool:
    return _SHOP_HOVER


def set_shop_hover(pos: tuple[int, int] | None, layout, run: RunState | None = None) -> None:
    global _SHOP_HOVER
    slot = shop_relic_rect(layout)
    ready = run is not None and bool(run.shop.relic_id) and shop_reveal.face_up
    _SHOP_HOVER = pos is not None and ready and slot.collidepoint(pos)


_SHOP_HOVER = False


def _blit_card_face(screen: pygame.Surface, assets: AssetManager, definition, rect: pygame.Rect, face_up: bool) -> None:
    plate = pygame.Surface((max(1, rect.w), max(1, rect.h)), pygame.SRCALPHA)
    local = plate.get_rect()
    if face_up and definition is not None:
        _CARDS.draw(plate, assets, definition, local)
    else:
        _CARDS.draw(plate, assets, definition, local, face_down=True)
    width = max(1, int(plate.get_width() * shop_reveal.scale_x))
    if width != plate.get_width():
        plate = pygame.transform.smoothscale(plate, (width, plate.get_height()))
    screen.blit(plate, plate.get_rect(center=rect.center))


def _fit_font(text: str, max_width: int, size: int, bold: bool) -> pygame.font.Font:
    while size > 11:
        font = get_font(size, bold=bold)
        if font.size(text)[0] <= max_width:
            return font
        size -= 1
    return get_font(11, bold=bold)
