# Conversation Mode — design

Goal: a student talks with an AI partner by voice. The AI keeps the conversation going. Behind the scenes, every student utterance is graded for pronunciation, and the session ends with one report: what to fix first.

This document is the plan. Nothing here is built yet. The read-aloud grader (this repo) is finished and becomes one component of it.

## The core design problem

The grader needs to know what the student *meant* to say — it compares produced phonemes against a reference script. In read-aloud mode the script is given. In free conversation there is no script.

Solution: run a normal ASR (Whisper-class) on the utterance to get the *intended words*, then feed that transcript to the phoneme grader as the reference script. This inverts the weakness noted in the README: Whisper's habit of guessing the intended word is exactly what we want here.

Consequence to design around: when ASR guesses wrong, the grader will flag errors the student didn't make. Mitigations:
- grade only words where ASR confidence is high; skip low-confidence words silently
- aggregate across the whole session and report only error *patterns* seen 3+ times (a dropped final that shows up in 9 words is real; one flagged word may be an ASR miss)

## Architecture (turn-based, v1)

```
Browser (Chrome)                      Server (Python, this repo + additions)
----------------                      --------------------------------------
push-to-talk mic capture   ── audio ─▶  1. ASR (faster-whisper small, CPU)
                                        2. LLM reply (see options)
speak reply aloud          ◀─ text ──   3. queue utterance for grading (async)
(speechSynthesis, free,
 runs in the browser)                   background: phoneme grader per utterance
                                        session end: aggregate → report HTML
```

Turn-based (student presses to talk, AI replies) — no interruption/barge-in in v1. That keeps latency tolerable: the conversation loop needs only ASR + LLM (~2-4s); the heavy phoneme grading (~10-30s per utterance on CPU) runs in the background and is only needed by session end.

## Component choices (free options)

| Component | Recommended | Alternative | Trade-off |
|---|---|---|---|
| Conversation ASR | faster-whisper `small` local, CPU | Browser Web Speech API | Local = private, works offline; browser API = zero server load but Chrome-only and sends audio to Google |
| LLM (dialogue brain) | Gemini Flash **free tier** | Local model via Ollama (e.g. Qwen 3B) | Free tier: good quality, rate limits fine for 1:1 tutoring; local: fully offline but this Mac has ~9GB free disk and no GPU — tight |
| TTS (AI voice) | Browser `speechSynthesis` | macOS `say` server-side | Browser TTS costs nothing and offloads the server; voices are decent for a tutor persona |
| Pronunciation grading | this repo, unchanged | — | already validated (native 95.7 vs VN-accent proxy 60.1) |

The only external dependency in the recommended stack is the LLM free tier. Everything else runs locally or in the student's browser.

## Session flow

1. Student picks a scenario (ordering food, IELTS Part 1, job interview...) and a level. Each scenario is a system prompt + vocabulary the AI should steer toward.
2. AI opens with a question (TTS in browser).
3. Student holds the talk button and answers. Audio goes to the server.
4. ASR transcript → LLM generates the next turn → browser speaks it. Utterance + transcript enter the grading queue.
5. Repeat for 5–15 minutes.
6. "End session" → server finishes the grading queue and renders one report:
   - top 3 error patterns by frequency (e.g. dropped finals 14×, th→t 8×, flat rhythm)
   - per-utterance detail with listen buttons (reuse the existing report renderer)
   - trend vs. previous sessions if a student name was given (JSON history already supported by `cli.py --json`)

## Build phases

| Phase | Scope | Effort |
|---|---|---|
| 1 | Turn-based voice chat: mic capture, ASR, LLM reply, browser TTS. No grading yet — prove the conversation feels OK | 1–2 days |
| 2 | Wire the grader: async per-utterance grading, confidence filter, end-of-session aggregated report | 1–2 days |
| 3 | Scenarios/levels, student history, teacher view | 1–2 days |

Phase 1 is the risky one (latency, mic UX) — build it first and throw it away cheaply if the experience is bad.

## Risks

- **ASR-as-script accuracy** is the main quality risk. The confidence filter and pattern-frequency reporting exist for this; validate early on real student audio.
- **Latency** on a laptop CPU: ASR small model ≈ 1-2s per utterance — acceptable; if not, drop to `base`.
- **LLM free-tier limits**: per-minute caps are fine for one student; a classroom of simultaneous sessions would need a local model or paid tier.
- **Privacy**: student audio stays on the server host; browser TTS/STT choices change this — document whichever is deployed.
