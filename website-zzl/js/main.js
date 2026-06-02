/* ZZL — Main JS */
(() => {
  'use strict';

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
    try {
      const res = await fetch('data/programs.json', { cache: 'no-cache' });
      if (!res.ok) throw new Error();
      const { weekday=[], weekend=[] } = await res.json();
      let html = '';

      if (weekday.length) {
        html += '<div class="mono text-[9px] text-gray-600 mb-2 uppercase">WEEKDAY (TUE-FRI)</div>';
        weekday.forEach(p => {
          html += `<div class="flex justify-between border-b border-white/5 pb-2">
            <span class="text-[10px] mono">${p.name.toUpperCase()}</span>
            <span class="text-[10px] text-[#D4FF00] font-bold">${p.time} / ${p.location}</span>
          </div>`;
        });
      }
      if (weekend.length) {
        if (weekday.length) html += '<div class="h-3"></div>';
        html += '<div class="mono text-[9px] text-gray-600 mb-2 uppercase">WEEKEND / HOLIDAY</div>';
        weekend.forEach(p => {
          html += `<div class="flex justify-between border-b border-white/5 pb-2">
            <span class="text-[10px] mono">${p.name.toUpperCase()}</span>
            <span class="text-[10px] text-[#D4FF00] font-bold">${p.time}</span>
          </div>`;
        });
      }
      if (!weekday.length && !weekend.length) {
        html = '<div class="mono text-[10px] text-gray-600">NO_PROGRAMS_REGISTERED</div>';
      }
      c.innerHTML = html;
    } catch {
      c.innerHTML = '<div class="mono text-[10px] text-gray-600">SCHEDULE_UNAVAILABLE</div>';
    }
  }
  loadPrograms();

  /* ── 설정(이메일) ── */
  async function loadSettings() {
    try {
      const res = await fetch('data/settings.json', { cache: 'no-cache' });
      if (!res.ok) return;
      const { group_email } = await res.json();
      const gl = document.getElementById('groupEmailLink');
      if (group_email && gl) gl.href = `mailto:${group_email}`;
    } catch {}
  }
  loadSettings();

  /* ── 예매 상품 로딩 ── */
  async function loadProducts() {
    try {
      const res = await fetch('data/products.json', { cache: 'no-cache' });
      if (!res.ok) return;
      const { products=[] } = await res.json();
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

  /* ── 제휴 폼 ── */
  document.getElementById('partnerForm')?.addEventListener('submit', e => {
    e.preventDefault();
    const company = document.getElementById('fCompany')?.value.trim();
    const name    = document.getElementById('fName')?.value.trim();
    const phone   = document.getElementById('fPhone')?.value.trim();
    const email   = document.getElementById('fEmail')?.value.trim();
    const content = document.getElementById('fContent')?.value.trim();
    const note    = document.getElementById('partnerNote');
    if (!email) {
      if (note) { note.classList.remove('hidden'); note.style.color='#ff4444'; note.textContent='EMAIL_REQUIRED: input valid address'; }
      return;
    }
    const subj = encodeURIComponent(`[ZZL PARTNERSHIP] ${company||'N/A'} - ${name||'N/A'}`);
    const body = encodeURIComponent(`COMPANY: ${company}\nCONTACT: ${name}\nPHONE: ${phone}\nEMAIL: ${email}\n\nPROPOSAL:\n${content}`);
    window.location.href = `mailto:biz@zoozoo.kr?subject=${subj}&body=${body}`;
    if (note) { note.classList.remove('hidden'); note.style.color='#D4FF00'; note.textContent='EMAIL_CLIENT_OPENED — reply within 2-3 business days'; }
  });

})();
