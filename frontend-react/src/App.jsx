import { useEffect, useRef, useState } from "react";
import { api } from "./api";

const popularModels = [
  ["qwen2.5:3b", "Fast general-purpose assistant"],
  ["qwen2.5-coder:3b", "Code generation and debugging"],
  ["llama3.2:3b", "Lightweight reasoning model"],
  ["mistral:7b", "General reasoning model"],
  ["phi3:mini", "Compact high-performance model"],
];

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

function ErrorNotice({ error }) {
  return error ? <div className="notice error">{error}</div> : null;
}

// ---------------------------------------------------------------------------
// WelcomePage — shown to visitors before they start login
// ---------------------------------------------------------------------------

function WelcomePage({ onContinue, onSignup }) {
  return (
    <main className="welcome-shell">
      <section className="welcome-content">
        <div className="welcome-brand">
          <span className="brand-mark">S</span>
          <span>SOVEREIGN AI WORKBENCH</span>
        </div>
        <div className="welcome-copy">
          <p className="eyebrow">LOCAL / PRIVATE / AIR-GAPPED</p>
          <h1>Sovereign AI Workbench</h1>
          <p>Local, private, air-gapped AI for sensitive work.</p>
          <button className="primary welcome-action" onClick={onContinue}>
            Sign in to continue <span aria-hidden="true">→</span>
          </button>
          <button className="text-button welcome-signup" onClick={onSignup}>Create a new account</button>
        </div>
        <div className="welcome-foot">
          <span>Built for confidential work</span>
          <span>Powered by your local models</span>
        </div>
      </section>
    </main>
  );
}

// ---------------------------------------------------------------------------
// LoginPage — credential form
// ---------------------------------------------------------------------------

function LoginPage({ onLogin, onBack }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api.login(username, password);
      if (!result.user) {
        throw new Error("Server returned an empty user. Please try again.");
      }
      onLogin(result.user);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="brand">
          <span className="brand-mark">S</span>
          <div>
            <strong>Sovereign AI</strong>
            <small>Private local intelligence</small>
          </div>
        </div>
        <p className="eyebrow">SECURE WORKBENCH</p>
        <h1>Sign in to your local workspace.</h1>
        <p className="muted">
          Your session is protected by an HTTP-only server cookie. Credentials never enter the
          React application.
        </p>
        <ErrorNotice error={error} />
        <form className="login-form" onSubmit={submit}>
          <label>
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <button className="primary" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        {onBack && (
          <button
            className="text-button"
            style={{ marginTop: "1rem" }}
            onClick={onBack}
          >
            ← Back
          </button>
        )}
      </section>
    </main>
  );
}

function SignupPage({ onSignup, onBack }) {
  const [form, setForm] = useState({ username: "", name: "", email: "", password: "", confirmation: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setError("");
    if (form.password !== form.confirmation) { setError("Passwords do not match."); return; }
    setBusy(true);
    try {
      const result = await api.signup(form.username, form.name, form.email, form.password);
      onSignup(result.user);
    } catch (requestError) { setError(requestError.message); } finally { setBusy(false); }
  }
  return <main className="login-shell"><section className="login-card"><div className="brand"><span className="brand-mark">S</span><div><strong>Sovereign AI</strong><small>Private local intelligence</small></div></div><p className="eyebrow">CREATE ACCOUNT</p><h1>Set up your local workspace.</h1><p className="muted">Your account and preferences stay in the local backend database.</p><ErrorNotice error={error} /><form className="login-form" onSubmit={submit}><label>Display name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} autoComplete="name" required /></label><label>Email<input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoComplete="email" required /></label><label>Username<input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} autoComplete="username" required /></label><label>Password<input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="new-password" minLength="8" required /></label><label>Confirm password<input type="password" value={form.confirmation} onChange={(e) => setForm({ ...form, confirmation: e.target.value })} autoComplete="new-password" required /></label><button className="primary" disabled={busy}>{busy ? "Creating account..." : "Create account"}</button></form><button className="text-button" style={{ marginTop: "1rem" }} onClick={onBack}>← Back</button></section></main>;
}

// ---------------------------------------------------------------------------
// SentryBadge
// ---------------------------------------------------------------------------

function SentryBadge() {
  const [status, setStatus] = useState(null);
  useEffect(() => {
    api.sentry().then(setStatus).catch(() => setStatus(null));
  }, []);

  if (!status)
    return <span className="muted">Unavailable</span>;
  return (
    <div className={status.airgapped ? "secure" : "warning"}>
      <span>{status.airgapped ? "● Secure air-gapped" : "● External traffic detected"}</span>
      <small>{status.external_socket_count} external sockets</small>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ChatView
// ---------------------------------------------------------------------------

function ChatView({ settings, setSettings }) {
  const [sessionId, setSessionId] = useState(
    () => localStorage.getItem("sovereign-session") || ""
  );
  const [messages, setMessages] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [file, setFile] = useState(null);
  const [models, setModels] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const abortRef = useRef(null);

  async function loadSession(id) {
    if (!id) return;
    try {
      const [history, artifactData] = await Promise.all([
        api.history(id),
        api.artifacts(id),
      ]);
      setMessages(
        (history.history || []).filter((item) =>
          ["user", "assistant"].includes(item.role)
        )
      );
      setArtifacts(artifactData.artifacts || []);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  useEffect(() => {
    api.models().then(setModels).catch((e) => setError(e.message));
    // Session hydration is an external API synchronization triggered by the session key.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (sessionId) loadSession(sessionId);
  }, [sessionId]);  

  async function newSession() {
    try {
      const result = await api.newSession();
      setSessionId(result.session_id);
      localStorage.setItem("sovereign-session", result.session_id);
      setMessages([]);
      setArtifacts([]);
      setFile(null);
      setError("");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function sendMessage(event) {
    event.preventDefault();
    if (!prompt.trim() || busy) return;
    const userPrompt = prompt.trim();
    const userMessage = { role: "user", content: userPrompt };
    setMessages((current) => [...current, userMessage]);
    setPrompt("");
    setBusy(true);
    setError("");
    abortRef.current = new AbortController();
    try {
      const result = await api.chat({
        ...settings,
        prompt: userPrompt,
        sessionId,
        file,
        signal: abortRef.current.signal,
      });
      const returnedSession = result.session_id || sessionId;
      setSessionId(returnedSession);
      localStorage.setItem("sovereign-session", returnedSession);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: result.final_output || "Task completed successfully.",
          selectedModel: result.selected_model,
          generatedCode: result.generated_code,
          toolResult: result.tool_result,
        },
      ]);
      setArtifacts(result.artifacts || []);
      setFile(null);
    } catch (requestError) {
      if (requestError.name !== "AbortError") setError(requestError.message);
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  return (
    <div className="workspace-grid">
      <aside className="sidebar panel">
        <div className="brand">
          <span className="brand-mark">S</span>
          <div>
            <strong>Sovereign AI</strong>
            <small>Local workbench</small>
          </div>
        </div>
        <button className="primary full" onClick={newSession}>
          + New session
        </button>
        <div className="session-label">
          Current session <code>{sessionId || "Not started"}</code>
        </div>
        <section className="control-group">
          <h3>Model routing</h3>
          <select
            value={settings.modelId}
            onChange={(e) => setSettings({ ...settings, modelId: e.target.value })}
          >
            <option value="auto">Auto-detect</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.id}
              </option>
            ))}
          </select>
          <label>
            Temperature <output>{settings.temperature}</output>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={settings.temperature}
              onChange={(e) => setSettings({ ...settings, temperature: e.target.value })}
            />
          </label>
          <label>
            Context window <output>{settings.numCtx}</output>
            <input
              type="range"
              min="2048"
              max="32768"
              step="1024"
              value={settings.numCtx}
              onChange={(e) => setSettings({ ...settings, numCtx: e.target.value })}
            />
          </label>
          <label>
            System prompt
            <textarea
              value={settings.systemPrompt}
              onChange={(e) => setSettings({ ...settings, systemPrompt: e.target.value })}
              placeholder="Optional instruction"
            />
          </label>
        </section>
        <section className="control-group sentry-mini">
          <h3>Network sentry</h3>
          <SentryBadge />
        </section>
      </aside>

      <main className="chat panel">
        <header className="page-header">
          <div>
            <p className="eyebrow">PRIVATE COMPUTE / CHAT</p>
            <h1>Ask your local intelligence.</h1>
            <p className="muted">
              Documents, code, and generated work stay inside your workbench.
            </p>
          </div>
          <span className="status-dot">Backend connected</span>
        </header>
        <ErrorNotice error={error} />
        <div className="message-list">
          {!messages.length && (
            <div className="empty-state">
              <div className="empty-icon">✦</div>
              <h2>Start a local session</h2>
              <p>Ask a question, upload a document, or request a Word, PowerPoint, or CSV artifact.</p>
            </div>
          )}
          {messages.map((message, index) => (
            <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
              <div className="message-role">{message.role === "user" ? "You" : "Sovereign AI"}</div>
              <div className="message-content">{message.content}</div>
              {message.selectedModel && (
                <small className="model-chip">{message.selectedModel}</small>
              )}
              {message.generatedCode && (
                <details>
                  <summary>Generated code</summary>
                  <pre>{message.generatedCode}</pre>
                </details>
              )}
              {message.toolResult && (
                <details>
                  <summary>Tool execution</summary>
                  <pre>{JSON.stringify(message.toolResult, null, 2)}</pre>
                </details>
              )}
            </article>
          ))}
          {busy && (
            <div className="message assistant pending">
              <div className="message-role">Sovereign AI</div>
              <div className="loader">Processing locally...</div>
            </div>
          )}
        </div>

        <form className="composer" onSubmit={sendMessage}>
          <div className="attachment-row">
            {file ? (
              <span className="file-pill">
                {file.name}
                <button type="button" onClick={() => setFile(null)} aria-label="Remove file">
                  ×
                </button>
              </span>
            ) : (
              <label className="attach-button">
                Attach file
                <input
                  type="file"
                  accept=".txt,.pdf,.png,.jpg,.jpeg,.csv,.docx"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
              </label>
            )}
            {busy && (
              <button
                type="button"
                className="text-button"
                onClick={() => abortRef.current?.abort()}
              >
                Cancel request
              </button>
            )}
          </div>
          <div className="compose-line">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ask Sovereign AI anything..."
              rows="2"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage(e);
                }
              }}
            />
            <button
              className="send-button"
              disabled={busy || !prompt.trim()}
              aria-label="Send message"
            >
              ↑
            </button>
          </div>
        </form>

        {!!artifacts.length && (
          <section className="artifacts">
            <div className="section-heading">
              <h2>Generated artifacts</h2>
              <span>{artifacts.length} files</span>
            </div>
            {artifacts.map((artifact) => (
              <div className="artifact" key={`${artifact.id}-${artifact.file_name}`}>
                <div>
                  <strong>{artifact.file_name}</strong>
                  <small>{artifact.file_type}</small>
                </div>
                <a
                  className="secondary"
                  href={api.downloadUrl(sessionId, artifact.file_name)}
                >
                  Download
                </a>
              </div>
            ))}
          </section>
        )}
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ModelHub
// ---------------------------------------------------------------------------

function ModelHub() {
  const [models, setModels] = useState([]);
  const [downloaded, setDownloaded] = useState([]);
  const [results, setResults] = useState([]);
  const [files, setFiles] = useState({});
  const [query, setQuery] = useState("Qwen");
  const [token, setToken] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = () =>
    Promise.all([api.models(), api.downloadedModels()])
      .then(([active, disk]) => {
        setModels(active);
        setDownloaded(disk);
      })
      .catch((error) => setNotice(error.message));

  useEffect(() => {
    refresh();
  }, []);  

  async function search() {
    setLoading(true);
    setNotice("");
    try {
      setResults(await api.searchModels(query, token));
    } catch (error) {
      setNotice(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function toggleFiles(repoId) {
    try {
      setFiles({ ...files, [repoId]: await api.modelFiles(repoId, token) });
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function startDownload(repoId, filename) {
    try {
      const result = await api.startDownload(repoId, filename, token);
      setNotice(`Download started: ${result.download_id}`);
    } catch (error) {
      setNotice(error.message);
    }
  }

  async function action(fn, message) {
    try {
      await fn();
      setNotice(message);
      refresh();
    } catch (error) {
      setNotice(error.message);
    }
  }

  return (
    <div className="page panel">
      <header className="page-header">
        <div>
          <p className="eyebrow">MODEL HUB</p>
          <h1>Manage local intelligence.</h1>
          <p className="muted">
            Search Hugging Face metadata, download weights, and inspect active engines.
          </p>
        </div>
        <button className="secondary" onClick={refresh}>
          Refresh
        </button>
      </header>
      <ErrorNotice error={notice} />
      <section className="hub-section">
        <div className="search-line">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search models"
          />
          <button className="primary" onClick={search} disabled={loading}>
            Search hub
          </button>
        </div>
        <input
          value={token}
          onChange={(e) => setToken(e.target.value)}
          type="password"
          placeholder="Optional Hugging Face token"
        />
      </section>
      <div className="cards">
        {results.map((model) => (
          <article className="model-card" key={model.id}>
            <strong>{model.id}</strong>
            <small>
              {(model.downloads || 0).toLocaleString()} downloads · {model.likes || 0} likes ·{" "}
              {model.pipeline_tag || "model"}
            </small>
            <button className="secondary" onClick={() => toggleFiles(model.id)}>
              {files[model.id] ? "Hide files" : "View files"}
            </button>
            {files[model.id] && (
              <div className="file-list">
                {files[model.id].map((filename) => (
                  <div key={filename}>
                    <code>{filename}</code>
                    <button onClick={() => startDownload(model.id, filename)}>Download</button>
                  </div>
                ))}
              </div>
            )}
          </article>
        ))}
      </div>
      <section className="hub-section">
        <div className="section-heading">
          <h2>Active inference engines</h2>
          <span>{models.length} ready</span>
        </div>
        {models.map((model) => (
          <div className="list-row" key={model.id}>
            <strong>{model.id}</strong>
            <span>
              {model.provider} · {model.size}
            </span>
            <b>Ready</b>
          </div>
        ))}
      </section>
      <section className="hub-section">
        <div className="section-heading">
          <h2>Downloaded weights</h2>
          <span>{downloaded.length} files</span>
        </div>
        {downloaded.map((model) => (
          <div className="list-row" key={model.filename}>
            <strong>{model.filename}</strong>
            <span>
              {model.type} · {model.size}
            </span>
            <button
              onClick={() =>
                action(
                  () => api.loadModel(model.filename),
                  `${model.filename} loaded into Ollama`
                )
              }
            >
              Load
            </button>
          </div>
        ))}
      </section>
      <section className="hub-section">
        <h2>Quick pull</h2>
        <div className="popular-grid">
          {popularModels.map(([name, description]) => (
            <button
              className="model-card pull"
              key={name}
              onClick={() => action(() => api.pullModel(name), `${name} pulled successfully`)}
            >
              <strong>{name}</strong>
              <small>{description}</small>
              <span>Pull model →</span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

function Projects() {
  const [projects, setProjects] = useState([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

  const refresh = () =>
    api.projects().then(setProjects).catch((e) => setError(e.message));

  useEffect(() => {
    refresh();
  }, []);  

  async function create(event) {
    event.preventDefault();
    try {
      await api.createProject(name, description);
      setName("");
      setDescription("");
      refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="page panel">
      <header className="page-header">
        <div>
          <p className="eyebrow">PROJECTS</p>
          <h1>Organize your work.</h1>
          <p className="muted">Keep sessions and tasks grouped for your team.</p>
        </div>
      </header>
      <ErrorNotice error={error} />
      <form className="project-form" onSubmit={create}>
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Project name"
        />
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description"
        />
        <button className="primary">Create project</button>
      </form>
      <section className="hub-section">
        <div className="section-heading">
          <h2>Active projects</h2>
          <span>{projects.length}</span>
        </div>
        {projects.length ? (
          projects.map((project) => (
            <article className="project-row" key={project.id}>
              <strong>{project.name}</strong>
              <small>{project.created_at?.slice(0, 10)}</small>
              <p>{project.description}</p>
            </article>
          ))
        ) : (
          <div className="empty-state compact">No projects created yet.</div>
        )}
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Status
// ---------------------------------------------------------------------------

function SettingsPage({ onSettingsSaved }) {
  const [models, setModels] = useState([]);
  const [form, setForm] = useState(null);
  const [passwords, setPasswords] = useState({ currentPassword: "", newPassword: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    Promise.all([api.userSettings(), api.models()])
      .then(([settings, availableModels]) => {
        setForm(settings);
        setModels(availableModels);
        document.documentElement.dataset.theme = settings.theme;
      })
      .catch((requestError) => setError(requestError.message))
      .finally(() => setBusy(false));
  }, []);

  function update(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function saveSettings(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      const saved = await api.updateUserSettings({
        name: form.name,
        theme: form.theme,
        default_model: form.default_model,
        default_temperature: Number(form.default_temperature),
        default_num_ctx: Number(form.default_num_ctx),
        default_system_prompt: form.default_system_prompt,
        default_landing_page: form.default_landing_page,
        session_retention_days: Number(form.session_retention_days),
      });
      setForm(saved);
      document.documentElement.dataset.theme = saved.theme;
      onSettingsSaved(saved);
      setMessage("Settings saved.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      await api.changePassword(passwords.currentPassword, passwords.newPassword);
      setPasswords({ currentPassword: "", newPassword: "" });
      setMessage("Password changed. Your current session remains active.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  if (busy || !form) return <div className="page panel"><div className="loader">Loading settings...</div></div>;

  return <div className="page panel settings-page">
    <header className="page-header"><div><p className="eyebrow">SETTINGS</p><h1>Your local workspace.</h1><p className="muted">Preferences are stored in the backend database for your account.</p></div></header>
    {message && <div className="notice success">{message}</div>}
    <ErrorNotice error={error} />
    <form className="settings-form" onSubmit={saveSettings}>
      <section className="settings-section"><div><h2>Profile</h2><p className="muted">This name appears in the workbench header.</p></div><label>Display name<input value={form.name || ""} onChange={(event) => update("name", event.target.value)} required /></label></section>
      <section className="settings-section"><div><h2>Appearance</h2><p className="muted">Choose how the workbench looks on this account.</p></div><label>Theme<select value={form.theme} onChange={(event) => update("theme", event.target.value)}><option value="dark">Dark</option><option value="light">Light</option><option value="system">System</option></select></label></section>
      <section className="settings-section"><div><h2>Chat defaults</h2><p className="muted">These values are applied when a new workbench session opens.</p></div><label>Default model<select value={form.default_model} onChange={(event) => update("default_model", event.target.value)}><option value="auto">Auto-detect</option>{models.map((model) => <option key={model.id} value={model.id}>{model.id}</option>)}</select></label><label>Default temperature<output>{form.default_temperature}</output><input type="range" min="0" max="2" step="0.1" value={form.default_temperature} onChange={(event) => update("default_temperature", event.target.value)} /></label><label>Default context window<output>{form.default_num_ctx}</output><input type="range" min="2048" max="32768" step="1024" value={form.default_num_ctx} onChange={(event) => update("default_num_ctx", event.target.value)} /></label><label>Default system prompt<textarea value={form.default_system_prompt || ""} onChange={(event) => update("default_system_prompt", event.target.value)} /></label></section>
      <section className="settings-section"><div><h2>Workspace</h2><p className="muted">Choose where you return after signing in and how long sessions are retained.</p></div><label>Default landing page<select value={form.default_landing_page} onChange={(event) => update("default_landing_page", event.target.value)}><option value="chat">Workbench</option><option value="models">Model Hub</option><option value="projects">Projects</option><option value="status">System Status</option><option value="settings">Settings</option></select></label><label>Session retention (days)<input type="number" min="1" max="3650" value={form.session_retention_days} onChange={(event) => update("session_retention_days", event.target.value)} /></label></section>
      <button className="primary" type="submit">Save settings</button>
    </form>
    <form className="settings-section password-section" onSubmit={changePassword}><div><h2>Change password</h2><p className="muted">Your new password is hashed by the backend and never returned to the browser.</p></div><label>Current password<input type="password" autoComplete="current-password" value={passwords.currentPassword} onChange={(event) => setPasswords({ ...passwords, currentPassword: event.target.value })} required /></label><label>New password<input type="password" autoComplete="new-password" minLength="8" value={passwords.newPassword} onChange={(event) => setPasswords({ ...passwords, newPassword: event.target.value })} required /></label><button className="secondary" type="submit">Change password</button></form>
  </div>;
}

function Status() {
  const [gpu, setGpu] = useState(null);
  const [models, setModels] = useState([]);

  useEffect(() => {
    Promise.all([api.gpu(), api.models()]).then(([gpuData, modelData]) => {
      setGpu(gpuData);
      setModels(modelData);
    });
  }, []);

  return (
    <div className="page panel">
      <header className="page-header">
        <div>
          <p className="eyebrow">SYSTEM STATUS</p>
          <h1>Know what is running.</h1>
          <p className="muted">Local hardware, inference engines, and air-gap telemetry.</p>
        </div>
      </header>
      <div className="status-grid">
        <section className="status-card">
          <h2>GPU status</h2>
          {gpu?.available ? (
            gpu.devices.map((device) => (
              <div className="gpu" key={device.index}>
                <strong>{device.name}</strong>
                <span>
                  {(device.used_bytes / 1073741824).toFixed(2)} GB /{" "}
                  {(device.total_bytes / 1073741824).toFixed(2)} GB
                </span>
                <progress value={device.usage_ratio} max="1" />
              </div>
            ))
          ) : (
            <p className="muted">No NVIDIA GPU detected or NVML is unavailable.</p>
          )}
        </section>
        <section className="status-card">
          <h2>Model engine</h2>
          <strong className="big-number">{models.length}</strong>
          <span className="muted">loaded models</span>
          {models.map((model) => (
            <div className="list-row" key={model.id}>
              <span>{model.id}</span>
              <small>{model.provider}</small>
            </div>
          ))}
        </section>
      </div>
      <section className="status-card">
        <h2>Network sentry</h2>
        <SentryBadge />
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root App — auth state machine
// ---------------------------------------------------------------------------

export default function App() {
  const [page, setPage] = useState("chat");
  const [settings, setSettings] = useState({
    modelId: "auto",
    temperature: 0,
    numCtx: 8192,
    systemPrompt: "",
  });
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  // "welcome" | "login" | "app"
  const [authScreen, setAuthScreen] = useState("welcome");

  // On mount: check if there is already a valid server session cookie
  useEffect(() => {
    api
      .authMe()
      .then((result) => {
        if (result.user) {
          setUser(result.user);
          setAuthScreen("app");
        } else {
          setAuthScreen("welcome");
        }
      })
      .catch(() => {
        setAuthScreen("welcome");
      })
      .finally(() => setAuthLoading(false));

    // If ANY protected endpoint returns 401 while the user is mid-session
    // (genuine cookie expiry), send them to the login page — NOT the welcome page.
    const handleExpired = () => {
      localStorage.removeItem("sovereign-session");
      setUser(null);
      setAuthScreen("login");
    };
    window.addEventListener("sovereign-auth-expired", handleExpired);
    return () => window.removeEventListener("sovereign-auth-expired", handleExpired);
  }, []);

  useEffect(() => {
    if (!user) return;
    api.userSettings().then((saved) => {
      setSettings({
        modelId: saved.default_model,
        temperature: saved.default_temperature,
        numCtx: saved.default_num_ctx,
        systemPrompt: saved.default_system_prompt,
      });
      setPage(saved.default_landing_page || "chat");
      document.documentElement.dataset.theme = saved.theme || "dark";
    }).catch(() => {});
  }, [user]);

  // ── Auth loading splash ────────────────────────────────────────────────────
  if (authLoading) {
    return (
      <main className="login-shell">
        <div className="loader">Checking secure session…</div>
      </main>
    );
  }

  // ── Welcome screen ─────────────────────────────────────────────────────────
  if (authScreen === "welcome") {
    return <WelcomePage onContinue={() => setAuthScreen("login")} onSignup={() => setAuthScreen("signup")} />;
  }

  // ── Login screen ───────────────────────────────────────────────────────────
  if (authScreen === "login") {
    return (
      <LoginPage
        onLogin={(nextUser) => {
          // Clear any leftover chat session from a previous user
          localStorage.removeItem("sovereign-session");
          setUser(nextUser);
          setAuthScreen("app");
        }}
        onBack={() => setAuthScreen("welcome")}
      />
    );
  }

  if (authScreen === "signup") {
    return <SignupPage onSignup={(nextUser) => { localStorage.removeItem("sovereign-session"); setUser(nextUser); setAuthScreen("app"); }} onBack={() => setAuthScreen("welcome")} />;
  }

  // ── Authenticated app shell ────────────────────────────────────────────────
  async function logout() {
    try {
      await api.logout();
    } catch {
      // ignore — clear client state regardless
    }
    localStorage.removeItem("sovereign-session");
    setUser(null);
    setAuthScreen("welcome");
  }

  return (
    <div className="app-shell">
      <nav className="topbar">
        <div className="brand">
          <span className="brand-mark">S</span>
          <div>
            <strong>Sovereign AI</strong>
            <small>Air-gapped workbench</small>
          </div>
        </div>
        <div className="nav-links">
          {[
            ["chat", "Workbench"],
            ["models", "Model hub"],
            ["projects", "Projects"],
            ["status", "System status"],
            ["settings", "Settings"],
          ].map(([id, label]) => (
            <button
              className={page === id ? "active" : ""}
              key={id}
              onClick={() => setPage(id)}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="user-menu">
          <span>{user.name || user.username}</span>
          <button onClick={logout}>Sign out</button>
        </div>
      </nav>

      {page === "chat" && <ChatView settings={settings} setSettings={setSettings} />}
      {page === "models" && <ModelHub />}
      {page === "projects" && <Projects />}
      {page === "status" && <Status />}
      {page === "settings" && <SettingsPage onSettingsSaved={(saved) => {
        setSettings({
          modelId: saved.default_model,
          temperature: saved.default_temperature,
          numCtx: saved.default_num_ctx,
          systemPrompt: saved.default_system_prompt,
        });
      }} />}

      <footer>All processing is routed through your configured local backend.</footer>
    </div>
  );
}
