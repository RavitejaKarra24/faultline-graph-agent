# Faultline

A calm incident command desk for engineers under pressure. Functional product UI, not a marketing landing page.

## Visual language
- Light default: warm off-white canvas #f7f8fa, white panels, ink #18232f, secondary #586575, border #dfe5eb.
- Accent: deep teal #087f72; semantic critical red #be3d43 and amber #96600c. Use color for meaning, not decoration.
- Dark mode tokens should preserve contrast, with charcoal surfaces and light ink.
- Typography: system sans (SF Pro / Segoe UI) for fast offline rendering, system mono for IDs, queries, counts.
- Restrained 6–10px radii, 1px borders, minimal shadows. Dense enough to work; breathable enough to scan.
- Layout: slim dark navigation rail, workspace header, incident introduction, command input, large connected topology, right-hand evidence/agent activity, plan below. No hero gradient, no decorative metric grid.
- Graph is the hero: readable service nodes, directional connectors, semantics in an explicit legend, focus and selection details accessible via buttons.
- Tone: concise, operational, honest. Say simulated approval, never imply real paging or remediation.
- All sample infrastructure and incidents are fictional. No fake live status or invented metrics.
- Respect reduced motion and keyboard focus. Mobile stacks all panels; graph can scroll within its own region.
