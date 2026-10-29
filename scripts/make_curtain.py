"""Build the curtain panel from a photo of straight-hanging red velvet.

The panel is a right-hand curtain (inner edge on its left); the page mirrors it for the left side.

usage:
  uv run --no-project --with pillow python scripts/make_curtain.py <velvet_photo.jpg> web/public/curtain.webp

Source (Unsplash license, free to use): "A red curtain with a black background"
by Ambitious Studio* | Rick Barrett,
https://unsplash.com/photos/a-red-curtain-with-a-black-background-AwsdyjRm-kw
"""

import sys

from PIL import Image, ImageEnhance

src_path, out_path = sys.argv[1:3]
OUT_HEIGHT = 2200

photo = Image.open(src_path).convert("RGB")
w, h = photo.size
# two full folds, starting just left of a lit crest so the inner edge reads as fabric turning away
panel = photo.crop((int(w * 0.37), 0, int(w * 0.85), h))
panel = panel.resize((round(panel.width * OUT_HEIGHT / panel.height), OUT_HEIGHT), Image.LANCZOS)
panel = ImageEnhance.Color(panel).enhance(1.25)
panel = ImageEnhance.Brightness(panel).enhance(1.12)
panel.save(out_path, "WEBP", quality=86, method=6)
print("panel", panel.size)
