import sqlite3
import json
from typing import List, Dict, Any, Optional
from config import DB_PATH


def init_db(db_path: str = None) -> None:
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            usdinr_spot REAL,
            rsi_daily   REAL,
            dxy         REAL,
            brent       REAL,
            recommendation TEXT,
            hedge_ratio INTEGER,
            confidence  TEXT,
            rationale   TEXT,
            score       REAL,
            raw_json    TEXT,
            near_month_oi REAL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS decisions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            action_taken TEXT,
            hedge_pct   INTEGER,
            notes       TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_snapshots_date ON snapshots(date);
    """)
    # Migrate existing DBs that pre-date the near_month_oi column
    try:
        conn.execute("ALTER TABLE snapshots ADD COLUMN near_month_oi REAL")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.close()


def save_snapshot(snapshot: Dict[str, Any], db_path: str = None) -> None:
    if db_path is None:
        db_path = DB_PATH
    init_db(db_path)
    row = {**snapshot, "near_month_oi": snapshot.get("near_month_oi")}
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT OR REPLACE INTO snapshots
            (date, usdinr_spot, rsi_daily, dxy, brent, recommendation,
             hedge_ratio, confidence, rationale, score, raw_json, near_month_oi)
        VALUES (:date, :usdinr_spot, :rsi_daily, :dxy, :brent, :recommendation,
                :hedge_ratio, :confidence, :rationale, :score, :raw_json,
                :near_month_oi)
    """, row)
    conn.commit()
    conn.close()


def get_history(n: int = 30, db_path: str = None) -> List[Dict[str, Any]]:
    if db_path is None:
        db_path = DB_PATH
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM snapshots ORDER BY date DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_oi_history(n: int = 20, db_path: str = None) -> List[Optional[float]]:
    """Return last n days of near-month OI, most recent first. None where not recorded."""
    if db_path is None:
        db_path = DB_PATH
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT near_month_oi FROM snapshots ORDER BY date DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def save_decision(decision: Dict[str, Any], db_path: str = None) -> None:
    if db_path is None:
        db_path = DB_PATH
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO decisions (date, action_taken, hedge_pct, notes)
        VALUES (:date, :action_taken, :hedge_pct, :notes)
    """, decision)
    conn.commit()
    conn.close()


def get_decisions(n: int = 30, db_path: str = None) -> List[Dict[str, Any]]:
    if db_path is None:
        db_path = DB_PATH
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM decisions ORDER BY date DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
