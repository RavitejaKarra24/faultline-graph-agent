# Cypher queries and graph algorithm

Faultline runs these seven read-only tools in order for each investigation. The `.cypher` files contain the same query text as [`planner.py`](../backend/src/faultline_backend/planner.py), with line breaks for readability. User values are driver-bound parameters. Each executed query, its parameters, result count, and duration appear in the API response's `trace` and the UI's query trace.

| Order / file | Purpose | Parameters | Result |
| --- | --- | --- | --- |
| [01-target](../queries/01-target.cypher) | Validate the selected service | `serviceId` | Service properties |
| [02-service-impact](../queries/02-service-impact.cypher) | Find services that transitively depend on the target | `serviceId` | Consumer ID, label, ordered evidence path |
| [03-customer-impact](../queries/03-customer-impact.cypher) | Find customers that transitively depend on the target | `serviceId` | Customer ID, label, ordered evidence path |
| [04-ownership](../queries/04-ownership.cypher) | Find owning teams and their on-call people | `serviceIds` | Service, team, and person IDs/labels |
| [05-knowledge](../queries/05-knowledge.cypher) | Retrieve linked runbooks, incidents, and decisions | `serviceIds`, `kinds` | Source ID, title, description, kind, related service |
| [06-memory](../queries/06-memory.cypher) | Recall helpful/avoid lessons from all sessions | `serviceIds` | Latest 100 memory property maps |
| [07-status](../queries/07-status.cypher) | Recheck recorded target status and tier | `serviceId` | Status and tier |

For the default example, `serviceId` is `svc-redis`. After tool 02, `serviceIds` is the target plus the distinct impacted service IDs. Tool 05 binds `kinds` to `["Incident", "Runbook", "Decision"]`. Those values are computed by the planner, not supplied by a model.

## Run a supplied query

From the repository root, with the Docker stack running:

```bash
# Initialize the default workspace if the UI has not been opened yet.
curl --fail http://localhost:8000/api/graph > /dev/null

uv sync --project backend --frozen
uv run --project backend python - <<'PY'
from pathlib import Path
from falkordb import FalkorDB

client = FalkorDB(host="127.0.0.1", port=6379)
try:
    graph = client.select_graph("faultline_demo")
    query = Path("queries/03-customer-impact.cypher").read_text()
    result = graph.ro_query(query, {"serviceId": "svc-redis"}, timeout=3000)
    for row in result.result_set:
        print(row)
finally:
    client.connection.close()
PY
```

On an unmodified fixture the result contains Acme Retail, Northstar Commerce, and Orbit Labs. Northstar's evidence path is:

```text
customer-northstar → svc-storefront → svc-checkout → svc-payments → svc-redis
```

The browser at http://localhost:3000 can also inspect `faultline_demo`. Use the API's trace to obtain the exact parameter values for any investigation; each trace query can be replayed through `graph.ro_query(step["query"], step["params"])`.

## Algorithm and behavior

1. Validate the target service in the selected workspace graph.
2. Traverse dependency edges ending at that service, with a maximum of six hops. Every relationship must have `enabled = true`. Collect distinct service and customer paths separately, capped at 256 paths per type, then deduplicate IDs in Python.
3. Resolve ownership for the target and impacted services. An optional person match preserves a team even if no on-call person is assigned.
4. Retrieve graph-linked operational knowledge and the latest service-scoped memories across sessions. Knowledge is capped at 128 rows; memory at 100. A cap warning is included when a bound is reached.
5. Recheck status and tier, then assemble cited response tasks. Applicable `avoid` feedback changes runbook proposals into review tasks. Helpful feedback becomes reviewable guidance. Severity is deterministic: tier 0 and at least three impacted customers → critical; any customers → high; any services → moderate; otherwise low.
6. Persist the result and proposed actions. Optional model synthesis rewrites only the summary; graph evidence and tasks remain code-owned.

This is bounded reachability with explicit path evidence. It does not claim live causal diagnosis, shortest-path selection, PageRank, embeddings, MCP tool selection, or independent LLM workers. Reads across the seven tools are not a transactionally isolated snapshot.

Disable Payments API → Redis with the UI switch and investigate Redis again: only Analytics and Orbit Labs remain in the blast radius. Re-enable the edge after the experiment. The [integration tests](../backend/tests/test_integration.py) verify the changed results, six-hop bounds, disabled intermediate edges, and exact trace replay against FalkorDB.

## Graph writes the product depends on

The canonical implementations and all supporting reads are in [`storage.py`](../backend/src/faultline_backend/storage.py). They use bound parameters and `graph.query`; the seven investigation reads above use `graph.ro_query`.

### Seed the company graph

For each trusted fixture label (`Service`, `Customer`, `Team`, `Person`, `Runbook`, `Incident`, `Decision`), `seed()` binds its list of property maps as `nodes`:

```cypher
UNWIND $nodes AS props
MERGE (n:Service {id: props.id}) ON CREATE SET n += props
```

For each trusted fixture relationship (`DEPENDS_ON`, `OWNS`, `ON_CALL_FOR`, `ABOUT`), it binds `edges` as maps of `source`/`target` IDs:

```cypher
UNWIND $edges AS edge MATCH (s {id: edge.source}), (t {id: edge.target})
MERGE (s)-[r:DEPENDS_ON]->(t) ON CREATE SET r.enabled = true
```

Only fixture constants replace labels/types in these templates. An internal `Workspace` node with ID `fixture-v1` marks initialization. `MERGE`/`ON CREATE` preserve existing lessons and disabled edges during reseeding. The complete synthetic input is [`fixture.py`](../backend/src/faultline_backend/fixture.py).

### Toggle a dependency

```cypher
MATCH (s {id: $source})-[r:DEPENDS_ON]->(t {id: $target})
SET r.enabled = $enabled RETURN s.id, t.id, r.enabled
```

The walkthrough uses `source = "svc-payments"`, `target = "svc-redis"`, and a boolean `enabled`.

### Store a cross-session lesson

```cypher
MATCH (s:Service {id: $serviceId})
CREATE (m:Memory {id: $id, serviceId: $serviceId, content: $content,
                 outcome: $outcome, sessionId: $sessionId, createdAt: $createdAt})
CREATE (m)-[:ABOUT]->(s) RETURN m.id
```

The backend generates `id` and `createdAt`; the request supplies a valid service ID, content, `helpful`/`avoid` outcome, and originating session. Recall is intentionally not filtered by session, so the lesson changes later investigations.

### Persist an investigation and its tasks

```cypher
MATCH (s:Service {id: $serviceId})
CREATE (i:Investigation {id: $id, sessionId: $sessionId, createdAt: $createdAt, json: $json})
CREATE (i)-[:ABOUT]->(s) WITH i, s UNWIND $actions AS task
CREATE (a:Action {id: task.id, status: 'pending', json: task.json})
CREATE (i)-[:PROPOSES]->(a) CREATE (a)-[:ABOUT]->(s)
```

`json` is the serialized investigation snapshot. `actions` is a list of maps with `id` and serialized task `json`. This is one write query. History reads reconcile the current Action status with the snapshot.

### Approve a simulated task

```cypher
MATCH (a:Action {id: $id}) SET a.status = 'approved' RETURN a.json, a.status
```

`id` identifies a proposed task in the current workspace. Approval records intent; it never sends messages or modifies infrastructure.
