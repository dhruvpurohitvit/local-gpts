import yaml
from yaml.loader import SafeLoader
import streamlit as st
import streamlit_authenticator as stauth
import os

def check_auth():
    auth_file = os.path.join(os.path.dirname(__file__), "auth.yaml")
    with open(auth_file) as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

    try:
        authenticator.login()
    except Exception as e:
        st.error(e)
        st.stop()

    if st.session_state.get("authentication_status"):
        authenticator.logout('Logout', 'sidebar')
        st.sidebar.write(f"👤 Logged in as *{st.session_state.get('name', 'User')}*")
        return True
    elif st.session_state.get("authentication_status") is False:
        st.error("❌ Username or password is incorrect.")
        st.stop()
    else:
        st.warning("👋 Please enter your username and password to continue.")
        st.stop()

    return False
