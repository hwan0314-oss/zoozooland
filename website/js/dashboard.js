/* ================================================
   쥬쥬랜드 — 마케팅 대시보드 (읽기 전용)
   ================================================ */
(() => {
  'use strict';

  // 참고: 이 PIN은 실제 보안이 아니라 캐주얼한 열람 방지용 UI 게이트입니다.
  // 이 파일 자체가 공개되어 있고, 데이터(../data/analytics.json)도 URL만 알면
  // 누구나 직접 접근 가능합니다 (GitHub Pages는 정적 호스팅이라 파일 단위 접근
  // 제어가 불가능함). 민감정보가 아닌 집계 통계이므로 감수하는 트레이드오프입니다.
  const ADMIN_PIN = 'zzldash2026';

  const pinScreen = document.getElementById('pinScreen');
  const pinInput  = document.getElementById('pinInput');
  const pinBtn    = document.getElementById('pinBtn');
  const pinError  = document.getElementById('pinError');
  const dash      = document.getElementById('dash');
  const tooltip   = document.getElementById('tooltip');

  function enter() {
    if (pinInput.value.trim() !== ADMIN_PIN) {
      pinError.classList.add('show');
      return;
    }
    pinScreen.classList.add('hidden');
    dash.classList.add('show');
    loadData();
  }
  pinBtn.addEventListener('click', enter);
  pinInput.addEventListener('keydown', e => { if (e.key === 'Enter') enter(); });

  async function loadData() {
    let data;
    try {
      const res = await fetch('../data/analytics.json?t=' + Date.now(), { cache: 'no-cache' });
      if (!res.ok) throw new Error('not found');
      data = await res.json();
    } catch {
      const msg = '<div class="empty-state">아직 수집된 데이터가 없습니다. ETL 워크플로우가 처음 실행되면 표시됩니다.</div>';
      document.getElementById('statRow').innerHTML = msg;
      document.getElementById('lineChart').parentElement.innerHTML += msg;
      document.getElementById('barChart').parentElement.innerHTML += msg;
      document.getElementById('queryTableWrap').innerHTML = msg;
      return;
    }
    renderUpdatedAt(data.updated_at);
    renderStats(data);
    renderLineChart(data.ga4?.daily || []);
    renderBarChart(data.ga4?.sources || []);
    renderQueryTable(data.gsc?.top_queries || []);
  }

  function renderUpdatedAt(iso) {
    if (!iso) return;
    const d = new Date(iso);
    document.getElementById('updatedAt').textContent =
      '마지막 갱신: ' + d.toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
  }

  function renderStats(data) {
    const daily = data.ga4?.daily || [];
    const today = daily[daily.length - 1];
    const total30 = daily.reduce((sum, d) => sum + d.activeUsers, 0);
    const clarityLatest = (data.clarity?.history || []).slice(-1)[0];

    const tiles = [
      { label: '오늘 방문자 (GA4)', value: today ? today.activeUsers.toLocaleString('ko-KR') : '–' },
      { label: '최근 30일 방문자 합계', value: total30.toLocaleString('ko-KR') },
      { label: '평균 스크롤 깊이 (Clarity)', value: clarityLatest ? `${clarityLatest.scrollDepth.toFixed(0)}%` : '–' },
      { label: '평균 참여 시간 (Clarity)', value: clarityLatest ? `${clarityLatest.engagementTime.toFixed(0)}초` : '–' },
    ];

    document.getElementById('statRow').innerHTML = tiles.map(t => `
      <div class="stat-tile">
        <div class="stat-label">${t.label}</div>
        <div class="stat-value">${t.value}</div>
      </div>
    `).join('');
  }

  function renderLineChart(daily) {
    const svg = document.getElementById('lineChart');
    if (!daily.length) { svg.parentElement.innerHTML += '<div class="empty-state">데이터 없음</div>'; return; }

    const W = 640, H = 220, padL = 36, padB = 24, padT = 12, padR = 12;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const max = Math.max(...daily.map(d => d.activeUsers), 1);
    const stepX = plotW / Math.max(daily.length - 1, 1);

    const points = daily.map((d, i) => {
      const x = padL + i * stepX;
      const y = padT + plotH - (d.activeUsers / max) * plotH;
      return { x, y, d };
    });

    const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    const areaPath = `${linePath} L${points[points.length - 1].x.toFixed(1)},${padT + plotH} L${points[0].x.toFixed(1)},${padT + plotH} Z`;

    const gridLines = [0, 0.5, 1].map(f => {
      const y = padT + plotH * (1 - f);
      return `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" stroke="var(--grid)" stroke-width="1"/>`;
    }).join('');

    const lastPoint = points[points.length - 1];

    svg.innerHTML = `
      ${gridLines}
      <path d="${areaPath}" fill="var(--series-1)" opacity="0.1"/>
      <path d="${linePath}" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
      <circle cx="${lastPoint.x}" cy="${lastPoint.y}" r="4" fill="var(--series-1)" stroke="var(--surface-1)" stroke-width="2"/>
      <text x="${lastPoint.x - 4}" y="${lastPoint.y - 10}" font-size="11" fill="var(--n700)" text-anchor="end">${lastPoint.d.activeUsers}</text>
      ${points.map(p => `<circle cx="${p.x}" cy="${p.y}" r="8" fill="transparent" data-date="${p.d.date}" data-value="${p.d.activeUsers}" class="hover-dot"/>`).join('')}
    `;

    svg.querySelectorAll('.hover-dot').forEach(dot => {
      dot.addEventListener('mousemove', e => showTooltip(e, `${dot.dataset.date}: 방문자 ${dot.dataset.value}명`));
      dot.addEventListener('mouseleave', hideTooltip);
    });
  }

  function renderBarChart(sources) {
    const svg = document.getElementById('barChart');
    if (!sources.length) { svg.parentElement.innerHTML += '<div class="empty-state">데이터 없음</div>'; return; }

    const W = 640, H = 200, padL = 140, padR = 50, rowH = 36, gap = 8;
    const max = Math.max(...sources.map(s => s.sessions), 1);
    const plotW = W - padL - padR;

    const truncate = s => s.length > 18 ? s.slice(0, 17) + '…' : s;

    const bars = sources.map((s, i) => {
      const y = i * (rowH + gap);
      const w = (s.sessions / max) * plotW;
      return `
        <text x="${padL - 10}" y="${y + rowH / 2 + 4}" font-size="12" fill="var(--n700)" text-anchor="end">${truncate(s.source)}<title>${s.source}</title></text>
        <rect x="${padL}" y="${y}" width="${w}" height="${rowH - 4}" rx="4" fill="var(--series-1)"/>
        <text x="${padL + w + 8}" y="${y + rowH / 2 + 4}" font-size="12" fill="var(--n700)">${s.sessions}</text>
      `;
    }).join('');

    svg.setAttribute('viewBox', `0 0 ${W} ${sources.length * (rowH + gap)}`);
    svg.innerHTML = bars;
  }

  function renderQueryTable(queries) {
    const wrap = document.getElementById('queryTableWrap');
    if (!queries.length) { wrap.innerHTML = '<div class="empty-state">데이터 없음</div>'; return; }
    wrap.innerHTML = `
      <table class="qtable">
        <thead><tr><th>검색어</th><th class="num">클릭</th><th class="num">노출</th><th class="num">평균 순위</th></tr></thead>
        <tbody>
          ${queries.map(q => `
            <tr>
              <td>${q.query}</td>
              <td class="num">${q.clicks}</td>
              <td class="num">${q.impressions}</td>
              <td class="num">${q.position}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  function showTooltip(e, text) {
    tooltip.textContent = text;
    tooltip.style.left = e.pageX + 12 + 'px';
    tooltip.style.top = e.pageY - 28 + 'px';
    tooltip.style.opacity = '1';
  }
  function hideTooltip() { tooltip.style.opacity = '0'; }
})();
