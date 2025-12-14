import streamlit as st
import pandas as pd
import urllib.parse
import streamlit.components.v1 as components
import datetime as dt
from google.oauth2.service_account import Credentials
import bcrypt
import gspread

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(page_title="Dairy Farm Management", layout="wide")

# ============================================================
# GOOGLE SHEET IDS (from Streamlit Secrets)
# ============================================================
AUTH_SHEET_ID = st.secrets["sheets"]["AUTH_SHEET_ID"]
AUTH_SHEET_NAME = "Sheet1"

MAIN_SHEET_ID = st.secrets["sheets"]["MAIN_SHEET_ID"]
CUSTOMER_TAB = "Manage_Customer"
BITRAN_TAB = "Milk_Distrubution"
COW_PROFILE_TAB = "Cow_Profile"
MILKING_FEEDING_TAB = "Milking_Feeding"
EXPENSE_TAB = "Expense"
INVESTMENT_TAB = "Investment"
PAYMENT_TAB = "Payment"
BILLING_TAB = "Billing"

# ============================================================
# GOOGLE SHEETS AUTH (SINGLE SOURCE OF TRUTH)
# ============================================================
def init_gsheets():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)


def open_sheet(sheet_id: str, tab: str):
    client = init_gsheets()
    sh = client.open_by_key(sheet_id)
    try:
        return sh.worksheet(tab)
    except gspread.WorksheetNotFound:
        return sh.get_worksheet(0)

# ============================================================
# AUTH SHEET (FIXED – NO DUPLICATE CLIENT)
# ============================================================
@st.cache_resource
def get_auth_sheet():
    try:
        client = init_gsheets()
        return client.open_by_key(AUTH_SHEET_ID).worksheet(AUTH_SHEET_NAME)
    except Exception:
        st.error("❌ AUTH sheet access denied. Share sheet with service account.")
        st.stop()

AUTH_sheet = get_auth_sheet()

@st.cache_resource
def load_auth_data():
    return pd.DataFrame(AUTH_sheet.get_all_records())

auth_df = load_auth_data()

# ============================================================
# PASSWORD VERIFY
# ============================================================
def verify_password(stored_hash, entered_password):
    return bcrypt.checkpw(entered_password.encode(), stored_hash.encode())

# ============================================================
# SESSION STATE
# ============================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.user_name = None

# ============================================================
# LOGIN PAGE
# ============================================================
if not st.session_state.authenticated:
    st.title("🔒 Secure Login")

    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")

    if st.button("Login"):
        user_data = auth_df[auth_df["Username"] == username]

        if user_data.empty:
            st.error("❌ User not found")
        else:
            row = user_data.iloc[0]
            if verify_password(row["Password"], password):
                st.session_state.authenticated = True
                st.session_state.user_role = row["Role"]
                st.session_state.username = username
                st.session_state.user_name = row["Name"]
                st.success(f"✅ Welcome, {row['Name']}")
                st.rerun()
            else:
                st.error("❌ Invalid Credentials")

# ============================================================
# DASHBOARD
# ============================================================
else:
    st.sidebar.success(f"👤 {st.session_state.user_name}")

    page = st.sidebar.radio(
        "Navigation",
        ["Manage Customers", "Milk Bitran"],
    )

    # ============================================================
    # MANAGE CUSTOMERS
    # ============================================================
    if page == "Manage Customers":

        st.title("👥 Manage Customers")

        if "show_add_form" not in st.session_state:
            st.session_state.show_add_form = False
        if "edit_customer_id" not in st.session_state:
            st.session_state.edit_customer_id = None

        def open_customer_sheet():
            return open_sheet(MAIN_SHEET_ID, CUSTOMER_TAB)

        def get_customers_df():
            ws = open_customer_sheet()
            rows = ws.get_all_values()
            if len(rows) <= 1:
                return pd.DataFrame(columns=[
                    "CustomerID","Name","Phone","Email",
                    "DateOfJoining","Shift","Status","Timestamp"
                ])
            return pd.DataFrame(rows[1:], columns=rows[0])

        def update_customer_by_id(customer_id, updated):
            ws = open_customer_sheet()
            rows = ws.get_all_values()
            header = rows[0]
            id_col = header.index("CustomerID")

            for i, r in enumerate(rows[1:], start=2):
                if r[id_col] == customer_id:
                    for k, v in updated.items():
                        ws.update_cell(i, header.index(k) + 1, v)
                    return True
            return False

        if st.button("Create Customer Profile"):
            st.session_state.show_add_form = True

        if st.session_state.show_add_form:
            with st.form("add_customer"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    name = st.text_input("Name")
                    phone = st.text_input("Phone")
                with c2:
                    email = st.text_input("Email")
                    doj = st.date_input("Date of Joining")
                with c3:
                    shift = st.selectbox("Shift", ["Morning","Evening","Both"])
                    status = st.selectbox("Status", ["Active","Inactive"])

                a, b = st.columns(2)
                create = a.form_submit_button("Create")
                cancel = b.form_submit_button("Cancel")

            if cancel:
                st.session_state.show_add_form = False
                st.rerun()

            if create:
                ws = open_customer_sheet()
                ws.append_row([
                    f"CUST{dt.datetime.now().strftime('%Y%m%d%H%M%S')}",
                    name, phone, email,
                    doj.strftime("%Y-%m-%d"),
                    shift, status,
                    dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ])
                st.success("Customer added")
                st.session_state.show_add_form = False
                st.rerun()

        df = get_customers_df()
        for i, row in df.iterrows():
            if i % 4 == 0:
                cols = st.columns(4)

            gradient = {
                "Morning": "linear-gradient(135deg,#43cea2,#185a9d)",
                "Evening": "linear-gradient(135deg,#7F00FF,#E100FF)",
                "Both": "linear-gradient(135deg,#f7971e,#ffd200)"
            }.get(row["Shift"])

            with cols[i % 4]:
                components.html(
                    f"""
                    <div style="padding:12px;border-radius:14px;background:{gradient};
                    color:white;box-shadow:0 6px 16px rgba(0,0,0,0.25);">
                    <b>{row['Name']}</b><br>
                    📞 {row['Phone']}<br>
                    🆔 {row['CustomerID']}<br>
                    ⏰ {row['Shift']} • {row['Status']}
                    </div>
                    """,
                    height=140
                )

    # ============================================================
    # MILK BITRAN (UNCHANGED)
    # ============================================================
    elif page == "Milk Bitran":

        st.title("🥛 Milk Bitran")

        BITRAN_HEADER = [
            "Date","Shift","CustomerID",
            "CustomerName","MilkDelivered","Timestamp"
        ]

        def load_customers():
            ws = open_sheet(MAIN_SHEET_ID, CUSTOMER_TAB)
            rows = ws.get_all_values()
            return pd.DataFrame(rows[1:], columns=rows[0])

        def load_bitran_data():
            ws = open_sheet(MAIN_SHEET_ID, BITRAN_TAB)
            rows = ws.get_all_values()
            if not rows or rows[0] != BITRAN_HEADER:
                ws.insert_row(BITRAN_HEADER, 1)
                return pd.DataFrame(columns=BITRAN_HEADER)
            return pd.DataFrame(rows[1:], columns=rows[0])

        def append_bitran_rows(rows):
            ws = open_sheet(MAIN_SHEET_ID, BITRAN_TAB)
            for r in rows:
                ws.append_row(r, value_input_option="USER_ENTERED")

        if "show_form" not in st.session_state:
            st.session_state.show_form = None

        c1, c2 = st.columns(2)
        if c1.button("🌅 Morning Bitran"):
            st.session_state.show_form = "Morning"
        if c2.button("🌃 Evening Bitran"):
            st.session_state.show_form = "Evening"

        if st.session_state.show_form:
            shift = st.session_state.show_form
            date = st.date_input("Date")

            customers = load_customers()
            customers = customers[
                (customers["Status"].str.lower() == "active") &
                (customers["Shift"].isin([shift, "Both"]))
            ]

            with st.form("bitran_form"):
                entries = []
                for _, c in customers.iterrows():
                    qty = st.text_input(f"{c['Name']} ({c['CustomerID']})")
                    entries.append((c, qty))
                save = st.form_submit_button("Save")

            if save:
                rows = []
                ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for c, q in entries:
                    rows.append([
                        date.strftime("%Y-%m-%d"),
                        shift,
                        c["CustomerID"],
                        c["Name"],
                        float(q),
                        ts,
                    ])
                append_bitran_rows(rows)
                st.success("Milk Bitran saved successfully ✅")
                st.session_state.show_form = None
                st.rerun()

    if st.sidebar.button("🔁 Refresh"):
        st.rerun()
