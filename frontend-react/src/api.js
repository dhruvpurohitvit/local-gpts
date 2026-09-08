// When running via `npm run dev`, Vite proxies all /auth, /chat, etc. requests
// to http://127.0.0.1:8000 — so we use a relative base URL.
// The VITE_API_BASE_URL env var lets you override this for production builds
// where you may want to point directly at a deployed backend URL.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options = {}) {
  // Pull out our custom flag before spreading into fetch — fetch rejects unknown keys
  // in strict environments and will log warnings in others.
  const { _skipAuthEvent, ...fetchOptions } = options;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...fetchOptions,
  });

  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    // FastAPI detail can be:
    //   - a plain string  → "Invalid username or password"
    //   - an array        → [{loc:[...], msg:"...", type:"..."}]  (validation errors)
    //   - an object       → {some: "thing"}
    // We always produce a human-readable string.
    let detail = typeof body === "object" ? body?.detail : body;
    if (Array.isArray(detail)) {
      // Pydantic validation errors — join the human messages
      detail = detail.map((e) => e?.msg || JSON.stringify(e)).join("; ");
    } else if (detail && typeof detail === "object") {
      detail = JSON.stringify(detail);
    }

    if (response.status === 401 && !_skipAuthEvent) {
      window.dispatchEvent(new Event("sovereign-auth-expired"));
      throw new Error("Session expired. Please sign in again.");
    }
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return body;
}

function formData(values) {
  const data = new FormData();
  Object.entries(values).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    // File and Blob objects must be appended directly — String(file) gives "[object File]"
    if (value instanceof File || value instanceof Blob) {
      data.append(key, value, value instanceof File ? value.name : undefined);
    } else {
      data.append(key, String(value));
    }
  });
  return data;
}

export const api = {
  // Exposed for components that need to build direct download links.
  baseUrl: API_BASE_URL,

  root: () => request("/"),

  // Auth endpoints — expected to return 401 in some cases, so we skip the
  // sovereign-auth-expired event for them.
  authMe: () => request("/auth/me", { _skipAuthEvent: true }),
  login: (username, password) =>
    request("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
      _skipAuthEvent: true,
    }),
  signup: (username, name, email, password) =>
    request("/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, name, email, password }),
      _skipAuthEvent: true,
    }),
  logout: () => request("/auth/logout", { method: "POST", _skipAuthEvent: true }),
  userSettings: () => request("/users/me/settings"),
  updateUserSettings: (values) => request("/users/me/settings", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) }),
  changePassword: (currentPassword, newPassword) => request("/users/me/password", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) }),
  users: () => request("/users"),
  updateUserRole: (username, role) => request(`/users/${encodeURIComponent(username)}/role`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role }) }),

  // Session management
  sessions: () => request("/sessions"),
  newSession: () => request("/sessions/new", { method: "POST" }),

  // Chat history & artifacts
  history: (sessionId) => request(`/history/${encodeURIComponent(sessionId)}`),
  artifacts: (sessionId) => request(`/artifacts/${encodeURIComponent(sessionId)}`),
  downloadUrl: (sessionId, filename) =>
    `${API_BASE_URL}/download/${encodeURIComponent(sessionId)}/${encodeURIComponent(filename)}`,

  // Proof of Air-Gap Audit Ledger
  airgapCertificate: (sessionId) =>
    request(`/sessions/${encodeURIComponent(sessionId)}/airgap-certificate`),
  downloadAirgapCertificateUrl: (sessionId) =>
    `${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}/airgap-certificate/download`,

  // Chat
  chat: ({ prompt, sessionId, modelId, temperature, numCtx, systemPrompt, file, signal }) =>
    request("/chat", {
      method: "POST",
      body: formData({
        prompt,
        session_id: sessionId,
        model_id: modelId,
        temperature,
        num_ctx: numCtx,
        system_prompt: systemPrompt,
        file,
      }),
      signal,
    }),

  // Model management
  models: () => request("/models/list"),
  searchModels: (query, token) =>
    request(
      `/models/search?q=${encodeURIComponent(query)}&hf_token=${encodeURIComponent(token || "")}`
    ),
  modelFiles: (repoId, token) =>
    request(
      `/models/files?repo_id=${encodeURIComponent(repoId)}&hf_token=${encodeURIComponent(
        token || ""
      )}`
    ),
  startDownload: (repoId, filename, token) =>
    request("/models/download", {
      method: "POST",
      body: formData({ repo_id: repoId, filename, hf_token: token }),
    }),
  downloadProgress: (downloadId) =>
    request(`/models/download/progress/${encodeURIComponent(downloadId)}`),
  cancelDownload: (downloadId) =>
    request(`/models/download/${encodeURIComponent(downloadId)}`, { method: "DELETE" }),
  downloadedModels: () => request("/models/downloaded"),
  deleteDownloadedModel: (filename) =>
    request(`/models/downloaded/${encodeURIComponent(filename)}`, { method: "DELETE" }),
  deleteOllamaModel: (modelName) =>
    request(`/models/ollama/${encodeURIComponent(modelName)}`, { method: "DELETE" }),
  pullModel: (modelName) =>
    request("/models/pull", { method: "POST", body: formData({ model_name: modelName }) }),
  loadModel: (filename) =>
    request("/models/load", { method: "POST", body: formData({ filename }) }),

  // Projects
  projects: () => request("/projects"),
  createProject: (name, description) =>
    request("/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    }),
  getProject: (projectId) => request(`/projects/${projectId}`),
  updateProject: (projectId, name, description) =>
    request(`/projects/${projectId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    }),
  archiveProject: (projectId) =>
    request(`/projects/${projectId}/archive`, { method: "POST" }),
  deleteProject: (projectId) =>
    request(`/projects/${projectId}`, { method: "DELETE" }),

  // Project ↔ Session linking
  attachSession: (projectId, sessionId) =>
    request(`/projects/${projectId}/sessions/${sessionId}`, { method: "POST" }),
  detachSession: (projectId, sessionId) =>
    request(`/projects/${projectId}/sessions/${sessionId}`, { method: "DELETE" }),

  // Tasks
  tasks: (projectId) => request(`/projects/${projectId}/tasks`),
  createTask: (projectId, title, description, status) =>
    request(`/projects/${projectId}/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description, status }),
    }),
  updateTask: (projectId, taskId, fields) =>
    request(`/projects/${projectId}/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fields),
    }),
  deleteTask: (projectId, taskId) =>
    request(`/projects/${projectId}/tasks/${taskId}`, { method: "DELETE" }),

  // System
  sentry: () => request("/sentry/status"),
  gpu: () => request("/system/gpu"),
};
