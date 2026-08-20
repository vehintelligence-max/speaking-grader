"""Từ diff âm vị -> chẩn đoán lỗi có tên, có bằng chứng, có mốc thời gian."""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from . import vn_rules
from .align import DEL, INS, MATCH, SUB, needleman_wunsch
from .phoneset import ipa, ipa_seq, is_vowel
from .prosody import f0_track, npvi, rms_track, span_mean, vowel_extents

LINK_GAP = 0.09              # nghỉ quá 90 ms ở chỗ đáng lẽ nối -> không nối
MIN_VOWELS_FOR_RHYTHM = 8    # ít hơn thì nPVI chỉ là nhiễu
STRESS_MARGIN = 0.22         # phải hơn rõ rệt mới kết luận nhấn sai
FINAL_LENGTHENING = 1.25     # âm tiết cuối từ tự nhiên dài hơn, phải bù lại


@dataclass
class Finding:
    kind: str                  # phoneme | stress | linking | rhythm | fluency
    code: str
    label: str
    why: str
    fix: str
    severity: int
    word: Optional[str] = None
    word_index: Optional[int] = None
    start: Optional[float] = None
    end: Optional[float] = None
    detail: str = ""


@dataclass
class WordResult:
    index: int
    text: str
    canonical_ipa: str
    actual_ipa: str
    start: Optional[float]
    end: Optional[float]
    n_phones: int
    n_correct: int
    findings: List[Finding] = field(default_factory=list)
    vowel_ms: List[float] = field(default_factory=list)
    expected_stress: Optional[int] = None
    detected_stress: Optional[int] = None
    spoken: bool = True

    @property
    def accuracy(self):
        return self.n_correct / self.n_phones if self.n_phones else 0.0


def align_script(words, slots, actual):
    """Khớp chuỗi chuẩn với chuỗi thực tế. -> (ops, times).

    times[i] = (start, end, coarse thực tế, token thực tế, conf) cho âm chuẩn i.
    """
    ops = needleman_wunsch([s.coarse for s in slots], [a.coarse for a in actual])
    times = {}
    for op in ops:
        if op["op"] in (MATCH, SUB):
            a = actual[op["actual_j"]]
            times[op["canon_i"]] = (a.start, a.end, a.coarse, a.token,
                                    a.conf, a.peak)
    return ops, times


def choose_variants(words, slots, actual, times):
    """Với từ có nhiều cách đọc, chọn cách đọc khớp nhất với âm thực tế.

    Không làm bước này thì học viên đọc 'saturday' = /sætərdeɪ/ trong khi CMUdict
    trả biến thể /sætərdi/ sẽ bị báo sai nguyên âm cuối — lỗi của từ điển, không
    phải của học viên.
    """
    from .lexicon import all_variants

    variants = all_variants(" ".join(w.text for w in words))
    choice = {}
    for w in words:
        cands = variants.get(w.index) or []
        if len(cands) < 2:
            continue
        idxs = [s.index for s in slots if s.word_index == w.index and s.index in times]
        if not idxs:
            continue
        t0 = times[min(idxs)][0] - 0.04
        t1 = times[max(idxs)][1] + 0.04
        heard = [a.coarse for a in actual if a.start >= t0 and a.end <= t1]
        if not heard:
            continue
        # Chỉ cho đổi sang biến thể khác về NGUYÊN ÂM hoặc trọng âm, không cho
        # đổi sang biến thể có ÍT PHỤ ÂM hơn. CMUdict có cả "asked" = /æst/ (nói
        # nhanh, rụng /k/). Nếu cho phép chọn nó thì học viên giản lược cụm phụ
        # âm cuối sẽ được tha bổng — đúng cái lỗi tool này sinh ra để bắt.
        n_cons0 = sum(1 for p in cands[w.variant] if not is_vowel(p))
        costs = []
        for vi, v in enumerate(cands):
            if sum(1 for p in v if not is_vowel(p)) < n_cons0:
                continue
            ops = needleman_wunsch(v, heard)
            costs.append((sum(o["cost"] for o in ops), vi))
        if not costs:
            continue
        best = min(costs)[1]
        if best != w.variant:
            choice[w.index] = best
    return choice


def analyse(words, slots, actual, pcm, sr, t_offset=0.0):
    """-> (list WordResult, list Finding toàn cục, dict metrics).

    Phân vai của từng phép đo:
      giải mã tự do  -> âm nào thực sự phát ra          (bắt lỗi)
      đỉnh CTC       -> âm đó xuất hiện ở giây nào      (khoảng nghỉ, nối âm)
      năng lượng     -> nguyên âm dài bao nhiêu         (trọng âm, nhịp)

    t_offset: mọi mốc thời gian đưa vào/đưa ra đều theo toạ độ FILE GỐC, còn pcm
    ở đây đã bị cắt lặng và đệm hai đầu. Phải trừ lại offset trước khi tra cường
    độ / cao độ, không thì đo lệch đúng bằng phần đã cắt.
    """
    ops, times = align_script(words, slots, actual)
    tt = {i: (v[0], v[1]) for i, v in times.items()}

    rms, rms_hop = rms_track(pcm, sr)
    f0, f0_hop = f0_track(pcm, sr)

    # Độ dài nguyên âm đo bằng bề rộng đỉnh năng lượng, không lấy từ CTC.
    nuc_peaks = sorted(((s.index, times[s.index][5]) for s in slots
                        if s.role == "nucleus" and s.index in times),
                       key=lambda kv: kv[1])
    vdur = vowel_extents(rms, rms_hop,
                         [(k, t - t_offset) for k, t in nuc_peaks])

    slot_by_index = {s.index: s for s in slots}
    by_word = {w.index: [] for w in words}
    ok_slots = set()          # âm chuẩn được coi là đọc đúng

    cluster_size = {
        w.index: sum(1 for s in slots
                     if s.word_index == w.index and s.in_final_cluster)
        for w in words
    }

    # -------------------------------------------------- lỗi ở mức âm vị ----
    for k, op in enumerate(ops):
        if op["op"] == MATCH:
            ok_slots.add(op["canon_i"])
            continue

        if op["op"] == SUB:
            slot = slot_by_index[op["canon_i"]]
            w = words[slot.word_index]
            a = actual[op["actual_j"]]
            if vn_rules.acceptable_substitution(op["canon"], op["actual"],
                                               slot, w, a.conf):
                ok_slots.add(op["canon_i"])
                continue
            e = vn_rules.substitution_error(op["canon"], op["actual"], slot, w)
            by_word[w.index].append(Finding(
                kind="phoneme", word=w.text, word_index=w.index,
                start=a.start, end=a.end,
                detail="chuẩn /%s/ → đọc /%s/ (tin cậy %.0f%%)"
                       % (ipa(op["canon"]), ipa(op["actual"]), a.conf * 100),
                **e))

        elif op["op"] == DEL:
            slot = slot_by_index[op["canon_i"]]
            w = words[slot.word_index]
            e = vn_rules.deletion_error(slot, w, cluster_size[w.index])
            ws, we = _word_span(slots, tt, w.index)
            by_word[w.index].append(Finding(
                kind="phoneme", word=w.text, word_index=w.index,
                start=ws, end=we,
                detail="thiếu /%s/ (chuẩn: /%s/)"
                       % (ipa(slot.coarse), ipa_seq(w.coarse)),
                **e))

        else:   # INS
            a = actual[op["actual_j"]]
            prev_slot = next_slot = None
            for m in range(k - 1, -1, -1):
                if ops[m]["canon_i"] is not None:
                    prev_slot = slot_by_index[ops[m]["canon_i"]]
                    break
            for m in range(k + 1, len(ops)):
                if ops[m]["canon_i"] is not None:
                    next_slot = slot_by_index[ops[m]["canon_i"]]
                    break
            if a.conf < vn_rules.MIN_CONFIDENCE:
                continue
            e = vn_rules.insertion_error(a, prev_slot, next_slot, a.dur)
            anchor = prev_slot or next_slot
            wi = anchor.word_index if anchor else None
            by_word.setdefault(wi, []).append(Finding(
                kind="phoneme", word=words[wi].text if wi is not None else None,
                word_index=wi, start=a.start, end=a.end,
                detail="phát ra thêm /%s/ (%s)" % (ipa(a.coarse), a.token), **e))

    # ---------------------------------------------------- theo từng từ ----
    results = []
    stress_total = stress_ok = 0
    for w in words:
        w_slots = [s for s in slots if s.word_index == w.index]
        act = [times[s.index][2] for s in w_slots if s.index in times]
        ws, we = _word_span(slots, tt, w.index)
        wr = WordResult(
            index=w.index, text=w.text,
            canonical_ipa=ipa_seq(w.coarse), actual_ipa=ipa_seq(act),
            start=ws, end=we, n_phones=len(w_slots),
            n_correct=sum(1 for s in w_slots if s.index in ok_slots),
            findings=sorted(by_word.get(w.index, []), key=lambda f: -f.severity),
            expected_stress=w.stress_index, spoken=bool(act))

        f = _check_stress(w, w_slots, times, tt, vdur, rms, rms_hop, f0, f0_hop,
                          wr, ws, we, t_offset)
        if f is not None:
            stress_total += 1
            if f is False:
                stress_ok += 1
            else:
                wr.findings.append(f)
        results.append(wr)

    # ------------------------------------------------------------ nối âm ----
    globals_, link_total, link_ok = [], 0, 0
    for a_w, b_w in zip(words, words[1:]):
        if a_w.followed_by_punct:
            continue                     # có dấu câu, được phép nghỉ
        a_slots = [s for s in slots if s.word_index == a_w.index]
        b_slots = [s for s in slots if s.word_index == b_w.index]
        if not a_slots or not b_slots:
            continue
        last, first = a_slots[-1], b_slots[0]
        if last.index not in times or first.index not in times:
            continue
        c_last, c_first = last.coarse, first.coarse
        if is_vowel(c_last):
            continue                     # nguyên âm + nguyên âm: bỏ qua ở v1
        same = (c_last == c_first)
        if not (same or is_vowel(c_first)):
            continue
        link_total += 1
        gap = tt[first.index][0] - tt[last.index][1]
        if gap <= LINK_GAP:
            link_ok += 1
            continue
        reason = ("hai phụ âm giống nhau, phải đọc thành một âm kéo dài"
                  if same else "phụ âm cuối phải nối sang nguyên âm đầu")
        globals_.append(Finding(
            kind="linking", code="no_linking",
            label="Không nối âm: '%s %s'" % (a_w.text, b_w.text),
            why="Có khoảng nghỉ %d ms giữa hai từ, %s. Đọc rời từng từ là lý do "
                "chính khiến câu nghe cứng và chậm." % (round(gap * 1000), reason),
            fix="Đọc liền như một từ: '%s%s' — /%s/ + /%s/ dính vào nhau, không ngắt."
                % (a_w.text, b_w.text, ipa(c_last), ipa(c_first)),
            severity=2, word="%s %s" % (a_w.text, b_w.text), word_index=a_w.index,
            start=times[last.index][1], end=times[first.index][0],
            detail="khoảng nghỉ %d ms" % round(gap * 1000)))

    # --------------------------------------------------------- nhịp điệu ----
    v_durs, stressed, unstressed = [], [], []
    for s in slots:
        if s.role != "nucleus" or s.index not in times:
            continue
        d = vdur.get(s.index, 0.0)
        if d <= 0:
            continue
        v_durs.append(d)
        (stressed if s.stress == 1 else unstressed).append(d)

    enough = len(v_durs) >= MIN_VOWELS_FOR_RHYTHM
    n_pvi = npvi(v_durs) if enough else None
    ratio = None
    if enough and len(stressed) >= 2 and len(unstressed) >= 2 \
            and np.mean(unstressed) > 0:
        ratio = float(np.mean(stressed)) / float(np.mean(unstressed))

    globals_ += _rhythm_findings(n_pvi, ratio)

    # Âm cuối: nhóm lỗi học viên Việt sai nhiều nhất, tách riêng để chấm.
    final_total = final_ok = 0
    for s in slots:
        if is_vowel(s.coarse) or not (s.is_word_final or s.in_final_cluster):
            continue
        final_total += 1
        if s.index in ok_slots:
            final_ok += 1

    metrics = dict(
        npvi=n_pvi, stress_ratio=ratio, n_vowels=len(v_durs),
        phone_total=len(slots), phone_ok=len(ok_slots),
        final_total=final_total, final_ok=final_ok,
        stress_total=stress_total, stress_ok=stress_ok,
        link_total=link_total, link_ok=link_ok,
        ops=ops, times=tt, produced=set(times),
    )
    return results, globals_, metrics


# ------------------------------------------------------------------ helpers --

def _word_span(slots, times, w_index):
    idxs = [s.index for s in slots if s.word_index == w_index and s.index in times]
    if not idxs:
        return None, None
    return times[min(idxs)][0], times[max(idxs)][1]


def _norm(vals):
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-9:
        return [0.5] * len(vals)
    return [(v - lo) / (hi - lo) for v in vals]


def _check_stress(w, w_slots, times, tt, vdur, rms, rms_hop, f0, f0_hop,
                  wr, ws, we, t_offset=0.0):
    """-> None (không xét được) | False (đúng) | Finding (sai).

    Chỉ dùng ĐỘ DÀI NGUYÊN ÂM, không dùng cả âm tiết: coda của âm tiết cuối
    ('week-END', 'beach-ES') tự làm âm tiết đó dài ra, và tiếng Anh còn kéo dài
    âm tiết cuối từ theo quán tính. Dùng độ dài âm tiết là báo nhấn sai ở gần như
    mọi từ hai âm tiết.
    """
    if w.n_syllables < 2 or w.stress_index is None or not wr.spoken:
        return None

    prom, durs = [], []
    for syl in w.syllables:
        nuc = [s.index for s in w_slots
               if s.syl_index == syl.index and s.role == "nucleus"
               and s.index in times]
        if not nuc:
            prom.append(None)
            durs.append(0.0)
            continue
        t0, t1 = tt[nuc[0]][0], tt[nuc[0]][1]
        d = vdur.get(nuc[0], 0.0)
        if syl.index == w.n_syllables - 1:
            d /= FINAL_LENGTHENING       # bù hiện tượng kéo dài âm tiết cuối
        durs.append(round(vdur.get(nuc[0], 0.0) * 1000, 1))
        a0, a1 = t0 - t_offset, t1 - t_offset      # về toạ độ của pcm đang giữ
        prom.append((d,
                     span_mean(rms, rms_hop, a0, a1),
                     span_mean(f0, f0_hop, a0, a1, positive_only=True)))
    wr.vowel_ms = durs

    valid = [i for i, p in enumerate(prom) if p is not None]
    if len(valid) < 2 or w.stress_index not in valid:
        return None

    d_n = _norm([prom[i][0] for i in valid])
    e_n = _norm([prom[i][1] for i in valid])
    p_vals = [prom[i][2] for i in valid]
    p_n = _norm(p_vals) if any(v > 0 for v in p_vals) else [0.5] * len(valid)
    # Độ dài nguyên âm là tín hiệu đáng tin nhất ở đây. Cao độ tuy là tín hiệu
    # trọng âm mạnh trong tiếng Anh nhưng ngữ điệu của CẢ CÂU lấn vào phép so
    # sánh trong MỘT TỪ (âm tiết cuối 'walk-ing' bị đội cao độ lên vì câu lên
    # giọng), nên chỉ cho nó trọng số nhỏ nhất.
    score = [0.45 * d_n[k] + 0.30 * e_n[k] + 0.25 * p_n[k]
             for k in range(len(valid))]

    detected = valid[int(np.argmax(score))]
    wr.detected_stress = detected
    exp = w.stress_index
    if detected == exp:
        return False

    margin = score[valid.index(detected)] - score[valid.index(exp)]
    # Chỉ báo lỗi khi học viên nhấn vào âm tiết KHÔNG có trọng âm nào. Nhấn vào
    # âm tiết mang trọng âm phụ (weekend, Saturday) không phải lỗi.
    detected_stress = w.syllables[detected].stress
    if margin <= STRESS_MARGIN or detected_stress != 0:
        return False

    syl_txt = " - ".join("".join(w.phones[i] for i in s.phone_indices)
                         for s in w.syllables)
    return Finding(
        kind="stress", code="wrong_stress",
        label="Sai trọng âm '%s': nhấn âm tiết %d, đúng phải là %d"
              % (w.text, detected + 1, exp + 1),
        why="Trọng âm sai làm người nghe khó nhận ra từ, đôi khi thành từ khác "
            "hẳn. Tiếng Việt không có trọng âm từ nên đây là lỗi rất phổ biến.",
        fix="Cấu trúc: %s. Nhấn âm tiết %d — đọc nó DÀI hơn, TO hơn và CAO hơn; "
            "các âm tiết còn lại đọc nhanh và lỏng." % (syl_txt, exp + 1),
        severity=3, word=w.text, word_index=w.index, start=ws, end=we,
        detail="độ dài nguyên âm (ms): %s" % durs)


def _rhythm_findings(n_pvi, ratio):
    from .scoring import NATIVE_NPVI, NATIVE_RATIO

    out = []
    if n_pvi is not None and n_pvi < NATIVE_NPVI * 0.80:
        out.append(Finding(
            kind="rhythm", code="syllable_timed",
            label="Nhịp câu đều đều — nghe rất 'thuần Việt' (nPVI %.0f)" % n_pvi,
            why="nPVI đo độ chênh dài–ngắn giữa các nguyên âm liền kề. Đo bằng "
                "chính tool này trên giọng bản ngữ được khoảng %.0f, vì âm tiết "
                "nhấn dài hẳn ra và âm tiết không nhấn bị rút ngắn. Bài này %.0f, "
                "tức các nguyên âm dài gần bằng nhau — đúng đặc điểm nhịp tiếng "
                "Việt, nơi mọi âm tiết đều nhau." % (NATIVE_NPVI, n_pvi),
            fix="Chọn 1–2 từ quan trọng nhất mỗi câu, đọc chúng dài gấp đôi; các "
                "từ chức năng (a, the, of, to, and) đọc thật nhanh và nhẹ.",
            severity=3,
            detail="nPVI %.1f | tham chiếu bản ngữ %.0f" % (n_pvi, NATIVE_NPVI)))

    if ratio is not None and ratio < NATIVE_RATIO * 0.85:
        out.append(Finding(
            kind="rhythm", code="no_reduction_global",
            label="Không giảm âm tiết không nhấn (tỉ lệ %.2f)" % ratio,
            why="Nguyên âm ở âm tiết nhấn chỉ dài hơn âm tiết không nhấn %.0f%%. "
                "Đo trên giọng bản ngữ bằng cùng cách này được %.2f. Đọc rõ đều "
                "mọi âm tiết làm mất hẳn nhạc điệu tiếng Anh."
                % ((ratio - 1) * 100, NATIVE_RATIO),
            fix="Luyện với từ nhiều âm tiết: 'comfortable' = COMF-tər-bəl (3 âm "
                "tiết, không phải 4), 'vegetable' = VEJ-tə-bəl.",
            severity=2,
            detail="tỉ lệ %.2f | tham chiếu bản ngữ %.2f" % (ratio, NATIVE_RATIO)))
    return out
