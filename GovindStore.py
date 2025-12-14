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
    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.username = None
        st.session_state.user_name = None
        st.experimental_set_query_params(logged_in="false")
        st.rerun()

    st.sidebar.write(f"👤 **Welcome, {st.session_state.user_name}!**")

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
            "Dashboard",
            "Milk Bitran",
            "Milking & Feeding",
            "Manage Customers",
            "Expese",
            "Investment",
            "Billing",
            "Cow Profile"
            
        ],
    )


    # ----------------------------
    # MANAGE CUSTOMERS PAGE
    # ----------------------------
    if page =="Dashboard":
        st.title("Dashboard")
    
    elif page=="Milking & Feeding":
        st.title("Milking & Feeding")
    
    elif page=="Expese":
        st.title("Expese")
    
    elif page=="Investment":
        st.title("Investment")
    
    elif page=="Billing":
        st.title("Billing")
    
    elif page == "Cow Profile":

        st.title("🐄🐃 Cow Profile")
    
        CURRENT_YEAR = dt.datetime.now().year
    
        COW_HEADER = [
            "CowID","ParentCowID","AnimalType","Gender","Breed",
            "AgeYears","PurchaseDate","PurchasePrice",
            "SoldPrice","SoldDate",
            "Status","MilkingStatus",
            "Notes","BirthYear","Timestamp"
        ]
    
        if "show_add_cow" not in st.session_state:
            st.session_state.show_add_cow = False
        if "edit_cow_id" not in st.session_state:
            st.session_state.edit_cow_id = None
    
        def open_cow_sheet():
            return open_sheet(MAIN_SHEET_ID, COW_PROFILE_TAB)
    
        def load_cows():
            ws = open_cow_sheet()
            rows = ws.get_all_values()
            if not rows or rows[0] != COW_HEADER:
                ws.clear()
                ws.insert_row(COW_HEADER, 1)
                return pd.DataFrame(columns=COW_HEADER)
            return pd.DataFrame(rows[1:], columns=rows[0])
    
        def update_cow_by_id(cow_id, updated):
            ws = open_cow_sheet()
            rows = ws.get_all_values()
            header = rows[0]
            id_col = header.index("CowID")
    
            for i, r in enumerate(rows[1:], start=2):
                if r[id_col] == cow_id:
                    for k, v in updated.items():
                        ws.update_cell(i, header.index(k) + 1, v)
                    return True
            return False
    
        # ---------- ADD COW ----------
        if st.button("➕ Add Cow / Buffalo"):
            st.session_state.show_add_cow = True
    
        if st.session_state.show_add_cow:
            with st.form("add_cow"):
                c1, c2, c3 = st.columns(3)
    
                with c1:
                    animal = st.selectbox("Animal Type", ["Cow", "Buffalo"])
                    gender = st.selectbox("Gender", ["Female", "Male"])
                    breed = st.text_input("Breed")
    
                with c2:
                    age = st.number_input("Age (Years)", min_value=0, step=1)
                    df = load_cows()
                    parents = df[df["Status"] == "Active"]["CowID"].tolist()
                    parent = st.selectbox("Parent Cow (Optional)", [""] + parents)
    
                    if parent:
                        dob = st.date_input("Date of Birth")
                        purchase_date = ""
                        purchase_price = ""
                    else:
                        purchase_date = st.date_input("Purchase Date")
                        purchase_price = st.number_input("Purchase Price", min_value=0.0, step=100.0)
                        dob = None
    
                with c3:
                    status = st.selectbox("Status", ["Active", "Sick", "Sold", "Dead"])
                    milking_status = st.selectbox(
                        "Milking Status",
                        ["Milking", "Dry", "Pregnant", "Not Pregnant", "Heifer"]
                    )
    
                    sold_price = ""
                    sold_date = ""
    
                    if status == "Sold":
                        sold_price = st.number_input("Sold Price", min_value=0.0, step=100.0)
                        sold_date = st.date_input("Sold Date")
    
                notes = st.text_area("Notes")
                save, cancel = st.columns(2)
    
            if cancel.form_submit_button("Cancel"):
                st.session_state.show_add_cow = False
                st.rerun()
    
            if save.form_submit_button("Save"):
    
                if status == "Sold" and (sold_price == "" or sold_date == ""):
                    st.error("❌ Sold Price and Sold Date are required")
                    st.stop()
    
                prefix = "COW" if animal == "Cow" else "BUF"
                cow_id = f"{prefix}{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"
                birth_year = CURRENT_YEAR - int(age)
    
                open_cow_sheet().append_row(
                    [
                        cow_id, parent, animal, gender, breed,
                        age,
                        dob.strftime("%Y-%m-%d") if dob else purchase_date.strftime("%Y-%m-%d"),
                        purchase_price,
                        sold_price,
                        sold_date.strftime("%Y-%m-%d") if sold_date else "",
                        status,
                        milking_status,
                        notes,
                        birth_year,
                        dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ],
                    value_input_option="USER_ENTERED"
                )
    
                st.success("Cow profile added successfully ✅")
                st.session_state.show_add_cow = False
                st.rerun()

        # ---------- LIST ----------
        st.markdown("### 📋 Cow List")
        df = load_cows()

        for i, row in df.iterrows():
            if i % 4 == 0:
                cols = st.columns(4)

            age = CURRENT_YEAR - int(row["BirthYear"])
            gradient = {
                "Active": "linear-gradient(135deg,#43cea2,#185a9d)",
                "Sold": "linear-gradient(135deg,#2193b0,#6dd5ed)",
                "Dead": "linear-gradient(135deg,#cb2d3e,#ef473a)",
            }.get(row["Status"], "#333")

            with cols[i % 4]:
                components.html(
                    f"""
                    <div style="padding:12px;border-radius:14px;
                    background:{gradient};color:white;">
                    <b>{'🐄' if row['AnimalType']=='Cow' else '🐃'} {row['CowID']}</b><br>
                    Breed: {row['Breed']}<br>
                    Gender: {row['Gender']}<br>
                    Age: {age} Years<br>
                    Status: {row['Status']}<br>
                    Health: {row['HealthStatus']}
                    </div>
                    """,
                    height=170
                )

                if st.button("✏️", key=f"edit_{row['CowID']}"):
                    st.session_state.edit_cow_id = row["CowID"]
                    st.rerun()

                if st.session_state.edit_cow_id == row["CowID"]:
                    with st.form(f"edit_{row['CowID']}"):
                        e_breed = st.text_input("Breed", row["Breed"])
                        e_age = st.number_input("Age", min_value=0, value=age)
                        e_status = st.selectbox("Status", ["Active","Sold","Dead"],
                            index=["Active","Sold","Dead"].index(row["Status"]))
                        e_health = st.selectbox("Health", ["Healthy","Sick"],
                            index=["Healthy","Sick"].index(row["HealthStatus"]))

                        e_sold_price = ""
                        e_sold_date = ""
                        if e_status == "Sold":
                            e_sold_price = st.number_input(
                                "Sold Price",
                                min_value=0.0,
                                value=float(row["SoldPrice"]) if row["SoldPrice"] else 0.0
                            )
                            e_sold_date = st.date_input(
                                "Sold Date",
                                value=pd.to_datetime(row["SoldDate"]).date()
                                if row["SoldDate"] else dt.date.today()
                            )

                        e_notes = st.text_area("Notes", row["Notes"])
                        u, c = st.columns(2)

                    if c.form_submit_button("Cancel"):
                        st.session_state.edit_cow_id = None
                        st.rerun()

                    if u.form_submit_button("Update"):
                        update_cow_by_id(
                            row["CowID"],
                            {
                                "Breed": e_breed,
                                "AgeYears": e_age,
                                "Status": e_status,
                                "HealthStatus": e_health,
                                "SoldPrice": e_sold_price if e_status=="Sold" else "",
                                "SoldDate": e_sold_date.strftime("%Y-%m-%d") if e_status=="Sold" else "",
                                "Notes": e_notes,
                                "BirthYear": CURRENT_YEAR - int(e_age),
                            }
                        )
                        st.success("Cow updated")
                        st.session_state.edit_cow_id = None
                        st.rerun()
    elif page == "Manage Customers":   

        st.title("👥 Manage Customers")

        # ---------- STATE ----------
        if "show_add_form" not in st.session_state:
            st.session_state.show_add_form = False

        if "edit_customer_id" not in st.session_state:
            st.session_state.edit_customer_id = None

    

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
