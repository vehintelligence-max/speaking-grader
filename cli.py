#!/usr/bin/env python3
"""Chấm một file ghi âm read-aloud.

    ./venv/bin/python cli.py --audio bai.m4a --script "I asked her about the books."
    ./venv/bin/python cli.py --audio bai.m4a --script-file de.txt --html bao_cao.html
"""

import argparse
import json
import sys

from grader.pipeline import grade
from grader.scoring import LABELS, band


def main():
    ap = argparse.ArgumentParser(description="Chấm phát âm bài read-aloud")
    ap.add_argument("--audio", required=True, help="file ghi âm (m4a/mp3/wav/...)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--script", help="text bài đọc")
    g.add_argument("--script-file", help="file .txt chứa bài đọc")
    ap.add_argument("--json", help="ghi kết quả đầy đủ ra file JSON")
    ap.add_argument("--html", help="ghi báo cáo HTML ra file")
    ap.add_argument("--quiet", action="store_true", help="không in ra terminal")
    args = ap.parse_args()

    script = args.script
    if args.script_file:
        with open(args.script_file, encoding="utf-8") as f:
            script = f.read()

    res = grade(args.audio, script)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        print("JSON  -> %s" % args.json, file=sys.stderr)

    if args.html:
        from grader.report import write_html
        write_html(res, args.html)
        print("HTML  -> %s" % args.html, file=sys.stderr)

    if args.quiet:
        return

    print("=" * 74)
    print("ĐIỂM TỔNG: %.1f/100   (%s)   |   %.1fs, %d từ"
          % (res["overall"], band(res["overall"])[0], res["duration"], res["n_words"]))
    print("=" * 74)
    for k, v in res["scores"].items():
        ok, total, unit = res["score_basis"][k]
        basis = "%s/%s %s" % (ok, total, unit) if total else unit
        print("  %-16s %s   (%s)"
              % (LABELS[k], "%5.1f" % v if v is not None else "    —", basis))

    print("\n--- 3 VIỆC CẦN SỬA TRƯỚC " + "-" * 47)
    if not res["priorities"]:
        print("  Không phát hiện lỗi đáng kể.")
    for i, p in enumerate(res["priorities"], 1):
        print("\n%d. %s  [%d lần]" % (i, p["label"], p["count"]))
        if p["words"]:
            print("   Từ: %s" % ", ".join(p["words"][:8]))
        print("   Vì sao: %s" % p["why"])
        print("   Sửa:    %s" % p["fix"])

    print("\n--- CHI TIẾT TỪNG TỪ " + "-" * 51)
    print("%-14s %-16s %-16s %5s  %s"
          % ("TỪ", "CHUẨN", "ĐỌC RA", "ĐÚNG", "LỖI"))
    for w in res["words"]:
        errs = "; ".join(f["label"] for f in w["findings"]) or "-"
        print("%-14s /%-15s /%-15s %2d/%-2d  %s"
              % (w["text"], w["canonical_ipa"] + "/", w["actual_ipa"] + "/",
                 w["n_correct"], w["n_phones"], errs))

    fm = res["fluency"]
    print("\n--- TRÔI CHẢY " + "-" * 58)
    print("  tốc độ %.0f từ/phút | %.1f âm tiết/giây | %d chỗ ngắt sai | %d âm đệm"
          % (fm["wpm"], fm["syll_per_s"], len(fm["pauses"]), fm["fillers"]))
    m = res["metrics"]
    print("  nhịp: nPVI %s | tỉ lệ giảm âm %s"
          % ("%.1f" % m["npvi"] if m["npvi"] else "—",
             "%.2f" % m["stress_ratio"] if m["stress_ratio"] else "—"))


if __name__ == "__main__":
    main()
