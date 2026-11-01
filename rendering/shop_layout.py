from dataclasses import dataclass

import pygame

from config.settings import (
    PRICE_SOURCE,
    REROLL_SOURCE,
    SHOP_BG_SOURCE,
    SHOP_BUY,
    SHOP_REROLL_LABEL,
    SHOP_SLOT_FRACTIONS,
)


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
    background = pygame.Rect(0, 0, width, height)
    background.center = area.center
    slots = {key: _fraction_rect(background, fractions) for key, fractions in SHOP_SLOT_FRACTIONS.items()}
    order = ("piece", "relic", "army_size")
    cards = [slots[key].copy() for key in order]
    tags = [_price_rect(card) for card in cards]
    tags.append(_price_rect(slots["relic_collection"]))
    tags.append(_price_rect(slots["piece_collection"]))
    buy_x, _buy_y, buy_w, buy_h = SHOP_BUY
    buys = []
    for card in cards:
        buy = pygame.Rect(
            card.x + int(card.w * buy_x),
            card.bottom - max(28, int(card.h * buy_h)),
            max(1, int(card.w * buy_w)),
            max(28, int(card.h * buy_h)),
        )
        buys.append(buy)
    reroll_w = max(108, min(168, int(background.w * 0.16)))
    reroll_h = max(56, int(round(reroll_w * REROLL_SOURCE[1] / REROLL_SOURCE[0])))
    reroll = pygame.Rect(0, 0, reroll_w, reroll_h)
    reroll.midbottom = (background.x + int(background.w * 0.40), background.bottom - int(background.h * 0.045))
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
    gold.center = (background.x + int(background.w * 0.62), reroll.centery)
    button = pygame.Rect(0, 0, max(132, int(background.w * 0.14)), max(42, int(background.h * 0.065)))
    button.midright = (background.right - int(background.w * 0.055), reroll.centery)
    notice = pygame.Rect(gold.x, gold.y - 28, gold.w, 24)
    return ShopLayout(background, cards, tags, buys, reroll, reroll_label, gold, button, notice, slots)


def _fraction_rect(bounds: pygame.Rect, fractions: tuple[float, float, float, float]) -> pygame.Rect:
    x, y, w, h = fractions
    return pygame.Rect(
        bounds.x + int(bounds.w * x),
        bounds.y + int(bounds.h * y),
        max(1, int(bounds.w * w)),
        max(1, int(bounds.h * h)),
    )


def _price_rect(card: pygame.Rect) -> pygame.Rect:
    width = max(72, int(card.w * 0.72))
    height = max(22, min(34, int(card.h * 0.16)))
    rect = pygame.Rect(0, 0, width, height)
    rect.midbottom = (card.centerx, card.bottom - 2)
    return rect
