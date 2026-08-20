#!/usr/bin/env python3
"""Web UI chạy local: dán bài đọc, tải file ghi âm lên, nhận báo cáo.

    ./venv/bin/python server.py            # mở http://127.0.0.1:8971

Chạy hoàn toàn trên máy: audio của học viên không đi ra khỏi máy này, và không
gọi API nào nên không tốn tiền. Model được nạp một lần lúc khởi động (khoảng 20
giây), sau đó mỗi bài chấm chỉ mất vài giây.
"""

import argparse
import html
import pathlib
import re
import tempfile
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
</div></body></html>"""


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

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(FORM % dict(error="", sample=html.escape(SAMPLE)))
        else:
            self._send("<h1>404</h1>", 404)

    def do_POST(self):
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
