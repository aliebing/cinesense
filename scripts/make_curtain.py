"""Cut the velvet curtain out of the cottonbro photo, taper it towards the bottom,
grade its colour towards photo B, and write a right-side curtain panel with alpha.

usage:
  uv run --no-project --with numpy --with pillow python scripts/make_curtain.py \
      pexels-cottonbro-6899772.jpg pexels-photo-35836715.jpeg web/public/curtain.webp preview.png

Sources (Pexels license, free to use): curtain https://www.pexels.com/photo/6899772/ (cottonbro studio),
colour reference https://www.pexels.com/photo/35836715/ (only its average colour is used).
"""

import sys

import numpy as np
from PIL import Image, ImageFilter

src_path, ref_path, out_path, preview_path = sys.argv[1:5]

src = Image.open(src_path).convert("RGB")
W, H = src.size
# the curtain occupies the right part of the frame; its inner edge flares outwards near the floor
x0 = int(W * 0.30)
img = np.asarray(src, dtype=np.float32)[:, x0:, :]
h, w, _ = img.shape
R, G, B = img[..., 0], img[..., 1], img[..., 2]

# --- alpha: the curtain runs to the right frame edge; find its inner (left) edge per row ---
is_curtain = (R > 32) & (R > 1.6 * np.maximum(G, B))
win = 60
edges = np.full(h, w, dtype=np.float32)
for y in range(h):
    c = np.concatenate([[0], np.cumsum(is_curtain[y])])
    frac = (c[win:] - c[:-win]) / win  # curtain share in [x, x+win)
    hit = np.flatnonzero(frac > 0.6)
    if hit.size:
        edges[y] = hit[0]
# smooth the edge vertically so it reads as one fabric line
k = 41
pad = np.pad(edges, k // 2, mode="edge")
edges = np.array([np.median(pad[i : i + k]) for i in range(h)], dtype=np.float32)
# the top rows pick up hanging scenery left of the curtain: don't let the edge jump left there
ref_edge = np.median(edges[int(h * 0.18) : int(h * 0.3)])
top = int(h * 0.17)
edges[:top] = np.maximum(edges[:top], ref_edge)
xs_full = np.arange(w, dtype=np.float32)[None, :]
edges_in = edges + 4  # pull the cut slightly into the fabric
alpha = np.clip((xs_full - edges_in[:, None]) / 6.0 + 0.5, 0, 1)
# near the edge, drop pixels that aren't red velvet (blue rim light, the white dress)
near = xs_full < (edges_in[:, None] + 18)
reddish = (R > 1.4 * np.maximum(G, B))
alpha = np.where(near & ~reddish, 0, alpha)
alpha = np.asarray(Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)), dtype=np.float32) / 255

# --- colour grade towards photo B (warmer, more saturated red) ---
ref = np.asarray(Image.open(ref_path).convert("RGB"), dtype=np.float32)
ref_mask = (ref[..., 0] - np.maximum(ref[..., 1], ref[..., 2])) > 25
src_mask = alpha > 0.9
gains = ref[ref_mask].mean(axis=0) / np.maximum(img[src_mask].mean(axis=0), 1)
gains = 1 + (gains - 1) * 0.6  # blend 60 % towards B
graded = np.clip(img * gains, 0, 255)
# a touch more contrast in the folds
lum = graded.mean(axis=2, keepdims=True)
graded = np.clip(lum + (graded - lum) * 1.12, 0, 255)
graded = np.clip((graded - 128) * 1.08 + 128, 0, 255)

rgba = np.dstack([graded, alpha * 255]).astype(np.uint8)

# --- taper: compress each row towards the outer (right) edge, more towards the bottom ---
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)

out = np.zeros_like(rgba)
xs = np.arange(w, dtype=np.float32)
for y in range(h):
    s = 1.0 - 0.55 * smoothstep(0.2, 1.0, y / h)  # 1 at top, 0.45 at the floor
    # destination x maps to source x: outer edge fixed at w-1
    src_x = (w - 1) - ((w - 1) - xs) / s
    valid = src_x >= 0
    sx = np.clip(src_x, 0, w - 1)
    x_lo = np.floor(sx).astype(int)
    x_hi = np.minimum(x_lo + 1, w - 1)
    f = (sx - x_lo)[:, None]
    row = rgba[y].astype(np.float32)
    val = row[x_lo] * (1 - f) + row[x_hi] * f
    val[~valid] = 0
    out[y] = val.astype(np.uint8)

panel = Image.fromarray(out, "RGBA")
bbox = panel.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
panel = panel.crop((bbox[0], 0, w, h))
panel = panel.resize((round(panel.width * 2200 / panel.height), 2200), Image.LANCZOS)
panel.save(out_path, "WEBP", quality=88, method=6)

prev = Image.new("RGB", panel.size, (5, 5, 7))
prev.paste(panel, (0, 0), panel)
prev.thumbnail((500, 1000))
prev.save(preview_path)
print("panel", panel.size, "gains", gains.round(3))
