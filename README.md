# Open Software Agent Skills

Agent skills for working with Open Software.

| Skill | What it does |
|---|---|
| [os-design](skills/os-design/SKILL.md) | Stand up design-featuring work the Open Software way: system-blocks-first, quiet by default |
| [os-platform](skills/os-platform/SKILL.md) | Query live Open Software platform data through the production API |
| [repo-build-pr](skills/repo-build-pr/SKILL.md) | End-to-end implementation loop: prompt to reviewed draft PR |

## Install

Install a skill with the Skills CLI:

```bash
npx skills add open-software-network/skills --skill os-design
npx skills add open-software-network/skills --skill os-platform
npx skills add open-software-network/skills --skill repo-build-pr
```

Or install with the standalone script:

```bash
curl -fsSL https://raw.githubusercontent.com/open-software-network/skills/main/skills/os-platform/scripts/install.sh | bash
```

Or install from a local checkout:

```bash
bash skills/os-platform/scripts/install.sh --source skills/os-platform --force
```

## os-design

`os-design` is the entry point for design-featuring work: it grounds agents
in the repo's existing design system before any pixels, enforces composing
from canonical blocks (token before value, primitive before bespoke), and
carries the house taste - quiet by default, one-dial tuning, and the
non-negotiables (no all caps, no tabular numerals, no typographic dashes).

It routes to specialist design skills when they are installed (impeccable,
emil-design-eng, make-interfaces-feel-better, transitions-dev, mobbin) under
one rule - skills advise, the system decides - and is self-sufficient when
they are not. References: `taste.md` (the full sensibility with shipped
numbers), `workflow.md` (reference-driven standup, state-parking drivers,
screenshot loop, handoff), `skill-map.md` (routing and the filter rule).

The skill stops at handoff: it never commits, pushes, or opens a PR unless
explicitly asked.

## repo-build-pr

`repo-build-pr` is the end-to-end implementation loop that takes a feature
prompt, bug report, or tracker task id to a reviewed draft PR: clarify, plan,
implement in an isolated worktree, validate with deterministic checks plus
live app walkthroughs, attach QA evidence, and run the automated review loop
with judgment. Authored in os-june, where it is also vendored; its repo
specifics adapt per repo.

## os-platform

`os-platform` lets agents query live Open Software platform data through the
production API instead of relying on stale docs, fixtures, or screenshots.

It can read current Orgs, Projects, Issues, Submissions, Comments, Activity,
Contributors, and API status.

API reference:

```text
https://app.opensoftware.co/api/docs
```

Example Issue commands:

```bash
python3 skills/os-platform/scripts/os_platform.py issues list open-software --status todo
python3 skills/os-platform/scripts/os_platform.py issues search open-software "wallet bug" --status todo --assignee none
python3 skills/os-platform/scripts/os_platform.py issues show open-software 123
python3 skills/os-platform/scripts/os_platform.py issues take open-software 123 --yes
```

## Configuration

The default API base URL is:

```text
https://app.opensoftware.co/api
```

Set an API key before use:

```bash
export OS_PLATFORM_API_KEY="..."
```

Optionally override the API base URL:

```bash
export OS_PLATFORM_API_BASE_URL="https://..."
```

Optional project defaults can live in `os-platform.json` at the root of a
workspace:

```json
{
  "org": "open-software",
  "limit": 20
}
```

Both fields are optional. Do not store API keys in this file.
