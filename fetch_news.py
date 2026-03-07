"""
Samsung DA Strategy Briefing — News Fetcher
Claude web_search 사용. 7일 이내 기사 수집 (24h 뉴스 없는 날 대응)
발행일을 기사에 명시해서 임원이 날짜 확인 가능
"""

import os, json, time
import anthropic
from datetime import datetime, timedelta, timezone

ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
DATA_DIR      = "data"
MAX_ARTICLES  = 12

KST           = timezone(timedelta(hours=9))
NOW           = datetime.now(KST)
TODAY_STR     = NOW.strftime("%Y-%m-%d")
WEEK_AGO      = (NOW - timedelta(days=7)).strftime("%Y-%m-%d")
YESTERDAY     = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")

QUERY_BATCHES = [
    [
        {"category": "Samsung DA",          "q": f"samsung bespoke after:{WEEK_AGO}"},
        {"category": "Samsung DA",          "q": f"samsung after:{WEEK_AGO}"},
        {"category": "Technology Trend",    "q": f"smart home appliance after:{WEEK_AGO}"},
        {"category": "Market Dynamics",     "q": f"home appliance after:{WEEK_AGO}"},
    ],
    [
        {"category": "Competitor Analysis", "q": f"lg electronics after:{WEEK_AGO}"},
        {"category": "Competitor Analysis", "q": f"whirlpool after:{WEEK_AGO}"},
        {"category": "Competitor Analysis", "q": f"haier after:{WEEK_AGO}"},
        {"category": "Market Dynamics",     "q": f"kitchen appliance after:{WEEK_AGO}"},
    ],
]

SYSTEM_PROMPT = f"""당신은 삼성전자 DA(가전) 부문 임원을 위한 전략 브리핑 작성 전문가입니다.
web_search로 최신 뉴스를 검색하고 MBB 컨설팅 수준으로 분석합니다.

날짜 기준: {WEEK_AGO} 이후 기사만 포함. 더 오래된 기사는 절대 포함 금지.
최종 출력은 순수 JSON 배열만 반환. 마크다운 코드블록 금지."""


def search_batch(queries: list) -> list:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    queries_text = "\n".join(
        f'- [{q["category"]}] {q["q"]}' for q in queries
    )

    user = f"""아래 쿼리들을 web_search로 검색하고, {WEEK_AGO} 이후 기사만 골라 JSON 배열로 반환하세요.
오늘은 {TODAY_STR}입니다.

검색 쿼리:
{queries_text}

출력 형식 (순수 JSON 배열만):
[
  {{
    "category": "카테고리명",
    "title": "한국어 번역 20자 내외",
    "media": "언론사 (국가)",
    "impact": 1~5,
    "time": "발행일 표시 — 오늘이면 'X시간 전', 어제면 '1일 전', 그 이전이면 'MM월 DD일'",
    "url": "실제 기사 URL",
    "summary_kr": "2~3문장 핵심 요약 (수치 포함)",
    "strategic_implications": "삼성 DA 위기/기회 + 대응 제언 2~3문장",
    "tags": ["risk"/"opp"/"watch" 1~3개]
  }}
]

규칙:
- {WEEK_AGO} 이전 기사 절대 포함 금지
- 각 카테고리당 최대 2개
- JSON만 반환, 다른 텍스트 없이"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
    )

    full_text = ""
    search_count = 0
    for block in resp.content:
        if block.type == "text":
            full_text += block.text
        elif block.type == "tool_use":
            search_count += 1
            q = getattr(block, 'input', {}).get('query', '')
            print(f"    검색: {q[:60]}")

    print(f"    {search_count}회 검색 → 텍스트 {len(full_text)}자")
    return parse_json_array(full_text)


def parse_json_array(text: str) -> list:
    text = text.strip()
    if "```" in text:
        for part in text.split("```"):
            part = part.lstrip("json").strip()
            if part.startswith("["):
                text = part
                break

    i = text.find("[")
    if i == -1:
        return []
    depth, j = 0, i
    while j < len(text):
        if text[j] == "[":
            depth += 1
        elif text[j] == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[i:j+1])
                except json.JSONDecodeError:
                    return []
        j += 1
    return []


def generate_takeaways(articles: list) -> list:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system="삼성전자 DA 임원 Top 3 전략 통찰 전문가. JSON 배열만 반환.",
        messages=[{"role": "user", "content": f"""오늘({TODAY_STR}) 뉴스 기반 삼성전자 DA 임원 Top 3 전략 통찰.

뉴스: {json.dumps(articles, ensure_ascii=False)}

출력 (JSON 배열 정확히 3개):
[{{"trend_label":"흐름 레이블","title":"25자 핵심 메시지","desc":"3~4문장 전략적 의미"}}]
JSON만."""}],
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
    print(f" 수집 범위: {WEEK_AGO} 이후 (최근 7일)")
    print(f"{'='*60}")

    all_articles = []

    for i, batch in enumerate(QUERY_BATCHES):
        print(f"\n[배치 {i+1}/{len(QUERY_BATCHES)}] {len(batch)}개 쿼리...")
        try:
            articles = search_batch(batch)
            print(f"  → {len(articles)}개 수집")
            all_articles.extend(articles)
        except anthropic.RateLimitError:
            print("  Rate limit — 60초 대기...")
            time.sleep(60)
            try:
                articles = search_batch(batch)
                all_articles.extend(articles)
                print(f"  → {len(articles)}개 수집 (재시도)")
            except Exception as e:
                print(f"  [ERROR] {e}")
        except Exception as e:
            print(f"  [ERROR] {e}")

        if i < len(QUERY_BATCHES) - 1:
            print("  30초 대기...")
            time.sleep(30)

    # 중복 제거
    seen, unique = set(), []
    for a in all_articles:
        url = a.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(a)
    all_articles = unique[:MAX_ARTICLES]

    print(f"\n  총 수집: {len(all_articles)}개")

    if not all_articles:
        print("[WARN] 기사 없음")
        save_data([], [
            {"trend_label": "⚠ 수집 오류", "title": "이번 주 주요 뉴스 없음", "desc": "최근 7일간 관련 뉴스가 없습니다."},
            {"trend_label": "—", "title": "—", "desc": "—"},
            {"trend_label": "—", "title": "—", "desc": "—"},
        ])
        return

    print("\n[Takeaways] 생성 중...")
    try:
        takeaways = generate_takeaways(all_articles)
    except Exception as e:
        print(f"  [WARN] {e}")
        takeaways = [
            {"trend_label": "—", "title": "오늘의 주요 동향", "desc": "아래 기사를 참조하세요."},
            {"trend_label": "—", "title": "—", "desc": "—"},
            {"trend_label": "—", "title": "—", "desc": "—"},
        ]

    save_data(all_articles, takeaways)


if __name__ == "__main__":
    main()
