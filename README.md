# Sustainability Analytics — Microplastics in Swiss Textiles

## Project structure

```text
Sustainability-Analytics_Microplastics-in-Swiss-Textiles/
├── README.md
├── app.py                          # Streamlit demo — verification engine dashboard
├── run_demo.py                     # Non-interactive script: 3 example brands through the engine
├── requirements.txt
├── __init__.py
│
├── data/
│   ├── raw/
│   │   ├── EMPA_clothing_endpoints_summary.csv
│   │   ├── PET_clothing_sankey_data.csv
│   │   └── Plastics-by-Type_EMPA.csv
│   ├── processed/
│   │   ├── textile_apparel_imports.csv
│   │   └── textile_imports_by_year.csv
│   └── cache/
│       └── business_summaries_cache.json   # cached AI-generated summaries (see below)
│
├── src/                             # Re:Nova verification engine
│   ├── __init__.py
│   ├── models.py                    # Session, FrameworkEntry, GreenwashingFlag, etc.
│   ├── tools.py
│   ├── prompts.py
│   ├── framework_matcher.py         # certification relevance matching
│   ├── greenwashing.py              # greenwashing risk / flag logic
│   ├── questionnaire.py             # Stage 1 chatbot intake engine
│   └── questions_stage1.py          # the 21-question Stage 1 intake, by pillar
│
├── analysis/
│   ├── time_series_monthly.Rmd
│   ├── 01_filter_textile_imports.R
│   ├── 02_aggregate_by_year.R
│   ├── 03_clothing_sankey.R
│   └── 04_sensitivity_analysis.R
│
└── outputs/
    ├── time_series_monthly.html
    ├── time_series_monthly.tex
    └── logs/
        └── time_series_monthly.log
```

## Data pipeline (R)
Source: SwissImpex / BAZG customs data (opendata.swiss)

1. `01_filter_textile_imports.R` — streams the large CPA6 import file in chunks and keeps only textile (`CPA2 = C13`) and apparel (`CPA2 = C14`) rows → `data/processed/textile_apparel_imports.csv`
2. `02_aggregate_by_year.R` — aggregates to yearly totals and applies the Textile Exchange synthetic-fiber share (69%) → `data/processed/textile_imports_by_year.csv`
3. `03_clothing_sankey.R` — draws the clothing → wastewater → environment pathway diagram from the digitized Empa (Kawecki & Nowack, 2019) dataset
4. `04_sensitivity_analysis.R` — tornado/sensitivity analysis on the bottom-up pollution formula

## Headline figures
- **Bottom-up estimate:** ~95–98 t/yr (synthetic imports × washes/yr × shedding rate × (1 − WWTP capture rate)). *Not used as the headline slide figure* — the washing-frequency input (25 washes/kg/yr) lacks a real Swiss data source.
- **Headline figure used on slides:** Empa's validated top-down estimate of **4.6 t/yr** (PET+PP only, reproducing the source paper's 4.8 t figure), presented as a conservative lower bound.
- **Most influential parameter (sensitivity analysis):** WWTP capture rate.

## Verification engine (Python)

`src/` implements Re:Nova's Stage 1 brand verification logic, producing two outputs per brand:

1. **Certification Relevance Map** (`framework_matcher.py`) — brand-facing. Matches a brand's disclosed materials, supply chain, and claims against ~15–26 sustainability certification frameworks (GOTS, OEKO-TEX, GRS, SA8000, ZDHC, B Corp, etc.), each with a plain-language reason.
2. **Greenwashing Risk Assessment** (`greenwashing.py`) — internal only. Cross-checks a brand's public marketing claims against the evidence given elsewhere in the intake, raising Critical/Moderate/Low flags and an overall Green/Amber/Red risk rating.

**Important limitation:** both modules use rule-based **keyword/substring matching** against structured questionnaire answers not retrieval-augmented generation (RAG) over the actual standards documents, and not semantic understanding. This is a deliberate, timeline-driven scope decision, not an oversight. A known consequence: substring matching can produce false positives from negated statements e.g. a brand stating "No recycled materials used" can still be matched to GRS, because the word "recycled" is present regardless of the negation. See the report for a full discussion.

### Demo scripts

- **`run_demo.py`** — runs 3 illustrative example brands (Clean / Red-flag / Amber) through the full engine and prints the Certification Relevance Map + Greenwashing Risk Assessment for each. No API key required.
- **`app.py`** — interactive Streamlit dashboard. Pick one of the 3 example brands, or fill in your own answers to the live intake form. Shows the relevance map, a risk gauge with flags, and an AI-generated (Groq) plain-language business summary of what the verdict means. The 3 example brands' summaries are pre-cached in `data/cache/business_summaries_cache.json`, so the app works instantly for anyone running it. No API key needed unless you use the live-input mode.

## Key sources
- SwissImpex / BAZG customs data — opendata.swiss
- Kawecki & Nowack (2019) — Empa material-flow model
- De Falco et al. (2021) — fiber shedding rates
- Conley et al.; Kaegi et al. — WWTP capture rates
- Resortecs, *From Waste to Profit* (2023) — Design for Disassembly

## Setup

**R** (pipeline, diagrams, sensitivity analysis)
```r
install.packages(c("readr", "dplyr", "networkD3"))
```

**Python** (verification engine + Streamlit demo)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

To use the AI-generated business summary in live-input mode, create a `.env` file in the repo root:
```
GROQ_API_KEY=your_key_here
```
Get a free key at [console.groq.com](https://console.groq.com) no billing required. The 3 example brands work without a key, since their summaries are pre-cached.

### Running the demo

```bash
# Non-interactive: print all 3 example brands' results to console
python3 run_demo.py

# Interactive dashboard
streamlit run app.py
```
