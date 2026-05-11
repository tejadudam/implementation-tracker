import streamlit as st
import bcrypt
from db import get_connection
from auth import require_login, get_role
from utils.ui import top_bar
from utils.layout import render_sidebar

render_sidebar()
require_login()

# top_bar()

st.header("👤 User Management")

conn = get_connection()
cur = conn.cursor()

# 🔐 Only admin allowed
if get_role() != "admin":
    st.error("Access Denied")
    st.stop()

# ================= ADD USER =================
st.subheader("➕ Add User")

username = st.text_input("Username")
password = st.text_input("Password", type="password")
role = st.selectbox("Role", ["admin", "associate", "viewer"])

if st.button("Create User"):
    if not username or not password:
        st.warning("Fill all fields")
    else:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        try:
            cur.execute("""
                INSERT INTO users (username, password, role)
                VALUES (?, ?, ?)
            """, (username, hashed, role))
            conn.commit()
            st.success("User created")
        except:
            st.error("Username already exists")

# ================= USER LIST =================
st.subheader("👥 Existing Users")

users = cur.execute("SELECT id, username, role FROM users").fetchall()

for u in users:
    uid, uname, urole = u

    col1, col2, col3 = st.columns([3,2,1])

    with col1:
        st.write(uname)

    with col2:
        new_role = st.selectbox(
            "Role",
            ["admin", "associate", "viewer"],
            index=["admin", "associate", "viewer"].index(urole),
            key=f"role_{uid}"
        )

    with col3:
        if st.button("Update", key=f"update_{uid}"):
            cur.execute("UPDATE users SET role=? WHERE id=?", (new_role, uid))
            conn.commit()
            st.success("Updated")
            st.rerun()