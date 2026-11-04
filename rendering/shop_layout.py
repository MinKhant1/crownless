from dataclasses import dataclass

import pygame

from config.settings import (
    SHOP_BACKGROUND_SCALE,
    SHOP_BG_SOURCE,
    SHOP_CONTINUE_BOUNDS,
    SHOP_NOTICE_BOUNDS,
    SHOP_PRICE_TAG,
    SHOP_REROLL_BOUNDS,
    SHOP_REROLL_LABEL,
    SHOP_SLOT_BOUNDS,
)

OFFER_KEYS = ("piece", "relic", "army_size")
CHEST_KEYS = ("relic_collection", "piece_collection")


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

    def mapped(bounds):
        return map_shop_rect(bounds, background, image_w, image_h)

    slots = {key: mapped(bounds) for key, bounds in SHOP_SLOT_BOUNDS.items()}
    # cards are the parchment windows inside each frame, above the name plaque
    cards = [_art_window(slots[key]) for key in OFFER_KEYS]
    tags = [_price_tag(slots[key], background.w / image_w) for key in OFFER_KEYS + CHEST_KEYS]
    buys = [_name_plaque(slots[key]) for key in OFFER_KEYS]
    reroll = mapped(SHOP_REROLL_BOUNDS)
    button = mapped(SHOP_CONTINUE_BOUNDS)
    notice = mapped(SHOP_NOTICE_BOUNDS)
    screen_bounds = pygame.Rect(offset + 8, 8, max(1, int(window_w) - offset - 16), max(1, int(window_h) - 16))
    for rect in (reroll, button, notice):
        _nudge_inside(rect, screen_bounds)
    label_x, label_y, label_w, label_h = SHOP_REROLL_LABEL
    reroll_label = pygame.Rect(
        reroll.x + int(reroll.w * label_x),
        reroll.y + int(reroll.h * label_y),
        int(reroll.w * label_w),
        int(reroll.h * label_h),
    )
    return ShopLayout(background, cards, tags, buys, reroll, reroll_label, notice.copy(), button, notice, slots)


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


def _art_window(frame: pygame.Rect) -> pygame.Rect:
    # buying_square.png: parchment from 11% to 89% across and 9% to 71% down, name plaque below
    return pygame.Rect(
        frame.x + int(frame.w * 0.12),
        frame.y + int(frame.h * 0.10),
        max(1, int(frame.w * 0.76)),
        max(1, int(frame.h * 0.60)),
    )


def _name_plaque(frame: pygame.Rect) -> pygame.Rect:
    return pygame.Rect(
        frame.x + int(frame.w * 0.16),
        frame.y + int(frame.h * 0.77),
        max(1, int(frame.w * 0.68)),
        max(1, int(frame.h * 0.15)),
    )


def _price_tag(item: pygame.Rect, scale: float) -> pygame.Rect:
    rect = pygame.Rect(0, 0, max(1, round(SHOP_PRICE_TAG[0] * scale)), max(1, round(SHOP_PRICE_TAG[1] * scale)))
    rect.midbottom = (item.centerx, item.top - max(2, round(8 * scale)))
    return rect
