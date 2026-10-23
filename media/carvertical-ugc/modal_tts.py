"""SIN TTS auf Modal — Chatterbox Multilingual (Resemble AI, 2026).

Deutsch (language_id="de"), GPU, Modellgewichte im Volume-Cache.
Aufruf:
  python3 -m modal run modal_tts.py --text "..." --out /pfad/out.wav --exaggeration 0.5
"""
from typing import Optional

import modal

app = modal.App("sin-tts-chatterbox")

hf_cache = modal.Volume.from_name("sin-hf-cache", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(
        "torch==2.6.0",
        "torchaudio==2.6.0",
        "chatterbox-tts",
        "soundfile",
        "huggingface_hub",
    )
)


@app.function(
    image=image,
    gpu="T4",
    timeout=1800,
    volumes={"/root/.cache/huggingface": hf_cache},
)
def synth(
    text: str,
    language: str = "de",
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
    seed: int = 42,
    audio_prompt: Optional[bytes] = None,
) -> bytes:
    import io
    import os
    import tempfile

    import torch
    import torchaudio

    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    torch.manual_seed(seed)
    model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
    kwargs = {
        "language_id": language,
        "exaggeration": exaggeration,
        "cfg_weight": cfg_weight,
    }
    if audio_prompt:
        fd, path = tempfile.mkstemp(suffix=".wav")
        with os.fdopen(fd, "wb") as fh:
            fh.write(audio_prompt)
        kwargs["audio_prompt_path"] = path
    wav = model.generate(text, **kwargs)
    buf = io.BytesIO()
    torchaudio.save(buf, wav.detach().cpu(), model.sr, format="wav")
    hf_cache.commit()
    return buf.getvalue()


@app.local_entrypoint()
def main(
    text: str,
    out: str = "out.wav",
    language: str = "de",
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
    seed: int = 42,
):
    data = synth.remote(
        text=text,
        language=language,
        exaggeration=exaggeration,
        cfg_weight=cfg_weight,
        seed=seed,
    )
    with open(out, "wb") as fh:
        fh.write(data)
    print(f"geschrieben: {out} ({len(data)} Bytes)")
