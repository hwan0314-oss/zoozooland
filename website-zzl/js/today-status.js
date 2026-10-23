/* ZZL — 오늘 운영 상태 (data/hours.json + data/programs.json, 한국 시간 기준) */
(() => {
  'use strict';

  const DOW = ['일', '월', '화', '수', '목', '금', '토'];
  const DAY_MS = 864e5;
  const toMin = t => { const [h, m] = String(t).split(':').map(Number); return h * 60 + (m || 0); };

  // 기기 시간대와 무관하게 한국 시간(UTC+9)의 날짜·요일·분을 구한다
  function kstDay(ms) {
    const d = new Date(ms + 9 * 3600e3);
    return {
      date: d.toISOString().slice(0, 10),
      dow:  d.getUTCDay(),
      min:  d.getUTCHours() * 60 + d.getUTCMinutes(),
      md:   `${d.getUTCMonth() + 1}/${d.getUTCDate()}`,
    };
  }

  function dayPlan(hours, date, dow) {
    const sp = (hours.special || []).find(s => s.date === date) || {};
    const holiday = (hours.holidays || []).includes(date);
    const closed = sp.closed ?? ((hours.closed_weekdays || []).includes(dow) && !holiday);
    return {
      closed, holiday,
      open:  sp.open  || hours.open,
      close: sp.close || hours.close,
      note:  sp.note  || (closed ? hours.closed_note : ''),
    };
  }

  // 주말·공휴일은 weekend 프로그램, 평일은 weekday 프로그램
  const programGroup = (dow, holiday) => (dow === 0 || dow === 6 || holiday) ? 'weekend' : 'weekday';

  function nextProgram(programs, group, fromMin, untilMin) {
    const slots = (programs[group] || []).flatMap(p =>
      (String(p.time).match(/\d{1,2}:\d{2}/g) || []).map(t => ({ t, min: toMin(t), name: p.name })));
    const next = slots.filter(s => s.min >= fromMin && s.min < untilMin).sort((a, b) => a.min - b.min)[0];
    return next ? `다음 프로그램 ${next.t} ${next.name}` : '';
  }

  function computeStatus(hours, programs, nowMs) {
    const today = kstDay(nowMs);
    const plan  = dayPlan(hours, today.date, today.dow);
    const group = programGroup(today.dow, plan.holiday);

    const nextOpen = () => {
      for (let i = 1; i <= 14; i++) {
        const k = kstDay(nowMs + i * DAY_MS);
        const p = dayPlan(hours, k.date, k.dow);
        if (!p.closed) return `${i === 1 ? '내일' : k.md}(${DOW[k.dow]}) ${p.open} 오픈`;
      }
      return '';
    };

    if (plan.closed) {
      // 정기휴무일이면 공휴일 예외 안내를 덧붙인다 (공휴일 목록이 빠졌을 때를 대비)
      const regular = !(hours.special || []).some(s => s.date === today.date);
      const sub = [nextOpen(), regular && hours.holiday_note].filter(Boolean).join(' · ');
      return { state: 'closed', group: null, text: `오늘 휴무 · ${plan.note || '정기휴무'}`, sub };
    }
    const open = toMin(plan.open), close = toMin(plan.close);
    if (today.min >= close) {
      return { state: 'closed', group: null, text: '오늘 운영 종료', sub: nextOpen() };
    }
    const program = nextProgram(programs, group, Math.max(today.min, open), close);
    const note = plan.note ? ` · ${plan.note}` : '';
    if (today.min < open) {
      return { state: 'soon', group, text: `오늘 ${plan.open} 오픈`, sub: program || `${plan.open}–${plan.close} 운영${note}` };
    }
    const closing = close - today.min <= 60;
    return {
      state: closing ? 'closing' : 'open', group,
      text: `${closing ? '곧 마감' : '지금 운영 중'} · ${plan.close}까지${note}`,
      sub: program,
    };
  }

  function render(s) {
    document.querySelectorAll('[data-today-status]').forEach(box => {
      box.dataset.state = s.state;
      const text = box.querySelector('[data-status-text]');
      const sub  = box.querySelector('[data-status-sub]');
      if (text) text.textContent = s.text;
      if (sub)  { sub.textContent = s.sub || ''; sub.hidden = !s.sub; }
    });
    // 운영 프로그램 카드에서 오늘 해당하는 요일 그룹 표시
    document.querySelectorAll('.prog-day[data-group]').forEach(el =>
      el.classList.toggle('is-today', el.dataset.group === s.group));
  }

  async function fetchJson(url) {
    try {
      const res = await fetch(url, { cache: 'no-cache' });
      return res.ok ? await res.json() : null;
    } catch { return null; }
  }

  async function init() {
    if (!document.querySelector('[data-today-status]')) return;
    const [hours, programs] = await Promise.all([fetchJson('data/hours.json'), fetchJson('data/programs.json')]);
    if (!hours || !hours.open || !hours.close) return; // 정보가 없으면 빌드된 기본 문구 유지
    const update = () => render(computeStatus(hours, programs || {}, Date.now()));
    update();
    setInterval(update, 60e3);
  }

  window.ZZLToday = { computeStatus };
  init();
})();
