import streamlit as st
from db import init_db
from auth import require_login
from utils.layout import render_sidebar
from utils.ui import top_bar

# ================= CONFIG =================
st.set_page_config(page_title="Tracker App", layout="wide")

# ================= INIT =================
init_db()

# ================= LOGIN =================
require_login()

# ================= SESSION INIT =================
if "selected_client_id" not in st.session_state:
    st.session_state["selected_client_id"] = None

if "edit_client_id" not in st.session_state:
    st.session_state["edit_client_id"] = None

# ================= UI =================
render_sidebar()


# ================= HOME CONTENT =================
st.markdown("### 👋 Welcome to Implementation Tracker")

st.info("Use the sidebar to navigate 🚀")

col1, col2 = st.columns(2)

with col1:
    if st.button("🏠 Go to Dashboard"):
        st.switch_page("pages/dashboard.py")

with col2:
    if st.button("➕ Create Client"):
        st.session_state["edit_client_id"] = None
        st.switch_page("pages/create_client.py")