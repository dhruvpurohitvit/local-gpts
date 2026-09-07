import os
import shutil
import subprocess
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.agent import SovereignAgent
from backend.db import db
from backend.network_sentry import check_airgap_status
from backend.hf_hub import hf_manager
from backend.model_manager import model_manager
from backend.logger import log
from backend.auth import (
    SESSION_COOKIE,
    authenticate,
    create_session,
    current_user,
    delete_session,
    hash_password,
    register_user,
    user_settings,
    verify_password,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)
OLLAMA_COMMAND = shutil.which("ollama") or os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Programs",
    "Ollama",
    "ollama.exe"
)

app = FastAPI(title="Sovereign AI Workbench API")
agent = SovereignAgent()

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:5175,http://127.0.0.1:5175"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    username: str
    name: str
    email: str
    password: str


class SettingsUpdate(BaseModel):
    name: Optional[str] = None
    theme: Optional[str] = None
    default_model: Optional[str] = None
    default_temperature: Optional[float] = None
    default_num_ctx: Optional[int] = None
    default_system_prompt: Optional[str] = None
    default_landing_page: Optional[str] = None
    session_retention_days: Optional[int] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@app.middleware("http")
async def require_authentication(request: Request, call_next):
    public_paths = {"/", "/auth/login", "/auth/signup", "/auth/me", "/docs", "/openapi.json", "/redoc"}
    if request.method == "OPTIONS" or request.url.path in public_paths:
        return await call_next(request)
    try:
        request.state.user = current_user(request.cookies.get(SESSION_COOKIE))
    except HTTPException as error:
        origin = request.headers.get("origin")
        headers = {"Access-Control-Allow-Credentials": "true"}
        if origin in allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail},
            headers=headers,
        )
    return await call_next(request)

@app.get("/")
def root():
    return {"service": "Sovereign AI Workbench", "status": "RUNNING"}


@app.post("/auth/login")
def login(credentials: LoginRequest):
    user = authenticate(credentials.username.strip(), credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_session(user["username"])
    response = JSONResponse({"authenticated": True, "user": user})
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path="/",
    )
    return response


@app.post("/auth/signup")
def signup(credentials: SignupRequest):
    try:
        user = register_user(credentials.username, credentials.name, credentials.email, credentials.password)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    token = create_session(user["username"])
    response = JSONResponse({"authenticated": True, "user": user})
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path="/",
    )
    return response


@app.get("/auth/me")
def auth_me(request: Request):
    try:
        return {"authenticated": True, "user": current_user(request.cookies.get(SESSION_COOKIE))}
    except HTTPException:
        return {"authenticated": False, "user": None}


@app.post("/auth/logout")
def logout(request: Request):
    delete_session(request.cookies.get(SESSION_COOKIE))
    response = JSONResponse({"authenticated": False})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@app.get("/users/me/settings")
def get_user_settings(request: Request):
    return user_settings(request.state.user["username"])


@app.patch("/users/me/settings")
def update_user_settings(request: Request, changes: SettingsUpdate):
    values = changes.model_dump(exclude_none=True)
    if "theme" in values and values["theme"] not in {"dark", "light", "system"}:
        raise HTTPException(status_code=422, detail="Invalid theme")
    if "default_landing_page" in values and values["default_landing_page"] not in {"chat", "models", "projects", "status", "settings"}:
        raise HTTPException(status_code=422, detail="Invalid landing page")
    if "default_temperature" in values and not 0 <= values["default_temperature"] <= 2:
        raise HTTPException(status_code=422, detail="Temperature must be between 0 and 2")
    if "default_num_ctx" in values and not 2048 <= values["default_num_ctx"] <= 32768:
        raise HTTPException(status_code=422, detail="Context window is out of range")
    if "session_retention_days" in values and not 1 <= values["session_retention_days"] <= 3650:
        raise HTTPException(status_code=422, detail="Session retention must be between 1 and 3650 days")
    db.update_user_settings(request.state.user["username"], values)
    return user_settings(request.state.user["username"])


@app.post("/users/me/password")
def change_password(request: Request, change: PasswordChange):
    if len(change.new_password) < 8:
        raise HTTPException(status_code=422, detail="New password must be at least 8 characters")
    username = request.state.user["username"]
    if not verify_password(username, change.current_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    db.update_user_password(username, hash_password(change.new_password))
    return {"success": True}

@app.get("/sessions")
def get_sessions(request: Request):
    return {"sessions": db.get_all_sessions(user_id=request.state.user["username"])}

@app.post("/sessions/new")
def create_new_session(request: Request):
    session_id = db.create_session(user_id=request.state.user["username"])
    ws = os.path.join(WORKSPACE_DIR, f"session_{session_id}")
    os.makedirs(ws, exist_ok=True)
    return {"success": True, "session_id": session_id, "workspace": ws}

@app.post("/chat")
def chat_endpoint(
    request: Request,
    prompt: str = Form(...),
    session_id: Optional[str] = Form(None),
    model_id: str = Form("auto"),
    temperature: float = Form(0.0),
    num_ctx: int = Form(8192),
    system_prompt: str = Form(""),
    file: Optional[UploadFile] = File(None)
):
    try:
        log.info(f"API /chat: session={session_id}, model={model_id}, temp={temperature}, ctx={num_ctx}")
        username = request.state.user["username"]
        if not session_id or session_id == "None":
            session_id = db.create_session(user_id=username)
        elif not db.session_exists(session_id):
            db.create_session_with_id(session_id, username)
        elif not db.session_belongs_to_user(session_id, username):
            raise HTTPException(status_code=403, detail="Session does not belong to the current user")

        session_workspace = os.path.abspath(os.path.join(WORKSPACE_DIR, f"session_{session_id}"))
        os.makedirs(session_workspace, exist_ok=True)

        file_path = None
        uploaded_file_name = None
        if file and file.filename:
            uploaded_file_name = os.path.basename(file.filename)
            file_path = os.path.join(session_workspace, uploaded_file_name)
            with open(file_path, "wb") as f:
                f.write(file.file.read())
            
            # Ingest RAG documents — PDF, plain text, markdown, AND CSV
            ext = os.path.splitext(uploaded_file_name)[1].lower()
            if ext in [".pdf", ".txt", ".md", ".csv"]:
                try:
                    from backend.rag_engine import ingest_document
                    chunks = ingest_document(file_path, session_id=session_id)
                    log.info(f"Ingested {uploaded_file_name} into RAG ({chunks} chunks) for session {session_id}.")
                except Exception as e:
                    log.error(f"Failed to ingest {uploaded_file_name} into RAG: {e}")

        result = agent.run(
            prompt=prompt,
            session_id=session_id,
            file_path=file_path,
            config={
                "model_id": model_id,
                "temperature": temperature,
                "num_ctx": num_ctx,
                "system_prompt": system_prompt
            }
        )

        artifacts = db.get_session_artifacts(session_id)
        return {
            "success": True,
            "session_id": session_id,
            "final_output": result.get("final_output"),
            "selected_model": result.get("selected_model"),
            "generated_code": result.get("generated_code"),
            "tool_result": result.get("tool_result"),
            "error_count": result.get("error_count"),
            "uploaded_file": uploaded_file_name,
            "uploaded_file_path": file_path,
            "artifacts": artifacts,
            "artifact_count": len(artifacts)
        }
    except Exception as error:
        log.error(f"/chat failed: {error}")
        raise HTTPException(status_code=500, detail=str(error))

@app.get("/models/list")
def list_models():
    return model_manager.list_available_models()

@app.get("/models/search")
def search_models(q: str, hf_token: Optional[str] = None):
    clean_token = hf_token.strip() if hf_token and hf_token.strip() else None
    return hf_manager.search_models(q, token=clean_token)

@app.get("/models/files")
def model_files(repo_id: str, hf_token: Optional[str] = None):
    clean_token = hf_token.strip() if hf_token and hf_token.strip() else None
    return hf_manager.get_model_files(repo_id, token=clean_token)

@app.post("/models/download")
def download_model(repo_id: str = Form(...), filename: str = Form(...), hf_token: Optional[str] = Form(None)):
    clean_token = hf_token.strip() if hf_token and hf_token.strip() else None
    dl_id = hf_manager.start_download(repo_id, filename, token=clean_token)
    return {"download_id": dl_id}

@app.get("/models/download/progress/{dl_id}")
def download_progress(dl_id: str):
    return hf_manager.get_download_status(dl_id)

@app.delete("/models/download/{dl_id}")
def cancel_download(dl_id: str):
    cancelled = hf_manager.cancel_download(dl_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Download not active or already finished")
    return {"success": True, "download_id": dl_id, "status": "cancelled"}

@app.get("/models/downloaded")
def list_downloaded_models():
    return hf_manager.list_local_downloaded_files()

@app.delete("/models/downloaded/{filename}")
def delete_downloaded_model(filename: str):
    try:
        hf_manager.delete_downloaded_file(filename)
        return {"success": True, "filename": filename}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found on disk")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

@app.delete("/models/ollama/{model_name:path}")
def delete_ollama_model(model_name: str):
    try:
        result = subprocess.run(
            [OLLAMA_COMMAND, "rm", model_name],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    if result.returncode != 0:
        raise HTTPException(status_code=502, detail=result.stderr or "Ollama model deletion failed")
    return {"success": True, "model_id": model_name, "output": result.stdout}

@app.post("/models/pull")
def pull_model(model_name: str = Form(...)):
    try:
        result = subprocess.run(
            [OLLAMA_COMMAND, "pull", model_name],
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    if result.returncode != 0:
        raise HTTPException(status_code=502, detail=result.stderr or "Ollama pull failed")
    return {"success": True, "model_id": model_name, "output": result.stdout}

@app.post("/models/load")
def load_downloaded_model(filename: str = Form(...)):
    safe_filename = os.path.basename(filename)
    downloaded_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "models", "downloads"))
    file_path = os.path.abspath(os.path.join(downloaded_dir, safe_filename))
    if os.path.commonpath([downloaded_dir, file_path]) != downloaded_dir or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Downloaded model file not found")

    ext = os.path.splitext(safe_filename)[1].lower()
    if ext != ".gguf":
        raise HTTPException(
            status_code=400,
            detail="Only GGUF format weights (.gguf) can be directly loaded into Ollama. Safetensors require conversion.",
        )

    model_tag = os.path.splitext(safe_filename)[0].lower().replace("_", "-").replace(".", "-")
    modelfile_path = os.path.join(downloaded_dir, f"Modelfile.{model_tag}")
    try:
        with open(modelfile_path, "w", encoding="utf-8") as modelfile:
            modelfile.write(f"FROM ./{safe_filename}\n")
        result = subprocess.run(
            [OLLAMA_COMMAND, "create", model_tag, "-f", os.path.basename(modelfile_path)],
            capture_output=True,
            text=True,
            cwd=downloaded_dir,
            timeout=180,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    finally:
        if os.path.exists(modelfile_path):
            os.remove(modelfile_path)

    if result.returncode != 0:
        raise HTTPException(status_code=502, detail=result.stderr or "Ollama model creation failed")
    return {"success": True, "model_id": model_tag, "output": result.stdout}

@app.get("/system/gpu")
def gpu_status():
    try:
        import pynvml
        pynvml.nvmlInit()
        devices = []
        for index in range(pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8", errors="replace")
            devices.append({
                "index": index,
                "name": name,
                "used_bytes": memory.used,
                "total_bytes": memory.total,
                "usage_ratio": memory.used / memory.total if memory.total else 0,
            })
        return {"available": True, "devices": devices}
    except Exception as error:
        return {"available": False, "devices": [], "message": str(error)}


# ------------------------------------------------------------------
# PROJECTS
# ------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class ProjectUpdate(BaseModel):
    name: str
    description: str = ""

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    status: str = "todo"

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None

VALID_TASK_STATUSES = {"todo", "in_progress", "done"}

@app.get("/projects")
def list_projects(request: Request):
    return db.get_projects(user_id=request.state.user["username"])

@app.post("/projects")
def create_project(request: Request, body: ProjectCreate):
    p_id = db.create_project(body.name, body.description, request.state.user["username"])
    project = db.get_project(p_id, user_id=request.state.user["username"])
    return project

@app.get("/projects/{project_id}")
def get_project(request: Request, project_id: int):
    project = db.get_project_detail(project_id, user_id=request.state.user["username"])
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.put("/projects/{project_id}")
def update_project(request: Request, project_id: int, body: ProjectUpdate):
    ok = db.rename_project(project_id, body.name, body.description,
                           user_id=request.state.user["username"])
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.get_project(project_id, user_id=request.state.user["username"])

@app.post("/projects/{project_id}/archive")
def archive_project(request: Request, project_id: int):
    ok = db.archive_project(project_id, user_id=request.state.user["username"])
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}

@app.delete("/projects/{project_id}")
def delete_project(request: Request, project_id: int):
    ok = db.delete_project(project_id, user_id=request.state.user["username"])
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}

# ------------------------------------------------------------------
# PROJECT ↔ SESSION
# ------------------------------------------------------------------

@app.post("/projects/{project_id}/sessions/{session_id}")
def attach_session(request: Request, project_id: int, session_id: str):
    if not db.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    ok = db.attach_session_to_project(project_id, session_id,
                                       user_id=request.state.user["username"])
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    return {"success": True}

@app.delete("/projects/{project_id}/sessions/{session_id}")
def detach_session(request: Request, project_id: int, session_id: str):
    ok = db.detach_session_from_project(project_id, session_id,
                                         user_id=request.state.user["username"])
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    return {"success": True}

# ------------------------------------------------------------------
# TASKS
# ------------------------------------------------------------------

@app.get("/projects/{project_id}/tasks")
def list_tasks(request: Request, project_id: int):
    project = db.get_project(project_id, user_id=request.state.user["username"])
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.get_tasks(project_id)

@app.post("/projects/{project_id}/tasks")
def create_task(request: Request, project_id: int, body: TaskCreate):
    project = db.get_project(project_id, user_id=request.state.user["username"])
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if body.status not in VALID_TASK_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {VALID_TASK_STATUSES}")
    t_id = db.create_task(project_id, body.title, body.description, body.status)
    return db.get_tasks(project_id)

@app.patch("/projects/{project_id}/tasks/{task_id}")
def update_task(request: Request, project_id: int, task_id: int, body: TaskUpdate):
    project = db.get_project(project_id, user_id=request.state.user["username"])
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if body.status is not None and body.status not in VALID_TASK_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {VALID_TASK_STATUSES}")
    ok = db.update_task(task_id, project_id, title=body.title,
                        description=body.description, status=body.status)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return db.get_tasks(project_id)

@app.delete("/projects/{project_id}/tasks/{task_id}")
def delete_task(request: Request, project_id: int, task_id: int):
    project = db.get_project(project_id, user_id=request.state.user["username"])
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    ok = db.delete_task(task_id, project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}

@app.get("/sentry/status")
def sentry_status():
    return check_airgap_status()

@app.get("/history/{session_id}")
def get_history(request: Request, session_id: str):
    if not db.session_exists(session_id) or not db.session_belongs_to_user(session_id, request.state.user["username"]):
        raise HTTPException(status_code=404, detail="Session not found")
    history = db.get_session_history(session_id)
    return {"session_id": session_id, "message_count": len(history), "history": history}

@app.get("/artifacts/{session_id}")
def get_artifacts(request: Request, session_id: str):
    if not db.session_exists(session_id) or not db.session_belongs_to_user(session_id, request.state.user["username"]):
        raise HTTPException(status_code=404, detail="Session not found")
    artifacts = db.get_session_artifacts(session_id)
    return {"session_id": session_id, "artifact_count": len(artifacts), "artifacts": artifacts}

@app.get("/download/{session_id}/{file_name}")
def download_file(request: Request, session_id: str, file_name: str):
    if not db.session_belongs_to_user(session_id, request.state.user["username"]):
        raise HTTPException(status_code=404, detail="Artifact not found")
    safe_file_name = os.path.basename(file_name)
    session_workspace = os.path.abspath(os.path.join(WORKSPACE_DIR, f"session_{session_id}"))
    requested_file = os.path.abspath(os.path.join(session_workspace, safe_file_name))
    
    if os.path.commonpath([session_workspace, requested_file]) != session_workspace:
        raise HTTPException(status_code=403, detail="Invalid file path")
        
    artifacts = db.get_session_artifacts(session_id)
    artifact = next((item for item in artifacts if item["file_name"] == safe_file_name), None)
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not registered")
        
    database_file_path = os.path.abspath(artifact["file_path"])
    
    if not os.path.exists(database_file_path):
        raise HTTPException(status_code=404, detail="Artifact file does not exist")
        
    if os.path.commonpath([session_workspace, database_file_path]) != session_workspace:
        raise HTTPException(status_code=403, detail="Invalid artifact location")
        
    return FileResponse(path=database_file_path, filename=safe_file_name, media_type="application/octet-stream")