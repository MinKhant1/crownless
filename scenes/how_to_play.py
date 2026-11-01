import random

import pygame

from ai.trait_definitions import AI_TRAITS, trait_description, trait_title
from config.settings import (
    GOLDEN_BONUS,
    MAX_LEVEL,
    SHOP_PIECE_KINDS,
    SHOP_PIECE_TRAITS,
    VICTORY_GOLD,
)
from game.piece import Piece
from game.relics.relic_data import RELICS, shop_relic_ids
from game.traits import TRAITS, trait_by_id
from game.transitions.easing import ease_out_cubic
from rendering.hud_renderer import _blit_text, draw_background, draw_button, get_font
from rendering.piece_visual_effects import figurines
from rendering.relic_card import CARD_RATIO, RelicCardRenderer
from scenes.menu_piece import MenuPiece, wrap_text


TABS = (
    ("play", "BASIC GAMEPLAY"),
    ("relics", "RELICS & COLLECTIONS"),
    ("pieces", "SPECIAL PIECES"),
    ("enemies", "ENEMY TRAITS"),
)

INK = (68, 40, 26)
MUTED = (92, 64, 42)
IVORY = (245, 232, 210)


class HowToPlayScreen:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.tab = "play"
        self.scroll = 0
        self.tab_age = 1.0
        self.age = 0.0
        self.notice = ""
        self.pawn = MenuPiece("pawn", TRAITS[0].id, piece_id=90002)
        self._held = False
        self._pointer = (0, 0)
        self._relic_cards = RelicCardRenderer()
        self._relic_offer: list[str] = []
        self._relic_pick: int | None = None
        self._piece_offer: list[tuple[str, str]] = []
        self._piece_pick: int | None = None
        self._enemy = AI_TRAITS[0]
        self._hits: list[tuple[str, pygame.Rect]] = []
        self._content_height = 0
        self._pawn_rest = pygame.Rect(0, 0, 1, 1)

    def open(self) -> None:
        self.age = 0.0
        self.tab = "play"
        self.scroll = 0
        self.tab_age = 1.0
        self.notice = ""
        self.pawn.trait = TRAITS[0].id
        self.pawn.on_release()
        self._relic_pick = None
        self._piece_pick = None
        pool = list(shop_relic_ids())
        self._relic_offer = self.rng.sample(pool, min(3, len(pool)))
        kinds = list(SHOP_PIECE_KINDS)
        self.rng.shuffle(kinds)
        self._piece_offer = [(kind, self.rng.choice(SHOP_PIECE_TRAITS)) for kind in kinds[:3]]

    def update(self, dt: float, window: tuple[int, int]) -> None:
        self.age += max(0.0, dt)
        self.tab_age = min(1.0, self.tab_age + max(0.0, dt) / 0.22)
        content = _frame(window)["content"]
        self._compose(content.w)
        if self.tab == "pieces":
            self.pawn.update(dt, self._pawn_rest, window)

    def on_event(self, event: pygame.event.Event, window: tuple[int, int]) -> str | None:
        frame = _frame(window)
        if event.type == pygame.MOUSEMOTION:
            self._pointer = event.pos
            if self.tab == "pieces":
                self.pawn.on_motion(event.pos, self._pawn_rest, window, self._held)
            return None
        if event.type == pygame.MOUSEWHEEL and frame["content"].collidepoint(self._pointer):
            self.scroll = _clamp_scroll(self.scroll - event.y * 42, self._content_height, frame["content"].h)
            return None
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "back"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._held = True
            if self.tab == "pieces" and self.pawn.on_press(event.pos, self._pawn_rest, window):
                return None
            return None
        if event.type != pygame.MOUSEBUTTONUP or event.button != 1:
            return None
        self._held = False
        self.pawn.on_release()
        for name, rect in self._hits:
            if not rect.collidepoint(event.pos):
                continue
            if name == "back":
                return "back"
            if name.startswith("tab:"):
                chosen = name.split(":", 1)[1]
                if chosen != self.tab:
                    self.tab = chosen
                    self.scroll = 0
                    self.tab_age = 0.0
                    self.notice = ""
                return None
            if name.startswith("enemy:"):
                self._enemy = name.split(":", 1)[1]
                return None
            if name == "pawn-prev":
                self._step_pawn(-1)
                return None
            if name == "pawn-next":
                self._step_pawn(1)
                return None
            if name.startswith("relic:"):
                self._relic_pick = int(name.split(":", 1)[1])
                self.notice = ""
                return None
            if name.startswith("piece:"):
                self._piece_pick = int(name.split(":", 1)[1])
                self.notice = ""
                return None
            if name == "relic-confirm":
                self.notice = "Preview only. No relic was added." if self._relic_pick is not None else "Choose a relic card first."
                return None
            if name == "piece-confirm":
                self.notice = "Preview only. No piece joined your army." if self._piece_pick is not None else "Choose a piece card first."
                return None
        return None

    def wants_hand(self) -> bool:
        if self.pawn.hovered or self.pawn.dragging:
            return True
        return any(rect.collidepoint(self._pointer) for _name, rect in self._hits)

    def draw(self, screen: pygame.Surface, assets) -> None:
        draw_background(screen, assets)
        window = screen.get_size()
        frame = _frame(window)
        panel = frame["panel"]
        pygame.draw.rect(screen, (48, 30, 20), panel, border_radius=18)
        pygame.draw.rect(screen, (236, 220, 196), panel.inflate(-10, -10), border_radius=14)
        pygame.draw.rect(screen, (214, 170, 90), panel, width=3, border_radius=18)
        _blit_text(screen, "How to Play", get_font(30, bold=True), INK, center=(panel.centerx, panel.y + 28))
        self._hits = [("back", frame["back"])]
        self._draw_tabs(screen, frame["tabs"])
        blocks = self._compose(frame["content"].w)
        self._content_height = sum(block[1] for block in blocks)
        self.scroll = _clamp_scroll(self.scroll, self._content_height, frame["content"].h)
        previous = screen.get_clip()
        screen.set_clip(frame["content"])
        shift = int((1.0 - ease_out_cubic(self.tab_age)) * 16)
        self._draw_blocks(screen, assets, frame["content"], blocks, shift, window)
        screen.set_clip(previous)
        if self.notice:
            _blit_text(screen, self.notice, get_font(16, bold=True), (120, 48, 36), center=(panel.centerx, frame["back"].y - 16))
        draw_button(screen, frame["back"], "BACK", font_size=18)

    def _step_pawn(self, direction: int) -> None:
        ids = [trait.id for trait in TRAITS]
        index = ids.index(self.pawn.trait) if self.pawn.trait in ids else 0
        self.pawn.trait = ids[(index + direction) % len(ids)]

    def _draw_tabs(self, screen: pygame.Surface, area: pygame.Rect) -> None:
        gap = 8
        width = max(1, (area.w - gap * (len(TABS) - 1)) // len(TABS))
        font = get_font(13, bold=True)
        for index, (key, label) in enumerate(TABS):
            rect = pygame.Rect(area.x + index * (width + gap), area.y, width, area.h)
            selected = key == self.tab
            fill = (120, 78, 36) if selected else (62, 38, 24)
            border = (232, 196, 96) if selected else (120, 84, 48)
            pygame.draw.rect(screen, fill, rect, border_radius=8)
            pygame.draw.rect(screen, border, rect, width=2, border_radius=8)
            _blit_text(screen, label, font, IVORY, center=rect.center)
            self._hits.append((f"tab:{key}", rect))

    def _compose(self, width: int) -> list[tuple[str, int, object]]:
        if self.tab == "play":
            return _play_blocks(width)
        if self.tab == "relics":
            return _relic_blocks(width)
        if self.tab == "pieces":
            return _piece_blocks(width)
        return _enemy_blocks(width)

    def _draw_blocks(
        self,
        screen: pygame.Surface,
        assets,
        content: pygame.Rect,
        blocks: list[tuple[str, int, object]],
        shift: int,
        window: tuple[int, int],
    ) -> None:
        y = content.y - self.scroll + shift
        for kind, height, payload in blocks:
            rect = pygame.Rect(content.x, y, content.w, height)
            if kind == "heading":
                _blit_text(screen, str(payload), get_font(22, bold=True), INK, midleft=(rect.x + 8, rect.y + 16))
            elif kind == "text":
                font = get_font(16, bold=False)
                line_y = rect.y
                for line in wrap_text(str(payload), font, rect.w - 16):
                    _blit_text(screen, line, font, MUTED, midleft=(rect.x + 8, line_y + 10))
                    line_y += 22
            elif kind == "board":
                _draw_mini_board(screen, assets, rect.inflate(-8, -8))
            elif kind == "relic-cards":
                self._draw_relic_cards(screen, assets, rect)
            elif kind == "piece-cards":
                self._draw_piece_cards(screen, assets, rect)
            elif kind == "chests":
                _draw_chests(screen, assets, rect)
            elif kind == "pawn":
                self._draw_pawn(screen, assets, rect, window)
            elif kind == "enemies":
                self._draw_enemies(screen, assets, rect)
            y += height

    def _draw_relic_cards(self, screen: pygame.Surface, assets, area: pygame.Rect) -> None:
        if not self._relic_offer:
            return
        card_h = min(210, area.h - 52)
        card_w = max(80, int(card_h * CARD_RATIO))
        gap = 16
        total = len(self._relic_offer) * card_w + (len(self._relic_offer) - 1) * gap
        left = area.centerx - total // 2
        for index, relic_id in enumerate(self._relic_offer):
            rect = pygame.Rect(left + index * (card_w + gap), area.y, card_w, card_h)
            relic = next(item for item in RELICS if item.id == relic_id)
            face = self._relic_cards.mini_surface(assets, relic, rect.w, rect.h, "active")
            screen.blit(face, rect.topleft)
            if self._relic_pick == index:
                pygame.draw.rect(screen, (232, 196, 96), rect.inflate(6, 6), width=3, border_radius=8)
            self._hits.append((f"relic:{index}", rect))
        button = pygame.Rect(0, 0, 180, 36)
        button.midtop = (area.centerx, area.bottom - 42)
        draw_button(screen, button, "Confirm Choice", enabled=self._relic_pick is not None, font_size=15)
        self._hits.append(("relic-confirm", button))

    def _draw_piece_cards(self, screen: pygame.Surface, assets, area: pygame.Rect) -> None:
        if not self._piece_offer:
            return
        card_w, card_h = 150, min(190, area.h - 52)
        gap = 16
        total = len(self._piece_offer) * card_w + (len(self._piece_offer) - 1) * gap
        left = area.centerx - total // 2
        for index, (kind, trait) in enumerate(self._piece_offer):
            rect = pygame.Rect(left + index * (card_w + gap), area.y, card_w, card_h)
            image = figurines.image(assets, Piece(91000 + index, kind, "white", trait=trait), int(rect.w * 0.7))
            screen.blit(image, image.get_rect(center=(rect.centerx, rect.y + int(rect.h * 0.38))))
            shown = trait_by_id(trait)
            label = f"{shown.name} {kind.capitalize()}" if shown else kind.capitalize()
            _blit_text(screen, label, get_font(14, bold=True), INK, center=(rect.centerx, rect.bottom - 22))
            if self._piece_pick == index:
                pygame.draw.rect(screen, (232, 196, 96), rect, width=3, border_radius=10)
            self._hits.append((f"piece:{index}", rect))
        button = pygame.Rect(0, 0, 180, 36)
        button.midtop = (area.centerx, area.bottom - 42)
        draw_button(screen, button, "Recruit", enabled=self._piece_pick is not None, font_size=15)
        self._hits.append(("piece-confirm", button))

    def _draw_pawn(self, screen: pygame.Surface, assets, area: pygame.Rect, window: tuple[int, int]) -> None:
        side = min(160, area.h - 36)
        rest = pygame.Rect(0, 0, side, side)
        rest.center = (area.centerx, area.centery)
        self._pawn_rest = rest
        previous = pygame.Rect(area.x + 12, rest.centery - 18, 36, 36)
        nxt = pygame.Rect(area.right - 48, rest.centery - 18, 36, 36)
        for name, rect, label in (("pawn-prev", previous, "<"), ("pawn-next", nxt, ">")):
            draw_button(screen, rect, label, font_size=18)
            self._hits.append((name, rect))
        self.pawn.paint(screen, assets, rest, window)
        trait = trait_by_id(self.pawn.trait)
        if trait is not None:
            _blit_text(screen, trait.name, get_font(20, bold=True), INK, center=(area.centerx, area.y + 16))
            font = get_font(15, bold=False)
            line_y = area.bottom - 36
            for line in wrap_text(trait.description, font, area.w - 120):
                _blit_text(screen, line, font, MUTED, center=(area.centerx, line_y))
                line_y += 18

    def _draw_enemies(self, screen: pygame.Surface, assets, area: pygame.Rect) -> None:
        font = get_font(15, bold=True)
        x = area.x + 8
        for trait in AI_TRAITS:
            rect = pygame.Rect(x, area.y + 8, 150, 54)
            selected = trait == self._enemy
            pygame.draw.rect(screen, (120, 78, 36) if selected else (62, 38, 24), rect, border_radius=8)
            pygame.draw.rect(screen, (232, 196, 96) if selected else (120, 84, 48), rect, width=2, border_radius=8)
            icon = _tag_icon(assets, trait, 36)
            if icon is not None:
                screen.blit(icon, icon.get_rect(midleft=(rect.x + 8, rect.centery)))
            _blit_text(screen, trait_title(trait).title(), font, IVORY, midleft=(rect.x + 48, rect.centery))
            self._hits.append((f"enemy:{trait}", rect))
            x += 158
            if x + 150 > area.right:
                x = area.x + 8
        detail = pygame.Rect(area.x + 8, area.y + 76, area.w - 16, area.h - 84)
        title = trait_title(self._enemy).title()
        _blit_text(screen, title, get_font(22, bold=True), INK, midleft=(detail.x, detail.y + 8))
        body = get_font(16, bold=False)
        line_y = detail.y + 36
        copy = trait_description(self._enemy) + " This personality is chosen once at the start of the battle and does not change on later turns."
        for line in wrap_text(copy, body, detail.w // 2):
            _blit_text(screen, line, body, MUTED, midleft=(detail.x, line_y))
            line_y += 22
        board = pygame.Rect(detail.right - 220, detail.y + 8, 200, 200)
        _draw_enemy_example(screen, assets, board, self._enemy)
        icon = _tag_icon(assets, self._enemy, 72)
        if icon is not None:
            screen.blit(icon, icon.get_rect(midtop=(detail.x + 80, line_y + 8)))


def _frame(window: tuple[int, int]) -> dict[str, pygame.Rect]:
    panel = pygame.Rect(0, 0, min(1080, window[0] - 36), min(860, window[1] - 24))
    panel.center = (window[0] // 2, window[1] // 2)
    tabs = pygame.Rect(panel.x + 24, panel.y + 52, panel.w - 48, 42)
    back = pygame.Rect(0, 0, 160, 42)
    back.midbottom = (panel.centerx, panel.bottom - 16)
    content = pygame.Rect(panel.x + 24, tabs.bottom + 12, panel.w - 48, back.y - tabs.bottom - 28)
    return {"panel": panel, "tabs": tabs, "content": content, "back": back}


def _clamp_scroll(scroll: int, content_h: int, view_h: int) -> int:
    return max(0, min(int(scroll), max(0, content_h - view_h)))


def _text_height(text: str, width: int) -> int:
    font = get_font(16, bold=False)
    return max(22, len(wrap_text(text, font, width - 16)) * 22)


def _play_blocks(width: int) -> list[tuple[str, int, object]]:
    sections = (
        ("Deployment", "You own an army of chess pieces. Before each battle, place them on your two home rows. Army size is how many pieces besides the King may start the battle. Pieces you leave off the board stay in reserve. Drag a piece from the army onto a highlighted home square, or swap two placed pieces, to change the formation."),
        ("Battle", "Pieces move by their chess rules unless a relic or special piece changes that. You and the enemy take turns. Captures can trigger relic effects. You win when no enemy pieces remain. You lose if your King is captured."),
        ("Progression", f"Win a battle to advance. Each victory pays {VICTORY_GOLD} gold, plus bonuses from surviving Golden pieces and some relics. The shop opens between battles, where you can recruit a piece, buy a relic, raise army size, or open a collection chest. There are {MAX_LEVEL} battles. Ghost pieces leave after the battle. Other pieces you still have return to the reserve army."),
    )
    blocks: list[tuple[str, int, object]] = []
    for title, body in sections:
        blocks.append(("heading", 36, title))
        blocks.append(("text", _text_height(body, width), body))
    blocks.append(("heading", 36, "Example"))
    blocks.append(("text", _text_height("A white knight moves onto a black pawn and captures it.", width), "A white knight moves onto a black pawn and captures it."))
    blocks.append(("board", 230, None))
    return blocks


def _relic_blocks(width: int) -> list[tuple[str, int, object]]:
    intro = "Relics grant passive or triggered effects. Some change how pieces move or capture. Others pay gold, add army size, or rewrite a piece at the start or end of a battle. Several relics can be owned at once, and their effects combine."
    examples = " ".join(f"{relic.name}: {relic.description}" for relic in RELICS if relic.in_shop)
    collection = "A Relic Collection costs gold in the shop and reveals three relics you do not already own. You keep one. The other two are discarded. A Piece Collection reveals three pieces. You recruit one, and it joins the reserve army. The cards below are a demonstration and do not spend gold or change a run."
    return [
        ("heading", 36, "Relics"),
        ("text", _text_height(intro, width), intro),
        ("text", _text_height(examples, width), examples),
        ("heading", 36, "Collections"),
        ("text", _text_height(collection, width), collection),
        ("chests", 150, None),
        ("heading", 36, "Relic collection preview"),
        ("relic-cards", 280, None),
        ("heading", 36, "Piece collection preview"),
        ("piece-cards", 260, None),
    ]


def _piece_blocks(width: int) -> list[tuple[str, int, object]]:
    intro = f"A special piece keeps its chess move and adds a trait. Golden pieces pay {GOLDEN_BONUS} gold for each one that is still on the board when you win. A Ghost is temporary and is removed when the battle ends. A piece that captures a Wooden piece cannot move for 2 turns. Wanted and Explosive are marked on the piece; their own battle effects are not active yet. Chain Fuse, if you own it, reacts when an Explosive piece dies."
    return [
        ("heading", 36, "Special pieces"),
        ("text", _text_height(intro, width), intro),
        ("pawn", 280, None),
    ]


def _enemy_blocks(width: int) -> list[tuple[str, int, object]]:
    intro = "Each battle gives the enemy one personality. Every enemy piece uses that personality for the whole battle. It is not rerolled between turns. A new battle can roll a different personality."
    return [
        ("heading", 36, "Enemy personalities"),
        ("text", _text_height(intro, width), intro),
        ("enemies", 320, None),
    ]


def _draw_mini_board(screen: pygame.Surface, assets, area: pygame.Rect) -> None:
    side = min(area.w, area.h, 220)
    origin = pygame.Rect(0, 0, side, side)
    origin.center = area.center
    tile = side // 4
    for row in range(4):
        for col in range(4):
            key = "light" if (col + row) % 2 == 0 else "dark"
            rect = pygame.Rect(origin.x + col * tile, origin.y + row * tile, tile, tile)
            if assets is not None and assets.has(key):
                screen.blit(assets.scaled(key, rect.size), rect.topleft)
            else:
                pygame.draw.rect(screen, (214, 176, 122) if key == "light" else (96, 62, 40), rect)
    knight = figurines.image(assets, Piece(1, "knight", "white"), tile - 4)
    pawn = figurines.image(assets, Piece(2, "pawn", "black"), tile - 4)
    screen.blit(knight, knight.get_rect(center=(origin.x + tile // 2, origin.y + tile + tile // 2)))
    screen.blit(pawn, pawn.get_rect(center=(origin.x + 2 * tile + tile // 2, origin.y + tile // 2)))
    pygame.draw.line(
        screen,
        (186, 42, 36),
        (origin.x + tile // 2, origin.y + tile + tile // 2),
        (origin.x + 2 * tile + tile // 2, origin.y + tile // 2),
        3,
    )


def _draw_chests(screen: pygame.Surface, assets, area: pygame.Rect) -> None:
    for index, (key, label) in enumerate((("relic_chest", "Relic Collection"), ("piece_chest", "Piece Collection"))):
        rect = pygame.Rect(0, 0, 120, 120)
        rect.center = (area.centerx - 90 + index * 180, area.centery - 8)
        if assets is not None and assets.has(key):
            image = assets.fitted(key, rect.w, rect.h)
            screen.blit(image, image.get_rect(center=rect.center))
        _blit_text(screen, label, get_font(14, bold=True), INK, center=(rect.centerx, rect.bottom + 8))


def _draw_enemy_example(screen: pygame.Surface, assets, area: pygame.Rect, trait: str) -> None:
    tile = area.w // 3
    for row in range(3):
        for col in range(3):
            key = "light" if (col + row) % 2 == 0 else "dark"
            rect = pygame.Rect(area.x + col * tile, area.y + row * tile, tile, tile)
            if assets is not None and assets.has(key):
                screen.blit(assets.scaled(key, rect.size), rect.topleft)
    piece = figurines.image(assets, Piece(3, "knight", "black", ai_trait=trait), tile - 6)
    screen.blit(piece, piece.get_rect(center=(area.x + tile + tile // 2, area.y + tile + tile // 2)))


def _tag_icon(assets, trait: str, size: int):
    key = f"tag_{trait}"
    if assets is None or not assets.has(key):
        return None
    return assets.fitted(key, size, size)
