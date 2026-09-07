import os
import subprocess
import time
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Model Hub - Sovereign AI", page_icon="📦", layout="wide")
from frontend.auth_helper import check_auth
check_auth()

st.title("📦 Model Hub")
st.caption("Search, download, and manage local models — LM Studio style.")

tab_search, tab_local, tab_pull = st.tabs(["🔍 HuggingFace Search", "💾 Downloaded / Local Models", "⚡ One-Click Pull"])

# ==========================================
# TAB 1: HUGGINGFACE SEARCH & DOWNLOAD
# ==========================================
with tab_search:
    with st.expander("🔑 Hugging Face Token (Optional - for Gated Models like Llama-3, Gemma)"):
        hf_token = st.text_input("Access Token", type="password", help="Required only for gated models")

    col_q, col_btn = st.columns([4, 1])
    with col_q:
        query = st.text_input("Search Hugging Face Models", value="Qwen", placeholder="e.g. Qwen, Llama-3, Mistral, Gemma")
    with col_btn:
        st.write("")
        st.write("")
        do_search = st.button("🔍 Search Hub", use_container_width=True)

    if do_search:
        with st.spinner("Searching Hugging Face..."):
            try:
                r = requests.get(f"{API_BASE_URL}/models/search", params={"q": query, "hf_token": hf_token})
                if r.status_code == 200:
                    results = r.json()
                    st.session_state["hf_search_results"] = results
                else:
                    st.error(f"Search request failed: {r.status_code}")
            except Exception as e:
                st.error(f"Cannot reach backend API: {e}")

    # Active downloads live tracker at the top
    active_dls = [k for k in list(st.session_state.keys()) if k.startswith("active_dl_")]
    if active_dls:
        st.divider()
        st.subheader("📥 Active Download Progress")
        for k in active_dls:
            dl_id = k.replace("active_dl_", "")
            fname = st.session_state[k]
            try:
                r_prog = requests.get(f"{API_BASE_URL}/models/download/progress/{dl_id}")
                if r_prog.status_code == 200:
                    prog = r_prog.json()
                    status = prog.get("status", "unknown")
                    pct = prog.get("progress", 0)
                    dl_mb = prog.get("downloaded_mb", "0.0 MB")
                    tot_mb = prog.get("total_mb", "Unknown")
                    
                    if status == "downloading":
                        st.write(f"⏳ **Downloading `{fname}`**: {dl_mb} / {tot_mb} ({pct}%)")
                        st.progress(pct / 100.0)
                        time.sleep(1)
                        st.rerun()
                    elif status == "completed":
                        st.success(f"✅ **Download Complete!** `{fname}` ({dl_mb}) is now saved to your local `models/downloads` folder!")
                        if st.button(f"Dismiss `{fname}` Notification", key=f"dismiss_{dl_id}"):
                            del st.session_state[k]
                            st.rerun()
                    elif status == "error":
                        st.error(f"❌ **Download Failed** for `{fname}`: {prog.get('error')}")
                        if st.button(f"Dismiss Error", key=f"dismiss_err_{dl_id}"):
                            del st.session_state[k]
                            st.rerun()
            except Exception as e:
                st.caption(f"Waiting for status: {e}")

    # Display search results
    results = st.session_state.get("hf_search_results", [])
    if results:
        st.divider()
        st.write(f"Found **{len(results)}** models:")
        for m in results:
            if not isinstance(m, dict) or "id" not in m:
                continue
            repo_id = m["id"]
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"### `{repo_id}`")
                    st.caption(f"⬇️ {m.get('downloads', 0):,} downloads | ❤️ {m.get('likes', 0):,} likes | Tag: `{m.get('pipeline_tag', 'text-generation')}`")
                with c2:
                    is_selected = st.session_state.get("selected_repo") == repo_id
                    btn_label = "📂 Close Files" if is_selected else "📂 View Files"
                    if st.button(btn_label, key=f"toggle_{repo_id}"):
                        if is_selected:
                            st.session_state["selected_repo"] = None
                        else:
                            st.session_state["selected_repo"] = repo_id
                        st.rerun()

                # If selected, show file browser right inside this card!
                if st.session_state.get("selected_repo") == repo_id:
                    st.divider()
                    st.markdown(f"**Available Model Files in `{repo_id}`:**")
                    with st.spinner("Fetching repo file tree..."):
                        r_files = requests.get(f"{API_BASE_URL}/models/files", params={"repo_id": repo_id, "hf_token": hf_token})
                        if r_files.status_code == 200:
                            files = r_files.json()
                            if not files:
                                st.warning("No `.gguf` or `.safetensors` model weights found in this repository.")
                            else:
                                for fname in files:
                                    fc1, fc2 = st.columns([4, 1])
                                    with fc1:
                                        st.code(fname, language=None)
                                    with fc2:
                                        dl_key = f"dl_{repo_id}_{fname}"
                                        if st.button(f"⬇️ Download", key=dl_key):
                                            dl_res = requests.post(
                                                f"{API_BASE_URL}/models/download",
                                                data={"repo_id": repo_id, "filename": fname, "hf_token": hf_token}
                                            )
                                            if dl_res.status_code == 200:
                                                dl_id = dl_res.json()["download_id"]
                                                st.session_state[f"active_dl_{dl_id}"] = fname
                                                st.success(f"Started downloading `{fname}`!")
                                                st.rerun()
                        else:
                            st.error(f"Failed to fetch files ({r_files.status_code})")

# ==========================================
# TAB 2: LOCAL / DOWNLOADED MODELS
# ==========================================
with tab_local:
    col_l1, col_l2 = st.columns([3, 1])
    with col_l1:
        st.subheader("💾 Ready to Run Local Models")
        st.caption("All models loaded in Ollama/vLLM or downloaded to disk ready for use.")
    with col_l2:
        if st.button("🔄 Refresh Local List", use_container_width=True):
            st.rerun()

    # Section A: Live engine models (ready to chat immediately)
    st.markdown("### 🟢 Active in Inference Engine (Ready to Chat)")
    try:
        r_models = requests.get(f"{API_BASE_URL}/models/list")
        if r_models.status_code == 200:
            local_models = r_models.json()
            if not local_models:
                st.info("No models currently loaded in Ollama or vLLM.")
            else:
                for lm in local_models:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 2, 2])
                        with c1:
                            st.markdown(f"#### 🧠 `{lm['id']}`")
                        with c2:
                            st.caption(f"Provider: **{lm.get('provider', 'Local')}** | Size: **{lm.get('size', 'N/A')}**")
                        with c3:
                            st.success("🟢 Ready to Run")
    except Exception as e:
        st.error(f"Cannot connect to backend: {e}")

    st.divider()

    # Section B: Raw downloaded files in models/downloads/
    st.markdown("### 📁 Downloaded Weights on Disk (`models/downloads/`)")
    try:
        r_dl = requests.get(f"{API_BASE_URL}/models/downloaded")
        if r_dl.status_code == 200:
            downloaded_files = r_dl.json()
            if not downloaded_files:
                st.caption("No custom model files downloaded yet.")
            else:
                for df in downloaded_files:
                    with st.container(border=True):
                        d1, d2, d3 = st.columns([3, 2, 2])
                        with d1:
                            st.markdown(f"**`{df['filename']}`**")
                        with d2:
                            st.caption(f"Format: **{df['type']}** | Size: **{df['size']}**")
                        with d3:
                            load_key = f"load_{df['filename']}"
                            model_tag = df['filename'].rsplit('.', 1)[0].lower().replace('_', '-').replace('.', '-')
                            
                            if st.button(f"⚡ Load as `{model_tag}`", key=load_key):
                                with st.spinner(f"Registering `{df['filename']}` into local engine..."):
                                    try:
                                        # Create Modelfile pointing directly to this downloaded weight
                                        dl_dir = os.path.abspath("models/downloads")
                                        modelfile_name = f"Modelfile.{model_tag}"
                                        modelfile_path = os.path.join(dl_dir, modelfile_name)
                                        with open(modelfile_path, "w", encoding="utf-8") as mf:
                                            mf.write(f"FROM ./{df['filename']}\n")
                                        
                                        # Run ollama create
                                        res = subprocess.run(
                                            ["ollama", "create", model_tag, "-f", modelfile_name],
                                            capture_output=True,
                                            cwd=dl_dir,
                                            timeout=180
                                        )
                                        if os.path.exists(modelfile_path):
                                            os.remove(modelfile_path)
                                            
                                        if res.returncode == 0:
                                            st.success(f"✅ `{model_tag}` is now loaded & ready to run in Chat!")
                                            st.rerun()
                                        else:
                                            err_msg = res.stderr.decode('utf-8', errors='replace') if res.stderr else "Unknown error"
                                            if "safetensors" in df['filename'].lower():
                                                st.warning(f"Note: Single `.safetensors` files require full tokenizer configs to run directly. Tip: Download **`.gguf`** files from HuggingFace (e.g. search `Qwen GGUF` or `Llama GGUF`) — they are self-contained and load instantly with 1 click!")
                                            st.error(f"Engine response: {err_msg}")
                                    except Exception as ex:
                                        st.error(f"Load error: {ex}")
    except Exception as e:
        st.caption(f"Could not load disk files: {e}")

# ==========================================
# TAB 3: ONE-CLICK PULL
# ==========================================
with tab_pull:
    st.subheader("⚡ Quick Pull Popular Models")
    st.caption("One-click install standard open-source models into your local engine.")
    
    popular_models = [
        {"name": "qwen2.5:3b", "desc": "Fast, high quality general purpose assistant (1.8 GB)"},
        {"name": "qwen2.5-coder:3b", "desc": "Specialized code generation & debugging (1.8 GB)"},
        {"name": "llama3.2:3b", "desc": "Meta Llama 3.2 lightweight model (2.0 GB)"},
        {"name": "mistral:7b", "desc": "Standard general reasoning 7B model (4.1 GB)"},
        {"name": "phi3:mini", "desc": "Microsoft lightweight high performance 3.8B model (2.2 GB)"},
    ]

    for pm in popular_models:
        with st.container(border=True):
            p1, p2 = st.columns([3, 1])
            with p1:
                st.markdown(f"**`{pm['name']}`**")
                st.caption(pm["desc"])
            with p2:
                if st.button(f"⬇️ Pull Model", key=f"pull_{pm['name']}"):
                    prog_box = st.empty()
                    prog_box.info(f"⏳ Pulling `{pm['name']}` from registry...")
                    try:
                        res = subprocess.run(["ollama", "pull", pm["name"]], capture_output=True, text=True)
                        if res.returncode == 0:
                            prog_box.success(f"✅ Successfully pulled `{pm['name']}`! Ready to chat.")
                            st.rerun()
                        else:
                            prog_box.error(f"Error pulling model: {res.stderr}")
                    except Exception as ex:
                        prog_box.error(f"Error: {ex}")
