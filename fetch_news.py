"""
Samsung DA Strategy Briefing — News Fetcher
Sources: Google News RSS + Reuters RSS + AP News RSS (fallback 포함)
API 키 불필요. feedparser로 안정적 파싱.
"""

import os, json, time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
import anthropic

ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
OUTPUT_FILE   = "news_data.json"
MAX_ARTICLES  = 10

KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── RSS SOURCES ──────────────────────────────────────────────────────────────
# Google News RSS + 카테고리별 직접 RSS 피드 병행
RSS_SOURCES = [
    # 삼성 가전
    {
        "category": "Samsung DA",
        "url": "https://news.google.com/rss/search?q=Samsung+appliance+Bespoke+SmartThings&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "category": "Samsung DA",
        "url": "https://news.google.com/rss/search?q=Samsung+refrigerator+washer+home+appliance+2025&hl=en-US&gl=US&ceid=US:en",
    },
    # 경쟁사
    {
        "category": "Competitor Analysis",
        "url": "https://news.google.com/rss/search?q=LG+Electronics+appliance+2025&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "category": "Competitor Analysis",
        "url": "https://news.google.com/rss/search?q=Haier+Whirlpool+appliance+strategy&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "category": "Competitor Analysis",
        "url": "https://news.google.com/rss/search?q=Bosch+Electrolux+Midea+home+appliance&hl=en-US&gl=US&ceid=US:en",
    },
    # 기술 트렌드
    {
        "category": "Technology Trend",
        "url": "https://news.google.com/rss/search?q=AI+home+appliance+smart+home+2025&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "category": "Technology Trend",
        "url": "https://news.google.com/rss/search?q=Matter+smart+home+Google+Apple+Samsung&hl=en-US&gl=US&ceid=US:en",
    },
    # 제품 리뷰
    {
        "category": "Product Reviews",
        "url": "https://news.google.com/rss/search?q=best+refrigerator+washing+machine+2025+review&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "category": "Product Reviews",
        "url": "https://news.google.com/rss/search?q=best+home+appliance+2025+top+picks+editor&hl=en-US&gl=US&ceid=US:en",
    },
    # 매크로·정책
    {
        "category": "Macro / Policy",
        "url": "https://news.google.com/rss/search?q=tariff+appliance+trade+policy+2025&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "category": "Macro / Policy",
        "url": "https://news.google.com/rss/search?q=IRA+energy+appliance+incentive+regulation+EU&hl=en-US&gl=US&ceid=US:en",
    },
    # 시장 동향
    {
        "category": "Market Dynamics",
        "url": "https://news.google.com/rss/search?q=home+appliance+market+growth+2025&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "category": "Market Dynamics",
        "url": "https://news.google.com/rss/search?q=India+Southeast+Asia+appliance+market+2025&hl=en-US&gl=US&ceid=US:en",
    },
    # 공급망
    {
        "category": "Supply Chain",
        "url": "https://news.google.com/rss/search?q=rare+earth+supply+chain+electronics+2025&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "category": "Supply Chain",
        "url": "https://news.google.com/rss/search?q=semiconductor+appliance+manufacturing+Vietnam+Mexico&hl=en-US&gl=US&ceid=US:en",
    },
]


def parse_rss(content: bytes, category: str, source_url: str) -> list:
    """RSS XML을 파싱해서 기사 목록 반환"""
    items = []
    try:
        root = ET.fromstring(content)
        # RSS 2.0
        for item in root.findall(".//item")[:3]:
            title  = item.findtext("title", "").strip()
            link   = item.findtext("link", "").strip()
            desc   = item.findtext("description", "").strip()
            pub    = item.findtext("pubDate", "")
            src_el = item.find("source")
            source = src_el.text.strip() if src_el is not None else "Google News"

            if not title or not link or title == "[Removed]":
                continue

            # 시간 계산
            try:
                from email.utils import parsedate_to_datetime
                pub_dt    = parsedate_to_datetime(pub).astimezone(KST)
                hours_ago = max(0, int((NOW - pub_dt).total_seconds() / 3600))
                time_str  = f"{hours_ago}시간 전" if hours_ago < 48 else f"{hours_ago // 24}일 전"
            except Exception:
                time_str = "최근"

            items.append({
                "category":    category,
                "title_en":    title,
                "description": desc[:300] if desc else "",
                "url":         link,
                "source":      source,
                "time_str":    time_str,
            })
    except ET.ParseError as e:
        print(f"    [WARN] XML parse error: {e}")
    return items


def fetch_rss(url: str, category: str) -> list:
    """단일 RSS URL에서 기사 수집 (재시도 포함)"""
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            print(f"    HTTP {resp.status_code} ← {url[:70]}")
            if resp.status_code == 200:
                items = parse_rss(resp.content, category, url)
                print(f"    → {len(items)} articles")
                return items
            else:
                print(f"    [WARN] status {resp.status_code}, retrying...")
                time.sleep(2)
        except Exception as e:
            print(f"    [WARN] attempt {attempt+1} failed: {e}")
            time.sleep(3)
    return []


def fetch_all() -> list:
    articles  = []
    seen_urls = set()

    for src in RSS_SOURCES:
        time.sleep(1)  # Google 차단 방지용 딜레이
        items = fetch_rss(src["url"], src["category"])
        for item in items:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                articles.append(item)

    print(f"\n  Total unique articles: {len(articles)}")
    return articles[:MAX_ARTICLES + 5]


# ── CLAUDE ANALYSIS ──────────────────────────────────────────────────────────
def _call_claude(articles_batch: list, client) -> list:
    """Claude API 호출 + JSON 안전 파싱"""
    system = """삼성전자 DA 부문 임원용 전략 브리핑 작성 전문가.
MBB 컨설팅 수준. 순수 JSON 배열만 반환. 마크다운 코드블록 절대 금지."""

    user = f"""아래 {len(articles_batch)}개 기사를 분석해 삼성전자 DA 임원 브리핑 JSON 배열 생성.

입력:
{json.dumps(articles_batch, ensure_ascii=False, indent=2)}

출력 형식 (순수 JSON 배열만):
[
  {{
    "category": "입력 category 그대로",
    "title": "한국어 번역/의역 20자 내외",
    "media": "source + 국가 (예: Bloomberg (US))",
    "impact": 1~5 정수,
    "time": "time_str 그대로",
    "url": "url 그대로",
    "summary_kr": "핵심 요약 2~3문장 (수치 포함)",
    "strategic_implications": "삼성 DA 위기/기회 분석 + 대응 제언",
    "tags": ["risk","opp","watch" 중 1~3개]
  }}
]

규칙: impact 5는 최대 2개, JSON만 반환, 다른 텍스트 절대 없이"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    # JSON 잘린 경우 복구
    if not raw.endswith("]"):
        last = raw.rfind("},")
        if last != -1:
            raw = raw[:last+1] + "]"
        else:
            last = raw.rfind("}")
            if last != -1:
                raw = raw[:last+1] + "]"

    return json.loads(raw)


def analyze_with_claude(articles: list) -> list:
    if not articles:
        print("  [ERROR] No articles to analyze!")
        return []

    client  = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    results = []
    BATCH   = 7  # 7개씩 나눠서 처리 → 토큰 초과 방지

    for i in range(0, len(articles), BATCH):
        batch = articles[i:i+BATCH]
        print(f"  Batch {i//BATCH+1}: analyzing {len(batch)} articles...")
        try:
            results.extend(_call_claude(batch, client))
            time.sleep(1)
        except json.JSONDecodeError as e:
            print(f"  [WARN] JSON parse failed for batch {i//BATCH+1}: {e}")
        except Exception as e:
            print(f"  [WARN] Claude error for batch {i//BATCH+1}: {e}")

    return results


def generate_takeaways(articles: list) -> list:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system="삼성전자 DA 임원 Top 3 전략 통찰 작성. JSON 배열만 반환.",
        messages=[{"role": "user", "content": f"""오늘 뉴스 기반 Top 3 전략 통찰.

뉴스: {json.dumps(articles, ensure_ascii=False)}

출력 (JSON 배열 3개):
[{{"trend_label":"레이블","title":"25자 내외 핵심 메시지","desc":"3~4문장 전략적 의미"}}]

JSON만."""}],
    )
    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*60}")
    print(f" Samsung DA Briefing  |  {NOW.strftime('%Y-%m-%d %H:%M KST')}")
    print(f" Source: Google News RSS (no API key)")
    print(f"{'='*60}")

    print("\n[1/3] Fetching news...")
    raw = fetch_all()

    if not raw:
        print("\n[ERROR] 0 articles fetched. 네트워크 또는 RSS 차단 가능성.")
        # 빈 상태로도 파일 저장 (사이트 깨지지 않게)
        output = {
            "generated_at":         NOW.isoformat(),
            "generated_at_display": NOW.strftime("%Y.%m.%d %H:%M KST"),
            "category_counts":      {},
            "takeaways":            [
                {"trend_label":"⚠ 수집 오류","title":"뉴스 수집에 실패했습니다","desc":"잠시 후 다시 실행해주세요."},
                {"trend_label":"—","title":"—","desc":"—"},
                {"trend_label":"—","title":"—","desc":"—"},
            ],
            "articles": [],
        }
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        return

    print(f"\n[2/3] Analyzing {len(raw)} articles with Claude...")
    analyzed = analyze_with_claude(raw)
    print(f"  → {len(analyzed)} kept")

    print("\n[3/3] Generating takeaways...")
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

    print(f"\n✅ Done → {OUTPUT_FILE}  |  {cat_counts}")


if __name__ == "__main__":
    main()
