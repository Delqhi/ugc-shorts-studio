"""ASR auf Modal (faster-whisper, GPU) — Ausweichweg, wenn Groq/Infisical nicht verfügbar.

Aufruf:
  modal run modal_asr.py --audio /pfad/datei.mp3 --out /pfad/resultat.json [--language en] [--model large-v3]
"""
import modal

app = modal.App("sin-asr-whisper")
cache = modal.Volume.from_name("sin-hf-cache", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install("faster-whisper==1.1.1", "numpy>=2.0", "requests", "huggingface_hub", "av", "tokenizers", "nvidia-cublas-cu12", "nvidia-cudnn-cu12")
)


@app.function(image=image, gpu="T4", timeout=1800, volumes={"/root/.cache/huggingface": cache})
def transcribe(data: bytes, language: str = "en", model_name: str = "small") -> str:
    import json
    import tempfile
    from faster_whisper import WhisperModel

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fh:
        fh.write(data)
        path = fh.name
    m = WhisperModel(model_name, device="cpu", compute_type="int8")
    segs, info = m.transcribe(path, language=language, beam_size=5, vad_filter=True, word_timestamps=True)
    out = {"language": info.language, "duration": info.duration, "segments": [], "words": []}
    for s in segs:
        out["segments"].append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
        for w in (s.words or []):
            out["words"].append({"word": w.word, "start": round(w.start, 2), "end": round(w.end, 2)})
    cache.commit()
    return json.dumps(out, ensure_ascii=False)


@app.local_entrypoint()
def main(audio: str, out: str = "asr.json", language: str = "en", model: str = "large-v3"):
    import json
    from pathlib import Path
    data = Path(audio).read_bytes()
    res = transcribe.remote(data, language=language, model_name=model)
    Path(out).write_text(res)
    d = json.loads(res)
    print(f"{len(d['segments'])} Segmente, {d['duration']:.1f}s -> {out}")
    for s in d["segments"][:40]:
        print(f"{s['start']:7.2f}  {s['text'][:100]}")
