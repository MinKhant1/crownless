import pygame

from config.settings import (
    ARMY_UPGRADE_PRICE,
    DARK_TEXT,
    LIGHT_TEXT,
    PIECE_PRICE,
    RELIC_PRICE,
    REROLL_PRICE,
    SCENE_SLIDE_TIME,
    SHOP_BUY,
    SHOP_CARD_STAGGER,
    TURN_CHECK,
)
from game.transitions.easing import ease_out_cubic
from game.relics.relic_data import relic_by_id
from game.run_state import RunState
from rendering.relic_card import RelicCardRenderer
from rendering.relic_flip import shop_reveal
from rendering.shop_piece_hand import piece_box, shop_piece
from rendering.shop_relic_hand import relic_offer_slot, shop_hand
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import _blit_text, draw_background, draw_button, draw_relic_glow, get_font
from rendering.shop_layout import ShopLayout


_CARDS = RelicCardRenderer()


def _gold_line(amount: int) -> str:
    return f"{amount} Gold"


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
    shop = assets.scaled("shop_background", (layout.background.w, layout.background.h))
    screen.blit(shop, layout.background.topleft)
    prices = (_gold_line(PIECE_PRICE), _gold_line(RELIC_PRICE), _gold_line(ARMY_UPGRADE_PRICE))
    card_image = assets.scaled("buying_square", (layout.cards[0].w, layout.cards[0].h))
    labels = (run.shop.piece_kind.capitalize(), "", "Army Size")
    for index, card in enumerate(layout.cards):
        dx, alpha = _card_motion(entrance, index)
        if alpha <= 0:
            continue
        _draw_shop_card(screen, assets, run, layout, index, card, card_image, prices[index], labels[index], dx, alpha)
    dx, alpha = _card_motion(entrance, 3)
    if alpha > 0:
        _draw_reroll(screen, assets, layout, dx, alpha)
    gold_tag = assets.scaled("price_tag", (layout.gold.w, layout.gold.h))
    screen.blit(gold_tag, layout.gold.topleft)
    _blit_text(
        screen,
        f"Gold  {run.gold}",
        get_font(max(18, layout.gold.h * 0.36), bold=True),
        DARK_TEXT,
        center=layout.gold.center,
    )
    draw_button(screen, layout.continue_button, "Continue", font_size=max(18, layout.continue_button.h // 2))
    offer_dx, offer_alpha = _card_motion(entrance, 1)
    piece_dx, piece_alpha = _card_motion(entrance, 0)
    shop_piece.prepare(assets, run, layout)
    relic_dragging = shop_hand.dragging
    if shop_piece.dragging and not relic_dragging:
        shop_hand.paint(screen, assets, run, layout, offer_dx, offer_alpha)
        shop_piece.paint(screen, piece_dx, piece_alpha, run, layout)
    else:
        shop_piece.paint(screen, piece_dx, piece_alpha, run, layout)
        shop_hand.paint(screen, assets, run, layout, offer_dx, offer_alpha)
    if run.notice:
        color = TURN_CHECK if run.notice == "Not enough gold" else (236, 214, 170)
        _blit_text(screen, run.notice, get_font(20, bold=True), color, center=layout.notice.center)


def _card_motion(entrance: float, index: int) -> tuple[int, int]:
    if entrance >= 1.0:
        return 0, 255
    portion = SHOP_CARD_STAGGER / max(0.01, SCENE_SLIDE_TIME)
    local = (entrance - index * portion) / 0.7
    local = max(0.0, min(1.0, local))
    eased = ease_out_cubic(local)
    return int((1.0 - eased) * 64), int(255 * eased)


def _draw_shop_card(
    screen: pygame.Surface,
    assets: AssetManager,
    run: RunState,
    layout: ShopLayout,
    index: int,
    card: pygame.Rect,
    card_image: pygame.Surface,
    price: str,
    label: str,
    dx: int,
    alpha: int,
) -> None:
    card = card.move(dx, 0)
    tag = layout.tags[index].move(dx, 0)
    buy = layout.buys[index].move(dx, 0)
    target: pygame.Surface = screen
    plate = None
    origin = card.topleft
    if alpha < 255:
        bounds = card.union(tag)
        plate = pygame.Surface(bounds.size, pygame.SRCALPHA)
        target = plate
        card = card.move(-bounds.x, -bounds.y)
        tag = tag.move(-bounds.x, -bounds.y)
        buy = buy.move(-bounds.x, -bounds.y)
        origin = bounds.topleft
    tag_font = get_font(max(16, tag.h * 0.34), bold=True)
    if index != 1:
        target.blit(assets.scaled("price_tag", (tag.w, tag.h)), tag.topleft)
        _blit_text(target, price, tag_font, DARK_TEXT, center=tag.center)
    target.blit(card_image, card.topleft)
    if index == 1:
        _draw_relic_offer(target, assets, card, run)
    else:
        _draw_offer(target, assets, card, label, "", index, run, hold_piece=index == 0 and shop_piece.live(run))
    relic_ready = run.shop.relic_id is not None and not run.shop.relic_sold
    sold = (run.shop.piece_sold, run.shop.relic_sold and run.shop.relic_id is not None, run.shop.army_sold)
    enabled = (not run.shop.piece_sold, relic_ready, not run.shop.army_sold)
    if index == 0 and shop_piece.live(run):
        plaque = None
    elif index == 1 and enabled[1] and not sold[1]:
        plaque = None
    elif index == 1 and run.shop.relic_id is None:
        plaque = "None"
    elif sold[index]:
        plaque = "Sold"
    else:
        plaque = "Buy"
    if plaque is not None:
        _blit_text(
            target,
            plaque,
            get_font(max(15, card.h * 0.07), bold=True),
            LIGHT_TEXT if enabled[index] or sold[index] else (176, 164, 148),
            center=buy.center,
        )
    if sold[index]:
        shade = pygame.Surface(card.size, pygame.SRCALPHA)
        shade.fill((24, 14, 10, 130))
        target.blit(shade, card.topleft)
        _blit_text(target, "SOLD OUT", get_font(max(18, card.h * 0.09), bold=True), (236, 214, 170), center=card.center)
    if plate is not None:
        plate.set_alpha(alpha)
        screen.blit(plate, origin)


def _draw_reroll(screen: pygame.Surface, assets: AssetManager, layout: ShopLayout, dx: int, alpha: int) -> None:
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
    _blit_text(
        target,
        _gold_line(REROLL_PRICE),
        get_font(max(16, layout.reroll_label.h * 0.42), bold=True),
        DARK_TEXT,
        center=label.center,
    )
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


def _draw_offer(
    screen: pygame.Surface,
    assets: AssetManager,
    card: pygame.Rect,
    label: str,
    subtitle: str,
    index: int,
    run: RunState,
    hold_piece: bool = False,
) -> None:
    text_width = int(card.w * 0.78)
    name_font = _fit_font(label, text_width, max(13, int(card.h * 0.07)), True)
    sub_font = _fit_font(subtitle, text_width, max(11, int(card.h * 0.048)), False) if subtitle else None
    buy_top = card.y + int(card.h * SHOP_BUY[1])
    text_block = name_font.get_height()
    if sub_font is not None:
        text_block += sub_font.get_height() + 1
    name_center = buy_top - text_block + name_font.get_height() // 2 - 2
    box = piece_box(card, label)
    if index == 0:
        if not hold_piece:
            image = assets.fitted(f"white_{run.shop.piece_kind}", box.w, box.h)
            screen.blit(image, image.get_rect(center=box.center))
    elif index == 1:
        image = assets.fitted("crown", int(box.w * 0.72), int(box.h * 0.72))
        screen.blit(image, image.get_rect(center=box.center))
    else:
        _blit_text(screen, "+1", get_font(max(22, int(box.h * 0.62)), bold=True), DARK_TEXT, center=box.center)
    _blit_text(screen, label, name_font, DARK_TEXT, center=(card.centerx, name_center))
    if sub_font is not None:
        _blit_text(
            screen,
            subtitle,
            sub_font,
            (96, 62, 40),
            center=(card.centerx, name_center + name_font.get_height() // 2 + sub_font.get_height() // 2 + 1),
        )
