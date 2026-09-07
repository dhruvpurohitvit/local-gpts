import os
import threading
import requests
from typing import Dict, Any
from huggingface_hub import HfApi
from backend.logger import get_logger

log = get_logger("hf_hub")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models", "downloads")
os.makedirs(MODELS_DIR, exist_ok=True)

class HFHubManager:
    def __init__(self):
        self.api = HfApi()
        self.downloads: Dict[str, Dict[str, Any]] = {}

    def search_models(self, query: str, limit: int = 30, token: str = None):
        try:
            results = list(self.api.list_models(
                search=query,
                limit=limit,
                sort="downloads",
                token=token
            ))
            models = []
            for m in results:
                models.append({
                    "id": m.id,
                    "downloads": getattr(m, "downloads", 0),
                    "likes": getattr(m, "likes", 0),
                    "tags": getattr(m, "tags", []),
                    "pipeline_tag": getattr(m, "pipeline_tag", ""),
                    "last_modified": str(getattr(m, "last_modified", "")),
                    "author": getattr(m, "author", ""),
                })
            return models
        except Exception as e:
            log.error(f"HF Search failed: {e}")
            return [{"error": str(e)}]

    def get_model_files(self, repo_id: str, token: str = None):
        try:
            files = self.api.list_repo_files(repo_id=repo_id, token=token)
            relevant_files = [f for f in files if f.endswith('.gguf') or f.endswith('.safetensors')]
            return relevant_files
        except Exception as e:
            log.error(f"HF Get Files failed for {repo_id}: {e}")
            return []

    def download_file_background(self, repo_id: str, filename: str, download_id: str, token: str = None):
        dest_path = os.path.join(MODELS_DIR, os.path.basename(filename))
        url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        self.downloads[download_id] = {
            "status": "downloading",
            "progress": 0,
            "downloaded_bytes": 0,
            "total_bytes": 0,
            "downloaded_mb": "0.0 MB",
            "total_mb": "Unknown",
            "speed_mbps": "0.0",
            "file": os.path.basename(filename),
            "repo": repo_id,
            "path": dest_path,
            "_cancel": False,
        }

        try:
            log.info(f"Starting direct HF download: {url} -> {dest_path}")
            with requests.get(url, headers=headers, stream=True, timeout=30) as r:
                r.raise_for_status()
                total_length = r.headers.get('content-length')
                if total_length:
                    total_bytes = int(total_length)
                    self.downloads[download_id]["total_bytes"] = total_bytes
                    self.downloads[download_id]["total_mb"] = f"{total_bytes / (1024*1024):.1f} MB"
                else:
                    total_bytes = 0

                downloaded = 0
                chunk_size = 1024 * 512  # 512 KB chunks for smooth tracking
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        # Check cancel flag on every chunk
                        if self.downloads[download_id].get("_cancel"):
                            log.info(f"Download cancelled: {download_id}")
                            self.downloads[download_id]["status"] = "cancelled"
                            break
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            self.downloads[download_id]["downloaded_bytes"] = downloaded
                            self.downloads[download_id]["downloaded_mb"] = f"{downloaded / (1024*1024):.1f} MB"
                            if total_bytes > 0:
                                pct = int((downloaded / total_bytes) * 100)
                                self.downloads[download_id]["progress"] = min(pct, 99)

                if self.downloads[download_id]["status"] == "cancelled":
                    # Remove partial file
                    try:
                        os.remove(dest_path)
                    except OSError:
                        pass
                    return

            self.downloads[download_id]["status"] = "completed"
            self.downloads[download_id]["progress"] = 100
            self.downloads[download_id]["path"] = dest_path
            log.info(f"Download complete: {dest_path} ({downloaded} bytes)")

        except Exception as e:
            log.error(f"Download failed for {download_id}: {e}")
            self.downloads[download_id]["status"] = "error"
            self.downloads[download_id]["error"] = str(e)
            # Remove partial file on error
            try:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
            except OSError:
                pass

    def start_download(self, repo_id: str, filename: str, token: str = None) -> str:
        download_id = f"{repo_id.replace('/', '_')}_{os.path.basename(filename)}"
        # If already running, return existing id
        if download_id in self.downloads and self.downloads[download_id]["status"] == "downloading":
            return download_id

        thread = threading.Thread(
            target=self.download_file_background,
            args=(repo_id, filename, download_id, token),
            daemon=True,
        )
        thread.start()
        return download_id

    def cancel_download(self, download_id: str) -> bool:
        if download_id in self.downloads and self.downloads[download_id]["status"] == "downloading":
            self.downloads[download_id]["_cancel"] = True
            return True
        return False

    def get_download_status(self, download_id: str):
        entry = self.downloads.get(download_id, {"status": "not_found"})
        # Don't expose internal cancel flag
        return {k: v for k, v in entry.items() if not k.startswith("_")}

    def list_local_downloaded_files(self):
        """List all downloaded model files on disk with size"""
        files = []
        if os.path.exists(MODELS_DIR):
            for fname in os.listdir(MODELS_DIR):
                fpath = os.path.join(MODELS_DIR, fname)
                if os.path.isfile(fpath) and not fname.startswith('.') and (
                    fname.endswith('.gguf') or fname.endswith('.safetensors')
                ):
                    size_bytes = os.path.getsize(fpath)
                    size_mb = size_bytes / (1024 * 1024)
                    size_str = f"{size_mb:.1f} MB" if size_mb < 1024 else f"{size_mb / 1024:.2f} GB"
                    files.append({
                        "filename": fname,
                        "path": fpath,
                        "size": size_str,
                        "size_bytes": size_bytes,
                        "type": "GGUF" if fname.endswith('.gguf') else "Safetensors",
                    })
        return files

    def delete_downloaded_file(self, filename: str) -> bool:
        safe = os.path.basename(filename)
        fpath = os.path.join(MODELS_DIR, safe)
        abs_models = os.path.abspath(MODELS_DIR)
        abs_target = os.path.abspath(fpath)
        if not abs_target.startswith(abs_models):
            raise ValueError("Path traversal detected")
        if not os.path.isfile(abs_target):
            raise FileNotFoundError(f"{safe} not found")
        os.remove(abs_target)
        log.info(f"Deleted downloaded file: {abs_target}")
        return True


hf_manager = HFHubManager()
