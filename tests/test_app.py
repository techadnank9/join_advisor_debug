import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app


def build_test_db_file(tmp_path: Path) -> Path:
    db_path = tmp_path / "app_join_test.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE left_table (
            left_id INTEGER PRIMARY KEY,
            customer_id TEXT,
            note TEXT
        );

        CREATE TABLE right_table (
            right_id INTEGER PRIMARY KEY,
            customer_id TEXT,
            payload TEXT
        );

        INSERT INTO left_table (customer_id, note) VALUES
            ('c1', 'alpha'),
            ('c1', 'beta'),
            ('c2', 'gamma');

        INSERT INTO right_table (customer_id, payload) VALUES
            ('c1', 'one'),
            ('c1', 'dup'),
            ('c3', 'two');
        """
    )
    conn.close()
    return db_path


def test_index_route_renders_ui():
    app = create_app()

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"Join Advisor" in response.data
    assert b"SQLite Join Analysis" in response.data
    assert b"Run Analysis" in response.data


def test_analyze_route_returns_json_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "")
    db_path = build_test_db_file(tmp_path)
    app = create_app()

    response = app.test_client().post(
        "/analyze",
        json={
            "db_path": str(db_path),
            "table_a": "left_table",
            "table_b": "right_table",
            "model": "fake-model",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["analysis"]["best_candidate"]["key"] == "customer_id"
    assert "NEBIUS_API_KEY is missing" in payload["llm_result"]["parsed"]
