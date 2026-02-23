"""
Pharma MCP/GEO Intelligence Engine v4 - Generic Pharma Auditor
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
# PARSE FUNCTIONS (ORIGINAL + ENHANCED)
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

def compute_score(types, signals, status):
    """Base pharma E-E-A-T scoring"""
    schema_diversity = min(len(types) * 3, 30)
    entity_coverage = 0
    important_entities = ["Drug", "MedicalCondition", "MedicalWebPage", "FAQPage", "MedicalTrial"]
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

def compute_mcp_geo_score(types, signals, mcp_signals, status):
    """Full MCP/GEO score with agent handshake bonuses"""
    base_score, base_breakdown = compute_score(types, signals, status)
    
    # MCP/Agent bonuses
    mcp_bonus = min(mcp_signals["mcp_manifests"] * 15, 30)
    agent_bonus = min(mcp_signals["agent_functions"] * 2, 15)
    webmcp_bonus = 20 if mcp_signals["webmcp_ready"] else 0
    
    total = base_score + mcp_bonus + agent_bonus + webmcp_bonus
    return min(total, 100), {
        **base_breakdown,
        "mcp_bonus": mcp_bonus,
        "agent_bonus": agent_bonus,
        "webmcp_bonus": webmcp_bonus
    }

def entity_authority_index(types):
    """Medical entity authority scoring"""
    score = 0
    medical_entities = ["Drug", "MedicalCondition", "MedicalTherapy", "MedicalTrial", "FAQPage"]
    score += sum(20 for e in medical_entities if e in types)
    if len(types) > 5:
        score += 20
    return min(score, 100)

# ------------------------------------------------------------
# GENERIC PHARMA MCP TOOLS
# ------------------------------------------------------------

PHARMA_MCP_TOOLS = {
    "get_trial_eligibility": {
        "name": "get_trial_eligibility",
        "description": "Check patient eligibility for clinical trials by age, condition, location",
        "parameters": {
            "type": "object",
            "properties": {
                "age": {"type": "number"},
                "condition": {"type": "string"},
                "zip_code": {"type": "string"}
            }
        }
    },
    "check_coverage": {
        "name": "check_coverage",
        "description": "Verify insurance/pharmacy coverage by NDC, plan, location",
        "parameters": {
            "type": "object",
            "properties": {
                "ndc": {"type": "string"},
                "insurance_plan": {"type": "string"},
                "pharmacy_zip": {"type": "string"}
            }
        }
    },
    "get_dosing_schedule": {
        "name": "get_dosing_schedule",
        "description": "Return dosing schedule by patient weight, condition, administration route",
        "parameters": {
            "type": "object",
            "properties": {
                "patient_weight_kg": {"type": "number"},
                "condition": {"type": "string"}
            }
        }
    },
    "find_specialists": {
        "name": "find_specialists",
        "description": "Locate prescribing specialists by condition, location, insurance",
        "parameters": {
            "type": "object",
            "properties": {
                "condition": {"type": "string"},
                "zip_code": {"type": "string"},
                "insurance": {"type": "string"}
            }
        }
    }
}

def generate_pharma_mcp_manifest(target_urls, brand_name="Pharma Brand"):
    """Generate generic pharma MCP manifest"""
    manifest = {
        "@context": ["https://schema.org", "https://modelcontext.org"],
        "@type": "MedicalWebPage",
        "name": f"{brand_name} Agentic MCP Manifest",
        "mcpTools": list(PHARMA_MCP_TOOLS.values()),
        "optimizedPages": [
            {
                "url": target_urls[i] if i < len(target_urls) else "",
                "primaryTool": list(PHARMA_MCP_TOOLS.keys())[i % len(PHARMA_MCP_TOOLS)]
            } for i in range(min(3, len(target_urls)))
        ],
        "policy": {
            "hipaaCompliant": True,
            "reviewedBy": "Medical Affairs Team",
            "lastReviewed": "2026-02-23"
        }
    }
    return manifest

def generate_geo_schema(url, tool_name, brand_name="Pharma Brand"):
    """Generate GEO-optimized schema for specific page"""
    return {
        "@context": "https://schema.org",
        "@type": "MedicalWebPage",
        "url": url,
        "name": f"{brand_name} {tool_name.replace('_', ' ').title()}",
        "reviewedBy": {
            "@type": "MedicalProfessional",
            "name": f"{brand_name} Medical Team"
        },
        "mcpTool": PHARMA_MCP_TOOLS[tool_name]
    }

# ------------------------------------------------------------
# DOWNLOAD PACKAGE
# ------------------------------------------------------------

def create_download_package(target_urls, brand_name="Pharma Brand"):
    """Create complete MCP/GEO deployment package"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Main MCP Manifest
        manifest = generate_pharma_mcp_manifest(target_urls, brand_name)
        zip_file.writestr("mcp-manifest.json", json.dumps(manifest, indent=2))
        
        # Page-specific schemas
        for i, url in enumerate(target_urls[:3]):
            tool_name = list(PHARMA_MCP_TOOLS.keys())[i]
            schema = generate_geo_schema(url, tool_name, brand_name)
            zip_file.writestr(f"{tool_name}-schema.json", json.dumps(schema, indent=2))
        
        # Deployment guide
        guide = f"""PHARMA MCP/GEO DEPLOYMENT GUIDE - {brand_name}

1. Add MCP Manifest to <head> of all pages:
