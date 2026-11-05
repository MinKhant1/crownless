"""Writes the level sheet: where every black piece starts in all 30 stages.

    .venv\\Scripts\\python.exe tools\\levels\\make_level_sheet.py

docs/levels/level_sheet.png  - every stage drawn with the game's own board and pieces
docs/levels/levels.csv       - one row per enemy piece: stage, square, piece, special trait, covered by a pawn

Both are generated from ENEMY_FORMATIONS / ENEMY_TRAITS in config/settings.py, so run this again after editing them.
"""

import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

pygame.display.init()
pygame.font.init()
SCREEN = pygame.display.set_mode((1440, 900))

from config.settings import ENEMY_FORMATIONS, ENEMY_TRAITS, FILES, MAX_LEVEL, parse_square
from game.level_manager import describe_counts, formation_counts
from game.run_state import RunState
from rendering import style
from rendering.asset_manager import AssetManager
from rendering.effects import TRAIT_COLORS
from rendering.layout import build_layout
from rendering.relic_bar_renderer import RelicBar
from scenes.deployment_scene import DeploymentScene

OUT = ROOT / "docs" / "levels"
COLS = 6
TILE = 300          # board size on the sheet
CAPTION = 92        # space under each board
GAP = 26
MARGIN = 40
HEADER = 150
INK = (241, 228, 200)
SOFT = (196, 176, 140)
GOLD = (236, 196, 110)
BACK = (30, 20, 14)


def board_image(assets, layout, level: int) -> pygame.Surface:
    run = RunState(1)
    run.level = level
    run.prepare_level()  # preview phase: the enemy army only, nothing of yours deployed yet
    scene = DeploymentScene()
    bar = RelicBar()
    bar.bind(run)
    scene.draw(SCREEN, assets, run, layout, bar)
    board = SCREEN.subsurface(layout.board).copy()
    return pygame.transform.smoothscale(board, (TILE, TILE))


def specials(level: int) -> list[str]:
    kinds = {square: kind for kind, square in ENEMY_FORMATIONS[level]}
    return [f"{trait.title()} {kinds[square]} {square}" for square, trait in sorted(ENEMY_TRAITS.get(level, {}).items())]


def draw_tile(sheet: pygame.Surface, x: int, y: int, level: int, image: pygame.Surface) -> None:
    milestone = level % 5 == 0
    frame = pygame.Rect(x - 6, y - 6, TILE + 12, TILE + 12)
    pygame.draw.rect(sheet, GOLD if milestone else (92, 66, 44), frame, width=4 if milestone else 2, border_radius=6)
    sheet.blit(image, (x, y))
    label_font = style.body_font(13, bold=True)
    square = TILE / 6
    for col in range(6):  # file letters under the board
        text = label_font.render(FILES[col], True, SOFT)
        sheet.blit(text, text.get_rect(center=(x + square * col + square / 2, y + TILE + 13)))
    for row in range(1, 7):  # rank numbers left of the board
        text = label_font.render(str(row), True, SOFT)
        sheet.blit(text, text.get_rect(center=(x - 16, y + TILE - square * row + square / 2)))
    title = f"Stage {level}" + ("   (design sheet)" if milestone else "")
    style.text(sheet, title, style.title_font(20, bold=True), GOLD if milestone else INK, midleft=(x, y + TILE + 36))
    army = describe_counts(formation_counts(level))
    style.text(sheet, army, _fit(army, 14, False), INK, midleft=(x, y + TILE + 58))
    special = ", ".join(specials(level)) or "No special pieces"
    style.text(sheet, special, _fit(special, 13, True), SOFT if special.startswith("No") else GOLD, midleft=(x, y + TILE + 78))


def _fit(text: str, size: int, italic: bool) -> pygame.font.Font:
    font = style.body_font(size, italic=italic)
    while font.size(text)[0] > TILE and size > 9:
        size -= 1
        font = style.body_font(size, italic=italic)
    return font


def write_sheet(path: Path) -> None:
    assets = AssetManager(ROOT / "assets")
    layout = build_layout(1440, 900)
    rows = (MAX_LEVEL + COLS - 1) // COLS
    width = MARGIN * 2 + COLS * TILE + (COLS - 1) * (GAP + 20)
    height = HEADER + rows * (TILE + CAPTION + GAP) + 80
    sheet = pygame.Surface((width, height))
    sheet.fill(BACK)
    style.text(sheet, "Crownless - Enemy Formations", style.title_font(44, bold=True), INK, midleft=(MARGIN, 52))
    style.text(sheet, "Where every black piece starts, stages 1-30. Rank 6 is the enemy back rank, rank 5 its pawn line; "
               "you deploy on ranks 1-2. Gold frames follow the design sheet.", style.body_font(17), SOFT, midleft=(MARGIN, 96))
    legend_x = MARGIN
    for trait, color in TRAIT_COLORS.items():
        if trait in ("golden", "ghost"):
            continue
        pygame.draw.circle(sheet, color, (legend_x + 8, 128), 8)
        label = trait.title()
        style.text(sheet, label, style.body_font(16, bold=True), INK, midleft=(legend_x + 22, 128))
        legend_x += 40 + style.body_font(16, bold=True).size(label)[0]
    for index, level in enumerate(range(1, MAX_LEVEL + 1)):
        col, row = index % COLS, index // COLS
        x = MARGIN + 20 + col * (TILE + GAP + 20)
        y = HEADER + row * (TILE + CAPTION + GAP)
        draw_tile(sheet, x, y, level, board_image(assets, layout, level))
    pygame.image.save(sheet, str(path))


def write_csv(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["stage", "square", "piece", "special", "covered_by_pawn"])
        for level in range(1, MAX_LEVEL + 1):
            pawns = {parse_square(square)[0] for kind, square in ENEMY_FORMATIONS[level] if kind == "pawn"}
            ordered = sorted(ENEMY_FORMATIONS[level], key=lambda item: (-parse_square(item[1])[1], item[1]))
            for kind, square in ordered:
                trait = ENEMY_TRAITS.get(level, {}).get(square, "")
                covered = "" if kind == "pawn" else ("yes" if parse_square(square)[0] in pawns else "no")
                writer.writerow([level, square, kind, trait, covered])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write_sheet(OUT / "level_sheet.png")
    write_csv(OUT / "levels.csv")
    print(f"wrote {OUT / 'level_sheet.png'} and {OUT / 'levels.csv'}")


if __name__ == "__main__":
    main()
