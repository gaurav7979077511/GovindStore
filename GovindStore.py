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
MILKING_TAB = "Milking"
EXPENSE_TAB = "Expense"
INVESTMENT_TAB = "Investment"
PAYMENT_TAB = "Payment"
BILLING_TAB = "Billing"
MEDICATION_TAB="Medication"

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
            "Milking",
            "Customers",
            "Expense",
            "Investment",
            "Payment",
            "Billing",
            "Cow Profile",
            "Medication"

            
        ],
    )

    # ============================================================
    # GLOBAL COW HELPERS (USED BY MULTIPLE MODULES)
    # ============================================================
    
    COW_HEADER = [
        "CowID","ParentCowID","AnimalType","Gender","Breed",
        "AgeYears","PurchaseDate","PurchasePrice",
        "SoldPrice","SoldDate",
        "Status","MilkingStatus",
        "Notes","BirthYear","Timestamp"
    ]
    
    def open_cow_sheet():
        return open_sheet(MAIN_SHEET_ID, COW_PROFILE_TAB)
    
    @st.cache_data(ttl=60)
    def load_cows():
        ws = open_cow_sheet()
        rows = ws.get_all_values()
    
        if not rows or rows[0] != COW_HEADER:
            return pd.DataFrame(columns=COW_HEADER)
    
        return pd.DataFrame(rows[1:], columns=rows[0])

    # ----------------------------
    # MANAGE CUSTOMERS PAGE
    # ----------------------------
    if page =="Dashboard":
        st.title("Dashboard")
    
    elif page == "Milking":

        st.title("🥛 Milking")
    
        MILKING_HEADER = [
            "Date", "Shift", "CowID", "AnimalType", "MilkQuantity", "Timestamp"
        ]
    
        # ================== SHEET HELPERS ==================
        def open_milking_sheet():
            return open_sheet(MAIN_SHEET_ID, MILKING_TAB)
    
        def load_milking_data():
            ws = open_milking_sheet()
            rows = ws.get_all_values()
    
            if not rows or rows[0] != MILKING_HEADER:
                ws.clear()
                ws.insert_row(MILKING_HEADER, 1)
                return pd.DataFrame(columns=MILKING_HEADER)
    
            return pd.DataFrame(rows[1:], columns=rows[0])
    
        def append_milking_rows(rows):
            ws = open_milking_sheet()
            for r in rows:
                ws.append_row(r, value_input_option="USER_ENTERED")
    
        # ================== STATE ==================
        if "show_milking_form" not in st.session_state:
            st.session_state.show_milking_form = None
    
        # ================== SHIFT BUTTONS ==================
        c1, c2 = st.columns(2)
    
        with c1:
            if st.button("🌅 Morning Milking", use_container_width=True):
                st.session_state.show_milking_form = "Morning"
    
        with c2:
            if st.button("🌃 Evening Milking", use_container_width=True):
                st.session_state.show_milking_form = "Evening"
    
        # ================== ENTRY FORM ==================
        if st.session_state.show_milking_form:
    
            shift = st.session_state.show_milking_form
            st.divider()
            st.subheader(f"📝 {shift} Milking Entry")
    
            date = st.date_input("Date", value=dt.date.today())
    
            # 🔹 Load only Active + Milking cows
            cows_df = load_cows()
            cows_df = cows_df[
                (cows_df["Status"] == "Active") &
                (cows_df["MilkingStatus"] == "Milking")
            ]
    
            if cows_df.empty:
                st.info("No active milking cows available.")
            else:
                with st.form("milking_form"):
                    entries = []
    
                    for _, cow in cows_df.iterrows():
                        qty = st.text_input(
                            f"{cow['CowID']} ({cow['AnimalType']})",
                            placeholder="Milk in litres",
                            key=f"{shift}_{cow['CowID']}"
                        )
                        entries.append((cow, qty))
    
                    save, cancel = st.columns(2)
                    save_btn = save.form_submit_button("💾 Save")
                    cancel_btn = cancel.form_submit_button("❌ Cancel")
    
                if cancel_btn:
                    st.session_state.show_milking_form = None
                    st.rerun()
    
                if save_btn:
                    date_str = date.strftime("%Y-%m-%d")
                    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
                    df_existing = load_milking_data()
                    rows_to_insert = []
                    has_error = False
    
                    for cow, qty in entries:
                        if not qty.strip():
                            st.error(f"Milk quantity required for {cow['CowID']}")
                            has_error = True
                            break
    
                        # ❌ Duplicate check
                        if (
                            (df_existing["Date"] == date_str) &
                            (df_existing["Shift"] == shift) &
                            (df_existing["CowID"] == cow["CowID"])
                        ).any():
                            st.error(f"Duplicate entry found for {cow['CowID']}")
                            has_error = True
                            break
    
                        rows_to_insert.append([
                            date_str,
                            shift,
                            cow["CowID"],
                            cow["AnimalType"],
                            float(qty),
                            ts
                        ])
    
                    if not has_error:
                        append_milking_rows(rows_to_insert)
                        st.success("Milking data saved successfully ✅")
                        st.session_state.show_milking_form = None
                        st.rerun()
    
        # ================== SUMMARY CARDS ==================
        df_milk = load_milking_data()
    
        if not df_milk.empty:
            df_milk["MilkQuantity"] = pd.to_numeric(
                df_milk["MilkQuantity"], errors="coerce"
            ).fillna(0)
    
            summary = (
                df_milk
                .groupby(["Date", "Shift"])["MilkQuantity"]
                .sum()
                .reset_index()
                .sort_values("Date", ascending=False)
            )
    
            st.subheader("📊 Daily Milking Summary")
    
            cols = st.columns(4)
    
            for i, row in summary.iterrows():
    
                gradient = (
                    "linear-gradient(135deg,#43cea2,#185a9d)"
                    if row["Shift"] == "Morning"
                    else "linear-gradient(135deg,#7F00FF,#E100FF)"
                )
    
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
                                {row['MilkQuantity']:.2f} L
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    #--------
    elif page == "Expense":

        st.title("💸 Expense Management")
    
        # ================= CLOUDINARY =================
        import cloudinary
        import cloudinary.uploader
    
        cloudinary.config(
            cloud_name=st.secrets["cloudinary"]["cloud_name"],
            api_key=st.secrets["cloudinary"]["api_key"],
            api_secret=st.secrets["cloudinary"]["api_secret"],
            secure=True
        )
    
        def upload_to_cloudinary(file):
            result = cloudinary.uploader.upload(
                file,
                folder="dairy/expenses",
                resource_type="auto"
            )
            return result["secure_url"]
    
        # ================= GSHEET =================
        def open_expense_sheet():
            return open_sheet(MAIN_SHEET_ID, EXPENSE_TAB)
    
        def load_expenses():
            ws = open_expense_sheet()
            rows = ws.get_all_values()
            if len(rows) <= 1:
                return pd.DataFrame(columns=rows[0])
            return pd.DataFrame(rows[1:], columns=rows[0])
    
        # ================= LOAD DATA =================
        expense_df = load_expenses()
        if not expense_df.empty:
            expense_df["Amount"] = pd.to_numeric(expense_df["Amount"], errors="coerce").fillna(0)
            expense_df["Date"] = pd.to_datetime(expense_df["Date"])
    
        # ================= KPI CALCULATIONS =================
        today = pd.Timestamp.today()
        month_df = expense_df[
            (expense_df["Date"].dt.month == today.month) &
            (expense_df["Date"].dt.year == today.year)
        ] if not expense_df.empty else pd.DataFrame()
    
        total_overall = expense_df["Amount"].sum() if not expense_df.empty else 0
        total_month = month_df["Amount"].sum() if not month_df.empty else 0
    
        avg_daily = (
            month_df.groupby(month_df["Date"].dt.date)["Amount"].sum().mean()
            if not month_df.empty else 0
        )
    
        top_category = (
            month_df.groupby("Category")["Amount"].sum().idxmax()
            if not month_df.empty else "-"
        )
    
        # ================= KPI CARDS =================
        st.subheader("📊 Expense Summary")
    
        k1, k2, k3, k4 = st.columns(4)
    
        def kpi_card(title, value):
            st.markdown(
                f"""
                <div style="
                    padding:16px;
                    border-radius:14px;
                    background:linear-gradient(135deg,#141E30,#243B55);
                    color:white;
                    box-shadow:0 6px 16px rgba(0,0,0,0.25);
                ">
                    <div style="font-size:13px;opacity:0.85">{title}</div>
                    <div style="font-size:22px;font-weight:800">₹ {value:,.2f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
        with k1:
            kpi_card("Total Expense (Overall)", total_overall)
        with k2:
            kpi_card("Total Expense (This Month)", total_month)
        with k3:
            kpi_card("Top Category (This Month)", 0)
            st.caption(top_category)
        with k4:
            kpi_card("Avg Daily Expense (This Month)", avg_daily)
    
        st.divider()
    
        # ================= ADD EXPENSE =================
        if "show_expense_form" not in st.session_state:
            st.session_state.show_expense_form = False
    
        if st.button("➕ Add Expense"):
            st.session_state.show_expense_form = True
    
        if st.session_state.show_expense_form:
            with st.form("expense_form"):
    
                c1, c2, c3 = st.columns(3)
    
                with c1:
                    date = st.date_input("Date")
                    category = st.selectbox(
                        "Category",
                        [
                            "Feed", "Medicine", "Labour", "Electricity",
                            "Maintenance", "Transport", "Veterinary",
                            "Equipment", "Other"
                        ]
                    )
    
                with c2:
                    cows_df = load_cows()
                    cow_ids = ["All"] + cows_df[cows_df["Status"] == "Active"]["CowID"].tolist()
                    cow_id = st.selectbox("Cow ID", cow_ids)
                    amount = st.number_input(
                        "Amount",
                        min_value=0.0,
                        value=None,
                        placeholder="Enter expense amount"
                    )
    
                with c3:
                    payment_mode = st.selectbox(
                        "Payment Mode",
                        ["Cash", "UPI", "Bank Transfer", "Cheque"]
                    )
                    expense_by = st.session_state.user_name
    
                notes = st.text_area("Notes")
                file = st.file_uploader(
                    "Upload Bill (Optional)",
                    type=["jpg", "jpeg", "png", "pdf"]
                )
    
                save, cancel = st.columns(2)
    
            # ---------- CANCEL ----------
            if cancel.form_submit_button("Cancel"):
                st.session_state.show_expense_form = False
                st.rerun()
    
            # ---------- SAVE ----------
            if save.form_submit_button("Save Expense"):
    
                if not category or not cow_id or not payment_mode or not notes or not amount or amount <= 0:
                    st.error("❌ All fields are mandatory except bill upload")
                    st.stop()
    
                file_url = ""
                if file:
                    with st.spinner("Uploading bill..."):
                        file_url = upload_to_cloudinary(file)
    
                expense_id = f"EXP{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"
    
                open_expense_sheet().append_row(
                    [
                        expense_id,
                        date.strftime("%Y-%m-%d"),
                        category,
                        cow_id,
                        amount,
                        payment_mode,
                        expense_by,
                        file_url,
                        notes,
                        dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ],
                    value_input_option="USER_ENTERED"
                )
    
                st.success("✅ Expense saved successfully")
                st.session_state.show_expense_form = False
                st.rerun()
    
        # ================= EXPENSE LIST =================
        st.subheader("📋 Expense History")

        if expense_df.empty:
            st.info("No expenses recorded yet.")
        else:
            expense_df = expense_df.sort_values("Date", ascending=False).reset_index(drop=True)
        
            # ---- OUTER FRAME ----
            st.markdown(
                """
                <div style="
                    border:1px solid #2d3748;
                    border-radius:16px;
                    padding:16px;
                    background:#0f172a;
                ">
                """,
                unsafe_allow_html=True
            )
        
            for i, row in expense_df.iterrows():
        
                if i % 5 == 0:   # 5 cards per row
                    cols = st.columns(5)
        
                bill_html = ""
                if row["FileURL"]:
                    bill_html = (
                        f"<a href='{row['FileURL']}' target='_blank' "
                        "style='font-size:11px;font-weight:600;"
                        "color:#38bdf8;text-decoration:none;'>"
                        "📎 Bill</a>"
                    )
        
                card_html = f"""
                <div style="
                    padding:10px;
                    border-radius:12px;
                    background:#1e293b;
                    color:white;
                    box-shadow:0 4px 10px rgba(0,0,0,0.25);
                    font-family:Arial;
                    height:180px;
                ">
        
                    <!-- Amount + Date -->
                    <div style="font-size:17px;font-weight:800;">
                        ₹ {float(row['Amount']):,.0f}
                    </div>
                    <div style="font-size:11px;opacity:0.7;">
                        {pd.to_datetime(row['Date']).strftime('%d %b %Y')}
                    </div>
        
                    <!-- Category -->
                    <div style="font-size:12px;margin-top:4px;">
                        <b>{row['Category']}</b>
                    </div>
        
                    <!-- Cow + Payment -->
                    <div style="font-size:11px;opacity:0.85;margin-top:2px;">
                        🐄 {row['CowID']} &nbsp;•&nbsp; 💳 {row['PaymentMode']}
                    </div>
        
                    <!-- Notes (trimmed) -->
                    <div style="
                        font-size:11px;
                        margin-top:6px;
                        opacity:0.85;
                        display:-webkit-box;
                        -webkit-line-clamp:2;
                        -webkit-box-orient:vertical;
                        overflow:hidden;
                    ">
                        {row['Notes']}
                    </div>
        
                    <!-- Footer -->
                    <div style="
                        font-size:11px;
                        opacity:0.75;
                        margin-top:6px;
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                    ">
                        <span>👤 {row['ExpenseBy']}</span>
                        <span>{bill_html}</span>
                    </div>
        
                </div>
                """
        
                with cols[i % 5]:
                    components.html(card_html, height=200)
        
            st.markdown("</div>", unsafe_allow_html=True)




    
    elif page=="Investment":
        st.title("Investment")

    elif page=="Payment":
        st.title("Payment")
    
    elif page=="Billing":
        st.title("Billing")
    
    elif page == "Cow Profile":

        st.title("🐄🐃 Cow Profile")
    
        CURRENT_YEAR = dt.datetime.now().year
    
    
        # ======================================================
        # STATE
        # ======================================================
        if "show_add_cow" not in st.session_state:
            st.session_state.show_add_cow = False
        if "edit_cow_id" not in st.session_state:
            st.session_state.edit_cow_id = None
    

    
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
    
        # ======================================================
        # ADD COW
        # ======================================================
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
                        cow_id,
                        parent,
                        animal,
                        gender,
                        breed,
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
    
        # ======================================================
        # LIST + EDIT
        # ======================================================
        st.markdown("### 📋 Cow List")
        df = load_cows()
    
        if df.empty:
            st.info("No cow records found.")
        else:
            for i, row in df.iterrows():
                if i % 4 == 0:
                    cols = st.columns(4)
    
                age = CURRENT_YEAR - int(row["BirthYear"])
    
                gradient = {
                    "Active": "linear-gradient(135deg,#43cea2,#185a9d)",
                    "Sick": "linear-gradient(135deg,#f7971e,#ffd200)",
                    "Sold": "linear-gradient(135deg,#2193b0,#6dd5ed)",
                    "Dead": "linear-gradient(135deg,#cb2d3e,#ef473a)",
                }.get(row["Status"], "linear-gradient(135deg,#757f9a,#d7dde8)")
    
                with cols[i % 4]:
                    components.html(
                        f"""
                        <div style="
                            padding:12px;
                            border-radius:14px;
                            background:{gradient};
                            color:white;
                            box-shadow:0 6px 16px rgba(0,0,0,0.25);
                            line-height:1.3;
                        ">
                            <div style="font-size:15px;font-weight:800;">
                                {'🐄' if row['AnimalType']=='Cow' else '🐃'} {row['CowID']}
                            </div>
                            <div style="font-size:12px;">Breed: {row['Breed']}</div>
                            <div style="font-size:12px;">Gender: {row['Gender']}</div>
                            <div style="font-size:12px;">Age: {age} Years</div>
                            <div style="font-size:12px;">Status: {row['Status']}</div>
                            <div style="font-size:12px;">Milking: {row['MilkingStatus']}</div>
                        </div>
                        """,
                        height=190,
                    )
    
                    if st.button("✏️", key=f"edit_{row['CowID']}"):
                        st.session_state.edit_cow_id = row["CowID"]
                        st.rerun()
    
                    if st.session_state.edit_cow_id == row["CowID"]:
                        with st.form(f"edit_{row['CowID']}"):
    
                            e1, e2, e3 = st.columns(3)
    
                            with e1:
                                e_breed = st.text_input("Breed", row["Breed"])
                                e_age = st.number_input("Age (Years)", min_value=0, value=age, step=1)
    
                            with e2:
                                e_status = st.selectbox(
                                    "Status",
                                    ["Active", "Sick", "Sold", "Dead"],
                                    index=["Active", "Sick", "Sold", "Dead"].index(row["Status"]),
                                )
                                e_milking = st.selectbox(
                                    "Milking Status",
                                    ["Milking", "Dry", "Pregnant", "Not Pregnant", "Heifer"],
                                    index=[
                                        "Milking",
                                        "Dry",
                                        "Pregnant",
                                        "Not Pregnant",
                                        "Heifer",
                                    ].index(row["MilkingStatus"]),
                                )
    
                            with e3:
                                e_sold_price = ""
                                e_sold_date = ""
    
                                if e_status == "Sold":
                                    e_sold_price = st.number_input(
                                        "Sold Price",
                                        min_value=0.0,
                                        value=float(row["SoldPrice"]) if row["SoldPrice"] else 0.0,
                                        step=100.0,
                                    )
                                    e_sold_date = st.date_input(
                                        "Sold Date",
                                        value=pd.to_datetime(row["SoldDate"]).date()
                                        if row["SoldDate"]
                                        else dt.date.today(),
                                    )
    
                            e_notes = st.text_area("Notes", row["Notes"])
    
                            u, c = st.columns(2)
                            update = u.form_submit_button("Update")
                            cancel = c.form_submit_button("Cancel")
    
                        if cancel:
                            st.session_state.edit_cow_id = None
                            st.rerun()
    
                        if update:
                            if e_status == "Sold" and (e_sold_price == "" or e_sold_date == ""):
                                st.error("❌ Sold Price and Sold Date are required")
                                st.stop()
    
                            update_cow_by_id(
                                row["CowID"],
                                {
                                    "Breed": e_breed,
                                    "AgeYears": e_age,
                                    "Status": e_status,
                                    "MilkingStatus": e_milking,
                                    "SoldPrice": e_sold_price if e_status == "Sold" else "",
                                    "SoldDate": e_sold_date.strftime("%Y-%m-%d") if e_status == "Sold" else "",
                                    "Notes": e_notes,
                                    "BirthYear": CURRENT_YEAR - int(e_age),
                                },
                            )
    
                            st.success("Cow profile updated ✅")
                            st.session_state.edit_cow_id = None
                            st.rerun()

    elif page == "Customers":   

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

    elif page=="Medication":
        st.title("Medication")
    # ----------------------------
    # REFRESH BUTTON
    # ----------------------------
    if st.sidebar.button("🔁 Refresh"):
        st.rerun()
