import pygame

from config.settings import (
    ARMY_UPGRADE_PRICE,
    DARK_TEXT,
    LIGHT_TEXT,
    PIECE_PRICE,
    RELIC_PRICE,
    REROLL_PRICE,
    SHOP_BUY,
    SHOP_ICON,
    TURN_CHECK,
)
from game.relics.relic_data import relic_by_id
from game.run_state import RunState
from rendering.relic_card import RelicCardRenderer
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import _blit_text, draw_button, get_font
from rendering.shop_layout import ShopLayout


_CARDS = RelicCardRenderer()


def _gold_line(amount: int) -> str:
    return f"{amount} Gold"


def draw_shop(screen: pygame.Surface, assets: AssetManager, run: RunState, layout: ShopLayout) -> None:
    background, origin = assets.cover("background", screen.get_width(), screen.get_height())
    screen.blit(background, origin)
    shop = assets.scaled("shop_background", (layout.background.w, layout.background.h))
    screen.blit(shop, layout.background.topleft)
    prices = (_gold_line(PIECE_PRICE), _gold_line(RELIC_PRICE), _gold_line(ARMY_UPGRADE_PRICE))
    tag_font = get_font(max(16, layout.tags[0].h * 0.34), bold=True)
    for tag, price in zip(layout.tags, prices):
        image = assets.scaled("price_tag", (tag.w, tag.h))
        screen.blit(image, tag.topleft)
        _blit_text(screen, price, tag_font, DARK_TEXT, center=tag.center)
    card_image = assets.scaled("buying_square", (layout.cards[0].w, layout.cards[0].h))
    labels = (run.shop.piece_kind.capitalize(), "", "Army Size")
    subtitles = ("", "", "")
    relic_ready = run.shop.relic_id is not None and not run.shop.relic_sold
    sold = (run.shop.piece_sold, run.shop.relic_sold and run.shop.relic_id is not None, run.shop.army_sold)
    enabled = (not run.shop.piece_sold, relic_ready, not run.shop.army_sold)
    for index, card in enumerate(layout.cards):
        screen.blit(card_image, card.topleft)
        if index == 1:
            _draw_relic_offer(screen, assets, card, run)
        else:
            _draw_offer(screen, assets, card, labels[index], subtitles[index], index, run)
        if index == 1 and run.shop.relic_id is None:
            plaque = "None"
        elif sold[index]:
            plaque = "Sold"
        else:
            plaque = "Buy"
        _blit_text(
            screen,
            plaque,
            get_font(max(15, card.h * 0.07), bold=True),
            LIGHT_TEXT if enabled[index] or sold[index] else (176, 164, 148),
            center=layout.buys[index].center,
        )
        if sold[index]:
            shade = pygame.Surface(card.size, pygame.SRCALPHA)
            shade.fill((24, 14, 10, 130))
            screen.blit(shade, card.topleft)
            _blit_text(screen, "SOLD OUT", get_font(max(18, card.h * 0.09), bold=True), (236, 214, 170), center=card.center)
    reroll = assets.scaled("reroll_board", (layout.reroll.w, layout.reroll.h))
    screen.blit(reroll, layout.reroll.topleft)
    _blit_text(
        screen,
        _gold_line(REROLL_PRICE),
        get_font(max(16, layout.reroll_label.h * 0.42), bold=True),
        DARK_TEXT,
        center=layout.reroll_label.center,
    )
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
    if run.notice:
        color = TURN_CHECK if run.notice == "Not enough gold" else (236, 214, 170)
        _blit_text(screen, run.notice, get_font(20, bold=True), color, center=layout.notice.center)


def _draw_relic_offer(screen: pygame.Surface, assets: AssetManager, card: pygame.Rect, run: RunState) -> None:
    relic_id = run.shop.relic_id
    definition = relic_by_id(relic_id) if relic_id else None
    if definition is None:
        _blit_text(screen, "No Relic", get_font(max(16, int(card.h * 0.08)), bold=True), DARK_TEXT, center=card.center)
        return
    inner = pygame.Rect(
        card.x + int(card.w * 0.08),
        card.y + int(card.h * 0.06),
        int(card.w * 0.84),
        int(card.h * 0.66),
    )
    _CARDS.draw(screen, assets, definition, inner, owned=run.relics.owns(definition.id))


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
) -> None:
    text_width = int(card.w * 0.78)
    name_font = _fit_font(label, text_width, max(13, int(card.h * 0.07)), True)
    sub_font = _fit_font(subtitle, text_width, max(11, int(card.h * 0.048)), False) if subtitle else None
    buy_top = card.y + int(card.h * SHOP_BUY[1])
    text_block = name_font.get_height()
    if sub_font is not None:
        text_block += sub_font.get_height() + 1
    name_center = buy_top - text_block + name_font.get_height() // 2 - 2
    icon_x, icon_y, icon_w, icon_h = SHOP_ICON
    box = pygame.Rect(
        card.x + int(card.w * icon_x),
        card.y + int(card.h * icon_y),
        int(card.w * icon_w),
        int(card.h * icon_h),
    )
    limit = name_center - name_font.get_height() // 2 - 4
    if box.bottom > limit:
        box.height = max(12, limit - box.y)
    if index == 0:
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
