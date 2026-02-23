"""
Pharma MCP/GEO Intelligence Engine
"""

import streamlit as st
import requests
import json
import re
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import io
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Optional
import time

# ============================================================================
# PAGE CONFIG — must be first Streamlit call
# ============================================================================

st.set_page_config(
    page_title="XO Pharma MCP/GEO v7",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================================
# THEME & GLOBAL CSS
# ============================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Reset & Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background: #04080f;
    color: #e8edf5;
}

.main .block-container { padding: 1.5rem 2.5rem 4rem; max-width: 1400px; }

/* ── Hero Header ── */
.hero {
    background: linear-gradient(135deg, #050d1a 0%, #0a1929 60%, #061224 100%);
    border: 1px solid rgba(56, 189, 248, 0.15);
    border-radius: 20px;
    padding: 2.8rem 3rem 2.2rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(56,189,248,0.08) 0%, transparent 70%);
    pointer-events: none;
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.6rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(90deg, #e0f2fe, #38bdf8, #7dd3fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 0.4rem;
}
.hero-sub {
    font-size: 0.95rem;
    color: #64748b;
    font-family: 'DM Mono', monospace;
    letter-spacing: 0.04em;
    margin: 0;
}
.hero-badges {
    margin-top: 1.2rem;
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
}
.badge {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    padding: 0.25rem 0.7rem;
    border-radius: 20px;
    border: 1px solid rgba(56,189,248,0.3);
    color: #38bdf8;
    background: rgba(56,189,248,0.06);
    letter-spacing: 0.06em;
}

/* ── Card ── */
.card {
    background: #080f1c;
    border: 1px solid #1e2d42;
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
}
.card-header {
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: #cbd5e1;
    margin-bottom: 0.8rem;
    letter-spacing: 0.02em;
}

/* ── Score Ring Pill ── */
.score-pill {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 1.5rem;
    font-weight: 500;
    padding: 0.2rem 0.9rem;
    border-radius: 10px;
}
.score-high  { background: rgba(34,197,94,0.12); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); }
.score-mid   { background: rgba(251,191,36,0.12); color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); }
.score-low   { background: rgba(239,68,68,0.12);  color: #f87171; border: 1px solid rgba(239,68,68,0.3); }

/* ── Expander override ── */
details { border: 1px solid #1e2d42 !important; border-radius: 12px !important; background: #080f1c !important; margin-bottom: 0.6rem !important; }
summary { font-family: 'DM Sans', sans-serif !important; padding: 0.8rem 1rem !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { gap: 0.3rem; background: transparent; border-bottom: 1px solid #1e2d42; }
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.05em;
    background: transparent;
    border: none;
    color: #475569;
    padding: 0.6rem 1.2rem;
}
.stTabs [aria-selected="true"] {
    color: #38bdf8 !important;
    border-bottom: 2px solid #38bdf8 !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #0ea5e9, #2563eb);
    border: none;
    border-radius: 10px;
    color: white;
    font-family: 'DM Mono', monospace;
    font-size: 0.85rem;
    letter-spacing: 0.04em;
    padding: 0.6rem 1.4rem;
    transition: opacity 0.15s;
}
.stButton > button:hover { opacity: 0.85; }

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: #080f1c;
    border: 1px solid #1e2d42;
    border-radius: 10px;
    padding: 0.8rem 1rem;
}
[data-testid="stMetricLabel"] { font-family: 'DM Mono', monospace; font-size: 0.72rem; color: #475569; }
[data-testid="stMetricValue"] { font-family: 'Syne', sans-serif; font-size: 1.4rem; color: #e2e8f0; }

/* ── Progress bar ── */
.stProgress > div > div { background: linear-gradient(90deg, #0ea5e9, #38bdf8); border-radius: 4px; }

/* ── Fix tags ── */
.fix-tag {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    background: rgba(251,191,36,0.1);
    border: 1px solid rgba(251,191,36,0.25);
    color: #fbbf24;
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    margin: 0.15rem 0.1rem;
}
.fix-tag.good {
    background: rgba(34,197,94,0.1);
    border-color: rgba(34,197,94,0.25);
    color: #4ade80;
}

/* ── Divider ── */
hr { border-color: #1e2d42 !important; }

/* ── DataFrame ── */
.stDataFrame { border: 1px solid #1e2d42 !important; border-radius: 10px !important; }

/* ── Input ── */
.stTextInput > div > div, .stTextArea > div > div {
    background: #080f1c !important;
    border-color: #1e2d42 !important;
    color: #e2e8f0 !important;
    border-radius: 10px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.85rem !important;
}

/* ── Code block ── */
.stCodeBlock { border-radius: 10px !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background: #050d1a; border-right: 1px solid #1e2d42; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONSTANTS & CONFIG
# ============================================================================

REQUEST_TIMEOUT = 12
MAX_WORKERS = 6

PHARMA_BENCHMARKS = {
    "Diabetes":  {"Lilly": 92, "Novo Nordisk": 87, "Merck": 71},
    "Oncology":  {"Roche": 89, "BMS": 85, "Pfizer": 68},
    "Cardio":    {"AstraZeneca": 83, "Sanofi": 79, "GSK": 65},
}

SCORE_WEIGHTS = {
    "schema":    25,
    "authority": 30,
    "tech":      12,
    "geo":       18,
    "mcp":       15,
}

DEFAULT_DOMAINS = """https://www.lilly.com
https://www.pfizer.com
https://www.merck.com
https://www.novonordisk.com
https://www.astrazeneca.com"""

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class MCPStatus:
    agent_ready: bool = False
    mcp_manifests: int = 0
    functions: int = 0

@dataclass
class PharmaSignals:
    medical_review: bool = False
    prescribing_info: bool = False
    med_guide: bool = False
    adverse_events: bool = False
    pubmed: bool = False
    doi_citations: bool = False
    references: bool = False
    faq_schema: bool = False

    def count(self) -> int:
        return sum(asdict(self).values())

@dataclass
class ScoreBreakdown:
    total: float = 0.0
    schema: float = 0.0
    authority: float = 0.0
    tech: float = 0.0
    geo: float = 0.0
    mcp: float = 0.0

@dataclass
class ScanResult:
    url: str
    domain: str
    score: ScoreBreakdown
    schemas: list = field(default_factory=list)
    signals: PharmaSignals = field(default_factory=PharmaSignals)
    mcp: MCPStatus = field(default_factory=MCPStatus)
    status_code: int = 0
    improvements: list = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def priority(self) -> str:
        if self.score.total < 60:
            return "CRITICAL"
        if self.score.total < 78:
            return "HIGH"
        return "GOOD"

    @property
    def score_class(self) -> str:
        if self.score.total >= 80:
            return "score-high"
        if self.score.total >= 60:
            return "score-mid"
        return "score-low"

# ============================================================================
# CORE ANALYSIS FUNCTIONS
# ============================================================================

def fetch_html(url: str) -> tuple[Optional[str], int]:
    """Fetch page HTML with a pharma user-agent. Returns (html, status_code)."""
    headers = {
        "User-Agent": "PharmaMCP/7.0 (GEO-Intelligence; +https://xodigital.com/bot)",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        return r.text, r.status_code
    except requests.exceptions.Timeout:
        return None, -1
    except requests.exceptions.ConnectionError:
        return None, -2
    except Exception:
        return None, -3


def extract_schemas(html: str) -> list[str]:
    """Return unique @type values from JSON-LD blocks."""
    soup = BeautifulSoup(html, "html.parser")
    types: set[str] = set()

    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "{}")
        except json.JSONDecodeError:
            continue

        def _recurse(obj):
            if isinstance(obj, dict):
                t = obj.get("@type")
                if t:
                    types.add(t if isinstance(t, str) else t[0])
                for v in obj.values():
                    _recurse(v)
            elif isinstance(obj, list):
                for item in obj:
                    _recurse(item)

        _recurse(data)

    return list(types)


def detect_signals(html: str) -> PharmaSignals:
    """Pharma E-E-A-T + GEO content signals."""
    text = html.lower()
    return PharmaSignals(
        medical_review=bool(re.search(r"reviewed by|medically reviewed", text)),
        prescribing_info="prescribing information" in text,
        med_guide="medication guide" in text,
        adverse_events=bool(re.search(r"adverse.{0,15}event", text)),
        pubmed="pubmed" in text,
        doi_citations=bool(re.search(r"\b10\.\d{4,9}/", text)),
        references=bool(re.search(r"\breferences?\b|\bsources?\b", text)),
        faq_schema=bool(re.search(r"\bfaq\b|frequently asked", text)),
    )


def detect_mcp(html: str) -> MCPStatus:
    """Model Context Protocol readiness signals."""
    soup = BeautifulSoup(html, "html.parser")
    return MCPStatus(
        agent_ready="navigator.modelContext" in html,
        mcp_manifests=len(soup.find_all("script", {"type": "application/mcp+json"})),
        functions=len(re.findall(r"\b(get_|find_|check_|book_|schedule_)\w+", html, re.I)),
    )


def compute_score(
    schemas: list[str],
    signals: PharmaSignals,
    status_code: int,
    mcp: MCPStatus,
) -> ScoreBreakdown:
    """Weighted scoring across five pillars (max 100)."""
    w = SCORE_WEIGHTS

    schema_score    = min(len(schemas) * 3.5, w["schema"])
    authority_score = min(signals.count() * 4.5, w["authority"])
    tech_score      = w["tech"] if status_code == 200 else max(0, w["tech"] - 6)
    geo_score       = min(len(schemas) * 2 + signals.faq_schema + signals.pubmed, w["geo"])
    mcp_score       = (
        w["mcp"]
        if mcp.agent_ready
        else min(mcp.functions * 2.5 + mcp.mcp_manifests * 3, w["mcp"] - 3)
    )

    total = min(schema_score + authority_score + tech_score + geo_score + mcp_score, 100)
    return ScoreBreakdown(
        total=round(total, 1),
        schema=round(schema_score, 1),
        authority=round(authority_score, 1),
        tech=round(tech_score, 1),
        geo=round(geo_score, 1),
        mcp=round(mcp_score, 1),
    )


def build_improvements(signals: PharmaSignals, schemas: list[str]) -> list[dict]:
    """Return prioritised fix list with point estimates."""
    fixes = []
    if not signals.faq_schema:
        fixes.append({"label": "FAQPage schema markup", "pts": 14, "type": "schema"})
    if not signals.pubmed:
        fixes.append({"label": "PubMed / DOI citations", "pts": 9, "type": "authority"})
    if signals.count() < 4:
        fixes.append({"label": "E-E-A-T trust signals", "pts": 12, "type": "authority"})
    if len(schemas) < 3:
        fixes.append({"label": "MedicalEntity schemas", "pts": 11, "type": "schema"})
    if not signals.medical_review:
        fixes.append({"label": "Medical review by-line", "pts": 8, "type": "authority"})
    return fixes[:4]


def scan_domain(url: str) -> ScanResult:
    """Full scan pipeline for a single domain."""
    # Normalise URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    domain = urlparse(url).netloc

    html, status_code = fetch_html(url)

    if html is None:
        error_map = {-1: "Timeout", -2: "Connection refused", -3: "Unknown error"}
        return ScanResult(
            url=url,
            domain=domain,
            score=ScoreBreakdown(),
            error=error_map.get(status_code, "Fetch failed"),
        )

    schemas    = extract_schemas(html)[:8]
    signals    = detect_signals(html)
    mcp_status = detect_mcp(html)
    score      = compute_score(schemas, signals, status_code, mcp_status)
    fixes      = build_improvements(signals, schemas)

    return ScanResult(
        url=url,
        domain=domain,
        score=score,
        schemas=schemas,
        signals=signals,
        mcp=mcp_status,
        status_code=status_code,
        improvements=fixes,
    )


def parallel_scan(urls: list[str]) -> list[ScanResult]:
    """Concurrent domain scanning with progress reporting."""
    results: list[ScanResult] = [None] * len(urls)
    progress = st.progress(0, text="Initialising scan…")
    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_index = {executor.submit(scan_domain, url): i for i, url in enumerate(urls)}
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                results[idx] = ScanResult(
                    url=urls[idx],
                    domain=urlparse(urls[idx]).netloc,
                    score=ScoreBreakdown(),
                    error=str(exc),
                )
            completed += 1
            progress.progress(completed / len(urls), text=f"Scanning… {completed}/{len(urls)} done")

    progress.empty()
    return results

# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_hero():
    st.markdown("""
    <div class="hero">
        <div class="hero-title">🔬 Pharma MCP/GEO Intelligence</div>
        <p class="hero-sub">XO DIGITAL · AI-FIRST PLATFORM · v7 ENTERPRISE</p>
        <div class="hero-badges">
            <span class="badge">⚡ PARALLEL SCAN</span>
            <span class="badge">🤖 MCP DETECTION</span>
            <span class="badge">📊 GEO SCORING</span>
            <span class="badge">🏆 BENCHMARKS</span>
            <span class="badge">📁 EXPORT</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_score_breakdown(score: ScoreBreakdown):
    """Compact five-pillar metric grid."""
    cols = st.columns(6)
    pillars = [
        ("Schema",    score.schema,    SCORE_WEIGHTS["schema"]),
        ("Authority", score.authority, SCORE_WEIGHTS["authority"]),
        ("Tech",      score.tech,      SCORE_WEIGHTS["tech"]),
        ("GEO",       score.geo,       SCORE_WEIGHTS["geo"]),
        ("MCP",       score.mcp,       SCORE_WEIGHTS["mcp"]),
    ]
    for col, (label, val, max_val) in zip(cols, pillars):
        pct = int((val / max_val) * 100)
        delta_str = f"{pct}% of max"
        col.metric(label, f"{val:.0f}/{max_val}", delta_str)

    with cols[5]:
        score_cls = (
            "score-high" if score.total >= 80 else
            "score-mid"  if score.total >= 60 else
            "score-low"
        )
        st.markdown(
            f"<div style='padding-top:0.5rem; text-align:center;'>"
            f"<div style='font-family:DM Mono,monospace;font-size:0.7rem;color:#475569;margin-bottom:0.3rem;'>TOTAL</div>"
            f"<span class='score-pill {score_cls}'>{score.total:.0f}/100</span></div>",
            unsafe_allow_html=True,
        )


def render_result_card(result: ScanResult):
    """Expander card for a single scan result."""
    score_cls = result.score_class
    priority_icon = {"CRITICAL": "🔴", "HIGH": "🟡", "GOOD": "🟢"}[result.priority]
    fix_pts = sum(f["pts"] for f in result.improvements)

    with st.expander(
        f"{priority_icon} **{result.domain}** — "
        f"{result.score.total:.0f}/100 · {result.priority} · "
        f"+{fix_pts}pts opportunity"
    ):
        render_score_breakdown(result.score)

        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Agent Ready", "✅ YES" if result.mcp.agent_ready else "❌ NO")
        col2.metric("MCP Functions", result.mcp.functions)
        col3.metric("Schemas Found", len(result.schemas))
        col4.metric("HTTP Status", result.status_code)

        if result.schemas:
            st.markdown(
                "**Detected schemas:** " +
                " ".join(f"`{s}`" for s in result.schemas[:6])
            )

        if result.improvements:
            st.markdown("**Priority fixes:**")
            tags_html = ""
            for fix in result.improvements:
                tags_html += f'<span class="fix-tag">+{fix["pts"]}pts · {fix["label"]}</span>'
            st.markdown(tags_html, unsafe_allow_html=True)
        else:
            st.markdown('<span class="fix-tag good">✅ No critical gaps found</span>', unsafe_allow_html=True)


def results_to_dataframe(results: list[ScanResult]) -> pd.DataFrame:
    rows = []
    for r in results:
        if not r.ok:
            continue
        rows.append({
            "Domain": r.domain,
            "Score": r.score.total,
            "Schema": r.score.schema,
            "Authority": r.score.authority,
            "Tech": r.score.tech,
            "GEO": r.score.geo,
            "MCP": r.score.mcp,
            "Agent Ready": r.mcp.agent_ready,
            "MCP Functions": r.mcp.functions,
            "Schemas Found": len(r.schemas),
            "Priority": r.priority,
            "Fix Potential (pts)": sum(f["pts"] for f in r.improvements),
            "Timestamp": r.timestamp,
        })
    return pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)


def export_csv(df: pd.DataFrame, client: str) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode()

# ============================================================================
# SESSION STATE HELPERS
# ============================================================================

def init_state():
    if "scan_results" not in st.session_state:
        st.session_state.scan_results = []
    if "history" not in st.session_state:
        st.session_state.history = []

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    init_state()
    render_hero()

    # ── Global client name ──
    client_name = st.text_input(
        "👤 Client / Brand",
        value="Pharma Brand",
        help="Used in export filenames and executive reports.",
        key="client_name",
    )

    # ── Tab workspace ──
    tab_scan, tab_agent, tab_bench, tab_exec = st.tabs([
        "🚀  Turbo Scanner",
        "🤖  Agent Tester",
        "🏆  Benchmarks",
        "📊  Executive",
    ])

    # ══════════════════════════════════════════════════════════
    # TAB 1 — TURBO SCANNER
    # ══════════════════════════════════════════════════════════
    with tab_scan:
        st.markdown("#### Scan up to 20 competitor domains in parallel")

        col_input, col_btn = st.columns([4, 1])
        with col_input:
            raw_input = st.text_area(
                "Domains (one per line)",
                value=DEFAULT_DOMAINS,
                height=160,
                label_visibility="collapsed",
            )
        with col_btn:
            st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
            run_scan = st.button("🚀 SCAN NOW", type="primary", use_container_width=True)
            clear = st.button("🗑 Clear", use_container_width=True)

        if clear:
            st.session_state.scan_results = []
            st.rerun()

        if run_scan:
            urls = [u.strip() for u in raw_input.splitlines() if u.strip()]
            if not urls:
                st.warning("No URLs provided.")
            elif len(urls) > 20:
                st.error("Maximum 20 domains per scan. Please trim the list.")
            else:
                t0 = time.time()
                with st.spinner(f"Scanning {len(urls)} domain(s) in parallel…"):
                    results = parallel_scan(urls)

                st.session_state.scan_results = results
                # Persist OK results to history (dedup by domain)
                existing_domains = {r.domain for r in st.session_state.history}
                for r in results:
                    if r.ok and r.domain not in existing_domains:
                        st.session_state.history.append(r)

                elapsed = time.time() - t0
                ok_count = sum(1 for r in results if r.ok)
                st.success(f"✅ {ok_count}/{len(urls)} domains analysed in **{elapsed:.1f}s**")

        if st.session_state.scan_results:
            st.markdown("---")
            # Sort: errors last, then by score descending
            sorted_results = sorted(
                st.session_state.scan_results,
                key=lambda r: (not r.ok, -r.score.total),
            )
            for result in sorted_results:
                if result.ok:
                    render_result_card(result)
                else:
                    status_map = {-1: "Timeout", -2: "Connection refused", -3: "Unknown error"}
                    st.error(f"❌ **{result.domain}** — {result.error}")

    # ══════════════════════════════════════════════════════════
    # TAB 2 — AGENT TESTER
    # ══════════════════════════════════════════════════════════
    with tab_agent:
        st.markdown("#### Test a single domain for AI-agent readiness")

        test_url = st.text_input("Domain URL", value="https://www.lilly.com", key="agent_url")

        if st.button("🧪 RUN AGENT TEST", type="primary"):
            with st.spinner("Running agent compatibility test…"):
                result = scan_domain(test_url)

            if not result.ok:
                st.error(f"Scan failed: {result.error}")
            else:
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.markdown("##### MCP Readiness")
                    st.metric("Agent Ready", "✅ YES" if result.mcp.agent_ready else "❌ NO")
                    st.metric("MCP Manifests", result.mcp.mcp_manifests)
                    st.metric("Callable Functions", result.mcp.functions)
                    st.metric("GEO Score", f"{result.score.total:.0f}/100")

                with col2:
                    st.markdown("##### Raw Agent Payload")
                    st.code(json.dumps({
                        "domain": result.domain,
                        "mcp_agent_ready": result.mcp.agent_ready,
                        "available_functions": result.mcp.functions,
                        "detected_schemas": result.schemas,
                        "score": f"{result.score.total:.1f}/100",
                        "recommended_endpoints": [
                            "get_prescribing_info(drug_id)",
                            "find_clinical_trials(condition, phase)",
                            "check_insurance_coverage(ndc_code, plan_id)",
                            "schedule_hcp_call(rep_id, specialty)",
                        ],
                        "e_e_a_t_signals": asdict(result.signals),
                        "timestamp": result.timestamp,
                    }, indent=2), language="json")

    # ══════════════════════════════════════════════════════════
    # TAB 3 — BENCHMARKS
    # ══════════════════════════════════════════════════════════
    with tab_bench:
        st.markdown("#### Pharma industry MCP/GEO benchmark scores")

        bm_rows = [
            {"Category": cat, "Company": co, "Score": sc}
            for cat, companies in PHARMA_BENCHMARKS.items()
            for co, sc in companies.items()
        ]
        bm_df = pd.DataFrame(bm_rows)
        pivot  = bm_df.pivot(index="Category", columns="Company", values="Score")

        st.dataframe(
            pivot.style.background_gradient(cmap="Blues", axis=None),
            use_container_width=True,
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Industry Average", f"{bm_df['Score'].mean():.1f}")
        col2.metric("Category Leader",  f"Lilly — 92")
        col3.metric("Lowest Benchmark", f"{bm_df['Score'].min()} ({bm_df.loc[bm_df['Score'].idxmin(), 'Company']})")

        # Contextual positioning if we have live data
        ok_results = [r for r in st.session_state.scan_results if r.ok]
        if ok_results:
            st.markdown("---")
            st.markdown("##### Your Scanned Domains vs. Benchmarks")
            live_avg = np.mean([r.score.total for r in ok_results])
            delta    = live_avg - bm_df["Score"].mean()
            st.metric(
                "Your portfolio avg",
                f"{live_avg:.1f}",
                delta=f"{delta:+.1f} vs industry avg",
            )

    # ══════════════════════════════════════════════════════════
    # TAB 4 — EXECUTIVE DASHBOARD
    # ══════════════════════════════════════════════════════════
    with tab_exec:
        st.markdown("#### Executive intelligence across all scanned domains")

        all_results = st.session_state.history
        if not all_results:
            st.info("👈 Run a Turbo Scan first to unlock the executive dashboard.")
        else:
            df = results_to_dataframe(all_results)

            # KPI bar
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Domains Analysed",  len(df))
            col2.metric("Avg GEO Score",     f"{df['Score'].mean():.1f}")
            col3.metric("Agent-Ready",        f"{df['Agent Ready'].sum()}/{len(df)}")
            col4.metric("Critical Priority",  len(df[df["Priority"] == "CRITICAL"]))
            col5.metric("Total Fix Potential", f"+{df['Fix Potential (pts)'].sum()}pts")

            # Leaderboard
            st.markdown("---")
            st.markdown("##### Competitive Leaderboard")

            display_df = df[["Domain", "Score", "Priority", "Agent Ready",
                             "MCP Functions", "Schemas Found", "Fix Potential (pts)"]].copy()
            display_df["Score"] = display_df["Score"].apply(lambda x: f"{x:.1f}")

            st.dataframe(
                display_df.style.applymap(
                    lambda v: "color: #f87171" if v == "CRITICAL"
                    else "color: #fbbf24" if v == "HIGH"
                    else "color: #4ade80",
                    subset=["Priority"],
                ),
                use_container_width=True,
                height=360,
            )

            # Export
            st.markdown("---")
            csv_data = export_csv(df, client_name)
            st.download_button(
                label=f"📥 Download Executive Report — {client_name}",
                data=csv_data,
                file_name=f"XO-Pharma-MCP-{client_name.replace(' ','_')}-{datetime.now().strftime('%Y%m%d-%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("## 🔧 Quick Stats")
        ok = [r for r in st.session_state.history if r.ok]
        if ok:
            st.metric("Domains in history", len(ok))
            st.metric("Avg Score", f"{np.mean([r.score.total for r in ok]):.1f}")
            agent_ready = sum(1 for r in ok if r.mcp.agent_ready)
            st.metric("Agent Ready", f"{agent_ready}/{len(ok)}")
        else:
            st.info("No scans yet.")

        st.markdown("---")
        if st.button("🗑 Clear All History"):
            st.session_state.history = []
            st.session_state.scan_results = []
            st.rerun()


if __name__ == "__main__":
    main()
