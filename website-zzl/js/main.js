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
  const mapModalClose = document.getElementById('mapModalClose');
  const mapModalImg   = document.getElementById('mapModalImg');
  const mapModalArea  = document.getElementById('mapModalArea');
  let sc = 1, px = 0, py = 0;

  function openModal()  { if (!guideMapLoaded) return; mapModal.classList.add('open'); mapModal.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden'; sc=1;px=0;py=0;applyT(); }
  function closeModal() { mapModal.classList.remove('open'); mapModal.setAttribute('aria-hidden','true'); document.body.style.overflow=''; }
  function applyT()     { mapModalImg.style.transform=`translate(${px}px,${py}px) scale(${sc})`; }

  btnMapZoom?.addEventListener('click', () => { location.href = '/dogam'; });
  gmapPreview?.addEventListener('click', () => { if (guideMapLoaded) location.href = '/dogam'; });
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

  // 화면 회전 시 줌/팬 리셋 (비율 깨짐 방지)
  window.addEventListener('orientationchange', () => setTimeout(() => {
    if (mapModal?.classList.contains('open')) { sc=1; px=0; py=0; applyT(); }
  }, 150));

  /* ── 단체도시락 안내 모달 (핀치줌) ── */
  const lunchboxModal      = document.getElementById('lunchboxModal');
  const lunchboxModalClose = document.getElementById('lunchboxModalClose');
  const lunchboxModalImg   = document.getElementById('lunchboxModalImg');
  const lunchboxModalArea  = document.getElementById('lunchboxModalArea');
  const btnLunchboxPreview = document.getElementById('btnLunchboxPreview');
  let lsc = 1, lpx = 0, lpy = 0;

  function hideLunchboxModal()  { lunchboxModal.classList.remove('open'); lunchboxModal.setAttribute('aria-hidden','true'); document.body.style.overflow=''; }
  function openLunchboxModal()  {
    lunchboxModal.classList.add('open'); lunchboxModal.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden'; lsc=1;lpx=0;lpy=0;applyLT();
    history.pushState({ lunchboxModal: true }, '');
  }
  function closeLunchboxModal() {
    // 뒤로가기(popstate)에서 호출된 경우가 아니라면, 눌러서 연 history 항목을 되돌려
    // 브라우저 "뒤로가기"가 이전 페이지가 아니라 이 모달을 닫도록 만든다.
    if (history.state?.lunchboxModal) history.back();
    else hideLunchboxModal();
  }
  function applyLT()            { lunchboxModalImg.style.transform=`translate(${lpx}px,${lpy}px) scale(${lsc})`; }

  window.addEventListener('popstate', () => { if (lunchboxModal?.classList.contains('open')) hideLunchboxModal(); });

  btnLunchboxPreview?.addEventListener('click', openLunchboxModal);
  lunchboxModalClose?.addEventListener('click', closeLunchboxModal);
  lunchboxModal?.addEventListener('click', e => { if (e.target === lunchboxModal) closeLunchboxModal(); });
  document.addEventListener('keydown', e => { if (e.key==='Escape' && lunchboxModal?.classList.contains('open')) closeLunchboxModal(); });

  // 터치 줌/팬
  let lld=0,llt=0,lpan=false,lpsx=0,lpsy=0,lppx=0,lppy=0;
  lunchboxModalArea?.addEventListener('touchstart', e => {
    if (e.touches.length===2) { lld=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY); }
    else if (e.touches.length===1) {
      const now=Date.now();
      if(now-llt<300){lsc=lsc>1.5?1:2.5;lpx=0;lpy=0;applyLT();llt=0;return;}
      llt=now;lpan=true;lpsx=e.touches[0].clientX;lpsy=e.touches[0].clientY;lppx=lpx;lppy=lpy;
    }
  },{passive:true});
  lunchboxModalArea?.addEventListener('touchmove', e => {
    if(e.touches.length===2){const d=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);lsc=Math.min(Math.max(lsc*(d/lld),1),5);lld=d;applyLT();}
    else if(e.touches.length===1&&lpan&&lsc>1){lpx=lppx+(e.touches[0].clientX-lpsx);lpy=lppy+(e.touches[0].clientY-lpsy);applyLT();}
  },{passive:true});
  lunchboxModalArea?.addEventListener('touchend',()=>{lpan=false;});
  lunchboxModalArea?.addEventListener('wheel',e=>{e.preventDefault();lsc=Math.min(Math.max(lsc*(e.deltaY<0?1.12:0.89),1),5);if(lsc===1){lpx=0;lpy=0;}applyLT();},{passive:false});

  // 마우스 드래그
  let lmd=false,lmsx=0,lmsy=0,lmpx=0,lmpy=0;
  lunchboxModalArea?.addEventListener('mousedown',e=>{if(lsc<=1)return;lmd=true;lmsx=e.clientX;lmsy=e.clientY;lmpx=lpx;lmpy=lpy;lunchboxModalArea.classList.add('dragging');});
  document.addEventListener('mousemove',e=>{if(!lmd)return;lpx=lmpx+(e.clientX-lmsx);lpy=lmpy+(e.clientY-lmsy);applyLT();});
  document.addEventListener('mouseup',()=>{lmd=false;lunchboxModalArea?.classList.remove('dragging');});

  window.addEventListener('orientationchange', () => setTimeout(() => {
    if (lunchboxModal?.classList.contains('open')) { lsc=1; lpx=0; lpy=0; applyLT(); }
  }, 150));

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
              ? `<img src="${imgSrc}" alt="쥬쥬랜드 1인 입장권" class="w-full h-full object-cover mix-blend-luminosity hover:mix-blend-normal transition duration-500">`
              : `<div class="w-full h-full flex items-center justify-center"><span class="text-4xl">🎟</span></div>`}
          </div>
          <div class="mono text-[10px] text-gray-500 mb-1">TICKET PRICE / 입장요금 안내</div>
          <div class="text-sm font-bold text-white mb-3">1인 입장권</div>
          <div class="flex items-center gap-3 flex-wrap mb-5">
            <div class="mono text-3xl font-bold text-[#D4FF00]">₩ ${Number(p.sale_price).toLocaleString()}</div>
            ${p.original_price && p.original_price > p.sale_price ? `
              <div class="flex flex-col items-start gap-1">
                <span class="mono text-[11px] text-gray-500 line-through">${Number(p.original_price).toLocaleString()}원</span>
                ${rate ? `<span class="tag-badge text-[9px] px-2 py-0.5">SALE ${rate}%</span>` : ''}
              </div>` : ''}
          </div>
          <a href="${p.booking_url}" target="_blank" rel="noopener"
             class="mt-auto block w-full py-4 border border-[#D4FF00]/40 text-sm font-bold text-[#D4FF00] text-center hover:bg-[#D4FF00] hover:text-black transition">
            네이버 예약하기 →
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
      if (wrapper) wrapper.innerHTML = ''; // SSG 정적 콘텐츠 제거 후 최신 데이터로 교체
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

  /* ── 리뷰 무한 루프 슬라이더 ── */
  function initReviewSlider() {
    const outer    = document.getElementById('reviewsOuter');
    const track    = document.getElementById('reviewsTrack');
    const dotsWrap = document.getElementById('reviewDots');
    if (!outer || !track) return;

    const origCards = Array.from(track.querySelectorAll('.review-card'));
    const TOTAL = origCards.length;
    if (!TOTAL) return;

    // 원본 카드를 뒤에 복사 → [0..N-1 원본] [0..N-1 클론]
    origCards.forEach(c => {
      const clone = c.cloneNode(true);
      clone.setAttribute('aria-hidden', 'true');
      track.appendChild(clone);
    });

    const INTERVAL = 4500;
    const ANIM_MS  = 300;
    let idx = 0;
    let timer;
    let touchStartX = 0;

    function cardW() { return origCards[0].offsetWidth + 24; }

    function move(i, animated = true) {
      idx = i;
      track.style.transition = animated
        ? `transform ${ANIM_MS}ms cubic-bezier(0.25,0.46,0.45,0.94)`
        : 'none';
      track.style.transform = `translateX(-${idx * cardW()}px)`;
      updateDots(((idx % TOTAL) + TOTAL) % TOTAL);
    }

    // 클론 구간에 진입했으면 애니메이션 끝난 뒤 원본으로 순간 이동
    function wrapAfter() {
      if (idx >= TOTAL) {
        setTimeout(() => move(idx - TOTAL, false), ANIM_MS + 20);
      }
    }

    function buildDots() {
      if (!dotsWrap) return;
      dotsWrap.innerHTML = '';
      for (let i = 0; i < TOTAL; i++) {
        const dot = document.createElement('div');
        dot.style.cssText = 'width:6px;height:6px;border:1px solid rgba(212,255,0,0.4);border-radius:0;transition:all 0.25s;cursor:pointer;flex-shrink:0;';
        dot.addEventListener('click', () => { move(i); resetTimer(); });
        dotsWrap.appendChild(dot);
      }
      updateDots(0);
    }

    function updateDots(active) {
      if (!dotsWrap) return;
      dotsWrap.querySelectorAll('div').forEach((d, i) => {
        d.style.background  = i === active ? '#D4FF00' : 'transparent';
        d.style.borderColor = i === active ? '#D4FF00' : 'rgba(212,255,0,0.3)';
        d.style.width       = i === active ? '20px'   : '6px';
      });
    }

    function advance()    { move(idx + 1); wrapAfter(); }
    function startTimer() { timer = setInterval(advance, INTERVAL); }
    function stopTimer()  { clearInterval(timer); }
    function resetTimer() { stopTimer(); startTimer(); }

    buildDots();
    move(0, false);
    startTimer();

    outer.addEventListener('mouseenter', stopTimer);
    outer.addEventListener('mouseleave', startTimer);

    outer.addEventListener('touchstart', e => {
      touchStartX = e.touches[0].clientX;
      stopTimer();
    }, { passive: true });

    outer.addEventListener('touchend', e => {
      const diff = touchStartX - e.changedTouches[0].clientX;
      if (Math.abs(diff) > 40) {
        if (diff > 0) {
          // 왼쪽 스와이프 → 다음
          move(idx + 1);
          wrapAfter();
        } else {
          // 오른쪽 스와이프 → 이전; idx=0이면 클론 끝에서 역방향으로 시작
          if (idx === 0) {
            move(TOTAL, false);
            requestAnimationFrame(() => requestAnimationFrame(() => move(TOTAL - 1)));
          } else {
            move(idx - 1);
          }
        }
      }
      setTimeout(startTimer, 2500);
    }, { passive: true });

    window.addEventListener('resize', () => move(idx % TOTAL, false));
  }
  initReviewSlider();


})();
