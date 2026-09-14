"""
Re:Nova Verification Engine — interactive Streamlit demo.

Sidebar: choose an example brand OR answer the intake questions live.
Main area: metric cards, tabbed views (Relevance / Risk / Business Summary),
with a plotly gauge and bar chart for visual interactivity.

Setup:
  pip install streamlit groq python-dotenv plotly
  .env file in repo root: GROQ_API_KEY=your_key_here
Run:
  streamlit run app.py
"""
import os
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv
from groq import Groq

from src.models import Session
from src.framework_matcher import match_frameworks
from src.greenwashing import run_greenwashing_check

load_dotenv()
CACHE_PATH = "business_summaries_cache.json"

st.set_page_config(page_title="Re:Nova Verification Demo", layout="wide", page_icon="🌿")

# ── Minimal custom styling ────────────────────────────────────────────────────
st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 12px 16px;
    }
    .flag-critical { border-left: 4px solid #e5484d; padding: 8px 12px; margin-bottom: 6px; background: rgba(229,72,77,0.08); border-radius: 4px; }
    .flag-moderate { border-left: 4px solid #f5a623; padding: 8px 12px; margin-bottom: 6px; background: rgba(245,166,35,0.08); border-radius: 4px; }
    .flag-low      { border-left: 4px solid #6b7280; padding: 8px 12px; margin-bottom: 6px; background: rgba(107,114,128,0.08); border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ── Cache helpers ─────────────────────────────────────────────────────────────

def load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict) -> None:
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def build_session(answers: dict) -> Session:
    s = Session()
    for qid, ans in answers.items():
        if ans:
            s.record_answer(qid, ans)
    return s


def generate_business_summary(cache_key: str, relevance_rows: list, flag_rows: list, overall_risk: str,
                               use_cache: bool = True) -> str:
    cache = load_cache()
    if use_cache and cache_key in cache:
        return cache[cache_key]

    api_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", None)
    if not api_key:
        return ("⚠️ No cached summary available and no GROQ_API_KEY set — "
                "add a .env file with your own key to generate one live.")

    client = Groq(api_key=api_key)
    prompt = f"""You are helping a sustainability analytics platform explain verification
results to a business stakeholder (not a technical audience).

Overall greenwashing risk rating: {overall_risk}

Relevant certification frameworks identified:
{relevance_rows}

Greenwashing flags raised (internal, not shown to the brand):
{flag_rows}

In 3-4 sentences, explain in plain business language what this verdict means:
should this brand be listed on the platform, flagged for review, or blocked?
What specific evidence drives that recommendation? Be concrete and concise."""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=300,
    )
    summary = response.choices[0].message.content

    if use_cache:
        cache[cache_key] = summary
        save_cache(cache)
    return summary


# ── Example brand data ────────────────────────────────────────────────────────

EXAMPLE_BRANDS = {
    "Clean brand": {
        "O-1.1": "Our mission is sustainable, ethical fashion with social and environmental impact at its core.",
        "O-1.3": "We are pursuing B Corp certification.",
        "O-1.4": "organic, fair trade, artisan, transparent",
        "O-1.5": "Yes, we publish our supplier list and full pricing breakdown.",
        "O-2.1": "organic cotton, silk",
        "O-2.2": "100% natural fibres",
        "O-2.3": "No recycled materials used.",
        "O-2.4": "No",
        "O-2.6": "Yes, GOTS certified.",
        "O-2.7": "Yes, fully traceable, country and facility of origin confirmed.",
        "O-2.8": "No synthetic dyes, natural dyeing only.",
        "O-2.9": "No",
        "O-2.10": "Yes, hand-embroidered by artisans.",
        "O-2.11": "India, sells to Switzerland and Germany.",
        "O-3.1": "1 cooperative",
        "O-3.2": "Yes, we work with a women's artisan cooperative.",
        "O-3.3": "Yes, confirmed above minimum wage, third-party audited.",
        "O-3.4": "Yes, confirmed via annual audit, no child or forced labour.",
        "O-4.1": "Full cost breakdown provided: materials 40%, labour 30%, overhead 30%.",
    },
    "Red-flag brand": {
        "O-1.1": "We sell affordable, trendy clothing for every season.",
        "O-1.3": "",
        "O-1.4": "organic, ethical, fair trade, artisan, transparent, handmade",
        "O-1.5": "No, we do not share supplier details.",
        "O-2.1": "cotton blend",
        "O-2.2": "roughly 50% cotton",
        "O-2.3": "No recycled content.",
        "O-2.4": "No",
        "O-2.6": "No certificate, we are unsure of organic status.",
        "O-2.7": "No, we don't track country of origin.",
        "O-2.8": "Synthetic dyes used across most lines.",
        "O-2.9": "No",
        "O-2.10": "No",
        "O-2.11": "Factories in Bangladesh, sells worldwide.",
        "O-3.1": "5 factories",
        "O-3.2": "No",
        "O-3.3": "We cannot confirm current wage levels at all facilities.",
        "O-3.4": "We are unsure and cannot confirm absence of child or forced labour.",
        "O-4.1": "",
    },
    "Amber brand": {
        "O-1.1": "Our mission is to make quality, timeless pieces with environmental awareness in mind.",
        "O-1.3": "",
        "O-1.4": "recycled, traceable",
        "O-1.5": "Yes, we share some supply chain information.",
        "O-2.1": "primarily polyester, small cotton trim",
        "O-2.2": "mostly synthetic, small natural share",
        "O-2.3": "We are still evaluating suppliers; no such materials used yet.",
        "O-2.4": "No",
        "O-2.6": "",
        "O-2.7": "Partially — we know the country but not the specific facility.",
        "O-2.8": "Some synthetic dyes used.",
        "O-2.9": "No",
        "O-2.10": "No",
        "O-2.11": "Vietnam factory, sells to UK and US.",
        "O-3.1": "3 factories",
        "O-3.2": "No",
        "O-3.3": "",
        "O-3.4": "Yes, confirmed via third-party audit, no child or forced labour.",
        "O-4.1": "",
    },
}

# Field labels + guidance text — sourced directly from questions_stage1.py
# (the real Stage 1 methodology), grouped by the actual 4 pillars.
FIELD_GROUPS = {
    "Pillar 1 — Company": {
        "O-1.1": ("What is your company's core mission? Does it explicitly reference social or environmental purpose?",
                   "A few sentences is sufficient. We are not looking for polished language — we want to understand what drives the company."),
        "O-1.2": ("Do you currently hold any third-party sustainability certification or label? If yes, please list them.",
                   "Include any certification at any level: product, supply chain, company-wide, or craft-specific (e.g. Handloom Mark, Craftmark, GOTS, Fair Trade, B Corp, SA8000)."),
        "O-1.3": ("Are you currently pursuing any certification? If yes, which one and at what stage?",
                   "This helps us understand your certification trajectory and prioritise which readiness analysis is most useful to you."),
        "O-1.4": ("What sustainability claims do you currently make in your marketing, on your website, or on product labels?",
                   'Examples: "organic cotton", "Fair Trade", "handmade", "zero waste", "carbon neutral", "sustainable". Please list every claim you make, however small.'),
        "O-1.5": ("Do you publicly disclose your supplier list? And do you disclose what proportion of your retail price reaches the artisan or producer?",
                   "Neither disclosure is currently required by law for brands of this size. Both are voluntary and signal a high level of transparency."),
    },
    "Pillar 2 — Product & Materials": {
        "O-2.1": ("Please list all primary materials and fibres used in your products. For each, what is the approximate percentage of total material use?",
                   "Include everything: cotton, silk, linen, wool, polyester, recycled polyester, leather, viscose, modal, jute, bamboo, etc."),
        "O-2.2": ("What percentage of your total material use comes from natural fibres — cotton, silk, linen, wool, jute?",
                   "Natural fibres are the key eligibility criterion for several certifications including GOTS."),
        "O-2.3": ("Do any of your products contain recycled content? If yes, what material and approximately what percentage?",
                   "Recycled polyester (rPET), recycled cotton, recycled wool, regenerated fibres."),
        "O-2.4": ("Do any of your products contain leather — including leather accessories, trims, or components?",
                   "Including leather accessories, trims, or components."),
        "O-2.5": ("Do any of your products use animal-derived materials — wool, silk, down, or leather? For wool: can you confirm your supply chain is free from mulesed sheep?",
                   "Mulesing is prohibited under GOTS. If unsure of your wool's origin or breed, please state this."),
        "O-2.6": ("Do you source certified organic fibres? If yes, which certification covers the farms or the processing?",
                   "Farm-level (NPOP, NOP, EU Organic) is separate from processing certification (GOTS)."),
        "O-2.7": ("Can you trace each material back to its country of origin — where the fibre was grown or recycled material collected?",
                   "Country of origin means where the raw material originates, not where the fabric was woven."),
        "O-2.8": ("Do you use natural or botanical dyes? If yes, please describe the process briefly.",
                   "Natural dyes include plant-based, mineral-based, and fermentation-based processes."),
        "O-2.9": ("Are any of your products made using handloom weaving? If yes, which techniques?",
                   "For example Jamdani, Ikat, Banarasi, or Chanderi."),
        "O-2.10": ("Are any products made using traditional handcraft techniques beyond weaving?",
                    "E.g. block printing, embroidery, hand-knitting, natural dyeing, or hand-spinning."),
        "O-2.11": ("What is the country and specific region of manufacture for each main product category?",
                    'E.g. "Block-printed kurtas — Bagru, Rajasthan." District level is ideal.'),
    },
    "Pillar 3 — Supply Chain": {
        "O-3.1": ("How many production suppliers do you work with in total?",
                   "These are your Tier 1 suppliers — direct commercial relationships."),
        "O-3.2": ("Do you work with artisan cooperatives, self-help groups, NGO-affiliated producer groups, or Fair Trade-certified producers?",
                   "If yes, please name the group(s) and describe the relationship briefly."),
        "O-3.3": ("To the best of your knowledge, do all workers in your supply chain receive at least the legal minimum wage?",
                   "If unsure, state this honestly — more useful than an assumed yes."),
        "O-3.4": ("Do you have evidence that no child labour or forced labour is used in your supply chain?",
                   "Evidence can be a supplier declaration, audit, or direct knowledge. Unsure is acceptable."),
    },
    "Pillar 4 — Financial & Commercial": {
        "O-4.1": ("What is the artisan or producer's share of your retail price? Can you give an approximate cost breakdown?",
                   'E.g. "roughly 20% goes to the maker, 15% materials, 10% logistics, 55% our margin."'),
        "O-4.2": ("What are your standard payment terms with suppliers? Advance, on delivery, or extended credit?",
                   "Standard is 30–60 days after delivery. Advance payment is best practice for home-based producers."),
    },
}


# ── Sidebar ────────────────────────────────────────────────────────────────────

st.sidebar.title("🌿 Re:Nova")
st.sidebar.caption("Verification engine controls")

mode = st.sidebar.radio("Mode", ["Example brand", "Answer questions live"])

st.sidebar.caption(
    ":gray[If you click **Example brand**, you'll instantly see results for one "
    "of 3 pre-built sample brands. If you click **Answer questions live**, you'll "
    "fill in your own answers and get a real-time verdict.]"
)


session = None
cache_key = None
use_cache = True

if mode == "Example brand":
    brand_label = st.sidebar.selectbox("Select an example brand", list(EXAMPLE_BRANDS.keys()))
    session = build_session(EXAMPLE_BRANDS[brand_label])
    cache_key = brand_label
    use_cache = True
else:
    st.sidebar.info("Fill in what you know — leave fields blank to skip them.")
    live_answers = {}
    with st.sidebar.form("live_intake_form"):
        for group_name, fields in FIELD_GROUPS.items():
            with st.expander(group_name, expanded=False):
                for qid, (question_text, guidance) in fields.items():
                    live_answers[qid] = st.text_area(
                        question_text, key=f"live_{qid}", height=60, help=guidance
                    )
        submitted = st.form_submit_button("Run verification")
    if submitted:
        session = build_session(live_answers)
        cache_key = None   # live answers aren't cached — always a fresh call
        use_cache = False
        st.session_state["live_session_ready"] = True
        st.session_state["live_last_answers"] = live_answers
    elif st.session_state.get("live_session_ready") and "live_last_answers" in st.session_state:
        session = build_session(st.session_state["live_last_answers"])
        cache_key = None
        use_cache = False


# ── Main area ──────────────────────────────────────────────────────────────────

st.title("Re:Nova Verification Engine")
st.caption("Certification relevance matching + greenwashing risk assessment, with an AI-generated business summary.")

if session is None:
    st.info("👈 Choose an example brand, or switch to live mode and submit the intake form.")
    st.stop()

relevance_result = match_frameworks(session)
assessment = run_greenwashing_check(session)
overall = assessment.overall_risk.value.upper()

relevance_rows = [
    {"Rank": e.priority_rank, "Framework": e.acronym, "Reason": e.reason}
    for e in relevance_result.relevant_frameworks[:10]
]
flag_rows = [
    {"Priority": f.priority.value.upper(), "Claim": f.claim, "Flag": f.flag_message, "Status": f.status.value}
    for f in assessment.flags
]

critical_n = sum(1 for f in assessment.flags if f.priority.value == "critical")
moderate_n = sum(1 for f in assessment.flags if f.priority.value == "moderate")
low_n = sum(1 for f in assessment.flags if f.priority.value == "low")

# ── Metric row ──────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
risk_emoji = {"GREEN": "🟢", "AMBER": "🟠", "RED": "🔴"}.get(overall, "")
m1.metric("Overall risk", f"{risk_emoji} {overall}")
m2.metric("Critical flags", critical_n)
m3.metric("Moderate flags", moderate_n)
m4.metric("Relevant frameworks", len(relevance_result.relevant_frameworks))

st.divider()

tab1, tab2, tab3 = st.tabs(["📋 Certification Relevance", "🚩 Greenwashing Risk", "💬 Business Summary"])

with tab1:
    st.caption("Brand-facing output")
    if relevance_rows:
        df = pd.DataFrame(relevance_rows)
        fig = go.Figure(go.Bar(
            x=df["Rank"].max() + 1 - df["Rank"],
            y=df["Framework"],
            orientation="h",
            marker_color="#3F7D4E",
        ))
        fig.update_layout(
            title="Framework relevance (longer bar = higher rank)",
            xaxis_title="Relative rank", yaxis_title="",
            height=350, margin=dict(l=10, r=10, t=40, b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No relevant frameworks matched.")

with tab2:
    st.caption("Internal — not shown to the brand")
    gauge_value = {"GREEN": 20, "AMBER": 55, "RED": 90}.get(overall, 0)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=gauge_value,
        gauge={
            "axis": {"range": [0, 100], "visible": False},
            "bar": {"color": {"GREEN": "#3F7D4E", "AMBER": "#f5a623", "RED": "#e5484d"}.get(overall, "#888")},
            "steps": [
                {"range": [0, 33], "color": "rgba(63,125,78,0.25)"},
                {"range": [33, 66], "color": "rgba(245,166,35,0.25)"},
                {"range": [66, 100], "color": "rgba(229,72,77,0.25)"},
            ],
        },
        title={"text": f"Risk level: {overall}"},
    ))
    fig.update_layout(height=280, margin=dict(l=20, r=20, t=50, b=10),
                       paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
    st.plotly_chart(fig, use_container_width=True)

    if flag_rows:
        for f in assessment.flags:
            css_class = f"flag-{f.priority.value}"
            st.markdown(
                f'<div class="{css_class}"><b>{f.priority.value.upper()}</b> — {f.claim}<br>{f.flag_message}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.success("No flags raised.")

with tab3:
    with st.spinner("Generating summary..."):
        summary = generate_business_summary(cache_key or "live", relevance_rows, flag_rows, overall, use_cache)
    st.write(summary)

st.divider()
st.caption(
    "Note: certification matching and greenwashing checks use rule-based keyword/substring "
    "matching, not retrieval-augmented generation over the standards documents. "
    "See the report for a discussion of this limitation."
)