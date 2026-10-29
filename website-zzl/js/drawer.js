/* ZZL — 잡동사니 서랍 (drawer.html): 클릭 추적 · 준비물 체크 · 가족에게 보내기 · 「필요해요」 · 단체 도시락 메뉴판 */
(() => {
  'use strict';

  /* ── 클릭 추적 (GA4 + Clarity) — main.js 와 같은 규칙: data-track="이벤트명" data-cta="위치" */
  document.addEventListener('click', e => {
    const el = e.target.closest('[data-track]');
    if (!el) return;
    const name = el.dataset.track;
    const cta = el.dataset.cta || '';
    try { window.gtag?.('event', name, { cta_location: cta, link_url: el.href || '' }); } catch {}
    try { window.clarity?.('event', cta ? `${name}:${cta}` : name); } catch {}
  });

  /* ── 준비물 체크(기기에만 저장) · 가족에게 보내기 · 「필요해요」 ── */
  const store = {
    get(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  };
  const checks = store.get('zzl.checklist') || {};
  document.querySelectorAll('[data-check]').forEach(box => {
    box.checked = !!checks[box.dataset.check];
    box.addEventListener('change', () => { checks[box.dataset.check] = box.checked; store.set('zzl.checklist', checks); });
  });
  document.querySelector('[data-share-checklist]')?.addEventListener('click', async e => {
    const btn = e.currentTarget;
    const card = btn.closest('.tb-check');
    const bring = [...card.querySelectorAll('label')].map(l => `☐ ${l.querySelector('b').textContent} — ${l.querySelector('span').textContent}`);
    const leave = [...card.querySelectorAll('.tb-no li')].map(li => `✕ ${li.querySelector('b').textContent}`);
    const text = `쥬쥬랜드 나들이 준비물\n${bring.join('\n')}\n\n두고 올 것\n${leave.join('\n')}`;
    const url = 'https://zoozoo.kr/drawer.html';
    try {
      if (navigator.share) { await navigator.share({ title: '쥬쥬랜드 나들이 준비물', text, url }); return; }
      await navigator.clipboard.writeText(`${text}\n\n${url}`);
      btn.textContent = '복사했어요! 카톡에 붙여 넣으세요';
    } catch {}
  });
  const wants = store.get('zzl.wants') || {};
  document.querySelectorAll('[data-want]').forEach(btn => {
    const mark = () => { btn.setAttribute('aria-pressed', 'true'); btn.textContent = '고마워요! 많이 눌리면 먼저 만들게요'; };
    btn.setAttribute('aria-pressed', 'false');
    if (wants[btn.dataset.want]) { mark(); btn.removeAttribute('data-track'); }
    btn.addEventListener('click', () => {
      if (btn.getAttribute('aria-pressed') === 'true') return;
      wants[btn.dataset.want] = true; store.set('zzl.wants', wants);
      // 클릭 추적(toolbox_want)이 먼저 보낸 뒤 바꾼다. 한 기기에서 한 번만 센다
      setTimeout(() => { mark(); btn.removeAttribute('data-track'); }, 0);
    });
  });

  /* ── 홈에서 준비물 체크리스트로 바로 들어오면 펼쳐 둔다 */
  if (location.hash === '#tbChecklist') document.getElementById('tbChecklist')?.setAttribute('open', '');

  /* ── 단체 도시락 메뉴판: 열 때 이미지를 불러온다 */
  const dialog = document.getElementById('lunchboxDialog');
  document.querySelectorAll('[data-open-lunchbox]').forEach(b => b.addEventListener('click', () => {
    const img = dialog.querySelector('img[data-src]');
    if (img && !img.src) img.src = img.dataset.src;
    dialog.showModal();
  }));
  dialog?.querySelector('[data-close-dialog]')?.addEventListener('click', () => dialog.close());
  dialog?.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
})();
