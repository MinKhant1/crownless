import pygame

from game.relics.relic_data import RelicDef, front_key
from rendering.asset_manager import AssetManager


# None keeps the visible illustration. A tuple is (x, y, width, height) from 0 to 1.
ART_CROPS: dict[str, tuple[float, float, float, float] | None] = {
    "banner": None,
    "blood_contract": None,
    "castle_wall": None,
    "chain_fuse": None,
    "collectors_crown": None,
    "conversion": None,
    "crowns_blessing": None,
    "first_blood": None,
    "flawless_victory": None,
    "graveyard": None,
    "recruitment": None,
    "royal_promotion": None,
    "squire": None,
    "gold_charm": None,
}


class RelicArtwork:
    def __init__(self) -> None:
        self._cache: dict[str, pygame.Surface | None] = {}

    def clear(self) -> None:
        self._cache.clear()

    def image(self, assets: AssetManager, relic: RelicDef) -> pygame.Surface | None:
        if relic.id in self._cache:
            return self._cache[relic.id]
        source = None
        for key in (f"relic_art_{relic.id}", f"relic_art_{front_key(relic).removeprefix('relic_front_')}"):
            if assets.has(key):
                source = assets.get(key)
                break
        if source is None:
            key = front_key(relic)
            if assets.has(key):
                source = assets.get(key)
        trimmed = None if source is None else _extract(source, ART_CROPS.get(relic.id))
        self._cache[relic.id] = trimmed
        return trimmed


def _extract(source: pygame.Surface, crop: tuple[float, float, float, float] | None) -> pygame.Surface:
    width, height = source.get_size()
    if crop is not None:
        rect = pygame.Rect(
            int(crop[0] * width),
            int(crop[1] * height),
            max(1, int(crop[2] * width)),
            max(1, int(crop[3] * height)),
        )
        rect.clamp_ip(source.get_rect())
    else:
        rect = source.get_bounding_rect()
        if rect.w < 2 or rect.h < 2:
            rect = source.get_rect()
    return source.subsurface(rect).copy()


artwork = RelicArtwork()
