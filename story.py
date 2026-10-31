"""Fictional Hindi story episodes with a recurring cast. No fact-check needed, no paid image service.

Scenes are drawn with Pillow (scenery + simple characters + captions) and given a slow zoom in ffmpeg.
  python story.py make            # next episode: script + safety check + video + Shorts
  python story.py autopilot       # same, then upload (privacy from YT_PRIVACY, default private)
"""
import json, math, random, sys
from pathlib import Path
import pipeline as P

CAST = json.loads(Path("cast.json").read_text(encoding="utf-8"))
STATE = Path("episodes.json")
SETTINGS = ["night_forest", "village", "house_inside", "river", "market", "mountain", "field", "well"]
MOODS = {  # top colour, bottom colour
    "calm": ((255, 214, 150), (120, 190, 120)), "tense": ((25, 25, 60), (10, 40, 40)),
    "funny": ((255, 240, 150), (255, 170, 120)), "sad": ((120, 130, 160), (70, 80, 100)),
    "night": ((15, 20, 55), (20, 50, 50)),
}

PROMPT = """You write episodes of a fictional Hindi story series called "{series}" for YouTube.
This is episode {n}. Genre this time: {genre}. Recurring cast (use 1-3 of them): {cast}
Earlier episodes (do not repeat plots): {past}

Write an original story in simple, vivid spoken Hindi (Devanagari), 8-10 minutes when read aloud (about 1300-1600
words), with: a hook in the first sentence, rising tension or comedy, and a surprising but fair twist at the end.
The characters are fictional; never mention real people, real organisations, real events, religion or politics.
No violence beyond mild suspense, nothing frightening for a general audience.
Return ONLY JSON:
{{"title": "...(Hindi, under 70 chars, curiosity-driven)", "description": "...(Hindi, 2 short paragraphs; first line must say this is a fictional story)",
 "tags": ["..."],
 "scenes": [{{"setting": one of {settings}, "mood": one of {moods}, "characters": ["names from the cast present in the scene, max 2"],
   "caption": "one short line shown on screen, in Devanagari letters only (no English letters)", "image_prompt": "ENGLISH description of what the picture shows: the action, place, time of day and mood (max 40 words, no character appearance details, no text in the picture)", "narration": "spoken text for this scene (about 100-150 words)"}}]}}
Use 10-14 scenes."""

CHECK = """Review this fictional Hindi story script for a general YouTube audience. Fix anything that mentions real people,
organisations, events, religion or politics, anything hateful, sexual or too violent/frightening, and anything copied
from a well-known existing story. Also make sure the first line is a strong hook and the ending has a twist. Keep the same
JSON structure. Return ONLY JSON: {{"ok": true or false, "issues": ["..."], "script": <full corrected script JSON>}}
Use "ok": false only if the story cannot be made safe by editing.

Script:
{script}"""

SHORTS = """From this Hindi story script, write {n} YouTube Shorts that work as cliffhanger trailers for the full episode. Each:
hook in the first line, tells only the setup, 30-45 seconds when read aloud (80-110 Hindi words), 3-4 scenes, and
ends by inviting viewers to watch the full story. Do not reveal the twist. Return ONLY JSON:
{{"shorts": [{{"title": "...(Hindi, under 60 chars)", "scenes": [{{"setting": ..., "mood": ..., "characters": [...],
 "caption": "...", "image_prompt": "ENGLISH picture description as above", "narration": "..."}}]}}]}}
Use the same setting/mood values as in the script.

Script:
{script}"""


def _json(text):
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


def _ask(prompt, tokens=16000):
    import anthropic
    r = anthropic.Anthropic().messages.create(model=P.MODEL, max_tokens=tokens,
                                              messages=[{"role": "user", "content": prompt}])
    return _json(P.reply_text(r))


# ---------- drawing ----------
def _gradient(img, top, bot):
    from PIL import ImageDraw
    d = ImageDraw.Draw(img); w, h = img.size
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))


def _scenery(d, setting, w, h, rnd):
    g = int(h * 0.68)  # ground line
    d.rectangle([0, g, w, h], fill=(60, 110, 60) if setting != "house_inside" else (150, 110, 80))
    if setting in ("night_forest", "field", "village", "mountain", "river", "market", "well"):
        for _ in range(60 if setting == "night_forest" else 0):
            x, y = rnd.randint(0, w), rnd.randint(0, int(g * 0.6)); d.ellipse([x, y, x + 5, y + 5], fill=(255, 255, 220))
    if setting == "night_forest":
        d.ellipse([w * 0.78, h * 0.08, w * 0.78 + h * 0.12, h * 0.08 + h * 0.12], fill=(250, 250, 225))
        for i in range(7):
            x = int(w * (0.05 + i * 0.15)); th = int(h * rnd.uniform(0.3, 0.45))
            d.rectangle([x, g - th // 3, x + 28, g], fill=(50, 35, 25))
            d.polygon([(x - 90, g - th // 3), (x + 14, g - th), (x + 118, g - th // 3)], fill=(20, 70, 40))
    elif setting == "mountain":
        for i, c in enumerate([(110, 110, 140), (80, 85, 110)]):
            d.polygon([(0, g), (w * (0.3 + i * 0.2), g - h * 0.4), (w * (0.7 + i * 0.1), g)], fill=c)
    elif setting == "river":
        d.rectangle([0, int(g + h * 0.05), w, int(g + h * 0.2)], fill=(70, 130, 200))
    elif setting == "village" or setting == "market":
        for i in range(3):
            x = int(w * (0.08 + i * 0.3)); bw = int(w * 0.2); bh = int(h * 0.2)
            d.rectangle([x, g - bh, x + bw, g], fill=(200, 150, 100)); d.polygon([(x - 15, g - bh), (x + bw // 2, g - bh - h * 0.1), (x + bw + 15, g - bh)], fill=(150, 70, 50))
            d.rectangle([x + bw // 2 - 20, g - bh // 2, x + bw // 2 + 20, g], fill=(90, 55, 35))
    elif setting == "field":
        for i in range(25):
            x = int(w * i / 25); d.line([(x, g + 20), (x + 6, g - 40)], fill=(220, 190, 60), width=6)
    elif setting == "well":
        cx = w // 2 + 200; d.ellipse([cx - 90, g - 30, cx + 90, g + 40], fill=(120, 120, 125)); d.ellipse([cx - 65, g - 18, cx + 65, g + 25], fill=(15, 15, 25))
    elif setting == "house_inside":
        d.rectangle([w * 0.1, h * 0.12, w * 0.3, h * 0.38], outline=(90, 60, 40), width=10, fill=(150, 200, 235))


def _person(d, cx, base, size, ch, mood, talk=False):
    skin, outfit = tuple(ch["skin"]), tuple(ch["outfit"])
    if ch["name"] == "बिल्लू":  # the cat
        d.ellipse([cx - size * .5, base - size * .55, cx + size * .5, base], fill=skin)
        d.ellipse([cx - size * .3, base - size * .95, cx + size * .3, base - size * .4], fill=skin)
        d.polygon([(cx - size * .3, base - size * .8), (cx - size * .2, base - size * 1.1), (cx - size * .08, base - size * .9)], fill=skin)
        d.polygon([(cx + size * .3, base - size * .8), (cx + size * .2, base - size * 1.1), (cx + size * .08, base - size * .9)], fill=skin)
        for ex in (-.12, .12): d.ellipse([cx + size * ex - 7, base - size * .72, cx + size * ex + 7, base - size * .62], fill=(250, 240, 80))
        return
    d.rounded_rectangle([cx - size * .3, base - size * 1.1, cx + size * .3, base - size * .25], radius=30, fill=outfit)
    d.rectangle([cx - size * .2, base - size * .27, cx - size * .05, base], fill=(60, 50, 50))
    d.rectangle([cx + size * .05, base - size * .27, cx + size * .2, base], fill=(60, 50, 50))
    hy = base - size * 1.4
    d.ellipse([cx - size * .26, hy - size * .26, cx + size * .26, hy + size * .26], fill=skin)
    d.pieslice([cx - size * .28, hy - size * .3, cx + size * .28, hy + size * .22], 180, 360, fill=(30, 25, 25))
    for ex in (-.1, .1): d.ellipse([cx + size * ex - 6, hy - 6, cx + size * ex + 6, hy + 6], fill=(255, 255, 255)); d.ellipse([cx + size * ex - 3, hy - 3, cx + size * ex + 3, hy + 3], fill=(20, 20, 20))
    if mood in ("tense", "sad"): d.arc([cx - size * .1, hy + size * .08, cx + size * .1, hy + size * .2], 200, 340, fill=(60, 30, 30), width=4)
    else: d.arc([cx - size * .12, hy + size * .02, cx + size * .12, hy + size * .16], 20, 160, fill=(60, 30, 30), width=5)


def drawn_scene(sc, path, size=(1920, 1080)):
    from PIL import Image, ImageDraw, ImageFont
    w, h = size
    mood = sc.get("mood", "calm"); mood = mood if mood in MOODS else "calm"
    img = Image.new("RGB", size); top, bot = MOODS[mood]; _gradient(img, top, bot)
    d = ImageDraw.Draw(img); rnd = random.Random(sc.get("caption", "") + sc.get("setting", ""))
    _scenery(d, sc.get("setting", "village"), w, h, rnd)
    by_name = {c["name"]: c for c in CAST["characters"]}
    names = [n for n in sc.get("characters", []) if n in by_name][:2]
    unit = min(w, h) * (0.32 if h > w else 0.36); base = int(h * 0.80)
    for i, n in enumerate(names):
        cx = int(w * ((i + 1) / (len(names) + 1))); _person(d, cx, base, unit, by_name[n], mood)
    if mood == "tense": img = Image.blend(img, Image.new("RGB", size, (0, 0, 0)), 0.15); d = ImageDraw.Draw(img)
    font = ImageFont.truetype(P.FONT, int(h * (0.032 if h > w else 0.03)))
    lines = P.wrap(d, sc.get("caption", ""), font, int(w * 0.82)); lh = int(font.size * 1.5)
    top_y = int(h * (0.86 if h <= w else 0.82)); box_h = lh * len(lines) + 30
    d.rounded_rectangle([w * 0.07, top_y, w * 0.93, top_y + box_h], radius=24, fill=(0, 0, 0))
    for j, ln in enumerate(lines): d.text((w * 0.1, top_y + 15 + j * lh), ln, font=font, fill=(255, 255, 255))
    img.save(path)


def _cloudflare_image(prompt):
    """Cloudflare Workers AI (FLUX.1 schnell). Needs CF_ACCOUNT_ID and CF_API_TOKEN. No watermark."""
    import base64, io, json, os, time, urllib.request
    from PIL import Image
    acct, tok = os.environ.get("CF_ACCOUNT_ID"), os.environ.get("CF_API_TOKEN")
    if not acct or not tok:
        return None
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    body = json.dumps({"prompt": prompt[:2000], "steps": 6}).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, data=body, headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=120).read())
            return Image.open(io.BytesIO(base64.b64decode(r["result"]["image"]))).convert("RGB")
        except Exception as e:
            print(f"cloudflare image attempt {attempt + 1} failed: {e}")
            time.sleep(8 * (attempt + 1))
    return None


def _pollinations_image(prompt, size, seed):
    """Free but adds a logo to the picture, so it is used only when USE_POLLINATIONS=1."""
    import io, time, urllib.parse, urllib.request
    from PIL import Image
    gw, gh = (1280, 720) if size[0] > size[1] else (720, 1280)
    url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
           f"?width={gw}&height={gh}&model=flux&seed={seed}&nologo=true")
    time.sleep(6)
    for attempt in range(4):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
            return Image.open(io.BytesIO(data)).convert("RGB")
        except Exception as e:
            print(f"pollinations attempt {attempt + 1} failed: {e}")
            time.sleep(10 * (attempt + 1))
    return None


def ai_image(prompt, size, seed):
    """A PIL image, or None so the caller falls back to the drawn scene."""
    import os
    im = _cloudflare_image(prompt)
    if im is None and os.environ.get("USE_POLLINATIONS") == "1":
        im = _pollinations_image(prompt, size, seed)
    return im


def full_prompt(sc):
    by_name = {c["name"]: c for c in CAST["characters"]}
    looks = "; ".join(by_name[n]["look"] for n in sc.get("characters", []) if n in by_name)
    parts = [CAST.get("style", ""), sc.get("image_prompt", ""), looks]
    return ", ".join(p for p in parts if p)


def caption_overlay(img, caption, size):
    from PIL import Image, ImageDraw, ImageFont
    w, h = size
    font = ImageFont.truetype(P.FONT, int(h * (0.032 if h > w else 0.03)))
    d = ImageDraw.Draw(img)
    lines = P.wrap(d, caption, font, int(w * 0.82)); lh = int(font.size * 1.5)
    top_y = int(h * (0.86 if h <= w else 0.80)); box_h = lh * len(lines) + 30
    layer = Image.new("RGBA", size, (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle([w * 0.07, top_y, w * 0.93, top_y + box_h], radius=24, fill=(0, 0, 0, 170))
    img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"); d = ImageDraw.Draw(img)
    for j, ln in enumerate(lines): d.text((w * 0.1, top_y + 15 + j * lh), ln, font=font, fill=(255, 255, 255))
    return img


def scene_image(sc, path, size=(1920, 1080)):
    """AI illustration when available (USE_AI_IMAGES=0 disables), otherwise the drawn scene."""
    import os
    from PIL import Image, ImageOps
    if os.environ.get("USE_AI_IMAGES", "1") != "0" and sc.get("image_prompt"):
        seed = sum(ord(ch) for ch in sc.get("caption", "")) % 100000
        im = ai_image(full_prompt(sc), size, seed)
        if im is not None:
            im = caption_overlay(ImageOps.fit(im, size, Image.LANCZOS), sc.get("caption", ""), size)
            im.save(path); return
    drawn_scene(sc, path, size)


# ---------- pipeline ----------
def make(upload=False):
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else []
    n = len(st) + 1; genre = "हल्का सस्पेंस/रहस्य" if n % 2 else "हास्य"
    cast = "; ".join(f'{c["name"]} ({c["role"]})' for c in CAST["characters"])
    script = _ask(PROMPT.format(series=CAST["series"], n=n, genre=genre, cast=cast, past=json.dumps(st, ensure_ascii=False),
                                settings=SETTINGS, moods=list(MOODS)))
    d = P.OUT / f"episode-{n:03d}"; d.mkdir(parents=True, exist_ok=True)
    chk = _ask(CHECK.format(script=json.dumps(script, ensure_ascii=False)))
    (d / "script.json").write_text(json.dumps(chk["script"], ensure_ascii=False, indent=2), encoding="utf-8")
    (d / "check.json").write_text(json.dumps({"ok": chk["ok"], "issues": chk["issues"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    st.append(chk["script"]["title"]); STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    if not chk["ok"]:
        (d / "REVIEW_NEEDED.txt").write_text("Safety check failed; not rendered. See check.json."); print("Skipped:", n); return
    P.build_video(chk["script"], d, "video", (1920, 1080), scene_image, zoom=True)
    P.make_shorts(d, 3, SHORTS, scene_image, zoom=True)
    if upload: P.upload(d)


def preview():
    """Make a few sample pictures (no video, no upload) to judge image quality."""
    d = Path("preview"); d.mkdir(exist_ok=True)
    samples = [
        {"setting": "night_forest", "mood": "tense", "characters": ["चंपक", "बिल्लू"], "caption": "Champak and Billu hear a sound in the forest",
         "image_prompt": "a boy and a cat walking carefully through a moonlit forest, a mysterious glowing light between the trees"},
        {"setting": "village", "mood": "funny", "characters": ["सरपंच जी", "दादी माँ"], "caption": "The Sarpanch argues with Dadi Maa",
         "image_prompt": "a headman and a grandmother arguing comically in a sunny village square, villagers laughing behind them"},
        {"setting": "house_inside", "mood": "calm", "characters": ["दादी माँ", "चंपक"], "caption": "Dadi Maa tells a story",
         "image_prompt": "a grandmother telling a story to a boy by an oil lamp inside a cosy village house"},
    ]
    for i, sc in enumerate(samples, 1):
        scene_image(sc, d / f"sample{i}_wide.png", (1920, 1080))
    scene_image(samples[0], d / "sample_vertical.png", (1080, 1920))
    print("preview images saved in", d)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "make"
    if cmd == "preview": preview()
    else: make(upload=(cmd == "autopilot"))
