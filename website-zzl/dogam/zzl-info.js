/* ============================================================
   ZZL 도감 백과사전 — zzl-info.js
   Phase 1 (A001–A012): 학명·생태·보전 정보 포함
   Phase 2–3 (A013–A062): 학명만 수록, 생태·보전은 사육사 감수 후 추가 예정

   ※ 모든 내용은 1차 출처(ADW, IUCN 등) 기반이나
     현장 사육사 감수 전이므로 공개 전 검수 필수

   ZZL_INFO[id] = { sname, iucn, eco, obs }
   ============================================================ */
(function (global) {
'use strict';

global.ZZL_INFO = {

/* ══ Phase 1 ═══════════════════════════════════════════════ */

'A001': {
  sname: 'Vicugna pacos',
  iucn: '가축화 종 (IUCN 미등재) · 야생 조상 비쿠냐 <em>LC</em>',
  eco: '남아메리카 안데스 고원(해발 3,500~5,000m)의 건조한 초원에서 10~20마리씩 무리 지어 삽니다. 3개의 위를 통해 거친 섬유소를 효율적으로 소화하며, 경계 시 침을 뱉는 행동으로도 유명합니다.',
  obs: '앞머리 모양과 짧은 삼각형 귀, 뭉쳐있는 풍성한 털이 라마와 구별되는 핵심입니다.'
},

'A002': {
  sname: 'Lama glama',
  iucn: '가축화 종 (IUCN 미등재)',
  eco: '안데스 고원에서 5,000년 이상 짐 운반용으로 길들여진 종입니다. 알파카보다 크고 목이 길며, 25~30kg 짐을 지고 험한 산길을 걷습니다. 위협을 느끼면 침을 뱉거나 발을 구릅니다.',
  obs: '바나나처럼 위로 굽어진 크고 긴 귀와 길고 매끈한 목이 가장 확실한 구분입니다.'
},

'A003': {
  sname: 'Cervus nippon',
  iucn: 'IUCN <em>LC</em> (일부 아종 취약) · CITES 부속서 I(일부 아종)',
  eco: '동아시아 온대림에 서식하며 여름에는 흰 반점이 선명하고 겨울에는 흐려집니다. 수컷만 뿔이 있으며 매년 봄 탈각 후 벨벳 상태로 새 뿔이 자랍니다.',
  obs: '흰 반점 무늬와 엉덩이의 흰 패치가 한눈에 보이는 포인트입니다. 수컷만 가지뿔이 있습니다.'
},

'A004': {
  sname: 'Macaca fuscata',
  iucn: 'IUCN <em>LC</em>',
  eco: '현존 영장류 중 가장 고위도(북위 41°)에 사는 종입니다. 겨울에 온천에 몸을 담그는 "목욕 원숭이"로 유명하며, 무리 안에 엄격한 위계질서가 있습니다.',
  obs: '붉은 민낯과 짧은 꼬리가 특징입니다. 어른이 될수록 얼굴이 더 빨개집니다.'
},

'A005': {
  sname: 'Oryctolagus cuniculus',
  iucn: 'IUCN <em>NT</em> (야생 개체군) · 가축화 품종 미등재',
  eco: '이베리아 반도 원산으로 지중해 저초지에서 땅굴을 파고 집단 생활을 합니다. 뒷다리가 앞다리보다 길어 폭발적인 도약이 가능하며, 큰 귀의 혈관망으로 체온을 조절합니다.',
  obs: '길고 직립하는 귀와 짧은 솜뭉치 꼬리가 특징입니다. 토끼와 산토끼(Lepus)는 다른 속입니다.'
},

'A006': {
  sname: 'Suricata suricatta',
  iucn: 'IUCN <em>LC</em>',
  eco: '아프리카 칼라하리 사막에서 5~30마리 집단생활을 합니다. 보초 개체가 두 발로 서서 주변을 감시하며, 포식자 종류에 따라 다른 경보음을 냅니다. 독사에 내성이 있어 위험한 먹이도 사냥합니다.',
  obs: '두 발로 서는 직립 자세와 눈 주위 검은 무늬가 핵심입니다.'
},

'A007': {
  sname: 'Vulpes zerda',
  iucn: 'IUCN <em>LC</em> · CITES 부속서 II',
  eco: '북아프리카 사하라 최건조 지역에 서식합니다. 몸에 비해 매우 큰 귀(약 15cm)는 방열 기관이자 청각 기관으로, 땅속 먹이를 소리로 감지합니다. 발바닥에 두꺼운 털이 나 있어 뜨거운 모래 위를 걷습니다.',
  obs: '몸집에 비해 압도적으로 큰 두 귀가 세계에서 가장 작은 여우라는 사실을 감추게 만듭니다.'
},

'A008': {
  sname: 'Procyon lotor',
  iucn: 'IUCN <em>LC</em>',
  eco: '북아메리카 원산으로, 현재 유럽·일본·한국 등 전 세계에 외래종으로 분포합니다. 먹이를 물에 적시며 먹는 행동이 독특하며, 앞발의 촉각이 매우 발달했습니다.',
  obs: '눈가의 검은 마스크 무늬와 꼬리의 고리 줄무늬 5~7개가 가장 확실한 특징입니다.'
},

'A009': {
  sname: 'Dromaius novaehollandiae',
  iucn: 'IUCN <em>LC</em>',
  eco: '오스트레일리아 내륙 초원에 서식하는 날지 못하는 대형 조류로, 타조 다음으로 키가 큽니다(최대 1.9m). 수컷이 알을 8주간 품고 새끼를 기르는 특이한 육아 패턴이 있습니다.',
  obs: '매우 긴 다리와 작은 흔적날개, 헝클어진 갈색 깃털 뭉치가 특징입니다.'
},

'A010': {
  sname: 'Ara ararauna',
  iucn: 'IUCN <em>LC</em> · CITES 부속서 II',
  eco: '남아메리카 아마존 열대우림과 습지에 서식하는 대형 앵무새입니다. 야생에서 무리를 지어 야자 열매를 먹으며, 점토 절벽에 모여 미네랄을 보충하는 행동이 관찰됩니다. 매우 영리하며 수십 년 함께 삽니다.',
  obs: '선명한 파란색 등과 노란색 배색, 그리고 긴 꼬리가 타 앵무새와 확연히 구별됩니다.'
},

'A011': {
  sname: 'Crocodylus porosus',
  iucn: 'IUCN <em>LC</em> (개체수 회복 중) · CITES 부속서 I/II',
  eco: '인도 동해안부터 오스트레일리아 북부까지 기수역·하구·연안에 서식하는 현존 최대 파충류입니다. 수컷은 최대 7m, 1,000kg에 달합니다. 강력한 턱과 매복 전술로 대형 포유류까지 사냥합니다.',
  obs: '넓고 두꺼운 주둥이가 미국 엘리게이터보다 더 뾰족하며, 입을 다물어도 아랫니가 보입니다.'
},

'A012': {
  sname: 'Centrochelys sulcata',
  iucn: 'IUCN <em>VU</em> (취약) · CITES 부속서 II',
  eco: '아프리카 사하라 사막 남쪽 사헬 지대에 서식하며, 갈라파고스·알다브라에 이어 세 번째로 큰 육지거북입니다. 성체 수컷은 최대 100kg이며 100년 이상 삽니다. 낮의 극심한 더위를 피해 땅굴을 파고 들어갑니다.',
  obs: '등딱지의 두꺼운 돔 형태와 굵은 기둥 같은 다리가 가장 확실한 구분 포인트입니다.'
},

/* ══ Phase 2–3 (학명 수록, 생태·보전 감수 예정) ════════════ */

'A013': { sname: 'Ovis aries' },
'A014': { sname: 'Capra hircus' },
'A015': { sname: 'Capra hircus (Boer)' },
'A016': { sname: 'Capra hircus' },
'A017': { sname: 'Ovis aries musimon' },
'A018': { sname: 'Ovis dalli' },
'A019': { sname: 'Equus asinus' },
'A020': { sname: 'Equus caballus' },
'A021': { sname: 'Genetta genetta' },
'A022': { sname: 'Saimiri sciureus' },
'A023': { sname: 'Cavia porcellus' },
'A024': { sname: 'Chinchilla lanigera' },
'A025': { sname: 'Octodon degus' },
'A026': { sname: 'Erinaceus amurensis' },
'A027': { sname: 'Mustela putorius furo' },
'A028': { sname: 'Petaurus breviceps' },
'A029': { sname: 'Trichosurus vulpecula' },
'A030': { sname: 'Cynomys ludovicianus' },
'A031': { sname: 'Helogale parvula' },
'A032': { sname: 'Nasua nasua' },
'A033': { sname: 'Hystrix brachyura' },
'A034': { sname: 'Melopsittacus undulatus' },
'A035': { sname: 'Agapornis sp.' },
'A036': { sname: 'Ara chloropterus' },
'A037': { sname: 'Amazona sp.' },
'A038': { sname: 'Eclectus roratus' },
'A039': { sname: 'Pyrrhura molinae' },
'A040': { sname: 'Pionites leucogaster' },
'A041': { sname: 'Anas platyrhynchos domesticus' },
'A042': { sname: 'Anser domesticus' },
'A043': { sname: 'Alligator mississippiensis' },
'A044': { sname: 'Tomistoma schlegelii' },
'A045': { sname: 'Chelonoidis carbonarius' },
'A046': { sname: 'Sternotherus odoratus' },
'A047': { sname: 'Pseudemys concinna' },
'A048': { sname: 'Chelydra serpentina' },
'A049': { sname: 'Macrochelys temminckii' },
'A050': { sname: 'Chelus fimbriata' },
'A051': { sname: 'Lepisosteus osseus' },
'A052': { sname: 'Eunectes murinus' },
'A053': { sname: 'Malayopython reticulatus' },
'A054': { sname: 'Boa constrictor' },
'A055': { sname: 'Salvator merianae' },
'A056': { sname: 'Varanus exanthematicus' },
'A057': { sname: 'Pogona vitticeps' },
'A058': { sname: 'Eublepharis macularius' },
'A059': { sname: 'Correlophus ciliatus' },
'A060': { sname: '—' },
'A061': { sname: 'Kaloula pulchra' },
'A062': { sname: 'Cynops pyrrhogaster' }

};

})(typeof window !== 'undefined' ? window : globalThis);
