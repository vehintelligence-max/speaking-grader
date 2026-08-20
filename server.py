#!/usr/bin/env python3
"""Web UI chạy local: dán bài đọc, tải file ghi âm lên, nhận báo cáo.

    ./venv/bin/python server.py            # mở http://127.0.0.1:8971

Chạy hoàn toàn trên máy: audio của học viên không đi ra khỏi máy này, và không
gọi API nào nên không tốn tiền. Model được nạp một lần lúc khởi động (khoảng 20
giây), sau đó mỗi bài chấm chỉ mất vài giây.
"""

import argparse
import html
import json
import pathlib
import re
import tempfile
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import shadow
from grader.pipeline import grade
from grader.recognize import PhonemeRecognizer
from grader.report import render

PORT = 8971
REC = None

SAMPLE = ("Last weekend I asked my friends about the best places to visit. "
          "They suggested three beaches and a small museum.")

FORM = """<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Chấm phát âm Speaking</title><style>
:root{--bg:#fbfaf8;--fg:#1c1a17;--mut:#6b665e;--line:#e4e0d8;--card:#fff;
--acc:#1f7a4d}
@media (prefers-color-scheme:dark){:root{--bg:#161513;--fg:#eceae6;--mut:#9a948a;
--line:#2e2c28;--card:#1e1d1a;--acc:#4fbb85}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 -apple-system,
BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding:40px 20px}
.wrap{max-width:680px;margin:0 auto}
h1{font-size:22px;margin:0 0 6px}
p.sub{color:var(--mut);font-size:14px;margin:0 0 26px}
label{display:block;font-size:13px;text-transform:uppercase;letter-spacing:.06em;
color:var(--mut);margin:18px 0 6px}
textarea,input[type=file],input[type=text]{width:100%%;padding:11px 13px;
border:1px solid var(--line);border-radius:10px;background:var(--card);
color:var(--fg);font:15px/1.5 inherit}
textarea{min-height:130px;resize:vertical}
button{margin-top:22px;padding:12px 22px;border:0;border-radius:10px;
background:var(--acc);color:#fff;font:600 15px inherit;cursor:pointer}
.note{margin-top:26px;font-size:13px;color:var(--mut);border-left:3px solid
var(--line);padding-left:12px}
.err{background:#a8341f;color:#fff;padding:12px 14px;border-radius:10px;
margin-bottom:18px;white-space:pre-wrap;font:13px/1.5 ui-monospace,Menlo,monospace}
</style></head><body><div class="wrap">
<h1>Chấm phát âm bài read-aloud</h1>
<p class="sub">Dán đúng đoạn text học viên được yêu cầu đọc, rồi tải file ghi âm
lên. Chạy trên máy này, audio không gửi đi đâu.</p>
%(error)s
<form method="post" action="/grade" enctype="multipart/form-data">
<label>Tên học viên (không bắt buộc)</label>
<input type="text" name="student" placeholder="vd: Nguyễn An — lớp IELTS 5.5">
<label>Bài đọc (script chuẩn)</label>
<textarea name="script" required>%(sample)s</textarea>
<label>File ghi âm (m4a, mp3, wav, aac, aiff…)</label>
<input type="file" name="audio" accept="audio/*" required>
<button type="submit">Chấm bài</button>
</form>
<div class="note">Script phải khớp với những gì học viên được yêu cầu đọc. Sai
script thì tool sẽ báo lỗi ở những chỗ học viên đọc đúng.</div>
<div class="note">Muốn luyện nhại theo giọng mẫu từng câu?
<a href="/shadow">Chế độ shadowing</a></div>
</div></body></html>"""

# Trang shadowing: KHÔNG dùng %-format (CSS/JS đầy ký tự %); bơm dữ liệu bằng
# .replace("__DATA__", json) để không lặp lại bug width:100% ở FORM.
SHADOW_PAGE = """<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Shadowing — luyện nhại theo giọng mẫu</title><style>
:root{--bg:#fbfaf8;--fg:#1c1a17;--mut:#6b665e;--line:#e4e0d8;--card:#fff;
--acc:#1f7a4d;--bad:#a8341f}
@media (prefers-color-scheme:dark){:root{--bg:#161513;--fg:#eceae6;--mut:#9a948a;
--line:#2e2c28;--card:#1e1d1a;--acc:#4fbb85;--bad:#e06c53}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 -apple-system,
BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding:40px 20px}
.wrap{max-width:720px;margin:0 auto}
h1{font-size:22px;margin:0 0 6px}
p.sub{color:var(--mut);font-size:14px;margin:0 0 20px}
.bar{display:flex;gap:10px;align-items:center;margin-bottom:22px;flex-wrap:wrap}
select{padding:8px 10px;border:1px solid var(--line);border-radius:8px;
background:var(--card);color:var(--fg);font:14px inherit}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;
padding:16px 18px;margin-bottom:14px}
.sent{font-size:17px;font-weight:600;margin:0 0 4px}
.focus{font-size:12.5px;color:var(--mut);margin:0 0 12px}
.btns{display:flex;gap:8px;flex-wrap:wrap}
button{padding:8px 14px;border:1px solid var(--line);border-radius:9px;
background:var(--card);color:var(--fg);font:14px inherit;cursor:pointer}
button.rec{border-color:var(--acc);color:var(--acc);font-weight:600}
button.rec.on{background:var(--bad);border-color:var(--bad);color:#fff}
button:disabled{opacity:.45;cursor:default}
.status{font-size:13px;color:var(--mut);margin-top:10px;min-height:18px}
.result{margin-top:12px;border-top:1px dashed var(--line);padding-top:12px}
.score{font-size:15px;font-weight:700}
.chips{margin:10px 0 6px;line-height:2.1}
.chip{display:inline-block;padding:2px 9px;border-radius:999px;font-size:14px;
margin-right:6px;border:1px solid var(--line)}
.chip.ok{border-color:var(--acc);color:var(--acc)}
.chip.err{border-color:var(--bad);color:var(--bad);cursor:help}
.fixes{font-size:13.5px;margin:6px 0 0;padding-left:18px}
.fixes li{margin-bottom:4px}
a{color:var(--acc)}
</style></head><body><div class="wrap">
<h1>Shadowing — nhại theo giọng mẫu</h1>
<p class="sub">Nghe câu mẫu, bấm ghi âm và nhại theo càng giống càng tốt.
Chấm ngay từng câu. Audio xử lý trên máy chủ của lớp, không gửi đi đâu khác.
&nbsp;<a href="/">← Chấm bài đọc dài</a></p>
<div class="bar">
<label style="font-size:13px;color:var(--mut)">Giọng mẫu</label>
<select id="voice"></select>
<label style="font-size:13px;color:var(--mut)">Tốc độ</label>
<select id="rate"><option value="normal">Bình thường</option>
<option value="slow">Chậm</option></select>
</div>
<div id="cards"></div>
</div>
<script>
const DATA = __DATA__;
const cards = document.getElementById('cards');
const voiceSel = document.getElementById('voice');
for (const [k, label] of DATA.voices) {
  const o = document.createElement('option'); o.value = k; o.textContent = label;
  voiceSel.appendChild(o);
}
let recorder = null, recCard = null;

DATA.lesson.forEach((s, i) => {
  const c = document.createElement('div'); c.className = 'card';
  c.innerHTML =
    '<p class="sent">' + (i+1) + '. ' + s.text + '</p>' +
    '<p class="focus">' + s.focus + '</p>' +
    '<div class="btns">' +
    '<button class="play">&#9654; Nghe m&#7851;u</button>' +
    '<button class="rec">&#9679; Nh&#7841;i theo</button>' +
    '<button class="mine" disabled>&#128066; Nghe l&#7841;i m&#236;nh</button>' +
    '</div><div class="status"></div><div class="result" hidden></div>';
  cards.appendChild(c);
  const st = c.querySelector('.status'), res = c.querySelector('.result');
  const playBtn = c.querySelector('.play'), recBtn = c.querySelector('.rec'),
        mineBtn = c.querySelector('.mine');
  let myUrl = null;

  playBtn.onclick = () => {
    new Audio('/shadow/audio?i=' + i + '&voice=' + voiceSel.value +
              '&rate=' + document.getElementById('rate').value).play();
  };
  mineBtn.onclick = () => { if (myUrl) new Audio(myUrl).play(); };

  recBtn.onclick = async () => {
    if (recorder && recCard === c) { recorder.stop(); return; }
    if (recorder) return; // đang ghi ở câu khác
    let stream;
    try { stream = await navigator.mediaDevices.getUserMedia({audio: true}); }
    catch (e) { st.textContent = 'Không mở được mic: ' + e.message; return; }
    const mime = ['audio/webm;codecs=opus','audio/webm','audio/mp4']
      .find(m => MediaRecorder.isTypeSupported(m)) || '';
    recorder = new MediaRecorder(stream, mime ? {mimeType: mime} : {});
    recCard = c;
    const chunks = [];
    recorder.ondataavailable = e => chunks.push(e.data);
    recorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      recBtn.classList.remove('on');
      recBtn.innerHTML = '&#9679; Nh&#7841;i theo';
      const blob = new Blob(chunks, {type: recorder.mimeType || 'audio/webm'});
      recorder = null; recCard = null;
      if (blob.size < 2000) { st.textContent = 'Ghi âm quá ngắn, thử lại.'; return; }
      myUrl = URL.createObjectURL(blob); mineBtn.disabled = false;
      st.textContent = 'Đang chấm...';
      const fd = new FormData();
      fd.append('i', String(i));
      fd.append('audio', blob, 'mic.' + (blob.type.includes('mp4') ? 'm4a' : 'webm'));
      try {
        const r = await fetch('/shadow/grade', {method: 'POST', body: fd});
        const d = await r.json();
        if (d.error) { st.textContent = 'Lỗi: ' + d.error; return; }
        st.textContent = '';
        show(d);
      } catch (e) { st.textContent = 'Lỗi mạng: ' + e.message; }
    };
    recorder.start();
    recBtn.classList.add('on');
    recBtn.innerHTML = '&#9632; D&#7915;ng';
    st.textContent = 'Đang ghi... đọc xong bấm Dừng.';
  };

  function show(d) {
    res.hidden = false;
    const chips = d.words.map(w => {
      if (w.ok) return '<span class="chip ok">' + w.word + '</span>';
      const tip = w.errors.map(e => e.label).join('; ');
      return '<span class="chip err" title="' + tip.replaceAll('"','&quot;') +
             '">' + w.word + '</span>';
    }).join('');
    const fixes = d.priorities.map(p =>
      '<li><b>' + p.label + '</b>' + (p.count > 1 ? ' (×' + p.count + ')' : '') +
      ' — ' + p.fix + '</li>').join('');
    res.innerHTML =
      '<div class="score">Điểm: ' + d.overall + '/100 &nbsp;·&nbsp; âm đúng ' +
      d.phone_ok + '/' + d.phone_total + ' &nbsp;·&nbsp; âm cuối ' +
      d.final_ok + '/' + d.final_total + '</div>' +
      '<div class="chips">' + chips + '</div>' +
      (fixes ? '<ul class="fixes">' + fixes + '</ul>' : '');
  }
});
</script></body></html>"""


def _parse_multipart(body, boundary):
    """Bóc multipart/form-data -> dict {tên: (tên file hoặc None, bytes)}.

    Tự bóc thay vì dùng module `cgi`: cgi bị bỏ khỏi Python 3.13, và ở đây chỉ
    cần hai trường nên không đáng phải phụ thuộc vào nó.
    """
    sep = b"--" + boundary
    out = {}
    for part in body.split(sep):
        if not part.strip() or part.strip() == b"--":
            continue
        if b"\r\n\r\n" not in part:
            continue
        head, data = part.split(b"\r\n\r\n", 1)
        data = data[:-2] if data.endswith(b"\r\n") else data
        h = head.decode("utf-8", "replace")
        name = re.search(r'name="([^"]*)"', h)
        fname = re.search(r'filename="([^"]*)"', h)
        if name:
            out[name.group(1)] = (fname.group(1) if fname else None, data)
    return out


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *a):
        print("  %s" % (fmt % a))

    def _send(self, body, code=200, ctype="text/html; charset=utf-8"):
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_bytes(self, raw, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "max-age=86400")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            self._send(FORM % dict(error="", sample=html.escape(SAMPLE)))
        elif url.path == "/shadow":
            data = json.dumps(dict(
                lesson=shadow.LESSON,
                voices=[[k, v[1]] for k, v in shadow.VOICES.items()]))
            self._send(SHADOW_PAGE.replace("__DATA__", data))
        elif url.path == "/shadow/audio":
            q = parse_qs(url.query)
            try:
                idx = int(q.get("i", ["0"])[0])
                path = shadow.synth(idx,
                                    voice=q.get("voice", ["samantha"])[0],
                                    rate=q.get("rate", ["normal"])[0])
                self._send_bytes(path.read_bytes(), "audio/mp4")
            except Exception:
                self._send("<h1>500</h1>", 500)
        else:
            self._send("<h1>404</h1>", 404)

    def do_POST(self):
        if self.path == "/shadow/grade":
            self._shadow_grade()
            return
        if self.path != "/grade":
            self._send("<h1>404</h1>", 404)
            return
        ctype = self.headers.get("Content-Type", "")
        m = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", ctype)
        if not m:
            self._send(FORM % dict(error='<div class="err">Thiếu boundary.</div>',
                                   sample=html.escape(SAMPLE)), 400)
            return
        boundary = (m.group(1) or m.group(2)).strip().encode()
        length = int(self.headers.get("Content-Length", "0"))
        fields = _parse_multipart(self.rfile.read(length), boundary)

        script = fields.get("script", (None, b""))[1].decode("utf-8", "replace")
        student = fields.get("student", (None, b""))[1].decode("utf-8", "replace")
        fname, blob = fields.get("audio", (None, b""))

        if not script.strip() or not blob:
            self._send(FORM % dict(
                error='<div class="err">Cần cả bài đọc và file ghi âm.</div>',
                sample=html.escape(script or SAMPLE)), 400)
            return

        suffix = pathlib.Path(fname or "bai.m4a").suffix or ".m4a"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(blob)
            tmp = f.name
        try:
            res = grade(tmp, script, recognizer=REC)
            res["audio"] = fname or pathlib.Path(tmp).name
            body = render(res)
            if student.strip():
                body = body.replace("<h1>Báo cáo phát âm</h1>",
                                    "<h1>Báo cáo phát âm — %s</h1>"
                                    % html.escape(student.strip()))
            self._send("<!doctype html><html lang='vi'><head>"
                       "<meta charset='utf-8'><meta name='viewport' "
                       "content='width=device-width,initial-scale=1'>"
                       + body + "</html>")
        except Exception:
            self._send(FORM % dict(
                error='<div class="err">%s</div>'
                      % html.escape(traceback.format_exc()),
                sample=html.escape(script)), 500)
        finally:
            pathlib.Path(tmp).unlink(missing_ok=True)

    def _shadow_grade(self):
        ctype = self.headers.get("Content-Type", "")
        m = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", ctype)
        if not m:
            self._send(json.dumps(dict(error="thiếu boundary")), 400,
                       "application/json")
            return
        boundary = (m.group(1) or m.group(2)).strip().encode()
        length = int(self.headers.get("Content-Length", "0"))
        fields = _parse_multipart(self.rfile.read(length), boundary)
        fname, blob = fields.get("audio", (None, b""))
        try:
            idx = int(fields.get("i", (None, b"0"))[1].decode())
            script = shadow.LESSON[idx]["text"]
        except (ValueError, IndexError):
            self._send(json.dumps(dict(error="câu không hợp lệ")), 400,
                       "application/json")
            return
        suffix = pathlib.Path(fname or "mic.webm").suffix or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(blob)
            tmp = f.name
        try:
            res = grade(tmp, script, recognizer=REC)
            self._send(json.dumps(shadow.summarize(res), ensure_ascii=False),
                       ctype="application/json; charset=utf-8")
        except Exception as e:
            self._send(json.dumps(dict(error=str(e)), ensure_ascii=False), 500,
                       "application/json; charset=utf-8")
        finally:
            pathlib.Path(tmp).unlink(missing_ok=True)


def main():
    global REC
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args()

    print("Đang nạp model âm vị (lần đầu mất ~20 giây)...")
    REC = PhonemeRecognizer()
    print("Sẵn sàng:  http://127.0.0.1:%d" % args.port)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
