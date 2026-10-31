"""Channel studio: makes and uploads episodes for each YouTube channel in channels.json.

  python studio.py run              # every channel scheduled for today (UTC) that has a login token
  python studio.py run kids         # one channel now, ignoring the schedule
Formats: learning (kids' lessons), stories (cartoon stories), explainers (slides, fact-checked).
All cartoon scenes are drawn by toon.py, so characters look the same in every episode.
"""
import asyncio, datetime, json, os, subprocess, sys, time, traceback
from pathlib import Path
import pipeline as P
import toon
import yt

ROOT = Path(__file__).parent
CAST = json.loads((ROOT / "cast.json").read_text(encoding="utf-8"))
CHANNELS = json.loads((ROOT / "channels.json").read_text(encoding="utf-8"))
OUT, STATE = Path("output"), Path("state")
SETTINGS = ["village", "night_forest", "house_inside", "river", "market", "mountain", "field", "well"]
MOODS = ["calm", "funny", "tense", "sad"]

LEARN = """You write episodes of a Hindi learning cartoon for children aged 2 to 5, called "{series}".
Teacher characters: चंपक (a cheerful boy who teaches) and बिल्लू (the cat, a funny helper).
Topic: {topic}
Notes: {notes}
Earlier lessons (do not repeat): {past}

Make a 3-4 minute lesson in very simple, warm, spoken Hindi (Devanagari) with lots of repetition: say each new thing,
ask the child to repeat ("मेरे साथ बोलो"), give one tiny example, and recap at the end. Everything must be correct and
age-appropriate. Each scene is one teaching step.
For a card use: "card": {{"big": "one Devanagari letter or numeral shown large", "prop": "one of {props} - ONLY if the
picture exactly matches the word, otherwise leave prop out", "count": a number 1-10 (only with a prop, for counting scenes),
"label": "short Hindi label"}}. The drawn props are: apple=सेब, mango=आम, banana=केला, ball=गेंद, star=तारा, flower=फूल,
balloon=गुब्बारा, heart=दिल, fish=मछली, pomegranate=अनार. Scenes without a card just show the characters talking.
Return ONLY JSON:
{{"title": "...(Hindi, under 70 chars)", "description": "...(Hindi, 2 short paragraphs; do not write that it is made for kids or children)",
 "tags": ["..."],
 "scenes": [{{"setting": one of {settings}, "mood": "calm" or "funny", "characters": ["चंपक", "बिल्लू"],
   "speaker": "चंपक" or "बिल्लू" or "narrator", "wave": "चंपक" (optional), "caption": "short Hindi line, Devanagari letters only",
   "card": {{...}} (optional), "narration": "spoken text, 1-3 short sentences"}}]}}
Use 14-20 scenes."""

STORY = """You write episodes of a fictional Hindi cartoon story series for a general audience (teenagers and adults), called "{series}".
This is episode {n}. Genre this time: {genre}. Cast (use 1-3 in a scene): {cast}
Earlier episodes (do not repeat plots): {past}

Write an original story in vivid, natural spoken Hindi (Devanagari), 6-8 minutes when read aloud, for grown-up viewers: a gripping
hook in the first sentence, believable village characters with real motives, sharp humour or real suspense, dialogue, and a clever
twist at the end. Themes can be mystery, irony, family tension, greed, jealousy, friendship or a puzzle solved by wit. Keep it clean:
no sexual content, no graphic violence, no hate, nothing aimed at young children. Fictional characters only: never mention real people,
organisations, events, religion or politics.
Return ONLY JSON:
{{"title": "...(Hindi, under 70 chars, curiosity-driven)", "description": "...(Hindi, 2 short paragraphs; first line says this is a fictional story; do not write that it is made for kids or children)",
 "tags": ["..."],
 "scenes": [{{"setting": one of {settings}, "mood": one of {moods}, "characters": ["names present, max 3"],
   "speaker": "a character name when that character speaks, or \\"narrator\\"", "caption": "one short Hindi line, Devanagari letters only",
   "narration": "the spoken words for this scene (1-4 sentences; in dialogue scenes only what the speaker says)"}}]}}
Use 22-30 scenes."""

CHECK = """Review this fictional Hindi story script for a general audience. Fix anything that mentions real people, organisations, events,
religion or politics, anything hateful, sexual or graphically violent, anything aimed at young children, and anything copied from a well-known story.
Make sure the first line is a strong hook and the ending has a twist. Keep the same JSON structure. Return ONLY JSON:
{{"ok": true or false, "issues": ["..."], "script": <full corrected script JSON>}}
Use "ok": false only if the story cannot be made safe by editing.

Script:
{script}"""

LCHECK = """Check this Hindi lesson for children aged 2-5 for factual mistakes (letters, words, numbers, counts, colours) and anything
unsuitable for young children. Fix problems; make sure every card's prop matches its label and every count matches the spoken
number. Keep the same JSON structure. Return ONLY JSON: {{"ok": true or false, "issues": ["..."], "script": <full corrected script JSON>}}
Use "ok": false only if it cannot be fixed.

Script:
{script}"""

SHORTS = """From this Hindi {kind} script, write {n} YouTube Shorts. {rule}
Each Short has 3-4 scenes and 80-110 spoken Hindi words in total (30-45 seconds). Use the same scene format and the same cast.
Return ONLY JSON: {{"shorts": [{{"title": "...(Hindi, under 60 chars)", "scenes": [ ...scenes... ]}}]}}

Script:
{script}"""

LEARN_TOPICS = [
    ("हिंदी स्वर: अ, आ, इ, ई", "अ से अनार, आ से आम, इ से इमली, ई से ईख"), ("हिंदी स्वर: उ, ऊ, ऋ, ए", "उ से उल्लू, ऊ से ऊँट, ए से एड़ी"),
    ("हिंदी स्वर: ऐ, ओ, औ, अं, अः", "ऐ से ऐनक, ओ से ओखली, औ से औरत"), ("गिनती 1 से 5", "हर संख्या के साथ चीज़ें गिनवाएँ"),
    ("गिनती 6 से 10", "हर संख्या के साथ चीज़ें गिनवाएँ"), ("हिंदी व्यंजन: क, ख, ग, घ", "क से कमल, ख से खरगोश, ग से गमला, घ से घर"),
    ("रंग पहचानें", "लाल, पीला, नीला, हरा"), ("आकार पहचानें", "गोला, चौकोर, तिकोना"), ("फल पहचानें", "सेब, आम, केला, अनार"),
    ("हिंदी व्यंजन: च, छ, ज, झ", "च से चम्मच, छ से छतरी, ज से जहाज़, झ से झंडा"), ("सप्ताह के दिन", "सोमवार से रविवार"),
    ("गिनती 11 से 15", "बड़ी संख्याएँ आराम से"), ("हिंदी व्यंजन: ट, ठ, ड, ढ", "ट से टमाटर, ठ से ठेला, ड से डमरू, ढ से ढोल"),
    ("शरीर के अंग", "आँख, नाक, कान, हाथ"), ("हिंदी व्यंजन: त, थ, द, ध, न", "त से तारा, थ से थाली, द से दवात, न से नल"),
    ("जानवर और उनकी आवाज़ें", "गाय, कुत्ता, बिल्ली, शेर"), ("हिंदी व्यंजन: प, फ, ब, भ, म", "प से पतंग, फ से फल, ब से बतख, भ से भालू, म से मछली"),
    ("गिनती 16 से 20", "बड़ी संख्याएँ आराम से"), ("हिंदी व्यंजन: य, र, ल, व", "य से यज्ञ, र से रथ, ल से लड्डू, व से वन"),
    ("अच्छी आदतें", "सुबह उठना, दाँत साफ़, हाथ धोना"),
]
LEARN_DONE_NOTE = "Repeat the curriculum from the start with new examples when the list ends."


def ask(prompt, tokens=16000):
    import anthropic
    r = anthropic.Anthropic().messages.create(model=P.MODEL, max_tokens=tokens, messages=[{"role": "user", "content": prompt}])
    text = P.reply_text(r)
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


def looks():
    return {c["name"]: toon.Look(c["name"], c["kind"], tuple(c["skin"]), tuple(c["outfit"]), tuple(c.get("hair", (35, 28, 28))),
                                 tuple(c.get("pants", (70, 70, 110)))) for c in CAST["characters"]}


async def _tts(text, v, path, rate):
    import edge_tts
    await edge_tts.Communicate(text, v["voice"], rate=rate, pitch=v.get("pitch", "+0Hz")).save(str(path))


def tts(text, speaker, path, slow=False):
    v = CAST["voices"].get(speaker) or CAST["voices"]["narrator"]
    rate = int(v.get("rate", "+0%").rstrip("%")) - (10 if slow else 0)
    for attempt in range(3):
        try:
            asyncio.run(_tts(text, v, path, f"{rate:+d}%")); return
        except Exception as e:
            print(f"voice attempt {attempt + 1} failed: {e}"); time.sleep(5)
    raise RuntimeError("voice generation failed")


def clean_scene(sc, cast):
    sc = dict(sc)
    sc["setting"] = sc.get("setting") if sc.get("setting") in SETTINGS else "village"
    sc["mood"] = sc.get("mood") if sc.get("mood") in toon.PALETTES else "calm"
    sp = sc.get("speaker") if sc.get("speaker") in cast else None
    chars = [n for n in sc.get("characters", []) if n in cast][:3]
    if sp and sp not in chars: chars = (chars + [sp])[:3]
    if not chars: chars = [next(iter(cast))]
    sc["speaker"], sc["characters"] = sp, chars
    card = sc.get("card")
    if isinstance(card, dict):
        card = {k: card[k] for k in ("big", "prop", "count", "label") if card.get(k)}
        if card.get("prop") not in toon.PROPS: card.pop("prop", None); card.pop("count", None)
        if "count" in card:
            try: card["count"] = max(1, min(10, int(card["count"])))
            except (TypeError, ValueError): card.pop("count")
        sc["card"] = card or None
    else:
        sc["card"] = None
    if sc.get("wave") not in cast: sc["wave"] = None
    return sc


def render_video(data, d, name, size, slow=False):
    cast = looks(); clips = []
    for i, raw in enumerate(data["scenes"]):
        sc = clean_scene(raw, cast)
        mp3, mp4 = d / f"{name}_{i}.mp3", d / f"{name}_{i}.mp4"
        tts(raw.get("narration") or sc.get("caption") or ".", sc["speaker"], mp3, slow)
        toon.render_scene(sc, cast, str(mp3), str(mp4), size)
        clips.append(mp4)
    lst = d / f"{name}_list.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in clips))
    out = d / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)], check=True)
    for c in clips: c.unlink(missing_ok=True); c.with_suffix(".mp3").unlink(missing_ok=True)
    return out


def shorts_for(data, d, kind, rule, slow=False, n=3):
    sp = d / "shorts.json"
    if not sp.exists():
        r = ask(SHORTS.format(kind=kind, rule=rule, n=n, script=json.dumps(data, ensure_ascii=False)), 12000)
        sp.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    items = json.loads(sp.read_text(encoding="utf-8"))["shorts"]
    return [(render_video(sh, d, f"short{i}", (720, 1280), slow), sh["title"]) for i, sh in enumerate(items, 1)]


def load_state(ch):
    f = STATE / f"{ch}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def save_state(ch, st):
    STATE.mkdir(exist_ok=True); (STATE / f"{ch}.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def make_episode(key, cfg):
    """Returns (folder, [(file, title)...], data) or None if the safety check rejects the script."""
    st = load_state(key); n = len(st) + 1
    d = OUT / f"{key}-{n:03d}"; d.mkdir(parents=True, exist_ok=True)
    fmt = cfg["format"]
    if fmt == "learning":
        topic, notes = LEARN_TOPICS[(n - 1) % len(LEARN_TOPICS)]
        draft = ask(LEARN.format(series=CAST.get("series_kids", CAST["series"]), topic=topic, notes=notes, past=json.dumps(st[-8:], ensure_ascii=False),
                                 props=toon.PROPS, settings=SETTINGS))
        chk = ask(LCHECK.format(script=json.dumps(draft, ensure_ascii=False)))
        slow, kind, rule, size = True, "learning lesson", "Each Short teaches ONE thing from the lesson (one letter, number, colour or word) with the same repeat-after-me style.", (1280, 720)
    elif fmt == "stories":
        genre = "हल्का सस्पेंस/रहस्य" if n % 2 else "हास्य"
        cast = "; ".join(f'{c["name"]} ({c["role"]})' for c in CAST["characters"])
        draft = ask(STORY.format(series=CAST["series"], n=n, genre=genre, cast=cast, past=json.dumps(st[-10:], ensure_ascii=False),
                                 settings=SETTINGS, moods=MOODS))
        chk = ask(CHECK.format(script=json.dumps(draft, ensure_ascii=False)))
        slow, kind, rule, size = False, "story", "Make them cliffhanger trailers: tell only the setup, never reveal the twist, and end by inviting viewers to watch the full story.", (1280, 720)
    else:
        raise ValueError(fmt)
    data = chk["script"]
    (d / "script.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (d / "check.json").write_text(json.dumps({"ok": chk["ok"], "issues": chk["issues"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    st.append(data["title"]); save_state(key, st)
    if not chk["ok"]:
        (d / "REVIEW_NEEDED.txt").write_text("Check failed; not rendered. See check.json."); return None
    items = [(render_video(data, d, "video", size, slow), data["title"])]
    items += [(f, t + " #Shorts") for f, t in shorts_for(data, d, kind, rule, slow)]
    return d, items, data


def make_explainer(key, cfg):
    st = load_state(key)
    t = P.next_topic(st)
    d = OUT / f"{key}-{len(st) + 1:03d}"; d.mkdir(parents=True, exist_ok=True)
    data, ok = P.factcheck(P.write_script(t["topic"], t["notes"], d), d)
    st.append(t["topic"]); save_state(key, st)
    if not ok:
        (d / "REVIEW_NEEDED.txt").write_text("Fact-check confidence low; skipped."); return None
    items = [(P.build_video(data, d), data["title"])]
    P.make_shorts(d)
    sj = json.loads((d / "shorts.json").read_text(encoding="utf-8"))["shorts"]
    items += [(d / f"short{i}.mp4", sh["title"] + " #Shorts") for i, sh in enumerate(sj, 1)]
    return d, items, data


LIMIT_ERRORS = ("uploadLimitExceeded", "quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded")


def run_channel(key, cfg, creds):
    res = make_explainer(key, cfg) if cfg["format"] == "explainers" else make_episode(key, cfg)
    if res is None:
        print(f"[{key}] skipped by the quality check"); return
    d, items, data = res
    kids = cfg.get("made_for_kids", False)
    desc = data.get("description", "")
    for n, (f, title) in enumerate(items):
        short = title.endswith("#Shorts")
        try:
            yt.upload(creds, f, title, desc + ("\n\n#Shorts" if short else ""), data.get("tags", []), kids, cfg.get("category", "27"))
        except Exception as e:
            if not any(x in str(e) for x in LIMIT_ERRORS):
                raise
            if n == 0:  # the main video did not go up: forget this topic so tomorrow retries it
                save_state(key, load_state(key)[:-1])
                raise RuntimeError("YouTube upload limit reached before the main video; will retry on the next run") from e
            print(f"[{key}] YouTube daily upload limit reached; {len(items) - n} Short(s) skipped for this episode")
            break


def run(only=None):
    today = datetime.datetime.now(datetime.timezone.utc).isoweekday()
    failed = []
    for key, cfg in CHANNELS.items():
        if only and key != only: continue
        if not only and today not in cfg.get("days", []): continue
        creds = yt.get_creds(cfg["token_env"], f"token_{key}.json")
        if creds is None:
            print(f"[{key}] no login token yet ({' / '.join(cfg['token_env'])}); skipped"); continue
        print(f"[{key}] making today's episode ({cfg['format']})")
        try:
            run_channel(key, cfg, creds)
        except Exception:
            traceback.print_exc(); failed.append(key)
    if failed:
        sys.exit(f"failed: {', '.join(failed)}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "run": run(sys.argv[2] if len(sys.argv) > 2 else None)
