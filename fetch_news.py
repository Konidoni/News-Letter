"""
Samsung DA Strategy Briefing — News Fetcher v4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
뉴스 수집: Google News RSS + Bing News RSS (무료, requests만 사용)
AI 사용:  Claude haiku 2회 — 번역 1회 + Takeaways 1회

의존성: anthropic, requests
"""

import os, json, time, re, html
import requests
import anthropic
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
DATA_DIR      = "data"

KST       = timezone(timedelta(hours=9))
NOW       = datetime.now(KST)
TODAY_STR = NOW.strftime("%Y-%m-%d")
SINCE     = NOW - timedelta(hours=24)

BLOCKED_DOMAINS = (
    ".co.kr", "naver.", "daum.", "chosun.", "joongang.", "yonhap",
    "koreatimes", "koreaherald", ".cn", ".jp", "sina.", "qq.com",
)

QUERIES = [
    {"category": "Samsung Bespoke",     "q": "samsung bespoke"},
    {"category": "Samsung Bespoke",     "q": "samsung bespoke refrigerator washer"},
    {"category": "Samsung Bespoke",     "q": "samsung bespoke review 2025"},
    {"category": "Samsung DA",          "q": "samsung home appliance"},
    {"category": "Samsung DA",          "q": "samsung electronics appliance 2025"},
    {"category": "Samsung Jet Bot",     "q": "samsung jet bot"},
    {"category": "Samsung Jet Bot",     "q": "samsung jet bot robot vacuum"},
    {"category": "Technology Trend",    "q": "smart home appliance news"},
    {"category": "Technology Trend",    "q": "AI home appliance 2025"},
    {"category": "Technology Trend",    "q": "smart appliance IoT matter"},
    {"category": "Market Dynamics",     "q": "home appliance market 2025"},
    {"category": "Market Dynamics",     "q": "kitchen appliance news"},
    {"category": "Market Dynamics",     "q": "home appliance industry trend"},
    {"category": "Competitor Analysis", "q": "LG electronics appliance news"},
    {"category": "Competitor Analysis", "q": "whirlpool appliance 2025"},
    {"category": "Competitor Analysis", "q": "haier appliance news"},
    {"category": "Competitor Analysis", "q": "bosch electrolux appliance"},
    {"category": "Competitor Analysis", "q": "dyson roomba robot vacuum news"},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SamsungDABot/1.0)"}


# ── RSS 파싱 공통 ─────────────────────────────────────────────────────────────
def parse_rss_items(content: bytes, category: str, source_tag: str) -> list:
    articles = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []

    for item in root.findall(".//item"):
        title_el   = item.find("title")
        link_el    = item.find("link")
        pubdate_el = item.find("pubDate")
        source_el  = item.find("source")
        desc_el    = item.find("description")

        title   = html.unescape(title_el.text or "")  if title_el   is not None else ""
        link    = link_el.text                         if link_el    is not None else ""
        pubdate = pubdate_el.text                      if pubdate_el is not None else ""
        source  = (source_el.text if source_el is not None else "") or source_tag
        desc    = html.unescape(desc_el.text or "")   if desc_el    is not None else ""

        if not title or not link:
            continue
        if any(bd in link.lower() for bd in BLOCKED_DOMAINS):
            continue

        time_str = "Today"
        if pubdate:
            try:
                pub_dt = parsedate_to_datetime(pubdate).astimezone(KST)
                if pub_dt < SINCE:
                    continue
                time_str = format_time(pub_dt)
            except Exception:
                pass

        # Google News redirect 처리
        real_url = link
        match = re.search(r'url=([^&]+)', link)
        if match:
            real_url = requests.utils.unquote(match.group(1))

        articles.append({
            "category":               category,
            "title":                  title,
            "media":                  source,
            "url":                    real_url,
            "time":                   time_str,
            "summary_kr":             re.sub(r'<[^>]+>', '', desc)[:300],
            "strategic_implications": "",
            "impact":                 auto_impact(title, category),
            "tags":                   auto_tags(title, category),
        })

    return articles


# ── Google News RSS ───────────────────────────────────────────────────────────
def fetch_google(query: str, category: str) -> list:
    q_enc = requests.utils.quote(query)
    url   = f"https://news.google.com/rss/search?q={q_enc}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return parse_rss_items(resp.content, category, "")
    except Exception as e:
        print(f"    [Google] error: {e}")
        return []


# ── Bing News RSS ─────────────────────────────────────────────────────────────
def fetch_bing(query: str, category: str) -> list:
    q_enc = requests.utils.quote(query)
    url   = f"https://www.bing.com/news/search?q={q_enc}&format=rss&mkt=en-US"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return parse_rss_items(resp.content, category, "Bing News")
    except Exception as e:
        print(f"    [Bing] error: {e}")
        return []


def format_time(dt: datetime) -> str:
    diff  = NOW - dt
    hours = int(diff.total_seconds() / 3600)
    if hours < 1:   return "Just now"
    elif hours < 24: return f"{hours}h ago"
    elif hours < 48: return "1d ago"
    else:            return dt.strftime("%b %d")


RISK_KEYWORDS = ["recall","lawsuit","fine","ban","drop","decline","cut","loss","concern","fail"]
OPP_KEYWORDS  = ["launch","new","release","award","win","growth","rise","record","expand","partner","unveil"]

def auto_tags(title: str, category: str) -> list:
    t = title.lower()
    tags = []
    if any(k in t for k in RISK_KEYWORDS): tags.append("risk")
    if any(k in t for k in OPP_KEYWORDS):  tags.append("opp")
    if category == "Competitor Analysis":   tags.append("watch")
    return tags or ["watch"]

def auto_impact(title: str, category: str) -> int:
    t = title.lower()
    if any(k in t for k in ["recall","lawsuit","ban","billion","record"]): return 5
    if any(k in t for k in ["launch","release","new","award","expand"]):   return 4
    if category in ("Samsung Bespoke","Samsung Jet Bot","Samsung DA"):     return 4
    return 3


def deduplicate(articles: list) -> list:
    seen_urls, seen_titles, unique = set(), set(), []
    for a in articles:
        url   = re.sub(r'\?.*$', '', a.get("url","")).rstrip("/").lower()
        title = re.sub(r'[^a-z0-9]', '', a.get("title","").lower())[:50]
        if url in seen_urls or (title and title in seen_titles):
            continue
        if url:   seen_urls.add(url)
        if title: seen_titles.add(title)
        unique.append(a)
    return unique


def translate_articles(articles: list) -> list:
    """제목 + snippet → 한국어. 1회 호출로 전체 처리."""
    if not articles:
        return articles

    items = [
        {"i": i, "title": a.get("title", ""), "summary": a.get("summary_kr", "")}
        for i, a in enumerate(articles)
    ]
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    try:
        resp = client.messages.create(
            model      = "claude-haiku-4-5-20251001",
            max_tokens = 4000,
            system     = "번역 전문가. JSON 배열만 반환. 마크다운 코드블록 금지.",
            messages   = [{"role": "user", "content": f"""뉴스 기사 제목과 요약을 한국어로 번역하세요.
summary가 비어있으면 title 기반 2문장 요약 작성.

입력:
{json.dumps(items, ensure_ascii=False)}

출력 (JSON 배열만):
[{{"i":0,"title_kr":"한국어 제목","summary_kr":"한국어 요약"}}]"""}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        tr_map = {r["i"]: r for r in json.loads(raw)}
        for i, a in enumerate(articles):
            if i in tr_map:
                a["title"]      = tr_map[i].get("title_kr",  a["title"])
                a["summary_kr"] = tr_map[i].get("summary_kr", a["summary_kr"])
        print(f"  ✅ 번역 완료 ({len(tr_map)}건)")
    except Exception as e:
        print(f"  [WARN] 번역 실패, 영어 유지: {e}")
    return articles


def generate_takeaways(articles: list) -> list:
    titles_text = "\n".join(
        f"[{a['category']}] {a['title']}" for a in articles[:60]
    )
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    resp = client.messages.create(
        model      = "claude-haiku-4-5-20251001",
        max_tokens = 800,
        system     = "삼성전자 DA 임원 전략 브리핑 전문가. JSON 배열만 반환. 마크다운 금지.",
        messages   = [{"role": "user", "content": f"""오늘({TODAY_STR}) 뉴스 제목 기반으로 삼성전자 DA 임원을 위한 Top 3 전략 통찰을 작성하세요.

뉴스 제목:
{titles_text}

출력 (JSON 배열 정확히 3개):
[{{"trend_label":"흐름 레이블","title":"25자 핵심 메시지","desc":"3~4문장 전략적 의미"}}]
JSON만. 다른 텍스트 없이."""}],
    )
    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw)


def save_data(articles: list, takeaways: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    cat_counts = {}
    for a in articles:
        k = a.get("category", "Unknown")
        cat_counts[k] = cat_counts.get(k, 0) + 1

    day_data = {
        "date":                 TODAY_STR,
        "date_display":         NOW.strftime("%Y년 %m월 %d일"),
        "generated_at":         NOW.isoformat(),
        "generated_at_display": NOW.strftime("%Y.%m.%d %H:%M KST"),
        "category_counts":      cat_counts,
        "takeaways":            takeaways,
        "articles":             articles,
    }

    day_file = os.path.join(DATA_DIR, f"{TODAY_STR}.json")
    with open(day_file, "w", encoding="utf-8") as f:
        json.dump(day_data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 저장 → {day_file}  |  기사 {len(articles)}개  |  {cat_counts}")

    manifest_file = os.path.join(DATA_DIR, "manifest.json")
    manifest = {"dates": []}
    if os.path.exists(manifest_file):
        try:
            with open(manifest_file, encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            pass

    dates = manifest.get("dates", [])
    if TODAY_STR not in dates:
        dates.insert(0, TODAY_STR)
    manifest = {"dates": dates[:30], "latest": TODAY_STR}

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"   manifest: {len(dates)}일치 아카이브")


def main():
    print(f"\n{'='*60}")
    print(f" Samsung DA Briefing  |  {NOW.strftime('%Y-%m-%d %H:%M KST')}")
    print(f" 수집: Google News RSS + Bing News RSS")
    print(f" 범위: 최근 24시간 | 분석: Claude haiku 2회")
    print(f"{'='*60}\n")

    print("[1/4] 뉴스 수집 중...")
    raw = []
    total = len(QUERIES)
    for i, item in enumerate(QUERIES):
        cat, q = item["category"], item["q"]
        print(f"  [{i+1:02d}/{total}] {cat} | {q}")

        g = fetch_google(q, cat)
        b = fetch_bing(q, cat)
        print(f"         Google {len(g)}개 / Bing {len(b)}개")
        raw.extend(g)
        raw.extend(b)
        time.sleep(1)

    articles = deduplicate(raw)
    print(f"\n  원본 {len(raw)}개 → 중복 제거 후 {len(articles)}개\n")

    if not articles:
        print("[WARN] 수집된 기사 없음")
        save_data([], [
            {"trend_label": "⚠ 수집 오류", "title": "24시간 내 관련 뉴스 없음", "desc": "관련 뉴스가 없습니다."},
            {"trend_label": "—", "title": "—", "desc": "—"},
            {"trend_label": "—", "title": "—", "desc": "—"},
        ])
        return

    # 번역 (제목 + 요약 → 한국어)
    print("[2/4] 한국어 번역 중 (Claude haiku)...")
    articles = translate_articles(articles)

    print("[3/4] Takeaways 생성 중 (Claude haiku)...")
    try:
        takeaways = generate_takeaways(articles)
        print("  ✅ 완료")
    except Exception as e:
        print(f"  [WARN] {e}")
        takeaways = [
            {"trend_label": "—", "title": "오늘의 주요 동향", "desc": "아래 기사를 참조하세요."},
            {"trend_label": "—", "title": "—", "desc": "—"},
            {"trend_label": "—", "title": "—", "desc": "—"},
        ]

    print("[4/4] 저장 중...")
    save_data(articles, takeaways)

    print("\n📊 카테고리별:")
    cat_counts = {}
    for a in articles:
        k = a.get("category","?")
        cat_counts[k] = cat_counts.get(k, 0) + 1
    for cat, cnt in sorted(cat_counts.items()):
        print(f"   {cat}: {cnt}개")


if __name__ == "__main__":
    main()
