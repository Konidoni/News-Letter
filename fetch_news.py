"""
Samsung DA Strategy Briefing — News Fetcher
Claude web_search + after:날짜 연산자 (24h 필터)
Rate limit 대응: 쿼리를 3개씩 나눠서 호출 + 딜레이
"""

import os, json, time
import anthropic
from datetime import datetime, timedelta, timezone

ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
DATA_DIR      = "data"
MAX_ARTICLES  = 12

KST       = timezone(timedelta(hours=9))
NOW       = datetime.now(KST)
TODAY_STR = NOW.strftime("%Y-%m-%d")
YESTERDAY = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")

# 카테고리별 쿼리 — 3개씩 배치로 분할
QUERY_BATCHES = [
    [
        {"category": "Samsung DA",          "q": f"Samsung home appliance Bespoke SmartThings after:{YESTERDAY}"},
        {"category": "Competitor Analysis", "q": f"LG Haier Whirlpool home appliance strategy after:{YESTERDAY}"},
        {"category": "Technology Trend",    "q": f"AI smart home appliance Matter energy after:{YESTERDAY}"},
    ],
    [
        {"category": "Product Reviews",     "q": f"best refrigerator washing machine review 2025 after:{YESTERDAY}"},
        {"category": "Macro / Policy",      "q": f"tariff trade policy home appliance after:{YESTERDAY}"},
        {"category": "Market Dynamics",     "q": f"home appliance market growth after:{YESTERDAY}"},
        {"category": "Supply Chain",        "q": f"rare earth semiconductor appliance supply chain after:{YESTERDAY}"},
    ],
]

SYSTEM_PROMPT = f"""당신은 삼성전자 DA(가전) 부문 임원을 위한 전략 브리핑 작성 전문가입니다.
web_search로 최신 뉴스를 검색하고 MBB 컨설팅 수준으로 분석합니다.

핵심 규칙:
- {YESTERDAY} 이후 발행된 기사만 포함 (오래된 기사 절대 금지)
- 최종 출력은 순수 JSON 배열만 (마크다운 코드블록 금지)"""


def search_batch(queries: list) -> list:
    """쿼리 배치 1개를 Claude web_search로 처리 → 기사 리스트 반환"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    queries_text = "\n".join(
        f'- [{q["category"]}] {q["q"]}' for q in queries
    )

    user = f"""아래 쿼리들을 각각 web_search로 검색하고, {YESTERDAY} 이후 기사만 골라 JSON 배열로 반환하세요.

검색 쿼리:
{queries_text}

출력 형식 (순수 JSON 배열만):
[
  {{
    "category": "카테고리명",
    "title": "한국어 번역 20자 내외",
    "media": "언론사 (국가)",
    "impact": 1~5,
    "time": "X시간 전",
    "url": "실제 기사 URL",
    "summary_kr": "2~3문장 핵심 요약",
    "strategic_implications": "삼성 DA 위기/기회 + 대응 제언",
    "tags": ["risk"/"opp"/"watch" 1~3개]
  }}
]

규칙: {YESTERDAY} 이전 기사 제외, JSON만 반환"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
    )

    full_text = ""
    for block in resp.content:
        if block.type == "text":
            full_text += block.text

    return parse_json_array(full_text)


def parse_json_array(text: str) -> list:
    """텍스트에서 JSON 배열 1개 추출"""
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
    """수집된 기사 전체로 Top 3 Takeaways 생성"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system="삼성전자 DA 임원 Top 3 전략 통찰 작성 전문가. JSON 배열만 반환.",
        messages=[{"role": "user", "content": f"""오늘 뉴스 기반 삼성전자 DA 임원 Top 3 전략 통찰.

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
    print(f"\n✅ 저장 → {day_file}")
    print(f"   기사 {len(articles)}개  |  {cat_counts}")

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
    print(f" 24h 필터: after:{YESTERDAY}")
    print(f"{'='*60}")

    all_articles = []

    for i, batch in enumerate(QUERY_BATCHES):
        print(f"\n[배치 {i+1}/{len(QUERY_BATCHES)}] {len(batch)}개 쿼리 검색 중...")
        try:
            articles = search_batch(batch)
            print(f"  → {len(articles)}개 기사 수집")
            all_articles.extend(articles)
        except anthropic.RateLimitError:
            print(f"  [WARN] Rate limit — 60초 대기 후 재시도...")
            time.sleep(60)
            try:
                articles = search_batch(batch)
                print(f"  → {len(articles)}개 기사 수집 (재시도 성공)")
                all_articles.extend(articles)
            except Exception as e:
                print(f"  [ERROR] 배치 {i+1} 실패: {e}")
        except Exception as e:
            print(f"  [ERROR] 배치 {i+1} 실패: {e}")

        # 배치 간 30초 딜레이 (Rate limit 방지)
        if i < len(QUERY_BATCHES) - 1:
            print(f"  30초 대기 중 (Rate limit 방지)...")
            time.sleep(30)

    # 중복 URL 제거
    seen, unique = set(), []
    for a in all_articles:
        if a.get("url") not in seen:
            seen.add(a.get("url"))
            unique.append(a)
    all_articles = unique[:MAX_ARTICLES]

    print(f"\n  총 수집: {len(all_articles)}개 기사")

    if not all_articles:
        print("[WARN] 기사 없음")
        save_data([], [
            {"trend_label": "⚠ 수집 오류", "title": "뉴스 수집 실패", "desc": "잠시 후 다시 실행해주세요."},
            {"trend_label": "—", "title": "—", "desc": "—"},
            {"trend_label": "—", "title": "—", "desc": "—"},
        ])
        return

    print("\n[Takeaways] Top 3 생성 중...")
    try:
        takeaways = generate_takeaways(all_articles)
    except Exception as e:
        print(f"  [WARN] Takeaways 생성 실패: {e}")
        takeaways = [
            {"trend_label": "—", "title": "오늘의 주요 동향", "desc": "분석 데이터를 확인하세요."},
            {"trend_label": "—", "title": "—", "desc": "—"},
            {"trend_label": "—", "title": "—", "desc": "—"},
        ]

    save_data(all_articles, takeaways)


if __name__ == "__main__":
    main()
