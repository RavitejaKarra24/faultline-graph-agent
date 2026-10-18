# Your incident agent needs relationships, not another paragraph

*Blog draft for Graph Hacks. Review and publish under your own name before entering the blog prize.*

Redis is timing out. What should an incident agent do?

A plausible answer is “restart Redis.” A useful answer is more careful: which services are downstream, which customers use them, who owns those services, and what happened the last time someone restarted Redis under load?

Those questions are not all stored in one document. They are connected facts. That is why I built **Faultline**, a graph-grounded incident command desk with FalkorDB as its context layer.

## The smallest interesting incident graph

The demo company is fictional. Its dependency chain is not complicated:

```text
Northstar Commerce → Storefront → Checkout → Payments API → Redis
Acme Retail        → Order service ─────────→ Payments API → Redis
Orbit Labs         → Analytics ───────────────────────────→ Redis
```

Each arrow means “depends on.” When Redis degrades, the impact traversal walks these edges in the opposite direction. That lets the agent connect a low-level failure with a high-level customer experience.

The graph also connects services to owners, teams, runbooks, decisions, and historical incidents. Operator lessons are persisted as memory, so the next investigation can use what the current engineer learned.

## Give the agent bounded tools

Faultline's default workflow is deliberately deterministic. An impact stage queries dependencies, an ownership stage resolves responders, a research stage retrieves related knowledge and memory, and a coordinator drafts a plan. These are specialist stages in one backend, not independently running AI models.

Every graph tool records its query, parameters, result count, and execution duration. The UI shows this audit trail alongside evidence paths. This is not private model chain-of-thought; it is an inspectable record of operations against the context store.

An optional model can synthesize a narrative after graph retrieval. It cannot generate executable Cypher or perform infrastructure actions. Without a key, the exact same graph reasoning and structured plan work locally.

## The test that catches decorative graphs

A graph visualization does not prove a graph-driven product. Here is a stronger test:

1. Investigate Redis and inspect the payment branch.
2. Remove the Payments API → Redis dependency.
3. Investigate again.

The payment branch drops out of the Redis blast radius, while Analytics remains. The customer impact changes with it. This counterfactual is the most important part of the demo: the answer depends on relationships in FalkorDB, not an answer template tied to the word “Redis.”

It is still a declared-dependency impact model—not proof that Redis caused a real outage. Keeping that distinction explicit matters.

## Memory is operational context

An engineer can save a lesson as helpful or avoid. On a later investigation, the research stage reads that lesson from the graph. A new browser session does not clear it. An avoid lesson adds a review constraint instead of silently authorizing a potentially harmful action.

The prototype does not solve automatic memory extraction, contradiction handling, or decay. Explicit operator input is a narrow but understandable starting point.

## Make the action boundary obvious

Faultline proposes response tasks and allows a human to approve them. An approval changes a persistent record. It does not page a real person, restart a database, or mutate Kubernetes.

That limitation is intentional. Before connecting remediation systems, the workflow would need authentication, authorization, idempotency at external APIs, stronger concurrency controls, rate limits, and an operational audit policy.

## What I would build next

The next useful additions are authenticated read-only imports from a service catalog, freshness timestamps on relationships, and a replay evaluation set that tests known incident scenarios against expected impact paths. Real task integrations should come after those foundations, not before.

The lesson from this build is simple: an agent does not need more confident language. It needs context it can traverse, memory it can retrieve, and evidence an engineer can check.

**Source and local setup:** https://github.com/RavitejaKarra24/faultline-graph-agent

*Built for Graph Hacks with FalkorDB and coding-assistant support. All demo company data is synthetic.*
