import { lazy, Suspense, useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import {
  ArrowDownToLine,
  ArrowLeftRight,
  ArrowRight,
  BookOpen,
  Check,
  CheckCheck,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  FileCheck2,
  FileText,
  FolderInput,
  GitBranch,
  Github,
  Inbox,
  Layers2,
  Loader2,
  Play,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { api, dateLabel, money } from './api';
import type { Config, Definition, Mode, Run, RunEvent, Scenario } from './types';

const Flow = lazy(() => import('./Flow'));
const categories = [
  'Employment',
  'Self-employment',
  'Business',
  'Investment',
  'Rental',
  'Agriculture & forestry',
  'Other',
  'Unclassified',
];
type View = 'documents' | 'workflow' | 'activity' | 'settings';
const statusLabels = {
  queued: 'Queued',
  processing: 'Processing',
  review: 'Needs review',
  approved: 'Approved',
  failed: 'Failed',
};

function StatusBadge({ run }: { run: Run }) {
  return (
    <span className={`badge ${run.status}`}>
      {run.status === 'approved' ? (
        <Check size={12} />
      ) : run.status === 'processing' ? (
        <Loader2 size={12} className="spin" />
      ) : (
        <span className="status-dot" />
      )}
      {statusLabels[run.status]}
    </span>
  );
}

function ReviewPanel({
  run,
  config,
  onRefresh,
  onError,
}: {
  run: Run;
  config?: Config;
  onRefresh: () => Promise<void>;
  onError: (value: string) => void;
}) {
  const record = run.result!;
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [note, setNote] = useState(record.review_note || '');
  const [form, setForm] = useState({
    document_id: record.document_id,
    client_name: record.client_name,
    party: record.party,
    purpose: record.purpose,
    document_date: record.document_date || '',
    original_amount: record.original_amount || '',
    currency: record.currency || '',
    income_type: record.income_type,
  });
  const field = (name: keyof typeof form, label: string, type = 'text') => (
    <label className="edit-field">
      {label}
      <input
        type={type}
        value={form[name]}
        required
        maxLength={name === 'purpose' ? 1000 : 200}
        step={type === 'number' ? '0.01' : undefined}
        onChange={(event) => setForm({ ...form, [name]: event.target.value })}
      />
    </label>
  );
  async function approve(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api(`/runs/${run.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ ...form, notes: note }),
      });
      await onRefresh();
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function sendSheet() {
    setBusy(true);
    try {
      await api(`/runs/${run.id}/sheets`, { method: 'POST' });
      await onRefresh();
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <aside className="review-panel" aria-label="Extracted document data">
      <div className="review-heading">
        <div>
          <h2>Extracted data</h2>
          <p>Structured, traceable, ready to review.</p>
        </div>
        <span className="icon-box">
          <Layers2 size={18} />
        </span>
      </div>
      <div className="quality-strip">
        <ShieldCheck size={17} />
        <span>
          <strong>
            {record.checks_passed} of {record.checks_total} required fields present
          </strong>
          <small>Completeness check, not AI confidence</small>
        </span>
      </div>
      <form onSubmit={approve}>
        <div className="section-heading">
          <h3>Document details</h3>
          {run.status === 'review' ? (
            <button type="button" className="text-button" onClick={() => setEditing(!editing)}>
              {editing ? 'Close editor' : 'Edit fields'}
            </button>
          ) : (
            <CheckCircle2 size={15} className="teal" />
          )}
        </div>
        {editing ? (
          <div className="edit-grid">
            {field('document_id', 'Document ID')}
            {field('client_name', 'Client name')}
            {field('party', 'Counterparty')}
            {field('purpose', 'Purpose')}
            {field('document_date', 'Document date', 'date')}
            {field('original_amount', 'Original amount', 'number')}
            {field('currency', 'Currency (ISO code)')}
            <label className="edit-field">
              Income category
              <select
                value={form.income_type}
                onChange={(event) => setForm({ ...form, income_type: event.target.value })}
              >
                {categories.map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            </label>
          </div>
        ) : (
          <dl className="details-list">
            <div>
              <dt>Document ID</dt>
              <dd>{form.document_id || <span className="missing">Missing</span>}</dd>
            </div>
            <div>
              <dt>Client</dt>
              <dd>
                {form.client_name || 'Not identified'}
                <small>{record.client_number}</small>
              </dd>
            </div>
            <div>
              <dt>Counterparty</dt>
              <dd>{form.party || 'Not identified'}</dd>
            </div>
            <div>
              <dt>Document date</dt>
              <dd>{dateLabel(form.document_date)}</dd>
            </div>
            <div>
              <dt>Source language</dt>
              <dd>
                {record.language === 'en'
                  ? 'English'
                  : record.language === 'de'
                    ? 'German'
                    : record.language || 'Unknown'}
                <span className="inline-note"> → German</span>
              </dd>
            </div>
          </dl>
        )}
        <div className="section-heading">
          <h3>Currency normalization</h3>
          <ArrowLeftRight size={15} />
        </div>
        <div className="money-conversion">
          <div>
            <span>Original amount</span>
            <strong>
              {record.currency
                ? money(record.original_amount, record.currency)
                : `${record.original_amount || '—'} ?`}
            </strong>
            <small>{record.currency || 'Currency unconfirmed'}</small>
          </div>
          <ArrowRight size={18} />
          <div>
            <span>Normalized amount</span>
            <strong className="eur-amount">{money(record.fx.amount_eur)}</strong>
            <small>EUR</small>
          </div>
        </div>
        <div className="rate-note">
          <span>
            {record.fx.rate
              ? `1 ${record.currency} = ${record.fx.rate} EUR`
              : 'No conversion available'}
          </span>
          <span>{record.fx.date ? dateLabel(record.fx.date) : 'Needs correction'}</span>
        </div>
        <p className="source-note">{record.fx.source}</p>
        <div className="section-heading">
          <h3>Tax classification</h3>
          <span className="small-pill">Suggested</span>
        </div>
        <div className="classification">
          <span className="category-icon">
            <FileCheck2 size={19} />
          </span>
          <div>
            <strong>{form.income_type}</strong>
            <span>
              {record.relevance} · {record.document_type}
            </span>
          </div>
        </div>
        <p className="assessment">{record.assessment}</p>
        {record.tax_deduction != null ? (
          <div className="deduction-row">
            <span>Withheld tax</span>
            <strong>{money(record.fx.tax_deduction_eur)}</strong>
          </div>
        ) : null}
        {record.evidence.length ? (
          <details className="evidence">
            <summary>
              View source evidence <ChevronDown size={14} />
            </summary>
            {record.evidence.map((quote) => (
              <blockquote key={quote}>{quote}</blockquote>
            ))}
          </details>
        ) : null}
        {record.warnings.length ? (
          <div className="review-warning">
            <AlertCircle size={16} />
            <div>
              <strong>Reviewer attention</strong>
              {record.warnings.map((warning) => (
                <p key={warning}>{warning}</p>
              ))}
            </div>
          </div>
        ) : null}
        {run.status === 'review' ? (
          <>
            <label className="notes-label" htmlFor="review-notes">
              Review note <span>Optional</span>
            </label>
            <textarea
              id="review-notes"
              value={note}
              maxLength={2000}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Add context or explain a correction…"
            />
            <button
              className="button primary full"
              type="submit"
              disabled={
                busy ||
                !form.document_date ||
                !form.currency ||
                !form.original_amount ||
                form.income_type === 'Unclassified'
              }
            >
              {busy ? <Loader2 size={16} className="spin" /> : <CheckCheck size={17} />}Approve
              document
            </button>
            <p className="approval-note">Confirm the data before exporting. Not tax advice.</p>
          </>
        ) : run.status === 'approved' ? (
          <div className="approved-actions">
            <p>
              <CheckCircle2 size={17} /> Reviewed {dateLabel(record.reviewed_at)}
            </p>
            <div className="export-pair">
              <a className="button primary" href={`/api/runs/${run.id}/export?format=csv`}>
                <ArrowDownToLine size={16} />
                Export CSV
              </a>
              <a className="button secondary" href={`/api/runs/${run.id}/export?format=json`}>
                JSON
              </a>
            </div>
            {run.mode === 'live' && config?.sheets_ready ? (
              <button
                className="button secondary full"
                type="button"
                disabled={busy || !!run.sheets_status}
                onClick={sendSheet}
              >
                {run.sheets_status ? 'Sheet export attempted' : 'Send to Google Sheets'}
              </button>
            ) : null}
          </div>
        ) : null}
      </form>
    </aside>
  );
}

function SourceDocument({ run }: { run: Run }) {
  const [translation, setTranslation] = useState(false);
  const text = translation ? run.result?.translated_text : run.original_text;
  return (
    <section className="source-panel" aria-label="Document preview">
      <div className="source-toolbar">
        <div className="segmented">
          <button className={!translation ? 'active' : ''} onClick={() => setTranslation(false)}>
            Original
          </button>
          <button
            className={translation ? 'active' : ''}
            onClick={() => setTranslation(true)}
            disabled={!run.result?.translated_text}
          >
            German translation
          </button>
        </div>
        <span className="source-format">
          <FileText size={14} /> Extracted text
        </span>
      </div>
      <div className="document-stage">
        <article className="document-paper">
          <div className="paper-topline">
            <div className="paper-mark">
              <FileText size={23} />
            </div>
            <span>{run.mode === 'demo' ? 'Fictional sample' : 'Source text'}</span>
          </div>
          <div className="paper-content">
            {text ? (
              text
                .split('\n')
                .map((line, index) =>
                  index === 0 ? <h2 key={index}>{line}</h2> : <p key={index}>{line || '\u00a0'}</p>,
                )
            ) : (
              <div className="source-loading">
                <Loader2 className="spin" size={24} />
                <p>Reading the document…</p>
              </div>
            )}
          </div>
          <div className="paper-bottom">
            <span>
              {run.mode === 'demo'
                ? 'Beleg demo · synthetic content'
                : 'Original extracted text · verify against your source file'}
            </span>
            <span>1</span>
          </div>
        </article>
      </div>
      <footer className="source-footer">
        <ShieldCheck size={14} />
        <span>
          {run.mode === 'demo'
            ? 'Prepared sample. No external services called.'
            : 'The original document is preserved in local storage.'}
        </span>
        <span className="local-tag">Local-first</span>
      </footer>
    </section>
  );
}

function SettingsPage({
  config,
  onImport,
}: {
  config?: Config;
  onImport: (source: string) => void;
}) {
  return (
    <div className="settings-page">
      <h2>Your machine. Your credentials.</h2>
      <p>
        Demo mode is ready without a key. Live mode runs the same workflow with your own provider.
      </p>
      <section className="settings-section">
        <h3>
          <Sparkles size={19} /> AI connection
        </h3>
        <dl className="settings-facts">
          <div>
            <dt>Status</dt>
            <dd>
              <span className={`badge ${config?.live_ready ? 'approved' : 'review'}`}>
                {config?.live_ready ? 'Configured on backend' : 'Not configured'}
              </span>
            </dd>
          </div>
          <div>
            <dt>Provider</dt>
            <dd>{config?.provider_host || 'OpenAI-compatible endpoint'}</dd>
          </div>
          <div>
            <dt>Model</dt>
            <dd>
              <code>{config?.model || 'auto'}</code>
            </dd>
          </div>
        </dl>
        <pre className="setup-code">{`# In your local .env (never committed)\nOPENAI_API_KEY=your-own-key\nOPENAI_BASE_URL=https://freellm.gotiq.co/v1\nOPENAI_MODEL=auto`}</pre>
        <p>
          Restart the backend after changing configuration. Keys are never sent to the browser.
          Scanned documents require a vision-capable model behind your endpoint.
        </p>
      </section>
      <section className="settings-section">
        <h3>
          <FolderInput size={19} /> Optional Google connectors
        </h3>
        <p>
          Configure a local Google credential file and resource IDs. Imports are explicit, bounded,
          and deduplicated by document content; nothing polls your accounts automatically.
        </p>
        <div className="connector-line">
          <div>
            <strong>Google Drive</strong>
            <span>Import the latest supported files from one folder.</span>
          </div>
          <button
            className="button secondary"
            disabled={!config?.drive_ready || !config?.live_ready}
            onClick={() => onImport('drive')}
          >
            Import files
          </button>
        </div>
        <div className="connector-line">
          <div>
            <strong>Gmail</strong>
            <span>Read attachments from recent messages. Requires user OAuth credentials.</span>
          </div>
          <button
            className="button secondary"
            disabled={!config?.google_ready || !config?.live_ready}
            onClick={() => onImport('gmail')}
          >
            Import attachments
          </button>
        </div>
        <div className="connector-line">
          <div>
            <strong>Google Sheets</strong>
            <span>
              {config?.sheets_ready
                ? 'Configured. Export an approved live document from its review panel.'
                : 'Set GOOGLE_SHEET_ID and credentials to enable explicit export.'}
            </span>
          </div>
          <span className="small-pill">{config?.sheets_ready ? 'Configured' : 'Optional'}</span>
        </div>
      </section>
      <div className="privacy-notice">
        <ShieldCheck size={21} />
        <div>
          <h3>Local-first is not the same as offline.</h3>
            <p>
              Demo makes no AI or Google requests. Live mode sends document content to your configured
              AI endpoint and queries Frankfurter for FX. The VPS copy is protected by Cloudflare
              Access for its owner; do not share access or use it for real tax records.
            </p>
        </div>
      </div>
      <a
        className="text-link"
        href="https://github.com/MantakaMahir/belegflow#readme"
        target="_blank"
        rel="noreferrer"
      >
        <BookOpen size={16} /> Read setup, privacy, and limitations <ExternalLink size={13} />
      </a>
    </div>
  );
}

export default function App() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [config, setConfig] = useState<Config>();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [definition, setDefinition] = useState<Definition>();
  const [selected, setSelected] = useState('');
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [view, setView] = useState<View>('documents');
  const [mode, setMode] = useState<Mode>('demo');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [showSamples, setShowSamples] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [showQueue, setShowQueue] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const run = runs.find((value) => value.id === selected);

  const refresh = useCallback(async () => {
    const data = await api<Run[]>('/runs');
    setRuns(data);
    setSelected(
      (previous) =>
        previous ||
        data.find((value) => value.scenario_id === 'us-dividend')?.id ||
        data[0]?.id ||
        '',
    );
  }, []);
  useEffect(() => {
    let disposed = false;
    Promise.all([api<Config>('/config'), api<Scenario[]>('/scenarios'), refresh()])
      .then(([configuration, samples]) => {
        if (!disposed) {
          setConfig(configuration);
          setScenarios(samples);
        }
      })
      .catch((error) => {
        if (!disposed) setError(error.message);
      })
      .finally(() => {
        if (!disposed) setLoading(false);
      });
    return () => {
      disposed = true;
    };
  }, [refresh]);
  useEffect(() => {
    if (view !== 'workflow' && view !== 'activity') return;
    let disposed = false;
    api<Definition>('/workflow')
      .then((graph) => {
        if (!disposed) setDefinition(graph);
      })
      .catch((error) => {
        if (!disposed) setError(error.message);
      });
    return () => {
      disposed = true;
    };
  }, [view]);
  const processing = runs.some(
    (value) => value.status === 'processing' || value.status === 'queued',
  );
  useEffect(() => {
    if (!processing) return;
    const timer = window.setInterval(
      () => refresh().catch((error) => setError(error.message)),
      1100,
    );
    return () => clearInterval(timer);
  }, [processing, refresh]);
  useEffect(() => {
    if (!selected) return;
    let disposed = false;
    setEvents([]);
    api<RunEvent[]>(`/runs/${selected}/events`)
      .then((data) => {
        if (!disposed) setEvents(data);
      })
      .catch((error) => {
        if (!disposed) setError(error.message);
      });
    const stream = new EventSource(`/api/runs/${selected}/stream`);
    stream.addEventListener('step', (event) => {
      const data = JSON.parse((event as MessageEvent).data) as RunEvent;
      if (!disposed)
        setEvents((previous) =>
          previous.some((value) => value.id === data.id) ? previous : [...previous, data],
        );
    });
    stream.addEventListener('settled', () => {
      stream.close();
      refresh().catch((error) => setError(error.message));
    });
    return () => {
      disposed = true;
      stream.close();
    };
  }, [selected, run?.status, refresh]);

  async function startDemo(scenario: string) {
    setError('');
    try {
      const result = await api<{ run: Run; created: boolean }>('/demo', {
        method: 'POST',
        body: JSON.stringify({ scenario_id: scenario }),
      });
      await refresh();
      setSelected(result.run.id);
      setMode('demo');
      setView('documents');
      setShowSamples(false);
    } catch (error) {
      setError((error as Error).message);
    }
  }
  async function upload(file?: File) {
    if (!file) return;
    if (!config?.live_ready) {
      setError('Set OPENAI_API_KEY in your backend .env, restart, and switch to live mode.');
      return;
    }
    if (file.size > (config.max_upload_mb || 15) * 1024 * 1024) {
      setError('Upload exceeds the 15 MB limit.');
      return;
    }
    setUploading(true);
    setError('');
    try {
      const form = new FormData();
      form.append('file', file);
      const data = await api<{ run: Run; created: boolean }[]>('/upload', {
        method: 'POST',
        body: form,
      });
      await refresh();
      setSelected(data[0].run.id);
      setView('documents');
      setMode('live');
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setUploading(false);
      if (input.current) input.current.value = '';
    }
  }
  async function importGoogle(source: string) {
    setUploading(true);
    setError('');
    try {
      await api('/import', { method: 'POST', body: JSON.stringify({ source, limit: 5 }) });
      await refresh();
      setMode('live');
      setView('documents');
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setUploading(false);
    }
  }
  const filtered = runs.filter(
    (value) =>
      value.mode === mode &&
      (filter === 'all' || value.status === filter) &&
      `${value.filename} ${value.result?.party || ''} ${value.result?.client_name || ''}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const counts = {
    review: runs.filter((value) => value.mode === mode && value.status === 'review').length,
    approved: runs.filter((value) => value.mode === mode && value.status === 'approved').length,
  };
  const title = {
    documents: 'Document inbox',
    workflow: 'Workflow',
    activity: 'Run activity',
    settings: 'Connections & setup',
  }[view];

  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace">
        Skip to workspace
      </a>
      <nav className="navigation" aria-label="Main navigation">
        <a
          href="#"
          className="brand"
          onClick={(event) => {
            event.preventDefault();
            setView('documents');
          }}
        >
          <span className="brand-symbol">
            <Layers2 size={23} />
          </span>
          <span>
            Beleg:
            <small>German Tax Document Review</small>
          </span>
        </a>
        <div className="workspace-label">
          <span className="workspace-avatar">M</span>
          <div>
            Mahir’s workspace<small>Local workspace</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <div className="nav-group">
          {(
            [
              ['documents', Inbox, 'Document inbox'],
              ['workflow', GitBranch, 'Workflow'],
              ['activity', Layers2, 'Run activity'],
            ] as const
          ).map(([id, Icon, label]) => (
            <button
              key={id}
              aria-label={label}
              aria-current={view === id ? 'page' : undefined}
              className={`nav-item ${view === id ? 'active' : ''}`}
              onClick={() => {
                setView(id);
                setShowQueue(false);
              }}
            >
              <Icon size={18} />
              <span>{label}</span>
              {id === 'documents' && counts.review ? (
                <span className="nav-count">{counts.review}</span>
              ) : null}
            </button>
          ))}
        </div>
        <div className="nav-section-label">Workspace</div>
        <button
          aria-label="Connections & setup"
          aria-current={view === 'settings' ? 'page' : undefined}
          className={`nav-item ${view === 'settings' ? 'active' : ''}`}
          onClick={() => setView('settings')}
        >
          <Settings2 size={18} />
          <span>Connections & setup</span>
        </button>
        <div className="sidebar-bottom">
          <div className="local-card">
            <span className="connection-dot" />
            <strong>Runs on your machine</strong>
            <p>Open source. No account required.</p>
            <a href="https://github.com/MantakaMahir/belegflow" target="_blank" rel="noreferrer">
              <Github size={15} /> View repository <ExternalLink size={12} />
            </a>
          </div>
          <a
            className="help-link"
            href="https://github.com/MantakaMahir/belegflow#quick-start"
            target="_blank"
            rel="noreferrer"
          >
            <CircleHelp size={17} /> Documentation <ExternalLink size={12} />
          </a>
          <div className="builder">
            <span className="builder-avatar">MM</span>
            <div>
              Built by Mantaka Mahir<small>AI engineer & product builder</small>
            </div>
          </div>
        </div>
      </nav>
      <main id="workspace" className="workspace" tabIndex={-1}>
        <header className="topbar">
          <div className="breadcrumb">
            <span>Workspace</span>
            <span>/</span>
            <strong>{title}</strong>
          </div>
          <div className="topbar-right">
            <a
              className="github-top"
              href="https://github.com/MantakaMahir/belegflow"
              target="_blank"
              rel="noreferrer"
            >
              <Github size={16} />
              <span>Source code</span>
            </a>
            <span className="top-avatar">MM</span>
          </div>
        </header>
        <div className="page-heading">
          <div>
            <h1>{title}</h1>
            <p>
              {view === 'documents'
                ? 'From source file to reviewed German tax records.'
                : view === 'workflow'
                  ? 'A real pipeline. Nothing behind a black box.'
                  : view === 'activity'
                    ? 'Follow every step from source to approval.'
                    : 'Connect live services when you’re ready.'}
            </p>
          </div>
          <div className="page-actions">
            <div className="mode-switch" aria-label="Processing mode">
              <button
                className={mode === 'demo' ? 'active' : ''}
                onClick={() => {
                  setMode('demo');
                  setSelected(runs.find((value) => value.mode === 'demo')?.id || '');
                }}
              >
                <Play size={12} />
                Demo
              </button>
              <button
                className={mode === 'live' ? 'active' : ''}
                onClick={() => {
                  setMode('live');
                  setSelected(runs.find((value) => value.mode === 'live')?.id || '');
                }}
              >
                Live
              </button>
            </div>
            <button
              className="button primary"
              disabled={uploading}
              onClick={() =>
                mode === 'demo' ? setShowSamples(!showSamples) : input.current?.click()
              }
            >
              {uploading ? <Loader2 size={16} className="spin" /> : <Plus size={17} />}
              {mode === 'demo' ? 'Try a sample' : 'Upload document'}
            </button>
          </div>
        </div>
        <input
          ref={input}
          className="visually-hidden"
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.txt,.eml"
          aria-label="Upload document or email file"
          onChange={(event) => upload(event.target.files?.[0])}
        />
        <div className={`mode-banner ${mode}`}>
          <span className="banner-icon">
            {mode === 'demo' ? <Sparkles size={17} /> : <ShieldCheck size={17} />}
          </span>
          <p>
            <strong>
              {mode === 'demo'
                ? 'Explore the product, without an API key.'
                : 'Live mode uses your configured AI provider.'}
            </strong>
            <span>
              {mode === 'demo'
                ? 'Fictional documents. Prepared AI responses. Real processing flow.'
                : config?.live_ready
                  ? `Model: ${config.model}. Document content will be sent to ${config.provider_host}.`
                  : 'Configure your API key in the backend .env to process your own documents.'}
            </span>
          </p>
          <button
            className="text-button"
            onClick={() => (mode === 'demo' ? setShowSamples(!showSamples) : setView('settings'))}
          >
            {mode === 'demo' ? 'Browse examples' : 'View setup'}
            <ArrowRight size={14} />
          </button>
        </div>
        {error ? (
          <div className="error-banner" role="alert">
            <AlertCircle size={17} />
            <span>{error}</span>
            <button aria-label="Dismiss error" onClick={() => setError('')}>
              <X size={16} />
            </button>
          </div>
        ) : null}
        {showSamples ? (
          <section className="sample-browser" aria-label="Prepared demo examples">
            <div className="section-heading">
              <h2>Three documents. Three different paths.</h2>
              <button
                className="icon-button"
                aria-label="Close examples"
                onClick={() => setShowSamples(false)}
              >
                <X size={17} />
              </button>
            </div>
            <div className="sample-options">
              {scenarios.map((scenario, index) => (
                <button key={scenario.id} onClick={() => startDemo(scenario.id)}>
                  <span className={`sample-number s${index}`}>
                    <FileText size={20} />
                  </span>
                  <strong>{scenario.title}</strong>
                  <span>{scenario.description}</span>
                  <span className="sample-action">
                    Open example <ArrowRight size={14} />
                  </span>
                </button>
              ))}
            </div>
          </section>
        ) : null}
        {loading ? (
          <div className="loading-state">
            <Loader2 size={24} className="spin" />
            <h2>Connecting to your workspace…</h2>
          </div>
        ) : view === 'settings' ? (
          <SettingsPage config={config} onImport={importGoogle} />
        ) : view === 'workflow' ? (
          definition ? (
            <Suspense fallback={<div className="loading-state">Loading workflow canvas…</div>}>
              <Flow definition={definition} events={events} run={run} />
            </Suspense>
          ) : (
            <div className="loading-state">
              <Loader2 size={24} className="spin" />
              <h2>Loading workflow definition…</h2>
            </div>
          )
        ) : view === 'activity' ? (
          <section className="activity-page">
            <div className="section-heading">
              <h2>{run?.filename || 'No document selected'}</h2>
              {run ? <StatusBadge run={run} /> : null}
            </div>
            <p>Persisted execution events, not a simulated progress bar.</p>
            <ol className="timeline">
              {events.map((event) => (
                <li key={event.id}>
                  <span className={`timeline-dot ${event.status}`}>
                    {event.status === 'completed' ? <Check size={13} /> : <span />}
                  </span>
                  <div>
                    <strong>
                      {definition?.nodes.find((node) => node.id === event.node)?.label ||
                        event.node}
                    </strong>
                    <span>
                      {event.status}
                      {event.payload.duration_ms != null
                        ? ` · ${event.payload.duration_ms} ms`
                        : ''}
                    </span>
                    {event.payload.error ? <p>{event.payload.error}</p> : null}
                  </div>
                  <time>{new Date(event.created_at).toLocaleTimeString()}</time>
                </li>
              ))}
            </ol>
            {!events.length ? <p>No events yet. Select or upload a document to start.</p> : null}
          </section>
        ) : (
          <>
            <div className="inbox-controls">
              <div className="filter-tabs">
                <button
                  className={filter === 'all' ? 'active' : ''}
                  onClick={() => setFilter('all')}
                >
                  All documents <span>{runs.filter((value) => value.mode === mode).length}</span>
                </button>
                <button
                  className={filter === 'review' ? 'active' : ''}
                  onClick={() => setFilter('review')}
                >
                  Needs review <span>{counts.review}</span>
                </button>
                <button
                  className={filter === 'approved' ? 'active' : ''}
                  onClick={() => setFilter('approved')}
                >
                  Approved <span>{counts.approved}</span>
                </button>
              </div>
              <label className="search">
                <Search size={16} />
                <input
                  placeholder="Search documents…"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  aria-label="Search documents"
                />
                <span>⌕</span>
              </label>
            </div>
            <div className={`inbox-layout ${showQueue ? 'queue-open' : ''}`}>
              <aside className="document-queue" aria-label="Document queue">
                <div className="queue-heading">
                  <span>Documents</span>
                  <span>{filtered.length}</span>
                </div>
                {filtered.length ? (
                  filtered.map((value) => (
                    <button
                      key={value.id}
                      className={`queue-item ${selected === value.id ? 'selected' : ''}`}
                      onClick={() => {
                        setSelected(value.id);
                        setShowQueue(false);
                      }}
                    >
                      <div className="queue-item-top">
                        <span
                          className={`file-icon ${value.result?.income_type === 'Investment' ? 'blue' : value.result?.income_type === 'Unclassified' ? 'amber' : 'teal-bg'}`}
                        >
                          <FileText size={19} />
                        </span>
                        <StatusBadge run={value} />
                      </div>
                      <strong>{value.result?.party || value.filename}</strong>
                      <span className="queue-filename">{value.filename}</span>
                      <div className="queue-meta">
                        <span>{value.result?.document_type || value.source}</span>
                        <strong>
                          {value.result?.original_amount
                            ? value.result.currency
                              ? money(value.result.original_amount, value.result.currency)
                              : `${value.result.original_amount} ?`
                            : 'Pending'}
                        </strong>
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="queue-empty">
                    <Inbox size={25} />
                    <p>
                      {query || filter !== 'all'
                        ? 'No matching documents.'
                        : 'Your inbox is clear.'}
                    </p>
                  </div>
                )}
                <button
                  className="queue-add"
                  onClick={() => (mode === 'demo' ? setShowSamples(true) : input.current?.click())}
                >
                  <Plus size={15} />
                  {mode === 'demo' ? 'Explore sample library' : 'Add a document'}
                </button>
                <div className="queue-bottom">
                  <ShieldCheck size={13} /> Documents stay in local storage
                </div>
              </aside>
              <section className="document-workspace">
                <button
                  className="mobile-queue-toggle button secondary"
                  onClick={() => setShowQueue(!showQueue)}
                >
                  <Inbox size={16} />
                  {showQueue ? 'Hide documents' : 'Choose document'}
                </button>
                {run && run.mode === mode ? (
                  <>
                    <div className="document-heading">
                      <div className="document-heading-main">
                        <span className="document-type-icon">
                          <FileText size={21} />
                        </span>
                        <div>
                          <h2>{run.filename}</h2>
                          <p>
                            {run.source}
                            <span>·</span>
                            {dateLabel(run.created_at)}
                            <span>·</span>
                            {run.result?.document_type || 'Processing document'}
                          </p>
                        </div>
                      </div>
                      <button
                        className="icon-button"
                        aria-label="View document workflow"
                        title="View workflow"
                        onClick={() => setView('workflow')}
                      >
                        <GitBranch size={19} />
                      </button>
                    </div>
                    <div className="document-subbar">
                      <span>
                        <span className="connection-dot" />
                        {run.status === 'review'
                          ? 'Processing complete. Your review is next.'
                          : run.status === 'approved'
                            ? 'Reviewed and ready to export.'
                            : run.status === 'failed'
                              ? 'This run needs attention.'
                              : 'Processing your document…'}
                      </span>
                      <StatusBadge run={run} />
                    </div>
                    {run.status === 'failed' ? (
                      <div className="failed-state">
                        <AlertCircle size={28} />
                        <h2>Processing stopped safely.</h2>
                        <p>{run.error}</p>
                        <button
                          className="button primary"
                          onClick={async () => {
                            try {
                              await api(`/runs/${run.id}/retry`, { method: 'POST' });
                              await refresh();
                            } catch (error) {
                              setError((error as Error).message);
                            }
                          }}
                        >
                          Retry from checkpoint
                        </button>
                      </div>
                    ) : (
                      <div className="document-split">
                        <SourceDocument key={`${run.id}-source`} run={run} />
                        {run.result ? (
                          <ReviewPanel
                            key={`${run.id}-${run.result.reviewed_at || 'unreviewed'}`}
                            run={run}
                            config={config}
                            onRefresh={refresh}
                            onError={setError}
                          />
                        ) : (
                          <div className="review-loading">
                            <Loader2 size={24} className="spin" />
                            <h3>Turning the document into data.</h3>
                            <p>Follow the actual processing steps in the workflow view.</p>
                            <button
                              className="button secondary"
                              onClick={() => setView('workflow')}
                            >
                              <GitBranch size={16} />
                              View workflow
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="empty-workspace">
                    <span className="empty-icon">
                      <FolderInput size={34} />
                    </span>
                    <h2>
                      {mode === 'demo'
                        ? 'Start with a real product walkthrough.'
                        : 'Give your documents a clear path.'}
                    </h2>
                    <p>
                      {mode === 'demo'
                        ? 'Choose a fictional example to inspect extraction, historical currency normalization, and human review.'
                        : `Upload a PDF, image, text document, or email file. Up to ${config?.max_upload_mb || 15} MB and ${config?.max_pages || 10} PDF pages.`}
                    </p>
                    <button
                      className="button primary"
                      onClick={() =>
                        mode === 'demo' ? setShowSamples(true) : input.current?.click()
                      }
                    >
                      {mode === 'demo' ? <Play size={16} /> : <Upload size={16} />}
                      {mode === 'demo' ? 'Explore examples' : 'Choose a file'}
                    </button>
                    {mode === 'live' ? (
                      <p className="small-note">
                        {config?.live_ready
                          ? 'Your file will be sent to the configured AI provider.'
                          : 'Configure a backend API key first. Demo mode needs no key.'}
                      </p>
                    ) : null}
                  </div>
                )}
              </section>
            </div>
          </>
        )}
        <footer className="workspace-footer">
          <span>
            <Layers2 size={13} /> Beleg <span>·</span> Open-source document review
          </span>
          <span>FastAPI / LangGraph / React Flow</span>
        </footer>
      </main>
    </div>
  );
}
