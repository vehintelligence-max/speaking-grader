"""Bộ âm vị thô (coarse phone set) dùng chung cho hai phía:

  - phía CHUẨN: ARPAbet từ CMUdict / g2p_en  ("AE1 S K T")
  - phía THỰC TẾ: eSpeak IPA từ wav2vec2      ("æ s k t")

Hai bộ ký hiệu này không so trực tiếp được, nên cả hai đều được map về một bộ
thô ở giữa. Bộ thô cố tình gộp các biến thể chỉ khác nhau về cách ghi (iː vs i,
əʊ vs oʊ) để không báo lỗi oan, nhưng vẫn giữ tách những cặp mà người Việt hay
sai thật (θ/t, ʃ/s, iː/ɪ, schwa vs nguyên âm đầy).
"""

# AX = schwa (âm giảm). Tách riêng khỏi AH để bắt được lỗi "không giảm âm".
VOWEL_SET = {
    "IY", "IH", "EY", "EH", "AE", "AA", "AH", "AX", "AO", "OW",
    "UH", "UW", "ER", "AY", "AW", "OY",
}

# ---------------------------------------------------------------- ARPAbet ----

# CMUdict AH0 là schwa, AH1/AH2 là /ʌ/. Xử lý riêng trong arpa_to_coarse().
_ARPA_TO_COARSE = {
    "AA": "AA", "AE": "AE", "AH": "AH", "AO": "AO", "AW": "AW", "AY": "AY",
    "EH": "EH", "ER": "ER", "EY": "EY", "IH": "IH", "IY": "IY", "OW": "OW",
    "OY": "OY", "UH": "UH", "UW": "UW",
    "B": "B", "CH": "CH", "D": "D", "DH": "DH", "F": "F", "G": "G",
    "HH": "HH", "JH": "JH", "K": "K", "L": "L", "M": "M", "N": "N",
    "NG": "NG", "P": "P", "R": "R", "S": "S", "SH": "SH", "T": "T",
    "TH": "TH", "V": "V", "W": "W", "Y": "Y", "Z": "Z", "ZH": "ZH",
}


def strip_stress(arpa):
    """'AE1' -> ('AE', 1).  'K' -> ('K', None)."""
    if arpa and arpa[-1].isdigit():
        return arpa[:-1], int(arpa[-1])
    return arpa, None


def arpa_to_coarse(arpa):
    """ARPAbet (có thể kèm số trọng âm) -> một âm vị thô."""
    base, stress = strip_stress(arpa)
    # Nguyên âm không nhấn kiểu AH0 chính là schwa -> phải giảm âm.
    if base == "AH" and stress == 0:
        return "AX"
    return _ARPA_TO_COARSE.get(base, "UNK")


# ------------------------------------------------------------ eSpeak IPA ----

# Một token eSpeak có thể ứng với nhiều âm thô (ɪə -> IH + ER).
_ESPEAK_TO_COARSE = {
    # nguyên âm đơn
    "i": ["IY"], "iː": ["IY"], "i:": ["IY"], "ɪ": ["IH"], "ɪː": ["IY"],
    "e": ["EH"], "ɛ": ["EH"], "æ": ["AE"], "a": ["AE"], "ɶ": ["AE"],
    "ɑ": ["AA"], "ɑː": ["AA"], "ɒ": ["AA"], "ɑ̃": ["AA"],
    "ʌ": ["AH"], "ɐ": ["AH"], "ə": ["AX"], "ɜ": ["ER"], "ɜː": ["ER"],
    "ɚ": ["ER"], "ɝ": ["ER"], "ɹ̩": ["ER"], "ɤ": ["ER"], "ɘ": ["AX"],
    "ɔ": ["AO"], "ɔː": ["AO"], "o": ["OW"], "oː": ["OW"], "ɵ": ["OW"],
    "ʊ": ["UH"], "u": ["UW"], "uː": ["UW"], "ɯ": ["UW"], "ʉ": ["UW"],
    # eSpeak dùng ᵻ / ᵿ cho nguyên âm giảm (places, beaches, decided).
    # Thiếu hai dòng này thì mọi đuôi -es đều bị báo là "âm không thuộc tiếng Anh".
    "\u1d7b": ["AX"], "\u1d7f": ["UH"], "ɨ": ["AX"], "ᵄ": ["AX"],
    "y": ["UW"], "ø": ["OW"], "œ": ["ER"],
    # nguyên âm đôi
    "eɪ": ["EY"], "aɪ": ["AY"], "ɔɪ": ["OY"], "aʊ": ["AW"],
    "oʊ": ["OW"], "əʊ": ["OW"], "ɐʊ": ["AW"], "ɑɪ": ["AY"],
    "ɪə": ["IH", "ER"], "iə": ["IY", "ER"], "eə": ["EH", "ER"],
    "ɛə": ["EH", "ER"], "ʊə": ["UH", "ER"], "uə": ["UW", "ER"],
    "ɔə": ["AO", "ER"], "aɪə": ["AY", "ER"], "aʊə": ["AW", "ER"],
    # âm tiết hoá
    "əl": ["AX", "L"], "ən": ["AX", "N"], "əm": ["AX", "M"],
    "l̩": ["AX", "L"], "n̩": ["AX", "N"], "m̩": ["AX", "M"],
    # phụ âm tắc
    "p": ["P"], "b": ["B"], "t": ["T"], "d": ["D"], "k": ["K"],
    "ɡ": ["G"], "g": ["G"], "ʈ": ["T"], "ɖ": ["D"], "c": ["K"],
    "q": ["K"], "ɓ": ["B"], "ɗ": ["D"], "ʔ": ["Q"],
    # phụ âm xát
    "f": ["F"], "v": ["V"], "θ": ["TH"], "ð": ["DH"], "s": ["S"],
    "z": ["Z"], "ʃ": ["SH"], "ʒ": ["ZH"], "h": ["HH"], "ɦ": ["HH"],
    "x": ["K"], "ɣ": ["G"], "ç": ["SH"], "ʝ": ["ZH"], "ɕ": ["SH"],
    "ʑ": ["ZH"], "ʂ": ["SH"], "ʐ": ["Z"], "β": ["V"], "ɸ": ["F"],
    "ħ": ["HH"], "ʕ": ["HH"], "χ": ["K"],
    # phụ âm tắc-xát
    "tʃ": ["CH"], "dʒ": ["JH"], "ts": ["T", "S"], "dz": ["D", "Z"],
    "tɕ": ["CH"], "dʑ": ["JH"], "tʂ": ["CH"],
    # mũi
    "m": ["M"], "n": ["N"], "ŋ": ["NG"], "ɲ": ["N", "Y"], "ɳ": ["N"],
    "ɴ": ["NG"],
    # nước / bán nguyên âm
    "l": ["L"], "ɫ": ["L"], "ɭ": ["L"], "ʎ": ["L", "Y"],
    "ɹ": ["R"], "r": ["R"], "ʁ": ["R"], "ɻ": ["R"], "ʀ": ["R"],
    "ɾ": ["DX"], "ɽ": ["DX"],      # âm vỗ: /t/ /d/ giữa hai nguyên âm (Saturday)
    "w": ["W"], "ʋ": ["V"], "j": ["Y"], "ɥ": ["W"],
}

# Dấu phụ / dấu trọng âm eSpeak: bỏ qua hoàn toàn.
_ESPEAK_IGNORE = {"ː", ":", "ˈ", "ˌ", "ˑ", "|", "‖", "ʰ", "ʲ", "ʷ", "̃",
                  "̥", "̬", "̪", "̯", "͡", "ˠ", "ˤ", "̚", "̆", "'", "-", ""}


def espeak_to_coarse(token):
    """Token eSpeak -> list âm vị thô. [] nếu là dấu phụ, ['UNK'] nếu lạ."""
    tok = token.strip()
    if tok in _ESPEAK_IGNORE:
        return []
    if tok in _ESPEAK_TO_COARSE:
        return list(_ESPEAK_TO_COARSE[tok])
    # Bỏ dấu phụ rồi thử lại (vd "tʰ" -> "t", "õ" -> "o")
    stripped = "".join(c for c in tok if c not in _ESPEAK_IGNORE)
    if stripped != tok and stripped in _ESPEAK_TO_COARSE:
        return list(_ESPEAK_TO_COARSE[stripped])
    # Thử bỏ dấu kết hợp Unicode
    bare = "".join(c for c in tok if not (0x0300 <= ord(c) <= 0x036F))
    if bare != tok and bare in _ESPEAK_TO_COARSE:
        return list(_ESPEAK_TO_COARSE[bare])
    return ["UNK"]


# ------------------------------------------------------ đặc trưng & chi phí ----

# Phụ âm: (hữu thanh, phương thức, vị trí)
_MANNER = ["stop", "affricate", "fricative", "nasal", "liquid", "glide"]
_PLACE = ["bilabial", "labiodental", "dental", "alveolar", "postalveolar",
          "palatal", "velar", "glottal"]

_CONS = {
    "P": (0, "stop", "bilabial"),        "B": (1, "stop", "bilabial"),
    "T": (0, "stop", "alveolar"),        "D": (1, "stop", "alveolar"),
    "K": (0, "stop", "velar"),           "G": (1, "stop", "velar"),
    "Q": (0, "stop", "glottal"),        "DX": (1, "stop", "alveolar"),
    "CH": (0, "affricate", "postalveolar"), "JH": (1, "affricate", "postalveolar"),
    "F": (0, "fricative", "labiodental"), "V": (1, "fricative", "labiodental"),
    "TH": (0, "fricative", "dental"),    "DH": (1, "fricative", "dental"),
    "S": (0, "fricative", "alveolar"),   "Z": (1, "fricative", "alveolar"),
    "SH": (0, "fricative", "postalveolar"), "ZH": (1, "fricative", "postalveolar"),
    "HH": (0, "fricative", "glottal"),
    "M": (1, "nasal", "bilabial"),       "N": (1, "nasal", "alveolar"),
    "NG": (1, "nasal", "velar"),
    "L": (1, "liquid", "alveolar"),      "R": (1, "liquid", "postalveolar"),
    "W": (1, "glide", "bilabial"),       "Y": (1, "glide", "palatal"),
}

# Nguyên âm: (độ cao 1..4, độ sau 1..3, tròn môi, là nguyên âm đôi)
_VOW = {
    "IY": (4, 1, 0, 0), "IH": (3, 1, 0, 0), "EY": (3, 1, 0, 1),
    "EH": (2, 1, 0, 0), "AE": (1, 1, 0, 0), "AA": (1, 3, 0, 0),
    "AH": (2, 2, 0, 0), "AX": (2, 2, 0, 0), "AO": (2, 3, 1, 0),
    "OW": (3, 3, 1, 1), "UH": (3, 3, 1, 0), "UW": (4, 3, 1, 0),
    "ER": (2, 2, 0, 0), "AY": (1, 2, 0, 1), "AW": (1, 2, 0, 1),
    "OY": (2, 3, 1, 1),
}


def is_vowel(p):
    return p in VOWEL_SET


def same_phone(a, b):
    """Có tính là đọc đúng hay không (nới lỏng ở các cặp trong EQUIVALENT)."""
    return a == b or frozenset((a, b)) in EQUIVALENT


# Những cặp âm mà chênh lệch KHÔNG phải lỗi của học viên:
#  ə/ʌ  - eSpeak ghi schwa thành ʌ; việc giảm âm được đo bằng độ dài, không bằng nhãn
#  ə/ɪ  - tiếng Anh có hai nguyên âm giảm hợp lệ (visit, happy)
#  ɔː/ɑː - giọng Mỹ nhập hai âm này (cot-caught merger): small, walk, along
#  ɜː/r  - CMUdict gộp màu 'r' vào ER, eSpeak tách rời
#  t/ɾ d/ɾ - âm vỗ tiếng Anh Mỹ (Saturday, water, better)
EQUIVALENT = [frozenset(("AX", "AH")), frozenset(("AX", "IH")),
              frozenset(("AO", "AA")), frozenset(("ER", "R")),
              frozenset(("T", "DX")), frozenset(("D", "DX"))]


def sub_cost(a, b):
    """Chi phí thay âm a bằng âm b, trong khoảng 0.0 (giống nhau) .. 1.0."""
    if a == b:
        return 0.0
    if frozenset((a, b)) in EQUIVALENT:
        return 0.0
    if a == "UNK" or b == "UNK":
        return 0.7
    av, bv = is_vowel(a), is_vowel(b)
    if av != bv:
        return 1.0                      # nguyên âm đổi thành phụ âm: lỗi nặng
    if av:
        ah, aback, around, adiph = _VOW[a]
        bh, bback, bround, bdiph = _VOW[b]
        return min(1.0, 0.40 * abs(ah - bh) / 3 + 0.35 * abs(aback - bback) / 2
                   + 0.15 * abs(around - bround) + 0.10 * abs(adiph - bdiph))
    if a not in _CONS or b not in _CONS:
        return 0.7
    avoi, aman, apla = _CONS[a]
    bvoi, bman, bpla = _CONS[b]
    man_d = abs(_MANNER.index(aman) - _MANNER.index(bman)) / (len(_MANNER) - 1)
    pla_d = abs(_PLACE.index(apla) - _PLACE.index(bpla)) / (len(_PLACE) - 1)
    return min(1.0, 0.25 * abs(avoi - bvoi) + 0.40 * man_d + 0.35 * pla_d)


# Ký hiệu IPA để hiển thị cho học viên.
IPA_DISPLAY = {
    "IY": "iː", "IH": "ɪ", "EY": "eɪ", "EH": "e", "AE": "æ", "AA": "ɑː",
    "AH": "ʌ", "AX": "ə", "AO": "ɔː", "OW": "oʊ", "UH": "ʊ", "UW": "uː",
    "ER": "ɜː", "AY": "aɪ", "AW": "aʊ", "OY": "ɔɪ",
    "P": "p", "B": "b", "T": "t", "D": "d", "K": "k", "G": "ɡ", "Q": "ʔ",
    "CH": "tʃ", "JH": "dʒ", "F": "f", "V": "v", "TH": "θ", "DH": "ð",
    "S": "s", "Z": "z", "SH": "ʃ", "ZH": "ʒ", "HH": "h",
    "M": "m", "N": "n", "NG": "ŋ", "L": "l", "R": "r", "W": "w", "Y": "j",
    "DX": "ɾ",
    "UNK": "?",
}


def ipa(p):
    return IPA_DISPLAY.get(p, p.lower())


def ipa_seq(phones):
    return "".join(ipa(p) for p in phones)
