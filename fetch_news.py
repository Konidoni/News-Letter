"""
Samsung DA Strategy Briefing — News Fetcher
Claude web_search 툴로 직접 검색 + 분석 (API 키 NewsAPI 불필요)
검색 시 24시간 필터 적용 → 수집/분석 1단계로 완료
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

# 카테고리별 검색 쿼리
SEARCH_QUERIES = [
    {"category": "Samsung DA",          "q": "Samsung home appliance Bespoke SmartThings news"},
    {"category": "Competitor Analysis", "q": "LG Haier Whirlpool home appliance strategy news"},
    {"category": "Technology Trend",    "q": "AI smart home appliance Matter energy news"},
    {"category": "Product Reviews",     "q": "best refrigerator washing machine 2025 review ranked"},
    {"category": "Macro / Policy",      "q": "tariff trade policy home appliance manufacturing news"},
    {"category": "Market Dynamics",     "q": "home appliance market growth India Southeast Asia news"},
    {"category": "Supply Chain",        "q": "rare earth semiconductor appliance supply chain news"},
]


def search_and_analyze() -> tuple[list, list]:
    """Claude web_search로 검색 + 분석 한 번에"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    system = """당신은 삼성전자 DA(가전) 부문 임원을 위한 전략 브리핑 작성 전문가입니다.
web_search 툴로 최신 뉴스를 검색하고, MBB 컨설팅 수준으로 분석합니다.
최종 출력은 순수 JSON만 반환합니다. 마크다운 코드블록 절대 금지."""

    queries_text = "\n".join(
        f'- [{q["category"]}] {q["q"]}' for q in SEARCH_QUERIES
    )

    user = f"""아래 7개 카테고리에 대해 web_search로 최근 뉴스를 검색하고, 삼성전자 DA 임원 브리핑용 JSON을 생성하세요.

## 검색 카테고리 및 쿼리:
{queries_text}

## 검색 방법:
- 각 쿼리로 web_search 실행
- 검색 결과에서 실제 기사 URL, 제목, 내용을 수집
- 중복 제거 후 최대 {MAX_ARTICLES}개 선별

## 최종 출력 형식 (순수 JSON 2개):
첫 번째: 기사 배열
[
  {{
    "category": "카테고리명 (위 카테고리 그대로)",
    "title": "한국어 번역/의역 20자 내외",
    "media": "언론사명 (국가)",
    "impact": 1~5 정수 (5=즉각 경영 의사결정 필요),
    "time": "X시간 전 또는 X일 전",
    "url": "실제 기사 URL",
    "summary_kr": "What happened — 구체적 수치/사실 포함 2~3문장",
    "strategic_implications": "삼성 DA 관점 위기/기회 분석 + 실행 대응 제언 2~3문장",
    "tags": ["risk"/"opp"/"watch" 중 1~3개]
  }}
]

두 번째: Top 3 Takeaways 배열
[
  {{
    "trend_label": "핵심 흐름 레이블 (예: ▲ Structural Shift)",
    "title": "임원이 즉시 이해하는 핵심 전략 메시지 25자 내외",
    "desc": "삼성 DA 전략적 의미와 구체적 대응 방향 3~4문장"
  }}
]

## 출력 규칙:
- 기사 배열 JSON → 빈 줄 → Takeaways 배열 JSON 순으로만 출력
- 다른 텍스트 절대 없이
- impact 5는 최대 3개
- Product Reviews는 삼성 vs LG·Whirlpool 순위 비교 필수"""

    print("  Claude web_search로 검색 + 분석 중...")

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
    )

    # 응답에서 텍스트 블록 추출
    full_text = ""
    for block in resp.content:
        if block.type == "text":
            full_text += block.text

    print(f"  응답 길이: {len(full_text)}자")

    # JSON 두 배열 파싱
    return parse_two_json_arrays(full_text)


def parse_two_json_arrays(text: str) -> tuple[list, list]:
    """텍스트에서 JSON 배열 2개 추출"""
    # 마크다운 코드블록 제거
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        text  = " ".join(p.lstrip("json").strip() for p in parts if p.strip() and not p.strip().startswith("json") or "[" in p)

    # [ ... ] 블록 2개 추출
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
    takeaways = arrays[1] if len(arrays) > 1 else []

    # Takeaways가 없으면 articles에서 생성
    if not takeaways and articles:
        takeaways = [
            {"trend_label": "— 분석 중", "title": "오늘의 주요 동향", "desc": "브리핑 분석 중입니다."},
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
    print(f"\n✅ 저장 → {day_file}  |  {cat_counts}")

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
    print(f"   manifest: {len(dates)}일치  |  아카이브 누적")


def main():
    print(f"\n{'='*60}")
    print(f" Samsung DA Briefing  |  {NOW.strftime('%Y-%m-%d %H:%M KST')}")
    print(f" Source: Claude web_search (24h filter 자동 적용)")
    print(f"{'='*60}")

    articles, takeaways = search_and_analyze()
    print(f"\n  기사: {len(articles)}개  |  Takeaways: {len(takeaways)}개")

    if not articles:
        print("[ERROR] 기사 없음 — 빈 파일 저장")
        save_data([], [
            {"trend_label": "⚠ 수집 오류", "title": "뉴스 수집 실패", "desc": "잠시 후 다시 실행해주세요."},
            {"trend_label": "—", "title": "—", "desc": "—"},
            {"trend_label": "—", "title": "—", "desc": "—"},
        ])
        return

    save_data(articles, takeaways)


if __name__ == "__main__":
    main()
