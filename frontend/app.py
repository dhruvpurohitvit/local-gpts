import uuid
import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Sovereign AI Workbench",
    page_icon="🛡️",
    layout="wide"
)

from frontend.auth_helper import check_auth
check_auth()


# ============================================================
# SESSION STATE
# ============================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None


# ============================================================
# API HELPERS
# ============================================================

def api_get(endpoint, timeout=10):
    try:
        response = requests.get(
            f"{API_BASE_URL}{endpoint}",
            timeout=timeout
        )

        if response.status_code == 200:
            return response.json()

        return None

    except Exception:
        return None


def get_sentry_status():
    return api_get("/sentry/status", timeout=5)


def get_history(session_id):
    return api_get(
        f"/history/{session_id}",
        timeout=10
    )


def get_artifacts(session_id):
    return api_get(
        f"/artifacts/{session_id}",
        timeout=10
    )


def load_history(session_id):

    history_data = get_history(session_id)

    if not history_data:
        return []

    history = history_data.get("history", [])

    messages = []

    for message in history:

        role = message.get("role")
        content = message.get("content")

        if role in ["user", "assistant"]:

            messages.append({
                "role": role,
                "content": content
            })

    return messages


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🛡️ Sovereign AI")

    st.caption(
        "Fully Local • Air-Gapped • Private AI"
    )

    st.divider()

    # ========================================================
    # MODEL CONFIGURATION (LM STUDIO STYLE)
    # ========================================================
    st.subheader("🧠 Model Selection")
    
    # Fetch all models from inference engine and downloads
    detected_models = []
    try:
        r = requests.get(f"{API_BASE_URL}/models/list", timeout=3)
        if r.status_code == 200:
            detected_models = r.json()
    except Exception:
        pass

    model_ids = [m["id"] for m in detected_models]

    # Mode Selector: Auto-Router vs Explicit Model
    selection_mode = st.radio(
        "Routing Mode",
        options=["🤖 Auto-Detect (Smart Router)", "🎯 Manual Model Selection"],
        index=0,
        help="Auto-Detect routes automatically (coding -> coder model, images -> vision model). Manual lets you force any single model."
    )

    if selection_mode == "🤖 Auto-Detect (Smart Router)":
        st.session_state["model_id"] = "auto"
        st.success("🟢 Auto-Routing Active (Qwen General / Coder / Vision)")
        with st.expander("ℹ️ Models in Auto Pool"):
            for m in detected_models:
                st.caption(f"• **`{m['id']}`** ({m.get('provider', 'Local')} - {m.get('size', '')})")
    else:
        if not model_ids:
            st.warning("No local models detected. Pull one from the Model Hub!")
            st.session_state["model_id"] = "auto"
        else:
            def format_model_label(mid):
                m_info = next((item for item in detected_models if item["id"] == mid), None)
                if m_info:
                    return f"{mid} ({m_info.get('size', 'ready')})"
                return mid

            selected_choice = st.selectbox(
                "Select Model to Chat With",
                options=model_ids,
                index=0,
                format_func=format_model_label,
                help="The prompt will be sent directly to this model."
            )
            st.session_state["model_id"] = selected_choice
            st.info(f"🎯 Direct Chat with: **`{selected_choice}`**")

    # Hyperparameters
    st.caption("Parameters")
    st.session_state["temperature"] = st.slider(
        "Temperature", 
        0.0, 2.0, 0.0, 0.1,
        help="Higher values make output more creative, lower values more deterministic."
    )

    st.session_state["num_ctx"] = st.slider(
        "Context Window", 
        2048, 32768, 8192, 1024,
        help="Maximum token memory context for this session."
    )

    st.session_state["system_prompt"] = st.text_area(
        "System Prompt",
        value="",
        placeholder="Override default system prompt...",
        height=100
    )

    st.divider()


    # ========================================================
    # SESSION MANAGEMENT
    # ========================================================

    st.subheader("💬 Chat Session")

    if st.button(
        "➕ New Session",
        use_container_width=True
    ):

        st.session_state.session_id = str(
            uuid.uuid4()
        )

        st.session_state.messages = []

        st.session_state.uploaded_file = None

        st.rerun()


    st.caption("Current Session")

    st.code(
        st.session_state.session_id,
        language=None
    )


    if st.button(
        "🔄 Refresh History",
        use_container_width=True
    ):

        st.session_state.messages = load_history(
            st.session_state.session_id
        )

        st.rerun()


    # Model Settings moved up

    # ========================================================
    # NETWORK SENTRY
    # ========================================================

    st.subheader("🛡️ Network Sentry")

    sentry = get_sentry_status()

    if sentry:

        workbench_status = sentry.get(
            "status",
            "UNKNOWN"
        )

        airgapped = sentry.get(
            "airgapped",
            False
        )

        socket_count = sentry.get(
            "external_socket_count",
            0
        )


        if airgapped:

            st.success(
                "🟢 SECURE AIR-GAPPED"
            )

            st.caption(
                f"0 Outbound Workbench Sockets"
            )

        else:

            st.warning(
                "🟠 NETWORK WARNING"
            )

            st.caption(
                f"External sockets: {socket_count}"
            )


        st.metric(
            "Workbench Status",
            workbench_status
        )


        with st.expander(
            "View Security Details"
        ):

            st.json(sentry)


    else:

        st.error(
            "🔴 NETWORK SENTRY OFFLINE"
        )

        st.caption(
            "Cannot reach FastAPI backend"
        )


    st.divider()


    # ========================================================
    # FILE UPLOAD
    # ========================================================

    st.subheader("📎 Upload Document")

    uploaded_file = st.file_uploader(
        "Upload a file for analysis",
        type=[
            "txt",
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "csv",
            "docx"
        ]
    )


    if uploaded_file:

        st.session_state.uploaded_file = uploaded_file

        st.success(
            f"📎 {uploaded_file.name}"
        )

        st.caption(
            f"Type: {uploaded_file.type}"
        )

        st.caption(
            f"Size: {uploaded_file.size} bytes"
        )


        if uploaded_file.type.startswith("image"):

            st.image(
                uploaded_file,
                use_container_width=True
            )


    elif st.session_state.uploaded_file:

        st.info(
            f"Ready: "
            f"{st.session_state.uploaded_file.name}"
        )


    st.divider()


    # ========================================================
    # ARTIFACT SUMMARY
    # ========================================================

    artifact_data = get_artifacts(
        st.session_state.session_id
    )

    if artifact_data:

        artifact_count = artifact_data.get(
            "artifact_count",
            0
        )

        st.metric(
            "Generated Files",
            artifact_count
        )


# ============================================================
# MAIN PAGE HEADER
# ============================================================

st.title("🛡️ Sovereign AI Workbench")

st.caption(
    "Fully Local • Air-Gapped • Private AI"
)

st.divider()


# ============================================================
# LOAD DATABASE HISTORY
# ============================================================

if len(st.session_state.messages) == 0:

    st.session_state.messages = load_history(
        st.session_state.session_id
    )


# ============================================================
# DISPLAY CHAT HISTORY
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# ============================================================
# DISPLAY ARTIFACTS
# ============================================================

def display_artifacts(session_id):

    artifact_data = get_artifacts(session_id)

    if not artifact_data:
        return

    artifacts = artifact_data.get(
        "artifacts",
        []
    )

    if not artifacts:
        return


    st.divider()

    st.subheader("📁 Generated Artifacts")


    for artifact in artifacts:

        file_name = artifact.get(
            "file_name"
        )

        file_type = artifact.get(
            "file_type",
            "file"
        )

        if not file_name:
            continue


        download_url = (
            f"{API_BASE_URL}"
            f"/download/{session_id}/{file_name}"
        )


        try:

            response = requests.get(
                download_url,
                timeout=30
            )


            if response.status_code == 200:

                col1, col2 = st.columns(
                    [3, 1]
                )


                with col1:

                    st.write(
                        f"📄 **{file_name}**"
                    )

                    st.caption(
                        f"Type: {file_type}"
                    )


                with col2:

                    st.download_button(
                        label="⬇ Download",
                        data=response.content,
                        file_name=file_name,
                        mime="application/octet-stream",
                        key=f"artifact_{session_id}_{file_name}"
                    )


            else:

                st.warning(
                    f"Could not load {file_name}"
                )


        except Exception:

            st.warning(
                f"Download unavailable: {file_name}"
            )


display_artifacts(
    st.session_state.session_id
)


# ============================================================
# CHAT INPUT
# ============================================================

prompt = st.chat_input(
    "Ask Sovereign AI anything..."
)


if prompt:


    # ========================================================
    # SHOW USER MESSAGE
    # ========================================================

    with st.chat_message("user"):

        st.markdown(prompt)


    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })


    # ========================================================
    # SHOW ASSISTANT RESPONSE
    # ========================================================

    with st.chat_message("assistant"):

        with st.spinner(
            "🧠 Processing locally..."
        ):

            try:


                # ====================================================
                # PREPARE FORM DATA
                # ====================================================

                form_data = {
                    "prompt": prompt,
                    "session_id": st.session_state.session_id,
                    "model_id": st.session_state.get("model_id", "auto"),
                    "temperature": st.session_state.get("temperature", 0.0),
                    "num_ctx": st.session_state.get("num_ctx", 8192),
                    "system_prompt": st.session_state.get("system_prompt", "")
                }


                files = None


                # ====================================================
                # OPTIONAL FILE
                # ====================================================

                active_file = (
                    st.session_state.uploaded_file
                )


                if active_file:

                    files = {
                        "file": (
                            active_file.name,
                            active_file.getvalue(),
                            active_file.type
                            or "application/octet-stream"
                        )
                    }


                # ====================================================
                # CALL API
                # ====================================================

                response = requests.post(
                    f"{API_BASE_URL}/chat",
                    data=form_data,
                    files=files,
                    timeout=180
                )


                # ====================================================
                # ERROR
                # ====================================================

                if response.status_code != 200:

                    st.error(
                        f"Backend Error "
                        f"({response.status_code})"
                    )

                    try:

                        error_data = response.json()

                        st.code(
                            error_data.get(
                                "detail",
                                response.text
                            )
                        )

                    except Exception:

                        st.code(
                            response.text
                        )


                # ====================================================
                # SUCCESS
                # ====================================================

                else:

                    result = response.json()


                    # --------------------------------------------
                    # UPDATE SESSION ID
                    # --------------------------------------------

                    returned_session_id = result.get(
                        "session_id"
                    )


                    if returned_session_id:

                        st.session_state.session_id = (
                            returned_session_id
                        )


                    # --------------------------------------------
                    # MODEL
                    # --------------------------------------------

                    selected_model = result.get(
                        "selected_model"
                    )


                    if selected_model:

                        st.caption(
                            f"🤖 Model: "
                            f"`{selected_model}`"
                        )


                    # --------------------------------------------
                    # FINAL OUTPUT
                    # --------------------------------------------

                    final_output = result.get(
                        "final_output"
                    )


                    if not final_output:

                        final_output = (
                            "Task completed successfully."
                        )


                    st.markdown(
                        final_output
                    )


                    # --------------------------------------------
                    # GENERATED CODE
                    # --------------------------------------------

                    generated_code = result.get(
                        "generated_code"
                    )


                    if generated_code:

                        with st.expander(
                            "💻 Generated Code"
                        ):

                            st.code(
                                generated_code,
                                language="python"
                            )


                    # --------------------------------------------
                    # TOOL RESULT
                    # --------------------------------------------

                    tool_result = result.get(
                        "tool_result"
                    )


                    if tool_result:

                        with st.expander(
                            "🔧 Tool Execution"
                        ):

                            st.json(
                                tool_result
                            )


                    # --------------------------------------------
                    # ARTIFACTS CREATED
                    # --------------------------------------------

                    new_artifacts = result.get(
                        "artifacts",
                        []
                    )


                    if new_artifacts:

                        st.success(
                            f"📁 Generated "
                            f"{len(new_artifacts)} file(s)"
                        )


                        for artifact in new_artifacts:

                            file_name = artifact.get(
                                "file_name"
                            )

                            if not file_name:
                                continue


                            download_url = (
                                f"{API_BASE_URL}"
                                f"/download/"
                                f"{st.session_state.session_id}"
                                f"/{file_name}"
                            )


                            try:

                                file_response = requests.get(
                                    download_url,
                                    timeout=30
                                )


                                if (
                                    file_response.status_code
                                    == 200
                                ):

                                    st.download_button(
                                        label=(
                                            f"⬇ Download "
                                            f"{file_name}"
                                        ),
                                        data=file_response.content,
                                        file_name=file_name,
                                        mime=(
                                            "application/"
                                            "octet-stream"
                                        ),
                                        key=(
                                            f"new_artifact_"
                                            f"{file_name}_"
                                            f"{uuid.uuid4()}"
                                        )
                                    )


                            except Exception:

                                st.warning(
                                    f"Could not load "
                                    f"{file_name}"
                                )


                    # --------------------------------------------
                    # SAVE MESSAGE LOCALLY
                    # --------------------------------------------

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": final_output
                    })


            except requests.exceptions.ConnectionError:

                st.error(
                    "❌ Cannot connect to backend API."
                )

                st.info(
                    "Start the backend using:\n\n"
                    "`py -m uvicorn backend.api:app --reload`"
                )


            except requests.exceptions.Timeout:

                st.error(
                    "⏳ Request timed out."
                )

                st.caption(
                    "The local Ollama model may still "
                    "be processing."
                )


            except Exception as error:

                st.error(
                    f"❌ Error: {str(error)}"
                )