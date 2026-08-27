#!/usr/bin/env python3
"""
SSG build script — zoozoo.kr
JSON 데이터를 index.html에 빌드 타임에 주입해 크롤러에게 정적 텍스트를 제공합니다.
각 섹션은 <!-- ssg:name --> ... <!-- /ssg:name --> 마커로 표시됩니다.
"""
import json, re
from html import escape as h
from pathlib import Path

ROOT = Path(__file__).parent          # website-zzl/
DATA = ROOT.parent / 'website' / 'data'
SRC  = ROOT / 'index.html'
OUT  = ROOT.parent / 'deploy' / 'index.html'

# ── JSON 로드 ──────────────────────────────────────────────────────────
info     = json.loads((DATA / 'info.json').read_text('utf-8'))
programs = json.loads((DATA / 'programs.json').read_text('utf-8'))
prods    = json.loads((DATA / 'products.json').read_text('utf-8'))
notices  = json.loads((DATA / 'notices.json').read_text('utf-8'))

# ── 먹이체험 ──────────────────────────────────────────────────────────
feeding_items = info.get('feeding', [])
if feeding_items:
    feeding_html = '\n'.join(
        '<li><span class="text-white font-semibold" style="font-family:\'Noto Sans KR\',sans-serif">{type}:</span>'
        ' <span style="font-family:\'Noto Sans KR\',sans-serif">{feed_str}{animals}</span></li>'.format(
            type=h(f['type']),
            feed_str=(' ' + h(f['feed']) + ' /') if f.get('feed') else '',
            animals=h(f['animals'])
        )
        for f in feeding_items
    )
else:
    feeding_html = '<li>먹이체험 정보를 준비 중입니다.</li>'

# ── 운영 프로그램 ─────────────────────────────────────────────────────
DAY = ("font-size:10px;font-family:'JetBrains Mono',monospace;"
       "text-transform:uppercase;letter-spacing:0.1em;"
       "color:rgba(255,255,255,0.25);margin-bottom:8px;")
ROW = ("display:flex;justify-content:space-between;align-items:center;"
       "border-bottom:1px solid rgba(255,255,255,0.05);"
       "padding-bottom:10px;margin-bottom:10px;gap:12px;")
NM  = "font-size:13px;font-family:'Noto Sans KR',sans-serif;color:rgba(255,255,255,0.88);"
TM  = ("font-size:11px;font-family:'JetBrains Mono',monospace;"
       "color:#D4FF00;font-weight:700;white-space:nowrap;flex-shrink:0;")

weekday = programs.get('weekday', [])
weekend = programs.get('weekend', [])
prog_parts = []
if weekday:
    prog_parts.append(f'<div style="{DAY}">WEEKDAY (TUE-FRI)</div>')
    for p in weekday:
        prog_parts.append(
            f'<div style="{ROW}"><span style="{NM}">{h(p["name"])}</span>'
            f'<span style="{TM}">{h(p["time"])}</span></div>'
        )
if weekend:
    if weekday:
        prog_parts.append('<div style="height:12px"></div>')
    prog_parts.append(f'<div style="{DAY}">WEEKEND &amp; HOLIDAY</div>')
    for p in weekend:
        prog_parts.append(
            f'<div style="{ROW}"><span style="{NM}">{h(p["name"])}</span>'
            f'<span style="{TM}">{h(p["time"])}</span></div>'
        )
programs_html = '\n'.join(prog_parts) if prog_parts else '<div>운영 프로그램 정보를 준비 중입니다.</div>'

# ── 이용수칙 ──────────────────────────────────────────────────────────
conduct_items = info.get('conduct', [])
if conduct_items:
    EN = ("font-size:10px;font-family:'JetBrains Mono',monospace;"
          "text-transform:uppercase;color:rgba(255,255,255,0.35);letter-spacing:0.08em;")
    KO = "font-size:12px;font-family:'Noto Sans KR',sans-serif;color:rgba(255,255,255,0.55);margin-top:2px;"
    cols = [[], [], []]
    for i, r in enumerate(conduct_items):
        cols[i % 3].append(r)
    def col_html(col):
        items = ''.join(
            f'<div><div style="{EN}">- {h(r["en"])}</div>'
            f'<div style="{KO}">　{h(r["ko"])}</div></div>'
            for r in col
        )
        return f'<div class="space-y-4">{items}</div>'
    conduct_html = '\n'.join(col_html(c) for c in cols)
else:
    conduct_html = '<div>이용수칙 정보를 준비 중입니다.</div>'

# ── 예매 상품 ──────────────────────────────────────────────────────────
products = prods.get('products', [])
if products:
    p    = products[0]
    sale = p.get('sale_price', 0)
    orig = p.get('original_price', 0)
    rate = p.get('discount_rate') or (round((1 - sale / orig) * 100) if orig and orig > sale else 0)
    img  = p.get('image') or p.get('og_image') or ''
    url  = h(p.get('booking_url', '#'))
    img_block = (
        f'<img src="{h(img)}" alt="쥬쥬랜드 1인 입장권" class="w-full h-full object-cover '
        f'mix-blend-luminosity hover:mix-blend-normal transition duration-500">'
        if img else
        '<div class="w-full h-full flex items-center justify-center"><span class="text-4xl">🎟</span></div>'
    )
    orig_block = ''
    if orig and orig > sale:
        sale_badge = f'<span class="tag-badge text-[9px] px-2 py-0.5">SALE {rate}%</span>' if rate else ''
        orig_block = (
            f'<div class="flex flex-col items-start gap-1">'
            f'<span class="mono text-[11px] text-gray-500 line-through">{orig:,}원</span>'
            f'{sale_badge}</div>'
        )
    product_html = (
        f'<div class="aspect-[4/5] bg-[#111] mb-5 overflow-hidden relative">{img_block}</div>\n'
        f'<div class="mono text-[10px] text-gray-500 mb-1">TICKET PRICE / 입장요금 안내</div>\n'
        f'<div class="text-sm font-bold text-white mb-3">1인 입장권</div>\n'
        f'<div class="flex items-center gap-3 flex-wrap mb-5">\n'
        f'  <div class="mono text-3xl font-bold text-[#D4FF00]">₩ {sale:,}</div>\n'
        f'  {orig_block}\n'
        f'</div>\n'
        f'<a href="{url}" target="_blank" rel="noopener" id="bookingBtnEmpty"\n'
        f'   class="mt-auto block w-full py-4 border border-[#D4FF00]/40 text-sm font-bold '
        f'text-[#D4FF00] text-center hover:bg-[#D4FF00] hover:text-black transition">\n'
        f'  네이버 예약하기 →\n'
        f'</a>'
    )
else:
    product_html = (
        '<div class="flex flex-col h-full">\n'
        '  <div class="aspect-[4/5] bg-[#111] mb-6 overflow-hidden flex items-center justify-center">\n'
        '    <div class="mono text-[#D4FF00] text-center">\n'
        '      <div class="text-2xl font-black mb-2">ZZL</div>\n'
        '      <div class="text-[10px] opacity-60">입장권 정보 업데이트 중</div>\n'
        '    </div>\n'
        '  </div>\n'
        '  <a href="https://m.booking.naver.com/booking/5/bizes/480021?area=bmp&amp;lang=ko'
        '&amp;map-search=1&amp;service-target=map-pc&amp;theme=place"\n'
        '     class="mt-auto block w-full py-4 border border-white/20 mono text-xs text-center '
        'hover:bg-white hover:text-black transition"\n'
        '     target="_blank" rel="noopener">네이버 예약 바로가기 →</a>\n'
        '</div>'
    )

# ── 공지사항 ──────────────────────────────────────────────────────────
notice_list = notices.get('notices', [])
if notice_list:
    slides = []
    for n in notice_list:
        img_tag = f'<img src="{h(n["image"])}" alt="{h(n.get("alt", "공지"))}" class="notice-img">'
        inner   = (
            f'<a href="{h(n["link"])}" target="_blank" rel="noopener">{img_tag}</a>'
            if n.get('link') else img_tag
        )
        slides.append(f'<div class="swiper-slide">{inner}</div>')
    notices_html = '\n'.join(slides)
else:
    notices_html = (
        '<div class="swiper-slide">\n'
        '  <div class="border border-white/10 aspect-[16/6] flex items-center justify-center bg-[#0E0F0E]">\n'
        '    <div class="text-center">\n'
        '      <div class="mono text-[#D4FF00] text-sm font-black mb-2">현재 진행 중인 공지가 없습니다</div>\n'
        '      <p class="mono text-[10px] text-gray-600">최신 소식은 인스타그램을 확인해주세요</p>\n'
        '    </div>\n'
        '  </div>\n'
        '</div>'
    )

# ── index.html에 적용 ─────────────────────────────────────────────────
def replace_ssg(content, name, new_content):
    pattern = rf'<!-- ssg:{re.escape(name)} -->.*?<!-- /ssg:{re.escape(name)} -->'
    replacement = f'<!-- ssg:{name} -->\n{new_content}\n<!-- /ssg:{name} -->'
    return re.sub(pattern, replacement, content, flags=re.DOTALL)

content = SRC.read_text('utf-8')
content = replace_ssg(content, 'feeding',  feeding_html)
content = replace_ssg(content, 'programs', programs_html)
content = replace_ssg(content, 'conduct',  conduct_html)
content = replace_ssg(content, 'product',  product_html)
content = replace_ssg(content, 'notices',  notices_html)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(content, 'utf-8')
print(f'SSG complete → {OUT}')
