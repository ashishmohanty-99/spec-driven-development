#!/usr/bin/env python3
"""Draw the plugin icon (needs Pillow): python3 tools/make_icon.py -> tools/plugin_overrides/icon.png"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SIZE, K = 1024, 3  # final size and supersampling factor
W = SIZE * K


def s(v):
    return round(v * K)


def gradient(top, bottom, angle_mix=0.55):
    """Diagonal two-colour gradient."""
    base = Image.new("RGB", (W, W))
    px = base.load()
    for y in range(W):
        for x in range(0, W, 1):
            t = (x * (1 - angle_mix) + y * angle_mix) / W
            px[x, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return base


def shadow(mask, offset, blur, strength):
    """Soft drop shadow for a shape given as an L mask."""
    sh = ImageChops.offset(mask, s(offset[0]), s(offset[1])).filter(ImageFilter.GaussianBlur(s(blur)))
    return sh.point(lambda v: int(v * strength))


def main(out: Path) -> None:
    img = gradient((79, 70, 229), (124, 58, 237)).convert("RGBA")  # indigo -> violet

    # soft light in the top-left corner
    glow = Image.new("L", (W, W), 0)
    ImageDraw.Draw(glow).ellipse([s(-320), s(-360), s(620), s(520)], fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(s(150)))
    img = Image.composite(Image.new("RGBA", (W, W), (255, 255, 255, 255)), img, glow)

    # ---- the spec sheet
    sheet = Image.new("L", (W, W), 0)
    d = ImageDraw.Draw(sheet)
    x0, y0, x1, y1, r, fold = 236, 150, 728, 800, 44, 118
    d.rounded_rectangle([s(x0), s(y0), s(x1), s(y1)], radius=s(r), fill=255)
    d.polygon([(s(x1 - fold), s(y0) - 2), (s(x1) + 2, s(y0) - 2), (s(x1) + 2, s(y0 + fold))], fill=0)  # cut the corner
    black = Image.new("RGBA", (W, W), (30, 20, 80, 255))
    img = Image.composite(black, img, shadow(sheet, (0, 22), 30, 0.38))
    img = Image.composite(Image.new("RGBA", (W, W), (255, 255, 255, 255)), img, sheet)

    d = ImageDraw.Draw(img)
    # folded corner
    d.polygon([(s(x1 - fold), s(y0)), (s(x1 - fold), s(y0 + fold - 26)), (s(x1 - 26), s(y0 + fold))],
              fill=(199, 210, 254, 255))
    d.polygon([(s(x1 - fold), s(y0)), (s(x1), s(y0 + fold)), (s(x1 - fold) + s(26), s(y0 + fold))],
              fill=(199, 210, 254, 255))
    d.rounded_rectangle([s(x1 - fold), s(y0 + fold - 60), s(x1 - fold + 60), s(y0 + fold)], radius=s(26),
                        fill=(199, 210, 254, 255))

    # title bar
    d.rounded_rectangle([s(300), s(236), s(520), s(280)], radius=s(22), fill=(67, 56, 202, 255))
    # three requirements: a ticked box and a line each
    for i, width in enumerate((300, 230, 270)):
        y = 350 + i * 104
        d.rounded_rectangle([s(300), s(y), s(352), s(y + 52)], radius=s(14), fill=(224, 231, 255, 255))
        d.line([(s(312), s(y + 27)), (s(323), s(y + 38)), (s(341), s(y + 16))], fill=(79, 70, 229, 255),
               width=s(8), joint="curve")
        d.rounded_rectangle([s(380), s(y + 8), s(380 + width), s(y + 44)], radius=s(18), fill=(199, 210, 254, 255))

    # ---- approval badge
    cx, cy, rad = 704, 744, 176
    badge = Image.new("L", (W, W), 0)
    ImageDraw.Draw(badge).ellipse([s(cx - rad), s(cy - rad), s(cx + rad), s(cy + rad)], fill=255)
    img = Image.composite(black, img, shadow(badge, (0, 20), 26, 0.45))
    ring = Image.new("L", (W, W), 0)
    ImageDraw.Draw(ring).ellipse([s(cx - rad - 20), s(cy - rad - 20), s(cx + rad + 20), s(cy + rad + 20)], fill=255)
    img = Image.composite(Image.new("RGBA", (W, W), (255, 255, 255, 255)), img, ring)
    green = gradient((52, 211, 153), (5, 150, 105), 0.8).convert("RGBA")
    img = Image.composite(green, img, badge)

    d = ImageDraw.Draw(img)
    pts = [(cx - 82, cy + 6), (cx - 24, cy + 64), (cx + 86, cy - 58)]
    d.line([(s(x), s(y)) for x, y in pts], fill=(255, 255, 255, 255), width=s(44), joint="curve")
    for x, y in pts:
        d.ellipse([s(x - 22), s(y - 22), s(x + 22), s(y + 22)], fill=(255, 255, 255, 255))

    img.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS).save(out, optimize=True)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(Path(__file__).resolve().parent / "plugin_overrides" / "icon.png")
