# Architecture and design decisions

## Scope

Faultline is a single-process, graph-tool incident workflow with a browser client. It reasons over a synthetic declared-dependency graph, not live monitoring. The default planner is deterministic. An optional model rewrites the narrative after graph retrieval; it does not select tools or control writes.

## Data flow

1. A validated `X-Workspace` header chooses `faultline_<slug>` in FalkorDB. `demo` is the default.
2. A fixture marker seeds a new workspace once. Repeated seeding uses `MERGE`/`ON CREATE`, preserving operator memories and disabled edges.
3. An investigation validates the selected service and executes read-only, code-owned Cypher tools.
4. The response coordinator builds impact evidence, ownership citations, knowledge references, and simulated task proposals.
5. Optional model synthesis may replace the summary, but not graph-derived structured fields or actions.
6. A single graph query persists the investigation snapshot and proposed Action nodes.
7. Approval updates an Action record. Investigation-history reads reconcile action statuses with the stored snapshot.

## Graph schema

| Source | Relationship | Target | Purpose |
| --- | --- | --- | --- |
| Service | `DEPENDS_ON` | Service | Reverse traversal establishes service blast radius |
| Customer | `DEPENDS_ON` | Service | Multi-hop customer impact |
| Team | `OWNS` | Service | Responsible team |
| Person | `ON_CALL_FOR` | Team | Named responder |
| Runbook / Incident / Decision | `ABOUT` | Service | Operational guidance and historical context |
| Memory | `ABOUT` | Service | Helpful/avoid operator feedback |
| Investigation | `ABOUT` | Service | Investigation target |
| Investigation | `PROPOSES` | Action | Proposed simulated task |
| Action | `ABOUT` | Service | Task's incident context |

Public graph nodes include `id`, `label`, and `kind`. Source IDs and evidence paths refer to those IDs. The seed contains 25 company entities and 31 relationships. The dependency canvas focuses on 11 services/customers; teams, people, and documents are surfaced through ownership and evidence panels rather than cluttering that canvas. User-created memories and investigation/action records are persisted but intentionally excluded from the default company topology view to keep it readable. Memory and investigation endpoints expose them separately.

`DEPENDS_ON.enabled` allows a controlled topology experiment without deleting the underlying dependency. Impact tools require **all** relationships in a path to be enabled.

## Tools and bounds

The [Cypher reference](CYPHER.md) maps every investigation tool to its [standalone query file](../queries/) and documents the graph writes, bound parameters, and replay instructions.

The planner performs a fixed sequence:

- Target service lookup.
- Reverse service paths, at most six hops.
- Customer dependency paths, at most six hops including the customer-to-service edge.
- Ownership for the target and impacted services.
- Runbooks, prior incidents, and decisions associated with that scope.
- Cross-session memories for that scope.
- Target status recheck before response assembly.

The response trace records actual queries, bound parameters, row counts, and tool duration. It is an operation audit trail, **not model chain-of-thought**. Path results are bounded (256 per type), knowledge retrieval is capped, and result-limit warnings are surfaced. This is not an unbounded production-scale graph explorer.

The public graph represents dependency potential. It cannot establish causality, current incident propagation, or SLO violation without telemetry.

### The central traversal

```cypher
MATCH p=(c:Customer)-[:DEPENDS_ON*1..6]->(root:Service {id: $serviceId})
WHERE all(r IN relationships(p) WHERE r.enabled = true)
RETURN DISTINCT c.id, c.label, [n IN nodes(p) | n.id]
ORDER BY c.id
LIMIT 256
```

For `serviceId = "svc-redis"`, this includes the four-edge Northstar → Storefront → Checkout → Payments → Redis path. Disabling Payments → Redis makes `all(...)` false for that path, so Northstar disappears without any prompt or answer-template change. The analogous service traversal excludes the root and follows the same enabled-edge condition.

## Memory changes behavior

- A helpful lesson is attached to the proposed runbook guidance and surfaced as a reviewable reuse task.
- An applicable avoid lesson changes a runbook task into a **review** task and adds an explicit warning. It is not automatically interpreted as an executable instruction.
- Memories remain service-scoped, survive new sessions and API restarts, and are stored in the graph rather than local browser state.

Memory is explicit user input. Automatic extraction, relevance scoring, conflict resolution, expiration, and deletion UX are future work.

## Persistence

FalkorDB stores company facts, memories, investigation snapshots, and approvals. Docker enables append-only persistence on a named `/data` volume. `FALKORDB_DATA_PATH=/data` explicitly aligns the server's actual data directory with that mount (the image's default data directory must not be assumed to match it). `docker compose down` keeps it; `docker compose down -v` destroys it. AOF uses `appendfsync everysec`, so an abrupt host failure can still lose approximately the most recent second of writes.

Investigation creation persists its snapshot and tasks in one query. The multi-stage read workflow is **not** a transactionally isolated snapshot: a concurrent topology change can produce mixed-time evidence. There are no distributed job claims, worker leases, or external execution semantics.

## Isolation is not authentication

Workspace validation restricts graph-name construction to a safe slug. Each workspace gets a distinct graph. This prevents accidental mixing of contexts, but anyone who can reach the demo API can choose a workspace. It is **not a security boundary** without authenticated tenant-to-workspace authorization.

All Docker-published ports bind to `127.0.0.1`. A public deployment needs at least:

- Authenticated users and authorized workspace mapping.
- TLS and private authenticated database networking.
- Request limits, rate limiting, quotas, and workspace provisioning controls.
- Audit retention and memory/data deletion policy.
- Source freshness, provenance, and import validation.

## Model boundary

The optional OpenAI-compatible call receives retrieved incident context, not graph write capability. Output is JSON-shape validated and its cited evidence IDs must belong to the investigation. Unknown citations or provider failure retain the deterministic summary and add a warning. Free-text factual grounding is not formally proven; an engineer should verify the narrative against structured evidence.

The model API base URL is operator configuration, not request input. Untrusted questions and lesson text are provided as data. They cannot cause shell execution, arbitrary Cypher, or infrastructure actions because those capabilities do not exist in the model path.

## Why these choices

**FalkorDB rather than relational joins or a vector-only index:** the central question is a variable-length relationship traversal. A single context store also keeps operational knowledge and durable memory adjacent to the topology.

**Bounded planner rather than arbitrary generated Cypher:** reproducible demonstrations, inspectable tools, and a narrow safety boundary. This trades open-ended language understanding for reliable service-centered investigations.

**Human approval with no integration:** proves the transition from evidence to proposed action without pretending production credentials or remediation safeguards exist.

**React + FastAPI + Compose:** a small, inspectable implementation that a judge can run without external accounts.
