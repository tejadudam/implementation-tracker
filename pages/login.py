import streamlit as st
from auth import login_user

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
    </style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="Login", layout="centered")

# ------------------ SESSION CHECK ------------------
# If already logged in → go to app
if "user_id" in st.session_state:
    st.switch_page("app.py")

# ------------------ UI ------------------
st.markdown("<h1 style='text-align: center;'>🔐 Login</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: grey;'>Implementation Tracker</p>", unsafe_allow_html=True)

st.divider()

# Centered layout
col1, col2, col3 = st.columns([1,2,1])

with col2:

    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")

    st.write("")

    # ------------------ LOGIN BUTTON ------------------
    if st.button("Login", use_container_width=True):

        if not username or not password:
            st.warning("Please enter username and password")
            st.stop()

        if login_user(username, password):
            st.success("Login successful")

            # 🔥 redirect to main app
            st.switch_page("app.py")

        else:
            st.error("Invalid username or password")

    st.write("")
    st.caption("Default login → admin / admin")