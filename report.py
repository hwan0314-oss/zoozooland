import asyncio
import io
import json
import os
import re
from datetime import date, timedelta, datetime, timezone

import requests
import telegram
import urllib3
from PIL import Image, ImageDraw, ImageFont

urllib3.disable_warnings()

BASE_URL  = "https://kis.okpos.co.kr"
API_URL   = BASE_URL + "/sale/sale/ddd.htmlSheetAction"

USER_ID   = os.environ["KIS_ID"]
USER_PW   = os.environ["KIS_PW"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

KST = timezone(timedelta(hours=9))

FOOD_KEYWORDS    = ["먹이", "양분유체험"]
ONLINE_TICKETS   = {"온라인티켓(LS)", "네이버 주중", "네이버 주말"}
ONLINE_TICKET_PRICE = 15_000
FREE_PRODUCTS    = {"24개월미만무료입장", "초대권"}

STORE_KEYS = [
    ("레스토랑",     "레스토랑"),
    ("카페테리아",   "카페테리아"),
    ("레스토랑신규", "레스토랑(신)"),
    ("무인점포",     "무인점포"),
    ("드론체험",     "드론체험"),
    ("베이커리",     "베이커리"),
]

S_SAVENAME = (
    "sSeq|LCLS_NM|MCLS_NM|SCLS_NM|SALE_DATE|PROD_CD|BAR_CD|MAP_PROD_CD"
    "|PROD_NM|VENDORS_NM|COLOR_CD|SIZE_STR_CD|SALE_QTY|PROD_WEIGHT"
    "|TOT_SALE_AMT|TOT_DC_AMT|DCM_SALE_AMT|DC_AMT_GEN|DC_AMT_SVC"
    "|DC_AMT_JCD|DC_AMT_CPN|DC_AMT_CST|DC_AMT_FOD|DC_AMT_PACK"
    "|DC_AMT_YAP|SHOP_CD"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# ─── Image style constants ────────────────────────────────────────────────────
FONT_REGULAR = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_BOLD    = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

C_TITLE_BG  = ( 30,  45,  60)
C_PERIOD_BG = ( 44,  62,  80)
C_COL_BG    = ( 58,  79,  99)
C_ROW_ODD   = (255, 255, 255)
C_ROW_EVEN  = (245, 248, 251)
C_ROW_TOTAL = (230, 242, 252)
C_SEP_ROW   = (173, 186, 199)
C_BORDER    = (180, 192, 205)
C_P_BORDER  = ( 90, 120, 155)   # thicker border between period groups
C_WHITE     = (255, 255, 255)
C_TEXT      = ( 44,  62,  80)
C_SUB       = ( 90, 110, 130)
C_POS       = ( 39, 174,  96)
C_NEG       = (192,  57,  43)
C_NA        = (127, 140, 141)


# ─── Login / session ──────────────────────────────────────────────────────────

def extract_token(html):
    m = re.search(
        r"id='([0-9a-f-]{36})'\s+name='([0-9a-f-]{36})'\s+value='([0-9a-f-]{36})'",
        html, re.IGNORECASE,
    )
    if m:
        return m.group(2), m.group(3)
    m = re.search(r'name="([0-9a-f-]{36})"[^>]*value="([0-9a-f-]{36})"', html, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r'name="([0-9a-f-]{36})"[^>]*value="([^"]+)"', html, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"name='([0-9a-f-]{36})'[^>]*value='([^']+)'", html, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    return None, None


def do_login():
    sess = requests.Session()
    sess.headers.update(HEADERS)
    r0 = sess.get(BASE_URL + "/login/login_form.jsp", verify=False, timeout=30)
    print(f"login_form: {r0.status_code} len={len(r0.text)}")
    form_tok_n, form_tok_v = extract_token(r0.text)
    print(f"form token: {form_tok_n[:8] if form_tok_n else None}...")
    login_data = {"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W"}
    if form_tok_n:
        login_data[form_tok_n] = form_tok_v
    r1 = sess.post(
        BASE_URL + "/login/login_check.jsp", data=login_data,
        headers={"Referer": BASE_URL + "/login/login_form.jsp"}, verify=False, timeout=30,
    )
    print(f"login_check: {r1.status_code} len={len(r1.text)}")
    tok_name, tok_val = extract_token(r1.text)
    if not tok_name:
        raise RuntimeError(f"No CSRF token. HTML: {r1.text[:300]}")
    print(f"CSRF: {tok_name[:8]}...")
    r2 = sess.post(
        BASE_URL + "/login/login_check_action.jsp",
        data={"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W", tok_name: tok_val},
        headers={"Referer": BASE_URL + "/login/login_check.jsp"}, verify=False, timeout=30,
    )
    print(f"login_action: {r2.status_code} len={len(r2.text)}")
    if "top_frame" not in r2.text:
        raise RuntimeError(f"Login failed. Response: {r2.text[:200]}")
    sess.get(BASE_URL + "/login/top_frame.jsp", verify=False, timeout=30)
    print("Login OK!")
    return sess


def get_api_token(sess):
    r1 = sess.get(
        BASE_URL + "/sale/sale/prod010.jsp",
        headers={"Referer": BASE_URL + "/login/top_frame.jsp"}, verify=False, timeout=30,
    )
    print(f"prod010: {r1.status_code} len={len(r1.text)}")
    tok10n, tok10v = extract_token(r1.text)
    if not tok10n:
        raise RuntimeError(f"No token in prod010. HTML: {r1.text[:300]}")
    r2 = sess.post(
        BASE_URL + "/sale/sale/prod011.jsp", data={tok10n: tok10v},
        headers={"Referer": BASE_URL + "/sale/sale/prod010.jsp"}, verify=False, timeout=30,
    )
    print(f"prod011: {r2.status_code} len={len(r2.text)}")
    if "S_CONTROLLER" not in r2.text:
        raise RuntimeError(f"prod011 bad response. First 200: {r2.text[:200]}")
    tok11n, tok11v = extract_token(r2.text)
    if not tok11n:
        raise RuntimeError("No token in prod011")
    print(f"prod011 token: {tok11n[:8]}...")
    return tok11n, tok11v


# ─── Sales data fetching ──────────────────────────────────────────────────────

def fetch_sales(sess, tok_name, tok_val, date_from, date_to):
    payload = {
        tok_name: tok_val,
        "S_CONTROLLER": "sale.sale.prod011", "S_METHOD": "search",
        "SHEETSEQ": "1", "S_SAVENAME": S_SAVENAME, "S_ORDERBY": "",
        "ss_PROD_FG": "N", "date1_1": date_from, "date1_2": date_to,
        "date_period1": "366",
        "ss_PROD_CD": "", "ss_PROD_NM": "",
        "ss_LCLS_CD": "", "ss_MCLS_CD": "", "ss_SCLS_CD": "", "ss_SIZE_CLS_CD": "",
        "ss_CLS_TEXT": "전체", "ss_BAR_CD": "", "ss_SHOP_CD": "",
        "ss_SHOP_NM": "전체", "ss_SHOP_INFO": "[]",
        "ss_VENDOR_CD": "", "ss_VENDOR_NM": "전체", "ss_VENDOR_INFO": "[]",
        "ss_chk": "0", "ss_PAGE_SIZE": "500", "ss_PAGE_NO1": "1",
    }
    r = sess.post(API_URL, data=payload,
                  headers={"Referer": BASE_URL + "/sale/sale/prod011.jsp"},
                  verify=False, timeout=60)
    print(f"API [{date_from}~{date_to}]: {r.status_code} len={len(r.text)}")
    data = json.loads(r.text)
    if "Result" in data and data["Result"].get("Code", 0) < 0:
        raise RuntimeError(f"API error: {data['Result']['Message']}")
    rows = data.get("Data", [])

    cats      = {}
    food      = {"qty": 0, "amt": 0}
    admission = {"individual": 0, "group": 0, "free": 0}

    for row in rows:
        cat     = row.get("MCLS_NM") or row.get("LCLS_NM") or "기타"
        prod_nm = (row.get("PROD_NM") or "").strip()
        scls_nm = (row.get("SCLS_NM") or "").strip()
        qty     = int(row.get("SALE_QTY", 0) or 0)
        amt     = qty * ONLINE_TICKET_PRICE if prod_nm in ONLINE_TICKETS \
                  else int(row.get("TOT_SALE_AMT", 0) or 0)

        if cat not in cats:
            cats[cat] = {"qty": 0, "amt": 0}
        cats[cat]["qty"] += qty
        cats[cat]["amt"] += amt

        if any(kw in prod_nm for kw in FOOD_KEYWORDS):
            food["qty"] += qty
            food["amt"] += amt

        if cat == "매표소":
            if prod_nm in FREE_PRODUCTS:
                admission["free"] += qty
            elif "단체" in scls_nm or "단체" in prod_nm:
                admission["group"] += qty
            elif "개인" in scls_nm:
                admission["individual"] += qty

    print(f"  Categories: {list(cats.keys())}")
    return {"cats": cats, "food": food, "admission": admission}


def fetch_sales_chunked(sess, date_from_str, date_to_str, max_days=90):
    start = date.fromisoformat(date_from_str)
    end   = date.fromisoformat(date_to_str)
    total = {
        "cats": {},
        "food": {"qty": 0, "amt": 0},
        "admission": {"individual": 0, "group": 0, "free": 0},
    }
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=max_days - 1), end)
        tn, tv = get_api_token(sess)
        chunk = fetch_sales(sess, tn, tv, current.isoformat(), chunk_end.isoformat())
        for cat, vals in chunk["cats"].items():
            if cat not in total["cats"]:
                total["cats"][cat] = {"qty": 0, "amt": 0}
            total["cats"][cat]["qty"] += vals["qty"]
            total["cats"][cat]["amt"] += vals["amt"]
        total["food"]["qty"] += chunk["food"]["qty"]
        total["food"]["amt"] += chunk["food"]["amt"]
        for k in ("individual", "group", "free"):
            total["admission"][k] += chunk["admission"][k]
        current = chunk_end + timedelta(days=1)
    return total


# ─── Data helpers ─────────────────────────────────────────────────────────────

def yoy(curr, prev):
    if not prev:
        return None
    return (curr - prev) / prev * 100

def fmt_num(n):
    return f"{int(n):,}"

def fyoy(v):
    if v is None:
        return "N/A"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%"


def _section_data(curr, prev):
    """(label, val_str, yoy_str) 리스트. None 은 구분선."""
    cats_c = curr["cats"];  cats_p = prev["cats"]
    fa     = curr["food"]["amt"]; pfa = prev["food"]["amt"]
    adm_c  = curr["admission"]; adm_p = prev["admission"]

    ind_c = adm_c["individual"]; ind_p = adm_p["individual"]
    grp_c = adm_c["group"];      grp_p = adm_p["group"]
    fre_c = adm_c["free"];       fre_p = adm_p["free"]
    tot_c = ind_c + grp_c + fre_c
    tot_p = ind_p + grp_p + fre_p

    tc, tp = 0, 0
    store_rows = []
    for k, lbl in STORE_KEYS:
        ca = cats_c.get(k, {}).get("amt", 0)
        pa = cats_p.get(k, {}).get("amt", 0)
        tc += ca; tp += pa
        store_rows.append((f"  {lbl}", f"{fmt_num(ca)}원", fyoy(yoy(ca, pa))))

    all_c = sum(v["amt"] for v in cats_c.values())
    all_p = sum(v["amt"] for v in cats_p.values())

    return [
        ("입장(전체)", f"{fmt_num(tot_c)}명", fyoy(yoy(tot_c, tot_p))),
        ("  개인",     f"{fmt_num(ind_c)}명", fyoy(yoy(ind_c, ind_p))),
        ("  단체",     f"{fmt_num(grp_c)}명", fyoy(yoy(grp_c, grp_p))),
        ("  무료",     f"{fmt_num(fre_c)}명", fyoy(yoy(fre_c, fre_p))),
        None,
        ("먹이판매",   f"{fmt_num(fa)}원",    fyoy(yoy(fa, pfa))),
        None,
        *store_rows,
        ("  점포합계", f"{fmt_num(tc)}원",    fyoy(yoy(tc, tp))),
        None,
        ("전체매출",   f"{fmt_num(all_c)}원", fyoy(yoy(all_c, all_p))),
    ]


# ─── Image rendering ──────────────────────────────────────────────────────────

def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except (IOError, OSError):
        return ImageFont.load_default()

def _yoy_color(s):
    if s == "N/A":        return C_NA
    if s.startswith("+"): return C_POS
    if s.startswith("-"): return C_NEG
    return C_TEXT


def create_report_image(today, dc, dp, mc, mp, yc, yp):
    fnt_r = _load_font(FONT_REGULAR, 14)
    fnt_b = _load_font(FONT_BOLD,    14)
    fnt_s = _load_font(FONT_REGULAR, 12)   # yoy values, sub-items
    fnt_t = _load_font(FONT_BOLD,    17)   # title

    # ── Build combined 7-column rows ──────────────────────────────────────
    d_rows = _section_data(dc, dp)
    m_rows = _section_data(mc, mp)
    y_rows = _section_data(yc, yp)

    combined = []
    for dr, mr, yr in zip(d_rows, m_rows, y_rows):
        if dr is None:
            combined.append(None)
        else:
            # (label, d_val, d_yoy, m_val, m_yoy, y_val, y_yoy)
            combined.append((dr[0], dr[1], dr[2], mr[1], mr[2], yr[1], yr[2]))

    # ── Measure text for column widths ────────────────────────────────────
    _tmp = Image.new("RGB", (1, 1))
    _td  = ImageDraw.Draw(_tmp)

    def _tw(text, font):
        b = _td.textbbox((0, 0), text, font=font)
        return b[2] - b[0]

    PAD = 16   # horizontal padding per cell (both sides combined)
    HDR = ["구분", "금액/수량", "전년비", "금액/수량", "전년비", "금액/수량", "전년비"]
    CFNT = [fnt_r, fnt_r, fnt_s, fnt_r, fnt_s, fnt_r, fnt_s]

    col_w = [_tw(h, fnt_b) + PAD for h in HDR]
    for row in combined:
        if row is None:
            continue
        for i, (cell, f) in enumerate(zip(row, CFNT)):
            col_w[i] = max(col_w[i], _tw(str(cell), f) + PAD)

    # Make sure period name fits its 2-column span
    for i, name in enumerate(["일별", "월누계", "연누계"]):
        needed = _tw(name, fnt_b) + PAD
        pair_w = col_w[1 + i*2] + col_w[2 + i*2]
        if needed > pair_w:
            diff = needed - pair_w
            col_w[1 + i*2] += (diff + 1) // 2
            col_w[2 + i*2] += diff // 2

    total_w = sum(col_w)
    cx = [sum(col_w[:i]) for i in range(7)]   # left-x of each column

    # ── Row heights ───────────────────────────────────────────────────────
    def _th(text, font):
        return _td.textbbox((0, 0), text, font=font)[3]

    VPAD    = 10
    base_h  = max(_th("가나Ag", fnt_r), _th("가나Ag", fnt_s))
    RH      = base_h + VPAD * 2   # data row height
    TITLE_H = 52
    P_H     = base_h + VPAD       # period header row
    C_H     = base_h + VPAD       # column header row
    SEP_H   = 4

    n_data = sum(1 for r in combined if r is not None)
    n_sep  = sum(1 for r in combined if r is None)
    img_h  = TITLE_H + P_H + C_H + n_data * RH + n_sep * SEP_H + 2

    img  = Image.new("RGB", (total_w, img_h), C_ROW_ODD)
    draw = ImageDraw.Draw(img)

    # ── Drawing helpers ───────────────────────────────────────────────────
    def fill(x, y, w, h, c):
        draw.rectangle([x, y, x + w - 1, y + h - 1], fill=c)

    def cell_text(x, y, w, h, s, font, color, align="center"):
        b   = draw.textbbox((0, 0), s, font=font)
        tw_ = b[2] - b[0];  th_ = b[3] - b[1]
        ty  = y + (h - th_) // 2
        if   align == "right": tx = x + w - tw_ - PAD // 2
        elif align == "left":  tx = x + PAD // 2
        else:                  tx = x + (w - tw_) // 2
        draw.text((tx, ty), s, font=font, fill=color)

    def hline(y, color=C_BORDER):
        draw.line([(0, y), (total_w - 1, y)], fill=color)

    def vline(x, y1, y2, color=C_BORDER, width=1):
        draw.line([(x, y1), (x, y2)], fill=color, width=width)

    # ── Title ─────────────────────────────────────────────────────────────
    cur_y = 0
    fill(0, cur_y, total_w, TITLE_H, C_TITLE_BG)
    cell_text(0, cur_y, total_w - 140, TITLE_H, "쥬쥬랜드 실적 리포트", fnt_t, C_WHITE)
    cell_text(total_w - 140, cur_y, 140, TITLE_H,
              today.strftime("%Y-%m-%d"), fnt_s, (160, 190, 215), "right")
    cur_y += TITLE_H
    header_top = cur_y

    # ── Period header (구분 spans P_H + C_H vertically) ───────────────────
    fill(cx[0], cur_y, col_w[0], P_H + C_H, C_PERIOD_BG)
    cell_text(cx[0], cur_y, col_w[0], P_H + C_H, "구분", fnt_b, C_WHITE)

    for i, name in enumerate(["일별", "월누계", "연누계"]):
        px = cx[1 + i * 2]
        pw = col_w[1 + i * 2] + col_w[2 + i * 2]
        fill(px, cur_y, pw, P_H, C_PERIOD_BG)
        cell_text(px, cur_y, pw, P_H, name, fnt_b, C_WHITE)

    cur_y += P_H

    # ── Column header ─────────────────────────────────────────────────────
    for i in range(1, 7):
        fill(cx[i], cur_y, col_w[i], C_H, C_COL_BG)
        cell_text(cx[i], cur_y, col_w[i], C_H, HDR[i], fnt_b, C_WHITE)

    cur_y += C_H
    header_bot = cur_y

    # Header border lines
    hline(header_top, C_BORDER)
    hline(header_bot - 1, C_BORDER)
    vline(cx[0] + col_w[0], header_top, header_bot, C_BORDER)
    vline(total_w - 1, header_top, header_bot, C_BORDER)
    # Thick dividers between period groups
    for i in (3, 5):
        vline(cx[i], header_top, header_bot, C_P_BORDER, 2)
    # Thin dividers within each period (val | yoy)
    for i in (2, 4, 6):
        vline(cx[i], header_top + P_H, header_bot, C_BORDER)

    # ── Data rows ─────────────────────────────────────────────────────────
    row_idx = 0
    for row in combined:
        if row is None:
            fill(0, cur_y, total_w, SEP_H, C_SEP_ROW)
            cur_y += SEP_H
            continue

        label    = row[0]
        is_total = "합계" in label or label == "전체매출"
        is_sub   = label.startswith("  ")
        bg = C_ROW_TOTAL if is_total else (C_ROW_ODD if row_idx % 2 == 0 else C_ROW_EVEN)
        fill(0, cur_y, total_w, RH, bg)

        lbl_font  = fnt_b if is_total else fnt_r
        lbl_color = C_SUB if is_sub else C_TEXT
        cell_text(cx[0], cur_y, col_w[0], RH, label.strip(), lbl_font, lbl_color, "left")

        for pi in range(3):
            vi, yi = 1 + pi * 2, 2 + pi * 2
            vf = fnt_b if is_total else fnt_r
            cell_text(cx[vi], cur_y, col_w[vi], RH, row[vi], vf, C_TEXT, "right")
            cell_text(cx[yi], cur_y, col_w[yi], RH, row[yi], fnt_s, _yoy_color(row[yi]), "right")

        # Row borders
        hline(cur_y + RH - 1)
        vline(cx[0] + col_w[0], cur_y, cur_y + RH, C_BORDER)
        vline(total_w - 1, cur_y, cur_y + RH, C_BORDER)
        for i in (3, 5):
            vline(cx[i], cur_y, cur_y + RH, C_P_BORDER, 2)
        for i in (2, 4, 6):
            vline(cx[i], cur_y, cur_y + RH, C_BORDER)

        cur_y  += RH
        row_idx += 1

    # Outer frame
    draw.rectangle([0, header_top, total_w - 1, cur_y - 1], outline=C_BORDER)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


# ─── Entry point ──────────────────────────────────────────────────────────────

async def main():
    today = datetime.now(KST).date()
    ms  = today.replace(day=1)
    pms = ms.replace(year=ms.year - 1)
    ys  = today.replace(month=1, day=1)
    pys = ys.replace(year=ys.year - 1)
    ptd = today.replace(year=today.year - 1)
    fmt_d = lambda d: d.strftime("%Y-%m-%d")

    sess = do_login()

    print("=== Current year ===")
    tn, tv = get_api_token(sess)
    dc = fetch_sales(sess, tn, tv, fmt_d(today), fmt_d(today))
    tn, tv = get_api_token(sess)
    mc = fetch_sales(sess, tn, tv, fmt_d(ms), fmt_d(today))
    yc = fetch_sales_chunked(sess, fmt_d(ys), fmt_d(today))

    print("=== Previous year ===")
    tn, tv = get_api_token(sess)
    dp = fetch_sales(sess, tn, tv, fmt_d(ptd), fmt_d(ptd))
    tn, tv = get_api_token(sess)
    mp = fetch_sales(sess, tn, tv, fmt_d(pms), fmt_d(ptd))
    yp = fetch_sales_chunked(sess, fmt_d(pys), fmt_d(ptd))

    print("Creating image...")
    img_buf = create_report_image(today, dc, dp, mc, mp, yc, yp)

    bot = telegram.Bot(token=BOT_TOKEN)
    await bot.send_photo(chat_id=CHAT_ID, photo=img_buf)
    print("Sent!")


if __name__ == "__main__":
    asyncio.run(main())
