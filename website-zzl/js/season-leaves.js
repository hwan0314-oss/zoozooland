/* ── 시즌 효과: 가을 낙엽 ───────────────────────────────────────────────
   data/settings.json 의 "season_effect" 가 "autumn_leaves" 일 때만 켜진다.
   시즌이 끝나면 그 값을 "" 로 바꿔 커밋하면 꺼진다 (코드 수정 불필요).

   - 단풍잎·은행잎·참나무잎을 미리 그려 둔 스프라이트로 날린다 (프레임마다 도형을 다시 그리지 않음)
   - 본문 위에 떠 있지만 클릭은 그대로 통과한다 (pointer-events: none)
   - 마우스를 가까이 대면 잎이 바람에 밀리듯 비켜 간다
   - 움직임 줄이기 설정이면 켜지 않는다. 방문자는 '낙엽 끄기' 버튼으로 끌 수 있고, 그 선택은 기억한다
   - 탭이 가려지면 멈춘다 */
(function () {
  'use strict';

  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const STORE_KEY = 'zzl.leaves.off';
  const readOff = () => { try { return localStorage.getItem(STORE_KEY) === '1'; } catch (e) { return false; } };
  const writeOff = (v) => { try { v ? localStorage.setItem(STORE_KEY, '1') : localStorage.removeItem(STORE_KEY); } catch (e) {} };

  fetch('data/settings.json', { cache: 'no-cache' })
    .then((r) => (r.ok ? r.json() : {}))
    .then((s) => { if (s && s.season_effect === 'autumn_leaves') start(); })
    .catch(() => {});

  function start() {
    /* ── 잎 모양 (단위 좌표: 중심 0,0 / 크기 약 1) ── */
    const SHAPES = {
      maple(ctx) {
        ctx.beginPath();
        ctx.moveTo(0, 0.5);
        ctx.lineTo(0.08, 0.28); ctx.lineTo(0.42, 0.36); ctx.lineTo(0.32, 0.22);
        ctx.lineTo(0.5, -0.02); ctx.lineTo(0.3, -0.04); ctx.lineTo(0.38, -0.3);
        ctx.lineTo(0.16, -0.18); ctx.lineTo(0.12, -0.38); ctx.lineTo(0, -0.5);
        ctx.lineTo(-0.12, -0.38); ctx.lineTo(-0.16, -0.18); ctx.lineTo(-0.38, -0.3);
        ctx.lineTo(-0.3, -0.04); ctx.lineTo(-0.5, -0.02); ctx.lineTo(-0.32, 0.22);
        ctx.lineTo(-0.42, 0.36); ctx.lineTo(-0.08, 0.28);
        ctx.closePath();
      },
      ginkgo(ctx) {
        ctx.beginPath();
        ctx.moveTo(0, 0.18);
        ctx.bezierCurveTo(-0.2, 0.05, -0.5, -0.1, -0.46, -0.32);
        ctx.quadraticCurveTo(-0.24, -0.5, -0.04, -0.4);
        ctx.lineTo(0, -0.3);
        ctx.lineTo(0.04, -0.4);
        ctx.quadraticCurveTo(0.24, -0.5, 0.46, -0.32);
        ctx.bezierCurveTo(0.5, -0.1, 0.2, 0.05, 0, 0.18);
        ctx.closePath();
      },
      oak(ctx) {
        ctx.beginPath();
        ctx.moveTo(0, 0.5);
        const pts = [[0.14, 0.32], [0.24, 0.22], [0.16, 0.1], [0.28, -0.02], [0.18, -0.14], [0.26, -0.28], [0.12, -0.36], [0, -0.5]];
        pts.forEach(([x, y]) => ctx.quadraticCurveTo(x + 0.08, y + 0.06, x, y));
        for (let i = pts.length - 2; i >= 0; i--) {
          const [x, y] = pts[i];
          ctx.quadraticCurveTo(-x - 0.08, y - 0.06, -x, y);
        }
        ctx.quadraticCurveTo(-0.08, 0.44, 0, 0.5);
        ctx.closePath();
      },
    };
    /* 모양별 색 (단풍은 빨강·주황, 은행은 노랑, 참나무는 갈색) */
    const PALETTE = [
      ['maple', '#D9481E'], ['maple', '#E8692C'], ['maple', '#C2361F'], ['maple', '#F08A24'],
      ['ginkgo', '#F2C230'], ['ginkgo', '#E8B21E'], ['ginkgo', '#F5D35A'],
      ['oak', '#B5651D'], ['oak', '#C98A3A'],
    ];

    const SPRITE = 96;
    function shade(hex, k) {
      const n = parseInt(hex.slice(1), 16);
      const c = (v) => Math.max(0, Math.min(255, Math.round(v * k)));
      return `rgb(${c(n >> 16)},${c((n >> 8) & 255)},${c(n & 255)})`;
    }
    const sprites = PALETTE.map(([shape, color]) => {
      const cv = document.createElement('canvas');
      cv.width = cv.height = SPRITE;
      const g = cv.getContext('2d');
      g.translate(SPRITE / 2, SPRITE / 2);
      g.scale(SPRITE * 0.9, SPRITE * 0.9);
      SHAPES[shape](g);
      const grad = g.createLinearGradient(-0.4, -0.5, 0.4, 0.5);
      grad.addColorStop(0, shade(color, 1.12));
      grad.addColorStop(1, shade(color, 0.82));
      g.fillStyle = grad;
      g.fill();
      /* 잎맥 */
      g.strokeStyle = shade(color, 0.62);
      g.lineWidth = 0.022;
      g.beginPath();
      if (shape === 'ginkgo') {
        for (let a = -0.9; a <= 0.9; a += 0.3) { g.moveTo(0, 0.16); g.lineTo(Math.sin(a) * 0.4, -0.3 + Math.abs(a) * 0.05); }
      } else {
        g.moveTo(0, 0.5); g.lineTo(0, -0.42);
        if (shape === 'maple') { g.moveTo(0, 0.2); g.lineTo(0.36, -0.02); g.moveTo(0, 0.2); g.lineTo(-0.36, -0.02); g.moveTo(0, 0.28); g.lineTo(0.3, 0.3); g.moveTo(0, 0.28); g.lineTo(-0.3, 0.3); }
      }
      g.stroke();
      /* 잎자루 */
      g.lineWidth = 0.03;
      g.beginPath();
      if (shape === 'ginkgo') { g.moveTo(0, 0.18); g.lineTo(0.02, 0.48); }
      else { g.moveTo(0, 0.5); g.lineTo(0.02, 0.62); }
      g.stroke();
      return cv;
    });

    /* ── 캔버스 ── */
    const canvas = document.createElement('canvas');
    canvas.className = 'season-leaves';
    canvas.setAttribute('aria-hidden', 'true');
    document.body.appendChild(canvas);
    const ctx = canvas.getContext('2d');

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'season-leaves-toggle';
    btn.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l1.6 3.8 3.9-1.2-1.1 3.9 3.8 1.6-3.3 2.4 2.2 3.4-4 .3L13.5 20H12v2h-1v-2H9.5l-.9-3.8-4 .2 2.2-3.4-3.3-2.4 3.8-1.6-1.1-3.9 3.9 1.2z" fill="currentColor"/></svg><span class="sr-only"></span>';
    const btnLabel = btn.querySelector('.sr-only');
    document.body.appendChild(btn);

    let W = 0, H = 0, DPR = 1, leaves = [], running = false, raf = 0, last = 0;
    const pointer = { x: -9999, y: -9999, vx: 0, vy: 0 };
    let scrollKick = 0, lastScroll = window.scrollY;

    const rand = (a, b) => a + Math.random() * (b - a);
    function makeLeaf(anywhere) {
      const small = W < 768;
      return {
        x: rand(-40, W + 40),
        y: anywhere ? rand(-H * 0.1, H) : rand(-120, -30),
        size: small ? rand(18, 32) : rand(22, 42),
        vy: rand(26, 58),            /* px/s */
        vx: rand(-8, 8),
        sway: rand(18, 46),          /* 좌우 흔들림 폭 */
        swaySpeed: rand(0.6, 1.4),
        phase: rand(0, Math.PI * 2),
        rot: rand(0, Math.PI * 2),
        rotSpeed: rand(-1.4, 1.4),
        flipSpeed: rand(1.2, 3.2),   /* 뒤집히며 떨어지는 속도 */
        sprite: sprites[(Math.random() * sprites.length) | 0],
        alpha: rand(0.78, 1),
        push: 0, pushX: 0, pushY: 0,
      };
    }
    function targetCount() {
      /* 화면 넓이에 비례해 흐드러지게, 다만 너무 빽빽하지 않게 */
      return Math.round(Math.min(95, Math.max(30, (W * H) / 15000)));
    }
    function resize() {
      DPR = Math.min(window.devicePixelRatio || 1, 1.5);
      W = window.innerWidth; H = window.innerHeight;
      canvas.width = Math.round(W * DPR); canvas.height = Math.round(H * DPR);
      canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
      const n = targetCount();
      while (leaves.length < n) leaves.push(makeLeaf(true));
      if (leaves.length > n) leaves.length = n;
    }

    /* 바람: 잔잔한 기본 바람 + 가끔 부는 돌풍 */
    let gust = 0, gustTarget = 0, nextGust = performance.now() + rand(4000, 9000);
    function wind(t, now) {
      if (now > nextGust) {
        gustTarget = rand(40, 110) * (Math.random() < 0.7 ? 1 : -1);
        nextGust = now + rand(7000, 14000);
        setTimeout(() => { gustTarget = 0; }, rand(1800, 3200));
      }
      gust += (gustTarget - gust) * 0.02;
      return Math.sin(t * 0.13) * 14 + gust;
    }

    function frame(now) {
      raf = requestAnimationFrame(frame);
      const dt = Math.min(0.05, (now - last) / 1000 || 0.016);
      last = now;
      const t = now / 1000;
      const w = wind(t, now);
      scrollKick *= 0.9;

      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
      ctx.clearRect(0, 0, W, H);

      for (let i = 0; i < leaves.length; i++) {
        const L = leaves[i];
        /* 마우스 근처 잎은 밀려난다 */
        const dx = L.x - pointer.x, dy = L.y - pointer.y, d2 = dx * dx + dy * dy;
        if (d2 < 14400) {
          const d = Math.sqrt(d2) || 1, f = (1 - d / 120) * 260;
          L.pushX += (dx / d) * f * dt + pointer.vx * 0.02;
          L.pushY += (dy / d) * f * dt + pointer.vy * 0.02;
        }
        L.pushX *= 0.94; L.pushY *= 0.94;

        const swayX = Math.sin(t * L.swaySpeed + L.phase) * L.sway;
        L.x += (L.vx + w * (0.6 + L.size / 60) + L.pushX) * dt + Math.cos(t * L.swaySpeed + L.phase) * L.sway * L.swaySpeed * dt;
        L.y += (L.vy + Math.abs(Math.sin(t * L.swaySpeed + L.phase)) * 10 + L.pushY - scrollKick) * dt;
        L.rot += L.rotSpeed * dt;

        if (L.y > H + 50 || L.x < -80 || L.x > W + 80) {
          Object.assign(L, makeLeaf(false));
          if (w > 30) L.x = rand(-80, W * 0.6); else if (w < -30) L.x = rand(W * 0.4, W + 80);
        }

        const flip = Math.cos(t * L.flipSpeed + L.phase);
        ctx.globalAlpha = L.alpha * (0.75 + 0.25 * Math.abs(flip));
        ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
        ctx.translate(L.x, L.y);
        ctx.rotate(L.rot + swayX * 0.004);
        ctx.scale(Math.max(0.3, Math.abs(flip)) * (flip < 0 ? -1 : 1), 1);
        ctx.drawImage(L.sprite, -L.size / 2, -L.size / 2, L.size, L.size);
      }
      ctx.globalAlpha = 1;
    }

    function play() {
      if (running) return;
      running = true; last = performance.now();
      canvas.hidden = false;
      raf = requestAnimationFrame(frame);
    }
    function stop(clear) {
      running = false;
      cancelAnimationFrame(raf);
      if (clear) { ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, canvas.width, canvas.height); canvas.hidden = true; }
    }
    function setOff(off) {
      const label = off ? '낙엽 효과 켜기' : '낙엽 효과 끄기';
      btnLabel.textContent = label;
      btn.title = label;
      btn.classList.toggle('is-off', off);
      off ? stop(true) : play();
    }

    window.addEventListener('resize', resize);
    window.addEventListener('pointermove', (e) => {
      if (e.pointerType !== 'mouse') return;
      pointer.vx = e.clientX - pointer.x; pointer.vy = e.clientY - pointer.y;
      pointer.x = e.clientX; pointer.y = e.clientY;
    }, { passive: true });
    document.addEventListener('mouseleave', () => { pointer.x = pointer.y = -9999; });
    window.addEventListener('scroll', () => {
      const y = window.scrollY;
      scrollKick = Math.max(-160, Math.min(160, scrollKick + (y - lastScroll) * 2));
      lastScroll = y;
    }, { passive: true });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) stop(false);
      else if (!readOff()) play();
    });
    btn.addEventListener('click', () => {
      const off = !readOff();
      writeOff(off);
      setOff(off);
    });

    resize();
    setOff(readOff());
  }
})();
