# Sovereign AI React Frontend

This Vite app is the React replacement for the Streamlit UI. It talks to the existing FastAPI backend; set `VITE_API_BASE_URL` only when the API is not at `http://127.0.0.1:8000`.

```powershell
cd frontend-react
npm install
npm run dev
```

The backend must be started separately:

```powershell
uvicorn backend.api:app --reload --port 8000
```

## Migration Map

| Streamlit capability | Backend API | React surface |
| --- | --- | --- |
| Chat, history, session reset | `/chat`, `/history/{session_id}`, `/sessions/new` | Workbench chat |
| Model routing and parameters | `/models/list`, multipart `/chat` | Workbench sidebar |
| Document/image/code upload and RAG ingestion | multipart `/chat` | Workbench attachment control |
| Generated code and tool result | `/chat` response fields | Assistant result details |
| Artifacts and downloads | `/artifacts/{session_id}`, `/download/...` | Artifact list |
| Hugging Face search/files/downloads | `/models/search`, `/models/files`, `/models/download`, `/models/download/progress/...` | Model hub |
| Active/downloaded models | `/models/list`, `/models/downloaded` | Model hub lists |
| Ollama quick pull/load | `/models/pull`, `/models/load` | Model hub actions |
| Projects | `/projects` | Projects page |
| Network sentry | `/sentry/status` | Sidebar and system status |
| GPU and engine status | `/system/gpu`, `/models/list` | System status page |

No frontend secret, telemetry SDK, CDN asset, or cloud AI API is used. Hugging Face access remains an explicit existing backend model-hub operation.
