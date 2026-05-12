import streamlit as st
from utils.ui import top_bar
from db import get_connection, init_db
from auth import require_login, get_current_user, get_role
from utils.ui import hide_sidebar
from utils.layout import render_sidebar

render_sidebar()

# ================= INIT =================
st.set_page_config(page_title="Tracker App", layout="wide")
require_login()
init_db()

# ================= SESSION =================
if "selected_client_id" not in st.session_state:
    st.session_state["selected_client_id"] = None


conn = get_connection()
cur = conn.cursor()

current_user = get_current_user()
user_role = get_role()


# ================= CLOSE TASK DIALOG =================
@st.dialog("Close Task")
def close_task_dialog(upd_id):

    remarks = st.text_area("Add remarks before closing")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Confirm"):

            cur.execute("""
                UPDATE updates
                SET status='Done',
                    closed_at=datetime('now'),
                    remarks=?
                WHERE id=?
            """, (remarks, upd_id))

            parent = cur.execute("""
                SELECT parent_id FROM updates WHERE id=?
            """, (upd_id,)).fetchone()

            if parent and parent[0]:
                mom_id = parent[0]

                pending_child = cur.execute("""
                    SELECT COUNT(*) FROM updates
                    WHERE parent_id=? AND status!='Done'
                """, (mom_id,)).fetchone()[0]

                if pending_child == 0:
                    cur.execute("""
                        UPDATE updates
                        SET status='Done',
                            closed_at=datetime('now')
                        WHERE id=?
                    """, (mom_id,))

            type_check = cur.execute("""
                SELECT type FROM updates WHERE id=?
            """, (upd_id,)).fetchone()

            if type_check and type_check[0] == "mom":
                cur.execute("""
                    UPDATE updates
                    SET status='Done',
                        closed_at=datetime('now')
                    WHERE parent_id=?
                """, (upd_id,))

            conn.commit()
            st.success("Closed successfully")
            st.rerun()

    with col2:
        if st.button("Cancel"):
            st.rerun()

# top_bar()

# ================= FETCH DATA (OPTIMIZED) =================
clients = cur.execute("SELECT * FROM clients").fetchall()

activities = cur.execute("""
    SELECT client_id, type, status 
    FROM updates
""").fetchall()

# ---- Precompute maps ----
pending_map = {}
latest_map = {}

for a in activities:
    cid, typ, status = a

    if status != "Done":
        pending_map[cid] = pending_map.get(cid, 0) + 1

# Latest updates (single query instead of per client)
latest_data = cur.execute("""
    SELECT u.client_id, u.title, u.created_at
    FROM updates u
    WHERE u.type='status'
    AND u.created_at = (
        SELECT MAX(created_at)
        FROM updates
        WHERE client_id = u.client_id AND type='status'
    )
""").fetchall()

latest_map = {
    cid: (f"📢 {title}", created_at)
    for cid, title, created_at in latest_data
}


# ================= COUNTS =================
total_clients = len(clients)
New = sum(1 for c in clients if c[9] == "New")
Dry_Run = sum(1 for c in clients if c[9] == "Dry Run")
Parallel = sum(1 for c in clients if c[9] == "Parallel")
hold = sum(1 for c in clients if c[9] == "Hold")
completed = sum(1 for c in clients if c[9] == "Completed")

pending_updates = sum(1 for a in activities if a[2] == "In Progress")
feature_logs = sum(1 for a in activities if a[1] == "feature_log" and a[2] == "In Progress")
update = sum(1 for a in activities if a[1] == "update" and a[2] == "In Progress")
requirement = sum(1 for a in activities if a[1] == "requirement" and a[2] == "In Progress")
mom = sum(1 for a in activities if a[1] == "mom_point" and a[2] == "In Progress")

# ================= TOP SECTION =================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📌 Client Overview")
    st.write(f"**Total Clients:** {total_clients}")
    st.write(f"🟣 New: {New}")
    st.write(f"🟡 Dry Run: {Dry_Run}")
    st.write(f"🔵 Parallel: {Parallel}")
    st.write(f"⏸️ Hold: {hold}")
    st.write(f"✅ Completed: {completed}")

with col2:
    st.subheader("⚡ Action Required")
    st.write(f"⏳ Pending Updates: {pending_updates}")
    st.write(f"📋 Feature Logs: {feature_logs}")
    st.write(f"📝 Updates: {update}")
    st.write(f"📄 Requirements: {requirement}")
    st.write(f"📊 MOM Points: {mom}")

st.divider()

# ================= CLIENT LIST =================
st.subheader("👥 Clients")

if not clients:
    st.info("No clients found. Please create one.")
else:
    for c in clients:
        client_id = c[0]
        client_code = c[11] if len(c) > 11 and c[11] else f"CLD{c[0]:04d}"
        client_name = c[1]
        status = c[9]

        pending = pending_map.get(client_id, 0)

        latest_text, latest_date = latest_map.get(client_id, ("No updates yet", ""))

        if latest_date:
            latest_date = latest_date[:16]

        with st.container(height=100):
            col1, col2, col3, col4, col5 = st.columns([3,1,1,3,3])

            with col1:
                st.markdown(f"##### {client_name}")
                st.caption(client_code)

            with col2:
                st.write(f"Status: **{status}**")

            with col3:
                st.write(f"Pending: **{pending}**")

            with col4:
                st.write(f"Latest: {latest_text}")
                if latest_date:
                    st.caption(latest_date)

            with col5:
                cola, colb = st.columns(2)

                with cola:
                    if st.button("➡️ Go to Client", key=f"go_{client_id}"):
                        st.session_state["selected_client_id"] = client_id
                        st.switch_page("pages/client_detail.py")

                with colb:
                    if st.button("✏️ Edit", key=f"edit_{client_id}"):
                        st.session_state["edit_client_id"] = client_id
                        st.switch_page("pages/create_client.py")

st.divider()

from collections import defaultdict

st.subheader("⏳ Pending Tasks (Quick Actions)")

# ---------- FILTER ----------
show_my_tasks = st.toggle("👤 My Tasks Only")

# ---------- FETCH ----------
pending_tasks = cur.execute("""
    SELECT u.id, u.client_id, u.title, u.description, u.parent_id, u.type,
           p.title as parent_title,
           c.name,
           c.owner,
           u.created_at
    FROM updates u
    LEFT JOIN updates p ON u.parent_id = p.id
    LEFT JOIN clients c ON u.client_id = c.id
    WHERE u.status!='Done'
    ORDER BY datetime(u.created_at) DESC
""").fetchall()

# ---------- FILTER ----------
if show_my_tasks:
    pending_tasks = [
        p for p in pending_tasks
        if p[8] == current_user or user_role == "admin"
    ]

if not pending_tasks:
    st.success("No pending tasks 🎉")
    st.stop()

# ================= HEADER =================
col1, col2, col3, col4, col5 = st.columns([1,2,4,1,1])

with col1:
    st.markdown("**Client**")
with col2:
    st.markdown("**Type**")
with col3:
    st.markdown("**Task**")
with col4:
    st.markdown("**Action**")

st.write("")  # Empty for spacing
# ================= ROWS =================
for p in pending_tasks:

    upd_id, client_id, title, desc, parent_id, type_, parent_title, client_name, client_owner, created = p

    can_modify = (current_user == client_owner) or (user_role == "admin")

    # ---------- TYPE LABEL ----------
    if type_ == "mom_point":
        type_label = f"MOM: {parent_title}" if parent_title else "MOM"
    elif type_ == "update":
        type_label = "Update"
    elif type_ == "requirement":
        type_label = "Requirement"
    elif type_ == "feature_log":
        type_label = "Feature"
    else:
        type_label = "Other"

    # ---------- TITLE ----------
    if type_ != "mom":
        display_title = title if title else (desc or "")

        col1, col2, col3, col4, col5 = st.columns([1,2,4,1,1])

        with col1:
            st.write(client_name or "Client")

        with col2:
            st.write(type_label)

        with col3:
            st.write(f"**{display_title.strip()}**")
            if desc and type_ != "mom_point":
                st.caption(desc)

        with col4:
            if can_modify:
                if st.button("✅ Close", key=f"close_{upd_id}"):
                    close_task_dialog(upd_id)
            else:
                st.button("✅", key=f"dis_{upd_id}", disabled=True)

        with col5:
            if st.button("🔍 Navigate", key=f"nav_{upd_id}"):
                st.session_state["selected_client_id"] = client_id
                st.switch_page("pages/client_detail.py")

        st.divider()
