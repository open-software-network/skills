# Open Software Agent Skills

Agent skills for working with Open Software.

## Install

Install the `os-platform` skill into your global Codex skills directory with the
Skills CLI:

```bash
npx skills add open-software-network/skills --skill os-platform --agent codex --global
```

Or install with the standalone script:

```bash
curl -fsSL https://raw.githubusercontent.com/open-software-network/skills/main/skills/os-platform/scripts/install.sh | bash
```

Or install from a local checkout:

```bash
bash skills/os-platform/scripts/install.sh --source skills/os-platform --force
```

## os-platform

`os-platform` lets agents query live Open Software platform data through the
production API instead of relying on stale docs, fixtures, or screenshots.

It can read current Orgs, Projects, Issues, Submissions, Comments, Activity,
Contributors, and API status.

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
