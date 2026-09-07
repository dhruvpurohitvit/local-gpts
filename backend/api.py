import os
import shutil
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from backend.agent import SovereignAgent
from backend.db import db
from backend.network_sentry import check_airgap_status
from backend.hf_hub import hf_manager
from backend.model_manager import model_manager
from backend.logger import log

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)

app = FastAPI(title="Sovereign AI Workbench API")
agent = SovereignAgent()

@app.get("/")
def root():
    return {"service": "Sovereign AI Workbench", "status": "RUNNING"}

@app.get("/sessions")
def get_sessions():
    return {"sessions": db.get_all_sessions()}

@app.post("/sessions/new")
def create_new_session():
    session_id = db.create_session()
    ws = os.path.join(WORKSPACE_DIR, f"session_{session_id}")
    os.makedirs(ws, exist_ok=True)
    return {"success": True, "session_id": session_id, "workspace": ws}

@app.post("/chat")
def chat_endpoint(
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
        if not session_id or session_id == "None":
            session_id = db.create_session()
        elif not db.session_exists(session_id):
            db.create_session_with_id(session_id)

        session_workspace = os.path.abspath(os.path.join(WORKSPACE_DIR, f"session_{session_id}"))
        os.makedirs(session_workspace, exist_ok=True)

        file_path = None
        uploaded_file_name = None
        if file and file.filename:
            uploaded_file_name = os.path.basename(file.filename)
            file_path = os.path.join(session_workspace, uploaded_file_name)
            with open(file_path, "wb") as f:
                f.write(file.file.read())
            
            # Ingest RAG documents
            ext = os.path.splitext(uploaded_file_name)[1].lower()
            if ext in [".pdf", ".txt", ".md"]:
                try:
                    from backend.rag_engine import ingest_document
                    chunks = ingest_document(file_path)
                    log.info(f"Ingested {uploaded_file_name} into RAG ({chunks} chunks).")
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

@app.get("/models/downloaded")
def list_downloaded_models():
    return hf_manager.list_local_downloaded_files()

@app.get("/projects")
def list_projects():
    return db.get_projects()

@app.post("/projects")
def create_project(name: str = Form(...), description: str = Form("")):
    p_id = db.create_project(name, description)
    return {"project_id": p_id}

@app.get("/sentry/status")
def sentry_status():
    return check_airgap_status()

@app.get("/history/{session_id}")
def get_history(session_id: str):
    if not db.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    history = db.get_session_history(session_id)
    return {"session_id": session_id, "message_count": len(history), "history": history}

@app.get("/artifacts/{session_id}")
def get_artifacts(session_id: str):
    if not db.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    artifacts = db.get_session_artifacts(session_id)
    return {"session_id": session_id, "artifact_count": len(artifacts), "artifacts": artifacts}

@app.get("/download/{session_id}/{file_name}")
def download_file(session_id: str, file_name: str):
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