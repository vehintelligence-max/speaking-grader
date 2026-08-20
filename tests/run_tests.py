#!/usr/bin/env python3
"""Bộ test cho tool chấm phát âm.

Hai phía đều phải đúng, và phía thứ hai mới là phía khó:

  KHÔNG BÁO OAN - audio bản ngữ chuẩn phải gần như sạch lỗi. Tool báo bừa thì
                  giáo viên mất niềm tin sau đúng một buổi.
  BẮT ĐƯỢC LỖI   - audio có lỗi thật phải bị bắt đúng tên lỗi. Tool im lặng cho
                  điểm cao thì vô dụng.

Audio sinh bằng `say` của macOS. Giọng bản ngữ (Samantha) làm mẫu đúng; giọng
tiếng Việt (Linh) đọc text tiếng Anh làm mẫu accent Việt nặng — nó rụng phụ âm
cuối, dùng nguyên âm tiếng Việt và đọc nhịp đều, đúng những gì cần bắt.

    ./venv/bin/python tests/run_tests.py
"""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from grader.pipeline import grade                 # noqa: E402
from grader.recognize import PhonemeRecognizer    # noqa: E402

AUDIO = ROOT / "tests" / "audio"
PASSAGE = ("Last weekend I asked my friends about the best places to visit. "
           "They suggested three beaches and a small museum. I decided to "
           "spend Saturday walking along the coast, and it turned out to be "
           "the most relaxing trip this year.")
SHORT = "I asked her about the books."
SHORT_DROPPED = "I ask her about the book."

CASES = [
    # (tên, giọng, tốc độ, text đọc, script chấm, kiểm tra)
    ("bản ngữ, đọc đúng", "Samantha", 165, SHORT, SHORT,
     dict(min_score=95, max_findings=0)),
    ("rụng -ed và -s", "Samantha", 165, SHORT_DROPPED, SHORT,
     dict(need_codes=["drop_ed", "drop_s"], max_findings=3)),
    ("bản ngữ, đoạn dài", "Samantha", 150, PASSAGE, PASSAGE,
     dict(min_score=88, max_findings=6)),
    ("accent Việt nặng", "Linh", 150, PASSAGE, PASSAGE,
     dict(max_score=70, need_kinds=["phoneme"], min_findings=8)),
]


def synth(voice, rate, text, out):
    if out.exists():
        return True
    out.parent.mkdir(parents=True, exist_ok=True)
    txt = out.with_suffix(".txt")
    txt.write_text(text, encoding="utf-8")
    r = subprocess.run(["say", "-v", voice, "-r", str(rate),
                        "-o", str(out), "-f", str(txt)], capture_output=True)
    return r.returncode == 0


def check(res, rule):
    """-> list mô tả những kỳ vọng bị vi phạm."""
    bad = []
    codes = {f["code"] for f in res["findings"]}
    kinds = {f["kind"] for f in res["findings"]}
    n = len(res["findings"])
    if "min_score" in rule and res["overall"] < rule["min_score"]:
        bad.append("điểm %.1f < %s" % (res["overall"], rule["min_score"]))
    if "max_score" in rule and res["overall"] > rule["max_score"]:
        bad.append("điểm %.1f > %s" % (res["overall"], rule["max_score"]))
    if "max_findings" in rule and n > rule["max_findings"]:
        bad.append("%d lỗi > %d" % (n, rule["max_findings"]))
    if "min_findings" in rule and n < rule["min_findings"]:
        bad.append("%d lỗi < %d" % (n, rule["min_findings"]))
    for c in rule.get("need_codes", []):
        if c not in codes:
            bad.append("thiếu mã lỗi '%s'" % c)
    for k in rule.get("need_kinds", []):
        if k not in kinds:
            bad.append("thiếu nhóm lỗi '%s'" % k)
    return bad


def main():
    rec = PhonemeRecognizer()
    passed = failed = skipped = 0

    for i, (name, voice, rate, text, script, rule) in enumerate(CASES):
        wav = AUDIO / ("%02d_%s.aiff" % (i, voice.lower()))
        if not synth(voice, rate, text, wav):
            print("SKIP  %-22s (không có giọng %s)" % (name, voice))
            skipped += 1
            continue

        res = grade(wav, script, recognizer=rec)
        bad = check(res, rule)
        m, fm = res["metrics"], res["fluency"]
        status = "PASS" if not bad else "FAIL"
        print("%s  %-22s điểm %5.1f | %2d lỗi | âm %d/%d | cuối %d/%d | "
              "nhấn %d/%d | nPVI %s"
              % (status, name, res["overall"], len(res["findings"]),
                 m["phone_ok"], m["phone_total"], m["final_ok"], m["final_total"],
                 m["stress_ok"], m["stress_total"],
                 "%.0f" % m["npvi"] if m["npvi"] else "—"))
        if bad:
            failed += 1
            for b in bad:
                print("        ! %s" % b)
        else:
            passed += 1
        for p in res["priorities"][:3]:
            print("        · [%d] %s (%dx)" % (p["severity"], p["label"], p["count"]))

    print("\n%d pass, %d fail, %d skip" % (passed, failed, skipped))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
