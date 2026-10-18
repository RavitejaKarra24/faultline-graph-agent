# Faultline API contract

All endpoints under `/api`. JSON uses camelCase. Errors `{ "error": { "code": "...", "message": "..." } }`.
No authentication in local demo; bind to localhost. `X-Workspace` header validated slug (default `demo`), graph per workspace.

- `GET /health` -> `{status:"ok"|"unavailable", database:"FalkorDB", mode:"graph-tools"|"llm", version:"0.1.0"}`
- `POST /seed` -> `{nodes:number, edges:number}`. Idempotent synthetic fixture, preserves memory.
- `GET /graph` -> `{nodes: GraphNode[], edges: GraphEdge[]}`
- `GET /services` -> `{services: GraphNode[]}`
- `POST /investigations` body `{serviceId:string, question:string, sessionId:string}` -> Investigation
- `GET /investigations?sessionId=optional` -> `{investigations:Investigation[]}` newest first, limit 50
- `POST /memories` body `{serviceId:string, content:string, outcome:"helpful"|"avoid", sessionId:string}` -> Memory
- `GET /memories` -> `{memories:Memory[]}` newest first, limit 100
- `POST /actions/{id}/approve` -> Action (only records approval of a simulated task; NEVER changes infrastructure). Idempotent.
- `PATCH /dependencies` body `{source:string,target:string,enabled:boolean}` -> `{source,target,enabled}`. Toggles a DEPENDS_ON edge; source depends on target. Investigation MUST change when toggled. Demo only.

GraphNode: `{id:string,label:string,kind:"Service"|"Team"|"Person"|"Customer"|"Runbook"|"Incident"|"Decision",status?:string,tier?:number,description?:string, [other props allowed]}`
GraphEdge: `{source:string,target:string,relation:string,enabled?:boolean}`
Memory: `{id:string,serviceId:string,content:string,outcome:"helpful"|"avoid",sessionId:string,createdAt:string}`
Action: `{id:string,title:string,description:string,kind:"notify"|"runbook"|"review",status:"pending"|"approved",target:string,evidenceIds:string[]}`
Evidence: `{id:string,title:string,detail:string,path:string[],source:string}` (path node IDs, source internal citation e.g. RUN-001)
TraceStep: `{agent:string,tool:string,purpose:string,query:string,params:object,resultCount:number,durationMs:number}`
Investigation: `{id:string,serviceId:string,question:string,sessionId:string,createdAt:string,summary:string,severity:"critical"|"high"|"moderate"|"low",impactedServices:string[],impactedCustomers:string[],owners:{name:string,team:string,serviceId:string}[],evidence:Evidence[],actions:Action[],trace:TraceStep[],memories:Memory[],mode:"graph-tools"|"llm",warnings:string[]}`

## Fixture IDs and narrative (must use)
Services: `svc-redis` (Redis / degraded), `svc-payments` (Payments API), `svc-checkout` (Checkout), `svc-orders` (Order service), `svc-storefront` (Storefront), `svc-notifications` (Notifications), `svc-analytics` (Analytics), `svc-auth` (Identity).
Dependencies: payments -> redis; checkout -> payments; orders -> payments; storefront -> checkout; notifications -> orders; analytics -> redis; checkout -> auth.
Customers depend on services: `customer-northstar` / Northstar Commerce -> storefront; `customer-acme` / Acme Retail -> orders; `customer-orbit` / Orbit Labs -> analytics. Customer impact follows arbitrary-length enabled dependency paths (bounded 6).
Include team/person ownership, a Redis connection exhaustion prior incident, a runbook advising pool cap/drain before restarts, and decision explaining why indiscriminate Redis restart is unsafe.
Graph displays edges direction as source DEPENDS_ON target (blast radius traversal goes reverse).

Default question: "Redis is timing out. What breaks, who should respond, and what worked last time?"
All fixture data explicitly fictional. No fake fallback graph: fail clearly if FalkorDB unavailable.
