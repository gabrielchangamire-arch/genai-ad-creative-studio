# Creative Studio interview walkthrough

Start with the user problem: regeneration used to overwrite the only saved creative set. The UI
also depended on a generic provider endpoint with no completed provider contract. The change makes
provider failure diagnosable and preserves the work a reviewer already approved or wants to compare.

1. **Brief boundary:** FastAPI validates product fields and lengths. Only those five fields are sent
   upstream. React receives the public mode, not API settings or keys. The browser never contacts
   the provider directly.
2. **Adapter:** `CopyGenerator` retains mock mode and the original `create_set` compatibility method.
   `generate` additionally returns metadata. Direct HTTP keeps the contract visible: strict schema,
   no tools, disabled storage, a token cap and finite retry settings. The endpoint is restricted to
   the documented provider host so a configuration typo cannot send its key to another service.
3. **Validation:** the provider's schema is backed by local Pydantic validation. Empty strings,
   extra keys, non-string values, excess items and overlong copy all fail before persistence.
   Refusals and incomplete Responses envelopes are separate outcomes, not JSON parse accidents.
4. **Failure handling:** retry transient failures with capped jitter, stop on permanent client and
   quota errors, and preserve safe request IDs and usage when available. Never log provider bodies.
   A retry may repeat billable work after a timeout; bounded retries are not a guarantee of exactly
   one provider execution. Timeout settings are per HTTP I/O operation, not a strict total deadline.
5. **Persistence:** `BEGIN IMMEDIATE` serializes version-number allocation. Append the version and
   update the latest creative set in one transaction; either both commit or neither does. Tests
   deliberately abort the second statement to verify rollback. Old output migrates exactly once
   and keeps its original contents even if the new limits are tighter.
6. **Interface:** old output stays visible while generation runs. Successful output becomes a new
   version, with the preceding version selected for comparison. Failure leaves history untouched
   and exposes a retry action. React escapes text; generated text is never interpreted as HTML.
7. **Evidence:** show mocked HTTP request assertions, a timeout exhausting three attempts, concurrent
   saves generating distinct version numbers, a reload retaining versions, and the optional live
   smoke. The offline suite proves application behavior, not provider availability or copy quality.

Why this architecture? SQLite transactions and a small provider adapter solve the current problem
without a queue, orchestration framework or separate vector store. Synchronous generation fits a
local demo, but a larger multi-user service needs authentication, per-user quotas, cancellation,
job management, pagination and durable request accounting. Advertising review remains human work:
a well-shaped response can still contain an unsupported product claim.
