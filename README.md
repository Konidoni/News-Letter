# Samsung DA — Global Appliance Strategy Briefing
**매일 오후 3시 KST 자동 업데이트되는 임원용 전략 대시보드**

## 뉴스 수집 범위 (7개 카테고리)
| 카테고리 | 커버리지 |
|---|---|
| 🔵 삼성 가전 (Samsung DA) | Samsung Bespoke, SmartThings, DA 실적·전략 |
| 🔴 경쟁사 동향 | LG, Haier, Whirlpool, Bosch, Electrolux |
| 🟠 제품 리뷰·순위 | Best refrigerator/washer/AC 2025, Editor's Choice |
| 🔵 기술 트렌드 | AI appliance, Matter 3.0, LFP 배터리, 에너지 규제 |
| 🟡 매크로·정책 | 미국 관세, 무역 정책, IRA 인센티브 |
| 🟢 시장 동향 | 글로벌/인도/동남아 가전 시장 성장 |
| 🟣 공급망 | 희토류, 반도체, 생산기지 이전 |

## 🚀 설치 (10분)

### 1. API 키 발급
- NewsAPI: https://newsapi.org/register (무료)
- Anthropic: https://console.anthropic.com

### 2. GitHub 저장소 생성
https://github.com/new → `samsung-da-briefing` (Private) → 파일 전체 업로드

### 3. Secret 키 등록
Settings → Secrets and variables → Actions → New repository secret
- `NEWS_API_KEY`
- `ANTHROPIC_API_KEY`

### 4. GitHub Pages 활성화
Settings → Pages → Branch: gh-pages / root → Save

### 5. 첫 실행
Actions → Daily Samsung DA Briefing → Run workflow
→ 약 3분 후 https://[username].github.io/samsung-da-briefing/ 에서 확인

## ⏰ 스케줄
매일 14:00 KST 자동 수집·분석 → 15:00 브리핑 준비 완료

## 💰 예상 비용
- NewsAPI 무료 플랜: $0
- Claude API Sonnet: ~$45~90/월
- Haiku 모델로 교체 시: ~$10/월
