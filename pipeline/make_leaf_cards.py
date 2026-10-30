"""Leaf-cluster sprites for the game-style card trees (lib/oldtown.py), made from Poly Haven's
shrub_03 leaf sheet (CC0): single leaves are cut out by their alpha and scattered, turned and
tinted into a twig cluster with alpha, the way game trees are textured.

  .venv/Scripts/python pipeline/make_leaf_cards.py

Writes assets/ext/generated/leaf_<kind>.png (RGBA, 1024 px): broad (linden/oak), small (birch,
fruit), willow (long drooping), needle (pine, cypress; drawn, not cut).
"""
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "ext" / "shrub_03" / "textures"
OUT = ROOT / "assets" / "ext" / "generated"
SIZE = 1024


def leaves():
    """Cut the big leaves out of the sheet: connected alpha blobs, by bounding box."""
    diff = Image.open(SRC / "shrub_03_diff_2k.jpg").convert("RGB")
    alpha = Image.open(SRC / "shrub_03_alpha_2k.png").convert("L")
    small = np.array(alpha.resize((256, 256))) > 128
    seen = np.zeros_like(small)
    boxes = []
    for y in range(256):
        for x in range(256):
            if small[y, x] and not seen[y, x]:
                stack, pts = [(y, x)], []
                seen[y, x] = True
                while stack:
                    cy, cx = stack.pop()
                    pts.append((cy, cx))
                    for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                        if 0 <= ny < 256 and 0 <= nx < 256 and small[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
                ys, xs = [p[0] for p in pts], [p[1] for p in pts]
                w, h = max(xs) - min(xs), max(ys) - min(ys)
                if len(pts) > 250 and 0.6 < w / max(h, 1) < 1.4:  # the round leaves, not the stems
                    k = alpha.width / 256
                    boxes.append((int(min(xs) * k), int(min(ys) * k), int((max(xs) + 1) * k), int((max(ys) + 1) * k)))
    out = []
    for b in boxes:
        rgba = diff.crop(b).convert("RGBA")
        rgba.putalpha(alpha.crop(b))
        out.append(rgba)
    return out


def cluster(cut, rng, n, scale, droop=False, tint=(1.0, 1.0, 1.0), shape=(0.46, 0.42)):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # twigs first, from the bottom centre out to where the leaves sit
    spots = []
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r = math.sqrt(rng.random())
        x = SIZE / 2 + math.cos(a) * r * SIZE * shape[0]
        y = SIZE / 2 + math.sin(a) * r * SIZE * shape[1] + (r * SIZE * 0.12 if droop else 0)
        spots.append((x, y))
    for x, y in spots[: n // 3]:
        d.line([(SIZE / 2, SIZE * 0.95), (SIZE / 2 + (x - SIZE / 2) * 0.6, SIZE / 2 + (y - SIZE / 2) * 0.6), (x, y)],
               fill=(78, 60, 42, 255), width=5, joint="curve")
    for x, y in sorted(spots, key=lambda p: p[1]):  # back to front by height reads as depth
        leaf = rng.choice(cut)
        s = scale * rng.uniform(0.7, 1.15) * SIZE / max(leaf.size)
        lw, lh = max(4, int(leaf.width * s)), max(4, int(leaf.height * s * (1.6 if droop else 1.0)))
        L = leaf.resize((lw, lh), Image.LANCZOS).rotate(rng.uniform(0, 360) if not droop else rng.uniform(150, 210),
                                                        expand=True, resample=Image.BICUBIC)
        rgb = L.convert("RGB")
        rgb = ImageEnhance.Brightness(rgb).enhance(rng.uniform(0.62, 1.12))
        rgb = ImageEnhance.Color(rgb).enhance(rng.uniform(0.85, 1.25))
        r_, g_, b_ = rgb.split()
        rgb = Image.merge("RGB", [ch.point(lambda v, k=k: min(255, int(v * k))) for ch, k in zip((r_, g_, b_), tint)])
        L = Image.merge("RGBA", (*rgb.split(), L.split()[3]))
        img.alpha_composite(L, (int(x - L.width / 2), int(y - L.height / 2)))
    return img


def needles(rng, n=900):
    """Conifer spray: dark needles along curving twigs."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for _ in range(14):
        x, y = SIZE / 2 + rng.uniform(-60, 60), SIZE * 0.92
        a = -math.pi / 2 + rng.uniform(-1.0, 1.0)
        for _ in range(40):
            nx, ny = x + math.cos(a) * 18, y + math.sin(a) * 18
            d.line([(x, y), (nx, ny)], fill=(70, 52, 36, 255), width=4)
            for _ in range(6):
                b = a + rng.choice((-1, 1)) * rng.uniform(0.6, 1.2)
                ln = rng.uniform(22, 44)
                g = rng.randint(70, 120)
                d.line([(nx, ny), (nx + math.cos(b) * ln, ny + math.sin(b) * ln)],
                       fill=(int(g * 0.45), g, int(g * 0.4), 255), width=3)
            x, y = nx, ny
            a += rng.uniform(-0.18, 0.18)
            if not (0 < x < SIZE and 0 < y < SIZE):
                break
    return img.filter(ImageFilter.SMOOTH)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cut = leaves()
    print(f"{len(cut)} leaves cut from shrub_03")
    rng = random.Random(7)
    cluster(cut, rng, 85, 0.16, tint=(0.78, 1.0, 0.68)).save(OUT / "leaf_broad.png")
    cluster(cut, rng, 140, 0.09, tint=(0.8, 1.04, 0.64)).save(OUT / "leaf_small.png")
    cluster(cut, rng, 110, 0.10, droop=True, tint=(0.9, 1.06, 0.6), shape=(0.36, 0.40)).save(OUT / "leaf_willow.png")
    needles(rng).save(OUT / "leaf_needle.png")
    print("wrote", ", ".join(p.name for p in sorted(OUT.glob("leaf_*.png"))))


if __name__ == "__main__":
    main()
