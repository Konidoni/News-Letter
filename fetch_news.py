"""
Samsung DA Strategy Briefing — News Fetcher v5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
완전 무료. AI API 없음.
뉴스 수집: Google News RSS + Bing News RSS
번역:      Google Translate 비공식 API (무료, 키 없음)
Takeaways: 규칙 기반 자동 생성

의존성: requests 만
"""

import os, json, time, re, html
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

DATA_DIR  = "data"

KST       = timezone(timedelta(hours=9))
NOW       = datetime.now(KST)
TODAY_STR = NOW.strftime("%Y-%m-%d")
SINCE     = NOW - timedelta(hours=24)

BLOCKED_DOMAINS = (
    ".co.kr", "naver.", "daum.", "chosun.", "joongang.", "yonhap",
    "koreatimes", "koreaherald", ".cn", ".jp", "sina.", "qq.com",
)

# 어그리게이터 / 신디케이션 매체 — 원본 기사 재탕
BLOCKED_MEDIA = {
    "aol", "msn", "yahoo news", "yahoo finance", "flipboard",
    "smartnews", "ground news", "newsnow", "alltop", "feedly",
    "pocketworthy", "upworthy", "buzzfeed", "patch",
    "dailymotion", "dailymail", "the mirror", "the sun",
}

# 삼성이 만들지 않는 제품 키워드 — 제목에 포함 시 제외
OFF_TOPIC_KEYWORDS = (
    "air fryer", "airfryer", "ninja", "instant pot", "instant vortex",
    "cosori", "philips airfryer", "gourmia", "actifry",
    "coffee maker", "coffee machine", "espresso", "keurig", "nespresso",
    "toaster", "microwave oven",           # 삼성 비주력 소형가전
    "blender", "juicer", "food processor",
    "lawnmower", "lawn mower", "chainsaw",
    "power tool", "drill",
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
        # 어그리게이터 매체 제외
        if source.lower().strip() in BLOCKED_MEDIA:
            continue
        # 삼성 비생산 제품 키워드 제외
        title_lower = title.lower()
        if any(kw in title_lower for kw in OFF_TOPIC_KEYWORDS):
            continue

        time_str = "Today"
        pub_ts   = 0
        if pubdate:
            try:
                pub_dt = parsedate_to_datetime(pubdate).astimezone(KST)
                if pub_dt < SINCE:
                    continue
                time_str = format_time(pub_dt)
                pub_ts   = int(pub_dt.timestamp())
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
            "pub_ts":                 pub_ts,
            "summary_kr":             "" if not desc or re.sub(r'[^a-z0-9]','',title.lower())[:30] in re.sub(r'[^a-z0-9]','',desc.lower()) and len(desc) < len(title) + 30 else re.sub(r'<[^>]+>', '', desc)[:150],
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


def fetch_article_summary(url: str, title: str) -> str:
    """기사 본문 첫 단락 추출 — 요약용 (최대 500자)"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        body = resp.text

        # <p> 태그에서 텍스트 추출
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', body, re.DOTALL | re.IGNORECASE)
        chunks = []
        for p in paragraphs:
            text = re.sub(r'<[^>]+>', '', p).strip()
            text = html.unescape(text)
            # 너무 짧거나 메뉴/광고성 텍스트 제외
            if len(text) < 40:
                continue
            if any(w in text.lower() for w in ["cookie", "subscribe", "sign in", "newsletter", "advertisement", "©"]):
                continue
            chunks.append(text)
            if sum(len(c) for c in chunks) >= 500:
                break

        result = " ".join(chunks)[:500]
        return result if len(result) > 80 else ""
    except Exception:
        return ""


def gtranslate(text: str) -> str:
    """Google Translate 비공식 API — 무료, 키 없음"""
    if not text or not text.strip():
        return text
    try:
        url    = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "en", "tl": "ko", "dt": "t", "q": text}
        resp   = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data   = resp.json()
        return "".join(seg[0] for seg in data[0] if seg[0])
    except Exception:
        return text


def translate_articles(articles: list) -> list:
    """기사 본문 fetch → 요약 추출 → 한국어 번역"""
    total = len(articles)
    for i, a in enumerate(articles):
        try:
            # 1) 제목 번역
            a["title"] = gtranslate(a.get("title", ""))

            # 2) 요약: RSS snippet이 짧으면 본문 직접 fetch
            s = a.get("summary_kr", "").strip()
            if len(s) < 80:
                s = fetch_article_summary(a.get("url", ""), a.get("title", ""))

            # 3) 요약 번역
            if s:
                a["summary_kr"] = gtranslate(s[:500])
            else:
                a["summary_kr"] = ""

            if (i + 1) % 5 == 0:
                print(f"  번역/요약 {i+1}/{total}...")
            time.sleep(0.5)
        except Exception as e:
            print(f"  [WARN] {i+1}번 실패: {e}")

    print(f"  ✅ 완료 ({total}건)")
    return articles


def generate_takeaways(articles: list) -> list:
    """규칙 기반 Takeaways — AI 없음, 완전 무료"""
    cat_counts = {}
    for a in articles:
        cat_counts[a.get("category","?")] = cat_counts.get(a.get("category","?"), 0) + 1

    risk_articles = [a for a in articles if "risk" in a.get("tags", [])]
    opp_articles  = [a for a in articles if "opp"  in a.get("tags", [])]
    comp_articles = [a for a in articles if a.get("category") == "Competitor Analysis"]

    def top_title(lst):
        return lst[0]["title"] if lst else "—"

    takeaways = [
        {
            "trend_label": "🔴 리스크 모니터링",
            "title": f"주요 리스크 {len(risk_articles)}건 감지",
            "desc": (
                f"오늘 수집된 {len(articles)}건 중 {len(risk_articles)}건이 리스크 신호를 포함합니다. "
                f"주요 이슈: {top_title(risk_articles)}. "
                f"경쟁사 동향 {cat_counts.get('Competitor Analysis',0)}건 포함 면밀한 모니터링이 필요합니다."
            ),
        },
        {
            "trend_label": "🟢 기회 신호",
            "title": f"시장 기회 {len(opp_articles)}건 포착",
            "desc": (
                f"신규 출시·성장·수상 관련 긍정 신호 {len(opp_articles)}건이 감지됩니다. "
                f"주목 기사: {top_title(opp_articles)}. "
                f"삼성 Bespoke {cat_counts.get('Samsung Bespoke',0)}건, "
                f"Jet Bot {cat_counts.get('Samsung Jet Bot',0)}건 커버리지 확인 바랍니다."
            ),
        },
        {
            "trend_label": "🟡 경쟁사 동향",
            "title": f"경쟁사 기사 {cat_counts.get('Competitor Analysis',0)}건",
            "desc": (
                f"LG·Whirlpool·Haier 등 주요 경쟁사 관련 {cat_counts.get('Competitor Analysis',0)}건 수집. "
                f"주요 동향: {top_title(comp_articles)}. "
                f"시장 전반 기사 {cat_counts.get('Market Dynamics',0)}건, "
                f"기술 트렌드 {cat_counts.get('Technology Trend',0)}건 함께 검토 권장."
            ),
        },
    ]
    return takeaways


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
    print(f" 수집: Google News RSS + Bing News RSS (완전 무료)")
    print(f" 번역: Google Translate | Takeaways: 규칙 기반")
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
    articles.sort(key=lambda a: a.get("pub_ts", 0), reverse=True)
    print(f"\n  원본 {len(raw)}개 → 중복 제거 후 {len(articles)}개 (최신순)\n")

    if not articles:
        print("[WARN] 수집된 기사 없음")
        save_data([], [
            {"trend_label": "⚠ 수집 오류", "title": "24시간 내 관련 뉴스 없음", "desc": "관련 뉴스가 없습니다."},
            {"trend_label": "—", "title": "—", "desc": "—"},
            {"trend_label": "—", "title": "—", "desc": "—"},
        ])
        return

    print("[2/4] 한국어 번역 중 (Google Translate)...")
    articles = translate_articles(articles)

    print("[3/4] Takeaways 생성 중 (규칙 기반)...")
    takeaways = generate_takeaways(articles)
    print(f"  ✅ {len(takeaways)}개 생성")

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
