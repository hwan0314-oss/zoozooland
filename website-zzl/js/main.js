/* ZZL — Main JS */
(() => {
  'use strict';

  /* ── 내비게이션 ── */
  const nav = document.getElementById('nav');
  const navToggle = document.getElementById('navToggle');
  const navMobile = document.getElementById('navMobile');

  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 40);
  }, { passive: true });

  navToggle?.addEventListener('click', () => {
    const open = navMobile.classList.toggle('open');
    navToggle.classList.toggle('open', open);
    navToggle.setAttribute('aria-expanded', String(open));
  });
  navMobile?.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => {
      navMobile.classList.remove('open');
      navToggle.classList.remove('open');
      navToggle.setAttribute('aria-expanded', 'false');
    });
  });

  /* ── 스크롤 활성 메뉴 ── */
  const sections = document.querySelectorAll('[id]');
  const navItems = document.querySelectorAll('.nav-item');
  new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting)
        navItems.forEach(a => a.classList.toggle('active', a.getAttribute('href') === `#${e.target.id}`));
    });
  }, { rootMargin: '-60px 0px -60% 0px' }).observe && sections.forEach(s =>
    new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting)
          navItems.forEach(a => a.classList.toggle('active', a.getAttribute('href') === `#${e.target.id}`));
      });
    }, { rootMargin: '-60px 0px -60% 0px' }).observe(s)
  );

  /* ── 스크롤 리빌 ── */
  const ro = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); ro.unobserve(e.target); } });
  }, { threshold: 0.1 });
  document.querySelectorAll('.reveal, .reveal-dark').forEach(el => ro.observe(el));

  /* ── 플로팅 가이드맵 버튼 ── */
  const floatBtn = document.getElementById('floatBtn');
  const guideSection = document.getElementById('guidemap');
  if (guideSection) {
    new IntersectionObserver(entries => {
      entries.forEach(e => floatBtn?.classList.toggle('show', !e.isIntersecting));
    }, { threshold: 0.1 }).observe(guideSection);
  }

  /* ── 푸터 연도 ── */
  const fy = document.getElementById('footerYear');
  if (fy) fy.textContent = new Date().getFullYear();

  /* ── 가이드맵 이미지 에러 ── */
  const gmapImg = document.getElementById('gmapImg');
  const gmapMissing = document.getElementById('gmapMissing');
  const btnMapZoom = document.getElementById('btnMapZoom');
  const gmapPreview = document.getElementById('gmapPreview');
  let guideMapLoaded = false;

  if (gmapImg) {
    gmapImg.addEventListener('load', () => { guideMapLoaded = true; });
    gmapImg.addEventListener('error', () => {
      guideMapLoaded = false;
      gmapImg.style.display = 'none';
      if (gmapMissing) gmapMissing.style.display = 'flex';
      if (btnMapZoom) btnMapZoom.style.display = 'none';
      const dl = document.getElementById('dlGuideMap');
      if (dl) dl.style.display = 'none';
    });
    if (gmapImg.complete && gmapImg.naturalWidth > 0) guideMapLoaded = true;
  }

  /* ── 가이드맵 모달 ── */
  const mapModal = document.getElementById('mapModal');
  const mapModalBg = document.getElementById('mapModalBg');
  const mapModalClose = document.getElementById('mapModalClose');
  const mapModalImg = document.getElementById('mapModalImg');
  const mapModalArea = document.getElementById('mapModalArea');
  let scale = 1, panX = 0, panY = 0;

  function openModal()  { if (!guideMapLoaded) return; mapModal.classList.add('open'); mapModal.setAttribute('aria-hidden','false'); document.body.style.overflow = 'hidden'; resetTransform(); }
  function closeModal() { mapModal.classList.remove('open'); mapModal.setAttribute('aria-hidden','true'); document.body.style.overflow = ''; }
  function resetTransform() { scale = 1; panX = 0; panY = 0; applyTransform(); }
  function applyTransform() { mapModalImg.style.transform = `translate(${panX}px,${panY}px) scale(${scale})`; }

  btnMapZoom?.addEventListener('click', openModal);
  gmapPreview?.addEventListener('click', () => { if (guideMapLoaded) openModal(); });
  mapModalBg?.addEventListener('click', closeModal);
  mapModalClose?.addEventListener('click', closeModal);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && mapModal?.classList.contains('open')) closeModal(); });

  /* 터치 줌 */
  let lastDist = 0, lastTap = 0, isPan = false, psx = 0, psy = 0, ppx = 0, ppy = 0;
  mapModalArea?.addEventListener('touchstart', e => {
    if (e.touches.length === 2) {
      lastDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
    } else if (e.touches.length === 1) {
      const now = Date.now();
      if (now - lastTap < 300) { scale = scale > 1.5 ? 1 : 2.5; panX = 0; panY = 0; applyTransform(); lastTap = 0; return; }
      lastTap = now; isPan = true; psx = e.touches[0].clientX; psy = e.touches[0].clientY; ppx = panX; ppy = panY;
    }
  }, { passive: true });
  mapModalArea?.addEventListener('touchmove', e => {
    if (e.touches.length === 2) {
      const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
      scale = Math.min(Math.max(scale * (d / lastDist), 1), 5); lastDist = d; applyTransform();
    } else if (e.touches.length === 1 && isPan && scale > 1) {
      panX = ppx + (e.touches[0].clientX - psx); panY = ppy + (e.touches[0].clientY - psy); applyTransform();
    }
  }, { passive: true });
  mapModalArea?.addEventListener('touchend', () => { isPan = false; });
  mapModalArea?.addEventListener('wheel', e => {
    e.preventDefault();
    scale = Math.min(Math.max(scale * (e.deltaY < 0 ? 1.12 : 0.89), 1), 5);
    if (scale === 1) { panX = 0; panY = 0; }
    applyTransform();
  }, { passive: false });

  /* 마우스 패닝 */
  let md = false, msx = 0, msy = 0, mpx = 0, mpy = 0;
  mapModalArea?.addEventListener('mousedown', e => { if (scale <= 1) return; md = true; msx = e.clientX; msy = e.clientY; mpx = panX; mpy = panY; mapModalArea.classList.add('dragging'); });
  document.addEventListener('mousemove', e => { if (!md) return; panX = mpx + (e.clientX - msx); panY = mpy + (e.clientY - msy); applyTransform(); });
  document.addEventListener('mouseup', () => { md = false; mapModalArea?.classList.remove('dragging'); });

  /* ── 프로그램 로딩 ── */
  async function loadPrograms() {
    const c = document.getElementById('programsList');
    if (!c) return;
    try {
      const res = await fetch('data/programs.json', { cache: 'no-cache' });
      if (!res.ok) throw new Error();
      const { weekday = [], weekend = [] } = await res.json();
      let html = '';
      if (weekday.length) {
        html += '<div class="prog-day-section"><div class="prog-day-label">📅 주중 (화~금)</div><div class="prog-list">';
        weekday.forEach(p => { html += `<div class="prog-row"><span class="prog-time">${p.time}</span><div class="prog-info"><b>${p.name}</b><span>${p.location}</span></div></div>`; });
        html += '</div></div>';
      }
      if (weekend.length) {
        html += '<div class="prog-day-section"><div class="prog-day-label">🎉 주말 · 공휴일</div><div class="prog-list">';
        weekend.forEach(p => { html += `<div class="prog-row"><span class="prog-time">${p.time}</span><div class="prog-info"><b>${p.name}</b><span>${p.location}</span></div></div>`; });
        html += '</div></div>';
      }
      if (!weekday.length && !weekend.length) html = '<p style="color:var(--text-muted-dark);font-size:13px">등록된 프로그램이 없습니다</p>';
      c.innerHTML = html;
    } catch { c.innerHTML = '<p style="color:var(--text-muted-dark);font-size:13px">프로그램 정보 없음</p>'; }
  }
  loadPrograms();

  /* ── 설정(이메일) 로딩 ── */
  async function loadSettings() {
    try {
      const res = await fetch('data/settings.json', { cache: 'no-cache' });
      if (!res.ok) return;
      const { group_email, biz_email } = await res.json();
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
      const { products = [] } = await res.json();
      if (!products.length) return;
      document.getElementById('productsEmpty')?.remove();
      const grid = document.getElementById('productsGrid');
      products.forEach(p => grid?.appendChild(buildCard(p)));
    } catch {}
  }
  function buildCard(p) {
    const rate = p.discount_rate ?? (p.original_price && p.sale_price && p.original_price > p.sale_price ? Math.round((1 - p.sale_price / p.original_price) * 100) : 0);
    const imgSrc = p.image || p.og_image || null;
    const imgHtml = imgSrc ? `<img src="${imgSrc}" alt="${p.name}" class="product-img" loading="lazy">` : `<div class="product-img-ph">🎟</div>`;
    const origHtml = p.original_price && p.original_price !== p.sale_price ? `<p class="product-original">${p.original_price.toLocaleString()}원</p>` : '';
    const card = document.createElement('div');
    card.className = 'product-card';
    card.innerHTML = `
      <div class="product-img-wrap">${imgHtml}<span class="product-badge">N 예약</span></div>
      <div class="product-body">
        <h4 class="product-name">${p.name}</h4>
        <div class="product-price-row">
          ${rate ? `<span class="product-discount">${rate}%</span>` : ''}
          <span class="product-sale">${Number(p.sale_price).toLocaleString()}원</span>
        </div>
        ${origHtml}
        ${p.valid_until ? `<p class="product-meta">${p.valid_until}까지</p>` : ''}
      </div>
      <a href="${p.booking_url || 'https://map.naver.com/p/entry/place/1008136590?placePath=%2Freservation'}"
         class="product-book-btn" target="_blank" rel="noopener">예약하기</a>`;
    return card;
  }
  loadProducts();

  /* ── 공지 Swiper ── */
  async function loadNotices() {
    const wrapper = document.getElementById('noticesWrapper');
    const placeholder = document.getElementById('noticePlaceholder');
    try {
      const res = await fetch('data/notices.json', { cache: 'no-cache' });
      if (!res.ok) return;
      const { notices = [] } = await res.json();
      if (!notices.length) { initSwiper(false); return; }
      placeholder?.remove();
      notices.forEach(n => {
        const slide = document.createElement('div');
        slide.className = 'swiper-slide';
        if (n.link) {
          slide.innerHTML = `<a href="${n.link}" target="_blank" rel="noopener"><img src="${n.image}" alt="${n.alt||'공지'}" class="notice-img" loading="lazy"></a>`;
        } else {
          slide.innerHTML = `<img src="${n.image}" alt="${n.alt||'공지'}" class="notice-img" loading="lazy">`;
        }
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
      if (note) { note.style.display = 'block'; note.style.color = '#c0392b'; note.textContent = '이메일은 필수입니다.'; }
      return;
    }
    const subject = encodeURIComponent(`[ZZL 제휴 문의] ${company || '(회사명 없음)'} - ${name || '(이름 없음)'}`);
    const body    = encodeURIComponent(`회사명: ${company}\n담당자: ${name}\n연락처: ${phone}\n이메일: ${email}\n\n제안 내용:\n${content}`);
    window.location.href = `mailto:biz@zoozoo.kr?subject=${subject}&body=${body}`;

    if (note) { note.style.display = 'block'; note.style.color = 'var(--forest)'; note.textContent = '이메일 앱이 열립니다. 발송 후 영업일 2~3일 내 답변드립니다.'; }
  });

})();
