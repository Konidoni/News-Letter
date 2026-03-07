"""
Samsung DA Strategy Briefing — News Fetcher
매일 data/YYYY-MM-DD.json 으로 저장 (날짜별 아카이브)
Google News RSS 사용 (API 키 불필요)
"""

import os, json, time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import anthropic

ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
DATA_DIR      = "data"
MAX_ARTICLES  = 10

KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)
TODAY_STR = NOW.strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

RSS_SOURCES = [
    {"category": "Samsung DA",           "url": "https://news.google.com/rss/search?q=Samsung+appliance+Bespoke+SmartThings&hl=en-US&gl=US&ceid=US:en"},
    {"category": "Samsung DA",           "url": "https://news.google.com/rss/search?q=Samsung+refrigerator+washer+home+appliance+2025&hl=en-US&gl=US&ceid=US:en"},
    {"category": "Competitor Analysis",  "url": "https://news.google.com/rss/search?q=LG+Electronics+home+appliance+2025&hl=en-US&gl=US&ceid=US:en"},
    {"category": "Competitor Analysis",  "url": "https://news.google.com/rss/search?q=Haier+Whirlpool+Bosch+appliance+strategy&hl=en-US&gl=US&ceid=US:en"},
    {"category": "Technology Trend",     "url": "https://news.google.com/rss/search?q=AI+home+appliance+smart+home+2025&hl=en-US&gl=US&ceid=US:en"},
    {"category": "Technology Trend",     "url": "https://news.google.com/rss/search?q=Matter+smart+home+Google+Apple+Samsung&hl=en-US&gl=US&ceid=US:en"},
    {"category": "Product Reviews",      "url": "https://news.google.com/rss/search?q=best+refrigerator+washing+machine+2025+review&hl=en-US&gl=US&ceid=US:en"},
    {"category": "Product Reviews",      "url": "https://news.google.com/rss/search?q=best+home+appliance+2025+top+picks+editor&hl=en-US&gl=US&ceid=US:en"},
    {"category": "Macro / Policy",       "url": "https://news.google.com/rss/search?q=tariff+appliance+trade+policy+2025&hl=en-US&gl=US&ceid=US:en"},
    {"category": "Macro / Policy",       "url": "https://news.google.com/rss/search?q=IRA+energy+appliance+EU+regulation&hl=en-US&gl=US&ceid=US:en"},
    {"category": "Market Dynamics",      "url": "https://news.google.com/rss/search?q=home+appliance+market+growth+premium+2025&hl=en-US&gl=US&ceid=US:en"},
    {"category": "Market Dynamics",      "url": "https://news.google.com/rss/search?q=India+Southeast+Asia+appliance+market+2025&hl=en-US&gl=US&ceid=US:en"},
    {"category": "Supply Chain",         "url": "https://news.google.com/rss/search?q=rare+earth+supply+chain+electronics+2025&hl=en-US&gl=US&ceid=US:en"},
    {"category": "Supply Chain",         "url": "https://news.google.com/rss/search?q=semiconductor+appliance+manufacturing+Vietnam&hl=en-US&gl=US&ceid=US:en"},
]


# ── RSS 파싱 ─────────────────────────────────────────────────────────────────
def parse_rss(content: bytes, category: str) -> list:
    items = []
    try:
        root = ET.fromstring(content)
        for item in root.findall(".//item")[:3]:
            title  = item.findtext("title", "").strip()
            link   = item.findtext("link", "").strip()
            desc   = item.findtext("description", "").strip()
            pub    = item.findtext("pubDate", "")
            src_el = item.find("source")
            source = src_el.text.strip() if src_el is not None else "Google News"

            if not title or not link or title == "[Removed]":
                continue

            try:
                pub_dt    = parsedate_to_datetime(pub).astimezone(KST)
                hours_ago = max(0, int((NOW - pub_dt).total_seconds() / 3600))
                if hours_ago > 24:
                    continue  # 24시간 초과 제외
                time_str = f"{hours_ago}시간 전"
            except Exception:
                time_str = "최근"

            items.append({
                "category":    category,
                "title_en":    title,
                "description": desc[:300],
                "url":         link,
                "source":      source,
                "time_str":    time_str,
            })
    except ET.ParseError as e:
        print(f"    [WARN] XML parse error: {e}")
    return items


def fetch_rss(url: str, category: str) -> list:
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            print(f"    HTTP {resp.status_code} [{category}]")
            if resp.status_code == 200:
                return parse_rss(resp.content, category)
            time.sleep(2)
        except Exception as e:
            print(f"    [WARN] {e}")
            time.sleep(3)
    return []


def fetch_all() -> list:
    articles, seen = [], set()
    for src in RSS_SOURCES:
        time.sleep(1)
        for item in fetch_rss(src["url"], src["category"]):
            if item["url"] not in seen:
                seen.add(item["url"])
                articles.append(item)
    print(f"  총 {len(articles)}개 기사 수집")
    return articles[:MAX_ARTICLES + 5]


# ── Claude 분석 ──────────────────────────────────────────────────────────────
def _call_claude_batch(batch: list, client) -> list:
    system = "삼성전자 DA 임원용 전략 브리핑 전문가. 순수 JSON 배열만 반환. 마크다운 금지."
    user = f"""아래 {len(batch)}개 기사를 분석해 JSON 배열 생성.

입력:
{json.dumps(batch, ensure_ascii=False, indent=2)}

출력 (순수 JSON 배열):
[{{
  "category": "입력 category 그대로",
  "title": "한국어 번역 20자 내외",
  "media": "source (국가)",
  "impact": 1~5,
  "time": "time_str 그대로",
  "url": "url 그대로",
  "summary_kr": "핵심 요약 2~3문장",
  "strategic_implications": "삼성 DA 위기/기회 + 대응 제언",
  "tags": ["risk"/"opp"/"watch" 1~3개]
}}]

JSON만, 설명 없이."""

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
    if not raw.endswith("]"):
        last = raw.rfind("},")
        raw = (raw[:last+1] if last != -1 else raw[:raw.rfind("}")+1]) + "]"
    return json.loads(raw)


def analyze_with_claude(articles: list) -> list:
    if not articles:
        return []
    client  = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    results = []
    for i in range(0, len(articles), 7):
        batch = articles[i:i+7]
        print(f"  배치 {i//7+1} 분석 중 ({len(batch)}개)...")
        try:
            results.extend(_call_claude_batch(batch, client))
            time.sleep(1)
        except Exception as e:
            print(f"  [WARN] 배치 {i//7+1} 실패: {e}")
    return results[:MAX_ARTICLES]


def generate_takeaways(articles: list) -> list:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system="삼성전자 DA 임원 Top 3 전략 통찰. JSON 배열만 반환.",
        messages=[{"role": "user", "content": f"""오늘 뉴스 기반 Top 3 전략 통찰.

뉴스: {json.dumps(articles, ensure_ascii=False)}

출력 (JSON 배열 3개):
[{{"trend_label":"레이블","title":"25자 핵심 메시지","desc":"3~4문장 전략적 의미"}}]

JSON만."""}],
    )
    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*60}")
    print(f" Samsung DA Briefing  |  {NOW.strftime('%Y-%m-%d %H:%M KST')}")
    print(f"{'='*60}")

    os.makedirs(DATA_DIR, exist_ok=True)

    print("\n[1/3] 뉴스 수집 중...")
    raw = fetch_all()

    if not raw:
        print("[ERROR] 수집된 기사 없음")
        # 빈 파일 저장 (사이트 안 깨지게)
        save_data([], [])
        return

    print(f"\n[2/3] Claude 분석 중 ({len(raw)}개)...")
    analyzed = analyze_with_claude(raw)
    print(f"  → {len(analyzed)}개 완료")

    print("\n[3/3] Top 3 Takeaways 생성 중...")
    takeaways = generate_takeaways(analyzed)

    save_data(analyzed, takeaways)


def save_data(articles: list, takeaways: list):
    cat_counts = {}
    for a in articles:
        cat_counts[a.get("category", "Unknown")] = cat_counts.get(a.get("category", "Unknown"), 0) + 1

    day_data = {
        "date":             TODAY_STR,
        "date_display":     NOW.strftime("%Y년 %m월 %d일"),
        "generated_at":     NOW.isoformat(),
        "generated_at_display": NOW.strftime("%Y.%m.%d %H:%M KST"),
        "category_counts":  cat_counts,
        "takeaways":        takeaways,
        "articles":         articles,
    }

    # 오늘 날짜 파일 저장
    day_file = os.path.join(DATA_DIR, f"{TODAY_STR}.json")
    with open(day_file, "w", encoding="utf-8") as f:
        json.dump(day_data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 저장 완료 → {day_file}")

    # manifest.json 업데이트 (날짜 목록)
    manifest_file = os.path.join(DATA_DIR, "manifest.json")
    if os.path.exists(manifest_file):
        with open(manifest_file, encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {"dates": []}

    # 오늘 날짜 추가 (중복 방지)
    dates = manifest.get("dates", [])
    if TODAY_STR not in dates:
        dates.insert(0, TODAY_STR)  # 최신 날짜를 앞에

    # 최대 30일치만 유지
    dates = dates[:30]
    manifest = {"dates": dates, "latest": TODAY_STR}

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"   manifest 업데이트 → 총 {len(dates)}일치 아카이브")
    print(f"   카테고리: {cat_counts}")


if __name__ == "__main__":
    main()
