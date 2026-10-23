# Voice: TTS + ASR auf Modal (GPU)

Chatterbox Multilingual läuft **nicht** auf dem Mac (Intel; PyTorch ≥ 2,6 hat keine
macOS-x86-Wheels) und **nicht** auf sin-vm2 (dort läuft ComfyUI/H3). Der beauftragte
Weg ist **Modal GPU (T4)** im Workspace `zukunftsorientierte-energie` (einer der drei
H3-Pool-Workspaces aus `connectors/video-generator/comfyui-modal-h3/pool.json`).

## 1) TTS (deutsch)
```python
# modal_tts.py im Projektordner
import modal
app = modal.App("sin-tts-chatterbox")
hf_cache = modal.Volume.from_name("sin-hf-cache", create_if_missing=True)
image = (modal.Image.debian_slim(python_version="3.11")
         .apt_install("ffmpeg", "libsndfile1")
         .pip_install("torch==2.6.0", "torchaudio==2.6.0", "chatterbox-tts",
                      "soundfile", "huggingface_hub"))

@app.function(image=image, gpu="T4", timeout=1800,
               volumes={"/root/.cache/huggingface": hf_cache})
def synth(text: str, language: str = "de", exaggeration: float = 0.45,
          cfg_weight: float = 0.6, seed: int = 42) -> bytes:
    import io, torch, torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    torch.manual_seed(seed)
    model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
    wav = model.generate(text, language_id=language, exaggeration=exaggeration,
                         cfg_weight=cfg_weight)
    buf = io.BytesIO()
    torchaudio.save(buf, wav.detach().cpu(), model.sr, format="wav")
    hf_cache.commit()
    return buf.getvalue()
```
**Regeln:** **einmal im Kontext** synthetisieren (satzweise Synthese hängt englische
Fakten an) · Zahlen als Wörter schreiben · Markennamen aus der Stimme heraushalten und
als On-Screen-Text setzen (TTS verhunzt „RTX Spark" → „ATX-Bar") · nach der Synthese
per ASR gegenprüfen.

## 2) ASR (Wort-Timings für die Untertitel)
```bash
# Cloud (Groq) - schnell, braucht GROQ_API_KEY
sin-infisical exec --keys GROQ_API_KEY -- bash -c 'curl -s https://api.groq.com/openai/v1/audio/transcriptions \
  -H "Authorization: Bearer $GROQ_API_KEY" -F "file=@vo.wav" -F "model=whisper-large-v3" \
  -F "response_format=verbose_json" -F "timestamp_granularities[]=word" -o vo.words.json'
```
**Wenn Infisical klemmt** (CLI-Timeout 8 s → „required Infisical secret unavailable"):
ASR auf Modal mit faster-whisper. Auf **CPU/int8** (GPU braucht libcublas im Image,
sonst `RuntimeError: libcublas.so.12 not found`), Modell `small` reicht für Wort-Timings:
```python
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, info = m.transcribe(path, language="de", vad_filter=True, word_timestamps=True)
```
Output: `{"words": [{"word": …, "start": …, "end": …}]}` → das Format, das
`engine/render.py` (`Subtitles`) erwartet.

## 3) Modal-Zugang
- Heute: lokales Modal-Profil `~/.modal.toml` (Workspace `zukunftsorientierte-energie`).
- Fleet-konform wäre der Infisical-Token (`MODAL_ACCOUNT*_TOKEN_ID/SECRET`) bzw. der
  H3-Proxy-Pool (`MODAL_H3_<WS>_PROXY_TOKEN_ID/SECRET` in `pool.json`) — **Achtung:**
  die Pool-Keys sind *Proxy*-Tokens; als `MODAL_TOKEN_ID` gesetzt liefert die CLI
  „Token ID is malformed".
- **Bekannter offener Punkt:** der Infisical-CLI läuft in einen 8-s-Timeout, wenn
  `eu.infisical.com` langsam ist. Das bricht Cloud-ASR **und** den Modal-Zugriff per
  Infisical — nicht den Key, den Abruf.
