"""
Samsung DA Strategy Briefing — News Fetcher
Claude web_search + after:YYYY-MM-DD 연산자로 24시간 필터
"""

import os, json
import anthropic
from datetime import datetime, timedelta, timezone

ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
DATA_DIR      = "data"
MAX_ARTICLES  = 12

KST       = timezone(timedelta(hours=9))
NOW       = datetime.now(KST)
TODAY_STR = NOW.strftime("%Y-%m-%d")
YESTERDAY = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")

# 카테고리별 검색 쿼리 — after: 연산자로 24시간 강제 필터
SEARCH_QUERIES = [
    {"category": "Samsung DA",
     "q": f"Samsung home appliance Bespoke SmartThings after:{YESTERDAY}"},
    {"category": "Competitor Analysis",
     "q": f"LG Haier Whirlpool home appliance strategy after:{YESTERDAY}"},
    {"category": "Technology Trend",
     "q": f"AI smart home appliance Matter energy after:{YESTERDAY}"},
    {"category": "Product Reviews",
     "q": f"best refrigerator washing machine review 2025 after:{YESTERDAY}"},
    {"category": "Macro / Policy",
     "q": f"tariff trade policy home appliance after:{YESTERDAY}"},
    {"category": "Market Dynamics",
     "q": f"home appliance market growth after:{YESTERDAY}"},
    {"category": "Supply Chain",
     "q": f"rare earth semiconductor appliance supply chain after:{YESTERDAY}"},
]


def search_and_analyze() -> tuple[list, list]:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    system = """당신은 삼성전자 DA(가전) 부문 임원을 위한 전략 브리핑 작성 전문가입니다.
web_search 툴로 최신 뉴스를 검색하고 MBB 컨설팅 수준으로 분석합니다.

중요: 검색 결과에서 반드시 발행일을 확인하세요.
어제({yesterday}) 이후 발행된 기사만 포함하세요. 오래된 기사는 절대 포함하지 마세요.
최종 출력은 순수 JSON만 반환합니다. 마크다운 코드블록 금지.""".format(yesterday=YESTERDAY)

    queries_text = "\n".join(
        f'{i+1}. [{q["category"]}] 검색어: {q["q"]}'
        for i, q in enumerate(SEARCH_QUERIES)
    )

    user = f"""오늘은 {TODAY_STR}입니다. {YESTERDAY} 이후 기사만 수집하세요.

아래 7개 쿼리를 각각 web_search로 검색하세요:
{queries_text}

각 검색마다:
1. 결과에서 발행일 확인 → {YESTERDAY} 이전 기사는 무시
2. 제목/본문/URL 수집
3. 중복 URL 제거

전체 검색 완료 후, 아래 형식으로 출력:

[기사 배열 JSON]
[
  {{
    "category": "카테고리명",
    "title": "한국어 번역 20자 내외",
    "media": "언론사명 (국가)",
    "impact": 1~5,
    "time": "몇 시간 전 (발행일 기준으로 계산)",
    "url": "실제 기사 URL",
    "summary_kr": "2~3문장 핵심 요약 (수치 포함)",
    "strategic_implications": "삼성 DA 위기/기회 + 대응 제언 2~3문장",
    "tags": ["risk"/"opp"/"watch" 1~3개]
  }}
]

[Top 3 Takeaways JSON]
[
  {{
    "trend_label": "흐름 레이블",
    "title": "핵심 전략 메시지 25자 내외",
    "desc": "삼성 DA 전략적 의미 3~4문장"
  }}
]

규칙:
- 최대 {MAX_ARTICLES}개 기사
- {YESTERDAY} 이전 기사 절대 포함 금지
- impact 5 최대 3개
- 두 JSON 배열만 출력, 다른 텍스트 없이"""

    print(f"  검색 기준일: {YESTERDAY} 이후")
    print(f"  쿼리 {len(SEARCH_QUERIES)}개 검색 중...")

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
    )

    # 텍스트 블록 수집
    full_text = ""
    search_count = 0
    for block in resp.content:
        if block.type == "text":
            full_text += block.text
        elif hasattr(block, 'type') and block.type == "tool_use":
            search_count += 1
            print(f"  검색 {search_count}: {getattr(block, 'input', {}).get('query', '')[:60]}")

    print(f"  총 {search_count}회 검색 완료")
    print(f"  응답 길이: {len(full_text)}자")

    return parse_two_json_arrays(full_text)


def parse_two_json_arrays(text: str) -> tuple[list, list]:
    text = text.strip()

    # 마크다운 코드블록 제거
    if "```" in text:
        cleaned = []
        for part in text.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("[") or part.startswith("{"):
                cleaned.append(part)
        text = "\n".join(cleaned)

    # [ ... ] 블록 추출
    arrays = []
    i = 0
    while i < len(text) and len(arrays) < 2:
        if text[i] == "[":
            depth, j = 0, i
            while j < len(text):
                if text[j] == "[":
                    depth += 1
                elif text[j] == "]":
                    depth -= 1
                    if depth == 0:
                        try:
                            arr = json.loads(text[i:j+1])
                            if isinstance(arr, list):
                                arrays.append(arr)
                        except json.JSONDecodeError:
                            pass
                        i = j + 1
                        break
                j += 1
            else:
                i = j
        else:
            i += 1

    articles  = arrays[0] if len(arrays) > 0 else []
    takeaways = arrays[1] if len(arrays) > 1 else [
        {"trend_label": "— 분석 중", "title": "오늘의 주요 동향", "desc": "데이터 집계 중입니다."},
        {"trend_label": "—", "title": "—", "desc": "—"},
        {"trend_label": "—", "title": "—", "desc": "—"},
    ]
    return articles, takeaways


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

    articles, takeaways = search_and_analyze()
    print(f"\n  수집 결과: 기사 {len(articles)}개")

    if not articles:
        print("[WARN] 기사 없음 — 빈 파일 저장")
        save_data([], [
            {"trend_label": "⚠ 수집 오류", "title": "뉴스 수집 실패", "desc": "잠시 후 다시 실행해주세요."},
            {"trend_label": "—", "title": "—", "desc": "—"},
            {"trend_label": "—", "title": "—", "desc": "—"},
        ])
        return

    save_data(articles, takeaways)


if __name__ == "__main__":
    main()
