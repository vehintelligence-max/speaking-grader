"""Nhận dạng âm vị THỰC TẾ học viên phát ra, kèm mốc thời gian.

Dùng facebook/wav2vec2-lv-60-espeak-cv-ft — model nhận dạng ra âm vị IPA
(eSpeak) chứ không ra chữ. Đây là điểm khác biệt so với mọi tool chấm nói
thông thường:

  ASR thường (Whisper) được huấn luyện để ĐOÁN TỪ NGƯỜI TA MUỐN NÓI. Học viên
  đọc "book" thiếu /s/, Whisper vẫn ghi "books" vì đoán theo ngữ cảnh. Lỗi biến
  mất.

  Model âm vị thì ghi lại ĐÚNG NHỮNG GÌ PHÁT RA. Thiếu /s/ là thiếu /s/. Nó
  cũng được huấn luyện đa ngôn ngữ nên ghi được cả những âm không thuộc tiếng
  Anh — chính là các âm "thuần Việt" mình cần bắt.

Không dùng Wav2Vec2Processor/tokenizer vì tokenizer âm vị của transformers đòi
package `phonemizer` (cần eSpeak binary, máy này không có brew). Ở đây chỉ cần
giải mã id -> token nên đọc vocab.json trực tiếp.
"""

import json
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from .phoneset import espeak_to_coarse

MODEL_ID = "facebook/wav2vec2-lv-60-espeak-cv-ft"
FRAME_S = 0.020            # wav2vec2 hạ mẫu 320x -> 1 frame = 20 ms @16 kHz
CHUNK_S = 20.0             # cắt khúc để attention không phình bộ nhớ
OVERLAP_S = 1.0


@dataclass
class ActualPhone:
    """Một âm học viên thực sự phát ra."""
    token: str             # token eSpeak gốc, vd 'θ', 'aɪ'
    coarse: str            # mã âm thô để đối chiếu
    start: float
    end: float
    conf: float            # độ tự tin trung bình của model trên các frame này
    peak: float = 0.0      # tâm của đỉnh CTC gốc, trước khi nới sang frame blank

    @property
    def dur(self):
        return self.end - self.start


def _merge_rhotic(phones):
    """Gộp /ɹ/ ngay sau /ɜː/ vào chính nó.

    CMUdict ký hiệu ER đã bao gồm màu 'r' (her = HH ER0). Model eSpeak lại ghi
    tách thành 'ɜː' + 'ɹ'. Không gộp thì mọi từ có ER đều bị báo oan là "thêm âm
    /r/ không có trong bài".
    """
    out = []
    for p in phones:
        if out and p.coarse == "R" and out[-1].coarse == "ER":
            out[-1].end = max(out[-1].end, p.end)

            continue
        out.append(p)
    return out


class PhonemeRecognizer:
    _cache = {}

    def __init__(self, model_id=MODEL_ID, device=None):
        import torch
        from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC
        from huggingface_hub import hf_hub_download

        self.torch = torch
        key = (model_id, device)
        if key in PhonemeRecognizer._cache:
            self.__dict__.update(PhonemeRecognizer._cache[key].__dict__)
            return

        self.device = device or "cpu"
        self.fe = Wav2Vec2FeatureExtractor.from_pretrained(model_id)
        self.model = Wav2Vec2ForCTC.from_pretrained(model_id).eval().to(self.device)

        with open(hf_hub_download(model_id, "vocab.json"), encoding="utf-8") as f:
            vocab = json.load(f)
        self.id2tok = {int(v): k for k, v in vocab.items()}
        pad = self.model.config.pad_token_id
        self.blank = pad if pad is not None else vocab.get("<pad>", 0)
        # Token đặc biệt: không phải âm, bỏ khi giải mã.
        self.special = {self.blank}
        for t in ("<pad>", "<s>", "</s>", "<unk>", "|", "<mask>"):
            if t in vocab:
                self.special.add(int(vocab[t]))

        PhonemeRecognizer._cache[key] = self

    # ------------------------------------------------------------------
    def _logits(self, pcm, sr):
        """Ghép logits của các khúc thành một mảng [T, V] liên tục."""
        torch = self.torch
        chunk_n, ov_n = int(CHUNK_S * sr), int(OVERLAP_S * sr)
        pieces, frame_offset = [], 0

        if len(pcm) <= chunk_n:
            spans = [(0, len(pcm))]
        else:
            spans, s = [], 0
            while s < len(pcm):
                spans.append((s, min(len(pcm), s + chunk_n)))
                if s + chunk_n >= len(pcm):
                    break
                s += chunk_n - ov_n

        for k, (a, b) in enumerate(spans):
            seg = pcm[a:b]
            if len(seg) < int(0.05 * sr):
                continue
            inp = self.fe(seg, sampling_rate=sr, return_tensors="pt",
                          padding=False)
            with torch.no_grad():
                out = self.model(inp.input_values.to(self.device)).logits[0]
            out = out.float().cpu().numpy()
            # Bỏ nửa vùng chồng lấn ở đầu khúc sau để không nhân đôi âm.
            if k > 0:
                drop = int((OVERLAP_S / 2) / FRAME_S)
                out = out[drop:]
                frame_offset = int(round((a / sr + OVERLAP_S / 2) / FRAME_S))
            elif k == 0:
                frame_offset = 0
            pieces.append((frame_offset, out))

        if not pieces:
            return np.zeros((0, len(self.id2tok)), dtype=np.float32), 0
        # Nối theo mốc frame; các khúc đã cắt chồng lấn nên chỉ cần xếp tiếp.
        total = pieces[-1][0] + len(pieces[-1][1])
        full = np.full((total, pieces[0][1].shape[1]), -1e9, dtype=np.float32)
        for off, arr in pieces:
            full[off:off + len(arr)] = arr
        return full, total

    def recognize(self, pcm, sr=16000) -> List[ActualPhone]:
        """-> danh sách âm thực tế theo thứ tự thời gian."""
        logits, _ = self._logits(pcm, sr)
        return self.decode_free(logits)

    def decode_free(self, logits) -> List[ActualPhone]:
        """Giải mã tự do: ghi lại đúng những âm phát ra, không bám script."""
        if len(logits) == 0:
            return []

        ids = logits.argmax(axis=-1)
        # softmax theo hàng, chỉ để lấy độ tự tin
        mx = logits.max(axis=-1, keepdims=True)
        probs = np.exp(logits - mx)
        probs /= probs.sum(axis=-1, keepdims=True)
        best = probs.max(axis=-1)

        # CTC: gộp frame trùng nhau, bỏ blank.
        runs, i, n = [], 0, len(ids)
        while i < n:
            j = i
            while j + 1 < n and ids[j + 1] == ids[i]:
                j += 1
            runs.append((int(ids[i]), i, j + 1))     # [start, end) theo frame
            i = j + 1
        keep = [r for r in runs if r[0] not in self.special]

        # CTC huấn luyện bằng hàm mất mát tổng trên mọi đường đi, nên đầu ra rất
        # "nhọn": mỗi âm chỉ chiếm 1 frame, xung quanh là blank. Lấy nguyên bề
        # rộng đó làm độ dài âm thì mọi âm đều dài 20 ms và nPVI luôn bằng 0.
        # Vì vậy phải trả các frame blank về cho hai âm kề nó, chia đôi ở giữa.
        # Chặn ở MAX_EXT để khoảng lặng thật không bị tính thành độ dài âm.
        MAX_EXT = 6                                  # 120 ms mỗi bên
        out = []
        for k, (tid, fs, fe) in enumerate(keep):
            gap_l = fs - keep[k - 1][2] if k > 0 else fs
            gap_r = keep[k + 1][1] - fe if k + 1 < len(keep) else max(0, n - fe)
            ext_l = min(gap_l - gap_l // 2, MAX_EXT) if k > 0 else min(gap_l, MAX_EXT)
            ext_r = min(gap_r // 2, MAX_EXT) if k + 1 < len(keep) else min(gap_r, MAX_EXT)
            f0, f1 = fs - ext_l, fe + ext_r

            tok = self.id2tok.get(tid, "")
            coarses = espeak_to_coarse(tok)
            if not coarses:
                continue
            t0, t1 = f0 * FRAME_S, f1 * FRAME_S
            conf = float(np.mean(best[fs:fe]))
            peak = (fs + fe) / 2.0 * FRAME_S     # vị trí đỉnh: rất chính xác
            step = (t1 - t0) / len(coarses)
            for c_i, c in enumerate(coarses):
                out.append(ActualPhone(
                    token=tok, coarse=c,
                    start=t0 + c_i * step, end=t0 + (c_i + 1) * step,
                    conf=conf, peak=peak))

        return _merge_rhotic(out)
