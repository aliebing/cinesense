"""Build the curtain panel from a photo of straight-hanging red velvet.

The panel is a right-hand curtain (inner edge on its left); the page mirrors it for the left side.

usage:
  uv run --no-project --with pillow python scripts/make_curtain.py \
      <velvet_photo.jpg> web/public/curtain.webp \
      [x0 x1 colour brightness [width]]   # crop (fractions of photo width), colour/brightness, output width

Source (Unsplash license, free to use): "A red curtain with a black background"
by Ambitious Studio* | Rick Barrett,
https://unsplash.com/photos/a-red-curtain-with-a-black-background-AwsdyjRm-kw
"""

import sys

from PIL import Image, ImageEnhance

src_path, out_path = sys.argv[1:3]
x0, x1, colour, brightness = (float(v) for v in (sys.argv[3:7] or (0.22, 0.83, 1.25, 1.12)))
out_width = int(sys.argv[7]) if len(sys.argv) > 7 else 600  # ~2 folds on screen
OUT_HEIGHT = 2200

photo = Image.open(src_path).convert("RGB")
w, h = photo.size
# about four folds of the photo, squeezed into a slim panel so the curtain looks slightly zoomed out
panel = photo.crop((int(w * x0), 0, int(w * x1), h))
panel = panel.resize((out_width or round(panel.width * OUT_HEIGHT / panel.height), OUT_HEIGHT), Image.LANCZOS)
panel = ImageEnhance.Color(panel).enhance(colour)
panel = ImageEnhance.Brightness(panel).enhance(brightness)
panel.save(out_path, "WEBP", quality=86, method=6)
print("panel", panel.size)
