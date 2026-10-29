"""Build the curtain panel from a photo of straight-hanging red velvet.

The panel is a right-hand curtain (inner edge on its left); the page mirrors it for the left side.

usage:
  uv run --no-project --with pillow python scripts/make_curtain.py \
      <velvet_photo.jpg> web/public/curtain.webp \
      [colour brightness]

Source (Unsplash license, free to use): "A red curtain with a black background"
by Ambitious Studio* | Rick Barrett,
https://unsplash.com/photos/a-red-curtain-with-a-black-background-AwsdyjRm-kw
"""

import sys

from PIL import Image, ImageEnhance

src_path, out_path = sys.argv[1:3]
colour, brightness = (float(v) for v in (sys.argv[3:5] or (1.15, 1.06)))
HALF_WIDTH = 0.16  # crop half-width around the crest, as a fraction of the photo width
OUT_HEIGHT = 2200

photo = Image.open(src_path).convert("RGB")
w, h = photo.size
# centre the panel on the broad crest in the middle of the photo, so the page (object-position: center)
# shows that crest in the middle of the visible strip at any window size
small = photo.convert("L").resize((400, 60))
cols = [sum(small.getpixel((x, y)) for y in range(60)) for x in range(400)]
cols = [sum(cols[max(0, i - 6) : i + 7]) / len(cols[max(0, i - 6) : i + 7]) for i in range(400)]
peaks = [i for i in range(1, 399) if cols[i] >= cols[i - 1] and cols[i] >= cols[i + 1] and 168 <= i <= 232]
crest = max(peaks, key=lambda i: cols[i]) / 400
panel = photo.crop((int(w * (crest - HALF_WIDTH)), 0, int(w * (crest + HALF_WIDTH)), h))
panel = panel.resize((round(panel.width * OUT_HEIGHT / panel.height), OUT_HEIGHT), Image.LANCZOS)
panel = ImageEnhance.Color(panel).enhance(colour)
panel = ImageEnhance.Brightness(panel).enhance(brightness)
# a slightly deeper red: pull green (the orange component) down a touch
r, g, b = panel.split()
panel = Image.merge("RGB", (r, g.point(lambda v: v * 0.88), b))
panel.save(out_path, "WEBP", quality=86, method=6)
print("panel", panel.size, "crest at", round(crest, 3))
