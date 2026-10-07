# Verification — 2026-10-07

Measured locally with Python 3.13.14 and Node 26.5.0. These are application tests and mock-mode
browser checks; no live-model success, deployment, user count, accuracy or conversion lift is claimed.

| Check | Actual result |
| --- | --- |
| Original backend baseline (`python -m pytest`, from backend) | 2 passed |
| Updated backend (`.venv/bin/pytest backend/tests -q`) | 41 passed, 1 live test skipped |
| Frontend (`npm test`) | 5 passed |
| Clean frontend install (`npm ci`) | Passed |
| Production bundle (`npm run build`) | Passed |
| Dependency audit (`npm audit`) | 0 vulnerabilities reported |
| Python syntax/import lint and formatting | Passed |
| Browser workflow | Created synthetic brief, saved two versions, compared, reloaded and retained both |

The initial documented direct `pytest` command failed to import `app`; adding `pythonpath = .`
to the pytest configuration fixed collection from both the root and backend directory. During
cleanup, moving shared fixtures into `conftest.py` fixed a transient fixture-discovery failure.
No unresolved test failure remains. One upstream Starlette/httpx deprecation warning remains.

Backend tests cover exact Responses request contract, strict field bounds, non-JSON/malformed
responses, refusal, incomplete output, timeouts, network errors, rate limits, exhausted retries,
quota errors, Retry-After handling, metadata, no secret in settings/error output, preservation after
failure, legacy migration, restart persistence, eight concurrent saves, and transaction rollback.
Frontend tests cover mode labels, loading locks, prior output remaining visible, failure/retry,
reloading initial data and comparison controls. Mock output is deterministic, so repeat generation
has identical text; distinct versions are still persisted.

The latest main-branch GitHub run observed before these changes had failed. Historical logs had
expired (HTTP 410), so its original cause could not be confirmed. New branch CI is the reproducible
check; a historical run is not relabeled or deleted. There were no pre-existing open issues or PRs
in either target repository and no non-main remote branches to clean up.

To perform a live smoke, provide a backend API key and an accessible structured-output model,
configure a provider project spending limit, then use the explicit command in the README. It sends
one synthetic brief with retries disabled. No key or approved spend budget was supplied for this
work, so the live smoke remains skipped. Automated field validation does not measure copy quality.
