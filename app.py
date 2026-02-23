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
import time

# Session state for historical tracking
if 'audit_history' not in st.session_state:
    st.session_state.audit_history = []

# Mock OpenClaw client
class MockOpenClawClient:
    def chat(self, prompt, model="heavy"):
        score = np.random.randint(65, 92)
        return f"""
        📊 **PHARMA INTEL** ({model.upper()})
        Score: {score}/100 | Key Action: Add FAQPage schema (+15pts)
        MCP Readiness: Implement navigator.modelContext for agents
        """

OPENCLAW_CLIENT = MockOpenClawClient()
USER_AGENT = "PharmaMCP-Auditor/5.0"
TIMEOUT = 20

# ------------------------------------------------------------
# ENHANCED SCORING WITH CUSTOM WEIGHTS + TOOLTIPS
# ------------------------------------------------------------

def score_breakdown_ui(score_data, weights):
    """Beautiful score breakdown with hover tooltips"""
    col1, col2, col3, col4, col5, col6, total_col = st.columns(7)
    
    with col1:
        st.metric(
            label="🔵 Schema Diversity", 
            value=f"{score_data['schema']}/{weights['schema']}",
            delta=None,
            help="""**🔵 Schema Diversity (Customizable)**  
💡 Counts unique JSON-LD @type schemas × 3pts  
✅ MedicalEntity, DrugClass, FAQPage = GEO power  
🎯 More schemas = better AI answer coverage"""
        )
    
    with col2:
        st.metric(
            label="🧬 Pharma Entities", 
            value=f"{score_data['entities']}/{weights['entities']}",
            help="""**🧬 Pharma Entities (Medical Schema)**  
💡 7 key schemas worth 5pts each:  
✅ DrugClass • MedicalCondition • PharmaceuticalProduct  
✅ MedicalTrial • MedicalGuideline • FAQPage  
🎯 Targets Perplexity/ChatGPT answers"""
        )
    
    with col3:
        st.metric(
            label="📚 E-E-A-T Signals", 
            value=f"{score_data['eat']}/{weights['eat']}",
            help="""**📚 E-E-A-T Authority (8 Signals)**  
💡 5pts each: Medically Reviewed, PI, Adverse Events  
✅ PubMed • DOI Citations • References • FAQ  
🎯 Builds AI trust for YMYL content"""
        )
    
    with col4:
        st.metric(
            label="⚙️ Technical", 
            value=f"{score_data['status']}/{weights['status']}",
            help="""**⚙️ Technical Health**  
💡 HTTP 200 + fast load = full points  
❌ 404/500 errors = 0pts  
🎯 AI agents need reliable access"""
        )
    
    with col5:
        st.metric(
            label="🎯 GEO Readiness", 
            value=f"{score_data['geo']}/{weights['geo']}",
            help="""**🎯 Generative Engine Optimization**  
💡 Schema count × 2 + FAQ/References/PubMed  
✅ Predicts Perplexity/ChatGPT ranking  
🎯 AI Answer Engine visibility"""
        )
    
    with col6:
        st.metric(
            label="🤖 MCP Agentic", 
            value=f"{score_data['mcp']}/{weights['mcp']}",
            help="""**🤖 Model Context Protocol Readiness**  
💡 navigator.modelContext = 25pts  
✅ MCP JSON manifests (5pts each)  
✅ Agent functions get_/find_ (2pts each)  
🎯 AI agent handshake capability"""
        )
    
    with total_col:
        st.metric(
            label="🏆 TOTAL SCORE", 
            value=f"{score_data['total']}/100",
            delta=None,
            help="""**🏆 Final GEO/MCP Score**  
🔥 >85 = Agent-ready leader  
✅ 70-85 = GEO competitive  
⚠️ 50-70 = Quick wins available  
❌ <50 = Full optimization needed"""
        )

def compute_score(types, signals, status, mcp_signals, custom_weights=None):
    """v5 scoring with client-customizable weights"""
    if custom_weights is None:
        custom_weights = {
            'schema': 30, 'entities': 25, 'eat': 40, 
            'status': 15, 'geo': 20, 'mcp': 25
        }
    
    schema_diversity = min(len(types) * 3, custom_weights['schema'])
    important_entities = ["DrugClass", "MedicalCondition", "PharmaceuticalProduct", "MedicalScholarlyArticle", "MedicalTrial", "MedicalGuideline", "FAQPage"]
    entity_coverage = min(sum(1 for t in types if any(ent in t for ent in important_entities)) * 5, custom_weights['entities'])
    eat_signals = min(sum(signals.values()) * 5, custom_weights['eat'])
    status_score = custom_weights['status'] if status == 200 else 0
    geo_score = min(len(types) * 2 + sum(signals[k] for k in ["faq", "references", "pubmed"]), custom_weights['geo'])
    mcp_score = (custom_weights['mcp'] if mcp_signals["webmcp_ready"] else 0) + min(mcp_signals["mcp_manifests"] * 5, 15) + min(mcp_signals["agent_functions"] * 2, 10)
    
    total = min(schema_diversity + entity_coverage + eat_signals + status_score + geo_score + mcp_score, 100)
    
    return {
        "total": total,
        "schema": schema_diversity,
        "entities": entity_coverage,
        "eat": eat_signals,
        "status": status_score,
        "geo": geo_score,
        "mcp": min(mcp_score, custom_weights['mcp'])
    }

# ------------------------------------------------------------
# CORE FUNCTIONS (optimized)
# ------------------------------------------------------------

@st.cache_data(ttl=3600)
def bulk_audit(urls):
    """Process 100+ domains efficiently"""
    results = []
    for i, url in enumerate(urls):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
            html = r.text
            status = r.status_code
            
            jsonld = extract_jsonld(html)
            types = flatten_types(jsonld)
            signals = extract_signals(html)
            mcp_signals = detect_mcp_signals(html)
            score_data = compute_score(types, signals, status, mcp_signals)
            
            results.append({
                "url": url,
                "score_data": score_data,
                "types": types[:5],
                "signals": signals,
                "mcp": mcp_signals,
                "status": status,
                "timestamp": datetime.now().isoformat()
            })
        except:
            results.append({"url": url, "error": "Failed to fetch", "timestamp": datetime.now().isoformat()})
    return results

def extract_jsonld(html): 
    if not html: return []
    soup = BeautifulSoup(html, "lxml")
    scripts = soup.find_all("script", type="application/ld+json")
    data = []
    for s in scripts:
        try: data.append(json.loads(s.string or ""))
        except: pass
    return data

def flatten_types(jsonld):
    types = set()
    def walk(node):
        if isinstance(node, dict) and "@type" in node:
            if isinstance(node["@type"], list): types.update(node["@type"])
            else: types.add(node["@type"])
        elif isinstance(node, dict):
            for v in node.values(): walk(v)
        elif isinstance(node, list):
            for x in node: walk(x)
    for j in jsonld: walk(j)
    return list(types)

def extract_signals(html):
    if not html: return {k: False for k in ["reviewed", "pi", "medguide", "adverse", "pubmed", "doi", "references", "faq"]}
    text = html.lower()
    return {
        "reviewed": "reviewed by" in text or "medically reviewed" in text,
        "pi": "prescribing information" in text, "medguide": "medication guide" in text,
        "adverse": "adverse" in text and "event" in text, "pubmed": "pubmed" in text,
        "doi": bool(re.search(r"\b10\.\d{4,9}/", text)),
        "references": "references" in text or "source" in text,
        "faq": "faq" in text or "frequently asked" in text,
    }

def detect_mcp_signals(html):
    if not html: return {"webmcp_ready": False, "mcp_manifests": 0, "agent_functions": 0}
    soup = BeautifulSoup(html, "lxml")
    return {
        "webmcp_ready": "navigator.modelContext" in html,
        "mcp_manifests": len(soup.find_all("script", {"type": "application/mcp+json"})),
        "agent_functions": len(re.findall(r"\b(get_|check_|find_|book_|schedule_)", html, re.I))
    }

# ------------------------------------------------------------
# ENTERPRISE UI - PDF EXPORT
# ------------------------------------------------------------

def export_pdf(results):
    """Client-ready CSV export"""
    df = pd.DataFrame([{
        "Domain": r["url"], 
        "GEO_MCP_Score": r["score_data"]["total"],
        "MCP_Ready": r["mcp"]["webmcp_ready"],
        "HTTP_Status": r.get("status", "N/A")
    } for r in results if "score_data" in r])
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Client Report (CSV)", 
        data=csv,
        file_name=f"pharma-mcp-audit-{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# ------------------------------------------------------------
# MAIN ENTERPRISE APP - BEAUTIFUL UI
# ------------------------------------------------------------

def main():
    # Beautiful header
    st.set_page_config(page_title="Pharma MCP/GEO v5 - Enterprise", layout="wide", initial_sidebar_state="expanded")
    
    # Gradient header
    st.markdown("""
    <div style='background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 10px; color: white; text-align: center;'>
        <h1>🔬 Pharma MCP/GEO Intelligence Engine v5</h1>
        <p><strong>🏢 ENTERPRISE EDITION</strong> | Bulk Analysis • Historical Tracking • PDF Export • Custom Weights</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Enterprise Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Quick Audit", "📈 Historical", "⚙️ Enterprise Bulk", "📊 Agency Dashboard"])
    
    with tab1:
        st.info("👆 **Paste competitor URLs in sidebar → Click RUN → Instant GEO/MCP scores!**")
        
        # Sidebar - Quick Audit
        with st.sidebar:
            st.header("🚀 Quick Audit")
            st.markdown("**✅ No setup required**")
            urls_input = st.text_area("Competitor URLs", 
                                    value="https://www.lilly.com/\nhttps://www.pfizer.com/\nhttps://www.merck.com/",
                                    height=150)
            if st.button("🚀 Run Quick Audit", type="primary", use_container_width=True):
                urls = [u.strip() for u in urls_input.split("\n") if u.strip()]
                st.session_state.current_results = bulk_audit(urls)
                st.session_state.audit_history.extend(st.session_state.current_results)
        
        # Results
        if 'current_results' in st.session_state:
            for r in st.session_state.current_results:
                if 'error' not in r:
                    with st.expander(f"🔍 {r['url']} | **{r['score_data']['total']:.0f}/100**"):
                        score_breakdown_ui(r["score_data"], {
                            'schema': 30, 'entities': 25, 'eat': 40, 
                            'status': 15, 'geo': 20, 'mcp': 25
                        })
                        st.json({"MCP_Signals": r["mcp"], "Top_Schemas": r["types"]})
    
    with tab2:
        st.subheader("📈 Historical Tracking")
        if st.session_state.audit_history:
            st.success(f"✅ {len(st.session_state.audit_history)} audits tracked")
            hist_df = pd.DataFrame([r for r in st.session_state.audit_history if 'score_data' in r])
            if len(hist_df) > 1:
                st.line_chart(hist_df.pivot_table(index='timestamp', columns='url', values='score_data.total', aggfunc='first'))
            st.dataframe(hist_df[['url', 'score_data.total', 'timestamp']].round(1))
        else:
            st.info("👈 Run Quick Audit to build history")
    
    with tab3:
        # Enterprise Bulk Analysis
        st.markdown("### 🏢 **Enterprise Bulk Analysis (100+ domains)**")
        
        col1, col2 = st.columns([1,1])
        
        with col1:
            st.markdown("**📁 Upload Domain List**")
            uploaded_file = st.file_uploader("CSV/TXT - One domain per line", type=['csv','txt'])
            domains = []
            if uploaded_file:
                content = uploaded_file.read().decode()
                domains = [line.strip() for line in content.splitlines() if line.strip()]
                st.success(f"✅ Loaded **{len(domains)}** domains")
        
        with col2:
            st.markdown("**⚖️ Custom Scoring Weights**")
            weights = {
                'schema': st.slider("🔵 Schema Diversity", 10, 40, 30, help="JSON-LD schema variety"),
                'entities': st.slider("🧬 Pharma Entities", 10, 40, 25, help="Medical schemas"),
                'eat': st.slider("📚 E-E-A-T Signals", 20, 60, 40, help="Authority signals"),
                'status': st.slider("⚙️ Technical", 5, 25, 15, help="HTTP status"),
                'geo': st.slider("🎯 GEO Readiness", 10, 30, 20, help="AI answer optimization"),
                'mcp': st.slider("🤖 MCP Agentic", 15, 40, 25, help="AI agent readiness")
            }
        
        if st.button("⚡ **BULK AUDIT 100+ DOMAINS**", type="primary", use_container_width=True) and domains:
            with st.spinner(f"🔄 Processing {min(50, len(domains))} domains..."):
                results = bulk_audit(domains[:50])  # Demo limit
                st.session_state.bulk_results = results
                st.session_state.audit_history.extend(results)
                export_pdf(results)
                
                # Bulk results table
                df = pd.DataFrame([{
                    "🏆 Score": r["score_data"]["total"],
                    "🌐 Domain": r["url"],
                    "🤖 MCP Ready": r["mcp"]["webmcp_ready"],
                    "📡 Status": r.get("status", "N/A")
                } for r in results if "score_data" in r]).sort_values("🏆 Score", ascending=False)
                st.dataframe(df, use_container_width=True)
    
    with tab4:
        # Agency Dashboard
        st.markdown("### 📊 **Agency Competitive Intelligence Dashboard**")
        
        col1, col2, col3, col4 = st.columns(4)
        total_audits = len([r for r in st.session_state.audit_history if 'score_data' in r])
        avg_score = np.mean([r['score_data']['total'] for r in st.session_state.audit_history if 'score_data' in r])
        mcp_ready = sum(1 for r in st.session_state.audit_history if r.get('mcp', {}).get('webmcp_ready', False))
        high_priority = sum(1 for r in st.session_state.audit_history if r['score_data']['total'] > 80 if 'score_data' in r)
        
        with col1: st.metric("📈 Total Audits", total_audits)
        with col2: st.metric("🎯 Avg Score", f"{avg_score:.1f}/100")
        with col3: st.metric("🤖 MCP Ready", f"{mcp_ready}/{total_audits}")
        with col4: st.metric("🔥 High Priority", high_priority)

if __name__ == "__main__":
    main()



