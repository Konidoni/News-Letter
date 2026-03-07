"""
Samsung DA Strategy Briefing — News Fetcher (Google News RSS)
API 키 없이 Google News RSS로 직접 수집.
Outputs: news_data.json
"""

import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import anthropic

# ── CONFIG ──────────────────────────────────────────────────────────────────
ANTHROPIC_KEY  = os.environ["ANTHROPIC_API_KEY"]
OUTPUT_FILE    = "news_data.json"
MAX_ARTICLES   = 15

KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)

# ── SEARCH QUERIES (Google News RSS) ────────────────────────────────────────
QUERIES = [
    # 1. 삼성 가전
    {"category": "Samsung DA", "q": "Samsung home appliance Bespoke"},
    {"category": "Samsung DA", "q": "Samsung SmartThings AI refrigerator"},
    {"category": "Samsung DA", "q": "Samsung washer dryer 2025"},

    # 2. 경쟁사 동향
    {"category": "Competitor Analysis", "q": "LG Electronics appliance 2025"},
    {"category": "Competitor Analysis", "q": "Haier appliance North America Europe"},
    {"category": "Competitor Analysis", "q": "Whirlpool strategy earnings 2025"},
    {"category": "Competitor Analysis", "q": "Bosch Electrolux home appliance"},

    # 3. 기술 트렌드
    {"category": "Technology Trend", "q": "AI home appliance smart home 2025"},
    {"category": "Technology Trend", "q": "Matter smart home standard Google Apple"},
    {"category": "Technology Trend", "q": "LFP battery energy efficient appliance"},

    # 4. 제품 리뷰·순위
    {"category": "Product Reviews", "q": "best refrigerator 2025 review"},
    {"category": "Product Reviews", "q": "best washing machine 2025 top picks"},
    {"category": "Product Reviews", "q": "best air conditioner dishwasher 2025"},

    # 5. 매크로·정책
    {"category": "Macro / Policy", "q": "tariff appliance manufacturing trade 2025"},
    {"category": "Macro / Policy", "q": "IRA energy appliance incentive regulation"},

    # 6. 시장 동향
    {"category": "Market Dynamics", "q": "home appliance market growth premium 2025"},
    {"category": "Market Dynamics", "q": "India Southeast Asia appliance market"},

    # 7. 공급망
    {"category": "Supply Chain", "q": "rare earth supply chain electronics 2025"},
    {"category": "Supply Chain", "q": "semiconductor appliance manufacturing Vietnam"},
]


def fetch_google_news_rss(query: str, max_items: int = 3) -> list:
    """Google News RSS에서 기사 수집"""
    url = (
        f"https://news.google.com/rss/search"
        f"?q={requests.utils.quote(query)}"
        f"&hl=en-US&gl=US&ceid=US:en"
    )
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []

        for item in root.findall(".//item")[:max_items]:
            title = item.findtext("title", "").strip()
            link  = item.findtext("link", "").strip()
            desc  = item.findtext("description", "").strip()
            pub   = item.findtext("pubDate", "")
            src_el= item.find("source")
            source= src_el.text.strip() if src_el is not None else "Unknown"

            if not title or not link:
                continue

            # pubDate 파싱
            try:
                pub_dt = parsedate_to_datetime(pub).astimezone(KST)
                hours_ago = int((NOW - pub_dt).total_seconds() / 3600)
                time_str = f"{hours_ago}시간 전" if hours_ago < 24 else f"{hours_ago // 24}일 전"
            except Exception:
                time_str = "최근"

            items.append({
                "title_en":    title,
                "description": desc,
                "url":         link,
                "source":      source,
                "time_str":    time_str,
            })

        return items

    except Exception as e:
        print(f"  [WARN] RSS fetch failed for '{query}': {e}")
        return []


def fetch_all_articles() -> list:
    articles  = []
    seen_urls = set()

    for entry in QUERIES:
        cat   = entry["category"]
        items = fetch_google_news_rss(entry["q"], max_items=2)

        for item in items:
            if item["url"] in seen_urls:
                continue
            seen_urls.add(item["url"])
            articles.append({
                "category":    cat,
                "title_en":    item["title_en"],
                "description": item["description"],
                "url":         item["url"],
                "source":      item["source"],
                "time_str":    item["time_str"],
            })

    print(f"  Raw articles fetched: {len(articles)}")
    return articles[:MAX_ARTICLES + 6]


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
    "title": "임원이 즉시 이해할 한국어 번역/의역 — 20자 내외",
    "media": "source 값 + 국가 약어 (예: Bloomberg (US))",
    "impact": 1~5 정수 (5=즉각 경영 의사결정 필요),
    "time": "time_str 값 그대로",
    "url": "url 값 그대로",
    "summary_kr": "What happened — 구체적 수치/사실 포함, 2~3문장",
    "strategic_implications": "삼성 DA 관점 위기/기회 분석 + 실행 대응 제언. Product Reviews는 삼성 포지션 vs 경쟁사 비교",
    "tags": ["risk"/"opp"/"watch" 중 1~3개]
  }}
]

규칙:
- 최대 {MAX_ARTICLES}개 (중복/저품질 제거)
- impact 5는 최대 3개
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


def generate_takeaways(articles: list) -> list:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    system = "삼성전자 DA 임원 브리핑 Top 3 Key Takeaways 작성 전문가. JSON 배열만 반환."

    user = f"""오늘 뉴스 기반으로 삼성전자 DA 임원 Top 3 전략 통찰 생성.

분석 뉴스:
{json.dumps(articles, ensure_ascii=False, indent=2)}

출력 (JSON 배열, 정확히 3개):
[
  {{
    "trend_label": "핵심 흐름 레이블",
    "title": "핵심 전략 메시지 25자 내외",
    "desc": "삼성 DA 전략적 의미 + 대응 방향 3~4문장"
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


def main():
    print(f"\n{'='*60}")
    print(f" Samsung DA Briefing  |  {NOW.strftime('%Y-%m-%d %H:%M KST')}")
    print(f" Source: Google News RSS (no API key required)")
    print(f"{'='*60}")

    print("\n[1/3] Fetching from Google News RSS...")
    raw = fetch_all_articles()

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
