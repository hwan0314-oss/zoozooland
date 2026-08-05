/* ============================================================
   ZZL BLOCK PARTS LIBRARY  v1.0
   쥬쥬랜드 동물도감 · 레고 블록형 3D 부품 라이브러리

   의존: three.js r128 (전역 THREE)
   사용: const model = ZZL.build(spec);  scene.add(model.root);

   설계 원칙
   - 모든 동물은 이 파일의 부품 조합으로만 만든다
   - 부품은 상자·원기둥·원뿔만 사용 (레고 호환 형태)
   - 종 구분은 색이 아니라 형태를 1순위로 한다
   - 각 부품은 정면 렌더 PNG로 뽑아 퍼즐 선택지에 그대로 쓴다
   ============================================================ */
(function (global) {
'use strict';

var ZZL = {};

/* ── 재질 ────────────────────────────────────────── */
var _matCache = {};
function mat(color) {
  if (!_matCache[color]) {
    _matCache[color] = new THREE.MeshStandardMaterial({
      color: color, roughness: 0.34, metalness: 0
    });
  }
  return _matCache[color];
}
ZZL.mat = mat;

/* ── 기본 도형 ───────────────────────────────────── */
function box(w, h, d, color, x, y, z) {
  var m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat(color));
  m.position.set(x || 0, y || 0, z || 0);
  m.castShadow = m.receiveShadow = true;
  return m;
}
function cyl(rt, rb, h, color, x, y, z, seg) {
  var m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg || 10), mat(color));
  m.position.set(x || 0, y || 0, z || 0);
  m.castShadow = m.receiveShadow = true;
  return m;
}
function cone(r, h, color, x, y, z, seg) {
  var m = new THREE.Mesh(new THREE.ConeGeometry(r, h, seg || 6), mat(color));
  m.position.set(x || 0, y || 0, z || 0);
  m.castShadow = m.receiveShadow = true;
  return m;
}
ZZL.box = box; ZZL.cyl = cyl; ZZL.cone = cone;

/* ── 레고 돌기(스터드) ───────────────────────────── */
function studs(parent, color, cols, rows, gapX, gapZ, y, z0, r) {
  r = r || 0.17;
  var g = new THREE.CylinderGeometry(r, r, 0.13, 10);
  for (var i = 0; i < cols; i++) for (var j = 0; j < rows; j++) {
    var m = new THREE.Mesh(g, mat(color));
    m.position.set((i - (cols - 1) / 2) * gapX, y, (z0 || 0) + (j - (rows - 1) / 2) * gapZ);
    m.castShadow = m.receiveShadow = true;
    parent.add(m);
  }
}
ZZL.studs = studs;

/* ── 눈 (픽셀형 · 블록 캐릭터 표준) ──────────────── */
function pixEye(size, dark) {
  var g = new THREE.Group();
  var w = box(size, size, 0.08, 0xFFFFFF);
  var p = box(size * 0.5, size * 0.62, 0.09, dark || 0x1A1E20, 0, 0, 0.02);
  g.add(w, p);
  g.userData.white = w;
  return g;
}
ZZL.pixEye = pixEye;

/* ============================================================
   PARTS — 부위별 부품
   각 함수는 THREE.Group을 돌려주며, 원점은 부착 지점(소켓)이다.
   ============================================================ */
var PARTS = {};

/* ── 몸통 ────────────────────────────────────────── */
PARTS.body = {
  /* 4족 보행형: 알파카·사슴·염소·라쿤 등 */
  quad: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    if (o.belly) g.add(box(o.w * 0.9, o.h * 0.2, o.d * 0.9, o.belly, 0, -o.h / 2 + 0.02, 0));
    if (o.studs !== false) studs(g, o.dark || o.color, o.sc || 2, o.sr || 3, o.w * 0.4, o.d * 0.3, o.h / 2 + 0.06, 0);
    return g;
  },
  /* 직립형: 미어캣·프레리독 */
  upright: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    if (o.belly) g.add(box(o.w * 0.7, o.h * 0.7, 0.12, o.belly, 0, -o.h * 0.05, o.d / 2 + 0.01));
    return g;
  },
  /* 조류형: 앵무·에뮤 */
  bird: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    if (o.belly) g.add(box(o.w * 0.75, o.h * 0.8, 0.14, o.belly, 0, -o.h * 0.04, o.d / 2 + 0.01));
    return g;
  },
  /* 납작 장동형: 악어·도마뱀 */
  lowLong: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    if (o.belly) g.add(box(o.w * 0.9, o.h * 0.25, o.d * 0.9, o.belly, 0, -o.h / 2 + 0.03, 0));
    if (o.crest) for (var i = 0; i < 5; i++)
      g.add(box(0.12, 0.2 - i * 0.02, 0.12, o.crest, 0, o.h / 2 + 0.09, o.d * 0.3 - i * (o.d * 0.17)));
    if (o.studs) studs(g, o.dark || o.color, 1, 3, 0, o.d * 0.28, o.h / 2 + 0.06, 0);
    return g;
  },
  /* 등딱지형: 거북 */
  shell: function (o) {
    var g = new THREE.Group();
    var dome = cyl(o.w * 0.42, o.w * 0.5, o.h, o.color, 0, 0, 0, o.seg || 8);
    g.add(dome);
    g.add(cyl(o.w * 0.5, o.w * 0.5, o.h * 0.28, o.dark || o.color, 0, -o.h * 0.5, 0, o.seg || 8));
    /* 등딱지 판 (스쿠트) */
    var n = o.scutes || 6;
    for (var i = 0; i < n; i++) {
      var a = (i / n) * Math.PI * 2;
      g.add(box(o.w * 0.2, 0.09, o.w * 0.2, o.dark || o.color,
        Math.cos(a) * o.w * 0.26, o.h * 0.5, Math.sin(a) * o.w * 0.26));
    }
    if (o.top) g.add(box(o.w * 0.24, 0.09, o.w * 0.24, o.dark || o.color, 0, o.h * 0.5, 0));
    return g;
  },
  /* 납작 등딱지: 마타마타·늑대거북 */
  shellFlat: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    var n = o.rows || 3;
    for (var i = 0; i < n; i++)
      for (var j = -1; j < 2; j++)
        g.add(box(o.w * 0.22, 0.1, o.d * 0.2, o.dark || o.color,
          j * o.w * 0.3, o.h / 2 + 0.04, (i - (n - 1) / 2) * o.d * 0.3));
    return g;
  },
  /* 뱀 — 다리 없이 이어지는 마디. 굵기로 종을 가른다 */
  serpent: function (o) {
    var g = new THREE.Group();
    var n = o.count || 7, segs = [];
    var p = g;
    for (var i = 0; i < n; i++) {
      var s = new THREE.Group();
      s.position.set(0, 0, i === 0 ? 0 : -o.seg);
      var k = 1 - Math.pow(i / n, 1.6) * 0.55;
      s.add(box(o.w * k, o.h * k, o.seg * 1.02, i % 2 ? (o.dark || o.color) : o.color, 0, 0, -o.seg / 2));
      if (o.tipColor && i >= n - 2)
        s.add(box(o.w * k * 1.01, o.h * k * 1.01, o.seg * 0.5, o.tipColor, 0, 0, -o.seg * 0.75));
      p.add(s); p = s; segs.push(s);
    }
    g.userData.segs = segs;
    return g;
  },
  /* 물고기 */
  fish: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    if (o.belly) g.add(box(o.w * 0.9, o.h * 0.24, o.d * 0.9, o.belly, 0, -o.h / 2 + 0.03, 0));
    return g;
  },
  /* 개구리·도롱뇽 — 앉은 자세의 납작 몸통 */
  frog: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    if (o.belly) g.add(box(o.w * 0.82, o.h * 0.34, 0.12, o.belly, 0, -o.h * 0.2, o.d / 2 + 0.01));
    if (o.dots) for (var i = 0; i < 5; i++)
      g.add(box(0.1, 0.05, 0.1, o.dots,
        (i % 2 ? 1 : -1) * o.w * 0.22, o.h / 2 + 0.02, (i - 2) * o.d * 0.2));
    return g;
  }
};

/* ── 머리 ────────────────────────────────────────── */
PARTS.head = {
  /* 기본 상자 머리 (+선택적 짧은 주둥이) */
  box: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    if (o.studs) studs(g, o.dark || o.color, 2, 1, o.w * 0.42, 0, o.h / 2 + 0.06, -o.d * 0.15);
    if (o.muzzle) {
      var m = o.muzzle;
      g.add(box(m.w, m.h, m.d, m.color || o.color, 0, m.y || -o.h * 0.22, o.d / 2 + m.d / 2 - 0.02));
      g.add(box(m.w * 0.34, 0.07, 0.1, o.nose || 0x2A2A2E, 0,
        (m.y || -o.h * 0.22) + m.h * 0.28, o.d / 2 + m.d - 0.02));
    }
    return g;
  },
  /* 긴 주둥이: 알파카·라마·사슴·말 */
  muzzle: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    var m = o.muzzle || {};
    var mw = m.w || o.w * 0.6, mh = m.h || o.h * 0.55, md = m.d || o.d * 0.5;
    g.add(box(mw, mh, md, m.color || o.color, 0, m.y || -o.h * 0.2, o.d / 2 + md / 2 - 0.02));
    g.add(box(mw * 0.36, 0.06, 0.1, o.nose || 0x453A2F, 0,
      (m.y || -o.h * 0.2) + mh * 0.2, o.d / 2 + md - 0.02));
    if (o.mouth) g.add(box(mw * 0.7, 0.06, 0.1, o.nose || 0x453A2F, 0,
      (m.y || -o.h * 0.2) - mh * 0.34, o.d / 2 + md - 0.04));
    return g;
  },
  /* 뾰족한 주둥이: 여우·미어캣·라쿤·코아티 */
  snout: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    var len = o.snoutLen || o.d * 0.55;
    var s = new THREE.Mesh(new THREE.CylinderGeometry(o.w * 0.34, o.w * 0.13, len, 4), mat(o.snoutColor || o.color));
    s.rotation.x = Math.PI / 2; s.rotation.y = Math.PI / 4;
    s.position.set(0, -o.h * 0.16, o.d / 2 + len / 2 - 0.04);
    s.castShadow = true; g.add(s);
    g.add(box(0.11, 0.09, 0.09, o.nose || 0x2A2A2E, 0, -o.h * 0.16, o.d / 2 + len - 0.06));
    if (o.mask) { /* 눈가 마스크: 라쿤·페럿 */
      g.add(box(o.w * 1.02, o.h * 0.26, 0.06, o.mask, 0, o.h * 0.06, o.d / 2 + 0.01));
    }
    return g;
  },
  /* 넓적 주둥이: 악어 */
  croc: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    if (o.studs !== false) studs(g, o.dark || o.color, 2, 1, o.w * 0.45, 0, o.h / 2 + 0.06, -o.d * 0.12);
    var s = o.snout || {};
    var sw = s.w || o.w * 0.78, sh = s.h || o.h * 0.45, sd = s.d || o.d * 1.2;
    g.add(box(sw, sh, sd, o.color, 0, -o.h * 0.1, o.d / 2 + sd / 2 - 0.02));
    /* 아래턱 (별도 그룹: 애니메이션용) */
    var jaw = new THREE.Group();
    jaw.position.set(0, -o.h * 0.32, o.d * 0.4);
    jaw.add(box(sw * 0.94, sh * 0.6, sd, o.dark || o.color, 0, 0, sd / 2));
    g.add(jaw); g.userData.jaw = jaw;
    /* 이빨 */
    var tn = o.teeth || 4;
    for (var i = 0; i < tn; i++) {
      var z = o.d / 2 + 0.18 + i * (sd / tn * 0.82);
      g.add(box(0.1, 0.15, 0.1, 0xFFFFFF, sw * 0.42, -o.h * 0.1 - sh * 0.5, z));
      g.add(box(0.1, 0.15, 0.1, 0xFFFFFF, -sw * 0.42, -o.h * 0.1 - sh * 0.5, z));
    }
    g.add(box(0.09, 0.07, 0.07, 0x2C3A22, sw * 0.2, -o.h * 0.1 + sh * 0.4, o.d / 2 + sd - 0.05));
    g.add(box(0.09, 0.07, 0.07, 0x2C3A22, -sw * 0.2, -o.h * 0.1 + sh * 0.4, o.d / 2 + sd - 0.05));
    return g;
  },
  /* 갈고리 부리: 앵무 */
  parrot: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    if (o.studs !== false) studs(g, o.dark || o.color, 2, 1, o.w * 0.44, 0, o.h / 2 + 0.06, -o.d * 0.16);
    if (o.face) g.add(box(o.w * 0.64, o.h * 0.58, 0.12, o.face, 0, -o.h * 0.04, o.d / 2 + 0.01));
    var bk = o.beak || 0x2A2A2E;
    g.add(box(o.w * 0.42, o.h * 0.4, o.d * 0.46, bk, 0, -o.h * 0.11, o.d / 2 + o.d * 0.2));
    g.add(box(o.w * 0.27, o.h * 0.34, o.d * 0.3, bk, 0, -o.h * 0.37, o.d / 2 + o.d * 0.16));
    return g;
  },
  /* 납작 부리: 오리·거위 */
  duck: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    g.add(box(o.w * 0.8, o.h * 0.24, o.d * 0.9, o.beak || 0xE8A93C, 0, -o.h * 0.2, o.d / 2 + o.d * 0.4));
    return g;
  },
  /* 거북 머리 */
  turtle: function (o) {
    var g = new THREE.Group();
    g.add(cyl(o.w * 0.45, o.w * 0.5, o.d, o.color, 0, 0, 0, 8));
    g.children[0].rotation.x = Math.PI / 2;
    g.add(box(o.w * 0.7, o.h * 0.5, o.d * 0.5, o.color, 0, -o.h * 0.1, o.d * 0.4));
    g.add(box(o.w * 0.5, 0.05, 0.12, o.dark || 0x3A3A2E, 0, -o.h * 0.2, o.d * 0.62));
    return g;
  },
  /* 뱀 머리 — 쐐기형 */
  snake: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    g.add(box(o.w * 0.68, o.h * 0.72, o.d * 0.55, o.color, 0, -o.h * 0.06, o.d * 0.72));
    g.add(box(o.w * 0.5, 0.05, 0.14, o.dark || 0x2A2A22, 0, -o.h * 0.3, o.d * 0.8));
    /* 혀 */
    if (o.tongue) {
      g.add(box(0.05, 0.04, o.d * 0.4, o.tongue, 0, -o.h * 0.26, o.d * 1.12));
      g.add(box(0.13, 0.04, 0.09, o.tongue, 0, -o.h * 0.26, o.d * 1.3));
    }
    return g;
  },
  /* 개구리·도롱뇽 머리 — 넓적하고 입이 크다 */
  frog: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    g.add(box(o.w * 0.92, 0.06, o.d * 0.5, o.dark || 0x2A3A28, 0, -o.h * 0.28, o.d * 0.28));
    g.add(box(0.07, 0.05, 0.05, o.dark || 0x2A3A28, o.w * 0.14, o.h * 0.1, o.d * 0.5));
    g.add(box(0.07, 0.05, 0.05, o.dark || 0x2A3A28, -o.w * 0.14, o.h * 0.1, o.d * 0.5));
    return g;
  },
  /* 물고기 머리 — 뾰족한 주둥이 */
  fish: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.d, o.color));
    var sn = o.snoutLen || o.d * 1.4;
    g.add(box(o.w * 0.36, o.h * 0.34, sn, o.dark || o.color, 0, -o.h * 0.06, o.d / 2 + sn / 2));
    g.add(box(o.w * 0.3, 0.05, sn * 0.9, 0xE8E2D2, 0, -o.h * 0.22, o.d / 2 + sn / 2));
    return g;
  }
};

/* ── 목 ──────────────────────────────────────────── */
PARTS.neck = {
  /* 긴 목: 알파카·라마·에뮤·거위 */
  long: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.w, o.color, 0, o.h / 2, 0));
    if (o.collar) g.add(box(o.w * 1.25, o.h * 0.35, o.w * 1.2, o.collar, 0, o.h * 0.22, 0));
    return g;
  },
  /* 짧은 목 (연결부만) */
  short: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.h, o.w, o.color, 0, o.h / 2, 0));
    return g;
  },
  /* 거북 목: 앞으로 뻗음 */
  fwd: function (o) {
    var g = new THREE.Group();
    var m = cyl(o.w * 0.4, o.w * 0.44, o.h, o.color, 0, 0, o.h / 2, 8);
    m.rotation.x = Math.PI / 2; g.add(m);
    return g;
  }
};

/* ── 다리 ────────────────────────────────────────── */
PARTS.legs = {
  /* 원기둥 다리 + 발굽/발 */
  post: function (o) {
    var g = new THREE.Group();
    o.pos.forEach(function (p) {
      var leg = new THREE.Group();
      leg.position.set(p[0], 0, p[1]);
      leg.add(cyl(o.r, o.r * 0.94, o.len, o.color, 0, -o.len / 2, 0, 9));
      if (o.foot === 'hoof') leg.add(cyl(o.r * 1.2, o.r * 1.2, 0.16, o.footColor || 0x453A2F, 0, -o.len - 0.06, 0, 9));
      else if (o.foot === 'paw') leg.add(box(o.r * 2.6, 0.13, o.r * 3.2, o.footColor || o.color, 0, -o.len - 0.05, o.r * 0.5));
      else if (o.foot === 'claw') {
        leg.add(box(o.r * 2.8, 0.13, o.r * 3.4, o.footColor || o.color, 0, -o.len - 0.05, o.r * 0.6));
        for (var i = -1; i < 2; i++)
          leg.add(box(0.08, 0.09, 0.16, o.clawColor || 0xE8E2D2, i * o.r * 0.9, -o.len - 0.05, o.r * 2.1));
      }
      if (o.fluff) leg.add(box(o.r * 2.6, o.r * 2.6, o.r * 2.6, o.fluff, 0, -o.len * 0.12, 0));
      g.add(leg);
    });
    return g;
  },
  /* 짧고 굵은 기둥: 설가타·코끼리형 */
  column: function (o) {
    var g = new THREE.Group();
    o.pos.forEach(function (p) {
      var leg = new THREE.Group();
      leg.position.set(p[0], 0, p[1]);
      leg.add(cyl(o.r, o.r * 1.15, o.len, o.color, 0, -o.len / 2, 0, 8));
      leg.add(box(o.r * 2.4, 0.14, o.r * 2.6, o.footColor || o.color, 0, -o.len - 0.05, 0));
      g.add(leg);
    });
    return g;
  },
  /* 조류 다리 */
  bird: function (o) {
    var g = new THREE.Group();
    o.pos.forEach(function (p) {
      var leg = new THREE.Group();
      leg.position.set(p[0], 0, p[1]);
      leg.add(cyl(o.r, o.r, o.len, o.color, 0, -o.len / 2, 0, 8));
      leg.add(box(o.r * 3.4, 0.11, o.r * 4.6, o.color, 0, -o.len - 0.04, o.r * 1.2));
      g.add(leg);
    });
    return g;
  },
  /* 도마뱀·악어형 벌어진 다리 */
  sprawl: function (o) {
    var g = new THREE.Group();
    o.pos.forEach(function (p) {
      var leg = new THREE.Group();
      leg.position.set(p[0], 0, p[1]);
      leg.rotation.z = p[0] > 0 ? -0.3 : 0.3;
      leg.add(cyl(o.r, o.r * 0.9, o.len, o.color, 0, -o.len / 2, 0, 8));
      leg.add(box(o.r * 3, 0.12, o.r * 3.4, o.color, 0, -o.len - 0.04, o.r * 0.6));
      g.add(leg);
    });
    return g;
  },
  /* 개구리 — 접힌 뒷다리 + 물갈퀴 발 */
  frog: function (o) {
    var g = new THREE.Group();
    /* 앞다리 */
    [[o.fw, o.fz], [-o.fw, o.fz]].forEach(function (p) {
      var leg = new THREE.Group();
      leg.position.set(p[0], 0, p[1]);
      leg.add(cyl(o.r * 0.8, o.r * 0.7, o.len * 0.8, o.color, 0, -o.len * 0.4, 0, 7));
      leg.add(box(o.r * 2.4, 0.1, o.r * 2.8, o.color, 0, -o.len * 0.8, o.r * 0.7));
      g.add(leg);
    });
    /* 뒷다리 — 옆으로 접힘 */
    [[o.bw, o.bz, 1], [-o.bw, o.bz, -1]].forEach(function (p) {
      var leg = new THREE.Group();
      leg.position.set(p[0], 0, p[1]);
      leg.rotation.z = p[2] * 0.5;
      leg.add(box(o.r * 2.2, o.r * 1.6, o.len * 1.1, o.color, 0, 0, -o.len * 0.3));
      leg.add(cyl(o.r * 0.8, o.r * 0.7, o.len * 0.9, o.color, p[2] * o.r * 0.6, -o.len * 0.45, 0, 7));
      leg.add(box(o.r * 3, 0.1, o.r * 3.6, o.web || o.color, p[2] * o.r * 0.6, -o.len * 0.88, o.r * 1.0));
      g.add(leg);
    });
    return g;
  }
};

/* ── 꼬리 ────────────────────────────────────────── */
PARTS.tail = {
  none: function () { return new THREE.Group(); },
  /* 마디형(휘어짐): 악어·도마뱀 */
  segment: function (o) {
    var g = new THREE.Group(); var segs = [], p = g;
    var n = o.count || 3;
    for (var i = 0; i < n; i++) {
      var s = new THREE.Group();
      s.position.set(0, 0, i === 0 ? 0 : -(o.len / n) * 0.95);
      var w = o.w * (1 - i / (n + 1)), h = o.h * (1 - i / (n + 1));
      s.add(box(w, h, o.len / n, i % 2 ? (o.dark || o.color) : o.color, 0, 0, -(o.len / n) / 2));
      if (o.crest && i < n - 1) s.add(box(0.1, 0.14, 0.1, o.crest, 0, h / 2 + 0.06, -(o.len / n) / 2));
      p.add(s); p = s; segs.push(s);
    }
    g.userData.segs = segs;
    return g;
  },
  /* 덤불 꼬리: 여우·라쿤·다람쥐 */
  bushy: function (o) {
    var g = new THREE.Group();
    var n = o.rings || 4;
    for (var i = 0; i < n; i++) {
      var c = (o.stripe && i % 2) ? o.stripe : o.color;
      g.add(box(o.w * (1 - i * 0.08), o.w * (1 - i * 0.08), o.len / n, c, 0, i * 0.04, -(o.len / n) * (i + 0.5)));
    }
    if (o.tip) g.add(box(o.w * 0.66, o.w * 0.66, o.len / n * 0.7, o.tip, 0, n * 0.04, -o.len - 0.08));
    return g;
  },
  /* 뭉치: 토끼·알파카 */
  tuft: function (o) {
    var g = new THREE.Group();
    g.add(box(o.w, o.w, o.w * 0.8, o.color, 0, 0, -o.w * 0.4));
    return g;
  },
  /* 깃털 부채: 앵무 */
  feather: function (o) {
    var g = new THREE.Group();
    g.rotation.x = o.tilt === undefined ? -0.35 : o.tilt;
    [[-o.w * 0.32, o.dark || o.color], [0, o.color], [o.w * 0.32, o.dark || o.color]].forEach(function (q) {
      g.add(box(o.w * 0.3, 0.1, o.len, q[1], q[0], 0, -o.len / 2));
    });
    return g;
  },
  /* 가늘고 긴: 원숭이·제넷 */
  thin: function (o) {
    var g = new THREE.Group(); var segs = [], p = g;
    var n = o.count || 4;
    for (var i = 0; i < n; i++) {
      var s = new THREE.Group();
      s.position.set(0, i === 0 ? 0 : 0.06, i === 0 ? 0 : -(o.len / n));
      var c = (o.stripe && i % 2) ? o.stripe : o.color;
      s.add(cyl(o.r * (1 - i * 0.1), o.r * (1 - i * 0.14), o.len / n, c, 0, 0, -(o.len / n) / 2, 7));
      s.children[0].rotation.x = Math.PI / 2;
      p.add(s); p = s; segs.push(s);
    }
    g.userData.segs = segs;
    return g;
  },
  /* 짧은 판: 거북 */
  stub: function (o) {
    var g = new THREE.Group();
    g.add(cone(o.r, o.len, o.color, 0, 0, -o.len / 2, 5));
    g.children[0].rotation.x = -Math.PI / 2;
    return g;
  }
};

/* ── 귀 ──────────────────────────────────────────── */
PARTS.ears = {
  none: function () { return new THREE.Group(); },
  /* 긴 귀: 토끼·나귀 */
  long: function (o) {
    var g = new THREE.Group(); var L = [];
    [1, -1].forEach(function (s) {
      var e = new THREE.Group();
      e.position.set(s * o.gap, 0, 0); e.rotation.z = s * (o.spread || 0.12);
      e.add(box(o.w, o.len, o.w * 0.5, o.color, 0, o.len / 2, 0));
      if (o.inner) e.add(box(o.w * 0.5, o.len * 0.72, 0.06, o.inner, 0, o.len / 2, o.w * 0.26));
      g.add(e); L.push(e);
    });
    g.userData.ears = L;
    return g;
  },
  /* 바나나형 (앞뒤로 휨): 라마 */
  banana: function (o) {
    var g = new THREE.Group(); var L = [];
    [1, -1].forEach(function (s) {
      var e = new THREE.Group();
      e.position.set(s * o.gap, 0, 0); e.rotation.z = s * 0.3; e.rotation.x = -0.2;
      e.add(box(o.w, o.len * 0.6, o.w * 0.5, o.color, 0, o.len * 0.3, 0));
      e.add(box(o.w * 0.8, o.len * 0.5, o.w * 0.5, o.color, 0, o.len * 0.78, -o.w * 0.22));
      g.add(e); L.push(e);
    });
    g.userData.ears = L;
    return g;
  },
  /* 삼각 귀: 알파카·염소·사슴 */
  point: function (o) {
    var g = new THREE.Group(); var L = [];
    [1, -1].forEach(function (s) {
      var e = new THREE.Group();
      e.position.set(s * o.gap, 0, 0); e.rotation.z = s * (o.spread || 0.22);
      e.add(cone(o.w, o.len, o.color, 0, o.len / 2, 0, 5));
      g.add(e); L.push(e);
    });
    g.userData.ears = L;
    return g;
  },
  /* 크고 넓은 귀: 사막여우 */
  big: function (o) {
    var g = new THREE.Group(); var L = [];
    [1, -1].forEach(function (s) {
      var e = new THREE.Group();
      e.position.set(s * o.gap, 0, 0); e.rotation.z = s * (o.spread || 0.3);
      e.add(box(o.w, o.len, o.w * 0.4, o.color, 0, o.len / 2, 0));
      if (o.inner) e.add(box(o.w * 0.6, o.len * 0.7, 0.06, o.inner, 0, o.len * 0.46, o.w * 0.21));
      g.add(e); L.push(e);
    });
    g.userData.ears = L;
    return g;
  },
  /* 작고 둥근 귀: 라쿤·미어캣·원숭이 */
  round: function (o) {
    var g = new THREE.Group(); var L = [];
    [1, -1].forEach(function (s) {
      var e = new THREE.Group();
      e.position.set(s * o.gap, 0, 0);
      e.add(cyl(o.w, o.w, 0.12, o.color, 0, 0, 0, 8));
      e.children[0].rotation.x = Math.PI / 2;
      if (o.inner) e.add(cyl(o.w * 0.55, o.w * 0.55, 0.13, o.inner, 0, 0, 0.02, 8)),
        e.children[1].rotation.x = Math.PI / 2;
      g.add(e); L.push(e);
    });
    g.userData.ears = L;
    return g;
  }
};

/* ── 부속 ────────────────────────────────────────── */
PARTS.extra = {
  /* 뿔 — 형태로 종을 가른다 */
  hornSpiral: function (o) {   /* 무플론: 크게 말린 나선 */
    var g = new THREE.Group();
    [1, -1].forEach(function (s) {
      var h = new THREE.Group(); h.position.set(s * o.gap, 0, 0);
      for (var i = 0; i < 6; i++) {
        var a = i * 0.9;
        h.add(box(o.w, o.w, o.w, o.color,
          s * Math.sin(a) * o.r * 0.5, Math.cos(a) * o.r * 0.4 + o.r * 0.3, -Math.sin(a) * o.r * 0.45));
      }
      g.add(h);
    });
    return g;
  },
  hornBack: function (o) {     /* 염소·산양: 뒤로 굽음 */
    var g = new THREE.Group();
    [1, -1].forEach(function (s) {
      var h = new THREE.Group(); h.position.set(s * o.gap, 0, 0);
      for (var i = 0; i < 4; i++)
        h.add(box(o.w * (1 - i * 0.12), o.w * (1 - i * 0.12), o.w, o.color,
          0, o.len * (i * 0.24), -o.len * (i * 0.2)));
      g.add(h);
    });
    return g;
  },
  hornShort: function (o) {    /* 보어염소: 짧은 뿔 */
    var g = new THREE.Group();
    [1, -1].forEach(function (s) {
      g.add(cone(o.w, o.len, o.color, s * o.gap, o.len / 2, -o.w, 5));
    });
    return g;
  },
  antler: function (o) {       /* 꽃사슴: 가지뿔 */
    var g = new THREE.Group();
    [1, -1].forEach(function (s) {
      var h = new THREE.Group(); h.position.set(s * o.gap, 0, 0); h.rotation.z = s * 0.24;
      h.add(box(o.w, o.len, o.w, o.color, 0, o.len / 2, 0));
      h.add(box(o.w * 0.8, o.len * 0.5, o.w * 0.8, o.color, s * o.len * 0.22, o.len * 0.82, 0));
      h.add(box(o.w * 0.8, o.len * 0.4, o.w * 0.8, o.color, 0, o.len * 0.9, -o.len * 0.22));
      g.add(h);
    });
    return g;
  },
  crest: function (o) {        /* 앵무 볏 */
    var g = new THREE.Group();
    [-1, 0, 1].forEach(function (i) {
      var c = box(o.w, o.len, o.w * 0.8, o.color, i * o.gap, o.len / 2, 0);
      c.rotation.x = -0.32; g.add(c);
    });
    return g;
  },
  wings: function (o) {        /* 날개 (애니메이션 대상) */
    var g = new THREE.Group(); var W = [];
    [1, -1].forEach(function (s) {
      var w = new THREE.Group(); w.position.set(s * o.gap, 0, 0);
      w.add(box(o.w, o.len, o.d, o.color, 0, -o.len / 2, 0));
      if (o.tip) w.add(box(o.w * 1.02, o.len * 0.34, o.d * 0.9, o.tip, 0, -o.len - o.len * 0.14, -0.02));
      g.add(w); W.push(w);
    });
    g.userData.wings = W;
    return g;
  },
  quills: function (o) {       /* 등가시: 고슴도치·호저 (tiltZ로 측면 가시 방향 제어) */
    var g = new THREE.Group();
    var tz = o.tiltZ !== undefined ? o.tiltZ : 0;
    for (var i = 0; i < (o.count || 12); i++) {
      var px = (Math.random() - 0.5) * o.w, pz = (Math.random() - 0.5) * o.d;
      var q = cone(o.r, o.len, o.color, px, 0, pz, 4);
      q.rotation.x = -0.3 + Math.random() * 0.6;
      q.rotation.z = tz + (Math.random() - 0.5) * 0.5;
      g.add(q);
    }
    return g;
  },
  dewlap: function (o) {       /* 목주름: 이구아나·테구 */
    var g = new THREE.Group();
    g.add(box(o.w, o.len, o.d, o.color, 0, -o.len / 2, 0));
    return g;
  },
  spots: function (o) {        /* 반점: 꽃사슴 */
    var g = new THREE.Group();
    (o.at || []).forEach(function (p) {
      g.add(box(o.size, 0.05, o.size, o.color, p[0], p[1], p[2]));
    });
    return g;
  },
  fins: function (o) {         /* 지느러미: 물고기 */
    var g = new THREE.Group();
    /* 등지느러미 */
    if (o.dorsal) g.add(box(0.08, o.h, o.d, o.color, 0, o.h / 2, o.dz || 0));
    /* 가슴지느러미 */
    [1, -1].forEach(function (s) {
      var f = box(0.07, o.h * 0.5, o.d * 0.5, o.color, s * o.gap, 0, 0);
      f.rotation.z = s * 0.4; g.add(f);
    });
    /* 꼬리지느러미 */
    if (o.caudal) g.add(box(0.08, o.h * 1.2, o.d * 0.7, o.color, 0, 0, o.cz));
    return g;
  },
  arms: function (o) {         /* 팔: 원숭이 — ㄴ자 위로 들기 */
    var uLen = o.upperLen || o.len * 0.46;
    var fLen = o.foreLen || o.len * 0.54;
    var g = new THREE.Group();
    [1, -1].forEach(function (s) {
      var shou = new THREE.Group();
      shou.position.set(s * o.gap, 0, o.z || 0);
      /* 위팔: X축 방향으로 수평 뻗기 */
      var ua = cyl(o.r, o.r * 0.88, uLen, o.color, 0, 0, 0, 7);
      ua.position.x = s * uLen / 2;
      ua.rotation.z = -s * Math.PI / 2;
      shou.add(ua);
      /* 아래팔: 팔꿈치에서 위로 뻗기 */
      var elb = new THREE.Group();
      elb.position.set(s * uLen, 0, 0);
      elb.add(cyl(o.r * 0.88, o.r * 0.74, fLen, o.color, 0, fLen / 2, 0, 7));
      elb.add(box(o.r * 2.4, 0.12, o.r * 2.4, o.handColor || o.color, 0, fLen + 0.06, 0));
      shou.add(elb);
      g.add(shou);
    });
    return g;
  },
  patagium: function (o) {     /* 비막: 슈가글라이더 */
    var g = new THREE.Group();
    [1, -1].forEach(function (s) {
      var m = box(o.w, 0.07, o.d, o.color, s * o.gap, 0, 0);
      m.rotation.z = s * 0.28; g.add(m);
    });
    return g;
  },
  pouchEye: function (o) {     /* 눈가 줄무늬: 슈가글라이더·페럿 */
    var g = new THREE.Group();
    g.add(box(o.w, o.h, 0.06, o.color, 0, 0, o.z || 0));
    return g;
  }
};

ZZL.PARTS = PARTS;

/* ============================================================
   BUILD — 조립 엔진
   spec을 받아 {root, update, react, rest, parts} 를 돌려준다.
   parts 는 퍼즐용 부위별 그룹 참조 (개별 렌더/하이라이트에 사용)
   ============================================================ */
ZZL.build = function (spec) {
  var root = new THREE.Group();
  var body = new THREE.Group();
  root.add(body);

  var parts = {};   /* 부위명 -> Group (퍼즐 단위) */
  var eyes = [];
  var anim = spec.anim || {};

  /* 몸통 */
  var b = spec.body;
  var bodyG = PARTS.body[b.type](b);
  bodyG.position.set(0, b.y, b.z || 0);
  body.add(bodyG);
  parts.body = bodyG;

  /* 목 + 머리
     머리 좌표는 몸통 공간의 절대값으로 해석한다.
     목이 있는 종만 목 끝을 기준으로 상대 배치한다. */
  var headHost = body, headBaseY = 0, headBaseZ = 0;
  if (spec.neck) {
    var n = spec.neck;
    var neckG = PARTS.neck[n.type](n);
    neckG.position.set(0, n.y, n.z);
    body.add(neckG);
    parts.neck = neckG;
    headHost = neckG; headBaseY = 0; headBaseZ = 0;
  }
  var h = spec.head;
  var headPivot = new THREE.Group();
  headPivot.position.set(0, headBaseY + h.y, headBaseZ + h.z);
  headHost.add(headPivot);
  var headG = PARTS.head[h.type](h);
  headPivot.add(headG);
  parts.head = headG;
  if (headG.userData.jaw) parts.jaw = headG.userData.jaw;

  /* 눈 */
  if (spec.eyes) {
    var e = spec.eyes;
    [1, -1].forEach(function (s) {
      var eye = pixEye(e.size, e.dark);
      eye.position.set(s * e.gap, e.y, e.z);
      if (e.side) eye.rotation.y = s * (Math.PI / 2);
      else if (e.turn) eye.rotation.y = s * e.turn;
      headG.add(eye); eyes.push(eye);
    });
  }

  /* 귀 */
  if (spec.ears) {
    var earG = PARTS.ears[spec.ears.type](spec.ears);
    earG.position.set(0, spec.ears.y, spec.ears.z || 0);
    headG.add(earG);
    parts.ears = earG;
  }

  /* 다리 */
  if (spec.legs) {
    var lg = PARTS.legs[spec.legs.type](spec.legs);
    lg.position.set(0, spec.legs.y, 0);
    body.add(lg);
    parts.legs = lg;
  }

  /* 꼬리 */
  if (spec.tail) {
    var t = spec.tail;
    var tg = PARTS.tail[t.type](t);
    tg.position.set(0, t.y, t.z);
    body.add(tg);
    parts.tail = tg;
  }

  /* 부속 */
  var extras = {};
  (spec.extras || []).forEach(function (x) {
    var g = PARTS.extra[x.type](x);
    g.position.set(x.x || 0, x.y, x.z || 0);
    var host = x.on === 'head' ? headG : (x.on === 'neck' && parts.neck ? parts.neck : body);
    host.add(g);
    extras[x.name || x.type] = g;
    if (x.puzzle !== false) parts[x.name || x.type] = g;
  });

  root.scale.setScalar(spec.scale || 1);

  /* 접지 정렬 — 조립 결과의 최저점을 y=0 에 맞춘다.
     사양에 미세한 높이 오차가 있어도 발이 뜨거나 파묻히지 않는다. */
  if (spec.groundAlign !== false) {
    root.updateMatrixWorld(true);
    var bb = new THREE.Box3().setFromObject(root);
    if (isFinite(bb.min.y)) body.position.y -= bb.min.y / (spec.scale || 1);
  }

  /* 측정값 — 카메라 프레이밍과 퍼즐 배치에 사용 */
  root.updateMatrixWorld(true);
  var mb = new THREE.Box3().setFromObject(root);
  var msz = new THREE.Vector3(), mct = new THREE.Vector3();
  mb.getSize(msz); mb.getCenter(mct);

  /* ── 애니메이션 ── */
  var jaw = parts.jaw;
  var wings = extras.wings && extras.wings.userData.wings;
  var earList = parts.ears && parts.ears.userData.ears;
  var tailSegs = parts.tail && parts.tail.userData.segs;
  var neckG2 = parts.neck;

  var bodyRestY = bodyG.position.y;

  function update(t) {
    if (root.userData.assembling) return;   /* 조립 연출 중에는 기본 모션 정지 */
    var bob = anim.bob === undefined ? 0.04 : anim.bob;
    bodyG.position.y = bodyRestY + Math.sin(t * (anim.bobSpeed || 1.6)) * bob;

    if (anim.headTurn !== false) {
      headPivot.rotation.y = Math.sin(t * (anim.turnSpeed || 0.45)) * (anim.headTurn || 0.28);
    }
    if (anim.headBob) {
      var c = (t * anim.headBob.rate) % 1;
      var k = c < 0.24 ? Math.max(0, Math.sin(c / 0.24 * Math.PI * 3)) * anim.headBob.amt : 0;
      headPivot.rotation.x = -k;
      if (extras.dewlap) extras.dewlap.scale.set(1, 1 + k * 0.4, 1 + k * 1.2);
    }
    if (anim.jerk) {   /* 앵무 특유의 끊기는 목 동작 */
      var j = (t * anim.jerk) % 1;
      headPivot.rotation.z = j < 0.13 ? 0.3 : (j < 0.26 ? -0.24 : 0);
    }
    if (neckG2 && anim.neckSway) {
      neckG2.rotation.x = Math.sin(t * 0.85) * anim.neckSway;
      neckG2.rotation.z = Math.sin(t * 0.6) * anim.neckSway * 0.8;
    }
    if (jaw && anim.jaw) {
      var jc = (t * anim.jaw) % 1;
      jaw.rotation.x = jc < 0.13 ? Math.sin(jc / 0.13 * Math.PI) * 0.36 : 0;
    }
    if (wings && anim.flap) {
      var f = ((t * anim.flap) % 1) < 0.09 ? Math.abs(Math.sin(t * 20)) * 0.5 : 0;
      wings[0].rotation.z = -0.08 - f; wings[1].rotation.z = 0.08 + f;
    }
    if (earList && anim.earTwitch) {
      var tw = ((t * 0.33) % 1) < 0.07 ? Math.sin(t * 24) * 0.26 : 0;
      earList[0].rotation.z += 0; /* 기준 회전 유지 */
      earList[0].rotation.x = tw; earList[1].rotation.x = -tw * 0.7;
    }
    if (tailSegs && anim.tailWave) {
      for (var i = 0; i < tailSegs.length; i++)
        tailSegs[i].rotation.y = Math.sin(t * 1.6 - i * 0.6) * (anim.tailWave + i * 0.02);
    }
    var bl = ((t * (anim.blink || 0.5)) % 1) < 0.05 ? 0.1 : 1;
    for (var k2 = 0; k2 < eyes.length; k2++) eyes[k2].userData.white.scale.y = bl;
  }

  function react(k) {
    root.position.y = Math.abs(Math.sin(k * Math.PI * 2)) * (anim.hop || 0.45);
    if (wings) { wings[0].rotation.z = -0.95; wings[1].rotation.z = 0.95; }
    if (jaw) jaw.rotation.x = 0.5;
  }
  function rest() { root.position.y = 0; }

  return {
    root: root, update: update, react: react, rest: rest,
    parts: parts, spec: spec,
    size: msz, center: mct, footR: Math.max(msz.x, msz.z) / 2
  };
};

/* ============================================================
   ASSEMBLY — 조립 연출
   부품이 제각각 흩어진 자리에서 튀어나왔다가(뿅) 한꺼번에
   빨려들어와 제자리에 꽂히는(척) 연출.

     var A = ZZL.assembly(model, { onLand: function(name,i){ ... } });
     A.play();
     // 프레임마다
     if (!A.done) A.update(performance.now());

   onLand 는 부품이 제자리에 꽂히는 순간 호출된다 → 효과음 2번 연결점.
   ============================================================ */
var EPS = 1e-6;

function easeOutCubic(x) { return 1 - Math.pow(1 - x, 3); }
function easeInCubic(x) { return x * x * x; }
function easeOutBack(x, s) {          /* 지나쳤다가 되돌아오는 착지감 */
  s = s === undefined ? 1.9 : s;
  var c = s + 1, p = x - 1;
  return 1 + c * p * p * p + s * p * p;
}
function easeInBack(x, s) {           /* 반대로 살짝 물러섰다 튀어나가는 도약감 */
  s = s === undefined ? 1.5 : s;
  return (s + 1) * x * x * x - s * x * x;
}

ZZL.assembly = function (model, opts) {
  opts = opts || {};
  var order = Object.keys(model.parts);
  var root = model.root;

  /* 타이밍 (ms) — 전체 약 1.9초 */
  var POP_STAGGER = opts.popStagger || 85;    /* 뿅뿅뿅 간격 — 짧게 겹쳐야 경쾌하다 */
  var POP_DUR     = opts.popDur     || 260;
  var HOLD        = opts.hold       || 230;   /* 다 튀어나온 뒤 잠깐 떠 있는 시간 */
  var FLY_STAGGER = opts.flyStagger || 55;
  var FLY_DUR     = opts.flyDur     || 620;
  var SNAP_DUR    = opts.snapDur    || 150;   /* 꽂힌 직후 눌렸다 펴지는 시간 */

  var reach = opts.reach || 0.30;             /* 흩어지는 거리 (모델 크기 배수) */
  var span = Math.max(model.size.x, model.size.y, model.size.z);

  /* 모델 중심 — 흩어짐의 기준점.
     각 부품의 제자리를 기준으로 흩뿌리면 원래 벌어진 부품일수록 더 멀리 날아가
     한쪽으로 몰린 것처럼 보인다. 중심 기준으로 잡아야 "모여든다"는 인상이 난다. */
  root.updateMatrixWorld(true);
  var bb0 = new THREE.Box3().setFromObject(root);
  var centerW = bb0.getCenter(new THREE.Vector3());

  /* 반경은 축마다 따로 잡는다. 가장 긴 축 하나로 잡으면
     악어처럼 길고 낮은 동물이 세로로 화면을 벗어난다. */
  var flat = Math.max(model.size.x, model.size.z);
  var Rx = flat * reach * 0.92;
  var Ry = model.size.y * reach;
  var Rz = model.size.z * reach * 0.7;

  /* 부품별 상태 준비 */
  var items = [];
  var names = order.filter(function (n) { return !!model.parts[n]; });
  var N = names.length;
  var GOLDEN = Math.PI * (3 - Math.sqrt(5));
  var seed = Math.random() * Math.PI * 2;

  names.forEach(function (name, i) {
    var g = model.parts[name];
    var home = {
      pos: g.position.clone(),
      quat: g.quaternion.clone(),
      scl: g.scale.clone()
    };

    /* 방향을 고르게 분배한다 (황금각). 무작위로 뽑으면 한쪽에 뭉친다. */
    var y = 1 - 2 * ((i + 0.5) / N);
    var rr = Math.sqrt(Math.max(0, 1 - y * y));
    var a = GOLDEN * i + seed;
    var jit = 0.88 + (i % 3) * 0.09;

    var startW = centerW.clone().add(new THREE.Vector3(
      Math.cos(a) * rr * Rx * jit,
      y * Ry * jit,
      Math.sin(a) * rr * Rz * jit
    ));
    var from = g.parent.worldToLocal(startW.clone());

    var axis = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).normalize();
    var spin = new THREE.Quaternion().setFromAxisAngle(axis, (Math.random() * 1.4 + 0.7) * (Math.random() < 0.5 ? -1 : 1));
    var away = home.quat.clone().multiply(spin);

    /* 계층 깊이 — 부모가 먼저 자리를 잡아야 자연스럽다 */
    var depth = 0, pnode = g.parent;
    while (pnode && pnode !== root) { depth++; pnode = pnode.parent; }

    items.push({
      name: name, g: g, home: home, from: from, away: away, depth: depth,
      popAt: i * POP_STAGGER, flyAt: 0, landed: false,
      wob: Math.random() * Math.PI * 2
    });
  });

  var popEnd = (items.length ? (items.length - 1) * POP_STAGGER : 0) + POP_DUR;
  var flyBase = popEnd + HOLD;
  /* 얕은 부품(몸통 쪽)부터 합체 */
  var flyOrder = items.slice().sort(function (a, b) { return a.depth - b.depth; });
  flyOrder.forEach(function (it, i) { it.flyAt = flyBase + i * FLY_STAGGER; });
  var lastLand = flyBase + (items.length ? (items.length - 1) * FLY_STAGGER : 0) + FLY_DUR + SNAP_DUR;

  /* ── 완성 임팩트 ─────────────────────────────
     ① 실루엣이 하얗게 번쩍  ② 빛무리가 퍼짐  ③ 충격파 고리
     ④ 불꽃이 사방으로  ⑤ 몸이 부풀었다 되돌아옴 */
  var FIN_DUR = opts.finaleDur || 820;
  var total = lastLand + FIN_DUR;
  var baseScale = model.spec.scale || 1;

  var flashMat = new THREE.MeshBasicMaterial({ color: 0xFFFFFF });
  var shots = [];
  root.traverse(function (o) { if (o.isMesh) shots.push({ m: o, orig: o.material }); });

  var fx = new THREE.Group();
  fx.visible = false;
  root.add(fx);
  var fxCenter = root.worldToLocal(centerW.clone());

  /* 빛무리 */
  var halo = null;
  try {
    var hc = document.createElement('canvas');
    hc.width = hc.height = 128;
    var hx = hc.getContext('2d');
    var grd = hx.createRadialGradient(64, 64, 4, 64, 64, 64);
    grd.addColorStop(0, 'rgba(255,255,255,1)');
    grd.addColorStop(0.35, 'rgba(255,242,196,0.72)');
    grd.addColorStop(1, 'rgba(255,220,150,0)');
    hx.fillStyle = grd; hx.fillRect(0, 0, 128, 128);
    halo = new THREE.Mesh(
      new THREE.PlaneGeometry(span * 2.8, span * 2.8),
      new THREE.MeshBasicMaterial({
        map: new THREE.CanvasTexture(hc), transparent: true, opacity: 0,
        blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide
      })
    );
    halo.position.copy(fxCenter);
    fx.add(halo);
  } catch (e) { halo = null; }

  /* 충격파 고리 2겹 */
  var rings = [];
  [[0xFFF0BE, 0.05, 0.06], [0xFFFFFF, 0.028, null]].forEach(function (q, i) {
    var rm = new THREE.MeshBasicMaterial({
      color: q[0], transparent: true, opacity: 0,
      blending: THREE.AdditiveBlending, depthWrite: false
    });
    var rg = new THREE.Mesh(new THREE.TorusGeometry(span * 0.5, span * q[1], 6, 32), rm);
    rg.rotation.x = Math.PI / 2;
    rg.position.set(0, q[2] === null ? fxCenter.y : q[2], 0);
    fx.add(rg); rings.push(rg);
  });

  /* 불꽃 */
  var sparkMat = new THREE.MeshBasicMaterial({
    color: 0xFFE9A8, transparent: true, opacity: 0,
    blending: THREE.AdditiveBlending, depthWrite: false
  });
  var sparks = [], SPARK_N = 16;
  for (var si = 0; si < SPARK_N; si++) {
    var sp = new THREE.Mesh(new THREE.BoxGeometry(span * 0.06, span * 0.06, span * 0.06), sparkMat);
    var sa = (si / SPARK_N) * Math.PI * 2;
    sp.userData.dir = new THREE.Vector3(
      Math.cos(sa), (si % 3 - 1) * 0.55, Math.sin(sa) * 0.6).normalize();
    fx.add(sp); sparks.push(sp);
  }

  function setFlash(on) {
    for (var i = 0; i < shots.length; i++) shots[i].m.material = on ? flashMat : shots[i].orig;
  }
  function clearFx() {
    fx.visible = false;
    setFlash(false);
    if (halo) halo.material.opacity = 0;
    rings.forEach(function (r) { r.material.opacity = 0; });
    sparkMat.opacity = 0;
    root.scale.setScalar(baseScale);
  }

  var t0 = 0, running = false;
  var api = { done: true, duration: total };

  api.play = function () {
    t0 = performance.now();
    running = true; api.done = false;
    root.userData.assembling = true;
    clearFx();
    items.forEach(function (it) {
      it.landed = false;
      it.g.visible = false;
      it.g.scale.set(EPS, EPS, EPS);
    });
    /* 첫 프레임 잔상 방지 */
    api.update(t0);
  };

  api.stop = function () {   /* 즉시 완성 상태로 */
    running = false; api.done = true;
    root.userData.assembling = false;
    clearFx();
    items.forEach(function (it) {
      it.g.visible = true;
      it.g.position.copy(it.home.pos);
      it.g.quaternion.copy(it.home.quat);
      it.g.scale.copy(it.home.scl);
    });
  };

  api.update = function (now) {
    if (!running) return;
    var e = now - t0;

    for (var i = 0; i < items.length; i++) {
      var it = items[i], g = it.g;

      /* ① 아직 등장 전 */
      if (e < it.popAt) { g.visible = false; continue; }
      g.visible = true;

      /* ② 뿅 — 중심 주위의 제 자리에서 튀어나옴 */
      if (e < it.popAt + POP_DUR) {
        var p = (e - it.popAt) / POP_DUR;
        var s = easeOutBack(p, 2.6);
        g.position.copy(it.from);
        g.quaternion.copy(it.away);
        g.scale.set(it.home.scl.x * s, it.home.scl.y * s, it.home.scl.z * s);
        continue;
      }

      /* ③ 대기 — 제자리에서 살짝 흔들리며 떠 있음 */
      if (e < it.flyAt) {
        var w = (e * 0.006) + it.wob;
        g.position.copy(it.from);
        g.position.y += Math.sin(w) * span * 0.018;
        g.quaternion.copy(it.away);
        g.scale.copy(it.home.scl);
        continue;
      }

      /* ④ 합체 — 살짝 물러섰다가 중심으로 빨려들어옴 */
      if (e < it.flyAt + FLY_DUR) {
        var f = (e - it.flyAt) / FLY_DUR;
        var k = f < 0.25
          ? -easeInBack(f / 0.25, 1.6) * 0.16
          : easeOutBack((f - 0.25) / 0.75, 1.5);
        g.position.lerpVectors(it.from, it.home.pos, k);
        g.quaternion.copy(it.away);
        if (f >= 0.25) g.quaternion.slerp(it.home.quat, easeOutCubic((f - 0.25) / 0.75));
        var st = 1 + Math.sin(Math.min(f / 0.25, 1) * Math.PI) * 0.1;
        g.scale.set(it.home.scl.x / st, it.home.scl.y * st, it.home.scl.z / st);
        continue;
      }

      /* ⑤ 착지 — 눌렸다 펴짐 */
      if (!it.landed) {
        it.landed = true;
        if (opts.onLand) opts.onLand(it.name, i);
      }
      var q = Math.min((e - it.flyAt - FLY_DUR) / SNAP_DUR, 1);
      var sq = 1 - Math.sin(q * Math.PI) * 0.14;
      g.position.copy(it.home.pos);
      g.quaternion.copy(it.home.quat);
      g.scale.set(it.home.scl.x / sq, it.home.scl.y * sq, it.home.scl.z / sq);
    }

    /* ⑥ 완성 임팩트 */
    if (e >= lastLand) {
      var fe = e - lastLand, u = Math.min(fe / FIN_DUR, 1);
      fx.visible = true;

      /* 하얀 섬광 — 아주 짧게, 대신 강하게 */
      setFlash(fe < 110);

      /* 빛무리: 확 커졌다 사라짐 */
      if (halo) {
        halo.material.opacity = Math.max(0, 1 - u) * (fe < 60 ? fe / 60 : 1) * 0.95;
        var hs = 0.35 + easeOutCubic(u) * 1.25;
        halo.scale.set(hs, hs, hs);
      }

      /* 충격파 고리: 시차를 두고 두 겹 */
      rings.forEach(function (rg, i) {
        var d = i * 0.14;
        var v = Math.min(Math.max((u - d) / (1 - d), 0), 1);
        var rs = 0.35 + easeOutCubic(v) * 2.5;
        rg.scale.set(rs, rs, 1);
        rg.material.opacity = (1 - v) * (1 - v) * 0.95;
      });

      /* 불꽃: 바깥으로 튀며 작아짐 */
      var sv = Math.min(u / 0.72, 1);
      sparkMat.opacity = (1 - sv) * 0.95;
      for (var k2 = 0; k2 < sparks.length; k2++) {
        var d2 = span * (0.25 + easeOutCubic(sv) * 1.15);
        sparks[k2].position.copy(fxCenter).addScaledVector(sparks[k2].userData.dir, d2);
        var ss = Math.max(0.05, 1 - sv);
        sparks[k2].scale.set(ss, ss, ss);
      }

      /* 몸이 부풀었다 되돌아옴 */
      var pop2 = fe < 320 ? Math.sin((fe / 320) * Math.PI) * 0.16 : 0;
      root.scale.setScalar(baseScale * (1 + pop2));
    }

    if (e >= total) {
      running = false; api.done = true;
      root.userData.assembling = false;
      items.forEach(function (it) {
        it.g.visible = true;
        it.g.position.copy(it.home.pos);
        it.g.quaternion.copy(it.home.quat);
        it.g.scale.copy(it.home.scl);
      });
      clearFx();
      if (opts.onComplete) opts.onComplete();
    }
  };

  return api;
};

/* ── 퍼즐 지원: 부위 표시/숨김 ───────────────────── */
ZZL.setPartVisible = function (model, name, v) {
  if (model.parts[name]) model.parts[name].visible = v;
};
ZZL.puzzleOrder = function (spec) {
  return ['head', 'body', 'legs'];
};

global.ZZL = ZZL;
})(typeof window !== 'undefined' ? window : globalThis);
