# os-platform Issue Search Design

## Goal

Implement Issue OS2-2: make the os-platform skill able to find existing Issues that are close to a user's query.

The change should remain read-only and fit the current Python standard-library helper.

## User-Facing Behavior

Add a new command:

```bash
python3 scripts/os_platform.py issues search [org] "user query"
```

The command fetches Issues for the target org and returns compact JSON records sorted by best local match.

Examples:

```bash
python3 scripts/os_platform.py issues search os-skill "existing issue"
python3 scripts/os_platform.py issues search os-skill "existing issue" --status todo --assignee none
```

Existing `issues list` and `issues show` behavior must remain unchanged.

## Search Scope

The local scorer should compare the query with these Issue fields when present:

- `title`
- `body_markdown` or `body`
- `external_id`
- `number_in_org` or `number`
- `labels`
- `type`
- `priority`
- `status`

Exact title, external id, and number matches should rank strongly. Body matches should matter enough that an Issue with a relevant body can outrank an unrelated title. Labels and metadata are useful supporting signals.

## Architecture

Parser support will add `issues search` beside the existing `issues list` and `issues show` subcommands.

Request construction will reuse the existing Issue list endpoint:

```text
GET /v1/orgs/{org}/bounties
```

The search command will accept the same practical filters as `issues list`, including `--status`, `--assignee`, `--project`, `--labels`, `--type`, `--priority`, `--creator`, `--sort`, `--cursor`, and `--per-page`.

Small pure helper functions will handle tokenization, field extraction, scoring, and sorting. This keeps ranking behavior testable without network calls.

## Data Flow

1. Parse `issues search [org] <query>` plus optional list filters.
2. Apply `os-platform.json` defaults for org and limit.
3. Fetch candidate Issues through the existing list endpoint.
4. Unwrap the API envelope.
5. Score each Issue locally against the query.
6. Remove zero-score matches.
7. Print compact JSON in best-match order.

## Error Handling

The search query is required and must be non-empty after trimming.

Network, authentication, JSON, and API-envelope errors should continue using the existing error handling path.

If no candidates match, print an empty JSON array.

## Testing

Tests should cover:

- Local ranking prefers an exact title or external id match.
- A relevant body match can outrank an unrelated title.
- Zero-score Issues are omitted.
- `issues search os-skill "existing issue" --status todo --assignee none` builds a GET request to `/v1/orgs/os-skill/bounties` with the expected filters.
- `issues list` request construction remains unchanged.

