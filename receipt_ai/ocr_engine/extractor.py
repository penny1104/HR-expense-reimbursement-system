import re
import difflib
import opencc

_cc = opencc.OpenCC('s2twp')   # 簡體 → 台灣繁體（含詞彙轉換）


def to_traditional(text):
    """將簡體中文轉為繁體中文，非字串則原樣回傳"""
    if isinstance(text, str) and text and text not in ('無', 'None'):
        return _cc.convert(text)
    return text


# =========================================================
# 共用工具
# =========================================================
_NORMALIZE_MAP = {
    "臺": "台", "牛": "年", "目": "月", "曰": "日", "O": "0", "I": "1",
}

def _norm(line):
    for k, v in _NORMALIZE_MAP.items():
        line = line.replace(k, v)
    return line.strip()

def _norm_all(lines):
    return [_norm(l) for l in lines]

def _clean(text):
    """去掉非中英數的符號"""
    return re.sub(r'[^一-鿿＀-￯A-Za-z0-9]', '', text)

def _zh_count(text):
    return len(re.findall(r'[一-鿿]', text))

_PHONE = re.compile(r'TEL|電話|电话|tel|\(0\d\)')


# =========================================================
# 判斷發票類型
# =========================================================
def detect_invoice_type(texts):
    for t in texts:
        if '電子發票' in t and '證明聯' in t:
            return 'electronic'
    return 'handwritten'


# =========================================================
# ① 電子發票
# =========================================================

_ELEC_SKIP = re.compile(
    r'電子發票|證明聯|\d{4}-\d{2}-\d{2}|隨機碼|賣方|買方|總計|序[：:]|櫃[：:]|帳[：:]|機[：:]'
)


def _elec_vendor(ordered):
    for line in ordered:
        t = _clean(line)
        if len(t) < 2:
            continue
        if _ELEC_SKIP.search(line):
            continue
        if re.fullmatch(r'[A-Z]{2}\d{8}', t):
            continue
        if _zh_count(t) >= 2:
            return line.strip()
        if re.fullmatch(r'[A-Za-z]{3,}', t):
            return line.strip()
    return "無"


def _elec_invoice_number(texts):
    for line in texts:
        m = re.search(r'[A-Z]{2}-?\d{8}', line)
        if m:
            return m.group().replace('-', '')
    return None


def _elec_date(texts):
    for line in texts:
        m = re.search(r'(\d{3})年(\d{1,2})[-~－](\d{1,2})月', line)
        if m:
            y = int(m.group(1)) + 1911
            return f"{y}-{int(m.group(2)):02d}"
        m = re.search(r'(\d{4})-(\d{2})-(\d{2})', line)
        if m:
            return m.group(0)
    return None


def _is_part_of_invoice_number(line, start_idx):
    """檢查匹配的 8 位數前面是否為台灣發票號碼的英文首綴（2 位英文字母，中間可能有空格或連字號）"""
    prefix = line[:start_idx]
    prefix_clean = re.sub(r'[\s\-－]+$', '', prefix)
    if len(prefix_clean) >= 2 and re.match(r'^[A-Za-z]{2}$', prefix_clean[-2:]):
        return True
    return False


def _elec_seller(texts):
    for line in texts:
        m = re.search(r'賣方[：:]\s*(\d{8})', line)
        if m:
            return m.group(1)
    for line in texts:
        if _PHONE.search(line):
            continue
        for m in re.finditer(r'(?<!\d)(\d{8})(?!\d)', line):
            val = m.group(1)
            if not _is_part_of_invoice_number(line, m.start()):
                return val
    return "無"


def _elec_buyer(texts):
    for line in texts:
        m = re.search(r'買方[：:]\s*(\d{8})', line)
        if m:
            return m.group(1)
    return "無"


def _elec_amount(texts):
    for line in texts:
        m = re.search(r'總計[：:]\s*(\d+)', line)
        if m:
            return int(m.group(1))
    for line in texts:
        if re.search(r'TEL|電話|\d{8}', line):
            continue
        m = re.search(r'\b(\d{2,5})\b', line)
        if m:
            val = int(m.group(1))
            if 10 <= val <= 99999:
                return val
    return None


# --- 從 YOLO 框內 OCR 文字解析各欄位值(輔助判決) ---
def _hint_taxid(text):
    if not text:
        return None
    norm_txt = _norm(text)
    for m in re.finditer(r'(?<!\d)(\d{8})(?!\d)', norm_txt):
        val = m.group(1)
        if not _is_part_of_invoice_number(norm_txt, m.start()):
            return val
    return None


def _taxids_in(text):
    """從一段文字抽出所有「乾淨 8 碼統編」,並排除電話號碼片段。"""
    if not text:
        return []
    t = _norm(text)
    # 先移除電話片段,避免把電話當統編
    t = re.sub(r'(?:TEL|電話|电话|tel)\s*[:：]?\s*[()\d\-\s]{6,}', ' ', t)
    t = re.sub(r'\(0\d\)\s*\d{6,}', ' ', t)
    out = []
    for m in re.finditer(r'(?<!\d)(\d{8})(?!\d)', t):
        val = m.group(1)
        if not _is_part_of_invoice_number(t, m.start()):
            if val not in out:
                out.append(val)
    return out


def _all_taxids(texts):
    """全圖 OCR 所有文字中的 8 碼統編候選(去重、排除電話)。"""
    out = []
    for line in texts:
        for tid in _taxids_in(line):
            if tid not in out:
                out.append(tid)
    return out


def _best_taxid_match(box_text, candidates):
    """
    YOLO 框內讀不到乾淨 8 碼(位數不對/夾雜雜訊)時:
    把框內的數字串,跟全圖 OCR 找到的 8 碼候選逐一比相似度,挑最像的填入。
    框內幾乎沒數字 → 回 None(無從比對,交給後備邏輯)。
    """
    if not candidates:
        return None
    digits = re.sub(r'\D', '', _norm(box_text or ''))
    if len(digits) < 4:
        return None
    best, best_score = None, 0.0
    for c in candidates:
        score = difflib.SequenceMatcher(None, digits, c).ratio()
        if score > best_score:
            best, best_score = c, score
    return best if best_score >= 0.5 else None


def _hint_invoice_num(text):
    if not text:
        return None
    m = re.search(r'[A-Z]{2}-?\d{8}', _norm(text))
    return m.group().replace('-', '') if m else None


# 金額關鍵字(用來判斷阿拉伯數字是否真的是金額)
_AMT_KW = re.compile(
    r'合計|合计|總計|总计|小計|小计|總額|总额|金額|金额|計|总'
    r'|新台幣|新臺幣|台幣|台帶|元整|元|圓|圆|塊|NT|\$'
)


def _arabic_amount(text):
    """
    抓「金額關鍵字附近」的阿拉伯數字(如 合計500 / 計：1758 / 500元)。
    只認靠近關鍵字的數字 → 避免把日期、數量、統編當金額。
    排除 8 碼(統編)。多個就取最大。
    """
    if not text:
        return None
    t = _norm(text).replace(',', '').replace(' ', '')
    best = None
    for km in _AMT_KW.finditer(t):
        after = t[km.end():km.end() + 7]
        before = t[max(0, km.start() - 7):km.start()]
        for seg in (after, before):
            for m in re.finditer(r'(?<!\d)(\d{1,7})(?!\d)', seg):
                s = m.group(1)
                if len(s) == 8:          # 統編
                    continue
                v = int(s)
                if v <= 0:
                    continue
                if best is None or v > best:
                    best = v
    return best


def _hint_amount_digits(text):
    """(電子發票用,維持原始行為)框內任意阿拉伯數字,取最大。"""
    if not text:
        return None
    nums = re.findall(r'\d+', _norm(text).replace(',', ''))
    if not nums:
        return None
    return max(int(n) for n in nums)


def _hint_amount_digits_hw(text):
    """(手寫專用)框內任意阿拉伯數字,取最大,排除 8 碼統編。"""
    if not text:
        return None
    vals = [int(s) for s in re.findall(r'\d+', _norm(text).replace(',', ''))
            if len(s) != 8 and int(s) > 0]
    return max(vals) if vals else None


def _hint_amount_tw(text):
    """
    手寫金額判定:
      ① 阿拉伯數字(靠近金額關鍵字)優先
      ② 國字大寫(萬仟佰拾元,含誤讀對照)
      ③ 框內任意阿拉伯數字(取最大)
    """
    if not text:
        return None
    a = _arabic_amount(text)
    if a is not None:
        return a
    tw = _parse_tw_amount(_norm(text))
    if tw:
        return tw
    return _hint_amount_digits_hw(text)


def _hint_date_elec(text):
    return _elec_date(_norm_all([text])) if text else None


def _hint_date_hw(text):
    return _hw_date(_norm_all([text])) if text else None


# 名稱片段中要排除的標籤詞 / 店章樣板 / 地址 / 電話(都不是店名本身)
_HINT_NAME_SKIP = re.compile(
    r'統一編號|统一编號|统一编号|統編|電話|电话|TEL|地址|發票|发票|收據|收据'
    r'|證明聯|证明联|買方|买方|賣方|卖方|買受人|买受人|合計|合计|總計|总计'
    # 店章 / 收據樣板字(含常見 OCR 誤讀)
    r'|票章|發票章|发票章|登票章|專用|专用|免用|見用|见用|銀貨|银货|兩訖|两讫'
    r'|餐總|餐总|總章|总章|責任|责任|自責|自责|自青|自貴|自貴'
    # 地址用字
    r'|路|街|段|號|号|巷|弄|市|縣|县|區|区'
)


def _hint_name(text):
    """
    框內 OCR 文字常含多個片段(原圖+銳化兩版,以空白分隔),且夾雜
    英文與誤讀。挑出「含中文、非標籤詞、最長」的單一片段當名稱,
    避免把所有片段黏成亂碼(如 馬可先生MrMarl馬川光生MrMark)。
    """
    if not text:
        return None
    best = None
    best_len = 0
    for tok in re.split(r'\s+', text):
        t = _clean(tok)                       # 去符號,保留中英數
        if _zh_count(t) < 2:                  # 至少 2 個中文字才算名稱
            continue
        if _HINT_NAME_SKIP.search(tok) or _HINT_NAME_SKIP.search(t):
            continue
        zc = _zh_count(t)
        if zc > best_len:                     # 取中文字最多的片段(同長度取第一個)
            best, best_len = t, zc
    return best


def extract_electronic_fields(texts, ordered, yolo_hints=None):
    texts = _norm_all(texts)
    ordered = _norm_all(ordered)
    h = yolo_hints or {}

    # YOLO 為主、regex 為輔:YOLO 框內解析到值就用,否則退回原本掃描
    return {
        'invoice_type':  'electronic',
        'invoice_number': _hint_invoice_num(h.get('invoice_num')) or _elec_invoice_number(texts),
        'date':           _hint_date_elec(h.get('date'))          or _elec_date(texts),
        'vendor':         to_traditional(_hint_name(h.get('seller')) or _elec_vendor(ordered)),
        'seller_tax_id':  _hint_taxid(h.get('seller_taxid')) or _elec_seller(texts),
        'buyer_tax_id':   _hint_taxid(h.get('buyer_taxid'))  or _elec_buyer(texts),
        'buyer_name':     None,
        'amount':         _hint_amount_digits(h.get('amount')) or _elec_amount(texts),
    }


# =========================================================
# ② 手寫收據
# =========================================================

# 金額解析：萬仟佰拾元角(含常見手寫 OCR 誤讀變體)
_DIGIT_MAP = {
    '〇': 0, '零': 0, '○': 0, '大': 0, '0': 0,
    '一': 1, '壹': 1, '壱': 1, '弌': 1,
    '二': 2, '貳': 2, '贰': 2, '貮': 2, '弍': 2, '兩': 2, '两': 2,
    '三': 3, '參': 3, '参': 3, '叁': 3, '弎': 3,
    '四': 4, '肆': 4, '䦅': 4,
    '五': 5, '伍': 5,
    '六': 6, '陸': 6, '陆': 6,
    '七': 7, '柒': 7,
    '八': 8, '捌': 8,
    '九': 9, '玖': 9,
}
_UNITS = [
    (['萬', '万', '萠'],            10000),
    (['仟', '千', '什', '干'],        1000),  # 什/干 = 仟 常見誤讀
    (['佰', '百', '伯'],              100),   # 伯 = 佰 常見誤讀
    (['拾', '十'],                    10),
    (['元', '圓', '员', '园', '塊', '块'],  1),
]


def _parse_tw_amount(text):
    """
    萬仟佰拾元角 格式解析。
    例：百五拾元角 → 拾位=五 → 50；七百八拾元 → 佰=七=700, 拾=八=80 → 780
    """
    total = 0
    for keywords, weight in _UNITS:
        for kw in keywords:
            idx = text.find(kw)
            if idx > 0:
                prev = text[idx - 1]
                if prev in _DIGIT_MAP and _DIGIT_MAP[prev] > 0:
                    total += _DIGIT_MAP[prev] * weight
                elif prev.isdigit() and int(prev) > 0:
                    total += int(prev) * weight
                break
    return total if total > 0 else None


def _hw_amount(texts):
    # ① 阿拉伯數字(靠近金額關鍵字)優先 — 逐行找,避免跨行誤接
    for line in texts:
        a = _arabic_amount(line)
        if a is not None:
            return a
    # ② 國字大寫(原邏輯)
    chunks = [l for l in texts
              if '合計' in l or '合计' in l
              or any(kw in l for kw in ['萬', '仟', '佰', '拾', '元角', '元'])]
    combined = ''.join(chunks)
    result = _parse_tw_amount(combined)
    if result:
        return result
    for line in texts:
        result = _parse_tw_amount(line)
        if result:
            return result
    return None


def _hw_full_tw(texts):
    """全圖 OCR 的國字大寫金額(供交叉檢查用)。"""
    chunks = [l for l in texts
              if '合計' in l or '合计' in l
              or any(kw in l for kw in ['萬', '仟', '佰', '拾', '元角', '元'])]
    r = _parse_tw_amount(''.join(chunks))
    if r:
        return r
    for line in texts:
        r = _parse_tw_amount(line)
        if r:
            return r
    return None


def _hw_full_arabic(texts):
    """全圖 OCR 靠近金額關鍵字的阿拉伯數字(供交叉檢查用)。"""
    for line in texts:
        a = _arabic_amount(line)
        if a is not None:
            return a
    return None


def _hw_amount_crosscheck(box_text, texts):
    """
    手寫金額 + 交叉檢查(只限手寫)。
    四個來源各自取值:框內阿拉伯 / 框內大寫 / 全圖阿拉伯 / 全圖大寫。
      ① 大寫 ↔ 阿拉伯互驗   ② YOLO 框 ↔ 全圖一致性
    ≥2 個來源得到同一值 → 採用,信心 high。
    只有單一來源 → medium;多來源但互相衝突 → 取較可信者(框內>全圖、阿拉伯>大寫),信心 low。
    回傳 (amount, confidence)  confidence ∈ {'high','medium','low',None}
    """
    # (值, 權重) — 權重越高越可信:框內阿拉伯>框內大寫>全圖阿拉伯>全圖大寫
    sources = [
        (_arabic_amount(box_text),                          4),
        (_parse_tw_amount(_norm(box_text)) if box_text else None, 3),
        (_hw_full_arabic(texts),                            2),
        (_hw_full_tw(texts),                                1),
    ]
    weighted = [(v, w) for v, w in sources if v is not None and v > 0]
    if not weighted:
        return None, None

    # 統計每個值被幾個來源支持(互驗 / 一致性)
    support = {}
    for v, _ in weighted:
        support[v] = support.get(v, 0) + 1

    agreed = [v for v, c in support.items() if c >= 2]
    if agreed:
        # 取支持來源最多的;同票取權重最高者的值
        best = max(agreed, key=lambda v: (support[v],
                                          max(w for x, w in weighted if x == v)))
        return best, 'high'

    # 無任何兩來源一致
    weighted.sort(key=lambda x: -x[1])
    if len(weighted) == 1:
        return weighted[0][0], 'medium'   # 只有單一來源,無從互驗
    return weighted[0][0], 'low'          # 多來源但衝突 → 取最可信者


def _hw_date(texts):
    for line in texts:
        if '中華民國' in line or '民國' in line:
            m = re.search(r'(\d{2,3})\D+(\d{1,2})\D+(\d{1,2})', line)
            if m:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if y < 150:
                    return f"{y + 1911}-{mo:02d}-{d:02d}"
    return None


def _hw_tax_ids(texts):
    """
    印章數字油墨粗深，4 路 OCR 都認得到，頻率高 → texts 排序靠前 → 賣方。
    買方統編（表單填寫較細）頻率低 → 排序靠後。

    使用 (?<!\\d)(\\d{8})(?!\\d) 而非 \\b，因中文字也是 Unicode word char，
    會導致 "统一段69115908" 裡的 \\b 邊界消失而抓不到。
    """
    seen_order = []
    seen_set = set()
    for line in texts:
        if _PHONE.search(line):
            continue
        for m in re.finditer(r'(?<!\d)(\d{8})(?!\d)', line):
            tid = m.group(1)
            if not _is_part_of_invoice_number(line, m.start()):
                if tid not in seen_set:
                    seen_set.add(tid)
                    seen_order.append(tid)

    seller = seen_order[0] if len(seen_order) >= 1 else "無"
    buyer  = seen_order[1] if len(seen_order) >= 2 else "無"
    return buyer, seller


_BUYER_NAME_SKIP = re.compile(
    r'統一編號|统一编號|數量|数量|單價|總價|品名|備註|合計|合计|中華民國|民國'
    r'|免用統一發票|收據專用章|銀貨兩訖|統一發票章|自貴人|自貴人|自責人'
)


def _hw_buyer_name(texts, ordered):
    """買方名稱：買受人後面的文字 或 台照同行/鄰近的中文"""
    def is_valid_name(text, raw_line=''):
        t = _clean(text)
        if _zh_count(t) < 3:
            return False
        if _BUYER_NAME_SKIP.search(raw_line or text):
            return False
        return True

    # 1. 在 ordered 中找「買受人」後面的內容
    for i, line in enumerate(ordered):
        if '買受人' in line:
            after = re.split(r'買受人[：:]?', line, maxsplit=1)
            if len(after) > 1 and is_valid_name(after[1], after[1]):
                return _clean(after[1])
            for j in range(i + 1, min(i + 5, len(ordered))):
                if is_valid_name(ordered[j], ordered[j]):
                    return _clean(ordered[j])
            break

    # 2. 找含「台照」的行 → 從最近往遠找公司名
    for i, line in enumerate(ordered):
        if '台照' in line:
            t = _clean(line.replace('台照', ''))
            if is_valid_name(t, line):
                return t
            for j in range(i - 1, max(-1, i - 6), -1):
                if is_valid_name(ordered[j], ordered[j]):
                    return _clean(ordered[j])
            break

    # 3. fallback：在 texts 裡找「買受人」
    for line in texts:
        if '買受人' in line:
            after = re.split(r'買受人[：:]?', line, maxsplit=1)
            if len(after) > 1 and is_valid_name(after[1], after[1]):
                return _clean(after[1])

    return None


_HW_VENDOR_SKIP = re.compile(
    r'免用統一發票|收據專用章|統一發票章|統一編號|买受人|買受人|合計|合計'
    r'|銀貨兩訖|數量|數量|品名|備註|中華民國|民國'
    r'|自買人|自貴人|自責人|自貴人|自青人|責任人|萬國牌|万国牌'
    r'|票章|發票|發票章|統一經|統一.*章|見用|見用'
)
_HW_ADDR = re.compile(r'路|街|段|號|巷|弄|市|縣|區')
_HW_AMOUNT_KW = re.compile(r'[萬仟佰拾][元角分]|元角|合計|合計')


def _char_overlap(a, b):
    """兩字串的字元集合重疊率"""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(len(sa), len(sb))


def _hw_vendor(texts, buyer_name):
    """
    賣方名稱：從 texts 找 3+ 中文字、非標準格式的行。
    排除買方名稱（含 OCR 誤讀的相似版本），避免誤判。
    """
    candidates = []
    buyer_clean = _clean(buyer_name) if buyer_name else ''

    for line in texts:
        if _PHONE.search(line):
            continue
        if _HW_VENDOR_SKIP.search(line):
            continue
        if _HW_ADDR.search(line):
            continue
        if _HW_AMOUNT_KW.search(line):
            continue
        if re.search(r'中華民國|民國|\d+年\d+月', line):
            continue
        t = _clean(line)
        if buyer_clean and _char_overlap(buyer_clean, t) >= 0.7:
            continue
        if re.search(r'\d{8}', t):
            continue
        if _zh_count(t) >= 3:
            candidates.append(t)

    if not candidates:
        return "無"

    # 優先選有公司名稱後綴的（行/店/館/坊/廳/社/業 等）
    _CO_SUFFIX = re.compile(r'[行店館坊廳社業鋪舖咖啡廠]$')
    with_suffix = [c for c in candidates if _CO_SUFFIX.search(c) and 3 <= _zh_count(c) <= 8]
    if with_suffix:
        return max(with_suffix, key=_zh_count)

    # 其次：長度適中（3-8字）的候選，取最長
    good = [c for c in candidates if 3 <= _zh_count(c) <= 8]
    if good:
        return max(good, key=_zh_count)
    return max(candidates, key=_zh_count)


def extract_handwritten_fields(texts, ordered, yolo_hints=None):
    texts  = _norm_all(texts)
    ordered = _norm_all(ordered)
    h = yolo_hints or {}

    buyer_regex, seller_regex = _hw_tax_ids(texts)   # 原始頻率啟發式(後備)
    buyer_name = _hw_buyer_name(texts, ordered)
    vendor = _hw_vendor(texts, buyer_name)

    # ── 統編判定規則(手寫權重類別:amount, buyer, buyer_taxid, date, stamp) ──
    # 1. 買方統編 ← YOLO「buyer_taxid」框內的 8 碼
    # 2. 賣方統編 ← YOLO「stamp」店章框內的 8 碼(店章上的統編是賣家的)
    # 3. 框內讀不到乾淨 8 碼(位數不對/雜訊) → 拿框內數字跟全圖 OCR 候選比對,挑最像的
    # 4. 框內完全沒數字 → 回退原始 regex 判斷
    all_ids = _all_taxids(texts)

    buyer_box_ids  = _taxids_in(h.get('buyer_taxid'))
    seller_box_ids = _taxids_in(h.get('stamp'))

    buyer_tax_id = (
        (buyer_box_ids[0] if buyer_box_ids else None)
        or _best_taxid_match(h.get('buyer_taxid'), all_ids)
        or buyer_regex
    )
    seller_tax_id = (
        (seller_box_ids[0] if seller_box_ids else None)
        or _best_taxid_match(h.get('stamp'), all_ids)
        or seller_regex
    )

    # 防呆:買賣方統編不應相同。若相撞,店章(賣方)較可信,
    # 買方改抓其他候選,沒有就標「無」,避免賣家統編誤填到買方。
    if buyer_tax_id not in (None, "無") and buyer_tax_id == seller_tax_id:
        buyer_tax_id = next((c for c in all_ids if c != seller_tax_id), "無")

    buyer_name = _hint_name(h.get('buyer')) or buyer_name
    # stamp 框內若有中文,可當賣方名稱補強
    vendor = (_hint_name(h.get('stamp')) if _hint_name(h.get('stamp')) else None) or vendor

    # 金額 + 交叉檢查(大寫↔阿拉伯互驗、YOLO框↔全圖一致性)
    amount, amount_conf = _hw_amount_crosscheck(h.get('amount'), texts)

    return {
        'invoice_type':  'handwritten',
        'invoice_number': None,
        'date':           _hint_date_hw(h.get('date')) or _hw_date(texts),
        'vendor':         to_traditional(vendor),
        'seller_tax_id':  seller_tax_id,
        'buyer_tax_id':   buyer_tax_id,
        'buyer_name':     to_traditional(buyer_name),
        'amount':         amount,
        'amount_confidence': amount_conf,   # 手寫專用:high/medium/low
    }


# =========================================================
# 主入口
# =========================================================
def extract_fields(texts, ordered=None, receipt_type=None, yolo_hints=None):
    """
    receipt_type: 由分類器(classifier)決定的 'electronic'|'handwritten';
                  若為 None 則退回原本的文字判斷。
                  yolo_hints:   {class_name: ocr_text} — YOLO 框內 OCR 的文字,做輔助判決。
    """
    if ordered is None:
        ordered = texts

    invoice_type = receipt_type or detect_invoice_type(texts)

    if invoice_type == 'electronic':
        res = extract_electronic_fields(texts, ordered, yolo_hints)
    else:
        res = extract_handwritten_fields(texts, ordered, yolo_hints)

    # 確保日期規格化與警告提示 (不補齊缺失的部分，但回報提醒)
    date_warning = None
    if res.get('date'):
        d_val = res['date'].strip()
        # 相容其他分隔符號
        if '/' in d_val:
            d_val = d_val.replace('/', '-')
        elif '.' in d_val:
            d_val = d_val.replace('.', '-')
        res['date'] = d_val

        # 如果長度為 7 (例如 YYYY-MM)，說明缺少了「日」
        if len(d_val) == 7 and d_val[4] == '-':
            date_warning = f"日期只辨識出年份與月份（<b>{d_val}</b>），未辨識出『日』，請手動確認補齊。"
    else:
        date_warning = "未自動辨識出單據日期，請手動確認填寫。"

    res['date_warning'] = date_warning
    return res
