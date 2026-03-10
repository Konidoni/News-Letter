"""
Samsung DA Strategy Briefing — Dashboard Builder
data/manifest.json + data/YYYY-MM-DD.json → index.html
날짜 탭으로 과거 브리핑 열람 가능
"""

import json
from pathlib import Path

DATA_DIR    = "data"
OUTPUT_FILE = "index.html"


def load_manifest():
    p = Path(DATA_DIR) / "manifest.json"
    if not p.exists():
        return {"dates": [], "latest": ""}
    return json.loads(p.read_text(encoding="utf-8"))


def load_day(date_str: str) -> dict:
    p = Path(DATA_DIR) / f"{date_str}.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def build_html(manifest: dict, days_data: dict) -> str:
    dates      = manifest.get("dates", [])
    latest     = manifest.get("latest", dates[0] if dates else "")
    # JS에 넘길 전체 데이터 (날짜 → 데이터 맵)
    all_data_json = json.dumps(days_data, ensure_ascii=False)
    dates_json    = json.dumps(dates, ensure_ascii=False)
    latest_json   = json.dumps(latest, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Samsung DA | Global Appliance Strategy Briefing</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700;900&family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
  --samsung-blue:#1428A0;--samsung-blue-accent:#2A50D8;--samsung-sky:#1A6FE8;
  --bg-deep:#F5F0E8;--bg-card:#FFFDF8;--bg-card-hover:#FFF8ED;
  --border:rgba(0,0,0,0.09);--border-blue:rgba(20,40,160,0.2);
  --text-primary:#1A1A2E;--text-secondary:#3D3D5C;--text-muted:#8A8AA8;
  --accent-gold:#B8860B;--accent-red:#C0392B;--accent-green:#1A7A4A;
  --font-display:'DM Serif Display',serif;
  --font-body:'Noto Sans KR',sans-serif;
  --font-mono:'DM Mono',monospace;
}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:var(--font-body);background:var(--bg-deep);color:var(--text-primary);min-height:100vh;-webkit-font-smoothing:antialiased;overflow-x:hidden;}}
body::before{{content:'';position:fixed;top:0;left:0;width:100%;height:100%;background:radial-gradient(ellipse 80% 50% at 20% -10%,rgba(20,40,160,.06) 0%,transparent 60%),radial-gradient(ellipse 60% 40% at 80% 100%,rgba(20,40,160,.04) 0%,transparent 50%);pointer-events:none;z-index:0;}}
.wrapper{{position:relative;z-index:1;max-width:1440px;margin:0 auto;padding:0 24px;}}

/* HEADER */
header{{border-bottom:1px solid var(--border);background:rgba(245,240,232,.95);backdrop-filter:blur(20px);position:sticky;top:0;z-index:100;}}
.header-inner{{display:flex;align-items:center;justify-content:space-between;padding:14px 24px;max-width:1440px;margin:0 auto;gap:12px;flex-wrap:wrap;}}
.header-left{{display:flex;align-items:center;gap:14px;}}
.logo-mark{{width:34px;height:34px;background:var(--samsung-blue);border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#fff;flex-shrink:0;letter-spacing:.05em;}}
.header-title-main{{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;}}
.header-title-sub{{font-size:10px;color:var(--text-secondary);letter-spacing:.04em;margin-top:2px;}}
.header-right{{display:flex;align-items:center;gap:10px;}}
.live-badge{{display:flex;align-items:center;gap:5px;font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent-green);font-family:var(--font-mono);}}
.live-dot{{width:5px;height:5px;border-radius:50%;background:var(--accent-green);animation:pulse 2s infinite;}}
@keyframes pulse{{0%,100%{{opacity:1;transform:scale(1);}}50%{{opacity:.5;transform:scale(1.4);}}}}
.timestamp{{font-size:10px;color:var(--text-muted);font-family:var(--font-mono);}}
.refresh-btn{{display:flex;align-items:center;gap:5px;padding:6px 12px;border-radius:7px;border:1px solid rgba(20,40,160,.3);background:rgba(20,40,160,.08);color:var(--samsung-blue);font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;cursor:pointer;text-decoration:none;transition:all .2s;font-family:var(--font-mono);white-space:nowrap;}}
.refresh-btn:hover{{background:rgba(20,40,160,.15);border-color:var(--samsung-blue);color:var(--samsung-blue);}}
.refresh-btn svg{{transition:transform .4s;}}
.refresh-btn:hover svg{{transform:rotate(180deg);}}

/* DATE TABS */
.date-tabs-wrap{{background:rgba(245,240,232,.9);border-bottom:1px solid var(--border);backdrop-filter:blur(10px);position:sticky;top:62px;z-index:90;overflow-x:auto;scrollbar-width:none;}}
.date-tabs-wrap::-webkit-scrollbar{{display:none;}}
.date-tabs{{display:flex;gap:0;padding:0 24px;max-width:1440px;margin:0 auto;width:max-content;min-width:100%;}}
.date-tab{{padding:10px 18px;font-size:12px;font-weight:600;color:var(--text-muted);cursor:pointer;border:none;background:transparent;border-bottom:2px solid transparent;white-space:nowrap;transition:all .2s;font-family:var(--font-body);letter-spacing:.02em;}}
.date-tab:hover{{color:var(--text-secondary);}}
.date-tab.active{{color:var(--samsung-blue);border-bottom-color:var(--samsung-blue);}}
.date-tab.today-tab{{color:var(--accent-green);}}
.date-tab.today-tab.active{{border-bottom-color:var(--accent-green);}}

/* SEARCH */
.search-container{{padding:18px 24px 0;max-width:1440px;margin:0 auto;display:flex;gap:10px;align-items:center;flex-wrap:wrap;}}
.search-wrap{{position:relative;flex:1;min-width:200px;max-width:400px;}}
.search-wrap svg{{position:absolute;left:13px;top:50%;transform:translateY(-50%);color:var(--text-muted);pointer-events:none;}}
.search-input{{width:100%;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:9px 13px 9px 38px;font-size:13px;color:var(--text-primary);font-family:var(--font-body);outline:none;transition:border-color .2s;}}
.search-input::placeholder{{color:var(--text-muted);}}
.search-input:focus{{border-color:var(--samsung-blue-accent);}}
.filter-chips{{display:flex;gap:7px;flex-wrap:wrap;}}
.chip{{padding:6px 13px;border-radius:20px;font-size:11px;font-weight:500;cursor:pointer;border:1px solid var(--border);background:transparent;color:var(--text-secondary);transition:all .2s;white-space:nowrap;}}
.chip:hover{{border-color:var(--samsung-blue-accent);color:var(--text-primary);}}
.chip.active{{background:var(--samsung-blue);border-color:var(--samsung-blue);color:#fff;}}

/* SECTION */
.section{{padding:24px 0;}}
.section-label{{font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--samsung-sky);margin-bottom:14px;display:flex;align-items:center;gap:8px;}}
.section-label::after{{content:'';flex:1;height:1px;background:linear-gradient(90deg,var(--border-blue),transparent);}}

/* TAKEAWAYS */
.takeaways-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;}}
@media(max-width:900px){{.takeaways-grid{{grid-template-columns:1fr;}}}}
.takeaway-card{{background:linear-gradient(135deg,rgba(20,40,160,.07),rgba(240,235,225,.9));border:1px solid rgba(20,40,160,.15);border-radius:12px;padding:18px;position:relative;overflow:hidden;transition:transform .2s,border-color .2s;box-shadow:0 2px 12px rgba(0,0,0,.06);}}
.takeaway-card:hover{{transform:translateY(-2px);border-color:rgba(20,40,160,.3);box-shadow:0 6px 20px rgba(0,0,0,.1);}}
.takeaway-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--samsung-blue),#6AABFF);}}
.takeaway-num{{font-family:var(--font-display);font-size:44px;line-height:1;color:rgba(20,40,160,.12);position:absolute;top:10px;right:14px;font-style:italic;}}
.takeaway-trend{{font-size:9px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--accent-gold);margin-bottom:7px;font-family:var(--font-mono);}}
.takeaway-title{{font-size:14px;font-weight:700;line-height:1.45;margin-bottom:8px;padding-right:38px;}}
.takeaway-desc{{font-size:12px;color:var(--text-secondary);line-height:1.7;}}

/* STATS */
.stats-bar{{display:flex;border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:24px;flex-wrap:wrap;background:var(--bg-card);box-shadow:0 1px 6px rgba(0,0,0,.05);}}
.stat-item{{flex:1;min-width:100px;padding:12px 18px;border-right:1px solid var(--border);display:flex;flex-direction:column;gap:3px;}}
.stat-item:last-child{{border-right:none;}}
.stat-value{{font-size:20px;font-weight:900;letter-spacing:-.02em;font-family:var(--font-mono);}}
.stat-label{{font-size:10px;color:var(--text-muted);font-weight:500;}}
.stat-delta{{font-size:10px;font-weight:700;font-family:var(--font-mono);}}
.delta-up{{color:var(--accent-green);}}.delta-down{{color:var(--accent-red);}}

/* NEWS */
.news-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px;}}
@media(max-width:580px){{.news-grid{{grid-template-columns:1fr;}}}}
a.news-card{{display:block;text-decoration:none;color:inherit;}}
.news-card{{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px;transition:all .25s;animation:fadeInUp .35s ease both;box-shadow:0 1px 6px rgba(0,0,0,.05);}}
.news-card:hover{{background:var(--bg-card-hover);border-color:rgba(20,40,160,.2);transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.1);}}
.card-header{{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:12px;}}
.category-badge{{font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;padding:3px 9px;border-radius:4px;white-space:nowrap;font-family:var(--font-mono);}}
.cat-competitor{{background:rgba(192,57,43,.1);color:#A0291D;border:1px solid rgba(192,57,43,.2);}}
.cat-tech{{background:rgba(20,40,160,.1);color:#1428A0;border:1px solid rgba(20,40,160,.2);}}
.cat-macro{{background:rgba(184,134,11,.1);color:#8A6500;border:1px solid rgba(184,134,11,.2);}}
.cat-market{{background:rgba(26,122,74,.1);color:#145C38;border:1px solid rgba(26,122,74,.2);}}
.cat-supply{{background:rgba(100,60,180,.1);color:#5A2EA0;border:1px solid rgba(100,60,180,.2);}}
.cat-samsung{{background:rgba(20,40,160,.1);color:#1428A0;border:1px solid rgba(20,40,160,.25);}}
.cat-reviews{{background:rgba(180,100,20,.1);color:#8A4A00;border:1px solid rgba(180,100,20,.2);}}
.card-time{{font-size:10px;color:var(--text-muted);font-family:var(--font-mono);white-space:nowrap;}}
.card-title{{font-size:15px;font-weight:700;line-height:1.45;margin-bottom:10px;letter-spacing:-.01em;}}
.card-section-label{{font-size:9px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--text-muted);margin-bottom:5px;font-family:var(--font-mono);}}
.card-summary{{font-size:12.5px;color:var(--text-secondary);line-height:1.75;margin-bottom:12px;}}
.implications-box{{background:rgba(20,40,160,.05);border:1px solid rgba(20,40,160,.15);border-left:3px solid var(--samsung-blue);border-radius:0 7px 7px 0;padding:10px 13px;margin-bottom:12px;}}
.implications-text{{font-size:12px;color:#2A3060;line-height:1.75;}}
.impl-tags{{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px;}}
.impl-tag{{font-size:9px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;padding:2px 7px;border-radius:3px;font-family:var(--font-mono);}}
.impl-risk{{background:rgba(192,57,43,.1);color:#A0291D;}}
.impl-opp{{background:rgba(26,122,74,.1);color:#145C38;}}
.impl-watch{{background:rgba(184,134,11,.1);color:#8A6500;}}
.card-footer{{display:flex;justify-content:space-between;align-items:center;}}
.media-name{{font-size:11px;font-weight:600;color:var(--text-secondary);}}
.impact-meter{{display:flex;align-items:center;gap:5px;}}
.impact-label{{font-size:9px;color:var(--text-muted);font-family:var(--font-mono);}}
.impact-bars{{display:flex;gap:2px;}}
.impact-bar{{width:3px;height:12px;border-radius:2px;}}
.impact-bar.filled-high{{background:var(--accent-red);}}.impact-bar.filled-med{{background:var(--accent-gold);}}.impact-bar.filled-low{{background:#D4CEBC;}}
.share-btn{{background:transparent;border:1px solid var(--border);border-radius:5px;padding:4px 9px;font-size:10px;font-weight:600;color:var(--text-muted);cursor:pointer;display:flex;align-items:center;gap:4px;transition:all .2s;font-family:var(--font-body);}}
.share-btn:hover{{border-color:var(--samsung-blue);color:var(--samsung-blue);}}
.share-btn.copied{{border-color:var(--accent-green);color:var(--accent-green);}}

/* EMPTY */
.empty-state{{text-align:center;padding:60px 20px;color:var(--text-muted);font-size:14px;display:none;}}
.empty-state.visible{{display:block;}}

/* TOAST */
.toast{{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(80px);background:var(--accent-green);color:#07090F;font-size:13px;font-weight:700;padding:11px 22px;border-radius:8px;z-index:999;transition:transform .3s cubic-bezier(.34,1.56,.64,1);white-space:nowrap;}}
.toast.show{{transform:translateX(-50%) translateY(0);}}

/* ANIMATIONS */
@keyframes fadeInUp{{from{{opacity:0;transform:translateY(14px);}}to{{opacity:1;transform:translateY(0);}}}}
.animate-in{{animation:fadeInUp .4s ease both;}}
.d1{{animation-delay:.05s;}}.d2{{animation-delay:.1s;}}.d3{{animation-delay:.15s;}}

mark{{background:rgba(20,40,160,.12);color:var(--samsung-blue);border-radius:2px;padding:0 2px;}}
::-webkit-scrollbar{{width:5px;}}::-webkit-scrollbar-track{{background:var(--bg-deep);}}::-webkit-scrollbar-thumb{{background:#C8C0AA;border-radius:3px;}}
</style>
</head>
<body>

<!-- HEADER -->
<header>
  <div class="header-inner">
    <div class="header-left">
      <div class="logo-mark">SEC</div>
      <div>
        <div class="header-title-main">Global Appliance Strategy Briefing</div>
        <div class="header-title-sub">Samsung Electronics · DA Division · Executive Intelligence</div>
      </div>
    </div>
    <div class="header-right">
      <div class="live-badge"><span class="live-dot"></span>LIVE</div>
      <div class="timestamp" id="ts">—</div>
      <a class="refresh-btn" href="https://github.com/konidoni/News-Letter/actions/workflows/daily.yml" target="_blank" rel="noopener">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
        지금 수집
      </a>
    </div>
  </div>
</header>

<!-- DATE TABS -->
<div class="date-tabs-wrap">
  <div class="date-tabs" id="dateTabs"></div>
</div>

<!-- SEARCH -->
<div class="search-container wrapper">
  <div class="search-wrap">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
    <input class="search-input" type="text" id="searchInput" placeholder="키워드 검색 (예: Samsung, LFP, Whirlpool)">
  </div>
  <div class="filter-chips" id="filterChips">
    <button class="chip active" data-cat="ALL">전체</button>
    <button class="chip" data-cat="Samsung DA">삼성 가전</button>
    <button class="chip" data-cat="Competitor Analysis">경쟁사</button>
    <button class="chip" data-cat="Product Reviews">제품 리뷰</button>
    <button class="chip" data-cat="Technology Trend">기술 트렌드</button>
    <button class="chip" data-cat="Macro / Policy">매크로·정책</button>
    <button class="chip" data-cat="Market Dynamics">시장 동향</button>
    <button class="chip" data-cat="Supply Chain">공급망</button>
  </div>
</div>

<!-- MAIN -->
<main class="wrapper">
  <div class="section animate-in d1">
    <div class="stats-bar" id="statsBar"></div>
  </div>
  <div class="section animate-in d2">
    <div class="section-label">Today's Top 3 Key Takeaways</div>
    <div class="takeaways-grid" id="takeawaysGrid"></div>
  </div>
  <div class="section animate-in d3">
    <div class="section-label" id="feedLabel">Intelligence Feed — 24H Window</div>
    <div class="news-grid" id="newsGrid"></div>
    <div class="empty-state" id="emptyState">
      <div style="font-size:32px;margin-bottom:12px;">📭</div>
      <div id="emptyTitle" style="font-size:15px;font-weight:700;color:var(--text-secondary);margin-bottom:8px;">오늘은 관련 뉴스가 없습니다</div>
      <div id="emptyDesc" style="font-size:13px;color:var(--text-muted);line-height:1.7;">가전 업계 주요 뉴스가 발생하면 다음 수집 시 자동으로 업데이트됩니다.<br>매일 오후 4시 KST 자동 수집됩니다.</div>
    </div>
  </div>
</main>

<div class="toast" id="toast">✓ 클립보드에 복사되었습니다</div>

<script>
const ALL_DATA  = {all_data_json};
const DATES     = {dates_json};
const LATEST    = {latest_json};

const catClass = {{"Competitor Analysis":"cat-competitor","Technology Trend":"cat-tech","Macro / Policy":"cat-macro","Market Dynamics":"cat-market","Supply Chain":"cat-supply","Samsung DA":"cat-samsung","Product Reviews":"cat-reviews"}};
const catLabel = {{"Competitor Analysis":"경쟁사 동향","Technology Trend":"기술 트렌드","Macro / Policy":"매크로·정책","Market Dynamics":"시장 동향","Supply Chain":"공급망","Samsung DA":"삼성 가전","Product Reviews":"제품 리뷰"}};

let curDate = LATEST;
let curCat  = 'ALL';
let curQ    = '';

// ── 날짜 탭 렌더 ──────────────────────────────────────────────────────────
function renderTabs() {{
  const today = new Date().toLocaleDateString('ko-KR',{{year:'numeric',month:'2-digit',day:'2-digit'}}).replace(/\. /g,'-').replace('.','');
  const tabs  = document.getElementById('dateTabs');
  tabs.innerHTML = DATES.map((d,i) => {{
    const isToday  = (i === 0);
    const label    = isToday ? '📅 오늘' : d.replace(/^\\d{{4}}-/,'').replace('-','월 ')+'일';
    const active   = d === curDate ? 'active' : '';
    const todayCls = isToday ? 'today-tab' : '';
    return `<button class="date-tab ${{active}} ${{todayCls}}" onclick="switchDate('${{d}}')">${{label}}</button>`;
  }}).join('');
}}

// ── 날짜 전환 ─────────────────────────────────────────────────────────────
function switchDate(date) {{
  curDate = date;
  curCat  = 'ALL';
  curQ    = '';
  document.getElementById('searchInput').value = '';
  document.querySelectorAll('.chip').forEach(c => c.classList.toggle('active', c.dataset.cat === 'ALL'));
  renderTabs();
  renderStats();
  renderTakeaways();
  render();
}}

// ── 현재 날짜 데이터 가져오기 ─────────────────────────────────────────────
function curData() {{
  return ALL_DATA[curDate] || {{}};
}}

// ── 타임스탬프 ───────────────────────────────────────────────────────────
function updateTs() {{
  const d = curData();
  document.getElementById('ts').textContent = d.generated_at_display || '—';
}}

// ── STATS ────────────────────────────────────────────────────────────────
function renderStats() {{
  updateTs();
  const articles = curData().articles || [];
  const cc = curData().category_counts || {{}};
  const highRisk = articles.filter(a => (a.tags||[]).includes('risk') && a.impact >= 4).length;
  const riskLevel = highRisk >= 4 ? 'High' : highRisk >= 2 ? 'Med' : 'Low';
  const riskCls   = highRisk >= 2 ? 'delta-down' : 'delta-up';
  const riskTxt   = highRisk >= 4 ? '↑ 위기 이슈 집중' : highRisk >= 2 ? '→ 주의 필요' : '↓ 안정적';
  document.getElementById('statsBar').innerHTML = `
    <div class="stat-item"><span class="stat-value">${{articles.length}}</span><span class="stat-label">수집 기사 수 (24h)</span></div>
    <div class="stat-item"><span class="stat-value">${{cc['Samsung DA']||0}}</span><span class="stat-label">삼성 가전 뉴스</span><span class="stat-delta delta-up">자사 모니터링</span></div>
    <div class="stat-item"><span class="stat-value">${{cc['Competitor Analysis']||0}}</span><span class="stat-label">경쟁사 동향</span></div>
    <div class="stat-item"><span class="stat-value">${{cc['Product Reviews']||0}}</span><span class="stat-label">제품 리뷰·순위</span></div>
    <div class="stat-item"><span class="stat-value">${{riskLevel}}</span><span class="stat-label">금일 시장 리스크</span><span class="stat-delta ${{riskCls}}">${{riskTxt}}</span></div>`;
}}

// ── TAKEAWAYS ───────────────────────────────────────────────────────────
function renderTakeaways() {{
  const takeaways = curData().takeaways || [];
  const nums = ['01','02','03'];
  document.getElementById('takeawaysGrid').innerHTML = takeaways.map((t,i) => `
    <div class="takeaway-card">
      <span class="takeaway-num">${{nums[i]||''}}</span>
      <div class="takeaway-trend">${{t.trend_label||''}}</div>
      <div class="takeaway-title">${{t.title||''}}</div>
      <div class="takeaway-desc">${{t.desc||''}}</div>
    </div>`).join('') || '<div style="color:var(--text-muted);font-size:13px;padding:20px 0;">데이터 없음</div>';
}}

// ── HELPERS ──────────────────────────────────────────────────────────────
function impactBars(n) {{
  let h=''; for(let i=1;i<=5;i++) h+=`<span class="impact-bar ${{i<=n?(n>=4?'filled-high':'filled-med'):'filled-low'}}"></span>`; return h;
}}
function tagsHtml(tags) {{
  const m={{risk:['impl-risk','🔴 위기'],opp:['impl-opp','🟢 기회'],watch:['impl-watch','🟡 모니터링']}};
  return (tags||[]).filter(t=>m[t]).map(t=>`<span class="impl-tag ${{m[t][0]}}">${{m[t][1]}}</span>`).join('');
}}
function hl(text,q) {{
  if(!q||!text) return text||'';
  return text.replace(new RegExp(`(${{q.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&')}})`, 'gi'),'<mark>$1</mark>');
}}

// ── CARD HTML ─────────────────────────────────────────────────────────────
function cardHtml(item) {{
  const t  = (item.title||'').replace(/`/g,"'");
  const s  = (item.summary_kr||'').replace(/`/g,"'");
  const im = (item.strategic_implications||'').replace(/`/g,"'");
  return `<a class="news-card" href="${{item.url}}" target="_blank" rel="noopener noreferrer">
    <div class="card-header">
      <span class="category-badge ${{catClass[item.category]||'cat-market'}}">${{catLabel[item.category]||item.category}}</span>
      <div style="display:flex;align-items:center;gap:7px;">
        <span class="card-time">${{item.time||''}}</span>
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--text-muted)"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
      </div>
    </div>
    <div class="card-title">${{hl(item.title,curQ)}}</div>
    <div class="card-section-label">What Happened</div>
    <div class="card-summary">${{hl(item.summary_kr,curQ)}}</div>
    <div class="card-section-label">Strategic Implications</div>
    <div class="implications-box">
      <div class="implications-text">${{hl(item.strategic_implications,curQ)}}</div>
      <div class="impl-tags">${{tagsHtml(item.tags)}}</div>
    </div>
    <div class="card-footer">
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="media-name">${{item.media||''}}</span>
        <div class="impact-meter"><span class="impact-label">영향도</span><div class="impact-bars">${{impactBars(item.impact)}}</div></div>
      </div>
      <button class="share-btn" onclick="event.preventDefault();event.stopPropagation();copyCard(this,\`${{t}}\`,\`${{s}}\`,\`${{im}}\`,\`${{item.media}}\`,\`${{item.url}}\`)">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>복사
      </button>
    </div>
  </a>`;
}}

// ── RENDER ───────────────────────────────────────────────────────────────
function render() {{
  const q        = curQ.toLowerCase();
  const articles = curData().articles || [];
  const filtered = articles.filter(a => {{
    const catOk = curCat === 'ALL' || a.category === curCat;
    const txtOk = !q || (a.title+a.summary_kr+a.strategic_implications).toLowerCase().includes(q);
    return catOk && txtOk;
  }});

  const empty = document.getElementById('emptyState');
  const d     = curData();
  document.getElementById('feedLabel').textContent =
    `Intelligence Feed — ${{d.date_display || curDate}}`;

  const allArticles = d.articles || [];
  if (!filtered.length) {{
    document.getElementById('newsGrid').innerHTML = '';
    empty.classList.add('visible');
    // 필터 vs 진짜 없음 구분
    if (allArticles.length === 0) {{
      document.getElementById('emptyTitle').textContent = '해당 날짜에 수집된 뉴스가 없습니다';
      document.getElementById('emptyDesc').textContent = '가전 업계 주요 뉴스가 없었거나 수집에 실패했습니다. 다음 수집 시 자동으로 업데이트됩니다.';
    }} else {{
      document.getElementById('emptyTitle').textContent = '검색 결과가 없습니다';
      document.getElementById('emptyDesc').textContent = '다른 키워드나 카테고리로 시도해보세요.';
    }}
    return;
  }}
  empty.classList.remove('visible');
  document.getElementById('newsGrid').innerHTML = filtered.map(cardHtml).join('');
}}

// ── EVENTS ───────────────────────────────────────────────────────────────
document.getElementById('filterChips').addEventListener('click', e => {{
  const chip = e.target.closest('.chip'); if(!chip) return;
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  chip.classList.add('active'); curCat = chip.dataset.cat; render();
}});
document.getElementById('searchInput').addEventListener('input', e => {{
  curQ = e.target.value.trim(); render();
}});

function copyCard(btn,title,summary,impl,media,url) {{
  const text = `📋 [Samsung DA 전략 브리핑]\\n\\n■ ${{title}}\\n\\n▶ 현황\\n${{summary}}\\n\\n▶ 전략적 비고\\n${{impl}}\\n\\n출처: ${{media}}\\n🔗 ${{url}}\\n\\n— Samsung Electronics DA Division · ${{new Date().toLocaleDateString('ko-KR')}}`;
  navigator.clipboard.writeText(text).then(() => {{
    btn.classList.add('copied'); btn.textContent='✓ 복사됨';
    const t = document.getElementById('toast'); t.classList.add('show');
    setTimeout(() => {{
      t.classList.remove('show'); btn.classList.remove('copied');
      btn.innerHTML='<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>복사';
    }}, 2000);
  }});
}}

// ── INIT ─────────────────────────────────────────────────────────────────
renderTabs();
renderStats();
renderTakeaways();
render();
</script>
</body>
</html>"""


def main():
    manifest  = load_manifest()
    dates     = manifest.get("dates", [])

    # 모든 날짜 데이터 로드
    days_data = {}
    for d in dates:
        data = load_day(d)
        if data:
            days_data[d] = data

    if not days_data:
        print("[WARN] No data files found in data/. Run fetch_news.py first.")
        # 빈 페이지라도 생성
        days_data = {}

    html = build_html(manifest, days_data)
    Path(OUTPUT_FILE).write_text(html, encoding="utf-8")
    print(f"✅ Dashboard built → {{OUTPUT_FILE}}")
    print(f"   날짜 탭: {{len(days_data)}}일치 아카이브")
    print(f"   최신: {{manifest.get('latest')}}")


if __name__ == "__main__":
    main()
