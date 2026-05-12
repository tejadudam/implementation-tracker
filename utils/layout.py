import streamlit as st
from auth import get_current_user, logout, get_role


def render_sidebar():
    user = get_current_user()
    role = get_role()

    # ---------- HIDE DEFAULT ----------
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

    # ---------- SIDEBAR STYLE ----------
    st.markdown("""
        <style>
        section[data-testid="stSidebar"] {
            background-color: #0e1117;
            padding-top: 10px;
        }

        .sidebar-title {
            color: white;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .nav-btn button {
            width: 100%;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 6px;
            background-color: transparent;
            color: white;
            border: 1px solid #2a2f3a;
        }

        .nav-btn button:hover {
            background-color: #262730;
            border: 1px solid #4CAF50;
        }

        .user-box {
            background-color: #262730;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 15px;
            color: white;
        }

        .logout-btn button {
            width: 100%;
            background-color: #ff4b4b;
            color: white;
            border-radius: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

    # ---------- USER INFO ----------
    st.sidebar.markdown(f"""
        <div class="user-box">
        👤 {user}, {role}        
        </div>
    """, unsafe_allow_html=True)

    # ---------- NAVIGATION ----------
    st.sidebar.markdown('<div class="sidebar-title">Navigation</div>', unsafe_allow_html=True)

    with st.sidebar:
        with st.container():
            st.markdown('<div class="nav-btn">', unsafe_allow_html=True)

            if st.button("🏠 Dashboard"):
                st.switch_page("pages/dashboard.py")

            if st.button("➕ Create Client"):
                st.session_state["edit_client_id"] = None
                st.switch_page("pages/create_client.py")

            if st.button("📂 Client Details"):
                st.switch_page("pages/client_detail.py")

            if role == "admin":
                if st.button("👥 User Management"):
                    st.switch_page("pages/user_management.py")

            st.markdown('</div>', unsafe_allow_html=True)

    # ---------- QUICK ACTIONS ----------
    st.sidebar.markdown("---")

    cola, colb = st.sidebar.columns(2)
    with colb:
        if st.button("⚡Update"):
            from utils.ui import quick_update_dialog
            quick_update_dialog()

    with cola:
        if st.button("⏻ Logout"):
            logout()
            st.rerun()
