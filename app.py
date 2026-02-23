"""
Pharma MCP/GEO Intelligence Engine - MCP Pharma Auditor
Audits competitor MCP readiness, generates agent handshake manifests, predicts GEO impact
"""

import streamlit as st
import requests
import json
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import zipfile
import io

# Optional Playwright
USE_PLAYWRIGHT = False
try:
    from playwright.sync_api import sync_playwright
    USE_PLAYWRIGHT = True
except:
    USE_PLAYWRIGHT = False

USER_AGENT = "PharmaMCP-Auditor/4.0"
TIMEOUT = 20

# ------------------------------------------------------------
# FETCH FUNCTIONS
# ------------------------------------------------------------

def fetch_page(url, use_js=False):
    """Fetch page HTML with optional JS rendering"""
    if use_js and USE_PLAYWRIGHT:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=20000)
                page.wait_for_load_state("networkidle")
                html = page.content()
                browser.close()
                return html, 200
        except:
            return "", 0
    else:
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
            return r.text, r.status_code
        except:
            return "", 0

# ------------------------------------------------------------
# PARSE FUNCTIONS (ALL ORIGINAL + ENHANCED)
# ------------------------------------------------------------

def extract_jsonld(html):
    """Extract JSON-LD structured data from HTML"""
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    scripts = soup.find_all("script", type="application/ld+json")
    data = []
    for s in scripts:
        try:
            parsed = json.loads(s.string or "")
            data.append(parsed)
        except:
            continue
    return data

def flatten_types(jsonld):
    """Extract all @type values from JSON-LD"""
    types = set()
    def walk(node):
        if isinstance(node, dict):
            if "@type" in node:
                if isinstance(node["@type"], list):
                    types.update(node["@type"])
                else:
                    types.add(node["@type"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for x in node:
                walk(x)
    for j in jsonld:
        walk(j)
    return list(types)

def extract_signals(html):
    """Extract pharma E-E-A-T signals from page content"""
    if not html:
        return {k: False for k in ["reviewed", "pi", "medguide", "adverse", "pubmed", "doi", "references", "faq"]}
    text = html.lower()
    return {
        "reviewed": "reviewed by" in text or "medically reviewed" in text,
        "pi": "prescribing information" in text,
        "medguide": "medication guide" in text,
        "adverse": "adverse" in text and "event" in text,
        "pubmed": "pubmed" in text,
        "doi": bool(re.search(r"\b10\.\d{4,9}/", text)),
        "references": "references" in text or "source" in text,
        "faq": "faq" in text or "frequently asked" in text,
    }

def detect_mcp_signals(html):
    """Detect WebMCP, MCP manifests, agent handshake readiness"""
    if not html:
        return {"webmcp_ready": False, "mcp_manifests": 0, "agent_functions": 0}
    
    soup = BeautifulSoup(html, "lxml")
    
    # WebMCP navigator.modelContext detection
    webmcp = "navigator.modelContext" in html
    
    # MCP Manifests (JSON tool definitions)
    mcp_manifests = len(soup.find_all("script", {"type": "application/mcp+json"}))
    
    # Agent function keywords (get_, check_, find_, etc.)
    agent_functions = len(re.findall(r"\b(get_|check_|find_|book_|schedule_)", html, re.I))
    
    return {
        "webmcp_ready": webmcp,
        "mcp_manifests": mcp_manifests,
        "agent_functions": agent_functions
    }

# ------------------------------------------------------------
# SCORING MODEL v4 (GEO + MCP + Agentic)
# ------------------------------------------------------------

def compute_score(types, signals, status, mcp_signals):
    """Enhanced v4 pharma E-E-A-T + GEO + MCP scoring"""
    # Schema diversity (max 30)
    schema_diversity = min(len(types) * 3, 30)
    
    # Entity coverage for important pharma entities
    important_entities = ["DrugClass", "MedicalCondition", "PharmaceuticalProduct", "MedicalScholarlyArticle", 
                         "MedicalTrial", "MedicalGuideline", "FAQPage"]
    entity_coverage = sum(1 for t in types if any(ent in t for ent in important_entities)) * 5
    
    # E-E-A-T signals (max 40)
    eat_signals = sum(signals.values()) * 5
    
    # Technical status (max 15)
    status_score = 15 if status == 200 else 0
    
    # GEO readiness signals (max 20)
    geo_score = min(len(types) * 2 + sum(signals[k] for k in ["faq", "references", "pubmed"]), 20)
    
    # MCP/Agentic readiness (max 25)
    mcp_score = (25 if mcp_signals["webmcp_ready"] else 0) + \
                mcp_signals["mcp_manifests"] * 5 + \
                min(mcp_signals["agent_functions"] * 2, 10)
    
    total = schema_diversity + entity_coverage + eat_signals + status_score + geo_score + mcp_score
    return min(total, 100)

# ------------------------------------------------------------
# MAIN STREAMLIT APP
# ------------------------------------------------------------

def main():
    st.set_page_config(page_title="Pharma MCP/GEO Auditor v4", layout="wide")
    st.title("🔬 Pharma MCP/GEO Intelligence Engine v4")
    st.markdown("**Generic Pharma Auditor** - Audits competitor MCP readiness, generates agent handshake manifests, predicts GEO impact")
    
    # Sidebar
    st.sidebar.header("Configuration")
    urls_input = st.sidebar.text_area("Competitor URLs (one per line)", 
                                     value="https://www.lilly.com/\nhttps://www.pfizer.com/\nhttps://www.merck.com/")
    max_pages = st.sidebar.slider("Max pages per domain", 1, 10, 3)
    use_js = st.sidebar.checkbox("Use JavaScript rendering (slower)")
    
    if st.sidebar.button("🚀 Run Audit", type="primary"):
        urls = [u.strip() for u in urls_input.split("\n") if u.strip()]
        
        if urls:
            progress_bar = st.progress(0)
            results = []
            
            for i, url in enumerate(urls):
                with st.expander(f"Analyzing {url}"):
                    html, status = fetch_page(url, use_js)
                    
                    jsonld = extract_jsonld(html)
                    types = flatten_types(jsonld)
                    signals = extract_signals(html)
                    mcp_signals = detect_mcp_signals(html)
                    
                    score = compute_score(types, signals, status, mcp_signals)
                    
                    results.append({
                        "url": url,
                        "score": score,
                        "types": types[:10],  # Top 10
                        "signals": signals,
                        "mcp": mcp_signals,
                        "status": status
                    })
                    
                    st.metric("GEO/MCP Score", f"{score}/100", delta=f"{score-50:+d}")
                    st.json({"Schema Types": types[:5], "E-E-A-T Signals": signals, "MCP Signals": mcp_signals})
                
                progress_bar.progress((i + 1) / len(urls))
            
            # Results table
            df = pd.DataFrame(results)
            st.subheader("📊 Audit Summary")
            st.dataframe(df[["url", "score", "status"]].round(1), use_container_width=True)
            
            # Leaderboard
            st.subheader("🏆 Leaderboard")
            top = df.nlargest(5, "score")[["url", "score"]]
            st.bar_chart(top.set_index("url")["score"])
            
            # Agent handshake manifest generation
            st.subheader("🤝 Agent Handshake Manifests")
            for r in results:
                if r["score"] > 70:
                    st.code(json.dumps({
                        "domain": urlparse(r["url"]).netloc,
                        "mcp_ready": r["mcp"]["webmcp_ready"],
                        "manifests": r["mcp"]["mcp_manifests"],
                        "recommended_tools": ["get_pi", "find_trials", "check_coverage"] if r["mcp"]["agent_functions"] > 0 else []
                    }, indent=2), language="json")

if __name__ == "__main__":
    main()
