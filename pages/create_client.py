import streamlit as st
import pandas as pd
from utils.ui import top_bar
from db import get_connection
from datetime import datetime
from auth import require_login
from utils.layout import render_sidebar

render_sidebar()

require_login()

# top_bar()

conn = get_connection()
cur = conn.cursor()

current_user = st.session_state.get("username")
role = st.session_state.get("role")


col1, col2 = st.columns([6,1])

with col1:
    # ================= MODE =================
    edit_id = st.session_state.get("edit_client_id")

    if edit_id:
        st.header("✏️ Edit Client")
        client = cur.execute("SELECT * FROM clients WHERE id=?", (edit_id,)).fetchone()
    else:
        st.header("➕ Create New Client")
        client = None

# ================= MODE SWITCH =================


with col2:
    if edit_id:
        if st.button("➕ New"):
            st.session_state["edit_client_id"] = None
            st.rerun()

# ================= PERMISSIONS =================
def can_edit(client_owner):
    if role == "admin":
        return True
    if role == "associate":
        return current_user == client_owner
    return False

client_owner = client[7] if client else None
editable = can_edit(client_owner)

if client and not editable:
    st.warning("👀 View Only Mode")

# ================= SAFE GET =================
def get_val(index, default=""):
    return client[index] if client else default

# ================= TABS =================
tab1, tab2 = st.tabs([
    "Client Info", "Features"
])

# ================= BASIC =================
states = [
    "Andhra Pradesh", "Delhi", "Gujarat", "Haryana",
    "Karnataka", "Maharashtra", "Odisha", "Punjab",
    "Rajasthan", "Telangana", "Tamil Nadu", "Uttar Pradesh"
]

products = ["FaME", "FaME + PocketFaME"]
owner = ["Sales1", "Sales2", "Sales3"]

with tab1:
    st.subheader("Basic Information")
    name = st.text_input("Client Name", value=get_val(1), disabled=not editable)
    state = st.selectbox(
        "State",
        states,
        index=states.index(get_val(3)) if client and get_val(3) in states else 0,
        disabled=not editable
    )

    # ================= OWNERSHIP =================
    cola, colb,colc = st.columns(3)
    with cola:
        po_date = st.date_input(
            "PO Date",
            value=pd.to_datetime(get_val(4)) if client and get_val(4) else datetime.today(),
            disabled=not editable
        )
    with colb:
        mail_date = st.date_input(
            "Mail Received Date",
            value=pd.to_datetime(get_val(5)) if client and get_val(5) else datetime.today(),
            disabled=not editable
        )
    with colc:
        owner = st.selectbox("Accounts Owner", owner, index=owner.index(get_val(6)) if  owner and get_val(6) in owner else 0, disabled=not editable)

    st.divider()
    # ================= PRODUCT =================
    st.subheader("Product Details")
    cola, colb, colc = st.columns(3)
    with cola:
        product = st.selectbox("Product", products, index=products.index(get_val(7)) if products and get_val(7) in products else 0, disabled=not editable)
    with colb:
        version = st.text_input("Version", value=get_val(8), disabled=not editable)
    with colc:
        manpower = st.number_input("Manpower", value=int(get_val(2) or 0), disabled=not editable)

    # ================= CONTACT =================
    st.divider()
    st.subheader("Contact Details")

    if client:
        contacts = cur.execute("""
            SELECT name, designation, email, phone
            FROM client_contacts WHERE client_id=?
        """, (edit_id,)).fetchall()

        df = pd.DataFrame(contacts, columns=[
            'Person Name', 'Designation', 'Email', 'Phone'
        ])
    else:
        df = pd.DataFrame([{
            'Person Name': '',
            'Designation': '',
            'Email': '',
            'Phone': ''
        }])

    contacts_df = st.data_editor(df, num_rows="dynamic", disabled=not editable)

# ================= FEATURES =================
with tab2:
    st.subheader("Select Features")

    all_features = [f[0] for f in cur.execute("SELECT feature_name FROM features_master").fetchall()]

    existing_features = []
    if client:
        existing_features = [
            f[0] for f in cur.execute(
                "SELECT feature_name FROM client_features WHERE client_id=? AND enabled=1",
                (edit_id,)
            ).fetchall()
        ]

    selected_features = []

    for fname in all_features:
        checked = fname in existing_features
        if st.checkbox(fname, value=checked, disabled=not editable):
            selected_features.append(fname)

    # 🔥 NEW: Remarks for feature changes
    feature_remark = st.text_input("Feature Change Remark (optional)", disabled=not editable)


# ================= SAVE =================
if editable and st.button("💾 Save"):

    if not name.strip():
        st.warning("Client Name is required")
        st.stop()

    # ================= UPDATE =================
    if edit_id:

        # 🔥 STEP 1: GET OLD FEATURES
        old_features = set([
            f[0] for f in cur.execute(
                "SELECT feature_name FROM client_features WHERE client_id=? AND enabled=1",
                (edit_id,)
            ).fetchall()
        ])

        new_features = set(selected_features)

        added_features = new_features - old_features
        removed_features = old_features - new_features

        # ================= UPDATE CLIENT =================
        cur.execute("""
            UPDATE clients
            SET name=?, manpower=?, state=?,
                po_date=?, mail_date=?, owner=?,
                product=?, version=?
            WHERE id=?
        """, (
            name.strip(),
            manpower,
            state,
            str(po_date),
            str(mail_date),
            owner.strip(),
            product.strip(),
            version.strip(),
            edit_id
        ))

        # ================= RESET FEATURES =================
        cur.execute("DELETE FROM client_features WHERE client_id=?", (edit_id,))

        for fname in selected_features:
            cur.execute("""
                INSERT INTO client_features (client_id, feature_name, enabled, enabled_on)
                VALUES (?, ?, 1, ?)
            """, (edit_id, fname, str(po_date)))

        # ================= 🔥 FEATURE LOGGING =================
        for f in added_features:
            cur.execute("""
                INSERT INTO updates (client_id, type, title, status, created_at, created_by, remarks)
                VALUES (?, 'feature_log', ?, 'Done', ?, ?, ?)
            """, (
                edit_id,
                f"Enabled Feature: {f}",
                str(datetime.now()),
                current_user,
                feature_remark
            ))

        for f in removed_features:
            cur.execute("""
                INSERT INTO updates (client_id, type, title, status, created_at, created_by, remarks)
                VALUES (?, 'feature_log', ?, 'Done', ?, ?, ?)
            """, (
                edit_id,
                f"Disabled Feature: {f}",
                str(datetime.now()),
                current_user,
                feature_remark
            ))

        # ================= RESET CONTACTS =================
        cur.execute("DELETE FROM client_contacts WHERE client_id=?", (edit_id,))

        for _, row in contacts_df.iterrows():
            if row['Person Name']:
                cur.execute("""
                    INSERT INTO client_contacts (client_id, name, designation, email, phone)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    edit_id,
                    row['Person Name'],
                    row['Designation'],
                    row['Email'],
                    row['Phone']
                ))

        conn.commit()
        st.success("✅ Client Updated Successfully!")
        st.session_state["edit_client_id"] = None
        st.rerun()

    # ================= CREATE =================
    else:

        cur.execute("""
            INSERT INTO clients (
                name, manpower, state,
                po_date, mail_date, owner,
                product, version, status, client_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name.strip(),
            manpower,
            state,
            str(po_date),
            str(mail_date),
            owner.strip(),
            product.strip(),
            version.strip(),
            "New",
            ""
        ))

        new_id = cur.lastrowid
        formatted_id = f"CLD{new_id:04d}"
        cur.execute(
            "UPDATE clients SET client_code=? WHERE id=?",
            (formatted_id, new_id)
        )

        # CONTACTS
        for _, row in contacts_df.iterrows():
            if row['Person Name']:
                cur.execute("""
                    INSERT INTO client_contacts (client_id, name, designation, email, phone)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    new_id,
                    row['Person Name'],
                    row['Designation'],
                    row['Email'],
                    row['Phone']
                ))

        # FEATURES
        for fname in selected_features:
            cur.execute("""
                INSERT INTO client_features (client_id, feature_name, enabled, enabled_on)
                VALUES (?, ?, 1, ?)
            """, (new_id, fname, str(po_date)))

        # ================= 🔥 FEATURE LOGGING (CREATE) =================
        for fname in selected_features:
            cur.execute("""
                INSERT INTO updates (
                    client_id, type, title, status, created_at, created_by, remarks
                )
                VALUES (?, 'feature_log', ?, 'Done', ?, ?, ?)
            """, (
                new_id,
                f"Enabled Feature: {fname}",
                str(datetime.now()),
                current_user,
                feature_remark
            ))

        conn.commit()
        st.success(f"✅ Client Created! ID: {formatted_id}")

        st.session_state["edit_client_id"] = None
