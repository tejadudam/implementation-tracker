import streamlit as st
from utils.ui import top_bar
from db import get_connection
from datetime import datetime
from auth import get_current_user, get_role, require_login
from utils.layout import render_sidebar

render_sidebar()


# ================= INIT =================
require_login()
conn = get_connection()
cur = conn.cursor()

current_user = get_current_user()
user_role = get_role()

# top_bar()


clients = cur.execute("""
    SELECT id, name FROM clients
    ORDER BY id DESC
""").fetchall()

if not clients:
    st.error("No clients found.")
    st.stop()

client_options = {
    f"{c[1]} (ID:CLD{c[0]:04d})": c[0]
    for c in clients
}

selected_client_id = st.session_state.get("selected_client_id")

default_index = 0
if selected_client_id:
    for i, (name, cid) in enumerate(client_options.items()):
        if cid == selected_client_id:
            default_index = i
            break

selected_name = st.selectbox(
    "Select Client",
    options=list(client_options.keys()),
    index=default_index,
    key="client_selector"
)

client_id = client_options[selected_name]

client = cur.execute(
    "SELECT * FROM clients WHERE id=?",
    (client_id,)
).fetchone()

# ================= PERMISSIONS =================
is_owner = current_user == client[6]
is_admin = user_role == "admin"
can_modify = is_owner or is_admin

# ================= EDIT DIALOG =================
@st.dialog("✏️ Edit Entry")
def edit_entry_dialog(upd_id):

    data = cur.execute("""
        SELECT title, description, type, status
        FROM updates WHERE id=?
    """, (upd_id,)).fetchone()

    if not data:
        st.error("Not found")
        return

    title, desc, type_, status = data

    # 🔒 LOCK if done
    if status == "Done":
        st.warning("Cannot edit completed item ❌")
        return

    st.write(f"Editing: **{type_.upper()}**")

    new_title = st.text_input("Title", value=title)

    # 👇 MOM POINTS usually don't have description
    if type_ in ["update", "requirement"]:
        new_desc = st.text_area("Description", value=desc or "")
    else:
        new_desc = desc  # keep as is

    if st.button("💾 Save Changes"):

        if type_ in ["update", "requirement"]:
            cur.execute("""
                UPDATE updates
                SET title=?, description=?
                WHERE id=?
            """, (new_title, new_desc, upd_id))
        else:
            # 🔥 MOM / MOM POINT → only title
            cur.execute("""
                UPDATE updates
                SET title=?
                WHERE id=?
            """, (new_title, upd_id))

        conn.commit()
        st.success("Updated successfully")
        st.rerun()

# ================= CLOSE LOGIC =================
@st.dialog("✅ Close Task")
def close_task_dialog(upd_id):

    st.write("Add remarks before closing")

    remark = st.text_area("Remarks")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Confirm Close"):

            if not remark.strip():
                st.warning("Remark is required")
                return

            # ================= CLOSE MAIN =================
            cur.execute("""
                UPDATE updates
                SET status='Done',
                    closed_at=?,
                    remarks=?
                WHERE id=?
            """, (str(datetime.now()), remark, upd_id))

            # ================= MOM LOGIC =================
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
                        SET status='Done', closed_at=?
                        WHERE id=?
                    """, (str(datetime.now()), mom_id))

            conn.commit()

            st.success("Task closed successfully ✅")
            st.rerun()

    with col2:
        if st.button("Cancel"):
            st.rerun()


# ================= HEADER =================
client_code = client[11] if len(client) > 11 and client[11] else f"CLD{client[0]:04d}"
st.title(f"👤 {client[1]} ({client_code})")

# ================= STATUS =================
def render_status():
    st.subheader("📌 Client Status")

    activities = cur.execute("""
        SELECT type, status FROM updates WHERE client_id=?
    """, (client_id,)).fetchall()

    pending = sum(1 for a in activities if a[1] == "In Progress")

    col1, col2 = st.columns([3,1])

    with col1:
        st.write(f"⏳ Pending: {pending}")

        current = cur.execute("""
            SELECT title, created_at FROM updates
            WHERE client_id=? AND type='status'
            ORDER BY created_at DESC LIMIT 1
        """, (client_id,)).fetchone()

        if current:
            st.success(f"📢 {current[0]}")
            st.caption(f"Last updated: {current[1][:16]}")

    with col2:

        status = st.selectbox(
            "Update Status",
            ["New", "Dry Run", "Parallel", "Completed", "Hold"],
            index=["New","Dry Run","Parallel","Completed","Hold"].index(client[9])
        )
        cola, colb = st.columns(2)
        with cola:
            if st.button("💾 Update"):
                cur.execute("UPDATE clients SET status=? WHERE id=?", (status, client_id))
                conn.commit()
                st.rerun()
        with colb:
            if st.button("📂Client Info", key=f"edit_{client_id}"):
                st.session_state["edit_client_id"] = client_id
                st.switch_page("pages/create_client.py")

render_status()
st.divider()

# ================= ENTRY =================
def render_entry():
    with st.expander("➕ Add Entry", expanded=False):

        entry_type = st.selectbox("Type", ["Update", "MOM", "Requirement", "Status"])
        title = st.text_input("Title")

        desc = ""
        points = ""
        is_paid = False

        if entry_type == "Update":
            desc = st.text_area("Description")

        elif entry_type == "MOM":
            points = st.text_area("MOM Points")

        elif entry_type == "Requirement":
            desc = st.text_area("Description")
            is_paid = st.selectbox("Paid?", ["Free","Paid"]) == "Paid"

        if st.button("Save Entry"):

            if not title.strip():
                st.warning("Title required")
                return

            if entry_type == "Update":
                cur.execute("""
                    INSERT INTO updates (client_id,type,title,description,status,created_at,created_by)
                    VALUES (?, 'update', ?, ?, 'In Progress', ?, ?)
                """, (client_id,title,desc,str(datetime.now()),current_user))

            elif entry_type == "Requirement":
                cur.execute("""
                    INSERT INTO updates (client_id,type,title,description,status,is_paid,created_at,created_by)
                    VALUES (?, 'requirement', ?, ?, 'In Progress', ?, ?, ?)
                """, (client_id,title,desc,int(is_paid),str(datetime.now()),current_user))

            elif entry_type == "MOM":
                cur.execute("""
                    INSERT INTO updates (client_id,type,title,status,created_at,created_by)
                    VALUES (?, 'mom', ?, 'In Progress', ?, ?)
                """, (client_id,title,str(datetime.now()),current_user))
                mom_id = cur.lastrowid

                for p in points.split("\n"):
                    if p.strip():
                        cur.execute("""
                            INSERT INTO updates (client_id,parent_id,type,title,status,created_at,created_by)
                            VALUES (?, ?, 'mom_point', ?, 'In Progress', ?, ?)
                        """, (client_id,mom_id,p.strip(),str(datetime.now()),current_user))

            elif entry_type == "Status":
                cur.execute("""
                    INSERT INTO updates (client_id,type,title,status,created_at,created_by)
                    VALUES (?, 'status', ?, 'Done', ?, ?)
                """, (client_id,title,str(datetime.now()),current_user))

            conn.commit()
            st.success("Saved")
            st.rerun()

render_entry()

# ================= PENDING =================
def render_pending():
    with st.expander(f"⏳ Pending Tasks", expanded=True):

        rows = cur.execute("""
            SELECT 
                u.id, u.title, u.type, u.created_at, u.status, u.description,
                u.parent_id,
                p.title as parent_title
            FROM updates u
            LEFT JOIN updates p ON u.parent_id = p.id
            WHERE u.client_id=? AND u.status!='Done' AND u.type!='mom'
            ORDER BY datetime(u.created_at) DESC
        """, (client_id,)).fetchall()

        if not rows:
            st.success("No pending tasks 🎉")
            return

        for r in rows:
            id_, title, type_, created, status, desc, parent_id, parent_title = r

            # 🔹 Better display for MOM points
            display_title = title if title else (desc or "No title")

            col1, col2, col3, col4 = st.columns([1,3,1,1])

            with col2:
                st.write(f"**{display_title.strip()}**")
                if desc and type_ != "mom_point":
                    st.caption(desc)

            with col1:

                if type_ == "mom_point":
                    label = f"MOM: {parent_title}" if parent_title else "MOM"

                elif type_ == "update":
                    label = "Update"

                elif type_ == "requirement":
                    label = "Requirement"

                elif type_ == "feature_log":
                    label = "Feature"

                elif type_ == "status":
                    label = "Status"

                else:
                    label = type_

                st.write(label)

            with col3:
                st.write(created[:16])


            with col4:
                if can_modify and status != "Done":
                    
                    colA, colB = st.columns(2)
                    
                    with colA:
                        if st.button("✏️", key=f"edit_{id_}"):
                            edit_entry_dialog(id_)
                    with colB:
                        if st.button("✅", key=f"close_{id_}"):
                            close_task_dialog(id_)

            st.divider()

render_pending()

#=================== Timeline =================
st.markdown("""
<style>
.card {
    padding: 12px;
    border-radius: 10px;
    margin-bottom: 10px;
}

.update { background-color: #e3f2fd; }      /* Blue */
.requirement { background-color: #f3e5f5; } /* Purple */
.mom { background-color: #fff8e1; }         /* Yellow */
.status { background-color: #e8f5e9; }      /* Green */
.feature_log { background-color: #ede7f6; } /* Violet */

/* MOM child styling */
.mom-child {
    margin-left: 15px;
    padding: 10px;
    border-left: 3px solid #fbc02d;
    margin-top: 8px;
    background-color: #fffde7;
    border-radius: 6px;
}
            

/* 🎯 Expander Header Styling */
[data-testid="stExpander"] > div:first-child {
    background-color: #fff8e1 !important;  /* MOM Yellow */
    border-radius: 10px;
    padding: 10px;
    font-weight: 600;
    border: 1px solid #fbc02d;
}

/* Remove default gap */
[data-testid="stExpander"] {
    border: none !important;
}

/* Expander content area */
[data-testid="stExpander"] > div:nth-child(2) {
    background-color: #fffde7;
    border-radius: 10px;
    padding: 10px;
    margin-top: 5px;
}

.small {
    font-size: 12px;
    color: gray;
}
</style>
""", unsafe_allow_html=True)


# ================= TIMELINE =================
from collections import defaultdict

def render_timeline():
    with st.expander("📜 Timeline", expanded=True):

        rows = cur.execute("""
            SELECT id, parent_id, type, title, status, created_at, description, remarks
            FROM updates
            WHERE client_id=?
            ORDER BY datetime(created_at) DESC
        """, (client_id,)).fetchall()

        # ================= STEP 1: BUILD MOM STRUCTURE =================
        moms = {}
        children_map = {}
        others = []

        for r in rows:
            id_, parent_id, type_, title, status, created, desc, remarks = r

            if type_ == "mom":
                moms[id_] = {
                    "id": id_,
                    "title": title,
                    "status": status,
                    "created": created
                }

            elif type_ == "mom_point":
                if parent_id:
                    children_map.setdefault(parent_id, []).append(r)

            else:
                others.append(r)

        # ================= STEP 2: GROUP BY DATE =================
        grouped_by_date = defaultdict(list)

        for r in rows:
            date = r[5][:10]
            grouped_by_date[date].append(r)

        # ================= STEP 3: RENDER =================
        for date in sorted(grouped_by_date.keys(), reverse=True):

            st.markdown(f"### 📅 {date}")

            day_rows = grouped_by_date[date]

            rendered_moms = set()

            for r in day_rows:
                id_, parent_id, type_, title, status, created, desc, remarks = r

                # ---------- NORMAL ----------
                if type_ not in ["mom", "mom_point"]:
                    
                    st.markdown(f"""
                    <div class="card {type_}">
                    <span class="small">{created[11:16]} | {status}</span><br>
                    <b>{type_.upper()}:</b> {title}<br>
                    {desc or ""} {("- " + remarks) if remarks else ""}                    
                    </div>
                    """, unsafe_allow_html=True)

                # ---------- MOM ----------
                elif type_ == "mom" and id_ not in rendered_moms:

                    with st.expander(f" MOM: {title} ({status})"):
                        
                        st.caption(created[11:16])

                        children = children_map.get(id_, [])

                        # 🔥 SORT CHILDREN BY TIME (important fix)
                        children = sorted(children, key=lambda x: x[5])

                        for child in children:
                            cid, _, _, ctitle, cstatus, ccreated, cdesc, cremarks = child

                            st.markdown(f"""
                            <div class="mom-child">
                            🔹 {ctitle} <b>({cstatus})</b><br>
                            {cdesc or ""} {("- " + cremarks) if cremarks else ""}<br>
                            </div>
                            """, unsafe_allow_html=True)

                    

                    rendered_moms.add(id_)

            st.divider()

render_timeline()