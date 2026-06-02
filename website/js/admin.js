/* ================================================
   쥬쥬랜드 — Admin JS (GitHub API 기반 CMS)
   ================================================ */

(() => {
  'use strict';

  const OWNER  = 'hwan0314-oss';
  const REPO   = 'zoozooland';
  const BRANCH = 'main';

  const API = `https://api.github.com/repos/${OWNER}/${REPO}/contents`;

  /* ── Storage ── */
  const storage = {
    getToken: () => localStorage.getItem('zz_token'),
    setToken: t  => localStorage.setItem('zz_token', t),
    clear:    ()  => localStorage.removeItem('zz_token'),
  };

  /* ── DOM refs ── */
  const loginScreen  = document.getElementById('loginScreen');
  const adminScreen  = document.getElementById('adminScreen');
  const tokenInput   = document.getElementById('tokenInput');
  const loginBtn     = document.getElementById('loginBtn');
  const loginError   = document.getElementById('loginError');
  const logoutBtn    = document.getElementById('logoutBtn');
  const adminUser    = document.getElementById('adminUser');

  // Guide map
  const mapFileInput    = document.getElementById('mapFileInput');
  const mapUploadZone   = document.getElementById('mapUploadZone');
  const mapProgress     = document.getElementById('mapProgress');
  const mapProgressFill = document.getElementById('mapProgressFill');
  const mapProgressLabel= document.getElementById('mapProgressLabel');
  const mapResult       = document.getElementById('mapResult');
  const currentMapWrap  = document.getElementById('currentMapWrap');
  const currentMapImg   = document.getElementById('currentMapImg');

  // Notices
  const noticeFileInput    = document.getElementById('noticeFileInput');
  const noticeUploadZone   = document.getElementById('noticeUploadZone');
  const noticeProgress     = document.getElementById('noticeProgress');
  const noticeProgressFill = document.getElementById('noticeProgressFill');
  const noticeProgressLabel= document.getElementById('noticeProgressLabel');
  const noticeResult       = document.getElementById('noticeResult');
  const noticeList         = document.getElementById('noticeList');
  const noticeListEmpty    = document.getElementById('noticeListEmpty');

  /* ── GitHub API helpers ── */
  async function ghFetch(path, opts = {}) {
    const token = storage.getToken();
    const res = await fetch(`${API}/${path}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'X-GitHub-Api-Version': '2022-11-28',
      },
      ...opts,
    });
    const json = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data: json };
  }

  async function getFileSHA(repoPath) {
    const { ok, data } = await ghFetch(repoPath);
    return ok ? data.sha : null;
  }

  async function putFile(repoPath, base64Content, message, sha = null) {
    const body = { message, content: base64Content, branch: BRANCH };
    if (sha) body.sha = sha;
    return ghFetch(repoPath, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  }

  async function deleteFile(repoPath, sha, message) {
    return ghFetch(repoPath, {
      method: 'DELETE',
      body: JSON.stringify({ message, sha, branch: BRANCH }),
    });
  }

  /* ── 토큰 암호화/복호화 (Web Crypto AES-GCM) ── */
  const CRYPTO_SALT = new TextEncoder().encode('zzl-zoozooland-admin-2026');

  async function deriveKey(password) {
    const mat = await crypto.subtle.importKey(
      'raw', new TextEncoder().encode(password), { name: 'PBKDF2' }, false, ['deriveKey']
    );
    return crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt: CRYPTO_SALT, iterations: 100000, hash: 'SHA-256' },
      mat, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']
    );
  }

  async function encryptToken(token, password) {
    const key = await deriveKey(password);
    const iv  = crypto.getRandomValues(new Uint8Array(12));
    const enc = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv }, key, new TextEncoder().encode(token)
    );
    const out = new Uint8Array(12 + enc.byteLength);
    out.set(iv); out.set(new Uint8Array(enc), 12);
    return btoa(String.fromCharCode(...out));
  }

  async function decryptToken(b64, password) {
    const key  = await deriveKey(password);
    const data = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    const plain = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: data.slice(0, 12) }, key, data.slice(12)
    );
    return new TextDecoder().decode(plain);
  }

  /* ── base64 → UTF-8 문자열 (한글 깨짐 방지) ── */
  function b64utf8(str) {
    return new TextDecoder('utf-8').decode(
      Uint8Array.from(atob(str.replace(/\n/g, '')), c => c.charCodeAt(0))
    );
  }

  /* ── File → base64 ── */
  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(',')[1]);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  /* ── Sanitize filename ── */
  function safeFilename(name) {
    return name.replace(/[^a-zA-Z0-9._-]/g, '_').toLowerCase();
  }

  /* ── UI helpers ── */
  function showProgress(fillEl, wrapEl, labelEl, pct, label = '') {
    wrapEl.classList.add('show');
    fillEl.style.width = `${pct}%`;
    if (label) labelEl.textContent = label;
  }

  function hideProgress(wrapEl) {
    wrapEl.classList.remove('show');
  }

  function showResult(el, ok, msg) {
    el.classList.add('show');
    el.classList.toggle('ok', ok);
    el.classList.toggle('err', !ok);
    el.textContent = ok ? `✅ ${msg}` : `❌ ${msg}`;
    setTimeout(() => el.classList.remove('show'), 6000);
  }

  /* ══════════════════════════════════════
     비밀번호 + 연동코드 2단계 로그인
  ══════════════════════════════════════ */

  // ── 관리자 비밀번호 (직원 공유용) ──────────────────
  // 변경 시 이 값만 수정하세요
  const ADMIN_PIN = 'zoozoo4500';
  // ─────────────────────────────────────────────────

  const pinInput  = document.getElementById('pinInput');
  const pinBtn    = document.getElementById('pinBtn');
  const pinError  = document.getElementById('pinError');
  const step1     = document.getElementById('step1');
  const step2     = document.getElementById('step2');

  // 비밀번호 확인 → auth.json에서 자동 복호화
  async function checkPin() {
    const pin = pinInput?.value.trim();
    if (pin !== ADMIN_PIN) { pinError?.classList.add('show'); return; }

    pinBtn.disabled = true;
    pinBtn.textContent = '확인 중…';
    pinError?.classList.remove('show');

    try {
      // 1. localStorage 우선
      let token = storage.getToken();

      // 2. 없으면 auth.json에서 복호화 시도
      if (!token) {
        const res = await fetch('data/auth.json?t=' + Date.now(), { cache: 'no-cache' });
        if (res.ok) {
          const { token: enc } = await res.json();
          if (enc) {
            token = await decryptToken(enc, pin);
            storage.setToken(token);
          }
        }
      }

      if (token) {
        showAdmin('관리자');
      } else {
        // 아직 연동 코드 미설정 → 최초 설정 화면
        step1.style.display = 'none';
        step2.style.display = 'block';
      }
    } catch {
      // 복호화 실패 (비밀번호 변경 등) → 연동 코드 재설정
      storage.clear();
      step1.style.display = 'none';
      step2.style.display = 'block';
    } finally {
      pinBtn.disabled = false;
      pinBtn.textContent = '입장';
    }
  }

  pinBtn?.addEventListener('click', checkPin);
  pinInput?.addEventListener('keydown', e => { if (e.key === 'Enter') checkPin(); });

  // 연동코드(GitHub 토큰) 최초 설정 → 암호화 후 auth.json 저장
  async function tryLogin(token) {
    loginBtn.disabled = true;
    loginBtn.textContent = '저장 중…';
    loginError.classList.remove('show');

    try {
      // 1. 토큰 유효성 확인
      const res = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}`, {
        headers: { 'Authorization': `Bearer ${token}`, 'Accept': 'application/vnd.github+json' },
      });
      if (!res.ok) throw new Error('Unauthorized');

      // 2. 현재 비밀번호로 토큰 암호화
      const encrypted = await encryptToken(token, ADMIN_PIN);

      // 3. auth.json에 저장 (GitHub API 직접 호출 - 아직 storage에 없으므로)
      const authRes = await fetch(`${API}/website/data/auth.json`, {
        headers: { 'Authorization': `Bearer ${token}`, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' }
      });
      const authData = await authRes.json().catch(() => ({}));

      const content = btoa(unescape(encodeURIComponent(JSON.stringify({ token: encrypted }, null, 2))));
      await fetch(`${API}/website/data/auth.json`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/vnd.github+json',
          'Content-Type': 'application/json',
          'X-GitHub-Api-Version': '2022-11-28'
        },
        body: JSON.stringify({
          message: '🔐 관리자 연동 코드 업데이트',
          content,
          branch: BRANCH,
          ...(authData.sha ? { sha: authData.sha } : {})
        })
      });

      // 4. localStorage 저장 및 진입
      storage.setToken(token);
      showAdmin('관리자');
    } catch {
      loginError.classList.add('show');
      loginError.textContent = '❌ 코드 확인 실패. 다시 확인해주세요.';
    } finally {
      loginBtn.disabled = false;
      loginBtn.textContent = '설정 완료';
    }
  }

  loginBtn?.addEventListener('click', () => {
    const t = tokenInput?.value.trim();
    if (t) tryLogin(t);
  });
  tokenInput?.addEventListener('keydown', e => {
    if (e.key === 'Enter') loginBtn?.click();
  });

  /* ── 자동 로그인 (비밀번호 없이 토큰만 있는 구버전 호환) ── */

  /* ── Show/Hide screens ── */
  function showAdmin(username) {
    loginScreen.classList.add('hidden');
    adminScreen.classList.add('show');
    if (adminUser) adminUser.textContent = username;
    loadCurrentMap();
    loadNotices();
    loadProducts();
    loadAdminPrograms();
    loadAdminSettings();
    loadAdminInfo();
  }

  logoutBtn?.addEventListener('click', () => {
    // 토큰은 유지 — 비밀번호 화면으로만 돌아감
    loginScreen.classList.remove('hidden');
    adminScreen.classList.remove('show');
    if (step1) step1.style.display = 'block';
    if (step2) step2.style.display = 'none';
    if (pinInput) pinInput.value = '';
    if (tokenInput) tokenInput.value = '';
  });

  /* ── 연동 해제 (토큰 초기화 + 비밀번호 화면) ── */
  document.getElementById('disconnectBtn')?.addEventListener('click', () => {
    if (!confirm('이 기기의 연동을 해제하면 다음 로그인 시 연동 코드를 다시 입력해야 합니다. 계속할까요?')) return;
    storage.clear();
    loginScreen.classList.remove('hidden');
    adminScreen.classList.remove('show');
    if (step1) step1.style.display = 'block';
    if (step2) step2.style.display = 'none';
    if (pinInput) pinInput.value = '';
  });

  /* ── 항상 비밀번호 화면 표시 ── */
  loginScreen.classList.remove('hidden');

  /* ══════════════════════════════════════
     가이드맵 업데이트
  ══════════════════════════════════════ */
  function loadCurrentMap() {
    const img = currentMapImg;
    if (!img) return;
    const src = `../images/guidemap.jpg?t=${Date.now()}`;
    const testImg = new Image();
    testImg.onload = () => {
      img.src = src;
      currentMapWrap.style.display = 'block';
    };
    testImg.onerror = () => {
      currentMapWrap.style.display = 'none';
    };
    testImg.src = src;
  }

  async function uploadGuideMap(file) {
    mapResult.classList.remove('show');
    showProgress(mapProgressFill, mapProgress, mapProgressLabel, 10, '이미지 읽는 중…');

    try {
      const b64 = await fileToBase64(file);
      showProgress(mapProgressFill, mapProgress, mapProgressLabel, 35, 'GitHub 확인 중…');

      const sha = await getFileSHA('website/images/guidemap.jpg');
      showProgress(mapProgressFill, mapProgress, mapProgressLabel, 60, '업로드 중…');

      const { ok } = await putFile(
        'website/images/guidemap.jpg',
        b64,
        '🗺 가이드맵 업데이트',
        sha
      );

      showProgress(mapProgressFill, mapProgress, mapProgressLabel, 100, '완료!');
      setTimeout(() => hideProgress(mapProgress), 1200);
      showResult(mapResult, ok, ok ? '가이드맵이 업데이트되었습니다. 1~3분 후 반영됩니다.' : '업로드 실패. 토큰 권한을 확인해주세요.');

      if (ok) loadCurrentMap();
    } catch (err) {
      hideProgress(mapProgress);
      showResult(mapResult, false, `오류: ${err.message}`);
    }
  }

  mapFileInput?.addEventListener('change', e => {
    const file = e.target.files?.[0];
    if (file) uploadGuideMap(file);
    e.target.value = '';
  });

  setupDragDrop(mapUploadZone, mapFileInput, uploadGuideMap);

  /* ══════════════════════════════════════
     공지/이벤트 관리
  ══════════════════════════════════════ */
  let noticesData = { notices: [] };

  async function loadNotices() {
    try {
      const { ok, data } = await ghFetch('website/data/notices.json');
      if (ok && data.content) {
        const raw = b64utf8(data.content);
        noticesData = JSON.parse(raw);
      }
    } catch {
      noticesData = { notices: [] };
    }
    renderNoticeList();
  }

  function renderNoticeList() {
    const list = noticesData.notices || [];

    // Clear existing items (keep empty state)
    Array.from(noticeList.children)
      .filter(el => el.classList.contains('notice-item'))
      .forEach(el => el.remove());

    if (list.length === 0) {
      noticeListEmpty.style.display = 'block';
      return;
    }

    noticeListEmpty.style.display = 'none';

    list.forEach(n => {
      const item = document.createElement('div');
      item.className = 'notice-item';
      item.dataset.id = n.id;

      const imgPath = `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}/website/${n.image}`;

      item.innerHTML = `
        <img class="notice-thumb" src="${imgPath}" alt="" loading="lazy">
        <div class="notice-item-info">
          <div class="notice-item-name">${n.id}</div>
          <div class="notice-item-date">${n.date}</div>
        </div>
        <div class="notice-item-actions">
          <button class="btn-del" data-id="${n.id}">삭제</button>
        </div>
      `;

      noticeList.insertBefore(item, noticeListEmpty);
    });

    // Delete buttons
    noticeList.querySelectorAll('.btn-del').forEach(btn => {
      btn.addEventListener('click', () => deleteNotice(btn.dataset.id));
    });
  }

  async function uploadNoticeImage(file) {
    noticeResult.classList.remove('show');
    showProgress(noticeProgressFill, noticeProgress, noticeProgressLabel, 10, '이미지 읽는 중…');

    try {
      const b64     = await fileToBase64(file);
      const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      const safeName = safeFilename(file.name);
      const uid     = `${dateStr}_${Date.now()}`;
      const imgFilename = `notice_${uid}_${safeName}`;
      const repoImgPath = `website/images/notices/${imgFilename}`;
      const dataImgPath = `images/notices/${imgFilename}`;

      showProgress(noticeProgressFill, noticeProgress, noticeProgressLabel, 35, '이미지 업로드 중…');

      const { ok: imgOk } = await putFile(repoImgPath, b64, `📢 공지 이미지 추가: ${imgFilename}`);
      if (!imgOk) throw new Error('이미지 업로드 실패');

      showProgress(noticeProgressFill, noticeProgress, noticeProgressLabel, 70, '목록 업데이트 중…');

      // Update notices.json
      const newNotice = {
        id:    uid,
        image: dataImgPath,
        alt:   '공지/이벤트',
        link:  null,
        date:  new Date().toISOString().slice(0, 10),
      };

      noticesData.notices.unshift(newNotice); // newest first

      const jsonSHA = await getFileSHA('website/data/notices.json');
      const jsonB64 = btoa(unescape(encodeURIComponent(JSON.stringify(noticesData, null, 2))));
      const { ok: jsonOk } = await putFile(
        'website/data/notices.json',
        jsonB64,
        '📢 공지 목록 업데이트',
        jsonSHA
      );

      if (!jsonOk) {
        // Rollback local data
        noticesData.notices.shift();
        throw new Error('목록 저장 실패');
      }

      showProgress(noticeProgressFill, noticeProgress, noticeProgressLabel, 100, '완료!');
      setTimeout(() => hideProgress(noticeProgress), 1200);
      showResult(noticeResult, true, '공지/이벤트가 등록되었습니다. 1~3분 후 반영됩니다.');
      renderNoticeList();
    } catch (err) {
      hideProgress(noticeProgress);
      showResult(noticeResult, false, `오류: ${err.message}`);
    }
  }

  async function deleteNotice(id) {
    if (!confirm(`"${id}" 공지를 삭제하시겠습니까?`)) return;

    const idx = noticesData.notices.findIndex(n => n.id === id);
    if (idx === -1) return;

    const notice = noticesData.notices[idx];
    const repoImgPath = `website/${notice.image}`;

    try {
      // Delete image file
      const imgSHA = await getFileSHA(repoImgPath);
      if (imgSHA) {
        await deleteFile(repoImgPath, imgSHA, `🗑 공지 이미지 삭제: ${id}`);
      }

      // Update notices.json
      noticesData.notices.splice(idx, 1);
      const jsonSHA = await getFileSHA('website/data/notices.json');
      const jsonB64 = btoa(unescape(encodeURIComponent(JSON.stringify(noticesData, null, 2))));
      await putFile('website/data/notices.json', jsonB64, '🗑 공지 목록 업데이트', jsonSHA);

      renderNoticeList();
      showResult(noticeResult, true, '공지가 삭제되었습니다.');
    } catch (err) {
      showResult(noticeResult, false, `삭제 실패: ${err.message}`);
      // Restore local data
      noticesData.notices.splice(idx, 0, notice);
    }
  }

  noticeFileInput?.addEventListener('change', e => {
    const file = e.target.files?.[0];
    if (file) uploadNoticeImage(file);
    e.target.value = '';
  });

  setupDragDrop(noticeUploadZone, noticeFileInput, uploadNoticeImage);

  /* ══════════════════════════════════════
     먹이체험 + 이용수칙 관리 (info.json)
  ══════════════════════════════════════ */
  let infoData = { feeding: [], conduct: [] };

  async function loadAdminInfo() {
    try {
      const { ok, data } = await ghFetch('website/data/info.json');
      if (ok && data.content) infoData = JSON.parse(b64utf8(data.content));
    } catch { infoData = { feeding: [], conduct: [] }; }
    renderFeedingList();
    renderConductList();
  }

  async function saveInfo(msg) {
    const sha = await getFileSHA('website/data/info.json');
    const b64 = btoa(unescape(encodeURIComponent(JSON.stringify(infoData, null, 2))));
    return putFile('website/data/info.json', b64, msg, sha);
  }

  // ── 먹이체험 ──
  function renderFeedingList() {
    const list = document.getElementById('feedingAdminList');
    const empty = document.getElementById('feedingAdminEmpty');
    if (!list) return;
    Array.from(list.children).filter(el => el.classList.contains('notice-item')).forEach(el => el.remove());
    if (!infoData.feeding.length) { empty.style.display = 'block'; return; }
    empty.style.display = 'none';
    infoData.feeding.forEach((f, idx) => {
      const item = document.createElement('div');
      item.className = 'notice-item';
      item.innerHTML = `
        <div class="product-item-info">
          <div class="product-item-name">${f.type}</div>
          <div class="product-item-price">${f.animals}</div>
        </div>
        <div class="notice-item-actions">
          <button class="btn-del" data-idx="${idx}">삭제</button>
        </div>`;
      list.insertBefore(item, empty);
    });
    list.querySelectorAll('.btn-del').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('삭제하시겠습니까?')) return;
        infoData.feeding.splice(+btn.dataset.idx, 1);
        const { ok } = await saveInfo('🥕 먹이체험 삭제');
        if (ok) { renderFeedingList(); showResult(document.getElementById('feedingResult'), true, '삭제되었습니다.'); }
      });
    });
  }

  document.getElementById('btnAddFeeding')?.addEventListener('click', async () => {
    const type    = document.getElementById('feedType')?.value.trim();
    const feed    = document.getElementById('feedItems')?.value.trim();
    const animals = document.getElementById('feedAnimals')?.value.trim();
    const res     = document.getElementById('feedingResult');
    if (!type || !animals) { showResult(res, false, '종류와 동물은 필수입니다.'); return; }
    infoData.feeding.push({ type, feed, animals });
    const { ok } = await saveInfo('🥕 먹이체험 추가');
    if (!ok) { infoData.feeding.pop(); showResult(res, false, '저장 실패'); return; }
    renderFeedingList();
    showResult(res, true, '추가되었습니다. 1~3분 후 반영됩니다.');
    ['feedType','feedItems','feedAnimals'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  });

  // ── 이용수칙 ──
  function renderConductList() {
    const list = document.getElementById('conductAdminList');
    const empty = document.getElementById('conductAdminEmpty');
    if (!list) return;
    Array.from(list.children).filter(el => el.classList.contains('notice-item')).forEach(el => el.remove());
    if (!infoData.conduct.length) { empty.style.display = 'block'; return; }
    empty.style.display = 'none';
    infoData.conduct.forEach((r, idx) => {
      const item = document.createElement('div');
      item.className = 'notice-item';
      item.innerHTML = `
        <div class="product-item-info">
          <div class="product-item-name">${r.ko}</div>
          <div class="product-item-price">${r.en}</div>
        </div>
        <div class="notice-item-actions">
          <button class="btn-del" data-idx="${idx}">삭제</button>
        </div>`;
      list.insertBefore(item, empty);
    });
    list.querySelectorAll('.btn-del').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('삭제하시겠습니까?')) return;
        infoData.conduct.splice(+btn.dataset.idx, 1);
        const { ok } = await saveInfo('📋 이용수칙 삭제');
        if (ok) { renderConductList(); showResult(document.getElementById('conductResult'), true, '삭제되었습니다.'); }
      });
    });
  }

  document.getElementById('btnAddConduct')?.addEventListener('click', async () => {
    const en  = document.getElementById('conductEn')?.value.trim();
    const ko  = document.getElementById('conductKo')?.value.trim();
    const res = document.getElementById('conductResult');
    if (!en || !ko) { showResult(res, false, '영문과 한국어 모두 입력해주세요.'); return; }
    infoData.conduct.push({ en, ko });
    const { ok } = await saveInfo('📋 이용수칙 추가');
    if (!ok) { infoData.conduct.pop(); showResult(res, false, '저장 실패'); return; }
    renderConductList();
    showResult(res, true, '추가되었습니다. 1~3분 후 반영됩니다.');
    ['conductEn','conductKo'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  });

  /* ══════════════════════════════════════
     프로그램 관리
  ══════════════════════════════════════ */
  let programsData = { weekday: [], weekend: [] };

  async function loadAdminPrograms() {
    try {
      const { ok, data } = await ghFetch('website/data/programs.json');
      if (ok && data.content) {
        programsData = JSON.parse(b64utf8(data.content));
      }
    } catch { programsData = { weekday: [], weekend: [] }; }
    renderProgramAdminList();
  }

  function renderProgramAdminList() {
    const container = document.getElementById('programAdminList');
    if (!container) return;
    container.innerHTML = '';

    const sections = [
      { key: 'weekend', label: '🎉 주말 · 공휴일' },
      { key: 'weekday', label: '📅 주중 (화~금)' },
    ];

    sections.forEach(({ key, label }) => {
      const list = programsData[key] || [];
      const wrap = document.createElement('div');
      wrap.style.marginBottom = '16px';
      wrap.innerHTML = `<div style="font-size:12px;font-weight:700;color:var(--g700);margin-bottom:8px;padding-bottom:6px;border-bottom:1.5px solid var(--g100)">${label}</div>`;

      if (list.length === 0) {
        const empty = document.createElement('p');
        empty.style.cssText = 'font-size:13px;color:var(--n500);padding:8px 0';
        empty.textContent = '등록된 프로그램 없음';
        wrap.appendChild(empty);
      } else {
        list.forEach((p, idx) => {
          const item = document.createElement('div');
          item.className = 'notice-item';
          item.style.marginBottom = '8px';
          item.innerHTML = `
            <div class="product-item-info">
              <div class="product-item-name">${p.time} · ${p.name}</div>
              <div class="product-item-price">${p.location}</div>
            </div>
            <div class="notice-item-actions">
              <button class="btn-del" data-key="${key}" data-idx="${idx}">삭제</button>
            </div>`;
          wrap.appendChild(item);
        });
      }
      container.appendChild(wrap);
    });

    container.querySelectorAll('.btn-del').forEach(btn => {
      btn.addEventListener('click', () => deleteProgram(btn.dataset.key, +btn.dataset.idx));
    });
  }

  document.getElementById('btnAddProgram')?.addEventListener('click', addProgram);

  async function addProgram() {
    const type     = document.getElementById('progType')?.value;
    const time     = document.getElementById('progTime')?.value.trim();
    const name     = document.getElementById('progName')?.value.trim();
    const location = document.getElementById('progLocation')?.value.trim();
    const resultEl = document.getElementById('progResult');

    if (!time || !name || !location) {
      showResult(resultEl, false, '시간, 프로그램명, 장소는 필수입니다.');
      return;
    }

    const btn = document.getElementById('btnAddProgram');
    btn.disabled = true;

    try {
      programsData[type].push({ time, name, location });
      const sha = await getFileSHA('website/data/programs.json');
      const b64 = btoa(unescape(encodeURIComponent(JSON.stringify(programsData, null, 2))));
      const { ok } = await putFile('website/data/programs.json', b64, '🎭 프로그램 추가', sha);

      if (!ok) { programsData[type].pop(); throw new Error('저장 실패'); }
      showResult(resultEl, true, '추가되었습니다. 1~3분 후 반영됩니다.');
      renderProgramAdminList();
      ['progTime','progName','progLocation'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    } catch (err) {
      showResult(resultEl, false, `오류: ${err.message}`);
    } finally { btn.disabled = false; }
  }

  async function deleteProgram(key, idx) {
    if (!confirm('프로그램을 삭제하시겠습니까?')) return;
    const removed = programsData[key].splice(idx, 1)[0];
    try {
      const sha = await getFileSHA('website/data/programs.json');
      const b64 = btoa(unescape(encodeURIComponent(JSON.stringify(programsData, null, 2))));
      await putFile('website/data/programs.json', b64, '🗑 프로그램 삭제', sha);
      renderProgramAdminList();
    } catch (err) {
      programsData[key].splice(idx, 0, removed);
      alert(`삭제 실패: ${err.message}`);
    }
  }

  /* ══════════════════════════════════════
     이메일 설정
  ══════════════════════════════════════ */
  async function loadAdminSettings() {
    try {
      const { ok, data } = await ghFetch('website/data/settings.json');
      if (ok && data.content) {
        const s = JSON.parse(b64utf8(data.content));
        const ge = document.getElementById('settingGroupEmail');
        const be = document.getElementById('settingBizEmail');
        if (ge) ge.value = s.group_email || '';
        if (be) be.value = s.biz_email   || '';
      }
    } catch {}
  }

  document.getElementById('btnSaveSettings')?.addEventListener('click', saveSettings);

  async function saveSettings() {
    const groupEmail = document.getElementById('settingGroupEmail')?.value.trim();
    const bizEmail   = document.getElementById('settingBizEmail')?.value.trim();
    const resultEl   = document.getElementById('settingsResult');
    const btn        = document.getElementById('btnSaveSettings');

    btn.disabled = true;
    try {
      const settings = { group_email: groupEmail, biz_email: bizEmail };
      const sha = await getFileSHA('website/data/settings.json');
      const b64 = btoa(unescape(encodeURIComponent(JSON.stringify(settings, null, 2))));
      const { ok } = await putFile('website/data/settings.json', b64, '✉️ 이메일 설정 저장', sha);
      showResult(resultEl, ok, ok ? '저장되었습니다. 1~3분 후 반영됩니다.' : '저장 실패. 다시 시도해주세요.');
    } catch (err) {
      showResult(resultEl, false, `오류: ${err.message}`);
    } finally { btn.disabled = false; }
  }

  /* ══════════════════════════════════════
     예매 상품 관리
  ══════════════════════════════════════ */
  let productsData = { products: [] };

  const productList      = document.getElementById('productList');
  const productListEmpty = document.getElementById('productListEmpty');
  const prodFetchError   = document.getElementById('prodFetchError');

  async function loadProducts() {
    try {
      const { ok, data } = await ghFetch('website/data/products.json');
      if (ok && data.content) {
        const raw = b64utf8(data.content);
        productsData = JSON.parse(raw);
      }
    } catch { productsData = { products: [] }; }
    renderProductList();
  }

  function renderProductList() {
    const list = productsData.products || [];
    Array.from(productList.children)
      .filter(el => el.classList.contains('product-item'))
      .forEach(el => el.remove());

    if (list.length === 0) { productListEmpty.style.display = 'block'; return; }
    productListEmpty.style.display = 'none';

    list.forEach(p => {
      const item = document.createElement('div');
      item.className = 'product-item';
      const thumb = p.image
        ? `<img src="https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}/website/${p.image}" alt="">`
        : '🎟';
      item.innerHTML = `
        <div class="product-thumb">${thumb}</div>
        <div class="product-item-info">
          <div class="product-item-name">${p.name}</div>
          <div class="product-item-price">${Number(p.sale_price).toLocaleString()}원${p.valid_until ? ' · ' + p.valid_until + '까지' : ''}</div>
        </div>
        <div class="notice-item-actions">
          <button class="btn-del" data-id="${p.id}">삭제</button>
        </div>`;
      productList.insertBefore(item, productListEmpty);
    });
    productList.querySelectorAll('.btn-del').forEach(btn => {
      btn.addEventListener('click', () => deleteProduct(btn.dataset.id));
    });
  }

  /* ── 네이버 URL → 상품 데이터 자동 파싱 ── */
  let fetchedProduct = null;  // 현재 미리보기 중인 상품 데이터

  const btnFetch         = document.getElementById('btnFetchProduct');
  const prodUrlInput     = document.getElementById('prodUrlInput');
  const prodPreview      = document.getElementById('prodPreview');
  const btnSaveProd      = document.getElementById('btnSaveProduct');
  const btnCancelProd    = document.getElementById('btnCancelProduct');
  const prodProgress     = document.getElementById('prodProgress');
  const prodProgressFill = document.getElementById('prodProgressFill');
  const prodProgressLabel= document.getElementById('prodProgressLabel');
  const prodResult       = document.getElementById('prodResult');

  btnFetch?.addEventListener('click', () => fetchFromUrl());
  prodUrlInput?.addEventListener('keydown', e => { if (e.key === 'Enter') fetchFromUrl(); });
  btnSaveProd?.addEventListener('click', () => saveProduct());
  btnCancelProd?.addEventListener('click', () => {
    prodPreview.style.display = 'none';
    fetchedProduct = null;
  });

  async function fetchFromUrl() {
    const url = prodUrlInput?.value.trim();
    if (!url) return;

    btnFetch.disabled = true;
    document.getElementById('fetchBtnText').textContent = '불러오는 중…';
    document.getElementById('fetchSpinner').style.display = 'block';
    prodFetchError.classList.remove('show');
    prodPreview.style.display = 'none';

    try {
      const parsed = await parseNaverBookingUrl(url);
      fetchedProduct = { ...parsed, booking_url: parsed.bookingUrl || url };
    } catch {
      // 이미지 fetch 실패해도 빈 폼으로 진행
      fetchedProduct = { name: '', image: '', salePrice: null, origPrice: null, discountRate: null, validUntil: null, booking_url: url };
    } finally {
      btnFetch.disabled = false;
      document.getElementById('fetchBtnText').textContent = '불러오기';
      document.getElementById('fetchSpinner').style.display = 'none';
    }
    renderPreview(fetchedProduct);
    prodPreview.style.display = 'block';
  }

  /* ── OG 이미지/URL만 프록시로 가져오기 ── */
  async function fetchOgImage(url) {
    try {
      const res = await fetch(`https://corsproxy.io/?${encodeURIComponent(url)}`, {
        signal: AbortSignal.timeout(8000),
      });
      if (!res.ok) return null;
      const html = await res.text();
      const doc  = new DOMParser().parseFromString(html, 'text/html');
      return doc.querySelector('meta[property="og:image"]')?.content || null;
    } catch { return null; }
  }

  async function parseNaverBookingUrl(rawUrl) {
    // Naver URL에서 이미지만 가져오기 (가장 성공률 높은 부분)
    const image = await fetchOgImage(rawUrl);

    // 예약 URL 구성
    const placeIdM = rawUrl.match(/place\/(\d{7,12})/i);
    const placeId  = placeIdM?.[1];
    const bookingUrl = placeId
      ? `https://map.naver.com/p/entry/place/${placeId}?placePath=/reservation`
      : rawUrl;

    // 이미지만 반환 — name·price·validUntil은 null → renderPreview에서 입력 폼 표시
    return { name: '', image: image || '', salePrice: null, origPrice: null, discountRate: null, validUntil: null, bookingUrl };
  }

  function renderPreview(p) {
    // 이미지
    const imgEl = document.getElementById('prodPreviewImg');
    const phEl  = document.getElementById('prodPreviewImgPh');
    if (p.image) {
      imgEl.src = p.image;
      imgEl.style.display = 'block';
      phEl.style.display  = 'none';
    } else {
      imgEl.style.display = 'none';
      phEl.style.display  = 'block';
    }

    // 이름
    document.getElementById('prodPreviewName').textContent = p.name || '(아래에서 상품명 입력)';

    // 할인율
    const rate = p.discountRate
      ?? (p.origPrice && p.salePrice && p.origPrice > p.salePrice
          ? Math.round((1 - p.salePrice / p.origPrice) * 100) : null);

    const discEl = document.getElementById('prodPreviewDisc');
    if (rate) { discEl.textContent = `${rate}%`; discEl.style.display = ''; }
    else discEl.style.display = 'none';

    const saleEl = document.getElementById('prodPreviewSale');
    saleEl.textContent = p.salePrice ? `${Number(p.salePrice).toLocaleString()}원` : '가격 미확인';

    const origEl = document.getElementById('prodPreviewOrig');
    if (p.origPrice && p.origPrice !== p.salePrice) {
      origEl.textContent = `${Number(p.origPrice).toLocaleString()}원`;
      origEl.style.display = '';
    } else origEl.style.display = 'none';

    // 메타 (기한만)
    const metaEl = document.getElementById('prodPreviewMeta');
    metaEl.textContent = p.validUntil ? `${p.validUntil}까지 사용가능` : '';

    // 없는 필드 수동 입력 폼
    const manualEl  = document.getElementById('prodManual');
    const fieldsEl  = document.getElementById('prodManualFields');
    const missing = [];
    if (!p.name)       missing.push({ id: 'mName',       label: '상품명 *',       type: 'text',   ph: '[2026.05]소풍은 쥬쥬랜드' });
    if (!p.salePrice)  missing.push({ id: 'mSalePrice',  label: '판매가 (원) *',  type: 'number', ph: '15000' });
    if (!p.origPrice)  missing.push({ id: 'mOrigPrice',  label: '정가 (원)',       type: 'number', ph: '27800' });
    if (!p.validUntil) missing.push({ id: 'mValidUntil', label: '사용기한',        type: 'text',   ph: '2026.5.31' });

    if (missing.length > 0) {
      fieldsEl.innerHTML = missing.map(f => `
        <div class="form-col">
          <label class="form-label">${f.label}</label>
          <input class="form-input" id="${f.id}" type="${f.type}" placeholder="${f.ph}">
        </div>`).join('');
      manualEl.style.display = 'block';
    } else {
      manualEl.style.display = 'none';
    }
  }

  async function saveProduct() {
    if (!fetchedProduct) return;

    // 수동 입력값 반영
    const mName  = document.getElementById('mName')?.value.trim();
    const mPrice = document.getElementById('mSalePrice')?.value;
    const mOrig  = document.getElementById('mOrigPrice')?.value;
    const mValid = document.getElementById('mValidUntil')?.value.trim();
    if (mName)  fetchedProduct.name      = mName;
    if (mPrice) fetchedProduct.salePrice = +mPrice;
    if (mOrig)  fetchedProduct.origPrice = +mOrig;
    if (mValid) fetchedProduct.validUntil = mValid;

    if (!fetchedProduct.name)      { showResult(prodResult, false, '상품명을 입력해주세요.'); return; }
    if (!fetchedProduct.salePrice) { showResult(prodResult, false, '판매가를 입력해주세요.'); return; }

    btnSaveProd.disabled = true;
    prodResult.classList.remove('show');
    showProgress(prodProgressFill, prodProgress, prodProgressLabel, 20, '저장 중…');

    try {
      const uid = `prod_${Date.now()}`;
      const rate = fetchedProduct.discountRate
        ?? (fetchedProduct.origPrice && fetchedProduct.origPrice > fetchedProduct.salePrice
            ? Math.round((1 - fetchedProduct.salePrice / fetchedProduct.origPrice) * 100) : null);

      const newProduct = {
        id: uid,
        name: fetchedProduct.name,
        sale_price: fetchedProduct.salePrice,
        ...(fetchedProduct.origPrice ? { original_price: fetchedProduct.origPrice } : {}),
        ...(rate ? { discount_rate: rate } : {}),
        ...(fetchedProduct.validUntil ? { valid_until: fetchedProduct.validUntil } : {}),
        booking_url: fetchedProduct.booking_url,
        ...(fetchedProduct.image ? { og_image: fetchedProduct.image } : {}),
      };

      productsData.products.push(newProduct);
      showProgress(prodProgressFill, prodProgress, prodProgressLabel, 70, 'GitHub에 저장 중…');

      const sha = await getFileSHA('website/data/products.json');
      const b64 = btoa(unescape(encodeURIComponent(JSON.stringify(productsData, null, 2))));
      const { ok } = await putFile('website/data/products.json', b64, '🎟 예매 상품 추가', sha);
      if (!ok) { productsData.products.pop(); throw new Error('저장 실패'); }

      showProgress(prodProgressFill, prodProgress, prodProgressLabel, 100, '완료!');
      setTimeout(() => hideProgress(prodProgress), 1000);
      showResult(prodResult, true, '등록 완료! 1~3분 후 홈페이지에 반영됩니다.');
      renderProductList();

      prodPreview.style.display = 'none';
      if (prodUrlInput) prodUrlInput.value = '';
      fetchedProduct = null;
    } catch (err) {
      hideProgress(prodProgress);
      showResult(prodResult, false, `오류: ${err.message}`);
    } finally {
      btnSaveProd.disabled = false;
    }
  }

  async function deleteProduct(id) {
    if (!confirm('상품을 삭제하시겠습니까?')) return;
    const idx = productsData.products.findIndex(p => p.id === id);
    if (idx === -1) return;
    const product = productsData.products[idx];
    try {
      productsData.products.splice(idx, 1);
      const sha = await getFileSHA('website/data/products.json');
      const b64 = btoa(unescape(encodeURIComponent(JSON.stringify(productsData, null, 2))));
      await putFile('website/data/products.json', b64, '🗑 예매 상품 삭제', sha);
      renderProductList();
      showResult(prodFetchError, true, '삭제되었습니다.');
    } catch (err) {
      productsData.products.splice(idx, 0, product);
      showResult(prodFetchError, false, `삭제 실패: ${err.message}`);
    }
  }

  /* ── Drag & drop helper ── */
  function setupDragDrop(zone, input, handler) {
    if (!zone) return;

    zone.addEventListener('dragover', e => {
      e.preventDefault();
      zone.classList.add('drag-over');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      const file = e.dataTransfer?.files?.[0];
      if (file && file.type.startsWith('image/')) handler(file);
    });
  }

})();
