# core/store.py
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")

def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute("PRAGMA journal_mode=WAL;")
    return c

def init_db():
    with _conn() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS status_memory(
            id INTEGER PRIMARY KEY CHECK (id=1),
            last_status INTEGER,
            last_change_ts TEXT,
            last_check_ts TEXT
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS checks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            mode TEXT NOT NULL,         -- PICO / NORMAL / MANUAL
            available INTEGER NOT NULL, -- 0/1
            latency_ms INTEGER NOT NULL,
            error TEXT
        )""")
        con.execute("INSERT OR IGNORE INTO status_memory(id,last_status,last_change_ts,last_check_ts) VALUES (1,NULL,NULL,NULL)")
        con.commit()

def get_memory():
    with _conn() as con:
        row = con.execute("SELECT last_status,last_change_ts,last_check_ts FROM status_memory WHERE id=1").fetchone()
        return row  # (status int/None, change_ts, check_ts)

def update_memory(new_status: int, check_ts: str):
    with _conn() as con:
        old = con.execute("SELECT last_status,last_change_ts FROM status_memory WHERE id=1").fetchone()
        old_status = old[0]
        change_ts = old[1]

        # if first time or changed -> set new change_ts
        if old_status is None or int(old_status) != int(new_status):
            change_ts = check_ts
            con.execute("UPDATE status_memory SET last_status=?, last_change_ts=?, last_check_ts=? WHERE id=1",
                        (int(new_status), change_ts, check_ts))
        else:
            con.execute("UPDATE status_memory SET last_check_ts=? WHERE id=1", (check_ts,))
        con.commit()

def log_check(ts: str, mode: str, available: int, latency_ms: int, error: str | None = None):
    with _conn() as con:
        con.execute(
            "INSERT INTO checks(ts,mode,available,latency_ms,error) VALUES (?,?,?,?,?)",
            (ts, mode, int(available), int(latency_ms), error)
        )
        con.commit()

def stats_today():
    # simple: last 24h
    with _conn() as con:
        rows = con.execute("""
            SELECT
              COUNT(*),
              SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END),
              AVG(latency_ms),
              MAX(latency_ms)
            FROM checks
            WHERE ts >= datetime('now','-24 hours')
        """).fetchone()
        return rows  # total, errors, avg_ms, max_ms

def peak_hours_by_latency(limit=5):
    # top hours (0-23) by avg latency in last 7 days
    with _conn() as con:
        rows = con.execute("""
            SELECT substr(ts,12,2) AS hour,
                   COUNT(*) AS n,
                   AVG(latency_ms) AS avg_ms
            FROM checks
            WHERE ts >= datetime('now','-7 days') AND error IS NULL
            GROUP BY hour
            HAVING n >= 5
            ORDER BY avg_ms DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return rows

def peak_hours_by_changes(limit=5):
    # hours with most "became available" transitions in last 30 days (based on memory changes)
    # We'll approximate: count checks where available=1 and previous check was 0.
    with _conn() as con:
        rows = con.execute("""
            WITH ordered AS (
              SELECT ts, available,
                     LAG(available) OVER (ORDER BY ts) AS prev
              FROM checks
              WHERE ts >= datetime('now','-30 days') AND error IS NULL
            )
            SELECT substr(ts,12,2) AS hour,
                   COUNT(*) AS hits
            FROM ordered
            WHERE available=1 AND (prev=0 OR prev IS NULL)
            GROUP BY hour
            ORDER BY hits DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return rows