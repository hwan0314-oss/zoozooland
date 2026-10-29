/* Tailwind 빌드 설정 — 예전에는 cdn.tailwindcss.com(개발용 런타임)을 썼고,
   지금은 실제 사용하는 클래스만 모아 css/tailwind.css 로 미리 빌드합니다.
   JS·build.py 안의 HTML 문자열에서 쓰는 클래스도 함께 스캔합니다. */
module.exports = {
  content: {
    relative: true,
    files: ['./index.html', './drawer.html', './js/**/*.js', './build.py'],
  },
  theme: { extend: {} },
  plugins: [],
};
