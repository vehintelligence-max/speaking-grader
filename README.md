# Speaking Grader — chấm phát âm bài read-aloud

Chấm file ghi âm của học viên và chỉ ra **đúng từng âm sai**: rụng âm cuối, rụng
`-s`/`-es`, rụng `-ed`, giản lược cụm phụ âm, `th` thành `t`, sai trọng âm, không
nối âm, nhịp đều kiểu tiếng Việt, tốc độ và chỗ ngắt.

Chạy 100% trên máy. Không gọi API, không tốn tiền, audio học viên không ra khỏi máy.

## Tại sao không dùng ASR thường

Whisper và các ASR khác được huấn luyện để **đoán từ người ta muốn nói**. Học viên
đọc `books` thiếu `/s/`, Whisper vẫn ghi "books" vì suy ra từ ngữ cảnh — lỗi biến
mất trước khi mình kịp thấy.

Tool này dùng model nhận dạng **âm vị** (`wav2vec2-lv-60-espeak-cv-ft`), ghi lại
đúng những âm phát ra. Thiếu `/s/` là thiếu `/s/`. Model được huấn luyện đa ngôn
ngữ nên còn ghi được cả những âm không thuộc tiếng Anh — chính là các âm "thuần
Việt" cần bắt.

## Cách chạy

Web UI (dễ nhất):

```bash
cd ~/speaking-grader && ./venv/bin/python server.py
```

Mở http://127.0.0.1:8971 → dán bài đọc → tải file ghi âm → nhận báo cáo.

Dòng lệnh, xuất báo cáo HTML:

```bash
cd ~/speaking-grader && ./venv/bin/python cli.py --audio bai.m4a --script "I asked her about the books." --html bao_cao.html
```

Chấm cả thư mục thì dùng `--script-file de.txt`. Thêm `--json kq.json` để lấy dữ
liệu thô cho việc theo dõi tiến bộ theo thời gian.

Chạy test:

```bash
cd ~/speaking-grader && ./venv/bin/python tests/run_tests.py
```

## Nó hoạt động thế nào

| Bước | Việc | Kết quả |
|---|---|---|
| 1 | PyAV giải mã audio → 16 kHz mono | không cần ffmpeg |
| 2 | `g2p_en`/CMUdict: script → chuỗi âm **chuẩn** + trọng âm | phân biệt được `record` (n) và `record` (v) |
| 3 | wav2vec2 âm vị: audio → chuỗi âm **thực tế** | ghi đúng cái phát ra |
| 4 | Needleman–Wunsch khớp hai chuỗi, chi phí theo đặc trưng ngữ âm | mỗi âm chuẩn nhận một phán quyết: đúng / thay / mất / thêm |
| 5 | Bảng luật người Việt đặt tên cho từng chênh lệch | "rụng âm cuối /t/ đuôi -ed", không phải "phone error" |
| 6 | Bề rộng đỉnh năng lượng → độ dài nguyên âm | trọng âm, nhịp |
| 7 | Khoảng cách giữa các đỉnh CTC | nối âm, chỗ ngắt, tốc độ |

Ba nguồn số liệu được phân vai rõ, cố ý:

- **nhận dạng tự do** → âm nào thực sự phát ra (bắt lỗi)
- **năng lượng** → nguyên âm dài bao nhiêu (trọng âm, nhịp)
- **đỉnh CTC** → âm xuất hiện ở giây nào (nối âm, ngắt, tốc độ)

Không dùng forced alignment để lấy độ dài âm: đầu ra CTC rất "nhọn", và Viterbi
trên cùng model đó cũng nhọn y vậy — bề rộng thu được là bề rộng khoảng lặng bên
cạnh, không phải của âm. Đã thử và đã bỏ.

## Cách chấm điểm

Mỗi điểm truy được về một tỉ lệ đếm được, không có hệ số tự nghĩ ra:

| Nhóm | Trọng số | Cách tính |
|---|---|---|
| Âm vị tổng thể | 30% | số âm đọc đúng / tổng số âm |
| **Âm cuối** | 22% | phụ âm cuối đúng / tổng phụ âm cuối |
| Trọng âm từ | 18% | từ đa âm tiết nhấn đúng / tổng |
| Nối âm | 12% | chỗ nối được / chỗ cần nối |
| Nhịp điệu | 10% | nPVI so với tham chiếu bản ngữ |
| Trôi chảy | 8% | tốc độ, chỗ ngắt, âm đệm |

Nhóm nào bài không có (vd không có từ đa âm tiết) thì bị loại khỏi điểm tổng và
chia lại trọng số, chứ không cho 0 điểm oan.

## Tham chiếu bản ngữ — phải hiểu chỗ này

`grader/calibration.json` giữ hai con số tham chiếu (nPVI, tỉ lệ giảm âm) **đo
bằng chính tool này** trên giọng mẫu, không lấy từ giáo trình.

Lý do: tài liệu ghi nPVI bản ngữ khoảng 55–65, nhưng họ gán ranh giới âm bằng tay.
Tool này đo từ frame 20 ms nên ra thấp hơn. Lấy 55–65 làm chuẩn thì **mọi** học
viên đều bị kết luận "nhịp thuần Việt", kể cả người nói tốt.

Hiện tham chiếu đo từ giọng TTS macOS — đây là **điểm yếu**. TTS đọc đều hơn người
thật. Khi có ghi âm giáo viên bản ngữ (mỗi file kèm một `.txt` cùng tên), chạy:

```bash
cd ~/speaking-grader && ./venv/bin/python calibrate.py --dir /duong/dan/ghi_am_mau
```

## Đã kiểm chứng đến đâu

`tests/run_tests.py` chạy cả hai phía. Giọng bản ngữ (Samantha) và giọng tiếng Việt
(Linh) đọc **cùng một đoạn 41 từ**:

| | bản ngữ | accent Việt |
|---|---|---|
| Điểm | 95.7 | 59.8 |
| Âm đúng | 153/155 (99%) | 71/155 (46%) |
| **Phụ âm cuối đúng** | 39/40 (98%) | **12/40 (30%)** |
| nPVI | 39 (= tham chiếu) | 26 |
| Số lỗi báo ra | 4 | 90 |

Bài riêng cho đuôi từ: audio đọc "I ask her about the book", script "I asked her
about the books" → bắt đúng **rụng /t/ đuôi -ed** và **rụng /s/ đuôi -s**, không
báo thêm gì khác.

## Giới hạn phải nói trước với giáo viên

1. **Sàn nhiễu ~1–3%.** Trên giọng bản ngữ hoàn hảo, tool vẫn báo 2–4 lỗi trên 41
   từ (`museum` trọng âm, `year` âm cuối `/r/`). Đừng coi mọi lỗi đơn lẻ là chân lý
   — hãy xem **nhóm lỗi lặp nhiều lần**, đó mới là vấn đề thật của học viên.
2. **Chỉ dùng cho read-aloud.** Phải có script đúng những gì học viên được yêu cầu
   đọc. Sai script là báo lỗi ở chỗ học viên đọc đúng.
3. **Tham chiếu nhịp còn dựa trên TTS**, xem mục trên.
4. **Đang bỏ qua có chủ đích, vì đo không đáng tin:** `ə` vs `ʌ` và `ə` vs `ɪ`
   (đều là âm giảm hợp lệ), `ɔː` vs `ɑː` (giọng Mỹ nhập hai âm này), `/t/` thành
   `[ɾ]` giữa hai nguyên âm (chuẩn Mỹ: *Saturday*, *water*), dạng yếu của từ chức
   năng (*to* → `/tə/`), `i`/`eɪ` ở cuối từ (*Saturday*, *holiday*).
   Việc giảm âm được đánh giá bằng **độ dài** ở phần nhịp điệu, đáng tin hơn nhãn âm vị.
5. **Chưa chấm ngữ pháp, từ vựng, nội dung.** Chỉ phát âm và trôi chảy.

## Cấu trúc

```
grader/phoneset.py    bộ âm vị thô + chi phí thay âm theo đặc trưng ngữ âm
grader/lexicon.py     script -> âm chuẩn, chia âm tiết, trọng âm, biến thể từ điển
grader/recognize.py   wav2vec2 âm vị -> âm thực tế + mốc thời gian
grader/align.py       Needleman-Wunsch
grader/vn_rules.py    bảng luật đặt tên lỗi người Việt  <- sửa ở đây khi thêm lỗi
grader/prosody.py     năng lượng, cao độ, bề rộng nguyên âm, nPVI
grader/diagnose.py    gộp thành chẩn đoán: âm vị, trọng âm, nối âm, nhịp
grader/fluency.py     tốc độ, chỗ ngắt, âm đệm
grader/scoring.py     quy ra điểm 0-100
grader/report.py      báo cáo HTML tự chứa, nhúng audio, bấm là nghe
cli.py  server.py  calibrate.py  tests/run_tests.py
```

Thêm một loại lỗi mới thì chỉ cần thêm một dòng vào `SUBSTITUTIONS` trong
`grader/vn_rules.py`.

## Bước tiếp theo

- **Free speaking** (IELTS Part 1/2): thêm Whisper để lấy câu học viên định nói,
  rồi dùng lại toàn bộ pipeline này. Dùng chung ~90% code.
- **Ngữ pháp / từ vựng / band score**: cần LLM. Đã tách sẵn để cắm vào sau. Lưu ý
  **ChatGPT Plus không có API** — muốn app gọi được phải dùng account API riêng
  (platform.openai.com, trả theo token) hoặc model local.
- **Tích hợp VEH Teaching Hub**: bọc `grader.pipeline.grade()` thành một HTTP
  endpoint. Xem `VEH-v25-AUDIT.md` trước — bản v25 còn xoá dữ liệu lúc khởi động.
