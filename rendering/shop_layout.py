from dataclasses import dataclass

import pygame

from config.settings import (
    CARD_SOURCE,
    PRICE_SOURCE,
    REROLL_SOURCE,
    SHOP_BACKGROUND_SCALE,
    SHOP_BUY,
    SHOP_CARD_CENTER_Y,
    SHOP_CARD_GAP_FRAC,
    SHOP_CARD_WIDTH_FRAC,
    SHOP_GOLD_WIDTH_FRAC,
    SHOP_PRICE_GAP_FRAC,
    SHOP_REROLL_LABEL,
    SHOP_REROLL_WIDTH_FRAC,
    SHOP_SIDE_RESERVE,
    SHOP_SOURCE,
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


def build_shop_layout(window_w: int, window_h: int) -> ShopLayout:
    reserve = SHOP_SIDE_RESERVE
    max_width = max(280, window_w - reserve * 2)
    max_height = max(320, window_h - 20)
    aspect = SHOP_SOURCE[0] / SHOP_SOURCE[1]
    height = max_height
    width = int(round(height * aspect))
    if width > max_width:
        width = max_width
        height = int(round(width / aspect))
    width = int(round(width * SHOP_BACKGROUND_SCALE))
    height = int(round(height * SHOP_BACKGROUND_SCALE))
    width_limit = max(280, window_w - 16)
    if width > width_limit:
        width = width_limit
        height = int(round(width / aspect))
    background = pygame.Rect((window_w - width) // 2, (window_h - height) // 2, width, height)
    card_w = max(88, int(width * SHOP_CARD_WIDTH_FRAC))
    card_h = max(88, int(round(card_w * CARD_SOURCE[1] / CARD_SOURCE[0])))
    gap = max(6, int(width * SHOP_CARD_GAP_FRAC))
    total = card_w * 3 + gap * 2
    if total > background.w - 8:
        scale = (background.w - 8) / total
        card_w = max(72, int(card_w * scale))
        card_h = max(72, int(round(card_w * CARD_SOURCE[1] / CARD_SOURCE[0])))
        gap = max(4, int(gap * scale))
        total = card_w * 3 + gap * 2
    left = background.x + (background.w - total) // 2
    card_y = background.y + int(background.h * SHOP_CARD_CENTER_Y) - card_h // 2
    tag_w = int(card_w * 0.96)
    tag_h = max(26, int(round(tag_w * PRICE_SOURCE[1] / PRICE_SOURCE[0])))
    tag_gap = max(2, int(height * SHOP_PRICE_GAP_FRAC))
    cards: list[pygame.Rect] = []
    tags: list[pygame.Rect] = []
    buys: list[pygame.Rect] = []
    buy_x, buy_y, buy_w, buy_h = SHOP_BUY
    for index in range(3):
        card = pygame.Rect(left + index * (card_w + gap), card_y, card_w, card_h)
        cards.append(card)
        tags.append(pygame.Rect(card.centerx - tag_w // 2, card.y - tag_gap - tag_h, tag_w, tag_h))
        buys.append(
            pygame.Rect(
                card.x + int(card.w * buy_x),
                card.y + int(card.h * buy_y),
                int(card.w * buy_w),
                int(card.h * buy_h),
            )
        )
    reroll_w = min(int(background.w * SHOP_REROLL_WIDTH_FRAC), max(140, background.x - 20))
    reroll_h = max(70, int(round(reroll_w * REROLL_SOURCE[1] / REROLL_SOURCE[0])))
    reroll = pygame.Rect(max(8, background.x - reroll_w - 10), background.bottom - reroll_h + 6, reroll_w, reroll_h)
    if reroll.bottom > window_h - 8:
        reroll.bottom = window_h - 8
    label_x, label_y, label_w, label_h = SHOP_REROLL_LABEL
    reroll_label = pygame.Rect(
        reroll.x + int(reroll.w * label_x),
        reroll.y + int(reroll.h * label_y),
        int(reroll.w * label_w),
        int(reroll.h * label_h),
    )
    gold_w = min(int(background.w * SHOP_GOLD_WIDTH_FRAC), max(150, window_w - background.right - 20))
    gold_h = max(40, int(round(gold_w * PRICE_SOURCE[1] / PRICE_SOURCE[0])))
    gold = pygame.Rect(background.right + 12, background.y + int(background.h * 0.16), gold_w, gold_h)
    if gold.right > window_w - 8:
        gold.x = window_w - gold_w - 8
    button = pygame.Rect(gold.x, background.bottom - 58, gold_w, 48)
    if button.bottom > window_h - 8:
        button.bottom = window_h - 8
    notice = pygame.Rect(gold.x, gold.bottom + 10, gold_w, 56)
    return ShopLayout(background, cards, tags, buys, reroll, reroll_label, gold, button, notice)
