#!/usr/bin/env python3
"""Đo tham chiếu bản ngữ bằng chính pipeline này, ghi ra grader/calibration.json.

Vì sao cần: mốc thời gian ở đây suy ra từ đầu ra CTC, lượng tử hoá theo frame
20 ms. nPVI tính được vì thế thấp hơn con số 55-65 trong các nghiên cứu (họ gán
ranh giới âm bằng tay). Nếu lấy 55-65 làm chuẩn thì MỌI học viên đều bị kết luận
"nhịp thuần Việt", kể cả người nói tốt. Nên phải đo mẫu bản ngữ bằng đúng cách
đo dành cho học viên rồi so với nhau.

Mặc định dùng giọng TTS macOS làm mẫu. Khi có ghi âm thật của giáo viên bản ngữ,
truyền vào bằng --dir để thay: đó là tham chiếu tốt hơn nhiều.
"""

import argparse
import json
import pathlib
import statistics
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from grader.pipeline import grade                          # noqa: E402
from grader.recognize import PhonemeRecognizer             # noqa: E402

VOICES = ["Samantha", "Alex", "Daniel", "Karen", "Fred"]
PASSAGE = ("Last weekend I asked my friends about the best places to visit. "
           "They suggested three beaches and a small museum. I decided to "
           "spend Saturday walking along the coast, and it turned out to be "
           "the most relaxing trip this year.")


def measure(rec, audio, script):
    """Đo mẫu bằng ĐÚNG hàm grade() dùng cho học viên.

    Nếu đo tham chiếu bằng một đường code khác thì hai con số không so được với
    nhau, và toàn bộ việc chuẩn hoá mất ý nghĩa.
    """
    r = grade(audio, script, recognizer=rec)
    m = r["metrics"]
    return m["npvi"], m["stress_ratio"], m["phone_ok"] / max(1, m["phone_total"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", help="thư mục ghi âm bản ngữ thật (kèm .txt cùng tên)")
    ap.add_argument("--out", default="grader/calibration.json")
    args = ap.parse_args()

    rec = PhonemeRecognizer()
    rows = []

    if args.dir:
        d = pathlib.Path(args.dir)
        for a in sorted(d.iterdir()):
            if a.suffix.lower() not in (".wav", ".m4a", ".mp3", ".aiff", ".aac"):
                continue
            t = a.with_suffix(".txt")
            if not t.exists():
                print("bỏ qua %s (thiếu %s)" % (a.name, t.name))
                continue
            rows.append((a.name, measure(rec, a, t.read_text())))
    else:
        tmp = pathlib.Path("samples/_cal")
        tmp.mkdir(parents=True, exist_ok=True)
        txt = tmp / "passage.txt"
        txt.write_text(PASSAGE)
        for v in VOICES:
            wav = tmp / ("%s.aiff" % v)
            if not wav.exists():
                r = subprocess.run(["say", "-v", v, "-r", "150", "-o", str(wav),
                                    "-f", str(txt)], capture_output=True)
                if r.returncode != 0:
                    print("không có giọng %s, bỏ qua" % v)
                    continue
            rows.append((v, measure(rec, wav, PASSAGE)))

    if not rows:
        print("Không đo được mẫu nào.")
        return 1

    print("%-14s %8s %8s %8s" % ("MẪU", "nPVI", "TỈ LỆ", "ĐÚNG ÂM"))
    npvis, ratios = [], []
    for name, (n, r, acc) in rows:
        print("%-14s %8s %8s %7.0f%%" % (
            name, "%.1f" % n if n else "—", "%.2f" % r if r else "—", acc * 100))
        if n:
            npvis.append(n)
        if r:
            ratios.append(r)

    out = dict(
        npvi=round(statistics.median(npvis), 1) if npvis else 42.0,
        stress_ratio=round(statistics.median(ratios), 2) if ratios else 1.45,
        n_samples=len(rows),
        source="ghi âm bản ngữ: %s" % args.dir if args.dir else "TTS macOS",
        samples={n: dict(npvi=v[0], stress_ratio=v[1]) for n, v in rows},
    )
    pathlib.Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2))
    print("\nTHAM CHIẾU (trung vị): nPVI %.1f | tỉ lệ giảm âm %.2f  ->  %s"
          % (out["npvi"], out["stress_ratio"], args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
