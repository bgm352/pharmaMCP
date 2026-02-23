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
from urllib.parse import urlparse, urljoin
import io
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Optional
import time
import hashlib

# PDF export
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="XO Pharma · MCP/GEO Intelligence",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================================
# GLOBAL CSS
# ============================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg:          #0b0e17;
    --surface:     #111520;
    --surface2:    #181d2e;
    --border:      #232b40;
    --border-lite: #1b2235;
    --text:        #f0f4ff;
    --text-muted:  #6b7a99;
    --cyan:        #22d3ee;
    --cyan-dim:    rgba(34,211,238,0.12);
    --cyan-border: rgba(34,211,238,0.25);
    --green:       #34d399;
    --green-dim:   rgba(52,211,153,0.12);
    --green-border:rgba(52,211,153,0.25);
    --amber:       #fbbf24;
    --amber-dim:   rgba(251,191,36,0.12);
    --amber-border:rgba(251,191,36,0.25);
    --red:         #f87171;
    --red-dim:     rgba(248,113,113,0.12);
    --red-border:  rgba(248,113,113,0.25);
    --blue:        #60a5fa;
    --purple:      #a78bfa;
    --radius-sm:   8px;
    --radius:      12px;
    --radius-lg:   18px;
}

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif !important;
    background: var(--bg) !important;
    color: var(--text) !important;
}
.main .block-container { padding: 0 2.5rem 5rem !important; max-width: 1400px !important; }

/* ── Hero ── */
.hero {
    background: linear-gradient(160deg, #0d1525 0%, #111a30 50%, #0b1220 100%);
    border: 1px solid var(--border);
    border-top: 3px solid var(--cyan);
    border-radius: 0 0 var(--radius-lg) var(--radius-lg);
    padding: 2.2rem 3rem 1.8rem;
    margin: 0 0 1.8rem;
    position: relative; overflow: hidden;
}
.hero::after {
    content: ''; position: absolute; inset: 0;
    background: radial-gradient(ellipse at 90% 0%, rgba(34,211,238,0.06) 0%, transparent 60%),
                radial-gradient(ellipse at 10% 100%, rgba(96,165,250,0.04) 0%, transparent 50%);
    pointer-events: none;
}
.hero-eyebrow { font-family:'JetBrains Mono',monospace; font-size:0.7rem; letter-spacing:0.14em; color:var(--cyan); text-transform:uppercase; margin-bottom:0.5rem; }
.hero-title   { font-size:2.3rem; font-weight:800; letter-spacing:-0.03em; color:var(--text); margin:0 0 0.3rem; line-height:1.1; }
.hero-title span { color:var(--cyan); }
.hero-desc    { font-size:0.95rem; color:var(--text-muted); margin:0 0 1.2rem; }
.badge-row    { display:flex; gap:0.5rem; flex-wrap:wrap; }
.badge        { font-family:'JetBrains Mono',monospace; font-size:0.65rem; letter-spacing:0.08em; text-transform:uppercase; padding:0.2rem 0.75rem; border-radius:20px; border:1px solid var(--border); color:var(--text-muted); background:var(--surface); }
.badge.active { border-color:var(--cyan-border); color:var(--cyan); background:var(--cyan-dim); }

/* ── Labels ── */
.section-label { font-family:'JetBrains Mono',monospace; font-size:0.68rem; letter-spacing:0.12em; text-transform:uppercase; color:var(--text-muted); margin:0 0 1rem; padding-bottom:0.5rem; border-bottom:1px solid var(--border-lite); }

/* ── Pillars ── */
.pillar { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:0.85rem 1rem; }
.pillar-label { font-family:'JetBrains Mono',monospace; font-size:0.62rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--text-muted); margin-bottom:0.5rem; }
.pillar-score { font-size:1.6rem; font-weight:800; line-height:1; margin-bottom:0.4rem; }
.pillar-max   { font-size:0.8rem; font-weight:400; color:var(--text-muted); }
.bar-track    { width:100%; height:5px; background:var(--border); border-radius:3px; margin-bottom:0.25rem; overflow:hidden; }
.bar-fill     { height:100%; border-radius:3px; }
.bar-cyan   { background:linear-gradient(90deg,#0891b2,var(--cyan)); }
.bar-blue   { background:linear-gradient(90deg,#1d4ed8,var(--blue)); }
.bar-purple { background:linear-gradient(90deg,#7c3aed,var(--purple)); }
.bar-green  { background:linear-gradient(90deg,#059669,var(--green)); }
.bar-amber  { background:linear-gradient(90deg,#b45309,var(--amber)); }
.pillar-pct { font-family:'JetBrains Mono',monospace; font-size:0.6rem; color:var(--text-muted); }

/* ── Tags ── */
.result-tags { display:flex; gap:0.4rem; flex-wrap:wrap; margin-top:0.4rem; }
.rtag { font-family:'JetBrains Mono',monospace; font-size:0.6rem; font-weight:500; letter-spacing:0.06em; text-transform:uppercase; padding:0.15rem 0.55rem; border-radius:4px; }
.rtag-critical { background:var(--red-dim);   color:var(--red);   border:1px solid var(--red-border); }
.rtag-high     { background:var(--amber-dim); color:var(--amber); border:1px solid var(--amber-border); }
.rtag-good     { background:var(--green-dim); color:var(--green); border:1px solid var(--green-border); }
.rtag-mcp      { background:var(--cyan-dim);  color:var(--cyan);  border:1px solid var(--cyan-border); }
.rtag-neutral  { background:var(--surface2);  color:var(--text-muted); border:1px solid var(--border); }
.rtag-cached   { background:rgba(167,139,250,0.1); color:var(--purple); border:1px solid rgba(167,139,250,0.25); }

/* ── Signals ── */
.signal-grid { display:grid; grid-template-columns:1fr 1fr; gap:0.35rem; }
.signal-item { display:flex; align-items:center; gap:0.4rem; font-size:0.78rem; color:var(--text-muted); }
.signal-dot  { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.dot-on      { background:var(--green); box-shadow:0 0 6px var(--green); }
.dot-off     { background:var(--border); }
.signal-on   { color:var(--text); }

/* ── Fixes ── */
.fix-list { display:flex; flex-direction:column; gap:0.4rem; }
.fix-item { display:flex; align-items:center; justify-content:space-between; background:var(--amber-dim); border:1px solid var(--amber-border); border-radius:var(--radius-sm); padding:0.45rem 0.75rem; font-size:0.8rem; color:var(--amber); }
.fix-pts  { font-family:'JetBrains Mono',monospace; font-size:0.72rem; font-weight:600; background:rgba(251,191,36,0.18); padding:0.1rem 0.4rem; border-radius:4px; }
.all-good { background:var(--green-dim); border:1px solid var(--green-border); border-radius:var(--radius-sm); padding:0.6rem 0.75rem; font-size:0.82rem; color:var(--green); }

/* ── AI Recs ── */
.ai-rec-box { background:linear-gradient(135deg,rgba(34,211,238,0.05),rgba(96,165,250,0.05)); border:1px solid var(--cyan-border); border-radius:var(--radius); padding:1rem 1.2rem; margin-top:0.5rem; }
.ai-rec-header { font-family:'JetBrains Mono',monospace; font-size:0.65rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--cyan); margin-bottom:0.6rem; display:flex; align-items:center; gap:0.4rem; }
.ai-rec-body { font-size:0.85rem; color:var(--text); line-height:1.7; white-space:pre-wrap; }

/* ── Schema chips ── */
.schema-chips { display:flex; flex-wrap:wrap; gap:0.3rem; margin-top:0.4rem; }
.schema-chip  { font-family:'JetBrains Mono',monospace; font-size:0.62rem; background:var(--surface2); border:1px solid var(--border); color:var(--blue); padding:0.15rem 0.5rem; border-radius:4px; }

/* ── Score ring ── */
.score-ring { display:inline-flex; flex-direction:column; align-items:center; justify-content:center; width:68px; height:68px; border-radius:50%; font-weight:800; font-size:1.3rem; line-height:1; border:3px solid; flex-shrink:0; margin-right:0.5rem; }
.ring-sub   { font-size:0.5rem; font-family:'JetBrains Mono',monospace; font-weight:400; letter-spacing:0.05em; margin-top:2px; opacity:0.65; }
.ring-green { color:var(--green); border-color:var(--green); background:var(--green-dim); }
.ring-amber { color:var(--amber); border-color:var(--amber); background:var(--amber-dim); }
.ring-red   { color:var(--red);   border-color:var(--red);   background:var(--red-dim); }

/* ── KPI Cards ── */
.kpi-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:0.75rem; margin-bottom:1.5rem; }
.kpi-card  { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:1.1rem 1.2rem; }
.kpi-label { font-family:'JetBrains Mono',monospace; font-size:0.62rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--text-muted); margin-bottom:0.5rem; }
.kpi-value { font-size:2rem; font-weight:800; line-height:1; color:var(--text); }
.kpi-sub   { font-size:0.72rem; color:var(--text-muted); margin-top:0.25rem; }
.kpi-up    { color:var(--green) !important; }
.kpi-down  { color:var(--red) !important; }

/* ── Compare ── */
.compare-header { display:grid; gap:0.75rem; margin-bottom:1rem; }
.compare-domain-label { font-size:0.85rem; font-weight:700; color:var(--text); padding:0.6rem 0.9rem; background:var(--surface2); border:1px solid var(--border); border-radius:var(--radius-sm); text-align:center; }
.compare-row { display:grid; gap:0.75rem; margin-bottom:0.4rem; align-items:center; }
.compare-label { font-family:'JetBrains Mono',monospace; font-size:0.68rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.08em; padding-right:0.5rem; }
.compare-cell  { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-sm); padding:0.6rem 0.9rem; font-size:0.88rem; font-weight:600; text-align:center; }
.compare-winner { border-color:var(--cyan-border); color:var(--cyan); }
.compare-loser  { color:var(--text-muted); }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background:transparent !important; border-bottom:1px solid var(--border) !important; gap:0 !important; padding:0 !important; }
.stTabs [data-baseweb="tab"] { font-family:'Outfit',sans-serif !important; font-size:0.88rem !important; font-weight:500 !important; color:var(--text-muted) !important; background:transparent !important; border:none !important; border-bottom:2px solid transparent !important; padding:0.75rem 1.4rem !important; transition:color 0.15s !important; }
.stTabs [data-baseweb="tab"]:hover { color:var(--text) !important; }
.stTabs [aria-selected="true"] { color:var(--cyan) !important; border-bottom-color:var(--cyan) !important; }
.stTabs [data-baseweb="tab-panel"] { padding:1.5rem 0 0 !important; }

/* ── Buttons ── */
.stButton > button { font-family:'Outfit',sans-serif !important; font-weight:600 !important; font-size:0.88rem !important; border-radius:var(--radius-sm) !important; border:none !important; background:linear-gradient(135deg,#0284c7,#1d4ed8) !important; color:#fff !important; padding:0.6rem 1.4rem !important; transition:all 0.15s !important; box-shadow:0 4px 12px rgba(2,132,199,0.25) !important; }
.stButton > button:hover { transform:translateY(-1px) !important; box-shadow:0 6px 18px rgba(2,132,199,0.35) !important; }

/* ── Inputs ── */
.stTextInput > div > div > input, .stTextArea > div > div > textarea { background:var(--surface) !important; border:1px solid var(--border) !important; color:var(--text) !important; border-radius:var(--radius-sm) !important; font-family:'JetBrains Mono',monospace !important; font-size:0.84rem !important; padding:0.6rem 0.9rem !important; }
.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus { border-color:var(--cyan) !important; box-shadow:0 0 0 2px var(--cyan-dim) !important; }
label[data-testid="stWidgetLabel"] { font-family:'JetBrains Mono',monospace !important; font-size:0.68rem !important; letter-spacing:0.08em !important; text-transform:uppercase !important; color:var(--text-muted) !important; }

/* ── Multiselect ── */
[data-baseweb="select"] { background:var(--surface) !important; border-color:var(--border) !important; }

/* ── Metrics ── */
[data-testid="stMetric"] { background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:var(--radius) !important; padding:1rem 1.1rem !important; }
[data-testid="stMetricLabel"] p { font-family:'JetBrains Mono',monospace !important; font-size:0.62rem !important; letter-spacing:0.1em !important; text-transform:uppercase !important; color:var(--text-muted) !important; }
[data-testid="stMetricValue"] { font-size:1.7rem !important; font-weight:800 !important; color:var(--text) !important; }

/* ── Progress ── */
.stProgress > div > div { background:linear-gradient(90deg,#0284c7,var(--cyan)) !important; border-radius:4px !important; }

/* ── DataFrame ── */
[data-testid="stDataFrame"] { border:1px solid var(--border) !important; border-radius:var(--radius) !important; overflow:hidden; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background:var(--surface) !important; border-right:1px solid var(--border) !important; }

/* ── Expander ── */
details { background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:var(--radius-lg) !important; margin-bottom:0.75rem !important; overflow:hidden; }
summary { font-family:'Outfit',sans-serif !important; font-size:0.95rem !important; font-weight:600 !important; padding:1rem 1.2rem !important; color:var(--text) !important; }
details[open] summary { border-bottom:1px solid var(--border-lite) !important; }
details > div { padding:1.2rem 1.4rem !important; }

hr { border-color:var(--border) !important; margin:1.5rem 0 !important; }
.err-card { background:var(--red-dim); border:1px solid var(--red-border); border-radius:var(--radius); padding:0.85rem 1.2rem; margin-bottom:0.5rem; font-size:0.88rem; color:var(--red); }

/* ── Agent stats ── */
.agent-stat-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:0.6rem; margin-bottom:1rem; }
.agent-stat { background:var(--surface2); border:1px solid var(--border); border-radius:var(--radius-sm); padding:0.85rem 1rem; }
.agent-stat-label { font-family:'JetBrains Mono',monospace; font-size:0.6rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--text-muted); margin-bottom:0.35rem; }
.agent-stat-value { font-size:1.4rem; font-weight:800; color:var(--text); }
.agent-ready-yes { color:var(--green) !important; }
.agent-ready-no  { color:var(--red) !important; }

/* ── Bench ── */
.bench-row { display:flex; align-items:center; gap:0.9rem; padding:0.65rem 0; border-bottom:1px solid var(--border-lite); }
.bench-row:last-child { border-bottom:none; }
.bench-label { width:120px; font-size:0.84rem; font-weight:600; color:var(--text); flex-shrink:0; }
.bench-cat   { width:80px; font-family:'JetBrains Mono',monospace; font-size:0.6rem; color:var(--text-muted); flex-shrink:0; }
.bench-bar-track { flex:1; height:8px; background:var(--border); border-radius:4px; overflow:hidden; }
.bench-bar-fill  { height:100%; border-radius:4px; background:linear-gradient(90deg,#0891b2,var(--cyan)); }
.bench-score { font-family:'JetBrains Mono',monospace; font-size:0.85rem; font-weight:600; color:var(--cyan); width:36px; text-align:right; flex-shrink:0; }

.input-hint { font-family:'JetBrains Mono',monospace; font-size:0.65rem; color:var(--text-muted); margin-top:0.4rem; letter-spacing:0.06em; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONSTANTS
# ============================================================================

REQUEST_TIMEOUT   = 14
MAX_WORKERS       = 8
CACHE_TTL_SECONDS = 3600   # 1 hour
MAX_RETRIES       = 2
RETRY_BACKOFF     = 1.2    # seconds

CRAWL_PATHS = ["", "/about", "/products", "/pipeline", "/newsroom", "/science"]

PHARMA_BENCHMARKS = {
    "Diabetes":  {"Lilly": 92, "Novo Nordisk": 87, "Merck": 71},
    "Oncology":  {"Roche": 89, "BMS": 85, "Pfizer": 68},
    "Cardio":    {"AstraZeneca": 83, "Sanofi": 79, "GSK": 65},
}

SCORE_WEIGHTS = {"schema": 25, "authority": 30, "tech": 12, "geo": 18, "mcp": 15}

PILLAR_META = [
    ("Schema",    "schema",    "bar-cyan",   "#22d3ee"),
    ("Authority", "authority", "bar-blue",   "#60a5fa"),
    ("Tech",      "tech",      "bar-purple", "#a78bfa"),
    ("GEO",       "geo",       "bar-green",  "#34d399"),
    ("MCP",       "mcp",       "bar-amber",  "#fbbf24"),
]

DEFAULT_DOMAINS = """https://www.lilly.com
https://www.pfizer.com
https://www.merck.com
https://www.novonordisk.com
https://www.astrazeneca.com"""

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

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
    pages_crawled: int = 1
    ai_recommendations: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    cached: bool = False
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def priority(self) -> str:
        if self.score.total < 60: return "CRITICAL"
        if self.score.total < 78: return "HIGH"
        return "GOOD"

    @property
    def ring_class(self) -> str:
        return "ring-green" if self.score.total >= 78 else "ring-amber" if self.score.total >= 60 else "ring-red"

    @property
    def tag_class(self) -> str:
        return {"CRITICAL": "rtag-critical", "HIGH": "rtag-high", "GOOD": "rtag-good"}[self.priority]

# ============================================================================
# CACHE LAYER
# ============================================================================

def _cache_key(url: str) -> str:
    return hashlib.md5(url.lower().encode()).hexdigest()

def cache_get(url: str) -> Optional[ScanResult]:
    key = _cache_key(url)
    entry = st.session_state.get(f"cache_{key}")
    if entry:
        result, ts = entry
        if datetime.now() - ts < timedelta(seconds=CACHE_TTL_SECONDS):
            result.cached = True
            return result
    return None

def cache_set(url: str, result: ScanResult):
    key = _cache_key(url)
    st.session_state[f"cache_{key}"] = (result, datetime.now())

# ============================================================================
# HTTP WITH RETRY
# ============================================================================

HEADERS = {
    "User-Agent": "PharmaMCP/9.0 (GEO-Intelligence; +https://xodigital.com/bot)",
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch_with_retry(url: str, timeout: int = REQUEST_TIMEOUT) -> tuple[Optional[str], int]:
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            return r.text, r.status_code
        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES: return None, -1
        except requests.exceptions.ConnectionError:
            if attempt == MAX_RETRIES: return None, -2
        except Exception:
            return None, -3
        time.sleep(RETRY_BACKOFF * (attempt + 1))
    return None, -3

# ============================================================================
# MULTI-PAGE CRAWLING
# ============================================================================

def crawl_domain(base_url: str) -> tuple[str, int, int]:
    """
    Fetch up to 6 pages for a domain, merge their HTML.
    Returns (merged_html, primary_status_code, pages_crawled).
    """
    parsed   = urlparse(base_url)
    root     = f"{parsed.scheme}://{parsed.netloc}"
    htmls    = []
    primary_status = 0
    pages_crawled  = 0

    def _fetch_path(path):
        url  = root + path if path else base_url
        html, status = fetch_with_retry(url, timeout=10)
        return html, status, path

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(_fetch_path, p): p for p in CRAWL_PATHS}
        for fut in as_completed(futures):
            html, status, path = fut.result()
            if html:
                htmls.append(html)
                pages_crawled += 1
                if path == "" or path == "/":
                    primary_status = status

    merged = "\n".join(htmls)
    if not primary_status and htmls:
        primary_status = 200
    return merged, primary_status, pages_crawled

# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def extract_schemas(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    types: set[str] = set()
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "{}")
        except json.JSONDecodeError:
            continue
        def _r(obj):
            if isinstance(obj, dict):
                t = obj.get("@type")
                if t: types.add(t if isinstance(t, str) else t[0])
                for v in obj.values(): _r(v)
            elif isinstance(obj, list):
                for item in obj: _r(item)
        _r(data)
    return list(types)


def detect_signals(html: str) -> PharmaSignals:
    text = html.lower()
    return PharmaSignals(
        medical_review   = bool(re.search(r"reviewed by|medically reviewed", text)),
        prescribing_info = "prescribing information" in text,
        med_guide        = "medication guide" in text,
        adverse_events   = bool(re.search(r"adverse.{0,15}event", text)),
        pubmed           = "pubmed" in text,
        doi_citations    = bool(re.search(r"\b10\.\d{4,9}/", text)),
        references       = bool(re.search(r"\breferences?\b|\bsources?\b", text)),
        faq_schema       = bool(re.search(r"\bfaq\b|frequently asked", text)),
    )


def detect_mcp(html: str) -> MCPStatus:
    soup = BeautifulSoup(html, "html.parser")
    return MCPStatus(
        agent_ready   = "navigator.modelContext" in html or "mcp.json" in html,
        mcp_manifests = len(soup.find_all("script", {"type": "application/mcp+json"})),
        functions     = len(re.findall(r"\b(get_|find_|check_|book_|schedule_)\w+", html, re.I)),
    )


def compute_score(schemas, signals, status_code, mcp) -> ScoreBreakdown:
    w = SCORE_WEIGHTS
    schema_score    = min(len(schemas) * 3.5, w["schema"])
    authority_score = min(signals.count() * 4.5, w["authority"])
    tech_score      = w["tech"] if status_code == 200 else max(0, w["tech"] - 6)
    geo_score       = min(len(schemas) * 2 + signals.faq_schema + signals.pubmed, w["geo"])
    mcp_score       = (w["mcp"] if mcp.agent_ready
                       else min(mcp.functions * 2.5 + mcp.mcp_manifests * 3, w["mcp"] - 3))
    total = min(schema_score + authority_score + tech_score + geo_score + mcp_score, 100)
    return ScoreBreakdown(
        total=round(total, 1), schema=round(schema_score, 1),
        authority=round(authority_score, 1), tech=round(tech_score, 1),
        geo=round(geo_score, 1), mcp=round(mcp_score, 1),
    )


def build_improvements(signals: PharmaSignals, schemas: list) -> list[dict]:
    fixes = []
    if not signals.faq_schema:     fixes.append({"label": "FAQPage schema markup",  "pts": 14})
    if not signals.pubmed:         fixes.append({"label": "PubMed / DOI citations", "pts": 9})
    if signals.count() < 4:       fixes.append({"label": "E-E-A-T trust signals",  "pts": 12})
    if len(schemas) < 3:           fixes.append({"label": "MedicalEntity schemas",  "pts": 11})
    if not signals.medical_review: fixes.append({"label": "Medical review by-line", "pts": 8})
    return fixes[:4]

# ============================================================================
# CLAUDE AI RECOMMENDATIONS
# ============================================================================

def get_ai_recommendations(result: ScanResult, api_key: str) -> str:
    """Call Claude API to generate tailored GEO/MCP improvement plan."""
    if not api_key:
        return ""

    sig = asdict(result.signals)
    present  = [k for k, v in sig.items() if v]
    missing  = [k for k, v in sig.items() if not v]

    prompt = f"""You are a pharmaceutical digital marketing strategist specialising in GEO (Generative Engine Optimisation) and MCP (Model Context Protocol) readiness.

Analyse this domain scan result and provide a concise, actionable improvement plan:

DOMAIN: {result.domain}
GEO/MCP SCORE: {result.score.total:.0f}/100
PRIORITY: {result.priority}

SCORE BREAKDOWN:
- Schema: {result.score.schema:.0f}/25
- Authority: {result.score.authority:.0f}/30
- Tech: {result.score.tech:.0f}/12
- GEO: {result.score.geo:.0f}/18
- MCP: {result.score.mcp:.0f}/15

DETECTED SIGNALS: {', '.join(present) if present else 'none'}
MISSING SIGNALS: {', '.join(missing) if missing else 'none'}
DETECTED SCHEMAS: {', '.join(result.schemas) if result.schemas else 'none'}
MCP AGENT READY: {result.mcp.agent_ready}
PAGES CRAWLED: {result.pages_crawled}

Provide exactly 4 specific, numbered recommendations tailored to this pharma domain. Each recommendation should:
1. Name the specific fix (bold it with **)
2. Explain WHY it matters for AI/LLM visibility in 1 sentence
3. Give one concrete implementation step

Keep the total response under 250 words. Be direct and specific — no generic advice."""

    try:
        resp = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        data = resp.json()
        if resp.status_code == 200:
            return data["content"][0]["text"].strip()
        return f"API error {resp.status_code}: {data.get('error', {}).get('message', 'Unknown')}"
    except Exception as e:
        return f"Could not reach Claude API: {e}"

# ============================================================================
# DOMAIN SCANNER
# ============================================================================

def scan_domain(url: str, multi_page: bool = True) -> ScanResult:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    domain = urlparse(url).netloc

    # Cache check
    cached = cache_get(url)
    if cached:
        return cached

    if multi_page:
        html, status_code, pages_crawled = crawl_domain(url)
    else:
        html, status_code = fetch_with_retry(url)
        pages_crawled = 1 if html else 0

    if not html:
        err = {-1: "Timeout", -2: "Connection refused", -3: "Unknown error"}.get(status_code, "Failed")
        return ScanResult(url=url, domain=domain, score=ScoreBreakdown(), error=err)

    schemas    = extract_schemas(html)[:10]
    signals    = detect_signals(html)
    mcp_status = detect_mcp(html)
    score      = compute_score(schemas, signals, status_code, mcp_status)
    fixes      = build_improvements(signals, schemas)

    result = ScanResult(
        url=url, domain=domain, score=score, schemas=schemas,
        signals=signals, mcp=mcp_status, status_code=status_code,
        improvements=fixes, pages_crawled=pages_crawled,
    )
    cache_set(url, result)
    return result


def parallel_scan(urls: list[str], multi_page: bool = True) -> list[ScanResult]:
    results: list[Optional[ScanResult]] = [None] * len(urls)
    bar  = st.progress(0, text="Starting scan…")
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(scan_domain, url, multi_page): i for i, url in enumerate(urls)}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:   results[idx] = fut.result()
            except Exception as e:
                results[idx] = ScanResult(
                    url=urls[idx], domain=urlparse(urls[idx]).netloc,
                    score=ScoreBreakdown(), error=str(e))
            done += 1
            bar.progress(done / len(urls), text=f"Scanning… {done}/{len(urls)} complete")
    bar.empty()
    return results

# ============================================================================
# PDF EXPORT
# ============================================================================

def build_pdf_report(results: list[ScanResult], client_name: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=18*mm, bottomMargin=18*mm,
    )

    # Colour palette
    C_DARK   = colors.HexColor("#0b0e17")
    C_NAVY   = colors.HexColor("#111520")
    C_CYAN   = colors.HexColor("#22d3ee")
    C_GREEN  = colors.HexColor("#34d399")
    C_AMBER  = colors.HexColor("#fbbf24")
    C_RED    = colors.HexColor("#f87171")
    C_TEXT   = colors.HexColor("#f0f4ff")
    C_MUTED  = colors.HexColor("#6b7a99")
    C_BORDER = colors.HexColor("#232b40")

    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    def sty(size=10, bold=False, color=C_TEXT, align=TA_LEFT, leading=None):
        return ParagraphStyle(
            "x", parent=normal, fontSize=size, fontName="Helvetica-Bold" if bold else "Helvetica",
            textColor=color, alignment=align, leading=leading or size * 1.35,
            spaceAfter=0, spaceBefore=0,
        )

    story = []
    W = A4[0] - 40*mm  # usable width

    # ── Cover header ──
    cover_data = [[
        Paragraph("🔬 XO Pharma MCP/GEO", sty(18, bold=True, color=C_CYAN)),
        Paragraph("INTELLIGENCE REPORT", sty(10, color=C_MUTED, align=TA_RIGHT)),
    ]]
    cover_tbl = Table(cover_data, colWidths=[W*0.65, W*0.35])
    cover_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
        ("LINEBELOW",     (0,0), (-1,0), 2, C_CYAN),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(cover_tbl)
    story.append(Spacer(1, 6*mm))

    # Meta row
    meta_data = [[
        Paragraph(f"Client: <b>{client_name}</b>", sty(9, color=C_TEXT)),
        Paragraph(f"Domains: <b>{len(results)}</b>", sty(9, color=C_TEXT, align=TA_CENTER)),
        Paragraph(f"Generated: <b>{datetime.now().strftime('%d %b %Y %H:%M')}</b>",
                  sty(9, color=C_TEXT, align=TA_RIGHT)),
    ]]
    meta_tbl = Table(meta_data, colWidths=[W/3, W/3, W/3])
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10), ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("LINEBELOW",     (0,0), (-1,0), 0.5, C_BORDER),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 8*mm))

    # ── Summary table ──
    story.append(Paragraph("EXECUTIVE SUMMARY", sty(8, bold=True, color=C_MUTED)))
    story.append(Spacer(1, 3*mm))

    hdr = ["Domain", "Score", "Priority", "Schema", "Authority", "GEO", "MCP", "Pages", "Fix Pts"]
    rows = [hdr]
    for r in sorted(results, key=lambda x: -x.score.total):
        p_color = C_RED if r.priority=="CRITICAL" else C_AMBER if r.priority=="HIGH" else C_GREEN
        rows.append([
            Paragraph(r.domain, sty(8, color=C_TEXT)),
            Paragraph(f"{r.score.total:.0f}", sty(9, bold=True, color=C_CYAN, align=TA_CENTER)),
            Paragraph(r.priority, sty(8, bold=True, color=p_color, align=TA_CENTER)),
            Paragraph(f"{r.score.schema:.0f}", sty(8, color=C_TEXT, align=TA_CENTER)),
            Paragraph(f"{r.score.authority:.0f}", sty(8, color=C_TEXT, align=TA_CENTER)),
            Paragraph(f"{r.score.geo:.0f}", sty(8, color=C_TEXT, align=TA_CENTER)),
            Paragraph(f"{r.score.mcp:.0f}", sty(8, color=C_TEXT, align=TA_CENTER)),
            Paragraph(str(r.pages_crawled), sty(8, color=C_TEXT, align=TA_CENTER)),
            Paragraph(f"+{sum(f['pts'] for f in r.improvements)}", sty(8, color=C_AMBER, align=TA_CENTER)),
        ])

    col_w = [W*0.28, W*0.08, W*0.11, W*0.07, W*0.09, W*0.07, W*0.07, W*0.07, W*0.08]
    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), C_NAVY),
        ("TEXTCOLOR",    (0,0), (-1,0), C_MUTED),
        ("FONTSIZE",     (0,0), (-1,0), 7),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("TOPPADDING",   (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",  (0,0), (-1,-1), 6), ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("LINEBELOW",    (0,0), (-1,-1), 0.4, C_BORDER),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_NAVY, C_DARK]),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 10*mm))

    # ── Per-domain detail ──
    for r in sorted(results, key=lambda x: -x.score.total):
        p_color = C_RED if r.priority=="CRITICAL" else C_AMBER if r.priority=="HIGH" else C_GREEN

        # Domain header
        dh_data = [[
            Paragraph(r.domain, sty(12, bold=True, color=C_TEXT)),
            Paragraph(f"{r.score.total:.0f}/100", sty(14, bold=True, color=C_CYAN, align=TA_RIGHT)),
        ]]
        dh_tbl = Table(dh_data, colWidths=[W*0.75, W*0.25])
        dh_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), C_NAVY),
            ("LINEBELOW",  (0,0), (-1,0), 1.5, p_color),
            ("TOPPADDING",    (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("RIGHTPADDING",  (0,0), (-1,-1), 10),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(KeepTogether([dh_tbl]))
        story.append(Spacer(1, 3*mm))

        # Pillar scores mini-table
        pillar_hdr  = [Paragraph(p[0], sty(7, bold=True, color=C_MUTED, align=TA_CENTER)) for p in PILLAR_META]
        pillar_vals = []
        for label, attr, _, col in PILLAR_META:
            v = getattr(r.score, attr)
            mx = SCORE_WEIGHTS[attr]
            pillar_vals.append(
                Paragraph(f"{v:.0f}/{mx}", sty(9, bold=True, color=colors.HexColor(col), align=TA_CENTER))
            )
        p_tbl = Table([pillar_hdr, pillar_vals], colWidths=[W/5]*5)
        p_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,-1), C_DARK),
            ("TOPPADDING",   (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LINEBELOW",    (0,0), (4,0), 0.4, C_BORDER),
            ("LINEABOVE",    (0,0), (4,0), 0.4, C_BORDER),
        ]))
        story.append(p_tbl)
        story.append(Spacer(1, 3*mm))

        # Fixes + signals side by side
        fix_lines = [Paragraph("PRIORITY FIXES", sty(7, bold=True, color=C_MUTED))]
        fix_lines.append(Spacer(1, 2*mm))
        for fix in r.improvements:
            fix_lines.append(
                Paragraph(f"➕ {fix['label']} (+{fix['pts']}pts)", sty(8, color=C_AMBER))
            )
        if not r.improvements:
            fix_lines.append(Paragraph("✅ No critical gaps", sty(8, color=C_GREEN)))

        sig = asdict(r.signals)
        sig_lines = [Paragraph("E-E-A-T SIGNALS", sty(7, bold=True, color=C_MUTED))]
        sig_lines.append(Spacer(1, 2*mm))
        for k, v in sig.items():
            label = k.replace("_", " ").title()
            icon  = "✓" if v else "✗"
            c     = C_GREEN if v else C_MUTED
            sig_lines.append(Paragraph(f"{icon}  {label}", sty(8, color=c)))

        detail_tbl = Table(
            [[fix_lines, sig_lines]],
            colWidths=[W*0.5, W*0.5],
        )
        detail_tbl.setStyle(TableStyle([
            ("VALIGN",       (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING",  (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING",   (0,0), (-1,-1), 0),
        ]))
        story.append(detail_tbl)

        # AI recommendations (if present)
        if r.ai_recommendations:
            story.append(Spacer(1, 3*mm))
            story.append(Paragraph("AI RECOMMENDATIONS", sty(7, bold=True, color=C_CYAN)))
            story.append(Spacer(1, 1*mm))
            for line in r.ai_recommendations.split("\n"):
                if line.strip():
                    story.append(Paragraph(line.strip(), sty(8, color=C_TEXT, leading=12)))

        story.append(Spacer(1, 7*mm))
        story.append(HRFlowable(width="100%", thickness=0.4, color=C_BORDER))
        story.append(Spacer(1, 5*mm))

    doc.build(story)
    return buf.getvalue()

# ============================================================================
# DATA UTILS
# ============================================================================

def results_to_df(results: list[ScanResult]) -> pd.DataFrame:
    rows = []
    for r in results:
        if not r.ok: continue
        rows.append({
            "Domain": r.domain, "Score": r.score.total,
            "Schema": r.score.schema, "Authority": r.score.authority,
            "Tech": r.score.tech, "GEO": r.score.geo, "MCP Score": r.score.mcp,
            "Agent Ready": r.mcp.agent_ready, "MCP Functions": r.mcp.functions,
            "Schemas Found": len(r.schemas), "Pages Crawled": r.pages_crawled,
            "Priority": r.priority,
            "Fix Potential (pts)": sum(f["pts"] for f in r.improvements),
            "Cached": r.cached, "Timestamp": r.timestamp,
        })
    return pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)

# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_hero():
    st.markdown("""
    <div class="hero">
        <div class="hero-eyebrow">XO Digital · Enterprise Platform · v9</div>
        <div class="hero-title">🔬 Pharma <span>MCP/GEO</span> Intelligence</div>
        <p class="hero-desc">Competitive AI-readiness analysis for pharmaceutical brands. Scan, score, compare, and fix.</p>
        <div class="badge-row">
            <span class="badge active">⚡ Parallel + Multi-Page</span>
            <span class="badge active">🤖 MCP Detection</span>
            <span class="badge active">🧠 AI Recommendations</span>
            <span class="badge active">📄 PDF Export</span>
            <span class="badge active">⚖️ Side-by-Side Compare</span>
            <span class="badge active">💾 1hr Cache</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_pillar_grid(score: ScoreBreakdown):
    cols = st.columns(5)
    for col, (label, attr, bar_cls, color) in zip(cols, PILLAR_META):
        val = getattr(score, attr)
        mx  = SCORE_WEIGHTS[attr]
        pct = int((val / mx) * 100)
        with col:
            st.markdown(f"""
            <div class="pillar">
                <div class="pillar-label">{label}</div>
                <div class="pillar-score" style="color:{color}">
                    {val:.0f}<span class="pillar-max">/{mx}</span>
                </div>
                <div class="bar-track"><div class="bar-fill {bar_cls}" style="width:{pct}%"></div></div>
                <div class="pillar-pct">{pct}% of max</div>
            </div>""", unsafe_allow_html=True)


def render_result_card(result: ScanResult, api_key: str = ""):
    fix_pts = sum(f["pts"] for f in result.improvements)
    priority_icon = {"CRITICAL": "🔴", "HIGH": "🟡", "GOOD": "🟢"}[result.priority]
    mcp_label = "✓ MCP Ready" if result.mcp.agent_ready else "✗ MCP"
    cached_tag = '<span class="rtag rtag-cached">💾 cached</span>' if result.cached else ""
    pages_tag  = f'<span class="rtag rtag-neutral">📄 {result.pages_crawled} pages</span>'

    with st.expander(
        f"{priority_icon}  **{result.domain}**"
        f"  ·  {result.score.total:.0f}/100"
        f"  ·  {result.priority}"
        f"  ·  +{fix_pts}pts"
    ):
        # Score ring + pillars
        ring_col, pillars_col = st.columns([1, 6])
        with ring_col:
            st.markdown(f"""
            <div style="display:flex;align-items:center;height:100%;padding-top:0.4rem;">
                <div class="score-ring {result.ring_class}">
                    {result.score.total:.0f}
                    <div class="ring-sub">/100</div>
                </div>
            </div>""", unsafe_allow_html=True)
        with pillars_col:
            render_pillar_grid(result.score)

        st.markdown("<div style='height:0.9rem'></div>", unsafe_allow_html=True)

        # Tags
        mcp_tag_cls = "rtag-mcp" if result.mcp.agent_ready else "rtag-neutral"
        st.markdown(f"""
        <div class="result-tags">
            <span class="rtag {result.tag_class}">{result.priority}</span>
            <span class="rtag {mcp_tag_cls}">{mcp_label}</span>
            <span class="rtag rtag-neutral">{len(result.schemas)} schemas</span>
            <span class="rtag rtag-neutral">HTTP {result.status_code}</span>
            <span class="rtag rtag-neutral">{result.mcp.functions} functions</span>
            {pages_tag}
            {cached_tag}
        </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # Signals + Fixes
        col_sig, col_fix = st.columns(2)
        with col_sig:
            st.markdown('<div class="section-label">E-E-A-T Signals</div>', unsafe_allow_html=True)
            sig_dict = asdict(result.signals)
            sig_labels = {
                "medical_review": "Medical Review", "prescribing_info": "Prescribing Info",
                "med_guide": "Med Guide",           "adverse_events": "Adverse Events",
                "pubmed": "PubMed Links",           "doi_citations": "DOI Citations",
                "references": "References",         "faq_schema": "FAQ Schema",
            }
            rows_html = '<div class="signal-grid">'
            for key, label in sig_labels.items():
                on = sig_dict[key]
                rows_html += f"""<div class="signal-item">
                    <div class="signal-dot {'dot-on' if on else 'dot-off'}"></div>
                    <span class="{'signal-on' if on else ''}">{label}</span>
                </div>"""
            rows_html += "</div>"
            st.markdown(rows_html, unsafe_allow_html=True)

            if result.schemas:
                st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
                st.markdown('<div class="section-label">Detected Schemas</div>', unsafe_allow_html=True)
                chips = "".join(f'<span class="schema-chip">{s}</span>' for s in result.schemas)
                st.markdown(f'<div class="schema-chips">{chips}</div>', unsafe_allow_html=True)

        with col_fix:
            st.markdown('<div class="section-label">Priority Fixes</div>', unsafe_allow_html=True)
            if result.improvements:
                html = '<div class="fix-list">'
                for fix in result.improvements:
                    html += f"""<div class="fix-item">
                        <span>➕ {fix['label']}</span>
                        <span class="fix-pts">+{fix['pts']}pts</span>
                    </div>"""
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.markdown('<div class="all-good">✅ No critical gaps detected</div>', unsafe_allow_html=True)

        # ── AI Recommendations ──
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">AI Recommendations</div>', unsafe_allow_html=True)

        if result.ai_recommendations:
            st.markdown(f"""
            <div class="ai-rec-box">
                <div class="ai-rec-header">🧠 Claude Analysis</div>
                <div class="ai-rec-body">{result.ai_recommendations}</div>
            </div>""", unsafe_allow_html=True)
        elif api_key:
            if st.button(f"🧠 Generate AI Recommendations", key=f"ai_{result.domain}"):
                with st.spinner("Asking Claude for tailored recommendations…"):
                    recs = get_ai_recommendations(result, api_key)
                    result.ai_recommendations = recs
                    # Update cache
                    cache_set(result.url, result)
                st.rerun()
        else:
            st.markdown(
                '<div style="font-size:0.8rem;color:var(--text-muted);">'
                '🔑 Enter your Anthropic API key in the sidebar to unlock AI recommendations.</div>',
                unsafe_allow_html=True)


def render_kpi_row(domains, avg_score, agent_ready, critical, fix_pts):
    avg_cls = "kpi-up" if avg_score >= 75 else "kpi-down"
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Domains Analysed</div>
            <div class="kpi-value">{domains}</div>
            <div class="kpi-sub">total in session</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Avg GEO Score</div>
            <div class="kpi-value {avg_cls}">{avg_score:.1f}</div>
            <div class="kpi-sub">out of 100</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Agent Ready</div>
            <div class="kpi-value">{agent_ready}</div>
            <div class="kpi-sub">of {domains} scanned</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Critical Priority</div>
            <div class="kpi-value kpi-down">{critical}</div>
            <div class="kpi-sub">need urgent fixes</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Fix Potential</div>
            <div class="kpi-value kpi-up">+{fix_pts}</div>
            <div class="kpi-sub">total score points</div>
        </div>
    </div>""", unsafe_allow_html=True)


def render_benchmark_bars():
    entries = sorted(
        [(co, cat, sc) for cat, companies in PHARMA_BENCHMARKS.items()
         for co, sc in companies.items()],
        key=lambda x: -x[2]
    )
    rows = ""
    for company, cat, score in entries:
        rows += f"""<div class="bench-row">
            <div class="bench-label">{company}</div>
            <div class="bench-cat">{cat}</div>
            <div class="bench-bar-track"><div class="bench-bar-fill" style="width:{score}%"></div></div>
            <div class="bench-score">{score}</div>
        </div>"""
    st.markdown(f"""
    <div style="background:var(--surface);border:1px solid var(--border);
                border-radius:var(--radius);padding:1.4rem 1.6rem;">
        <div class="section-label">Industry MCP/GEO Scores — Ranked</div>
        {rows}
    </div>""", unsafe_allow_html=True)


def render_compare_tab(history: list[ScanResult]):
    """Side-by-side comparison of 2–4 selected domains."""
    ok = [r for r in history if r.ok]
    if len(ok) < 2:
        st.info("Scan at least 2 domains to use the comparison view.")
        return

    domain_map = {r.domain: r for r in ok}
    selected = st.multiselect(
        "SELECT DOMAINS TO COMPARE (2–4)",
        options=list(domain_map.keys()),
        default=list(domain_map.keys())[:min(4, len(domain_map))],
        max_selections=4,
    )
    if len(selected) < 2:
        st.warning("Select at least 2 domains.")
        return

    chosen = [domain_map[d] for d in selected]
    n = len(chosen)

    # Header row
    cols = st.columns([1.4] + [1]*n)
    cols[0].markdown('<div class="section-label" style="margin-top:2rem">Metric</div>',
                     unsafe_allow_html=True)
    for col, r in zip(cols[1:], chosen):
        ring_color = {"ring-green": "#34d399", "ring-amber": "#fbbf24", "ring-red": "#f87171"}[r.ring_class]
        col.markdown(f"""
        <div style="text-align:center;padding:0.8rem;background:var(--surface);
                    border:1px solid var(--border);border-radius:var(--radius-sm);
                    border-top:3px solid {ring_color};">
            <div style="font-size:1.8rem;font-weight:800;color:{ring_color}">{r.score.total:.0f}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:var(--text-muted);margin-top:2px">/100</div>
            <div style="font-size:0.82rem;font-weight:600;color:var(--text);margin-top:4px">{r.domain}</div>
            <span class="rtag {r.tag_class}" style="margin-top:4px;display:inline-block">{r.priority}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # Comparison rows
    def _compare_row(label: str, values: list, fmt=lambda x: x, higher_better=True):
        cols = st.columns([1.4] + [1]*n)
        cols[0].markdown(
            f'<div style="font-family:JetBrains Mono,monospace;font-size:0.7rem;'
            f'color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;'
            f'padding-top:0.5rem;">{label}</div>',
            unsafe_allow_html=True)

        best = max(values) if higher_better else min(values)
        for col, val in zip(cols[1:], values):
            is_best  = val == best
            win_cls  = "color:var(--cyan);border:1px solid var(--cyan-border);background:var(--cyan-dim)" if is_best else "color:var(--text-muted);border:1px solid var(--border);background:var(--surface)"
            col.markdown(
                f'<div style="text-align:center;padding:0.5rem 0.4rem;border-radius:var(--radius-sm);'
                f'font-weight:{"700" if is_best else "400"};font-size:0.9rem;{win_cls}">{fmt(val)}</div>',
                unsafe_allow_html=True)

    _compare_row("Total Score",    [r.score.total    for r in chosen], fmt=lambda x: f"{x:.0f}/100")
    _compare_row("Schema",         [r.score.schema   for r in chosen], fmt=lambda x: f"{x:.0f}/25")
    _compare_row("Authority",      [r.score.authority for r in chosen], fmt=lambda x: f"{x:.0f}/30")
    _compare_row("Tech",           [r.score.tech     for r in chosen], fmt=lambda x: f"{x:.0f}/12")
    _compare_row("GEO",            [r.score.geo      for r in chosen], fmt=lambda x: f"{x:.0f}/18")
    _compare_row("MCP",            [r.score.mcp      for r in chosen], fmt=lambda x: f"{x:.0f}/15")
    _compare_row("Pages Crawled",  [r.pages_crawled  for r in chosen], fmt=str)
    _compare_row("Schemas Found",  [len(r.schemas)   for r in chosen], fmt=str)
    _compare_row("E-E-A-T Signals",[r.signals.count() for r in chosen], fmt=lambda x: f"{x}/8")
    _compare_row("MCP Functions",  [r.mcp.functions  for r in chosen], fmt=str)
    _compare_row("Fix Potential",  [sum(f["pts"] for f in r.improvements) for r in chosen],
                 fmt=lambda x: f"+{x}pts", higher_better=False)

# ============================================================================
# SESSION STATE
# ============================================================================

def init_state():
    for key in ("scan_results", "history"):
        if key not in st.session_state:
            st.session_state[key] = []

# ============================================================================
# MAIN
# ============================================================================

def main():
    init_state()
    render_hero()

    # ── Sidebar ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        api_key = st.text_input(
            "ANTHROPIC API KEY",
            type="password",
            help="Required for AI recommendations. Never stored.",
            placeholder="sk-ant-...",
        )
        multi_page = st.toggle("Multi-page crawling", value=True,
                               help="Crawls up to 6 pages per domain for richer analysis")
        st.markdown("---")

        st.markdown("### 📊 Session Stats")
        ok = [r for r in st.session_state.history if r.ok]
        if ok:
            avg     = np.mean([r.score.total for r in ok])
            ready   = sum(1 for r in ok if r.mcp.agent_ready)
            avg_fix = int(np.mean([sum(f["pts"] for f in r.improvements) for r in ok]))
            cached  = sum(1 for r in ok if r.cached)
            st.metric("Domains scanned", len(ok))
            st.metric("Avg Score",       f"{avg:.1f}")
            st.metric("Agent Ready",     f"{ready}/{len(ok)}")
            st.metric("Avg Fix Potential", f"+{avg_fix}pts")
            if cached:
                st.metric("From Cache", f"{cached}/{len(ok)}")
        else:
            st.info("No scans yet.")

        st.markdown("---")
        if st.button("🗑 Clear All History"):
            st.session_state.history      = []
            st.session_state.scan_results = []
            st.rerun()

    # ── Client name ──
    col_client, _ = st.columns([2, 5])
    with col_client:
        client_name = st.text_input("CLIENT / BRAND", value="Pharma Brand", key="client_name")
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Tabs ──
    tab_scan, tab_compare, tab_agent, tab_bench, tab_exec = st.tabs([
        "🚀  Scanner",
        "⚖️  Compare",
        "🤖  Agent Tester",
        "🏆  Benchmarks",
        "📊  Executive",
    ])

    # ══════════════════════════════════════════
    # TAB 1 — SCANNER
    # ══════════════════════════════════════════
    with tab_scan:
        mode_label = "multi-page (up to 6 pages per domain)" if multi_page else "homepage only"
        st.markdown(f'<div class="section-label">Paste competitor domains · one per line · max 20 · {mode_label}</div>',
                    unsafe_allow_html=True)

        col_inp, col_act = st.columns([5, 1])
        with col_inp:
            raw_input = st.text_area("DOMAINS", value=DEFAULT_DOMAINS, height=180,
                                     label_visibility="collapsed")
            st.markdown('<div class="input-hint">HTTPS prefix optional · results cached 1hr · retry on failure</div>',
                        unsafe_allow_html=True)
        with col_act:
            st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
            run_scan  = st.button("🚀 SCAN NOW", type="primary", use_container_width=True)
            st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
            clear_btn = st.button("🗑 Clear",    use_container_width=True)

        if clear_btn:
            st.session_state.scan_results = []
            st.rerun()

        if run_scan:
            urls = [u.strip() for u in raw_input.splitlines() if u.strip()]
            if not urls:
                st.warning("No URLs provided.")
            elif len(urls) > 20:
                st.error("Maximum 20 domains per scan.")
            else:
                t0 = time.time()
                results = parallel_scan(urls, multi_page=multi_page)
                st.session_state.scan_results = results
                existing = {r.domain for r in st.session_state.history}
                for r in results:
                    if r.ok and r.domain not in existing:
                        st.session_state.history.append(r)
                    elif r.ok:
                        # update existing entry
                        for i, h in enumerate(st.session_state.history):
                            if h.domain == r.domain:
                                st.session_state.history[i] = r
                elapsed  = time.time() - t0
                ok_count = sum(1 for r in results if r.ok)
                cached_count = sum(1 for r in results if r.ok and r.cached)
                cache_note = f" ({cached_count} from cache)" if cached_count else ""
                st.success(f"✅ {ok_count}/{len(urls)} domains analysed in **{elapsed:.1f}s**{cache_note}")

        if st.session_state.scan_results:
            st.markdown("---")
            sorted_r    = sorted(st.session_state.scan_results, key=lambda r: (not r.ok, -r.score.total))
            ok_results  = [r for r in sorted_r if r.ok]
            err_results = [r for r in sorted_r if not r.ok]

            if ok_results:
                # Bulk AI recommendations button
                if api_key:
                    needs_recs = [r for r in ok_results if not r.ai_recommendations]
                    if needs_recs:
                        if st.button(f"🧠 Generate AI Recommendations for all {len(needs_recs)} domains"):
                            bar = st.progress(0, text="Getting AI recommendations…")
                            for i, r in enumerate(needs_recs):
                                r.ai_recommendations = get_ai_recommendations(r, api_key)
                                cache_set(r.url, r)
                                bar.progress((i+1)/len(needs_recs), text=f"Analysing {r.domain}…")
                            bar.empty()
                            st.rerun()

                st.markdown(f'<div class="section-label">{len(ok_results)} domain(s) analysed</div>',
                            unsafe_allow_html=True)
                for r in ok_results:
                    render_result_card(r, api_key=api_key)

            if err_results:
                st.markdown('<div class="section-label">Failed scans</div>', unsafe_allow_html=True)
                for r in err_results:
                    st.markdown(f'<div class="err-card">❌ <strong>{r.domain}</strong> — {r.error}</div>',
                                unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # TAB 2 — COMPARE
    # ══════════════════════════════════════════
    with tab_compare:
        st.markdown('<div class="section-label">Side-by-side domain comparison — select 2 to 4</div>',
                    unsafe_allow_html=True)
        render_compare_tab(st.session_state.history)

    # ══════════════════════════════════════════
    # TAB 3 — AGENT TESTER
    # ══════════════════════════════════════════
    with tab_agent:
        st.markdown('<div class="section-label">Test a single domain for MCP / AI-agent readiness</div>',
                    unsafe_allow_html=True)

        col_url, col_btn = st.columns([5, 1])
        with col_url:
            test_url = st.text_input("DOMAIN URL", value="https://www.lilly.com",
                                     key="agent_url", label_visibility="collapsed")
        with col_btn:
            run_test = st.button("🧪 RUN TEST", type="primary", use_container_width=True)

        if run_test:
            with st.spinner("Running agent compatibility test…"):
                result = scan_domain(test_url, multi_page=False)

            if not result.ok:
                st.markdown(f'<div class="err-card">❌ Scan failed: {result.error}</div>',
                            unsafe_allow_html=True)
            else:
                col_stats, col_json = st.columns([1, 2])
                with col_stats:
                    ar  = result.mcp.agent_ready
                    cls = "agent-ready-yes" if ar else "agent-ready-no"
                    lbl = "✅ YES" if ar else "❌ NO"
                    st.markdown(f"""
                    <div class="agent-stat-grid">
                        <div class="agent-stat" style="grid-column:span 2">
                            <div class="agent-stat-label">Agent Ready</div>
                            <div class="agent-stat-value {cls}">{lbl}</div>
                        </div>
                        <div class="agent-stat">
                            <div class="agent-stat-label">GEO Score</div>
                            <div class="agent-stat-value">{result.score.total:.0f}/100</div>
                        </div>
                        <div class="agent-stat">
                            <div class="agent-stat-label">Callable Functions</div>
                            <div class="agent-stat-value">{result.mcp.functions}</div>
                        </div>
                        <div class="agent-stat">
                            <div class="agent-stat-label">MCP Manifests</div>
                            <div class="agent-stat-value">{result.mcp.mcp_manifests}</div>
                        </div>
                        <div class="agent-stat">
                            <div class="agent-stat-label">Schemas Found</div>
                            <div class="agent-stat-value">{len(result.schemas)}</div>
                        </div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown('<div class="section-label" style="margin-top:1rem">Score Breakdown</div>',
                                unsafe_allow_html=True)
                    render_pillar_grid(result.score)

                with col_json:
                    st.markdown('<div class="section-label">Raw Agent Payload</div>',
                                unsafe_allow_html=True)
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

    # ══════════════════════════════════════════
    # TAB 4 — BENCHMARKS
    # ══════════════════════════════════════════
    with tab_bench:
        st.markdown('<div class="section-label">Pharma industry MCP/GEO benchmark scores</div>',
                    unsafe_allow_html=True)
        col_bars, col_stats = st.columns([3, 1])
        bm_rows = [
            {"Category": cat, "Company": co, "Score": sc}
            for cat, companies in PHARMA_BENCHMARKS.items()
            for co, sc in companies.items()
        ]
        bm_df = pd.DataFrame(bm_rows)

        with col_bars:
            render_benchmark_bars()
        with col_stats:
            st.metric("Industry Avg", f"{bm_df['Score'].mean():.1f}")
            st.metric("Top Score",    f"{bm_df['Score'].max()}")
            st.metric("Lowest Score", f"{bm_df['Score'].min()}")
            ok_results = [r for r in st.session_state.scan_results if r.ok]
            if ok_results:
                st.markdown("---")
                live_avg = np.mean([r.score.total for r in ok_results])
                delta    = live_avg - bm_df["Score"].mean()
                st.metric("Your Avg", f"{live_avg:.1f}", delta=f"{delta:+.1f} vs industry")

    # ══════════════════════════════════════════
    # TAB 5 — EXECUTIVE
    # ══════════════════════════════════════════
    with tab_exec:
        st.markdown('<div class="section-label">Executive intelligence — all scanned domains</div>',
                    unsafe_allow_html=True)

        all_results = [r for r in st.session_state.history if r.ok]
        if not all_results:
            st.info("Run a Turbo Scan first to unlock the executive dashboard.")
        else:
            df = results_to_df(all_results)

            render_kpi_row(
                domains     = len(df),
                avg_score   = df["Score"].mean(),
                agent_ready = int(df["Agent Ready"].sum()),
                critical    = len(df[df["Priority"] == "CRITICAL"]),
                fix_pts     = int(df["Fix Potential (pts)"].sum()),
            )

            st.markdown('<div class="section-label">Competitive Leaderboard</div>',
                        unsafe_allow_html=True)
            disp = df[["Domain", "Score", "Priority", "Agent Ready",
                        "Pages Crawled", "MCP Functions", "Schemas Found",
                        "Fix Potential (pts)"]].copy()
            disp["Score"] = disp["Score"].apply(lambda x: f"{x:.1f}")

            def _pc(v):
                if v == "CRITICAL": return "color:#f87171;font-weight:700"
                if v == "HIGH":     return "color:#fbbf24;font-weight:700"
                return "color:#34d399;font-weight:700"

            st.dataframe(
                disp.style.applymap(_pc, subset=["Priority"]),
                use_container_width=True, height=380,
            )

            st.markdown("---")
            col_csv, col_pdf = st.columns(2)

            with col_csv:
                buf = io.StringIO()
                df.to_csv(buf, index=False)
                st.download_button(
                    label="📥 Download CSV Report",
                    data=buf.getvalue().encode(),
                    file_name=f"XO-Pharma-{client_name.replace(' ','_')}-{datetime.now().strftime('%Y%m%d-%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            with col_pdf:
                if st.button("📄 Generate PDF Report", use_container_width=True):
                    with st.spinner("Building executive PDF…"):
                        pdf_bytes = build_pdf_report(all_results, client_name)
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"XO-Pharma-{client_name.replace(' ','_')}-{datetime.now().strftime('%Y%m%d-%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )


if __name__ == "__main__":
    main()
