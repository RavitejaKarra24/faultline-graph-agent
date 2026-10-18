import { useMemo, useState } from 'react';
import {
  Building2,
  Database,
  Focus,
  Minus,
  Plus,
  Server,
  X,
  ArrowUpRight,
} from 'lucide-react';
import type { Evidence, Graph, Investigation } from '../types';

const positions: Record<string, { x: number; y: number }> = {
  'customer-northstar': { x: 12, y: 60 },
  'svc-storefront': { x: 212, y: 60 },
  'svc-checkout': { x: 412, y: 60 },
  'svc-auth': { x: 632, y: 12 },
  'svc-payments': { x: 632, y: 180 },
  'svc-redis': { x: 852, y: 240 },
  'customer-acme': { x: 212, y: 240 },
  'svc-orders': { x: 412, y: 240 },
  'svc-notifications': { x: 212, y: 390 },
  'customer-orbit': { x: 412, y: 440 },
  'svc-analytics': { x: 632, y: 390 },
};
const width = 164;
const height = 76;

interface Props {
  graph: Graph;
  investigation: Investigation | null;
  highlightedEvidence: Evidence | null;
  stale: boolean;
}

export default function Topology({
  graph,
  investigation,
  highlightedEvidence,
  stale,
}: Props) {
  const [zoom, setZoom] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const nodes = useMemo(
    () =>
      graph.nodes.filter((n) => n.kind === 'Service' || n.kind === 'Customer'),
    [graph.nodes],
  );
  const layout = useMemo(() => {
    let extra = 0;
    return new Map(
      nodes.map((node) => [
        node.id,
        positions[node.id] ?? {
          x: 12 + (extra++ % 5) * 200,
          y: 570 + Math.floor((extra - 1) / 5) * 120,
        },
      ]),
    );
  }, [nodes]);
  const canvasHeight = Math.max(
    550,
    ...Array.from(layout.values()).map((p) => p.y + 100),
  );
  const impacted = new Set(
    stale
      ? []
      : [
          ...(investigation?.impactedServices ?? []),
          ...(investigation?.impactedCustomers ?? []),
          ...(investigation ? [investigation.serviceId] : []),
        ],
  );
  const evidencePath = stale ? [] : (highlightedEvidence?.path ?? []);
  const selected = graph.nodes.find((n) => n.id === selectedId);
  const label = (id: string) =>
    graph.nodes.find((n) => n.id === id)?.label ?? id;
  const dependencies = graph.edges.filter(
    (e) => layout.has(e.source) && layout.has(e.target),
  );

  return (
    <section className="panel topology-panel" aria-labelledby="topology-title">
      <div className="panel-heading">
        <div>
          <h2 id="topology-title">Dependency topology</h2>
          <p>Follow the connections. Find the consequences.</p>
        </div>
        <span className="mono count-tag">{nodes.length} nodes</span>
      </div>
      <div className="graph-meta">
        <span className="eyebrow">
          {investigation && !stale ? 'BLAST RADIUS' : 'WORKSPACE / DEMO'}
        </span>
        <span>
          Arrows point to dependencies{' '}
          <ArrowUpRight size={13} aria-hidden="true" />
        </span>
      </div>
      <div
        className="graph-scroll"
        role="region"
        aria-label="Interactive dependency topology. Scroll to explore; use node buttons for details."
        tabIndex={0}
      >
        <svg
          className="topology"
          viewBox={`0 0 1040 ${canvasHeight}`}
          style={{ width: `${zoom * 100}%`, minWidth: `${zoom * 760}px` }}
          aria-label="Service and customer dependency graph"
        >
          <defs>
            <pattern
              id="dots"
              width="20"
              height="20"
              patternUnits="userSpaceOnUse"
            >
              <circle cx="1" cy="1" r="0.8" fill="currentColor" />
            </pattern>
            <marker
              id="arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--edge)" />
            </marker>
            <marker
              id="arrow-impact"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--teal)" />
            </marker>
          </defs>
          <rect
            width="1040"
            height={canvasHeight}
            fill="url(#dots)"
            className="graph-dots"
          />
          {dependencies.map((edge) => {
            const from = layout.get(edge.source)!;
            const to = layout.get(edge.target)!;
            const backwards = to.x < from.x;
            const x1 = from.x + (backwards ? 0 : width);
            const x2 = to.x + (backwards ? width : 0);
            const y1 = from.y + height / 2;
            const y2 = to.y + height / 2;
            const bend = Math.max(45, Math.abs(x2 - x1) / 2);
            const active =
              edge.enabled !== false &&
              impacted.has(edge.source) &&
              impacted.has(edge.target);
            const cited = evidencePath.some(
              (id, i) =>
                (id === edge.source && evidencePath[i + 1] === edge.target) ||
                (id === edge.target && evidencePath[i + 1] === edge.source),
            );
            return (
              <path
                key={`${edge.source}-${edge.target}-${edge.relation}`}
                d={`M ${x1} ${y1} C ${x1 + (backwards ? -bend : bend)} ${y1}, ${x2 + (backwards ? bend : -bend)} ${y2}, ${x2} ${y2}`}
                className={`graph-edge ${active || cited ? 'active' : ''} ${edge.enabled === false ? 'disabled' : ''} ${cited ? 'cited' : ''}`}
                markerEnd={`url(#${active || cited ? 'arrow-impact' : 'arrow'})`}
              >
                <title>
                  {label(edge.source)} → {label(edge.target)} · {edge.relation}
                  {edge.enabled === false ? ' · disabled' : ''}
                </title>
              </path>
            );
          })}
          {nodes.map((node) => {
            const point = layout.get(node.id)!;
            const isSource = investigation?.serviceId === node.id && !stale;
            const affected = impacted.has(node.id);
            const isDegraded = node.status === 'degraded';
            const Icon =
              node.kind === 'Customer'
                ? Building2
                : node.id === 'svc-redis'
                  ? Database
                  : Server;
            return (
              <foreignObject
                key={node.id}
                x={point.x}
                y={point.y}
                width={width}
                height={height}
                overflow="visible"
              >
                <button
                  className={`graph-node ${affected ? 'impacted' : ''} ${isSource || isDegraded ? 'degraded' : ''} ${selectedId === node.id || evidencePath.includes(node.id) ? 'selected' : ''}`}
                  onClick={() => setSelectedId(node.id)}
                  aria-pressed={selectedId === node.id}
                  aria-label={`${node.label}, ${node.status ?? node.kind}${affected ? ', impacted' : ''}. Show details`}
                >
                  <span className="node-top">
                    <Icon size={16} aria-hidden="true" />
                    <span>{node.label}</span>
                    {isDegraded ? <span className="status-dot danger" /> : null}
                  </span>
                  <span className="node-bottom">
                    <span className="mono">
                      {node.id.replace('svc-', '').replace('customer-', '')}
                    </span>
                    <span>
                      {isSource
                        ? 'origin'
                        : affected
                          ? 'impacted'
                          : node.kind === 'Customer'
                            ? 'customer'
                            : (node.status ?? 'service')}
                    </span>
                  </span>
                </button>
              </foreignObject>
            );
          })}
        </svg>
      </div>
      <div className="graph-footer">
        <div className="legend">
          <span>
            <i className="legend-origin" /> Degraded
          </span>
          <span>
            <i className="legend-impact" /> Impacted
          </span>
          <span>
            <i /> Dependency
          </span>
        </div>
        <div className="zoom-controls">
          <button
            className="icon-button"
            aria-label="Zoom out"
            disabled={zoom <= 0.8}
            onClick={() => setZoom((z) => Math.max(0.8, z - 0.2))}
          >
            <Minus size={15} />
          </button>
          <button
            className="icon-button"
            aria-label="Reset graph zoom"
            onClick={() => setZoom(1)}
          >
            <Focus size={16} />
          </button>
          <button
            className="icon-button"
            aria-label="Zoom in"
            disabled={zoom >= 1.8}
            onClick={() => setZoom((z) => Math.min(1.8, z + 0.2))}
          >
            <Plus size={15} />
          </button>
        </div>
      </div>
      {selected ? (
        <div className="node-inspector">
          <div className="row between">
            <h3>{selected.label}</h3>
            <button
              className="icon-button"
              aria-label="Close node details"
              onClick={() => setSelectedId(null)}
            >
              <X size={16} />
            </button>
          </div>
          <code>{selected.id}</code>
          <p>
            {selected.description ??
              `${selected.kind} in the fictional demo workspace.`}
          </p>
          <div className="chip-row">
            <span className="chip">{selected.kind}</span>
            {selected.status ? (
              <span className="chip">{selected.status}</span>
            ) : null}
            {selected.tier !== undefined ? (
              <span className="chip">Tier {selected.tier}</span>
            ) : null}
          </div>
          <ul className="relation-list">
            {graph.edges
              .filter(
                (e) => e.source === selected.id || e.target === selected.id,
              )
              .map((e, i) => (
                <li key={i}>
                  <span>{label(e.source)}</span>
                  <code>{e.relation}</code>
                  <span>
                    {label(e.target)}
                    {e.enabled === false ? ' (disabled)' : ''}
                  </span>
                </li>
              ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
