import os
import requests
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from backend.logger import get_logger

log = get_logger("model_manager")

class ModelManager:
    def __init__(self):
        # Prefer vLLM OpenAI API endpoint (port 8001 or custom, NOT our own port 8000)
        self.vllm_base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
        self.use_vllm = False
        self.ollama_base_url = "http://localhost:11434"

    def is_vllm_alive(self) -> bool:
        if not os.getenv("VLLM_BASE_URL"):
            return False
        try:
            resp = requests.get(f"{self.vllm_base_url}/models", timeout=1)
            return resp.status_code == 200
        except Exception:
            return False

    def list_available_models(self) -> List[Dict[str, Any]]:
        models = []
        # Check vLLM
        if self.is_vllm_alive():
            try:
                resp = requests.get(f"{self.vllm_base_url}/models", timeout=2)
                data = resp.json()
                for m in data.get("data", []):
                    models.append({
                        "id": m["id"],
                        "name": m["id"],
                        "provider": "vLLM",
                        "size": "unknown"
                    })
            except Exception as e:
                log.error(f"Failed to list vLLM models: {e}")
        
        # Check Ollama as fallback
        try:
            resp = requests.get(f"{self.ollama_base_url}/api/tags", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                for m in data.get("models", []):
                    details = m.get("details", {})
                    models.append({
                        "id": m["name"],
                        "name": m["name"],
                        "provider": "Ollama",
                        "size": f"{m.get('size', 0) / (1024**3):.2f} GB",
                        "family": details.get("family", ""),
                        "parameter_size": details.get("parameter_size", ""),
                        "quantization_level": details.get("quantization_level", ""),
                        "format": details.get("format", ""),
                        "modified_at": m.get("modified_at", ""),
                    })
        except Exception as e:
            log.error(f"Failed to list Ollama models: {e}")

        return models

    def get_llm(self, model_id: str, temperature: float = 0.0, num_ctx: int = 8192):
        """Returns the appropriate Langchain Chat model based on availability."""
        
        # Determine if model is provided by vLLM or Ollama
        provider = "Ollama"
        for m in self.list_available_models():
            if m["id"] == model_id:
                provider = m["provider"]
                break

        log.info(f"Initializing LLM: {model_id} via {provider} (temp={temperature}, ctx={num_ctx})")

        if provider == "vLLM" or self.is_vllm_alive():
            # For vLLM, it usually ignores max_tokens/ctx in ChatOpenAI init but we pass what we can
            return ChatOpenAI(
                model=model_id,
                temperature=temperature,
                max_tokens=num_ctx,
                api_key="empty",
                base_url=self.vllm_base_url
            )
        else:
            # Fallback to Ollama
            return ChatOllama(
                model=model_id,
                temperature=temperature,
                num_ctx=num_ctx
            )

model_manager = ModelManager()
