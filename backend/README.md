# Faultline backend

Python **3.12**, FastAPI, official `falkordb` driver. Implements all endpoints in
`../CONTRACT.md`; JSON is camelCase. All seeded entities and incident narratives
are **fictional**. No authentication: local demo only.

## Run

With a real FalkorDB server already listening on localhost:6379:

```sh
cd backend
uv sync --locked
uv run faultline-backend
# Equivalent ASGI target:
# uv run uvicorn faultline_backend.app:app --host 127.0.0.1 --port 8000
```

OpenAPI: `http://127.0.0.1:8000/docs`. All contract routes are under `/api`.
The default bind is loopback. **Only inside a container**, set `HOST=0.0.0.0`
(or pass the equivalent uvicorn flag); publish the container on loopback.

Settings (environment or optional `backend/.env`; example in `.env.example`):

- `FALKORDB_HOST=localhost`, `FALKORDB_PORT=6379`, optional `FALKORDB_PASSWORD`.
- `GRAPH_PREFIX=faultline_`, `QUERY_TIMEOUT_MS=3000` (100–30000).
- `HOST=127.0.0.1`, `PORT=8000` for the `faultline-backend` command.
- Optional `OPENAI_API_KEY`, `OPENAI_BASE_URL=https://api.openai.com/v1`,
  `OPENAI_MODEL=gpt-4o-mini`. Omit/unset the key for graph-tools-only mode.

`X-Workspace` defaults to `demo`: 1–40 lowercase letters/digits/hyphens, no leading
or trailing hyphen. Each workspace uses its own graph. First data access seeds
25 nodes and 31 edges. `POST /api/seed` is repeatable: `MERGE ... ON CREATE` preserves
existing properties, dependency toggles, memories, and investigations. Startup
never wipes or resets a graph. Database failure is an explicit 503, never fixture
fallback. Health checks the graph command, not merely Redis PING; unavailable
health uses the contract's health shape with HTTP 503.

## What the planner actually does

The no-key planner is a **deterministic, bounded graph-tools coordinator**, not an
LLM. A fixed seven-read plan validates the service, finds service and customer
blast radius, resolves ownership/on-call, retrieves incidents/runbooks/decisions
and cross-session memory, then rechecks target state and assembles the response.
User questions are retained as context, not translated into executable Cypher.

- Enabled `DEPENDS_ON` paths are followed in reverse for blast radius, bounded to
  six edges and 256 paths per type. Customer paths include every intermediate
  service. The originating service is not listed as its own downstream impact.
- Ownership covers the originating and all affected services. Evidence includes
  actual node-ID paths, past incidents, runbooks, decisions, and memory citations.
- Avoid feedback changes relevant runbook proposals into human-review tasks;
  helpful feedback is incorporated into proposed tasks. Feedback from all sessions
  is considered only when linked to the current affected service scope.
- Every graph operation is logged with actual Cypher, bound parameters, row count,
  and wall-clock duration. The seven planner reads are also included in the trace.
  Logs contain local demo questions/memories in persistence parameters; do not use
  sensitive production data.
- An optional genuine OpenAI-compatible call may synthesize **summary prose only**
  from tool results. It receives no tools or execution capability. Unknown citations,
  invalid output, timeout, or API errors retain the deterministic summary with a
  warning. `mode=llm` means summary synthesis actually succeeded; health always
  describes the core `graph-tools` planner. Generated prose still needs verification.

Investigation snapshots (entire JSON), Action nodes, and Memory nodes persist in
FalkorDB and link to services. Approvals only set the canonical Action status;
list responses overlay that durable status on immutable investigation snapshots.
Approval is idempotent and **never sends notifications, executes runbooks, calls
infrastructure, or changes topology**. Only the explicit demo dependency PATCH
changes enabled topology.

## Verify

```sh
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest                         # unit tests, no DB or model calls
uv run pytest -m integration -v       # real FalkorDB required; no model calls
uv run pytest -m ''                   # both suites
```

Integration tests use unique `faultline_it-*` graphs and delete only those test
graphs. They verify six-hop customer/service paths and disabled edges, exact trace
replay, ownership, persistence, restart-safe seeding, memory-driven recommendations,
approval idempotency, workspace isolation, and list limits. They fail rather than
silently skip/fake data when FalkorDB is unavailable.

Limits: 16 KiB request bodies (including chunked), 2000-character questions/memories,
100-character session IDs, strict identifiers and boolean toggles, latest 50
investigations and latest 100 memories. Planner research is bounded to 128 knowledge
rows and 100 recent scoped memories. CORS accepts only localhost/loopback origins.
Reads across planner stages are not one transaction; topology can change between
reads, and graph impact is inferred, not live telemetry. No authentication,
production tenancy/access control, background execution, or infrastructure
mutation is provided.
