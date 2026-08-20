"""Script (text bài đọc) -> chuỗi âm CHUẨN, có chia âm tiết và trọng âm.

Dùng g2p_en: CMUdict cho từ có trong từ điển, mạng neural nhỏ cho từ lạ, và
quan trọng là xử lý từ đồng tự theo từ loại — "record" (n) nhấn âm 1, "record"
(v) nhấn âm 2. Nếu không phân biệt được thì phần chấm trọng âm sẽ sai oan.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional

from .phoneset import arpa_to_coarse, is_vowel, strip_stress

# Cụm phụ âm được phép mở đầu âm tiết tiếng Anh — dùng cho nguyên tắc
# "maximal onset" khi chia âm tiết.
_ONSET3 = {"SPL", "SPR", "STR", "SKR", "SKW"}
_ONSET2 = {
    "PL", "PR", "BL", "BR", "TR", "TW", "DR", "DW", "KL", "KR", "KW",
    "GL", "GR", "GW", "FL", "FR", "THR", "THW", "SHR", "SL", "SW",
    "SP", "ST", "SK", "SM", "SN", "SF", "PY", "BY", "KY", "GY", "MY",
    "FY", "VY", "HHY", "HHW",
}

_g2p = None


def _get_g2p():
    global _g2p
    if _g2p is None:
        from g2p_en import G2p
        _g2p = G2p()
    return _g2p


@dataclass
class Syllable:
    index: int
    phone_indices: List[int]          # vị trí trong Word.phones
    nucleus: int                      # vị trí nguyên âm chính
    stress: int                       # 0 không nhấn, 1 nhấn chính, 2 nhấn phụ


@dataclass
class Word:
    index: int
    text: str                         # chính tả gốc, cần cho luật -ed / -s
    phones: List[str]                 # ARPAbet kèm số trọng âm
    coarse: List[str]                 # âm vị thô, để so với âm thực tế
    syllables: List[Syllable] = field(default_factory=list)
    stress_index: Optional[int] = None    # âm tiết đáng lẽ nhấn chính
    oov: bool = False                 # không có trong CMUdict -> phiên âm đoán
    followed_by_punct: bool = False    # có dấu câu ngay sau -> được phép nghỉ
    n_variants: int = 1               # số cách đọc CMUdict cho từ này
    variant: int = 0                  # cách đọc đang dùng

    @property
    def n_syllables(self):
        return len(self.syllables)


@dataclass
class PhoneSlot:
    """Một âm chuẩn, kèm đủ ngữ cảnh để đặt tên lỗi cho nó."""
    index: int                        # vị trí trong toàn bài
    arpa: str
    coarse: str
    stress: Optional[int]
    word_index: int
    syl_index: int
    role: str                         # onset | nucleus | coda
    in_word_index: int
    is_word_final: bool               # âm cuối cùng của từ
    in_final_cluster: bool            # thuộc cụm phụ âm cuối từ


def _preprocess(text):
    """Chuẩn hoá y như g2p_en làm, để tokenize khớp với phiên âm."""
    from g2p_en.expand import normalize_numbers
    text = normalize_numbers(str(text))
    text = "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^ a-z'.,?!\-]", "", text)
    return text


MAX_VARIANTS = 4


def variants_for(g2p, word, pos):
    """Mọi cách đọc hợp lệ của một từ. -> (list phones, oov).

    CMUdict có nhiều biến thể thật: saturday = ...D EY2 và ...D IY0, either =
    IY1/AY1, the = DH AH0/DH IY0. Nếu chỉ lấy biến thể đầu tiên thì học viên đọc
    biến thể thứ hai sẽ bị báo sai oan.
    """
    if word in g2p.homograph2features:
        # Từ đồng tự đã được phân giải bằng từ loại, không cần thử biến thể nữa.
        pron1, pron2, pos1 = g2p.homograph2features[word]
        return [list(pron1) if pos.startswith(pos1) else list(pron2)], False
    if word in g2p.cmu:
        return [list(p) for p in g2p.cmu[word][:MAX_VARIANTS]], False
    return [list(g2p.predict(word))], True


def _syllabify(phones):
    """Chia âm tiết theo nguyên tắc maximal onset. -> list Syllable."""
    vpos = [i for i, p in enumerate(phones) if is_vowel(arpa_to_coarse(p))]
    if not vpos:
        # Từ không có nguyên âm (vd viết tắt phiên âm lạ): coi là 1 âm tiết.
        return [Syllable(0, list(range(len(phones))), -1, 0)]

    # Điểm bắt đầu của từng âm tiết.
    starts = [0]
    for a, b in zip(vpos, vpos[1:]):
        run = [strip_stress(phones[i])[0] for i in range(a + 1, b)]
        split = b                      # mặc định: tất cả phụ âm về coda trước
        for k in range(min(3, len(run)), 0, -1):
            cluster = "".join(run[-k:])
            ok = (cluster in _ONSET3) if k == 3 else \
                 (cluster in _ONSET2) if k == 2 else (cluster != "NG")
            if ok:
                split = b - k
                break
        starts.append(split)

    syls = []
    for si, s in enumerate(starts):
        e = starts[si + 1] if si + 1 < len(starts) else len(phones)
        idxs = list(range(s, e))
        nucleus = next(i for i in idxs if is_vowel(arpa_to_coarse(phones[i])))
        _, stress = strip_stress(phones[nucleus])
        syls.append(Syllable(si, idxs, nucleus, stress if stress is not None else 0))
    return syls


def _pick_stress(syls):
    """Âm tiết nhấn chính. Từ 1 âm tiết -> None (không xét trọng âm)."""
    if len(syls) < 2:
        return None
    for want in (1, 2):
        for s in syls:
            if s.stress == want:
                return s.index
    return 0


def parse_script(text, variant_choice=None):
    """-> (list Word, list PhoneSlot phẳng theo thứ tự đọc).

    variant_choice: dict {chỉ số từ -> chỉ số biến thể}. Lượt đầu để None (dùng
    biến thể 0), sau khi nhận dạng xong thì pipeline chọn lại biến thể khớp nhất
    rồi gọi lần hai.
    """
    import nltk
    variant_choice = variant_choice or {}

    g2p = _get_g2p()
    clean = _preprocess(text)
    tokens = nltk.word_tokenize(clean)
    tagged = nltk.pos_tag(tokens)

    words, slots = [], []
    for tok, pos in tagged:
        if not re.search("[a-z]", tok):
            # Dấu câu: cho phép từ đứng trước được nghỉ hơi.
            if words and set(tok) & set(",.!?;:"):
                words[-1].followed_by_punct = True
            continue
        all_v, oov = variants_for(g2p, tok, pos)
        all_v = [[p for p in v if p and p != " "] for v in all_v]
        all_v = [v for v in all_v if v]
        if not all_v:
            continue
        wi = len(words)
        vi = min(variant_choice.get(wi, 0), len(all_v) - 1)
        phones = all_v[vi]
        coarse = [arpa_to_coarse(p) for p in phones]
        w = Word(index=wi, text=tok, phones=phones, coarse=coarse, oov=oov,
                 n_variants=len(all_v), variant=vi)
        w.syllables = _syllabify(phones)
        w.stress_index = _pick_stress(w.syllables)

        # Cụm phụ âm cuối từ: dãy phụ âm liên tục ở cuối.
        tail = len(phones)
        while tail > 0 and not is_vowel(coarse[tail - 1]):
            tail -= 1
        final_cluster = set(range(tail, len(phones)))

        for si, syl in enumerate(w.syllables):
            for i in syl.phone_indices:
                if i == syl.nucleus:
                    role = "nucleus"
                elif i < syl.nucleus:
                    role = "onset"
                else:
                    role = "coda"
                _, stress = strip_stress(phones[i])
                slots.append(PhoneSlot(
                    index=len(slots), arpa=phones[i], coarse=coarse[i],
                    stress=stress, word_index=w.index, syl_index=si, role=role,
                    in_word_index=i, is_word_final=(i == len(phones) - 1),
                    in_final_cluster=(i in final_cluster),
                ))
        words.append(w)

    return words, slots


def all_variants(text):
    """-> dict {chỉ số từ -> list các chuỗi âm thô ứng với từng biến thể}."""
    import nltk

    g2p = _get_g2p()
    tokens = nltk.word_tokenize(_preprocess(text))
    out, wi = {}, 0
    for tok, pos in nltk.pos_tag(tokens):
        if not re.search("[a-z]", tok):
            continue
        all_v, _ = variants_for(g2p, tok, pos)
        all_v = [[p for p in v if p and p != " "] for v in all_v]
        all_v = [v for v in all_v if v]
        if not all_v:
            continue
        out[wi] = [[arpa_to_coarse(p) for p in v] for v in all_v]
        wi += 1
    return out
