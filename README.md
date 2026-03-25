# Claude Code Usage Analytics Platform

## Project Overview

An end-to-end analytics platform for Claude Code telemetry — Anthropic's CLI tool for AI-assisted software engineering. The platform covers the full data lifecycle: synthetic data generation, structured ingestion into SQLite, 12 pre-computed SQL metrics, and an interactive five-tab Streamlit dashboard that includes machine learning forecasting and anomaly detection. It is designed to give engineering leaders clear visibility into AI tool adoption, cost distribution, developer behaviour patterns, and forward-looking spend projections.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌──────────────────────┐                                               │
│  │  generate_fake_data  │                                               │
│  │       .py            │                                               │
│  └──────────┬───────────┘                                               │
│             │                                                           │
│     ┌───────┴────────┐                                                  │
│     ▼                ▼                                                  │
│  telemetry_       employees                                             │
│  logs.jsonl          .csv                                               │
│     │                │                                                  │
│     └───────┬────────┘                                                  │
│             ▼                                                           │
│       ┌──────────┐                                                      │
│       │ ingest   │  · parses double-nested JSONL                        │
│       │   .py    │  · joins employee records                            │
│       │          │  · loads 5 normalised tables                         │
│       └────┬─────┘                                                      │
│            │                                                            │
│            ▼                                                            │
│       analytics.db                                                      │
│       (SQLite)                                                          │
│            │                                                            │
│            ▼                                                            │
│      ┌───────────┐                                                      │
│      │ analytics │  · 12 SQL queries                                    │
│      │    .py    │  · aggregations, joins, time bucketing               │
│      └─────┬─────┘                                                      │
│            │                                                            │
│            ▼                                                            │
│   analytics_results.json                                                │
│            │                                                            │
│            ▼                                                            │
│      ┌─────────────┐       ┌────────────────────────────────────────┐  │
│      │ dashboard   │──────▶│  Streamlit UI                          │  │
│      │    .py      │       │                                        │  │
│      └─────────────┘       │  Tab 1 · Overview                     │  │
│                            │  Tab 2 · Model Analysis                │  │
│                            │  Tab 3 · Developer Behavior            │  │
│                            │  Tab 4 · Team Insights                 │  │
│                            │  Tab 5 · Predictive Analytics          │  │
│                            └──────────────────┬─────────────────────┘  │
│                                               │                        │
│                                               ▼                        │
│                                        scikit-learn                    │
│                                        · LinearRegression              │
│                                        · RandomForestClassifier        │
│                                        · IsolationForest               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Setup Instructions

### Requirements

- Python 3.9 or higher
- No external dependencies for `generate_fake_data.py` or `ingest.py` (standard library only)

### Install dependencies

```bash
pip install streamlit plotly pandas scikit-learn
```

### Run the pipeline

**Step 1 — Generate synthetic telemetry data**

```bash
python3 generate_fake_data.py --num-users 100 --num-sessions 5000 --days 60
```

Produces `output/telemetry_logs.jsonl` (~521 MB, ~454k events) and `output/employees.csv` (100 engineers).

**Step 2 — Ingest into SQLite**

```bash
python3 ingest.py
```

Parses and loads all events into `analytics.db`. Fully idempotent — safe to re-run without duplicating data.

**Step 3 — Run analytical queries**

```bash
python3 analytics.py
```

Executes 12 queries against `analytics.db` and writes results to `analytics_results.json`.

**Step 4 — Launch the dashboard**

```bash
streamlit run dashboard.py
```

Opens the interactive dashboard at `http://localhost:8501`.

---

## Project Structure

```
claude-code-analytics/
│
├── generate_fake_data.py       # Synthetic data generator (stdlib only)
├── ingest.py                   # JSONL + CSV → SQLite ingestion pipeline
├── analytics.py                # SQL query runner → analytics_results.json
├── dashboard.py                # Streamlit dashboard (5 tabs + ML)
│
├── output/
│   ├── telemetry_logs.jsonl    # Raw CloudWatch-style event batches
│   └── employees.csv           # Employee directory (100 engineers)
│
├── analytics.db                # SQLite database (generated by ingest.py)
├── analytics_results.json      # Query results cache (generated by analytics.py)
│
└── README.md
```

---

## Dashboard Tabs

### Tab 1 — Overview
Top-level health metrics for the 60-day period: total spend, session count, total API requests, and average session length. A filled area line chart shows daily cost over time; a horizontal bar chart breaks spend down by engineering practice. Sidebar filters for Practice and Model propagate across all tabs.

### Tab 2 — Model Analysis
Bar chart of total cost and request count per model, a grouped bar chart comparing average input, output, and cache-read token counts side by side, and a tabular error-rate breakdown by model showing request volume, error count, and error-rate percentage.

### Tab 3 — Developer Behavior
Hourly API request distribution across the 24-hour clock, a top-10 horizontal bar chart of tool usage by decision count, a colour-graduated success-rate chart per tool, and a filterable table of the top 10 highest-spending developers including their practice and seniority.

### Tab 4 — Team Insights
Cost distribution across seniority levels L1–L10, session counts by engineering practice, and a merged summary table showing total cost, session count, and derived cost-per-session per practice — useful for normalised team comparisons.

### Tab 5 — Predictive Analytics
Four ML-powered components built with scikit-learn:

| Component | Method | Output |
|---|---|---|
| Cost Forecasting | Linear Regression | 14-day projected cost with uncertainty band |
| Anomaly Detection | 2-σ threshold | Flags unusual spend days on the historical chart |
| High-Cost User Prediction | Random Forest | Feature importance chart (request count, practice, level) |
| Usage Spike Detection | Isolation Forest | Flags anomalous hours in red on the activity chart |

---

## Key Insights

- **Business hours dominate usage** — request volume peaks sharply at 16:00–17:00 UTC with a sustained concentration from 09:00–18:00, reflecting end-of-workday coding sessions across time zones.
- **Opus models drive the majority of spend** — despite a smaller share of requests, claude-opus models account for over 70% of total cost; Haiku handles ~39% of requests at roughly 3% of spend.
- **Cache reads significantly reduce effective token cost** — Opus and Sonnet models average 70,000–78,000 cache-read tokens per request, far exceeding raw input tokens and absorbing the bulk of context overhead.
- **Read and Bash are the most-used tools** — together accounting for over 89,000 decisions, confirming a code-read-then-execute loop as the dominant agentic workflow pattern.
- **ML Engineering and Frontend Engineering lead total spend** — both practices exceeded $1,470 over the 60-day period; Platform Engineering spent roughly half that amount.
- **Mid-level engineers (L5–L6) generate the most usage** — this cohort accounts for the highest cumulative cost, indicating they are the primary power users integrating Claude Code into daily workflows.
- **Linear regression forecasts a stable ~$98–100/day trend** — the cost trajectory shows no meaningful acceleration, indicating consistent team adoption rather than a usage spike or runaway spend.
- **Anomaly detection flagged 2 unusually expensive days** — both deviated more than 2 standard deviations from the 60-day mean, potentially corresponding to large batch jobs or end-of-sprint pushes worth investigating.
- **Random Forest identifies request count as the top predictor of high spend** — with ~45% feature importance, raw usage volume outweighs seniority level (~29%) and practice (~25%) in predicting whether a developer exceeds the median cost threshold.
- **Bash has the lowest tool success rate (~93%)** — all file-system tools (Read, Edit, Write, Grep) exceed 99%, pointing to shell command complexity and environment variability as the primary friction points in agentic sessions.

---

## Tech Stack

| Technology | Role |
|---|---|
| **Python 3.9+** | All pipeline scripts; standard library for ingestion and data generation |
| **SQLite / sqlite3** | Local analytical database; zero-infrastructure, file-based |
| **Streamlit** | Interactive web dashboard framework |
| **Plotly Express / Graph Objects** | Interactive charts across all five dashboard tabs |
| **Pandas** | DataFrame manipulation, melting, merging, and display formatting |
| **scikit-learn** | Linear Regression, Random Forest, Isolation Forest (Tab 5) |

---

## LLM Usage Log

### Tools Used

**Claude** (claude.ai) — Claude Sonnet via the claude.ai web interface, used throughout all phases of the project.

### How It Was Used

Claude was the primary development accelerator across every layer of the platform:

- **Schema and ingestion design** — defining the five-table SQLite schema, resolving the double-JSON nesting in the CloudWatch JSONL format, diagnosing a field-location bug where `user.email` lives in `attributes` rather than `resource`, and adding type coercions for string-encoded numeric fields.
- **SQL query authoring** — writing all 12 analytical queries including `STRFTIME`-based time bucketing, subquery patterns for session-length averaging, `LEFT JOIN` error-rate calculation, and `INSERT OR IGNORE` idempotency.
- **Dashboard architecture and styling** — designing the five-tab Streamlit layout, writing Plotly Express and Graph Objects configurations, and building a custom CSS theme with KPI cards, monospace section headers, and a dark sidebar.
- **Machine learning component design** — structuring the Predictive Analytics tab with four distinct models, selecting appropriate sklearn estimators, handling edge cases (insufficient data, string-encoded level fields), and writing the explanatory copy for each model's business interpretation.
- **Documentation** — drafting the README structure, ASCII architecture diagram, key insights, and this usage log.

### Example Prompts

1. *"Build a Python ingestion script called ingest.py that reads output/telemetry_logs.jsonl line by line… generate a stable event_id using hashlib.md5… use INSERT OR IGNORE to make it idempotent… print a summary at the end with row counts per table."*

2. *"Write a Python file called analytics.py that runs the following queries and saves results as a dict to analytics_results.json: [12 queries described in plain English including daily cost, cost by model, tokens by model, tool success rate, error rate by model, avg session length]."*

3. *"Build a Streamlit dashboard called dashboard.py using analytics_results.json… sidebar with Practice and Model multiselects… four pages as st.tabs… plotly.express for all charts… handle missing data gracefully… add a footer."*

4. *"Add a new Tab 5 called Predictive Analytics… linear regression on daily_cost for a 14-day forecast… 2-σ anomaly detection on cost… Random Forest classifier for high-cost user prediction with a feature importance chart… Isolation Forest on hourly_activity for spike detection… only show me the tab5 code block."*

### Validation Approach

- **End-to-end execution** — each script was run in sequence from a clean state and verified to complete without errors or warnings.
- **Row count cross-referencing** — dashboard KPI totals (118,014 API requests, 5,000 sessions, $6,001 total cost) were matched against `ingest.py` summary output and the raw generator event count.
- **Join correctness** — the practice and level breakdowns initially returned no data; the bug was confirmed by inspecting a raw log record, tracing the email field to `attributes["user.email"]`, and re-ingesting after the fix.
- **Query spot-checks** — daily cost values for selected dates were manually summed from `api_requests` and compared against `analytics_results.json` to confirm aggregate accuracy.
- **Visual inspection** — all five dashboard tabs were reviewed in the browser to confirm charts rendered correctly, sidebar filters applied as expected, and edge cases (empty filter selections, missing JSON keys) were handled gracefully.
- **Idempotency test** — `ingest.py` was run twice against the same `analytics.db`; row counts remained identical, confirming `INSERT OR IGNORE` behaviour.

---

*Data generated synthetically for demonstration purposes.*
