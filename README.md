# Faultline

### Your incident has a blast radius. Your agent should know it.

Faultline is a graph-grounded incident command desk. Start with a failing service; follow its dependencies to affected products and customers; find the people responsible; recover previous incident knowledge; and draft a response with an inspectable evidence trail.

**Built for [Graph Hacks: Context for AI Agents](https://www.wemakedevs.org/hackathons/falkordb) · Powered by FalkorDB · MIT licensed**

[![Checks](https://github.com/RavitejaKarra24/faultline-graph-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/RavitejaKarra24/faultline-graph-agent/actions/workflows/ci.yml)

[Submission copy](docs/SUBMISSION.md) · [Cypher queries](docs/CYPHER.md) · [Architecture](docs/ARCHITECTURE.md) · [Recording walkthrough](docs/DEMO.md)

The submitter will supply the final demo video. The entry uses the complete local setup below rather than a public deployment.

![Faultline incident command desk](docs/screenshot-overview.png)

## The problem

“Redis is timing out” isn't enough context to act. The useful questions cross records:

- Does the storefront depend on it indirectly?
- Which customers are downstream, and who owns the affected services?
- What did the team try last time? What should we *not* repeat?
- Can we show the actual relationship behind a recommendation?

A document similarity search can find a Redis runbook. It cannot, by itself, establish the live chain **Northstar Commerce → Storefront → Checkout → Payments API → Redis**. Faultline traverses that chain in FalkorDB before making a plan.

## Run it — no AI key required

Requires **Docker with Compose**, a running Docker engine, and internet access for the first build.

```bash
git clone https://github.com/RavitejaKarra24/faultline-graph-agent.git
cd faultline-graph-agent
docker compose up --build -d
```

Open **http://localhost:8080**. First build can take a few minutes.

Verify startup before opening the app:

```bash
docker compose ps
curl --fail http://localhost:8000/api/health
```

The API should return `{"status":"ok","database":"FalkorDB","mode":"graph-tools","version":"0.1.0"}`. The database and API should be healthy, and the web container should be running. The first graph or investigation request creates the fictional company graph automatically.

| URL | Purpose |
| --- | --- |
| http://localhost:8080 | Incident command desk |
| http://localhost:8000/docs | Interactive API documentation |
| http://localhost:8000/api/health | Backend / FalkorDB health |
| http://localhost:3000 | FalkorDB Browser |

The fictional company graph seeds automatically. No credentials, paid models, or external integrations are needed. FalkorDB is mandatory at runtime: an unavailable database produces a real error, **not a fake offline response**.

```bash
docker compose logs -f api      # Troubleshoot startup
docker compose down             # Stop; keep graph and memory
docker compose up -d            # Resume with persisted memory
# DESTRUCTIVE: docker compose down -v removes all demo graphs and memory.
```

If startup fails, start Docker Desktop (or your Docker engine), then retry `docker compose up --build -d`. Ports **8080, 8000, 6379, and 3000** must be free. Inspect `docker compose logs --tail=100 falkordb api web` for build or health errors. No `.env` file is required for the default setup. If you previously configured an AI key and want key-free mode, leave `OPENAI_API_KEY` empty in `.env` and recreate the API container.

## A two-minute judge's walkthrough

1. **Investigate Redis.** Keep the default question and run an investigation. Inspect affected services, customers, and owners.
2. **Follow the proof.** Open evidence paths and the query trace. Each tool records its actual Cypher, parameters, result count, and elapsed time.
3. **Remember a lesson.** Add an `avoid` memory for Redis, such as “Do not restart Redis during checkout traffic; drain the payment connection pool first.”
4. **Start a new session.** Investigate again. The saved memory remains available to the response coordinator; it is stored in FalkorDB, not browser storage.
5. **Change the graph.** Disable the Payments API → Redis dependency using the topology control, then rerun the investigation. The payment branch no longer contributes to Redis's blast radius. Re-enable the edge afterward.
6. **Approve a draft action.** Approval is persisted and visible, but is explicitly simulated: no page is sent and no infrastructure is modified.

See [the recorded demo and script](docs/DEMO.md) for the walkthrough and [submission copy](docs/SUBMISSION.md) for the entry form.

## Why this is a graph agent, not a chatbot over a diagram

FalkorDB is the primary context and memory store. It determines:

- **What to investigate:** reverse traversal of enabled dependency edges, up to six hops.
- **Who is affected:** customer-to-service paths, not keyword matching.
- **Who should respond:** ownership relationships for the affected services.
- **What to do next:** connected runbooks, prior incidents, decisions, and persistent helpful/avoid lessons.
- **Why:** concrete node paths and source IDs accompany the response.

The topology toggle is a falsifiable demo: change one relationship and the answer changes. The graph isn't decorative, and there is no parallel in-memory graph answering the question.

### Execution modes — transparent by design

**`graph-tools` (default):** a bounded, deterministic agent workflow coordinates impact analysis, ownership resolution, knowledge/memory retrieval, and response planning. It uses actual graph tools but **does not use an LLM**. These are specialist stages in one process, not separate independently running AI models. This mode is reproducible, key-free, and appropriate for a time-sensitive demo.

**`llm` (optional):** after graph tools complete, an OpenAI-compatible model can synthesize the narrative from the retrieved context. The model does not invent Cypher, select arbitrary tools, or execute actions. Structured evidence, impact, and approval boundaries remain graph-derived. If synthesis fails, the grounded plan remains available with a warning.

```bash
cp .env.example .env
# Edit .env: set OPENAI_API_KEY and optionally OPENAI_MODEL.
docker compose up -d --force-recreate api
```

**Privacy:** enabling model synthesis sends investigation context, including relevant saved lessons, to the configured model provider. Use synthetic data unless you have permission.

## Architecture

```mermaid
flowchart LR
    UI[React command desk] --> API[FastAPI]
    API --> Impact[Impact analyst]
    Impact --> Owners[Ownership resolver]
    Owners --> Research[Knowledge and memory researcher]
    Research --> Plan[Response coordinator]
    Impact <--> Graph[(FalkorDB)]
    Owners <--> Graph
    Research <--> Graph
    Plan --> Graph
    Plan -. optional grounded narrative .-> LLM[OpenAI-compatible model]
    API --> Approval[Human approval: simulated only]
    Approval --> Graph
```

### Graph model

```mermaid
graph LR
    Customer -->|DEPENDS_ON| Service
    Service -->|DEPENDS_ON| OtherService[Service]
    Team -->|OWNS| Service
    Person -->|ON_CALL_FOR| Team
    Runbook -->|ABOUT| Service
    Incident -->|ABOUT| Service
    Decision -->|ABOUT| Service
    Memory -->|ABOUT| Service
    Investigation -->|ABOUT| Service
    Investigation -->|PROPOSES| Action
    Action -->|ABOUT| Service
```

| Node label | Stored facts |
| --- | --- |
| `Service` | Stable ID, display label, description, recorded status, tier |
| `Customer` | Stable ID, display label, description; dependencies identify used services |
| `Team`, `Person` | Ownership and on-call relationships; a person's role |
| `Runbook`, `Incident`, `Decision` | Source ID, title in `label`, guidance/history in `description` |
| `Memory` | Service ID, content, `helpful`/`avoid` outcome, originating session, timestamp |
| `Investigation` | ID, session, timestamp, JSON result snapshot; target and proposed actions are graph links |
| `Action` | ID, pending/approved status, JSON task payload; linked to its investigation and target service |
| `Workspace` | Internal fixture-version marker used for idempotent initialization |

Dependency edges point **from the consumer to its dependency**. `DEPENDS_ON.enabled` controls whether traversals include the edge. The initial graph has **25 company nodes and 31 relationships**; memories, investigations, and actions are added as the app is used. Each workspace uses a separate `faultline_<slug>` graph.

See [architecture and tradeoffs](docs/ARCHITECTURE.md) for exact relationships, isolation, persistence, and limitations. [CONTRACT.md](CONTRACT.md) documents the API. FastAPI's `/docs` is the generated schema reference.

### Queries and graph algorithm

The [query reference](docs/CYPHER.md) explains all seven investigation tools, their parameters, graph writes, and a runnable example. Exact read queries are also provided as [standalone `.cypher` files](queries/). The algorithm follows enabled reverse dependency paths for up to six hops, resolves owners, retrieves related guidance and persistent lessons, and attaches those paths to simulated response tasks. It uses Cypher traversals rather than PageRank or a separate graph-algorithm service. The runtime implementations are [planner.py](backend/src/faultline_backend/planner.py) and [storage.py](backend/src/faultline_backend/storage.py).

## Local development

Requires **Python 3.12**, [uv](https://docs.astral.sh/uv/), [Bun 1.4.3+](https://bun.sh/), and Docker.

```bash
# Terminal 1: graph database
docker compose up -d falkordb

# Terminal 2: API
cd backend
uv sync --frozen
uv run uvicorn faultline_backend.app:app --reload --host 127.0.0.1 --port 8000

# Terminal 3: web UI (from repository root)
cd frontend
bun install --frozen-lockfile
bun run dev --host 127.0.0.1
```

Open the Vite URL printed in terminal. `/api` requests proxy to port 8000. Docker's port-8080 app and the local dev app share the same graph if they use the default workspace.

### Checks

```bash
make check             # Backend unit tests, Ruff, TypeScript, frontend lint/format/build
make integration       # Real FalkorDB integration tests; database must be running
```

The integration suite is deliberately separate from unit tests: **mock-only tests cannot prove Cypher works**. Browser smoke coverage and reproducible test instructions are documented in [testing](docs/TESTING.md).

## Repository

```text
backend/       FastAPI, parameterized graph tools, planner, fixture, tests
frontend/      React + TypeScript command desk and topology visualization
infra/         Multi-stage Dockerfiles and nginx reverse proxy
scripts/       Reproducible browser smoke test
queries/       Standalone Cypher for all seven investigation tools
compose.yaml   FalkorDB + API + UI, local-only exposed ports, persistent volume
docs/          Architecture, demo, testing, submission copy, blog draft
```

## Scope, safety, and honest limitations

- All seeded infrastructure, customers, people, incidents, and documents are **fictional**. This is a working prototype, not a production incident platform.
- **Actions are drafts.** “Approve” records a simulated approval in the graph; it does not call Slack, PagerDuty, Kubernetes, or cloud APIs.
- No authentication/RBAC is included. Workspace headers provide graph namespaces, **not access control**. Compose binds ports to loopback. Do not expose this demo publicly without authentication, TLS, rate limits, and protected database credentials.
- Traversals are bounded at six dependency hops. The fixture represents explicit dependency facts, not real-time telemetry or causal root-cause proof.
- Memory is explicit operator input. There is no automatic extraction from Slack/GitHub, vector retrieval, memory decay, or contradiction resolution.
- The graph-tools workflow is deterministic. Optional LLM mode adds narrative synthesis, not open-ended autonomous planning.
- A single-instance persistent volume and synchronous workflow are sufficient for this demo; high-concurrency coordination, job queues, locking, and distributed worker claims are not implemented.

## Hackathon fit

| Track | Implemented demonstration |
| --- | --- |
| **01 · Agents That Act on Connected Data** (primary) | Multi-hop impact reasoning, parameterized Cypher tools, evidence-linked action drafts, human approval |
| **02 · Agent Memory and Coordination** (additional fit) | Cross-session lessons, graph-persisted investigations/actions, shared context across specialist stages, workspace namespaces |
| **03 · Company Brain** (additional fit) | Services, teams, people, customers, runbooks, historical incidents, and decisions connected in one graph |

**Submission track: 01 · Agents That Act on Connected Data.** The other rows describe related capabilities; they are not additional track entries.

Built with coding-assistant support. The submitter should review the code, run the demo, and be prepared to explain the graph model and planner. See [LICENSE](LICENSE).
