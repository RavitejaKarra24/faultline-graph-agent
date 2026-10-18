# Submission copy

Prepared for [Graph Hacks: Context for AI Agents](https://www.wemakedevs.org/hackathons/falkordb), using the [official rules](https://www.wemakedevs.org/hackathons/falkordb/rules) reviewed October 18, 2026.

## Team details

- Team name: **Faultline Labs**
- Participant: **Raviteja Karra** (solo)
- GitHub: https://github.com/RavitejaKarra24
- X / Twitter: https://x.com/RavitejaKarra24

Only the participant supplied for this entry is listed. Private registration fields, if requested, must be completed in the event panel.

## Project name
Faultline

## Tagline
A graph-grounded incident agent that knows what breaks, who owns it, and what worked last time.

## Primary track
**Track 01 — Agents That Act on Connected Data**

## Additional track fit
The rules allow multiple tracks. This entry selects **Track 01**. Persistent memory and connected company knowledge are supporting capabilities; Track 02 and Track 03 are not selected in this entry copy.

## Short description
Faultline turns a failing service into an evidence-backed incident response plan. FalkorDB stores service dependencies, customer relationships, ownership, runbooks, previous incidents, architectural decisions, and persistent operator lessons. A bounded workflow traverses the graph, resolves affected customers and responders, recalls earlier lessons, and drafts response tasks with source paths. Engineers can inspect every executed Cypher tool and approve simulated actions. Change a dependency and the blast radius changes; start a new session and the learned context remains.

## What makes it different
- A graph-mutation demo proves the graph determines the answer.
- Customer impact follows indirect dependency paths, not just adjacent nodes.
- Lessons tagged helpful or avoid become durable incident context.
- Exact query traces and evidence paths make recommendations auditable.
- Runs locally without an AI key; optional model synthesis doesn't control writes or actions.
- Human approval is a deliberate boundary; no unreviewed production remediation.

## How FalkorDB is used
FalkorDB is the primary database and the central context layer, not an optional visualization backend. Parameterized Cypher performs bounded multi-hop traversals and retrieves ownership, knowledge, and memory. Investigations, memories, and action approval records are persisted in the same workspace graph. Workspaces use separate graph names in one FalkorDB instance. The browser graph is read from those same facts.

## Stack
FalkorDB, Python, FastAPI, Pydantic, React, TypeScript, Vite, Docker Compose. Optional OpenAI-compatible narrative synthesis.

## Implementation transparency
The default agent is a deterministic, bounded multi-stage workflow using graph tools. The specialist stages run in a single process; they are not independent autonomous LLM agents. The optional model only synthesizes the graph-derived narrative. The seeded company and incidents are fictional. Approvals are simulated. No production integration or high-concurrency orchestration is claimed. Built with coding-assistant support.

## Links
- Repository: https://github.com/RavitejaKarra24/faultline-graph-agent
- Setup and graph model: https://github.com/RavitejaKarra24/faultline-graph-agent/blob/main/README.md
- Cypher reference: https://github.com/RavitejaKarra24/faultline-graph-agent/blob/main/docs/CYPHER.md
- Standalone queries: https://github.com/RavitejaKarra24/faultline-graph-agent/tree/main/queries
- Architecture: https://github.com/RavitejaKarra24/faultline-graph-agent/blob/main/docs/ARCHITECTURE.md
- Local demo: http://localhost:8080 (complete setup in README)
- Demo video: **the submitter will record/upload the final video and supply its public URL**.
- Hosted app: **not publicly deployed**. Use the complete local setup below.
- Blog: [repository draft](BLOG.md) — publish separately if entering the blog prize

## Local setup field

Faultline is a local incident-response prototype with a mutable graph and no user authentication. The submitted setup keeps the API and database on localhost. Judges can run the full application with Docker Compose; no AI key, paid account, or manual data import is required.

```bash
git clone https://github.com/RavitejaKarra24/faultline-graph-agent.git
cd faultline-graph-agent
docker compose up --build -d
docker compose ps
curl --fail http://localhost:8000/api/health
```

Open http://localhost:8080. FalkorDB and the API should report healthy; the web container should be running. The fictional company graph initializes on first use. The README covers required ports, troubleshooting, optional AI mode, local development, and persistent storage. `docker compose down` stops the app while retaining graph data.

## Requirement checklist

| Requirement | Deliverable / status |
| --- | --- |
| Public source-code repository | Existing GitHub repository verified `PUBLIC` through the GitHub API |
| README with setup and graph model | [README](../README.md): Docker quick start, health check, directed graph diagram, node properties and relationships |
| Cypher queries or graph algorithms | [Query reference](CYPHER.md), [seven standalone queries](../queries/), runtime [planner](../backend/src/faultline_backend/planner.py) and [storage](../backend/src/faultline_backend/storage.py) |
| Working-project demo video | Submitter-owned; final public video URL still required |
| Live deployment or complete local setup | Local Docker setup built and started successfully; no hosted URL claimed |
| Track entered | Track 01 — Agents That Act on Connected Data |
| Team information | Faultline Labs; Raviteja Karra; supplied GitHub and X links |
| Coding-assistant disclosure | Included in this entry and README |

## Before filing the entry

- [ ] Confirm registration and participant information in the WeMakeDevs panel.
- [ ] Confirm that the main coding/design work took place during the event and be ready to explain the graph model, queries, architecture, and decisions.
- [ ] Add the final public video URL and verify that it plays without signing in.
- [ ] Copy the entry fields into the event panel and submit before **October 18, 2026, 11:59 PM IST**; save the confirmation.

This file is prepared entry copy, **not confirmation that an entry has been submitted**.
