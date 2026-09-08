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
  const [form, setForm] = useState({
    username: "", name: "", email: "", password: "", confirmation: "",
  });
  const [error, setError]   = useState("");
  const [busy,  setBusy]    = useState(false);

  function field(key) {
    return (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    if (form.password !== form.confirmation) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const result = await api.signup(form.username, form.name, form.email, form.password);
      onSignup(result.user);
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

        <p className="eyebrow">CREATE ACCOUNT</p>
        <h1>Set up your local workspace.</h1>
        <p className="muted">
          Your account and preferences are stored in the local backend database — nothing leaves
          this machine.
        </p>

        <ErrorNotice error={error} />

        <form className="login-form" onSubmit={submit}>
          <label>
            Display name
            <input
              value={form.name}
              onChange={field("name")}
              autoComplete="name"
              autoFocus
              placeholder="e.g. Aanya"
              required
            />
          </label>
          <label>
            Email
            <input
              type="email"
              value={form.email}
              onChange={field("email")}
              autoComplete="email"
              placeholder="you@example.com"
              required
            />
          </label>
          <label>
            Username
            <input
              value={form.username}
              onChange={field("username")}
              autoComplete="username"
              placeholder="letters, numbers, underscores (min 3)"
              minLength={3}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={form.password}
              onChange={field("password")}
              autoComplete="new-password"
              placeholder="At least 8 characters"
              minLength={8}
              required
            />
          </label>
          <label>
            Confirm password
            <input
              type="password"
              value={form.confirmation}
              onChange={field("confirmation")}
              autoComplete="new-password"
              required
            />
          </label>
          <button className="primary" disabled={busy}>
            {busy ? "Creating account…" : "Create account"}
          </button>
        </form>

        <button className="text-button" style={{ marginTop: "1rem" }} onClick={onBack}>
          ← Already have an account? Sign in
        </button>
      </section>
    </main>
  );
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
// AirgapCertificateModal & AirgapLedgerBadge
// ---------------------------------------------------------------------------

function AirgapCertificateModal({ sessionId, onClose }) {
  const [cert, setCert] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sessionId) return;
    api
      .airgapCertificate(sessionId)
      .then(setCert)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [sessionId]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="cert-header">
          <div>
            <p className="eyebrow">TAMPER-EVIDENT CRYPTOGRAPHIC AUDIT</p>
            <h1 style={{ fontSize: 24, marginTop: 4 }}>Proof of Air-Gap Compliance Certificate</h1>
            <small style={{ color: "var(--muted)" }}>
              Session ID: <code>{sessionId}</code>
            </small>
          </div>
          <button className="text-button" style={{ fontSize: 20 }} onClick={onClose}>
            ×
          </button>
        </div>

        {loading && <div className="loader">Verifying Merkle hash chain…</div>}
        {error && <div className="notice error">{error}</div>}

        {cert && (
          <div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
              <span
                className={`badge-status ${
                  cert.compliance_status === "VERIFIED_COMPLIANT"
                    ? "badge-completed"
                    : "badge-error"
                }`}
                style={{ fontSize: 13, padding: "6px 14px" }}
              >
                ● {cert.compliance_status === "VERIFIED_COMPLIANT" ? "VERIFIED AIR-GAPPED (ZERO LEAKS)" : cert.compliance_status}
              </span>
              <span className="tag-chip accent">Tamper Check: {cert.tamper_check_passed ? "PASSED" : "FAILED"}</span>
            </div>

            <div className="cert-grid">
              <div className="cert-metric">
                <small>Certificate ID</small>
                <code>{cert.certificate_id}</code>
              </div>
              <div className="cert-metric">
                <small>Audit Blocks Verified</small>
                <strong>{cert.total_events_verified} Chained Events</strong>
              </div>
              <div className="cert-metric">
                <small>External Sockets Leaked</small>
                <strong style={{ color: cert.external_socket_leaks_detected === 0 ? "var(--accent)" : "var(--orange)" }}>
                  {cert.external_socket_leaks_detected} sockets
                </strong>
              </div>
              <div className="cert-metric">
                <small>Timestamp Generated</small>
                <span style={{ fontSize: 12 }}>{new Date(cert.generated_at).toLocaleString()}</span>
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <small style={{ color: "var(--muted)", textTransform: "uppercase", fontSize: 11 }}>
                Merkle Root Hash (SHA-256)
              </small>
              <div className="cert-hash-box">{cert.merkle_root_hash}</div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <small style={{ color: "var(--muted)", textTransform: "uppercase", fontSize: 11 }}>
                Local Authority Digital Signature (HMAC-SHA256)
              </small>
              <div className="cert-hash-box">{cert.digital_signature_hmac}</div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <div className="section-heading" style={{ marginBottom: 8 }}>
                <h2>Chained Event Ledger</h2>
                <span>{cert.audit_trail?.length || 0} blocks</span>
              </div>
              <div className="audit-list">
                {(cert.audit_trail || []).map((b) => (
                  <div className="audit-item" key={b.index}>
                    <div>
                      <strong>#{b.index} [{b.event_type}]</strong>
                      <div style={{ fontSize: 11, color: "var(--muted)" }}>
                        Hash: <code>{b.block_hash.slice(0, 16)}…</code> · Sockets: {b.network_snapshot?.external_socket_count || 0}
                      </div>
                    </div>
                    <span style={{ fontSize: 11, color: "var(--muted)" }}>
                      {new Date(b.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <a
                className="primary"
                href={api.downloadAirgapCertificateUrl(sessionId)}
                download={`AirGap_Certificate_${sessionId.slice(0, 8)}.json`}
                style={{ textDecoration: "none", display: "inline-block", fontSize: 13, padding: "8px 16px" }}
              >
                Download Signed Certificate (.json) ↓
              </a>
              <button className="secondary" onClick={onClose}>
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AirgapLedgerBadge({ sessionId, refreshTrigger }) {
  const [certSummary, setCertSummary] = useState(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    api
      .airgapCertificate(sessionId)
      .then(setCertSummary)
      .catch(() => setCertSummary(null));
  }, [sessionId, refreshTrigger]);

  return (
    <>
      <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--line)" }}>
        <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 4 }}>CRYPTOGRAPHIC AUDIT</div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 6 }}>
          <span style={{ fontSize: 12, color: certSummary?.airgap_preserved ? "var(--accent)" : "var(--orange)" }}>
            ● {certSummary ? `${certSummary.total_events_verified} Chained Events` : "Tracking Active"}
          </span>
          <button
            className="text-button"
            style={{ fontSize: 11, textDecoration: "underline", color: "var(--ink)" }}
            onClick={() => setShowModal(true)}
          >
            Verify Proof →
          </button>
        </div>
      </div>

      {showModal && (
        <AirgapCertificateModal
          sessionId={sessionId}
          onClose={() => setShowModal(false)}
        />
      )}
    </>
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
  const [listening, setListening] = useState(false);
  const [speakingIndex, setSpeakingIndex] = useState(null);
  const abortRef = useRef(null);
  const recognitionRef = useRef(null);

  function toggleListen() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      alert("Speech recognition is not supported in this browser. Try Chrome, Edge, or a WebSpeech-enabled browser.");
      return;
    }

    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    try {
      const rec = new SpeechRec();
      rec.continuous = false;
      rec.interimResults = true;
      rec.lang = "en-US";

      rec.onstart = () => setListening(true);
      rec.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map((r) => r[0].transcript)
          .join("");
        setPrompt(transcript);
      };
      rec.onerror = () => setListening(false);
      rec.onend = () => setListening(false);

      recognitionRef.current = rec;
      rec.start();
    } catch {
      setListening(false);
    }
  }

  function toggleSpeak(text, index) {
    if (!window.speechSynthesis) return;

    if (speakingIndex === index) {
      window.speechSynthesis.cancel();
      setSpeakingIndex(null);
      return;
    }

    window.speechSynthesis.cancel();
    const cleanText = text
      .replace(/```[\s\S]*?```/g, "Code block omitted.")
      .replace(/[*_#`]/g, "");

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.05;
    utterance.onend = () => setSpeakingIndex(null);
    utterance.onerror = () => setSpeakingIndex(null);

    setSpeakingIndex(index);
    window.speechSynthesis.speak(utterance);
  }

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
          {sessionId && <AirgapLedgerBadge sessionId={sessionId} refreshTrigger={messages.length} />}
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
          <span className="status-dot">● Proof of Air-Gap Active</span>
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
              <div className="message-role" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span>{message.role === "user" ? "You" : "Sovereign AI"}</span>
                {message.role === "assistant" && (
                  <button
                    type="button"
                    className="text-button"
                    style={{ fontSize: 11, padding: 0 }}
                    onClick={() => toggleSpeak(message.content, index)}
                  >
                    {speakingIndex === index ? "⏹️ Stop speech" : "🔊 Read aloud"}
                  </button>
                )}
              </div>
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
          {listening && (
            <div className="voice-banner">
              <span>● Tactical Voice Active: Listening… (Speak your question, click mic to finish)</span>
            </div>
          )}
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
              type="button"
              className={`mic-button ${listening ? "listening" : ""}`}
              onClick={toggleListen}
              title={listening ? "Stop listening" : "Tactical Voice Dictation (Push-to-Talk)"}
              aria-label="Dictate prompt"
            >
              {listening ? "⏹" : "🎙️"}
            </button>
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

function ModelHub({ user }) {
  const role = user?.role || "analyst";
  const isAdmin = role === "admin";
  const isAuditor = role === "auditor";
  const [tab, setTab] = useState("engines"); // "engines" | "weights" | "hf" | "quick"
  const [models, setModels] = useState([]);
  const [downloaded, setDownloaded] = useState([]);
  const [results, setResults] = useState([]);
  const [files, setFiles] = useState({});
  const [query, setQuery] = useState("Qwen");
  const [token, setToken] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingModel, setLoadingModel] = useState({});
  const [pullingModel, setPullingModel] = useState({});
  const [activeDownloads, setActiveDownloads] = useState({});

  const refresh = () =>
    Promise.all([api.models(), api.downloadedModels()])
      .then(([active, disk]) => {
        setModels(active);
        setDownloaded(disk);
      })
      .catch((err) => setError(err.message));

  useEffect(() => {
    refresh();
  }, []);

  // Poll active downloads every 1.5 seconds while any download is running
  useEffect(() => {
    const hasRunning = Object.values(activeDownloads).some(
      (d) => d.status === "downloading"
    );
    if (!hasRunning) return;

    const interval = setInterval(async () => {
      const runningIds = Object.keys(activeDownloads).filter(
        (id) => activeDownloads[id].status === "downloading"
      );

      for (const id of runningIds) {
        try {
          const status = await api.downloadProgress(id);
          if (!status || status.status === "not_found") continue;

          setActiveDownloads((prev) => ({
            ...prev,
            [id]: { ...prev[id], ...status },
          }));

          if (status.status === "completed") {
            refresh();
          }
        } catch {
          // ignore transient polling errors
        }
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeDownloads]);

  async function search() {
    if (!query.trim()) return;
    setLoading(true);
    setNotice("");
    setError("");
    try {
      const res = await api.searchModels(query.trim(), token);
      if (res && res[0]?.error) {
        throw new Error(res[0].error);
      }
      setResults(res || []);
    } catch (err) {
      setError(`Search failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function toggleFiles(repoId) {
    if (files[repoId]) {
      setFiles((prev) => {
        const next = { ...prev };
        delete next[repoId];
        return next;
      });
      return;
    }
    try {
      const fileList = await api.modelFiles(repoId, token);
      setFiles((prev) => ({ ...prev, [repoId]: fileList }));
    } catch (err) {
      setError(`Failed to list files for ${repoId}: ${err.message}`);
    }
  }

  async function startDownload(repoId, filename) {
    setError("");
    setNotice("");
    try {
      const result = await api.startDownload(repoId, filename, token);
      const dlId = result.download_id;
      setActiveDownloads((prev) => ({
        ...prev,
        [dlId]: {
          id: dlId,
          repo: repoId,
          file: filename,
          status: "downloading",
          progress: 0,
          downloaded_mb: "0.0 MB",
          total_mb: "Calculating...",
        },
      }));
      setNotice(`Started download: ${filename}`);
      setTab("hf"); // Switch to HF tab to view download progress
    } catch (err) {
      setError(`Download failed to start: ${err.message}`);
    }
  }

  async function cancelDownload(dlId) {
    try {
      await api.cancelDownload(dlId);
      setActiveDownloads((prev) => ({
        ...prev,
        [dlId]: { ...prev[dlId], status: "cancelled" },
      }));
      setNotice("Download cancelled.");
      refresh();
    } catch (err) {
      setError(`Cancel failed: ${err.message}`);
    }
  }

  async function loadWeight(filename) {
    const ext = filename.split(".").pop().toLowerCase();
    if (ext !== "gguf") {
      setError(`Cannot load "${filename}": Only GGUF files can be directly converted into Ollama engines. Safetensors weights require vLLM.`);
      return;
    }

    setLoadingModel((prev) => ({ ...prev, [filename]: true }));
    setError("");
    setNotice("");
    try {
      const res = await api.loadModel(filename);
      setNotice(`Successfully imported ${filename} into Ollama as '${res.model_id}'! You can now select it in Chat.`);
      refresh();
      setTab("engines");
    } catch (err) {
      setError(`Failed to load ${filename}: ${err.message}`);
    } finally {
      setLoadingModel((prev) => ({ ...prev, [filename]: false }));
    }
  }

  async function deleteOllama(modelId) {
    if (!window.confirm(`Are you sure you want to delete Ollama engine '${modelId}'?`)) return;
    setError("");
    setNotice("");
    try {
      await api.deleteOllamaModel(modelId);
      setNotice(`Model '${modelId}' successfully deleted from Ollama.`);
      refresh();
    } catch (err) {
      setError(`Failed to delete '${modelId}': ${err.message}`);
    }
  }

  async function deleteDownloaded(filename) {
    if (!window.confirm(`Are you sure you want to delete file '${filename}' from local storage?`)) return;
    setError("");
    setNotice("");
    try {
      await api.deleteDownloadedModel(filename);
      setNotice(`File '${filename}' deleted from local storage.`);
      refresh();
    } catch (err) {
      setError(`Failed to delete '${filename}': ${err.message}`);
    }
  }

  async function pullQuick(name) {
    setPullingModel((prev) => ({ ...prev, [name]: true }));
    setError("");
    setNotice("");
    try {
      await api.pullModel(name);
      setNotice(`Model '${name}' pulled and registered in Ollama!`);
      refresh();
      setTab("engines");
    } catch (err) {
      setError(`Pull failed for ${name}: ${err.message}`);
    } finally {
      setPullingModel((prev) => ({ ...prev, [name]: false }));
    }
  }

  const downloadsList = Object.values(activeDownloads);

  return (
    <div className="page panel">
      <header className="page-header">
        <div>
          <p className="eyebrow">MODEL HUB</p>
          <h1>Manage local intelligence.</h1>
          <p className="muted">
            Configure local inference engines, manage downloaded weight files, and discover models from Hugging Face.
          </p>
        </div>
        <button className="secondary" onClick={refresh}>
          Refresh
        </button>
      </header>

      {notice && <div className="notice success">{notice}</div>}
      <ErrorNotice error={error} />

      {isAuditor && (
        <div className="notice" style={{ border: "1px solid #315380", background: "rgba(109, 182, 255, 0.1)", color: "#6db6ff" }}>
          <strong>Auditor Access Mode:</strong> You have read-only compliance permissions. Model downloading, pulling, and deletion are restricted to administrators and analysts.
        </div>
      )}

      {/* Sub-tabs to clearly separate different model behaviors */}
      <nav className="hub-tabs">
        <button
          className={`hub-tab ${tab === "engines" ? "active" : ""}`}
          onClick={() => setTab("engines")}
        >
          Inference Engines ({models.length})
        </button>
        <button
          className={`hub-tab ${tab === "weights" ? "active" : ""}`}
          onClick={() => setTab("weights")}
        >
          Downloaded Weights ({downloaded.length})
        </button>
        <button
          className={`hub-tab ${tab === "hf" ? "active" : ""}`}
          onClick={() => setTab("hf")}
        >
          Hugging Face Hub {downloadsList.length > 0 && `(${downloadsList.length} DL)`}
        </button>
        <button
          className={`hub-tab ${tab === "quick" ? "active" : ""}`}
          onClick={() => setTab("quick")}
        >
          Quick Pull
        </button>
      </nav>

      {/* ── Active Downloads Banner (Visible on all tabs if any download is active) ── */}
      {downloadsList.length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <div className="section-heading">
            <h2>Active & Recent Downloads</h2>
            <span>{downloadsList.length} tasks</span>
          </div>
          {downloadsList.map((dl) => (
            <div className="download-card" key={dl.id}>
              <div className="download-card-header">
                <div>
                  <strong>{dl.file || dl.id}</strong>
                  <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                    From: <code>{dl.repo}</code>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className={`badge-status badge-${dl.status}`}>
                    {dl.status === "downloading" ? "Downloading…" : dl.status}
                  </span>
                  {dl.status === "downloading" && (
                    <button
                      className="text-button"
                      style={{ fontSize: 12, color: "var(--orange)" }}
                      onClick={() => cancelDownload(dl.id)}
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </div>

              {dl.status === "downloading" && (
                <>
                  <div className="download-progress-bar">
                    <div
                      className="download-progress-fill"
                      style={{ width: `${dl.progress || 0}%` }}
                    />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--muted)" }}>
                    <span>{dl.downloaded_mb || "0 MB"} / {dl.total_mb || "Unknown"}</span>
                    <span>{dl.progress || 0}%</span>
                  </div>
                </>
              )}

              {dl.status === "error" && (
                <div className="notice error" style={{ margin: 0, padding: "8px 12px", fontSize: 12 }}>
                  Download error: {dl.error || "Connection terminated or repository unavailable."}
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {/* ── TAB 1: INFERENCE ENGINES (Ollama / vLLM) ── */}
      {tab === "engines" && (
        <section className="hub-section" style={{ borderTop: 0, paddingTop: 0 }}>
          <div className="section-heading">
            <div>
              <h2>Ready Inference Engines</h2>
              <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                These models are loaded in your local inference runtime (Ollama) and ready for immediate chat, code generation, and reasoning.
              </p>
            </div>
            <span>{models.length} ready</span>
          </div>

          {models.length === 0 ? (
            <div className="empty-state compact">
              No inference engines currently loaded. Pull one from <strong>Quick Pull</strong> or import a downloaded GGUF file.
            </div>
          ) : (
            models.map((model) => (
              <div className="list-row" key={model.id} style={{ padding: "14px 0" }}>
                <div style={{ flex: 1, display: "grid", gap: 6 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                    <strong style={{ fontSize: 14 }}>{model.id}</strong>
                    <span className="tag-chip accent">Ready</span>
                    {model.family && <span className="tag-chip">{model.family}</span>}
                    {model.parameter_size && <span className="tag-chip">{model.parameter_size}</span>}
                    {model.quantization_level && <span className="tag-chip">{model.quantization_level}</span>}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--muted)" }}>
                    Provider: {model.provider} · Size on disk: {model.size}
                  </div>
                </div>

                {isAdmin && (
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <button
                      className="text-button"
                      style={{ color: "var(--orange)", fontSize: 12 }}
                      onClick={() => deleteOllama(model.id)}
                      title="Remove model from Ollama"
                    >
                      Delete engine
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </section>
      )}

      {/* ── TAB 2: DOWNLOADED WEIGHTS (Local GGUF / Safetensors) ── */}
      {tab === "weights" && (
        <section className="hub-section" style={{ borderTop: 0, paddingTop: 0 }}>
          <div className="section-heading">
            <div>
              <h2>Downloaded Weight Files</h2>
              <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                Raw model weight files stored in <code>models/downloads/</code>. GGUF format weights can be directly converted into Ollama engines.
              </p>
            </div>
            <span>{downloaded.length} files</span>
          </div>

          {downloaded.length === 0 ? (
            <div className="empty-state compact">
              No downloaded weights found in <code>models/downloads/</code>. Search Hugging Face to download weights.
            </div>
          ) : (
            downloaded.map((model) => {
              const isGguf = model.type === "GGUF" || model.filename.endsWith(".gguf");
              const isLoading = loadingModel[model.filename];

              return (
                <div className="list-row" key={model.filename} style={{ padding: "14px 0" }}>
                  <div style={{ flex: 1, display: "grid", gap: 6 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                      <strong style={{ fontSize: 13, wordBreak: "break-all" }}>{model.filename}</strong>
                      <span className={`tag-chip ${isGguf ? "accent" : "orange"}`}>
                        {model.type || (isGguf ? "GGUF" : "Safetensors")}
                      </span>
                      <span className="tag-chip">{model.size}</span>
                    </div>
                    {!isGguf && (
                      <div style={{ fontSize: 11, color: "var(--muted)" }}>
                        Notice: Safetensors require conversion or vLLM to run. Only GGUF can be imported directly to Ollama.
                      </div>
                    )}
                  </div>

                  <div style={{ display: "flex", gap: 10, alignItems: "center", flexShrink: 0 }}>
                    {isGguf && !isAuditor && (
                      <button
                        className="primary"
                        style={{ fontSize: 12, padding: "6px 12px" }}
                        disabled={isLoading}
                        onClick={() => loadWeight(model.filename)}
                      >
                        {isLoading ? "Importing to Ollama…" : "Import to Ollama →"}
                      </button>
                    )}
                    {isAdmin && (
                      <button
                        className="text-button"
                        style={{ color: "var(--orange)", fontSize: 12 }}
                        disabled={isLoading}
                        onClick={() => deleteDownloaded(model.filename)}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </section>
      )}

      {/* ── TAB 3: HUGGING FACE HUB DISCOVERY ── */}
      {tab === "hf" && (
        <section className="hub-section" style={{ borderTop: 0, paddingTop: 0 }}>
          <div className="section-heading">
            <div>
              <h2>Search Hugging Face Hub</h2>
              <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                Discover models, inspect repository files, and download GGUF quantizations directly to disk.
              </p>
            </div>
          </div>

          <div style={{ display: "grid", gap: 10, marginBottom: 20, maxWidth: 700 }}>
            <div className="search-line">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && search()}
                placeholder="Search Hugging Face models (e.g. Qwen2.5, Llama-3.2, Mistral)"
              />
              <button className="primary" onClick={search} disabled={loading}>
                {loading ? "Searching…" : "Search"}
              </button>
            </div>
            <input
              value={token}
              onChange={(e) => setToken(e.target.value)}
              type="password"
              placeholder="Optional Hugging Face Access Token (for gated or private models)"
            />
          </div>

          <div className="cards">
            {results.map((model) => (
              <article className="model-card" key={model.id}>
                <div style={{ display: "grid", gap: 4 }}>
                  <strong style={{ fontSize: 14 }}>{model.id}</strong>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                    <span className="tag-chip">{(model.downloads || 0).toLocaleString()} DLs</span>
                    <span className="tag-chip">❤️ {model.likes || 0}</span>
                    {model.pipeline_tag && <span className="tag-chip accent">{model.pipeline_tag}</span>}
                  </div>
                  {model.author && (
                    <small style={{ color: "var(--muted)", marginTop: 4 }}>
                      Author: {model.author}
                    </small>
                  )}
                </div>

                <button
                  className="secondary"
                  style={{ justifySelf: "start", fontSize: 12 }}
                  onClick={() => toggleFiles(model.id)}
                >
                  {files[model.id] ? "Hide weight files" : "Inspect weight files"}
                </button>

                {files[model.id] && (
                  <div className="file-list">
                    {files[model.id].length === 0 ? (
                      <small className="muted" style={{ padding: "6px 0" }}>
                        No .gguf or .safetensors files found in this repository.
                      </small>
                    ) : (
                      files[model.id].map((filename) => {
                        const dlId = `${model.id.replace('/', '_')}_${filename}`;
                        const isDownloading = activeDownloads[dlId]?.status === "downloading";

                        return (
                          <div key={filename} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                            <code style={{ fontSize: 11, wordBreak: "break-all" }}>{filename}</code>
                            <button
                              disabled={isDownloading}
                              onClick={() => startDownload(model.id, filename)}
                              style={{ flexShrink: 0 }}
                            >
                              {isDownloading ? "Downloading…" : "Download"}
                            </button>
                          </div>
                        );
                      })
                    )}
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      )}

      {/* ── TAB 4: QUICK PULL ── */}
      {tab === "quick" && (
        <section className="hub-section" style={{ borderTop: 0, paddingTop: 0 }}>
          <div className="section-heading">
            <div>
              <h2>Quick Pull Verified Models</h2>
              <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                One-click direct pull from Ollama's official library into your local runtime.
              </p>
            </div>
          </div>

          <div className="popular-grid">
            {popularModels.map(([name, description]) => {
              const isPulling = pullingModel[name];

              return (
                <div
                  className="model-card pull"
                  key={name}
                  style={{ cursor: isPulling ? "wait" : "pointer" }}
                  onClick={() => !isPulling && pullQuick(name)}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <strong style={{ fontSize: 15 }}>{name}</strong>
                    {isPulling && <span className="tag-chip orange">Pulling…</span>}
                  </div>
                  <small>{description}</small>
                  <span style={{ color: isPulling ? "var(--orange)" : "var(--accent)", marginTop: 8 }}>
                    {isPulling ? "Downloading weights from Ollama library…" : "Pull model →"}
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Projects — full CRUD + tasks + session linking
// ---------------------------------------------------------------------------

const TASK_STATUSES = ["todo", "in_progress", "done"];
const STATUS_LABEL  = { todo: "To do", in_progress: "In progress", done: "Done" };
const STATUS_COLOR  = { todo: "var(--muted)", in_progress: "var(--orange)", done: "var(--accent)" };

function TaskCard({ task, projectId, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle]     = useState(task.title);
  const [desc,  setDesc]      = useState(task.description || "");

  async function cycleStatus() {
    const next = TASK_STATUSES[(TASK_STATUSES.indexOf(task.status) + 1) % TASK_STATUSES.length];
    await onUpdate(task.id, { status: next });
  }

  async function saveEdit(e) {
    e.preventDefault();
    if (!title.trim()) return;
    await onUpdate(task.id, { title: title.trim(), description: desc });
    setEditing(false);
  }

  if (editing) {
    return (
      <form className="task-card editing" onSubmit={saveEdit}>
        <input value={title} onChange={e => setTitle(e.target.value)} required autoFocus />
        <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="Description (optional)" />
        <div style={{ display: "flex", gap: 8 }}>
          <button className="primary" type="submit" style={{ padding: "6px 12px", fontSize: 12 }}>Save</button>
          <button type="button" className="secondary" style={{ padding: "6px 12px", fontSize: 12 }} onClick={() => setEditing(false)}>Cancel</button>
        </div>
      </form>
    );
  }

  return (
    <div className="task-card">
      <div className="task-card-header">
        <strong>{task.title}</strong>
        <div className="task-actions">
          <button className="text-button" style={{ fontSize: 11 }} onClick={() => setEditing(true)}>Edit</button>
          <button className="text-button" style={{ fontSize: 11, color: "var(--muted)" }} onClick={() => onDelete(task.id)}>×</button>
        </div>
      </div>
      {task.description && <p className="task-desc">{task.description}</p>}
      <button
        className="task-status-badge"
        style={{ color: STATUS_COLOR[task.status] }}
        onClick={cycleStatus}
        title="Click to cycle status"
      >
        {STATUS_LABEL[task.status]} →
      </button>
    </div>
  );
}

function ProjectDetail({ project, allSessions, onBack, onChanged }) {
  const [tasks,      setTasks]      = useState(project.tasks    || []);
  const [sessions,   setSessions]   = useState(project.sessions || []);
  const [taskTitle,  setTaskTitle]  = useState("");
  const [taskDesc,   setTaskDesc]   = useState("");
  const [editMode,   setEditMode]   = useState(false);
  const [projName,   setProjName]   = useState(project.name);
  const [projDesc,   setProjDesc]   = useState(project.description || "");
  const [error,      setError]      = useState("");
  const [notice,     setNotice]     = useState("");

  const attached = new Set(sessions.map(s => s.session_id));

  async function addTask(e) {
    e.preventDefault();
    if (!taskTitle.trim()) return;
    try {
      const updated = await api.createTask(project.id, taskTitle.trim(), taskDesc);
      setTasks(updated);
      setTaskTitle(""); setTaskDesc("");
    } catch (err) { setError(err.message); }
  }

  async function handleUpdateTask(taskId, fields) {
    try {
      const updated = await api.updateTask(project.id, taskId, fields);
      setTasks(updated);
    } catch (err) { setError(err.message); }
  }

  async function handleDeleteTask(taskId) {
    try {
      await api.deleteTask(project.id, taskId);
      setTasks(t => t.filter(x => x.id !== taskId));
    } catch (err) { setError(err.message); }
  }

  async function saveProjectEdit(e) {
    e.preventDefault();
    try {
      await api.updateProject(project.id, projName.trim(), projDesc);
      setEditMode(false);
      setNotice("Project updated.");
      onChanged();
    } catch (err) { setError(err.message); }
  }

  async function toggleSession(sessionId) {
    try {
      if (attached.has(sessionId)) {
        await api.detachSession(project.id, sessionId);
        setSessions(s => s.filter(x => x.session_id !== sessionId));
      } else {
        await api.attachSession(project.id, sessionId);
        const freshProject = await api.getProject(project.id);
        setSessions(freshProject.sessions || []);
      }
    } catch (err) { setError(err.message); }
  }

  const byStatus = status => tasks.filter(t => t.status === status);

  return (
    <div className="project-detail">
      <button className="text-button" style={{ marginBottom: 18 }} onClick={onBack}>← All projects</button>

      {/* Project header */}
      {editMode ? (
        <form onSubmit={saveProjectEdit} style={{ marginBottom: 24, display: "grid", gap: 10, maxWidth: 600 }}>
          <input value={projName} onChange={e => setProjName(e.target.value)} required />
          <textarea value={projDesc} onChange={e => setProjDesc(e.target.value)} placeholder="Description" />
          <div style={{ display: "flex", gap: 8 }}>
            <button className="primary" type="submit" style={{ padding: "7px 14px" }}>Save</button>
            <button type="button" className="secondary" onClick={() => setEditMode(false)}>Cancel</button>
          </div>
        </form>
      ) : (
        <header className="page-header" style={{ marginBottom: 24 }}>
          <div>
            <p className="eyebrow">PROJECT</p>
            <h1>{projName}</h1>
            {projDesc && <p className="muted">{projDesc}</p>}
          </div>
          <button className="secondary" onClick={() => setEditMode(true)}>Rename / edit</button>
        </header>
      )}

      {notice && <div className="notice success">{notice}</div>}
      <ErrorNotice error={error} />

      {/* Tasks board */}
      <section className="hub-section">
        <div className="section-heading"><h2>Tasks</h2><span>{tasks.length} total</span></div>

        <form onSubmit={addTask} style={{ display: "flex", gap: 8, marginBottom: 18, flexWrap: "wrap" }}>
          <input
            style={{ flex: "1 1 220px" }}
            value={taskTitle}
            onChange={e => setTaskTitle(e.target.value)}
            placeholder="New task title…"
            required
          />
          <input
            style={{ flex: "2 1 280px" }}
            value={taskDesc}
            onChange={e => setTaskDesc(e.target.value)}
            placeholder="Description (optional)"
          />
          <button className="primary" type="submit" style={{ whiteSpace: "nowrap" }}>+ Add task</button>
        </form>

        <div className="tasks-board">
          {TASK_STATUSES.map(status => (
            <div key={status} className="tasks-column">
              <div className="tasks-column-header" style={{ color: STATUS_COLOR[status] }}>
                {STATUS_LABEL[status]} <span className="tasks-count">{byStatus(status).length}</span>
              </div>
              {byStatus(status).map(task => (
                <TaskCard
                  key={task.id}
                  task={task}
                  projectId={project.id}
                  onUpdate={handleUpdateTask}
                  onDelete={handleDeleteTask}
                />
              ))}
              {byStatus(status).length === 0 && (
                <div className="tasks-empty">No tasks here</div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Session linking */}
      <section className="hub-section">
        <div className="section-heading">
          <h2>Linked sessions</h2>
          <span>{sessions.length} attached</span>
        </div>
        {allSessions.length === 0 && (
          <p className="muted" style={{ fontSize: 13 }}>No chat sessions yet. Start a conversation first.</p>
        )}
        {allSessions.map(s => {
          const isAttached = attached.has(s.session_id);
          return (
            <div className="list-row" key={s.session_id}>
              <div style={{ display: "grid", gap: 2, flex: 1 }}>
                <strong style={{ fontSize: 13 }}>{s.first_message || "Untitled session"}</strong>
                <span>{s.session_id.slice(0, 8)}… · {s.created_at?.slice(0, 10)}</span>
              </div>
              <button
                className={isAttached ? "secondary" : "primary"}
                style={{ fontSize: 12, padding: "5px 10px" }}
                onClick={() => toggleSession(s.session_id)}
              >
                {isAttached ? "Detach" : "Attach"}
              </button>
            </div>
          );
        })}
      </section>
    </div>
  );
}

function Projects() {
  const [projects,    setProjects]    = useState([]);
  const [allSessions, setAllSessions] = useState([]);
  const [openProject, setOpenProject] = useState(null); // project detail object
  const [name,        setName]        = useState("");
  const [description, setDescription] = useState("");
  const [error,       setError]       = useState("");
  const [notice,      setNotice]      = useState("");

  const refresh = () =>
    Promise.all([api.projects(), api.sessions()])
      .then(([projs, sessionData]) => {
        setProjects(projs);
        setAllSessions(sessionData.sessions || []);
      })
      .catch(e => setError(e.message));

  useEffect(() => { refresh(); }, []);

  async function create(event) {
    event.preventDefault();
    try {
      const proj = await api.createProject(name, description);
      setName(""); setDescription("");
      setNotice(`Project "${proj.name}" created.`);
      refresh();
    } catch (e) { setError(e.message); }
  }

  async function openDetail(projectId) {
    try {
      const detail = await api.getProject(projectId);
      setOpenProject(detail);
    } catch (e) { setError(e.message); }
  }

  async function archiveProject(projectId, projectName) {
    if (!window.confirm(`Archive "${projectName}"? It will be hidden from this list.`)) return;
    try {
      await api.archiveProject(projectId);
      setNotice(`"${projectName}" archived.`);
      refresh();
    } catch (e) { setError(e.message); }
  }

  async function deleteProject(projectId, projectName) {
    if (!window.confirm(`Delete "${projectName}" and all its tasks? This cannot be undone.`)) return;
    try {
      await api.deleteProject(projectId);
      setNotice(`"${projectName}" deleted.`);
      refresh();
    } catch (e) { setError(e.message); }
  }

  if (openProject) {
    return (
      <div className="page panel">
        <ProjectDetail
          project={openProject}
          allSessions={allSessions}
          onBack={() => { setOpenProject(null); refresh(); }}
          onChanged={() => refresh()}
        />
      </div>
    );
  }

  return (
    <div className="page panel">
      <header className="page-header">
        <div>
          <p className="eyebrow">PROJECTS</p>
          <h1>Organize your work.</h1>
          <p className="muted">Group sessions and tasks into projects.</p>
        </div>
      </header>

      {notice && <div className="notice success">{notice}</div>}
      <ErrorNotice error={error} />

      <form className="project-form" onSubmit={create}>
        <input required value={name} onChange={e => setName(e.target.value)} placeholder="Project name" />
        <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Description (optional)" />
        <button className="primary">Create project</button>
      </form>

      <section className="hub-section">
        <div className="section-heading">
          <h2>Active projects</h2>
          <span>{projects.length}</span>
        </div>
        {projects.length ? projects.map(project => (
          <article className="project-row" key={project.id}>
            <div style={{ flex: 1, display: "grid", gap: 4 }}>
              <strong>{project.name}</strong>
              <small>{project.created_at?.slice(0, 10)}</small>
              {project.description && <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>{project.description}</p>}
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
              <button className="primary" style={{ fontSize: 12, padding: "5px 10px" }} onClick={() => openDetail(project.id)}>
                Open →
              </button>
              <button className="secondary" style={{ fontSize: 12, padding: "5px 10px" }} onClick={() => archiveProject(project.id, project.name)}>
                Archive
              </button>
              <button className="text-button" style={{ fontSize: 12, color: "var(--orange)" }} onClick={() => deleteProject(project.id, project.name)}>
                Delete
              </button>
            </div>
          </article>
        )) : (
          <div className="empty-state compact">No projects yet. Create one above.</div>
        )}
      </section>
    </div>
  );
}
// ---------------------------------------------------------------------------
// Status
// ---------------------------------------------------------------------------

function SettingsPage({ user, onSettingsSaved }) {
  const [form,      setForm]      = useState(null);
  const [models,    setModels]    = useState([]);
  const [passwords, setPasswords] = useState({ currentPassword: "", newPassword: "" });
  const [message,   setMessage]   = useState("");
  const [error,     setError]     = useState("");
  const [busy,      setBusy]      = useState(true);
  const [usersList, setUsersList] = useState([]);
  const [governanceNotice, setGovernanceNotice] = useState("");

  useEffect(() => {
    Promise.all([api.userSettings(), api.models()])
      .then(([settings, availableModels]) => {
        setForm(settings);
        setModels(availableModels);
        document.documentElement.dataset.theme = settings.theme || "dark";
      })
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  }, []);

  useEffect(() => {
    if (user?.role === "admin") {
      api.users().then((res) => setUsersList(res.users || [])).catch(() => {});
    }
  }, [user]);

  async function handleRoleChange(targetUsername, newRole) {
    try {
      await api.updateUserRole(targetUsername, newRole);
      setGovernanceNotice(`Role updated: '${targetUsername}' is now ${newRole.toUpperCase()}.`);
      const res = await api.users();
      setUsersList(res.users || []);
    } catch (err) {
      setError(err.message);
    }
  }

  function update(key, value) {
    setForm((current) => {
      const next = { ...current, [key]: value };
      // Apply theme change LIVE so the user sees the preview immediately
      if (key === "theme") {
        document.documentElement.dataset.theme = value;
      }
      return next;
    });
  }

  async function saveSettings(event) {
    event.preventDefault();
    setMessage(""); setError("");
    try {
      const saved = await api.updateUserSettings({
        name:                    form.name,
        theme:                   form.theme,
        default_model:           form.default_model,
        default_temperature:     Number(form.default_temperature),
        default_num_ctx:         Number(form.default_num_ctx),
        default_system_prompt:   form.default_system_prompt,
        default_landing_page:    form.default_landing_page,
        session_retention_days:  Number(form.session_retention_days),
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
    setMessage(""); setError("");
    try {
      await api.changePassword(passwords.currentPassword, passwords.newPassword);
      setPasswords({ currentPassword: "", newPassword: "" });
      setMessage("Password changed. Your current session remains active.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  if (busy || !form) {
    return <div className="page panel"><div className="loader">Loading settings…</div></div>;
  }

  return (
    <div className="page panel settings-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">SETTINGS</p>
          <h1>Your local workspace.</h1>
          <p className="muted">Preferences are stored in the backend database for your account.</p>
        </div>
      </header>

      {message && <div className="notice success">{message}</div>}
      <ErrorNotice error={error} />

      <form className="settings-form" onSubmit={saveSettings}>

        {/* ── Profile ───────────────────────────────────────────── */}
        <section className="settings-section">
          <div>
            <h2>Profile</h2>
            <p className="muted">Your account information from sign-up.</p>
          </div>
          <label>
            Display name
            <input
              value={form.name || ""}
              onChange={(e) => update("name", e.target.value)}
              required
            />
          </label>
          <label>
            Username
            <input value={form.username || ""} disabled style={{ opacity: 0.6 }} />
          </label>
          <label>
            Email
            <input value={form.email || ""} disabled style={{ opacity: 0.6 }} />
          </label>
          <label>
            Security role
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
              <span className="tag-chip accent" style={{ textTransform: "uppercase", fontWeight: 700 }}>
                {form.role || user?.role || "analyst"}
              </span>
              <small className="muted">
                {(form.role || user?.role) === "admin"
                  ? "Administrator (Full access to model deletion, user governance, and system tuning)"
                  : (form.role || user?.role) === "auditor"
                  ? "Auditor (Read-only compliance mode — inspects proofs of air-gap and logs)"
                  : "Analyst (Standard permissions for chat, project tasks, and RAG analysis)"}
              </small>
            </div>
          </label>
        </section>

        {/* ── Appearance ────────────────────────────────────────── */}
        <section className="settings-section">
          <div>
            <h2>Appearance</h2>
            <p className="muted">Changes apply instantly as a live preview.</p>
          </div>
          <label>
            Theme
            <select
              value={form.theme}
              onChange={(e) => update("theme", e.target.value)}
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
              <option value="system">System preference</option>
            </select>
          </label>
        </section>

        {/* ── Chat defaults ─────────────────────────────────────── */}
        <section className="settings-section">
          <div>
            <h2>Chat defaults</h2>
            <p className="muted">Applied when a new workbench session opens.</p>
          </div>
          <label>
            Default model
            <select
              value={form.default_model}
              onChange={(e) => update("default_model", e.target.value)}
            >
              <option value="auto">Auto-detect</option>
              {models.map((m) => <option key={m.id} value={m.id}>{m.id}</option>)}
            </select>
          </label>
          <label>
            Default temperature
            <output>{form.default_temperature}</output>
            <input
              type="range" min="0" max="2" step="0.1"
              value={form.default_temperature}
              onChange={(e) => update("default_temperature", e.target.value)}
            />
          </label>
          <label>
            Default context window
            <output>{form.default_num_ctx}</output>
            <input
              type="range" min="2048" max="32768" step="1024"
              value={form.default_num_ctx}
              onChange={(e) => update("default_num_ctx", e.target.value)}
            />
          </label>
          <label>
            Default system prompt
            <textarea
              value={form.default_system_prompt || ""}
              onChange={(e) => update("default_system_prompt", e.target.value)}
            />
          </label>
        </section>

        {/* ── Workspace ─────────────────────────────────────────── */}
        <section className="settings-section">
          <div>
            <h2>Workspace</h2>
            <p className="muted">Where to land after signing in and how long to keep sessions.</p>
          </div>
          <label>
            Default landing page
            <select
              value={form.default_landing_page}
              onChange={(e) => update("default_landing_page", e.target.value)}
            >
              <option value="chat">Workbench</option>
              <option value="models">Model Hub</option>
              <option value="projects">Projects</option>
              <option value="status">System Status</option>
              <option value="settings">Settings</option>
            </select>
          </label>
          <label>
            Session retention (days)
            <input
              type="number" min="1" max="3650"
              value={form.session_retention_days}
              onChange={(e) => update("session_retention_days", e.target.value)}
            />
          </label>
        </section>

        <button className="primary" type="submit">Save settings</button>
      </form>

      {/* ── Change password ───────────────────────────────────────── */}
      <form className="settings-section password-section" onSubmit={changePassword}>
        <div>
          <h2>Change password</h2>
          <p className="muted">Hashed by the backend — never returned to the browser.</p>
        </div>
        <label>
          Current password
          <input
            type="password"
            autoComplete="current-password"
            value={passwords.currentPassword}
            onChange={(e) => setPasswords({ ...passwords, currentPassword: e.target.value })}
            required
          />
        </label>
        <label>
          New password
          <input
            type="password"
            autoComplete="new-password"
            minLength={8}
            value={passwords.newPassword}
            onChange={(e) => setPasswords({ ...passwords, newPassword: e.target.value })}
            placeholder="At least 8 characters"
            required
          />
        </label>
        <button className="secondary" type="submit">Change password</button>
      </form>

      {/* ── User Governance (Admin Only) ────────────────────────── */}
      {user?.role === "admin" && (
        <section className="settings-section" style={{ gridTemplateColumns: "1fr", marginTop: 24 }}>
          <div>
            <h2>User Governance & Role Management</h2>
            <p className="muted">Assign security roles to local users (Admin, Analyst, Auditor).</p>
          </div>
          {governanceNotice && <div className="notice success">{governanceNotice}</div>}
          <div style={{ overflowX: "auto" }}>
            <table className="user-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Display Name</th>
                  <th>Email</th>
                  <th>Assigned Role</th>
                  <th>Registered</th>
                </tr>
              </thead>
              <tbody>
                {usersList.map((u) => (
                  <tr key={u.username}>
                    <td><strong>{u.username}</strong></td>
                    <td>{u.name}</td>
                    <td>{u.email || "—"}</td>
                    <td>
                      {u.username === "admin" ? (
                        <span className="tag-chip accent">PRIMARY ADMIN</span>
                      ) : (
                        <select
                          value={u.role || "analyst"}
                          onChange={(e) => handleRoleChange(u.username, e.target.value)}
                          style={{ width: "auto", padding: "4px 8px", fontSize: 12 }}
                        >
                          <option value="analyst">Analyst (Standard)</option>
                          <option value="auditor">Auditor (Read-Only)</option>
                          <option value="admin">Administrator (Full)</option>
                        </select>
                      )}
                    </td>
                    <td style={{ color: "var(--muted)", fontSize: 12 }}>
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
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
    numCtx: 16384,
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
          <span className="tag-chip accent" style={{ textTransform: "uppercase", fontSize: 10, letterSpacing: "0.08em", fontWeight: 700 }}>
            {user.role || "analyst"}
          </span>
          <span>{user.name || user.username}</span>
          <button onClick={logout}>Sign out</button>
        </div>
      </nav>

      {page === "chat" && <ChatView settings={settings} setSettings={setSettings} user={user} />}
      {page === "models" && <ModelHub user={user} />}
      {page === "projects" && <Projects user={user} />}
      {page === "status" && <Status user={user} />}
      {page === "settings" && <SettingsPage user={user} onSettingsSaved={(saved) => {
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
