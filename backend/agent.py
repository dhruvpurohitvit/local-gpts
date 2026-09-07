import os
import re
import json
import base64
import mimetypes

from typing import TypedDict, Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from langgraph.graph import END, StateGraph

from backend.router import TaskRouter
from backend.db import db
from backend.rag_engine import query_rag

from backend.tools.docker_sandbox import execute_code

from backend.tools.doc_generator import (
    generate_word_doc,
    generate_powerpoint,
    generate_csv
)


# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

WORKSPACE_DIR = os.path.join(
    PROJECT_ROOT,
    "workspace"
)


# ==========================================================
# AGENT STATE
# ==========================================================

class AgentState(TypedDict):

    session_id: str
    prompt: str
    file_path: Optional[str]
    config: dict

    selected_model: str
    rag_context: str

    generated_code: str
    detected_language: str

    tool_result: dict

    error_count: int
    final_output: str

    artifact_type: str
    artifact_name: str
    artifact_path: str



# ==========================================================
# SOVEREIGN AGENT
# ==========================================================

class SovereignAgent:

    IMAGE_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".gif"
    }

    CODE_EXTENSIONS = {
        ".py": "python",
        ".java": "java",
        ".js": "javascript",
        ".mjs": "javascript",
        ".c": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp"
    }


    def __init__(self):

        self.router = TaskRouter()

        self.workspace_base = WORKSPACE_DIR

        os.makedirs(
            self.workspace_base,
            exist_ok=True
        )

        self.graph = self._build_graph()

        self.correction_graph = (
            self._build_correction_graph()
        )


    # ==========================================================
    # SESSION WORKSPACE
    # ==========================================================

    def get_workspace_path(
        self,
        session_id: str
    ) -> str:

        safe_session_id = re.sub(
            r"[^a-zA-Z0-9_-]",
            "",
            session_id
        )

        if not safe_session_id:

            raise ValueError(
                "Invalid session ID"
            )

        workspace_path = os.path.join(
            self.workspace_base,
            f"session_{safe_session_id}"
        )

        os.makedirs(
            workspace_path,
            exist_ok=True
        )

        return workspace_path


    # ==========================================================
    # FILE HELPERS
    # ==========================================================

    def is_image_file(
        self,
        file_path: Optional[str]
    ) -> bool:

        if not file_path:
            return False

        extension = os.path.splitext(
            file_path
        )[1].lower()

        return extension in self.IMAGE_EXTENSIONS


    def is_code_file(
        self,
        file_path: Optional[str]
    ) -> bool:

        if not file_path:
            return False

        extension = os.path.splitext(
            file_path
        )[1].lower()

        return extension in self.CODE_EXTENSIONS


    def get_file_language(
        self,
        file_path: Optional[str]
    ) -> str:

        if not file_path:
            return ""

        extension = os.path.splitext(
            file_path
        )[1].lower()

        return self.CODE_EXTENSIONS.get(
            extension,
            ""
        )


    # ==========================================================
    # IMAGE TO BASE64
    # ==========================================================

    def _encode_image(
        self,
        file_path: str
    ) -> str:

        if not os.path.exists(file_path):

            raise FileNotFoundError(
                f"Image file not found: {file_path}"
            )

        mime_type, _ = mimetypes.guess_type(
            file_path
        )

        if not mime_type:

            mime_type = "image/png"

        with open(
            file_path,
            "rb"
        ) as image_file:

            encoded_image = base64.b64encode(
                image_file.read()
            ).decode("utf-8")

        return (
            f"data:{mime_type};base64,"
            f"{encoded_image}"
        )


    # ==========================================================
    # CLEAN LLM OUTPUT
    # ==========================================================

    def _clean_code(
        self,
        text: str
    ) -> str:

        if not text:
            return ""

        text = text.strip()

        match = re.search(
            r"```(?:python|py|java|javascript|js|"
            r"cpp|c\+\+|c)?\s*\n(.*?)```",
            text,
            re.DOTALL | re.IGNORECASE
        )

        if match:

            return match.group(1).strip()

        return text.strip()


    # ==========================================================
    # SAFE JSON EXTRACTION
    # ==========================================================

    def _extract_json(
        self,
        text: str,
        fallback: dict
    ) -> dict:

        cleaned_text = self._clean_code(text)

        try:

            return json.loads(
                cleaned_text
            )

        except Exception:

            pass

        try:

            start = cleaned_text.find("{")
            end = cleaned_text.rfind("}")

            if start != -1 and end != -1:

                return json.loads(
                    cleaned_text[start:end + 1]
                )

        except Exception:

            pass

        return fallback


    # ==========================================================
    # ARTIFACT INTENT
    # ==========================================================

    def detect_artifact_intent(
        self,
        prompt: str
    ) -> str:

        prompt_lower = prompt.lower()

        word_keywords = [
            "word document",
            "word report",
            "create a word",
            "generate a word",
            "docx",
            ".docx",
            "microsoft word"
        ]

        powerpoint_keywords = [
            "powerpoint",
            "power point",
            "presentation",
            "pptx",
            ".pptx",
            "create slides",
            "generate slides",
            "make slides"
        ]

        csv_keywords = [
            "csv",
            ".csv",
            "generate csv",
            "create csv",
            "build a csv",
            "export table"
        ]

        if any(
            keyword in prompt_lower
            for keyword in powerpoint_keywords
        ):
            return "powerpoint"

        if any(
            keyword in prompt_lower
            for keyword in csv_keywords
        ):
            return "csv"

        if any(
            keyword in prompt_lower
            for keyword in word_keywords
        ):
            return "word"

        return ""


    # ==========================================================
    # SAFE FILENAME
    # ==========================================================

    def _create_safe_filename(
        self,
        title: str,
        extension: str
    ) -> str:

        if not title:

            title = "generated_artifact"

        filename = re.sub(
            r"[^a-zA-Z0-9]+",
            "_",
            title.lower()
        )

        filename = filename.strip("_")

        if not filename:

            filename = "generated_artifact"

        return filename[:60] + extension


    # ==========================================================
    # CODE REQUEST DETECTION
    # ==========================================================

    def is_code_request(
        self,
        prompt: str
    ) -> bool:

        prompt_lower = prompt.lower()

        phrases = [

            "write code",
            "generate code",
            "create code",

            "write a program",
            "create a program",
            "generate a program",

            "write python",
            "write java",
            "write javascript",
            "write c++",
            "write cpp",
            "write c code",

            "give me code",
            "provide code",

            "implement",
            "solve this problem",

            "debug this code",
            "fix this code",
            "refactor this code",

            "write a script",
            "create a script"
        ]

        return any(
            phrase in prompt_lower
            for phrase in phrases
        )


    # ==========================================================
    # EXECUTION REQUEST DETECTION
    # ==========================================================

    def is_execution_request(
        self,
        prompt: str
    ) -> bool:

        prompt_lower = prompt.lower()

        phrases = [

            "execute this code",
            "execute the code",

            "run this code",
            "run the code",

            "compile and run",
            "compile this code",

            "test this code",

            "run this program",
            "execute this program"
        ]

        return any(
            phrase in prompt_lower
            for phrase in phrases
        )


    # ==========================================================
    # LANGUAGE DETECTION
    # ==========================================================

    def detect_language(
        self,
        prompt: str,
        code: str = "",
        file_path: str = None
    ) -> str:

        # First priority: uploaded code file

        file_language = self.get_file_language(
            file_path
        )

        if file_language:

            return file_language

        code_lower = code.lower()
        prompt_lower = prompt.lower()

        # --------------------------------------------------
        # JAVA
        # --------------------------------------------------

        if (
            "public static void main" in code_lower
            or "system.out.println" in code_lower
            or re.search(
                r"\bclass\s+\w+",
                code
            )
            and "static void main" in code_lower
        ):
            return "java"

        # --------------------------------------------------
        # JAVASCRIPT
        # --------------------------------------------------

        if (
            "console.log" in code_lower
            or "require(" in code_lower
            or "process.stdout" in code_lower
        ):
            return "javascript"

        # --------------------------------------------------
        # C++
        # --------------------------------------------------

        if (
            "#include <iostream>" in code
            or "std::" in code
            or "using namespace std" in code_lower
        ):
            return "cpp"

        # --------------------------------------------------
        # C
        # --------------------------------------------------

        if (
            "#include <stdio.h>" in code
            or "#include<stdio.h>" in code_lower
        ):
            return "c"

        # --------------------------------------------------
        # PYTHON
        # --------------------------------------------------

        if (
            re.search(
                r"^\s*def\s+\w+\(",
                code,
                re.MULTILINE
            )
            or "print(" in code
            or "import " in code_lower
            or "from " in code_lower
        ):
            return "python"

        # --------------------------------------------------
        # PROMPT LANGUAGE
        # --------------------------------------------------

        if "javascript" in prompt_lower:

            return "javascript"

        if (
            "node.js" in prompt_lower
            or "nodejs" in prompt_lower
        ):

            return "javascript"

        if "java" in prompt_lower:

            return "java"

        if (
            "c++" in prompt_lower
            or "cpp" in prompt_lower
        ):

            return "cpp"

        if re.search(
            r"\bc language\b|\bc code\b",
            prompt_lower
        ):

            return "c"

        if "python" in prompt_lower:

            return "python"

        # Default

        return "python"


    # ==========================================================
    # RAG NODE
    # ==========================================================

    def rag_node(
        self,
        state: AgentState
    ):

        try:

            context = query_rag(
                state["prompt"],
                top_k=3
            )

        except Exception:

            context = (
                "No relevant local RAG context available."
            )

        return {
            "rag_context": context
        }


    # ==========================================================
    # ROUTER NODE
    # ==========================================================

    def router_node(self, state: AgentState):
        from backend.logger import log
        config = state.get("config", {})
        requested_model = config.get("model_id", "auto")
        
        if requested_model != "auto" and requested_model != "":
            log.info(f"[ROUTER] User explicitly requested model: {requested_model}")
            return {"selected_model": requested_model}

        category = self.router.route(
            prompt=state["prompt"],
            file_path=state["file_path"]
        )
        
        # Simple mapping: in a real production LM Studio clone, you'd map tags.
        # Here we just pick some known models or defaults.
        model_mapping = {
            "general": "qwen2.5:3b",
            "coder": "qwen2.5-coder:3b",
            "vision": "qwen2.5vl:7b"
        }
        
        selected_model = model_mapping.get(category, "qwen2.5:3b")
        log.info(f"[ROUTER] Auto-routed category '{category}' -> {selected_model}")

        return {
            "selected_model": selected_model
        }


    # ==========================================================
    # CHAT HISTORY
    # ==========================================================

    def _get_history_text(
        self,
        session_id: str
    ) -> str:

        try:

            history = db.get_session_history(
                session_id,
                limit=10
            )

        except Exception:

            return "No previous conversation."

        if not history:

            return "No previous conversation."

        history_parts = []

        for message in history:

            role = message.get(
                "role",
                "unknown"
            )

            content = message.get(
                "content",
                ""
            )

            history_parts.append(
                f"{role.upper()}: {content}"
            )

        return "\n".join(
            history_parts
        )


    # ==========================================================
    # ARTIFACT ROUTER
    # ==========================================================

    def should_generate_artifact(
        self,
        state: AgentState
    ):

        artifact_type = self.detect_artifact_intent(
            state["prompt"]
        )

        if artifact_type:

            return "artifact"

        return "normal"


    # ==========================================================
    # ARTIFACT NODE
    # ==========================================================

    def artifact_node(self, state: AgentState):
        from backend.model_manager import model_manager
        
        artifact_type = self.detect_artifact_intent(state["prompt"])
        workspace_path = self.get_workspace_path(state["session_id"])
        prompt = state["prompt"]

        config = state.get("config", {})
        temp = config.get("temperature", 0.0)
        ctx = config.get("num_ctx", 8192)
        model_name = state.get("selected_model", "qwen2.5:3b")

        llm = model_manager.get_llm(model_name, temperature=temp, num_ctx=ctx)

        # --------------------------------------------------
        # WORD
        # --------------------------------------------------

        if artifact_type == "word":

            generation_prompt = f"""
Generate content for a Microsoft Word document.

USER REQUEST:
{prompt}

LOCAL RAG CONTEXT:
{state["rag_context"]}

Return ONLY valid JSON:

{{
    "title": "Report Title",
    "content": "Detailed report content"
}}
"""

            response = llm.invoke(
                generation_prompt
            )

            data = self._extract_json(
                response.content,
                {
                    "title": "Generated Report",
                    "content": response.content
                }
            )

            title = str(
                data.get(
                    "title",
                    "Generated Report"
                )
            )

            content = str(
                data.get(
                    "content",
                    prompt
                )
            )

            file_name = self._create_safe_filename(
                title,
                ".docx"
            )

            file_path = os.path.join(
                workspace_path,
                file_name
            )

            generate_word_doc(
                title=title,
                content=content,
                filepath=file_path
            )

            final_output = (
                f"✅ Word document created: {file_name}"
            )


        # --------------------------------------------------
        # POWERPOINT
        # --------------------------------------------------

        elif artifact_type == "powerpoint":

            generation_prompt = f"""
Generate PowerPoint content.

USER REQUEST:
{prompt}

Return ONLY valid JSON:

{{
    "title": "Presentation Title",
    "bullet_points": [
        "Point 1",
        "Point 2",
        "Point 3"
    ]
}}
"""

            response = llm.invoke(
                generation_prompt
            )

            data = self._extract_json(
                response.content,
                {
                    "title": "Generated Presentation",
                    "bullet_points": [
                        response.content
                    ]
                }
            )

            title = str(
                data.get(
                    "title",
                    "Generated Presentation"
                )
            )

            bullet_points = data.get(
                "bullet_points",
                []
            )

            if not isinstance(
                bullet_points,
                list
            ):

                bullet_points = [
                    str(bullet_points)
                ]

            file_name = self._create_safe_filename(
                title,
                ".pptx"
            )

            file_path = os.path.join(
                workspace_path,
                file_name
            )

            generate_powerpoint(
                title=title,
                bullet_points=bullet_points,
                filepath=file_path
            )

            final_output = (
                f"✅ PowerPoint created: {file_name}"
            )


        # --------------------------------------------------
        # CSV
        # --------------------------------------------------

        elif artifact_type == "csv":

            generation_prompt = f"""
Generate structured CSV data.

USER REQUEST:
{prompt}

Return ONLY valid JSON:

{{
    "headers": ["Column 1", "Column 2"],
    "rows": [
        ["Value 1", "Value 2"]
    ]
}}
"""

            response = llm.invoke(
                generation_prompt
            )

            data = self._extract_json(
                response.content,
                {
                    "headers": ["Request"],
                    "rows": [[prompt]]
                }
            )

            headers = data.get(
                "headers",
                ["Data"]
            )

            rows = data.get(
                "rows",
                []
            )

            if not isinstance(headers, list):

                headers = ["Data"]

            if not isinstance(rows, list):

                rows = []

            file_name = "generated_data.csv"

            file_path = os.path.join(
                workspace_path,
                file_name
            )

            generate_csv(
                headers=headers,
                rows=rows,
                filepath=file_path
            )

            final_output = (
                f"✅ CSV created: {file_name}"
            )

        else:

            raise ValueError(
                "Unsupported artifact type"
            )


        absolute_file_path = os.path.abspath(
            file_path
        )

        db.register_artifact(
            session_id=state["session_id"],
            file_name=file_name,
            file_path=absolute_file_path,
            file_type=artifact_type
        )

        return {

            "artifact_type": artifact_type,

            "artifact_name": file_name,

            "artifact_path": absolute_file_path,

            "final_output": final_output,

            "tool_result": {

                "success": True,

                "artifact_generated": True,

                "artifact_type": artifact_type,

                "file_name": file_name,

                "file_path": absolute_file_path
            }
        }


    # ==========================================================
    # LLM NODE
    # ==========================================================

    def llm_node(self, state: AgentState):
        from backend.model_manager import model_manager
        from backend.logger import log

        model_name = state["selected_model"]
        config = state.get("config", {})
        temp = config.get("temperature", 0.0)
        ctx = config.get("num_ctx", 8192)

        log.info(f"[LLM] Creating client for {model_name} with temp={temp}, ctx={ctx}")
        llm = model_manager.get_llm(model_name, temperature=temp, num_ctx=ctx)

        history_text = self._get_history_text(
            state["session_id"]
        )

        code_request = self.is_code_request(
            state["prompt"]
        )

        execution_request = self.is_execution_request(
            state["prompt"]
        )

        # --------------------------------------------------
        # CODE FILE INPUT
        # --------------------------------------------------

        uploaded_code = ""

        if self.is_code_file(
            state["file_path"]
        ):

            try:

                with open(
                    state["file_path"],
                    "r",
                    encoding="utf-8"
                ) as file:

                    uploaded_code = file.read()

            except Exception as error:

                uploaded_code = (
                    f"Could not read uploaded file: {error}"
                )


        # --------------------------------------------------
        # INSTRUCTIONS
        # --------------------------------------------------

        if code_request or execution_request:

            instruction = """
The user is requesting programming help.

If code is requested, return ONLY valid source code.

Do not include:
- markdown fences
- explanations before the code
- explanations after the code

Generate complete executable code when appropriate.
"""

        else:

            instruction = """
Answer naturally and clearly.

Do not generate executable source code unless
the user explicitly requests programming help.
"""


        system_prompt = config.get("system_prompt", "")
        if system_prompt:
            instruction += f"\n\nUSER SYSTEM PROMPT:\n{system_prompt}\n"

        # ==================================================
        # PROMPT FORMATTING (CHAT MESSAGES)
        # ==================================================
        from langchain_core.messages import SystemMessage

        system_content = f"""You are the local assistant for Sovereign AI Workbench. You operate completely locally.

RULES:
- Do not claim internet access.
- Do not use external APIs.
{instruction}"""

        if state.get("rag_context"):
            system_content += f"\n\nLOCAL RAG CONTEXT:\n{state['rag_context']}"

        user_text = state["prompt"]
        if uploaded_code:
            user_text += f"\n\nUPLOADED CODE:\n{uploaded_code}"

        if self.is_image_file(state["file_path"]):
            try:
                image_data = self._encode_image(state["file_path"])
                message = HumanMessage(
                    content=[
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": image_data}
                    ]
                )
                response = llm.invoke([SystemMessage(content=system_content), message])
            except Exception as error:
                return {
                    "generated_code": f"Unable to process uploaded image: {error}",
                    "detected_language": ""
                }
        else:
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=user_text)
            ]
            response = llm.invoke(messages)


        output = response.content.strip()

        if code_request or execution_request:

            output = self._clean_code(
                output
            )


        language = ""

        if code_request or execution_request:

            language = self.detect_language(
                prompt=state["prompt"],
                code=output,
                file_path=state["file_path"]
            )


        return {

            "generated_code": output,

            "detected_language": language
        }


    # ==========================================================
    # SHOULD EXECUTE CODE
    # ==========================================================

    def should_execute_code(
        self,
        state: AgentState
    ):

        # Execute ONLY when user explicitly asks to run code

        if not self.is_execution_request(
            state["prompt"]
        ):

            return "skip"

        if not state["generated_code"].strip():

            return "skip"

        return "execute"


    # ==========================================================
    # DOCKER SANDBOX
    # ==========================================================

    def sandbox_node(
        self,
        state: AgentState
    ):

        language = state.get(
            "detected_language"
        )

        if not language:

            language = self.detect_language(
                prompt=state["prompt"],
                code=state["generated_code"],
                file_path=state["file_path"]
            )

        workspace_path = self.get_workspace_path(
            state["session_id"]
        )

        result = execute_code(
            code=state["generated_code"],
            language=language,
            working_directory=workspace_path
        )

        return {

            "tool_result": result,

            "detected_language": language
        }


    # ==========================================================
    # SELF CORRECTION
    # ==========================================================

    def self_correct_node(self, state: AgentState):
        from backend.model_manager import model_manager
        
        previous_code = state["generated_code"]
        language = state.get("detected_language", "python")
        error_message = state["tool_result"].get("stderr", "Unknown execution error")
        new_error_count = state["error_count"] + 1

        config = state.get("config", {})
        temp = config.get("temperature", 0.0)
        ctx = config.get("num_ctx", 8192)
        model_name = state.get("selected_model", "qwen2.5-coder:3b")

        llm = model_manager.get_llm(model_name, temperature=temp, num_ctx=ctx)

        correction_prompt = f"""
You are a {language} debugging assistant.

FAILED {language.upper()} CODE:

{previous_code}

EXECUTION ERROR:

{error_message}

Fix the code.

Return ONLY complete executable {language} source code.

No markdown.
No explanations.
"""

        response = llm.invoke(
            correction_prompt
        )

        corrected_code = self._clean_code(
            response.content
        )

        return {

            "generated_code": corrected_code,

            "error_count": new_error_count
        }


    # ==========================================================
    # CHECK EXECUTION
    # ==========================================================

    def check_execution(
        self,
        state: AgentState
    ):

        success = state["tool_result"].get(
            "success",
            False
        )

        error_count = state["error_count"]

        if success:

            return "success"

        if error_count >= 3:

            return "failed"

        return "retry"


    # ==========================================================
    # NO EXECUTION
    # ==========================================================

    def no_execution_node(
        self,
        state: AgentState
    ):

        return {

            "final_output":
                state["generated_code"],

            "tool_result": {

                "success": True,

                "stdout": "",

                "stderr": "",

                "execution_required": False
            }
        }


    # ==========================================================
    # SUCCESS
    # ==========================================================

    def success_node(
        self,
        state: AgentState
    ):

        stdout = state["tool_result"].get(
            "stdout",
            ""
        )

        language = state.get(
            "detected_language",
            "unknown"
        )

        if stdout.strip():

            final_output = (
                f"Execution successful ({language}).\n\n"
                f"Output:\n{stdout}"
            )

        else:

            final_output = (
                f"Execution successful ({language})."
            )

        return {

            "final_output": final_output
        }


    # ==========================================================
    # FAILURE
    # ==========================================================

    def failure_node(
        self,
        state: AgentState
    ):

        error_message = state["tool_result"].get(
            "stderr",
            "Unknown execution error"
        )

        return {

            "final_output": (
                "Execution failed after 3 correction attempts.\n\n"
                + error_message
            )
        }


    # ==========================================================
    # SQLITE PERSISTENCE
    # ==========================================================

    def db_persist_node(
        self,
        state: AgentState
    ):

        session_id = state["session_id"]

        db.save_message(
            session_id=session_id,
            role="user",
            content=state["prompt"],
            model_used=None
        )

        db.save_message(
            session_id=session_id,
            role="assistant",
            content=state["final_output"],
            model_used=state["selected_model"]
        )

        if state.get("tool_result"):

            if state.get("artifact_path"):

                tool_name = "document-generator"

            elif self.is_execution_request(
                state["prompt"]
            ):

                language = state.get(
                    "detected_language",
                    "unknown"
                )

                tool_name = (
                    f"docker-sandbox-{language}"
                )

            elif self.is_image_file(
                state.get("file_path")
            ):

                tool_name = "vision-model"

            else:

                tool_name = "local-agent"

            db.save_message(
                session_id=session_id,
                role="tool",
                content=str(
                    state["tool_result"]
                ),
                model_used=tool_name
            )

        return {
            "final_output": state.get("final_output", ""),
            "selected_model": state.get("selected_model", ""),
            "generated_code": state.get("generated_code", ""),
            "tool_result": state.get("tool_result", {}),
        }


    # ==========================================================
    # MAIN GRAPH
    # ==========================================================

    def _build_graph(self):

        workflow = StateGraph(
            AgentState
        )

        workflow.add_node(
            "rag",
            self.rag_node
        )

        workflow.add_node(
            "router",
            self.router_node
        )

        workflow.add_node(
            "artifact",
            self.artifact_node
        )

        workflow.add_node(
            "llm",
            self.llm_node
        )

        workflow.add_node(
            "sandbox",
            self.sandbox_node
        )

        workflow.add_node(
            "self_correct",
            self.self_correct_node
        )

        workflow.add_node(
            "no_execution",
            self.no_execution_node
        )

        workflow.add_node(
            "success",
            self.success_node
        )

        workflow.add_node(
            "failure",
            self.failure_node
        )

        workflow.add_node(
            "persist",
            self.db_persist_node
        )


        workflow.set_entry_point(
            "rag"
        )

        workflow.add_edge(
            "rag",
            "router"
        )

        workflow.add_conditional_edges(
            "router",
            self.should_generate_artifact,
            {
                "artifact": "artifact",
                "normal": "llm"
            }
        )

        workflow.add_edge(
            "artifact",
            "persist"
        )

        workflow.add_conditional_edges(
            "llm",
            self.should_execute_code,
            {
                "execute": "sandbox",
                "skip": "no_execution"
            }
        )

        workflow.add_conditional_edges(
            "sandbox",
            self.check_execution,
            {
                "success": "success",
                "retry": "self_correct",
                "failed": "failure"
            }
        )

        workflow.add_edge(
            "self_correct",
            "sandbox"
        )

        workflow.add_edge(
            "no_execution",
            "persist"
        )

        workflow.add_edge(
            "success",
            "persist"
        )

        workflow.add_edge(
            "failure",
            "persist"
        )

        workflow.add_edge(
            "persist",
            END
        )

        return workflow.compile()


    # ==========================================================
    # CORRECTION GRAPH
    # ==========================================================

    def _build_correction_graph(self):

        workflow = StateGraph(
            AgentState
        )

        workflow.add_node(
            "sandbox",
            self.sandbox_node
        )

        workflow.add_node(
            "self_correct",
            self.self_correct_node
        )

        workflow.add_node(
            "success",
            self.success_node
        )

        workflow.add_node(
            "failure",
            self.failure_node
        )

        workflow.add_node(
            "persist",
            self.db_persist_node
        )

        workflow.set_entry_point(
            "sandbox"
        )

        workflow.add_conditional_edges(
            "sandbox",
            self.check_execution,
            {
                "success": "success",
                "retry": "self_correct",
                "failed": "failure"
            }
        )

        workflow.add_edge(
            "self_correct",
            "sandbox"
        )

        workflow.add_edge(
            "success",
            "persist"
        )

        workflow.add_edge(
            "failure",
            "persist"
        )

        workflow.add_edge(
            "persist",
            END
        )

        return workflow.compile()


    # ==========================================================
    # RUN AGENT
    # ==========================================================

    def run(
        self,
        prompt: str,
        session_id: str = None,
        file_path: str = None,
        config: dict = None
    ):

        if session_id is None:
            session_id = db.create_session()
        elif not db.session_exists(session_id):
            db.create_session_with_id(session_id)

        self.get_workspace_path(session_id)
        
        if config is None:
            config = {"model_id": "auto", "temperature": 0.0, "num_ctx": 8192, "system_prompt": ""}

        initial_state = {
            "session_id": session_id,
            "prompt": prompt,
            "file_path": file_path,
            "config": config,
            "selected_model": config.get("model_id", "auto"),
            "rag_context": "",
            "generated_code": "",
            "detected_language": "",
            "tool_result": {},
            "error_count": 0,
            "final_output": "",
            "artifact_type": "",
            "artifact_name": "",
            "artifact_path": ""
        }

        return self.graph.invoke(initial_state)


    # ==========================================================
    # RUN EXISTING CODE
    # ==========================================================

    def run_with_code(
        self,
        code: str,
        language: str = "python",
        session_id: str = None,
        prompt: str = "Execute this code"
    ):

        if session_id is None:

            session_id = db.create_session()

        elif not db.session_exists(session_id):

            db.create_session_with_id(
                session_id
            )

        self.get_workspace_path(
            session_id
        )

        initial_state = {

            "session_id": session_id,

            "prompt": prompt,

            "file_path": None,

            "selected_model":
                "qwen2.5-coder:3b",

            "rag_context": "",

            "generated_code": code,

            "detected_language": language,

            "tool_result": {},

            "error_count": 0,

            "final_output": "",

            "artifact_type": "",

            "artifact_name": "",

            "artifact_path": ""
        }

        return self.correction_graph.invoke(
            initial_state
        )