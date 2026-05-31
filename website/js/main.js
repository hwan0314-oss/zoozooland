/* ================================================
   쥬쥬랜드 — Main JS
   ================================================ */

(() => {
  'use strict';

  /* ── Navbar scroll state ── */
  const navbar = document.getElementById('navbar');

  function updateNavbar() {
    if (window.scrollY > 40) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  }
  window.addEventListener('scroll', updateNavbar, { passive: true });
  updateNavbar();

  /* ── Mobile nav toggle ── */
  const navToggle = document.getElementById('navToggle');
  const navMobile = document.getElementById('navMobile');

  navToggle?.addEventListener('click', () => {
    const open = navMobile.classList.toggle('open');
    navToggle.classList.toggle('open', open);
    navToggle.setAttribute('aria-expanded', String(open));
  });

  // Close mobile menu when a link is clicked
  navMobile?.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => {
      navMobile.classList.remove('open');
      navToggle.classList.remove('open');
      navToggle.setAttribute('aria-expanded', 'false');
    });
  });

  /* ── Active nav link on scroll ── */
  const sections = document.querySelectorAll('[id]');
  const navItems = document.querySelectorAll('.nav-item');

  const sectionObserver = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        navItems.forEach(a => {
          a.classList.toggle('active', a.getAttribute('href') === `#${e.target.id}`);
        });
      }
    });
  }, { rootMargin: `-${60}px 0px -60% 0px` });

  sections.forEach(s => sectionObserver.observe(s));

  /* ── Scroll reveal ── */
  const revealObserver = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        revealObserver.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });

  document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

  /* ── Floating guide map button ── */
  const floatBtn = document.getElementById('floatBtn');
  const guideMapSection = document.getElementById('guidemap');

  const floatObserver = new IntersectionObserver(entries => {
    entries.forEach(e => {
      // Show button when guide map section is NOT visible
      floatBtn?.classList.toggle('show', !e.isIntersecting);
    });
  }, { threshold: 0.1 });

  if (guideMapSection) floatObserver.observe(guideMapSection);

  /* ── Footer year ── */
  const footerYear = document.getElementById('footerYear');
  if (footerYear) footerYear.textContent = new Date().getFullYear();

  /* ── Guide map image load state ── */
  const gmapImg     = document.getElementById('gmapImg');
  const gmapMissing = document.getElementById('gmapMissing');
  const btnMapZoom  = document.getElementById('btnMapZoom');
  const gmapPreview = document.getElementById('gmapPreview');

  let guideMapLoaded = false;

  function setGuideMapReady(ok) {
    guideMapLoaded = ok;
    if (ok) {
      if (gmapMissing) gmapMissing.style.display = 'none';
    } else {
      gmapImg.style.display = 'none';
      if (gmapMissing) gmapMissing.style.display = 'flex';
      if (btnMapZoom)  btnMapZoom.style.display  = 'none';
      const dlBtn = document.getElementById('dlGuideMap');
      if (dlBtn) dlBtn.style.display = 'none';
    }
  }

  if (gmapImg) {
    gmapImg.addEventListener('load',  () => setGuideMapReady(true));
    gmapImg.addEventListener('error', () => setGuideMapReady(false));
    // 이미 캐시돼서 load 이벤트가 이미 발생했을 경우 대비
    if (gmapImg.complete && gmapImg.naturalWidth > 0) setGuideMapReady(true);
  }

  /* ── Guide map modal ── */
  const mapModal      = document.getElementById('mapModal');
  const mapModalBg    = document.getElementById('mapModalBg');
  const mapModalClose = document.getElementById('mapModalClose');
  const mapModalImg   = document.getElementById('mapModalImg');
  const mapModalArea  = document.getElementById('mapModalArea');

  let modalScale = 1;
  let panX = 0;
  let panY = 0;

  function openModal() {
    if (!guideMapLoaded) return;   // 이미지 없으면 모달 열지 않음
    mapModal.classList.add('open');
    mapModal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    resetModalTransform();
  }

  function closeModal() {
    mapModal.classList.remove('open');
    mapModal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  function resetModalTransform() {
    modalScale = 1;
    panX = 0;
    panY = 0;
    applyModalTransform();
  }

  function applyModalTransform() {
    mapModalImg.style.transform = `translate(${panX}px, ${panY}px) scale(${modalScale})`;
  }

  btnMapZoom?.addEventListener('click', openModal);
  gmapPreview?.addEventListener('click', () => {
    if (guideMapLoaded) openModal();
  });
  mapModalBg?.addEventListener('click', closeModal);
  mapModalClose?.addEventListener('click', closeModal);

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && mapModal?.classList.contains('open')) closeModal();
  });

  /* ── Modal: Pinch zoom (touch) ── */
  let lastTouchDist = 0;
  let lastTapTime   = 0;
  let isPanning     = false;
  let panStartX     = 0;
  let panStartY     = 0;
  let panStartPX    = 0;
  let panStartPY    = 0;

  mapModalArea?.addEventListener('touchstart', e => {
    if (e.touches.length === 2) {
      lastTouchDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
    } else if (e.touches.length === 1) {
      // Double-tap detection
      const now = Date.now();
      if (now - lastTapTime < 300) {
        modalScale = modalScale > 1.5 ? 1 : 2.5;
        panX = 0; panY = 0;
        applyModalTransform();
        lastTapTime = 0;
        return;
      }
      lastTapTime = now;

      // Pan start
      isPanning = true;
      panStartX = e.touches[0].clientX;
      panStartY = e.touches[0].clientY;
      panStartPX = panX;
      panStartPY = panY;
    }
  }, { passive: true });

  mapModalArea?.addEventListener('touchmove', e => {
    if (e.touches.length === 2) {
      const dist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      const delta = dist / lastTouchDist;
      modalScale = Math.min(Math.max(modalScale * delta, 1), 5);
      lastTouchDist = dist;
      applyModalTransform();
    } else if (e.touches.length === 1 && isPanning && modalScale > 1) {
      panX = panStartPX + (e.touches[0].clientX - panStartX);
      panY = panStartPY + (e.touches[0].clientY - panStartY);
      applyModalTransform();
    }
  }, { passive: true });

  mapModalArea?.addEventListener('touchend', () => { isPanning = false; });

  /* ── Modal: Mouse wheel zoom ── */
  mapModalArea?.addEventListener('wheel', e => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.12 : 0.89;
    modalScale = Math.min(Math.max(modalScale * factor, 1), 5);
    if (modalScale === 1) { panX = 0; panY = 0; }
    applyModalTransform();
  }, { passive: false });

  /* ── Modal: Mouse pan ── */
  let mouseDown = false;
  let mousePanStartX = 0;
  let mousePanStartY = 0;
  let mousePanStartPX = 0;
  let mousePanStartPY = 0;

  mapModalArea?.addEventListener('mousedown', e => {
    if (modalScale <= 1) return;
    mouseDown = true;
    mousePanStartX = e.clientX;
    mousePanStartY = e.clientY;
    mousePanStartPX = panX;
    mousePanStartPY = panY;
    mapModalArea.classList.add('dragging');
  });

  document.addEventListener('mousemove', e => {
    if (!mouseDown) return;
    panX = mousePanStartPX + (e.clientX - mousePanStartX);
    panY = mousePanStartPY + (e.clientY - mousePanStartY);
    applyModalTransform();
  });

  document.addEventListener('mouseup', () => {
    mouseDown = false;
    mapModalArea?.classList.remove('dragging');
  });

  /* ── 예매 상품 카드 렌더링 ── */
  async function loadProducts() {
    try {
      const res = await fetch('data/products.json', { cache: 'no-cache' });
      if (!res.ok) return;
      const data = await res.json();
      const products = data.products || [];
      if (products.length === 0) return;

      const empty = document.getElementById('productsEmpty');
      const grid  = document.getElementById('productsGrid');
      empty?.remove();

      products.forEach(p => grid?.appendChild(buildProductCard(p)));
    } catch { /* keep empty state */ }
  }

  function buildProductCard(p) {
    const rate = p.discount_rate
      ?? (p.original_price && p.sale_price && p.original_price > p.sale_price
          ? Math.round((1 - p.sale_price / p.original_price) * 100)
          : 0);

    const card = document.createElement('div');
    card.className = 'product-card';

    const imgSrc = p.image || p.og_image || null;
    const imgHtml = imgSrc
      ? `<img src="${imgSrc}" alt="${p.name}" class="product-img" loading="lazy">`
      : `<div class="product-img-ph">🎟</div>`;

    const origHtml = p.original_price && p.original_price !== p.sale_price
      ? `<p class="product-original">${p.original_price.toLocaleString()}원</p>` : '';

    const metaLines = [
      p.valid_until ? `${p.valid_until}까지 사용가능` : '',
    ].filter(Boolean).join('<br>');

    card.innerHTML = `
      <div class="product-img-wrap">
        ${imgHtml}
        <span class="product-badge">N 예약</span>
      </div>
      <div class="product-body">
        <h4 class="product-name">${p.name}</h4>
        <div class="product-price-row">
          ${rate ? `<span class="product-discount">${rate}%</span>` : ''}
          <span class="product-sale">${Number(p.sale_price).toLocaleString()}원</span>
        </div>
        ${origHtml}
        ${metaLines ? `<p class="product-meta">${metaLines}</p>` : ''}
      </div>
      <a href="${p.booking_url || 'https://map.naver.com/p/entry/place/1008136590?placePath=%2Freservation'}"
         class="btn btn--naver product-book-btn" target="_blank" rel="noopener">예약하기</a>
    `;
    return card;
  }

  loadProducts();

  /* ── Notices Swiper (loads from data/notices.json) ── */
  const noticesWrapper   = document.getElementById('noticesWrapper');
  const noticePlaceholder = document.getElementById('noticePlaceholder');

  async function loadNotices() {
    try {
      const res = await fetch('data/notices.json', { cache: 'no-cache' });
      if (!res.ok) return;
      const data = await res.json();
      const notices = data.notices || [];
      if (notices.length === 0) return; // keep placeholder

      // Remove placeholder
      noticePlaceholder?.remove();

      // Build slides
      notices.forEach(n => {
        const slide = document.createElement('div');
        slide.className = 'swiper-slide';

        if (n.link) {
          const a = document.createElement('a');
          a.href = n.link;
          a.target = '_blank';
          a.rel = 'noopener noreferrer';
          const img = document.createElement('img');
          img.src = n.image;
          img.alt = n.alt || '공지/이벤트';
          img.className = 'notice-img';
          img.loading = 'lazy';
          a.appendChild(img);
          slide.appendChild(a);
        } else {
          const img = document.createElement('img');
          img.src = n.image;
          img.alt = n.alt || '공지/이벤트';
          img.className = 'notice-img';
          img.loading = 'lazy';
          slide.appendChild(img);
        }

        noticesWrapper?.appendChild(slide);
      });

      // Init Swiper after slides are added
      initSwiper();
    } catch {
      // Fail silently — placeholder remains
    }
  }

  function initSwiper() {
    if (typeof Swiper === 'undefined') return;
    new Swiper('.notices-swiper', {
      loop: noticesWrapper?.querySelectorAll('.swiper-slide').length > 1,
      autoplay: {
        delay: 4500,
        disableOnInteraction: false,
        pauseOnMouseEnter: true,
      },
      pagination: {
        el: '.swiper-pagination',
        clickable: true,
      },
      navigation: {
        nextEl: '.swiper-button-next',
        prevEl: '.swiper-button-prev',
      },
      grabCursor: true,
      keyboard: { enabled: true },
    });
  }

  // Init Swiper with placeholder (loop off)
  function initSwiperEmpty() {
    if (typeof Swiper === 'undefined') return;
    new Swiper('.notices-swiper', {
      loop: false,
      pagination: { el: '.swiper-pagination', clickable: true },
      navigation: {
        nextEl: '.swiper-button-next',
        prevEl: '.swiper-button-prev',
      },
    });
  }

  loadNotices().then(() => {
    // If no notices were added (placeholder still present), init empty swiper
    if (document.getElementById('noticePlaceholder')) {
      initSwiperEmpty();
    }
  });

})();
