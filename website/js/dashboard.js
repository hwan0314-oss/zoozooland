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
      document.getElementById('pagesChart').parentElement.innerHTML += msg;
      document.getElementById('queryTableWrap').innerHTML = msg;
      document.getElementById('deviceChart').parentElement.parentElement.parentElement.innerHTML += msg;
      document.getElementById('uxSignalsWrap').innerHTML = msg;
      return;
    }
    renderUpdatedAt(data.updated_at);
    renderStats(data);
    renderLineChart(data.ga4?.daily || []);
    renderRankedBar('barChart', data.ga4?.sources || [], 'source', 'sessions');
    renderRankedBar('pagesChart', data.ga4?.topPages || [], 'path', 'views');
    renderQueryTable(data.gsc?.top_queries || []);
    renderRankedBar('deviceChart', data.clarity?.devices || [], 'name', 'sessions',
      { W: 300, padL: 85, padR: 30, rowH: 28, gap: 6, truncateLen: 10 });
    renderRankedBar('browserChart', data.clarity?.browsers || [], 'name', 'sessions',
      { W: 300, padL: 85, padR: 30, rowH: 28, gap: 6, truncateLen: 10 });
    renderUxSignals(data.clarity?.uxSignals || {});
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

    const nvr = data.ga4?.newVsReturning || { new: 0, returning: 0 };
    const nvrTotal = nvr.new + nvr.returning;
    const pct = n => nvrTotal ? Math.round((n / nvrTotal) * 100) : 0;

    const tiles = [
      { label: '오늘 방문자 (GA4)', value: today ? today.activeUsers.toLocaleString('ko-KR') : '–' },
      { label: '최근 30일 방문자 합계', value: total30.toLocaleString('ko-KR') },
      { label: '신규 방문자 (최근 30일)', value: nvrTotal ? `${nvr.new.toLocaleString('ko-KR')} (${pct(nvr.new)}%)` : '–' },
      { label: '재방문자 (최근 30일)', value: nvrTotal ? `${nvr.returning.toLocaleString('ko-KR')} (${pct(nvr.returning)}%)` : '–' },
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

  // 카테고리별 순위 막대 차트 (유입 경로, 인기 페이지, 기기, 브라우저에서 공용으로 사용)
  function renderRankedBar(svgId, items, labelKey, valueKey, opts = {}) {
    const { W = 640, padL = 140, padR = 50, rowH = 36, gap = 8, truncateLen = 18 } = opts;
    const svg = document.getElementById(svgId);
    if (!items.length) { svg.parentElement.innerHTML += '<div class="empty-state">데이터 없음</div>'; return; }

    const max = Math.max(...items.map(it => it[valueKey]), 1);
    const plotW = W - padL - padR;
    const initialClip = s => s.length > truncateLen ? s.slice(0, truncateLen - 1) + '…' : s;

    const bars = items.map((it, i) => {
      const y = i * (rowH + gap);
      const w = (it[valueKey] / max) * plotW;
      const label = String(it[labelKey]);
      return `
        <text class="rb-label" x="${padL - 10}" y="${y + rowH / 2 + 4}" font-size="12" fill="var(--n700)" text-anchor="end"><tspan class="rb-label-text">${initialClip(label)}</tspan><title>${label}</title></text>
        <rect x="${padL}" y="${y}" width="${w}" height="${rowH - 4}" rx="4" fill="var(--series-1)"/>
        <text x="${padL + w + 8}" y="${y + rowH / 2 + 4}" font-size="12" fill="var(--n700)">${it[valueKey]}</text>
      `;
    }).join('');

    svg.setAttribute('viewBox', `0 0 ${W} ${items.length * (rowH + gap)}`);
    svg.innerHTML = bars;

    // 문자 수 기준 클리핑은 폰트가 고정폭이 아니라 부정확하므로(예: "MobileSafari"의 i/l vs
    // "ChromeMobile"의 C/M), 렌더링된 실제 폭(getComputedTextLength)을 재서 넘치면 한 글자씩
    // 더 줄인다. 라벨 영역 좌측 끝(x=0)을 넘지 않도록 padL - 10을 예산으로 삼는다.
    const budget = padL - 10;
    svg.querySelectorAll('.rb-label').forEach(el => {
      const tspan = el.querySelector('.rb-label-text');
      let text = tspan.textContent;
      while (el.getComputedTextLength() > budget && text.length > 1) {
        text = text.length > 2 ? text.slice(0, -2) + '…' : '…';
        tspan.textContent = text;
      }
    });
  }

  const UX_LABELS = {
    rageClick: 'Rage Click — 짜증나서 반복 클릭',
    deadClick: 'Dead Click — 눌러도 반응 없음',
    quickback: 'Quickback — 들어오자마자 이탈',
    excessiveScroll: '과도한 스크롤',
    scriptError: '스크립트 오류 발생',
  };

  function renderUxSignals(ux) {
    const wrap = document.getElementById('uxSignalsWrap');
    const keys = Object.keys(UX_LABELS).filter(k => ux && ux[k] !== undefined);
    if (!keys.length) { wrap.innerHTML = '<div class="empty-state">데이터 없음</div>'; return; }
    wrap.innerHTML = `
      <table class="qtable">
        <thead><tr><th>신호</th><th class="num">발생 세션 비율</th></tr></thead>
        <tbody>
          ${keys.map(k => `
            <tr>
              <td>${UX_LABELS[k]}</td>
              <td class="num">${ux[k].toFixed(1)}%</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
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
