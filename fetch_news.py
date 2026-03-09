"""
Samsung DA Strategy Briefing — News Fetcher v2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
뉴스 수집: DuckDuckGo Search (완전 무료, API 키 없음, 토큰 없음)
AI 사용:  Claude haiku — Takeaways 3개 생성 1회만 (하루 $0.001 미만)

구조:
  1. DDGS로 20개 쿼리 전수 수집 (24h 필터)
  2. 중복 제거 + 영어 소스 필터
  3. Claude haiku 1회 → Top 3 Takeaways
  4. data/YYYY-MM-DD.json 저장
"""

import os, json, time, re
import anthropic
from datetime import datetime, timedelta, timezone
from duckduckgo_search import DDGS

ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
DATA_DIR      = "data"

KST       = timezone(timedelta(hours=9))
NOW       = datetime.now(KST)
TODAY_STR = NOW.strftime("%Y-%m-%d")

# ── 영어 전용 소스 필터 ──────────────────────────────────────────────────────
BLOCKED_DOMAINS = (
    ".co.kr", "naver.", "daum.", "chosun.", "joongang.", "yonhap",
    "koreatimes", "koreaherald", ".cn", ".jp", "sina.", "qq.com",
)

EN_PREFERRED = (
    "cnet", "theverge", "engadget", "techcrunch", "techradar",
    "digitaltrends", "pcmag", "zdnet", "wirecutter", "rtings",
    "reuters", "bloomberg", "wsj", "apnews", "forbes", "businessinsider",
    "tomsguide", "9to5mac", "androidcentral", "slashgear",
)

# ── 쿼리 목록 (카테고리별) ────────────────────────────────────────────────────
QUERIES = [
    # Samsung Bespoke
    {"category": "Samsung Bespoke",     "q": "samsung bespoke"},
    {"category": "Samsung Bespoke",     "q": "samsung bespoke refrigerator washer dishwasher"},
    {"category": "Samsung Bespoke",     "q": "samsung bespoke AI launch release 2025"},
    {"category": "Samsung Bespoke",     "q": "samsung bespoke review"},
    # Samsung DA (general)
    {"category": "Samsung DA",          "q": "samsung home appliance news"},
    {"category": "Samsung DA",          "q": "samsung electronics home appliance 2025"},
    # Samsung Jet Bot
    {"category": "Samsung Jet Bot",     "q": "samsung jet bot"},
    {"category": "Samsung Jet Bot",     "q": "samsung jet bot robot vacuum review"},
    {"category": "Samsung Jet Bot",     "q": "samsung robot vacuum 2025"},
    # Technology Trend
    {"category": "Technology Trend",    "q": "smart home appliance news"},
    {"category": "Technology Trend",    "q": "AI home appliance connected home 2025"},
    {"category": "Technology Trend",    "q": "smart appliance IoT matter"},
    # Market Dynamics
    {"category": "Market Dynamics",     "q": "home appliance market trend 2025"},
    {"category": "Market Dynamics",     "q": "kitchen appliance news"},
    {"category": "Market Dynamics",     "q": "home appliance industry report"},
    # Competitor Analysis
    {"category": "Competitor Analysis", "q": "LG electronics home appliance news"},
    {"category": "Competitor Analysis", "q": "whirlpool appliance news 2025"},
    {"category": "Competitor Analysis", "q": "haier appliance news 2025"},
    {"category": "Competitor Analysis", "q": "bosch electrolux appliance news"},
    {"category": "Competitor Analysis", "q": "dyson roomba robot vacuum news"},
]

# ── 자동 태그 + 임팩트 룰 (AI 없이) ─────────────────────────────────────────
RISK_KEYWORDS = ["recall", "lawsuit", "fine", "ban", "drop", "decline", "cut", "loss", "concern", "fail"]
OPP_KEYWORDS  = ["launch", "new", "release", "award", "win", "growth", "rise", "record", "expand", "partner"]

def auto_tags(title: str, category: str) -> list:
    t = title.lower()
    tags = []
    if any(k in t for k in RISK_KEYWORDS):
        tags.append("risk")
    if any(k in t for k in OPP_KEYWORDS):
        tags.append("opp")
    if category == "Competitor Analysis":
        tags.append("watch")
    return tags or ["watch"]

def auto_impact(title: str, category: str) -> int:
    t = title.lower()
    if any(k in t for k in ["recall", "lawsuit", "ban", "major", "record", "billion"]):
        return 5
    if any(k in t for k in ["launch", "release", "new", "award", "expand"]):
        return 4
    if category in ("Samsung Bespoke", "Samsung Jet Bot", "Samsung DA"):
        return 4
    return 3

def format_time(date_str: str) -> str:
    """DDGS date string → 'Xh ago' / '1d ago' / 'MMM DD' """
    if not date_str:
        return "Today"
    try:
        # DDGS returns strings like "2025-03-09T12:34:00+00:00" or "3 hours ago"
        if "ago" in date_str:
            return date_str
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        dt_kst = dt.astimezone(KST)
        diff = NOW - dt_kst
        hours = int(diff.total_seconds() / 3600)
        if hours < 24:
            return f"{hours}h ago" if hours > 0 else "Just now"
        elif hours < 48:
            return "1d ago"
        else:
            return dt_kst.strftime("%b %d")
    except Exception:
        return date_str[:10] if len(date_str) >= 10 else "Today"


# ── 뉴스 수집 (DDGS) ─────────────────────────────────────────────────────────
def fetch_all() -> list:
    articles = []
    ddgs = DDGS()

    for i, item in enumerate(QUERIES):
        cat = item["category"]
        q   = item["q"]
        print(f"  [{i+1:02d}/{len(QUERIES)}] {cat} | {q}")
        try:
            results = ddgs.news(
                keywords  = q,
                region    = "us-en",
                safesearch= "off",
                timelimit = "d",       # past 24 hours
                max_results = 20,
            )
            count = 0
            for r in results:
                url = r.get("url", "")
                # 한국어/비영어 도메인 필터
                if any(bd in url.lower() for bd in BLOCKED_DOMAINS):
                    continue
                articles.append({
                    "category":              cat,
                    "title":                 r.get("title", ""),
                    "media":                 r.get("source", ""),
                    "url":                   url,
                    "published_raw":         r.get("date", ""),
                    "time":                  format_time(r.get("date", "")),
                    "summary_kr":            r.get("body", ""),   # 영어 snippet (대시보드에 표시)
                    "strategic_implications":"",                   # Takeaways에서 커버
                    "impact":                auto_impact(r.get("title",""), cat),
                    "tags":                  auto_tags(r.get("title",""), cat),
                })
                count += 1
            print(f"         → {count}개")
        except Exception as e:
            print(f"         ⚠ {e}")

        time.sleep(1.5)   # DDGS rate limit 방지

    return articles


# ── 중복 제거 ─────────────────────────────────────────────────────────────────
def deduplicate(articles: list) -> list:
    seen_urls, seen_titles, unique = set(), set(), []
    for a in articles:
        url   = re.sub(r'\?.*$', '', a.get("url","")).rstrip("/").lower()
        title = re.sub(r'[^a-z0-9]', '', a.get("title","").lower())[:50]
        if url in seen_urls or title in seen_titles:
            continue
        if url:   seen_urls.add(url)
        if title: seen_titles.add(title)
        unique.append(a)
    return unique


# ── Takeaways (Claude haiku 1회) ──────────────────────────────────────────────
def generate_takeaways(articles: list) -> list:
    # 제목만 전달 → 토큰 최소화
    titles_text = "\n".join(
        f"[{a['category']}] {a['title']}" for a in articles[:60]
    )
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    resp = client.messages.create(
        model      = "claude-haiku-4-5-20251001",   # 최저가 모델
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


# ── 저장 ──────────────────────────────────────────────────────────────────────
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


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*60}")
    print(f" Samsung DA Briefing  |  {NOW.strftime('%Y-%m-%d %H:%M KST')}")
    print(f" 수집: DuckDuckGo (무료)  |  분석: Claude haiku (1회)")
    print(f"{'='*60}\n")

    # 1. 뉴스 수집
    print("[1/3] 뉴스 수집 중...")
    raw = fetch_all()
    print(f"  수집 원본: {len(raw)}개")

    # 2. 중복 제거
    articles = deduplicate(raw)
    print(f"  중복 제거 후: {len(articles)}개\n")

    if not articles:
        print("[WARN] 수집된 기사 없음")
        save_data([], [
            {"trend_label": "⚠ 수집 오류", "title": "24시간 내 관련 뉴스 없음", "desc": "관련 뉴스가 없습니다."},
            {"trend_label": "—", "title": "—", "desc": "—"},
            {"trend_label": "—", "title": "—", "desc": "—"},
        ])
        return

    # 3. Takeaways (haiku 1회)
    print("[2/3] Takeaways 생성 중 (Claude haiku)...")
    try:
        takeaways = generate_takeaways(articles)
        print("  ✅ Takeaways 생성 완료")
    except Exception as e:
        print(f"  [WARN] {e}")
        takeaways = [
            {"trend_label": "—", "title": "오늘의 주요 동향", "desc": "아래 기사를 참조하세요."},
            {"trend_label": "—", "title": "—", "desc": "—"},
            {"trend_label": "—", "title": "—", "desc": "—"},
        ]

    # 4. 저장
    print("[3/3] 저장 중...")
    save_data(articles, takeaways)

    # 카테고리별 요약 출력
    print("\n📊 카테고리별 수집 결과:")
    cat_counts = {}
    for a in articles:
        k = a.get("category","?")
        cat_counts[k] = cat_counts.get(k, 0) + 1
    for cat, cnt in sorted(cat_counts.items()):
        print(f"   {cat}: {cnt}개")


if __name__ == "__main__":
    main()
