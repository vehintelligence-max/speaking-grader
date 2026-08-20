"""Khớp chuỗi âm CHUẨN với chuỗi âm THỰC TẾ (Needleman-Wunsch).

Đây là trái tim của tool. Chi phí thay thế lấy từ đặc trưng ngữ âm, nên thuật
toán ưu tiên khớp /s/ với /z/ (gần nhau) hơn là khớp /s/ với /ɑː/ (rất xa).
Nhờ vậy mỗi âm chuẩn nhận được đúng một trong bốn phán quyết:

  match  - đọc đúng
  sub    - đọc thành âm khác          (æ -> ɛ, θ -> t)
  del    - không phát ra âm này       -> MẤT ÂM CUỐI, rụng -s/-ed
  ins    - phát ra âm không có trong bài  -> chèn âm, filler
"""

from .phoneset import sub_cost

GAP = 0.8          # chi phí bỏ/chèn một âm
MATCH = "match"
SUB = "sub"
DEL = "del"        # có trong bài, học viên không đọc
INS = "ins"        # học viên đọc thêm, bài không có


def needleman_wunsch(canon, actual, gap=GAP):
    """canon, actual: list mã âm thô. -> list op dict."""
    n, m = len(canon), len(actual)
    # D[i][j] = chi phí tối ưu khi đã xử lý i âm chuẩn và j âm thực tế
    D = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        D[i][0] = i * gap
    for j in range(1, m + 1):
        D[0][j] = j * gap

    for i in range(1, n + 1):
        ci = canon[i - 1]
        Di, Dprev = D[i], D[i - 1]
        for j in range(1, m + 1):
            Di[j] = min(
                Dprev[j - 1] + sub_cost(ci, actual[j - 1]),
                Dprev[j] + gap,
                Di[j - 1] + gap,
            )

    ops, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            c = sub_cost(canon[i - 1], actual[j - 1])
            if abs(D[i][j] - (D[i - 1][j - 1] + c)) < 1e-9:
                ops.append({
                    "op": MATCH if c == 0.0 else SUB,
                    "canon_i": i - 1, "actual_j": j - 1,
                    "canon": canon[i - 1], "actual": actual[j - 1],
                    "cost": c,
                })
                i, j = i - 1, j - 1
                continue
        if i > 0 and abs(D[i][j] - (D[i - 1][j] + gap)) < 1e-9:
            ops.append({"op": DEL, "canon_i": i - 1, "actual_j": None,
                        "canon": canon[i - 1], "actual": None, "cost": gap})
            i -= 1
            continue
        ops.append({"op": INS, "canon_i": None, "actual_j": j - 1,
                    "canon": None, "actual": actual[j - 1], "cost": gap})
        j -= 1

    ops.reverse()
    return ops
