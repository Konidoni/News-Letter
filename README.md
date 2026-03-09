# Samsung DA Executive Briefing

삼성전자 DA(가전) 부문 임원을 위한 자동화 뉴스 브리핑 대시보드.

🔗 **Live:** https://konidoni.github.io/News-Letter/

---

## 개요

매일 자동으로 최근 24시간 내 영문 보도자료를 수집하고, 경쟁사 동향과 시장 트렌드를 분석해 대시보드로 배포합니다.

- **수집:** DuckDuckGo Search (무료, 토큰 없음)
- **분석:** Claude haiku (Takeaways 생성 1회만)
- **배포:** GitHub Actions → GitHub Pages

---

## 모니터링 키워드

| 카테고리 | 주요 키워드 |
|---|---|
| Samsung Bespoke | samsung bespoke, refrigerator, washer, AI launch |
| Samsung DA | samsung home appliance, samsung electronics |
| Samsung Jet Bot | samsung jet bot, robot vacuum |
| Technology Trend | smart home appliance, AI appliance, IoT, Matter |
| Market Dynamics | home appliance market, kitchen appliance, industry trend |
| Competitor Analysis | LG, Whirlpool, Haier, Bosch, Electrolux, Dyson, Roomba |

수집 대상: CNET, The Verge, Engadget, TechCrunch, Reuters, Bloomberg, WSJ, PCMag, TechRadar, Wirecutter, rtings.com 등 영문 매체

---

## 파일 구조

```
├── fetch_news.py          # 뉴스 수집 + Takeaways 생성
├── build_dashboard.py     # HTML 대시보드 빌드
├── daily_workflow.yml     # GitHub Actions 워크플로우
├── data/
│   ├── manifest.json      # 날짜 아카이브 목록 (최대 30일)
│   └── YYYY-MM-DD.json    # 일별 수집 결과
└── index.html             # 빌드된 대시보드 (자동 생성)
```

---

## 실행 흐름

```
DuckDuckGo (20쿼리 × 최대 20건)
    ↓
중복 제거 (URL + 제목 해시)
    ↓
Claude haiku 1회 → Top 3 Takeaways
    ↓
data/YYYY-MM-DD.json 저장
    ↓
build_dashboard.py → index.html
    ↓
GitHub Pages 배포
```

---

## 설치 및 로컬 실행

```bash
pip install anthropic duckduckgo-search

export ANTHROPIC_API_KEY=sk-ant-...

python fetch_news.py
python build_dashboard.py
```

---

## 자동 실행 (GitHub Actions)

`daily_workflow.yml`을 `.github/workflows/`에 위치시키면 매일 **16:00 KST** 자동 실행됩니다.

수동 실행: GitHub repo → Actions 탭 → `Daily Samsung DA Briefing` → **Run workflow**

**필요한 Secret:**
- `ANTHROPIC_API_KEY` → GitHub repo Settings → Secrets → Actions

---

## 비용

| 항목 | 비용 |
|---|---|
| DuckDuckGo 검색 | 무료 |
| Claude haiku (Takeaways 1회) | ~$0.001/일 |
| GitHub Actions | 무료 (public repo) |
| GitHub Pages | 무료 |

**월 예상 비용: $0.03 미만**
