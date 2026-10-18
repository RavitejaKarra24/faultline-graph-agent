import { useState } from 'react';
import {
  BookmarkPlus,
  Check,
  Lightbulb,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react';
import { api, message } from '../api';
import type { GraphNode, Memory } from '../types';

interface Props {
  memories: Memory[];
  services: GraphNode[];
  sessionId: string;
  onSaved: (memory: Memory) => void;
  onRefresh: () => void;
  connected: boolean;
}
export default function MemoryPage({
  memories,
  services,
  sessionId,
  onSaved,
  onRefresh,
  connected,
}: Props) {
  const [serviceId, setServiceId] = useState('svc-redis');
  const [outcome, setOutcome] = useState<Memory['outcome']>('helpful');
  const [content, setContent] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [filter, setFilter] = useState('all');
  const filtered = memories.filter(
    (m) => filter === 'all' || m.serviceId === filter,
  );
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!content.trim()) {
      setError('Write a learning before saving.');
      return;
    }
    setBusy(true);
    setError('');
    setSaved(false);
    try {
      const memory = await api.saveMemory(
        serviceId,
        content.trim(),
        outcome,
        sessionId,
      );
      onSaved(memory);
      setContent('');
      setSaved(true);
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="memory-layout">
      <section className="panel memory-form-panel">
        <div className="panel-heading">
          <div>
            <h2>Leave context for next time</h2>
            <p>Good incident response compounds.</p>
          </div>
          <BookmarkPlus size={21} aria-hidden="true" />
        </div>
        <form onSubmit={save} className="memory-form">
          <label htmlFor="memory-service">Service</label>
          <select
            id="memory-service"
            value={serviceId}
            onChange={(e) => setServiceId(e.target.value)}
            required
          >
            {services.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
          <fieldset>
            <legend>What should we remember?</legend>
            <div className="outcome-options">
              <label className={outcome === 'helpful' ? 'checked' : ''}>
                <input
                  type="radio"
                  name="outcome"
                  value="helpful"
                  checked={outcome === 'helpful'}
                  onChange={() => setOutcome('helpful')}
                />
                <Lightbulb size={17} aria-hidden="true" /> Helpful
              </label>
              <label className={outcome === 'avoid' ? 'checked' : ''}>
                <input
                  type="radio"
                  name="outcome"
                  value="avoid"
                  checked={outcome === 'avoid'}
                  onChange={() => setOutcome('avoid')}
                />
                <ShieldAlert size={17} aria-hidden="true" /> Avoid
              </label>
            </div>
          </fieldset>
          <label htmlFor="memory-content">
            Learning <span className="muted">(required)</span>
          </label>
          <textarea
            id="memory-content"
            value={content}
            onChange={(e) => {
              setContent(e.target.value);
              setSaved(false);
            }}
            placeholder="e.g. Cap connection pools before draining Redis clients. Avoid a blanket restart."
            rows={6}
            maxLength={2000}
            required
            aria-describedby="memory-hint memory-error"
            aria-invalid={Boolean(error)}
          />
          <p id="memory-hint" className="small muted">
            Saved in the workspace graph, not just this browser. Recalled by
            future investigations.
          </p>
          {error ? (
            <p id="memory-error" className="form-error" role="alert">
              {error}
            </p>
          ) : null}
          <button
            className="button primary"
            disabled={busy || !connected || services.length === 0}
            aria-busy={busy}
          >
            {busy ? (
              <span className="spinner" />
            ) : (
              <BookmarkPlus size={16} aria-hidden="true" />
            )}
            {busy ? 'Saving learning…' : 'Save learning'}
          </button>
          {saved ? (
            <p className="success-note" role="status">
              <Check size={16} aria-hidden="true" /> Learning saved. Run another
              investigation to recall it.
            </p>
          ) : null}
        </form>
      </section>
      <section className="panel memory-list-panel">
        <div className="panel-heading">
          <div>
            <h2>
              Workspace memory{' '}
              <span className="mono muted">{memories.length}</span>
            </h2>
            <p>Preserved across new sessions.</p>
          </div>
          <button
            className="icon-button"
            aria-label="Refresh memories"
            onClick={onRefresh}
          >
            <RefreshCw size={16} />
          </button>
        </div>
        <div className="memory-filter">
          <label htmlFor="memory-filter">Filter by service</label>
          <select
            id="memory-filter"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">All services</option>
            {services.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        {filtered.length ? (
          <ul className="memory-list">
            {filtered.map((m) => (
              <li key={m.id}>
                <div className="row between">
                  <span className={`outcome ${m.outcome}`}>
                    {m.outcome === 'helpful' ? (
                      <Lightbulb size={13} aria-hidden="true" />
                    ) : (
                      <ShieldAlert size={13} aria-hidden="true" />
                    )}
                    {m.outcome}
                  </span>
                  <time dateTime={m.createdAt} className="small muted">
                    {new Date(m.createdAt).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </time>
                </div>
                <p>{m.content}</p>
                <div className="row between small">
                  <code>{m.serviceId}</code>
                  <span className="muted">
                    {m.sessionId === sessionId
                      ? 'This session'
                      : 'Previous session'}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="memory-empty">
            <Lightbulb size={30} aria-hidden="true" />
            <h3>
              {filter === 'all'
                ? 'The next response starts here.'
                : 'No learnings for this service.'}
            </h3>
            <p>
              Record what helped—or what to avoid. New sessions keep this
              knowledge intact.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
