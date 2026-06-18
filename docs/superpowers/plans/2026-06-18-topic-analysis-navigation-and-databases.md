# Topic Analysis Navigation And Databases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add left navigation, a settings modal, and single-source database selection across `PubMed`, `arXiv`, and `Semantic Scholar`.

**Architecture:** Keep the current static frontend shell but split it into sidebar and module views. Extend the in-memory run workflow with a `database` field and route collection through a source selector that chooses one collector class per run.

**Tech Stack:** Static HTML/CSS/JS, FastAPI-compatible routes, in-memory service state, pytest

---

### Task 1: Lock In Failing Contract Tests

**Files:**
- Modify: `D:\ResearchMind\tests\integration\test_frontend_shell.py`
- Modify: `D:\ResearchMind\tests\integration\test_api_research_runs.py`
- Modify: `D:\ResearchMind\tests\unit\test_research_service.py`

- [ ] **Step 1: Write failing frontend shell assertions**

```python
assert "主题论文分析" in html
assert "会议论文近期趋势" in html
assert "settingsModal" in html
assert "database-tabs" in html
```

- [ ] **Step 2: Run targeted frontend shell tests to verify they fail**

Run: `py -m pytest tests/integration/test_frontend_shell.py -q`
Expected: FAIL because the current shell still contains the old always-visible settings card and no database tabs or second module.

- [ ] **Step 3: Write failing API/service assertions for database propagation**

```python
assert fetch_calls[0]["database"] == "semantic_scholar"
assert created["database"] == "semantic_scholar"
assert run["database"] == "arxiv"
```

- [ ] **Step 4: Run targeted backend tests to verify they fail**

Run: `py -m pytest tests/integration/test_api_research_runs.py tests/unit/test_research_service.py -q`
Expected: FAIL because the request schema and service do not yet accept or return `database`.

### Task 2: Add Database-Aware Collectors

**Files:**
- Create: `D:\ResearchMind\app\services\collectors\arxiv_source.py`
- Create: `D:\ResearchMind\app\services\collectors\semantic_scholar_source.py`
- Modify: `D:\ResearchMind\app\services\collectors\__init__.py`
- Modify: `D:\ResearchMind\app\workflows\state.py`
- Modify: `D:\ResearchMind\app\workflows\nodes.py`
- Modify: `D:\ResearchMind\app\schemas\research_runs.py`
- Modify: `D:\ResearchMind\app\services\research_service.py`
- Modify: `D:\ResearchMind\app\api\routes\research_runs.py`

- [ ] **Step 1: Extend run schema/state with `database`**
- [ ] **Step 2: Add source selector helper in workflow collection**
- [ ] **Step 3: Implement minimal arXiv fetch-and-parse source**
- [ ] **Step 4: Implement minimal Semantic Scholar fetch-and-parse source**
- [ ] **Step 5: Update serialization to return `database`**

### Task 3: Rebuild The Frontend Shell

**Files:**
- Modify: `D:\ResearchMind\app\static\index.html`
- Modify: `D:\ResearchMind\app\static\styles.css`
- Modify: `D:\ResearchMind\app\static\app.js`

- [ ] **Step 1: Replace sidebar markup with module navigation and settings button**
- [ ] **Step 2: Add settings modal markup**
- [ ] **Step 3: Add topic-analysis database tabs and state wiring**
- [ ] **Step 4: Add upcoming-state rendering for `会议论文近期趋势`**
- [ ] **Step 5: Keep existing workflow polling and selection analysis behavior intact**

### Task 4: Verify The Full Change

**Files:**
- Test: `D:\ResearchMind\tests\integration\test_frontend_shell.py`
- Test: `D:\ResearchMind\tests\integration\test_api_research_runs.py`
- Test: `D:\ResearchMind\tests\unit\test_research_service.py`
- Test: `D:\ResearchMind\tests\unit\test_pubmed_source.py`

- [ ] **Step 1: Run focused test suite**

Run: `py -m pytest tests/integration/test_frontend_shell.py tests/integration/test_api_research_runs.py tests/unit/test_research_service.py tests/unit/test_pubmed_source.py -q`
Expected: PASS

- [ ] **Step 2: Inspect git diff for unintended churn**

Run: `git diff -- app tests docs`
Expected: Only the planned frontend, workflow, collector, and docs changes appear.
