import os, sys, sqlite3, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from storage.db import init_db, save_snapshot, get_history, DB_PATH

TEST_DB = "test_forex.db"

@pytest.fixture(autouse=True)
def use_test_db(monkeypatch):
    monkeypatch.setattr("storage.db.DB_PATH", TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_init_creates_tables():
    init_db()
    conn = sqlite3.connect(TEST_DB)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "snapshots" in tables
    assert "decisions" in tables

def test_save_and_read_snapshot():
    init_db()
    snapshot = {
        "date": "2026-05-03",
        "usdinr_spot": 94.95,
        "rsi_daily": 68.5,
        "dxy": 104.2,
        "brent": 82.5,
        "recommendation": "COVER PARTIAL",
        "hedge_ratio": 50,
        "confidence": "Medium",
        "rationale": "RSI moderately high with DXY falling",
        "score": 5,
        "raw_json": '{"test": true}',
    }
    save_snapshot(snapshot)
    history = get_history(n=10)
    assert len(history) == 1
    assert history[0]["usdinr_spot"] == 94.95
    assert history[0]["recommendation"] == "COVER PARTIAL"
