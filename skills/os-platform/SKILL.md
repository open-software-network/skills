---
name: os-platform
description: Query live Open Software os-platform production data through the platform API. Use when an agent needs current Issues/Bounties, Orgs, Projects, Submissions, Comments, Activity, Contributors, or API status instead of inspecting repo files, fixtures, screenshots, or stale docs.
---

# os-platform

Use this skill when the user asks about current Open Software / os-platform state: Issues, Bounties, Projects, Orgs, Submissions, Comments, Activity, Contributors, or whether API endpoints are real-backed. Prefer the bundled script over reading code, seed data, frontend fixtures, or docs when the question is about production data.

## Quick Start

Run commands from this skill directory:

```bash
python3 scripts/os_platform.py --base-url "$OS_PLATFORM_API_BASE_URL" status
python3 scripts/os_platform.py issues list open-software --q "wallet" --limit 10
python3 scripts/os_platform.py issues show open-software 123
```

Configuration:

- `OS_PLATFORM_API_BASE_URL` is required unless `--base-url` is passed.
- `OS_PLATFORM_API_KEY` is required unless `--api-key` is passed. The script sends it as `Authorization: Bearer ...`.
- Never ask the user to paste an API key into chat. Ask them to set the environment variable in their shell or agent runtime.
- The installer does not prompt for or write environment values. If env vars are missing, tell the user to set them first.

## Available Script

`scripts/os_platform.py` is a read-only API helper. It uses only Python standard library modules.

Core commands:

```bash
python3 scripts/os_platform.py status
python3 scripts/os_platform.py org get <org>
python3 scripts/os_platform.py projects list <org>
python3 scripts/os_platform.py project get <org> <project>
python3 scripts/os_platform.py issues list <org>
python3 scripts/os_platform.py issues show <org> <number>
python3 scripts/os_platform.py submissions list <org> <issue-number>
python3 scripts/os_platform.py activity list <org> <issue-number>
python3 scripts/os_platform.py comments list issue <org> <issue-number>
python3 scripts/os_platform.py contributors list <org>
python3 scripts/os_platform.py contributors show <org> <user-handle>
python3 scripts/os_platform.py raw GET /v1/...
```

Common flags:

- `--limit N` caps list output.
- `--json` prints the unwrapped `data` payload.
- `--full` prints the full unwrapped data without compact summarization.
- `--base-url URL` overrides `OS_PLATFORM_API_BASE_URL`.

`scripts/install.sh` installs this skill into a local agent skills directory. It defaults to `~/.codex/skills`, supports `--dest`, `--source`, `--repo`, `--ref`, `--path`, and `--force`, and never stores credentials.

## Workflow

1. Decide whether the question is about current production state. If yes, use this skill.
2. If the target route is unclear, read `references/api-map.md`.
3. Run the narrowest script command that answers the question.
4. Use default compact output for summaries. Use `--json` or `--full` only when exact fields matter.
5. Cite the live API result in your answer, and mention if a route appears fixture-backed or unreachable.

## Language Rules

- User-facing product language says **Issue**.
- Internal tables/code may say **Bounty**.
- The product is **Open Software** and the platform/repo is **os-platform**.
- If the API path says `bounties`, explain results to users as Issues unless discussing internal implementation.

## Safety

- The bundled API script is read-only. Do not add mutation commands unless the user explicitly asks for a new version of the skill.
- Do not print or persist `OS_PLATFORM_API_KEY`.
- Do not infer private data from missing public data. A 404 on private/member-only resources can mean hidden, missing, or inaccessible.
- Treat production data as current at request time, not as a durable local fact.

## Reference

Read `references/api-map.md` for endpoint mappings, useful filters, and real-vs-fixture guidance.
