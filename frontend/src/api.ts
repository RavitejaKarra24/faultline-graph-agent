import type {
  Action,
  Graph,
  GraphNode,
  Health,
  Investigation,
  Memory,
} from './types';

function errorMessage(body: unknown): string | undefined {
  if (typeof body !== 'object' || body === null) return undefined;
  if ('error' in body) {
    if (typeof body.error === 'string') return body.error;
    if (
      typeof body.error === 'object' &&
      body.error !== null &&
      'message' in body.error &&
      typeof body.error.message === 'string'
    )
      return body.error.message;
  }
  if ('detail' in body && typeof body.detail === 'string') return body.detail;
  return undefined;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 60_000);
  try {
    const response = await fetch(`/api${path}`, {
      ...options,
      signal: options.signal ?? controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'X-Workspace': 'demo',
        ...options.headers,
      },
    });
    const text = await response.text();
    let body: unknown;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      throw new Error(
        'The API returned an unreadable response. Check that the backend is running on port 8000.',
      );
    }
    if (!response.ok)
      throw new Error(
        errorMessage(body) ??
          `Request failed (${response.status}). Please retry.`,
      );
    return body as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError')
      throw new Error(
        'The request timed out. Check the backend and FalkorDB, then retry.',
      );
    if (error instanceof TypeError)
      throw new Error(
        'Cannot reach the API. Start the backend on 127.0.0.1:8000 and retry.',
      );
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export const api = {
  health: () => request<Health>('/health'),
  graph: () => request<Graph>('/graph'),
  services: () => request<{ services: GraphNode[] }>('/services'),
  memories: () => request<{ memories: Memory[] }>('/memories'),
  history: (sessionId: string) =>
    request<{ investigations: Investigation[] }>(
      `/investigations?sessionId=${encodeURIComponent(sessionId)}`,
    ),
  seed: () =>
    request<{ nodes: number; edges: number }>('/seed', { method: 'POST' }),
  investigate: (serviceId: string, question: string, sessionId: string) =>
    request<Investigation>('/investigations', {
      method: 'POST',
      body: JSON.stringify({ serviceId, question, sessionId }),
    }),
  saveMemory: (
    serviceId: string,
    content: string,
    outcome: Memory['outcome'],
    sessionId: string,
  ) =>
    request<Memory>('/memories', {
      method: 'POST',
      body: JSON.stringify({ serviceId, content, outcome, sessionId }),
    }),
  approve: (id: string) =>
    request<Action>(`/actions/${encodeURIComponent(id)}/approve`, {
      method: 'POST',
    }),
  dependency: (enabled: boolean) =>
    request<{ source: string; target: string; enabled: boolean }>(
      '/dependencies',
      {
        method: 'PATCH',
        body: JSON.stringify({
          source: 'svc-payments',
          target: 'svc-redis',
          enabled,
        }),
      },
    ),
};

export function message(error: unknown) {
  return error instanceof Error
    ? error.message
    : 'An unexpected error occurred. Please retry.';
}

export function newSession() {
  return `session-${crypto.randomUUID()}`;
}
export function readSession() {
  try {
    return sessionStorage.getItem('faultline.session.v1') || newSession();
  } catch {
    return newSession();
  }
}
export function persistSession(id: string) {
  try {
    sessionStorage.setItem('faultline.session.v1', id);
  } catch {
    /* Private browsing can disable storage. The in-memory session still works. */
  }
}

export function downloadInvestigation(
  investigation: Investigation,
  format: 'json' | 'md',
) {
  const content =
    format === 'json'
      ? JSON.stringify(investigation, null, 2)
      : [
          '# Faultline investigation',
          '\n> Fictional dataset. All approvals are simulated.\n',
          `**ID:** ${investigation.id}`,
          `**Service:** ${investigation.serviceId}`,
          `**Severity:** ${investigation.severity}`,
          `**Question:** ${investigation.question}`,
          '\n## Summary',
          investigation.summary,
          '\n## Impacted services',
          ...investigation.impactedServices.map((id) => `- ${id}`),
          '\n## Impacted customers',
          ...investigation.impactedCustomers.map((id) => `- ${id}`),
          '\n## Owners',
          ...investigation.owners.map(
            (owner) => `- ${owner.name} · ${owner.team} · ${owner.serviceId}`,
          ),
          '\n## Evidence',
          ...investigation.evidence.map(
            (e) =>
              `### ${e.title}\n${e.detail}\n\nSource: ${e.source}\n\nPath: ${e.path.join(' → ')}`,
          ),
          '\n## Response plan — simulated',
          ...investigation.actions.map(
            (a) =>
              `- [${a.status === 'approved' ? 'x' : ' '}] ${a.title}: ${a.description}`,
          ),
          '\n## Query trace',
          ...investigation.trace.map(
            (t) =>
              `### ${t.agent} · ${t.tool}\n${t.purpose}\n\n\`\`\`cypher\n${t.query}\n\`\`\`\n\n\`\`\`json\n${JSON.stringify(t.params, null, 2)}\n\`\`\`\n${t.resultCount} results · ${t.durationMs} ms`,
          ),
        ].join('\n');
  const url = URL.createObjectURL(
    new Blob([content], {
      type: format === 'json' ? 'application/json' : 'text/markdown',
    }),
  );
  const link = document.createElement('a');
  link.href = url;
  link.download = `faultline-${investigation.id}.${format}`;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
