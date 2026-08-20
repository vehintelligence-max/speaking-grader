"""Chế độ shadowing: nghe câu mẫu, nhại theo, chấm tức thì.

Câu mẫu được tổng hợp bằng `say` của macOS (giọng bản ngữ) và cache lại thành
m4a để trình duyệt nào cũng phát được. Khi deploy lên Linux thì thay _synth()
bằng TTS khác (Edge-TTS/Piper) hoặc dùng clip thu sẵn — phần còn lại giữ nguyên.
"""

import hashlib
import pathlib
import subprocess

CACHE = pathlib.Path(__file__).parent / "shadow_cache"

# Giọng mẫu: tên hiển thị -> (tên voice của `say`, mô tả ngắn)
VOICES = {
    "samantha": ("Samantha", "Nữ — Mỹ"),
    "daniel":   ("Daniel",   "Nam — Anh"),
    "karen":    ("Karen",    "Nữ — Úc"),
    "moira":    ("Moira",    "Nữ — Ireland"),
}
DEFAULT_VOICE = "samantha"

# tốc độ: bình thường ~175 wpm, chậm để nghe rõ từng âm
RATES = {"normal": 170, "slow": 115}

# Bài 1: mỗi câu nhắm một nhóm lỗi phổ biến của người Việt.
LESSON = [
    dict(text="I asked my friends about the books.",
         focus="Âm cuối + cụm phụ âm: asked /skt/, friends /ndz/, books /ks/"),
    dict(text="She watched three movies last night.",
         focus="Đuôi -ed: watched /tʃt/, th: three"),
    dict(text="Think about it and tell me the truth.",
         focus="Âm th đầu và cuối từ: think, the, truth"),
    dict(text="He wants a cup of coffee and some milk.",
         focus="Nối âm: wants‿a, cup‿of; âm cuối: milk /lk/"),
    dict(text="We visited the museum along the river.",
         focus="Trọng âm: VI-si-ted, mu-SE-um, a-LONG"),
    dict(text="Turn it off and put it on the desk.",
         focus="Nối âm: turn‿it‿off, put‿it‿on; cuối: desk /sk/"),
    dict(text="The world's biggest problems need simple answers.",
         focus="Cụm phụ âm khó: world's /rldz/, problems /mz/"),
    dict(text="My parents lived in a small village for years.",
         focus="Đuôi -ed thành /d/: lived; -s: parents, years"),
]


def synth(idx, voice=DEFAULT_VOICE, rate="normal"):
    """Trả về đường dẫn file m4a của câu mẫu, tổng hợp lần đầu rồi cache."""
    sent = LESSON[idx]["text"]
    vname, _ = VOICES.get(voice, VOICES[DEFAULT_VOICE])
    wpm = RATES.get(rate, RATES["normal"])
    key = hashlib.sha1(("%s|%s|%d" % (sent, vname, wpm)).encode()).hexdigest()[:16]
    path = CACHE / ("%s.m4a" % key)
    if not path.exists():
        CACHE.mkdir(exist_ok=True)
        subprocess.run(
            ["say", "-v", vname, "-r", str(wpm), "-o", str(path),
             "--file-format=m4af", sent],
            check=True, capture_output=True)
    return path


def summarize(res):
    """Rút gọn kết quả grade() thành JSON đủ cho một câu shadowing.

    Báo cáo đầy đủ dành cho bài dài; một câu 5-8 từ thì học viên cần đúng
    ba thứ: điểm, từ nào sai, và sửa thế nào.
    """
    words = []
    for w in res["words"]:
        errs = [dict(label=f["label"], fix=f["fix"])
                for f in w["findings"] if f["severity"] >= 2]
        words.append(dict(word=w["text"], ok=not errs, errors=errs))
    m = res["metrics"]
    return dict(
        overall=res["overall"],
        words=words,
        phone_ok=m["phone_ok"], phone_total=m["phone_total"],
        final_ok=m["final_ok"], final_total=m["final_total"],
        priorities=[dict(label=p["label"], fix=p["fix"], count=p["count"])
                    for p in res["priorities"]],
    )
