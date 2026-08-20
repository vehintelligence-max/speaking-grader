# Speaking Practice Studio — design (v2)

Extends `conversation-mode-design.md`. The product grows from one grader into a self-serve practice site with three modes sharing one grading engine. Students log in, pick a mode, practice alone, and every recording feeds one progress history.

## Mode map

| Mode | Student does | Reference script | Grading |
|---|---|---|---|
| **Shadowing / Mimicking** | listens to a model clip, repeats sentence by sentence | known — the clip's transcript | full phoneme grading + prosody-similarity vs. the model clip |
| **Conversation** | talks with an AI partner | ASR transcript of the utterance | pattern aggregation (see conversation-mode doc) |
| **Free talk** | speaks freely, watches live transcript appear | ASR transcript | optional, on demand |

Shadowing is the best fit for the existing engine: the script is known in advance, so grading works exactly like read-aloud mode today — no ASR-as-script uncertainty.

## Shadowing / Mimicking mode

### Clip library
Each item = audio + transcript + level/topic tags. Sources, in order of preference:

1. **Real clips of real people** (interviews, speeches, movie scenes) — embed from YouTube or trim short excerpts. This is the classic shadowing method and covers the "celebrity voice" request with the person's *actual* voice, which teaches more than any synthetic imitation. Keep excerpts short; attribute the source.
2. **TTS persona voices** for house-made scripts — a bench of accents (US/UK/AU, male/female) via free TTS (browser `speechSynthesis`, or Edge-TTS server-side for better quality).
3. **A consenting teacher's cloned voice** as the VEH signature voice, using an open local model (e.g. XTTS) — only with the teacher's written consent.

**Do not clone real celebrities' voices without consent.** It carries right-of-publicity legal risk, platforms ban it, and free cloning quality is poor anyway. Option 1 gives students the real voice legitimately.

### Practice loop (per sentence)
1. Play the model sentence (loop button, 0.75× speed option).
2. Student records their imitation.
3. Instant feedback, two layers:
   - **Segmental** (existing grader): wrong/dropped phonemes, finals, clusters, th-stopping.
   - **Mimicry score** (new): how close the student's prosody is to *this specific clip* — stress placement per word, rhythm (nPVI), pace, pause positions, and F0 direction per stressed syllable. All of these features are already extracted by `grader/prosody.py`; the new work is extracting them from the model clip too and scoring the delta.
4. Side-by-side playback: model sentence vs. student's attempt.

### New code required
- Reference-clip analyzer: run the existing feature extractors on the model audio once, cache per clip (~1 day).
- Similarity scorer + per-sentence UI (~1–2 days).
- Clip library CRUD for teachers (~1 day).

## Live transcript (free talk + all modes)

Two engines, used together:

| Engine | Latency | Privacy | Use for |
|---|---|---|---|
| Web Speech API (built into Chrome) | word-by-word, near-instant | audio goes to Google | the live on-screen transcript |
| faster-whisper on the server | 1–2 s per chunk | stays on our server | the transcript that grading actually uses |

Display fast, grade accurately. If a deployment must be fully private, drop the Web Speech display or replace it with chunked server streaming and accept the 1–2 s delay.

## Multi-user reality

Self-serve students means concurrency. Grading is the bottleneck: one CPU grades one clip at a time (~10–30 s each).

- Keep grading **async with a queue**; the practice loop never blocks on it (mimicry prosody scoring is much lighter than full phoneme grading and can stay near-instant).
- Hugging Face Spaces free CPU handles one class if students tolerate queued detailed reports.
- If usage grows: a single small GPU box cuts grading to ~1–2 s per clip. Decide only after real usage data.

## Accounts and progress

Minimal: student name + class code (no passwords in v1), one JSON history per student (already supported by `cli.py --json`). Progress view: error-pattern counts per week — "dropped finals: 14 → 6". Later this can plug into the VEH Teaching Hub as a module.

## Build order (updated)

| Phase | Scope | Effort |
|---|---|---|
| 1 | Shadowing mode, single clip hardcoded: loop UX, record, segmental grading | 2 days |
| 2 | Mimicry prosody-similarity score + side-by-side playback | 2 days |
| 3 | Clip library + teacher upload; TTS persona voices | 1–2 days |
| 4 | Live-transcript free talk mode | 1 day |
| 5 | Conversation mode (see conversation-mode-design.md) | 3–4 days |
| 6 | Student accounts, progress history, teacher dashboard | 2 days |

Shadowing moved ahead of conversation: it reuses the validated engine as-is, needs no LLM dependency, and is the feature students can use alone on day one.
