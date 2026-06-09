"""
데이터 검증 스크립트
====================
report.py 와 동일한 API 호출 경로를 사용해 금년/전년 데이터를 나란히 출력하여
전년비 계산 기준이 올바른지, 누락된 점포는 없는지 등을 검증합니다.

실행:
  python validate_data.py [YYYY-MM-DD]   # 날짜 생략 시 오늘
"""

import sys
from datetime import date, timedelta

# report.py 의 모든 함수/상수를 그대로 재사용
from report import (
    do_login, get_api_token, fetch_sales, fetch_sales_chunked,
    fetch_shop_sales, nearest_same_weekday_last_year, online_ticket_price,
    fmt_num, yoy, fyoy, STORE_KEYS, NAVER_TICKETS, LS_TICKETS,
    ONLINE_TICKETS, FREE_PRODUCTS,
)

SEP  = "=" * 80
SEP2 = "-" * 80

# ─── 날짜 설정 ────────────────────────────────────────────────────────────────
if len(sys.argv) > 1:
    today = date.fromisoformat(sys.argv[1])
else:
    from datetime import datetime, timezone, timedelta as td
    KST = timezone(td(hours=9))
    today = datetime.now(KST).date()

ms   = today.replace(day=1)                      # 월초 (금년)
ys   = today.replace(month=1, day=1)             # 연초 (금년)
ptd  = nearest_same_weekday_last_year(today)     # 전년 동일 요일
pms  = ms.replace(year=ms.year - 1)             # 월초 (전년)
pys  = ys.replace(year=ys.year - 1)             # 연초 (전년)

WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

def wd(d):
    return f"{d} ({WEEKDAY_KO[d.weekday()]})"

def fmt_d(d):
    return d.strftime("%Y-%m-%d")

print(SEP)
print("■ 조회 기간 요약")
print(SEP)
print(f"  금년 일별   : {wd(today)}")
print(f"  전년 일별   : {wd(ptd)}  ← nearest_same_weekday 적용")
print(f"    └ 원래 전년 동일일 : {today.replace(year=today.year-1)} ({WEEKDAY_KO[today.replace(year=today.year-1).weekday()]})")
print(f"    └ 요일 조정 일수  : {(ptd - today.replace(year=today.year-1)).days:+d}일")
print()
print(f"  금년 월누계 : {wd(ms)} ~ {wd(today)}")
print(f"  전년 월누계 : {wd(pms)} ~ {wd(ptd)}")
print()
print(f"  금년 연누계 : {wd(ys)} ~ {wd(today)}")
print(f"  전년 연누계 : {wd(pys)} ~ {wd(ptd)}")
print()

# ─── API 호출 ─────────────────────────────────────────────────────────────────
print(SEP)
print("■ 데이터 수집 중...")
print(SEP)

sess = do_login()

print("[금년] 일별/월누계/연누계 상품분류 판매 조회...")
tn, tv = get_api_token(sess); dc = fetch_sales(sess, tn, tv, fmt_d(today), fmt_d(today))
tn, tv = get_api_token(sess); mc = fetch_sales(sess, tn, tv, fmt_d(ms),    fmt_d(today))
yc = fetch_sales_chunked(sess, fmt_d(ys), fmt_d(today))

print("[금년] 일별/월누계/연누계 점포별 매출 조회...")
dc["shops"] = fetch_shop_sales(sess, fmt_d(today), fmt_d(today))
mc["shops"] = fetch_shop_sales(sess, fmt_d(ms),    fmt_d(today))
yc["shops"] = fetch_shop_sales(sess, fmt_d(ys),    fmt_d(today))

print("[전년] 일별/월누계/연누계 상품분류 판매 조회...")
tn, tv = get_api_token(sess); dp = fetch_sales(sess, tn, tv, fmt_d(ptd), fmt_d(ptd))
tn, tv = get_api_token(sess); mp = fetch_sales(sess, tn, tv, fmt_d(pms), fmt_d(ptd))
yp = fetch_sales_chunked(sess, fmt_d(pys), fmt_d(ptd))

print("[전년] 일별/월누계/연누계 점포별 매출 조회...")
dp["shops"] = fetch_shop_sales(sess, fmt_d(ptd), fmt_d(ptd))
mp["shops"] = fetch_shop_sales(sess, fmt_d(pms), fmt_d(ptd))
yp["shops"] = fetch_shop_sales(sess, fmt_d(pys), fmt_d(ptd))

print()

# ─── 헬퍼 ─────────────────────────────────────────────────────────────────────
def row3(label, cv, pv, width=28):
    yoy_s = fyoy(yoy(cv, pv))
    print(f"  {label:<{width}} {fmt_num(cv):>12}  vs  {fmt_num(pv):>12}   YoY {yoy_s}")

def section(title):
    print()
    print(SEP2)
    print(f"■ {title}")
    print(SEP2)
    print(f"  {'항목':<28} {'금년':>12}       {'전년':>12}   전년비")

# ─── 1. 입장객 수 ─────────────────────────────────────────────────────────────
for period, c, p, label in [
    ("일별",   dc, dp, f"{wd(today)}  vs  {wd(ptd)}"),
    ("월누계", mc, mp, f"{wd(ms)}~{wd(today)}  vs  {wd(pms)}~{wd(ptd)}"),
    ("연누계", yc, yp, f"{wd(ys)}~{wd(today)}  vs  {wd(pys)}~{wd(ptd)}"),
]:
    section(f"입장객 수 [{period}]  {label}")
    ind_c = c["admission"]["individual"]
    grp_c = c["admission"]["group"]
    fre_c = c["admission"]["free"]
    ind_p = p["admission"]["individual"]
    grp_p = p["admission"]["group"]
    fre_p = p["admission"]["free"]
    row3("개인(유료)",    ind_c, ind_p)
    row3("단체",         grp_c, grp_p)
    row3("무료",         fre_c, fre_p)
    row3("유료합계(개인+단체)", ind_c+grp_c, ind_p+grp_p)
    row3("전체합계",     ind_c+grp_c+fre_c, ind_p+grp_p+fre_p)

# ─── 2. 입장매출 ──────────────────────────────────────────────────────────────
for period, c, p, label in [
    ("일별",   dc, dp, f"{wd(today)}  vs  {wd(ptd)}"),
    ("월누계", mc, mp, f"{wd(ms)}~{wd(today)}  vs  {wd(pms)}~{wd(ptd)}"),
    ("연누계", yc, yp, f"{wd(ys)}~{wd(today)}  vs  {wd(pys)}~{wd(ptd)}"),
]:
    section(f"입장매출 [{period}]  {label}")
    ir_c = c["admission_rev"]["individual_pos"]
    gr_c = c["admission_rev"]["group"]
    ir_p = p["admission_rev"]["individual_pos"]
    gr_p = p["admission_rev"]["group"]
    nv_c = c["online_rev"]["naver"];  nv_p = p["online_rev"]["naver"]
    ls_c = c["online_rev"]["ls"];     ls_p = p["online_rev"]["ls"]
    row3("개인(POS+온라인추정)", ir_c, ir_p)
    row3("  └ 네이버 추정",     nv_c, nv_p)
    row3("  └ LS 추정",        ls_c, ls_p)
    row3("단체",               gr_c, gr_p)
    row3("입장매출 합계",       ir_c+gr_c, ir_p+gr_p)

# ─── 3. 먹이매출 ──────────────────────────────────────────────────────────────
for period, c, p, label in [
    ("일별",   dc, dp, f"{wd(today)}  vs  {wd(ptd)}"),
    ("월누계", mc, mp, f"{wd(ms)}~{wd(today)}  vs  {wd(pms)}~{wd(ptd)}"),
    ("연누계", yc, yp, f"{wd(ys)}~{wd(today)}  vs  {wd(pys)}~{wd(ptd)}"),
]:
    section(f"먹이매출 [{period}]  {label}")
    row3("먹이매출(동물먹이 카테고리)", c["food"]["amt"], p["food"]["amt"])
    row3("먹이 수량",                  c["food"]["qty"], p["food"]["qty"])

# ─── 4. 점포별 매출 ───────────────────────────────────────────────────────────
for period, c, p, label in [
    ("일별",   dc, dp, f"{wd(today)}  vs  {wd(ptd)}"),
    ("월누계", mc, mp, f"{wd(ms)}~{wd(today)}  vs  {wd(pms)}~{wd(ptd)}"),
    ("연누계", yc, yp, f"{wd(ys)}~{wd(today)}  vs  {wd(pys)}~{wd(ptd)}"),
]:
    sc = c.get("shops", {}); sp = p.get("shops", {})
    section(f"점포별 매출 [{period}]  {label}")

    # STORE_KEYS 기준 비교
    for k, lbl in STORE_KEYS:
        ca = sc.get(k, {}).get("amt", 0)
        pa = sp.get(k, {}).get("amt", 0)
        flag = "  ⚠ 전년 0" if pa == 0 and ca > 0 else ""
        row3(lbl, ca, pa)
        if flag:
            print(f"    └{flag}")

    # raw API 결과에 있지만 STORE_KEYS에 없는 매장 확인
    known = {k for k, _ in STORE_KEYS}
    extra_c = [k for k in sc if k not in known]
    extra_p = [k for k in sp if k not in known]
    if extra_c:
        print(f"\n  ⚠ 금년 API에 있지만 STORE_KEYS 미등록: {extra_c}")
        for k in extra_c:
            print(f"     {k}: {fmt_num(sc[k]['amt'])}원 ({sc[k]['cnt']}건)")
    if extra_p:
        print(f"\n  ⚠ 전년 API에 있지만 STORE_KEYS 미등록: {extra_p}")
        for k in extra_p:
            print(f"     {k}: {fmt_num(sp[k]['amt'])}원 ({sp[k]['cnt']}건)")

    # 전체 raw API 합계
    sum_c_api = sum(v["amt"] for v in sc.values())
    sum_p_api = sum(v["amt"] for v in sp.values())
    print()
    row3("[API 전체 raw 합계]", sum_c_api, sum_p_api)

    # 금년 원시 API 매장 목록 전체 출력
    print(f"\n  [금년 API 매장 전체 목록]")
    for k, v in sorted(sc.items(), key=lambda x: -x[1]["amt"]):
        print(f"     {k:<16} {fmt_num(v['amt']):>12}원  {v['cnt']:>5}건")
    print(f"  [전년 API 매장 전체 목록]")
    for k, v in sorted(sp.items(), key=lambda x: -x[1]["amt"]):
        print(f"     {k:<16} {fmt_num(v['amt']):>12}원  {v['cnt']:>5}건")

# ─── 5. 전체매출 검증 ─────────────────────────────────────────────────────────
print()
print(SEP)
print("■ 전체매출 공식 검증  (점포 raw 합계 + 네이버추정 + LS추정)")
print(SEP)

for period, c, p, label in [
    ("일별",   dc, dp, f"{wd(today)}  vs  {wd(ptd)}"),
    ("월누계", mc, mp, f"{wd(ms)}~{wd(today)}  vs  {wd(pms)}~{wd(ptd)}"),
    ("연누계", yc, yp, f"{wd(ys)}~{wd(today)}  vs  {wd(pys)}~{wd(ptd)}"),
]:
    sc = c.get("shops", {}); sp = p.get("shops", {})
    shop_c = sum(v["amt"] for v in sc.values())
    shop_p = sum(v["amt"] for v in sp.values())
    nv_c   = c["online_rev"]["naver"];  nv_p = p["online_rev"]["naver"]
    ls_c   = c["online_rev"]["ls"];     ls_p = p["online_rev"]["ls"]
    all_c  = shop_c + nv_c + ls_c
    all_p  = shop_p + nv_p + ls_p

    print(f"\n  [{period}]  {label}")
    print(f"  {'항목':<30} {'금년':>14}  {'전년':>14}")
    print(f"  {'점포 raw 합계':<30} {fmt_num(shop_c):>14}  {fmt_num(shop_p):>14}")
    print(f"    {'└ 네이버 추정매출 포함분':<28} {fmt_num(nv_c):>14}  {fmt_num(nv_p):>14}")
    print(f"    {'└ LS 추정매출 포함분':<28} {fmt_num(ls_c):>14}  {fmt_num(ls_p):>14}")
    print(f"  {'─'*60}")
    print(f"  {'전체매출 (표시값)':<30} {fmt_num(all_c):>14}  {fmt_num(all_p):>14}   YoY {fyoy(yoy(all_c, all_p))}")

# ─── 6. 상품분류(cats) 전체 덤프 ──────────────────────────────────────────────
print()
print(SEP)
print("■ 상품분류(MCLS_NM) 전체 목록 [일별 금년 / 전년]")
print(SEP)
all_cats = sorted(set(dc["cats"]) | set(dp["cats"]))
print(f"  {'분류명':<20} {'금년 수량':>10} {'금년 금액':>14}   {'전년 수량':>10} {'전년 금액':>14}")
for cat in all_cats:
    cc = dc["cats"].get(cat, {"qty": 0, "amt": 0})
    cp = dp["cats"].get(cat, {"qty": 0, "amt": 0})
    flag = " ← 누락" if cat not in dp["cats"] else ("" if cat in dc["cats"] else " ← 금년없음")
    print(f"  {cat:<20} {fmt_num(cc['qty']):>10} {fmt_num(cc['amt']):>14}   {fmt_num(cp['qty']):>10} {fmt_num(cp['amt']):>14}{flag}")

print()
print(SEP)
print("■ 검증 완료")
print(SEP)
