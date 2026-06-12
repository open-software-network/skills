# os-platform Issue Take Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `issues take` so agents can safely move a `todo` Issue to `in_progress`.

**Architecture:** Extend the existing `os_platform.py` helper with JSON request-body support, a narrow `issues take` parser action, and a small orchestration function that fetches the Issue before posting the status update. Keep the broad read commands unchanged and keep the write command explicit.

**Tech Stack:** Python standard library, `argparse`, `urllib.request`, `unittest`.

---

## File Structure

- Modify `skills/os-platform/scripts/os_platform.py`: request body support, `issues take` parser, status request helpers, take workflow, and main dispatch.
- Modify `tests/test_os_platform.py`: request-body, parser, and take-flow unit tests.
- Modify `skills/os-platform/SKILL.md`: document controlled write behavior.
- Modify `skills/os-platform/references/api-map.md`: document status endpoint.
- Modify `README.md`: add `issues take` example.

## Task 1: Request Body Support

**Files:**
- Modify: `skills/os-platform/scripts/os_platform.py`
- Test: `tests/test_os_platform.py`

- [ ] **Step 1: Write failing request body tests**

Add a test class to `tests/test_os_platform.py`:

```python
class RequestJsonBodyTest(unittest.TestCase):
    def setUp(self):
        self.os_platform = load_os_platform()

    def test_build_json_request_sets_body_and_content_type(self):
        request = self.os_platform.build_json_request(
            "POST",
            "https://example.test/v1/issues/1/status",
            "secret",
            {"status": "in_progress"},
        )

        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.data, b'{"status":"in_progress"}')
        self.assertEqual(request.headers["Content-type"], "application/json")
        self.assertEqual(request.headers["Authorization"], "Bearer secret")
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
python3 -m unittest tests.test_os_platform.RequestJsonBodyTest
```

Expected: fails because `build_json_request` does not exist.

- [ ] **Step 3: Implement minimal request builder and wire it into `request_json`**

Add:

```python
def build_json_request(method: str, url: str, api_key: str, body: Mapping[str, Any] | None = None) -> urllib.request.Request:
    headers = {
        "Accept": "application/json",
        "User-Agent": "os-platform-agent-skill/1.0",
        "Authorization": f"Bearer {api_key}",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")
    return urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
```

Update `request_json` to accept `body: Mapping[str, Any] | None = None` and call `build_json_request(method, url, api_key, body)`.

- [ ] **Step 4: Verify green**

Run:

```bash
python3 -m unittest tests.test_os_platform.RequestJsonBodyTest
```

Expected: pass.

## Task 2: `issues take` Request Helpers

**Files:**
- Modify: `skills/os-platform/scripts/os_platform.py`
- Test: `tests/test_os_platform.py`

- [ ] **Step 1: Write failing parser/request tests**

Add:

```python
class IssueTakeCommandTest(unittest.TestCase):
    def setUp(self):
        self.os_platform = load_os_platform()

    def test_issues_take_uses_config_org_when_only_number_is_supplied(self):
        parser = self.os_platform.build_parser()
        args = parser.parse_args(["issues", "take", "1", "--yes"])

        self.os_platform.apply_project_config(args, {"org": "os-skill"})

        method, path, query = self.os_platform.command_to_request(args)
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/v1/orgs/os-skill/bounties/1")
        self.assertEqual(query, {})
        self.assertTrue(args.yes)

    def test_issue_status_request_posts_in_progress(self):
        method, path, query, body = self.os_platform.issue_status_request("os-skill", "1", "in_progress")

        self.assertEqual(method, "POST")
        self.assertEqual(path, "/v1/orgs/os-skill/bounties/1/status")
        self.assertEqual(query, {})
        self.assertEqual(body, {"status": "in_progress"})
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
python3 -m unittest tests.test_os_platform.IssueTakeCommandTest
```

Expected: fails because `issues take` and `issue_status_request` do not exist.

- [ ] **Step 3: Implement parser and status request helper**

Add `take` to scoped refs in `set_scoped_target` by keeping it in the existing `issues` branch.

In `build_parser()`, add:

```python
issues_take = leaf_parser(issues_sub, "take", help="Move a todo Issue to in_progress after confirmation.")
issues_take.add_argument("refs", nargs="*", metavar="ref")
issues_take.add_argument("--yes", action="store_true", help="Skip confirmation prompt.")
```

Add:

```python
def issue_status_request(org: str, number: str, status: str) -> tuple[str, str, dict[str, Any], dict[str, str]]:
    org_ref = urllib.parse.quote(require_text(org, "org"))
    number_ref = urllib.parse.quote(require_text(number, "issue number"))
    return "POST", f"/v1/orgs/{org_ref}/bounties/{number_ref}/status", {}, {"status": status}
```

Add `require_text`:

```python
def require_text(value: Any, description: str) -> str:
    if value is None or str(value).strip() == "":
        die(f"{description} is required")
    return str(value)
```

- [ ] **Step 4: Verify green**

Run:

```bash
python3 -m unittest tests.test_os_platform.IssueTakeCommandTest
```

Expected: pass.

## Task 3: Take Flow

**Files:**
- Modify: `skills/os-platform/scripts/os_platform.py`
- Test: `tests/test_os_platform.py`

- [ ] **Step 1: Write failing take-flow tests**

Add tests to `IssueTakeCommandTest`:

```python
    def test_take_issue_refuses_non_todo_status(self):
        calls = []

        def fake_request(method, path, *, base_url, api_key, query=None, timeout=30, body=None):
            calls.append((method, path, body))
            return {"success": True, "data": {"external_id": "OS2-1", "status": "in_progress"}}

        result = self.os_platform.take_issue(
            "os-skill",
            "1",
            base_url="https://example.test/api",
            api_key="secret",
            timeout=30,
            assume_yes=True,
            request=fake_request,
            confirm=lambda _: True,
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(result["status"], "in_progress")
        self.assertEqual(result["take_result"], "not_todo")

    def test_take_issue_cancels_when_confirmation_declines(self):
        calls = []

        def fake_request(method, path, *, base_url, api_key, query=None, timeout=30, body=None):
            calls.append((method, path, body))
            return {"success": True, "data": {"external_id": "OS2-1", "status": "todo", "title": "Take me"}}

        result = self.os_platform.take_issue(
            "os-skill",
            "1",
            base_url="https://example.test/api",
            api_key="secret",
            timeout=30,
            assume_yes=False,
            request=fake_request,
            confirm=lambda _: False,
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(result["take_result"], "cancelled")

    def test_take_issue_posts_in_progress_when_confirmed(self):
        calls = []

        def fake_request(method, path, *, base_url, api_key, query=None, timeout=30, body=None):
            calls.append((method, path, body))
            if method == "GET":
                return {"success": True, "data": {"external_id": "OS2-1", "status": "todo", "title": "Take me"}}
            return {"success": True, "data": {"external_id": "OS2-1", "status": "in_progress"}}

        result = self.os_platform.take_issue(
            "os-skill",
            "1",
            base_url="https://example.test/api",
            api_key="secret",
            timeout=30,
            assume_yes=False,
            request=fake_request,
            confirm=lambda _: True,
        )

        self.assertEqual(calls[1], ("POST", "/v1/orgs/os-skill/bounties/1/status", {"status": "in_progress"}))
        self.assertEqual(result["status"], "in_progress")

    def test_take_issue_posts_in_progress_with_yes(self):
        calls = []

        def fake_request(method, path, *, base_url, api_key, query=None, timeout=30, body=None):
            calls.append((method, path, body))
            if method == "GET":
                return {"success": True, "data": {"external_id": "OS2-1", "status": "todo", "title": "Take me"}}
            return {"success": True, "data": {"external_id": "OS2-1", "status": "in_progress"}}

        result = self.os_platform.take_issue(
            "os-skill",
            "1",
            base_url="https://example.test/api",
            api_key="secret",
            timeout=30,
            assume_yes=True,
            request=fake_request,
            confirm=lambda _: False,
        )

        self.assertEqual(len(calls), 2)
        self.assertEqual(result["status"], "in_progress")
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
python3 -m unittest tests.test_os_platform.IssueTakeCommandTest
```

Expected: fails because `take_issue` does not exist.

- [ ] **Step 3: Implement take flow**

Add:

```python
def confirm_take_issue(issue: Mapping[str, Any]) -> bool:
    label = issue.get("external_id") or issue.get("number_in_org") or "Issue"
    title = issue.get("title") or ""
    answer = input(f"Move {label} {title!r} from todo to in_progress? [y/N] ")
    return answer.strip().lower() in {"y", "yes"}


def take_issue(
    org: str,
    number: str,
    *,
    base_url: str,
    api_key: str,
    timeout: int,
    assume_yes: bool = False,
    request: Any = request_json,
    confirm: Any = confirm_take_issue,
) -> Any:
    get_method, get_path, get_query = issue_get_request(org, number)
    payload = request(get_method, get_path, base_url=base_url, api_key=api_key, query=get_query, timeout=timeout)
    issue = unwrap_envelope(payload)
    if not isinstance(issue, Mapping):
        raise OsPlatformError("issue response did not contain an object")
    if issue.get("status") != "todo":
        result = dict(issue)
        result["take_result"] = "not_todo"
        return result
    if not assume_yes and not confirm(issue):
        return {"take_result": "cancelled", "external_id": issue.get("external_id"), "status": issue.get("status")}
    post_method, post_path, post_query, body = issue_status_request(org, number, "in_progress")
    updated_payload = request(post_method, post_path, base_url=base_url, api_key=api_key, query=post_query, timeout=timeout, body=body)
    return unwrap_envelope(updated_payload)
```

Add:

```python
def issue_get_request(org: str, number: str) -> tuple[str, str, dict[str, Any]]:
    org_ref = urllib.parse.quote(require_text(org, "org"))
    number_ref = urllib.parse.quote(require_text(number, "issue number"))
    return "GET", f"/v1/orgs/{org_ref}/bounties/{number_ref}", {}
```

Use `issue_get_request` inside `command_to_request` for issue detail reads.

- [ ] **Step 4: Verify green**

Run:

```bash
python3 -m unittest tests.test_os_platform.IssueTakeCommandTest
```

Expected: pass.

## Task 4: Main Dispatch and Docs

**Files:**
- Modify: `skills/os-platform/scripts/os_platform.py`
- Modify: `skills/os-platform/SKILL.md`
- Modify: `skills/os-platform/references/api-map.md`
- Modify: `README.md`
- Test: `tests/test_os_platform.py`

- [ ] **Step 1: Wire `main()` to call `take_issue`**

Before `command_to_request(args)` in `main()`, add:

```python
if args.resource == "issues" and args.action == "take":
    data = take_issue(
        args.org,
        args.number,
        base_url=base_url,
        api_key=api_key,
        timeout=args.timeout,
        assume_yes=args.yes,
    )
    print_payload(data, args)
    return 0
```

- [ ] **Step 2: Update documentation**

Document:

```bash
python3 scripts/os_platform.py issues take <org> <number>
python3 scripts/os_platform.py issues take <org> <number> --yes
```

Mention that this is the only controlled write command and uses:

```text
POST /v1/orgs/{org}/bounties/{number}/status
```

- [ ] **Step 3: Verify full suite and live dry command shape**

Run:

```bash
python3 -m unittest
python3 skills/os-platform/scripts/os_platform.py issues show os-skill 1
```

Expected: tests pass; live show confirms whether OS2-1 is currently `todo`.

- [ ] **Step 4: Optional live take**

If OS2-1 is still `todo`, run:

```bash
python3 skills/os-platform/scripts/os_platform.py issues take os-skill 1 --yes
```

Expected: response status becomes `in_progress`.
