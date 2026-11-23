import os, re, math, random, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ---------- SETTINGS ----------
FORMAT = os.environ.get("FORMAT", "landscape").strip().lower()
W, H = (2160, 3840) if FORMAT == "vertical" else (3840, 2160)
FPS = 30
AUDIO = "song.mp3.mp3"
COVER = "cover.jpg.JPG"
LYRICS_FILE = "lyrics.js"
TIMES_FILE = "times.js"
FONT_FILE = "font.ttf"
OUT = f"thing_dem_work_4k_{FORMAT}.mp4"
ARTIST = "BAZRAGOD"
TITLE = "THING DEM WORK"

RED = (255, 31, 61)
GOLD = (255, 201, 40)
WHITE = (255, 255, 255)
BLACK = (5, 5, 5)
OUTLINE = (0, 0, 0)

HOOK = re.compile(r"thing dem wo", re.I)

# ---------- HELPERS ----------
def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3

def load_font(size):
    for p in [FONT_FILE, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def audio_duration():
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", AUDIO],
        capture_output=True, text=True)
    return float(r.stdout.strip())

def load_lyrics():
    with open(LYRICS_FILE, encoding="utf-8") as f:
        txt = f.read()
    m = re.search(r"\[(.*)\]", txt, re.S)
    if not m:
        return []
    items = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
    return [s for s in items if s.strip()]

def load_times():
    with open(TIMES_FILE, encoding="utf-8") as f:
        txt = f.read()
    m = re.search(r"\[(.*?)\]", txt, re.S)
    if not m:
        return []
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", m.group(1))]

BASE = min(W * 0.075, H * 0.11)
BIG = load_font(int(BASE))
SMALL = load_font(int(BASE * 0.75))
FONT_TITLE = load_font(int(min(W * 0.09, H * 0.14)))
FONT_ARTIST = load_font(int(min(W * 0.045, H * 0.07)))

def layout(text, font):
    words = text.split()
    space = font.getlength(" ")
    rows, cur, width = [], [], 0
    for wd in words:
        wl = font.getlength(wd)
        if cur and width + space + wl > W * 0.84:
            rows.append((cur, width))
            cur, width = [wd], wl
        else:
            width = wl if not cur else width + space + wl
            cur.append(wd)
    if cur:
        rows.append((cur, width))
    line_h = font.size * 1.2
    total_h = len(rows) * line_h
    y = H / 2 - total_h / 2
    placed = []
    for row, rw in rows:
        x = (W - rw) / 2
        for wd in row:
            placed.append((wd, x, y))
            x += font.getlength(wd) + space
        y += line_h
    return placed, total_h

def build_lines(lyrics, times, dur):
    n = min(len(times), len(lyrics))
    out = []
    for i in range(n):
        s = times[i]
        nxt = times[i + 1] if i + 1 < n else None
        e = min(nxt, s + 8) if nxt is not None else min(s + 4, dur)
        span = (nxt if nxt is not None else s + 4) - s
        text = lyrics[i].upper()
        font = BIG
        placed, h = layout(text, font)
        if h > font.size * 1.2 * 3:
            font = SMALL
            placed, h = layout(text, font)
        step = min(0.22, max(0.05, span * 0.55 / max(1, len(placed))))
        out.append({"s": s, "e": e, "words": placed, "font": font, "h": h,
                    "step": step, "hook": bool(HOOK.search(text))})
    return out

# ---------- BACKGROUND ----------
def make_bg():
    if not os.path.exists(COVER):
        return Image.new("RGBA", (W, H), BLACK + (255,))
    c = Image.open(COVER).convert("RGB")
    scale = max(W / c.width, H / c.height)
    c = c.resize((int(c.width * scale) + 1, int(c.height * scale) + 1))
    left, top = (c.width - W) // 2, (c.height - H) // 2
    c = c.crop((left, top, left + W, top + H))
    c = c.filter(ImageFilter.GaussianBlur(int(max(W, H) * 0.002)))
    c = ImageEnhance.Brightness(c).enhance(0.55)
    c = ImageEnhance.Color(c).enhance(1.35)
    return c.convert("RGBA")

M = max(W, H)
random.seed(14)
SHARD_COLORS = [(255, 31, 61, 80), (255, 201, 40, 70), (179, 0, 27, 90)]
SHARDS = []
for i in range(9):
    SHARDS.append({
        "x": random.uniform(0, W), "y": random.uniform(0, H),
        "r": random.uniform(M * 0.065, M * 0.18), "spin": random.uniform(-0.15, 0.15),
        "drift": random.uniform(M * 0.005, M * 0.015), "phase": random.uniform(0, 6.28),
        "color": SHARD_COLORS[i % 3],
        "pts": [random.uniform(0.55, 1.0) for _ in range(5)],
    })

def draw_shards(od, t):
    for s in SHARDS:
        a = s["phase"] + t * s["spin"]
        cx = s["x"] + math.sin(t * 0.2 + s["phase"]) * s["drift"]
        cy = s["y"] + math.cos(t * 0.17 + s["phase"]) * s["drift"]
        n = len(s["pts"])
        pts = [(cx + math.cos(a + i * 2 * math.pi / n) * s["r"] * s["pts"][i],
                cy + math.sin(a + i * 2 * math.pi / n) * s["r"] * s["pts"][i])
               for i in range(n)]
        od.polygon(pts, fill=s["color"])

# ---------- SCENES ----------
def outlined(d, xy, text, font, fill):
    fs = font.size
    sh = fs * 0.07
    d.text((xy[0] + sh, xy[1] + sh), text, font=font, fill=RED,
           stroke_width=max(2, int(fs * 0.035)), stroke_fill=OUTLINE)
    d.text(xy, text, font=font, fill=fill,
           stroke_width=max(2, int(fs * 0.035)), stroke_fill=OUTLINE)

def draw_card(d, t, top, big, top_font, big_font):
    p = ease(t / 0.8)
    tw = top_font.getlength(top)
    bw = big_font.getlength(big)
    tx = (W - tw) / 2 - (1 - p) * W * 0.6
    bx = (W - bw) / 2 + (1 - p) * W * 0.6
    d.text((tx, H * 0.36), top, font=top_font, fill=GOLD,
           stroke_width=max(2, int(top_font.size * 0.03)), stroke_fill=OUTLINE)
    outlined(d, (bx, H * 0.44), big, big_font, WHITE)
    rh = max(8, H * 0.01)
    y = H * 0.44 + big_font.size * 1.35
    d.rectangle([W * 0.2, y, W * 0.2 + W * 0.6 * ease((t - 0.2) / 0.9), y + rh], fill=GOLD)

def shake(L, lt):
    if L["hook"] and lt < 0.35:
        amp = (1 - lt / 0.35) * W * 0.012
        return math.sin(lt * 90) * amp, math.cos(lt * 70) * amp * 0.5
    return 0, 0

def draw_bar(od, L, t):
    lt = t - L["s"]
    dur = L["e"] - L["s"]
    dx, dy = shake(L, lt)
    pin = ease(lt / 0.35)
    pout = ease((lt - (dur - 0.3)) / 0.3) if dur > 0.7 else 0
    bh = L["h"] + H * 0.08
    cy = H / 2 + dy
    skew = bh * 0.25
    x0, x1 = W * pout - skew + dx, W * pin + skew + dx
    if x1 > x0:
        od.polygon([(x0, cy - bh / 2), (x1 + skew, cy - bh / 2),
                    (x1, cy + bh / 2), (x0 - skew, cy + bh / 2)], fill=(0, 0, 0, 190))
        edge = bh * 0.06
        od.rectangle([x0, cy + bh / 2 - edge, x1, cy + bh / 2], fill=(255, 31, 61, 230))
        rh = max(8, H * 0.01)
        gap = H * 0.024
        rl = (x1 - x0) * 0.6
        od.rectangle([x0, cy - bh / 2 - gap - rh, x0 + rl, cy - bh / 2 - gap], fill=GOLD + (255,))
        od.rectangle([x1 - rl, cy + bh / 2 + gap, x1, cy + bh / 2 + gap + rh], fill=GOLD + (255,))
    return pout

def draw_words(d, L, t, pout):
    if pout > 0.5:
        return
    lt = t - L["s"]
    dx, dy = shake(L, lt)
    font = L["font"]
    fs = font.size
    for i, (wd, x, y) in enumerate(L["words"]):
        appear = 0.18 + i * L["step"]
        if lt < appear:
            continue
        k = ease((lt - appear) / 0.32)
        yy = y - 0.6 * fs * (1 - k) + dy
        early = (lt - appear) < 0.21
        if L["hook"]:
            color = WHITE if early else GOLD
        else:
            color = GOLD if early else WHITE
        outlined(d, (x + dx, yy), wd, font, color)

# ---------- MAIN ----------
DUR_FULL = audio_duration()
DUR = DUR_FULL
ts = os.environ.get("TEST_SECONDS", "").strip()
if ts:
    DUR = min(DUR, float(ts))

LYRICS = load_lyrics()
TIMES = load_times()
if not TIMES:
    raise SystemExit("times.js has no timings yet - do SYNC LYRICS first.")
if len(TIMES) != len(LYRICS):
    print(f"WARNING: {len(TIMES)} timings for {len(LYRICS)} lines - re-sync for a perfect match.", flush=True)
LINES = build_lines(LYRICS, TIMES, DUR_FULL)
FIRST = LINES[0]["s"]
END_AT = LINES[-1]["e"] + 0.5
BG = make_bg()

def render(t):
    img = BG.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    draw_shards(od, t)
    active = None
    if FIRST <= t < END_AT:
        for L in LINES:
            if L["s"] <= t < L["e"]:
                active = L
                break
    pout = draw_bar(od, active, t) if active else 0
    img = Image.alpha_composite(img, ov)
    d = ImageDraw.Draw(img)
    if t < FIRST:
        draw_card(d, t, ARTIST, TITLE, FONT_ARTIST, FONT_TITLE)
    elif t >= END_AT:
        draw_card(d, t - END_AT, "WRITTEN BY BAZRAGOD", "PARISH 14 NATION", FONT_ARTIST, FONT_TITLE)
    elif active:
        draw_words(d, active, t, pout)
    d.rectangle([0, H - max(10, H * 0.0075), int(W * t / DUR_FULL), H], fill=GOLD)
    return img.convert("RGB")

cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
       "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
       "-i", AUDIO, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k",
       "-shortest", "-movflags", "+faststart", OUT]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
total = int(DUR * FPS)
for f in range(total):
    proc.stdin.write(render(f / FPS).tobytes())
    if f % 300 == 0:
        print(f"frame {f}/{total}", flush=True)
proc.stdin.close()
proc.wait()
print("done:", OUT)
