# Deployment notes

Read this before deploying. The most common mistake is treating this as a static site.

## This is not a static site

The web UI is served by a Python process (`server.py`) that runs a 1.2GB phoneme-recognition model on every grading request. **GitHub Pages, Netlify, Vercel static hosting, and Cloudflare Pages will not work** — they serve files, they cannot run the model. The page would render but "Chấm bài" (grade) would do nothing.

## What the server needs

| Requirement | Detail |
|---|---|
| Python | 3.9+ with the packages in `requirements.txt` |
| Model download | `facebook/wav2vec2-lv-60-espeak-cv-ft` (~1.2GB), auto-downloaded from Hugging Face on first run, cached in `~/.cache/huggingface` |
| RAM | ~3GB during inference |
| CPU | Works on CPU; no GPU required. A 30-second clip takes ~10-30s on a laptop CPU, longer on small cloud CPUs |
| ffmpeg | **Not required.** Audio decoding uses PyAV (bundled Python wheels) |
| Disk | ~2GB for model cache + ~1GB for Python packages |

## Run it

```bash
pip install -r requirements.txt
python server.py --port 8971
```

Endpoints:
- `GET /` — upload form (paste script, upload recording)
- `POST /grade` — multipart form (`student`, `script`, `audio`) → self-contained HTML report with embedded audio players
- `GET /shadow` — shadowing mode: listen to a model sentence, record an imitation, instant per-sentence grading
- `GET /shadow/audio?i=&voice=&rate=` — model clip (m4a)
- `POST /shadow/grade` — multipart (`i`, `audio` from browser mic, webm/opus or mp4) → JSON score

**macOS-only piece:** shadowing model clips are synthesized on demand with the macOS `say` command (`shadow.py: synth()`). On a Linux deployment, replace `synth()` with another TTS (e.g. Edge-TTS, Piper) or ship pre-generated clips — everything else is portable. Browser mic capture requires HTTPS in production (localhost is exempt).

There is also a CLI (`cli.py`) for batch grading and JSON output.

## Recommended free hosting

1. **Hugging Face Spaces** (best fit): free CPU tier, the model is already on HF so downloads are fast. Wrap `grader/` in a small Gradio app, or run `server.py` in a Docker Space. Set persistent storage or accept re-download on rebuild.
2. **Render / Railway / Fly.io free tiers**: work, but cold starts re-download the 1.2GB model unless you add a persistent volume; small instances (512MB RAM) will OOM — you need ~3GB.

## Privacy

Student recordings are processed in memory and embedded (base64) into the returned HTML report. Nothing is persisted server-side by default. If you deploy publicly, state this on the page and keep it true.

## Repo layout

```
grader/        core pipeline: decode → phoneme ASR → align vs script → score
server.py      web UI (stdlib http.server, no framework)
cli.py         command-line grading, HTML/JSON output
calibrate.py   recompute native-reference rhythm stats (nPVI) with the same pipeline
tests/         run: python tests/run_tests.py (4 checks, needs the model)
docs/          design docs, incl. the interactive conversation mode plan
```
