import streamlit as st
import pandas as pd
import urllib.parse
import streamlit.components.v1 as components
import datetime as dt

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(page_title="Dairy Farm Management", layout="wide")

# ============================================================
# GOOGLE SHEET IDS (from Streamlit Secrets)
# ============================================================


MAIN_SHEET_ID = st.secrets["sheets"]["MAIN_SHEET_ID"]
CUSTOMER_TAB = "Manage_Customer"
BITRAN_TAB = "Milk_Distrubution"

# ============================================================
# UTILITY FUNCTIONS
# ============================================================
@st.cache_data(ttl=600)
def load_csv(url, drop_cols=None):
    """Load a CSV from Google Sheets"""
    try:
        df = pd.read_csv(url)
        if drop_cols:
            df = df.drop(columns=[col for col in drop_cols if col in df.columns])
        return df
    except Exception as e:
        st.error(f"❌ Failed to load data from Google Sheet: {e}")
        return pd.DataFrame()


def sum_numeric_columns(df, exclude_cols=None):
    """Sum all numeric columns except excluded ones"""
    if df.empty:
        return 0
    if exclude_cols is None:
        exclude_cols = []
    numeric_cols = [col for col in df.columns if col not in exclude_cols]
    df_numeric = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    return df_numeric.sum().sum()

# ============================================================
# SIDEBAR NAVIGATION
# ============================================================
st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Go to",
    [
        "Manage Customers",
        "Milk Bitran"
    ],
)


# ----------------------------
# MANAGE CUSTOMERS PAGE
# ----------------------------
if page == "Manage Customers":


    

    st.title("👥 Manage Customers")

    # ---------- STATE ----------
    if "show_add_form" not in st.session_state:
        st.session_state.show_add_form = False

    if "edit_customer_id" not in st.session_state:
        st.session_state.edit_customer_id = None

   

    # ---------- GOOGLE SHEETS ----------
    def init_gsheets():
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            dict(st.secrets["gcp_service_account"]),
            scopes=scope,
        )
        return gspread.authorize(creds)

    def open_customer_sheet():
        client = init_gsheets()
        sh = client.open_by_key(MAIN_SHEET_ID)
        return sh.worksheet(CUSTOMER_TAB)

    def get_customers_df():
        ws = open_customer_sheet()
        data = ws.get_all_values()
        if len(data) <= 1:
            return pd.DataFrame(columns=[
                "CustomerID","Name","Phone","Email",
                "DateOfJoining","Shift","Status","Timestamp"
            ])
        return pd.DataFrame(data[1:], columns=data[0])

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

    # ---------- ADD CUSTOMER ----------
    st.markdown("### ➕ Add Customer")
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
            cid = f"CUST{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"
            ws = open_customer_sheet()
            ws.append_row([
                cid, name, phone, email,
                doj.strftime("%Y-%m-%d"),
                shift, status,
                dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])
            st.success("Customer added")
            st.session_state.show_add_form = False
            st.rerun()

    # ---------- CUSTOMER CARDS ----------
    st.markdown("### 📋 Customers List")
    df = get_customers_df()

    for i, row in df.iterrows():

        if i % 4 == 0:
            cols = st.columns(4)

        shift = row["Shift"]
        gradient = {
            "Morning": "linear-gradient(135deg,#43cea2,#185a9d)",
            "Evening": "linear-gradient(135deg,#7F00FF,#E100FF)",
            "Both": "linear-gradient(135deg,#f7971e,#ffd200)"
        }.get(shift, "linear-gradient(135deg,#757f9a,#d7dde8)")

        card_html = f"""
        <div style="
            position:relative;
            padding:12px;
            border-radius:14px;
            background:{gradient};
            color:white;
            box-shadow:0 6px 16px rgba(0,0,0,0.25);
            line-height:1.3;
        ">

            <div style="font-size:15px;font-weight:800;">👤 {row['Name']}</div>
            <div style="font-size:12px;">📞 {row['Phone']}</div>
            <div style="font-size:12px;">✉️ {row['Email']}</div>
            <div style="font-size:12px;">🆔 {row['CustomerID']}</div>
            <div style="font-size:12px;">📅 {row['DateOfJoining']}</div>
            <div style="font-size:13px;font-weight:700;">
                ⏰ {row['Shift']} • {row['Status']}
            </div>
        </div>
        """

        with cols[i % 4]:
            components.html(card_html, height=150)

            if st.button("✏️", key=f"edit_{row['CustomerID']}"):
                st.session_state.edit_customer_id = row["CustomerID"]
                st.rerun()

            # ---------- INLINE EDIT FORM ----------
            if st.session_state.edit_customer_id == row["CustomerID"]:
                with st.form(f"edit_{row['CustomerID']}"):

                    e1, e2, e3 = st.columns(3)
                    with e1:
                        e_name = st.text_input("Name", row["Name"])
                        e_phone = st.text_input("Phone", row["Phone"])
                    with e2:
                        e_email = st.text_input("Email", row["Email"])
                        e_doj = st.date_input(
                            "DOJ",
                            pd.to_datetime(row["DateOfJoining"]).date()
                        )
                    with e3:
                        e_shift = st.selectbox(
                            "Shift",
                            ["Morning","Evening","Both"],
                            index=["Morning","Evening","Both"].index(row["Shift"])
                        )
                        e_status = st.selectbox(
                            "Status",
                            ["Active","Inactive"],
                            index=0 if row["Status"] == "Active" else 1
                        )

                    u, c = st.columns(2)
                    update = u.form_submit_button("Update")
                    cancel = c.form_submit_button("Cancel")

                if cancel:
                    st.session_state.edit_customer_id = None
                    st.rerun()

                if update:
                    update_customer_by_id(
                        row["CustomerID"],
                        {
                            "Name": e_name,
                            "Phone": e_phone,
                            "Email": e_email,
                            "DateOfJoining": e_doj.strftime("%Y-%m-%d"),
                            "Shift": e_shift,
                            "Status": e_status,
                        }
                    )
                    st.success("Customer updated")
                    st.session_state.edit_customer_id = None
                    st.rerun()

elif page == "Milk Bitran":

    st.title("🥛 Milk Bitran")


    BITRAN_HEADER = [
        "Date", "Shift", "CustomerID",
        "CustomerName", "MilkDelivered", "Timestamp"
    ]

    # ================= GSheets =================
    def init_gsheets():
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            dict(st.secrets["gcp_service_account"]),
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        return gspread.authorize(creds)

    def open_sheet(sheet_id, tab):
        sh = init_gsheets().open_by_key(sheet_id)
        try:
            return sh.worksheet(tab)
        except Exception:
            return sh.get_worksheet(0)

    def load_customers():
        ws = open_sheet(MAIN_SHEET_ID, CUSTOMER_TAB)
        rows = ws.get_all_values()
        if len(rows) <= 1:
            return pd.DataFrame(columns=["CustomerID", "Name", "Shift", "Status"])
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

    # ================= STATE =================
    if "show_form" not in st.session_state:
        st.session_state.show_form = None

    col1, col2 = st.columns(2)
    # ===================== SHIFT BUTTONS =====================
    with col1:
        if st.button("🌅 Morning Bitran", use_container_width=True):
            st.session_state.show_form = "Morning"
    
    with col2:
        if st.button("🌃 Evening Bitran", use_container_width=True):
            st.session_state.show_form = "Evening"
    
    # ================= ENTRY FORM =================
    if st.session_state.show_form:

        shift = st.session_state.show_form
        st.divider()
        st.subheader(f"📝 {shift} Bitran Entry")

        date = st.date_input("Date")

        customers = load_customers()
        customers = customers[
            (customers["Status"].str.lower() == "active")
            & (customers["Shift"].isin([shift, "Both"]))
        ]

        with st.form("bitran_form"):
            entries = []
            for _, c in customers.iterrows():
                qty = st.text_input(
                    f"{c['Name']} ({c['CustomerID']})",
                    placeholder="Enter milk in liters",
                    key=f"{shift}_{c['CustomerID']}",
                )
                entries.append((c, qty))

            save = st.form_submit_button("💾 Save")
            cancel = st.form_submit_button("❌ Cancel")

        if cancel:
            st.session_state.show_form = None
            st.rerun()

        if save:
            date_str = date.strftime("%Y-%m-%d")
            df_existing = load_bitran_data()

            rows, has_error = [], False
            ts = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

            for c, qty in entries:
                if not qty.strip():
                    st.error(f"Milk value required for {c['Name']}")
                    has_error = True
                    break

                if (
                    (df_existing["Date"] == date_str)
                    & (df_existing["Shift"] == shift)
                    & (df_existing["CustomerID"] == c["CustomerID"])
                ).any():
                    st.error(f"Duplicate entry: {c['Name']}")
                    has_error = True
                    break

                rows.append([
                    date_str, shift, c["CustomerID"],
                    c["Name"], float(qty), ts
                ])

            if not has_error:
                append_bitran_rows(rows)
                st.success("Milk Bitran saved successfully ✅")
                st.session_state.show_form = None
                st.rerun()

    # ===================== SUMMARY CARDS =====================
    df_bitran = load_bitran_data()
    
    if not df_bitran.empty and "MilkDelivered" in df_bitran.columns:
    
        df_bitran["MilkDelivered"] = (
            pd.to_numeric(df_bitran["MilkDelivered"], errors="coerce")
            .fillna(0)
        )
    
        summary = (
            df_bitran
            .groupby(["Date", "Shift"])["MilkDelivered"]
            .sum()
            .reset_index()
            .sort_values("Date", ascending=False)
        )
        summary["MilkDelivered"] = summary["MilkDelivered"].round(2)
    
        st.subheader("📊 Daily Summary")
    
        cols = st.columns(4)
    
        for i, row in summary.iterrows():

            # 🎨 Gradient based on shift
            if row["Shift"] == "Morning":
                gradient = "linear-gradient(135deg,#43cea2,#185a9d)"
            else:  # Evening
                gradient = "linear-gradient(135deg,#7F00FF,#E100FF)"
        
            with cols[i % 4]:
                st.markdown(
                    f"""
                    <div style="
                        padding:16px;
                        margin:12px 0;
                        border-radius:14px;
                        background:{gradient};
                        color:white;
                        box-shadow:0 6px 16px rgba(0,0,0,0.25);
                    ">
                        <div style="font-size:13px;opacity:0.9">
                            {row['Date']}
                        </div>
                        <div style="font-size:15px;font-weight:700">
                            {row['Shift']}
                        </div>
                        <div style="font-size:20px;font-weight:800">
                            {row['MilkDelivered']:.2f} L
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# ----------------------------
# REFRESH BUTTON
# ----------------------------
if st.sidebar.button("🔁 Refresh"):
    st.rerun()
