"""Năng lượng và cao độ theo frame — nguyên liệu để xét trọng âm và ngữ điệu.

Cố tình chỉ dùng numpy: máy này không có ffmpeg/praat, và cài thêm parselmouth
là không cần thiết cho việc so tương đối giữa các âm tiết trong cùng một từ.
"""

import numpy as np

HOP = 0.010        # 10 ms, khớp với bước nhảy quen dùng cho prosody
WIN = 0.030


def rms_track(pcm, sr, hop=HOP, win=WIN):
    """-> (rms theo frame, hop giây). Cường độ tương đối để xét trọng âm."""
    hop_n, win_n = int(hop * sr), int(win * sr)
    if len(pcm) < win_n:
        return np.zeros(1, dtype=np.float32), hop
    n = 1 + (len(pcm) - win_n) // hop_n
    idx = np.arange(win_n)[None, :] + hop_n * np.arange(n)[:, None]
    frames = pcm[idx]
    return np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12).astype(np.float32), hop


def f0_track(pcm, sr, hop=HOP, win=0.040, fmin=60.0, fmax=400.0):
    """Cao độ bằng tự tương quan chuẩn hoá. -> (f0 Hz, 0 nếu vô thanh), hop.

    Đủ chính xác cho việc so cao độ giữa các âm tiết. Không dùng để đo tuyệt đối.
    """
    hop_n, win_n = int(hop * sr), int(win * sr)
    lag_min, lag_max = int(sr / fmax), int(sr / fmin)
    if len(pcm) < win_n or lag_max >= win_n:
        return np.zeros(1, dtype=np.float32), hop
    n = 1 + (len(pcm) - win_n) // hop_n
    out = np.zeros(n, dtype=np.float32)
    for k in range(n):
        seg = pcm[k * hop_n: k * hop_n + win_n].astype(np.float64)
        seg = seg - seg.mean()
        e0 = np.dot(seg, seg)
        if e0 < 1e-8:
            continue
        ac = np.correlate(seg, seg, mode="full")[win_n - 1:]
        band = ac[lag_min:lag_max + 1]
        if len(band) == 0:
            continue
        lag = int(np.argmax(band)) + lag_min
        # Chuẩn hoá theo năng lượng để loại nhiễu ở đoạn vô thanh.
        if ac[lag] / e0 > 0.35:
            out[k] = sr / float(lag)
    return out, hop


def span_mean(track, hop, t0, t1, positive_only=False):
    """Trung bình một track theo frame trên khoảng thời gian [t0, t1) giây."""
    if track is None or len(track) == 0 or t1 <= t0:
        return 0.0
    a = max(0, int(round(t0 / hop)))
    b = min(len(track), max(a + 1, int(round(t1 / hop))))
    seg = track[a:b]
    if positive_only:
        seg = seg[seg > 0]
    return float(np.mean(seg)) if len(seg) else 0.0


def vowel_extents(rms, hop, peaks, rel=0.5, cap=0.32):
    """Độ dài từng nguyên âm, đo bằng bề rộng vùng năng lượng quanh đỉnh.

    Vì sao không lấy độ dài từ đầu ra CTC: CTC được huấn luyện bằng tổng trên mọi
    đường đi nên đầu ra rất "nhọn" — mỗi âm chỉ chiếm 1 frame, và forced alignment
    trên cùng model đó cũng nhọn y vậy. Bề rộng thu được là bề rộng của khoảng
    blank bên cạnh, không phải của âm.

    Nguyên âm thì luôn là một đỉnh năng lượng. Lấy bề rộng tại ngưỡng -6 dB so với
    đỉnh (rel=0.5 về biên độ) cho độ dài không phụ thuộc CTC. Biên bị chặn ở trung
    điểm tới nguyên âm kề bên nên hai nguyên âm không bao giờ chồng nhau.

    peaks: list (khoá, thời điểm đỉnh giây), đã sắp theo thời gian.
    -> dict {khoá -> độ dài giây}
    """
    out, n = {}, len(rms)
    if n == 0 or not peaks:
        return {p[0]: 0.0 for p in peaks}
    ts = [t for _, t in peaks]
    half_cap = int(round(cap / 2 / hop))
    for k, (key, t) in enumerate(peaks):
        c = max(0, min(n - 1, int(round(t / hop))))
        local = float(rms[max(0, c - 2):min(n, c + 3)].max())
        if local <= 0:
            out[key] = 0.0
            continue
        thr = rel * local
        lo = 0 if k == 0 else int(round((ts[k - 1] + t) / 2 / hop))
        hi = n if k == len(peaks) - 1 else int(round((t + ts[k + 1]) / 2 / hop))
        lo = max(0, lo, c - half_cap)
        hi = min(n, hi, c + half_cap + 1)
        i = j = c
        while i - 1 >= lo and rms[i - 1] >= thr:
            i -= 1
        while j + 1 < hi and rms[j + 1] >= thr:
            j += 1
        out[key] = (j - i + 1) * hop
    return out


def npvi(durations):
    """nPVI — chỉ số biến thiên độ dài giữa các âm liền kề.

    Tiếng Anh là stress-timed: nguyên âm dài ngắn chênh nhau nhiều -> nPVI cao
    (bản ngữ thường ~55-65). Tiếng Việt là syllable-timed: các âm tiết đều nhau
    -> nPVI thấp. Đây chính là con số đo được của cảm giác "nghe rất thuần Việt".
    """
    d = [x for x in durations if x > 0]
    if len(d) < 2:
        return None
    total = 0.0
    for a, b in zip(d, d[1:]):
        total += abs(a - b) / ((a + b) / 2.0)
    return 100.0 * total / (len(d) - 1)
