from dataclasses import dataclass

import pygame

from config.settings import (
    PRICE_SOURCE,
    REROLL_SOURCE,
    SHOP_BACKGROUND_SCALE,
    SHOP_BG_SOURCE,
    SHOP_RELIC_CARD_SCALE,
    SHOP_REROLL_LABEL,
    SHOP_SLOT_BOUNDS,
)
from rendering.relic_card import CARD_RATIO


@dataclass
class ShopLayout:
    background: pygame.Rect
    cards: list[pygame.Rect]
    tags: list[pygame.Rect]
    buys: list[pygame.Rect]
    reroll: pygame.Rect
    reroll_label: pygame.Rect
    gold: pygame.Rect
    continue_button: pygame.Rect
    notice: pygame.Rect
    slots: dict[str, pygame.Rect]


def build_shop_layout(window_w: int, window_h: int, left_edge: int = 0) -> ShopLayout:
    offset = max(0, int(left_edge))
    area = pygame.Rect(offset + 8, 8, max(1, int(window_w) - offset - 16), max(1, int(window_h) - 16))
    aspect = SHOP_BG_SOURCE[0] / SHOP_BG_SOURCE[1]
    width = area.w
    height = max(1, int(round(width / aspect)))
    if height > area.h:
        height = area.h
        width = max(1, int(round(height * aspect)))
    width = max(1, int(round(width * SHOP_BACKGROUND_SCALE)))
    height = max(1, int(round(height * SHOP_BACKGROUND_SCALE)))
    background = pygame.Rect(0, 0, width, height)
    background.center = area.center
    image_w, image_h = SHOP_BG_SOURCE
    slots = {
        key: map_shop_rect(bounds, background, image_w, image_h)
        for key, bounds in SHOP_SLOT_BOUNDS.items()
    }
    piece_art = _art_band(slots["piece"])
    relic_art = _scale_about_center(_fit_card(_art_band(slots["relic"]), CARD_RATIO), SHOP_RELIC_CARD_SCALE)
    army_art = _art_band(slots["army_size"])
    cards = [piece_art, relic_art, army_art]
    tags = [_price_anchor(slots[key]) for key in ("piece", "relic", "army_size", "relic_collection", "piece_collection")]
    buys = [_buy_anchor(slots[key]) for key in ("piece", "relic", "army_size")]
    reroll_w = max(96, min(150, int(background.w * 0.13)))
    reroll_h = max(52, int(round(reroll_w * REROLL_SOURCE[1] / REROLL_SOURCE[0])))
    reroll = pygame.Rect(0, 0, reroll_w, reroll_h)
    reroll.center = _image_point(background, 0.34, 0.905)
    label_x, label_y, label_w, label_h = SHOP_REROLL_LABEL
    reroll_label = pygame.Rect(
        reroll.x + int(reroll.w * label_x),
        reroll.y + int(reroll.h * label_y),
        int(reroll.w * label_w),
        int(reroll.h * label_h),
    )
    gold_w = max(120, min(180, int(background.w * 0.16)))
    gold_h = max(36, int(round(gold_w * PRICE_SOURCE[1] / PRICE_SOURCE[0])))
    gold = pygame.Rect(0, 0, gold_w, gold_h)
    gold.center = _image_point(background, 0.52, 0.905)
    button = pygame.Rect(0, 0, max(120, int(background.w * 0.13)), max(40, int(background.h * 0.06)))
    button.center = (int(window_w) // 2, _image_point(background, 0.70, 0.905)[1])
    notice = pygame.Rect(gold.x, gold.y - 28, gold.w, 24)
    screen_bounds = pygame.Rect(offset + 8, 8, max(1, int(window_w) - offset - 16), max(1, int(window_h) - 16))
    _nudge_inside(reroll, screen_bounds)
    reroll_label.topleft = (
        reroll.x + int(reroll.w * label_x),
        reroll.y + int(reroll.h * label_y),
    )
    _nudge_inside(gold, screen_bounds)
    _nudge_inside(button, pygame.Rect(8, 8, max(1, int(window_w) - 16), max(1, int(window_h) - 16)))
    notice.midbottom = (gold.centerx, gold.y - 4)
    return ShopLayout(background, cards, tags, buys, reroll, reroll_label, gold, button, notice, slots)


def map_shop_rect(
    relative_rect: tuple[float, float, float, float],
    shop_bg_rect: pygame.Rect,
    image_width: int,
    image_height: int,
) -> pygame.Rect:
    x, y, w, h = relative_rect
    return pygame.Rect(
        int(round(shop_bg_rect.x + x * shop_bg_rect.w / image_width)),
        int(round(shop_bg_rect.y + y * shop_bg_rect.h / image_height)),
        max(1, int(round(w * shop_bg_rect.w / image_width))),
        max(1, int(round(h * shop_bg_rect.h / image_height))),
    )


def _nudge_inside(rect: pygame.Rect, bounds: pygame.Rect) -> None:
    if rect.right > bounds.right:
        rect.right = bounds.right
    if rect.left < bounds.left:
        rect.left = bounds.left
    if rect.bottom > bounds.bottom:
        rect.bottom = bounds.bottom
    if rect.top < bounds.top:
        rect.top = bounds.top


def _image_point(bounds: pygame.Rect, x: float, y: float) -> tuple[int, int]:
    return bounds.x + int(bounds.w * x), bounds.y + int(bounds.h * y)


def _art_band(slot: pygame.Rect) -> pygame.Rect:
    label_h = max(40, int(slot.h * 0.30))
    return pygame.Rect(slot.x + 4, slot.y + 2, max(1, slot.w - 8), max(1, slot.h - label_h))


def _scale_about_center(rect: pygame.Rect, scale: float) -> pygame.Rect:
    grown = pygame.Rect(rect)
    grown.w = max(1, int(round(rect.w * scale)))
    grown.h = max(1, int(round(rect.h * scale)))
    grown.center = rect.center
    return grown


def _fit_card(area: pygame.Rect, ratio: float) -> pygame.Rect:
    height = area.h
    width = max(1, int(round(height * ratio)))
    if width > area.w:
        width = area.w
        height = max(1, int(round(width / ratio)))
    rect = pygame.Rect(0, 0, width, height)
    rect.center = area.center
    return rect


def _price_anchor(slot: pygame.Rect) -> pygame.Rect:
    rect = pygame.Rect(0, 0, max(72, int(slot.w * 0.72)), 26)
    rect.midbottom = (slot.centerx, slot.bottom - 2)
    return rect


def _buy_anchor(slot: pygame.Rect) -> pygame.Rect:
    rect = pygame.Rect(0, 0, max(88, int(slot.w * 0.78)), 28)
    rect.midbottom = (slot.centerx, slot.bottom - 2)
    return rect
