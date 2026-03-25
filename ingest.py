#!/usr/bin/env python3
"""
ingest.py — Load Claude Code telemetry into analytics.db (SQLite).

Usage:
    python3 ingest.py
    python3 ingest.py --telemetry output/telemetry_logs.jsonl \
                      --employees output/employees.csv \
                      --db analytics.db
"""

import argparse
import csv
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS api_requests (
    event_id             TEXT PRIMARY KEY,
    session_id           TEXT,
    user_email           TEXT,
    timestamp            TEXT,
    model                TEXT,
    cost_usd             REAL,
    duration_ms          REAL,
    input_tokens         INTEGER,
    output_tokens        INTEGER,
    cache_read_tokens    INTEGER,
    cache_creation_tokens INTEGER
);

CREATE TABLE IF NOT EXISTS api_errors (
    event_id    TEXT PRIMARY KEY,
    session_id  TEXT,
    user_email  TEXT,
    timestamp   TEXT,
    model       TEXT,
    error       TEXT,
    status_code TEXT
);

CREATE TABLE IF NOT EXISTS tool_events (
    event_id        TEXT PRIMARY KEY,
    session_id      TEXT,
    user_email      TEXT,
    timestamp       TEXT,
    tool_name       TEXT,
    event_type      TEXT,
    decision        TEXT,
    decision_source TEXT,
    success         INTEGER,
    duration_ms     REAL
);

CREATE TABLE IF NOT EXISTS user_prompts (
    event_id   TEXT PRIMARY KEY,
    session_id TEXT,
    user_email TEXT,
    timestamp  TEXT
);

CREATE TABLE IF NOT EXISTS employees (
    email     TEXT PRIMARY KEY,
    full_name TEXT,
    practice  TEXT,
    level     TEXT,
    location  TEXT
);
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_event_id(raw_message: str) -> str:
    return hashlib.md5(raw_message.encode()).hexdigest()


def get_attr(attributes: dict, *keys, default=None):
    """Try multiple key names, return first match."""
    for k in keys:
        if k in attributes:
            return attributes[k]
    return default


def _float(v):
    try:
        return float(v) if v is not None else None
    except (ValueError, TypeError):
        return None

def _int(v):
    try:
        return int(float(v)) if v is not None else None
    except (ValueError, TypeError):
        return None

def warn(line_num: int, reason: str, snippet: str = ""):
    preview = (snippet[:120] + "…") if len(snippet) > 120 else snippet
    print(f"  [WARN] line {line_num}: {reason}" + (f" | {preview}" if preview else ""),
          file=sys.stderr)


# ---------------------------------------------------------------------------
# Parsers — one per event type
# ---------------------------------------------------------------------------

def parse_api_request(event_id, attrs, resource, ts):
    return (
        event_id,
        get_attr(attrs, "session.id", "session_id"),
        get_attr(attrs, "user.email") or get_attr(resource, "user.email"),
        ts,
        get_attr(attrs, "model"),
        _float(get_attr(attrs, "cost_usd")),
        _float(get_attr(attrs, "duration_ms")),
        _int(get_attr(attrs, "input_tokens")),
        _int(get_attr(attrs, "output_tokens")),
        _int(get_attr(attrs, "cache_read_tokens")),
        _int(get_attr(attrs, "cache_creation_tokens")),
    )


def parse_api_error(event_id, attrs, resource, ts):
    return (
        event_id,
        get_attr(attrs, "session.id", "session_id"),
        get_attr(attrs, "user.email") or get_attr(resource, "user.email"),
        ts,
        get_attr(attrs, "model"),
        get_attr(attrs, "error"),
        str(get_attr(attrs, "status_code", default="")),
    )


def parse_tool_decision(event_id, attrs, resource, ts):
    return (
        event_id,
        get_attr(attrs, "session.id", "session_id"),
        get_attr(attrs, "user.email") or get_attr(resource, "user.email"),
        ts,
        get_attr(attrs, "tool_name"),
        "decision",
        get_attr(attrs, "decision"),
        get_attr(attrs, "decision_source"),
        None,   # success — not applicable
        None,   # duration_ms — not applicable
    )


def parse_tool_result(event_id, attrs, resource, ts):
    raw_success = get_attr(attrs, "success")
    if isinstance(raw_success, bool):
        success = 1 if raw_success else 0
    elif raw_success is None:
        success = None
    else:
        success = 1 if str(raw_success).lower() in ("true", "1", "yes") else 0

    return (
        event_id,
        get_attr(attrs, "session.id", "session_id"),
        get_attr(attrs, "user.email") or get_attr(resource, "user.email"),
        ts,
        get_attr(attrs, "tool_name"),
        "result",
        None,   # decision — not applicable
        None,   # decision_source — not applicable
        success,
        _float(get_attr(attrs, "duration_ms")),
    )


def parse_user_prompt(event_id, attrs, resource, ts):
    return (
        event_id,
        get_attr(attrs, "session.id", "session_id"),
        get_attr(attrs, "user.email") or get_attr(resource, "user.email"),
        ts,
    )


PARSERS = {
    "claude_code.api_request":   ("api_requests",  parse_api_request),
    "claude_code.api_error":     ("api_errors",    parse_api_error),
    "claude_code.tool_decision": ("tool_events",   parse_tool_decision),
    "claude_code.tool_result":   ("tool_events",   parse_tool_result),
    "claude_code.user_prompt":   ("user_prompts",  parse_user_prompt),
}

INSERT_SQL = {
    "api_requests": """
        INSERT OR IGNORE INTO api_requests
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """,
    "api_errors": """
        INSERT OR IGNORE INTO api_errors
        VALUES (?,?,?,?,?,?,?)
    """,
    "tool_events": """
        INSERT OR IGNORE INTO tool_events
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """,
    "user_prompts": """
        INSERT OR IGNORE INTO user_prompts
        VALUES (?,?,?,?)
    """,
}

# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_employees(conn: sqlite3.Connection, path: Path) -> int:
    print(f"Loading employees from {path} …")
    count = 0
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [
            (
                row.get("email", "").strip(),
                row.get("full_name", "").strip(),
                row.get("practice", "").strip(),
                row.get("level", "").strip(),
                row.get("location", "").strip(),
            )
            for row in reader
        ]
    conn.executemany("INSERT OR IGNORE INTO employees VALUES (?,?,?,?,?)", rows)
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    print(f"  → {len(rows)} rows processed, {count} in table")
    return count


def load_telemetry(conn: sqlite3.Connection, path: Path) -> dict:
    print(f"Loading telemetry from {path} …")

    counters   = {t: 0 for t in INSERT_SQL}
    warn_count = 0
    batch_size = 5_000          # rows per commit
    buffers    = {t: [] for t in INSERT_SQL}

    def flush(table=None):
        tables = [table] if table else list(buffers)
        for t in tables:
            if buffers[t]:
                conn.executemany(INSERT_SQL[t], buffers[t])
                buffers[t].clear()
        conn.commit()

    with path.open(encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            # --- outer JSON (log batch) ---
            try:
                batch = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                warn(line_num, f"outer JSON parse error: {exc}", raw_line)
                warn_count += 1
                continue

            log_events = batch.get("logEvents", [])
            if not isinstance(log_events, list):
                warn(line_num, "logEvents is not a list")
                warn_count += 1
                continue

            for event in log_events:
                raw_msg = event.get("message", "")
                if not raw_msg:
                    warn(line_num, "empty message field")
                    warn_count += 1
                    continue

                # --- inner JSON (message) ---
                try:
                    msg = json.loads(raw_msg)
                except json.JSONDecodeError as exc:
                    warn(line_num, f"inner message JSON parse error: {exc}", raw_msg)
                    warn_count += 1
                    continue

                event_type = msg.get("body", "")
                attrs      = msg.get("attributes", {})
                resource   = msg.get("resource", {})
                ts         = get_attr(attrs, "event.timestamp")
                event_id   = make_event_id(raw_msg)

                if event_type not in PARSERS:
                    # Unknown event type — silently skip
                    continue

                table, parser = PARSERS[event_type]

                try:
                    row = parser(event_id, attrs, resource, ts)
                except Exception as exc:
                    warn(line_num, f"parser error for {event_type}: {exc}")
                    warn_count += 1
                    continue

                buffers[table].append(row)
                counters[table] += 1

                if counters[table] % batch_size == 0:
                    flush(table)

            # Progress every 10 000 lines
            if line_num % 10_000 == 0:
                flush()
                total = sum(counters.values())
                print(f"  … line {line_num:,}  |  {total:,} events staged")

    flush()
    print(f"  → done  |  {warn_count} warnings")
    return counters


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(conn: sqlite3.Connection):
    tables = ["api_requests", "api_errors", "tool_events", "user_prompts", "employees"]
    print("\n" + "=" * 45)
    print(f"{'Table':<25} {'Rows':>10}")
    print("-" * 45)
    total = 0
    for t in tables:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t:<25} {n:>10,}")
        total += n
    print("-" * 45)
    print(f"{'TOTAL':<25} {total:>10,}")
    print("=" * 45)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ingest Claude Code telemetry into SQLite.")
    parser.add_argument("--telemetry", default="output/telemetry_logs.jsonl",
                        help="Path to telemetry_logs.jsonl")
    parser.add_argument("--employees", default="output/employees.csv",
                        help="Path to employees.csv")
    parser.add_argument("--db",        default="analytics.db",
                        help="SQLite database file to create/update")
    args = parser.parse_args()

    telemetry_path = Path(args.telemetry)
    employees_path = Path(args.employees)
    db_path        = Path(args.db)

    for p in (telemetry_path, employees_path):
        if not p.exists():
            print(f"ERROR: File not found: {p}", file=sys.stderr)
            sys.exit(1)

    print(f"Opening database: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(DDL)
    conn.commit()

    load_employees(conn, employees_path)
    counters = load_telemetry(conn, telemetry_path)

    print_summary(conn)
    conn.close()
    print(f"\nDone. Database written to {db_path}")


if __name__ == "__main__":
    main()
