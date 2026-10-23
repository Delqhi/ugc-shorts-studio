#!/bin/bash
# Mix (Voice + Whooshes an den Szenengrenzen) -> Two-Pass-loudnorm (-14 LUFS) -> Export + QA-Sheets.
#
# Aufruf:
#   finalize.sh --raw build/video_raw.mp4 --vo tts/vo.wav --out out/short.mp4 \
#                --dur 24 [--cuts 2.45,6.0,12.0,16.55,19.72] [--ffmpeg /usr/local/bin/ffmpeg]
set -e
# KEIN cd: die Pfade stammen vom Aufrufer (Workdir mit Medien/VO/Storyboard).
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

RAW=""; VO=""; OUT=""; DUR=""; CUTS=""; QADIR=""; FF="${FFMPEG:-ffmpeg}"; FFP="${FFPROBE:-ffprobe}"
while [ $# -gt 0 ]; do
  case "$1" in
    --raw) RAW="$2"; shift 2;;
    --vo) VO="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --dur) DUR="$2"; shift 2;;
    --cuts) CUTS="$2"; shift 2;;
    --ffmpeg) FF="$2"; shift 2;;
    --music) MUSIC="$2"; shift 2;;
    --qa) QADIR="$2"; shift 2;;
    --music-gain) MG="$2"; shift 2;;
    *) echo "unknown arg $1"; exit 2;;
  esac
done
[ -n "$RAW" ] && [ -n "$VO" ] && [ -n "$OUT" ] || { echo "Pflicht: --raw --vo --out"; exit 2; }
[ -n "$DUR" ] || DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$RAW")
BASE="$(basename "$OUT" .mp4)"
TMPD="$(dirname "$OUT")/build_tmp/$BASE"
[ -n "$QADIR" ] || QADIR="$(dirname "$OUT")/qa/$BASE"
mkdir -p "$(dirname "$OUT")" "$TMPD"

# 1) Whoosh-Betrieb: pinkes Rauschen, gefiltert, kurzer Ausklang
$FF -y -v error -f lavfi -i "anoisesrc=d=0.45:c=pink:a=0.4" \
  -af "highpass=f=220,lowpass=f=3000,afade=t=in:st=0:d=0.05,afade=t=out:st=0.15:d=0.3,volume=0.8" \
  -ar 48000 -ac 2 $TMPD/whoosh.wav

# 2) Filtergraph bauen (Index-Pruefung in build_mix_filter.py, s. pitfalls.md H1)
MAP=$(python3 "$SKILL_DIR/scripts/build_mix_filter.py" --raw "$RAW" --vo "$VO" --cuts "$CUTS" --dur "$DUR" \
        --whoosh "$TMPD/whoosh.wav" ${MUSIC:+--music "$MUSIC" --music-gain "$MG"} \
        | sed -n 's/^ARGS=//p')
FILT=$(python3 "$SKILL_DIR/scripts/build_mix_filter.py" --raw "$RAW" --vo "$VO" --cuts "$CUTS" --dur "$DUR" \
        --whoosh "$TMPD/whoosh.wav" ${MUSIC:+--music "$MUSIC" --music-gain "$MG"} \
        | sed -n 's/^FILT=//p')
python3 "$SKILL_DIR/scripts/build_mix_filter.py" --raw "$RAW" --vo "$VO" --cuts "$CUTS" --dur "$DUR" \
        --whoosh "$TMPD/whoosh.wav" ${MUSIC:+--music "$MUSIC" --music-gain "$MG"} --check-only >/dev/null

# 3) Mix ohne Normalisierung -> messen -> linear anpassen
$FF -y -v error $MAP -filter_complex "$FILT" -map "[mix]" -t "$DUR" -c:a pcm_s24le $TMPD/mix.wav
J=$($FF -hide_banner -nostats -i $TMPD/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
v() { echo "$J" | python3 -c "import json,sys;print(json.load(sys.stdin)['$1'])"; }
$FF -y -v error -i "$RAW" -i $TMPD/mix.wav \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(v input_i):measured_TP=$(v input_tp):measured_LRA=$(v input_lra):measured_thresh=$(v input_thresh):offset=$(v target_offset):linear=true,aresample=48000" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -t "$DUR" -movflags +faststart "$OUT"

$FFP -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,pix_fmt \
  -of default=nw=1 "$OUT"
$FF -hide_banner -nostats -i "$OUT" -af loudnorm=I=-14:TP=-1.5:print_format=summary -f null - 2>&1 \
  | grep -E "Input Integrated|Input True Peak"

# 4) QA-Sheets (Frame-Sweep über die ganze Länge)
QAD="$QADIR"
mkdir -p "$QAD"
rm -f "$QAD"/f*.png "$QAD"/sheet_*.jpg
NFR=$(python3 -c "print(int(float('$DUR')*2))")
i=0; while [ $i -lt $NFR ]; do
  T=$(python3 -c "print(f'{$i*0.5+0.1:.2f}')")
  $FF -y -v error -ss "$T" -i "$OUT" -frames:v 1 "$(printf '%s/f%03d.png' "$QAD" $i)"
  i=$((i+1))
done
python3 - "$QAD" <<'PY'
from PIL import Image
import glob, os, sys
qad = sys.argv[1] if len(sys.argv) > 1 else 'qa'
fs = sorted(glob.glob(os.path.join(qad, 'f*.png')))
for s in range(0, len(fs), 8):
    sheet = Image.new('RGB', (360 * 4, 640 * 2))
    for i, f in enumerate(fs[s:s + 8]):
        sheet.paste(Image.open(f).resize((360, 640)), ((i % 4) * 360, (i // 4) * 640))
    sheet.save(os.path.join(qad, f'sheet_{s // 8}.jpg'), quality=88)
print('QA-Sheets:', (len(fs) + 7) // 8)
PY
