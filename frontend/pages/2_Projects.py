import streamlit as st
import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Projects", page_icon="📁")
from frontend.auth_helper import check_auth
check_auth()

st.title("📁 Projects Dashboard")
st.markdown("Manage multiple users, tasks, and project sessions.")

st.subheader("Create New Project")
with st.form("new_project"):
    name = st.text_input("Project Name")
    desc = st.text_area("Description")
    if st.form_submit_button("Create"):
        r = requests.post(f"{API_BASE_URL}/projects", data={"name": name, "description": desc})
        if r.status_code == 200:
            st.success("Project created!")

st.divider()
st.subheader("Active Projects")

try:
    r = requests.get(f"{API_BASE_URL}/projects")
    if r.status_code == 200:
        projects = r.json()
        if not projects:
            st.info("No projects created yet.")
        else:
            for p in projects:
                with st.expander(f"📁 {p['name']} (Created: {p['created_at'][:10]})"):
                    st.write(p["description"])
                    st.button("View Tasks", key=f"view_{p['id']}")
except Exception as e:
    st.error("Failed to load projects.")
