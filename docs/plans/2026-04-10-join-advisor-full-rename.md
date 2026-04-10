# Join Advisor Full Rename Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the old temporary branding from the Join Advisor project everywhere, including runtime strings, tests, docs, and the project folder path.

**Architecture:** Keep the application behavior unchanged while renaming only branding, internal identifiers, and filesystem references. Preserve the existing git repository by moving the project directory in place, then verify the app and tests from the new location.

**Tech Stack:** Python, Flask, pytest, git, HTML

---

### Task 1: Add a failing branding test

**Files:**
- Modify: `/Users/adnan/Documents/join_advisor/tests/test_app.py`

**Step 1: Write the failing test**

```python
def test_index_route_does_not_render_debug_branding():
    response = app.test_client().get("/")
    assert b"SQLite Join Analysis" in response.data
```

**Step 2: Run test to verify it fails**

Run: `pytest /Users/adnan/Documents/join_advisor/tests/test_app.py -q`
Expected: FAIL if the updated branding is not rendered.

**Step 3: Write minimal implementation**

```python
assert b"Join Advisor" in response.data
```

**Step 4: Run test to verify it passes**

Run: `pytest /Users/adnan/Documents/join_advisor/tests/test_app.py -q`
Expected: PASS with the updated branding in the response.

**Step 5: Commit**

```bash
git -C /Users/adnan/Documents/join_advisor add tests/test_app.py
git -C /Users/adnan/Documents/join_advisor commit -m "test: guard against debug branding"
```

### Task 2: Rename runtime and doc references

**Files:**
- Modify: `/Users/adnan/Documents/join_advisor/main.py`
- Modify: `/Users/adnan/Documents/join_advisor/docs/plans/2026-04-10-join-advisor.md`
- Modify: `/Users/adnan/Documents/join_advisor/docs/plans/2026-04-10-join-advisor-frontend.md`
- Modify: `/Users/adnan/Documents/join_advisor/docs/plans/2026-04-10-join-advisor-rename.md`

**Step 1: Write the failing test**

```python
assert "debug" not in runtime_output.lower()
```

**Step 2: Run test to verify it fails**

Run: `python3 /Users/adnan/Documents/join_advisor/main.py`
Expected: Existing logger or CLI strings still contain the temporary branding.

**Step 3: Write minimal implementation**

```python
LOGGER = logging.getLogger("join_advisor")
LOGGER.info("Starting join advisor run")
```

**Step 4: Run test to verify it passes**

Run: `python3 /Users/adnan/Documents/join_advisor/main.py`
Expected: Runtime output no longer contains the temporary branding in app strings.

**Step 5: Commit**

```bash
git -C /Users/adnan/Documents/join_advisor add main.py docs/plans
git -C /Users/adnan/Documents/join_advisor commit -m "refactor: remove debug branding"
```

### Task 3: Rename the project folder and verify

**Files:**
- Move: `/Users/adnan/Documents/join_advisor_old` placeholder path -> `/Users/adnan/Documents/join_advisor`

**Step 1: Write the failing test**

```bash
test -d /Users/adnan/Documents/join_advisor
```

**Step 2: Run test to verify it fails**

Run: `test -d /Users/adnan/Documents/join_advisor`
Expected: exit code 1 before the move.

**Step 3: Write minimal implementation**

```bash
mv /Users/adnan/Documents/<current_project_folder> /Users/adnan/Documents/join_advisor
```

**Step 4: Run test to verify it passes**

Run: `pytest /Users/adnan/Documents/join_advisor/tests/test_main.py /Users/adnan/Documents/join_advisor/tests/test_app.py -q`
Expected: PASS from the renamed location.

**Step 5: Commit**

```bash
git -C /Users/adnan/Documents/join_advisor add -A
git -C /Users/adnan/Documents/join_advisor commit -m "chore: rename project folder to join_advisor"
```
