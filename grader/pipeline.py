"""Ghép toàn bộ các bước thành một hàm grade()."""

from collections import OrderedDict
from dataclasses import asdict

from . import fluency as fluency_mod
from . import scoring
import numpy as np

from .audio import load_audio, trim_silence

PAD_HEAD, PAD_TAIL = 0.10, 0.25   # giây
from .diagnose import align_script, analyse, choose_variants
from .lexicon import parse_script
from .phoneset import ipa_seq
from .recognize import PhonemeRecognizer


def _priorities(all_findings, limit=3):
    """Gộp lỗi trùng mã lại thành danh sách việc cần sửa, nặng nhất lên trước.

    Học viên không sửa được 40 lỗi rời. Họ sửa được 3 nhóm.
    """
    groups = OrderedDict()
    for f in all_findings:
        g = groups.setdefault(f.code, dict(
            code=f.code, kind=f.kind, label=f.label, why=f.why, fix=f.fix,
            severity=f.severity, count=0, words=[]))
        g["count"] += 1
        if f.word and f.word not in g["words"]:
            g["words"].append(f.word)
    ranked = sorted(groups.values(),
                    key=lambda g: (-g["severity"], -g["count"], g["code"]))
    return ranked[:limit], ranked


def grade(audio_path, script, device=None, recognizer=None):
    pcm_raw, sr = load_audio(audio_path)
    total_dur = len(pcm_raw) / float(sr)
    pcm, offset = trim_silence(pcm_raw, sr)
    # wav2vec2 cần ngữ cảnh hai bên mới phát ra được âm ở sát biên. Không đệm thì
    # phụ âm cuối của câu bị bỏ và tool báo oan học viên là "rụng âm cuối".
    head = int(PAD_HEAD * sr)
    pcm = np.pad(pcm, (head, int(PAD_TAIL * sr)))
    offset -= PAD_HEAD

    words, slots = parse_script(script)
    if not words:
        raise ValueError("Script không có từ nào đọc được.")

    rec = recognizer or PhonemeRecognizer(device=device)
    logits, _ = rec._logits(pcm, sr)
    actual = rec.decode_free(logits)
    # Trả mốc thời gian về hệ toạ độ của file gốc để giáo viên tua đúng chỗ.
    # Phải dịch CẢ BA mốc: bỏ sót `peak` là vowel_extents đo sai bề rộng nguyên
    # âm, và hệ quả là báo sai trọng âm ở những từ đọc đúng.
    for a in actual:
        a.start += offset
        a.end += offset
        a.peak += offset

    # Lượt 1 chỉ để biết mỗi từ nằm ở đâu, từ đó chọn biến thể phát âm khớp nhất
    # (saturday = /-deɪ/ hay /-di/), rồi khớp lại lần hai trên chuỗi chuẩn đã đúng.
    _, times0 = align_script(words, slots, actual)
    choice = choose_variants(words, slots, actual, times0)
    if choice:
        words, slots = parse_script(script, variant_choice=choice)

    results, global_findings, metrics = analyse(words, slots, actual, pcm, sr,
                                               t_offset=offset)
    word_findings = [f for wr in results for f in wr.findings]
    flu_findings, flu_metrics = fluency_mod.analyse(
        words, slots, metrics["times"], actual, total_dur, word_findings)

    all_findings = word_findings + global_findings + flu_findings
    all_findings.sort(key=lambda f: (-f.severity, f.start if f.start else 0.0))
    scores, overall, basis = scoring.compute(metrics, flu_metrics)
    top, ranked = _priorities(all_findings)

    return dict(
        audio=str(audio_path),
        script=script,
        duration=round(total_dur, 2),
        n_words=len(words),
        variants_adjusted=len(choice),
        canonical_ipa=" ".join(ipa_seq(w.coarse) for w in words),
        actual_ipa=" ".join(a.token for a in actual),
        words=[asdict(wr) for wr in results],
        findings=[asdict(f) for f in all_findings],
        priorities=top,
        error_groups=ranked,
        scores=scores,
        score_basis={k: list(v) for k, v in basis.items()},
        overall=overall,
        metrics=dict(npvi=metrics["npvi"], stress_ratio=metrics["stress_ratio"],
                     phone_ok=metrics["phone_ok"], phone_total=metrics["phone_total"],
                     final_ok=metrics["final_ok"], final_total=metrics["final_total"],
                     stress_ok=metrics["stress_ok"], stress_total=metrics["stress_total"],
                     link_ok=metrics["link_ok"], link_total=metrics["link_total"]),
        fluency=flu_metrics,
    )
