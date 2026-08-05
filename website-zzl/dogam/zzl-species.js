/* ============================================================
   ZZL SPECIES SPEC  v1.0 — Phase 1 (12종)
   각 항목은 ZZL.build(spec.model) 로 3D 모델이 된다.

   필드
     id      동물ID (마스터 시트와 일치)
     kname   국명 / ename 영명
     zone    게임 구역
     n       개체수 (출현 가중치에 사용)
     parts   퍼즐 부위 수 (3~5)
     tell    식별 포인트 — 퍼즐 오답 조각 구성 기준
     rivals  같은 구역 근연종 (오답 조각 출처)
     model   조립 사양
   ============================================================ */
(function (global) {
'use strict';

var S = [

/* ── 알파카 ─────────────────────────────────────── */
{
  id: 'A001', kname: '알파카', ename: 'Alpaca', zone: '알파카 빌리지', n: 13,
  parts: 4, tell: '뭉친 털 + 앞머리 + 짧은 삼각 귀',
  rivals: ['라마'],
  model: {
    scale: 0.92,
    body: { type: 'quad', w: 1.44, h: 1.16, d: 1.9, y: 1.5, color: 0xF6E9CE, dark: 0xE0CBA2, sc: 2, sr: 3 },
    neck: { type: 'long', w: 0.56, h: 1.0, y: 2.0, z: 0.72, color: 0xD8B588, collar: 0xF6E9CE },
    head: { type: 'muzzle', w: 0.86, h: 0.76, d: 0.92, color: 0xD8B588, y: 1.16, z: 0.06,
            muzzle: { w: 0.52, h: 0.42, d: 0.36 }, nose: 0x453A2F, mouth: true },
    eyes: { size: 0.22, gap: 0.24, y: 0.02, z: 0.47 },
    ears: { type: 'point', w: 0.1, len: 0.4, gap: 0.28, y: 0.42, spread: 0.2, color: 0xD8B588 },
    legs: { type: 'post', pos: [[0.46, 0.52], [-0.46, 0.52], [0.42, -0.56], [-0.42, -0.56]],
            r: 0.145, len: 0.86, y: 0.92, color: 0xD8B588, foot: 'hoof', footColor: 0x453A2F },
    tail: { type: 'tuft', w: 0.3, y: 1.9, z: -1.0, color: 0xF6E9CE },
    extras: [{ type: 'crest', name: 'fringe', w: 0.3, len: 0.3, gap: 0.3, on: 'head', y: 0.42, z: 0.3,
               color: 0xE0CBA2, puzzle: false }],
    anim: { bob: 0.04, headTurn: 0.28, neckSway: 0.05, earTwitch: true, blink: 0.52 },
    puzzle: ['head', 'body', 'legs', 'ears']
  }
},

/* ── 라마 ───────────────────────────────────────── */
{
  id: 'A002', kname: '라마', ename: 'Llama', zone: '대동물 방목장', n: 1,
  parts: 5, tell: '바나나형 큰 귀 + 더 긴 목 + 털이 없는 매끈한 머리',
  rivals: ['알파카'],
  model: {
    scale: 0.86,
    body: { type: 'quad', w: 1.34, h: 1.06, d: 2.0, y: 1.62, color: 0xE8D8B8, dark: 0xD2BE96, sc: 2, sr: 3 },
    neck: { type: 'long', w: 0.5, h: 1.5, y: 2.05, z: 0.78, color: 0xE8D8B8 },
    head: { type: 'muzzle', w: 0.74, h: 0.66, d: 1.0, color: 0xE8D8B8, y: 1.62, z: 0.1,
            muzzle: { w: 0.46, h: 0.38, d: 0.42, color: 0xF6EEDC }, nose: 0x453A2F, mouth: true },
    eyes: { size: 0.2, gap: 0.22, y: 0.04, z: 0.51 },
    ears: { type: 'banana', w: 0.13, len: 0.62, gap: 0.24, y: 0.36, color: 0xE8D8B8 },
    legs: { type: 'post', pos: [[0.44, 0.56], [-0.44, 0.56], [0.4, -0.6], [-0.4, -0.6]],
            r: 0.14, len: 1.06, y: 1.06, color: 0xE8D8B8, foot: 'hoof', footColor: 0x453A2F },
    tail: { type: 'tuft', w: 0.26, y: 2.0, z: -1.06, color: 0xE8D8B8 },
    anim: { bob: 0.035, headTurn: 0.3, neckSway: 0.06, earTwitch: true, blink: 0.5 },
    puzzle: ['head', 'neck', 'body', 'legs', 'ears']
  }
},

/* ── 꽃사슴 ─────────────────────────────────────── */
{
  id: 'A003', kname: '꽃사슴', ename: 'Formosan sika deer', zone: '대동물 방목장', n: 4,
  parts: 5, tell: '가지뿔 + 등의 흰 반점',
  rivals: ['무플론', '면양'],
  model: {
    scale: 0.9,
    body: { type: 'quad', w: 1.0, h: 0.92, d: 1.86, y: 1.42, color: 0xB98A54, dark: 0xA0743F,
            belly: 0xEDE0C8, sc: 2, sr: 3 },
    neck: { type: 'long', w: 0.42, h: 0.86, y: 1.8, z: 0.74, color: 0xB98A54 },
    head: { type: 'muzzle', w: 0.6, h: 0.56, d: 0.88, color: 0xB98A54, y: 0.98, z: 0.12,
            muzzle: { w: 0.4, h: 0.34, d: 0.34 }, nose: 0x2A2620, mouth: true },
    eyes: { size: 0.17, gap: 0.2, y: 0.04, z: 0.45 },
    ears: { type: 'point', w: 0.13, len: 0.42, gap: 0.3, y: 0.3, spread: 0.72, color: 0xB98A54 },
    legs: { type: 'post', pos: [[0.34, 0.56], [-0.34, 0.56], [0.32, -0.6], [-0.32, -0.6]],
            r: 0.11, len: 0.96, y: 0.96, color: 0xB98A54, foot: 'hoof', footColor: 0x2A2620 },
    tail: { type: 'tuft', w: 0.2, y: 1.72, z: -1.0, color: 0xEDE0C8 },
    extras: [
      { type: 'antler', name: 'antler', w: 0.11, len: 0.66, gap: 0.2, on: 'head', y: 0.28, z: -0.06, color: 0x8E6B3E },
      { type: 'spots', name: 'spots', size: 0.13, color: 0xF2E8D2, puzzle: false, y: 0.47,
        at: [[0.3, 0, 0.5], [-0.3, 0, 0.5], [0.34, 0, 0], [-0.34, 0, 0], [0.28, 0, -0.5], [-0.28, 0, -0.5]] }
    ],
    anim: { bob: 0.035, headTurn: 0.34, neckSway: 0.06, earTwitch: true, blink: 0.46 },
    puzzle: ['head', 'antler', 'body', 'legs', 'ears']
  }
},

/* ── 일본원숭이 ─────────────────────────────────── */
{
  id: 'A004', kname: '일본원숭이', ename: 'Japanese Macaque', zone: '원숭이 빌리지', n: 5,
  parts: 5, tell: '붉은 얼굴 + 아주 짧은 꼬리',
  rivals: ['다람쥐원숭이'],
  model: {
    scale: 0.94,
    body: { type: 'upright', w: 1.02, h: 1.2, d: 0.86, y: 1.16, color: 0xA08B6E, belly: 0xD8C8A8 },
    neck: { type: 'short', w: 0.4, h: 0.24, y: 1.72, z: 0.06, color: 0xA08B6E },
    head: { type: 'box', w: 0.86, h: 0.78, d: 0.78, color: 0xA08B6E, y: 0.34, z: 0.02,
            studs: true, dark: 0x8A7658,
            muzzle: { w: 0.5, h: 0.44, d: 0.3, color: 0xD9756A, y: -0.14 }, nose: 0x5A3A34 },
    eyes: { size: 0.19, gap: 0.2, y: 0.1, z: 0.42 },
    ears: { type: 'round', w: 0.15, gap: 0.48, y: 0.06, z: -0.02, color: 0xC49A88, inner: 0xA07C6C },
    legs: { type: 'post', pos: [[0.36, 0.24], [-0.36, 0.24], [0.34, -0.3], [-0.34, -0.3]],
            r: 0.14, len: 0.56, y: 0.6, color: 0xA08B6E, foot: 'paw', footColor: 0x8A7658 },
    tail: { type: 'thin', r: 0.09, len: 0.4, count: 2, y: 1.06, z: -0.44, color: 0xA08B6E },
    extras: [{ type: 'spots', name: 'face', size: 0.4, color: 0xD9756A, puzzle: false, y: 0.16,
               at: [[0, 0, 0.4]] }],
    anim: { bob: 0.05, bobSpeed: 1.9, headTurn: 0.42, turnSpeed: 0.6, blink: 0.62, hop: 0.4 },
    puzzle: ['head', 'body', 'legs', 'ears', 'tail']
  }
},

/* ── 토끼 ───────────────────────────────────────── */
{
  id: 'A005', kname: '토끼', ename: 'Rabbit', zone: '파충류 빌리지', n: 30,
  parts: 3, tell: '아주 긴 귀 + 동그란 짧은 꼬리',
  rivals: ['기니피그', '친칠라'],
  model: {
    scale: 1.15,
    body: { type: 'quad', w: 0.86, h: 0.72, d: 1.14, y: 0.62, color: 0xF2EAD8, dark: 0xDED2B8,
            belly: 0xFFFBF2, sc: 2, sr: 2, studs: true },
    head: { type: 'box', w: 0.72, h: 0.62, d: 0.64, color: 0xF2EAD8, y: 0.98, z: 0.62,
            muzzle: { w: 0.4, h: 0.3, d: 0.22 }, nose: 0xD48C96 },
    eyes: { size: 0.19, gap: 0.22, y: 0.06, z: 0.34 },
    ears: { type: 'long', w: 0.17, len: 0.86, gap: 0.17, y: 0.3, spread: 0.14,
            color: 0xF2EAD8, inner: 0xE8B8BE },
    legs: { type: 'post', pos: [[0.3, 0.34], [-0.3, 0.34], [0.32, -0.34], [-0.32, -0.34]],
            r: 0.13, len: 0.26, y: 0.3, color: 0xF2EAD8, foot: 'paw', footColor: 0xDED2B8 },
    tail: { type: 'tuft', w: 0.24, y: 0.66, z: -0.6, color: 0xFFFBF2 },
    anim: { bob: 0.03, bobSpeed: 2.2, headTurn: 0.3, earTwitch: true, blink: 0.7, hop: 0.5 },
    puzzle: ['head', 'body', 'ears']
  }
},

/* ── 미어캣 ─────────────────────────────────────── */
{
  id: 'A006', kname: '미어캣', ename: 'Meerkat', zone: '파충류 빌리지', n: 7,
  parts: 4, tell: '두 발로 선 자세 + 눈 주위 검은 무늬',
  rivals: ['난쟁이몽구스', '프레리독'],
  model: {
    scale: 1.02,
    body: { type: 'upright', w: 0.58, h: 1.24, d: 0.52, y: 1.02, color: 0xC9A876, belly: 0xE8D6B0 },
    head: { type: 'snout', w: 0.56, h: 0.5, d: 0.48, color: 0xC9A876, y: 1.86, z: 0.04,
            snoutLen: 0.32, snoutColor: 0xD8BC90, nose: 0x2A2A2E, mask: 0x3A3128 },
    eyes: { size: 0.15, gap: 0.16, y: 0.06, z: 0.26 },
    ears: { type: 'round', w: 0.1, gap: 0.3, y: 0.1, z: -0.06, color: 0x3A3128 },
    legs: { type: 'post', pos: [[0.18, 0], [-0.18, 0]],
            r: 0.1, len: 0.42, y: 0.42, color: 0xC9A876, foot: 'paw', footColor: 0xB08E5E },
    tail: { type: 'thin', r: 0.09, len: 0.9, count: 3, y: 0.5, z: -0.28, color: 0xC9A876, stripe: 0xB08E5E },
    anim: { bob: 0.025, bobSpeed: 1.4, headTurn: 0.5, turnSpeed: 0.7, blink: 0.6, hop: 0.35 },
    puzzle: ['head', 'body', 'legs', 'tail']
  }
},

/* ── 사막여우 ───────────────────────────────────── */
{
  id: 'A007', kname: '사막여우', ename: 'Fennec Fox', zone: '파충류 빌리지', n: 5,
  parts: 4, tell: '몸에 비해 과장되게 큰 귀',
  rivals: ['라쿤', '페럿'],
  model: {
    scale: 1.06,
    body: { type: 'quad', w: 0.74, h: 0.6, d: 1.08, y: 0.66, color: 0xEBD5A8, dark: 0xD8BE8C,
            belly: 0xFAF0DC, sc: 2, sr: 2, studs: true },
    head: { type: 'snout', w: 0.64, h: 0.54, d: 0.56, color: 0xEBD5A8, y: 0.96, z: 0.6,
            snoutLen: 0.34, snoutColor: 0xF6E8C8, nose: 0x2A2A2E },
    eyes: { size: 0.17, gap: 0.18, y: 0.08, z: 0.3 },
    ears: { type: 'big', w: 0.34, len: 0.74, gap: 0.24, y: 0.3, spread: 0.24,
            color: 0xEBD5A8, inner: 0xF6E8C8 },
    legs: { type: 'post', pos: [[0.26, 0.32], [-0.26, 0.32], [0.26, -0.32], [-0.26, -0.32]],
            r: 0.1, len: 0.34, y: 0.36, color: 0xE0C79A, foot: 'paw', footColor: 0xD8BE8C },
    tail: { type: 'bushy', w: 0.34, len: 0.9, rings: 4, y: 0.62, z: -0.52,
            color: 0xEBD5A8, tip: 0x4A4038 },
    anim: { bob: 0.03, bobSpeed: 1.8, headTurn: 0.36, earTwitch: true, blink: 0.66, hop: 0.42 },
    puzzle: ['head', 'body', 'ears', 'tail']
  }
},

/* ── 라쿤 ───────────────────────────────────────── */
{
  id: 'A008', kname: '라쿤', ename: 'Raccoon', zone: '양 분유 체험장', n: 4,
  parts: 4, tell: '눈가 검은 마스크 + 고리 줄무늬 꼬리',
  rivals: ['코아티', '페럿'],
  model: {
    scale: 1.0,
    body: { type: 'quad', w: 0.86, h: 0.72, d: 1.16, y: 0.7, color: 0x8E8B84, dark: 0x6E6B66,
            belly: 0xB8B4AA, sc: 2, sr: 2, studs: true },
    head: { type: 'snout', w: 0.72, h: 0.6, d: 0.58, color: 0x9E9A92, y: 1.06, z: 0.64,
            snoutLen: 0.3, snoutColor: 0xD8D2C6, nose: 0x2A2A2E, mask: 0x33302C },
    eyes: { size: 0.17, gap: 0.2, y: 0.1, z: 0.31 },
    ears: { type: 'round', w: 0.14, gap: 0.34, y: 0.28, z: -0.06, color: 0x9E9A92, inner: 0xD8D2C6 },
    legs: { type: 'post', pos: [[0.3, 0.34], [-0.3, 0.34], [0.3, -0.36], [-0.3, -0.36]],
            r: 0.12, len: 0.36, y: 0.4, color: 0x6E6B66, foot: 'paw', footColor: 0x4A4844 },
    tail: { type: 'bushy', w: 0.36, len: 1.0, rings: 5, y: 0.72, z: -0.56,
            color: 0x9E9A92, stripe: 0x3A3733 },
    anim: { bob: 0.03, bobSpeed: 1.7, headTurn: 0.34, blink: 0.58, hop: 0.42 },
    puzzle: ['head', 'body', 'legs', 'tail']
  }
},

/* ── 에뮤 ───────────────────────────────────────── */
{
  id: 'A009', kname: '에뮤', ename: 'Emu', zone: '양 분유 체험장', n: 1,
  parts: 4, tell: '아주 긴 다리 + 큰 몸 + 작은 머리',
  rivals: ['거위', '오리'],
  model: {
    scale: 0.72,
    body: { type: 'bird', w: 1.3, h: 1.5, d: 1.5, y: 2.0, color: 0x7A6B58, belly: 0x8E8070 },
    neck: { type: 'long', w: 0.36, h: 1.5, y: 2.5, z: 0.36, color: 0x5E5348 },
    head: { type: 'box', w: 0.46, h: 0.42, d: 0.56, color: 0x4A4238, y: 1.66, z: 0.04,
            muzzle: { w: 0.22, h: 0.16, d: 0.3, color: 0x3A342C, y: -0.06 }, nose: 0x2A2620 },
    eyes: { size: 0.15, gap: 0.19, y: 0.06, z: 0.28 },
    legs: { type: 'bird', pos: [[0.32, 0], [-0.32, 0]],
            r: 0.15, len: 1.3, y: 1.3, color: 0x6E6254 },
    anim: { bob: 0.04, bobSpeed: 1.5, headTurn: 0.5, turnSpeed: 0.55, neckSway: 0.07, blink: 0.6, hop: 0.5 },
    puzzle: ['head', 'neck', 'body', 'legs']
  }
},

/* ── 청금강앵무 ─────────────────────────────────── */
{
  id: 'A010', kname: '청금강앵무새', ename: 'Blue-and-yellow Macaw', zone: '파충류 빌리지', n: 1,
  parts: 5, tell: '대형 + 청·황 배색 + 아주 긴 꼬리',
  rivals: ['할리퀸금강앵무새', '코뉴어', '아마존앵무새'],
  model: {
    scale: 0.92,
    body: { type: 'bird', w: 1.08, h: 1.34, d: 0.92, y: 1.12, color: 0x3A6FD8, belly: 0xF0B62B },
    head: { type: 'parrot', w: 0.98, h: 0.86, d: 0.9, color: 0x3A6FD8, dark: 0x27509E,
            y: 2.16, z: 0.02, studs: true, face: 0xF7F0E2, beak: 0x2A2A2E },
    eyes: { size: 0.2, gap: 0.36, y: 0.1, z: 0.46 },
    legs: { type: 'bird', pos: [[0.24, 0.06], [-0.24, 0.06]],
            r: 0.09, len: 0.32, y: 0.45, color: 0x5A5048 },
    tail: { type: 'feather', w: 0.56, len: 1.1, y: 0.62, z: -0.44, tilt: -0.36,
            color: 0x3A6FD8, dark: 0x27509E },
    extras: [
      { type: 'crest', name: 'crest', w: 0.16, len: 0.3, gap: 0.22, on: 'head', y: 0.44, z: -0.1, color: 0x27509E },
      { type: 'wings', name: 'wings', w: 0.16, len: 0.92, d: 0.66, gap: 0.62, y: 1.6,
        color: 0x27509E, tip: 0xF0B62B }
    ],
    anim: { bob: 0.035, bobSpeed: 2.0, headTurn: 0.4, turnSpeed: 0.6, jerk: 0.32,
            flap: 0.26, blink: 0.65, hop: 0.55 },
    puzzle: ['head', 'body', 'wings', 'tail', 'legs']
  }
},

/* ── 바다악어 ───────────────────────────────────── */
{
  id: 'A011', kname: '바다악어', ename: 'Saltwater Crocodile', zone: '악어 빌리지', n: 1,
  parts: 5, tell: '넓고 두꺼운 주둥이 (엘리게이터보다 뾰족)',
  rivals: ['엘리게이터', '펄스가비알'],
  model: {
    scale: 0.86,
    body: { type: 'lowLong', w: 1.5, h: 0.95, d: 1.9, y: 1.02, color: 0x57B04A, dark: 0x3E8C36,
            belly: 0xF3E4B0, studs: true },
    head: { type: 'croc', w: 1.28, h: 0.92, d: 1.0, color: 0x57B04A, dark: 0x3E8C36,
            y: 0.76, z: 1.42, snout: { w: 1.0, h: 0.42, d: 1.15 }, teeth: 4, studs: true },
    eyes: { size: 0.26, gap: 0.38, y: 0.5, z: 0.33 },
    legs: { type: 'sprawl', pos: [[0.72, 0.62], [-0.72, 0.62], [0.72, -0.6], [-0.72, -0.6]],
            r: 0.19, len: 0.56, y: 0.55, color: 0x3E8C36 },
    tail: { type: 'segment', w: 0.95, h: 0.72, len: 1.8, count: 3, y: 1.02, z: -1.0,
            color: 0x57B04A, dark: 0x3E8C36, crest: 0x3E8C36 },
    anim: { bob: 0.04, bobSpeed: 1.7, headTurn: 0.18, turnSpeed: 0.45,
            jaw: 0.38, tailWave: 0.12, blink: 0.5, hop: 0.42 },
    puzzle: ['head', 'body', 'legs', 'tail', 'jaw']
  }
},

/* ── 설가타 ─────────────────────────────────────── */
{
  id: 'A012', kname: '설가타', ename: 'African Spurred Tortoise', zone: '거북이 빌리지 방사장', n: 19,
  parts: 4, tell: '대형 돔 등딱지 + 굵은 기둥 다리',
  rivals: ['레드풋 육지거북', '쿠터'],
  model: {
    scale: 1.0,
    body: { type: 'shell', w: 2.2, h: 0.86, y: 0.92, color: 0xC9A05C, dark: 0xA07C42,
            scutes: 7, top: true, seg: 8 },
    neck: { type: 'fwd', w: 0.5, h: 0.5, y: 0.72, z: 0.86, color: 0xB8945A },
    head: { type: 'turtle', w: 0.56, h: 0.5, d: 0.5, color: 0xB8945A, dark: 0x6A5638, y: 0.02, z: 0.46 },
    eyes: { size: 0.14, gap: 0.19, y: 0.08, z: 0.3 },
    legs: { type: 'column', pos: [[0.72, 0.62], [-0.72, 0.62], [0.72, -0.62], [-0.72, -0.62]],
            r: 0.24, len: 0.5, y: 0.62, color: 0xB8945A, footColor: 0x8E7040 },
    tail: { type: 'stub', r: 0.14, len: 0.3, y: 0.72, z: -1.0, color: 0xB8945A },
    anim: { bob: 0.015, bobSpeed: 0.9, headTurn: 0.34, turnSpeed: 0.3,
            headBob: { rate: 0.16, amt: 0.24 }, blink: 0.38, hop: 0.22 },
    puzzle: ['head', 'body', 'legs', 'tail']
  }
}

];

global.ZZL_SPECIES = S;
})(typeof window !== 'undefined' ? window : globalThis);
