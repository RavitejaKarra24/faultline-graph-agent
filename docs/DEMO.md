# Faultline — demo script

Target length: 2–3 minutes. Use the default synthetic workspace. No API key needed.

## Before recording

1. `docker compose up --build -d` and open http://localhost:8080.
2. Check `/api/health` reports FalkorDB connected.
3. Make sure Payments API → Redis is enabled. Use a clean workspace if you have previously added lessons.
4. Set browser zoom to 100%, hide unrelated tabs, and avoid showing credentials.

## Narration and clicks

### 0:00 — The missing context

> “When Redis times out, a generic agent can suggest restarting it. But it doesn't know what depends on Redis, which customers are affected, or why that restart failed last time. This is Faultline, an incident command desk whose context layer is FalkorDB.”

Show the graph and the default Redis investigation question.

### 0:20 — Connected data determines the answer

Click **Investigate**.

> “The impact stage traverses dependencies in reverse. A customer is connected to Storefront, which depends on Checkout, which depends on Payments, which depends on Redis. That is a multi-hop fact—not a similarity match.”

Show impacted services/customers, owners, and an evidence path. Explain arrow direction: A → B means A depends on B; blast-radius reasoning walks backwards.

### 0:50 — Inspectable reasoning, not hidden thoughts

Open the query trace and expand a query.

> “These are actual executed Cypher tools, their parameters, result counts, and timings. The runbook and earlier incident constrain the plan. This is a tool audit trail, not a claim to expose private model reasoning.”

Show the prior incident / runbook / decision sources.

### 1:15 — Memory survives the session

Add an `avoid` memory: “Don't restart Redis during checkout traffic; drain the payment connection pool first.” Start a new session and investigate Redis again.

> “This lesson lives in FalkorDB. It survives a new browser session and is available to later specialist stages. The plan includes a review gate for things operators have told us to avoid.”

### 1:45 — Prove the graph matters

Disable **Payments API → Redis**, then investigate Redis again.

> “We removed one dependency. The payment branch and its customers are no longer in this Redis blast radius; Analytics still is. If the graph were decoration, the answer wouldn't change.”

Re-enable the edge after showing the result.

### 2:10 — Safe action boundary

Approve a draft response task.

> “Approval is persisted, but deliberately simulated. We do not page real people or touch production. The default agent is a deterministic graph-tool workflow; an optional model synthesizes the narrative from the same evidence. FalkorDB remains the source of truth in both modes.”

### 2:30 — Close

> “Faultline connects the service graph, company knowledge, and durable incident memory. It doesn't just produce an answer—it gives an engineer the paths needed to check it.”

Show the repository URL and README setup commands.

## Important submission notes

- Record the real running UI. Do not present proposed integrations as implemented.
- Upload your recording to a publicly accessible video URL if the submission form requests one.
- The repository includes a blog **draft**, not a published article.
- Registration, entry-form submission, and eligibility checks must be completed by the participant.
