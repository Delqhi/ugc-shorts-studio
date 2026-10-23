"""Proof-Short-Engine v5: JSON-Storyboard -> 9:16-Frames -> ffmpeg-Pipe.

Entstanden aus dem carVertical-UGC-Short (21./22.10.2026), generalisiert auf alle
Beleg-Shorts. Die Engine kennt KEINE Marke: alles kommt aus dem Storyboard-JSON.

v5 (Gefahrenzone-Frame):
- Inhalt 1032x1728 = 86,0 % der Flaeche, Kopfleiste 88 px, Warnband 24 px rundum mit
  abgeschraegten Ecken, Ecken-Marker, Blinklichter, rote Innenkante beim Szenenstart.
- Headline als Overlay im Inhalt (Tinten-Unterkante y=300), Untertitel als unteres Band (y=1620).
- Neues Szenen-Kind "danger" (Hook: Bild vollflaechig ab Frame 1, Text-Schlaege mit Punch,
  roter Rand-Puls, Ring, Stempel).
- clip: "fit": "cover" (Standard, fuellt den Inhalt) | "card" (ganzes 16:9-Bild auf Unschaerfe).

Storyboard-Schema (siehe ../schema/brief.schema.json):
{
  "meta": {"fps":30, "duration":24.0, "vo":"tts/vo.wav", "words":"tts/vo.words.json",
           "code": {"label":"CODE USC20 · −20 %", "from": 13.4},
           "fonts": {"display":"assets/fonts/Anton-Regular.ttf",
                     "text":"assets/fonts/Montserrat-ExtraBold.ttf"},
           "out": "out/short.mp4", "frame_style": "hazard"},
  "scenes": [
   {"kind":"danger", "tag":"BEWEIS 01 · UNFALLFOTO", "start":0.0, "end":2.6,
    "media":{"path":"m/v4_wreck.png","unit":2.4,"span":474,"fx":560,"fx_to":820,"fy":330,
             "punch_step":0.06},
    "ring":{"center":[885,375],"rx":205,"ry":150,"at":0.5},
    "chops":[[0.0,"KEIN UNFALL?","white"],[0.9,"22.501 – 25.000 €","yellow"]],
    "chop_y":0.30,
    "stamp":{"text":"WAHNSINN!","at":2.0,"x":0.5,"y":0.55,"deg":-7,"size":170}},
   {"kind":"evidence","tag":"BEWEIS 02","start":2.6,
    "media":{"path":"m/km.png","span":1290,"span_to":1200,"fy":620,"anchor":[0.5,0.33]},
    "headlines":[[0.0,"DER REPORT SAGT:","white"],[1.43,"KILOMETER-MANIPULATION","yellow"]],
    "annotations":[
      {"type":"rect","box":[176,538,1212,738],"color":"yellow","width":9,"at":1.45,"dur":0.8},
      {"type":"arrow","from":[1150,330],"to":[1060,515],"color":"red","width":10,"at":2.0},
      {"type":"label","text":"KILOMETER-RÜCKSTELLUNG","at_xy":[786,1446],"size":32}]},
   {"kind":"clip", "fit":"cover", ...}, {"kind":"coupon", ...} ]
}

Wichtig (aus den Fehlern der ersten Versionen):
- Untertitel: Text zuerst auf EINER Grundlinie rendern, Alpha-Bbox messen, Platte = Bbox + Padding.
  Niemals Platte und Text getrennt positionieren -> der Text sitzt sonst neben der Platte.
- Text-Ebenen auf die Tinte zuschneiden (Alpha-Bbox) und mit Anker setzen -> y ist die
  Glyphenkante, nicht die Layer-Oberkante (sonst sitzt alles ~28 px zu tief).
- Kamera: Subpixel-Box via PIL resize(box=...) statt ffmpeg-zoompan (das wackelt).
- Inhaltsfenster startet bei x0=0 der Quelle, sonst werden Report-Ueberschriften links abgeschnitten.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent          # Skill-Wurzel
W, H, FPS = 1080, 1920, 30

# ---- Gefahrenzone-Frame (v5): Inhalt 1032x1728 = 86,0 % der Flaeche
HEADER_H = 88                                   # Kopfleiste (<= 120 px)
BAND = 24                                       # Warnband rundum
CHAMFER = 56                                    # abgeschraegte Aussenecken
ICHAMFER = 46                                   # abgeschraegte Innenecken (Inhalt)
STRIPE = 34                                     # Streifenbreite, 45°
CX0, CY0 = BAND, HEADER_H + BAND                # 24, 112
CX1, CY1 = W - BAND, HEADER_H + BAND + 1728     # 1056, 1840
CW, CH = CX1 - CX0, CY1 - CY0                   # 1032 x 1728 (Fix: war CX1 - CY0)
TAPE = BAND                                     # Altname
HEAD_BASE = 300                                 # Headline-Overlay: Tinten-Unterkante
SUB_CY = 1620                                   # Untertitel-Band: Plattenmitte
FRAME_IN = 0.35                                 # Band-Einzug am Videostart (s, ease_out)
HOT_EDGE = 0.30                                 # rote Innenkante je Szenenstart (s)
BEACON_HZ = 2.5                                 # Blinklichter, wechselseitig
HOOK_DUR = 2.6                                  # Hook-Abschnitt (danger): Standardlaenge in s
SCRIM_TOP = (0, 330, 175)                       # Inhalt-y von, bis, max. Alpha (Headline)
SCRIM_BOT = (1340, 1728, 110)                   # schwach: Untertitel-Platte bleibt messbar

C_BG = (0x07, 0x09, 0x0F)
C_HAZ = (0xFF, 0xD4, 0x00)
C_HAZ_DARK = (0x11, 0x11, 0x11)
C_BEACON = (0xFF, 0x2D, 0x2D)
C_EDGE = (0x00, 0x00, 0x00)

YELLOW = (255, 212, 0)
WHITE = (255, 255, 255)
INK = (10, 15, 28)
RED = (255, 64, 64)
GREY = (150, 162, 182)
BLACK = (0, 0, 0)
COLORS = {"yellow": YELLOW, "red": RED, "white": WHITE, "grey": GREY, "ink": INK}

_fonts: dict = {}


# ------------------------------------------------------------------ Helfer
def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def seg(t, t0, t1):
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return clamp((t - t0) / (t1 - t0))


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_out_back(t):
    t = clamp(t)
    c1, c3 = 1.9, 2.9
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_in_out(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2


def load_fonts(meta):
    disp = ROOT / meta.get("fonts", {}).get("display", "assets/fonts/Anton-Regular.ttf")
    txt = ROOT / meta.get("fonts", {}).get("text", "assets/fonts/Montserrat-ExtraBold.ttf")
    _fonts["display"] = str(disp)
    _fonts["text"] = str(txt)


@lru_cache(maxsize=None)
def f_display(size):
    return ImageFont.truetype(_fonts["display"], size)


@lru_cache(maxsize=None)
def f_text(size):
    f = ImageFont.truetype(_fonts["text"], size)
    try:
        f.set_variation_by_axes([800])
    except Exception:
        pass
    return f


@lru_cache(maxsize=512)
def ink_layer(text, font_key, fill, stroke_w=0, stroke=BLACK):
    """Text -> RGBA-Ebene, exakt auf die Tinte (Alpha-Bbox) zugeschnitten.

    font_key = (pfad, size) oder (font_factory, size)."""
    path, size = font_key
    font = path(size) if callable(path) else ImageFont.truetype(path, size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    bb = tmp.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
    pad = 20 + stroke_w
    lay = Image.new("RGBA", (bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((pad - bb[0], pad - bb[1]), text, font=font, fill=fill,
                             stroke_width=stroke_w, stroke_fill=stroke)
    return lay.crop(lay.getchannel("A").getbbox())


def place(base, lay, x, y, anchor="lt", scale=1.0, alpha=255):
    if alpha <= 0 or scale <= 0.01:
        return
    if scale != 1.0:
        lay = lay.resize((max(1, round(lay.width * scale)), max(1, round(lay.height * scale))),
                         Image.LANCZOS)
    if alpha < 255:
        lay = lay.copy()
        lay.putalpha(lay.getchannel("A").point(lambda v: v * alpha // 255))
    ax = {"l": 0.0, "c": 0.5, "r": 1.0}[anchor[0]]
    ay = {"t": 0.0, "c": 0.5, "b": 1.0}[anchor[1]]
    base.alpha_composite(lay, (round(x - lay.width * ax), round(y - lay.height * ay)))


def text(base, s, font_key, x, y, fill=WHITE, stroke_w=0, anchor="lt", scale=1.0, alpha=255):
    place(base, ink_layer(s, font_key, fill, stroke_w), x, y, anchor, scale, alpha)


def fit_size(s, font_path, start, max_w, stroke_w=0):
    size = start
    while size > 30:
        lay = ink_layer(s, (font_path, size), WHITE, stroke_w)
        if lay.width <= max_w:
            return size
        size -= 4
    return size


def chip(base, s, x, y, size=34, fg=YELLOW, bg=INK, border=None, anchor="lt", alpha=255,
         pad=(18, 12), font="text"):
    lay = ink_layer(s, ((f_text if font == "text" else f_display), size), fg)
    plate = Image.new("RGBA", (lay.width + 2 * pad[0], lay.height + 2 * pad[1]), bg + (238,))
    if border:
        ImageDraw.Draw(plate).rectangle([0, 0, plate.width - 1, plate.height - 1],
                                        outline=border, width=3)
    plate.alpha_composite(lay, pad)
    place(base, plate, x, y, anchor, alpha=alpha)
    return plate.size


# ------------------------------------------------------------- Annotationen
def draw_rect_progress(d, box, color, width, p):
    x0, y0, x1, y1 = box
    p = clamp(p)
    if p <= 0:
        return
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    lens = [abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1]) for i in range(4)]
    rem = sum(lens) * p
    for i in range(4):
        if rem <= 0:
            break
        a, b = pts[i], pts[i + 1]
        f = min(1.0, rem / lens[i])
        d.line([a, (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)], fill=color, width=width)
        rem -= lens[i]
    if p >= 1:
        for (px, py) in pts[:4]:
            d.rectangle([px - width / 2, py - width / 2, px + width / 2, py + width / 2], fill=color)


def draw_ring(d, c, rx, ry, color, width, p, start=-110):
    if p <= 0:
        return
    d.arc([c[0] - rx, c[1] - ry, c[0] + rx, c[1] + ry], start, start + 360 * clamp(p),
          fill=color, width=width)


def draw_arrow(d, p0, p1, color, width, p=1.0):
    p = clamp(p)
    if p <= 0:
        return
    x1 = p0[0] + (p1[0] - p0[0]) * p
    y1 = p0[1] + (p1[1] - p0[1]) * p
    d.line([p0, (x1, y1)], fill=color, width=width)
    ang = math.atan2(y1 - p0[1], x1 - p0[0])
    L = width * 3.6
    for s in (-0.5, 0.5):
        d.line([(x1, y1), (x1 - L * math.cos(ang + s), y1 - L * math.sin(ang + s))],
               fill=color, width=width)


# ----------------------------------------------------------------- Medien
class Media:
    """Quelle fuer das Inhaltsfenster. Koordinaten in 'Einheiten' (Original-Pixel)."""

    def __init__(self, path: Path, unit: float = 1.0):
        self.base = Image.open(path).convert("RGB")
        self.k = unit
        self.ow = self.base.width / unit          # Breite in Einheiten (fehlte -> span<20 stuerzte ab)
        self.oh = self.base.height / unit

    def source(self, ann=None):
        if ann is None:
            return self.base
        img = self.base.copy()
        ann(ImageDraw.Draw(img), self.k)
        return img

    def max_span(self):
        """Groesstes Fenster (Breite in Einheiten), das ins Inhaltsformat CW x CH passt."""
        return min(self.ow, self.oh * CW / CH)

    def window(self, span, fx, fy, anchor=(0.5, 0.5), source=None):
        """span = sichtbare Breite in Einheiten (Original-Pixel).

        Ist span < 20, wird es als ZOOMFAKTOR gelesen (1.0 = volle Breite).
        Sonst wuerde ein span=1.0 ein 1-Pixel-Fenster ergeben -> leere, weisse Flaeche.
        """
        src = source if source is not None else self.base
        if span < 20:
            span = self.ow * span                 # = self.base.width * span bei unit 1
        cw = span * self.k
        ch = cw * CH / CW
        if ch > self.base.height:
            ch = float(self.base.height)
            cw = ch * CW / CH
        if cw > self.base.width:
            cw = float(self.base.width)
            ch = cw * CH / CW
        x0 = min(max(fx * self.k - cw * anchor[0], 0.0), self.base.width - cw)
        y0 = min(max(fy * self.k - ch * anchor[1], 0.0), self.base.height - ch)
        img = src.resize((CW, CH), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
        return img, (x0, y0, cw, ch)


def to_screen(box, x, y, k):
    x0, y0, cw, ch = box
    return (CX0 + (x * k - x0) / cw * CW, CY0 + (y * k - y0) / ch * CH)


# ------------------------------------------------------- Gefahrenzone-Frame
def _chamfer_poly(x0, y0, x1, y1, c):
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c),
            (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def _frame_assets():
    inner = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(inner).polygon(_chamfer_poly(0, 0, CW - 1, CH - 1, ICHAMFER), fill=255)
    ring = Image.new("L", (W, H), 0)
    rd = ImageDraw.Draw(ring)
    rd.polygon(_chamfer_poly(0, HEADER_H, W - 1, CY1 + BAND - 1, CHAMFER), fill=255)
    rd.polygon(_chamfer_poly(CX0, CY0, CX1 - 1, CY1 - 1, ICHAMFER), fill=0)
    tex = Image.new("RGB", (W + 2 * STRIPE, H), C_HAZ)
    td = ImageDraw.Draw(tex)
    for x in range(-H, W + 2 * STRIPE, 2 * STRIPE):
        td.polygon([(x, H), (x + STRIPE, H), (x + STRIPE + H, 0), (x + H, 0)], fill=C_HAZ_DARK)
    scrim = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scrim)
    y0, y1, a = SCRIM_TOP
    for y in range(y0, y1):
        sd.line([(0, y), (CW, y)], fill=(0, 0, 0, int(a * (1 - (y - y0) / (y1 - y0)) ** 1.6)))
    y0, y1, a = SCRIM_BOT
    for y in range(y0, y1):
        sd.line([(0, y), (CW, y)], fill=(0, 0, 0, int(a * ((y - y0) / (y1 - y0)) ** 1.3)))
    glow = Image.new("L", (90, 90), 0)
    ImageDraw.Draw(glow).ellipse([27, 27, 63, 63], fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(12))
    vign = Image.radial_gradient("L").resize((CW, CH), Image.BILINEAR)   # 0 Mitte .. 255 Rand
    return inner, ring, tex, scrim, glow, vign


INNER_MASK, RING_MASK, HAZ_TEX, SCRIM, BEACON_GLOW, VIGNETTE = _frame_assets()
BEACON_IMG = Image.new("RGBA", BEACON_GLOW.size, C_BEACON + (255,))
_STATE = {"t": 0.0, "scene_t": 0.0, "style": "hazard"}


def draw_frame_style(frame, img, t, style="hazard", scene_t=0.0):
    """Inhalt in den Gefahrenzone-Frame setzen.

    Reihenfolge: 1 Grund  2 Inhalt + Scrims (abgeschraegte Maske)  3 Warnband (laeuft; zieht am
    Videostart in FRAME_IN s von links ein)  4 Innenkante (rot beim Szenenstart)  5 Ecken-Marker
    6 Blinklichter. Headline/Stempel/Chips zeichnet die Szene danach."""
    if img.size != (CW, CH):
        img = img.resize((CW, CH), Image.BICUBIC)
    frame.paste(C_BG + (255,), (0, HEADER_H, W, H))
    pane = img.convert("RGBA")
    pane.alpha_composite(SCRIM)
    frame.paste(pane, (CX0, CY0), INNER_MASK)
    if style == "none":
        return
    off = int(t * FPS * 2) % (2 * STRIPE)                 # ganzzahlig -> kein Flimmern
    band = HAZ_TEX.crop((off, 0, off + W, H))
    mask = RING_MASK
    p = ease_out(seg(t, 0.0, FRAME_IN))
    if p < 1.0:
        mask = Image.new("L", (W, H), 0)
        xw = int(W * p)
        if xw > 0:
            mask.paste(RING_MASK.crop((0, 0, xw, H)), (0, 0))
    frame.paste(band, (0, 0), mask)
    d = ImageDraw.Draw(frame)
    hot = 1 - ease_out(seg(scene_t, 0.0, HOT_EDGE))
    edge = tuple(int(C_EDGE[i] + (C_BEACON[i] - C_EDGE[i]) * hot) for i in range(3))
    poly = _chamfer_poly(CX0, CY0, CX1 - 1, CY1 - 1, ICHAMFER)
    d.line(poly + [poly[0]], fill=edge, width=4)
    L, th, ins = 64, 7, 30
    for (x, y, sx, sy) in ((CX0 + ins, CY0 + ins, 1, 1), (CX1 - ins, CY0 + ins, -1, 1),
                           (CX0 + ins, CY1 - ins, 1, -1), (CX1 - ins, CY1 - ins, -1, -1)):
        d.rectangle([min(x, x + sx * L), min(y, y + sy * th), max(x, x + sx * L),
                     max(y, y + sy * th)], fill=C_HAZ)
        d.rectangle([min(x, x + sx * th), min(y, y + sy * L), max(x, x + sx * th),
                     max(y, y + sy * L)], fill=C_HAZ)
    ph = (t * BEACON_HZ) % 1.0
    for i, cx in enumerate((22, W - 22)):
        cy = HEADER_H + 22
        on = (ph < 0.5) == (i == 0)                       # wechselseitig wie Blaulicht
        if on:
            frame.paste(BEACON_IMG, (cx - 45, cy - 45), BEACON_GLOW)
        d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=(255, 225, 225) if on else (90, 18, 18))


def draw_header(frame, t, tag, scene_t, code=None):
    """Kopfleiste 0..HEADER_H: rotes Beweis-Etikett links, Code-Etikett rechts."""
    ImageDraw.Draw(frame).rectangle([0, 0, W - 1, HEADER_H - 1], fill=C_BG)
    if tag:
        lay = ink_layer(tag, (f_text, 30), WHITE)
        th = 56
        ti = Image.new("RGBA", (lay.width + 84, th), C_BEACON + (255,))
        td = ImageDraw.Draw(ti)
        td.polygon([(18, th - 14), (37, 13), (56, th - 14)], fill=WHITE)   # Warndreieck
        td.rectangle([35, 24, 39, th - 24], fill=C_BEACON)
        ti.alpha_composite(lay, (70, (th - lay.height) // 2))
        s = ease_out(seg(scene_t, 0.0, 0.25))
        frame.alpha_composite(ti, (int(56 - (1 - s) * (ti.width + 60)), (HEADER_H - th) // 2))
    if code and t >= code.get("from", 1e9):
        s = ease_out(seg(t, code["from"], code["from"] + 0.3))
        lay = ink_layer(code["label"], (f_text, 30), C_HAZ)
        ci = Image.new("RGBA", (lay.width + 36, 56), (6, 6, 6, 255))
        ImageDraw.Draw(ci).rectangle([0, 0, ci.width - 1, 55], outline=C_HAZ, width=3)
        ci.alpha_composite(lay, (18, (56 - lay.height) // 2))
        frame.alpha_composite(ci, (int(W - 56 - ci.width + (1 - s) * (ci.width + 60)),
                                   (HEADER_H - 56) // 2))


def headline(frame, items, t, max_w=1012):
    """items = [[t_start, text, farbe]]; die zuletzt gestartete Zeile poppt als Overlay im Inhalt."""
    cur = None
    for it in items:
        if t >= it[0]:
            cur = it
    if cur is None:
        return None
    t0, s, col = cur
    color = COLORS.get(col, WHITE) if isinstance(col, str) else col
    size = fit_size(s, _fonts["display"], 150, max_w, 8)
    lay = ink_layer(s, (_fonts["display"], size), color, 8)
    sc = 1.0 + 0.16 * (1 - ease_out_back(seg(t - t0, 0.0, 0.24)))
    # G4: der Pop darf die Zeile nicht über den Bildrand schieben. fit_size()
    # begrenzt nur die Ruhebreite; die Skalierung wächst um den linken Anker.
    sc = min(sc, (W - 6 - 34) / max(1, lay.width))
    place(frame, lay, 34, HEAD_BASE, "lb", scale=sc, alpha=255)
    return (34, HEAD_BASE - lay.height, 34 + lay.width, HEAD_BASE)


def content(frame, img):
    draw_frame_style(frame, img, _STATE["t"], _STATE["style"], _STATE["scene_t"])


def ts_pill(frame, x, y, label):
    lay = ink_layer(label, (f_text, 34), WHITE)
    h = lay.height + 24
    pill = Image.new("RGBA", (lay.width + 78, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle([0, 0, pill.width - 1, h - 1], radius=h // 2, fill=C_BEACON + (245,))
    pd.polygon([(24, h / 2 - 12), (24, h / 2 + 12), (44, h / 2)], fill=WHITE)   # Play-Dreieck
    pill.alpha_composite(lay, (56, (h - lay.height) // 2))
    frame.alpha_composite(pill, (int(x), int(y)))


def quote_card(frame, quote, bottom_y, alpha=255):
    """Belegzitat (woertlich), max. 2 Zeilen, gelber Balken links, unten verankert."""
    f = f_text(44)
    tmp = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    lines, cur = [], ""
    for w in quote.split():
        nxt = (cur + " " + w).strip()
        if cur and tmp.textlength(nxt, font=f) > CW - 130:
            lines.append(cur)
            cur = w
        else:
            cur = nxt
    lines.append(cur)
    if len(lines) > 2:
        lines = [lines[0], lines[1] + " …"]
    lays = [ink_layer(l, (f_text, 44), WHITE) for l in lines]
    gap = 14
    hh = sum(l.height for l in lays) + gap * (len(lays) - 1)
    card = Image.new("RGBA", (max(l.width for l in lays) + 76, hh + 48), C_BG + (230,))
    ImageDraw.Draw(card).rectangle([0, 0, 9, card.height], fill=C_HAZ)
    y = 24
    for l in lays:
        card.alpha_composite(l, (46, y))
        y += l.height + gap
    place(frame, card, CX0 + 30, bottom_y, "lb", alpha=alpha)


# ------------------------------------------------------------- Untertitel
class Subtitles:
    """Untertitel aus ASR-Worttimings. Platte = gemessene Text-Bbox -> deckungsgleich."""

    def __init__(self, words_json: Path, max_words=2, max_chars=17, vo_end=None):
        data = json.loads(Path(words_json).read_text())
        end = vo_end if vo_end else max(w["end"] for w in data["words"])
        words = [w for w in data["words"] if w["word"].strip() and w["end"] <= end]
        chunks, cur = [], []
        for w in words:
            cur.append(w)
            if len(cur) >= max_words or sum(len(x["word"]) + 1 for x in cur) >= max_chars:
                chunks.append(cur)
                cur = []
        if cur:
            chunks.append(cur)
        self.items = []
        for ci, ch in enumerate(chunks):
            nxt = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else end
            for i, w in enumerate(ch):
                stop = (ch[i + 1]["start"] - 0.02) if i + 1 < len(ch) else min(w["end"] + 0.18, nxt - 0.02)
                if stop <= w["start"] + 0.05:
                    continue
                self.items.append((w["start"], stop, tuple(x["word"].strip() for x in ch), i))

    @lru_cache(maxsize=256)
    def card(self, words, idx):
        f = f_display(76)
        stroke = 6
        tmp = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
        gap = tmp.textlength(" ", font=f) + 4
        widths = [tmp.textlength(w, font=f) for w in words]
        total = sum(widths) + gap * (len(words) - 1)
        canvas = Image.new("RGBA", (int(total) + 120, 220), (0, 0, 0, 0))
        cd = ImageDraw.Draw(canvas)
        x = 60.0
        for j, (w, wd) in enumerate(zip(words, widths)):
            cd.text((x, 150), w, font=f, fill=YELLOW if j == idx else WHITE, anchor="ls",
                    stroke_width=stroke, stroke_fill=BLACK)   # gemeinsame Grundlinie
            x += wd + gap
        ink = canvas.crop(canvas.getchannel("A").getbbox())
        if ink.width > 960:
            ink = ink.resize((960, round(ink.height * 960 / ink.width)), Image.LANCZOS)
        px, py = 30, 20
        card = Image.new("RGBA", (ink.width + 2 * px, ink.height + 2 * py), (0, 0, 0, 0))
        # Der Rahmen muss hell sein: nur so ist die Platte im fertigen Video von einem
        # dunklen Hintergrund messbar (Preflight subs.alignment, Gate G4).
        ImageDraw.Draw(card).rounded_rectangle([0, 0, card.width - 1, card.height - 1], radius=14,
                                               fill=INK + (240,), outline=(255, 255, 255, 245), width=3)
        card.alpha_composite(ink, (px, py))
        return card

    def draw(self, frame, t):
        active = [s for s in self.items if s[0] <= t < s[1]]
        if not active:
            return
        st, en, words, idx = active[0]
        sc = 1.0 + 0.06 * (1 - ease_out((t - st) / 0.14))
        place(frame, self.card(words, idx), W / 2, SUB_CY, "cc", scale=sc)



def draw_source_timeline(frame, src):
    """Quell-Timeline: zeigt, WO im Originalvideo wir sind (G8-Beleg)."""
    if not src or not src.get("duration") or not src.get("span"):
        return
    d = ImageDraw.Draw(frame)
    total = float(src["duration"])
    a0, a1 = src["span"]
    bx0, bw_, by = CX0 + 60, CW - 120, CY1 - 44
    d.rectangle([bx0, by, bx0 + bw_, by + 8], fill=(90, 90, 90))
    d.rectangle([bx0 + bw_ * a0 / total, by, bx0 + bw_ * a1 / total, by + 8], fill=C_HAZ)


# ----------------------------------------------------------------- Szenen
class Engine:
    def __init__(self, storyboard: dict, workdir: Path):
        self.sb = storyboard
        self.meta = storyboard["meta"]
        self.work = workdir
        load_fonts(self.meta)
        self.subs = Subtitles(self.work / self.meta["words"],
                              vo_end=self.meta.get("vo_end"))
        self.media: dict[str, Media] = {}
        self._stamp_cache: dict = {}

    def media_for(self, spec) -> Media:
        key = spec["path"]
        if key not in self.media:
            self.media[key] = Media(self.work / key, unit=spec.get("unit", 1.0))
        return self.media[key]

    def draw_stamp(self, frame, stamp, t, default_y=0.67):
        k = t - stamp["at"]
        if k < 0:
            return
        place(frame, self.stamp_layer(stamp), W * stamp.get("x", 0.5), H * stamp.get("y", default_y),
              "cc", scale=1.0 + 0.7 * (1 - ease_out(seg(k, 0, 0.13))),
              alpha=int(255 * ease_out(seg(k, 0, 0.06))))

    # -------------------------------------------------- Szenen-Kind: hero
    def scene_hero(self, frame, t, T, sc):
        med = self.media_for(sc["media"])
        m = sc["media"]
        stamp = sc.get("stamp")
        pr = ease_out(seg(t, stamp["at"] - 0.4, stamp["at"] - 0.06)) if stamp else 0

        def ann(d, k):
            if stamp and sc.get("stamp_ring"):
                r = sc["stamp_ring"]
                draw_ring(d, (r["center"][0] * k, r["center"][1] * k), r["rx"] * k, r["ry"] * k,
                          RED, int(r.get("width", 11) * k), pr)

        span = m.get("span", 1290)
        span_to = m.get("span_to", span)
        fx = m.get("fx", 645)
        fx_to = m.get("fx_to", fx)
        fy = m.get("fy", 0)
        anchor = tuple(m.get("anchor", (0.5, 0.5)))
        dur = m.get("dur", 2.4)
        punch = m.get("punch")
        if punch:
            sp = span * (1 + 0.30 * (1 - ease_out(seg(t, 0, 0.45))))
            sp = sp + (span_to - span) * ease_in_out(seg(t, 0.45, dur))
        else:
            sp = span + (span_to - span) * ease_in_out(seg(t, 0, dur))
        view, box = med.window(sp,
            fx + (fx_to - fx) * ease_in_out(seg(t, 0, dur)),
            fy, anchor, source=med.source(ann))
        content(frame, view)
        c = sc.get("chip")
        if c:
            s = ease_out(seg(t, c["at"], c["at"] + 0.2))
            if s > 0:
                lay = ink_layer(c["text"], (f_display, c.get("size", 112)), YELLOW, 6)
                plate = Image.new("RGBA", (lay.width + 44, lay.height + 36), (6, 6, 6, 235))
                plate.alpha_composite(lay, (22, 18))
                frame.alpha_composite(plate, (int(CX0 + c.get("x", 34) - (1 - s) * (plate.width + 60)),
                                             CY0 + c.get("y", HEAD_BASE - CY0 + 28)))
        if stamp:
            self.draw_stamp(frame, stamp, t)
        hb = headline(frame, sc.get("headlines", []), t)
        if sc.get("strikethrough") and hb:
            ps = ease_out(seg(t, sc["strikethrough"], sc["strikethrough"] + 0.22))
            if ps > 0:
                d = ImageDraw.Draw(frame)
                ym = (hb[1] + hb[3]) / 2
                d.line([(hb[0] - 10, ym + 12), (hb[0] - 10 + (hb[2] - hb[0] + 20) * ps, ym - 12)],
                       fill=RED, width=16)
        return sc.get("tag", "")

    def stamp_layer(self, stamp):
        key = (stamp["text"], stamp.get("size", 168), stamp.get("deg", 8))
        if key in self._stamp_cache:
            return self._stamp_cache[key]
        lay = ink_layer(stamp["text"], (f_display, stamp.get("size", 168)), RED)
        pad = 28
        st = Image.new("RGBA", (lay.width + 2 * pad, lay.height + 2 * pad), (255, 255, 255, 60))
        ImageDraw.Draw(st).rectangle([0, 0, st.width - 1, st.height - 1], outline=RED, width=12)
        st.alpha_composite(lay, (pad, pad))
        out = st.rotate(stamp.get("deg", 8), resample=Image.BICUBIC, expand=True)
        self._stamp_cache[key] = out
        return out

    # ------------------------------------------------ Szenen-Kind: danger (Hook)
    def scene_danger(self, frame, t, T, sc):
        """Hook: Bild ab Frame 1 vollflaechig, Punch je Text-Schlag, roter Rand-Puls, Ring, Stempel.

        chops = [[t, text, farbe(, groesse)], ...]; mit dem Stempel verschwindet der letzte Schlag.
        media.span: >= 20 Breite in Einheiten, < 20 Anteil der Bildbreite (kleiner = naeher)."""
        med = self.media_for(sc["media"])
        m = sc["media"]
        chops = sorted(sc.get("chops", []), key=lambda c: c[0])
        stamp = sc.get("stamp")
        ring = sc.get("ring")
        past = [c for c in chops if t >= c[0]]
        last = past[-1][0] if past else 0.0
        step = (len(past) - 1 + ease_out(seg(t, last, last + 0.12))) if past else 0.0
        drift = ease_in_out(seg(t, 0, m.get("dur", T)))
        f = (1 + m.get("punch_step", 0.05) * step) * (1 + 0.04 * drift)
        # span = Zoomfaktor auf den Cover-Ausschnitt (1.0 = fuellt den Inhalt).
        # Der Cover-Ausschnitt ist hoehenbegrenzt: cover_w = min(breite, hoehe*CW/CH).
        cover_w = min(med.ow, med.oh * CW / CH)
        sp = cover_w / f                                  # in Einheiten; kleineres Fenster = naeher
        fx0 = m.get("fx", med.ow / 2)
        fx = fx0 + (m.get("fx_to", fx0) - fx0) * drift
        fy = m.get("fy", med.oh / 2)

        def ann(d, k):
            p = ease_out(seg(t, ring.get("at", 0.0), ring.get("at", 0.0) + ring.get("dur", 0.35)))
            draw_ring(d, (ring["center"][0] * k, ring["center"][1] * k), ring["rx"] * k,
                      ring["ry"] * k, RED, int(ring.get("width", 11) * k), p)

        if sc.get("fit", "cover") == "card":
            # Ganzes Quellbild als Karte im Gefahrenzone-Frame (der Nutzerwunsch:
            # "Hauptinhalte in FRAMES anzeigen"). Hintergrund = unscharf + abgedunkelt.
            full = med.base
            scale = CW / full.width
            card_h = max(1, round(full.height * scale))
            if card_h > CH:
                card_h = CH
                scale = CH / full.height
            bw = min(float(full.width), full.height * CW / CH)
            bg = full.resize((CW, CH), Image.BILINEAR,
                             box=((full.width - bw) / 2, 0, (full.width + bw) / 2, full.height))
            bg = Image.blend(bg.filter(ImageFilter.GaussianBlur(26)),
                             Image.new("RGB", (CW, CH), C_BG), 0.55)
            view = bg
            card = full.resize((CW, max(1, round(full.height * scale))), Image.BICUBIC)
            view.paste(card, (0, int(sc.get("card_y", max(0, (CH - card_h) // 2 - 120)))))
        else:
            view, _ = med.window(sp, fx, fy, tuple(m.get("anchor", (0.5, 0.5))),
                                 source=med.source(ann) if ring else None)
        pulse = sc.get("pulse", 0.09)
        lvl = 0.22 + pulse * (1 + math.sin(t * 2 * math.pi * 2.0))     # roter Rand-Puls, 2 Hz
        view = Image.composite(Image.new("RGB", (CW, CH), RED), view,
                               VIGNETTE.point(lambda v: int(v * lvl)))
        k = t - last
        if past and k < 0.08:                                           # Blitz je Schlag
            view = Image.blend(view, Image.new("RGB", (CW, CH), WHITE), 0.35 * (1 - k / 0.08))
        content(frame, view)
        if sc.get("timestamp"):
            ts_pill(frame, CX0 + 30, HEAD_BASE + 26, sc["timestamp"])
        stamped = stamp is not None and t >= stamp["at"]
        if past and not stamped:
            c = past[-1]
            col = COLORS.get(c[2], WHITE) if len(c) > 2 else WHITE
            size = fit_size(c[1], _fonts["display"], c[3] if len(c) > 3 else 190, CW - 60, 10)
            lay = ink_layer(c[1], (_fonts["display"], size), col, 10)
            s_ = 1.0 + 0.45 * (1 - ease_out(seg(k, 0, 0.12)))
            s_ = min(s_, (CW - 20) / max(1, lay.width))                 # Schlag bleibt im Inhalt
            place(frame, lay, W / 2, CY0 + CH * sc.get("chop_y", 0.44), "cc", scale=s_)
        if stamped:
            self.draw_stamp(frame, stamp, t, default_y=0.5)
        if sc.get("quote"):
            quote_card(frame, sc["quote"], 1440, alpha=int(255 * ease_out(seg(t, 0.25, 0.55))))
        draw_source_timeline(frame, sc.get("source"))
        headline(frame, sc.get("headlines", []), t)
        return sc.get("tag", "")

    # ----------------------------------------------- Szenen-Kind: evidence
    def scene_evidence(self, frame, t, T, sc):
        med = self.media_for(sc["media"])
        m = sc["media"]
        anns = sc.get("annotations", [])
        dur = m.get("dur", T)

        def ann(d, k):
            for a in anns:
                p = ease_out(seg(t, a.get("at", 0), a.get("at", 0) + a.get("dur", 0.8)))
                if p <= 0:
                    continue
                col = COLORS.get(a.get("color", "yellow"), YELLOW)
                if a["type"] == "rect":
                    draw_rect_progress(d, [a["box"][0] * k, a["box"][1] * k, a["box"][2] * k,
                                           a["box"][3] * k], col, int(a.get("width", 8) * k), p)
                elif a["type"] == "ring":
                    draw_ring(d, (a["center"][0] * k, a["center"][1] * k), a["rx"] * k, a["ry"] * k,
                              col, int(a.get("width", 8) * k), p)
                elif a["type"] == "arrow":
                    draw_arrow(d, (a["from"][0] * k, a["from"][1] * k),
                               (a["to"][0] * k, a["to"][1] * k), col, int(a.get("width", 9) * k), p)

        span = m.get("span", 1290)
        span_to = m.get("span_to", span)
        fx = m.get("fx", 645)
        fy = m.get("fy", 0)
        fy_to = m.get("fy_to", fy)
        anchor = tuple(m.get("anchor", (0.5, 0.5)))
        view, box = med.window(
            span + (span_to - span) * ease_in_out(seg(t, 0, dur)),
            fx, fy + (fy_to - fy) * ease_in_out(seg(t, 0, dur)), anchor, source=med.source(ann))
        content(frame, view)
        for a in anns:
            if a["type"] != "label":
                continue
            p = ease_out(seg(t, a.get("at", 0), a.get("at", 0) + a.get("dur", 0.5)))
            if p <= 0:
                continue
            x, y = to_screen(box, a["at_xy"][0], a["at_xy"][1], med.k)
            chip(frame, a["text"], x, y, size=a.get("size", 32),
                 fg=COLORS.get(a.get("color", "yellow"), YELLOW), bg=(6, 6, 6),
                 border=a.get("border"), anchor="rc", alpha=int(255 * p))
        headline(frame, sc.get("headlines", []), t)
        return sc.get("tag", "")

    # ------------------------------------------------- Szenen-Kind: clip (Video-Frame)
    def scene_clip(self, frame, t, T, sc):
        """Video-Frame im Gefahrenzone-Frame.

        fit='cover' (Standard): Ausschnitt fuellt den Inhalt. fit='card': ganzes 16:9-Bild auf
        unscharfem Grund. media.span/span_to = Zoom (1.0 = groesstes Fenster, groesser = naeher).
        Zeitstempel-Pille, Belegzitat und Quell-Timeline als Overlay."""
        med = self.media_for(sc["media"])
        m = sc["media"]
        dur = m.get("dur", T)
        z0 = m.get("span", 1.0)
        z1 = m.get("span_to", z0)
        z = z0 + (z1 - z0) * ease_in_out(seg(t, 0, dur))
        if m.get("punch"):
            z *= 1 + 0.28 * (1 - ease_out(seg(t, 0, 0.45)))
        fx = m.get("fx", med.ow / 2)
        fy = m.get("fy", med.oh / 2)
        if sc.get("fit", "cover") == "cover":
            view, _ = med.window(max(20.0, med.max_span() / max(z, 0.05)), fx, fy)
        else:
            full = med.base
            cw = full.width / z
            ch = cw * 9 / 16
            if ch > full.height:
                ch = float(full.height)
                cw = ch * 16 / 9
            x0 = min(max(fx * med.k - cw / 2, 0.0), full.width - cw)
            y0 = min(max(fy * med.k - ch / 2, 0.0), full.height - ch)
            bw = min(float(full.width), full.height * CW / CH)
            view = full.resize((CW, CH), Image.BILINEAR,
                               box=((full.width - bw) / 2, 0, (full.width + bw) / 2, full.height))
            view = Image.blend(view.filter(ImageFilter.GaussianBlur(26)),
                               Image.new("RGB", (CW, CH), C_BG), 0.5)
            card_h = round(CW * ch / cw)
            view.paste(full.resize((CW, card_h), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch)),
                       (0, sc.get("card_y", 420)))
        content(frame, view)
        if sc.get("timestamp"):
            ts_pill(frame, CX0 + 30, HEAD_BASE + 26, sc["timestamp"])
        if sc.get("quote"):
            quote_card(frame, sc["quote"], 1440, alpha=int(255 * ease_out(seg(t, 0.25, 0.55))))
        draw_source_timeline(frame, sc.get("source"))
        c = sc.get("chip")
        if c:
            s_ = ease_out(seg(t, c["at"], c["at"] + 0.2))
            if s_ > 0:
                lay = ink_layer(c["text"], (f_display, c.get("size", 56)), YELLOW, 6)
                plate = Image.new("RGBA", (lay.width + 44, lay.height + 36), (6, 6, 6, 235))
                plate.alpha_composite(lay, (22, 18))
                frame.alpha_composite(plate, (int(CX0 + c.get("x", 34) - (1 - s_) * 60),
                                              int(CY0 + c.get("y", 300))))
        if sc.get("stamp"):
            self.draw_stamp(frame, sc["stamp"], t, default_y=0.6)
        headline(frame, sc.get("headlines", []), t)
        return sc.get("tag", "")

    # -------------------------------------------------- Szenen-Kind: coupon
    def scene_coupon(self, frame, t, T, sc):
        code = sc.get("code", "USC20")
        sub = sc.get("sub", "−20 % AUF DEINEN REPORT")
        cta = sc.get("cta", "")
        pane = Image.new("RGB", (CW, CH), C_BG)
        pane.paste(C_HAZ, (0, 0, CW, CH), VIGNETTE.point(lambda v: int((255 - v) * 0.30)))
        content(frame, pane)
        y_c = sc.get("y", CY0 + int(CH * 0.42))
        pop = ease_out_back(seg(t, 0.0, 0.4))
        lay = ink_layer(code, (f_display, sc.get("size", 300)), BLACK)
        plate = Image.new("RGBA", (lay.width + 120, lay.height + 190), YELLOW + (255,))
        pd = ImageDraw.Draw(plate)
        # Perforation
        for x in range(0, plate.width, 26):
            pd.ellipse([x, 6, x + 8, 14], fill=(20, 20, 20, 255))
            pd.ellipse([x, plate.height - 14, x + 8, plate.height - 6], fill=(20, 20, 20, 255))
        plate.alpha_composite(lay, (60, 40))
        sl = ink_layer(sub, (f_text, 40), BLACK)
        plate.alpha_composite(sl, (60, plate.height - 80))
        place(frame, plate, W / 2, y_c, "cc", scale=0.85 + 0.15 * pop)
        if cta:
            b = ease_out(seg(t, 0.35, 0.75))
            text(frame, cta, (f_text, 34), W / 2, y_c + 260, WHITE, anchor="ct", alpha=int(255 * b))
        headline(frame, sc.get("headlines", []), t)
        return sc.get("tag", "")

    # ---------------------------------------------------------- Dispatcher
    def draw_scene(self, frame, t):
        style = self.meta.get("frame_style", "hazard")
        for sc in self.sb["scenes"]:
            t0 = sc.get("start", 0.0)
            t1 = sc.get("end")
            if t1 is None:
                nxt = [s.get("start", 0.0) for s in self.sb["scenes"] if s.get("start", 0.0) > t0]
                if nxt:
                    t1 = min(nxt)
                elif sc.get("kind") == "danger":
                    t1 = t0 + HOOK_DUR
                else:
                    t1 = self.meta["duration"]
            if not (t0 <= t < t1):
                continue
            _STATE.update(t=t, scene_t=t - t0, style=sc.get("frame_style", style))
            fn = getattr(self, "scene_" + sc.get("kind", "evidence"), self.scene_evidence)
            tag = fn(frame, t - t0, t1 - t0, sc)
            draw_header(frame, t, tag, t - t0, self.meta.get("code"))
            return
        _STATE.update(t=t, scene_t=0.0)
        draw_frame_style(frame, Image.new("RGB", (CW, CH), C_BG), t, style, 0.0)
        draw_header(frame, t, "", 0.0, self.meta.get("code"))

    def render_frame(self, t):
        frame = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        self.draw_scene(frame, t)
        self.subs.draw(frame, t)
        return frame.convert("RGB")

    def render(self, out_path: Path):
        dur = float(self.meta["duration"])
        ff = self.meta.get("ffmpeg", "ffmpeg")
        cmd = [ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", str(self.meta.get("fps", FPS)), "-i", "-",
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
               str(out_path)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        n = int(dur * self.meta.get("fps", FPS))
        for i in range(n):
            t = i / self.meta.get("fps", FPS)
            proc.stdin.write(self.render_frame(t).tobytes())
        proc.stdin.close()
        proc.wait()


def main(argv):
    if len(argv) < 2:
        print("usage: render.py <storyboard.json> [workdir] [--stills t1,t2,...]")
        return 2
    sb_path = Path(argv[1]).resolve()
    storyboard = json.loads(sb_path.read_text())
    rest = [a for a in argv[2:] if not a.startswith("--stills")]
    workdir = Path(rest[0]).resolve() if rest else sb_path.parent
    eng = Engine(storyboard, workdir)
    stills = [a for a in argv[2:] if a.startswith("--stills")]
    if stills:                                            # QA: einzelne Zeitpunkte als PNG
        out_dir = workdir / "qa" / "stills"
        out_dir.mkdir(parents=True, exist_ok=True)
        for ts in stills[0].split("=", 1)[1].split(","):
            eng.render_frame(float(ts)).save(out_dir / f"still_{float(ts):06.2f}.png")
        print("stills:", out_dir)
        return 0
    out = workdir / storyboard["meta"].get("out", "out/short.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    eng.render(out)
    print("gerendert:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
