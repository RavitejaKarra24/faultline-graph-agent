import {
  ArrowRight,
  Check,
  ChevronRight,
  FileSearch,
  Fingerprint,
  GitBranch,
  Route,
  Terminal,
} from 'lucide-react';
import { useState } from 'react';
import type { Evidence, Investigation } from '../types';

interface Props {
  investigation: Investigation | null;
  busy: boolean;
  activeEvidence: Evidence | null;
  onEvidence: (evidence: Evidence | null) => void;
  view: 'evidence' | 'trace';
  onView: (view: 'evidence' | 'trace') => void;
}

export default function InvestigationPanel({
  investigation,
  busy,
  activeEvidence,
  onEvidence,
  view,
  onView,
}: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);
  return (
    <aside
      className="panel investigation-panel"
      aria-labelledby="investigation-panel-title"
    >
      <div className="panel-heading">
        <div>
          <h2 id="investigation-panel-title">Investigation context</h2>
          <p>Every conclusion has a source.</p>
        </div>
        <Fingerprint size={20} className="muted" aria-hidden="true" />
      </div>
      <div className="segmented" aria-label="Investigation context view">
        <button
          aria-pressed={view === 'evidence'}
          onClick={() => onView('evidence')}
        >
          <FileSearch size={15} aria-hidden="true" /> Evidence{' '}
          {investigation ? <span>{investigation.evidence.length}</span> : null}
        </button>
        <button aria-pressed={view === 'trace'} onClick={() => onView('trace')}>
          <Terminal size={15} aria-hidden="true" /> Query trace{' '}
          {investigation ? <span>{investigation.trace.length}</span> : null}
        </button>
      </div>
      {busy ? (
        <div className="context-body" role="status" aria-live="polite">
          <div className="row teal">
            <span className="spinner" /> Investigating graph context…
          </div>
          <p>
            Tracing dependencies, ownership, prior incidents, and saved
            learnings. Only returned evidence will appear here.
          </p>
          <div className="skeleton" />
          <div className="skeleton short" />
          <div className="skeleton" />
        </div>
      ) : !investigation ? (
        <div className="context-empty">
          <div className="context-icon">
            <GitBranch size={27} aria-hidden="true" />
          </div>
          <h3>Context before action.</h3>
          <p>
            Start an investigation to connect the fault to its downstream impact
            and the people who can help.
          </p>
          <ol className="ready-steps">
            <li>
              <span>01</span>
              <div>
                <strong>Trace the blast radius</strong>
                <small>Services and customers downstream</small>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <strong>Recover what worked</strong>
                <small>Runbooks, decisions, and memory</small>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <strong>Coordinate a response</strong>
                <small>Evidence-backed, simulated actions</small>
              </div>
            </li>
          </ol>
          <span className="small muted">
            <Route size={14} aria-hidden="true" /> Grounded in your FalkorDB
            graph
          </span>
        </div>
      ) : view === 'evidence' ? (
        <div className="evidence-list">
          <div className="context-kicker">
            <span className="status-dot" /> {investigation.evidence.length}{' '}
            source-linked findings
          </div>
          {investigation.evidence.length === 0 ? (
            <p className="empty-inline">
              No evidence returned. Try a different service or question.
            </p>
          ) : (
            investigation.evidence.map((e, index) => (
              <article
                key={e.id}
                className={`evidence-card ${activeEvidence?.id === e.id ? 'selected' : ''}`}
              >
                <div className="row between">
                  <span className="eyebrow">
                    EVIDENCE {String(index + 1).padStart(2, '0')}
                  </span>
                  <span className="source-tag mono">{e.source}</span>
                </div>
                <h3>{e.title}</h3>
                <p>{e.detail}</p>
                <button
                  className="text-button"
                  aria-expanded={activeEvidence?.id === e.id}
                  onClick={() =>
                    onEvidence(activeEvidence?.id === e.id ? null : e)
                  }
                >
                  {activeEvidence?.id === e.id
                    ? 'Hide exact path'
                    : 'Inspect exact path'}
                  <ArrowRight size={14} aria-hidden="true" />
                </button>
                {activeEvidence?.id === e.id ? (
                  <div className="exact-path">
                    <span className="eyebrow">RETURNED GRAPH PATH</span>
                    {e.path.length ? (
                      e.path.map((id, i) => (
                        <span key={`${id}-${i}`}>
                          <code>{id}</code>
                          {i < e.path.length - 1 ? (
                            <ChevronRight size={13} aria-hidden="true" />
                          ) : null}
                        </span>
                      ))
                    ) : (
                      <p>No path returned for this source.</p>
                    )}
                    <small>
                      Source: {e.source} · Evidence: {e.id}
                    </small>
                  </div>
                ) : null}
              </article>
            ))
          )}
          {investigation.memories.length ? (
            <div className="memory-used">
              <h3>Learnings recalled</h3>
              {investigation.memories.map((m) => (
                <p key={m.id}>
                  <span className={`outcome ${m.outcome}`}>{m.outcome}</span>{' '}
                  {m.content}
                </p>
              ))}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="trace-list">
          <div className="context-kicker">
            <Check size={13} aria-hidden="true" /> {investigation.trace.length}{' '}
            ordered stages ·{' '}
            {investigation.trace
              .reduce((n, t) => n + t.durationMs, 0)
              .toLocaleString()}{' '}
            ms
          </div>
          {investigation.trace.length === 0 ? (
            <p className="empty-inline">
              This investigation returned no query trace.
            </p>
          ) : (
            investigation.trace.map((step, index) => (
              <article className="trace-step" key={`${step.tool}-${index}`}>
                <button
                  className="trace-trigger"
                  onClick={() => setExpanded(expanded === index ? null : index)}
                  aria-expanded={expanded === index}
                  aria-controls={`trace-${index}`}
                >
                  <span className="step-number mono">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <span>
                    <strong>{step.agent}</strong>
                    <small>{step.tool}</small>
                  </span>
                  <ChevronRight
                    size={16}
                    className={expanded === index ? 'rotated' : ''}
                    aria-hidden="true"
                  />
                </button>
                <p>{step.purpose}</p>
                <div className="trace-meta mono">
                  {step.resultCount} results <span>·</span> {step.durationMs} ms
                </div>
                {expanded === index ? (
                  <div id={`trace-${index}`} className="query-detail">
                    <h4>Exact Cypher</h4>
                    <pre>
                      <code>{step.query || '(No query returned)'}</code>
                    </pre>
                    <h4>Parameters</h4>
                    <pre>
                      <code>{JSON.stringify(step.params, null, 2)}</code>
                    </pre>
                    <div className="row between">
                      <span>Result count</span>
                      <code>{step.resultCount}</code>
                    </div>
                    <div className="row between">
                      <span>Execution time</span>
                      <code>{step.durationMs} ms</code>
                    </div>
                    <small className="muted">
                      The API returns result counts, not raw result rows.
                    </small>
                  </div>
                ) : null}
              </article>
            ))
          )}
        </div>
      )}
      <div className="context-footer">
        <span className="mono">{investigation?.mode ?? 'GRAPH CONTEXT'}</span>
        <span>No infrastructure is changed</span>
      </div>
    </aside>
  );
}
