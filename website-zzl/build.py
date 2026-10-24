#!/usr/bin/env python3
"""
SSG build script — zoozoo.kr
JSON 데이터를 index.html에 빌드 타임에 주입해 크롤러에게 정적 텍스트를 제공합니다.
각 섹션은 <!-- ssg:name --> ... <!-- /ssg:name --> 마커로 표시됩니다.

빌드된 HTML의 <img src="images/...jpg|png"> 는 WebP 반응형 이미지(<picture>)로 바꿉니다.
(Pillow가 없으면 이 단계만 건너뜁니다.)
"""
import json, re
from html import escape as h
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None

ROOT   = Path(__file__).parent          # website-zzl/
DATA   = ROOT.parent / 'website' / 'data'
IMAGES = ROOT.parent / 'website' / 'images'
SRC    = ROOT / 'index.html'
DEPLOY = ROOT.parent / 'deploy'
OUT    = DEPLOY / 'index.html'

# ── JSON 로드 ──────────────────────────────────────────────────────────
def load(name):
    path = DATA / name
    return json.loads(path.read_text('utf-8')) if path.exists() else {}

info     = load('info.json')
programs = load('programs.json')
prods    = load('products.json')
notices  = load('notices.json')
igfeed   = load('instagram_feed.json')
hours    = load('hours.json')
reviews  = load('reviews.json')
settings = load('settings.json')
faq      = load('faq.json')

DEFAULT_BOOKING_URL = ('https://m.booking.naver.com/booking/5/bizes/480021?area=bmp&lang=ko'
                       '&map-search=1&service-target=map-pc&theme=place')

# ── 먹이체험 ──────────────────────────────────────────────────────────
feeding_items = info.get('feeding', [])
if feeding_items:
    feeding_html = '\n'.join(
        '<li><span class="font-ko text-white font-semibold">{type}:</span>'
        ' <span class="font-ko">{feed_str}{animals}</span></li>'.format(
            type=h(f['type']),
            feed_str=(' ' + h(f['feed']) + ' /') if f.get('feed') else '',
            animals=h(f['animals'])
        )
        for f in feeding_items
    )
else:
    feeding_html = '<li>먹이체험 정보를 준비 중입니다.</li>'

# ── 운영 프로그램 ─────────────────────────────────────────────────────
def prog_row(p):
    return (f'<div class="prog-row"><span class="prog-name">{h(p["name"])}</span>'
            f'<span class="prog-time">{h(p["time"])}</span></div>')

weekday = programs.get('weekday', [])
weekend = programs.get('weekend', [])
prog_parts = []
if weekday:
    prog_parts.append('<div class="prog-day" data-group="weekday">WEEKDAY (TUE-FRI)</div>')
    prog_parts += [prog_row(p) for p in weekday]
if weekend:
    if weekday:
        prog_parts.append('<div class="prog-gap"></div>')
    prog_parts.append('<div class="prog-day" data-group="weekend">WEEKEND &amp; HOLIDAY</div>')
    prog_parts += [prog_row(p) for p in weekend]
programs_html = '\n'.join(prog_parts) if prog_parts else '<div>운영 프로그램 정보를 준비 중입니다.</div>'

# ── 이용수칙 ──────────────────────────────────────────────────────────
conduct_items = info.get('conduct', [])
if conduct_items:
    cols = [[], [], []]
    for i, r in enumerate(conduct_items):
        cols[i % 3].append(r)
    def col_html(col):
        items = ''.join(
            f'<div><div class="conduct-en">- {h(r["en"])}</div>'
            f'<div class="conduct-ko">　{h(r["ko"])}</div></div>'
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
        f'<img src="{h(img)}" alt="쥬쥬랜드 1인 입장권" loading="lazy" '
        f'data-sizes="(min-width: 1024px) 30vw, 100vw" class="w-full h-full object-cover '
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
        f'   data-booking data-track="booking_click" data-cta="ticket_card"\n'
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

# ── 오늘 운영 상태 기본 문구 (JS가 한국 시간 기준으로 갱신) / 하단 예약 바 가격 ──
hours_html = (f'운영시간 {h(hours["open"])}–{h(hours["close"])}'
              + (f' · {h(hours["closed_note"])}' if hours.get('closed_note') else '')
              if hours.get('open') and hours.get('close') else '운영시간 10:00–18:00')
if products:
    barprice_html = f'1인 ₩{sale:,}' + (f' · {rate}% 할인' if rate else '')
else:
    barprice_html = '네이버 예약'
booking_url = (products[0].get('booking_url') if products else None) or DEFAULT_BOOKING_URL

# ── 공지사항 ──────────────────────────────────────────────────────────
notice_list = notices.get('notices', [])
if notice_list:
    slides = []
    for n in notice_list:
        img_tag = f'<img src="{h(n["image"])}" alt="{h(n.get("alt", "공지"))}" class="notice-img" loading="lazy">'
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

# ── 인스타그램 피드 ───────────────────────────────────────────────────
ig_posts = igfeed.get('posts', [])
instagram_html = '\n'.join(
    f'<a href="{h(p.get("permalink") or "#")}" target="_blank" rel="noopener" class="photo-cell">'
    f'<img src="{h(p["image"])}" alt="{h(p.get("caption") or "ZZL Instagram")}" loading="lazy" data-sizes="33vw">'
    f'<span class="photo-log">{h((p.get("caption") or "")[:24])}</span></a>'
    for p in ig_posts if p.get('image')
)

# ── 리뷰 (data/reviews.json) ─────────────────────────────────────────
def review_card(i, r):
    # 카드 테두리·별 색을 라임/흰색으로 번갈아 표시
    lime = i % 2 == 0
    border = 'border-[#D4FF00]' if lime else 'border-white'
    star = 'text-[#D4FF00]' if lime else 'text-white'
    meta = 'text-[#D4FF00]' if lime else 'text-gray-400'
    rating = max(1, min(5, int(r.get('rating', 5))))
    tags = ' · '.join(h(t) for t in r.get('tags', []))
    return (
        f'<div class="review-card border-l-4 {border}">\n'
        f'  <div class="{star} mb-5 text-sm" aria-label="별점 {rating}점">{"★" * rating}</div>\n'
        f'  <blockquote class="text-base font-medium leading-relaxed mb-8">"{h(r["text"])}"</blockquote>\n'
        f'  <div class="flex justify-between items-end gap-3">\n'
        f'    <div><span class="mono text-[10px] {meta}">{h(r.get("meta", ""))}</span><br>'
        f'<span class="mono text-[9px] text-gray-500">{tags}</span></div>\n'
        f'    <span class="mono text-[8px] opacity-40">{h(r.get("date", ""))}</span>\n'
        f'  </div>\n'
        f'</div>'
    )

review_items = [r for r in reviews.get('reviews', []) if r.get('text')]
reviews_html = '\n'.join(review_card(i, r) for i, r in enumerate(review_items))
reviews_more_html = (
    f'<div class="px-6 mt-8"><a href="{h(reviews["more_url"])}" target="_blank" rel="noopener" '
    f'data-track="reviews_more_click" data-cta="reviews" '
    f'class="mono text-xs text-gray-400 hover:text-[#D4FF00] transition">네이버 리뷰 더 보기 →</a></div>'
    if reviews.get('more_url') else ''
)

# ── 카카오 채널 (settings.json kakao_channel_url 이 있을 때만 표시) ─────────
kakao_url = settings.get('kakao_channel_url') or ''
kakao_html = (
    f'<a href="{h(kakao_url)}" target="_blank" rel="noopener" '
    f'data-track="kakao_channel_click" data-cta="crm_kakao" '
    f'class="group p-12 border-t md:border-t-0 md:border-l border-white/10 hover:bg-[#3A1D1D] transition duration-500 block">\n'
    f'  <div class="mono text-xs mb-4 text-gray-500">PLATFORM: KAKAO</div>\n'
    f'  <h3 class="text-2xl md:text-3xl font-black mb-3 group-hover:translate-x-2 transition">카카오 채널 추가하고<br>먹이쿠폰 받기</h3>\n'
    f'  <p class="text-gray-400 text-sm mb-4">채널을 추가하시면<br>먹이쿠폰과 소식을 보내드려요</p>\n'
    f'  <div class="text-[#FEE500] mono text-xs">KAKAO_CHANNEL &gt;</div>\n'
    f'</a>'
    if kakao_url else ''
)

# ── 자주 묻는 질문 (data/faq.json) ───────────────────────────────────
def fmt_programs(items):
    return ', '.join(f'{p["name"]} {p["time"]}' for p in items) or '없음'

faq_values = {
    'open': hours.get('open', ''), 'close': hours.get('close', ''),
    'closed_note': hours.get('closed_note', ''), 'holiday_note': hours.get('holiday_note', ''),
    'sale_price': f'{sale:,}' if products else '', 'original_price': f'{orig:,}' if products else '',
    'programs_weekday': fmt_programs(weekday), 'programs_weekend': fmt_programs(weekend),
}
def fill(text):
    # {key} 자리만 바꾸고 모르는 중괄호는 그대로 둔다
    return re.sub(r'\{(\w+)\}', lambda m: str(faq_values.get(m.group(1), m.group(0))), text)

faq_items = [{'q': fill(i['q']), 'a': fill(i['a'])} for i in faq.get('items', []) if i.get('q') and i.get('a')]
faq_html = '\n'.join(
    f'<details class="faq-item">\n'
    f'  <summary>{h(i["q"])}</summary>\n'
    f'  <div class="faq-a">{h(i["a"]).replace(chr(10), "<br>")}</div>\n'
    f'</details>'
    for i in faq_items
)

# ── 구조화 데이터 (JSON-LD: Zoo + FAQPage) ────────────────────────────
DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
SITE = 'https://zoozoo.kr'
org = {
    '@type': ['Zoo', 'TouristAttraction'],
    '@id': f'{SITE}/#zoo',
    'name': '쥬쥬랜드',
    'alternateName': ['ZooZooLand', 'ZZL'],
    'url': f'{SITE}/',
    'description': '고양 동물 테마파크 쥬쥬랜드. 알파카·원숭이·파충류 50여 종과 함께하는 가장 힙한 동물원 나들이.',
    'image': f'{SITE}/images/og-image.jpg',
    'telephone': '+82-31-962-4500',
    'address': {
        '@type': 'PostalAddress',
        'streetAddress': '원당로458번길 7-42',
        'addressLocality': '고양시 덕양구',
        'addressRegion': '경기도',
        'addressCountry': 'KR',
    },
    'hasMap': 'https://map.naver.com/p/entry/place/1008136590',
    'sameAs': ['https://www.instagram.com/zoozooland_zzl/', 'https://map.naver.com/p/entry/place/1008136590'],
    'isAccessibleForFree': False,
    'inLanguage': 'ko',
}
if hours.get('open') and hours.get('close'):
    org['openingHoursSpecification'] = [{
        '@type': 'OpeningHoursSpecification',
        'dayOfWeek': [DAYS[d] for d in range(7) if d not in hours.get('closed_weekdays', [])],
        'opens': hours['open'], 'closes': hours['close'],
    }]
graph = [org]
if faq_items:
    graph.append({
        '@type': 'FAQPage',
        '@id': f'{SITE}/#faq',
        'mainEntity': [{'@type': 'Question', 'name': i['q'],
                        'acceptedAnswer': {'@type': 'Answer', 'text': i['a']}} for i in faq_items],
    })
jsonld_html = ('<script type="application/ld+json">\n'
               + json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, indent=2)
               .replace('</', '<\\/')
               + '\n</script>')

# ── index.html에 적용 ─────────────────────────────────────────────────
def replace_ssg(content, name, new_content, inline=False):
    pattern = rf'<!-- ssg:{re.escape(name)} -->.*?<!-- /ssg:{re.escape(name)} -->'
    nl = '' if inline else '\n'
    replacement = f'<!-- ssg:{name} -->{nl}{new_content}{nl}<!-- /ssg:{name} -->'
    return re.sub(pattern, lambda _: replacement, content, flags=re.DOTALL)

def mark_ssg(content, el_id):
    """JS가 이미 빌드된 콘텐츠를 다시 그리지 않도록 컨테이너에 data-ssg 표시"""
    return content.replace(f'id="{el_id}"', f'id="{el_id}" data-ssg', 1)

content = SRC.read_text('utf-8')
content = replace_ssg(content, 'feeding',  feeding_html)
content = replace_ssg(content, 'programs', programs_html)
content = replace_ssg(content, 'conduct',  conduct_html)
content = replace_ssg(content, 'product',  product_html)
content = replace_ssg(content, 'notices',  notices_html)
content = replace_ssg(content, 'instagram', instagram_html)
content = replace_ssg(content, 'hours',    hours_html, inline=True)
content = replace_ssg(content, 'barprice', barprice_html, inline=True)
if reviews_html:
    content = replace_ssg(content, 'reviews', reviews_html)
content = replace_ssg(content, 'reviews_more', reviews_more_html, inline=True)
content = replace_ssg(content, 'kakao', kakao_html)
content = replace_ssg(content, 'jsonld', jsonld_html)
if faq_html:
    content = replace_ssg(content, 'faq', faq_html)
if kakao_html:
    content = content.replace('class="grid" id="crmGrid"', 'class="grid md:grid-cols-2" id="crmGrid"', 1)
content = content.replace(DEFAULT_BOOKING_URL, booking_url)
for el_id, has_data in [('feedingList', feeding_items), ('programsList', prog_parts),
                        ('conductList', conduct_items), ('productSlot', products),
                        ('noticesWrapper', notice_list), ('igFeed', instagram_html)]:
    if has_data:
        content = mark_ssg(content, el_id)

# ── 이미지 최적화 (WebP 반응형) ──────────────────────────────────────
WIDTHS = (640, 1280, 1920)
MAX_W  = 2560
_variants = {}

def attr(tag, name):
    m = re.search(rf'(?<![\w-]){name}="([^"]*)"', tag)
    return m.group(1) if m else None

def make_variants(src):
    """images/... 원본에서 WebP 변형을 deploy/images 에 만들고 (w, h, srcset) 반환"""
    if src in _variants:
        return _variants[src]
    result = None
    path = IMAGES / src[len('images/'):]
    if Image and path.is_file():
        im = ImageOps.exif_transpose(Image.open(path))
        if im.mode not in ('RGB', 'RGBA'):
            im = im.convert('RGBA' if 'transparency' in im.info or im.mode in ('LA', 'P') else 'RGB')
        w, ht = im.size
        widths = [x for x in WIDTHS if x < w * 0.85] + [min(w, MAX_W)]
        srcset = []
        for vw in widths:
            rel = f'{src.rsplit(".", 1)[0]}-{vw}.webp'
            out = DEPLOY / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            im.resize((vw, round(ht * vw / w)), Image.LANCZOS).save(out, 'WEBP', quality=80, method=5)
            srcset.append(f'{h(rel)} {vw}w')
        # 이미 작은 원본(변형 1개)이 WebP로 더 커지면 원본을 그대로 쓴다
        if len(widths) == 1 and out.stat().st_size >= path.stat().st_size:
            out.unlink()
        else:
            result = (w, ht, ', '.join(srcset))
    _variants[src] = result
    return result

def to_picture(m):
    tag = m.group(0)
    src = attr(tag, 'src')
    if not src or not re.fullmatch(r'images/[^"]+\.(?:jpe?g|png)', src, re.I):
        return tag
    sizes = attr(tag, 'data-sizes') or '100vw'
    tag = re.sub(r'\s+data-sizes="[^"]*"', '', tag)
    v = make_variants(src)
    if not v:
        return tag
    w, ht, srcset = v
    if attr(tag, 'width') is None:
        tag = tag.replace('<img', f'<img width="{w}" height="{ht}"', 1)
    if attr(tag, 'decoding') is None:
        tag = tag.replace('<img', '<img decoding="async"', 1)
    return f'<picture><source type="image/webp" srcset="{srcset}" sizes="{sizes}">{tag}</picture>'

if Image is None:
    print('Pillow 미설치 — WebP 이미지 최적화를 건너뜁니다 (pip install pillow)')
content = re.sub(r'<img\b[^>]*>', to_picture, content)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(content, 'utf-8')

# ── sitemap.xml (빌드 날짜를 lastmod 로) ──────────────────────────────
from datetime import datetime, timedelta, timezone
today_kst = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
(DEPLOY / 'sitemap.xml').write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    f'  <url>\n    <loc>{SITE}/</loc>\n    <lastmod>{today_kst}</lastmod>\n'
    '    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n  </url>\n'
    '</urlset>\n', 'utf-8')
print(f'SSG complete → {OUT} (WebP: {sum(1 for v in _variants.values() if v)} images)')
