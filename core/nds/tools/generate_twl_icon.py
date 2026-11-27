"""Generate the 32x32 TWiLight Menu Pokewalker banner icon.

The indexed BMP uses palette index 255 for transparent pixels, matching the
Calico/devkitPro NDS banner bitmap convention.
"""

from pathlib import Path
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "assets" / "pokewalker-icon.bmp"

COLORS = {
    1: (8, 12, 16),       # outline and device seam
    2: (176, 31, 42),      # red shadow
    3: (232, 48, 58),      # red shell
    4: (250, 82, 87),      # shell highlight
    5: (235, 237, 224),    # white shell
    6: (176, 184, 178),    # button shadow
    7: (248, 248, 236),    # button face
    8: (55, 64, 61),       # LCD frame
    9: (169, 184, 143),    # LCD face
    10: (101, 130, 95),    # LCD pixels
    11: (53, 83, 67),      # dark LCD pixels
    12: (122, 133, 126),   # side mark
    13: (255, 255, 255),   # shine
    255: (0, 0, 0),        # transparent background
}


def main() -> None:
    image = Image.new("P", (32, 32), 255)
    palette = [0] * (256 * 3)
    for index, rgb in COLORS.items():
        palette[index * 3 : index * 3 + 3] = rgb
    image.putpalette(palette)
    draw = ImageDraw.Draw(image)

    # Rounded, circular body with a red upper shell and white lower shell.
    draw.ellipse((1, 0, 30, 31), fill=1)
    cx, cy, radius = 15.5, 15.5, 13.6
    for y in range(2, 30):
        dy = y - cy
        half = int((radius * radius - dy * dy) ** 0.5)
        if half < 0:
            continue
        left, right = round(cx - half), round(cx + half)
        color = 3 if y < 15 else 5
        draw.line((left, y, right, y), fill=color)
        if y < 8 and (y % 2 == 0):
            draw.line((left + 3, y, min(right - 4, left + 12), y), fill=4)

    # Side trim and the black seam are visible around the screen bezel.
    draw.line((3, 15, 8, 15), fill=1, width=2)
    draw.line((23, 15, 28, 15), fill=1, width=2)
    draw.line((3, 16, 8, 16), fill=1)
    draw.line((23, 16, 28, 16), fill=1)

    # LCD with a tiny route/tree motif, matching the device's original face.
    draw.rounded_rectangle((7, 9, 24, 21), radius=2, fill=1)
    draw.rectangle((8, 10, 23, 20), fill=8)
    draw.rectangle((9, 11, 22, 18), fill=9)
    draw.rectangle((9, 19, 22, 19), fill=10)
    draw.rectangle((10, 17, 13, 18), fill=11)
    draw.rectangle((11, 15, 12, 17), fill=10)
    draw.rectangle((12, 13, 14, 15), fill=10)
    draw.rectangle((17, 13, 18, 17), fill=11)
    draw.rectangle((16, 14, 20, 15), fill=10)
    draw.rectangle((18, 12, 19, 14), fill=10)
    draw.rectangle((20, 16, 21, 17), fill=11)
    draw.rectangle((20, 11, 21, 12), fill=10)

    # Two small directional buttons and the round center button.
    draw.polygon(((5, 23), (8, 21), (8, 25)), fill=6)
    draw.polygon(((6, 23), (8, 22), (8, 24)), fill=7)
    draw.polygon(((27, 23), (24, 21), (24, 25)), fill=6)
    draw.polygon(((26, 23), (24, 22), (24, 24)), fill=7)
    draw.ellipse((13, 24, 18, 29), fill=6)
    draw.ellipse((14, 24, 17, 28), fill=7)
    draw.ellipse((15, 25, 16, 26), fill=8)
    draw.line((6, 20, 6, 17), fill=12)
    draw.point((7, 18), fill=13)

    image.save(DESTINATION, format="BMP")
    print(f"Generated {DESTINATION}")


if __name__ == "__main__":
    main()
