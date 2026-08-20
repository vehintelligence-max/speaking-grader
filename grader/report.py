"""Báo cáo HTML một file, tự chứa, nhúng luôn audio.

Điểm quan trọng về mặt sư phạm: mỗi lỗi có một nút bấm để nghe đúng đoạn audio
đó. Học viên đọc chữ "bạn rụng âm /t/" thì không tin và không sửa được; nghe lại
đúng 0,4 giây chỗ mình rụng âm thì tin ngay. Vì vậy audio được nhúng thẳng dạng
base64 để file HTML gửi qua Zalo/email vẫn chạy, không cần kèm file rời.

Thứ tự trình bày theo lối trả lời trước: điểm và 3 việc cần sửa lên đầu, bảng số
liệu để sau. Giáo viên mở ra là biết phải nói gì với học viên trong 10 giây.
"""

import base64
import html
import io
import wave

from .audio import load_audio
from .scoring import LABELS, band

CSS = """
:root{--bg:#fbfaf8;--fg:#1c1a17;--mut:#6b665e;--line:#e4e0d8;--card:#fff;
--good:#1f7a4d;--ok:#2f6f9e;--warn:#b06a10;--bad:#a8341f;--hl:#f3efe7}
@media (prefers-color-scheme:dark){:root{--bg:#161513;--fg:#eceae6;--mut:#9a948a;
--line:#2e2c28;--card:#1e1d1a;--good:#4fbb85;--ok:#6ba8d4;--warn:#d99b3e;
--bad:#e0705a;--hl:#252420}}
:root[data-theme=dark]{--bg:#161513;--fg:#eceae6;--mut:#9a948a;--line:#2e2c28;
--card:#1e1d1a;--good:#4fbb85;--ok:#6ba8d4;--warn:#d99b3e;--bad:#e0705a;--hl:#252420}
:root[data-theme=light]{--bg:#fbfaf8;--fg:#1c1a17;--mut:#6b665e;--line:#e4e0d8;
--card:#fff;--good:#1f7a4d;--ok:#2f6f9e;--warn:#b06a10;--bad:#a8341f;--hl:#f3efe7}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 -apple-system,
BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding:28px 20px 64px}
.wrap{max-width:920px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px} h2{font-size:15px;text-transform:uppercase;
letter-spacing:.08em;color:var(--mut);margin:34px 0 12px;font-weight:600}
.sub{color:var(--mut);font-size:14px;margin-bottom:22px}
.hero{display:flex;gap:24px;align-items:center;background:var(--card);
border:1px solid var(--line);border-radius:14px;padding:20px 24px}
.big{font-size:52px;font-weight:700;line-height:1} .big small{font-size:18px;
color:var(--mut);font-weight:400}
.bars{flex:1;display:grid;grid-template-columns:auto 1fr auto;gap:6px 12px;
align-items:center;font-size:14px}
.bar{height:8px;background:var(--hl);border-radius:99px;overflow:hidden}
.bar i{display:block;height:100%;border-radius:99px}
.basis{color:var(--mut);font-size:12px;white-space:nowrap}
.good{color:var(--good)}.ok{color:var(--ok)}.warn{color:var(--warn)}
.bad{color:var(--bad)}.muted{color:var(--mut)}
.bg-good{background:var(--good)}.bg-ok{background:var(--ok)}
.bg-warn{background:var(--warn)}.bg-bad{background:var(--bad)}
.bg-muted{background:var(--mut)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:16px 18px;margin-bottom:12px}
.card h3{margin:0 0 8px;font-size:17px;display:flex;gap:8px;align-items:baseline}
.rank{color:var(--mut);font-variant-numeric:tabular-nums}
.tag{font-size:11px;padding:2px 8px;border-radius:99px;background:var(--hl);
color:var(--mut);white-space:nowrap}
.lbl{color:var(--mut);font-size:13px;text-transform:uppercase;letter-spacing:.06em}
.words{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:14px;min-width:560px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);
vertical-align:top}
th{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut)}
.ipa{font-family:ui-monospace,Menlo,monospace}
.play{cursor:pointer;border:1px solid var(--line);background:var(--card);
color:var(--fg);border-radius:7px;padding:2px 9px;font-size:12px;
font-family:inherit}
.play:hover{background:var(--hl)}
audio{width:100%;margin:6px 0 2px}
.note{font-size:13px;color:var(--mut);border-left:3px solid var(--line);
padding:2px 0 2px 12px;margin:6px 0}
ul.err{margin:4px 0 0;padding-left:18px}
"""

JS = """
const A=document.getElementById('aud');
document.addEventListener('click',e=>{
  const b=e.target.closest('.play'); if(!b||!A) return;
  const t=parseFloat(b.dataset.t), d=parseFloat(b.dataset.d||'0.6');
  A.currentTime=Math.max(0,t-0.15); A.play();
  clearTimeout(window._st);
  window._st=setTimeout(()=>A.pause(),(d+0.3)*1000);
});
"""


def _wav_data_uri(path):
    """Đọc audio bằng PyAV rồi đóng lại thành WAV base64 để nhúng.

    Trình duyệt không phát được .aiff/.m4a một cách đáng tin, còn WAV thì luôn
    chạy. File 15 giây ra khoảng 600 KB base64 — chấp nhận được cho một báo cáo.
    """
    try:
        pcm, sr = load_audio(path)
    except Exception:
        return None
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((pcm.clip(-1, 1) * 32767).astype("<i2").tobytes())
    return "data:audio/wav;base64," + base64.b64encode(buf.getvalue()).decode()


def _play_btn(start, end, text="▶ nghe"):
    if start is None:
        return ""
    dur = max(0.3, (end - start) if end else 0.6)
    return ('<button class="play" data-t="%.3f" data-d="%.3f">%s %.1fs</button>'
            % (start, dur, text, start))


def _bar(score):
    lab, cls = band(score)
    pct = 0 if score is None else max(2, min(100, score))
    return ('<div class="bar"><i class="bg-%s" style="width:%.0f%%"></i></div>'
            % (cls, pct)), lab, cls


def render(res):
    e = html.escape
    lab, cls = band(res["overall"])
    m, fm = res["metrics"], res["fluency"]

    # ---- điểm tổng + phân rã
    rows = []
    for k, v in res["scores"].items():
        bar, blab, bcls = _bar(v)
        ok, total, unit = res["score_basis"][k]
        basis = "%s/%s %s" % (ok, total, unit) if total else e(str(unit))
        rows.append(
            '<div>%s</div>%s<div class="basis %s">%s · %s</div>'
            % (e(LABELS[k]), bar, bcls,
               "%.0f" % v if v is not None else "—", basis))

    hero = ('<div class="hero"><div><div class="big %s">%.0f<small>/100</small>'
            '</div><div class="basis">%s</div></div><div class="bars">%s</div></div>'
            % (cls, res["overall"], e(lab), "".join(rows)))

    # ---- 3 việc cần sửa trước
    prio = []
    for i, p in enumerate(res["priorities"], 1):
        words = (' <span class="tag">%s</span>'
                 % e(", ".join(p["words"][:6])) if p["words"] else "")
        prio.append(
            '<div class="card"><h3><span class="rank">%d.</span> %s'
            '<span class="tag">%d lần</span></h3>%s'
            '<div class="note"><b>Vì sao:</b> %s</div>'
            '<div class="note"><b>Cách sửa:</b> %s</div></div>'
            % (i, e(p["label"]), p["count"], words, e(p["why"]), e(p["fix"])))
    if not prio:
        prio.append('<div class="card">Không phát hiện lỗi đáng kể. '
                    'Bài này đọc tốt.</div>')

    # ---- bảng từng từ
    trs = []
    for w in res["words"]:
        errs = "".join("<li>%s %s</li>" % (e(f["label"]), _play_btn(
            f["start"], f["end"])) for f in w["findings"])
        acc = w["n_correct"] / w["n_phones"] if w["n_phones"] else 0
        acls = "good" if acc >= 0.999 else "warn" if acc >= 0.6 else "bad"
        if not w["spoken"]:
            acls = "bad"
        trs.append(
            "<tr><td><b>%s</b>%s</td><td class='ipa muted'>/%s/</td>"
            "<td class='ipa'>/%s/</td><td class='%s'>%d/%d</td><td>%s</td></tr>"
            % (e(w["text"]),
               "" if w["spoken"] else " <span class='tag'>không đọc</span>",
               e(w["canonical_ipa"]), e(w["actual_ipa"]), acls,
               w["n_correct"], w["n_phones"],
               ("<ul class='err'>%s</ul>" % errs) if errs else
               "<span class='muted'>—</span>"))

    # ---- lỗi toàn câu (nhịp, nối âm, trôi chảy)
    glob = [f for f in res["findings"]
            if f["kind"] in ("rhythm", "linking", "fluency")]
    gl = "".join(
        '<div class="card"><h3>%s</h3><div class="note"><b>Vì sao:</b> %s</div>'
        '<div class="note"><b>Cách sửa:</b> %s</div>%s</div>'
        % (e(f["label"]), e(f["why"]), e(f["fix"]), _play_btn(f["start"], f["end"]))
        for f in glob) or '<div class="card muted">Không có ghi nhận nào.</div>'

    from .scoring import NATIVE_NPVI, NATIVE_RATIO
    stats = [
        ("Tốc độ", "%.0f từ/phút" % fm["wpm"] if fm.get("rate_reliable")
         else "bài quá ngắn để đo"),
        ("Tốc độ âm tiết", "%.1f âm tiết/giây" % fm["syll_per_s"]),
        ("Ngắt sai chỗ", "%d chỗ" % len(fm["pauses"])),
        ("Âm đệm", "%d" % fm["fillers"]),
        ("nPVI (nhịp)", "%.1f — tham chiếu bản ngữ %.1f"
         % (m["npvi"], NATIVE_NPVI) if m["npvi"] else "cần bài dài hơn"),
        ("Tỉ lệ giảm âm", "%.2f — tham chiếu bản ngữ %.2f"
         % (m["stress_ratio"], NATIVE_RATIO) if m["stress_ratio"]
         else "cần bài dài hơn"),
    ]
    st = "".join("<tr><td>%s</td><td>%s</td></tr>" % (e(a), e(str(b)))
                 for a, b in stats)

    uri = _wav_data_uri(res["audio"])
    player = ('<audio id="aud" controls preload="metadata" src="%s"></audio>' % uri
              if uri else '<div class="note">Không nhúng được audio.</div>')

    return """<title>Chấm phát âm — %s</title><style>%s</style>
<div class="wrap">
<h1>Báo cáo phát âm</h1>
<div class="sub">%s · %.1f giây · %d từ%s</div>
%s
%s
<h2>Ba việc cần sửa trước</h2>
%s
<h2>Nhịp điệu, nối âm, trôi chảy</h2>
%s
<h2>Chi tiết từng từ</h2>
<div class="scroll"><table>
<tr><th>Từ</th><th>Chuẩn</th><th>Đọc ra</th><th>Đúng</th><th>Lỗi</th></tr>
%s
</table></div>
<h2>Số liệu</h2>
<div class="scroll"><table>%s</table></div>
<h2>Bài đọc</h2>
<div class="card words">%s</div>
<div class="note">Cách đọc báo cáo: mỗi con số đều là "đúng bao nhiêu trên tổng
bao nhiêu", bấm ▶ để nghe đúng đoạn được nhắc. Tham chiếu bản ngữ được đo bằng
chính tool này trên giọng mẫu, không lấy từ giáo trình.</div>
</div><script>%s</script>""" % (
        e(res["audio"].rsplit("/", 1)[-1]), CSS,
        e(res["audio"].rsplit("/", 1)[-1]), res["duration"], res["n_words"],
        " · đã chọn lại %d cách đọc từ điển" % res["variants_adjusted"]
        if res.get("variants_adjusted") else "",
        player, hero, "".join(prio), gl, "".join(trs), st,
        e(res["script"].strip()), JS)


def write_html(res, path):
    doc = ("<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
           "<meta name='viewport' content='width=device-width,initial-scale=1'>"
           + render(res) + "</html>")
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path
