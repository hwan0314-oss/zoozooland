/* ============================================================
   ZZL SPECIES SPEC — Phase 2·3 (50종)
   zzl-species.js 뒤에 로드된다. ZZL_SPECIES 배열에 이어 붙인다.

   원형(archetype) 함수로 골격을 잡고 종별 차이만 인자로 준다.
   부품 라이브러리와 같은 사상: 개별 동물용 일회성 코드를 만들지 않는다.
   ============================================================ */
(function (global) {
'use strict';

var S = global.ZZL_SPECIES || (global.ZZL_SPECIES = []);

/* ══ 원형 ═══════════════════════════════════════ */

/* 우제·기제류 — 뿔·귀·체구로 종을 가른다 */
function hoof(p) {
  var k = p.k || 1, c = p.c, d = p.d || c, f = p.f || c;
  return {
    scale: p.scale || 0.9,
    body: { type: 'quad', w: 1.0 * k, h: 0.92 * k, d: 1.8 * k, y: 1.42 * k,
            color: c, dark: d, belly: p.belly, sc: 2, sr: 3 },
    neck: { type: 'long', w: 0.42 * k, h: (p.neck || 0.8) * k, y: 1.78 * k, z: 0.72 * k,
            color: p.neckC || c, collar: p.collar },
    head: { type: 'muzzle', w: 0.6 * k, h: 0.56 * k, d: 0.86 * k, color: f,
            y: (p.neck || 0.8) * k + 0.14 * k, z: 0.12 * k,
            muzzle: { w: 0.4 * k, h: 0.34 * k, d: 0.34 * k, color: p.muz || f },
            nose: p.nose || 0x2A2620, mouth: true },
    eyes: { size: 0.17 * k, gap: 0.2 * k, y: 0.04 * k, z: 0.44 * k },
    ears: p.ears,
    legs: { type: 'post',
            pos: [[0.34 * k, 0.56 * k], [-0.34 * k, 0.56 * k], [0.32 * k, -0.6 * k], [-0.32 * k, -0.6 * k]],
            r: 0.115 * k, len: (p.leg || 0.9) * k, y: 0.96 * k,
            color: p.legC || f, foot: 'hoof', footColor: p.hoofC || 0x2A2620 },
    tail: p.tail || { type: 'tuft', w: 0.2 * k, y: 1.68 * k, z: -0.98 * k, color: p.tailC || c },
    extras: p.extras || [],
    anim: { bob: .035, headTurn: .32, neckSway: .06, earTwitch: true, blink: .48 },
    puzzle: p.puzzle
  };
}

/* 소형 네발 포유류 — 꼬리·귀·주둥이로 종을 가른다 */
function smallQuad(p) {
  var k = p.k || 1, c = p.c, d = p.d || c;
  return {
    scale: p.scale || 1.05,
    body: { type: 'quad', w: 0.8 * k, h: 0.66 * k, d: 1.1 * k, y: 0.66 * k,
            color: c, dark: d, belly: p.belly, sc: 2, sr: 2, studs: p.studs !== false },
    head: (p.snout === false)
      ? { type: 'box', w: 0.68 * k, h: 0.6 * k, d: 0.6 * k, color: p.f || c,
          y: 0.98 * k, z: 0.6 * k,
          muzzle: { w: 0.38 * k, h: 0.28 * k, d: 0.2 * k, color: p.muz || p.f || c },
          nose: p.nose || 0x2A2A2E }
      : { type: 'snout', w: 0.64 * k, h: 0.56 * k, d: 0.56 * k, color: p.f || c,
          y: 0.98 * k, z: 0.6 * k, snoutLen: (p.snoutLen || 0.32) * k,
          snoutColor: p.muz || p.f || c, nose: p.nose || 0x2A2A2E, mask: p.mask },
    eyes: { size: 0.17 * k, gap: 0.19 * k, y: 0.07 * k, z: 0.31 * k },
    ears: p.ears,
    legs: { type: 'post',
            pos: [[0.28 * k, 0.32 * k], [-0.28 * k, 0.32 * k], [0.28 * k, -0.32 * k], [-0.28 * k, -0.32 * k]],
            r: 0.11 * k, len: (p.leg || 0.32) * k, y: 0.36 * k,
            color: p.legC || d, foot: 'paw', footColor: p.pawC || d },
    tail: p.tail,
    extras: p.extras || [],
    anim: p.anim || { bob: .03, bobSpeed: 1.8, headTurn: .34, earTwitch: !!p.ears, blink: .62, hop: .42 },
    puzzle: p.puzzle
  };
}

/* 직립형 소형 포유류 */
function upright(p) {
  var k = p.k || 1, c = p.c;
  return {
    scale: p.scale || 1.02,
    body: { type: 'upright', w: 0.58 * k, h: 1.2 * k, d: 0.52 * k, y: 1.0 * k,
            color: c, belly: p.belly },
    head: { type: 'snout', w: 0.56 * k, h: 0.5 * k, d: 0.48 * k, color: p.f || c,
            y: 1.82 * k, z: 0.04 * k, snoutLen: (p.snoutLen || 0.3) * k,
            snoutColor: p.muz || p.f || c, nose: 0x2A2A2E, mask: p.mask },
    eyes: { size: 0.15 * k, gap: 0.16 * k, y: 0.06 * k, z: 0.26 * k },
    ears: p.ears,
    legs: { type: 'post', pos: [[0.18 * k, 0], [-0.18 * k, 0]],
            r: 0.1 * k, len: 0.4 * k, y: 0.4 * k, color: c, foot: 'paw', footColor: p.d || c },
    tail: p.tail,
    anim: { bob: .025, bobSpeed: 1.4, headTurn: .5, turnSpeed: .7, blink: .6, hop: .35 },
    puzzle: p.puzzle
  };
}

/* 영장류 */
function primate(p) {
  var k = p.k || 1, c = p.c;
  return {
    scale: p.scale || 0.94,
    body: { type: 'upright', w: 1.0 * k, h: 1.18 * k, d: 0.84 * k, y: 1.14 * k,
            color: c, belly: p.belly },
    neck: { type: 'short', w: 0.4 * k, h: 0.24 * k, y: 1.7 * k, z: 0.06 * k, color: c },
    head: { type: 'box', w: 0.84 * k, h: 0.76 * k, d: 0.76 * k, color: c,
            y: 0.34 * k, z: 0.02 * k, studs: true, dark: p.d || c,
            muzzle: { w: 0.48 * k, h: 0.42 * k, d: 0.3 * k, color: p.face || c, y: -0.14 * k },
            nose: p.nose || 0x5A3A34 },
    eyes: { size: 0.19 * k, gap: 0.2 * k, y: 0.1 * k, z: 0.41 * k },
    ears: { type: 'round', w: 0.14 * k, gap: 0.46 * k, y: 0.06 * k, z: -0.02 * k,
            color: p.earC || c, inner: p.face || c },
    legs: { type: 'post',
            pos: [[0.35 * k, 0.24 * k], [-0.35 * k, 0.24 * k], [0.33 * k, -0.3 * k], [-0.33 * k, -0.3 * k]],
            r: 0.13 * k, len: 0.54 * k, y: 0.58 * k, color: c, foot: 'paw', footColor: p.d || c },
    tail: p.tail,
    anim: { bob: .05, bobSpeed: 1.9, headTurn: .42, turnSpeed: .6, blink: .62, hop: .4 },
    puzzle: p.puzzle
  };
}

/* 앵무 — 크기 3단계 + 꼬리 길이로 종을 가른다 */
function parrot(p) {
  var k = p.k || 1, c = p.c, d = p.d || c;
  return {
    scale: p.scale || 0.92,
    body: { type: 'bird', w: 1.06 * k, h: 1.3 * k, d: 0.9 * k, y: 1.1 * k,
            color: c, belly: p.belly || c },
    head: { type: 'parrot', w: 0.96 * k, h: 0.84 * k, d: 0.88 * k, color: p.headC || c,
            dark: d, y: 2.12 * k, z: 0.02 * k, studs: true,
            face: p.face, beak: p.beak || 0x2A2A2E },
    eyes: { size: 0.19 * k, gap: 0.35 * k, y: 0.1 * k, z: 0.45 * k },
    legs: { type: 'bird', pos: [[0.23 * k, 0.06 * k], [-0.23 * k, 0.06 * k]],
            r: 0.09 * k, len: 0.32 * k, y: 0.44 * k, color: 0x5A5048 },
    tail: { type: 'feather', w: 0.54 * k, len: (p.tailLen || 1.0) * k,
            y: 0.6 * k, z: -0.44 * k, tilt: -0.36, color: p.tailC || c, dark: d },
    extras: [
      { type: 'crest', name: 'crest', w: 0.16 * k, len: 0.28 * k, gap: 0.2 * k,
        on: 'head', y: 0.42 * k, z: -0.1 * k, color: d },
      { type: 'wings', name: 'wings', w: 0.16 * k, len: 0.9 * k, d: 0.64 * k,
        gap: 0.6 * k, y: 1.56 * k, color: d, tip: p.wingTip || c }
    ],
    anim: { bob: .035, bobSpeed: 2.0, headTurn: .4, turnSpeed: .6, jerk: .32,
            flap: .26, blink: .65, hop: .55 },
    puzzle: ['head', 'body', 'wings', 'tail', 'legs']
  };
}

/* 오리·거위 */
function waterfowl(p) {
  var k = p.k || 1, c = p.c;
  return {
    scale: p.scale || 1.0,
    body: { type: 'bird', w: 0.86 * k, h: 0.78 * k, d: 1.34 * k, y: 0.78 * k,
            color: c, belly: p.belly },
    neck: { type: 'long', w: 0.34 * k, h: (p.neck || 0.5) * k, y: 1.1 * k, z: 0.5 * k, color: p.neckC || c },
    head: { type: 'duck', w: 0.52 * k, h: 0.46 * k, d: 0.56 * k, color: p.headC || c,
            y: (p.neck || 0.5) * k + 0.2 * k, z: 0.04 * k, beak: p.beak || 0xE8A93C },
    eyes: { size: 0.15 * k, gap: 0.2 * k, y: 0.08 * k, z: 0.28 * k },
    legs: { type: 'bird', pos: [[0.22 * k, 0], [-0.22 * k, 0]],
            r: 0.1 * k, len: 0.36 * k, y: 0.4 * k, color: p.footC || 0xE8A93C },
    tail: { type: 'feather', w: 0.36 * k, len: 0.42 * k, y: 0.86 * k, z: -0.66 * k,
            tilt: 0.3, color: c, dark: p.d || c },
    anim: { bob: .03, bobSpeed: 1.6, headTurn: .4, neckSway: .07, blink: .55, hop: .4 },
    puzzle: ['head', 'neck', 'body', 'legs']
  };
}

/* 돔형 등딱지 거북 */
function turtleDome(p) {
  var k = p.k || 1, c = p.c;
  return {
    scale: p.scale || 1.0,
    body: { type: 'shell', w: 2.0 * k, h: 0.8 * k, y: 0.88 * k,
            color: c, dark: p.d || c, scutes: p.scutes || 6, top: true, seg: 8 },
    neck: { type: 'fwd', w: 0.46 * k, h: 0.46 * k, y: 0.7 * k, z: 0.8 * k, color: p.f || c },
    head: { type: 'turtle', w: 0.52 * k, h: 0.46 * k, d: 0.46 * k,
            color: p.f || c, dark: 0x6A5638, y: 0.02 * k, z: 0.42 * k },
    eyes: { size: 0.13 * k, gap: 0.18 * k, y: 0.08 * k, z: 0.28 * k },
    legs: { type: 'column',
            pos: [[0.66 * k, 0.56 * k], [-0.66 * k, 0.56 * k], [0.66 * k, -0.56 * k], [-0.66 * k, -0.56 * k]],
            r: 0.22 * k, len: 0.46 * k, y: 0.6 * k, color: p.f || c, footColor: p.d || c },
    tail: { type: 'stub', r: 0.13 * k, len: 0.28 * k, y: 0.7 * k, z: -0.92 * k, color: p.f || c },
    anim: { bob: .015, bobSpeed: .9, headTurn: .34, turnSpeed: .3,
            headBob: { rate: .16, amt: .22 }, blink: .38, hop: .22 },
    puzzle: ['head', 'body', 'legs', 'tail']
  };
}

/* 납작 등딱지 거북 (수생) */
function turtleFlat(p) {
  var k = p.k || 1, c = p.c;
  return {
    scale: p.scale || 1.05,
    body: { type: 'shellFlat', w: 1.7 * k, h: 0.44 * k, d: 1.9 * k, y: 0.6 * k,
            color: c, dark: p.d || c, rows: p.rows || 3 },
    neck: { type: 'fwd', w: 0.4 * k, h: (p.neck || 0.42) * k, y: 0.56 * k, z: 0.94 * k, color: p.f || c },
    head: { type: 'turtle', w: (p.headW || 0.5) * k, h: 0.4 * k, d: 0.44 * k,
            color: p.f || c, dark: 0x4A4030, y: 0, z: 0.4 * k },
    eyes: { size: 0.12 * k, gap: 0.17 * k, y: 0.07 * k, z: 0.26 * k },
    legs: { type: 'sprawl',
            pos: [[0.72 * k, 0.6 * k], [-0.72 * k, 0.6 * k], [0.72 * k, -0.6 * k], [-0.72 * k, -0.6 * k]],
            r: 0.14 * k, len: 0.34 * k, y: 0.5 * k, color: p.f || c },
    tail: { type: 'stub', r: 0.11 * k, len: (p.tailLen || 0.4) * k, y: 0.56 * k, z: -1.0 * k, color: p.f || c },
    anim: { bob: .018, bobSpeed: 1.1, headTurn: .34, turnSpeed: .35,
            headBob: { rate: .18, amt: .2 }, blink: .4, hop: .24 },
    puzzle: ['head', 'body', 'legs', 'tail']
  };
}

/* 악어 — 주둥이 형태가 곧 종 구분 */
function crocodile(p) {
  var k = p.k || 1, c = p.c, d = p.d || c;
  return {
    scale: p.scale || 0.86,
    body: { type: 'lowLong', w: 1.46 * k, h: 0.92 * k, d: 1.86 * k, y: 1.0 * k,
            color: c, dark: d, belly: p.belly, studs: true },
    head: { type: 'croc', w: 1.24 * k, h: 0.88 * k, d: 0.98 * k, color: c, dark: d,
            y: 0.74 * k, z: 1.4 * k,
            snout: { w: (p.snoutW || 1.0) * k, h: (p.snoutH || 0.4) * k, d: (p.snoutD || 1.15) * k },
            teeth: p.teeth || 4, studs: true },
    eyes: { size: 0.25 * k, gap: 0.37 * k, y: 0.48 * k, z: 0.32 * k },
    legs: { type: 'sprawl',
            pos: [[0.7 * k, 0.6 * k], [-0.7 * k, 0.6 * k], [0.7 * k, -0.58 * k], [-0.7 * k, -0.58 * k]],
            r: 0.18 * k, len: 0.54 * k, y: 0.54 * k, color: d },
    tail: { type: 'segment', w: 0.92 * k, h: 0.7 * k, len: 1.76 * k, count: 3,
            y: 1.0 * k, z: -0.98 * k, color: c, dark: d, crest: d },
    anim: { bob: .04, bobSpeed: 1.7, headTurn: .18, turnSpeed: .45,
            jaw: .38, tailWave: .12, blink: .5, hop: .42 },
    puzzle: ['head', 'body', 'legs', 'tail', 'jaw']
  };
}

/* 도마뱀 */
function lizard(p) {
  var k = p.k || 1, c = p.c, d = p.d || c;
  return {
    scale: p.scale || 1.0,
    body: { type: 'lowLong', w: 0.86 * k, h: 0.52 * k, d: 1.4 * k, y: 0.62 * k,
            color: c, dark: d, belly: p.belly, crest: p.crest, studs: p.studs },
    head: { type: 'box', w: 0.68 * k, h: 0.44 * k, d: 0.62 * k, color: c,
            y: 0.7 * k, z: 0.96 * k,
            muzzle: { w: 0.46 * k, h: 0.32 * k, d: 0.34 * k, color: c, y: -0.04 * k },
            nose: d },
    eyes: { size: 0.14 * k, gap: 0.34 * k, y: 0.12 * k, z: 0.2 * k, side: p.sideEye },
    legs: { type: 'sprawl',
            pos: [[0.5 * k, 0.44 * k], [-0.5 * k, 0.44 * k], [0.5 * k, -0.44 * k], [-0.5 * k, -0.44 * k]],
            r: 0.12 * k, len: 0.36 * k, y: 0.5 * k, color: d },
    tail: { type: 'segment', w: (p.tailW || 0.6) * k, h: (p.tailH || 0.4) * k,
            len: (p.tailLen || 1.5) * k, count: 4, y: 0.62 * k, z: -0.7 * k,
            color: c, dark: d, crest: p.crest },
    extras: p.extras || [],
    anim: { bob: .02, bobSpeed: 1.2, headTurn: .3, turnSpeed: .4,
            headBob: p.bobHead ? { rate: .2, amt: .24 } : null, tailWave: .1, blink: .42, hop: .3 },
    puzzle: p.puzzle || ['head', 'body', 'legs', 'tail']
  };
}

/* 뱀 — 굵기가 곧 종 구분. 몸통과 꼬리를 나눠 3부위를 만든다 */
function snake(p) {
  var k = p.k || 1, c = p.c, d = p.d || c;
  var th = (p.thick || 0.62) * k;
  var seg = 0.62 * k;
  var frontN = p.count || 3;
  var y = th * 0.5;
  return {
    scale: p.scale || 1.0,
    body: { type: 'serpent', w: th, h: th * 0.8, seg: seg, count: frontN,
            y: y, z: 0, color: c, dark: d, tipColor: null },
    head: { type: 'snake', w: th * 1.05, h: th * 0.66, d: 0.5 * k,
            color: p.headC || c, dark: d, y: y, z: 0.3 * k, tongue: 0xD8506A },
    eyes: { size: 0.11 * k, gap: th * 0.42, y: 0.06 * k, z: 0.2 * k, turn: 0.5 },
    tail: { type: 'segment', w: th * 0.92, h: th * 0.74, len: (p.tailLen || 2.0) * k,
            count: 4, y: y, z: -seg * frontN, color: c, dark: d },
    anim: { bob: .02, bobSpeed: 1.1, headTurn: .32, turnSpeed: .4,
            tailWave: .18, blink: .34, hop: .26 },
    puzzle: ['head', 'body', 'tail']
  };
}

/* 개구리·도롱뇽 */
function frogling(p) {
  var k = p.k || 1, c = p.c;
  return {
    scale: p.scale || 1.25,
    body: { type: 'frog', w: 0.82 * k, h: 0.56 * k, d: 0.92 * k, y: 0.5 * k,
            color: c, belly: p.belly, dots: p.dots },
    head: { type: 'frog', w: 0.8 * k, h: 0.4 * k, d: 0.6 * k, color: c,
            dark: p.d || 0x2A3A28, y: 0.78 * k, z: 0.5 * k },
    eyes: { size: 0.2 * k, gap: 0.28 * k, y: 0.24 * k, z: 0.14 * k, turn: 0.7 },
    legs: { type: 'frog', fw: 0.3 * k, fz: 0.36 * k, bw: 0.42 * k, bz: -0.24 * k,
            r: 0.11 * k, len: 0.4 * k, y: 0.5 * k, color: c, web: p.web || c },
    anim: { bob: .03, bobSpeed: 1.3, headTurn: .26, turnSpeed: .35, blink: .3, hop: .55 },
    puzzle: ['head', 'body', 'legs']
  };
}

/* 물고기 */
function fishy(p) {
  var k = p.k || 1, c = p.c;
  return {
    scale: p.scale || 1.0,
    body: { type: 'fish', w: 0.44 * k, h: 0.56 * k, d: 2.2 * k, y: 1.1 * k,
            color: c, belly: p.belly },
    head: { type: 'fish', w: 0.42 * k, h: 0.5 * k, d: 0.5 * k, color: c,
            dark: p.d || c, y: 1.1 * k, z: 1.36 * k, snoutLen: 1.1 * k },
    eyes: { size: 0.14 * k, gap: 0.23 * k, y: 0.08 * k, z: 0, side: true },
    extras: [{ type: 'fins', name: 'fins', h: 0.4 * k, d: 0.6 * k, gap: 0.26 * k,
               dorsal: true, dz: -0.6 * k, caudal: true, cz: -1.34 * k,
               color: p.finC || c, y: 1.1 * k }],
    anim: { bob: .06, bobSpeed: 1.8, headTurn: .16, turnSpeed: .5, blink: .001 },
    puzzle: ['head', 'body', 'fins']
  };
}

/* ══ 종 사양 ═══════════════════════════════════ */
function add(a) { S.push(a); }

/* ── 대동물 방목장 ─────────────────────────── */
add({ id: 'A013', kname: '면양', ename: 'Sheep', zone: '대동물 방목장', n: 21, parts: 4,
  tell: '두꺼운 양털 몸통 + 옆으로 말린 뿔', rivals: ['자넨', '보어염소', '무플론'],
  model: hoof({ c: 0xF2ECDC, d: 0xDCD2BC, f: 0xE6DAC2, k: 0.95, neck: 0.5, leg: 0.8,
    ears: { type: 'point', w: 0.11, len: 0.3, gap: 0.3, y: 0.2, spread: 1.1, color: 0xE6DAC2 },
    extras: [{ type: 'hornSpiral', name: 'horn', w: 0.12, r: 0.42, gap: 0.26, on: 'head', y: 0.12, color: 0xC9B896 }],
    puzzle: ['head', 'horn', 'body', 'legs'] }) });

add({ id: 'A014', kname: '자넨', ename: 'Saanen Goat', zone: '대동물 방목장', n: 1, parts: 4,
  tell: '뿔이 없고 순백 + 길게 늘어진 귀', rivals: ['면양', '보어염소', '흑염소'],
  model: hoof({ c: 0xFAF6EC, d: 0xE4DCCC, f: 0xFAF6EC, k: 0.92, neck: 0.62,
    ears: { type: 'long', w: 0.13, len: 0.44, gap: 0.28, y: 0.18, spread: 1.3, color: 0xFAF6EC },
    tail: { type: 'tuft', w: 0.16, y: 1.6, z: -0.92, color: 0xFAF6EC },
    puzzle: ['head', 'body', 'legs', 'ears'] }) });

add({ id: 'A015', kname: '보어염소', ename: 'Boer Goat', zone: '대동물 방목장', n: 4, parts: 4,
  tell: '흰 몸 + 갈색 머리 + 짧고 굵은 뿔', rivals: ['자넨', '흑염소', '면양'],
  model: hoof({ c: 0xF4EEE0, d: 0xDED4C0, f: 0xA85C34, muz: 0xC07848, k: 0.92, neck: 0.6,
    ears: { type: 'long', w: 0.14, len: 0.42, gap: 0.28, y: 0.16, spread: 1.35, color: 0xA85C34 },
    extras: [{ type: 'hornShort', name: 'horn', w: 0.1, len: 0.34, gap: 0.2, on: 'head', y: 0.2, color: 0x6A5236 }],
    puzzle: ['head', 'horn', 'body', 'ears'] }) });

add({ id: 'A016', kname: '흑염소', ename: 'Korean Black Goat', zone: '대동물 방목장', n: 2, parts: 4,
  tell: '전신 검정 + 뒤로 곧게 뻗은 뿔', rivals: ['자넨', '보어염소', '산양'],
  model: hoof({ c: 0x33302C, d: 0x22201D, f: 0x33302C, k: 0.9, neck: 0.6, nose: 0x141312,
    ears: { type: 'point', w: 0.11, len: 0.34, gap: 0.26, y: 0.18, spread: 1.0, color: 0x33302C },
    extras: [{ type: 'hornBack', name: 'horn', w: 0.11, len: 0.46, gap: 0.18, on: 'head', y: 0.2, color: 0x6A5C48 }],
    puzzle: ['head', 'horn', 'body', 'legs'] }) });

add({ id: 'A017', kname: '무플론', ename: 'Mouflon', zone: '대동물 방목장', n: 2, parts: 5,
  tell: '머리 옆으로 크게 말려 감긴 나선뿔', rivals: ['면양', '산양', '흑염소'],
  model: hoof({ c: 0x8A6440, d: 0x6E4E30, f: 0x9C7248, belly: 0xE8DCC4, k: 0.95, neck: 0.6,
    ears: { type: 'point', w: 0.1, len: 0.28, gap: 0.3, y: 0.16, spread: 1.2, color: 0x9C7248 },
    extras: [{ type: 'hornSpiral', name: 'horn', w: 0.14, r: 0.54, gap: 0.24, on: 'head', y: 0.14, color: 0xB09468 }],
    puzzle: ['head', 'horn', 'body', 'legs', 'ears'] }) });

add({ id: 'A018', kname: '산양', ename: 'Dall Sheep', zone: '대동물 방목장', n: 10, parts: 5,
  tell: '굵고 뒤로 크게 휜 뿔 + 흰 몸', rivals: ['무플론', '면양', '흑염소'],
  model: hoof({ c: 0xF0EAD8, d: 0xD8D0BA, f: 0xF0EAD8, k: 0.98, neck: 0.62,
    ears: { type: 'point', w: 0.1, len: 0.28, gap: 0.3, y: 0.16, spread: 1.1, color: 0xF0EAD8 },
    extras: [{ type: 'hornBack', name: 'horn', w: 0.16, len: 0.6, gap: 0.2, on: 'head', y: 0.16, color: 0xB8A278 }],
    puzzle: ['head', 'horn', 'body', 'legs', 'ears'] }) });

add({ id: 'A019', kname: '미니나귀', ename: 'Miniature Donkey', zone: '대동물 방목장', n: 1, parts: 4,
  tell: '몸에 비해 아주 긴 귀 + 회색', rivals: ['미니말'],
  model: hoof({ c: 0x9A948A, d: 0x7C766C, f: 0xA69F94, belly: 0xD8D2C6, k: 1.0, neck: 0.66, leg: 0.94,
    ears: { type: 'long', w: 0.15, len: 0.72, gap: 0.22, y: 0.22, spread: 0.24, color: 0x9A948A, inner: 0xC9C2B4 },
    tail: { type: 'thin', r: 0.07, len: 0.5, count: 2, y: 1.6, z: -0.94, color: 0x4A443C },
    puzzle: ['head', 'body', 'legs', 'ears'] }) });

add({ id: 'A020', kname: '미니말', ename: 'Miniature Horse', zone: '대동물 방목장', n: 3, parts: 4,
  tell: '짧고 둥근 귀 + 목 갈기', rivals: ['미니나귀'],
  model: hoof({ c: 0x8C5E36, d: 0x6E4728, f: 0x9C6A3E, k: 1.0, neck: 0.7, leg: 0.96,
    ears: { type: 'point', w: 0.1, len: 0.24, gap: 0.24, y: 0.22, spread: 0.3, color: 0x8C5E36 },
    tail: { type: 'bushy', w: 0.24, len: 0.7, rings: 3, y: 1.62, z: -0.96, color: 0x3A2C1E },
    extras: [{ type: 'crest', name: 'mane', w: 0.14, len: 0.3, gap: 0.0, on: 'neck', y: 0.5, z: -0.2, color: 0x3A2C1E, puzzle: false }],
    puzzle: ['head', 'body', 'legs', 'ears'] }) });

/* ── 오솔길 빌리지 ─────────────────────────── */
add({ id: 'A021', kname: '제넷', ename: 'Genet', zone: '오솔길 빌리지', n: 2, parts: 5,
  tell: '가늘고 긴 몸 + 검은 고리 줄무늬 꼬리', rivals: ['페럿', '라쿤'],
  model: smallQuad({ c: 0xD8C9A8, d: 0xB8A684, f: 0xE0D3B6, k: 1.0, snoutLen: 0.34,
    belly: 0xF2E9D4, nose: 0x2A2A2E,
    ears: { type: 'round', w: 0.14, gap: 0.3, y: 0.26, z: -0.04, color: 0xD8C9A8, inner: 0xEFE4CC },
    tail: { type: 'bushy', w: 0.26, len: 1.3, rings: 6, y: 0.68, z: -0.56, color: 0xE4D8BC, stripe: 0x38332C },
    puzzle: ['head', 'body', 'legs', 'tail', 'ears'] }) });

add({ id: 'A022', kname: '다람쥐원숭이', ename: 'Squirrel Monkey', zone: '오솔길 빌리지', n: 2, parts: 5,
  tell: '흰 얼굴 가면 + 몸보다 훨씬 긴 꼬리', rivals: ['일본원숭이'],
  model: primate({ c: 0xC2A85E, d: 0x9C8442, face: 0xF4EEDC, earC: 0xF4EEDC,
    belly: 0xE8DCB4, k: 0.78, scale: 1.0,
    tail: { type: 'thin', r: 0.08, len: 1.5, count: 5, y: 0.9, z: -0.38, color: 0xC2A85E, stripe: 0x8A7238 },
    puzzle: ['head', 'body', 'legs', 'tail', 'ears'] }) });

/* ── 파충류 빌리지 · 포유류 ────────────────── */
add({ id: 'A023', kname: '기니피그', ename: 'Guinea Pig', zone: '파충류 빌리지', n: 30, parts: 3,
  tell: '귀도 꼬리도 거의 없는 통짜 몸', rivals: ['토끼', '친칠라', '데구'],
  model: smallQuad({ c: 0xD8A868, d: 0xB8894E, f: 0xE8C08A, k: 0.9, snout: false,
    belly: 0xF2E4C8, leg: 0.2, scale: 1.15,
    ears: { type: 'round', w: 0.12, gap: 0.28, y: 0.24, z: -0.04, color: 0xC9946A },
    puzzle: ['head', 'body', 'ears'] }) });

add({ id: 'A024', kname: '친칠라', ename: 'Chinchilla', zone: '파충류 빌리지', n: 11, parts: 4,
  tell: '동그란 큰 귀 + 풍성한 붓 꼬리', rivals: ['토끼', '기니피그', '데구'],
  model: smallQuad({ c: 0xB4B2B8, d: 0x94929A, f: 0xC2C0C6, k: 0.85, snout: false,
    belly: 0xE8E6EA, leg: 0.22, scale: 1.15,
    ears: { type: 'round', w: 0.24, gap: 0.3, y: 0.3, z: -0.02, color: 0xB4B2B8, inner: 0xD8C4C8 },
    tail: { type: 'bushy', w: 0.28, len: 0.6, rings: 3, y: 0.66, z: -0.5, color: 0xA8A6AE },
    puzzle: ['head', 'body', 'ears', 'tail'] }) });

add({ id: 'A025', kname: '데구', ename: 'Degu', zone: '파충류 빌리지', n: 2, parts: 4,
  tell: '가는 꼬리 끝에만 붓처럼 털', rivals: ['친칠라', '기니피그', '프레리독'],
  model: smallQuad({ c: 0xA8895E, d: 0x8A6E46, f: 0xB89A6C, k: 0.72, snoutLen: 0.24,
    belly: 0xE0CFAA, leg: 0.2, scale: 1.2,
    ears: { type: 'round', w: 0.15, gap: 0.24, y: 0.26, z: -0.04, color: 0xA8895E, inner: 0xD4B892 },
    tail: { type: 'thin', r: 0.07, len: 0.8, count: 3, y: 0.62, z: -0.48, color: 0xA8895E },
    puzzle: ['head', 'body', 'ears', 'tail'] }) });

add({ id: 'A026', kname: '고슴도치', ename: 'Amur Hedgehog', zone: '파충류 빌리지', n: 6, parts: 3,
  tell: '등을 덮은 짧은 가시', rivals: ['말레이호저', '기니피그'],
  model: smallQuad({ c: 0xC9B08A, d: 0xA8906C, f: 0xE4D6BC, k: 0.78, snoutLen: 0.3,
    leg: 0.16, scale: 1.2, studs: false,
    extras: [{ type: 'quills', name: 'quills', w: 0.6, d: 0.9, r: 0.06, len: 0.3,
               count: 22, on: 'body', y: 0.3, color: 0x6E5C44 }],
    puzzle: ['head', 'body', 'quills'] }) });

add({ id: 'A027', kname: '페럿', ename: 'Ferret', zone: '파충류 빌리지', n: 3, parts: 4,
  tell: '아주 긴 몸통 + 눈가 검은 무늬', rivals: ['제넷', '난쟁이몽구스'],
  model: smallQuad({ c: 0xE0D2B4, d: 0xB8A684, f: 0xF0E6CE, k: 0.82, snoutLen: 0.3,
    mask: 0x4A4038, leg: 0.2, scale: 1.1,
    ears: { type: 'round', w: 0.11, gap: 0.26, y: 0.24, z: -0.04, color: 0xE0D2B4 },
    tail: { type: 'bushy', w: 0.22, len: 0.8, rings: 4, y: 0.62, z: -0.48, color: 0xB8A684 },
    puzzle: ['head', 'body', 'legs', 'tail'] }) });

add({ id: 'A028', kname: '슈가글라이더', ename: 'Sugar Glider', zone: '파충류 빌리지', n: 3, parts: 4,
  tell: '앞뒤 다리를 잇는 비막 + 등 검은 줄', rivals: ['데구', '주머니여우'],
  model: smallQuad({ c: 0xB0B4BA, d: 0x8E9298, f: 0xE4E6E8, k: 0.66, snoutLen: 0.26,
    belly: 0xF0F0F0, leg: 0.18, scale: 1.25,
    ears: { type: 'round', w: 0.16, gap: 0.24, y: 0.28, z: -0.02, color: 0xB0B4BA, inner: 0xD8C0C4 },
    tail: { type: 'bushy', w: 0.2, len: 0.9, rings: 4, y: 0.6, z: -0.46, color: 0xA0A4AA, tip: 0x3A3A40 },
    extras: [{ type: 'patagium', name: 'patagium', w: 0.34, d: 0.9, gap: 0.42,
               on: 'body', y: -0.02, color: 0xA8ACB2 }],
    puzzle: ['head', 'body', 'patagium', 'tail'] }) });

add({ id: 'A029', kname: '주머니여우', ename: 'Common Brushtail Possum', zone: '파충류 빌리지', n: 1, parts: 4,
  tell: '분홍 코 + 덤불처럼 굵은 검은 꼬리', rivals: ['슈가글라이더', '페럿'],
  model: smallQuad({ c: 0x9A9690, d: 0x7A766F, f: 0xB0ACA4, k: 0.92, snoutLen: 0.3,
    belly: 0xDCD6C8, nose: 0xD48C96, leg: 0.24, scale: 1.05,
    ears: { type: 'round', w: 0.2, gap: 0.3, y: 0.3, z: -0.04, color: 0x9A9690, inner: 0xE0BEC2 },
    tail: { type: 'bushy', w: 0.34, len: 1.0, rings: 4, y: 0.66, z: -0.52, color: 0x38352F },
    puzzle: ['head', 'body', 'ears', 'tail'] }) });

add({ id: 'A030', kname: '프레리독', ename: 'Prairie Dog', zone: '파충류 빌리지', n: 2, parts: 4,
  tell: '통통한 몸 + 아주 짧은 꼬리 (미어캣과 대조)', rivals: ['미어캣', '난쟁이몽구스', '데구'],
  model: upright({ c: 0xCBA870, f: 0xD9BC8A, belly: 0xEBDCBC, k: 0.9, snoutLen: 0.24, scale: 1.1,
    ears: { type: 'round', w: 0.1, gap: 0.26, y: 0.12, z: -0.06, color: 0xB08E58 },
    tail: { type: 'tuft', w: 0.2, y: 0.5, z: -0.3, color: 0xB08E58 },
    puzzle: ['head', 'body', 'legs', 'tail'] }) });

add({ id: 'A031', kname: '난쟁이몽구스', ename: 'Dwarf Mongoose', zone: '파충류 빌리지', n: 3, parts: 3,
  tell: '네 발로 선 가늘고 낮은 몸 (미어캣은 두 발)', rivals: ['미어캣', '페럿', '프레리독'],
  model: smallQuad({ c: 0x8A7256, d: 0x6E5A42, f: 0x9C8464, k: 0.66, snoutLen: 0.28,
    leg: 0.2, scale: 1.2,
    ears: { type: 'round', w: 0.1, gap: 0.22, y: 0.2, z: -0.06, color: 0x6E5A42 },
    tail: { type: 'thin', r: 0.08, len: 0.72, count: 3, y: 0.6, z: -0.46, color: 0x8A7256 },
    puzzle: ['head', 'body', 'tail'] }) });

/* ── 기타 구역 ─────────────────────────────── */
add({ id: 'A032', kname: '코아티', ename: 'Coati', zone: '기타', n: 1, parts: 5,
  tell: '위로 들린 아주 긴 코 + 고리 꼬리', rivals: ['라쿤', '제넷'],
  model: smallQuad({ c: 0x8A6A4A, d: 0x6C5038, f: 0xA88462, k: 1.0, snoutLen: 0.58,
    muz: 0xD8C4A8, belly: 0xC9B08A, leg: 0.3, scale: 1.0,
    ears: { type: 'round', w: 0.12, gap: 0.3, y: 0.26, z: -0.06, color: 0x8A6A4A },
    tail: { type: 'thin', r: 0.13, len: 1.4, count: 5, y: 0.7, z: -0.54, color: 0xB8946C, stripe: 0x4A3828 },
    puzzle: ['head', 'body', 'legs', 'tail', 'ears'] }) });

add({ id: 'A033', kname: '말레이호저', ename: 'Crested Porcupine', zone: '기타', n: 1, parts: 3,
  tell: '길고 뾰족한 흑백 가시가 등을 덮음', rivals: ['고슴도치'],
  model: smallQuad({ c: 0x4A443C, d: 0x33302A, f: 0x5C554A, k: 1.15, snoutLen: 0.34,
    leg: 0.28, scale: 0.92, studs: false,
    extras: [{ type: 'quills', name: 'quills', w: 0.8, d: 1.2, r: 0.07, len: 0.9,
               count: 26, on: 'body', y: 0.32, color: 0xF0EADC }],
    puzzle: ['head', 'body', 'quills'] }) });

/* ── 사랑새 빌리지 ─────────────────────────── */
add({ id: 'A034', kname: '사랑앵무새', ename: 'Budgerigar', zone: '사랑새 빌리지', n: 142, parts: 3,
  tell: '소형 + 길고 뾰족한 꼬리', rivals: ['모란앵무새', '코뉴어'],
  model: parrot({ c: 0x86C93E, d: 0x6BA82E, headC: 0xF2DE3A, face: 0xF7F0E2,
    belly: 0x9ED45A, beak: 0x8A8A80, k: 0.52, scale: 1.25, tailLen: 1.5, wingTip: 0x3E7A2E }) });

add({ id: 'A035', kname: '모란앵무새', ename: 'Lovebird', zone: '사랑새 빌리지', n: 26, parts: 3,
  tell: '소형 + 뭉툭하게 짧은 꼬리 (사랑앵무와 대조)', rivals: ['사랑앵무새', '코뉴어'],
  model: parrot({ c: 0x4CA83E, d: 0x3A8630, headC: 0xE8724A, face: 0xF2C44A,
    belly: 0x6ABF4E, beak: 0xD8564A, k: 0.54, scale: 1.25, tailLen: 0.5, wingTip: 0x2E6A28 }) });

/* ── 파충류 빌리지 · 앵무 ──────────────────── */
add({ id: 'A036', kname: '할리퀸금강앵무새', ename: 'Red-and-green Macaw', zone: '파충류 빌리지', n: 1, parts: 5,
  tell: '대형 + 적·녹 배색 (청금강과 대조)', rivals: ['청금강앵무새', '아마존앵무새'],
  model: parrot({ c: 0xC8342E, d: 0x9E2622, headC: 0xC8342E, face: 0xF7F0E2,
    belly: 0xC8342E, k: 1.0, tailLen: 1.15, wingTip: 0x2E7A4E }) });

add({ id: 'A037', kname: '아마존앵무새', ename: 'Amazon Parrot', zone: '파충류 빌리지', n: 1, parts: 4,
  tell: '중형 + 전신 녹색 + 짧은 꼬리', rivals: ['뉴기니아', '코뉴어', '노랑머리카이큐'],
  model: parrot({ c: 0x4E9E3E, d: 0x3C7C30, headC: 0x4E9E3E, face: 0xF2E8C8,
    belly: 0x62B04E, beak: 0x9A9084, k: 0.78, tailLen: 0.55, wingTip: 0xE8B62E }) });

add({ id: 'A038', kname: '뉴기니아', ename: 'Eclectus Parrot', zone: '파충류 빌리지', n: 1, parts: 4,
  tell: '중형 + 굵고 밝은 부리 + 단색 몸', rivals: ['아마존앵무새', '코뉴어'],
  model: parrot({ c: 0xC0322E, d: 0x9A2624, headC: 0xC0322E, belly: 0x8A2A6E,
    beak: 0xE8A32E, k: 0.8, tailLen: 0.6, wingTip: 0x2E4E9E }) });

add({ id: 'A039', kname: '코뉴어', ename: 'Green-cheeked Conure', zone: '파충류 빌리지', n: 3, parts: 4,
  tell: '중소형 + 녹색 몸에 긴 꼬리', rivals: ['아마존앵무새', '사랑앵무새', '노랑머리카이큐'],
  model: parrot({ c: 0x5AA84A, d: 0x448A38, headC: 0x4A423E, face: 0x8A5C4A,
    belly: 0xA84A3E, beak: 0x38342E, k: 0.62, scale: 1.1, tailLen: 1.2, wingTip: 0x2E5A9E }) });

add({ id: 'A040', kname: '노랑머리카이큐', ename: 'White-bellied Caique', zone: '파충류 빌리지', n: 1, parts: 4,
  tell: '중소형 + 흰 배 + 주황빛 머리', rivals: ['코뉴어', '아마존앵무새'],
  model: parrot({ c: 0x4E9E3E, d: 0x3C7C30, headC: 0xE8942E, face: 0xF7F0E2,
    belly: 0xF7F2E2, beak: 0xC9C2B4, k: 0.62, scale: 1.1, tailLen: 0.55, wingTip: 0x3C7C30 }) });

/* ── 호숫가 ────────────────────────────────── */
add({ id: 'A041', kname: '오리', ename: 'Duck', zone: '호숫가', n: 8, parts: 3,
  tell: '납작 부리 + 짧은 목', rivals: ['거위', '에뮤'],
  model: waterfowl({ c: 0xE8E2D2, d: 0xC9C2B0, neckC: 0xE8E2D2, headC: 0x3E7A4E,
    belly: 0xF4F0E4, beak: 0xE8A93C, k: 0.95, neck: 0.42, scale: 1.05 }) });

add({ id: 'A042', kname: '거위', ename: 'Goose', zone: '호숫가', n: 1, parts: 4,
  tell: '오리보다 크고 목이 길다', rivals: ['오리', '에뮤'],
  model: waterfowl({ c: 0xF4F0E6, d: 0xD8D2C2, neckC: 0xF4F0E6, headC: 0xF4F0E6,
    belly: 0xFAF8F0, beak: 0xE87A3C, footC: 0xE87A3C, k: 1.15, neck: 1.15, scale: 0.95 }) });

/* ── 악어 빌리지 ───────────────────────────── */
add({ id: 'A043', kname: '엘리게이터', ename: 'American Alligator', zone: '악어 빌리지', n: 2, parts: 5,
  tell: 'U자로 뭉툭한 넓은 주둥이 (바다악어보다 둥글다)', rivals: ['바다악어', '펄스가비알'],
  model: crocodile({ c: 0x3E4A3A, d: 0x2C362A, belly: 0xD8D2B0,
    snoutW: 1.08, snoutH: 0.42, snoutD: 0.95, teeth: 3, k: 0.98 }) });

add({ id: 'A044', kname: '펄스가비알', ename: 'Gharial', zone: '악어 빌리지', n: 1, parts: 5,
  tell: '젓가락처럼 가늘고 아주 긴 주둥이', rivals: ['바다악어', '엘리게이터'],
  model: crocodile({ c: 0x6E7A5E, d: 0x54603E, belly: 0xE4DCBC,
    snoutW: 0.34, snoutH: 0.26, snoutD: 2.0, teeth: 6, k: 0.94 }) });

/* ── 거북이 빌리지 카페 ────────────────────── */
add({ id: 'A045', kname: '레드풋 육지거북', ename: 'Red-footed Tortoise', zone: '거북이 빌리지 카페', n: 1, parts: 4,
  tell: '중형 돔 등딱지 + 다리의 붉은 반점', rivals: ['설가타', '커먼머스크터틀'],
  model: turtleDome({ c: 0x3E3A34, d: 0xC94A2E, f: 0x4A443A, k: 0.72, scutes: 6, scale: 1.15 }) });

add({ id: 'A046', kname: '커먼머스크터틀', ename: 'Common musk turtle', zone: '거북이 빌리지 카페', n: 2, parts: 3,
  tell: '아주 작고 높이 솟은 돔 등딱지', rivals: ['쿠터', '레드풋 육지거북'],
  model: turtleDome({ c: 0x4A443A, d: 0x36322A, f: 0x5C5648, k: 0.5, scutes: 5, scale: 1.4 }) });

add({ id: 'A047', kname: '쿠터', ename: 'River cooter', zone: '거북이 빌리지 카페', n: 26, parts: 4,
  tell: '납작한 유선형 등딱지 + 머리의 노란 줄무늬', rivals: ['늑대거북', '커먼머스크터틀', '악어거북'],
  model: turtleFlat({ c: 0x3A5A3E, d: 0x2A4430, f: 0x4A7048, k: 0.86, rows: 3, scale: 1.1 }) });

add({ id: 'A048', kname: '늑대거북', ename: 'Snapping Turtle', zone: '거북이 빌리지 카페', n: 4, parts: 4,
  tell: '몸에 비해 큰 머리 + 톱니 달린 긴 꼬리', rivals: ['악어거북', '쿠터', '마타마타거북'],
  model: turtleFlat({ c: 0x4A4238, d: 0x33302A, f: 0x5C5448, k: 0.95,
    headW: 0.72, neck: 0.5, tailLen: 0.8, rows: 3 }) });

add({ id: 'A049', kname: '악어거북', ename: 'Alligator snapping turtle', zone: '거북이 빌리지 카페', n: 2, parts: 5,
  tell: '등딱지 위 세 줄로 솟은 돌기', rivals: ['늑대거북', '쿠터'],
  model: turtleFlat({ c: 0x3E3830, d: 0x2A2620, f: 0x504838, k: 1.0,
    headW: 0.76, neck: 0.46, tailLen: 0.85, rows: 4 }) });

add({ id: 'A050', kname: '마타마타거북', ename: 'Mata Mata', zone: '거북이 빌리지 카페', n: 1, parts: 5,
  tell: '납작한 삼각 머리 + 목에 늘어진 술 장식', rivals: ['늑대거북', '쿠터'],
  model: turtleFlat({ c: 0x6E5C42, d: 0x503E2C, f: 0x7C6A4E, k: 0.92,
    headW: 0.9, neck: 0.62, tailLen: 0.5, rows: 3 }) });

add({ id: 'A051', kname: '긴코민물꼬치고기', ename: 'Longnose gar', zone: '거북이 빌리지 카페', n: 1, parts: 3,
  tell: '가늘고 긴 몸 + 바늘처럼 뾰족한 주둥이', rivals: [],
  model: fishy({ c: 0x5C6E5A, d: 0x445243, belly: 0xE0DCC4, finC: 0x6E8068, k: 1.0, scale: 0.95 }) });

/* ── 파충류 빌리지 · 파충류 ────────────────── */
add({ id: 'A052', kname: '그린아나콘다', ename: 'Green Anaconda', zone: '파충류 빌리지', n: 1, parts: 3,
  tell: '세 뱀 중 가장 굵다 + 올리브 녹색', rivals: ['레틱 파이톤', '레드테일보아'],
  model: snake({ c: 0x5A6E3E, d: 0x44542E, headC: 0x6A7E4A, thick: 0.86, count: 3, tailLen: 2.0, k: 1.0, scale: 0.86 }) });

add({ id: 'A053', kname: '레틱 파이톤', ename: 'Reticulated Python', zone: '파충류 빌리지', n: 1, parts: 3,
  tell: '중간 굵기 + 그물 무늬 + 가장 길다', rivals: ['그린아나콘다', '레드테일보아'],
  model: snake({ c: 0xC9A96E, d: 0x6E5A38, headC: 0xD8BC84, thick: 0.6, count: 4, tailLen: 2.5, k: 1.0, scale: 0.8 }) });

add({ id: 'A054', kname: '레드테일보아', ename: 'Boa Constrictor', zone: '파충류 빌리지', n: 1, parts: 3,
  tell: '가장 가늘고 꼬리 쪽이 붉다', rivals: ['그린아나콘다', '레틱 파이톤'],
  model: snake({ c: 0xB09A78, d: 0x8A7454, headC: 0xC0AC8A, thick: 0.44, count: 3, tailLen: 2.0, k: 1.0, scale: 1.0 }) });

add({ id: 'A055', kname: '테구', ename: 'Tegu', zone: '파충류 빌리지', n: 1, parts: 5,
  tell: '대형 + 굵은 꼬리 + 흑백 밴드 + 목주름', rivals: ['사바나모니터', '비어디 드래곤'],
  model: lizard({ c: 0x3E3A36, d: 0xE0DCD2, k: 1.15, tailW: 0.62, tailH: 0.44, tailLen: 1.8,
    belly: 0xC9C4B8, bobHead: true,
    extras: [{ type: 'dewlap', name: 'dewlap', w: 0.34, len: 0.28, d: 0.3,
               on: 'head', y: -0.3, z: 0.36, color: 0x54504A }],
    puzzle: ['head', 'body', 'legs', 'tail', 'dewlap'] }) });

add({ id: 'A056', kname: '사바나모니터', ename: 'Savannah Monitor', zone: '파충류 빌리지', n: 1, parts: 5,
  tell: '넓적한 몸통 + 강한 발톱 + 굵은 목', rivals: ['테구', '비어디 드래곤'],
  model: lizard({ c: 0x9A8A62, d: 0x7A6C48, k: 1.1, tailW: 0.5, tailH: 0.36, tailLen: 1.9,
    belly: 0xD8CCA8, studs: true, sideEye: false,
    puzzle: ['head', 'body', 'legs', 'tail'] }) });

add({ id: 'A057', kname: '비어디 드래곤', ename: 'Bearded Dragon', zone: '파충류 빌리지', n: 1, parts: 4,
  tell: '턱 아래와 옆구리를 두른 가시', rivals: ['테구', '레오파드게코', '사바나모니터'],
  model: lizard({ c: 0xC9A464, d: 0xA88448, k: 0.9, tailW: 0.4, tailH: 0.28, tailLen: 1.2,
    belly: 0xE8D8B0, crest: 0xA88448, bobHead: true,
    extras: [{ type: 'quills', name: 'beard', w: 0.5, d: 0.3, r: 0.05, len: 0.2,
               count: 10, on: 'head', y: -0.2, color: 0x8A6C3E }],
    puzzle: ['head', 'beard', 'body', 'tail'] }) });

add({ id: 'A058', kname: '레오파드게코', ename: 'Leopard gecko', zone: '파충류 빌리지', n: 3, parts: 4,
  tell: '통통하게 부푼 꼬리 + 표범 반점', rivals: ['크레스티드게코', '비어디 드래곤'],
  model: lizard({ c: 0xE8CE7A, d: 0x9A7E3E, k: 0.62, tailW: 0.52, tailH: 0.44, tailLen: 0.9,
    belly: 0xF4E8C0, scale: 1.3,
    puzzle: ['head', 'body', 'legs', 'tail'] }) });

add({ id: 'A059', kname: '크레스티드게코', ename: 'Crested gecko', zone: '파충류 빌리지', n: 1, parts: 4,
  tell: '눈 위로 솟은 속눈썹 모양 볏', rivals: ['레오파드게코', '비어디 드래곤'],
  model: lizard({ c: 0xB07A4A, d: 0x8A5C34, k: 0.6, tailW: 0.3, tailH: 0.24, tailLen: 1.0,
    belly: 0xD8B48A, scale: 1.3,
    extras: [{ type: 'crest', name: 'crest', w: 0.1, len: 0.2, gap: 0.2,
               on: 'head', y: 0.24, z: 0.1, color: 0xC9915E }],
    puzzle: ['head', 'crest', 'body', 'tail'] }) });

/* ── 파충류 빌리지 · 양서류 ────────────────── */
add({ id: 'A060', kname: '화이트트리프록', ename: "White's Tree Frog", zone: '파충류 빌리지', n: 1, parts: 3,
  tell: '매끈한 청록색 + 크고 둥근 발판', rivals: ['츄비프록', '파이어벨리뉴트'],
  model: frogling({ c: 0x5EA87E, belly: 0xE0EED8, web: 0x7CBE96, k: 1.0 }) });

add({ id: 'A061', kname: '츄비프록', ename: 'Chubby frog', zone: '파충류 빌리지', n: 1, parts: 3,
  tell: '통통한 갈색 몸에 굵은 크림색 줄', rivals: ['화이트트리프록', '파이어벨리뉴트'],
  model: frogling({ c: 0x8A5A38, belly: 0xE8D8B8, web: 0x9A6A44, dots: 0xD8B884, k: 0.95, scale: 1.3 }) });

add({ id: 'A062', kname: '파이어벨리뉴트', ename: 'Fire-bellied Newt', zone: '파충류 빌리지', n: 2, parts: 4,
  tell: '도롱뇽 몸매 + 주황색 배 + 긴 꼬리', rivals: ['화이트트리프록', '츄비프록'],
  model: lizard({ c: 0x2E332C, d: 0xE86A2E, k: 0.5, tailW: 0.26, tailH: 0.34, tailLen: 1.1,
    belly: 0xE86A2E, scale: 1.35,
    puzzle: ['head', 'body', 'legs', 'tail'] }) });

})(typeof window !== 'undefined' ? window : globalThis);
