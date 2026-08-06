/* ============================================================
   ZZL DEX APP  v1.0
   쥬쥬랜드 동물도감 — 수집형 게임 본체

   의존: three.js r128, zzl-parts.js, zzl-species.js, zzl-species2.js
   기획: zzl-dogam-plan-v2.md + v3-revision.md

   구조
     ZDX.zones     구역 마스터 (실좌표)
     ZDX.save      진행 저장 (localStorage → 없으면 메모리)
     ZDX.sound     Web Audio 합성 효과음 (외부 음원 없음)
     ZDX.thumbs    3D → 2D 썸네일 캐시 (도감 목록·퍼즐 조각)
     ZDX.app       화면 전환·조우·퍼즐 로직
   ============================================================ */
(function (global) {
'use strict';

var ZDX = {};

/* ══ 구역 마스터 ══════════════════════════════
   좌표는 원본 동물 리스트 실측값.
   파충류관 + 소동물 빌리지는 같은 건물 층 구분이라 하나로 합쳤다. */
ZDX.zones = [
  { name: '파충류 빌리지',      lon: 126.8551391, lat: 37.6900442, gap: 0 },
  { name: '대동물 방목장',      lon: 126.8552881, lat: 37.6897889, gap: 0 },
  { name: '거북이 빌리지 카페', lon: 126.8550938, lat: 37.6911538, gap: 0 },
  { name: '오솔길 빌리지',      lon: 126.8553185, lat: 37.6903786, gap: 0 },
  { name: '악어 빌리지',        lon: 126.8547149, lat: 37.6906056, gap: 0 },
  { name: '호숫가',             lon: 126.8544686, lat: 37.6903647, gap: 0 },
  { name: '양 분유 체험장',     lon: 126.8548843, lat: 37.6915665, gap: 0 },
  { name: '사랑새 빌리지',      lon: 126.8552734, lat: 37.6902112, gap: 0 },
  { name: '기타',               lon: 126.8548195, lat: 37.6897747, gap: 0 },
  { name: '알파카 빌리지',      lon: 126.8544674, lat: 37.6912988, gap: 0 },
  { name: '원숭이 빌리지',      lon: 126.8547835, lat: 37.6913813, gap: 0 },
  { name: '거북이 빌리지 방사장', lon: 126.8548991, lat: 37.6914150, gap: 0 }
];
ZDX.RADIUS = 20;   /* m. 겹침 허용 — 규칙 7-A.
                      부지가 75×198m로 좁아 22m면 한자리에서 대부분의 구역에 걸린다.
                      GPS 오차(5~15m)는 흡수하면서 '가야 만난다'는 감각은 남기는 값. */

ZDX.dist = function (lo1, la1, lo2, la2) {
  var dx = (lo2 - lo1) * 111320 * Math.cos((la1 + la2) / 2 * Math.PI / 180);
  var dy = (la2 - la1) * 110540;
  return Math.sqrt(dx * dx + dy * dy);
};

/* ══ 저장 ══════════════════════════════════════
   1차 localStorage, 막히면 메모리로 자동 강등.
   운영에서는 여기에 복구 코드 서버 동기화를 붙인다 (기획 5장). */
ZDX.save = (function () {
  var KEY = 'zzl.dex.v1';
  var mem = null, useLS = false;
  try {
    localStorage.setItem(KEY + '.t', '1');
    localStorage.removeItem(KEY + '.t');
    useLS = true;
  } catch (e) { useLS = false; }

  function blank() {
    return { code: null, got: {}, visits: 1, sfx: true, bgm: false };
  }
  function read() {
    if (mem) return mem;
    if (useLS) {
      try {
        var raw = localStorage.getItem(KEY);
        mem = raw ? JSON.parse(raw) : blank();
      } catch (e) { mem = blank(); }
    } else mem = blank();
    return mem;
  }
  function write() {
    if (!useLS) return;
    try { localStorage.setItem(KEY, JSON.stringify(mem)); } catch (e) { useLS = false; }
  }
  function code() {
    var C = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789', s = '';
    for (var i = 0; i < 4; i++) s += C[Math.floor(Math.random() * C.length)];
    return 'ZZL-' + s;
  }
  return {
    persistent: function () { return useLS; },
    get: read,
    has: function (id) { return !!read().got[id]; },
    count: function () { return Object.keys(read().got).length; },
    add: function (id) {
      var d = read();
      if (!d.got[id]) d.got[id] = { at: Date.now(), seen: 1 };
      else d.got[id].seen++;
      if (!d.code) d.code = code();
      write();
      return d.got[id];
    },
    reset: function () { mem = blank(); write(); },
    set: function (k, v) { read()[k] = v; write(); }
  };
})();

/* ══ 음향 ══════════════════════════════════════
   외부 음원 없이 Web Audio로 합성한다 (저작권·용량 문제 없음).
   규칙 9-A: 소리를 꺼도 게임은 완전히 동작한다.
   규칙 9-B: 동물 울음소리는 쓰지 않는다. */
ZDX.sound = (function () {
  var ctx = null, master = null, bgGain = null, bgTimer = null;

  function ac() {
    if (!ctx) {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
      master = ctx.createGain(); master.gain.value = 0.5; master.connect(ctx.destination);
      bgGain = ctx.createGain(); bgGain.gain.value = 0.0; bgGain.connect(master);
    }
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
  }

  function tone(freq, dur, type, vol, at, slide) {
    var c = ac(); if (!c) return;
    var t = c.currentTime + (at || 0);
    var o = c.createOscillator(), g = c.createGain();
    o.type = type || 'sine';
    o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(40, slide), t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol || 0.25, t + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(master);
    o.start(t); o.stop(t + dur + 0.02);
  }
  function noise(dur, vol, at, hp) {
    var c = ac(); if (!c) return;
    var t = c.currentTime + (at || 0);
    var n = Math.floor(c.sampleRate * dur);
    var buf = c.createBuffer(1, n, c.sampleRate), d = buf.getChannelData(0);
    for (var i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
    var s = c.createBufferSource(); s.buffer = buf;
    var f = c.createBiquadFilter(); f.type = 'highpass'; f.frequency.value = hp || 1200;
    var g = c.createGain(); g.gain.value = vol || 0.12;
    s.connect(f); f.connect(g); g.connect(master);
    s.start(t);
  }

  var on = function () { return ZDX.save.get().sfx; };

  var SFX = {
    /* 1 구역 진입 */
    zone: function () { tone(523, .12, 'sine', .18); tone(784, .22, 'sine', .16, .1); },
    /* 2 조각 정답 — 딸깍 */
    snap: function () { noise(.05, .1, 0, 2600); tone(880, .07, 'square', .1); },
    /* 3 조각 오답 — 중립적인 튕김 (규칙 9-C) */
    miss: function () { tone(320, .12, 'sine', .12, 0, 250); },
    /* 4 조립 완성 */
    build: function () {
      [523, 659, 784, 1047].forEach(function (f, i) { tone(f, .18, 'triangle', .16, i * .06); });
    },
    /* 5 채색 전환 */
    paint: function () { noise(.3, .07, 0, 900); tone(1200, .3, 'sine', .08, 0, 2400); },
    /* 6 도감 등록 — 도장 */
    stamp: function () { tone(180, .18, 'sine', .3, 0, 90); noise(.09, .14, 0, 700); },
    /* 7 변종·희귀 */
    rare: function () {
      [784, 988, 1175, 1568].forEach(function (f, i) { tone(f, .3, 'sine', .14, i * .08); });
    },
    /* 8 전 종 완주 */
    fanfare: function () {
      [523, 659, 784, 1047, 784, 1047, 1319].forEach(function (f, i) {
        tone(f, .32, 'triangle', .18, i * .13);
      });
    },
    /* 동물 등장 */
    pop: function () { tone(660, .1, 'sine', .14, 0, 990); }
  };

  var api = {};
  Object.keys(SFX).forEach(function (k) {
    api[k] = function () { if (on()) try { SFX[k](); } catch (e) {} };
  });

  /* 배경음 — 잔잔한 아르페지오. 기본 꺼짐, 켜도 낮은 볼륨 */
  var SCALE = [392, 440, 523, 587, 659, 784];
  api.bgm = function (want) {
    var c = ac(); if (!c) return;
    if (want) {
      bgGain.gain.setTargetAtTime(0.22, c.currentTime, .4);
      if (bgTimer) return;
      var i = 0;
      bgTimer = setInterval(function () {
        if (!ZDX.save.get().bgm) return;
        var f = SCALE[(i * 3 + Math.floor(i / 6)) % SCALE.length];
        var t = c.currentTime;
        var o = c.createOscillator(), g = c.createGain();
        o.type = 'sine'; o.frequency.value = f * (i % 12 < 6 ? 1 : 0.5);
        g.gain.setValueAtTime(0.0001, t);
        g.gain.exponentialRampToValueAtTime(.09, t + .3);
        g.gain.exponentialRampToValueAtTime(.0001, t + 1.6);
        o.connect(g); g.connect(bgGain);
        o.start(t); o.stop(t + 1.7);
        i++;
      }, 720);
    } else {
      bgGain.gain.setTargetAtTime(0, c.currentTime, .3);
    }
  };
  api.unlock = function () { ac(); };
  return api;
})();

/* ══ 썸네일 ════════════════════════════════════
   도감 목록과 퍼즐 조각은 2D 이미지로 쓴다 (기획 10장 저사양 대응).
   3D 모델을 오프스크린에서 한 번 렌더해 dataURL로 캐시. */
ZDX.thumbs = (function () {
  var R = null, scene = null, cam = null, cache = {};

  function init() {
    if (R) return;
    var cv = document.createElement('canvas');
    cv.width = cv.height = 220;
    R = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true });
    R.setPixelRatio(1);
    if (THREE.sRGBEncoding) R.outputEncoding = THREE.sRGBEncoding;
    scene = new THREE.Scene();
    scene.add(new THREE.HemisphereLight(0xEAF4F8, 0x8E8560, 1.0));
    var k = new THREE.DirectionalLight(0xFFF8E8, 1.0); k.position.set(4, 7, 6); scene.add(k);
    var r2 = new THREE.DirectionalLight(0xC6DCFF, .35); r2.position.set(-4, 2, -3); scene.add(r2);
    cam = new THREE.PerspectiveCamera(32, 1, .1, 200);
  }

  function frame(obj, turn) {
    var b = new THREE.Box3().setFromObject(obj);
    var s = new THREE.Vector3(), c = new THREE.Vector3();
    b.getSize(s); b.getCenter(c);
    var m = Math.max(s.x, s.y, s.z) * 1.25;
    var d = (m / 2) / Math.tan(cam.fov * Math.PI / 360);
    var a = turn === undefined ? -0.6 : turn;
    cam.position.set(c.x + Math.sin(a) * d, c.y + m * 0.22, c.z + Math.cos(a) * d);
    cam.lookAt(c);
  }

  return {
    /* 종 전체 썸네일. silhouette=true 면 단색 실루엣 */
    species: function (spec, silhouette) {
      init();
      var key = spec.id + (silhouette ? ':sil' : ':full');
      if (cache[key]) return cache[key];
      var m = ZZL.build(spec.model);
      var swap = [];
      if (silhouette) {
        var sm = new THREE.MeshBasicMaterial({ color: 0xB9B3A2 });
        m.root.traverse(function (o) { if (o.isMesh) { swap.push([o, o.material]); o.material = sm; } });
      }
      scene.add(m.root);
      frame(m.root);
      R.render(scene, cam);
      var url = R.domElement.toDataURL('image/png');
      scene.remove(m.root);
      swap.forEach(function (q) { q[0].material = q[1]; });
      cache[key] = url;
      return url;
    },
    /* 부위 하나만 떼어 렌더 — 퍼즐 선택지
       head: neckG 통째로 분리 (목+머리+귀+뿔 등 head-attached extras 포함)
       body: bodyContainer에서 목·다리만 숨기고 렌더 (꼬리·body extras 포함)
       legs: 기존 단독 분리 방식 */
    part: function (spec, partName) {
      init();
      var key = spec.id + ':p:' + partName;
      if (cache[key]) return cache[key];
      var m = ZZL.build(spec.model);
      var g, parent, url;

      if (partName === 'head') {
        /* neck 그룹 자체가 head·ears·head-extras의 상위 → 통째로 분리 */
        g = m.parts.neck || m.parts.head.parent;
        parent = g.parent;
        scene.add(g);
        g.position.set(0, 0, 0);
        g.quaternion.identity();
        frame(g, -0.5);
        R.render(scene, cam);
        url = R.domElement.toDataURL('image/png');
        scene.remove(g);
        parent.add(g);

      } else if (partName === 'body') {
        /* body 컨테이너에서 머리(목)·다리만 가리고 렌더
           꼬리·quills·fins 등 body-attached extras는 자동 포함 */
        var bodyContainer = m.parts.body.parent;
        var headGroup = m.parts.neck || m.parts.head.parent;
        headGroup.visible = false;
        if (m.parts.legs) m.parts.legs.visible = false;
        parent = bodyContainer.parent;
        scene.add(bodyContainer);
        bodyContainer.position.set(0, 0, 0);
        bodyContainer.quaternion.identity();
        bodyContainer.updateMatrixWorld(true);
        /* 카메라는 몸통+꼬리 영역에 맞춤 (invisible 목·다리 제외) */
        var b = new THREE.Box3();
        b.expandByObject(m.parts.body);
        if (m.parts.tail) b.expandByObject(m.parts.tail);
        if (b.isEmpty()) b.setFromObject(m.parts.body);
        var sz = new THREE.Vector3(), ct = new THREE.Vector3();
        b.getSize(sz); b.getCenter(ct);
        var mSz = Math.max(sz.x, sz.y, sz.z) * 1.25;
        var d = (mSz / 2) / Math.tan(cam.fov * Math.PI / 360);
        cam.position.set(ct.x + Math.sin(-0.5) * d, ct.y + mSz * 0.22, ct.z + Math.cos(-0.5) * d);
        cam.lookAt(ct);
        R.render(scene, cam);
        url = R.domElement.toDataURL('image/png');
        scene.remove(bodyContainer);
        parent.add(bodyContainer);
        headGroup.visible = true;
        if (m.parts.legs) m.parts.legs.visible = true;

      } else {
        /* 다리 등 단순 부위: 기존 단독 분리 방식 */
        g = m.parts[partName];
        if (!g) { cache[key] = null; return null; }
        parent = g.parent;
        scene.add(g);
        g.position.set(0, 0, 0);
        g.quaternion.identity();
        frame(g, -0.5);
        R.render(scene, cam);
        url = R.domElement.toDataURL('image/png');
        scene.remove(g);
        parent.add(g);
      }

      cache[key] = url;
      return url;
    }
  };
})();

/* ══ 조우 로직 ═════════════════════════════════ */
ZDX.encounter = (function () {
  var lastAt = {};    /* 구역별 다음 출현 가능 시각 */
  var pending = {};   /* 구역별 남은 대기(ms) — 이탈 시 보존, 규칙 C-3 */

  return {
    /* 구역의 미수집 종 중 하나를 가중치로 뽑는다 (규칙 C-4)
       개체수가 많고 찾기 쉬운 종이 먼저 나온다 */
    pick: function (zone, list) {
      var pool = list.filter(function (s) {
        return s.zone === zone && !ZDX.save.has(s.id);
      });
      if (!pool.length) return null;
      var tot = 0;
      pool.forEach(function (s) { s._w = Math.log(1 + (s.n || 1)) + 0.4; tot += s._w; });
      var r = Math.random() * tot;
      for (var i = 0; i < pool.length; i++) { r -= pool[i]._w; if (r <= 0) return pool[i]; }
      return pool[pool.length - 1];
    },
    gap: function (zone) {
      var z = ZDX.zones.filter(function (x) { return x.name === zone; })[0];
      return z ? z.gap * 1000 : 0;
    },
    ready: function (zone) {
      return !lastAt[zone] || Date.now() >= lastAt[zone];
    },
    remain: function (zone) {
      return Math.max(0, (lastAt[zone] || 0) - Date.now());
    },
    arm: function (zone) {
      var g = this.gap(zone);
      if (g > 0) lastAt[zone] = Date.now() + g;
    },
    reset: function () { lastAt = {}; pending = {}; }
  };
})();

/* ══ 퍼즐 ══════════════════════════════════════
   규칙 4-A: 오답 조각은 같은 구역 근연종의 실제 부품을 쓴다.
   무작위·엉터리 조각을 오답으로 쓰지 않는다. */
ZDX.puzzle = {
  /* 같은 자리에 붙는 부품끼리는 서로 오답이 될 수 있다.
     꽃사슴의 가지뿔 문제라면 무플론의 나선뿔·흑염소의 뒤로 굽은 뿔이 오답이 된다.
     "머리에 무엇이 달렸는가"를 묻게 되므로 오히려 관찰 유도에 맞다. */
  SLOT: {
    antler: 'headgear', horn: 'headgear', crest: 'headgear', beard: 'headgear',
    quills: 'attach', patagium: 'attach', fins: 'attach', dewlap: 'attach'
  },
  slotOf: function (p) { return this.SLOT[p] || p; },

  /* 어떤 종이 주어진 슬롯에서 내놓을 수 있는 부품 이름 */
  partFor: function (spec, slot) {
    var self = this;
    var order = ZZL.puzzleOrder(spec.model);
    for (var i = 0; i < order.length; i++) {
      if (self.slotOf(order[i]) === slot) return order[i];
    }
    return null;
  },

  make: function (spec, all, parts) {
    var self = this;
    var order = ZZL.puzzleOrder(spec.model).slice(0, parts || 99);
    order = order.filter(function (p) {
      return p === 'head' || p === 'body' || spec.model[p] !== undefined;
    });
    var rivals = (spec.rivals || []).map(function (n) {
      return all.filter(function (s) { return s.kname === n; })[0];
    }).filter(Boolean);
    /* 근연종이 부족하면 같은 구역의 다른 종으로 보충 */
    all.forEach(function (s) {
      if (rivals.length >= 4) return;
      if (s.id !== spec.id && s.zone === spec.zone && rivals.indexOf(s) < 0) rivals.push(s);
    });

    return order.map(function (p) {
      var slot = self.slotOf(p);
      var wrong = [];
      function tryAdd(s) {
        if (wrong.length >= 2) return;
        if (s.id === spec.id) return;
        if (wrong.some(function (w) { return w.spec.id === s.id; })) return;
        var part = self.partFor(s, slot);
        if (part) wrong.push({ spec: s, part: part });
      }
      rivals.forEach(tryAdd);                                  /* ① 근연종 우선 */
      all.forEach(function (s) { if (s.zone === spec.zone) tryAdd(s); });  /* ② 같은 구역 */
      all.forEach(tryAdd);                                     /* ③ 그래도 모자라면 전체 */

      var opts = [{ spec: spec, part: p, ok: true }]
        .concat(wrong.map(function (w) { return { spec: w.spec, part: w.part, ok: false }; }));
      for (var j = opts.length - 1; j > 0; j--) {
        var k = Math.floor(Math.random() * (j + 1));
        var t = opts[j]; opts[j] = opts[k]; opts[k] = t;
      }
      return { part: p, slot: slot, options: opts };
    });
  },
};

global.ZDX = ZDX;
})(typeof window !== 'undefined' ? window : globalThis);
