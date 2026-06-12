# os-platform Issue Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only `issues search` command that ranks existing Issues by closeness to a user query.

**Architecture:** Extend the existing single-file Python API helper with a new `issues search` parser action, reuse the current Issue list endpoint, then locally score returned records before printing compact JSON. Keep ranking helpers pure so tests can exercise them without network calls.

**Tech Stack:** Python standard library, `argparse`, `unittest`, existing `os_platform.py` helper.

---

## File Structure

- Modify `skills/os-platform/scripts/os_platform.py`: parser action, request construction, query validation, pure search helpers, and search-specific output flow.
- Modify `tests/test_os_platform.py`: unit tests for ranking, parser/request construction, and unchanged list behavior.

## Task 1: Search Request Shape

**Files:**
- Modify: `skills/os-platform/scripts/os_platform.py`
- Test: `tests/test_os_platform.py`

- [ ] **Step 1: Write the failing parser/request tests**

Add these tests to `tests/test_os_platform.py`:

```python
class IssueSearchCommandTest(unittest.TestCase):
    def setUp(self):
        self.os_platform = load_os_platform()

    def test_issues_search_builds_list_request_with_filters(self):
        parser = self.os_platform.build_parser()
        args = parser.parse_args(
            [
                "issues",
                "search",
                "os-skill",
                "existing issue",
                "--status",
                "todo",
                "--assignee",
                "none",
            ]
        )

        self.os_platform.apply_project_config(args, {})

        method, path, query = self.os_platform.command_to_request(args)
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/v1/orgs/os-skill/bounties")
        self.assertEqual(query, {"status": "todo", "assignee": "none"})
        self.assertEqual(args.search_query, "existing issue")

    def test_issues_list_request_shape_stays_unchanged(self):
        parser = self.os_platform.build_parser()
        args = parser.parse_args(["issues", "list", "os-skill", "--status", "todo"])

        self.os_platform.apply_project_config(args, {})

        method, path, query = self.os_platform.command_to_request(args)
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/v1/orgs/os-skill/bounties")
        self.assertEqual(query, {"status": "todo"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_os_platform.IssueSearchCommandTest
```

Expected: fails because `issues search` is not a valid subcommand.

- [ ] **Step 3: Add minimal parser and request support**

In `build_parser()`, add an `issues_search` parser beside `issues_list` and `issues_show`:

```python
issues_search = leaf_parser(issues_sub, "search", help="Search Issues by local query relevance.")
issues_search.add_argument("org", nargs="?")
issues_search.add_argument("search_query")
add_issue_filters(issues_search)
```

In `command_to_request()`, treat `search` like `list` for request construction:

```python
if args.action in {"list", "search"}:
    query = query_from_args(
        args,
        [
            "cursor",
            "per_page",
            "sort",
            "status",
            "type",
            "priority",
            "assignee",
            "creator",
            "project",
            "labels",
            "q",
        ],
    )
    return "GET", f"/v1/orgs/{org}/bounties", query
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_os_platform.IssueSearchCommandTest
```

Expected: pass.

## Task 2: Pure Local Ranking Helpers

**Files:**
- Modify: `skills/os-platform/scripts/os_platform.py`
- Test: `tests/test_os_platform.py`

- [ ] **Step 1: Write failing ranking tests**

Add these tests to `IssueSearchCommandTest`:

```python
    def test_search_ranking_prefers_exact_title_and_external_id_matches(self):
        issues = [
            {"title": "Add wallet screen", "external_id": "OS2-9"},
            {"title": "Unrelated work", "external_id": "OS2-2"},
            {"title": "Search existing issue", "external_id": "OS2-3"},
        ]

        ranked = self.os_platform.rank_issue_search_results(issues, "OS2-2")

        self.assertEqual([item["external_id"] for item in ranked], ["OS2-2"])

    def test_search_ranking_allows_relevant_body_to_beat_unrelated_title(self):
        issues = [
            {
                "title": "Wallet polish",
                "body_markdown": "Unrelated UI cleanup",
                "external_id": "OS2-9",
            },
            {
                "title": "Small helper change",
                "body_markdown": "Search existing issue close to user query",
                "external_id": "OS2-2",
            },
        ]

        ranked = self.os_platform.rank_issue_search_results(issues, "search existing issue")

        self.assertEqual(ranked[0]["external_id"], "OS2-2")

    def test_search_ranking_omits_zero_score_issues(self):
        issues = [
            {"title": "Wallet polish", "body_markdown": "Payment cleanup"},
            {"title": "Search existing issue", "body_markdown": "Find close matches"},
        ]

        ranked = self.os_platform.rank_issue_search_results(issues, "existing issue")

        self.assertEqual([item["title"] for item in ranked], ["Search existing issue"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_os_platform.IssueSearchCommandTest
```

Expected: fails because `rank_issue_search_results` does not exist.

- [ ] **Step 3: Add minimal pure helpers**

Add these imports near the top of `os_platform.py`:

```python
import re
```

Add helpers before `print_payload()`:

```python
WORD_RE = re.compile(r"[a-z0-9]+")


def tokenize_search_text(value: Any) -> list[str]:
    return WORD_RE.findall(str(value).lower())


def issue_search_values(issue: Mapping[str, Any]) -> list[tuple[str, Any]]:
    values: list[tuple[str, Any]] = []
    for field in ("external_id", "number_in_org", "number", "title", "body_markdown", "body", "type", "priority", "status"):
        if issue.get(field) is not None:
            values.append((field, issue[field]))
    labels = issue.get("labels")
    if isinstance(labels, list):
        for label in labels:
            if isinstance(label, Mapping):
                values.extend(("label", label.get(key)) for key in ("slug", "name", "title") if label.get(key))
            elif label:
                values.append(("label", label))
    return values


def score_issue_for_query(issue: Mapping[str, Any], query: str) -> int:
    query_text = query.strip().lower()
    query_tokens = set(tokenize_search_text(query_text))
    if not query_tokens:
        return 0

    score = 0
    for field, raw_value in issue_search_values(issue):
        value_text = str(raw_value).lower()
        value_tokens = set(tokenize_search_text(value_text))
        matched_tokens = query_tokens & value_tokens
        if not matched_tokens:
            continue
        weight = {
            "external_id": 40,
            "number_in_org": 40,
            "number": 40,
            "title": 12,
            "body_markdown": 5,
            "body": 5,
            "label": 4,
        }.get(field, 2)
        score += len(matched_tokens) * weight
        if query_text == value_text.strip():
            score += weight * 3
        elif query_text in value_text:
            score += weight
    return score


def rank_issue_search_results(issues: Sequence[Any], query: str) -> list[Any]:
    scored: list[tuple[int, int, Any]] = []
    for index, issue in enumerate(issues):
        if not isinstance(issue, Mapping):
            continue
        score = score_issue_for_query(issue, query)
        if score > 0:
            scored.append((score, index, issue))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [issue for _, _, issue in scored]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_os_platform.IssueSearchCommandTest
```

Expected: pass.

## Task 3: Search Output Flow and Query Validation

**Files:**
- Modify: `skills/os-platform/scripts/os_platform.py`
- Test: `tests/test_os_platform.py`

- [ ] **Step 1: Write failing output and validation tests**

Add these tests to `IssueSearchCommandTest`:

```python
    def test_search_payload_is_ranked_before_printing(self):
        parser = self.os_platform.build_parser()
        args = parser.parse_args(["issues", "search", "os-skill", "existing issue"])
        self.os_platform.apply_project_config(args, {})
        payload = {
            "items": [
                {"title": "Wallet polish", "external_id": "OS2-9"},
                {"title": "Search existing issue", "external_id": "OS2-2"},
            ]
        }

        output = self.os_platform.output_data_for_args(payload, args)

        self.assertEqual(output["items"][0]["external_id"], "OS2-2")

    def test_empty_search_query_is_rejected(self):
        parser = self.os_platform.build_parser()
        args = parser.parse_args(["issues", "search", "os-skill", "   "])
        self.os_platform.apply_project_config(args, {})

        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.os_platform.command_to_request(args)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_os_platform.IssueSearchCommandTest
```

Expected: fails because `output_data_for_args` does not exist and blank query validation is missing.

- [ ] **Step 3: Add output transform and validation**

Add this function before `print_payload()`:

```python
def output_data_for_args(data: Any, args: argparse.Namespace) -> Any:
    if getattr(args, "resource", None) != "issues" or getattr(args, "action", None) != "search":
        return data
    query = getattr(args, "search_query", "")
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        result = dict(data)
        result["items"] = rank_issue_search_results(data["items"], query)
        return result
    if isinstance(data, list):
        return rank_issue_search_results(data, query)
    return data
```

Update `print_payload()`:

```python
def print_payload(data: Any, args: argparse.Namespace) -> None:
    output_data = output_data_for_args(data, args)
    if args.full or args.json:
        output = output_data
    else:
        output = compact_value(output_data, limit=args.limit)
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
```

In `command_to_request()`, before building the list/search query:

```python
if args.action == "search" and not getattr(args, "search_query", "").strip():
    die("search query is required")
```

- [ ] **Step 4: Run focused tests and full suite**

Run:

```bash
python3 -m unittest tests.test_os_platform.IssueSearchCommandTest
python3 -m unittest
```

Expected: pass.

## Task 4: Documentation and Final Verification

**Files:**
- Modify: `skills/os-platform/SKILL.md`
- Modify: `skills/os-platform/references/api-map.md`
- Modify: `README.md`

- [ ] **Step 1: Add focused documentation**

Document `issues search` in the skill quick start and command list, API map command table, and README usage examples.

- [ ] **Step 2: Run full verification**

Run:

```bash
python3 -m unittest
python3 skills/os-platform/scripts/os_platform.py issues search os-skill "existing issue" --status todo --assignee none --limit 5
```

Expected: unit tests pass; live command returns OS2-2 near the top if the API key and network are available.

- [ ] **Step 3: Commit implementation**

```bash
git add skills/os-platform/scripts/os_platform.py tests/test_os_platform.py skills/os-platform/SKILL.md skills/os-platform/references/api-map.md README.md docs/superpowers/plans/2026-06-12-os-platform-issue-search.md
git commit -m "Add os-platform issue search"
```

