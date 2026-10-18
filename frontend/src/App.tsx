import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  CircleHelp,
  Database,
  GitBranch,
  Layers,
  LoaderCircle,
  Moon,
  PanelLeft,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Sun,
  Terminal,
  TriangleAlert,
  Workflow,
  Zap,
} from 'lucide-react';
import {
  api,
  downloadInvestigation,
  message,
  newSession,
  persistSession,
  readSession,
} from './api';
import type {
  Evidence,
  Graph,
  GraphNode,
  Health,
  Investigation,
  Memory,
} from './types';
import Topology from './components/Topology';
import InvestigationPanel from './components/InvestigationPanel';
import MemoryPage from './components/MemoryPage';

const defaultQuestion =
  'Redis is timing out. What breaks, who should respond, and what worked last time?';
const emptyGraph: Graph = { nodes: [], edges: [] };

export default function App() {
  const [page, setPage] = useState<'desk' | 'memory'>('desk');
  const [sessionId, setSessionId] = useState(readSession);
  const [health, setHealth] = useState<Health | null>(null);
  const [graph, setGraph] = useState<Graph>(emptyGraph);
  const [services, setServices] = useState<GraphNode[]>([]);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [investigation, setInvestigation] = useState<Investigation | null>(
    null,
  );
  const [serviceId, setServiceId] = useState('svc-redis');
  const [question, setQuestion] = useState(defaultQuestion);
  const [loading, setLoading] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const [approving, setApproving] = useState<string | null>(null);
  const [patching, setPatching] = useState(false);
  const [stale, setStale] = useState(false);
  const [activeEvidence, setActiveEvidence] = useState<Evidence | null>(null);
  const [contextView, setContextView] = useState<'evidence' | 'trace'>(
    'evidence',
  );
  const [helpOpen, setHelpOpen] = useState(false);
  const [dark, setDark] = useState(() => {
    try {
      return localStorage.getItem('faultline.theme') === 'dark';
    } catch {
      return false;
    }
  });
  const connected = health?.status === 'ok' && !error;
  const paymentsDependency = graph.edges.find(
    (e) =>
      e.source === 'svc-payments' &&
      e.target === 'svc-redis' &&
      e.relation === 'DEPENDS_ON',
  );
  const dependencyEnabled = Boolean(
    paymentsDependency && paymentsDependency.enabled !== false,
  );
  const label = (id: string) =>
    graph.nodes.find((n) => n.id === id)?.label ?? id;

  const loadGeneration = useRef(0);
  const load = useCallback(async () => {
    const generation = ++loadGeneration.current;
    setLoading(true);
    setError('');
    try {
      const status = await api.health();
      if (generation !== loadGeneration.current) return;
      setHealth(status);
      if (status.status !== 'ok')
        throw new Error(
          'FalkorDB is unavailable. No graph data can be loaded.',
        );
      let [nextGraph, nextServices, nextMemories, history] = await Promise.all([
        api.graph(),
        api.services(),
        api.memories(),
        api.history(sessionId),
      ]);
      if (nextGraph.nodes.length === 0) {
        await api.seed();
        [nextGraph, nextServices, nextMemories, history] = await Promise.all([
          api.graph(),
          api.services(),
          api.memories(),
          api.history(sessionId),
        ]);
      }
      if (generation !== loadGeneration.current) return;
      setGraph(nextGraph);
      setActiveEvidence(null);
      setServices(nextServices.services);
      setMemories(nextMemories.memories);
      const previous = history.investigations[0] ?? null;
      setInvestigation(previous);
      // A saved result is historical; the API has no topology revision.
      // Require fresh context before approving actions against today's graph.
      setStale(Boolean(previous));
      if (previous) {
        setServiceId(previous.serviceId);
        setQuestion(previous.question);
      }
    } catch (err) {
      if (generation === loadGeneration.current) setError(message(err));
    } finally {
      if (generation === loadGeneration.current) setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    persistSession(sessionId);
    // Cleanup prevents duplicate StrictMode requests and stale session responses.
    const timer = window.setTimeout(() => void load(), 0);
    return () => {
      window.clearTimeout(timer);
      loadGeneration.current += 1;
    };
  }, [load, sessionId]);
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    try {
      localStorage.setItem('faultline.theme', dark ? 'dark' : 'light');
    } catch {
      /* Theme still applies when storage is unavailable. */
    }
  }, [dark]);
  useEffect(() => {
    const timer = window.setInterval(() => {
      void api
        .health()
        .then(setHealth)
        .catch(() => setHealth(null));
    }, 30_000);
    return () => window.clearInterval(timer);
  }, []);

  async function investigate(event?: React.FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (!question.trim() || investigating) return;
    setInvestigating(true);
    setActionError('');
    setNotice('');
    setActiveEvidence(null);
    try {
      const result = await api.investigate(
        serviceId,
        question.trim(),
        sessionId,
      );
      setInvestigation(result);
      setStale(false);
      setContextView('evidence');
      setNotice(
        'Investigation complete. Findings are grounded in the returned graph evidence.',
      );
      // Refresh the topology so newly persisted graph memories are available for inspection.
      void api
        .graph()
        .then(setGraph)
        .catch(() => {
          /* The investigation remains valid if the optional refresh fails. */
        });
    } catch (err) {
      setActionError(message(err));
    } finally {
      setInvestigating(false);
    }
  }
  function resetSession() {
    loadGeneration.current += 1;
    setLoading(true);
    setSessionId(newSession());
    setInvestigation(null);
    setActiveEvidence(null);
    setStale(false);
    setServiceId('svc-redis');
    setQuestion(defaultQuestion);
    setActionError('');
    setPage('desk');
    setNotice('New session started. Workspace memories are preserved.');
  }
  async function toggleDependency() {
    setPatching(true);
    setActionError('');
    try {
      await api.dependency(!dependencyEnabled);
      const updated = await api.graph();
      setGraph(updated);
      setStale(Boolean(investigation));
      setActiveEvidence(null);
      setNotice(
        'Demo dependency updated in the graph. Re-investigate to recompute impact.',
      );
    } catch (err) {
      setActionError(message(err));
    } finally {
      setPatching(false);
    }
  }
  async function approve(id: string) {
    setApproving(id);
    setActionError('');
    try {
      const action = await api.approve(id);
      setInvestigation((previous) =>
        previous
          ? {
              ...previous,
              actions: previous.actions.map((a) => (a.id === id ? action : a)),
            }
          : null,
      );
      setNotice(
        'Simulated approval recorded. No infrastructure was changed or notification sent.',
      );
    } catch (err) {
      setActionError(message(err));
    } finally {
      setApproving(null);
    }
  }
  async function refreshMemories() {
    setActionError('');
    try {
      const result = await api.memories();
      setMemories(result.memories);
    } catch (err) {
      setActionError(message(err));
    }
  }
  function savedMemory(memory: Memory) {
    setMemories((previous) => [
      memory,
      ...previous.filter((m) => m.id !== memory.id),
    ]);
    setNotice(
      'Learning persisted in the workspace graph. It will survive a new session.',
    );
    void api
      .graph()
      .then(setGraph)
      .catch(() => {
        /* Retry workspace refresh to inspect the new graph node. */
      });
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to workspace
      </a>
      <nav className="rail" aria-label="Main navigation">
        <a className="brand-mark" href="#main" aria-label="Faultline workspace">
          <Zap size={25} aria-hidden="true" />
        </a>
        <div className="rail-main">
          <button
            className={`rail-button ${page === 'desk' ? 'active' : ''}`}
            aria-label="Incident command desk"
            aria-current={page === 'desk' ? 'page' : undefined}
            onClick={() => setPage('desk')}
            title="Command desk"
          >
            <Workflow size={21} />
            <span>Desk</span>
          </button>
          <button
            className={`rail-button ${page === 'memory' ? 'active' : ''}`}
            aria-label="Workspace memory"
            aria-current={page === 'memory' ? 'page' : undefined}
            onClick={() => setPage('memory')}
            title="Memory"
          >
            <BookOpen size={20} />
            <span>Memory</span>
          </button>
          <button
            className="rail-button"
            aria-label="Show query trace"
            onClick={() => {
              setPage('desk');
              setContextView('trace');
              window.setTimeout(
                () =>
                  document
                    .getElementById('investigation-panel-title')
                    ?.scrollIntoView({ behavior: 'instant', block: 'nearest' }),
                0,
              );
            }}
            title="Query trace"
          >
            <Terminal size={20} />
            <span>Trace</span>
          </button>
        </div>
        <div className="rail-bottom">
          <button
            className="rail-button"
            aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
            onClick={() => setDark(!dark)}
            title="Change theme"
          >
            {dark ? <Sun size={20} /> : <Moon size={20} />}
            <span>Theme</span>
          </button>
          <button
            className={`rail-button ${helpOpen ? 'active' : ''}`}
            aria-label="About this demo"
            aria-expanded={helpOpen}
            onClick={() => setHelpOpen(!helpOpen)}
            title="About"
          >
            <CircleHelp size={20} />
            <span>About</span>
          </button>
          <div className="workspace-avatar" aria-label="Demo workspace">
            D
          </div>
        </div>
      </nav>
      <div className="workspace">
        <header className="workspace-header">
          <div className="breadcrumb">
            <strong>
              faultline<span className="brand-dot">.</span>
            </strong>
            <span className="header-divider" />
            <span>Demo workspace</span>
            <ChevronRight size={14} aria-hidden="true" />
            <span className="breadcrumb-current">
              {page === 'desk' ? 'Command desk' : 'Memory'}
            </span>
          </div>
          <div className="header-actions">
            <span
              className={`connection ${health?.status === 'ok' ? 'is-connected' : ''}`}
              role="status"
            >
              <span className="status-dot" />
              {health?.status === 'ok'
                ? 'FalkorDB connected'
                : loading
                  ? 'Connecting…'
                  : 'Database unavailable'}
            </span>
            <button
              className="icon-button"
              aria-label="Refresh workspace and connection"
              disabled={loading || investigating || patching}
              onClick={() => void load()}
            >
              <RefreshCw size={16} className={loading ? 'spin' : ''} />
            </button>
          </div>
        </header>
        <main id="main">
          <div className="page-intro">
            <div>
              <div className="eyebrow intro-eyebrow">
                <span className="teal-line" />{' '}
                {page === 'desk'
                  ? 'INCIDENT WORKSPACE'
                  : 'ORGANIZATIONAL MEMORY'}
              </div>
              <h1>
                {page === 'desk'
                  ? 'Clarity when it breaks.'
                  : 'Make the next response better.'}
              </h1>
              <p>
                {page === 'desk'
                  ? 'Trace the impact. Find the context. Coordinate the response.'
                  : 'Keep what worked. Remember what didn’t. Carry context across sessions.'}
              </p>
            </div>
            <div className="intro-actions">
              <span className="dataset-badge">
                <Layers size={13} aria-hidden="true" /> Synthetic dataset
              </span>
              <button
                className="button"
                onClick={resetSession}
                disabled={investigating || patching || Boolean(approving)}
              >
                <Plus size={15} aria-hidden="true" /> New session
              </button>
            </div>
          </div>
          {helpOpen ? (
            <section className="panel about-panel">
              <h2>A command desk, not an autopilot.</h2>
              <p>
                All services, customers, people, and incidents in this workspace
                are fictional. Faultline traverses the actual workspace graph to
                assemble evidence. Approvals only record simulated tasks: they
                never page people, run commands, or change infrastructure.
              </p>
              <p>
                Dependencies point from a service to what it depends on. Impact
                is traced in reverse. New sessions clear the investigation, not
                the graph or its memories.
              </p>
              <button
                className="text-button"
                onClick={() => setHelpOpen(false)}
              >
                Close explanation <Check size={15} aria-hidden="true" />
              </button>
            </section>
          ) : null}
          {error || (health && health.status !== 'ok') ? (
            <section className="error-banner" role="alert">
              <TriangleAlert size={22} aria-hidden="true" />
              <div>
                <h2>Graph connection needs attention</h2>
                <p>{error || 'FalkorDB is unavailable.'}</p>
                <p>
                  Start FalkorDB, verify the backend’s database connection
                  settings, then start the API on <code>127.0.0.1:8000</code>.
                  The Vite development server proxies <code>/api</code> to that
                  address. No offline graph is substituted.
                </p>
                <button
                  className="button"
                  disabled={loading}
                  onClick={() => void load()}
                >
                  <RefreshCw size={15} aria-hidden="true" />
                  {loading ? 'Reconnecting…' : 'Retry connection'}
                </button>
              </div>
            </section>
          ) : null}
          {!health && !loading && !error ? (
            <div className="error-banner" role="alert">
              <TriangleAlert size={18} aria-hidden="true" />
              <div>
                <strong>API connection lost</strong>
                <p>
                  Previously loaded data is retained, but actions are paused.
                  Check the backend and retry.
                </p>
                <button className="button" onClick={() => void load()}>
                  Reconnect
                </button>
              </div>
            </div>
          ) : null}
          {actionError ? (
            <div className="error-banner compact" role="alert">
              <TriangleAlert size={18} aria-hidden="true" />
              <p>
                {actionError} Your inputs are preserved; retry the action when
                ready.
              </p>
              <button
                className="icon-button"
                aria-label="Dismiss action error"
                onClick={() => setActionError('')}
              >
                <Plus size={17} className="close-icon" />
              </button>
            </div>
          ) : null}
          <div className="sr-only" role="status" aria-live="polite">
            {notice}
          </div>
          {page === 'memory' ? (
            <MemoryPage
              memories={memories}
              services={services}
              sessionId={sessionId}
              onSaved={savedMemory}
              onRefresh={() => void refreshMemories()}
              connected={connected && !loading}
            />
          ) : (
            <>
              <section
                className="panel command-panel"
                aria-labelledby="command-title"
              >
                <div className="command-caption">
                  <span className="command-icon">
                    <Sparkles size={17} aria-hidden="true" />
                  </span>
                  <h2 id="command-title">Start with the signal.</h2>
                  <span className="small muted">
                    A question in. An evidence-backed response out.
                  </span>
                </div>
                <form
                  onSubmit={(event) => void investigate(event)}
                  className="command-form"
                >
                  <div className="service-field">
                    <label htmlFor="service">Affected service</label>
                    <select
                      id="service"
                      value={serviceId}
                      disabled={investigating || loading}
                      onChange={(event) => {
                        const id = event.target.value;
                        setServiceId(id);
                        const selectedLabel =
                          services.find((s) => s.id === id)?.label ?? id;
                        setQuestion(
                          id === 'svc-redis'
                            ? defaultQuestion
                            : `${selectedLabel} is failing. What breaks, who should respond, and what worked last time?`,
                        );
                      }}
                      required
                    >
                      {services.length ? (
                        services.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.label}
                          </option>
                        ))
                      ) : (
                        <option value="svc-redis">Waiting for services…</option>
                      )}
                    </select>
                  </div>
                  <div className="question-field">
                    <label htmlFor="question">Investigation question</label>
                    <textarea
                      id="question"
                      rows={2}
                      value={question}
                      required
                      maxLength={2000}
                      disabled={investigating}
                      onChange={(event) => setQuestion(event.target.value)}
                    />
                  </div>
                  <button
                    className="button primary investigate-button"
                    disabled={
                      !connected ||
                      loading ||
                      investigating ||
                      patching ||
                      !services.length ||
                      !question.trim()
                    }
                    aria-busy={investigating}
                  >
                    {investigating ? (
                      <LoaderCircle
                        size={17}
                        className="spin"
                        aria-hidden="true"
                      />
                    ) : (
                      <ArrowRight size={17} aria-hidden="true" />
                    )}
                    {investigating
                      ? 'Investigating…'
                      : investigation
                        ? 'Re-investigate'
                        : 'Investigate'}
                  </button>
                </form>
                <div className="command-footnote">
                  <span>
                    <Database size={13} aria-hidden="true" />{' '}
                    {health?.mode === 'llm'
                      ? 'LLM + graph tools'
                      : 'Graph-grounded reasoning'}
                  </span>
                  <span>
                    <ShieldCheck size={13} aria-hidden="true" /> Read-only
                    investigation · simulated response
                  </span>
                </div>
              </section>
              {investigation && !investigating ? (
                <section
                  className={`result-summary ${stale ? 'stale' : ''}`}
                  aria-labelledby="summary-title"
                >
                  <div className="summary-top">
                    <div className="row">
                      <span className={`severity ${investigation.severity}`}>
                        {investigation.severity}
                      </span>
                      <h2 id="summary-title">
                        {stale
                          ? 'Saved investigation · revalidate context'
                          : 'The fault, in context.'}
                      </h2>
                    </div>
                    <div className="export-actions">
                      <button
                        className="text-button"
                        onClick={() =>
                          downloadInvestigation(investigation, 'md')
                        }
                      >
                        <ArrowDownToLine size={14} aria-hidden="true" />{' '}
                        Markdown
                      </button>
                      <button
                        className="text-button mono"
                        onClick={() =>
                          downloadInvestigation(investigation, 'json')
                        }
                      >
                        JSON
                      </button>
                    </div>
                  </div>
                  <p>{investigation.summary}</p>
                  <div className="impact-summary">
                    <span>
                      <strong className="mono">
                        {investigation.impactedServices.length}
                      </strong>{' '}
                      impacted services
                    </span>
                    <span>
                      <strong className="mono">
                        {investigation.impactedCustomers.length}
                      </strong>{' '}
                      impacted customers
                    </span>
                    <span>
                      <strong className="mono">
                        {investigation.evidence.length}
                      </strong>{' '}
                      evidence sources
                    </span>
                  </div>
                  {stale ? (
                    <p className="stale-message">
                      <TriangleAlert size={15} aria-hidden="true" /> This result
                      is a historical snapshot. Re-investigate to see the new
                      blast radius; highlighting is paused.
                    </p>
                  ) : null}
                  {investigation.warnings.map((warning, i) => (
                    <p className="warning-note" key={i}>
                      <TriangleAlert size={15} aria-hidden="true" />
                      {warning}
                    </p>
                  ))}
                </section>
              ) : null}
              <div className="desk-grid">
                <div className="graph-column">
                  {loading && !graph.nodes.length ? (
                    <section className="panel graph-loading" aria-busy="true">
                      <div className="panel-heading">
                        <h2>Loading dependency topology</h2>
                        <span className="spinner" />
                      </div>
                      <div className="graph-skeleton">
                        <div className="skeleton" />
                        <div className="skeleton" />
                        <div className="skeleton" />
                        <div className="skeleton" />
                      </div>
                      <p>Reading the actual workspace graph…</p>
                    </section>
                  ) : graph.nodes.length ? (
                    <Topology
                      graph={graph}
                      investigation={investigation}
                      highlightedEvidence={activeEvidence}
                      stale={stale}
                    />
                  ) : (
                    <section className="panel graph-unavailable">
                      <GitBranch size={38} aria-hidden="true" />
                      <h2>
                        {error
                          ? 'The graph is unavailable.'
                          : 'No topology loaded yet.'}
                      </h2>
                      <p>
                        Connect to FalkorDB to load the fictional workspace.
                        This view never uses an offline substitute.
                      </p>
                      <button
                        className="button"
                        onClick={() => void load()}
                        disabled={loading}
                      >
                        <RefreshCw size={15} aria-hidden="true" /> Retry loading
                        graph
                      </button>
                    </section>
                  )}
                  <section className="panel demo-control">
                    <div className="demo-control-copy">
                      <span className="small eyebrow">
                        <GitBranch size={14} aria-hidden="true" /> TOPOLOGY LAB
                      </span>
                      <h3>A small change. A different blast radius.</h3>
                      <p>
                        Toggle a real demo dependency, then re-investigate to
                        compare the evidence.
                      </p>
                      <code>
                        payments <ArrowRight size={13} aria-hidden="true" />{' '}
                        redis
                      </code>
                    </div>
                    <div className="dependency-control">
                      <button
                        className="switch"
                        role="switch"
                        aria-checked={dependencyEnabled}
                        aria-label="Payments depends on Redis"
                        disabled={
                          !connected || loading || patching || investigating
                        }
                        onClick={() => void toggleDependency()}
                      >
                        <span />
                      </button>
                      <strong>
                        {patching
                          ? 'Updating…'
                          : !graph.nodes.length
                            ? 'Unknown'
                            : dependencyEnabled
                              ? 'Enabled'
                              : 'Disabled'}
                      </strong>
                      <span className="small muted">Demo graph only</span>
                    </div>
                  </section>
                  {investigation && !investigating ? (
                    <section className="panel owners-panel">
                      <div className="panel-heading">
                        <div>
                          <h2>Who should respond</h2>
                          <p>Ownership returned by the graph.</p>
                        </div>
                        <span className="count-tag mono">
                          {investigation.owners.length}
                        </span>
                      </div>
                      <div className="owner-list">
                        {investigation.owners.length ? (
                          investigation.owners.map((owner, i) => (
                            <div
                              className="owner"
                              key={`${owner.serviceId}-${i}`}
                            >
                              <span className="owner-avatar">
                                {owner.name
                                  .split(' ')
                                  .map((part) => part[0])
                                  .slice(0, 2)
                                  .join('')}
                              </span>
                              <div>
                                <strong>{owner.name}</strong>
                                <span>{owner.team}</span>
                              </div>
                              <span className="chip">
                                {label(owner.serviceId)}
                              </span>
                            </div>
                          ))
                        ) : (
                          <p className="empty-inline">
                            No owner was returned for this investigation.
                          </p>
                        )}
                      </div>
                      {investigation.impactedCustomers.length ? (
                        <div className="customer-impact">
                          <span className="eyebrow">CUSTOMERS IN THE PATH</span>
                          <div className="chip-row">
                            {investigation.impactedCustomers.map((id) => (
                              <span className="chip" key={id}>
                                {label(id)}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </section>
                  ) : null}
                </div>
                <InvestigationPanel
                  investigation={investigation}
                  busy={investigating}
                  activeEvidence={activeEvidence}
                  onEvidence={setActiveEvidence}
                  view={contextView}
                  onView={setContextView}
                />
              </div>
              <section
                className="panel response-plan"
                aria-labelledby="plan-title"
              >
                <div className="panel-heading">
                  <div>
                    <h2 id="plan-title">
                      {investigation
                        ? 'A considered next move.'
                        : 'From understanding to response.'}
                    </h2>
                    <p>
                      {investigation
                        ? 'Suggested actions, linked to evidence. Nothing runs automatically.'
                        : 'Your response plan will appear after an investigation.'}
                    </p>
                  </div>
                  <span className="simulation-badge">
                    <ShieldCheck size={14} aria-hidden="true" /> Simulated
                    approvals only
                  </span>
                </div>
                {investigation && !investigating ? (
                  <>
                    <ol className="action-list">
                      {investigation.actions.map((action, index) => (
                        <li key={action.id}>
                          <span className="action-index mono">
                            {String(index + 1).padStart(2, '0')}
                          </span>
                          <div className="action-copy">
                            <div className="row">
                              <h3>{action.title}</h3>
                              <span className="action-kind">{action.kind}</span>
                            </div>
                            <p>{action.description}</p>
                            <div className="action-evidence">
                              <code>{action.target}</code>
                              {action.evidenceIds.map((id) => (
                                <button
                                  key={id}
                                  className="citation-button"
                                  onClick={() => {
                                    const evidence =
                                      investigation.evidence.find(
                                        (e) => e.id === id,
                                      );
                                    if (evidence) {
                                      setActiveEvidence(evidence);
                                      setContextView('evidence');
                                      document
                                        .getElementById(
                                          'investigation-panel-title',
                                        )
                                        ?.scrollIntoView({
                                          behavior: 'instant',
                                          block: 'nearest',
                                        });
                                    }
                                  }}
                                  disabled={
                                    !investigation.evidence.some(
                                      (e) => e.id === id,
                                    )
                                  }
                                >
                                  {id}
                                </button>
                              ))}
                            </div>
                          </div>
                          <button
                            className={`button approve-button ${action.status === 'approved' ? 'approved' : ''}`}
                            disabled={
                              action.status === 'approved' ||
                              Boolean(approving) ||
                              stale ||
                              !connected
                            }
                            onClick={() => void approve(action.id)}
                            aria-busy={approving === action.id}
                          >
                            {approving === action.id ? (
                              <span className="spinner" />
                            ) : action.status === 'approved' ? (
                              <Check size={15} aria-hidden="true" />
                            ) : (
                              <ShieldCheck size={15} aria-hidden="true" />
                            )}
                            {action.status === 'approved'
                              ? 'Simulated · approved'
                              : approving === action.id
                                ? 'Recording…'
                                : 'Approve simulation'}
                          </button>
                        </li>
                      ))}
                    </ol>
                    {!investigation.actions.length ? (
                      <p className="empty-inline">
                        No response actions were returned. Review the evidence
                        before deciding what to do.
                      </p>
                    ) : null}
                    <div className="plan-footer">
                      <ShieldCheck size={14} aria-hidden="true" /> Approval
                      records intent only. No paging, runbook execution, or
                      infrastructure changes.
                    </div>
                  </>
                ) : (
                  <div className="plan-empty">
                    <span className="plan-empty-icon">
                      <PanelLeft size={23} aria-hidden="true" />
                    </span>
                    <div>
                      <h3>Evidence first. Action second.</h3>
                      <p>
                        Investigate a signal above to assemble a grounded
                        response plan.
                      </p>
                    </div>
                  </div>
                )}
              </section>
            </>
          )}
          <footer className="page-footer">
            <span>
              <Zap size={13} aria-hidden="true" /> Faultline{' '}
              <span className="mono">/</span> Context is your first responder.
            </span>
            <span>Fictional infrastructure. Real graph reasoning.</span>
          </footer>
        </main>
        <div className="workspace-status">
          <span>
            <Activity size={12} aria-hidden="true" />{' '}
            {health?.mode ?? 'graph-tools'}{' '}
            <span className="status-separator">/</span> {graph.nodes.length}{' '}
            graph nodes <span className="status-separator">/</span>{' '}
            {graph.edges.length} relationships
          </span>
          <span className="mono">
            {sessionId.slice(0, 16)} <span className="status-separator">·</span>{' '}
            v{health?.version ?? '0.1.0'}
          </span>
        </div>
      </div>
    </div>
  );
}
