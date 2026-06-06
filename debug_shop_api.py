"""OKPOS 매장별매출분석 - 올바른 S_CONTROLLER(010)로 API 호출"""
import os, re, json, requests, urllib3
from datetime import date

urllib3.disable_warnings()
BASE_URL = "https://kis.okpos.co.kr"
USER_ID  = os.environ["KIS_ID"]
USER_PW  = os.environ["KIS_PW"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

def extract_token(html):
    for pat in [
        r"id='([0-9a-f-]{36})'\s+name='([0-9a-f-]{36})'\s+value='([0-9a-f-]{36})'",
        r'name="([0-9a-f-]{36})"[^>]*value="([0-9a-f-]{36})"',
        r'name="([0-9a-f-]{36})"[^>]*value="([^"]+)"',
        r"name='([0-9a-f-]{36})'[^>]*value='([^']+)'",
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            return (m.group(2), m.group(3)) if len(m.groups()) == 3 else (m.group(1), m.group(2))
    return None, None

def do_login():
    sess = requests.Session()
    sess.headers.update(HEADERS)
    r0 = sess.get(BASE_URL + "/login/login_form.jsp", verify=False, timeout=30)
    n, v = extract_token(r0.text)
    login_data = {"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W"}
    if n: login_data[n] = v
    r1 = sess.post(BASE_URL + "/login/login_check.jsp", data=login_data,
                   headers={"Referer": BASE_URL + "/login/login_form.jsp"}, verify=False, timeout=30)
    n, v = extract_token(r1.text)
    r2 = sess.post(BASE_URL + "/login/login_check_action.jsp",
                   data={"user_id": USER_ID, "user_pwd": USER_PW, "AutoFg": "W", n: v},
                   headers={"Referer": BASE_URL + "/login/login_check.jsp"}, verify=False, timeout=30)
    if "top_frame" not in r2.text:
        raise RuntimeError(f"Login failed: {r2.text[:200]}")
    sess.get(BASE_URL + "/login/top_frame.jsp", verify=False, timeout=30)
    print("Login OK")
    return sess


def call_shop_api(sess, jsp_path, ctrl, n, v, date1, date2):
    """dayranking010.jsp 폼 필드에 맞게 API 호출"""
    payload = {
        n: v,
        "S_CONTROLLER": ctrl,
        "S_METHOD": "search",
        "SHEETSEQ": "1",
        "S_SAVENAME": "SHOP_CD,SHOP_NM,TOT_SALE_AMT,TOT_DC_AMT,DCM_SALE_AMT,VAT_AMT,TOT_SALE_CNT,FD_GST_T_CNT,SALE_DATE_CNT",
        "S_ORDERBY": "",
        "date1_1": date1,
        "date1_2": date2,
        "date_period1": "366",
        "ss_SHOP_TYPE_FG": "%",
        "ss_SHOP_GROUP_CD": "%",
        "ss_TYPE_UD": "U",
        "ss_SEL_CNT": "500",
        "EX_CST": "false",
    }
    r = sess.post(BASE_URL + "/sale/shopsale/ddd.htmlSheetAction",
                  data=payload,
                  headers={"Referer": BASE_URL + jsp_path},
                  verify=False, timeout=15)
    try:
        d = r.json()
        code = d.get("Result", {}).get("Code", 0)
        msg  = d.get("Result", {}).get("Msg", "")
        rows = len(d.get("Data", []))
        return code, msg, rows, d
    except Exception as e:
        return None, str(e), 0, {}


def main():
    today = date.today().strftime("%Y-%m-%d")
    jan1  = date.today().strftime("%Y") + "-01-01"
    sess  = do_login()

    # 각 sub-page에서 토큰 + 올바른 컨트롤러로 API 호출
    sub_pages = [
        ("/sale/shopsale/dayranking010.jsp",   "sale.shopsale.dayranking010",   "매장순위"),
        ("/sale/shopsale/dayranking020.jsp",   "sale.shopsale.dayranking020",   "매장순위(상품)"),
        ("/sale/shopsale/monthranking010.jsp", "sale.shopsale.monthranking010", "매장월별순위"),
        ("/sale/shopsale/type010.jsp",         "sale.shopsale.type010",         "매장형태별"),
        ("/sale/shopsale/brand010.jsp",        "sale.shopsale.brand010",        "브랜드별"),
    ]

    print(f"\n=== 매장별매출분석 API 호출 (기간: {jan1} ~ {today}) ===")
    for jsp_path, ctrl, label in sub_pages:
        r = sess.get(BASE_URL + jsp_path,
                     headers={"Referer": BASE_URL + "/sale/shopsale/shopsale010.jsp"},
                     verify=False, timeout=15)
        n, v = extract_token(r.content.decode("utf-8", errors="ignore"))
        if not n:
            print(f"\n[{label}] CSRF 토큰 없음 (status={r.status_code})")
            continue

        code, msg, rows, d = call_shop_api(sess, jsp_path, ctrl, n, v, jan1, today)
        sym = "✅" if rows > 0 else ("⚠️" if code == 0 else "❌")
        print(f"\n[{label}] {sym} ctrl={ctrl} code={code} rows={rows} msg={msg}")

        if rows > 0:
            keys = list(d["Data"][0].keys())
            print(f"  Keys: {keys}")
            for row in d["Data"][:20]:
                print(f"  {json.dumps(row, ensure_ascii=False)}")

        # 오늘 하루만도 시도
        if rows == 0:
            code2, msg2, rows2, d2 = call_shop_api(sess, jsp_path, ctrl, n, v, today, today)
            print(f"  [오늘만] code={code2} rows={rows2} msg={msg2}")
            if rows2 > 0:
                keys = list(d2["Data"][0].keys())
                print(f"  Keys: {keys}")
                for row in d2["Data"][:20]:
                    print(f"  {json.dumps(row, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
