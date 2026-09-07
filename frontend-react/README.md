# Sovereign AI Workbench — Quick Setup

## Default login credentials

| Username | Password  |
|----------|-----------|
| `admin`  | `admin123` |

> Change it after first login via **Settings → Change password**

---

## Running (development — single machine)

```bash
# Terminal 1 — Backend
cd local-gpts
.venv\Scripts\activate
uvicorn backend.api:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend-react
npm run dev
```

Open: http://localhost:5173

---

## Running across a LAN (teammates on same network)

### Step 1 — Find your LAN IP
```powershell
ipconfig   # look for IPv4 address, e.g. 192.168.1.42
```

### Step 2 — Start the backend bound to all interfaces
```bash
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
```

### Step 3 — Tell the frontend where the backend is
Create `frontend-react/.env.local`:
```
VITE_BACKEND_URL=http://192.168.1.42:8000
```

### Step 4 — Tell the backend to allow your LAN origin
Create `local-gpts/.env` (or set in your shell):
```
CORS_ALLOWED_ORIGINS=http://192.168.1.42:5173,http://localhost:5173
```

### Step 5 — Start the frontend
```bash
cd frontend-react
npm run dev
```

Teammates open: `http://192.168.1.42:5173`  
(Vite now binds to `0.0.0.0` — accessible from the LAN.)

---

## File uploads & RAG (document Q&A)

Supported formats: **PDF, TXT, MD, CSV**

1. Click **Attach file** in the chat
2. Upload your document
3. Ask a question about it — the system extracts the content and injects it into the model's context

> Each session's documents are isolated — uploading a file in one chat session does NOT affect another session.
