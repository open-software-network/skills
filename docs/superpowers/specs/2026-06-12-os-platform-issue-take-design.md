# os-platform Issue Take Design

## Goal

Implement Issue OS2-1: when a user chooses to work on a `todo` Issue, the skill should support moving that Issue to `in_progress`.

The implementation should add a narrow controlled write path without turning the helper into a general-purpose mutation client.

## API Reference

The Open Software API docs live at:

```text
https://app.opensoftware.co/api/docs
```

The verified endpoint for status changes is:

```text
POST /v1/orgs/{org}/bounties/{number}/status
```

Request body:

```json
{
  "status": "in_progress"
}
```

The endpoint returns an `ApiResponse_IssueDto` envelope.

## User-Facing Behavior

Add a command:

```bash
python3 scripts/os_platform.py issues take [org] <number>
```

Behavior:

1. Fetch the current Issue with `GET /v1/orgs/{org}/bounties/{number}`.
2. If the Issue status is not `todo`, stop and report the current status.
3. If the Issue status is `todo`, ask for explicit confirmation.
4. If confirmed, send `POST /v1/orgs/{org}/bounties/{number}/status` with `{"status": "in_progress"}`.
5. Print the updated Issue payload using the existing compact/full/json output behavior.

For automation, support:

```bash
python3 scripts/os_platform.py issues take os-skill 1 --yes
```

`--yes` skips the prompt but does not skip the preflight status check.

## Scope

This design intentionally does not add a generic `update-status` command. The only write behavior is the `todo -> in_progress` take flow.

Existing read commands must keep their behavior.

## Error Handling

- Missing org or Issue number should use existing argument validation.
- If the preflight fetch fails, do not attempt the status update.
- If the Issue is not `todo`, do not attempt the status update.
- If the user declines confirmation, print a small cancellation payload and do not update.
- API errors from the status endpoint should use the existing `OsPlatformError` path.

## Documentation

Update the README with the API docs reference.

Update the skill docs and API map to document the controlled write command and the status endpoint.

## Testing

Tests should cover:

- Request construction for `issues take`.
- Status update request body construction.
- Request JSON supports JSON bodies for non-GET commands.
- Take flow refuses non-`todo` Issues.
- Take flow cancels when confirmation is declined.
- Take flow posts `in_progress` when confirmed or when `--yes` is passed.
- Existing read command behavior remains unchanged.

