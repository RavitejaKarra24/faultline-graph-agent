# Verification

## Verified build — October 18, 2026

- **43 backend unit tests passed.**
- **10 integration tests passed against FalkorDB v4.22.1.**
- **4 Playwright UI tests passed**, including real topology at three viewport widths and unavailable-API recovery.
- The separate **real-API browser smoke passed against the production Docker stack**: investigation, approval reload, cross-session memory, changed tasks, changed topology, responsive layout, theme, and no uncaught JS errors.
- Ruff, TypeScript, ESLint, Prettier, production build, and Gitleaks secret scan passed.
- [GitHub Actions code checks and real-database tests passed](https://github.com/RavitejaKarra24/faultline-graph-agent/actions/runs/39100998709) on the initial published implementation.
- A memory written through the API survived **database container recreation**, not just a new application instance. The Redis data directory was confirmed as `/data`, matching the mounted volume.

These results describe the tested prototype, not a production-readiness certification.

## Automated code checks

```bash
make check
```

Runs backend unit tests (no database required), Ruff lint/format checks, TypeScript, ESLint, Prettier checks, and a production frontend build. Dependencies are lockfile-backed.

## Real FalkorDB integration tests

```bash
docker compose up -d falkordb
make integration
```

The suite creates isolated, random `it-*` workspace graphs and cleans them up. It does not run `FLUSHDB` or overwrite the default demo workspace.

Coverage includes:

- Idempotent seeding and graph/services API contract.
- Real six-hop-bounded Cypher service and customer traversals.
- Exact trace replay against FalkorDB and source-path checks.
- Dependency toggle changes impacted services/customers and severity.
- Helpful and avoid lessons are recalled across sessions and alter tasks.
- Memory and topology survive a new app/driver instance and reseeding.
- Simulated action approval is idempotent, durable, and does not change topology.
- Workspace isolation and unknown-resource behavior.

Unit tests separately cover malformed input, bounded bodies, unavailable-database behavior, and optional model-output handling. A passing unit suite is not a substitute for the real-database suite.

## Frontend browser checks

With the API and FalkorDB running:

```bash
cd frontend
bunx playwright install chromium
bun run test:ui
```

These checks cover live topology, node details, memory navigation, themes, responsive layout, and explicit connection-failure recovery. The separate script below tests the complete investigation and mutation flow.

## Browser smoke test

Start the full app:

```bash
docker compose up --build -d
uv run --python 3.12 --with playwright playwright install chromium
make smoke
```

To test the Vite development server instead:

```bash
FAULTLINE_URL=http://127.0.0.1:5173 make smoke
```

The script intercepts requests only to assign a fresh `smoke-*` workspace header; **API responses are not mocked**. It checks the actual running application:

1. FalkorDB connection and successful Redis investigation.
2. Six downstream services, three customers, and actual query traces.
3. Simulated approval survives a page reload.
4. An avoid lesson survives a new session and changes a response task.
5. Disabling Payments API → Redis leaves only Analytics and Orbit Labs in the blast radius.
6. Re-enabling the edge restores the fixture topology.
7. No page-level horizontal overflow at 375, 768, and 1440px.
8. Theme switching and no uncaught browser JavaScript errors.

Screenshots are written to `docs/screenshot.png` and `docs/screenshot-dark.png`. The isolated smoke graph is intentionally retained for inspection; it contains synthetic data only. These are smoke checks, not a complete accessibility, security, concurrency, or performance certification.

## Manual checks before submitting

- Tab through navigation, form fields, graph node controls, evidence, and action buttons; verify visible focus.
- Use the Memory page with both helpful and avoid outcomes.
- Open the exact Cypher trace and follow a customer-to-Redis evidence path.
- Stop FalkorDB, refresh, and verify an honest connection error with no fabricated data.
- Restart FalkorDB without deleting volumes and verify memories remain.
- Download JSON/Markdown and inspect the exported evidence and action statuses.
- Record the real UI using [DEMO.md](DEMO.md), upload the recording, and test the public video link.

## Continuous integration

`.github/workflows/ci.yml` runs code checks and real integration tests against a FalkorDB service on pushes and pull requests. Browser smoke testing is a separate local step and is not silently claimed as CI coverage.
