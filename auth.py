import streamlit as st
import bcrypt
from db import get_connection

def login_user(username, password):
    conn = get_connection()
    cur = conn.cursor()

    user = cur.execute("""
        SELECT id, username, password, role
        FROM users WHERE username=?
    """, (username,)).fetchone()

    conn.close()

    if user and bcrypt.checkpw(password.encode(), user[2].encode()):
        st.session_state["user_id"] = user[0]
        st.session_state["username"] = user[1]
        st.session_state["role"] = user[3]
        return True
    return False


def logout():
    for key in ["user_id", "username", "role"]:
        st.session_state.pop(key, None)


def require_login():
    if "user_id" not in st.session_state:
        st.switch_page("pages/login.py")


def get_current_user():
    return st.session_state.get("username")


def get_role():
    return st.session_state.get("role")

def is_admin():
    return st.session_state.get("role") == "admin"

def is_associate():
    return st.session_state.get("role") == "associate"

def is_viewer():
    return st.session_state.get("role") == "viewer"