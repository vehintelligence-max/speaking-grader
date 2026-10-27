"""Kiểm tra âm cuối bằng so sánh hai giả thuyết (minimal-pair scoring).

Giải mã tự do (decode_free) hỏi "học viên phát ra âm gì?" rồi so với bài. Với âm
cuối như /s/, /z/, /t/, /d/ cách đó dễ sai: âm cuối nhỏ, ngắn, model hay bỏ qua
dù học viên có đọc, hoặc ngược lại.

Ở đây hỏi câu khác, hẹp hơn và chắc hơn: "đoạn ghi âm này giống câu CÓ đuôi hay
câu KHÔNG đuôi hơn?" Tính xác suất CTC của cả câu theo hai cách đọc, chỉ khác
nhau ở đúng từ cần chấm, rồi lấy chênh lệch:

    margin = log P(audio | cách đọc đúng) − log P(audio | cách đọc sai)

  margin > 0  → giống cách đọc đúng hơn
  margin < 0  → giống cách đọc sai hơn (thiếu s, thiếu ed, hoặc thêm s)

Mọi lỗi khác trong câu có mặt ở cả hai giả thuyết nên tự triệt tiêu. Đây là cùng
ý tưởng với GOP (goodness of pronunciation) mà các app chấm phát âm thương mại
dùng, áp riêng cho âm cuối.
"""

import re

import numpy as np

from .audio import load_audio, trim_silence
from .lexicon import parse_script
from .phoneset import espeak_to_coarse

PAD_HEAD, PAD_TAIL = 0.3, 0.4
SIBILANT = {"S", "Z", "SH", "ZH", "CH", "JH"}
VOICELESS = {"P", "T", "K", "F", "TH"}
REDUCED = {"AX", "IH", "AH"}


def _classes(rec):
    """Gộp ~390 token eSpeak thành các lớp âm thô + blank."""
    names = ["<b>"]
    tok2cls = {}
    for tid, tok in rec.id2tok.items():
        if tid in rec.special:
            tok2cls[tid] = 0
            continue
        cs = espeak_to_coarse(tok)
        c = cs[0] if cs else "<b>"
        if c not in names:
            names.append(c)
        tok2cls[tid] = names.index(c)
    return names, tok2cls


def _coarse_logprobs(rec, logits):
    """[T, V] logits → [T, C] log-xác suất theo lớp âm thô (log-sum-exp trong lớp)."""
    if not hasattr(rec, "_cls"):
        rec._cls = _classes(rec)
    names, tok2cls = rec._cls
    lp = logits - logits.max(axis=-1, keepdims=True)
    p = np.exp(lp)
    p /= p.sum(axis=-1, keepdims=True)
    M = np.zeros((logits.shape[1], len(names)), dtype=np.float32)
    for tid, c in tok2cls.items():
        if tid < M.shape[0]:
            M[tid, c] = 1.0
    P = p @ M
    return np.log(np.clip(P, 1e-12, None)), names


def _ctc_logp(torch, lp, names, seq):
    idx = [names.index(c) for c in seq if c in names]
    if not idx:
        return -1e9
    x = torch.from_numpy(lp).unsqueeze(1)                     # [T, 1, C]
    y = torch.tensor([idx], dtype=torch.long)
    loss = torch.nn.functional.ctc_loss(x, y, torch.tensor([lp.shape[0]]), torch.tensor([len(idx)]),
                                        blank=0, reduction="sum", zero_infinity=True)
    return -float(loss)


def _alt(coarse, text, kind):
    """Cách đọc SAI của một từ, để so với cách đọc đúng."""
    c = list(coarse)
    if kind in ("s", "pl"):
        if not c or c[-1] not in ("S", "Z"):
            return None
        if len(c) >= 3 and c[-2] in REDUCED and c[-3] in SIBILANT:
            return c[:-2]                          # washes → wash
        return c[:-1]                              # works → work
    if kind == "ed":
        if not c or c[-1] not in ("T", "D") or not text.lower().endswith("ed"):
            return None
        if len(c) >= 3 and c[-2] in REDUCED and c[-3] in ("T", "D"):
            return c[:-2]                          # waited → wait
        return c[:-1]                              # watched → watch
    if kind == "nos":
        if not c:
            return None
        if c[-1] in SIBILANT:
            return c + ["IH", "Z"]
        return c + (["S"] if c[-1] in VOICELESS else ["Z"])
    return None


def check_endings(audio_path, script, targets, rec):
    """targets: [{"w": "works", "occ": 0, "k": "s"}] (occ = lần xuất hiện thứ mấy của từ đó)
    -> [{"w", "k", "margin", "ok", "unsure"}] cùng thứ tự."""
    torch = rec.torch
    pcm, sr = load_audio(audio_path)
    pcm, _ = trim_silence(pcm, sr)
    pcm = np.pad(pcm, (int(PAD_HEAD * sr), int(PAD_TAIL * sr)))
    logits, _ = rec._logits(pcm, sr)
    lp, names = _coarse_logprobs(rec, logits)
    words, _ = parse_script(script)
    norm = lambda t: re.sub(r"[^a-z']", "", t.lower())
    base = [c for w in words for c in w.coarse]
    lp_base = _ctc_logp(torch, lp, names, base)
    out = []
    for t in targets:
        hits = [w for w in words if norm(w.text) == norm(t["w"])]
        w = hits[min(t.get("occ", 0), len(hits) - 1)] if hits else None
        alt = _alt(w.coarse, w.text, t["k"]) if w else None
        if alt is None:
            out.append(dict(w=t["w"], k=t["k"], margin=None, ok=None, unsure=True))
            continue
        seq = [c for x in words for c in (alt if x is w else x.coarse)]
        m = lp_base - _ctc_logp(torch, lp, names, seq)
        out.append(dict(w=t["w"], k=t["k"], margin=round(m, 2), ok=m > 0, unsure=abs(m) < 1.0))
    return out
