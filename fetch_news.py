"""
Samsung DA Strategy Briefing — News Fetcher + Claude AI Analyzer
Runs daily at 14:00 KST via GitHub Actions.
Outputs: news_data.json

Coverage:
  1. Competitor Analysis  — LG, Haier, Whirlpool, Bosch, Electrolux
  2. Technology Trend     — AI appliance, Matter, Energy/LFP
  3. Samsung DA           — Samsung home appliance, Bespoke, SmartThings
  4. Product Reviews      — Best appliance picks, editor's choice, top-rated
  5. Macro / Policy       — US tariff, trade policy, IRA incentive
  6. Market Dynamics      — Global appliance market growth
  7. Supply Chain         — Rare earth, semiconductor, manufacturing
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone
import anthropic

# ── CONFIG ──────────────────────────────────────────────────────────────────
NEWS_API_KEY   = os.environ["NEWS_API_KEY"]
ANTHROPIC_KEY  = os.environ["ANTHROPIC_API_KEY"]
OUTPUT_FILE    = "news_data.json"
MAX_ARTICLES   = 14

KST       = timezone(timedelta(hours=9))
NOW       = datetime.now(KST)
FROM_DATE = (NOW - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")


# ── SEARCH QUERIES ───────────────────────────────────────────────────────────
QUERIES = [
    # 1. 경쟁사 동향
    {
        "category": "Competitor Analysis",
        "queries": [
            "LG Electronics home appliance strategy 2025",
            "Haier appliance North America Europe expansion",
            "Whirlpool business strategy earnings",
            "Bosch BSH home appliance market",
            "Electrolux Midea appliance strategy",
        ],
        "max_per_query": 2,
    },
    # 2. 기술 트렌드
    {
        "category": "Technology Trend",
        "queries": [
            "AI home appliance smart home 2025",
            "Matter smart home interoperability standard",
            "LFP battery home appliance energy storage",
            "Google Home Amazon Alexa appliance integration",
            "energy efficient appliance EU regulation",
        ],
        "max_per_query": 2,
    },
    # 3. 삼성전자 가전 사업
    {
        "category": "Samsung DA",
        "queries": [
            "Samsung home appliance Bespoke 2025",
            "Samsung SmartThings AI home",
            "Samsung refrigerator washer new product launch",
            "Samsung DA division strategy earnings",
        ],
        "max_per_query": 3,
    },
    # 4. 제품 리뷰 / 추천 리스트
    {
        "category": "Product Reviews",
        "queries": [
            "best refrigerator 2025 review ranked",
            "best washing machine dryer 2025 top picks",
            "best air conditioner 2025 editor choice",
            "best dishwasher 2025 recommended",
            "best smart home appliance 2025 buying guide",
        ],
        "max_per_query": 2,
    },
    # 5. 매크로 / 정책
    {
        "category": "Macro / Policy",
        "queries": [
            "Trump tariff appliance manufacturing Mexico",
            "US trade policy electronics tariff 2025",
            "IRA energy appliance incentive subsidy",
        ],
        "max_per_query": 2,
    },
    # 6. 시장 동향
    {
        "category": "Market Dynamics",
        "queries": [
            "global home appliance market growth premium 2025",
            "India appliance market growth forecast",
            "Southeast Asia consumer electronics market",
        ],
        "max_per_query": 2,
    },
    # 7. 공급망
    {
        "category": "Supply Chain",
        "queries": [
            "rare earth export controls electronics supply chain",
            "semiconductor appliance supply disruption 2025",
            "Vietnam Mexico manufacturing relocation",
        ],
        "max_per_query": 2,
    },
]


# ── FETCH FROM NEWSAPI ───────────────────────────────────────────────────────
def fetch_articles():
    articles  = []
    seen_urls = set()

    for group in QUERIES:
        category  = group["category"]
        max_per_q = group.get("max_per_query", 2)

        for q in group["queries"]:
            try:
                resp = requests.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q":        q,
                        "from":     FROM_DATE,
                        "sortBy":   "relevancy",
                        "language": "en",
                        "pageSize": max_per_q,
                        "apiKey":   NEWS_API_KEY,
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()

                for art in data.get("articles", []):
                    if (
                        art["url"] not in seen_urls
                        and art.get("description")
                        and art.get("title", "") != "[Removed]"
                    ):
                        seen_urls.add(art["url"])
                        articles.append({
                            "category":    category,
                            "title_en":    art["title"],
                            "description": art.get("description", ""),
                            "content":     art.get("content") or art.get("description", ""),
                            "url":         art["url"],
                            "source":      art["source"]["name"],
                            "publishedAt": art["publishedAt"],
                        })
            except Exception as e:
                print(f"  [WARN] '{q}': {e}")

    print(f"  Raw articles fetched: {len(articles)}")
    return articles[:MAX_ARTICLES + 6]


# ── CLAUDE ANALYSIS ──────────────────────────────────────────────────────────
def analyze_with_claude(articles: list) -> list:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    system = """당신은 삼성전자 DA(가전) 부문 임원을 위한 전략 브리핑 작성 전문가입니다.
MBB 컨설팅 수준의 전문성과 간결함으로 분석합니다.
순수 JSON 배열만 반환하세요. 마크다운 코드블록 없이."""

    user = f"""아래 {len(articles)}개 뉴스 기사를 분석해 삼성전자 DA 임원 브리핑용 JSON 배열을 생성하세요.

입력 기사:
{json.dumps(articles, ensure_ascii=False, indent=2)}

출력 형식 (순수 JSON 배열):
[
  {{
    "category": "입력의 category 그대로",
    "title": "임원이 즉시 이해할 한국어 번역/의역 — 20자 내외, 핵심만",
    "media": "출처명 (국가, 예: Bloomberg (US))",
    "impact": 1~5 정수 (5=즉각 경영 의사결정 필요),
    "time": "publishedAt 기준 'X시간 전'",
    "url": "원문 URL 그대로",
    "summary_kr": "What happened — 구체적 수치/사실 포함, 2~3문장",
    "strategic_implications": "삼성 DA 관점 위기/기회 분석 + 실행 대응 제언. Product Reviews는 '삼성 제품 순위 포지션 vs 경쟁사 강약점' 관점으로 작성",
    "tags": ["risk"/"opp"/"watch" 중 1~3개]
  }}
]

규칙:
- 최대 {MAX_ARTICLES}개 (중복/저품질 제거)
- impact 5는 최대 3개만
- Product Reviews: 삼성 포지션 vs LG·Whirlpool 비교 필수
- Samsung DA: 자사 관점 전략적 해석
- 순수 JSON만, 설명 없이"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=5000,
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw   = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── TOP 3 TAKEAWAYS ──────────────────────────────────────────────────────────
def generate_takeaways(articles: list) -> list:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    system = """삼성전자 DA 임원 브리핑 'Top 3 Key Takeaways' 작성 전문가.
단순 요약이 아닌 거시적 전략 흐름을 짚는 통찰. JSON 배열만 반환."""

    user = f"""오늘 뉴스를 바탕으로 삼성전자 DA 임원이 반드시 알아야 할 Top 3 전략적 통찰을 생성하세요.

분석 뉴스:
{json.dumps(articles, ensure_ascii=False, indent=2)}

출력 (JSON 배열, 정확히 3개):
[
  {{
    "trend_label": "핵심 흐름 레이블 (예: ▲ Structural Shift / ⚠ Risk: Policy / ◎ Opportunity: AI)",
    "title": "임원이 즉시 이해하는 핵심 전략 메시지 — 25자 내외",
    "desc": "삼성 DA에 주는 전략적 의미와 구체적 대응 방향 3~4문장"
  }}
]

JSON만, 마크다운 없이."""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw   = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*60}")
    print(f" Samsung DA Briefing Pipeline  |  {NOW.strftime('%Y-%m-%d %H:%M KST')}")
    print(f"{'='*60}")

    print("\n[1/3] Fetching news from NewsAPI...")
    raw = fetch_articles()

    print(f"\n[2/3] Analyzing {len(raw)} articles with Claude...")
    analyzed = analyze_with_claude(raw)
    print(f"  → {len(analyzed)} articles after filtering")

    print("\n[3/3] Generating Top 3 Takeaways...")
    takeaways = generate_takeaways(analyzed)

    cat_counts = {}
    for a in analyzed:
        cat_counts[a["category"]] = cat_counts.get(a["category"], 0) + 1

    output = {
        "generated_at":         NOW.isoformat(),
        "generated_at_display": NOW.strftime("%Y.%m.%d %H:%M KST"),
        "category_counts":      cat_counts,
        "takeaways":            takeaways,
        "articles":             analyzed,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done → {OUTPUT_FILE}")
    print(f"   {cat_counts}")


if __name__ == "__main__":
    main()
