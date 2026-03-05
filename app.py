"""
Pharma MCP Agent Readiness Auditor

The question this app answers:
  "Can an AI agent actually USE this pharma website as an MCP tool?"

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


st.set_page_config(
    page_title="Pharma MCP Auditor",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Fira+Code:wght@400;500&display=swap');

:root {
    --bg:          #0f1117;
    --surface:     #181c2a;
    --surface2:    #1f2438;
    --surface3:    #272c42;
    --border:      #2d3348;
    --border-lit:  #3a4060;
    --text:        #edf0fa;
    --text-mid:    #8891b0;
    --text-dim:    #4a5270;
    --blue:        #4f8ef7;
    --blue-dim:    rgba(79,142,247,0.13);
    --blue-bdr:    rgba(79,142,247,0.35);
    --green:       #34d399;
    --green-dim:   rgba(52,211,153,0.12);
    --green-bdr:   rgba(52,211,153,0.35);
    --amber:       #f59e0b;
    --amber-dim:   rgba(245,158,11,0.12);
    --amber-bdr:   rgba(245,158,11,0.35);
    --red:         #f87171;
    --red-dim:     rgba(248,113,113,0.12);
    --red-bdr:     rgba(248,113,113,0.35);
    --purple:      #a78bfa;
    --purple-dim:  rgba(167,139,250,0.12);
    --purple-bdr:  rgba(167,139,250,0.35);
    --teal:        #2dd4bf;
    --teal-dim:    rgba(45,212,191,0.12);
    --teal-bdr:    rgba(45,212,191,0.35);
    --sans: 'Plus Jakarta Sans', sans-serif;
    --mono: 'Fira Code', monospace;
    --r: 10px; --r-lg: 16px; --r-sm: 6px;
}
html, body, [class*="css"] { font-family: var(--sans) !important; background: var(--bg) !important; color: var(--text) !important; }
.main .block-container { padding: 0 2.2rem 5rem !important; max-width: 1400px !important; }

/* Hero */
.hero { background: linear-gradient(140deg,#141829 0%,#181e34 55%,#121726 100%); border-bottom: 1px solid var(--border); padding: 2.2rem 2.6rem 2rem; margin: 0 -2.2rem 2rem; position: relative; overflow: hidden; }
.hero::after { content: ''; position: absolute; top: -60px; right: -60px; width: 380px; height: 380px; background: radial-gradient(circle,rgba(79,142,247,0.07) 0%,transparent 65%); pointer-events: none; }
.hero-pill { display: inline-flex; align-items: center; gap: 0.4rem; background: var(--blue-dim); border: 1px solid var(--blue-bdr); border-radius: 20px; padding: 0.22rem 0.8rem; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase; color: var(--blue); margin-bottom: 0.9rem; }
.hero-title { font-size: 2.1rem; font-weight: 800; letter-spacing: -0.025em; color: var(--text); margin: 0 0 0.45rem; line-height: 1.15; }
.hero-title em { color: var(--blue); font-style: normal; }
.hero-sub { font-size: 0.95rem; color: var(--text-mid); margin: 0 0 1.4rem; max-width: 620px; line-height: 1.65; }
.fp-row { display: flex; gap: 0.45rem; flex-wrap: wrap; }
.fp { font-size: 0.72rem; font-weight: 600; padding: 0.22rem 0.75rem; border-radius: 20px; background: var(--surface2); border: 1px solid var(--border); color: var(--text-mid); }
.fp.on { color: var(--green); border-color: var(--green-bdr); background: var(--green-dim); }

/* Section heading */
.sec-h { display: flex; align-items: center; gap: 0.6rem; font-size: 0.7rem; font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-dim); margin-bottom: 0.9rem; }
.sec-h::after { content: ''; flex: 1; height: 1px; background: var(--border); }

/* Pillar cards */
.pc { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 1rem 1.1rem; position: relative; overflow: hidden; }
.pc::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; border-radius: var(--r) var(--r) 0 0; }
.pc-b::before { background: var(--blue); }
.pc-t::before { background: var(--teal); }
.pc-g::before { background: var(--green); }
.pc-a::before { background: var(--amber); }
.pc-p::before { background: var(--purple); }
.pc-icon { font-size: 1.25rem; margin-bottom: 0.35rem; }
.pc-name { font-size: 0.65rem; font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-dim); margin-bottom: 0.45rem; }
.pc-score { font-size: 1.65rem; font-weight: 800; line-height: 1; margin-bottom: 0.45rem; }
.pc-denom { font-size: 0.82rem; font-weight: 400; color: var(--text-dim); }
.pc-bar { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; margin-bottom: 0.3rem; }
.pc-fill { height: 100%; border-radius: 2px; }
.pf-b { background: var(--blue); } .pf-t { background: var(--teal); } .pf-g { background: var(--green); } .pf-a { background: var(--amber); } .pf-p { background: var(--purple); }
.pc-desc { font-size: 0.68rem; color: var(--text-dim); line-height: 1.4; }

/* Verdict badge */
.verdict { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.28rem 0.85rem; border-radius: 20px; font-size: 0.78rem; font-weight: 700; }
.vg { background: var(--green-dim); color: var(--green); border: 1px solid var(--green-bdr); }
.va { background: var(--amber-dim); color: var(--amber); border: 1px solid var(--amber-bdr); }
.vr { background: var(--red-dim);   color: var(--red);   border: 1px solid var(--red-bdr); }

/* Score ring */
.sr { width: 72px; height: 72px; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; font-weight: 800; font-size: 1.3rem; line-height: 1; border: 3px solid; flex-shrink: 0; }
.sr-g { color: var(--green); border-color: var(--green); background: var(--green-dim); }
.sr-a { color: var(--amber); border-color: var(--amber); background: var(--amber-dim); }
.sr-r { color: var(--red);   border-color: var(--red);   background: var(--red-dim); }
.sr-sub { font-size: 0.46rem; opacity: 0.6; margin-top: 2px; font-weight: 400; }

/* Check items */
.checks { display: flex; flex-direction: column; gap: 0.28rem; }
.chk { display: flex; align-items: center; gap: 0.6rem; padding: 0.42rem 0.65rem; border-radius: var(--r-sm); font-size: 0.82rem; }
.chk-pass { background: var(--green-dim); color: var(--text); }
.chk-fail { background: var(--surface2);  color: var(--text-dim); }
.chk-icon { font-size: 0.82rem; flex-shrink: 0; }

/* Probe results */
.probe-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.28rem; }
.probe { display: flex; align-items: center; gap: 0.45rem; padding: 0.38rem 0.55rem; border-radius: var(--r-sm); font-family: var(--mono); font-size: 0.66rem; }
.probe-y { background: var(--green-dim); color: var(--green); }
.probe-n { background: var(--surface2);  color: var(--text-dim); }

/* Fix list */
.fixes { display: flex; flex-direction: column; gap: 0.35rem; }
.fix { display: flex; align-items: flex-start; gap: 0.55rem; padding: 0.55rem 0.75rem; background: var(--amber-dim); border: 1px solid var(--amber-bdr); border-radius: var(--r-sm); font-size: 0.82rem; color: var(--text); }
.fix-n { font-family: var(--mono); font-size: 0.62rem; font-weight: 600; background: var(--amber-dim); color: var(--amber); border: 1px solid var(--amber-bdr); padding: 0.08rem 0.35rem; border-radius: 3px; flex-shrink: 0; margin-top: 1px; }
.fix-pts { font-family: var(--mono); font-size: 0.62rem; color: var(--amber); padding: 0.08rem 0.32rem; border-radius: 3px; background: var(--amber-dim); border: 1px solid var(--amber-bdr); flex-shrink: 0; white-space: nowrap; margin-left: auto; }
.fix-ok { background: var(--green-dim); border: 1px solid var(--green-bdr); border-radius: var(--r-sm); padding: 0.6rem 0.85rem; font-size: 0.85rem; color: var(--green); display: flex; align-items: center; gap: 0.5rem; }

/* AI recommendation box */
.ai-box { background: linear-gradient(135deg,var(--blue-dim),var(--purple-dim)); border: 1px solid var(--blue-bdr); border-radius: var(--r); padding: 1.1rem 1.3rem; }
.ai-lbl { font-size: 0.65rem; font-weight: 800; letter-spacing: 0.09em; text-transform: uppercase; color: var(--blue); margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem; }
.ai-body { font-size: 0.88rem; color: var(--text); line-height: 1.75; white-space: pre-wrap; }

/* KPI grid */
.kpi-grid { display: grid; grid-template-columns: repeat(5,1fr); gap: 0.65rem; margin-bottom: 1.5rem; }
.kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 1.1rem 1.2rem; }
.kpi-icon { font-size: 1.5rem; margin-bottom: 0.35rem; }
.kpi-lbl  { font-size: 0.65rem; font-weight: 800; letter-spacing: 0.09em; text-transform: uppercase; color: var(--text-dim); margin-bottom: 0.3rem; }
.kpi-val  { font-size: 2.1rem; font-weight: 800; line-height: 1; color: var(--text); }
.kpi-sub  { font-size: 0.7rem; color: var(--text-dim); margin-top: 0.2rem; }
.kg { color: var(--green) !important; } .ka { color: var(--amber) !important; } .kr { color: var(--red) !important; }

/* Schema chips */
.chips { display: flex; flex-wrap: wrap; gap: 0.28rem; margin-top: 0.4rem; }
.chip { font-family: var(--mono); font-size: 0.6rem; background: var(--surface3); border: 1px solid var(--border); color: var(--purple); padding: 0.12rem 0.48rem; border-radius: 3px; }

/* Compare */
.cmp-card { text-align: center; padding: 1rem; background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); border-top: 3px solid; }
.cmp-lbl  { font-size: 0.78rem; font-weight: 600; color: var(--text-mid); padding-top: 0.4rem; }
.cmp-cell { text-align: center; padding: 0.45rem; border-radius: var(--r-sm); font-size: 0.9rem; font-weight: 600; border: 1px solid; }
.cmp-w { background: var(--green-dim); color: var(--green); border-color: var(--green-bdr); }
.cmp-l { background: var(--surface2);  color: var(--text-dim); border-color: var(--border); }

/* Benchmarks */
.bench-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); padding: 1.3rem 1.5rem; }
.bench-row  { display: flex; align-items: center; gap: 0.9rem; padding: 0.55rem 0; border-bottom: 1px solid var(--border); }
.bench-row:last-child { border-bottom: none; }
.bench-name  { font-size: 0.88rem; font-weight: 700; color: var(--text); width: 115px; flex-shrink: 0; }
.bench-cat   { font-size: 0.68rem; color: var(--text-dim); width: 70px; flex-shrink: 0; }
.bench-track { flex: 1; height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }
.bench-fill  { height: 100%; border-radius: 4px; }
.bench-score { font-family: var(--mono); font-size: 0.85rem; font-weight: 600; width: 30px; text-align: right; flex-shrink: 0; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid var(--border) !important; gap: 0 !important; }
.stTabs [data-baseweb="tab"] { font-family: var(--sans) !important; font-size: 0.88rem !important; font-weight: 700 !important; color: var(--text-dim) !important; background: transparent !important; border: none !important; border-bottom: 2px solid transparent !important; padding: 0.72rem 1.3rem !important; }
.stTabs [data-baseweb="tab"]:hover { color: var(--text-mid) !important; }
.stTabs [aria-selected="true"] { color: var(--blue) !important; border-bottom-color: var(--blue) !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 1.5rem 0 0 !important; }

/* Buttons */
.stButton > button { font-family: var(--sans) !important; font-weight: 700 !important; font-size: 0.88rem !important; border-radius: var(--r-sm) !important; border: none !important; background: var(--blue) !important; color: #fff !important; padding: 0.6rem 1.4rem !important; box-shadow: 0 4px 14px rgba(79,142,247,0.3) !important; transition: all 0.15s !important; }
.stButton > button:hover { opacity: 0.88 !important; transform: translateY(-1px) !important; }

/* Inputs */
.stTextInput > div > div > input, .stTextArea > div > div > textarea { background: var(--surface2) !important; border: 1px solid var(--border) !important; color: var(--text) !important; border-radius: var(--r-sm) !important; font-size: 0.88rem !important; padding: 0.6rem 0.9rem !important; }
.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus { border-color: var(--blue) !important; box-shadow: 0 0 0 3px var(--blue-dim) !important; }
label[data-testid="stWidgetLabel"] { font-size: 0.72rem !important; font-weight: 700 !important; letter-spacing: 0.06em !important; text-transform: uppercase !important; color: var(--text-dim) !important; }

/* Metrics */
[data-testid="stMetric"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: var(--r) !important; padding: 1rem 1.1rem !important; }
[data-testid="stMetricLabel"] p { font-size: 0.65rem !important; font-weight: 800 !important; letter-spacing: 0.09em !important; text-transform: uppercase !important; color: var(--text-dim) !important; }
[data-testid="stMetricValue"] { font-size: 1.7rem !important; font-weight: 800 !important; color: var(--text) !important; }

/* Progress / DataFrame / Sidebar / Expander */
.stProgress > div > div { background: var(--blue) !important; border-radius: 3px !important; }
[data-testid="stDataFrame"] { border: 1px solid var(--border) !important; border-radius: var(--r) !important; }
section[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border) !important; }
details { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: var(--r-lg) !important; margin-bottom: 0.75rem !important; overflow: hidden; }
summary { font-family: var(--sans) !important; font-size: 0.95rem !important; font-weight: 700 !important; padding: 1rem 1.2rem !important; color: var(--text) !important; }
details[open] summary { border-bottom: 1px solid var(--border) !important; }
details > div { padding: 1.3rem 1.4rem !important; }
hr { border-color: var(--border) !important; margin: 1.4rem 0 !important; }

/* Utility */
.err-card  { background: var(--red-dim);   border: 1px solid var(--red-bdr);   border-radius: var(--r); padding: 0.8rem 1rem; margin-bottom: 0.5rem; font-size: 0.85rem; color: var(--red); }
.warn-card { background: var(--amber-dim); border: 1px solid var(--amber-bdr); border-radius: var(--r); padding: 0.8rem 1rem; font-size: 0.85rem; color: var(--amber); }
.hint { font-size: 0.78rem; color: var(--text-dim); margin-top: 0.35rem; }

/* Agent test stats */
.ast-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
.ast { background: var(--surface2); border: 1px solid var(--border); border-radius: var(--r-sm); padding: 0.8rem 0.95rem; }
.ast-lbl { font-size: 0.62rem; font-weight: 800; letter-spacing: 0.09em; text-transform: uppercase; color: var(--text-dim); margin-bottom: 0.3rem; }
.ast-val { font-size: 1.3rem; font-weight: 800; color: var(--text); }
.ast-g { color: var(--green) !important; } .ast-r { color: var(--red) !important; }
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


# ============================================================================
# UI COMPONENTS
# ============================================================================

PILLAR_UI = [
    ("manifest",  "📡", "Agent Manifest",     20, "pf-b", "pc-b", "mcp.json · OpenAPI · ai-plugin.json"),
    ("endpoints", "🔌", "Callable Endpoints", 25, "pf-t", "pc-t", "Drug lookup · trial finder · coverage API"),
    ("schema",    "🗂",  "Structured Data",   20, "pf-g", "pc-g", "Drug · MedicalCondition · Trial schemas"),
    ("trust",     "🏥", "Medical Authority",  20, "pf-a", "pc-a", "Citations · prescribing info · clinical data"),
    ("context",   "📖", "Context Quality",    15, "pf-p", "pc-p", "MOA · dosing · indications for agents"),
]
VERDICT_CFG = {
    "AGENT_READY": ("vg", "✅", "Agent Ready",       "var(--green)"),
    "PARTIAL":     ("va", "⚠️", "Partially Ready",   "var(--amber)"),
    "NOT_READY":   ("vr", "❌", "Not Agent Ready",   "var(--red)"),
}
RING_CFG = {"AGENT_READY": "sr-g", "PARTIAL": "sr-a", "NOT_READY": "sr-r"}
FRIENDLY_PATHS = {
    "/.well-known/mcp.json":       "MCP Manifest",
    "/.well-known/ai-plugin.json": "AI Plugin",
    "/api/mcp":                    "/api/mcp",
    "/mcp":                        "/mcp",
    "/api/v1/mcp":                 "/api/v1/mcp",
    "/openapi.json":               "OpenAPI Spec",
    "/swagger.json":               "Swagger Spec",
    "/api-docs":                   "API Docs",
}


def render_hero():
    st.markdown("""
    <div class="hero">
        <div class="hero-title">Pharma <em>MCP Agent</em> Readiness Auditor</div>
        <div class="hero-sub">
            Actively probes pharma websites to check whether AI agents can call them as live MCP tools —
            scoring their manifests, endpoints, schemas, and context across five dimensions.
        </div>
        <div class="fp-row">
            <span class="fp on">⚡ Live Endpoint Probing</span>
            <span class="fp on">🤖 Claude AI Analysis</span>
            <span class="fp on">📄 Multi-page Crawl</span>
            <span class="fp on">⚖️ Side-by-Side Compare</span>
            <span class="fp on">📊 PDF Export</span>
            <span class="fp on">💾 1-hour Cache</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_pillars(scores: MCPScores):
    cols = st.columns(5)
    for col, (pid, icon, name, mx, fill_cls, card_cls, desc) in zip(cols, PILLAR_UI):
        val = scores.get(pid)
        pct = int((val / mx) * 100)
        color = "var(--green)" if pct >= 70 else "var(--amber)" if pct >= 40 else "var(--red)"
        with col:
            st.markdown(f"""
            <div class="pc {card_cls}">
                <div class="pc-icon">{icon}</div>
                <div class="pc-name">{name}</div>
                <div class="pc-score" style="color:{color}">
                    {val:.0f}<span class="pc-denom">/{mx}</span>
                </div>
                <div class="pc-bar"><div class="pc-fill {fill_cls}" style="width:{pct}%"></div></div>
                <div class="pc-desc">{desc}</div>
            </div>""", unsafe_allow_html=True)


def render_result_card(result: AuditResult, api_key: str = ""):
    found_eps = sum(1 for v in result.probed_endpoints.values() if v)
    vcls, vicon, vlabel, _ = VERDICT_CFG[result.readiness_level]
    cached_note = "  · 💾 cached" if result.cached else ""

    with st.expander(
        f"{vicon}  **{result.domain}**"
        f"  ·  Score: {result.scores.total:.0f}/100"
        f"  ·  {vlabel}"
        f"  ·  {found_eps}/{len(MCP_ENDPOINT_PATHS)} MCP endpoints live"
        f"{cached_note}"
    ):
        r_col, p_col = st.columns([1, 7])
        with r_col:
            rc = RING_CFG[result.readiness_level]
            st.markdown(f"""
            <div style="display:flex;align-items:center;justify-content:center;padding-top:0.4rem;">
                <div class="sr {rc}">{result.scores.total:.0f}<div class="sr-sub">/100</div></div>
            </div>""", unsafe_allow_html=True)
        with p_col:
            render_pillars(result.scores)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        # Quick-status bar
        mcp  = "✅ mcp.json"  if result.manifest.has_mcp_json  else "❌ No mcp.json"
        oas  = "✅ OpenAPI"   if result.manifest.has_openapi   else "❌ No OpenAPI"
        plug = "✅ ai-plugin" if result.manifest.has_ai_plugin else "❌ No ai-plugin"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:0.8rem;flex-wrap:wrap;
                    padding:0.65rem 0.9rem;background:var(--surface2);
                    border-radius:var(--r-sm);margin-bottom:1.2rem;">
            <span class="verdict {vcls}">{vicon} {vlabel}</span>
            <span style="color:var(--border-lit)">|</span>
            <span style="font-size:0.82rem;color:var(--text-mid)">{mcp}</span>
            <span style="font-size:0.82rem;color:var(--text-mid)">{oas}</span>
            <span style="font-size:0.82rem;color:var(--text-mid)">{plug}</span>
            <span style="font-size:0.82rem;color:var(--text-mid)">📄 {result.pages_crawled} pages crawled</span>
            <span style="font-size:0.82rem;color:var(--text-mid)">⚡ {result.manifest.callable_functions} agent functions detected</span>
        </div>""", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown('<div class="sec-h">Live Endpoint Probe</div>', unsafe_allow_html=True)
            st.caption("We tested these MCP paths — green means live.")
            html = '<div class="probe-grid">'
            for path, found in result.probed_endpoints.items():
                cls  = "probe-y" if found else "probe-n"
                icon = "✓" if found else "·"
                html += f'<div class="probe {cls}"><span>{icon}</span>{FRIENDLY_PATHS.get(path, path)}</div>'
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="sec-h">What Agents Can Access</div>', unsafe_allow_html=True)
            st.caption("Data an AI agent can read, cite, or relay from this site.")
            items = [
                ("Drug / therapy schema",      result.schema.drug_schema),
                ("Medical condition schema",   result.schema.medical_condition),
                ("Clinical trial schema",      result.schema.clinical_trial),
                ("FAQ schema (agent Q&A)",     result.schema.faq_schema),
                ("Mechanism of action",        result.context.mechanism_of_action),
                ("Dosing information",         result.context.dosing_info),
                ("Approved indications",       result.context.indication_detail),
                ("Prescribing information",    result.trust.prescribing_info),
                ("PubMed / DOI citations",     result.trust.pubmed_refs),
                ("Clinical study data",        result.trust.clinical_data),
            ]
            html = '<div class="checks">'
            for label, val in items:
                cls = "chk-pass" if val else "chk-fail"
                icon = "✓" if val else "○"
                html += f'<div class="chk {cls}"><span class="chk-icon">{icon}</span>{label}</div>'
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
            if result.schema.detected_types:
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                chips = "".join(f'<span class="chip">{t}</span>' for t in result.schema.detected_types[:8])
                st.markdown(f'<div class="chips">{chips}</div>', unsafe_allow_html=True)

        with c3:
            st.markdown('<div class="sec-h">Top Fixes</div>', unsafe_allow_html=True)
            st.caption("Highest-impact changes to make this site agent-callable.")
            if result.improvements:
                html = '<div class="fixes">'
                for i, fix in enumerate(result.improvements, 1):
                    html += f"""<div class="fix">
                        <span class="fix-n">#{i}</span>
                        <span style="flex:1;line-height:1.4">{fix['label']}</span>
                        <span class="fix-pts">+{fix['pts']}pts</span>
                    </div>"""
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.markdown('<div class="fix-ok">🎉 No critical gaps — this site is agent-callable</div>',
                            unsafe_allow_html=True)

        st.markdown("<div style='height:0.9rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="sec-h">Claude AI Recommendations</div>', unsafe_allow_html=True)

        if result.ai_recommendations:
            st.markdown(f"""
            <div class="ai-box">
                <div class="ai-lbl">🤖 Claude · MCP Integration Recommendations</div>
                <div class="ai-body">{result.ai_recommendations}</div>
            </div>""", unsafe_allow_html=True)
        elif api_key:
            if st.button("🤖 Generate AI Recommendations", key=f"ai_{result.domain}"):
                with st.spinner("Asking Claude for MCP integration recommendations…"):
                    result.ai_recommendations = get_ai_recommendations(result, api_key)
                    cache_set(result.url, result)
                st.rerun()
        else:
            st.markdown(
                '<div class="hint">🔑 Add your Anthropic API key in the sidebar to unlock Claude\'s recommendations.</div>',
                unsafe_allow_html=True)


def render_kpi_row(results: list):
    ok = [r for r in results if r.ok]
    if not ok: return
    avg     = np.mean([r.scores.total for r in ok])
    ready   = sum(1 for r in ok if r.readiness_level == "AGENT_READY")
    partial = sum(1 for r in ok if r.readiness_level == "PARTIAL")
    not_r   = sum(1 for r in ok if r.readiness_level == "NOT_READY")
    avg_cls = "kg" if avg >= 70 else "ka" if avg >= 45 else "kr"
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card"><div class="kpi-icon">🔍</div><div class="kpi-lbl">Domains Audited</div><div class="kpi-val">{len(ok)}</div><div class="kpi-sub">this session</div></div>
        <div class="kpi-card"><div class="kpi-icon">📊</div><div class="kpi-lbl">Avg MCP Score</div><div class="kpi-val {avg_cls}">{avg:.1f}</div><div class="kpi-sub">out of 100</div></div>
        <div class="kpi-card"><div class="kpi-icon">✅</div><div class="kpi-lbl">Agent Ready</div><div class="kpi-val kg">{ready}</div><div class="kpi-sub">score ≥ 70</div></div>
        <div class="kpi-card"><div class="kpi-icon">⚠️</div><div class="kpi-lbl">Partially Ready</div><div class="kpi-val ka">{partial}</div><div class="kpi-sub">score 45–69</div></div>
        <div class="kpi-card"><div class="kpi-icon">❌</div><div class="kpi-lbl">Not Ready</div><div class="kpi-val kr">{not_r}</div><div class="kpi-sub">score &lt; 45</div></div>
    </div>""", unsafe_allow_html=True)


def render_compare(history: list):
    ok = [r for r in history if r.ok]
    if len(ok) < 2:
        st.info("Audit at least 2 domains to use the comparison view.")
        return
    domain_map = {r.domain: r for r in ok}
    selected = st.multiselect(
        "Choose 2–4 domains to compare",
        options=list(domain_map.keys()),
        default=list(domain_map.keys())[:min(4, len(domain_map))],
        max_selections=4,
    )
    if len(selected) < 2:
        st.warning("Select at least 2 domains.")
        return
    chosen = [domain_map[d] for d in selected]
    n = len(chosen)

    hcols = st.columns([1.5] + [1]*n)
    hcols[0].markdown("<div style='height:2.2rem'></div>", unsafe_allow_html=True)
    for col, r in zip(hcols[1:], chosen):
        vcls, vicon, vlabel, vcolor = VERDICT_CFG[r.readiness_level]
        col.markdown(f"""
        <div class="cmp-card" style="border-top-color:{vcolor};">
            <div style="font-size:1.9rem;font-weight:800;color:{vcolor};">{r.scores.total:.0f}</div>
            <div style="font-size:0.58rem;color:var(--text-dim);margin-bottom:0.35rem;">/100</div>
            <div style="font-size:0.82rem;font-weight:700;color:var(--text);margin-bottom:0.4rem;">{r.domain}</div>
            <span class="verdict {vcls}" style="font-size:0.7rem;">{vicon} {vlabel}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    def cmp_row(label, values, fmt=str, higher_better=True):
        cols = st.columns([1.5] + [1]*n)
        cols[0].markdown(f'<div class="cmp-lbl">{label}</div>', unsafe_allow_html=True)
        best = max(values) if higher_better else min(values)
        for col, val in zip(cols[1:], values):
            cls = "cmp-w" if val == best else "cmp-l"
            col.markdown(f'<div class="cmp-cell {cls}">{fmt(val)}</div>', unsafe_allow_html=True)

    cmp_row("Total Score",          [r.scores.total for r in chosen],      fmt=lambda x: f"{x:.0f}/100")
    cmp_row("Agent Manifest",       [r.scores.manifest for r in chosen],   fmt=lambda x: f"{x:.0f}/20")
    cmp_row("Callable Endpoints",   [r.scores.endpoints for r in chosen],  fmt=lambda x: f"{x:.0f}/25")
    cmp_row("Structured Schema",    [r.scores.schema for r in chosen],     fmt=lambda x: f"{x:.0f}/20")
    cmp_row("Medical Authority",    [r.scores.trust for r in chosen],      fmt=lambda x: f"{x:.0f}/20")
    cmp_row("Context Quality",      [r.scores.context for r in chosen],    fmt=lambda x: f"{x:.0f}/15")
    cmp_row("Live Endpoints Found", [sum(1 for v in r.probed_endpoints.values() if v) for r in chosen], fmt=str)
    cmp_row("Agent Functions",      [r.manifest.callable_functions for r in chosen], fmt=str)
    cmp_row("Schema Types Found",   [len(r.schema.detected_types) for r in chosen],  fmt=str)
    cmp_row("Pages Crawled",        [r.pages_crawled for r in chosen],     fmt=str)
    cmp_row("Fix Points Needed",    [r.fix_pts for r in chosen], fmt=lambda x: f"+{x}pts", higher_better=False)


def render_benchmarks(scan_results: list):
    st.markdown('<div class="sec-h">Industry MCP Readiness Benchmarks</div>', unsafe_allow_html=True)
    st.caption("Estimated MCP agent-readiness scores for major pharma brands based on publicly observable signals.")
    entries = sorted(
        [(co, cat, sc) for cat, companies in BENCHMARKS.items() for co, sc in companies.items()],
        key=lambda x: -x[2])
    html = '<div class="bench-wrap">'
    for company, cat, score in entries:
        color = "var(--green)" if score >= 70 else "var(--amber)" if score >= 45 else "var(--red)"
        html += f"""<div class="bench-row">
            <div class="bench-name">{company}</div><div class="bench-cat">{cat}</div>
            <div class="bench-track"><div class="bench-fill" style="width:{score}%;background:{color};"></div></div>
            <div class="bench-score" style="color:{color}">{score}</div>
        </div>"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
    ok = [r for r in scan_results if r.ok]
    if ok:
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        bm_scores = [sc for _, companies in BENCHMARKS.items() for sc in companies.values()]
        live_avg = np.mean([r.scores.total for r in ok])
        ind_avg  = np.mean(bm_scores)
        c1, c2, c3 = st.columns(3)
        c1.metric("Your Portfolio Avg", f"{live_avg:.1f}/100")
        c2.metric("Industry Avg",       f"{ind_avg:.1f}/100")
        c3.metric("vs Industry",        f"{live_avg - ind_avg:+.1f} pts")


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
    render_hero()

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
            st.markdown('<div class="hint">// no audits yet</div>', unsafe_allow_html=True)
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
        st.markdown(f'<div class="sec-h">Paste pharma domains to audit · one per line · max 20 · {mode}</div>',
                    unsafe_allow_html=True)

        ci, ca = st.columns([5, 1])
        with ci:
            raw = st.text_area("DOMAINS", value=DEFAULT_DOMAINS, height=170,
                               label_visibility="collapsed")
            st.markdown('<div class="hint">// https prefix optional · results cached 1hr · retries on failure</div>',
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

                st.markdown(f'<div class="sec-h">{len(ok_r)} domain(s) audited</div>', unsafe_allow_html=True)
                for r in ok_r:
                    render_result_card(r, api_key=api_key)

            for r in err_r:
                st.markdown(f'<div class="err-card">✗ {r.domain} — {r.error}</div>', unsafe_allow_html=True)

    # ══════════════════════════════
    # TAB 2 — COMPARE
    # ══════════════════════════════
    with t2:
        st.markdown('<div class="sec-h">Side-by-side MCP readiness comparison</div>', unsafe_allow_html=True)
        render_compare(st.session_state.history)

    # ══════════════════════════════
    # TAB 3 — AGENT TEST
    # ══════════════════════════════
    with t3:
        st.markdown('<div class="sec-h">Deep-probe a single domain for MCP agent compatibility</div>',
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
                            <div class="ast-lbl">Readiness Level</div>
                            <div class="ast-val {lc}">{result.readiness_level.replace("_"," ")}</div>
                        </div>
                        <div class="ast"><div class="ast-lbl">MCP Score</div><div class="ast-val">{result.scores.total:.0f}/100</div></div>
                        <div class="ast"><div class="ast-lbl">mcp.json</div><div class="ast-val {'ast-g' if result.manifest.has_mcp_json else 'ast-r'}">{'✓' if result.manifest.has_mcp_json else '✗'}</div></div>
                        <div class="ast"><div class="ast-lbl">OpenAPI</div><div class="ast-val {'ast-g' if result.manifest.has_openapi else 'ast-r'}">{'✓' if result.manifest.has_openapi else '✗'}</div></div>
                        <div class="ast"><div class="ast-lbl">Functions</div><div class="ast-val">{result.manifest.callable_functions}</div></div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
                    render_pillars(result.scores)

                with c2:
                    st.markdown('<div class="sec-h">Raw MCP Probe Payload</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="sec-h">Executive dashboard · all audited domains</div>', unsafe_allow_html=True)
        ok_all = [r for r in st.session_state.history if r.ok]

        if not ok_all:
            st.markdown('<div class="hint">// run an audit first to unlock executive view</div>',
                        unsafe_allow_html=True)
        else:
            render_kpi_row(ok_all)
            df = results_to_df(ok_all)

            st.markdown('<div class="sec-h">Leaderboard</div>', unsafe_allow_html=True)

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
