import streamlit as st
from db import get_connection
from auth import get_current_user, logout

def top_bar():
    col1, col2 = st.columns([8,1])

    with col1:
        st.markdown(f"#### 🚀 Implementation Tracker | 👤 {get_current_user()}")

    with col2:
        cola, colb = st.columns(2)
        with colb:
            if st.button("⏻"):
                logout()
                st.rerun()
        
        with cola:
            if st.button("⚡"):
                quick_update_dialog()
    
    st.divider()


# Floating Action Button
def floating_button():
    fab_container = st.container()

    # Inject CSS ONCE
    st.markdown("""
    <style>
    .fab-wrap {
        position: fixed;
        bottom: 25px;
        right: 25px;
        z-index: 9999;
    }

    .fab-wrap button {
        height: 60px !important;
        width: 60px !important;
        border-radius: 50% !important;
        font-size: 28px !important;
        background-color: #ff4b4b !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }

    .fab-wrap button:hover {
        transform: scale(1.1);
        transition: 0.2s;
    }
    </style>
    """, unsafe_allow_html=True)

    with fab_container:
        st.markdown('<div class="fab-wrap">', unsafe_allow_html=True)
        clicked = st.button("➕", key="fab_button")
        st.markdown('</div>', unsafe_allow_html=True)

    return clicked

# ================= QUICK UPDATE DIALOG =================
@st.dialog("⚡ Quick Update")
def quick_update_dialog():

    conn = get_connection()
    cur = conn.cursor()
    current_user = get_current_user()

    # ---------- CLIENT LIST ----------
    clients = cur.execute("""
        SELECT id, client_code, name FROM clients ORDER BY name
    """).fetchall()

    if not clients:
        st.warning("No clients available. Create a client first.")
        return

    client_options = {
        f"{c[2]} (ID:{c[1] or f'CLD{c[0]:04d}'})": c[0]
        for c in clients
    }

    selected_name = st.selectbox(
        "Select Client",
        options=list(client_options.keys())
    )

    if not selected_name:
        return

    client_id = client_options.get(selected_name)

    if not client_id:
        st.warning("Invalid client selection")
        return

    # ---------- TYPE ----------
    entry_type = st.selectbox("Type", ["Status", "Update"])

    # ---------- INPUTS ----------
    title = st.text_input("Title")
    description = st.text_area("Description")

    # ---------- SAVE ----------
    if st.button("💾 Save"):

        if not title.strip():
            st.warning("Title is required")
            return

        if entry_type == "Status":
            cur.execute("""
                INSERT INTO updates
                (client_id, type, title, description, status, created_at, created_by)
                VALUES (?, 'status', ?, ?, 'Done', datetime('now'), ?)
            """, (client_id, title, description, current_user))

        else:
            cur.execute("""
                INSERT INTO updates
                (client_id, type, title, description, status, created_at, created_by)
                VALUES (?, 'update', ?, ?, 'In Progress', datetime('now'), ?)
            """, (client_id, title, description, current_user))

        conn.commit()
        st.success("Added successfully ⚡")
        st.rerun()

def hide_sidebar():
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {display: none;}
        </style>
    """, unsafe_allow_html=True)