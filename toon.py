"""Our own 2D cartoon engine: vector characters that blink, bob and lip-sync, plus backgrounds and
educational cards. Draws with cairo, shapes Hindi text with Pillow, pipes frames to ffmpeg.
Free, offline and consistent: a character looks the same in every scene of every episode."""
import math, os, random, subprocess
import numpy as np
import cairocffi as cairo
from PIL import Image, ImageDraw, ImageFont

FPS = 24
FONT = os.environ.get("HINDI_FONT", "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf")


def rgb(c, a=None):
    return (c[0] / 255, c[1] / 255, c[2] / 255) + (() if a is None else (a,))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def rrect(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0); cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi); cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def ellipse(cr, x, y, rx, ry):
    cr.save(); cr.translate(x, y); cr.scale(max(rx, 0.01), max(ry, 0.01)); cr.arc(0, 0, 1, 0, 2 * math.pi); cr.restore()


def fill(cr, c, a=1.0):
    cr.set_source_rgba(*rgb(c, a)); cr.fill()


def stroke(cr, c, w, a=1.0):
    cr.set_source_rgba(*rgb(c, a)); cr.set_line_width(w); cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.stroke()


# ---------------------------------------------------------------- text (Pillow shapes Devanagari)
_text_cache = {}


def text_surface(text, px, color=(255, 255, 255), box=None, maxw=None):
    key = (text, px, color, box, maxw)
    if key in _text_cache:
        return _text_cache[key]
    font = ImageFont.truetype(FONT, px)
    probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if maxw and probe.textlength(t, font=font) > maxw and cur:
            lines.append(cur); cur = word
        else:
            cur = t
    lines.append(cur)
    lh = int(px * 1.45); pad = int(px * 0.5) if box else 6
    w = int(max(probe.textlength(l, font=font) for l in lines)) + 2 * pad
    h = lh * len(lines) + 2 * pad - int(px * 0.2)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if box:
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(px * 0.6), fill=box)
    for i, l in enumerate(lines):
        d.text((w / 2, pad + i * lh), l, font=font, fill=color + (255,), anchor="ma")
    arr = np.array(img).astype(np.float32)
    arr[..., :3] *= arr[..., 3:4] / 255.0
    bgra = arr[..., [2, 1, 0, 3]].astype(np.uint8)
    buf = bytearray(bgra.tobytes())
    surf = cairo.ImageSurface.create_for_data(buf, cairo.FORMAT_ARGB32, w, h, w * 4)
    _text_cache[key] = (surf, buf, w, h)
    return _text_cache[key]


def put_text(cr, text, cx, y, px, **kw):
    surf, _buf, w, h = text_surface(text, px, **kw)
    cr.set_source_surface(surf, cx - w / 2, y); cr.paint()
    return h


# ---------------------------------------------------------------- backgrounds
PALETTES = {  # sky top, sky bottom, far hills, ground
    "calm": ((135, 206, 250), (255, 236, 190), (150, 200, 140), (110, 175, 90)),
    "funny": ((255, 226, 130), (255, 170, 120), (240, 170, 90), (150, 190, 80)),
    "tense": ((30, 35, 80), (80, 60, 110), (40, 50, 90), (30, 70, 60)),
    "sad": ((130, 145, 175), (190, 195, 210), (110, 125, 150), (90, 120, 110)),
    "night": ((12, 18, 50), (40, 50, 100), (25, 35, 70), (25, 60, 55)),
}


def background(cr, W, H, setting, mood, t):
    top, bot, hill, ground = PALETTES.get(mood, PALETTES["calm"])
    g = cairo.LinearGradient(0, 0, 0, H * 0.7)
    g.add_color_stop_rgb(0, *rgb(top)); g.add_color_stop_rgb(1, *rgb(bot))
    cr.set_source(g); cr.paint()
    rnd = random.Random(setting + mood)
    night = mood in ("tense", "night")
    if night:
        for _ in range(70):
            x, y = rnd.random() * W, rnd.random() * H * 0.45
            ellipse(cr, x, y, 2, 2); fill(cr, (255, 255, 230), 0.5 + 0.5 * math.sin(t * 2 + x))
        ellipse(cr, W * 0.8, H * 0.15, H * 0.07, H * 0.07); fill(cr, (250, 248, 225))
        k = (H * 0.14) / (H * 0.7); sky = tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3))
        ellipse(cr, W * 0.8 + H * 0.03, H * 0.135, H * 0.065, H * 0.065); fill(cr, sky)
    else:
        ellipse(cr, W * 0.8, H * 0.16, H * 0.09, H * 0.09); fill(cr, (255, 240, 150))
        for i, (cx, cy) in enumerate([(0.2, 0.14), (0.55, 0.2), (0.35, 0.3)]):  # drifting clouds
            x = (cx * W + t * (12 + 6 * i)) % (W + 300) - 150
            for dx, dy, r in [(0, 0, 38), (40, 8, 30), (-40, 10, 28), (15, -15, 30)]:
                ellipse(cr, x + dx, cy * H + dy, r * 1.4, r); fill(cr, (255, 255, 255), 0.85)
    ground_y = H * 0.70
    for k, (amp, ph, col) in enumerate([(0.07, 0.0, shade(hill, 0.9)), (0.05, 2.0, hill)]):
        cr.move_to(0, H)
        for i in range(0, 41):
            x = W * i / 40
            cr.line_to(x, ground_y - H * 0.06 - H * amp * (0.5 + 0.5 * math.sin(i * 0.5 + ph + k)))
        cr.line_to(W, H); cr.close_path(); fill(cr, col)
    cr.rectangle(0, ground_y, W, H - ground_y); fill(cr, ground)
    cr.rectangle(0, ground_y, W, 6); fill(cr, shade(ground, 0.85))
    scenery(cr, W, H, ground_y, setting, mood, t)


def tree(cr, x, gy, h, t, col=(40, 130, 70), pine=False):
    sway = math.sin(t * 1.3 + x) * 3
    rrect(cr, x - h * 0.05, gy - h * 0.4, h * 0.1, h * 0.4, 4); fill(cr, (110, 75, 45))
    if pine:
        for i in range(3):
            w = h * (0.34 - i * 0.07)
            cr.move_to(x - w + sway * i * 0.3, gy - h * (0.25 + i * 0.22)); cr.line_to(x + sway, gy - h * (0.55 + i * 0.22))
            cr.line_to(x + w + sway * i * 0.3, gy - h * (0.25 + i * 0.22)); cr.close_path(); fill(cr, shade(col, 0.8 + i * 0.1))
    else:
        for dx, dy, r in [(0, 0.62, 0.3), (-0.2, 0.5, 0.22), (0.2, 0.5, 0.22)]:
            ellipse(cr, x + h * dx + sway, gy - h * dy, h * r, h * r); fill(cr, col)


def house(cr, x, gy, w, h, col, roof=(160, 70, 50)):
    rrect(cr, x, gy - h, w, h, 6); fill(cr, col)
    cr.move_to(x - 14, gy - h); cr.line_to(x + w / 2, gy - h - h * 0.5); cr.line_to(x + w + 14, gy - h); cr.close_path(); fill(cr, roof)
    rrect(cr, x + w * 0.4, gy - h * 0.55, w * 0.2, h * 0.55, 5); fill(cr, (95, 60, 40))
    rrect(cr, x + w * 0.12, gy - h * 0.75, w * 0.18, w * 0.18, 4); fill(cr, (255, 235, 150))


def scenery(cr, W, H, gy, setting, mood, t):
    if setting in ("night_forest", "forest"):
        for i in range(9):
            tree(cr, W * (0.04 + i * 0.12), gy + (i % 2) * 18, H * (0.42 + 0.1 * (i % 3)), t, (25, 90, 60), pine=True)
    elif setting == "village":
        for i, (x, w, h, c) in enumerate([(0.04, 0.2, 0.22, (222, 184, 135)), (0.38, 0.17, 0.18, (200, 160, 120)), (0.7, 0.22, 0.24, (230, 200, 150))]):
            house(cr, W * x, gy + 4, W * w, H * h, c)
        tree(cr, W * 0.3, gy + 4, H * 0.35, t); tree(cr, W * 0.62, gy + 4, H * 0.3, t)
    elif setting == "field":
        for r in range(4):
            for i in range(24):
                x = W * i / 24 + r * 17; y = gy + 20 + r * 28
                cr.move_to(x, y); cr.line_to(x + math.sin(t * 2 + i) * 4, y - 36); stroke(cr, (225, 190, 70), 6)
        tree(cr, W * 0.15, gy, H * 0.32, t)
    elif setting == "river":
        rrect(cr, 0, gy + H * 0.06, W, H * 0.12, 0); fill(cr, (80, 150, 215))
        for i in range(10):
            x = (W * i / 10 + t * 30) % W; cr.move_to(x, gy + H * 0.1); cr.curve_to(x + 20, gy + H * 0.08, x + 40, gy + H * 0.12, x + 60, gy + H * 0.1); stroke(cr, (200, 230, 255), 3)
        tree(cr, W * 0.1, gy, H * 0.35, t); tree(cr, W * 0.9, gy, H * 0.3, t)
    elif setting == "mountain":
        for x, hh, c in [(0.2, 0.42, (120, 125, 150)), (0.55, 0.52, (95, 100, 130)), (0.85, 0.38, (130, 135, 160))]:
            cr.move_to(W * (x - 0.28), gy); cr.line_to(W * x, gy - H * hh); cr.line_to(W * (x + 0.28), gy); cr.close_path(); fill(cr, c)
            cr.move_to(W * (x - 0.05), gy - H * hh * 0.82); cr.line_to(W * x, gy - H * hh); cr.line_to(W * (x + 0.05), gy - H * hh * 0.82); cr.close_path(); fill(cr, (250, 250, 255))
    elif setting == "market":
        for i, c in enumerate([(220, 70, 70), (70, 150, 220), (240, 180, 50)]):
            x = W * (0.05 + i * 0.32)
            rrect(cr, x, gy - H * 0.2, W * 0.26, H * 0.2, 4); fill(cr, (150, 100, 60))
            for s in range(6):
                cr.rectangle(x + s * W * 0.26 / 6, gy - H * 0.33, W * 0.26 / 6, H * 0.12); fill(cr, c if s % 2 == 0 else (255, 255, 255))
            for s in range(5):
                ellipse(cr, x + W * (0.03 + s * 0.05), gy - H * 0.21, 14, 14); fill(cr, [(230, 60, 50), (250, 190, 40), (90, 180, 70)][s % 3])
    elif setting == "well":
        cx = W * 0.5
        rrect(cr, cx - 80, gy - 60, 160, 60, 10); fill(cr, (140, 140, 150))
        ellipse(cr, cx, gy - 60, 80, 20); fill(cr, (30, 30, 45))
        for s in (-1, 1): rrect(cr, cx + s * 70 - 6, gy - 170, 12, 110, 4); fill(cr, (110, 75, 45))
        cr.move_to(cx - 90, gy - 165); cr.line_to(cx, gy - 215); cr.line_to(cx + 90, gy - 165); cr.close_path(); fill(cr, (160, 70, 50))
        tree(cr, W * 0.12, gy, H * 0.35, t); tree(cr, W * 0.88, gy, H * 0.32, t)
    elif setting == "house_inside":
        cr.rectangle(0, 0, W, gy); fill(cr, (236, 214, 178)); cr.rectangle(0, gy - 14, W, 14); fill(cr, (170, 120, 80))
        cr.rectangle(0, gy, W, H - gy); fill(cr, (176, 124, 84))
        for i in range(0, int(W), 120): cr.move_to(i, gy); cr.line_to(i - 60, H); stroke(cr, (150, 100, 66), 3)
        rrect(cr, W * 0.1, H * 0.12, W * 0.16, H * 0.3, 8); fill(cr, (140, 205, 245)); stroke(cr, (120, 80, 50), 10)
        cr.move_to(W * 0.18, H * 0.12); cr.line_to(W * 0.18, H * 0.42); stroke(cr, (120, 80, 50), 6)
        ellipse(cr, W * 0.8, H * 0.28, 70, 70); fill(cr, (255, 230, 150), 0.35 + 0.1 * math.sin(t * 3))
        rrect(cr, W * 0.8 - 10, H * 0.28, 20, 60, 4); fill(cr, (120, 80, 50)); ellipse(cr, W * 0.8, H * 0.28, 12, 20); fill(cr, (255, 200, 60))


# ---------------------------------------------------------------- characters
class Look:
    def __init__(self, name, kind, skin, outfit, hair=(35, 28, 28), pants=(70, 70, 110), voice=None):
        self.name, self.kind, self.skin, self.outfit, self.hair, self.pants, self.voice = name, kind, skin, outfit, hair, pants, voice


def blink_amount(t, seed):
    ph = (t + seed * 1.7) % 3.4
    return 1.0 - (math.sin(ph / 0.18 * math.pi) if ph < 0.18 else 0.0)


def draw_cat(cr, L, t, mouth, emo):
    c = L.skin
    tail = math.sin(t * 4) * 0.5
    cr.move_to(70, -45); cr.curve_to(150, -60 + 40 * tail, 150, -150, 110 + 20 * tail, -170); stroke(cr, c, 22)
    ellipse(cr, 0, -60, 82, 56); fill(cr, c)
    for dx in (-35, 35): ellipse(cr, dx, -5, 24, 14); fill(cr, shade(c, 1.15))
    ellipse(cr, 0, -48, 40, 30); fill(cr, shade(c, 1.35))
    cr.save(); cr.translate(0, -135 + math.sin(t * 2.4) * 2)
    for s in (-1, 1):
        cr.move_to(s * 20, -40); cr.line_to(s * 56, -88); cr.line_to(s * 52, -25); cr.close_path(); fill(cr, c)
        cr.move_to(s * 28, -42); cr.line_to(s * 49, -74); cr.line_to(s * 46, -32); cr.close_path(); fill(cr, (240, 160, 170))
    ellipse(cr, 0, 0, 62, 54); fill(cr, c)
    for s in (-1, 1):
        ellipse(cr, s * 25, -6, 15, 17 * blink_amount(t, 3)); fill(cr, (250, 235, 90))
        ellipse(cr, s * 25, -6, 5, 12 * blink_amount(t, 3)); fill(cr, (20, 20, 20))
        for k in (-1, 0, 1): cr.move_to(s * 28, 14 + k * 7); cr.line_to(s * 80, 10 + k * 16); stroke(cr, (240, 240, 240), 2)
    cr.move_to(-7, 10); cr.line_to(7, 10); cr.line_to(0, 18); cr.close_path(); fill(cr, (230, 130, 140))
    if mouth > 0.15: ellipse(cr, 0, 28, 10, 4 + 11 * mouth); fill(cr, (120, 30, 40))
    else: cr.arc(-8, 22, 8, 0.2, math.pi * 0.85); stroke(cr, (80, 40, 40), 2.5); cr.arc(8, 22, 8, math.pi * 0.15, math.pi * 0.8); stroke(cr, (80, 40, 40), 2.5)
    cr.restore()


def draw_person(cr, L, t, mouth, emo, wave=0.0, seed=0):
    k = L.kind
    sk, of = L.skin, L.outfit
    talk = mouth if mouth > 0 else 0
    bob = math.sin(t * 2 * math.pi * 1.1 + seed) * 3 + talk * 4
    long_dress = k in ("headman", "grandma")
    if not long_dress:
        for s in (-1, 1):
            rrect(cr, s * 24 - 14, -78, 28, 78, 12); fill(cr, L.pants)
            ellipse(cr, s * 24 + s * 4, -2, 24, 11); fill(cr, (60, 40, 40))
    cr.save(); cr.translate(0, bob * 0.5)
    if long_dress:
        cr.move_to(-56, -170); cr.line_to(56, -170); cr.line_to(70, -8); cr.line_to(-70, -8); cr.close_path(); fill(cr, of)
        for s in (-1, 1): ellipse(cr, s * 22, -4, 22, 9); fill(cr, (150, 105, 75))
        if k == "grandma": cr.move_to(-56, -150); cr.curve_to(-10, -110, 20, -190, 56, -130); stroke(cr, shade(of, 1.3), 10)
    else:
        rrect(cr, -50, -195, 100, 130, 34); fill(cr, of)
        rrect(cr, -50, -195, 100, 22, 11); fill(cr, shade(of, 1.12))
    # arms
    for s in (-1, 1):
        sh = (s * 50, -172)
        ang = (0.35 + 0.05 * math.sin(t * 2 + s)) if s < 0 else (0.35 + wave * (-2.0 + 0.5 * math.sin(t * 9)) if wave else 0.35 + 0.05 * math.sin(t * 2.2))
        ax, ay = math.sin(ang) * s * 70, math.cos(ang) * 70
        if wave and s > 0: ax, ay = 40 + math.sin(t * 8) * 8, -85
        cr.move_to(*sh); cr.line_to(sh[0] + ax, sh[1] + ay); stroke(cr, of if k != "boy" else of, 24)
        ellipse(cr, sh[0] + ax, sh[1] + ay + 2, 13, 13); fill(cr, sk)
    cr.restore()
    # head
    cr.save(); cr.translate(0, -250 + bob); cr.rotate(math.sin(t * 1.6 + seed) * 0.03 + (0.04 if emo == "funny" else 0))
    for s in (-1, 1): ellipse(cr, s * 60, 2, 13, 17); fill(cr, shade(sk, 0.93))
    ellipse(cr, 0, 0, 63, 66); fill(cr, sk)
    if k == "boy":
        cr.arc(0, -4, 66, math.pi * 1.02, math.pi * 1.98); cr.close_path(); fill(cr, L.hair)
        for i in range(-3, 4): ellipse(cr, i * 17, -42 + abs(i) * 3, 12, 15); fill(cr, L.hair)
    elif k == "headman":
        for i, (w, h, y, c) in enumerate([(78, 36, -52, (235, 130, 40)), (70, 30, -72, (245, 150, 55)), (52, 24, -90, (235, 130, 40))]):
            ellipse(cr, 0, y, w, h); fill(cr, c)
        cr.move_to(-70, -45); cr.curve_to(-20, -25, 20, -25, 70, -45); stroke(cr, (200, 100, 30), 6)
    elif k == "grandma":
        ellipse(cr, 0, -78, 26, 26); fill(cr, (215, 215, 220))
        cr.arc(0, -2, 66, math.pi * 1.0, math.pi * 2.0); cr.close_path(); fill(cr, (215, 215, 220))
        ellipse(cr, 0, -10, 52, 46); fill(cr, sk)
    bl = blink_amount(t, seed)
    for s in (-1, 1):
        ellipse(cr, s * 24, -6, 14, 16 * bl); fill(cr, (255, 255, 255))
        ellipse(cr, s * 24 + math.sin(t * 0.8) * 2.5, -5, 7, 9 * bl); fill(cr, (30, 25, 25))
        ellipse(cr, s * 24 + 2, -9, 2.4, 2.4 * bl); fill(cr, (255, 255, 255))
        lift = {"tense": -8, "funny": 4, "sad": -4}.get(emo, 0)
        cr.move_to(s * 36, -26 + (lift if s < 0 else lift * 0.5)); cr.line_to(s * 12, -30 - (lift if s > 0 else lift * 0.5)); stroke(cr, L.hair if k != "headman" else (240, 240, 240), 4.5)
    if k == "grandma":
        for s in (-1, 1): ellipse(cr, s * 24, -6, 21, 21); stroke(cr, (110, 80, 50), 3.5)
        cr.move_to(-3, -6); cr.line_to(3, -6); stroke(cr, (110, 80, 50), 3.5)
    ellipse(cr, 0, 10, 6, 5); fill(cr, shade(sk, 0.82))
    for s in (-1, 1): ellipse(cr, s * 40, 16, 11, 7); fill(cr, (240, 120, 120), 0.35)
    if k == "headman":
        for s in (-1, 1): cr.move_to(0, 25); cr.curve_to(s * 25, 18, s * 55, 28, s * 62, 6 if s < 0 else 6); stroke(cr, (245, 245, 245), 10)
    my = 30
    if mouth > 0.12:
        ellipse(cr, 0, my, 17, 3 + 17 * mouth); fill(cr, (120, 30, 40))
        if mouth > 0.45: ellipse(cr, 0, my + 4 + 6 * mouth, 9, 5 * mouth); fill(cr, (230, 110, 120))
    elif emo in ("tense", "sad"):
        cr.arc(0, my + 12, 14, math.pi * 1.15, math.pi * 1.85); stroke(cr, (90, 40, 40), 3.5)
    else:
        cr.arc(0, my - 6, 17, 0.25, math.pi - 0.25); stroke(cr, (90, 40, 40), 3.5)
    cr.restore()


def draw_character(cr, L, x, y, scale, t, mouth=0.0, emo="calm", wave=0.0, seed=0):
    cr.save(); cr.translate(x, y); cr.scale(scale, scale)
    ellipse(cr, 0, 2, 80, 12); fill(cr, (0, 0, 0), 0.18)  # ground shadow
    if L.kind == "cat": draw_cat(cr, L, t, mouth, emo)
    else: draw_person(cr, L, t, mouth, emo, wave, seed)
    cr.restore()


# ---------------------------------------------------------------- props for educational scenes
def prop(cr, kind, x, y, s, t=0.0):
    cr.save(); cr.translate(x, y + math.sin(t * 3 + x) * 3); cr.scale(s, s)
    if kind == "apple":
        ellipse(cr, -9, -26, 26, 28); fill(cr, (215, 40, 45)); ellipse(cr, 9, -26, 26, 28); fill(cr, (225, 50, 55))
        cr.move_to(0, -52); cr.line_to(4, -66); stroke(cr, (100, 70, 40), 5); ellipse(cr, 14, -62, 14, 7); fill(cr, (80, 170, 70))
    elif kind == "pomegranate":
        ellipse(cr, 0, -32, 32, 30); fill(cr, (200, 40, 70)); ellipse(cr, -8, -40, 14, 12); fill(cr, (225, 70, 95), 0.7)
        for i in range(5): a = -math.pi / 2 + (i - 2) * 0.5; cr.move_to(math.cos(a) * 8, -62); cr.line_to(math.cos(a) * 16, -76 + abs(i - 2) * 3); stroke(cr, (170, 30, 60), 6)
    elif kind == "mango":
        cr.save(); cr.rotate(-0.4); ellipse(cr, 0, -28, 22, 32); fill(cr, (250, 190, 40)); ellipse(cr, 4, -34, 14, 20); fill(cr, (255, 140, 50), 0.6); cr.restore()
        ellipse(cr, 8, -62, 12, 6); fill(cr, (70, 150, 60))
    elif kind == "banana":
        cr.arc(0, -40, 34, math.pi * 0.15, math.pi * 0.9); stroke(cr, (250, 215, 50), 22); cr.arc(0, -40, 34, math.pi * 0.15, math.pi * 0.2); stroke(cr, (110, 80, 40), 24)
    elif kind == "ball":
        ellipse(cr, 0, -32, 32, 32); fill(cr, (70, 140, 230)); cr.arc(0, -32, 32, 0.3, 1.6); stroke(cr, (255, 255, 255), 6); cr.arc(0, -32, 32, 3.4, 4.7); stroke(cr, (255, 210, 60), 6)
    elif kind == "star":
        cr.move_to(0, -66)
        for i in range(10):
            r = 34 if i % 2 == 0 else 15; a = -math.pi / 2 + i * math.pi / 5
            cr.line_to(math.cos(a) * r, -34 + math.sin(a) * r)
        cr.close_path(); fill(cr, (255, 205, 40)); stroke(cr, (240, 160, 20), 4)
    elif kind == "flower":
        for i in range(6):
            a = i * math.pi / 3; ellipse(cr, math.cos(a) * 18, -40 + math.sin(a) * 18, 15, 15); fill(cr, (245, 120, 170))
        ellipse(cr, 0, -40, 12, 12); fill(cr, (255, 220, 70)); cr.move_to(0, -26); cr.line_to(0, 0); stroke(cr, (70, 160, 70), 5)
    elif kind == "balloon":
        ellipse(cr, 0, -50, 26, 32); fill(cr, (235, 80, 140)); cr.move_to(0, -18); cr.curve_to(-8, -8, 8, 2, 0, 12); stroke(cr, (120, 120, 120), 2.5)
    elif kind == "heart":
        cr.move_to(0, -12); cr.curve_to(-40, -40, -20, -75, 0, -52); cr.curve_to(20, -75, 40, -40, 0, -12); fill(cr, (230, 50, 80))
    else:  # fish
        ellipse(cr, 0, -30, 34, 20); fill(cr, (250, 150, 50)); cr.move_to(28, -30); cr.line_to(52, -48); cr.line_to(52, -12); cr.close_path(); fill(cr, (240, 120, 40)); ellipse(cr, -16, -34, 4, 4); fill(cr, (20, 20, 20))
    cr.restore()


PROPS = ["apple", "mango", "banana", "ball", "star", "flower", "balloon", "heart", "fish", "pomegranate"]


# ---------------------------------------------------------------- audio -> mouth movement
def mouth_envelope(audio, n_frames):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", audio, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    hop = 16000 // FPS
    rms = np.array([np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2)) if len(a[i * hop:(i + 1) * hop]) else 0 for i in range(n_frames)])
    if rms.max() > 0: rms = np.clip(rms / (np.percentile(rms, 92) + 1e-6), 0, 1)
    out, cur = np.zeros(n_frames), 0.0
    for i, v in enumerate(rms):  # fast attack, slower release looks like talking
        cur = v if v > cur else cur * 0.55 + v * 0.45
        out[i] = cur
    return np.clip(out ** 0.8, 0, 1)


# ---------------------------------------------------------------- scene renderer
def layout(names, W, H):
    n = max(1, len(names)); return [(W * (i + 1) / (n + 1)) for i in range(n)]


def render_frame(cr, scene, cast, W, H, t, env_i, idx):
    cr.save(); cr.set_antialias(cairo.ANTIALIAS_BEST)
    background(cr, W, H, scene.get("setting", "village"), scene.get("mood", "calm"), t)
    names = [n for n in scene.get("characters", []) if n in cast][:3]
    gy = H * 0.84
    base = (H / 460.0) * (0.95 if len(names) < 3 else 0.8) * (1.0 if W > H else 0.9)
    card = scene.get("card")
    xs = layout(names, W, H) if not card else ([W * 0.86 - i * W * 0.16 for i in range(len(names))] if W > H else [W * 0.5 for _ in names])
    for i, (n, x) in enumerate(zip(names, xs)):
        speaking = scene.get("speaker") == n
        draw_character(cr, cast[n], x, gy, base * (1.06 if speaking else 1.0), t,
                       mouth=env_i if speaking else 0.0, emo=scene.get("mood", "calm"),
                       wave=1.0 if (scene.get("wave") == n) else 0.0, seed=i * 1.3)
    if card:  # educational card: big letter/number + objects
        cw, ch = (W * 0.58, H * 0.66) if W > H else (W * 0.86, H * 0.36)
        cx, cy = (W * 0.04, H * 0.07) if W > H else (W * 0.07, H * 0.05)
        pop = min(1.0, t / 0.35); cr.save(); cr.translate(cx + cw / 2, cy + ch / 2); cr.scale(0.6 + 0.4 * pop, 0.6 + 0.4 * pop); cr.translate(-cx - cw / 2, -cy - ch / 2)
        rrect(cr, cx, cy, cw, ch, 36); fill(cr, (255, 255, 255), 0.96); rrect(cr, cx, cy, cw, ch, 36); stroke(cr, (255, 190, 60), 10)
        if card.get("big"):
            put_text(cr, card["big"], cx + cw / 2 - (cw * 0.2 if card.get("prop") else 0), cy + ch * 0.05, int(ch * 0.62), color=(220, 60, 60))
        if card.get("count"):
            k, n = card.get("prop", "apple"), int(card["count"]); cols = min(n, 5); rows = (n + cols - 1) // cols
            for j in range(n):
                shown = t > 0.5 + j * 0.45
                if shown: prop(cr, k, cx + cw * (0.12 + 0.76 * ((j % cols) + 0.5) / cols), cy + ch * (0.42 + 0.5 * ((j // cols) + 1) / rows) - ch * 0.12, ch / 330 * (1.0 if rows < 2 else 0.8), t)
        elif card.get("prop"):
            prop(cr, card["prop"], cx + cw * 0.74, cy + ch * 0.82, ch / 190, t)
        if card.get("label"):
            put_text(cr, card["label"], cx + cw / 2, cy + ch * 0.8, int(ch * 0.13), color=(60, 60, 120))
        cr.restore()
    cap = scene.get("caption")
    if cap:
        surf, _b, w, h = text_surface(cap, int(H * (0.05 if W > H else 0.034)), color=(255, 255, 255), box=(0, 0, 0, 165), maxw=int(W * 0.84))
        cr.set_source_surface(surf, (W - w) / 2, H - h - H * 0.035); cr.paint()
    cr.restore()


def render_scene(scene, cast, audio, out, size=(1280, 720)):
    W, H = size
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", audio],
                               capture_output=True, text=True, check=True).stdout)
    n = int(dur * FPS) + 6
    env = mouth_envelope(audio, n) if scene.get("speaker") else np.zeros(n)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); cr = cairo.Context(surf)
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", audio, "-vf", f"fade=t=in:st=0:d=0.25,fade=t=out:st={max(dur - 0.25, 0):.2f}:d=0.25,format=yuv420p",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-shortest", str(out)], stdin=subprocess.PIPE)
    for i in range(n):
        render_frame(cr, scene, cast, W, H, i / FPS, float(env[i]), i)
        surf.flush(); ff.stdin.write(bytes(surf.get_data()))
    ff.stdin.close(); ff.wait()
    return out


def save_frame(scene, cast, size, t, path, mouth=0.0):
    W, H = size
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); cr = cairo.Context(surf)
    render_frame(cr, scene, cast, W, H, t, mouth, 0); surf.write_to_png(path)
