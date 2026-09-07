import streamlit as st
import requests
import os

try:
    import pynvml
    pynvml.nvmlInit()
    HAS_GPU = True
except Exception:
    HAS_GPU = False

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="System Status", page_icon="🖥️")
from frontend.auth_helper import check_auth
check_auth()

st.title("🖥️ System Status")

col1, col2 = st.columns(2)

with col1:
    st.subheader("GPU Status")
    if HAS_GPU:
        device_count = pynvml.nvmlDeviceGetCount()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            used_gb = mem.used / (1024**3)
            total_gb = mem.total / (1024**3)
            
            st.metric(f"GPU {i}: {name}", f"{used_gb:.2f} GB / {total_gb:.2f} GB")
            st.progress(mem.used / mem.total)
    else:
        st.warning("No NVIDIA GPU detected or pynvml failed to initialize.")

with col2:
    st.subheader("Model Engine")
    try:
        r = requests.get(f"{API_BASE_URL}/models/list")
        if r.status_code == 200:
            models = r.json()
            st.write(f"**Loaded Models:** {len(models)}")
            for m in models:
                st.caption(f"- {m['id']} ({m['provider']})")
    except:
        st.error("Failed to connect to backend engine.")

st.divider()

st.subheader("Network Security Sentry")
try:
    r = requests.get(f"{API_BASE_URL}/sentry/status")
    if r.status_code == 200:
        st.json(r.json())
except:
    st.error("Network Sentry Offline")
