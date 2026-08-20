"""Đọc audio bằng PyAV. Máy này không có ffmpeg CLI nên không dùng subprocess.

PyAV nói trực tiếp với libav nên đọc được m4a / mp3 / wav / aac / ogg / caf /
aiff, và tự resample về 16 kHz mono float32 — đúng định dạng wav2vec2 cần.
"""

import av
import numpy as np

TARGET_SR = 16000


def load_audio(path, target_sr=TARGET_SR):
    """-> (samples float32 mono trong [-1,1], sample_rate)."""
    with av.open(str(path)) as container:
        streams = [s for s in container.streams if s.type == "audio"]
        if not streams:
            raise ValueError("Không tìm thấy stream audio trong %s" % path)
        stream = streams[0]
        stream.thread_type = "AUTO"

        resampler = av.AudioResampler(format="s16", layout="mono", rate=target_sr)
        chunks = []
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray().reshape(-1))
        # Xả nốt phần còn trong bộ đệm của resampler.
        for out in resampler.resample(None):
            chunks.append(out.to_ndarray().reshape(-1))

    if not chunks:
        raise ValueError("Giải mã được 0 sample từ %s" % path)
    pcm = np.concatenate(chunks).astype(np.float32) / 32768.0
    return pcm, target_sr


def trim_silence(pcm, sr, thresh_db=-50.0, pad=0.15):
    """Cắt khoảng lặng đầu/cuối. -> (pcm đã cắt, offset giây đã cắt ở đầu).

    Ngưỡng để rộng và chừa 150 ms: phụ âm cuối (/s/, /t/, /ɚ/) rất yếu, cắt sát
    là mất luôn âm cuối rồi tool lại báo học viên "rụng âm cuối".
    """
    win = max(1, int(0.02 * sr))
    n = len(pcm) // win
    if n == 0:
        return pcm, 0.0
    frames = pcm[: n * win].reshape(n, win)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    loud = np.where(db > thresh_db)[0]
    if len(loud) == 0:
        return pcm, 0.0
    start = max(0, int((loud[0] * 0.02 - pad) * sr))
    end = min(len(pcm), int((loud[-1] * 0.02 + 0.02 + pad) * sr))
    return pcm[start:end], start / sr


def duration_s(pcm, sr):
    return len(pcm) / float(sr)
