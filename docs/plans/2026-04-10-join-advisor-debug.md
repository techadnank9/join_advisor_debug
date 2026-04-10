# Join Advisor Debug Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a runnable Python CLI that inspects two SQLite tables, detects candidate join keys, measures join quality, generates SQL, and asks Nebius for reasoning with a local fallback.

**Architecture:** Keep the project intentionally small with one importable `main.py` module that owns CLI parsing, SQLite inspection, SQL logging, join-quality analysis, and Nebius integration. Add a focused `pytest` suite against an in-memory SQLite database so the key behaviors are verified without external dependencies.

**Tech Stack:** Python, SQLite, `python-dotenv`, `openai`, `pytest`

---

### Task 1: Scaffold the project

**Files:**
- Create: `join_advisor_debug/main.py`
- Create: `join_advisor_debug/.env.example`
- Create: `join_advisor_debug/requirements.txt`

**Step 1: Write the failing test**

Create a test that imports `analyze_join` and expects a detected shared key.

**Step 2: Run test to verify it fails**

Run: `pytest /Users/adnan/Documents/join_advisor_debug/tests/test_main.py -v`
Expected: FAIL because `main.py` does not exist yet.

**Step 3: Write minimal implementation**

Create the project files and a basic importable module layout.

**Step 4: Run test to verify it passes**

Run: `pytest /Users/adnan/Documents/join_advisor_debug/tests/test_main.py -v`
Expected: initial import/setup passes after implementation work is completed.

### Task 2: Implement join analysis and logging

**Files:**
- Modify: `join_advisor_debug/main.py`
- Test: `join_advisor_debug/tests/test_main.py`

**Step 1: Write the failing test**

Add an in-memory SQLite test that expects candidate keys, match counts, NULL detection, duplicate detection, and generated SQL.

**Step 2: Run test to verify it fails**

Run: `pytest /Users/adnan/Documents/join_advisor_debug/tests/test_main.py::test_analyze_join_detects_intersection_and_profiles_match_quality -v`
Expected: FAIL until join analysis exists.

**Step 3: Write minimal implementation**

Implement schema discovery, column intersection, per-column profiling, and join match-rate calculations with DEBUG logging of all SQL and intermediate counts.

**Step 4: Run test to verify it passes**

Run: `pytest /Users/adnan/Documents/join_advisor_debug/tests/test_main.py::test_analyze_join_detects_intersection_and_profiles_match_quality -v`
Expected: PASS.

### Task 3: Implement Nebius reasoning and fallback

**Files:**
- Modify: `join_advisor_debug/main.py`
- Test: `join_advisor_debug/tests/test_main.py`

**Step 1: Write the failing test**

Add a test that expects a local reasoning fallback when the API key is missing.

**Step 2: Run test to verify it fails**

Run: `pytest /Users/adnan/Documents/join_advisor_debug/tests/test_main.py::test_local_reasoning_reports_missing_api_key -v`
Expected: FAIL until fallback reasoning exists.

**Step 3: Write minimal implementation**

Implement `.env` loading, API key checks, Nebius client setup, raw/parsed response logging, and fallback reasoning when the key is missing or the request fails.

**Step 4: Run test to verify it passes**

Run: `pytest /Users/adnan/Documents/join_advisor_debug/tests/test_main.py::test_local_reasoning_reports_missing_api_key -v`
Expected: PASS.

### Task 4: Verify the CLI end-to-end

**Files:**
- Modify: `join_advisor_debug/main.py`

**Step 1: Run verification**

Run: `python /Users/adnan/Documents/join_advisor_debug/main.py`
Expected: CLI prints the DB path, detected tables, candidate keys, SQL, intermediate counts, warnings, and local or Nebius reasoning.
