from pathlib import Path

import pygame

from config.settings import HUD_FILES, PIECE_KINDS, SHOP_FILES


class AssetManager:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._raw: dict[str, pygame.Surface] = {}
        self._scaled: dict[tuple, pygame.Surface] = {}
        self._load()

    def _load(self) -> None:
        hud = self.root / "hud"
        for key, filename in HUD_FILES.items():
            self._raw[key] = pygame.image.load(hud / filename).convert_alpha()
        shop = hud / "shop"
        for key, filename in SHOP_FILES.items():
            image = pygame.image.load(shop / filename).convert_alpha()
            if key == "shop_background":
                image = _drop_checkerboard(image)
            self._raw[key] = image
        pieces = self.root / "pieces" / "normal"
        for color in ("white", "black"):
            for kind in PIECE_KINDS:
                key = f"{color}_{kind}"
                self._raw[key] = pygame.image.load(pieces / f"{key}.png").convert_alpha()
        self._load_optional(self.root / "relics" / "card_background.png", "relic_card")
        self._load_optional(self.root / "relics" / "back_card.png", "relic_back")
        art = self.root / "relics" / "art"
        if art.exists():
            for path in art.glob("*.png"):
                self._load_optional(path, f"relic_art_{path.stem}")
        fronts = self.root / "relics"
        if fronts.exists():
            for path in fronts.glob("*.png"):
                if path.stem in ("back_card", "card_background"):
                    continue
                self._load_optional(path, f"relic_front_{path.stem}")

    def has(self, key: str) -> bool:
        return key in self._raw

    def get(self, key: str) -> pygame.Surface:
        return self._raw[key]

    def _load_optional(self, path: Path, key: str) -> None:
        if path.exists():
            self._raw[key] = pygame.image.load(path).convert_alpha()

    def scaled(self, key: str, size: tuple[int, int]) -> pygame.Surface:
        width = max(1, int(size[0]))
        height = max(1, int(size[1]))
        cache_key = (key, width, height)
        cached = self._scaled.get(cache_key)
        if cached is None:
            cached = pygame.transform.smoothscale(self._raw[key], (width, height))
            self._scaled[cache_key] = cached
        return cached

    def fitted(self, key: str, max_width: int, max_height: int) -> pygame.Surface:
        raw = self._raw[key]
        raw_width, raw_height = raw.get_size()
        scale = min(max_width / raw_width, max_height / raw_height)
        width = max(1, int(round(raw_width * scale)))
        height = max(1, int(round(raw_height * scale)))
        return self.scaled(key, (width, height))

    def cover(self, key: str, width: int, height: int) -> tuple[pygame.Surface, tuple[int, int]]:
        raw_width, raw_height = self._raw[key].get_size()
        scale = max(width / raw_width, height / raw_height)
        surface_width = max(1, int(round(raw_width * scale)))
        surface_height = max(1, int(round(raw_height * scale)))
        surface = self.scaled(key, (surface_width, surface_height))
        origin = ((width - surface_width) // 2, (height - surface_height) // 2)
        return surface, origin

    def clear_scaled(self) -> None:
        self._scaled.clear()


def _neutral(red: int, green: int, blue: int, spread: int, floor: int) -> bool:
    return max(red, green, blue) - min(red, green, blue) <= spread and min(red, green, blue) >= floor


def _drop_checkerboard(surface: pygame.Surface) -> pygame.Surface:
    width, height = surface.get_size()
    buf = bytearray(pygame.image.tobytes(surface, "RGBA"))
    seen = bytearray(width * height)
    stack: list[int] = []

    def consider(index: int) -> None:
        if seen[index]:
            return
        seen[index] = 1
        offset = index * 4
        if _neutral(buf[offset], buf[offset + 1], buf[offset + 2], 16, 205):
            stack.append(index)

    for x in range(width):
        consider(x)
        consider((height - 1) * width + x)
    for y in range(height):
        consider(y * width)
        consider(y * width + width - 1)
    while stack:
        index = stack.pop()
        offset = index * 4
        buf[offset : offset + 4] = b"\x00\x00\x00\x00"
        x = index % width
        y = index // width
        if x > 0:
            consider(index - 1)
        if x + 1 < width:
            consider(index + 1)
        if y > 0:
            consider(index - width)
        if y + 1 < height:
            consider(index + width)
    for _repeat in range(2):
        fringe: list[int] = []
        for index in range(width * height):
            offset = index * 4
            if buf[offset + 3] == 0:
                continue
            if not _neutral(buf[offset], buf[offset + 1], buf[offset + 2], 28, 175):
                continue
            x = index % width
            y = index // width
            neighbors = []
            if x > 0:
                neighbors.append(index - 1)
            if x + 1 < width:
                neighbors.append(index + 1)
            if y > 0:
                neighbors.append(index - width)
            if y + 1 < height:
                neighbors.append(index + width)
            if any(buf[item * 4 + 3] == 0 for item in neighbors):
                fringe.append(index)
        for index in fringe:
            offset = index * 4
            buf[offset : offset + 4] = b"\x00\x00\x00\x00"
    return pygame.image.frombytes(bytes(buf), (width, height), "RGBA").convert_alpha()
