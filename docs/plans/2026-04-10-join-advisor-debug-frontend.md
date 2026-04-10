# Join Advisor Debug Frontend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Flask single-page frontend so the join advisor can be demoed in a browser while reusing the existing SQLite analysis and Nebius reasoning flow.

**Architecture:** Keep backend logic centralized in `main.py` and expose it through a lightweight Flask app in `app.py`. Serve one HTML page with a form and in-place results rendering so the demo runs with a single Python process and one browser tab.

**Tech Stack:** Python, Flask, SQLite, `python-dotenv`, `openai`, `pytest`

---

### Task 1: Add a shared analysis entrypoint

**Files:**
- Modify: `join_advisor_debug/main.py`
- Test: `join_advisor_debug/tests/test_main.py`

**Step 1: Write the failing test**

Add a test that exercises a reusable function for running analysis without printing CLI output.

**Step 2: Run test to verify it fails**

Run: `pytest /Users/adnan/Documents/join_advisor_debug/tests/test_main.py -v`
Expected: FAIL because the reusable entrypoint does not exist yet.

**Step 3: Write minimal implementation**

Extract the CLI’s main analysis flow into a shared function that returns structured data for both CLI and Flask usage.

**Step 4: Run test to verify it passes**

Run: `pytest /Users/adnan/Documents/join_advisor_debug/tests/test_main.py -v`
Expected: PASS.

### Task 2: Add Flask backend routes

**Files:**
- Create: `join_advisor_debug/app.py`
- Modify: `join_advisor_debug/requirements.txt`
- Test: `join_advisor_debug/tests/test_app.py`

**Step 1: Write the failing test**

Add Flask test client coverage for `GET /` and `POST /analyze`.

**Step 2: Run test to verify it fails**

Run: `pytest /Users/adnan/Documents/join_advisor_debug/tests/test_app.py -v`
Expected: FAIL because the Flask app does not exist yet.

**Step 3: Write minimal implementation**

Create the Flask app, homepage route, JSON analysis endpoint, and error handling with stack traces in responses.

**Step 4: Run test to verify it passes**

Run: `pytest /Users/adnan/Documents/join_advisor_debug/tests/test_app.py -v`
Expected: PASS.

### Task 3: Build the demo UI

**Files:**
- Create: `join_advisor_debug/templates/index.html`
- Create: `join_advisor_debug/static/styles.css`

**Step 1: Write the UI**

Create a single-page form with inputs for DB path, tables, and model, plus sections for match rates, warnings, generated SQL, and full Nebius reasoning.

**Step 2: Verify manually**

Run: `python3 /Users/adnan/Documents/join_advisor_debug/app.py`
Expected: Browser UI loads and can submit analysis without page reload.

### Task 4: Verify the full demo path

**Files:**
- Modify: `join_advisor_debug/.env.example`

**Step 1: Run verification**

Run: `pytest /Users/adnan/Documents/join_advisor_debug/tests/test_main.py /Users/adnan/Documents/join_advisor_debug/tests/test_app.py -v`
Expected: all tests pass.

Run: `python3 /Users/adnan/Documents/join_advisor_debug/main.py`
Expected: CLI still works.

Run: `python3 /Users/adnan/Documents/join_advisor_debug/app.py`
Expected: Flask server starts cleanly for demo use.
