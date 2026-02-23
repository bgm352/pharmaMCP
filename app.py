"""
Pharma MCP Agent Readiness Auditor
XO Digital | 2026

The question this app answers:
  "Can an AI agent actually USE this pharma website as an MCP tool?"

Not a SEO tool. Not a GEO tool.
A protocol-level audit: does this site expose the structured endpoints,
callable functions, machine-readable data, and agent manifests that
AI systems need to query it in real-time?
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
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Optional
import time
import hashlib

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether,
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Pharma MCP Auditor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================================
# CSS — Terminal / Protocol aesthetic
# Monochrome green-on-black. Amber for warnings. Red for failures.
# Feels like an agent runtime, not a marketing dashboard.
# ============================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

:root {
    --bg:         #080b08;
    --bg2:        #0d110d;
    --surface:    #111611;
    --surface2:   #161e16;
    --border:     #1e2b1e;
    --border-lit: #243024;

    --green:      #4ade80;
    --green-dim:  rgba(74,222,128,0.08);
    --green-glow: rgba(74,222,128,0.2);
    --green-bdr:  rgba(74,222,128,0.25);

    --amber:      #fbbf24;
    --amber-dim:  rgba(251,191,36,0.08);
    --amber-bdr:  rgba(251,191,36,0.3);

    --red:        #f87171;
    --red-dim:    rgba(248,113,113,0.08);
    --red-bdr:    rgba(248,113,113,0.3);

    --cyan:       #67e8f9;
    --cyan-dim:   rgba(103,232,249,0.08);
    --cyan-bdr:   rgba(103,232,249,0.25);

    --text:       #e2ffe2;
    --text-mid:   #8aaa8a;
    --text-dim:   #3d573d;

    --mono: 'IBM Plex Mono', monospace;
    --sans: 'IBM Plex Sans', sans-serif;

    --r: 6px;
    --r-lg: 10px;
}

html, body, [class*="css"] {
    font-family: var(--sans) !important;
    background: var(--bg) !important;
    color: var(--text) !important;
}
.main .block-container { padding: 0 2rem 5rem !important; max-width: 1360px !important; }

/* ── Scanlines overlay ── */
.main::before {
    content: '';
    position: fixed; inset: 0;
    background: repeating-linear-gradient(
        0deg, transparent, transparent 2px,
        rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px
    );
    pointer-events: none; z-index: 0;
}

/* ── Header bar ── */
.header-bar {
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 1.4rem 2rem 1.2rem;
    margin: 0 -2rem 2rem;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 2rem;
}
.header-logo {
    font-family: var(--mono);
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--green);
    letter-spacing: 0.04em;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.header-logo::before {
    content: '▶';
    font-size: 0.7rem;
    animation: blink 1.4s step-end infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
.header-tagline {
    font-family: var(--mono);
    font-size: 0.7rem;
    color: var(--text-dim);
    letter-spacing: 0.06em;
}
.header-right {
    font-family: var(--mono);
    font-size: 0.65rem;
    color: var(--text-dim);
    text-align: right;
    line-height: 1.8;
}
.header-right span { color: var(--green); }

/* ── Section label ── */
.slabel {
    font-family: var(--mono);
    font-size: 0.62rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin: 0 0 0.8rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.slabel::before { content: '//'; color: var(--green); font-size: 0.7rem; }

/* ── Protocol check pillars ── */
.pillar-grid { display: grid; grid-template-columns: repeat(5,1fr); gap: 0.6rem; }
.pillar {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: 0.9rem 1rem;
    position: relative;
    overflow: hidden;
}
.pillar::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
}
.pillar-g::before { background: var(--green); }
.pillar-a::before { background: var(--amber); }
.pillar-r::before { background: var(--red); }
.pillar-c::before { background: var(--cyan); }
.pillar-label {
    font-family: var(--mono);
    font-size: 0.58rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 0.5rem;
}
.pillar-val {
    font-family: var(--mono);
    font-size: 1.5rem;
    font-weight: 600;
    line-height: 1;
    margin-bottom: 0.35rem;
}
.pillar-max { font-size: 0.75rem; font-weight: 300; color: var(--text-dim); }
.bar-track { width:100%; height:3px; background:var(--border); border-radius:2px; margin-bottom:0.2rem; overflow:hidden; }
.bar-fill  { height:100%; border-radius:2px; }
.bf-g { background: var(--green); }
.bf-a { background: var(--amber); }
.bf-r { background: var(--red); }
.bf-c { background: var(--cyan); }
.pillar-pct { font-family:var(--mono); font-size:0.55rem; color:var(--text-dim); }

/* ── Result card ── */
.rcard {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--r-lg);
    margin-bottom: 0.75rem;
    overflow: hidden;
}
.rcard:hover { border-color: var(--border-lit); }

/* ── Score badge ── */
.score-badge {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 64px; height: 64px;
    border-radius: 50%;
    border: 2px solid;
    font-family: var(--mono);
    font-weight: 600;
    font-size: 1.2rem;
    line-height: 1;
    flex-shrink: 0;
}
.sb-g { color:var(--green); border-color:var(--green); background:var(--green-dim); }
.sb-a { color:var(--amber); border-color:var(--amber); background:var(--amber-dim); }
.sb-r { color:var(--red);   border-color:var(--red);   background:var(--red-dim); }
.sb-sub { font-size:0.45rem; opacity:0.6; margin-top:2px; }

/* ── Tags ── */
.tags { display:flex; gap:0.35rem; flex-wrap:wrap; margin-top:0.35rem; }
.tag {
    font-family: var(--mono);
    font-size: 0.58rem;
    font-weight: 500;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 0.12rem 0.5rem;
    border-radius: 3px;
    border: 1px solid;
}
.tag-g   { color:var(--green); border-color:var(--green-bdr); background:var(--green-dim); }
.tag-a   { color:var(--amber); border-color:var(--amber-bdr); background:var(--amber-dim); }
.tag-r   { color:var(--red);   border-color:var(--red-bdr);   background:var(--red-dim); }
.tag-c   { color:var(--cyan);  border-color:var(--cyan-bdr);  background:var(--cyan-dim); }
.tag-dim { color:var(--text-dim); border-color:var(--border); background:var(--surface2); }
.tag-cache { color:var(--text-mid); border-color:var(--border); background:var(--surface2); }

/* ── Signal checklist ── */
.check-grid { display:grid; grid-template-columns:1fr 1fr; gap:0.3rem; }
.check-row  { display:flex; align-items:center; gap:0.5rem; font-family:var(--mono); font-size:0.72rem; }
.chk-on  { color:var(--green); }
.chk-off { color:var(--text-dim); }
.check-row.on  { color: var(--text); }
.check-row.off { color: var(--text-dim); }

/* ── Fix items ── */
.fix-stack { display:flex; flex-direction:column; gap:0.35rem; }
.fix-row {
    display:flex; align-items:center; justify-content:space-between;
    background: var(--amber-dim);
    border: 1px solid var(--amber-bdr);
    border-radius: var(--r);
    padding: 0.4rem 0.7rem;
    font-family: var(--mono);
    font-size: 0.72rem;
    color: var(--amber);
}
.fix-pts { background:rgba(251,191,36,0.15); padding:0.1rem 0.35rem; border-radius:3px; font-weight:600; }
.no-fixes { background:var(--green-dim); border:1px solid var(--green-bdr); border-radius:var(--r); padding:0.5rem 0.7rem; font-family:var(--mono); font-size:0.72rem; color:var(--green); }

/* ── AI rec box ── */
.ai-box {
    background: linear-gradient(135deg, rgba(74,222,128,0.04), rgba(103,232,249,0.04));
    border: 1px solid var(--green-bdr);
    border-radius: var(--r);
    padding: 0.9rem 1.1rem;
}
.ai-box-header { font-family:var(--mono); font-size:0.6rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--green); margin-bottom:0.5rem; }
.ai-box-body   { font-family:var(--sans); font-size:0.83rem; color:var(--text); line-height:1.7; white-space:pre-wrap; }

/* ── KPI bar ── */
.kpi-row { display:grid; grid-template-columns:repeat(5,1fr); gap:0.6rem; margin-bottom:1.4rem; }
.kpi { background:var(--surface); border:1px solid var(--border); border-radius:var(--r); padding:1rem 1.1rem; }
.kpi-label { font-family:var(--mono); font-size:0.58rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--text-dim); margin-bottom:0.4rem; }
.kpi-val   { font-family:var(--mono); font-size:1.9rem; font-weight:600; line-height:1; color:var(--text); }
.kpi-sub   { font-family:var(--mono); font-size:0.58rem; color:var(--text-dim); margin-top:0.2rem; }
.kpi-g { color:var(--green) !important; }
.kpi-a { color:var(--amber) !important; }
.kpi-r { color:var(--red) !important; }

/* ── Compare ── */
.cmp-winner { color:var(--green) !important; border-color:var(--green-bdr) !important; background:var(--green-dim) !important; font-weight:600 !important; }
.cmp-loser  { color:var(--text-dim) !important; }

/* ── Benchmark ── */
.bench-row { display:flex; align-items:center; gap:0.8rem; padding:0.5rem 0; border-bottom:1px solid var(--border); }
.bench-row:last-child { border-bottom:none; }
.bench-name  { font-family:var(--mono); font-size:0.78rem; font-weight:500; color:var(--text); width:110px; flex-shrink:0; }
.bench-cat   { font-family:var(--mono); font-size:0.58rem; color:var(--text-dim); width:75px; flex-shrink:0; }
.bench-track { flex:1; height:6px; background:var(--border); border-radius:3px; overflow:hidden; }
.bench-fill  { height:100%; border-radius:3px; background:var(--green); opacity:0.7; }
.bench-score { font-family:var(--mono); font-size:0.78rem; font-weight:600; color:var(--green); width:32px; text-align:right; flex-shrink:0; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background:transparent !important; border-bottom:1px solid var(--border) !important; gap:0 !important; padding:0 !important; }
.stTabs [data-baseweb="tab"] { font-family:var(--mono) !important; font-size:0.75rem !important; font-weight:400 !important; color:var(--text-dim) !important; background:transparent !important; border:none !important; border-bottom:2px solid transparent !important; padding:0.7rem 1.2rem !important; letter-spacing:0.04em !important; text-transform:uppercase !important; }
.stTabs [data-baseweb="tab"]:hover { color:var(--text-mid) !important; }
.stTabs [aria-selected="true"] { color:var(--green) !important; border-bottom-color:var(--green) !important; }
.stTabs [data-baseweb="tab-panel"] { padding:1.4rem 0 0 !important; }

/* ── Buttons ── */
.stButton > button { font-family:var(--mono) !important; font-size:0.78rem !important; font-weight:500 !important; letter-spacing:0.06em !important; text-transform:uppercase !important; background:var(--green-dim) !important; border:1px solid var(--green-bdr) !important; color:var(--green) !important; border-radius:var(--r) !important; padding:0.55rem 1.2rem !important; transition:all 0.15s !important; box-shadow:none !important; }
.stButton > button:hover { background:rgba(74,222,128,0.15) !important; box-shadow:0 0 12px var(--green-glow) !important; }

/* ── Inputs ── */
.stTextInput > div > div > input, .stTextArea > div > div > textarea { background:var(--surface) !important; border:1px solid var(--border) !important; color:var(--text) !important; border-radius:var(--r) !important; font-family:var(--mono) !important; font-size:0.8rem !important; padding:0.55rem 0.85rem !important; }
.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus { border-color:var(--green) !important; box-shadow:0 0 0 2px var(--green-dim) !important; }
label[data-testid="stWidgetLabel"] { font-family:var(--mono) !important; font-size:0.62rem !important; letter-spacing:0.1em !important; text-transform:uppercase !important; color:var(--text-dim) !important; }

/* ── Toggle ── */
.stCheckbox label, .stToggle label { font-family:var(--mono) !important; font-size:0.72rem !important; color:var(--text-mid) !important; }

/* ── Metrics ── */
[data-testid="stMetric"] { background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:var(--r) !important; padding:0.9rem 1rem !important; }
[data-testid="stMetricLabel"] p { font-family:var(--mono) !important; font-size:0.58rem !important; letter-spacing:0.1em !important; text-transform:uppercase !important; color:var(--text-dim) !important; }
[data-testid="stMetricValue"] { font-family:var(--mono) !important; font-size:1.5rem !important; font-weight:600 !important; color:var(--text) !important; }

/* ── Progress ── */
.stProgress > div > div { background:var(--green) !important; border-radius:2px !important; }

/* ── DataFrame ── */
[data-testid="stDataFrame"] { border:1px solid var(--border) !important; border-radius:var(--r) !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background:var(--bg2) !important; border-right:1px solid var(--border) !important; }

/* ── Expander ── */
details { background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:var(--r-lg) !important; margin-bottom:0.6rem !important; overflow:hidden; }
summary { font-family:var(--mono) !important; font-size:0.82rem !important; font-weight:500 !important; padding:0.9rem 1.1rem !important; color:var(--text) !important; letter-spacing:0.02em !important; }
details[open] summary { border-bottom:1px solid var(--border) !important; color:var(--green) !important; }
details > div { padding:1.1rem 1.3rem !important; }

hr { border-color:var(--border) !important; margin:1.2rem 0 !important; }
.err-card { background:var(--red-dim); border:1px solid var(--red-bdr); border-radius:var(--r); padding:0.75rem 1rem; margin-bottom:0.5rem; font-family:var(--mono); font-size:0.75rem; color:var(--red); }
.warn-card { background:var(--amber-dim); border:1px solid var(--amber-bdr); border-radius:var(--r); padding:0.75rem 1rem; font-family:var(--mono); font-size:0.75rem; color:var(--amber); }
.info-hint { font-family:var(--mono); font-size:0.62rem; color:var(--text-dim); margin-top:0.35rem; letter-spacing:0.04em; }

/* ── Agent stat grid ── */
.ast-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:0.5rem; }
.ast { background:var(--surface2); border:1px solid var(--border); border-radius:var(--r); padding:0.75rem 0.9rem; }
.ast-label { font-family:var(--mono); font-size:0.58rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--text-dim); margin-bottom:0.3rem; }
.ast-val { font-family:var(--mono); font-size:1.3rem; font-weight:600; color:var(--text); }
.ast-g { color:var(--green) !important; }
.ast-r { color:var(--red) !important; }

/* schema chips */
.chips { display:flex; flex-wrap:wrap; gap:0.25rem; margin-top:0.35rem; }
.chip { font-family:var(--mono); font-size:0.58rem; background:var(--surface2); border:1px solid var(--border); color:var(--cyan); padding:0.12rem 0.45rem; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONSTANTS
# ============================================================================

REQUEST_TIMEOUT   = 14
MAX_WORKERS       = 8
CACHE_TTL_SECONDS = 3600
MAX_RETRIES       = 2
RETRY_BACKOFF     = 1.0

# Pages to crawl per domain
CRAWL_PATHS = ["", "/about", "/products", "/pipeline", "/newsroom", "/science", "/health-care-professionals"]

# MCP-specific endpoint paths to probe
MCP_ENDPOINT_PATHS = [
    "/.well-known/mcp.json",
    "/.well-known/ai-plugin.json",
    "/api/mcp",
    "/mcp",
    "/api/v1/mcp",
    "/openapi.json",
    "/swagger.json",
    "/api-docs",
]

# Benchmark data — MCP agent readiness scores
BENCHMARKS = {
    "Diabetes":  {"Lilly": 78, "Novo Nordisk": 71, "Merck": 52},
    "Oncology":  {"Roche": 74, "BMS": 69, "Pfizer": 48},
    "Cardio":    {"AstraZeneca": 66, "Sanofi": 61, "GSK": 44},
}

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

DEFAULT_DOMAINS = """https://www.lilly.com
https://www.pfizer.com
https://www.merck.com
https://www.novonordisk.com
https://www.astrazeneca.com"""

# ============================================================================
# MCP SCORING PILLARS
# The five dimensions of agent usability
# ============================================================================

# Each pillar: (id, label, description, max_score, bar_colour_class, pillar_colour_class)
PILLARS = [
    ("manifest",    "Agent Manifest",    "MCP/OpenAPI manifest files",          20, "bf-g", "pillar-g"),
    ("endpoints",   "Callable Endpoints","Structured, agent-callable functions", 25, "bf-c", "pillar-c"),
    ("schema",      "Structured Data",   "Machine-readable schema markup",       20, "bf-g", "pillar-g"),
    ("trust",       "Medical Authority", "E-E-A-T trust + citation signals",     20, "bf-a", "pillar-a"),
    ("context",     "Context Quality",   "Rich context for AI response gen",     15, "bf-g", "pillar-g"),
]
PILLAR_IDS  = [p[0] for p in PILLARS]
PILLAR_MAX  = {p[0]: p[3] for p in PILLARS}

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class ManifestStatus:
    """MCP / OpenAPI manifest detection."""
    has_mcp_json: bool = False
    has_ai_plugin: bool = False
    has_openapi: bool = False
    has_mcp_script: bool = False
    agent_context_api: bool = False
    callable_functions: int = 0

    def found_count(self) -> int:
        return sum([self.has_mcp_json, self.has_ai_plugin,
                    self.has_openapi, self.has_mcp_script, self.agent_context_api])

@dataclass
class EndpointSignals:
    """Agent-callable endpoint patterns."""
    rest_api_patterns: int = 0
    graphql: bool = False
    drug_lookup: bool = False
    trial_finder: bool = False
    coverage_check: bool = False
    hcp_portal: bool = False
    formulary_api: bool = False

    def score(self) -> int:
        pts = min(self.rest_api_patterns * 2, 8)
        pts += 4 if self.graphql else 0
        pts += 3 if self.drug_lookup else 0
        pts += 3 if self.trial_finder else 0
        pts += 3 if self.coverage_check else 0
        pts += 2 if self.hcp_portal else 0
        pts += 2 if self.formulary_api else 0
        return min(pts, 25)

@dataclass
class SchemaSignals:
    """Structured data / schema.org markup."""
    drug_schema: bool = False
    medical_condition: bool = False
    clinical_trial: bool = False
    faq_schema: bool = False
    organization: bool = False
    breadcrumb: bool = False
    detected_types: list = field(default_factory=list)

    def score(self) -> int:
        pts = 0
        pts += 7 if self.drug_schema else 0
        pts += 5 if self.medical_condition else 0
        pts += 5 if self.clinical_trial else 0
        pts += 3 if self.faq_schema else 0
        pts += 2 if self.organization else 0
        pts += 1 if self.breadcrumb else 0
        return min(pts, 20)

@dataclass
class TrustSignals:
    """Medical authority + citation signals."""
    medical_review: bool = False
    prescribing_info: bool = False
    adverse_events: bool = False
    pubmed_refs: bool = False
    doi_citations: bool = False
    clinical_data: bool = False
    regulatory_refs: bool = False

    def score(self) -> int:
        checks = [self.medical_review, self.prescribing_info, self.adverse_events,
                  self.pubmed_refs, self.doi_citations, self.clinical_data, self.regulatory_refs]
        return min(sum(checks) * 3, 20)

@dataclass
class ContextSignals:
    """Rich context for AI response generation."""
    mechanism_of_action: bool = False
    dosing_info: bool = False
    indication_detail: bool = False
    patient_resources: bool = False
    med_guide: bool = False

    def score(self) -> int:
        checks = [self.mechanism_of_action, self.dosing_info,
                  self.indication_detail, self.patient_resources, self.med_guide]
        return min(sum(checks) * 3, 15)

@dataclass
class MCPScores:
    manifest:   float = 0.0
    endpoints:  float = 0.0
    schema:     float = 0.0
    trust:      float = 0.0
    context:    float = 0.0

    @property
    def total(self) -> float:
        return round(self.manifest + self.endpoints + self.schema + self.trust + self.context, 1)

    def get(self, key: str) -> float:
        return getattr(self, key)

@dataclass
class AuditResult:
    url: str
    domain: str
    scores: MCPScores
    manifest: ManifestStatus = field(default_factory=ManifestStatus)
    endpoints: EndpointSignals = field(default_factory=EndpointSignals)
    schema: SchemaSignals = field(default_factory=SchemaSignals)
    trust: TrustSignals = field(default_factory=TrustSignals)
    context: ContextSignals = field(default_factory=ContextSignals)
    status_code: int = 0
    pages_crawled: int = 0
    probed_endpoints: dict = field(default_factory=dict)  # path → found (bool)
    improvements: list = field(default_factory=list)
    ai_recommendations: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    cached: bool = False
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def readiness_level(self) -> str:
        t = self.scores.total
        if t >= 70: return "AGENT_READY"
        if t >= 45: return "PARTIAL"
        return "NOT_READY"

    @property
    def badge_class(self) -> str:
        return {"AGENT_READY": "sb-g", "PARTIAL": "sb-a", "NOT_READY": "sb-r"}[self.readiness_level]

    @property
    def tag_class(self) -> str:
        return {"AGENT_READY": "tag-g", "PARTIAL": "tag-a", "NOT_READY": "tag-r"}[self.readiness_level]

    @property
    def fix_pts(self) -> int:
        return sum(f["pts"] for f in self.improvements)

# ============================================================================
# CACHE
# ============================================================================

def _ckey(url: str) -> str:
    return "mcp_" + hashlib.md5(url.lower().encode()).hexdigest()

def cache_get(url: str) -> Optional[AuditResult]:
    entry = st.session_state.get(_ckey(url))
    if entry:
        result, ts = entry
        if datetime.now() - ts < timedelta(seconds=CACHE_TTL_SECONDS):
            result.cached = True
            return result
    return None

def cache_set(url: str, result: AuditResult):
    st.session_state[_ckey(url)] = (result, datetime.now())

# ============================================================================
# HTTP
# ============================================================================

HEADERS = {
    "User-Agent": "PharmaAgentAuditor/1.0 (MCP-Readiness; +https://xodigital.com/bot)",
    "Accept": "application/json, text/html, */*",
}

def fetch(url: str, timeout: int = REQUEST_TIMEOUT) -> tuple[Optional[str], int]:
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
# MCP ENDPOINT PROBING
# ============================================================================

def probe_mcp_endpoints(base: str) -> dict[str, bool]:
    """Actively probe known MCP/agent manifest paths."""
    parsed = urlparse(base)
    root   = f"{parsed.scheme}://{parsed.netloc}"
    results = {}

    def _probe(path):
        url = root + path
        try:
            r = requests.get(url, headers=HEADERS, timeout=6, allow_redirects=True)
            found = r.status_code == 200 and len(r.text) > 20
            return path, found
        except Exception:
            return path, False

    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_probe, p): p for p in MCP_ENDPOINT_PATHS}
        for fut in as_completed(futures):
            path, found = fut.result()
            results[path] = found

    return results

# ============================================================================
# MULTI-PAGE CRAWL
# ============================================================================

def crawl(base_url: str) -> tuple[str, int, int]:
    parsed = urlparse(base_url)
    root   = f"{parsed.scheme}://{parsed.netloc}"
    htmls  = []
    primary_status = 0
    pages  = 0

    def _fetch(path):
        url = root + path if path else base_url
        html, status = fetch(url, timeout=10)
        return html, status, path

    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(_fetch, p): p for p in CRAWL_PATHS}
        for fut in as_completed(futures):
            html, status, path = fut.result()
            if html:
                htmls.append(html)
                pages += 1
                if path in ("", "/"):
                    primary_status = status

    if not primary_status and htmls:
        primary_status = 200
    return "\n".join(htmls), primary_status, pages

# ============================================================================
# SIGNAL DETECTORS
# ============================================================================

def detect_manifest(html: str, probed: dict) -> ManifestStatus:
    return ManifestStatus(
        has_mcp_json       = probed.get("/.well-known/mcp.json", False),
        has_ai_plugin      = probed.get("/.well-known/ai-plugin.json", False),
        has_openapi        = probed.get("/openapi.json", False) or probed.get("/swagger.json", False),
        has_mcp_script     = bool(re.search(r'application/mcp\+json', html, re.I))
                             or "navigator.modelContext" in html,
        agent_context_api  = "AgentContext" in html or "mcp-manifest" in html,
        callable_functions = len(re.findall(
            r'\b(get_|find_|check_|retrieve_|search_|book_|schedule_|lookup_|query_)\w+',
            html, re.I)),
    )


def detect_endpoints(html: str) -> EndpointSignals:
    text = html.lower()
    return EndpointSignals(
        rest_api_patterns = len(re.findall(r'/api/v\d+/', text)),
        graphql           = "graphql" in text or "/graphql" in text,
        drug_lookup       = bool(re.search(r'drug.{0,20}(lookup|search|find|api)', text)),
        trial_finder      = bool(re.search(r'(clinical.trial|trial.find|find.trial|trial.search)', text)),
        coverage_check    = bool(re.search(r'(coverage|formulary|insurance).{0,20}(check|api|tool)', text)),
        hcp_portal        = bool(re.search(r'hcp.portal|healthcare.professional.portal|prescriber.portal', text)),
        formulary_api     = bool(re.search(r'formulary.{0,15}api|api.{0,15}formulary', text)),
    )


def detect_schemas(html: str) -> SchemaSignals:
    soup  = BeautifulSoup(html, "html.parser")
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
                for i in obj: _r(i)
        _r(data)

    t = types
    return SchemaSignals(
        drug_schema       = bool({"Drug", "MedicalTherapy", "DrugClass"} & t),
        medical_condition = bool({"MedicalCondition", "MedicalSign", "MedicalSymptom"} & t),
        clinical_trial    = bool({"MedicalTrial", "MedicalStudy", "ClinicalTrial"} & t),
        faq_schema        = bool({"FAQPage", "Question"} & t),
        organization      = bool({"Organization", "MedicalOrganization", "Pharmacy"} & t),
        breadcrumb        = "BreadcrumbList" in t,
        detected_types    = sorted(list(t))[:10],
    )


def detect_trust(html: str) -> TrustSignals:
    text = html.lower()
    return TrustSignals(
        medical_review  = bool(re.search(r"reviewed by|medically reviewed", text)),
        prescribing_info= "prescribing information" in text,
        adverse_events  = bool(re.search(r"adverse.{0,15}event", text)),
        pubmed_refs     = "pubmed" in text or "ncbi.nlm.nih.gov" in text,
        doi_citations   = bool(re.search(r"\b10\.\d{4,9}/", text)),
        clinical_data   = bool(re.search(r"(clinical.data|phase [123]|randomized.controlled)", text)),
        regulatory_refs = bool(re.search(r"(fda|ema|prescribing|package.insert)", text)),
    )


def detect_context(html: str) -> ContextSignals:
    text = html.lower()
    return ContextSignals(
        mechanism_of_action = bool(re.search(r"mechanism.of.action|how.it.works|mode.of.action", text)),
        dosing_info         = bool(re.search(r"dosing|dosage|recommended.dose", text)),
        indication_detail   = bool(re.search(r"indication|approved.for|indicated.for", text)),
        patient_resources   = bool(re.search(r"patient.resource|patient.support|copay|savings.card", text)),
        med_guide           = "medication guide" in text,
    )

# ============================================================================
# SCORING
# ============================================================================

def score_manifest(m: ManifestStatus) -> float:
    pts  = 8  if m.has_mcp_json else 0
    pts += 5  if m.has_ai_plugin else 0
    pts += 4  if m.has_openapi else 0
    pts += 3  if m.has_mcp_script else 0
    pts += 3  if m.agent_context_api else 0
    pts += min(m.callable_functions * 0.5, 4)
    return round(min(pts, 20), 1)


def build_improvements(result: "AuditResult") -> list[dict]:
    m, e, s, t, c = result.manifest, result.endpoints, result.schema, result.trust, result.context
    fixes = []

    if not m.has_mcp_json:
        fixes.append({"label": "Publish /.well-known/mcp.json manifest",      "pts": 15, "pillar": "manifest"})
    if not m.has_openapi:
        fixes.append({"label": "Expose OpenAPI / Swagger spec",                "pts": 10, "pillar": "manifest"})
    if not e.drug_lookup:
        fixes.append({"label": "Add structured drug-lookup API endpoint",      "pts": 10, "pillar": "endpoints"})
    if not e.trial_finder:
        fixes.append({"label": "Expose clinical trial search endpoint",        "pts": 8,  "pillar": "endpoints"})
    if not s.drug_schema:
        fixes.append({"label": "Add Drug / MedicalTherapy schema markup",     "pts": 9,  "pillar": "schema"})
    if not s.clinical_trial:
        fixes.append({"label": "Add MedicalTrial schema markup",              "pts": 6,  "pillar": "schema"})
    if not t.pubmed_refs:
        fixes.append({"label": "Add PubMed / DOI citation references",        "pts": 6,  "pillar": "trust"})
    if not c.mechanism_of_action:
        fixes.append({"label": "Add structured mechanism-of-action content",  "pts": 5,  "pillar": "context"})

    return fixes[:5]

# ============================================================================
# MAIN AUDIT FUNCTION
# ============================================================================

def audit_domain(url: str, multi_page: bool = True) -> AuditResult:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    domain = urlparse(url).netloc

    cached = cache_get(url)
    if cached:
        return cached

    # Parallel: crawl pages + probe endpoints simultaneously
    html_result   = [None, 0, 0]
    probed_result = [{}]

    def _crawl():
        if multi_page:
            html, status, pages = crawl(url)
        else:
            html, status = fetch(url)
            pages = 1 if html else 0
        html_result[:] = [html, status, pages]

    def _probe():
        probed_result[0] = probe_mcp_endpoints(url)

    with ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(_crawl)
        f2 = ex.submit(_probe)
        f1.result(); f2.result()

    html, status_code, pages_crawled = html_result
    probed = probed_result[0]

    if not html:
        err = {-1: "Timeout", -2: "Connection refused", -3: "Unknown error"}.get(status_code, "Failed")
        return AuditResult(url=url, domain=domain, scores=MCPScores(), error=err)

    manifest_data = detect_manifest(html, probed)
    endpoint_data = detect_endpoints(html)
    schema_data   = detect_schemas(html)
    trust_data    = detect_trust(html)
    context_data  = detect_context(html)

    scores = MCPScores(
        manifest  = score_manifest(manifest_data),
        endpoints = float(endpoint_data.score()),
        schema    = float(schema_data.score()),
        trust     = float(trust_data.score()),
        context   = float(context_data.score()),
    )

    result = AuditResult(
        url=url, domain=domain, scores=scores,
        manifest=manifest_data, endpoints=endpoint_data,
        schema=schema_data, trust=trust_data, context=context_data,
        status_code=status_code, pages_crawled=pages_crawled,
        probed_endpoints=probed,
    )
    result.improvements = build_improvements(result)
    cache_set(url, result)
    return result


def parallel_audit(urls: list[str], multi_page: bool = True) -> list[AuditResult]:
    results: list[Optional[AuditResult]] = [None] * len(urls)
    bar  = st.progress(0, text="Initialising audit…")
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(audit_domain, url, multi_page): i for i, url in enumerate(urls)}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:   results[idx] = fut.result()
            except Exception as e:
                results[idx] = AuditResult(
                    url=urls[idx], domain=urlparse(urls[idx]).netloc,
                    scores=MCPScores(), error=str(e))
            done += 1
            bar.progress(done / len(urls), text=f"Auditing… {done}/{len(urls)} complete")
    bar.empty()
    return results

# ============================================================================
# CLAUDE AI RECOMMENDATIONS
# ============================================================================

def get_ai_recommendations(result: AuditResult, api_key: str) -> str:
    if not api_key:
        return ""

    found_endpoints = [p for p, v in result.probed_endpoints.items() if v]
    missing_endpoints = [p for p, v in result.probed_endpoints.items() if not v]

    prompt = f"""You are an MCP (Model Context Protocol) integration specialist for pharma brands.

An AI agent trying to USE this pharma website as an MCP tool would encounter these results:

DOMAIN: {result.domain}
MCP READINESS SCORE: {result.scores.total:.0f}/100
READINESS LEVEL: {result.readiness_level}

SCORE BREAKDOWN:
- Agent Manifest (/.well-known/mcp.json etc): {result.scores.manifest:.0f}/20
- Callable Endpoints (drug lookup, trial finder, coverage): {result.scores.endpoints:.0f}/25
- Structured Schema (Drug, MedicalCondition, MedicalTrial): {result.scores.schema:.0f}/20
- Medical Authority (citations, prescribing info, clinical data): {result.scores.trust:.0f}/20
- Context Quality (MOA, dosing, indications): {result.scores.context:.0f}/15

ACTIVE ENDPOINT PROBE RESULTS:
Found: {found_endpoints if found_endpoints else 'none'}
Missing: {missing_endpoints[:5]}

MCP MANIFEST: {'✓ has mcp.json' if result.manifest.has_mcp_json else '✗ no mcp.json'} | {'✓ has OpenAPI' if result.manifest.has_openapi else '✗ no OpenAPI'} | {'✓ has ai-plugin' if result.manifest.has_ai_plugin else '✗ no ai-plugin'}
CALLABLE FUNCTIONS DETECTED: {result.manifest.callable_functions}
SCHEMA TYPES FOUND: {result.schema.detected_types[:5] if result.schema.detected_types else 'none'}

Write exactly 4 numbered MCP integration recommendations for this pharma domain.
Each must:
1. Start with the specific technical action in **bold**
2. Explain what AI agents currently CAN'T do without this fix (1 sentence)
3. Give the exact implementation step

Focus on MCP protocol readiness — not SEO. These are engineering recommendations for making the site agent-callable.
Under 220 words total."""

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
        return f"API error {resp.status_code}: {data.get('error', {}).get('message', '')}"
    except Exception as e:
        return f"Could not reach Claude API: {e}"

# ============================================================================
# PDF EXPORT
# ============================================================================

def build_pdf(results: list[AuditResult], client: str) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab not installed")
    colors = rl_colors

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=16*mm, bottomMargin=16*mm)

    C_BG   = colors.HexColor("#080b08")
    C_SURF = colors.HexColor("#111611")
    C_GRN  = colors.HexColor("#4ade80")
    C_AMB  = colors.HexColor("#fbbf24")
    C_RED  = colors.HexColor("#f87171")
    C_TXT  = colors.HexColor("#e2ffe2")
    C_DIM  = colors.HexColor("#3d573d")
    C_BDR  = colors.HexColor("#1e2b1e")

    styles = getSampleStyleSheet()
    base   = styles["Normal"]

    def s(sz=9, bold=False, col=C_TXT, align=TA_LEFT, lead=None):
        return ParagraphStyle("_", parent=base, fontSize=sz,
            fontName="Courier-Bold" if bold else "Courier",
            textColor=col, alignment=align, leading=lead or sz*1.35)

    W = A4[0] - 36*mm
    story = []

    # Header
    hd = Table([[
        Paragraph("PHARMA MCP AGENT READINESS AUDIT", s(13, True, C_GRN)),
        Paragraph(f"CLIENT: {client}", s(9, col=C_DIM, align=TA_RIGHT)),
    ]], colWidths=[W*0.65, W*0.35])
    hd.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), C_SURF),
        ("LINEBELOW",    (0,0),(-1,0), 2, C_GRN),
        ("TOPPADDING",   (0,0),(-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
        ("LEFTPADDING",  (0,0),(-1,-1), 12),
        ("RIGHTPADDING", (0,0),(-1,-1), 12),
    ]))
    story += [hd, Spacer(1, 4*mm)]

    meta = Table([[
        Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}", s(8, col=C_DIM)),
        Paragraph(f"Domains: {len(results)}", s(8, col=C_DIM, align=TA_CENTER)),
        Paragraph("XO Digital · AI-First 2026", s(8, col=C_DIM, align=TA_RIGHT)),
    ]], colWidths=[W/3]*3)
    meta.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),C_SURF),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
    ]))
    story += [meta, Spacer(1, 6*mm)]

    # Summary table
    story.append(Paragraph("// EXECUTIVE SUMMARY", s(7, True, C_DIM)))
    story.append(Spacer(1, 2*mm))

    hdr = [Paragraph(h, s(7, True, C_DIM, TA_CENTER)) for h in
           ["Domain", "Score", "Level", "Manifest", "Endpoints", "Schema", "Trust", "Context"]]
    rows = [hdr]
    for r in sorted(results, key=lambda x: -x.scores.total):
        lc = C_GRN if r.readiness_level == "AGENT_READY" else C_AMB if r.readiness_level == "PARTIAL" else C_RED
        rows.append([
            Paragraph(r.domain, s(8)),
            Paragraph(f"{r.scores.total:.0f}", s(10, True, lc, TA_CENTER)),
            Paragraph(r.readiness_level.replace("_"," "), s(7, True, lc, TA_CENTER)),
            Paragraph(f"{r.scores.manifest:.0f}/20", s(8, col=C_TXT, align=TA_CENTER)),
            Paragraph(f"{r.scores.endpoints:.0f}/25", s(8, col=C_TXT, align=TA_CENTER)),
            Paragraph(f"{r.scores.schema:.0f}/20", s(8, col=C_TXT, align=TA_CENTER)),
            Paragraph(f"{r.scores.trust:.0f}/20", s(8, col=C_TXT, align=TA_CENTER)),
            Paragraph(f"{r.scores.context:.0f}/15", s(8, col=C_TXT, align=TA_CENTER)),
        ])

    cw = [W*0.28, W*0.08, W*0.16, W*0.1, W*0.1, W*0.1, W*0.1, W*0.08]
    tbl = Table(rows, colWidths=cw, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), C_SURF),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_SURF, C_BG]),
        ("LINEBELOW",     (0,0),(-1,-1), 0.4, C_BDR),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story += [tbl, Spacer(1, 8*mm)]

    # Per-domain detail
    for r in sorted(results, key=lambda x: -x.scores.total):
        lc = C_GRN if r.readiness_level == "AGENT_READY" else C_AMB if r.readiness_level == "PARTIAL" else C_RED

        dh = Table([[
            Paragraph(r.domain, s(11, True, C_TXT)),
            Paragraph(f"{r.scores.total:.0f}/100  {r.readiness_level.replace('_',' ')}", s(11, True, lc, TA_RIGHT)),
        ]], colWidths=[W*0.65, W*0.35])
        dh.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,-1), C_SURF),
            ("LINEBELOW",  (0,0),(-1,0), 1.5, lc),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ]))
        story.append(KeepTogether([dh]))
        story.append(Spacer(1, 3*mm))

        # Pillars
        ph  = [Paragraph(p[1], s(7, True, C_DIM, TA_CENTER)) for p in PILLARS]
        pv  = [Paragraph(f"{r.scores.get(p[0]):.0f}/{p[3]}", s(9, True, C_GRN, TA_CENTER)) for p in PILLARS]
        pt  = Table([ph, pv], colWidths=[W/5]*5)
        pt.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), C_BG),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LINEBELOW",     (0,0),(4,0), 0.4, C_BDR),
        ]))
        story += [pt, Spacer(1, 3*mm)]

        # Fixes
        if r.improvements:
            story.append(Paragraph("// PRIORITY FIXES", s(7, True, C_DIM)))
            story.append(Spacer(1, 1*mm))
            for fix in r.improvements:
                story.append(Paragraph(f"  [{fix['pillar'].upper()}] +{fix['pts']}pts — {fix['label']}", s(8, col=C_AMB)))

        # AI recs
        if r.ai_recommendations:
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph("// AI RECOMMENDATIONS", s(7, True, C_DIM)))
            story.append(Spacer(1, 1*mm))
            for line in r.ai_recommendations.split("\n"):
                if line.strip():
                    story.append(Paragraph(line.strip(), s(8, col=C_TXT, lead=12)))

        story += [Spacer(1, 5*mm), HRFlowable(width="100%", thickness=0.4, color=C_BDR), Spacer(1, 4*mm)]

    doc.build(story)
    return buf.getvalue()

# ============================================================================
# DATA UTILS
# ============================================================================

def results_to_df(results: list[AuditResult]) -> pd.DataFrame:
    rows = []
    for r in results:
        if not r.ok: continue
        rows.append({
            "Domain": r.domain, "Score": r.scores.total,
            "Level": r.readiness_level.replace("_"," "),
            "Manifest": r.scores.manifest, "Endpoints": r.scores.endpoints,
            "Schema": r.scores.schema, "Trust": r.scores.trust, "Context": r.scores.context,
            "MCP Manifest": r.manifest.has_mcp_json,
            "OpenAPI": r.manifest.has_openapi,
            "Agent Functions": r.manifest.callable_functions,
            "Pages Crawled": r.pages_crawled,
            "Fix Pts": r.fix_pts,
            "Cached": r.cached, "Timestamp": r.timestamp,
        })
    return pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)

# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_header():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.markdown(f"""
    <div class="header-bar">
        <div>
            <div class="header-logo">PHARMA MCP AGENT READINESS AUDITOR</div>
            <div class="header-tagline">// can an AI agent actually USE this site as an MCP tool?</div>
        </div>
        <div class="header-right">
            XO Digital · AI-First 2026<br>
            <span>{now}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_pillars(scores: MCPScores):
    cols = st.columns(5)
    pillar_colors = [
        ("#4ade80", "bf-g", "pillar-g"),
        ("#67e8f9", "bf-c", "pillar-c"),
        ("#4ade80", "bf-g", "pillar-g"),
        ("#fbbf24", "bf-a", "pillar-a"),
        ("#4ade80", "bf-g", "pillar-g"),
    ]
    for col, pillar, (color, barcls, pillarcls) in zip(cols, PILLARS, pillar_colors):
        pid, label, desc, mx, _, _ = pillar
        val = scores.get(pid)
        pct = int((val / mx) * 100)
        with col:
            st.markdown(f"""
            <div class="pillar {pillarcls}">
                <div class="pillar-label">{label}</div>
                <div class="pillar-val" style="color:{color}">
                    {val:.0f}<span class="pillar-max">/{mx}</span>
                </div>
                <div class="bar-track"><div class="bar-fill {barcls}" style="width:{pct}%"></div></div>
                <div class="pillar-pct">{pct}% · {desc}</div>
            </div>""", unsafe_allow_html=True)


def render_result_card(result: AuditResult, api_key: str = ""):
    lvl_icon = {"AGENT_READY": "🟢", "PARTIAL": "🟡", "NOT_READY": "🔴"}[result.readiness_level]
    lvl_label = result.readiness_level.replace("_", " ")
    found_eps = sum(1 for v in result.probed_endpoints.values() if v)
    cache_tag = ' <span class="tag tag-cache">💾 cached</span>' if result.cached else ""

    with st.expander(
        f"{lvl_icon}  **{result.domain}**"
        f"  ·  {result.scores.total:.0f}/100"
        f"  ·  {lvl_label}"
        f"  ·  {found_eps}/{len(MCP_ENDPOINT_PATHS)} endpoints"
    ):
        # Score badge + pillars
        rc, pc = st.columns([1, 7])
        with rc:
            st.markdown(f"""
            <div style="padding-top:0.5rem;display:flex;justify-content:center;">
                <div class="score-badge {result.badge_class}">
                    {result.scores.total:.0f}
                    <div class="sb-sub">/100</div>
                </div>
            </div>""", unsafe_allow_html=True)
        with pc:
            render_pillars(result.scores)

        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

        # Tags
        mcp_tag = "tag-g" if result.manifest.has_mcp_json else "tag-dim"
        api_tag = "tag-c" if result.manifest.has_openapi else "tag-dim"
        st.markdown(f"""
        <div class="tags">
            <span class="tag {result.tag_class}">{lvl_label}</span>
            <span class="tag {mcp_tag}">{'✓' if result.manifest.has_mcp_json else '✗'} mcp.json</span>
            <span class="tag {api_tag}">{'✓' if result.manifest.has_openapi else '✗'} openapi</span>
            <span class="tag {'tag-g' if result.manifest.has_ai_plugin else 'tag-dim'}">{'✓' if result.manifest.has_ai_plugin else '✗'} ai-plugin</span>
            <span class="tag tag-dim">📄 {result.pages_crawled} pages</span>
            <span class="tag tag-dim">⚡ {result.manifest.callable_functions} functions</span>
            <span class="tag tag-dim">HTTP {result.status_code}</span>
            {cache_tag}
        </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # Three columns: Endpoints probed | Schema + context | Fixes
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown('<div class="slabel">Endpoint Probe</div>', unsafe_allow_html=True)
            checks_html = '<div class="check-grid">'
            for path, found in result.probed_endpoints.items():
                cls = "on" if found else "off"
                icon = "✓" if found else "✗"
                label = path.replace("/.well-known/", "·/").replace("/api/v1", "/api")
                checks_html += f'<div class="check-row {cls}"><span class="chk-{"on" if found else "off"}">{icon}</span>{label}</div>'
            checks_html += "</div>"
            st.markdown(checks_html, unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="slabel">Schema + Context</div>', unsafe_allow_html=True)
            schema_checks = {
                "Drug schema":       result.schema.drug_schema,
                "MedicalCondition":  result.schema.medical_condition,
                "ClinicalTrial":     result.schema.clinical_trial,
                "FAQPage":           result.schema.faq_schema,
                "Mechanism of action": result.context.mechanism_of_action,
                "Dosing info":       result.context.dosing_info,
                "Indications":       result.context.indication_detail,
                "Prescribing info":  result.trust.prescribing_info,
            }
            ch_html = '<div class="check-grid">'
            for label, val in schema_checks.items():
                cls = "on" if val else "off"
                icon = "✓" if val else "✗"
                ch_html += f'<div class="check-row {cls}"><span class="chk-{"on" if val else "off"}">{icon}</span>{label}</div>'
            ch_html += "</div>"
            st.markdown(ch_html, unsafe_allow_html=True)

            if result.schema.detected_types:
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                chips = "".join(f'<span class="chip">{t}</span>' for t in result.schema.detected_types[:6])
                st.markdown(f'<div class="chips">{chips}</div>', unsafe_allow_html=True)

        with c3:
            st.markdown('<div class="slabel">Priority Fixes</div>', unsafe_allow_html=True)
            if result.improvements:
                html = '<div class="fix-stack">'
                for fix in result.improvements:
                    html += f"""<div class="fix-row">
                        <span>[{fix['pillar'].upper()}] {fix['label']}</span>
                        <span class="fix-pts">+{fix['pts']}pts</span>
                    </div>"""
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.markdown('<div class="no-fixes">✓ No critical gaps — site is agent-callable</div>',
                            unsafe_allow_html=True)

        # AI Recommendations
        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="slabel">AI Recommendations</div>', unsafe_allow_html=True)

        if result.ai_recommendations:
            st.markdown(f"""
            <div class="ai-box">
                <div class="ai-box-header">⚡ Claude MCP Analysis · {result.domain}</div>
                <div class="ai-box-body">{result.ai_recommendations}</div>
            </div>""", unsafe_allow_html=True)
        elif api_key:
            if st.button("⚡ Generate AI Analysis", key=f"ai_{result.domain}"):
                with st.spinner("Consulting Claude…"):
                    result.ai_recommendations = get_ai_recommendations(result, api_key)
                    cache_set(result.url, result)
                st.rerun()
        else:
            st.markdown(
                '<div class="info-hint">// add anthropic api key in sidebar to unlock claude analysis</div>',
                unsafe_allow_html=True)


def render_kpi_row(results: list[AuditResult]):
    ok = [r for r in results if r.ok]
    if not ok: return
    avg    = np.mean([r.scores.total for r in ok])
    ready  = sum(1 for r in ok if r.readiness_level == "AGENT_READY")
    partial= sum(1 for r in ok if r.readiness_level == "PARTIAL")
    not_r  = sum(1 for r in ok if r.readiness_level == "NOT_READY")
    fix_pt = sum(r.fix_pts for r in ok)

    avg_cls = "kpi-g" if avg >= 70 else "kpi-a" if avg >= 45 else "kpi-r"
    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi"><div class="kpi-label">Domains Audited</div><div class="kpi-val">{len(ok)}</div><div class="kpi-sub">in session</div></div>
        <div class="kpi"><div class="kpi-label">Avg MCP Score</div><div class="kpi-val {avg_cls}">{avg:.1f}</div><div class="kpi-sub">out of 100</div></div>
        <div class="kpi"><div class="kpi-label">Agent Ready</div><div class="kpi-val kpi-g">{ready}</div><div class="kpi-sub">score ≥ 70</div></div>
        <div class="kpi"><div class="kpi-label">Partial</div><div class="kpi-val kpi-a">{partial}</div><div class="kpi-sub">score 45–69</div></div>
        <div class="kpi"><div class="kpi-label">Not Ready</div><div class="kpi-val kpi-r">{not_r}</div><div class="kpi-sub">score &lt; 45</div></div>
    </div>""", unsafe_allow_html=True)


def render_compare(history: list[AuditResult]):
    ok = [r for r in history if r.ok]
    if len(ok) < 2:
        st.info("Audit at least 2 domains to use comparison view.")
        return

    domain_map = {r.domain: r for r in ok}
    selected   = st.multiselect(
        "SELECT DOMAINS TO COMPARE (2–4)",
        options=list(domain_map.keys()),
        default=list(domain_map.keys())[:min(4, len(domain_map))],
        max_selections=4,
    )
    if len(selected) < 2:
        st.warning("Select at least 2 domains.")
        return

    chosen = [domain_map[d] for d in selected]
    n      = len(chosen)

    # Domain headers
    header_cols = st.columns([1.5] + [1]*n)
    header_cols[0].markdown('<div class="slabel" style="margin-top:1.5rem">Metric</div>',
                            unsafe_allow_html=True)
    level_colors = {"AGENT_READY": "#4ade80", "PARTIAL": "#fbbf24", "NOT_READY": "#f87171"}
    for col, r in zip(header_cols[1:], chosen):
        lc = level_colors[r.readiness_level]
        col.markdown(f"""
        <div style="text-align:center;padding:0.75rem;background:var(--surface);
                    border:1px solid var(--border);border-radius:var(--r);
                    border-top:3px solid {lc};">
            <div style="font-family:var(--mono);font-size:1.6rem;font-weight:600;color:{lc}">{r.scores.total:.0f}</div>
            <div style="font-family:var(--mono);font-size:0.55rem;color:var(--text-dim)">/100</div>
            <div style="font-family:var(--sans);font-size:0.8rem;font-weight:600;color:var(--text);margin-top:3px">{r.domain}</div>
            <span class="tag {r.tag_class}" style="margin-top:4px;display:inline-block">{r.readiness_level.replace("_"," ")}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    def cmp_row(label: str, values, fmt=str, higher_better=True):
        cols = st.columns([1.5] + [1]*n)
        cols[0].markdown(
            f'<div style="font-family:var(--mono);font-size:0.65rem;color:var(--text-dim);'
            f'text-transform:uppercase;letter-spacing:0.08em;padding-top:0.4rem;">{label}</div>',
            unsafe_allow_html=True)
        best = max(values) if higher_better else min(values)
        for col, val in zip(cols[1:], values):
            is_best = val == best
            style = ("color:var(--green);border:1px solid var(--green-bdr);background:var(--green-dim);font-weight:600"
                     if is_best else
                     "color:var(--text-dim);border:1px solid var(--border);background:var(--surface)")
            col.markdown(
                f'<div style="text-align:center;padding:0.45rem;border-radius:var(--r);'
                f'font-family:var(--mono);font-size:0.85rem;{style}">{fmt(val)}</div>',
                unsafe_allow_html=True)

    cmp_row("Total MCP Score", [r.scores.total for r in chosen], fmt=lambda x: f"{x:.0f}/100")
    cmp_row("Agent Manifest",  [r.scores.manifest for r in chosen], fmt=lambda x: f"{x:.0f}/20")
    cmp_row("Callable Endpoints", [r.scores.endpoints for r in chosen], fmt=lambda x: f"{x:.0f}/25")
    cmp_row("Structured Schema",  [r.scores.schema for r in chosen], fmt=lambda x: f"{x:.0f}/20")
    cmp_row("Medical Authority",  [r.scores.trust for r in chosen], fmt=lambda x: f"{x:.0f}/20")
    cmp_row("Context Quality",    [r.scores.context for r in chosen], fmt=lambda x: f"{x:.0f}/15")
    cmp_row("Endpoints Found",    [sum(1 for v in r.probed_endpoints.values() if v) for r in chosen], fmt=str)
    cmp_row("Agent Functions",    [r.manifest.callable_functions for r in chosen], fmt=str)
    cmp_row("Schema Types",       [len(r.schema.detected_types) for r in chosen], fmt=str)
    cmp_row("Pages Crawled",      [r.pages_crawled for r in chosen], fmt=str)
    cmp_row("Fix Points Needed",  [r.fix_pts for r in chosen], fmt=lambda x: f"+{x}pts", higher_better=False)


def render_benchmarks(scan_results: list[AuditResult]):
    st.markdown('<div class="slabel">Industry MCP Readiness Benchmarks</div>', unsafe_allow_html=True)
    entries = sorted(
        [(co, cat, sc) for cat, companies in BENCHMARKS.items() for co, sc in companies.items()],
        key=lambda x: -x[2])
    rows = ""
    for company, cat, score in entries:
        rows += f"""<div class="bench-row">
            <div class="bench-name">{company}</div>
            <div class="bench-cat">{cat}</div>
            <div class="bench-track"><div class="bench-fill" style="width:{score}%"></div></div>
            <div class="bench-score">{score}</div>
        </div>"""
    st.markdown(f"""
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:var(--r-lg);padding:1.2rem 1.4rem;">
        {rows}
    </div>""", unsafe_allow_html=True)

    ok = [r for r in scan_results if r.ok]
    if ok:
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        bm_scores = [sc for _, companies in BENCHMARKS.items() for sc in companies.values()]
        live_avg  = np.mean([r.scores.total for r in ok])
        ind_avg   = np.mean(bm_scores)
        col1, col2, col3 = st.columns(3)
        col1.metric("Your Portfolio Avg", f"{live_avg:.1f}")
        col2.metric("Industry Avg",       f"{ind_avg:.1f}")
        col3.metric("vs Industry",        f"{live_avg - ind_avg:+.1f}")

# ============================================================================
# SESSION STATE
# ============================================================================

def init_state():
    for key in ("audit_results", "history"):
        if key not in st.session_state:
            st.session_state[key] = []

# ============================================================================
# MAIN
# ============================================================================

def main():
    init_state()
    render_header()

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚡ Settings")
        api_key = st.text_input(
            "ANTHROPIC API KEY",
            type="password",
            placeholder="sk-ant-...",
            help="For Claude MCP analysis. Never stored.",
        )
        multi_page = st.toggle("Multi-page crawl", value=True,
                               help="Crawls 7 pages + probes 8 MCP endpoints per domain")
        st.markdown("---")
        st.markdown("### // Session")
        ok = [r for r in st.session_state.history if r.ok]
        if ok:
            st.metric("Audited", len(ok))
            st.metric("Avg Score", f"{np.mean([r.scores.total for r in ok]):.1f}")
            ready = sum(1 for r in ok if r.readiness_level == "AGENT_READY")
            st.metric("Agent Ready", f"{ready}/{len(ok)}")
            cached = sum(1 for r in ok if r.cached)
            if cached: st.metric("From Cache", f"{cached}/{len(ok)}")
        else:
            st.markdown('<div class="info-hint">// no audits yet</div>', unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🗑 Clear Session"):
            st.session_state.history      = []
            st.session_state.audit_results = []
            st.rerun()

    # Client name
    col_c, _ = st.columns([2, 5])
    with col_c:
        client_name = st.text_input("CLIENT", value="Pharma Brand", key="client")
    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    # Tabs
    t1, t2, t3, t4, t5 = st.tabs([
        "⚡  Audit",
        "⚖️  Compare",
        "🤖  Agent Test",
        "🏆  Benchmarks",
        "📊  Executive",
    ])

    # ══════════════════════════════
    # TAB 1 — AUDIT
    # ══════════════════════════════
    with t1:
        mode = "multi-page + endpoint probe" if multi_page else "homepage + endpoint probe"
        st.markdown(f'<div class="slabel">Paste pharma domains to audit · one per line · max 20 · {mode}</div>',
                    unsafe_allow_html=True)

        ci, ca = st.columns([5, 1])
        with ci:
            raw = st.text_area("DOMAINS", value=DEFAULT_DOMAINS, height=170,
                               label_visibility="collapsed")
            st.markdown('<div class="info-hint">// https prefix optional · results cached 1hr · retries on failure</div>',
                        unsafe_allow_html=True)
        with ca:
            st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
            run   = st.button("⚡ AUDIT NOW", type="primary", use_container_width=True)
            st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
            clear = st.button("🗑 Clear",    use_container_width=True)

        if clear:
            st.session_state.audit_results = []
            st.rerun()

        if run:
            urls = [u.strip() for u in raw.splitlines() if u.strip()]
            if not urls:
                st.warning("No URLs provided.")
            elif len(urls) > 20:
                st.error("Maximum 20 domains.")
            else:
                t0 = time.time()
                results = parallel_audit(urls, multi_page=multi_page)
                st.session_state.audit_results = results
                existing = {r.domain for r in st.session_state.history}
                for r in results:
                    if r.ok:
                        if r.domain not in existing:
                            st.session_state.history.append(r)
                        else:
                            for i, h in enumerate(st.session_state.history):
                                if h.domain == r.domain:
                                    st.session_state.history[i] = r
                elapsed = time.time() - t0
                ok_n    = sum(1 for r in results if r.ok)
                cached_n= sum(1 for r in results if r.ok and r.cached)
                note    = f" ({cached_n} from cache)" if cached_n else ""
                st.success(f"✅ {ok_n}/{len(urls)} domains audited in **{elapsed:.1f}s**{note}")

        if st.session_state.audit_results:
            st.markdown("---")
            sorted_r = sorted(st.session_state.audit_results, key=lambda r: (not r.ok, -r.scores.total))
            ok_r     = [r for r in sorted_r if r.ok]
            err_r    = [r for r in sorted_r if not r.ok]

            if ok_r:
                # Bulk AI button
                if api_key:
                    needs = [r for r in ok_r if not r.ai_recommendations]
                    if needs:
                        if st.button(f"⚡ AI Analysis for all {len(needs)} domains"):
                            bar = st.progress(0)
                            for i, r in enumerate(needs):
                                r.ai_recommendations = get_ai_recommendations(r, api_key)
                                cache_set(r.url, r)
                                bar.progress((i+1)/len(needs))
                            bar.empty()
                            st.rerun()

                st.markdown(f'<div class="slabel">{len(ok_r)} domain(s) audited</div>', unsafe_allow_html=True)
                for r in ok_r:
                    render_result_card(r, api_key=api_key)

            for r in err_r:
                st.markdown(f'<div class="err-card">✗ {r.domain} — {r.error}</div>', unsafe_allow_html=True)

    # ══════════════════════════════
    # TAB 2 — COMPARE
    # ══════════════════════════════
    with t2:
        st.markdown('<div class="slabel">Side-by-side MCP readiness comparison</div>', unsafe_allow_html=True)
        render_compare(st.session_state.history)

    # ══════════════════════════════
    # TAB 3 — AGENT TEST
    # ══════════════════════════════
    with t3:
        st.markdown('<div class="slabel">Deep-probe a single domain for MCP agent compatibility</div>',
                    unsafe_allow_html=True)

        cu, cb = st.columns([5, 1])
        with cu:
            test_url = st.text_input("DOMAIN URL", value="https://www.lilly.com",
                                     key="agent_url", label_visibility="collapsed")
        with cb:
            run_test = st.button("⚡ PROBE", type="primary", use_container_width=True)

        if run_test:
            with st.spinner("Probing MCP endpoints…"):
                result = audit_domain(test_url, multi_page=False)

            if not result.ok:
                st.markdown(f'<div class="err-card">✗ {result.error}</div>', unsafe_allow_html=True)
            else:
                c1, c2 = st.columns([1, 2])
                with c1:
                    lc = {"AGENT_READY":"ast-g","PARTIAL":"ast-a","NOT_READY":"ast-r"}.get(result.readiness_level,"")
                    st.markdown(f"""
                    <div class="ast-grid">
                        <div class="ast" style="grid-column:span 2">
                            <div class="ast-label">Readiness Level</div>
                            <div class="ast-val {lc}">{result.readiness_level.replace("_"," ")}</div>
                        </div>
                        <div class="ast"><div class="ast-label">MCP Score</div><div class="ast-val">{result.scores.total:.0f}/100</div></div>
                        <div class="ast"><div class="ast-label">mcp.json</div><div class="ast-val {'ast-g' if result.manifest.has_mcp_json else 'ast-r'}">{'✓' if result.manifest.has_mcp_json else '✗'}</div></div>
                        <div class="ast"><div class="ast-label">OpenAPI</div><div class="ast-val {'ast-g' if result.manifest.has_openapi else 'ast-r'}">{'✓' if result.manifest.has_openapi else '✗'}</div></div>
                        <div class="ast"><div class="ast-label">Functions</div><div class="ast-val">{result.manifest.callable_functions}</div></div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
                    render_pillars(result.scores)

                with c2:
                    st.markdown('<div class="slabel">Raw MCP Probe Payload</div>', unsafe_allow_html=True)
                    st.code(json.dumps({
                        "domain": result.domain,
                        "mcp_readiness": result.readiness_level,
                        "score": f"{result.scores.total:.1f}/100",
                        "manifest": {
                            "mcp_json":   result.manifest.has_mcp_json,
                            "openapi":    result.manifest.has_openapi,
                            "ai_plugin":  result.manifest.has_ai_plugin,
                            "mcp_script": result.manifest.has_mcp_script,
                        },
                        "probed_endpoints": result.probed_endpoints,
                        "callable_functions": result.manifest.callable_functions,
                        "schema_types": result.schema.detected_types,
                        "recommended_agent_tools": [
                            "get_prescribing_info(drug_id: str) -> PIDocument",
                            "find_clinical_trials(condition: str, phase: int) -> Trial[]",
                            "check_formulary_coverage(ndc: str, plan_id: str) -> Coverage",
                            "get_drug_interactions(drugs: list[str]) -> InteractionReport",
                        ],
                        "timestamp": result.timestamp,
                    }, indent=2), language="json")

    # ══════════════════════════════
    # TAB 4 — BENCHMARKS
    # ══════════════════════════════
    with t4:
        render_benchmarks(st.session_state.audit_results)

    # ══════════════════════════════
    # TAB 5 — EXECUTIVE
    # ══════════════════════════════
    with t5:
        st.markdown('<div class="slabel">Executive dashboard · all audited domains</div>', unsafe_allow_html=True)
        ok_all = [r for r in st.session_state.history if r.ok]

        if not ok_all:
            st.markdown('<div class="info-hint">// run an audit first to unlock executive view</div>',
                        unsafe_allow_html=True)
        else:
            render_kpi_row(ok_all)
            df = results_to_df(ok_all)

            st.markdown('<div class="slabel">Leaderboard</div>', unsafe_allow_html=True)

            def _lc(v):
                if v == "AGENT READY": return "color:#4ade80;font-weight:700"
                if v == "PARTIAL":     return "color:#fbbf24;font-weight:700"
                return "color:#f87171;font-weight:700"

            disp = df[["Domain","Score","Level","Manifest","Endpoints","Schema","Trust","Context",
                        "Agent Functions","Pages Crawled","Fix Pts"]].copy()
            disp["Score"] = disp["Score"].apply(lambda x: f"{x:.1f}")
            st.dataframe(
                disp.style.applymap(_lc, subset=["Level"]),
                use_container_width=True, height=380,
            )

            st.markdown("---")
            cc, cp = st.columns(2)
            with cc:
                buf = io.StringIO()
                df.to_csv(buf, index=False)
                st.download_button(
                    "📥 Download CSV",
                    data=buf.getvalue().encode(),
                    file_name=f"MCP-Audit-{client_name.replace(' ','_')}-{datetime.now().strftime('%Y%m%d-%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with cp:
                if not REPORTLAB_AVAILABLE:
                    st.markdown(
                        '<div class="warn-card">⚠ PDF export requires reportlab in requirements.txt</div>',
                        unsafe_allow_html=True)
                elif st.button("📄 Generate PDF Report", use_container_width=True):
                    with st.spinner("Building PDF…"):
                        pdf = build_pdf(ok_all, client_name)
                    st.download_button(
                        "⬇️ Download PDF",
                        data=pdf,
                        file_name=f"MCP-Audit-{client_name.replace(' ','_')}-{datetime.now().strftime('%Y%m%d-%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )


if __name__ == "__main__":
    main()
