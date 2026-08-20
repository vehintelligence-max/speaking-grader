"""Độ trôi chảy: tốc độ nói, khoảng nghỉ bất thường, âm đệm.

Tất cả mốc thời gian đã có sẵn từ bước khớp âm vị, nên phần này gần như miễn phí.
"""

from .diagnose import Finding

PAUSE_GAP = 0.25          # nghỉ giữa hai từ, không có dấu câu
PAUSE_GAP_PUNCT = 0.90    # nghỉ ở chỗ có dấu câu thì được phép dài hơn
WPM_LOW, WPM_OK_LO, WPM_OK_HI, WPM_HIGH = 90, 110, 175, 200
MIN_WORDS_FOR_RATE = 12   # dưới ngưỡng này tốc độ đo được chỉ là nhiễu


def analyse(words, slots, times, actual, total_dur, word_findings):
    """-> (list Finding, dict metrics)."""
    spans = {}
    for w in words:
        idxs = [s.index for s in slots if s.word_index == w.index and s.index in times]
        if idxs:
            spans[w.index] = (times[min(idxs)][0], times[max(idxs)][1])

    if not spans:
        return [], dict(wpm=0.0, syll_per_s=0.0, pauses=[], pause_total=0.0,
                        speech_dur=0.0, n_spoken=0, fillers=0)

    ordered = sorted(spans.items())
    speech_start = ordered[0][1][0]
    speech_end = ordered[-1][1][1]
    speech_dur = max(1e-6, speech_end - speech_start)

    findings, pauses, pause_total = [], [], 0.0
    for (ia, sa), (ib, sb) in zip(ordered, ordered[1:]):
        gap = sb[0] - sa[1]
        if gap <= 0:
            continue
        limit = PAUSE_GAP_PUNCT if words[ia].followed_by_punct else PAUSE_GAP
        pause_total += gap
        if gap > limit:
            pauses.append(dict(after=words[ia].text, before=words[ib].text,
                               gap_ms=round(gap * 1000), at=round(sa[1], 2)))

    n_spoken = len(spans)
    n_syll = sum(words[i].n_syllables for i in spans)
    wpm = n_spoken / (speech_dur / 60.0)
    articulation = max(1e-6, speech_dur - pause_total)
    syll_per_s = n_syll / articulation

    # Nghỉ vụn: nhiều chỗ ngắt ngắn còn hại hơn một chỗ ngắt dài.
    if len(pauses) >= 2:
        worst = sorted(pauses, key=lambda p: -p["gap_ms"])[:4]
        findings.append(Finding(
            kind="fluency", code="choppy",
            label="Ngắt %d chỗ không đúng chỗ trong câu" % len(pauses),
            why="Ngắt giữa cụm từ làm người nghe phải tự ghép lại nghĩa. Nghỉ chỉ "
                "nên xuất hiện ở ranh giới ý, thường là chỗ có dấu câu.",
            fix="Chia câu thành cụm nghĩa và chỉ nghỉ ở ranh giới cụm. Dài nhất: %s."
                % ", ".join("sau '%s' (%d ms)" % (p["after"], p["gap_ms"])
                            for p in worst),
            severity=2,
            detail="; ".join("%s | %s: %d ms" % (p["after"], p["before"], p["gap_ms"])
                             for p in pauses)))
    elif len(pauses) == 1:
        p = pauses[0]
        findings.append(Finding(
            kind="fluency", code="one_pause",
            label="Một chỗ ngắt bất thường sau '%s' (%d ms)" % (p["after"], p["gap_ms"]),
            why="Chỗ này không có dấu câu nên người nghe không chờ một khoảng nghỉ.",
            fix="Đọc liền '%s %s'." % (p["after"], p["before"]),
            severity=1, start=p["at"], detail="%d ms" % p["gap_ms"]))

    rate_ok = n_spoken >= MIN_WORDS_FOR_RATE
    if not rate_ok:
        pass
    elif wpm < WPM_LOW:
        findings.append(Finding(
            kind="fluency", code="too_slow",
            label="Tốc độ quá chậm: %.0f từ/phút" % wpm,
            why="Bài đọc tự nhiên thường 110–175 từ/phút. Chậm hơn nhiều thường là "
                "do dừng lại nghĩ cách phát âm từng từ.",
            fix="Đọc thầm cả câu một lượt trước khi ghi âm, rồi đọc liền mạch.",
            severity=2, detail="%.0f wpm | %.1f âm tiết/giây" % (wpm, syll_per_s)))
    elif wpm < WPM_OK_LO:
        findings.append(Finding(
            kind="fluency", code="slow",
            label="Tốc độ hơi chậm: %.0f từ/phút" % wpm,
            why="Dưới mức tự nhiên 110–175 từ/phút một chút.",
            fix="Tăng tốc ở các từ chức năng (a, the, of, to), giữ nguyên tốc độ ở "
                "từ mang nghĩa.",
            severity=1, detail="%.0f wpm | %.1f âm tiết/giây" % (wpm, syll_per_s)))
    elif wpm > WPM_HIGH:
        findings.append(Finding(
            kind="fluency", code="too_fast",
            label="Tốc độ quá nhanh: %.0f từ/phút" % wpm,
            why="Nói nhanh thường kéo theo rụng âm cuối và nuốt âm tiết.",
            fix="Giảm tốc và cường điệu âm cuối; nhanh mà mất âm thì người nghe "
                "vẫn không hiểu.",
            severity=2, detail="%.0f wpm | %.1f âm tiết/giây" % (wpm, syll_per_s)))

    fillers = sum(1 for f in word_findings if f.code == "filler")
    if fillers >= 2:
        findings.append(Finding(
            kind="fluency", code="fillers",
            label="Có %d âm đệm ngập ngừng ('ừm', 'à')" % fillers,
            why="Âm đệm làm loãng câu và là dấu hiệu chưa quen mặt chữ.",
            fix="Đọc trước 1–2 lượt không ghi âm. Khi bí, nghỉ im lặng thay vì đệm âm.",
            severity=1))

    metrics = dict(wpm=wpm, syll_per_s=syll_per_s, pauses=pauses,
                   rate_reliable=rate_ok,
                   pause_total=pause_total, speech_dur=speech_dur,
                   n_spoken=n_spoken, n_words=len(words), fillers=fillers,
                   total_dur=total_dur)
    return findings, metrics
