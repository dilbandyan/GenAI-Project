#!/usr/bin/env python3
"""
analytics.py — Run 12 analytical queries against analytics.db
              and save results to analytics_results.json.

Usage:
    python3 analytics.py
    python3 analytics.py --db analytics.db --out analytics_results.json
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Query definitions
# ---------------------------------------------------------------------------

QUERIES = {

    "daily_cost": (
        "Total cost_usd per calendar day",
        """
        SELECT
            DATE(timestamp)  AS day,
            ROUND(SUM(cost_usd), 4) AS total_cost_usd
        FROM api_requests
        WHERE timestamp IS NOT NULL
        GROUP BY day
        ORDER BY day
        """,
    ),

    "cost_by_model": (
        "Total cost_usd and request count by model",
        """
        SELECT
            model,
            ROUND(SUM(cost_usd), 4) AS total_cost_usd,
            COUNT(*)                AS request_count
        FROM api_requests
        GROUP BY model
        ORDER BY total_cost_usd DESC
        """,
    ),

    "cost_by_practice": (
        "Total cost_usd by engineering practice",
        """
        SELECT
            e.practice,
            ROUND(SUM(r.cost_usd), 4) AS total_cost_usd
        FROM api_requests r
        JOIN employees e ON r.user_email = e.email
        GROUP BY e.practice
        ORDER BY total_cost_usd DESC
        """,
    ),

    "cost_by_level": (
        "Total cost_usd by employee seniority level",
        """
        SELECT
            e.level,
            ROUND(SUM(r.cost_usd), 4) AS total_cost_usd
        FROM api_requests r
        JOIN employees e ON r.user_email = e.email
        GROUP BY e.level
        ORDER BY e.level
        """,
    ),

    "tokens_by_model": (
        "Average input / output / cache_read tokens by model",
        """
        SELECT
            model,
            ROUND(AVG(input_tokens),      1) AS avg_input_tokens,
            ROUND(AVG(output_tokens),     1) AS avg_output_tokens,
            ROUND(AVG(cache_read_tokens), 1) AS avg_cache_read_tokens
        FROM api_requests
        GROUP BY model
        ORDER BY model
        """,
    ),

    "top_users_by_cost": (
        "Top 10 users by total spend",
        """
        SELECT
            r.user_email,
            e.full_name,
            e.practice,
            e.level,
            ROUND(SUM(r.cost_usd), 4) AS total_cost_usd,
            COUNT(*)                  AS request_count
        FROM api_requests r
        JOIN employees e ON r.user_email = e.email
        GROUP BY r.user_email
        ORDER BY total_cost_usd DESC
        LIMIT 10
        """,
    ),

    "hourly_activity": (
        "API request count by hour of day (0–23)",
        """
        SELECT
            CAST(STRFTIME('%H', timestamp) AS INTEGER) AS hour,
            COUNT(*) AS request_count
        FROM api_requests
        WHERE timestamp IS NOT NULL
        GROUP BY hour
        ORDER BY hour
        """,
    ),

    "tool_usage_frequency": (
        "Decision-type tool events counted by tool_name, descending",
        """
        SELECT
            tool_name,
            COUNT(*) AS decision_count
        FROM tool_events
        WHERE event_type = 'decision'
        GROUP BY tool_name
        ORDER BY decision_count DESC
        """,
    ),

    "tool_success_rate": (
        "Success rate per tool_name for result-type tool events",
        """
        SELECT
            tool_name,
            COUNT(*)                                     AS total_results,
            SUM(success)                                 AS successful,
            ROUND(100.0 * SUM(success) / COUNT(*), 2)   AS success_rate_pct
        FROM tool_events
        WHERE event_type = 'result'
          AND success IS NOT NULL
        GROUP BY tool_name
        ORDER BY success_rate_pct DESC
        """,
    ),

    "error_rate_by_model": (
        "API error count vs request count, and error rate, by model",
        """
        SELECT
            r.model,
            COUNT(DISTINCT r.event_id)                              AS total_requests,
            COUNT(DISTINCT e.event_id)                             AS total_errors,
            ROUND(100.0 * COUNT(DISTINCT e.event_id)
                       / COUNT(DISTINCT r.event_id), 4)            AS error_rate_pct
        FROM api_requests r
        LEFT JOIN api_errors e ON r.model = e.model
        GROUP BY r.model
        ORDER BY error_rate_pct DESC
        """,
    ),

    "avg_session_length": (
        "Average number of user prompts per session",
        """
        SELECT
            ROUND(AVG(prompt_count), 2) AS avg_prompts_per_session,
            COUNT(*)                    AS total_sessions,
            SUM(prompt_count)           AS total_prompts
        FROM (
            SELECT session_id, COUNT(*) AS prompt_count
            FROM user_prompts
            WHERE session_id IS NOT NULL
            GROUP BY session_id
        )
        """,
    ),

    "sessions_by_practice": (
        "Distinct session count by engineering practice",
        """
        SELECT
            e.practice,
            COUNT(DISTINCT p.session_id) AS session_count
        FROM user_prompts p
        JOIN employees e ON p.user_email = e.email
        GROUP BY e.practice
        ORDER BY session_count DESC
        """,
    ),
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_query(conn: sqlite3.Connection, name: str, description: str, sql: str) -> list:
    try:
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        return rows
    except sqlite3.Error as exc:
        print(f"  [ERROR] {name}: {exc}", file=sys.stderr)
        return []


def fmt_value(v):
    if isinstance(v, float):
        return f"{v:,.4f}".rstrip("0").rstrip(".")
    if isinstance(v, int):
        return f"{v:,}"
    return str(v) if v is not None else "—"


def print_result(name: str, description: str, rows: list):
    print(f"\n{'─' * 60}")
    print(f"  {name}")
    print(f"  {description}")
    print(f"{'─' * 60}")
    if not rows:
        print("  (no data)")
        return
    cols = list(rows[0].keys())
    # column widths
    widths = {c: max(len(c), *(len(fmt_value(r[c])) for r in rows)) for c in cols}
    header = "  " + "  ".join(c.ljust(widths[c]) for c in cols)
    print(header)
    print("  " + "  ".join("-" * widths[c] for c in cols))
    for row in rows:
        print("  " + "  ".join(fmt_value(row[c]).ljust(widths[c]) for c in cols))
    print(f"  ({len(rows)} row{'s' if len(rows) != 1 else ''})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run analytics queries on analytics.db.")
    parser.add_argument("--db",  default="analytics.db",          help="SQLite database path")
    parser.add_argument("--out", default="analytics_results.json", help="Output JSON path")
    args = parser.parse_args()

    db_path  = Path(args.db)
    out_path = Path(args.out)

    if not db_path.exists():
        print(f"ERROR: database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = None  # we build dicts manually for clarity

    results = {}

    print(f"Running {len(QUERIES)} queries against {db_path} …")

    for name, (description, sql) in QUERIES.items():
        rows = run_query(conn, name, description, sql)
        results[name] = rows
        print_result(name, description, rows)

    conn.close()

    # --- Save JSON ---
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n{'═' * 60}")
    print(f"  Results saved to {out_path}")
    print(f"  Queries run:     {len(QUERIES)}")
    total_rows = sum(len(v) for v in results.values())
    print(f"  Total rows:      {total_rows:,}")
    print(f"{'═' * 60}")


if __name__ == "__main__":
    main()
