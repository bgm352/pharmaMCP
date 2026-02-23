import streamlit as st
import requests
import json
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Optional Playwright
USE_PLAYWRIGHT = False
try:
    from playwright.sync_api import sync_playwright
    USE_PLAYWRIGHT = True
except:
    USE_PLAYWRIGHT = False

USER_AGENT = "BioGraphMCP/2.0"
TIMEOUT = 20

# ------------------------------------------------------------
# FETCH
# ------------------------------------------------------------

def fetch_page(url, use_js=False):
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
# PARSE
# ------------------------------------------------------------

def extract_jsonld(html):
    soup = BeautifulSoup(html, "lxml")
    scripts = soup.find_all("script", type="application/ld+json")
    data = []
    for s in scripts:
        try:
            parsed = json.loads(s.string)
            data.append(parsed)
        except:
            continue
    return data


def flatten_types(jsonld):
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
    text = html.lower()
    return {
        "reviewed": "reviewed by" in text or "medically reviewed" in text,
        "pi": "prescribing information" in text,
        "medguide": "medication guide" in text,
        "adverse": "adverse" in text,
        "pubmed": "pubmed" in text,
        "doi": bool(re.search(r"\b10\.\d{4,9}/", text)),
        "references": "references" in text,
        "faq": "faq" in text,
    }


# ------------------------------------------------------------
# SCORING MODEL V2
# ------------------------------------------------------------

def compute_score(types, signals, status):

    schema_diversity = min(len(types) * 3, 30)

    entity_coverage = 0
    important_entities = ["Drug", "MedicalCondition", "MedicalWebPage", "FAQPage"]
    entity_coverage = sum(5 for e in important_entities if e in types)
    entity_coverage = min(entity_coverage, 20)

    trust = 0
    trust += 10 if signals["reviewed"] else 0
    trust += 10 if signals["pi"] else 0
    trust += 5 if signals["medguide"] else 0

    evidence = 0
    evidence += 10 if signals["pubmed"] else 0
    evidence += 10 if signals["doi"] else 0
    evidence += 5 if signals["references"] else 0

    compliance = 10 if signals["adverse"] else 0
    crawl = 10 if status == 200 else 0

    total = schema_diversity + entity_coverage + trust + evidence + compliance + crawl
    return min(total, 100), {
        "schema_diversity": schema_diversity,
        "entity_coverage": entity_coverage,
        "trust": trust,
        "evidence": evidence,
        "compliance": compliance,
        "crawl": crawl
    }


# ------------------------------------------------------------
# ENTITY AUTHORITY INDEX
# ------------------------------------------------------------

def entity_authority_index(types):
    score = 0
    if "Drug" in types:
        score += 20
    if "MedicalCondition" in types:
        score += 20
    if "MedicalTherapy" in types:
        score += 20
    if "FAQPage" in types:
        score += 20
    if len(types) > 5:
        score += 20
    return score


# ------------------------------------------------------------
# AI OVERVIEW SIMULATION
# ------------------------------------------------------------

def simulate_ai_summary(domain, types):
    if "Drug" in types and "MedicalCondition" in types:
        return f"{domain} is structured with explicit drug and condition entities, increasing likelihood of AI citation."
    return f"{domain} lacks full medical entity modeling and may be summarized generically by AI systems."


# ------------------------------------------------------------
# IDEAL OUTPUT NOTES
# ------------------------------------------------------------

def ideal_output_notes(score):
    if score >= 80:
        return "High MCP readiness. Likely strong AI visibility. Focus on competitive comparison schema."
    elif score >= 60:
        return "Moderate readiness. Improve citations, reviewedBy, and FAQ modeling."
    elif score >= 40:
        return "Weak medical structuring. Add MedicalCondition + Drug graph modeling."
    else:
        return "Low MCP readiness. Requires structured schema overhaul."


# ------------------------------------------------------------
# STREAMLIT APP
# ------------------------------------------------------------

st.set_page_config(layout="wide")
st.title("BioGraph MCP – Pharma SEO/GEO Intelligence Engine v2")

with st.sidebar:
    domains_input = st.text_area("Competitor Domains",
                                 value="nucala.com\ndupixent.com\nfasenra.com\ntezspire.com\ncinqaero.com")

    target1 = st.text_input("Target URL 1")
    target2 = st.text_input("Target URL 2")
    target3 = st.text_input("Target URL 3")

    use_js = st.checkbox("Enable JS Rendering (Playwright)", value=False)
    run = st.button("Run Full MCP Analysis")

if run:
    domains = [d.strip() for d in domains_input.split("\n") if d.strip()]
    results = []

    for domain in domains:
        url = domain if domain.startswith("http") else f"https://{domain}"
        html, status = fetch_page(url, use_js)

        jsonld = extract_jsonld(html)
        types = flatten_types(jsonld)
        signals = extract_signals(html)

        score, breakdown = compute_score(types, signals, status)
        eai = entity_authority_index(types)

        results.append({
            "domain": domain,
            "MCP Score": score,
            "Entity Authority Index": eai,
            "Schema Types": ", ".join(types),
            "AI Simulation": simulate_ai_summary(domain, types),
            "Ideal Recommendation": ideal_output_notes(score),
            **breakdown
        })

    df = pd.DataFrame(results)
    st.subheader("MCP Competitor Scorecard")
    st.dataframe(df)

    st.download_button("Download CSV", df.to_csv(index=False), "mcp_scorecard.csv")

    # Radar
    if not df.empty:
        row = df.iloc[0]
        categories = ["schema_diversity", "entity_coverage", "trust", "evidence", "compliance", "crawl"]
        values = [row[c] for c in categories]
        values += values[:1]
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]

        fig = plt.figure()
        ax = fig.add_subplot(111, polar=True)
        ax.plot(angles, values)
        ax.fill(angles, values, alpha=0.3)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        st.pyplot(fig)

    # Manifest
    st.subheader("Generated MCP Manifest")
    manifest = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Xolair",
        "hasPart": [target1, target2, target3]
    }
    st.code(json.dumps(manifest, indent=2), language="json")

    st.subheader("Executive Summary")
    avg_score = df["MCP Score"].mean()
    st.write(f"Average competitor MCP readiness: {round(avg_score,1)} / 100")
    st.write("Higher structural authority increases likelihood of generative citation and AI overview inclusion.")

