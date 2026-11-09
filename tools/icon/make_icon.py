"""Make the app icons from one square picture.

    .venv\\Scripts\\python.exe tools\\icon\\make_icon.py path\\to\\icon_art.png

Writes into assets/icon/:
    crownless.png   window / taskbar / dock icon, loaded by main.py
    crownless.ico   Windows exe icon (crownless.spec)
    crownless.icns  macOS app icon (crownless.spec)

A plain white background around the rounded square is made transparent.
Needs Pillow (tools/requirements.txt).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "icon"
SIZE = 1024
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
WHITE_TOLERANCE = 60


def _clear_white_border(image: Image.Image) -> Image.Image:
    """Flood the white margin from each corner with transparency, keeping the art inside untouched."""
    if image.getextrema()[3][0] < 255:
        return image  # already has transparency
    marker = (255, 0, 255, 0)
    flooded = image.copy()
    w, h = flooded.size
    for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if flooded.getpixel(corner)[3] != 0:
            ImageDraw.floodfill(flooded, corner, marker, thresh=WHITE_TOLERANCE)
    alpha = Image.new("L", (w, h), 255)
    src, out = flooded.load(), alpha.load()
    for y in range(h):
        for x in range(w):
            if src[x, y] == marker:
                out[x, y] = 0
    result = image.copy()
    result.putalpha(alpha)
    return result


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    art = Image.open(sys.argv[1]).convert("RGBA")
    side = max(art.size)
    square = Image.new("RGBA", (side, side), (255, 255, 255, 255))
    square.paste(art, ((side - art.width) // 2, (side - art.height) // 2))
    icon = _clear_white_border(square.resize((SIZE, SIZE), Image.LANCZOS))

    # Windows and the game window show the icon at small sizes, so crop the empty margin there.
    # macOS expects the margin (its icon grid leaves ~10% around the rounded square), so .icns keeps it.
    box = icon.getchannel("A").getbbox() or (0, 0, SIZE, SIZE)
    edge = max(box[2] - box[0], box[3] - box[1])
    cx, cy = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
    tight = icon.crop((cx - edge // 2, cy - edge // 2, cx - edge // 2 + edge, cy - edge // 2 + edge))
    tight = tight.resize((512, 512), Image.LANCZOS)

    OUT.mkdir(parents=True, exist_ok=True)
    tight.save(OUT / "crownless.png")
    tight.save(OUT / "crownless.ico", sizes=ICO_SIZES)
    icon.save(OUT / "crownless.icns")
    print(f"Wrote crownless.png, crownless.ico, crownless.icns to {OUT}")


if __name__ == "__main__":
    main()
