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

# Session state for historical tracking
if 'audit_history' not in st.session_state:
    st.session_state.audit_history = []
if 'current_results' not in st.session_state:
    st.session_state.current_results = []

# OpenClaw Model Selection
OPENCLAW_MODELS = {
    "light": "Mistral 7B (Fast)",
    "heavy": "MiniMax M2.5 (Deep Pharma)", 
    "agency": "Enterprise Blend"
}

class MockOpenClawClient:
    def chat(self, prompt, model="light"):
        if model == "heavy":
            return """🧬 PHARMA DEEP ANALYSIS (MiniMax M2.5)
🎯 GEO Score: 87/100 - Excellent FAQ + MedicalEntity coverage
🤖 MCP Ready: navigator.modelContext detected
💡 Action: Add MedicalTrial schema (+8pts predicted)
🚀 Agent Manifest: Ready for production handshake"""
        elif model == "agency":
            return """📊 AGENCY INTEL (Enterprise Blend)
💼 Client Pitch: "Competitor leads by 24 GEO points"
📈 Quick Win: FAQPage schema = +15pts immediate
🤖 MCP Gap: No agent functions detected
📋 Copy-paste ready recommendations generated"""
        else:
            score = np.random.randint(65, 92)
            return f"""📊 QUICK SCAN (Mistral 7B)
Score: {score}/100
Key Findings: {np.random.randint(2, 6)}/8 E-E-A-T signals
GEO Action: Add FAQPage schema (+12pts)"""

OPENCLAW_CLIENT = MockOpenClawClient()
USER_AGENT = "PharmaMCP-Auditor/5.0"
TIMEOUT = 20

# ------------------------------------------------------------
# SCORING + TOOLTIPS
# ------------------------------------------------------------

def score_breakdown_ui(score_data, weights):
    col1, col2, col3, col4, col5, col6, total_col = st.columns(7)
    
    with col1:
        st.metric("🔵 Schema", f"{score_data['schema']}/{weights['schema']}",
                 help="JSON-LD @types × 3pts | MedicalEntity, FAQPage = GEO power")
    
    with col2:
        st.metric("🧬 Entities", f"{score_data['entities']}/{weights['entities']}",
                 help="DrugClass, MedicalTrial (5pts each) | AI answer targeting")
    
    with col3:
        st.metric("📚 E-E-A-T", f"{score_data['eat']}/{weights['eat']}",
                 help="PubMed, PI, reviewed-by (5pts each) | YMYL authority")
    
    with col4:
        st.metric("⚙️ Tech", f"{score_data['status']}/{weights['status']}",
                 help="HTTP 200 = full points | Agent reliability")
    
    with col5:
        st.metric("🎯 GEO", f"{score_data['geo']}/{weights['geo']}",
                 help="FAQ + citations | Perplexity/ChatGPT ranking")
    
    with col6:
        st.metric("🤖 MCP", f"{score_data['mcp']}/{weights['mcp']}",
                 help="navigator.modelContext = agent-ready")
    
    with total_col:
        st.metric("🏆 TOTAL", f"{score_data['total']}/100",
                 help=">85=Leader | 70-85=Competitive | <70=Optimize")

def compute_score(types, signals, status, mcp_signals, custom_weights=None):
    if custom_weights is None:
        custom_weights = {'schema': 30, 'entities': 25, 'eat': 40, 'status': 15, 'geo': 20, 'mcp': 25}
    
    schema_diversity = min(len(types) * 3, custom_weights['schema'])
    important_entities = ["DrugClass", "MedicalCondition", "PharmaceuticalProduct", "MedicalScholarlyArticle", "MedicalTrial", "MedicalGuideline", "FAQPage"]
    entity_coverage = min(sum(1 for t in types if any(ent in t for ent in important_entities)) * 5, custom_weights['entities'])
    eat_signals = min(sum(signals.values()) * 5, custom_weights['eat'])
    status_score = custom_weights['status'] if status == 200 else 0
    geo_score = min(len(types) * 2 + sum(signals[k] for k in ["faq", "references", "pubmed"]), custom_weights['geo'])
    mcp_score = (custom_weights['mcp'] if mcp_signals["webmcp_ready"] else 0) + min(mcp_signals["mcp_manifests"] * 5, 15) + min(mcp_signals["agent_functions"] * 2, 10)
    
    total = min(schema_diversity + entity_coverage + eat_signals + status_score + geo_score + mcp_score, 100)
    
    return {
        "total": total, "schema": schema_diversity, "entities": entity_coverage,
        "eat": eat_signals, "status": status_score, "geo": geo_score, "mcp": min(mcp_score, custom_weights['mcp'])
    }

# ------------------------------------------------------------
# CORE FUNCTIONS
# ------------------------------------------------------------

@st.cache_data(ttl=3600)
def analyze_url(url):
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        html = r.text
        status = r.status_code
        
        jsonld = extract_jsonld(html)
        types = flatten_types(jsonld)
        signals = extract_signals(html)
        mcp_signals = detect_mcp_signals(html)
        score_data = compute_score(types, signals, status, mcp_signals)
        
        return {
            "url": url, "score_data": score_data, "types": types[:5],
            "signals": signals, "mcp": mcp_signals, "status": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"url": url, "error": str(e), "timestamp": datetime.now().isoformat()}

def extract_jsonld(html): 
    if not html: return []
    soup = BeautifulSoup(html, "lxml")
    scripts = soup.find_all("script", type="application/ld+json")
    data = []
    for s in scripts:
        try: 
            if s.string: data.append(json.loads(s.string))
        except: pass
    return data

def flatten_types(jsonld):
    types = set()
    def walk(node):
        if isinstance(node, dict) and "@type" in node:
            if isinstance(node["@type"], list): 
                types.update(node["@type"])
            else: 
                types.add(node["@type"])
        elif isinstance(node, dict): 
            [walk(v) for v in node.values()]
        elif isinstance(node, list): 
            [walk(x) for x in node]
    for j in jsonld: walk(j)
    return list(types)

def extract_signals(html):
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
    if not html: 
        return {"webmcp_ready": False, "mcp_manifests": 0, "agent_functions": 0}
    soup = BeautifulSoup(html, "lxml")
    return {
        "webmcp_ready": "navigator.modelContext" in html,
        "mcp_manifests": len(soup.find_all("script", {"type": "application/mcp+json"})),
        "agent_functions": len(re.findall(r"\b(get_|check_|find_|book_|schedule_)", html, re.I))
    }

# ------------------------------------------------------------
# PDF EXPORT
# ------------------------------------------------------------

def export_pdf(results):
    valid_results = [r for r in results if "score_data" in r]
    if not valid_results:
        st.warning("No valid results to export")
        return
        
    df = pd.DataFrame([{
        "Domain": r["url"], 
        "GEO_MCP_Score": r["score_data"]["total"],
        "MCP_Ready": r["mcp"]["webmcp_ready"], 
        "HTTP_Status": r.get("status", "N/A")
    } for r in valid_results])
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Client Report (CSV)", 
        data=csv,
        file_name=f"pharma-mcp-audit-{datetime.now().strftime('%Y%m%d-%H%M')}.csv",
        mime="text/csv"
    )

# ------------------------------------------------------------
# MAIN APP - PRODUCTION READY
# ------------------------------------------------------------

def main():
    st.set_page_config(page_title="Pharma MCP/GEO v5", layout="wide", initial_sidebar_state="expanded")
    
    # Header
    st.markdown("""
    <div style='background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 10px; color: white; text-align: center;'>
        <h1>🔬 Pharma MCP/GEO Intelligence Engine v5</h1>
        <p><strong>🏢 ENTERPRISE EDITION</strong> | Bulk Analysis • Historical • Custom Weights • OpenClaw</p>
    </div>
    """, unsafe_allow_html=True)
    
    # GLOBAL CONTROLS
    col1, col2 = st.columns([3,1])
    with col2:
        selected_model = st.selectbox("🤖 OpenClaw Model:", list(OPENCLAW_MODELS.values()), key="global_model")
    
    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Quick Audit", "📈 Historical", "⚙️ Bulk Analysis", "📊 Dashboard"])
    
    with tab1:
        st.info("👆 **Paste competitor URLs in sidebar → Click RUN → Instant analysis!**")
        
        with st.sidebar:
            st.header("🚀 Quick Audit")
            urls_input = st.text_area("Competitor URLs (one per line)", 
                                    value="https://www.lilly.com/\nhttps://www.pfizer.com/\nhttps://www.merck.com/",
                                    height=150)
            if st.button("🚀 RUN QUICK AUDIT", type="primary", use_container_width=True):
                urls = [u.strip() for u in urls_input.split("\n") if u.strip()]
                with st.spinner(f"Analyzing {len(urls)} domains..."):
                    st.session_state.current_results = [analyze_url(url) for url in urls]
                    st.session_state.audit_history.extend([r for r in st.session_state.current_results if 'error' not in r])
        
        # Display results
        if st.session_state.current_results:
            st.subheader("📊 Audit Results")
            for r in st.session_state.current_results:
                if 'error' not in r:
                    with st.expander(f"🔍 {r['url']} | **{r['score_data']['total']:.0f}/100**"):
                        score_breakdown_ui(r["score_data"], {
                            'schema': 30, 'entities': 25, 'eat': 40, 
                            'status': 15, 'geo': 20, 'mcp': 25
                        })
                        col1, col2 = st.columns(2)
                        with col1:
                            st.json({"MCP_Signals": r["mcp"]})
                        with col2:  
                            st.json({"Top_Schemas": r["types"]})
                else:
                    st.error(f"❌ {r['url']}: {r['error']}")
    
    with tab2:
        st.subheader("📈 Historical Tracking")
        valid_history = [r for r in st.session_state.audit_history if 'score_data' in r]
        
        if valid_history:
            st.success(f"✅ {len(valid_history)} historical audits")
            
            # FIXED: Safe pivot table
            hist_df = pd.DataFrame([{
                'url': r['url'], 
                'score': r['score_data']['total'],
                'timestamp': pd.to_datetime(r['timestamp'])
            } for r in valid_history])
            
            if len(hist_df) > 1 and len(hist_df['url'].unique()) > 1:
                pivot_df = hist_df.pivot(index='timestamp', columns='url', values='score')
                st.line_chart(pivot_df)
            
            st.dataframe(hist_df[['url', 'score', 'timestamp']].round(1), use_container_width=True)
        else:
            st.info("👈 Run Quick Audit tab to build historical data")
    
    with tab3:
        st.markdown("### 🏢 **Enterprise Bulk Analysis**")
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_file = st.file_uploader("📁 Upload CSV/TXT (one domain per line)", type=['csv','txt'])
            domains = []
            if uploaded_file:
                content = uploaded_file.read().decode('utf-8')
                domains = [line.strip() for line in content.splitlines() if line.strip()]
                st.success(f"✅ Loaded **{len(domains)}** domains")
        
        with col2:
            weights = {
                'schema': st.slider("🔵 Schema Weight", 10, 40, 30, help="JSON-LD Diversity"),
                'entities': st.slider("🧬 Entities Weight", 10, 40, 25, help="Medical Schemas"),
                'eat': st.slider("📚 E-E-A-T Weight", 20, 60, 40, help="Authority Signals"),
                'status': st.slider("⚙️ Tech Weight", 5, 25, 15, help="HTTP Status"),
                'geo': st.slider("🎯 GEO Weight", 10, 30, 20, help="AI Answer Optimization"),
                'mcp': st.slider("🤖 MCP Weight", 15, 40, 25, help="Agent Readiness")
            }
        
        if st.button("⚡ RUN BULK ANALYSIS (25 domains max)", type="primary") and domains:
            with st.spinner(f"Processing {min(25, len(domains))} domains..."):
                results = [analyze_url(domain) for domain in domains[:25]]
                st.session_state.bulk_results = results
                export_pdf(results)
                
                df = pd.DataFrame([{
                    "Score": r["score_data"]["total"],
                    "Domain": r["url"], 
                    "MCP_Ready": r["mcp"]["webmcp_ready"]
                } for r in results if "score_data" in r]).sort_values("Score", ascending=False)
                st.dataframe(df, use_container_width=True)
    
    with tab4:
        valid_history = [r for r in st.session_state.audit_history if 'score_data' in r]
        if valid_history:
            col1, col2, col3, col4 = st.columns(4)
            total_audits = len(valid_history)
            avg_score = np.mean([r['score_data']['total'] for r in valid_history])
            mcp_ready = sum(1 for r in valid_history if r['mcp']['webmcp_ready'])
            high_priority = sum(1 for r in valid_history if r['score_data']['total'] > 80)
            
            with col1: st.metric("📈 Total Audits", total_audits)
            with col2: st.metric("🎯 Avg Score", f"{avg_score:.1f}/100")
            with col3: st.metric("🤖 MCP Ready", f"{mcp_ready}/{total_audits}")
            with col4: st.metric("🔥 High Priority", high_priority)
        else:
            st.info("👈 Run audits to populate dashboard")

if __name__ == "__main__":
    main()


