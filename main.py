import argparse
import json
import logging
import os
import sqlite3
import sys
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
NEBIUS_TIMEOUT_SECONDS = 20.0
DEFAULT_DB_PATH = "./datasets/olist-ecommerce/olist_dirty.db"
DISCOVERED_DB_HINT = "/Users/adnan/Documents/static-assets/datasets/olist-ecommerce/olist_dirty.db"
DEFAULT_TABLE_A = "olist_orders"
DEFAULT_TABLE_B = "olist_order_items"
DEFAULT_MODEL = "Qwen/Qwen3.5-397B-A17B-fast"
FALLBACK_MODEL = "Qwen/Qwen3.5-397B-A17B-fast"

LOGGER = logging.getLogger("join_advisor")


@dataclass
class ColumnProfile:
    table: str
    column: str
    total_rows: int
    null_rows: int
    non_null_rows: int
    distinct_non_null_values: int
    duplicate_groups: int
    duplicate_rows: int
    warnings: list[str]


@dataclass
class JoinCandidateAnalysis:
    key: str
    left_profile: ColumnProfile
    right_profile: ColumnProfile
    matched_left_rows: int
    matched_right_rows: int
    matched_distinct_values: int
    left_match_rate: float
    right_match_rate: float
    average_match_rate: float
    join_sql: str
    unmatched_left_sql: str
    unmatched_right_sql: str
    warnings: list[str]


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
    )


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def quoted_table(table_name: str) -> str:
    return quote_identifier(table_name)


def quoted_column(column_name: str) -> str:
    return quote_identifier(column_name)


def log_header(message: str) -> None:
    print(f"\n=== {message} ===")


def execute_scalar(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> int:
    LOGGER.debug("SQL to execute:\n%s\nParams: %s", sql, params)
    cursor = conn.execute(sql, params)
    row = cursor.fetchone()
    value = 0 if row is None or row[0] is None else int(row[0])
    LOGGER.debug("SQL scalar result: %s", value)
    return value


def execute_rows(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    LOGGER.debug("SQL to execute:\n%s\nParams: %s", sql, params)
    cursor = conn.execute(sql, params)
    rows = cursor.fetchall()
    LOGGER.debug("SQL returned %s row(s)", len(rows))
    return rows


def get_tables(conn: sqlite3.Connection) -> list[str]:
    sql = """
    SELECT name
    FROM sqlite_master
    WHERE type IN ('table', 'view')
      AND name NOT LIKE 'sqlite_%'
    ORDER BY name
    """
    rows = execute_rows(conn, sql)
    tables = [row["name"] for row in rows]
    LOGGER.info("Tables detected: %s", tables)
    return tables


def get_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    sql = f"PRAGMA table_info({quoted_table(table_name)})"
    rows = execute_rows(conn, sql)
    columns = [row["name"] for row in rows]
    LOGGER.info("Columns for table %s: %s", table_name, columns)
    return columns


def get_total_rows(conn: sqlite3.Connection, table_name: str) -> int:
    sql = f"SELECT COUNT(*) FROM {quoted_table(table_name)}"
    return execute_scalar(conn, sql)


def get_column_profile(conn: sqlite3.Connection, table_name: str, column_name: str) -> ColumnProfile:
    table_sql = quoted_table(table_name)
    column_sql = quoted_column(column_name)
    non_blank_filter = f"{column_sql} IS NOT NULL AND TRIM(CAST({column_sql} AS TEXT)) <> ''"

    total_rows = get_total_rows(conn, table_name)
    null_rows = execute_scalar(
        conn,
        f"""
        SELECT COUNT(*)
        FROM {table_sql}
        WHERE {column_sql} IS NULL OR TRIM(CAST({column_sql} AS TEXT)) = ''
        """,
    )
    distinct_non_null_values = execute_scalar(
        conn,
        f"""
        SELECT COUNT(DISTINCT {column_sql})
        FROM {table_sql}
        WHERE {non_blank_filter}
        """,
    )
    duplicate_groups = execute_scalar(
        conn,
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT {column_sql}
            FROM {table_sql}
            WHERE {non_blank_filter}
            GROUP BY {column_sql}
            HAVING COUNT(*) > 1
        )
        """,
    )
    duplicate_rows = execute_scalar(
        conn,
        f"""
        SELECT COALESCE(SUM(group_count - 1), 0)
        FROM (
            SELECT COUNT(*) AS group_count
            FROM {table_sql}
            WHERE {non_blank_filter}
            GROUP BY {column_sql}
            HAVING COUNT(*) > 1
        )
        """,
    )

    warnings: list[str] = []
    if null_rows > 0:
        warnings.append(f"{table_name}.{column_name} contains {null_rows} NULL/blank value(s)")
    if duplicate_groups > 0:
        warnings.append(
            f"{table_name}.{column_name} has {duplicate_groups} duplicate key group(s) covering {duplicate_rows} extra row(s)"
        )

    profile = ColumnProfile(
        table=table_name,
        column=column_name,
        total_rows=total_rows,
        null_rows=null_rows,
        non_null_rows=total_rows - null_rows,
        distinct_non_null_values=distinct_non_null_values,
        duplicate_groups=duplicate_groups,
        duplicate_rows=duplicate_rows,
        warnings=warnings,
    )
    LOGGER.debug("Column profile computed: %s", profile)
    return profile


def compute_join_candidate(conn: sqlite3.Connection, left_table: str, right_table: str, key: str) -> JoinCandidateAnalysis:
    left_profile = get_column_profile(conn, left_table, key)
    right_profile = get_column_profile(conn, right_table, key)

    left_table_sql = quoted_table(left_table)
    right_table_sql = quoted_table(right_table)
    key_sql = quoted_column(key)
    left_non_blank = f"a.{key_sql} IS NOT NULL AND TRIM(CAST(a.{key_sql} AS TEXT)) <> ''"
    right_non_blank = f"b.{key_sql} IS NOT NULL AND TRIM(CAST(b.{key_sql} AS TEXT)) <> ''"

    matched_left_rows_sql = f"""
    SELECT COUNT(*)
    FROM {left_table_sql} AS a
    INNER JOIN (
        SELECT DISTINCT {key_sql}
        FROM {right_table_sql}
        WHERE {key_sql} IS NOT NULL AND TRIM(CAST({key_sql} AS TEXT)) <> ''
    ) AS matching_keys
        ON a.{key_sql} = matching_keys.{key_sql}
    WHERE {left_non_blank}
    """
    matched_right_rows_sql = f"""
    SELECT COUNT(*)
    FROM {right_table_sql} AS b
    INNER JOIN (
        SELECT DISTINCT {key_sql}
        FROM {left_table_sql}
        WHERE {key_sql} IS NOT NULL AND TRIM(CAST({key_sql} AS TEXT)) <> ''
    ) AS matching_keys
        ON b.{key_sql} = matching_keys.{key_sql}
    WHERE {right_non_blank}
    """
    matched_distinct_sql = f"""
    SELECT COUNT(*)
    FROM (
        SELECT {key_sql}
        FROM {left_table_sql}
        WHERE {key_sql} IS NOT NULL AND TRIM(CAST({key_sql} AS TEXT)) <> ''
        INTERSECT
        SELECT {key_sql}
        FROM {right_table_sql}
        WHERE {key_sql} IS NOT NULL AND TRIM(CAST({key_sql} AS TEXT)) <> ''
    )
    """

    matched_left_rows = execute_scalar(conn, matched_left_rows_sql)
    matched_right_rows = execute_scalar(conn, matched_right_rows_sql)
    matched_distinct_values = execute_scalar(conn, matched_distinct_sql)

    LOGGER.info(
        "Intermediate counts for key %s: left_total=%s, right_total=%s, matched_left=%s, matched_right=%s, matched_distinct=%s",
        key,
        left_profile.total_rows,
        right_profile.total_rows,
        matched_left_rows,
        matched_right_rows,
        matched_distinct_values,
    )

    left_denominator = left_profile.non_null_rows or 1
    right_denominator = right_profile.non_null_rows or 1
    left_match_rate = matched_left_rows / left_denominator if left_profile.non_null_rows else 0.0
    right_match_rate = matched_right_rows / right_denominator if right_profile.non_null_rows else 0.0
    average_match_rate = (left_match_rate + right_match_rate) / 2

    join_sql = f"""
    SELECT a.*, b.*
    FROM {left_table_sql} AS a
    INNER JOIN {right_table_sql} AS b
        ON a.{key_sql} = b.{key_sql}
    WHERE {left_non_blank}
      AND {right_non_blank}
    LIMIT 10
    """.strip()
    unmatched_left_sql = f"""
    SELECT a.*
    FROM {left_table_sql} AS a
    LEFT JOIN {right_table_sql} AS b
        ON a.{key_sql} = b.{key_sql}
    WHERE {left_non_blank}
      AND b.{key_sql} IS NULL
    LIMIT 10
    """.strip()
    unmatched_right_sql = f"""
    SELECT b.*
    FROM {right_table_sql} AS b
    LEFT JOIN {left_table_sql} AS a
        ON a.{key_sql} = b.{key_sql}
    WHERE {right_non_blank}
      AND a.{key_sql} IS NULL
    LIMIT 10
    """.strip()

    warnings = list(left_profile.warnings) + list(right_profile.warnings)
    if matched_left_rows == 0 or matched_right_rows == 0:
        warnings.append(f"Join key {key} produced zero matched rows on at least one side")
    if left_match_rate < 0.8 or right_match_rate < 0.8:
        warnings.append(
            f"Join key {key} has low match rate (left={left_match_rate:.2%}, right={right_match_rate:.2%})"
        )

    return JoinCandidateAnalysis(
        key=key,
        left_profile=left_profile,
        right_profile=right_profile,
        matched_left_rows=matched_left_rows,
        matched_right_rows=matched_right_rows,
        matched_distinct_values=matched_distinct_values,
        left_match_rate=left_match_rate,
        right_match_rate=right_match_rate,
        average_match_rate=average_match_rate,
        join_sql=join_sql,
        unmatched_left_sql=unmatched_left_sql,
        unmatched_right_sql=unmatched_right_sql,
        warnings=warnings,
    )


def analyze_join(conn: sqlite3.Connection, left_table: str, right_table: str) -> dict[str, Any]:
    tables = get_tables(conn)
    if left_table not in tables:
        raise ValueError(f"Table {left_table!r} was not found in the database")
    if right_table not in tables:
        raise ValueError(f"Table {right_table!r} was not found in the database")

    left_columns = get_columns(conn, left_table)
    right_columns = get_columns(conn, right_table)
    candidate_keys = sorted(set(left_columns).intersection(right_columns))
    LOGGER.info("Candidate keys from column intersection: %s", candidate_keys)

    candidate_analyses = [compute_join_candidate(conn, left_table, right_table, key) for key in candidate_keys]
    best_candidate = max(candidate_analyses, key=lambda candidate: candidate.average_match_rate, default=None)

    return {
        "left_table": left_table,
        "right_table": right_table,
        "tables": tables,
        "left_columns": left_columns,
        "right_columns": right_columns,
        "candidate_keys": candidate_keys,
        "candidate_analyses": [asdict(candidate) for candidate in candidate_analyses],
        "best_candidate": asdict(best_candidate) if best_candidate else None,
    }


def build_local_reasoning(analysis: dict[str, Any], api_key_missing: bool = False, llm_error: str | None = None) -> str:
    best_candidate = analysis.get("best_candidate")
    if not best_candidate:
        reason = "No shared column names were found, so there is no safe automatic join key candidate."
    else:
        reason = (
            f"Best join key candidate is {best_candidate['key']} between "
            f"{analysis['left_table']} and {analysis['right_table']}. "
            f"Left match rate is {best_candidate['left_match_rate']:.2%} and "
            f"right match rate is {best_candidate['right_match_rate']:.2%}. "
            f"Matched distinct values: {best_candidate['matched_distinct_values']}."
        )
        if best_candidate["warnings"]:
            reason += " Warnings: " + " | ".join(best_candidate["warnings"])

    if api_key_missing:
        reason += " Nebius reasoning was skipped because NEBIUS_API_KEY is missing."
    if llm_error:
        reason += f" Nebius reasoning failed, so this fallback summary was used instead. Error: {llm_error}"
    return reason


def request_nebius_reasoning(analysis: dict[str, Any], model: str) -> dict[str, str]:
    api_key = os.getenv("NEBIUS_API_KEY", "").strip()
    if not api_key:
        LOGGER.warning("WARNING: NEBIUS_API_KEY is missing. Skipping Nebius request.")
        fallback = build_local_reasoning(analysis, api_key_missing=True)
        raw_payload = json.dumps({"status": "skipped", "reason": "missing_api_key", "fallback": fallback}, indent=2)
        LOGGER.debug("Full LLM response (raw): %s", raw_payload)
        LOGGER.info("Full LLM response (parsed): %s", fallback)
        return {"raw": raw_payload, "parsed": fallback}

    prompt = (
        "You are reviewing SQLite join quality. Analyze the join candidates, explain which key is best, "
        "call out match rate, NULLs, duplicates, risk level, and recommend next SQL checks.\n\n"
        f"Join analysis payload:\n{json.dumps(analysis, indent=2)}"
    )
    last_error: Exception | None = None

    try:
        client = OpenAI(
            base_url=NEBIUS_BASE_URL,
            api_key=api_key,
            timeout=NEBIUS_TIMEOUT_SECONDS,
            max_retries=0,
        )
        models_to_try = [model]
        if model != FALLBACK_MODEL:
            models_to_try.append(FALLBACK_MODEL)

        for candidate_model in models_to_try:
            try:
                LOGGER.info("Requesting Nebius reasoning with model: %s", candidate_model)
                response = client.chat.completions.create(
                    model=candidate_model,
                    temperature=0,
                    messages=[
                        {"role": "system", "content": "Be precise, concise, and explicit about join risks."},
                        {"role": "user", "content": prompt},
                    ],
                )
                raw_response = response.model_dump_json(indent=2)
                parsed_response = response.choices[0].message.content or ""
                LOGGER.debug("Full LLM response (raw): %s", raw_response)
                LOGGER.info("Full LLM response (parsed): %s", parsed_response)
                return {"raw": raw_response, "parsed": parsed_response}
            except Exception as exc:
                last_error = exc
                LOGGER.exception("ERROR: Nebius reasoning request failed for model %s", candidate_model)
                if "does not exist" in str(exc) and candidate_model != FALLBACK_MODEL:
                    LOGGER.warning(
                        "WARNING: Model %s was not found. Retrying once with fallback model %s.",
                        candidate_model,
                        FALLBACK_MODEL,
                    )
                    continue
                break
    except Exception as exc:
        last_error = exc

    assert last_error is not None
    fallback = build_local_reasoning(analysis, llm_error=str(last_error))
    raw_payload = json.dumps({"status": "error", "error": str(last_error), "fallback": fallback}, indent=2)
    LOGGER.debug("Full LLM response (raw): %s", raw_payload)
    LOGGER.info("Full LLM response (parsed): %s", fallback)
    return {"raw": raw_payload, "parsed": fallback}


def print_summary(analysis: dict[str, Any], llm_result: dict[str, str], db_path: Path) -> None:
    log_header("Join Advisor")
    print(f"Database path: {db_path}")
    print(f"Tables analyzed: {analysis['left_table']} <-> {analysis['right_table']}")
    print(f"Candidate keys: {', '.join(analysis['candidate_keys']) if analysis['candidate_keys'] else 'None'}")

    best_candidate = analysis.get("best_candidate")
    if best_candidate:
        log_header("Best Candidate")
        print(f"Key: {best_candidate['key']}")
        print(
            "Match rate: "
            f"left={best_candidate['left_match_rate']:.2%}, "
            f"right={best_candidate['right_match_rate']:.2%}"
        )
        print(
            "Intermediate counts: "
            f"left_total={best_candidate['left_profile']['total_rows']}, "
            f"right_total={best_candidate['right_profile']['total_rows']}, "
            f"matched_left={best_candidate['matched_left_rows']}, "
            f"matched_right={best_candidate['matched_right_rows']}, "
            f"matched_distinct={best_candidate['matched_distinct_values']}"
        )
        print("Generated SQL:")
        print(best_candidate["join_sql"])
        if best_candidate["warnings"]:
            log_header("Warnings")
            for warning in best_candidate["warnings"]:
                print(f"WARNING: {warning}")
    else:
        print("No candidate join keys were detected from column intersection.")

    log_header("LLM Reasoning")
    print("Raw response:")
    print(llm_result["raw"])
    print("\nParsed reasoning:")
    print(llm_result["parsed"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Join advisor for SQLite tables.")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to the SQLite database file.")
    parser.add_argument("--table-a", default=DEFAULT_TABLE_A, help="Left table for join analysis.")
    parser.add_argument("--table-b", default=DEFAULT_TABLE_B, help="Right table for join analysis.")
    parser.add_argument("--model", default=os.getenv("NEBIUS_MODEL", DEFAULT_MODEL), help="Nebius model name.")
    return parser.parse_args()


def validate_db_path(db_path: Path) -> None:
    LOGGER.info("DB path being used: %s", db_path)
    if db_path.exists():
        return

    hint = ""
    if Path(DISCOVERED_DB_HINT).exists():
        hint = f" A matching local dataset was found at {DISCOVERED_DB_HINT}."
    raise FileNotFoundError(f"Database file was not found at {db_path}.{hint}")


def run_join_analysis(db_path_value: str, table_a: str, table_b: str, model: str) -> dict[str, Any]:
    load_dotenv()
    configure_logging()
    db_path = Path(db_path_value).expanduser().resolve()
    conn: sqlite3.Connection | None = None

    LOGGER.info("Using Nebius base URL: %s", NEBIUS_BASE_URL)
    LOGGER.info("Tables requested for analysis: %s and %s", table_a, table_b)

    try:
        validate_db_path(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        LOGGER.debug("SQLite connection established successfully")

        analysis = analyze_join(conn, table_a, table_b)
        llm_result = request_nebius_reasoning(analysis, model)
        return {
            "db_path": str(db_path),
            "analysis": analysis,
            "llm_result": llm_result,
        }
    finally:
        if conn is not None:
            conn.close()
            LOGGER.debug("SQLite connection closed")


def main() -> int:
    args = parse_args()

    try:
        LOGGER.info("Starting join advisor run")
        result = run_join_analysis(args.db_path, args.table_a, args.table_b, args.model)
        print_summary(result["analysis"], result["llm_result"], Path(result["db_path"]))
        LOGGER.info("Join advisor run finished successfully")
        return 0
    except Exception as exc:
        LOGGER.exception("ERROR: join_advisor failed with an unhandled exception")
        print("\n=== ERROR ===")
        print(f"Unhandled error: {exc}")
        print("Full stack trace:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
