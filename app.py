import streamlit as st
import requests
import json
import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

# Optional JS rendering
USE_PLAYWRIGHT = False
try:
    from playwright.sync_api import sync_playwright
    USE_PLAYWRIGHT = True
except:
    USE_PLAYWRIGHT = False


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

USER_AGENT = "BioGraphMCP/1.0 (+https://example.com)"
TIMEOUT = 20


# ------------------------------------------------------------
# FETCHING
# ------------------------------------------------------------

def fetch_static(url):
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        return r.text, r.status_code
    except:
        return "", 0


def fetch_js(url):
    if not USE_PLAYWRIGHT:
        return fetch_static(url)

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


def safe_url(domain):
    if domain.startswith("http"):
        return domain
    return f"https://{domain}/"


# ------------------------------------------------------------
# PARSING
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


def flatten_schema_types(jsonld):
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

    for item in jsonld:
        walk(item)

    return list(types)


def extract_signals(html):
    text = html.lower()
    return {
        "has_pi": "prescribing information" in text,
        "has_medguide": "medication guide" in text,
        "has_adverse": "adverse" in text or "side effects" in text,
        "has_pubmed": "pubmed" in text,
        "has_doi": bool(re.search(r"\b10\.\d{4,9}/", text)),
        "has_reviewed": "reviewed by" in text or "medically reviewed" in text,
        "has_references": "references" in text,
    }


# ------------------------------------------------------------
# SCORING
# ------------------------------------------------------------

def score_domain(schema_types, signals, status_ok):

    structured = min(len(schema_types) * 5, 30)

    trust = 0
    trust += 10 if signals["has_reviewed"] else 0
    trust += 10 if signals["has_pi"] else 0
    trust += 10 if signals["has_medguide"] else 0

    evidence = 0
    evidence += 10 if signals["has_pubmed"] else 0
    evidence += 10 if signals["has_doi"] else 0
    evidence += 10 if signals["has_references"] else 0

    compliance = 10 if signals["has_adverse"] else 0
    crawl = 10 if status_ok else 0

    overall = structured + trust + evidence + compliance + crawl
    return min(overall, 100)


# ------------------------------------------------------------
# RADAR CHART
# ------------------------------------------------------------

def radar_chart(row):
    categories = ["structured", "trust", "evidence", "compliance", "crawl"]
    values = [
        row["structured"],
        row["trust"],
        row["evidence"],
        row["compliance"],
        row["crawl"],
    ]

    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]

    fig = plt.figure()
    ax = fig.add_subplot(111, polar=True)
    ax.plot(angles, values)
    ax.fill(angles, values, alpha=0.2)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    return fig


# ------------------------------------------------------------
# MCP MANIFEST
# ------------------------------------------------------------

def generate_manifest(site_name, base_url, urls):
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site_name,
        "url": base_url,
        "hasPart": [
            {
                "@type": "MedicalWebPage",
                "url": u,
                "about": {"@type": "Drug", "name": "Xolair"},
            }
            for u in urls
        ],
    }


# ------------------------------------------------------------
# PAGE OPTIMIZATION
# ------------------------------------------------------------

def generate_page_schema(url):

    condition = "Allergic Disease"
    if "asthma" in url:
        condition = "Allergic Asthma"
    elif "hives" in url:
        condition = "Chronic Spontaneous Urticaria"
    elif "food" in url:
        condition = "IgE-mediated Food Allergy"

    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "MedicalWebPage",
                "url": url,
                "mainEntity": {
                    "@type": "MedicalCondition",
                    "name": condition,
                },
            },
            {
                "@type": "Drug",
                "name": "Xolair",
                "nonproprietaryName": "omalizumab",
            },
        ],
    }


# ------------------------------------------------------------
# STREAMLIT UI
# ------------------------------------------------------------

st.set_page_config(page_title="BioGraph MCP", layout="wide")

st.title("BioGraph MCP – Pharma SEO/GEO Intelligence Engine")

with st.sidebar:
    st.header("Inputs")

    competitors_input = st.text_area(
        "Competitor Domains",
        value="nucala.com\ndupixent.com\nfasenra.com\ntezspire.com\ncinqaero.com",
        height=150,
    )

    target1 = st.text_input("Target URL 1")
    target2 = st.text_input("Target URL 2")
    target3 = st.text_input("Target URL 3")

    use_js = st.checkbox("Enable JS Rendering (Playwright)", value=False)

    run = st.button("Run MCP Audit")

if run:

    competitors = [c.strip() for c in competitors_input.split("\n") if c.strip()]
    results = []

    for domain in competitors:
        url = safe_url(domain)
        html, status = fetch_js(url) if use_js else fetch_static(url)

        jsonld = extract_jsonld(html)
        schema_types = flatten_schema_types(jsonld)
        signals = extract_signals(html)

        overall = score_domain(schema_types, signals, status == 200)

        results.append({
            "domain": domain,
            "overall": overall,
            "structured": min(len(schema_types) * 5, 30),
            "trust": 30 if signals["has_reviewed"] else 0,
            "evidence": 30 if signals["has_pubmed"] else 0,
            "compliance": 10 if signals["has_adverse"] else 0,
            "crawl": 10 if status == 200 else 0,
            "schema_types": ", ".join(schema_types),
        })

    df = pd.DataFrame(results)
    st.subheader("Competitor MCP Scorecard")
    st.dataframe(df)

    if not df.empty:
        st.subheader("Radar Visualization")
        st.pyplot(radar_chart(results[0]))

    # Manifest
    st.subheader("Generated MCP Manifest")
    manifest = generate_manifest("Xolair", "https://www.xolair.com", [target1, target2, target3])
    st.code(json.dumps(manifest, indent=2), language="json")

    # Page Schemas
    st.subheader("Agent Handshake Schema")
    for t in [target1, target2, target3]:
        if t:
            schema = generate_page_schema(t)
            st.markdown(f"### {t}")
            st.code(json.dumps(schema, indent=2), language="json")

    # Export
    st.download_button("Download Scorecard CSV", df.to_csv(index=False), "mcp_scorecard.csv")
    st.download_button("Download Manifest JSON", json.dumps(manifest, indent=2), "mcp_manifest.json")
