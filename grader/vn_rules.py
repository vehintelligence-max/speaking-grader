"""Bảng luật đặt tên lỗi theo đặc thù người Việt học tiếng Anh.

Diff âm vị thô chỉ cho biết "âm A bị đọc thành âm B". Bảng này biến nó thành
tên lỗi mà giáo viên và học viên đọc là hiểu ngay, kèm lý do và cách sửa.

severity:  3 = đổi nghĩa hoặc đổi ngữ pháp (sửa trước)
           2 = người nghe nhận ra ngay là chưa chuẩn
           1 = chi tiết tinh, sửa sau
"""

from .phoneset import ipa

# ------------------------------------------------- lỗi thay âm (substitution) --
# (âm chuẩn, âm đọc thành) -> (mã lỗi, nhãn, giải thích, cách sửa, severity)
SUBSTITUTIONS = {
    ("TH", "T"): ("th_stop", "Âm /θ/ đọc thành /t/",
                  "Tiếng Việt không có /θ/ nên phản xạ là thay bằng /t/ gần nhất.",
                  "Đặt đầu lưỡi chạm nhẹ mép răng trên rồi đẩy hơi ra, lưỡi KHÔNG chặn hẳn luồng hơi. So: think / tink.", 2),
    ("TH", "S"): ("th_s", "Âm /θ/ đọc thành /s/",
                  "Hơi ra đúng nhưng lưỡi lùi vào trong, thành /s/.",
                  "Đưa đầu lưỡi ra chạm răng, nhìn gương phải thấy đầu lưỡi. So: thick / sick.", 2),
    ("TH", "F"): ("th_f", "Âm /θ/ đọc thành /f/",
                  "Dùng môi–răng thay vì lưỡi–răng.",
                  "Bỏ môi dưới ra, dùng đầu lưỡi. So: three / free.", 2),
    ("TH", "D"): ("th_d", "Âm /θ/ đọc thành /d/",
                  "Thay âm xát vô thanh bằng âm tắc hữu thanh — sai cả hai đặc tính.",
                  "Giữ hơi chảy liên tục, đừng chặn lưỡi. So: thank / dank.", 3),
    ("DH", "D"): ("dh_stop", "Âm /ð/ đọc thành /d/",
                  "Chặn hẳn luồng hơi thay vì để hơi xát qua.",
                  "Lưỡi chạm răng nhưng vẫn để hơi lọt. So: they / day.", 2),
    ("DH", "Z"): ("dh_z", "Âm /ð/ đọc thành /z/",
                  "Lưỡi lùi vào trong quá.",
                  "Đầu lưỡi ra mép răng trên. So: then / zen.", 2),
    ("DH", "V"): ("dh_v", "Âm /ð/ đọc thành /v/", "Dùng môi thay cho lưỡi.",
                  "Dùng đầu lưỡi chạm răng, không dùng môi dưới.", 2),
    ("SH", "S"): ("sh_s", "Âm /ʃ/ đọc thành /s/",
                  "Tiếng Việt 'x' gần /s/ nên hay thay thế.",
                  "Kéo lưỡi lùi về sau, môi tròn nhẹ. So: she / see, ship / sip.", 2),
    ("ZH", "Z"): ("zh_z", "Âm /ʒ/ đọc thành /z/", "Lưỡi chưa lùi đủ.",
                  "Lùi lưỡi như khi nói /ʃ/ nhưng có rung dây thanh. Vd: vision.", 1),
    ("ZH", "JH"): ("zh_jh", "Âm /ʒ/ đọc thành /dʒ/", "Thêm phần tắc ở đầu âm.",
                  "Đừng chặn hơi ở đầu, để hơi xát liên tục ngay từ đầu.", 1),
    ("CH", "SH"): ("ch_sh", "Âm /tʃ/ đọc thành /ʃ/", "Mất phần tắc /t/ ở đầu.",
                  "Chặn hơi bằng lưỡi rồi mới bung. So: chair / share.", 2),
    ("JH", "Y"): ("jh_y", "Âm /dʒ/ đọc thành /j/",
                  "Tiếng Việt 'gi' đọc gần /j/ nên chuyển thẳng sang.",
                  "Chặn hơi bằng lưỡi rồi bung có tiếng. So: jet / yet.", 2),
    ("JH", "Z"): ("jh_z", "Âm /dʒ/ đọc thành /z/", "Mất phần tắc ở đầu âm.",
                  "Chặn hơi trước khi phát. So: joke / (z)oke.", 2),
    ("V", "F"): ("v_f", "Âm /v/ đọc thành /f/ (mất hữu thanh)",
                 "Không rung dây thanh.",
                 "Đặt tay lên cổ, phải cảm nhận rung khi nói /v/. So: van / fan.", 2),
    ("V", "B"): ("v_b", "Âm /v/ đọc thành /b/", "Dùng hai môi thay vì môi–răng.",
                 "Môi dưới chạm răng trên, để hơi lọt qua. So: vote / boat.", 2),
    ("V", "W"): ("v_w", "Âm /v/ đọc thành /w/", "Môi tròn lại, không chạm răng.",
                 "Môi dưới phải chạm răng trên. So: vine / wine.", 2),
    ("W", "V"): ("w_v", "Âm /w/ đọc thành /v/", "Môi chạm răng khi không nên.",
                 "Chỉ tròn môi, không chạm răng. So: west / vest.", 2),
    ("Z", "S"): ("z_s_devoice", "Âm /z/ đọc thành /s/ (mất hữu thanh)",
                 "Tiếng Việt không có phụ âm hữu thanh ở cuối từ, nên /z/ tự động thành /s/.",
                 "Kéo dài âm cuối và giữ rung dây thanh. So: eyes / ice, buzz / bus.", 2),
    ("S", "Z"): ("s_z", "Âm /s/ đọc thành /z/", "Thêm rung dây thanh không cần thiết.",
                 "Ngắt tiếng, chỉ để hơi xát. So: bus / buzz.", 1),
    ("R", "Z"): ("r_z", "Âm /r/ đọc thành /z/",
                 "Ảnh hưởng cách đọc 'r' của giọng Bắc.",
                 "Cong đầu lưỡi lên nhưng KHÔNG cho chạm vòm miệng, môi tròn nhẹ. So: rice / (z)ice.", 3),
    ("R", "G"): ("r_g", "Âm /r/ đọc thành /g/ hoặc /ɣ/",
                 "Ảnh hưởng cách đọc 'r' của giọng Nam.",
                 "Đưa lưỡi ra trước và cong lên, không đẩy về cuống lưỡi.", 3),
    ("R", "L"): ("r_l", "Âm /r/ đọc thành /l/", "Đầu lưỡi chạm vòm miệng.",
                 "Cong lưỡi nhưng giữ khoảng cách, không chạm. So: right / light.", 2),
    ("L", "N"): ("l_n", "Âm /l/ đọc thành /n/", "Lẫn l/n theo phương ngữ.",
                 "Khi nói /l/ hơi phải thoát ra hai bên lưỡi, mũi không rung.", 2),
    ("N", "L"): ("n_l", "Âm /n/ đọc thành /l/", "Lẫn n/l theo phương ngữ.",
                 "Khi nói /n/ hơi đi qua mũi, bịt mũi sẽ thấy tắc.", 2),
    ("IY", "IH"): ("iy_ih", "Âm /iː/ đọc ngắn thành /ɪ/",
                   "Tiếng Việt không phân biệt dài–ngắn ở cặp này nên hay đọc gộp.",
                   "Kéo dài và căng môi hơn. So: sheep / ship, feet / fit.", 2),
    ("IH", "IY"): ("ih_iy", "Âm /ɪ/ đọc dài thành /iː/", "Đọc quá căng và dài.",
                   "Buông lỏng môi, ngắn lại. So: ship / sheep.", 2),
    ("UW", "UH"): ("uw_uh", "Âm /uː/ đọc ngắn thành /ʊ/", "Thiếu độ dài.",
                   "Tròn môi mạnh và giữ lâu hơn. So: fool / full.", 2),
    ("UH", "UW"): ("uh_uw", "Âm /ʊ/ đọc dài thành /uː/", "Đọc quá dài.",
                   "Ngắn và lỏng môi hơn. So: full / fool.", 2),
    ("AE", "EH"): ("ae_eh", "Âm /æ/ đọc thành /e/",
                   "Tiếng Việt không có /æ/, âm gần nhất là 'e'.",
                   "Hạ hàm xuống thấp hơn, miệng mở rộng ngang. So: bad / bed, man / men.", 2),
    ("EH", "AE"): ("eh_ae", "Âm /e/ đọc thành /æ/", "Mở miệng rộng quá.",
                   "Khép hàm lại một chút. So: bed / bad.", 2),
    ("AE", "AA"): ("ae_aa", "Âm /æ/ đọc thành /ɑː/", "Lưỡi lùi về sau quá.",
                   "Đưa lưỡi ra trước, miệng mở ngang chứ không mở dọc. So: cat / cart.", 2),
    ("AA", "AE"): ("aa_ae", "Âm /ɑː/ đọc thành /æ/", "Lưỡi quá ra trước.",
                   "Lùi lưỡi về sau và hạ thấp. So: cart / cat.", 2),
    ("AH", "AA"): ("ah_aa", "Âm /ʌ/ đọc thành /ɑː/", "Mở miệng rộng và dài quá.",
                   "Ngắn lại, miệng mở vừa phải. So: cup / carp.", 1),
    ("AO", "OW"): ("ao_ow", "Âm /ɔː/ đọc thành /oʊ/", "Thêm phần trượt của nguyên âm đôi.",
                   "Giữ nguyên một khẩu hình, không trượt. So: law / low.", 2),
    ("OW", "AO"): ("ow_ao", "Âm /oʊ/ đọc thành /ɔː/", "Thiếu phần trượt.",
                   "Bắt đầu từ /o/ rồi trượt về /ʊ/, môi tròn dần. So: low / law.", 2),
    ("EY", "EH"): ("ey_eh", "Âm /eɪ/ đọc thành /e/ (mất nguyên âm đôi)",
                   "Đọc thành một âm đơn, tiếng Việt không có phần trượt này.",
                   "Trượt từ /e/ lên /ɪ/. So: late / let, pain / pen.", 2),
    ("OW", "AA"): ("ow_aa", "Âm /oʊ/ đọc thành /ɑː/ (mất nguyên âm đôi)",
                   "Bỏ phần trượt.", "Tròn môi dần về cuối âm. So: coat / cart.", 2),
    ("AY", "AE"): ("ay_ae", "Âm /aɪ/ đọc thành /æ/ (mất nguyên âm đôi)",
                   "Bỏ phần trượt lên /ɪ/.", "Trượt hàm từ mở lên khép. So: like / lack.", 2),
    ("ER", "AH"): ("er_ah", "Âm /ɜː/ đọc mất màu 'r'", "Không cong lưỡi.",
                   "Cong đầu lưỡi lên khi giữ nguyên âm. So: bird / bud.", 1),
    ("P", "B"): ("p_b", "Âm /p/ đọc thành /b/ (thêm hữu thanh)",
                 "Tiếng Việt 'p' đầu từ rất yếu nên dễ chuyển sang /b/.",
                 "Bật hơi mạnh, đặt tờ giấy trước miệng phải thấy giấy động. So: pin / bin.", 2),
    ("B", "P"): ("b_p", "Âm /b/ đọc thành /p/ (mất hữu thanh)", "Không rung dây thanh.",
                 "Rung dây thanh ngay từ lúc bật môi. So: bat / pat.", 2),
    ("T", "D"): ("t_d", "Âm /t/ đọc thành /d/", "Thêm rung dây thanh.",
                 "Bật hơi mạnh, không cho dây thanh rung trước. So: two / do.", 2),
    ("D", "T"): ("d_t", "Âm /d/ đọc thành /t/ (mất hữu thanh)",
                 "Phụ âm cuối tiếng Việt luôn vô thanh.",
                 "Giữ rung dây thanh đến hết âm. So: bed / bet.", 2),
    ("K", "G"): ("k_g", "Âm /k/ đọc thành /ɡ/", "Thêm rung dây thanh.",
                 "Bật hơi, không rung. So: coat / goat.", 2),
    ("G", "K"): ("g_k", "Âm /ɡ/ đọc thành /k/ (mất hữu thanh)", "Không rung dây thanh.",
                 "Rung dây thanh từ đầu âm. So: bag / back.", 2),
    ("NG", "N"): ("ng_n", "Âm /ŋ/ đọc thành /n/", "Lưỡi ở phía trước thay vì cuống lưỡi.",
                 "Nâng cuống lưỡi chạm vòm mềm. So: sing / sin, thing / thin.", 2),
    ("N", "NG"): ("n_ng", "Âm /n/ đọc thành /ŋ/", "Lưỡi lùi về cuống.",
                 "Đầu lưỡi chạm vòm cứng ngay sau răng. So: sin / sing.", 2),
    ("M", "N"): ("m_n", "Âm /m/ đọc thành /n/", "Không khép môi.",
                 "Khép hẳn hai môi. So: some / sun.", 2),
    ("HH", "K"): ("hh_k", "Âm /h/ đọc thành /kh/", "Ảnh hưởng phụ âm 'kh' tiếng Việt.",
                 "Chỉ thở ra, không cho cuống lưỡi cọ vào vòm. So: house / khouse.", 2),
}

# Âm cuối bị chặn thành âm tắc thanh hầu — lỗi rất đặc trưng tiếng Việt.
GLOTTAL_STOPS = {"P", "T", "K", "B", "D", "G"}

# Từ chức năng: trong câu nói liền, chúng có "dạng yếu" (weak form) hợp lệ —
# to /tuː/ thành /tə/, and /ænd/ thành /ənd/, for /fɔːr/ thành /fər/. Đây là dấu
# hiệu nói TỐT, không phải lỗi. Không có danh sách này thì tool sẽ trừ điểm học
# viên đúng vào lúc họ nói tự nhiên nhất.
FUNCTION_WORDS = {
    "a", "an", "the", "to", "of", "and", "or", "but", "for", "from", "at",
    "in", "on", "as", "that", "than", "is", "are", "was", "were", "am", "be",
    "been", "do", "does", "did", "have", "has", "had", "can", "could", "will",
    "would", "shall", "should", "must", "may", "might", "he", "she", "we",
    "you", "they", "them", "him", "her", "his", "us", "me", "my", "your",
    "our", "their", "it", "its", "some", "there", "just", "not", "with",
}
REDUCED_VOWELS = {"AX", "AH", "IH"}

# Dưới ngưỡng tự tin này, model không chắc nó nghe được gì. Im lặng còn hơn báo
# sai: nói với học viên rằng họ phát âm sai trong khi máy đang đoán là mất uy tín.
MIN_CONFIDENCE = 0.35


def acceptable_substitution(canon, actual, slot, word, conf=1.0):
    """True nếu chênh lệch này KHÔNG nên báo là lỗi."""
    from .phoneset import is_vowel

    if conf < MIN_CONFIDENCE:
        return True                     # máy không chắc -> không kết luận
    if not (is_vowel(canon) and is_vowel(actual)):
        return False
    # Cuối từ, /i/ và /eɪ/ đổi nhau tuỳ vùng: Saturday, Monday, holiday, happy.
    if slot.is_word_final and frozenset((canon, actual)) == frozenset(("IY", "EY")):
        return True
    # Dạng yếu của từ chức năng.
    if word.text.lower() in FUNCTION_WORDS and (
            actual in REDUCED_VOWELS or canon in REDUCED_VOWELS):
        return True
    # Giảm nguyên âm ở âm tiết không nhấn của bất kỳ từ nào cũng là đúng.
    if slot.stress == 0 and actual in REDUCED_VOWELS:
        return True
    return False


def substitution_error(canon, actual, slot, word):
    """-> dict lỗi, hoặc None nếu chênh lệch không đáng kể."""
    key = (canon, actual)
    if key in SUBSTITUTIONS:
        code, label, why, fix, sev = SUBSTITUTIONS[key]
        # Ở cuối từ, mọi lỗi âm cuối đều nặng hơn một bậc: nó xoá luôn ngữ pháp.
        if slot.is_word_final and sev < 3:
            sev += 1
        return dict(code=code, label=label, why=why, fix=fix, severity=sev)

    if actual == "Q" and canon in GLOTTAL_STOPS:
        return dict(
            code="final_glottal",
            label="Âm cuối /%s/ bị chặn ở cổ, không bung hơi" % ipa(canon),
            why="Phụ âm cuối tiếng Việt không bung hơi, nên /p/ /t/ /k/ cuối từ "
                "bị nghẹn lại ở thanh hầu. Người nghe không nhận ra phụ âm nào.",
            fix="Bung hơi nhẹ sau khi chặn: 'stop' → 'stop-p', 'what' → 'what-t'. "
                "Cường điệu lúc luyện rồi giảm dần.",
            severity=3)

    if actual == "UNK":
        return dict(
            code="non_english_sound",
            label="Phát ra âm không thuộc tiếng Anh (thay cho /%s/)" % ipa(canon),
            why="Model nhận ra một âm ngoài hệ thống tiếng Anh — dấu hiệu đang "
                "dùng khẩu hình tiếng Việt.",
            fix="Nghe lại mẫu và bắt chước khẩu hình, đừng thay bằng âm tiếng Việt gần nhất.",
            severity=2)

    if canon == "AX" and actual not in ("AX", "AH"):
        return dict(
            code="no_reduction",
            label="Âm tiết không nhấn đọc thành nguyên âm đầy /%s/" % ipa(actual),
            why="Tiếng Anh giảm nguyên âm không nhấn về /ə/. Đọc rõ từng âm tiết "
                "làm câu nghe đều đều — đây là nguyên nhân chính của cảm giác "
                "'nói tiếng Anh mà nghe rất Việt'.",
            fix="Đọc nhanh và lỏng âm tiết không nhấn: 'about' = ə-BOUT, không phải A-BOUT.",
            severity=2)

    from .phoneset import is_vowel
    kind = "nguyên âm" if is_vowel(canon) else "phụ âm"
    return dict(
        code="generic_sub",
        label="Đọc /%s/ thành /%s/" % (ipa(canon), ipa(actual)),
        why="Sai chất %s." % kind,
        fix="Nghe lại từ mẫu và so khẩu hình.",
        severity=2 if slot.is_word_final else 1)


# --------------------------------------------------- lỗi mất âm (deletion) ----

def _ends_with_s(text):
    t = text.lower().rstrip("'")
    return t.endswith("s") or t.endswith("es")


def deletion_error(slot, word, cluster_size):
    """Đặt tên cho một âm chuẩn mà học viên không phát ra."""
    from .phoneset import is_vowel
    p = ipa(slot.coarse)

    if slot.role == "nucleus":
        return dict(
            code="vowel_dropped",
            label="Bỏ hẳn nguyên âm /%s/ trong '%s'" % (p, word.text),
            why="Cả âm tiết bị lướt qua hoặc bị nuốt.",
            fix="Đọc chậm lại, tách rõ từng âm tiết của '%s' rồi mới tăng tốc." % word.text,
            severity=3)

    if slot.is_word_final and slot.coarse in ("S", "Z") and _ends_with_s(word.text):
        return dict(
            code="drop_s",
            label="Rụng âm cuối /%s/ — đuôi -s/-es của '%s'" % (p, word.text),
            why="Đây là lỗi ngữ pháp, không chỉ là lỗi phát âm: mất /s/ là mất "
                "dấu số nhiều hoặc dấu chia động từ ngôi thứ ba.",
            fix="Luyện riêng phần đuôi: '%s' → tách 'book—s', giữ tiếng xì rõ 0.2 giây, "
                "rồi ghép lại." % word.text,
            severity=3)

    if slot.is_word_final and slot.coarse in ("T", "D") and word.text.lower().endswith("ed"):
        return dict(
            code="drop_ed",
            label="Rụng âm cuối /%s/ — đuôi -ed của '%s'" % (p, word.text),
            why="Mất /t/ /d/ là mất dấu quá khứ. Người nghe hiểu thành hiện tại.",
            fix="'%s' kết thúc bằng /%s/. Luyện cặp tối thiểu: ask / asked, "
                "walk / walked." % (word.text, p),
            severity=3)

    if slot.in_final_cluster and cluster_size >= 2:
        return dict(
            code="cluster_reduction",
            label="Giản lược cụm phụ âm cuối: mất /%s/ trong '%s'" % (p, word.text),
            why="Tiếng Việt không có cụm phụ âm cuối, nên phản xạ là chỉ đọc âm đầu "
                "của cụm rồi dừng.",
            fix="Tách cụm ra đọc chậm từng âm rồi nối dần lại, giữ đủ số âm.",
            severity=3)

    if slot.is_word_final or slot.role == "coda":
        return dict(
            code="drop_final",
            label="Mất âm cuối /%s/ của '%s'" % (p, word.text),
            why="Âm tiết tiếng Việt kết thúc rất nhẹ hoặc không bung hơi, nên phụ "
                "âm cuối tiếng Anh hay bị bỏ luôn.",
            fix="Cường điệu âm cuối khi luyện: kéo dài /%s/ ra rồi mới ngắt." % p,
            severity=3)

    if is_vowel(slot.coarse):
        return dict(code="drop_vowel_glide", label="Mất phần /%s/ của nguyên âm" % p,
                    why="Nguyên âm đôi bị đọc rút thành âm đơn.",
                    fix="Giữ đủ hai phần của nguyên âm đôi, trượt khẩu hình.",
                    severity=2)

    return dict(
        code="drop_onset",
        label="Mất âm đầu /%s/ của '%s'" % (p, word.text),
        why="Âm đầu bị lướt, thường do nối từ trước quá nhanh.",
        fix="Đọc rời từng từ trước, xác nhận có /%s/ rồi mới nối." % p,
        severity=3)


# --------------------------------------------------- lỗi chèn âm (insertion) --

def insertion_error(actual, prev_slot, next_slot, dur):
    """Âm học viên phát ra thêm mà bài không có."""
    from .phoneset import is_vowel
    p = ipa(actual.coarse)

    # Chèn nguyên âm vào giữa cụm phụ âm — lỗi kinh điển: school -> sờ-cun
    if (is_vowel(actual.coarse) and prev_slot is not None and next_slot is not None
            and not is_vowel(prev_slot.coarse) and not is_vowel(next_slot.coarse)):
        return dict(
            code="epenthesis",
            label="Thêm nguyên âm /%s/ vào giữa cụm phụ âm" % p,
            why="Tiếng Việt không có cụm phụ âm, nên phản xạ là chèn nguyên âm để "
                "tách ra thành hai âm tiết. Từ một âm tiết bị đọc thành hai.",
            fix="Đọc hai phụ âm liền nhau không nghỉ: /sk/, /pl/, /str/. Đếm âm tiết "
                "để kiểm tra: 'school' đúng là 1 âm tiết.",
            severity=2)

    if dur > 0.18 and actual.coarse in ("AX", "AH", "M", "N", "ER", "UNK"):
        return dict(
            code="filler",
            label="Âm đệm / ngập ngừng (%.2f giây)" % dur,
            why="Âm 'ừm', 'à' chen vào làm câu mất mạch.",
            fix="Thay bằng im lặng ngắn: nghỉ không tiếng nghe tự nhiên hơn nhiều.",
            severity=1)

    return dict(
        code="extra_sound",
        label="Thêm âm /%s/ không có trong bài" % p,
        why="Có âm thừa ở vị trí này.",
        fix="Đọc lại chậm, đối chiếu với phiên âm.",
        severity=1)
