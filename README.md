# GenAI Ad Creative Studio

A local campaign workspace with FastAPI, React and SQLite. Draft copy from a brief, keep every
successful creative version, and compare versions side by side. Mock mode works without a key;
the optional OpenAI Responses adapter is tested through mocked HTTP contracts.

## Quick start

Requirements: Python 3.12+ and Node 22.12+ (or Node 24/26). From the repository root on macOS/Linux:

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open <http://127.0.0.1:5173>. Vite proxies `/api` to the backend; leave `VITE_API_BASE_URL` empty
for this local setup. On Windows PowerShell, use `Copy-Item .env.example .env`,
`python -m venv .venv` and `.\.venv\Scripts\Activate.ps1`; the remaining commands are the same.
The database is created automatically in ignored `backend/data/studio.db`.

## Reviewer demo

1. Confirm the header says **OFFLINE MOCK**.
2. Save a brief with a product name, factual product detail, audience, tone and objective.
3. Choose **Generate new version** twice. Each success appends a version; mock content is
   deterministic, so identical briefs produce identical text with distinct saved version metadata.
4. Use **View version** and **Compare with** to compare the outputs. Reload to verify persistence.
5. During generation, prior output stays visible and competing actions are disabled. A failure
   preserves every previous version and offers **Retry generation**.

The live header reads **LIVE PROVIDER**. Configure only the backend's ignored `.env` to enable it:

| Variable | Purpose / default |
| --- | --- |
| `GENERATION_MODE` | `mock` (default) or `provider` |
| `GENAI_PROVIDER_API_KEY` | Server-side credential, never a `VITE_` value |
| `GENAI_PROVIDER_BASE_URL` | `https://api.openai.com/v1`; this adapter rejects other endpoints |
| `GENAI_PROVIDER_MODEL` | `gpt-5-mini`; select a model your account can access |
| `GENAI_TIMEOUT_SECONDS` | Per-I/O timeout, default 20; maximum 60 |
| `GENAI_MAX_RETRIES` | Default 2 retries (3 attempts); maximum 3 |
| `GENAI_MAX_OUTPUT_TOKENS` | Default 2,000; range 128–8,000 |
| `DATABASE_URL` | SQLite path; see `.env.example` |
| `FRONTEND_ORIGINS` | Allowed browser origins |

Restart the backend after changing configuration. No live calls have been verified. Supply an API
key and choose a provider project spending limit before opting in; don't paste credentials into
briefs or command arguments. Provider timeouts can still incur charges, and retry counts are not
a dollar spending cap. Missing usage stays null; this app does not estimate model cost.

## Architecture and failure handling

```text
React brief / version comparison → FastAPI → CopyGenerator → mock or Responses HTTP
                                      ↓            ↓
                               SQLite transaction  strict output validation
                               append version + update latest
```

The existing generation abstraction owns both modes. New outputs require 1–5 nonblank strings
per field: headlines ≤120 characters, descriptions ≤300, calls to action ≤80, concepts ≤500.
The provider receives only the brief, with no prior versions or settings. Requests use strict
`text.format` JSON schema, `store=false`, no tools and an output-token cap. Schema validation
cannot establish that advertising claims are true: review copy against actual product facts.

Timeouts, network errors, 408/409/429 and server errors use bounded exponential backoff with jitter.
Authentication/client errors, refusals, malformed or incomplete output and exhausted quota fail
cleanly. Retry-After is honored within a two-second delay budget; longer waits fail for manual retry.
Responses include server-generated request IDs. Saved versions show mode, model (when live),
attempts, latency and token usage where supplied. Errors expose fixed codes and safe metadata,
never response bodies or authorization headers. API keys are omitted from settings representations.

SQLite saves each version and updates the latest set atomically. A transaction serializes concurrent
version allocation. An idempotent migration imports pre-existing creative sets without truncating
or rejecting historical output. Failed generation makes no database write.

## Tests and reproducible evidence

```bash
.venv/bin/python -m pytest backend/tests -q
cd frontend
npm ci
npm test
npm run build
npm audit
```

The backend includes HTTP contract, validation, retry, persistence, migration, concurrent-write and
rollback tests. The frontend tests loading, failure/retry, mode labels and version comparison.
CI runs both suites and the production build. See [actual verification results](evidence/verification.md)
and the [interview walkthrough](docs/interview-walkthrough.md).

One opt-in live smoke sends a synthetic brief, with retries disabled:

```bash
STUDIO_RUN_LIVE=1 .venv/bin/python -m pytest backend/tests/test_live.py -m live -q -s
```

Normal tests skip it. In PowerShell, set `$env:STUDIO_RUN_LIVE="1"` first. Output includes only safe
metadata; a passing mock contract is not evidence of a successful live call.

## Limitations

This is a single-user loopback demo. It has no authentication, per-user isolation or server request
quota. Do not expose it publicly without those controls. SQLite and loading full campaign history
are deliberate small-workspace choices; pagination and a multi-user store would be next steps.
Creative quality, conversion lift, product truth and live provider reliability are not measured.
Browser retries create new versions on success; provider attempts are not guaranteed idempotent.
There is no deployment, ad-platform publishing or automated campaign execution.

Provider contract checked 2026-10-07 against official
[Responses documentation](https://developers.openai.com/api/reference/python/resources/responses),
[structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and
[error codes](https://developers.openai.com/api/docs/guides/error-codes).
