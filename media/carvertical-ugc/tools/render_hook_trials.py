#!/usr/bin/env python3
"""Rendert 1,5-s-Stummtests aus den P1-Boards. Keine finalen Shorts.

Das Bildmaterial kommt aus den Kampagnen-Belegen; V1 zusätzlich aus einem echten
Creator-Take. V1 bleibt gesperrt, solange die Aufnahme fehlt; KI-/Stock-Gesichter
sind kein Ersatz. Echtheit/Einwilligung müssen Menschen prüfen.
Die Previews haben bewusst keine erfundene VO oder Pseudo-ASR und dürfen nicht als
finaler MP4-Preflight ausgegeben werden. Sie sind zum stummen Thumbstop-Vergleich.

    python3 tools/render_hook_trials.py --all
    python3 tools/render_hook_trials.py --short cv5 --variant v3 --size 1080x1920
"""
from __future__ import annotations

import argparse
import io
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

# Aufruf aus einem beliebigen Arbeitsverzeichnis; keine fremden Dateien laden.
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
FONTS = REPO / "skill/assets/fonts"
FALLBACKS = [Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
             Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
             Path("C:/Windows/Fonts/arialbd.ttf")]
SIZE = (720, 1280)
FPS = 30
DURATION = 1.5
PALETTE = {
    "cv5": {"accent": (255, 222, 26), "signal": (255, 66, 52), "ink": (13, 13, 20)},
    "app": {"accent": (116, 255, 200), "signal": (255, 210, 32), "ink": (4, 28, 32)},
    "yt": {"accent": (225, 248, 68), "signal": (255, 74, 74), "ink": (14, 11, 29)},
}


def clamp(x: float, lo: float = 0, hi: float = 1) -> float:
    return min(hi, max(lo, x))


def ease(x: float) -> float:
    return 1 - (1 - clamp(x)) ** 3


def pulse(x: float) -> float:
    # Bei t=0 bereits sichtbar, dann elastischer Punch und schnelle Landung.
    return 1 + 0.10 * math.exp(-7 * max(0.0, x)) * math.sin(16 * max(0.0, x))


def font(size: int, display: bool = True) -> ImageFont.FreeTypeFont:
    preferred = FONTS / ("Anton-Regular.ttf" if display else "Montserrat-ExtraBold.ttf")
    candidate = next((p for p in [preferred, *FALLBACKS] if p.is_file()), None)
    return ImageFont.truetype(str(candidate), max(10, size)) if candidate else ImageFont.load_default(size=max(10, size))


def ink(text: str, width: int, size: int, color: tuple[int, int, int],
        *, border: int = 0, display: bool = True) -> Image.Image:
    """Text als beschnittene Ebene; kein Clipping am Rand oder blindes Font-Offset."""
    while True:
        f = font(size, display)
        bb = f.getbbox(text, stroke_width=border)
        if bb[2] - bb[0] <= width or size <= 18:
            break
        size -= 2
    pad = border + 8
    image = Image.new("RGBA", (bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2))
    d = ImageDraw.Draw(image)
    d.text((pad - bb[0], pad - bb[1]), text, font=f, fill=color,
           stroke_width=border, stroke_fill=(5, 7, 10))
    return image.crop(image.getchannel("A").getbbox())


def paste_center(frame: Image.Image, layer: Image.Image, x: float, y: float,
                 *, scale: float = 1.0, shadow: bool = False) -> None:
    if scale != 1:
        layer = layer.resize((max(1, round(layer.width * scale)), max(1, round(layer.height * scale))),
                             Image.Resampling.LANCZOS)
    xy = (round(x - layer.width / 2), round(y - layer.height / 2))
    if shadow:
        sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        sh.putalpha(layer.getchannel("A").filter(ImageFilter.GaussianBlur(max(4, layer.width // 70))))
        frame.alpha_composite(sh, (xy[0] + 10, xy[1] + 18))
    frame.alpha_composite(layer, xy)


class Trial:
    """Motion-Templates lesen Text/Beleg/Zeit aus dem Konzept, nie Marketing-Claims aus Code."""

    def __init__(self, short: str, variant: str, size: tuple[int, int] = SIZE):
        from check_hook_storyboards import ConceptError, validate

        if short not in PALETTE or variant not in ("v1", "v2", "v3"):
            raise ConceptError("Unbekannter Short/Variante")
        self.short, self.variant = short, variant
        self.w, self.h = size
        if self.w < 240 or self.h * 9 != self.w * 16:
            raise ValueError("9:16 mit mindestens 240 Pixel Breite nötig")
        self.s = self.w / 720
        self.color = PALETTE[short]
        self.board = json.loads((ROOT / f"hooks/storyboard_{short}_{variant}.json").read_text(encoding="utf-8"))
        pending = validate(self.board, f"storyboard_{short}_{variant}.json")
        if pending:
            raise ConceptError(f"V1 braucht einen echten Creator-Take: {', '.join(pending)}")
        self.creator_frames = self._load_creator() if variant == "v1" else []
        self.images = {name: Image.open(ROOT / name).convert("RGB")
                       for beat in self.board["beats"][:2] for name in beat["images"]}
        # Ein inhaltlich anderer Hintergrund je Konzept, aber immer die echte Bildquelle.
        self.backgrounds: dict[str, Image.Image] = {}
        for name, source in self.images.items():
            if short == "app":
                source = source.crop((0, 380, source.width, 1410))
            cover = ImageOps.fit(source, (self.w + 150, self.h + 200), Image.Resampling.LANCZOS,
                                 centering=(0.47, 0.56))
            self.backgrounds[name] = cover
        self.blurs = {name: im.filter(ImageFilter.GaussianBlur(round(30 * self.s)))
                      for name, im in self.backgrounds.items()}
        self.proofs = {
            "cv5": ((50, 790, 1100, 1180) if variant == "v2" else (70, 800, 770, 980)),
            "app": ((35, 610, 1050, 1370) if variant == "v2" else (35, 635, 1050, 1040)),
            "yt": ((0, 0, 1280, 720) if variant == "v2" else (0, 0, 1280, 720)),
        }
        self.source_names = {"cv5": "MUSTERBERICHT · VW PASSAT", "app": "EINFACH HAUSEN · BELEG",
                             "yt": "DPCCARS · ORIGINALFRAME"}

    def _load_creator(self) -> list[bytes]:
        """Nur tatsächliche, vom Creator gelieferte Videoframes; kein Avatar-Ersatz."""
        try:
            from imageio_ffmpeg import read_frames
        except ImportError as exc:
            raise RuntimeError("imageio-ffmpeg fehlt für echte Creator-Aufnahmen") from exc
        asset = ROOT / self.board["beats"][0]["face"]["asset"]
        reader = read_frames(str(asset), pix_fmt="rgb24", output_params=[
            "-vf", f"fps={FPS},scale={self.w}:{self.h}:force_original_aspect_ratio=increase,crop={self.w}:{self.h}",
            "-frames:v", str(round(FPS * DURATION))])
        frames: list[bytes] = []
        try:
            meta = next(reader)
            width, height = meta["size"]
            if (width, height) != (self.w, self.h):
                raise ValueError(f"Creator-Take liefert {width}x{height}, erwartet {self.w}x{self.h}")
            for raw in reader:
                buf = io.BytesIO()
                Image.frombytes("RGB", (width, height), raw).save(buf, format="JPEG", quality=91)
                frames.append(buf.getvalue())
        finally:
            reader.close()
        if len(frames) != round(DURATION * FPS):
            raise ValueError(f"Creator-Take zu kurz: {len(frames)} Frames statt {round(DURATION * FPS)}")
        return frames

    def px(self, number: float) -> int:
        return round(number * self.s)

    def background(self, source: str, t: float, *, blur: bool, dark: float) -> Image.Image:
        # Die Kamera läuft schon im ersten Frame; keine Standbildtafel hinter Typografie.
        oversize = self.blurs[source] if blur else self.backgrounds[source]
        margin_x = (oversize.width - self.w) // 2
        margin_y = (oversize.height - self.h) // 2
        dx = round(self.px(22) * math.sin(t * 1.9))
        dy = round(self.px(25) * t)
        x, y = margin_x + dx, margin_y - dy
        result = oversize.crop((x, y, x + self.w, y + self.h)).convert("RGBA")
        shade = Image.new("RGBA", result.size, self.color["ink"] + (round(255 * dark),))
        result.alpha_composite(shade)
        return result

    def line(self, base: Image.Image, x0: int, y0: int, x1: int, y1: int,
             *, color: tuple[int, int, int] | None = None, width: int = 8) -> None:
        ImageDraw.Draw(base).line((self.px(x0), self.px(y0), self.px(x1), self.px(y1)),
                                  fill=(color or self.color["accent"]) + (255,), width=self.px(width))

    def question(self, frame: Image.Image, text: str, t: float) -> None:
        # Senderlose redaktionelle Frage: bewusst KEIN erfundener Chat/Avatar.
        accent = self.color["accent"]
        lay = ink(text, self.px(580), self.px(115), self.color["ink"], display=True)
        padx, pady = self.px(34), self.px(30)
        badge = Image.new("RGBA", (lay.width + 2 * padx, lay.height + 2 * pady))
        ImageDraw.Draw(badge).rounded_rectangle((0, 0, badge.width - 1, badge.height - 1),
                                                radius=self.px(18), fill=accent + (255,))
        badge.alpha_composite(lay, (padx, pady))
        wobble = round(self.px(36) * (1 - ease(t / 0.15)))
        # Sichtbarkeit ab Frame 0; springt nur in die finale Position.
        paste_center(frame, badge, self.w / 2 - wobble, self.px(290), shadow=True)
        d = ImageDraw.Draw(frame)
        if t > 0.18:
            p = ease((t - 0.18) / 0.22)
            d.line((self.px(125), self.px(414), self.px(125 + 480 * p), self.px(405)),
                   fill=self.color["signal"] + (255,), width=self.px(12))

    def number(self, frame: Image.Image, text: str, t: float, *, small: bool) -> None:
        width = self.px(620) if small else self.px(640)
        size = self.px(330 if small else (680 if len(text) == 1 else 520))
        layer = ink(text, width, size, self.color["accent"], border=self.px(5))
        scale = (0.96 + 0.04 * ease(t / 0.25)) if small else (0.93 + 0.07 * ease(t / 0.22)) * pulse(t)
        y = self.px(278 if small else 505)
        paste_center(frame, layer, self.w / 2 + self.px(8 * math.sin(7 * t)), y,
                     scale=scale, shadow=True)

    def panel(self, frame: Image.Image, image: str, crop: tuple[int, int, int, int],
              x: int, y: int, width: int, *, slide: float = 0.0) -> tuple[int, int, int, int]:
        original = self.images[image].crop(crop)
        w = self.px(width)
        h = round(original.height * w / original.width)
        fitted = original.resize((w, h), Image.Resampling.LANCZOS).convert("RGBA")
        ox = self.px(x) + round(self.px(slide))
        oy = self.px(y)
        # Starke, einfache Papier-Metapher nur für echte Belege, nicht als Deko-Frame.
        shadow = Image.new("RGBA", (w + self.px(20), h + self.px(20)), (0, 0, 0, 100))
        frame.alpha_composite(shadow, (ox + self.px(16), oy + self.px(18)))
        frame.alpha_composite(fitted, (ox, oy))
        ImageDraw.Draw(frame).rectangle((ox - 2, oy - 2, ox + w + 1, oy + h + 1),
                                        outline=self.color["accent"] + (255,), width=self.px(5))
        return ox, oy, w, h

    def credit(self, frame: Image.Image, beat: dict) -> None:
        text = self.source_names[self.short]
        if self.short == "yt":
            text += "  ·  " + beat["source_time"]
        lay = ink(text, self.px(620), self.px(33), (247, 249, 246), display=False)
        base_y = self.px(1201)
        ImageDraw.Draw(frame).rectangle((self.px(38), base_y - self.px(20),
                                         self.w - self.px(38), base_y + self.px(48)),
                                        fill=(10, 12, 18, 245))
        self.line(frame, 42, 1187, 42, 1248, width=6)
        frame.alpha_composite(lay, (self.px(65), base_y - self.px(2)))

    def opening_question(self, t: float) -> Image.Image:
        beat = self.board["beats"][0]
        img = beat["images"][0]
        # Beim Auto die Schadensquelle erst NACH der offenen Frage scharf zeigen:
        # sonst verrät das Rad den Konter schon im ersten Frame.
        frame = self.background(img, t, blur=self.short == "cv5",
                                dark=0.33 if self.short == "cv5" else 0.44)
        if self.short == "app":
            frame = self.background(img, t, blur=True, dark=0.52)
            self.panel(frame, img, (45, 630, 1045, 815), 38, 590, 644)
        elif self.short == "yt":
            frame = self.background(img, t, blur=True, dark=0.58)
            self.panel(frame, img, (65, 35, 660, 720), 38, 445, 644)
            # Jensen ist im echten Quellframe groß sichtbar; kein künstliches Creator-Gesicht.
        self.question(frame, beat["on_screen"][0]["value"], t)
        if self.short == "yt":
            self.credit(frame, beat)
        return frame

    def proof_question(self, t: float) -> Image.Image:
        beat = self.board["beats"][1]
        dt = t - 0.8
        img = beat["images"][0]
        frame = self.background(img, t, blur=self.short != "cv5", dark=0.35 if self.short == "cv5" else 0.76)
        # 0,8 s ist ein echter harter Bildwechsel, kein sanfter Crossfade.
        # Die kurze Belichtung (bei 30 fps drei Frames) betont den Cut.
        if self.short == "cv5":
            proof = beat["images"][1]
            box = self.panel(frame, proof, self.proofs["cv5"], 38, 833, 644,
                             slide=(1 - ease(dt / 0.15)) * 300)
            label = beat["on_screen"][0]["value"]
            layer = ink(label, self.px(635), self.px(170), self.color["accent"], border=self.px(3))
            paste_center(frame, layer, self.w / 2, self.px(655),
                         scale=0.93 + 0.07 * ease(dt / 0.18), shadow=True)
            p = ease((dt - 0.10) / 0.30)
            if p > 0:
                self.line(frame, 85, 833 + round(box[3] / self.s) + 28,
                          85 + round(540 * p), 833 + round(box[3] / self.s) + 28,
                          color=self.color["signal"], width=10)
        elif self.short == "app":
            self.panel(frame, img, self.proofs["app"], 38, 640, 644,
                       slide=(1 - ease(dt / 0.15)) * 750)
            label = beat["on_screen"][0]["value"]
            layer = ink(label, self.px(630), self.px(155), self.color["accent"], border=self.px(4))
            paste_center(frame, layer, self.w / 2, self.px(420), shadow=True)
        else:
            self.panel(frame, img, self.proofs["yt"], 38, 460, 644,
                       slide=(1 - ease(dt / 0.14)) * 750)
            self.panel(frame, img, (250, 420, 1280, 720), 38, 865, 644)
        if dt < 0.08:
            white = Image.new("RGBA", frame.size, (255, 255, 255, round(92 * (1 - dt / 0.08))))
            frame.alpha_composite(white)
        self.credit(frame, beat)
        return frame

    def opening_number(self, t: float) -> Image.Image:
        beat = self.board["beats"][0]
        frame = self.background(beat["images"][0], t, blur=True, dark=0.83)
        # Große grafische Fläche statt lesbarer Report-Typografie im ersten Frame.
        d = ImageDraw.Draw(frame)
        travel = round(self.px(45) * math.sin(2.5 * t))
        d.polygon((self.px(-180) + travel, 0, self.px(145) + travel, 0,
                   self.px(345) + travel, self.h, self.px(10) + travel, self.h),
                  fill=self.color["accent"] + (18,))
        self.number(frame, beat["on_screen"][0]["value"], t, small=False)
        # Ab Frame 1 ist genau ein Textelement sichtbar: die Zahl. Keine Etiketten.
        self.line(frame, 60, 890, 60 + round(580 * ease(t / 0.66)), 890, width=8)
        return frame

    def proof_number(self, t: float) -> Image.Image:
        beat = self.board["beats"][1]
        dt = t - 0.8
        img = beat["images"][0]
        frame = self.background(img, t, blur=True, dark=0.78)
        self.number(frame, self.board["beats"][0]["on_screen"][0]["value"], dt, small=True)
        box = self.panel(frame, img, self.proofs[self.short], 38, 540, 644,
                         slide=(1 - ease(dt / 0.14)) * 300)
        p = ease((dt - 0.08) / 0.28)
        if p > 0:
            # Belegzeile wird aktiv unterstrichen, kein dauerhafter Screenshot.
            self.line(frame, 60, 540 + round(box[3] / self.s) + 18,
                      60 + round(580 * p), 540 + round(box[3] / self.s) + 18, width=7)
        if self.short == "cv5":
            # Gegenbild, nicht bloß noch ein Screenshot: belegtes Unfallfoto.
            wreck = self.images["m/v4_wreck.png"]
            # Nur vorhandenes Belegbild aus Beat 2, keine zusätzliche Aussage.
            crop = wreck.crop((500, 150, 2700, 1500)).resize((self.px(650), self.px(355)), Image.Resampling.LANCZOS)
            frame.alpha_composite(crop.convert("RGBA"), (self.px(35), self.px(818)))
            ImageDraw.Draw(frame).rectangle((self.px(33), self.px(816), self.px(687), self.px(1175)),
                                            outline=self.color["accent"] + (255,), width=self.px(4))
        elif self.short == "yt":
            self.panel(frame, img, (300, 450, 1280, 720), 38, 890, 644)
        self.credit(frame, beat)
        return frame

    def creator_frame(self, t: float) -> Image.Image:
        n = min(len(self.creator_frames) - 1, round(t * FPS))
        shot = Image.open(io.BytesIO(self.creator_frames[n])).convert("RGBA")
        if t < 0.8:
            return shot
        beat = self.board["beats"][1]
        dt = t - 0.8
        if self.short == "yt":
            # Erst echter Creator, dann Original-Quellframe mit Jensen. Nicht vertauschen.
            image = beat["images"][0]
            shot = self.background(image, t, blur=True, dark=0.65)
            self.panel(shot, image, (0, 0, 1280, 720), 35, 465, 650,
                       slide=(1 - ease(dt / 0.13)) * 280)
        else:
            image = beat["images"][0]
            crop = ((400, 20, 2870, 1480) if self.short == "cv5" else (45, 640, 1030, 1030))
            self.panel(shot, image, crop, 85, 855, 550,
                       slide=(1 - ease(dt / 0.15)) * 300)
        self.credit(shot, beat)
        return shot

    def frame(self, t: float) -> Image.Image:
        if not 0 <= t < DURATION:
            raise ValueError("Hook-Test hat exakt 0 <= t < 1,5 s")
        if self.variant == "v1":
            output = self.creator_frame(t)
        elif self.variant == "v2":
            output = self.opening_number(t) if t < 0.8 else self.proof_number(t)
        else:
            output = self.opening_question(t) if t < 0.8 else self.proof_question(t)
        return output.convert("RGB")

    def render(self, dest: Path, ffmpeg: str) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = dest.with_name(dest.stem + ".part.mp4")
        cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
               "-pix_fmt", "rgb24", "-s", f"{self.w}x{self.h}", "-r", str(FPS), "-i", "-",
               "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temp)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for n in range(round(DURATION * FPS)):
                proc.stdin.write(self.frame(n / FPS).tobytes())
            proc.stdin.close()
            if proc.wait() != 0:
                raise RuntimeError(f"ffmpeg: {proc.stderr.read().decode(errors='replace')[-900:]}")
            temp.replace(dest)          # nie einen guten Preview durch einen Teil-Export ersetzen
        except Exception:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
            proc.wait(timeout=20)
            temp.unlink(missing_ok=True)
            raise
        return dest


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as e:
        raise RuntimeError("ffmpeg fehlt: pip install imageio-ffmpeg oder System-ffmpeg installieren") from e


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--short", choices=PALETTE, help="cv5 / app / yt")
    parser.add_argument("--variant", choices=("v1", "v2", "v3"), help="Gesicht, Zahl oder Widerspruch")
    parser.add_argument("--all", action="store_true", help="alle verfügbaren P1-Tests (V1 nur mit echtem Creator-Take)")
    parser.add_argument("--size", default="720x1280", help="9:16; z.B. 1080x1920")
    parser.add_argument("--outdir", type=Path, default=ROOT / "hooks/previews")
    args = parser.parse_args(argv)
    if args.all == bool(args.short or args.variant):
        parser.error("entweder --all ODER --short und --variant")
    if not args.all and not (args.short and args.variant):
        parser.error("--short und --variant zusammen angeben")
    try:
        size = tuple(int(n) for n in args.size.lower().split("x"))
        if len(size) != 2:
            raise ValueError
        jobs = [(s, v) for s in PALETTE for v in ("v1", "v2", "v3")
                if v != "v1" or (ROOT / f"hooks/raw/{s}_creator.mp4").is_file()] if args.all else [(args.short, args.variant)]
        if args.all:
            for s in PALETTE:
                if (s, "v1") not in jobs:
                    print(f"V1 wartet auf echten Take: hooks/raw/{s}_creator.mp4")
        ffmpeg = ffmpeg_exe()
        for short, variant in jobs:
            if variant == "v1":
                print("V1: Echtheit/Einwilligung der Creator-Aufnahme manuell prüfen; Dateiexistenz ist kein Beweis.")
            trial = Trial(short, variant, size)
            target = args.outdir / f"{short}_{variant}_SILENT_PREVIEW.mp4"
            trial.render(target, ffmpeg)
            print(f"Stummer Hook-Test (NICHT Post/Preflight): {target} [{size[0]}x{size[1]}, {DURATION:g} s]")
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(1, f"Fehler: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
