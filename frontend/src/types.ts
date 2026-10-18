export interface GraphNode {
  id: string;
  label: string;
  kind:
    | 'Service'
    | 'Team'
    | 'Person'
    | 'Customer'
    | 'Runbook'
    | 'Incident'
    | 'Decision';
  status?: string;
  tier?: number;
  description?: string;
  [key: string]: unknown;
}
export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  enabled?: boolean;
}
export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
export interface Health {
  status: 'ok' | 'unavailable';
  database: 'FalkorDB';
  mode: 'graph-tools' | 'llm';
  version: string;
}
export interface Memory {
  id: string;
  serviceId: string;
  content: string;
  outcome: 'helpful' | 'avoid';
  sessionId: string;
  createdAt: string;
}
export interface Action {
  id: string;
  title: string;
  description: string;
  kind: 'notify' | 'runbook' | 'review';
  status: 'pending' | 'approved';
  target: string;
  evidenceIds: string[];
}
export interface Evidence {
  id: string;
  title: string;
  detail: string;
  path: string[];
  source: string;
}
export interface TraceStep {
  agent: string;
  tool: string;
  purpose: string;
  query: string;
  params: Record<string, unknown>;
  resultCount: number;
  durationMs: number;
}
export interface Investigation {
  id: string;
  serviceId: string;
  question: string;
  sessionId: string;
  createdAt: string;
  summary: string;
  severity: 'critical' | 'high' | 'moderate' | 'low';
  impactedServices: string[];
  impactedCustomers: string[];
  owners: { name: string; team: string; serviceId: string }[];
  evidence: Evidence[];
  actions: Action[];
  trace: TraceStep[];
  memories: Memory[];
  mode: 'graph-tools' | 'llm';
  warnings: string[];
}
