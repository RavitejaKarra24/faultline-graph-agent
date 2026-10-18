# Submission copy

## Project name
Faultline

## Tagline
A graph-grounded incident agent that knows what breaks, who owns it, and what worked last time.

## Primary track
Agents That Act on Connected Data

## Additional track fit
Agent Memory and Coordination; Company Brain. Check the entry form for whether multiple tracks can be selected.

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
- Local demo: http://localhost:8080 (complete setup in README)
- Public demo video: **ADD YOUR UPLOADED VIDEO URL**
- Optional hosted app: **ADD ONLY IF ACTUALLY DEPLOYED**
- Blog: [repository draft](BLOG.md) — publish separately if entering the blog prize

## Participant checklist
- [ ] Confirm registration and team details on WeMakeDevs.
- [ ] Confirm the main implementation was completed within the event window.
- [ ] Run the project from the README and understand the core queries.
- [ ] Record and upload the demo; verify the video is viewable without requesting access.
- [ ] Verify the repository is public and contains no secrets.
- [ ] Replace every placeholder in the actual submission form.
- [ ] Submit through the event panel before the announced deadline and save confirmation.

This file is prepared entry copy, **not confirmation that an entry has been submitted**.
