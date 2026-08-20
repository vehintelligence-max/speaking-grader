"""Quy các con số đo được thành điểm 0–100 theo từng nhóm kỹ năng.

Nguyên tắc: mỗi điểm phải truy được về một tỉ lệ đếm được, không có hệ số tự
nghĩ ra. Vd điểm âm cuối = đúng bao nhiêu / tổng bao nhiêu phụ âm cuối. Nhờ vậy
khi học viên hỏi "sao em bị 62?" thì giáo viên chỉ được đúng chỗ.
"""

import json
import pathlib

# Tham chiếu bản ngữ ĐO BẰNG CHÍNH PIPELINE NÀY, không lấy từ giáo trình.
# Lý do: mốc thời gian ở đây suy ra từ đầu ra CTC, lượng tử hoá theo frame 20 ms,
# nên nPVI tính được thấp hơn con số 55-65 mà các nghiên cứu đo bằng ranh giới
# gán tay. So học viên với con số của giáo trình là trừ điểm oan tất cả. Chạy
# calibrate.py để cập nhật hai hằng số này từ giọng mẫu.
_CAL = pathlib.Path(__file__).with_name("calibration.json")
NATIVE_NPVI, NATIVE_RATIO = 42.0, 1.45
if _CAL.exists():
    try:
        _d = json.loads(_CAL.read_text())
        NATIVE_NPVI = float(_d.get("npvi", NATIVE_NPVI))
        NATIVE_RATIO = float(_d.get("stress_ratio", NATIVE_RATIO))
    except (ValueError, KeyError):
        pass

WEIGHTS = {
    "phoneme": 0.30,
    "final": 0.22,
    "stress": 0.18,
    "linking": 0.12,
    "rhythm": 0.10,
    "fluency": 0.08,
}

LABELS = {
    "phoneme": "Âm vị tổng thể",
    "final": "Âm cuối",
    "stress": "Trọng âm từ",
    "linking": "Nối âm",
    "rhythm": "Nhịp điệu",
    "fluency": "Trôi chảy",
}


def _pct(ok, total):
    return None if not total else 100.0 * ok / total


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def rhythm_score(npvi, ratio):
    """Chấm theo tỉ lệ so với tham chiếu bản ngữ: đạt mức bản ngữ = 100 điểm."""
    if npvi is None:
        return None
    base = _clamp((npvi - 0.5 * NATIVE_NPVI) / (0.5 * NATIVE_NPVI) * 100.0)
    if ratio is not None and NATIVE_RATIO > 1.0:
        r = _clamp((ratio - 1.0) / (NATIVE_RATIO - 1.0) * 100.0)
        return 0.6 * base + 0.4 * r
    return base


def fluency_score(fm):
    """Điểm trôi chảy: tốc độ hợp lý, ít ngắt sai chỗ, ít âm đệm."""
    if not fm.get("n_spoken") or not fm.get("rate_reliable"):
        return None        # bài quá ngắn để kết luận về tốc độ
    wpm = fm["wpm"]
    if 110 <= wpm <= 175:
        speed = 100.0
    elif wpm < 110:
        speed = _clamp(100.0 - (110 - wpm) * 1.6)
    else:
        speed = _clamp(100.0 - (wpm - 175) * 1.6)
    # mỗi chỗ ngắt sai trừ 8, mỗi âm đệm trừ 6
    penalty = 8.0 * len(fm.get("pauses", [])) + 6.0 * fm.get("fillers", 0)
    return _clamp(0.65 * speed + 35.0 - penalty)


def compute(metrics, fluency_metrics):
    """-> (dict điểm từng nhóm, điểm tổng, dict tử/mẫu để giải trình)."""
    parts = {
        "phoneme": _pct(metrics.get("phone_ok", 0), metrics.get("phone_total", 0)),
        "final": _pct(metrics.get("final_ok", 0), metrics.get("final_total", 0)),
        "stress": _pct(metrics.get("stress_ok", 0), metrics.get("stress_total", 0)),
        "linking": _pct(metrics.get("link_ok", 0), metrics.get("link_total", 0)),
        "rhythm": rhythm_score(metrics.get("npvi"), metrics.get("stress_ratio")),
        "fluency": fluency_score(fluency_metrics),
    }
    basis = {
        "phoneme": (metrics.get("phone_ok", 0), metrics.get("phone_total", 0), "âm"),
        "final": (metrics.get("final_ok", 0), metrics.get("final_total", 0), "phụ âm cuối"),
        "stress": (metrics.get("stress_ok", 0), metrics.get("stress_total", 0), "từ đa âm tiết"),
        "linking": (metrics.get("link_ok", 0), metrics.get("link_total", 0), "chỗ cần nối"),
        "rhythm": (None, None, "nPVI %.0f" % metrics["npvi"] if metrics.get("npvi") else "—"),
        "fluency": (None, None, "%.0f từ/phút" % fluency_metrics.get("wpm", 0)),
    }

    # Nhóm nào không đo được (vd bài không có từ đa âm tiết) thì bỏ khỏi điểm tổng
    # và chia lại trọng số, chứ không cho 0 điểm oan.
    usable = {k: v for k, v in parts.items() if v is not None}
    wsum = sum(WEIGHTS[k] for k in usable) or 1.0
    overall = sum(WEIGHTS[k] * v for k, v in usable.items()) / wsum
    return parts, round(overall, 1), basis


def band(score):
    """Nhãn ngắn để học viên biết mình đang ở đâu."""
    if score is None:
        return "—", "muted"
    if score >= 85:
        return "Tốt", "good"
    if score >= 70:
        return "Ổn", "ok"
    if score >= 55:
        return "Cần luyện", "warn"
    return "Yếu", "bad"
