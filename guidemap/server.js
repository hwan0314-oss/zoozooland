const express = require('express');
const fs = require('fs');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = 3000;

// 미들웨어
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.static(__dirname));

// FACILITIES 데이터 저장 API
app.post('/api/save-facilities', (req, res) => {
  try {
    const { facilities } = req.body;

    if (!Array.isArray(facilities)) {
      return res.status(400).json({ error: 'Invalid data format' });
    }

    // index.html 파일 읽기
    const indexPath = path.join(__dirname, 'index.html');
    let content = fs.readFileSync(indexPath, 'utf8');

    // FACILITIES 배열 부분 찾아서 교체
    const facilitiesJson = JSON.stringify(facilities, null, 2);
    const newFacilitiesBlock = `const FACILITIES = ${facilitiesJson};`;

    // 정규식으로 const FACILITIES = [ ... ]; 부분 찾기
    const regex = /const FACILITIES = \[[\s\S]*?\];/;

    if (!regex.test(content)) {
      return res.status(500).json({ error: 'FACILITIES 배열을 찾을 수 없습니다' });
    }

    content = content.replace(regex, newFacilitiesBlock);

    // 파일 저장
    fs.writeFileSync(indexPath, content, 'utf8');

    console.log(`✅ FACILITIES 업데이트 완료 (${facilities.length}개 항목)`);

    res.json({
      success: true,
      message: `${facilities.length}개 시설이 저장되었습니다`,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('❌ 저장 실패:', error);
    res.status(500).json({
      error: '파일 저장 중 오류가 발생했습니다',
      details: error.message
    });
  }
});

// 현재 FACILITIES 데이터 조회 API
app.get('/api/get-facilities', (req, res) => {
  try {
    const indexPath = path.join(__dirname, 'index.html');
    const content = fs.readFileSync(indexPath, 'utf8');

    // FACILITIES 배열 추출
    const match = content.match(/const FACILITIES = (\[[\s\S]*?\]);/);

    if (!match) {
      return res.status(500).json({ error: 'FACILITIES 데이터를 찾을 수 없습니다' });
    }

    const facilities = eval(match[1]); // 주의: 신뢰할 수 있는 코드에서만 사용
    res.json({ facilities });

  } catch (error) {
    console.error('❌ 조회 실패:', error);
    res.status(500).json({ error: error.message });
  }
});

// 서버 시작
app.listen(PORT, () => {
  console.log('\n🦁 쥬쥬랜드 관리 서버 실행 중');
  console.log(`📍 사용자 페이지: http://localhost:${PORT}/index.html`);
  console.log(`⚙️  관리자 페이지: http://localhost:${PORT}/admin.html`);
  console.log(`\n종료하려면 Ctrl+C를 누르세요\n`);
});
