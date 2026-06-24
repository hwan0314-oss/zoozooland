/* ZZL — Main JS */
(() => {
  'use strict';

  /* ── 인스타그램 피드 ── */
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  async function loadInstagramFeed() {
    const grid = document.getElementById('igFeed');
    if (!grid) return;
    try {
      const res = await fetch('data/instagram_feed.json', { cache: 'no-cache' });
      if (!res.ok) return;
      const { posts = [] } = await res.json();
      grid.innerHTML = posts.map(p => `
        <a href="${escapeHtml(p.permalink || '#')}" target="_blank" rel="noopener" class="photo-cell">
          <img src="${escapeHtml(p.image)}" alt="${escapeHtml(p.caption || 'ZZL Instagram')}" loading="lazy">
          <span class="photo-log">${escapeHtml((p.caption || '').slice(0, 24))}</span>
        </a>
      `).join('');
    } catch {}
  }
  loadInstagramFeed();

  /* ── 스무스 스크롤 ── */
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (!target) return;
      e.preventDefault();
      window.scrollTo({ top: target.offsetTop - 68, behavior: 'smooth' });
    });
  });

  /* ── 플로팅 버튼 ── */
  const floatBtn = document.getElementById('floatBtn');
  const guidemapSection = document.getElementById('guidemap');
  if (guidemapSection) {
    new IntersectionObserver(entries => {
      entries.forEach(e => floatBtn?.classList.toggle('show', !e.isIntersecting));
    }, { threshold: 0.1 }).observe(guidemapSection);
  }

  /* ── 푸터 연도 ── */
  const fy = document.getElementById('footerYear');
  if (fy) fy.textContent = new Date().getFullYear();

  /* ── 가이드맵 이미지 에러 처리 ── */
  const gmapImg     = document.getElementById('gmapImg');
  const gmapMissing = document.getElementById('gmapMissing');
  const btnMapZoom  = document.getElementById('btnMapZoom');
  const gmapPreview = document.getElementById('gmapPreview');
  let guideMapLoaded = false;

  if (gmapImg) {
    gmapImg.addEventListener('load',  () => { guideMapLoaded = true; });
    gmapImg.addEventListener('error', () => {
      guideMapLoaded = false;
      gmapImg.style.display = 'none';
      if (gmapMissing) gmapMissing.style.display = 'flex';
      if (btnMapZoom)  btnMapZoom.style.display  = 'none';
      const dl = document.getElementById('dlGuideMap');
      if (dl) dl.style.display = 'none';
    });
    if (gmapImg.complete && gmapImg.naturalWidth > 0) guideMapLoaded = true;
  }

  /* ── 가이드맵 모달 ── */
  const mapModal      = document.getElementById('mapModal');
  const mapModalBg    = mapModal?.querySelector('.map-modal-body')?.parentElement;
  const mapModalClose = document.getElementById('mapModalClose');
  const mapModalImg   = document.getElementById('mapModalImg');
  const mapModalArea  = document.getElementById('mapModalArea');
  let sc = 1, px = 0, py = 0;

  function openModal()  { if (!guideMapLoaded) return; mapModal.classList.add('open'); mapModal.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden'; sc=1;px=0;py=0;applyT(); }
  function closeModal() { mapModal.classList.remove('open'); mapModal.setAttribute('aria-hidden','true'); document.body.style.overflow=''; }
  function applyT()     { mapModalImg.style.transform=`translate(${px}px,${py}px) scale(${sc})`; }

  btnMapZoom?.addEventListener('click', openModal);
  gmapPreview?.addEventListener('click', () => { if (guideMapLoaded) openModal(); });
  mapModalClose?.addEventListener('click', closeModal);
  document.addEventListener('keydown', e => { if (e.key==='Escape' && mapModal?.classList.contains('open')) closeModal(); });

  // 모달 외부 클릭 닫기
  mapModal?.addEventListener('click', e => { if (e.target === mapModal) closeModal(); });

  // 터치 줌/팬
  let ld=0,lt=0,pan=false,psx=0,psy=0,ppx=0,ppy=0;
  mapModalArea?.addEventListener('touchstart', e => {
    if (e.touches.length===2) { ld=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY); }
    else if (e.touches.length===1) {
      const now=Date.now();
      if(now-lt<300){sc=sc>1.5?1:2.5;px=0;py=0;applyT();lt=0;return;}
      lt=now;pan=true;psx=e.touches[0].clientX;psy=e.touches[0].clientY;ppx=px;ppy=py;
    }
  },{passive:true});
  mapModalArea?.addEventListener('touchmove', e => {
    if(e.touches.length===2){const d=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);sc=Math.min(Math.max(sc*(d/ld),1),5);ld=d;applyT();}
    else if(e.touches.length===1&&pan&&sc>1){px=ppx+(e.touches[0].clientX-psx);py=ppy+(e.touches[0].clientY-psy);applyT();}
  },{passive:true});
  mapModalArea?.addEventListener('touchend',()=>{pan=false;});
  mapModalArea?.addEventListener('wheel',e=>{e.preventDefault();sc=Math.min(Math.max(sc*(e.deltaY<0?1.12:0.89),1),5);if(sc===1){px=0;py=0;}applyT();},{passive:false});

  // 마우스 드래그
  let md=false,msx=0,msy=0,mpx=0,mpy=0;
  mapModalArea?.addEventListener('mousedown',e=>{if(sc<=1)return;md=true;msx=e.clientX;msy=e.clientY;mpx=px;mpy=py;mapModalArea.classList.add('dragging');});
  document.addEventListener('mousemove',e=>{if(!md)return;px=mpx+(e.clientX-msx);py=mpy+(e.clientY-msy);applyT();});
  document.addEventListener('mouseup',()=>{md=false;mapModalArea?.classList.remove('dragging');});

  /* ── 프로그램 로딩 ── */
  async function loadPrograms() {
    const c = document.getElementById('programsList');
    if (!c) return;

    const dayLabel = t => `<div style="font-size:10px;font-family:'JetBrains Mono',monospace;text-transform:uppercase;letter-spacing:0.1em;color:rgba(255,255,255,0.25);margin-bottom:8px;">${t}</div>`;
    const row = (name, time) => `
      <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,0.05);padding-bottom:10px;margin-bottom:10px;gap:12px;">
        <span style="font-size:13px;font-family:'Noto Sans KR',sans-serif;color:rgba(255,255,255,0.88);">${name}</span>
        <span style="font-size:11px;font-family:'JetBrains Mono',monospace;color:#D4FF00;font-weight:700;white-space:nowrap;flex-shrink:0;">${time}</span>
      </div>`;

    try {
      const res = await fetch('data/programs.json', { cache: 'no-cache' });
      if (!res.ok) throw new Error();
      const { weekday=[], weekend=[] } = await res.json();
      let html = '';

      if (weekday.length) {
        html += dayLabel('WEEKDAY (TUE-FRI)');
        weekday.forEach(p => { html += row(p.name, p.time); });
      }
      if (weekend.length) {
        if (weekday.length) html += '<div style="height:12px"></div>';
        html += dayLabel('WEEKEND &amp; HOLIDAY');
        weekend.forEach(p => { html += row(p.name, p.time); });
      }
      if (!html) html = '<div style="font-size:10px;font-family:\'JetBrains Mono\',monospace;color:rgba(255,255,255,0.2);">NO_PROGRAMS_REGISTERED</div>';
      c.innerHTML = html;
    } catch {
      c.innerHTML = '<div style="font-size:10px;font-family:\'JetBrains Mono\',monospace;color:rgba(255,255,255,0.2);">SCHEDULE_UNAVAILABLE</div>';
    }
  }
  loadPrograms();

  /* ── info.json (먹이체험 + 이용수칙) 로딩 ── */
  async function loadInfo() {
    try {
      const res = await fetch('data/info.json', { cache: 'no-cache' });
      if (!res.ok) return;
      const { feeding=[], conduct=[] } = await res.json();

      // 먹이체험
      const fl = document.getElementById('feedingList');
      if (fl && feeding.length) {
        fl.innerHTML = feeding.map(f => `
          <li>
            <span class="text-white font-semibold" style="font-family:'Noto Sans KR',sans-serif">${f.type}:</span>
            <span style="font-family:'Noto Sans KR',sans-serif">
              ${f.feed ? ` ${f.feed} /` : ''} ${f.animals}
            </span>
          </li>`).join('');
      }

      // 이용수칙 (한영 병기)
      const cl = document.getElementById('conductList');
      if (cl && conduct.length) {
        // 3열 배치용 그룹핑
        const cols = [[], [], []];
        conduct.forEach((r, i) => cols[i % 3].push(r));
        cl.innerHTML = cols.map(col => `
          <div class="space-y-4">
            ${col.map(r => `
              <div>
                <div style="font-size:10px;font-family:'JetBrains Mono',monospace;text-transform:uppercase;color:rgba(255,255,255,0.35);letter-spacing:0.08em;">- ${r.en}</div>
                <div style="font-size:12px;font-family:'Noto Sans KR',sans-serif;color:rgba(255,255,255,0.55);margin-top:2px;">　${r.ko}</div>
              </div>`).join('')}
          </div>`).join('');
      }
    } catch {}
  }
  loadInfo();

  /* ── 설정(이메일) ── */
  async function loadSettings() {
    try {
      const res = await fetch('data/settings.json', { cache: 'no-cache' });
      if (!res.ok) return;
      const { group_email, biz_email } = await res.json();
      const gl = document.getElementById('groupEmailLink');
      if (group_email && gl) gl.href = `mailto:${group_email}`;
      const bl = document.getElementById('bizEmailLink');
      if (biz_email && bl) bl.href = `mailto:${biz_email}?subject=%5BZZL%20PARTNERSHIP%5D%20%EC%A0%9C%ED%9C%B4%20%EB%AC%B8%EC%9D%98`;
    } catch {}
  }
  loadSettings();

  /* ── 예매 상품 로딩 ── */
  async function loadProducts() {
    try {
      const res = await fetch('data/products.json', { cache: 'no-cache' });
      if (!res.ok) return;
      const { products=[] } = await res.json();

      // 첫 번째 상품의 booking_url로 예약 버튼 전체 업데이트
      if (products.length && products[0].booking_url) {
        const url = products[0].booking_url;
        ['bookingBtnHero', 'bookingBtnEmpty', 'bookingBtnCrm'].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.href = url;
        });
      }

      if (!products.length) return;

      const slot  = document.getElementById('productSlot');
      const empty = document.getElementById('productEmpty');
      if (!slot) return;
      empty?.remove();

      // 첫 번째 상품만 슬롯에 표시 (나머지는 row로 추가 가능)
      const p = products[0];
      const rate = p.discount_rate ?? (p.original_price && p.sale_price && p.original_price > p.sale_price
        ? Math.round((1 - p.sale_price / p.original_price) * 100) : 0);
      const imgSrc = p.image || p.og_image || null;

      slot.innerHTML = `
        <div class="card-frame bg-black p-6 h-full flex flex-col">
          <div class="aspect-[4/5] bg-[#111] mb-5 overflow-hidden relative">
            ${imgSrc
              ? `<img src="${imgSrc}" class="w-full h-full object-cover mix-blend-luminosity hover:mix-blend-normal transition duration-500">`
              : `<div class="w-full h-full flex items-center justify-center"><span class="text-4xl">🎟</span></div>`}
            ${rate ? `<div class="absolute top-3 right-3 tag-badge">SALE ${rate}%</div>` : ''}
          </div>
          <div class="flex justify-between items-start mb-2">
            <h3 class="text-xl font-bold">${p.name}</h3>
          </div>
          <div class="mono text-3xl font-bold text-[#D4FF00] mb-2">₩ ${Number(p.sale_price).toLocaleString()}</div>
          ${p.valid_until ? `<div class="mono text-[10px] text-gray-600 mb-5">VALID_UNTIL: ${p.valid_until}</div>` : '<div class="mb-5"></div>'}
          <a href="${p.booking_url}" target="_blank" rel="noopener"
             class="mt-auto block w-full py-4 border border-[#D4FF00]/40 mono text-xs text-[#D4FF00] text-center hover:bg-[#D4FF00] hover:text-black transition">
            BOOK VIA NAVER →
          </a>
        </div>`;

      // 추가 상품이 있으면 아래에 작은 카드로 표시
      if (products.length > 1) {
        const extra = document.createElement('div');
        extra.className = 'mt-4 space-y-3';
        products.slice(1).forEach(p2 => {
          const r2 = p2.discount_rate ?? 0;
          extra.innerHTML += `
            <div class="card-frame p-4 flex justify-between items-center cursor-pointer"
                 onclick="window.open('${p2.booking_url}','_blank')">
              <div>
                <div class="text-sm font-bold">${p2.name}</div>
                ${p2.valid_until ? `<div class="mono text-[9px] text-gray-600">VALID: ${p2.valid_until}</div>` : ''}
              </div>
              <div class="text-right">
                ${r2 ? `<div class="tag-badge mb-1">-${r2}%</div>` : ''}
                <div class="mono text-[#D4FF00] font-bold">₩${Number(p2.sale_price).toLocaleString()}</div>
              </div>
            </div>`;
        });
        slot.appendChild(extra);
      }
    } catch {}
  }
  loadProducts();

  /* ── 공지 Swiper ── */
  async function loadNotices() {
    const wrapper = document.getElementById('noticesWrapper');
    const placeholder = document.getElementById('noticePlaceholder');
    try {
      const res = await fetch('data/notices.json', { cache: 'no-cache' });
      if (!res.ok) return;
      const { notices=[] } = await res.json();
      if (!notices.length) { initSwiper(false); return; }
      placeholder?.remove();
      notices.forEach(n => {
        const slide = document.createElement('div');
        slide.className = 'swiper-slide';
        const inner = n.link
          ? `<a href="${n.link}" target="_blank" rel="noopener"><img src="${n.image}" alt="${n.alt||'공지'}" class="notice-img"></a>`
          : `<img src="${n.image}" alt="${n.alt||'공지'}" class="notice-img">`;
        slide.innerHTML = inner;
        wrapper?.appendChild(slide);
      });
      initSwiper(notices.length > 1);
    } catch { initSwiper(false); }
  }
  function initSwiper(loop) {
    if (typeof Swiper === 'undefined') return;
    new Swiper('.notices-swiper', {
      loop, grabCursor: true, keyboard: { enabled: true },
      autoplay: loop ? { delay: 4500, disableOnInteraction: false, pauseOnMouseEnter: true } : false,
      pagination: { el: '.swiper-pagination', clickable: true },
      navigation: { nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' },
    });
  }
  loadNotices().then(() => {
    if (document.getElementById('noticePlaceholder')) initSwiper(false);
  });

  /* ── 리뷰 자동 슬라이더 (탁탁 방식) ── */
  function initReviewSlider() {
    const outer = document.getElementById('reviewsOuter');
    const track = document.getElementById('reviewsTrack');
    const dotsWrap = document.getElementById('reviewDots');
    if (!outer || !track) return;

    const cards = Array.from(track.querySelectorAll('.review-card'));
    const TOTAL = cards.length;
    if (!TOTAL) return;

    const INTERVAL = 4500;
    let idx = 0;
    let timer;
    let touchStartX = 0;

    // 카드 너비 계산 (gap 24px 포함)
    function cardW() {
      return cards[0].offsetWidth + 24;
    }

    // 슬라이드 이동
    function goTo(i, instant = false) {
      idx = ((i % TOTAL) + TOTAL) % TOTAL;
      if (instant) track.classList.add('no-transition');
      track.style.transform = `translateX(-${idx * cardW()}px)`;
      if (instant) requestAnimationFrame(() => {
        requestAnimationFrame(() => track.classList.remove('no-transition'));
      });
      updateDots();
    }

    // 인디케이터 점
    function buildDots() {
      if (!dotsWrap) return;
      dotsWrap.innerHTML = '';
      for (let i = 0; i < TOTAL; i++) {
        const dot = document.createElement('div');
        dot.style.cssText = `
          width:6px;height:6px;border:1px solid rgba(212,255,0,0.4);
          border-radius:0;transition:all 0.25s;cursor:pointer;flex-shrink:0;
        `;
        dot.addEventListener('click', () => { goTo(i); resetTimer(); });
        dotsWrap.appendChild(dot);
      }
      updateDots();
    }
    function updateDots() {
      if (!dotsWrap) return;
      dotsWrap.querySelectorAll('div').forEach((d, i) => {
        d.style.background   = i === idx ? '#D4FF00' : 'transparent';
        d.style.borderColor  = i === idx ? '#D4FF00' : 'rgba(212,255,0,0.3)';
        d.style.width        = i === idx ? '20px'    : '6px';
      });
    }

    function advance()    { goTo(idx + 1); }
    function startTimer() { timer = setInterval(advance, INTERVAL); }
    function stopTimer()  { clearInterval(timer); }
    function resetTimer() { stopTimer(); startTimer(); }

    buildDots();
    startTimer();

    // 호버 일시정지
    outer.addEventListener('mouseenter', stopTimer);
    outer.addEventListener('mouseleave', startTimer);

    // 터치 스와이프
    outer.addEventListener('touchstart', e => {
      touchStartX = e.touches[0].clientX;
      stopTimer();
    }, { passive: true });
    outer.addEventListener('touchend', e => {
      const diff = touchStartX - e.changedTouches[0].clientX;
      if (Math.abs(diff) > 40) goTo(diff > 0 ? idx + 1 : idx - 1);
      setTimeout(startTimer, 2500);
    }, { passive: true });

    // 리사이즈 시 위치 보정
    window.addEventListener('resize', () => goTo(idx, true));
  }
  initReviewSlider();


})();
