"""Draw the starter face set into assets/faces/ (transparent PNGs, classic blocky-avatar style).

Every expression comes in three ages:
    <expression>.png        kid: no brows, bigger eyes
    <expression>_adult.png  dark brows
    <expression>_old.png    grey bushy brows, smaller eyes, wrinkles and smile lines

    python pipeline/make_faces.py            # needs Pillow

They're plain images: redraw any of them, or drop in new ones and use them by file name,
e.g. face(s, rig, "suspicious_old", t).
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets" / "faces"
N = 2048  # drawn big, saved at 512 for smooth edges
INK = (20, 20, 22, 255)
SHINE = (255, 255, 255, 255)
BLUSH = (240, 120, 120, 90)

# eye: (height factor, lid) lid = None | "half" (sleepy) | "angry" | "worried"
# mouth: (kind, width, depth) kind = curve | open | flat | o | wobble
# brow: tilt in pixels (inner end up > 0, inner end down < 0)
EXPRESSIONS = {
    "neutral":   dict(eye=(1.0, None), mouth=("flat", 0.16, 0), brow=0),
    "smile":     dict(eye=(1.0, None), mouth=("curve", 0.22, 0.07), brow=0),
    "grin":      dict(eye=(0.9, None), mouth=("open", 0.28, 0.12), brow=10),
    "frown":     dict(eye=(1.0, None), mouth=("curve", 0.18, -0.05), brow=-40),
    "sad":       dict(eye=(1.0, "worried"), mouth=("curve", 0.16, -0.06), brow=60),
    "surprised": dict(eye=(1.3, None), mouth=("o", 0.08, 0.10), brow=0, raise_=60),
    "angry":     dict(eye=(0.9, "angry"), mouth=("open", 0.20, -0.07), brow=-80),
    "sleepy":    dict(eye=(1.0, "half"), mouth=("flat", 0.10, 0), brow=0, raise_=-20),
    "worried":   dict(eye=(1.0, "worried"), mouth=("wobble", 0.18, 0.02), brow=70),
    "smug":      dict(eye=(1.0, "half"), mouth=("smirk", 0.18, 0.05), brow=-20),
}
AGES = {
    "":       dict(eye_scale=1.15, brow=None, wrinkles=False, blush=True),
    "_adult": dict(eye_scale=1.0, brow=INK, wrinkles=False, blush=False),
    "_old":   dict(eye_scale=0.85, brow=(205, 205, 200, 255), wrinkles=True, blush=False),
}


def u(v):
    return int(v * N)


def draw_face(expr, age):
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    eh, lid = expr["eye"]
    ew, eh = u(0.075) * age["eye_scale"], u(0.12) * eh * age["eye_scale"]
    ey = u(0.42)
    line = u(0.022)
    for side in (-1, 1):
        ex = u(0.5) + side * u(0.15)
        d.ellipse((ex - ew / 2, ey - eh / 2, ex + ew / 2, ey + eh / 2), fill=INK)
        d.ellipse((ex - ew * 0.25, ey - eh * 0.38, ex + ew * 0.05, ey - eh * 0.1), fill=SHINE)
        clear = (0, 0, 0, 0)
        if lid == "half":  # cut the top half of the eye off with a lid line
            d.rectangle((ex - ew, ey - eh, ex + ew, ey - eh * 0.05), fill=clear)
            d.line((ex - ew * 0.6, ey - eh * 0.05, ex + ew * 0.6, ey - eh * 0.05), fill=INK, width=line)
        elif lid in ("angry", "worried"):  # slant: cut a triangle off the inner/outer top
            inner_x, outer_x = ex - side * ew, ex + side * ew
            hi_x, lo_x = (inner_x, outer_x) if lid == "angry" else (outer_x, inner_x)
            d.polygon([(hi_x, ey - eh * 0.02), (lo_x, ey - eh * 0.6), (hi_x, ey - eh * 0.6)], fill=clear)
        if age["wrinkles"]:  # crow's feet and bags under the eyes
            ox = ex + side * ew * 0.9
            for k in (-1, 1):
                d.line((ox, ey + k * eh * 0.08, ox + side * u(0.03), ey + k * eh * 0.2), fill=INK, width=line // 2)
            d.arc((ex - ew * 0.8, ey + eh * 0.35, ex + ew * 0.8, ey + eh * 0.85), 20, 160, fill=INK, width=line // 2)
        if age["brow"] is not None:
            by = ey - eh / 2 - u(0.06) - expr.get("raise_", 0) * N / 2048
            inner, outer = ex - side * u(0.06), ex + side * u(0.07)
            tilt = expr["brow"] * N / 2048
            thick = line * (1.6 if age["wrinkles"] else 1.0)
            d.line((outer, by, inner, by - tilt), fill=age["brow"], width=int(thick))
        if age["blush"]:
            d.ellipse((ex - u(0.06), u(0.53), ex + u(0.06), u(0.57)), fill=BLUSH)

    kind, w, depth = expr["mouth"]
    mx, my, mw, md = u(0.5), u(0.64), u(w), u(depth)
    if kind == "flat":
        d.line((mx - mw / 2, my, mx + mw / 2, my), fill=INK, width=line)
    elif kind == "curve":  # smile (depth > 0) or frown (depth < 0)
        top, bot = (my - abs(md), my + abs(md))
        box = (mx - mw / 2, top - abs(md), mx + mw / 2, bot)
        if md > 0:
            d.arc(box, 20, 160, fill=INK, width=line)
        else:
            d.arc((mx - mw / 2, my, mx + mw / 2, my + 3 * abs(md)), 200, 340, fill=INK, width=line)
    elif kind == "open":  # big D-shaped mouth, upside down when angry
        if md > 0:
            d.chord((mx - mw / 2, my - md, mx + mw / 2, my + md), 0, 180, fill=INK)
            d.chord((mx - mw / 3, my + md * 0.3, mx + mw / 3, my + md * 0.95), 180, 360, fill=(230, 90, 90, 255))
        else:
            d.chord((mx - mw / 2, my + md, mx + mw / 2, my - md * 1.5), 180, 360, fill=INK)
    elif kind == "o":
        d.ellipse((mx - mw / 2, my - md / 2, mx + mw / 2, my + md / 2), fill=INK)
    elif kind == "wobble":
        pts = [(mx - mw / 2 + i * mw / 8, my + (md if i % 2 else -md) * 0.6) for i in range(9)]
        d.line(pts, fill=INK, width=line, joint="curve")
    elif kind == "smirk":
        d.line((mx - mw / 2, my + md * 0.3, mx + mw * 0.15, my + md * 0.3), fill=INK, width=line)
        d.arc((mx, my - md * 1.5, mx + mw / 2, my + md * 0.4), 20, 110, fill=INK, width=line)
    if age["wrinkles"]:  # smile lines either side of the mouth
        for side in (-1, 1):
            x = mx + side * (mw / 2 + u(0.05))
            box = (x - u(0.05), my - u(0.05), x + u(0.05), my + u(0.05))
            d.arc(box, *((140, 220) if side < 0 else (320, 400)), fill=INK, width=line // 2)
    return img.resize((512, 512), Image.LANCZOS)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, expr in EXPRESSIONS.items():
        for suffix, age in AGES.items():
            draw_face(expr, age).save(OUT / f"{name}{suffix}.png")
    print(f"{len(EXPRESSIONS) * len(AGES)} faces in {OUT}")
