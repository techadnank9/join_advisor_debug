# Join Advisor Rename Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rename the app's user-facing product copy from "Join Advisor" placeholder and older debug branding to the final "Join Advisor" name and remove demo phrasing from the main UI.

**Architecture:** Keep the project structure unchanged and update only user-facing labels in the Flask template, CLI summary header, and tests that assert rendered copy. Avoid touching backend behavior or API payload structure.

**Tech Stack:** Python, Flask, pytest, HTML

---

### Task 1: Update the UI copy

**Files:**
- Modify: `/Users/adnan/Documents/join_advisor/templates/index.html`
- Test: `/Users/adnan/Documents/join_advisor/tests/test_app.py`

**Step 1: Write the failing test**

```python
def test_index_route_renders_ui():
    response = app.test_client().get("/")
    assert b"Join Advisor" in response.data
```

**Step 2: Run test to verify it fails**

Run: `pytest /Users/adnan/Documents/join_advisor/tests/test_app.py::test_index_route_renders_ui -v`
Expected: FAIL because the template still renders the older branding.

**Step 3: Write minimal implementation**

```html
<title>Join Advisor</title>
<h1>Join Advisor</h1>
```

**Step 4: Run test to verify it passes**

Run: `pytest /Users/adnan/Documents/join_advisor/tests/test_app.py::test_index_route_renders_ui -v`
Expected: PASS with the updated copy.

**Step 5: Commit**

```bash
git add /Users/adnan/Documents/join_advisor/templates/index.html /Users/adnan/Documents/join_advisor/tests/test_app.py
git commit -m "feat: rename app copy to Join Advisor"
```

### Task 2: Align CLI-facing copy

**Files:**
- Modify: `/Users/adnan/Documents/join_advisor/main.py`

**Step 1: Write the failing test**

```python
def test_print_summary_header():
    assert "Join Advisor" in captured_output
```

**Step 2: Run test to verify it fails**

Run: `pytest /Users/adnan/Documents/join_advisor/tests/test_main.py -k summary -v`
Expected: FAIL or no matching test, confirming the CLI header still uses the old name.

**Step 3: Write minimal implementation**

```python
log_header("Join Advisor")
```

**Step 4: Run test to verify it passes**

Run: `python3 /Users/adnan/Documents/join_advisor/main.py`
Expected: The first CLI banner uses `Join Advisor`.

**Step 5: Commit**

```bash
git add /Users/adnan/Documents/join_advisor/main.py
git commit -m "chore: align CLI branding with Join Advisor"
```
