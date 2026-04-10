import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import analyze_join, build_local_reasoning, run_join_analysis


def build_test_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
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
            ('c2', 'gamma'),
            (NULL, 'missing');

        INSERT INTO right_table (customer_id, payload) VALUES
            ('c1', 'one'),
            ('c3', 'two'),
            ('', 'blank'),
            ('c1', 'dup');
        """
    )
    return conn


def build_test_db_file(tmp_path: Path) -> Path:
    db_path = tmp_path / "join_test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
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
            ('c2', 'gamma'),
            (NULL, 'missing');

        INSERT INTO right_table (customer_id, payload) VALUES
            ('c1', 'one'),
            ('c3', 'two'),
            ('', 'blank'),
            ('c1', 'dup');
        """
    )
    conn.close()
    return db_path


def test_analyze_join_detects_intersection_and_profiles_match_quality():
    conn = build_test_db()

    analysis = analyze_join(conn, "left_table", "right_table")

    assert "customer_id" in analysis["candidate_keys"]
    best = analysis["best_candidate"]
    assert best["key"] == "customer_id"
    assert best["matched_left_rows"] == 2
    assert best["matched_right_rows"] == 2
    assert best["left_profile"]["null_rows"] == 1
    assert best["right_profile"]["null_rows"] == 1
    assert best["left_profile"]["duplicate_groups"] == 1
    assert best["right_profile"]["duplicate_groups"] == 1
    assert "INNER JOIN" in best["join_sql"]


def test_local_reasoning_reports_missing_api_key():
    conn = build_test_db()
    analysis = analyze_join(conn, "left_table", "right_table")

    reasoning = build_local_reasoning(analysis, api_key_missing=True)

    assert "Best join key candidate is customer_id" in reasoning
    assert "NEBIUS_API_KEY is missing" in reasoning


def test_run_join_analysis_returns_structured_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "")
    db_path = build_test_db_file(tmp_path)

    result = run_join_analysis(str(db_path), "left_table", "right_table", "fake-model")

    assert result["analysis"]["best_candidate"]["key"] == "customer_id"
    assert result["llm_result"]["parsed"].startswith("Best join key candidate is customer_id")
    assert result["db_path"] == str(db_path.resolve())
