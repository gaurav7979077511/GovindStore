import streamlit as st
import pandas as pd
import urllib.parse
import streamlit.components.v1 as components
import datetime as dt
from google.oauth2.service_account import Credentials
import bcrypt
import gspread
import textwrap


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
TRANSACTION_TAB="Transaction"

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
                    "DateOfJoining","Shift","RatePerLitre","Status","Timestamp"
                ])
            return pd.DataFrame(data[1:], columns=data[0])

# ---------- VIEW MODE STATE ----------
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "display"   # display | edit

if "edit_customer_id" not in st.session_state:
    st.session_state.edit_customer_id = None

if "edit_customer_row" not in st.session_state:
    st.session_state.edit_customer_row = None

if "edit_row_index" not in st.session_state:
    st.session_state.edit_row_index = None


if "cow_view_mode" not in st.session_state:
    st.session_state.cow_view_mode = "display"  # display | edit

if "edit_cow_id" not in st.session_state:
    st.session_state.edit_cow_id = None

if "edit_cow_row" not in st.session_state:
    st.session_state.edit_cow_row = None


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
auth_df.columns = (
    auth_df.columns
    .astype(str)
    .str.replace("\u00a0", "", regex=False)
    .str.strip()
    .str.lower()
)



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
        user_data = auth_df[auth_df["username"] == username]

        if user_data.empty:
            st.error("❌ User not found")
        else:
            row = user_data.iloc[0]
            if verify_password(row["password"], password):
                st.session_state.authenticated = True
                st.session_state.user_role = row["role"]
                st.session_state.username = username
                st.session_state.user_name = row["name"]
                st.success(f"✅ Welcome, {row['name']}")
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
            "Medication",
            "Transaction"

            
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
    
        def kpi_card(title, value, is_currency=True):
            display_value = (
                f"₹ {value:,.2f}" if is_currency else str(value)
            )
        
            st.markdown(
                f"""
                <div style="
                    padding:16px;
                    margin:8px 0;
                    border-radius:14px;
                    background:linear-gradient(135deg,#141E30,#243B55);
                    color:white;
                    box-shadow:0 6px 16px rgba(0,0,0,0.25);
                ">
                    <div style="font-size:13px;opacity:0.85">{title}</div>
                    <div style="font-size:22px;font-weight:800">{display_value}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    
        with k1:
            kpi_card("Total Expense (Overall)", total_overall)
        with k2:
            kpi_card("Total Expense (This Month)", total_month)
        with k3:
            kpi_card("Top Category (This Month)", top_category, is_currency=False)
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
        
            for i, row in expense_df.iterrows():
        
                if i % 5 == 0:   # 5 cards per row
                    cols = st.columns(5)
        
                bill_html = ""
                if row["FileURL"]:
                    bill_html = (
                        f"<a href='{row['FileURL']}' target='_blank' "
                        "style='text-decoration:none;color:#475569;"
                        "font-size:11px;'>📎</a>"
                    )

                #---Card Html
                card_html = f"""
                    <div style="
                        border-radius:10px;
                        overflow:hidden;
                    ">
                        <div style="
                            background:#f8fafc;
                            color:#0f172a;
                            border:1px solid #e5e7eb;
                            border-radius:10px;
                            padding:8px;
                            font-family:Arial;
                            height:95px;
                            box-shadow:0 1px 2px rgba(0,0,0,0.05);
                        ">
                    
                            <!-- Amount & Date -->
                            <div style="display:flex;justify-content:space-between;">
                                <div style="font-size:15px;font-weight:700;">
                                    ₹ {float(row['Amount']):,.0f}
                                </div>
                                <div style="font-size:11px;color:#64748b;">
                                    {pd.to_datetime(row['Date']).strftime('%d %b')}
                                </div>
                            </div>
                    
                            <!-- Category -->
                            <div style="font-size:12px;font-weight:600;margin-top:1px;">
                                {row['Category']}
                            </div>
                    
                            <!-- Meta -->
                            <div style="font-size:11px;color:#475569;margin-top:1px;">
                                {row['PaymentMode']} | {row['CowID']}
                            </div>
                    
                            <!-- Notes -->
                            <div style="
                                font-size:11px;
                                color:#334155;
                                margin-top:4px;
                                display:-webkit-box;
                                -webkit-line-clamp:3;
                                -webkit-box-orient:vertical;
                                overflow:hidden;
                            ">
                                {row['Notes']}
                            </div>
                    
                            <!-- Footer -->
                            <div style="
                                display:flex;
                                justify-content:space-between;
                                align-items:center;
                                margin-top:4px;
                                font-size:11px;
                                color:#64748b;
                            ">
                                <span>{row['ExpenseBy']}</span>
                                <span>{bill_html}</span>
                            </div>
                    
                        </div>
                    </div>
                    """

        
                with cols[i % 5]:
                    components.html(card_html, height=125)




    #-----investment
    elif page == "Investment":

        st.title("💼 Investment")
    
        # =========================================================
        # STATE
        # =========================================================
        if "show_add_investment" not in st.session_state:
            st.session_state.show_add_investment = False
    
        # =========================================================
        # CONSTANTS
        # =========================================================
        INVESTMENT_HEADER = [
            "InvestmentID",
            "Date",
            "InvestedBy",
            "Amount",
            "InvestmentType",
            "FundDestination",
            "FileURL",
            "Notes",
            "Timestamp",
        ]
    
        # =========================================================
        # SHEET FUNCTIONS
        # =========================================================
        def open_investment_sheet():
            return open_sheet(MAIN_SHEET_ID, INVESTMENT_TAB)
    
        def load_investments():
            ws = open_investment_sheet()
            rows = ws.get_all_values()
    
            if not rows or rows[0] != INVESTMENT_HEADER:
                ws.clear()
                ws.insert_row(INVESTMENT_HEADER, 1)
                return pd.DataFrame(columns=INVESTMENT_HEADER)
    
            return pd.DataFrame(rows[1:], columns=rows[0])
    
        # =========================================================
        # CLOUDINARY UPLOAD
        # =========================================================
        import cloudinary
        import cloudinary.uploader
    
        cloudinary.config(
            cloud_name=st.secrets["cloudinary"]["cloud_name"],
            api_key=st.secrets["cloudinary"]["api_key"],
            api_secret=st.secrets["cloudinary"]["api_secret"],
            secure=True,
        )
    
        def upload_to_cloudinary(file):
            result = cloudinary.uploader.upload(
                file,
                folder="dairy/investments",
                resource_type="auto",
            )
            return result["secure_url"]
    
        # =========================================================
        # LOAD DATA
        # =========================================================
        investment_df = load_investments()
        if not investment_df.empty:
            investment_df["Amount"] = pd.to_numeric(
                investment_df["Amount"], errors="coerce"
            ).fillna(0)
    
        # =========================================================
        # DAIRY USERS (SAFE)
        # =========================================================
        dairy_users = (
            auth_df[
                auth_df["accesslevel"]
                .fillna("")
                .str.contains(r"\bdairy\b", case=False)
            ]["name"]
            .unique()
            .tolist()
        )
    
        # =========================================================
        # KPI SECTION
        # =========================================================
        total_investment = investment_df["Amount"].sum() if not investment_df.empty else 0
    
        st.subheader("📊 Investment Summary")
    
        def kpi_card(title, amount, percent=None):

            percent_html = ""
            if percent is not None:
                percent_html = f"""
                <div style="font-size:12px;color:#94a3b8;">
                    {percent}%
                </div>
                """
        
            components.html(
                f"""
                <div style="
                            padding:16px;
                            margin:8px 0;
                            border-radius:14px;
                            background:linear-gradient(135deg,#141E30,#243B55);
                            color:white;
                            box-shadow:0 6px 16px rgba(0,0,0,0.25);
                ">
                    <div style="font-size:13px;opacity:0.85">
                        {title}
                    </div>
        
                    <div style="display:flex;align-items:center;gap:8px;margin-top:6px;"
                    ">
                        <div style="font-size:22px;font-weight:800">
                            ₹ {amount:,.0f}
                        </div>
                        {percent_html}
                    </div>
                </div>
                """,
                height=100,
            )

        # --- Overall + Per User Cards (hide zero users) ---
        visible_users = []
        for u in dairy_users:
            if investment_df[investment_df["InvestedBy"] == u]["Amount"].sum() > 0:
                visible_users.append(u)
    
        cols = st.columns(len(visible_users) + 1)
    
        with cols[0]:
            kpi_card("Overall Investment", total_investment)
    
        for i, user in enumerate(visible_users, start=1):
            user_total = investment_df[investment_df["InvestedBy"] == user]["Amount"].sum()
            percent = round((user_total / total_investment) * 100, 1) if total_investment > 0 else 0
            with cols[i]:
                kpi_card(user, user_total, percent)
    
        st.divider()
    
        # =========================================================
        # ADD INVESTMENT
        # =========================================================
        if st.button("➕ Add Investment"):
            st.session_state.show_add_investment = True
    
        if st.session_state.show_add_investment:
    
            with st.form("add_investment"):
                c1, c2, c3 = st.columns(3)
    
                with c1:
                    invested_by = st.selectbox("Invested By", dairy_users)
                    amount = st.number_input(
                        "Amount",
                        min_value=0.0,
                        value=None,
                        placeholder="Enter investment amount",
                        step=1000.0,
                    )
    
                with c2:
                    inv_type = st.selectbox(
                        "Investment Type",
                        [
                            "Owner Capital",
                            "Partner Investment",
                            "Loan",
                            "Temporary Advance",
                            "Other",
                        ],
                    )
                    destination = st.selectbox(
                        "Fund Destination",
                        ["Company Account"] + dairy_users,
                    )
    
                    wallet_user = ""
                    if destination == "User Wallet":
                        wallet_user = st.selectbox("Select User Wallet", dairy_users)
    
                with c3:
                    proof = st.file_uploader(
                        "Upload Proof (Optional)",
                        type=["jpg", "png", "pdf"],
                    )
                    notes = st.text_area("Notes", height=80)
    
                save, cancel = st.columns(2)
    
            if cancel.form_submit_button("Cancel"):
                st.session_state.show_add_investment = False
                st.rerun()
    
            if save.form_submit_button("Save"):
                if amount is None or amount <= 0:
                    st.error("❌ Amount must be greater than 0")
                    st.stop()
    
                final_destination = (
                    f"User Wallet: {wallet_user}"
                    if destination == "User Wallet"
                    else "Company Account"
                )
    
                file_url = upload_to_cloudinary(proof) if proof else ""
    
                open_investment_sheet().append_row(
                    [
                        f"INV{dt.datetime.now().strftime('%Y%m%d%H%M%S')}",
                        dt.date.today().strftime("%Y-%m-%d"),
                        invested_by,
                        amount,
                        inv_type,
                        final_destination,
                        file_url,
                        notes,
                        dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ],
                    value_input_option="USER_ENTERED",
                )
    
                st.success("Investment added successfully ✅")
                st.session_state.show_add_investment = False
                st.rerun()
    
        st.divider()
    
        # =========================================================
        # INVESTMENT LIST
        # =========================================================
        st.subheader("📋 Investment List")

        if investment_df.empty:
            st.info("No investments recorded yet.")
        else:
            investment_df = investment_df.sort_values("Date", ascending=False).reset_index(drop=True)
        
            for i, row in investment_df.iterrows():
        
                # 🔹 Create 5 columns per row
                if i % 5 == 0:
                    cols = st.columns(5, gap="small")
        
                with cols[i % 5]:
                    components.html(
        f"""
        <div style="
            background:#f9fafb;
            border:1px solid #e5e7eb;
            border-radius:10px;
            padding:8px;
            height:95px;
            box-sizing:border-box;
            box-shadow:0 1px 2px rgba(0,0,0,0.04);
            font-family:Arial, sans-serif;
        ">
        
            <!-- Amount & Date -->
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="font-size:15px;font-weight:700;color:#0f172a;">
                    ₹ {float(row['Amount']):,.0f}
                </div>
                <div style="font-size:11px;color:#64748b;">
                    {pd.to_datetime(row['Date']).strftime('%d %b')}
                </div>
            </div>
        
            <!-- Type -->
            <div style="font-size:12px;font-weight:600;color:#334155;margin-top:2px;">
                {row['InvestmentType']}
            </div>
        
            <!-- Destination -->
            <div style="font-size:11px;color:#475569;margin-top:1px;">
                {row['FundDestination']}
            </div>
        
            <!-- Notes -->
            <div style="
                font-size:11px;
                color:#334155;
                margin-top:4px;
                display:-webkit-box;
                -webkit-line-clamp:3;
                -webkit-box-orient:vertical;
                overflow:hidden;
            ">
                {row['Notes'] or ""}
            </div>
        
            <!-- Footer -->
            <div style="
                display:flex;
                justify-content:space-between;
                align-items:center;
                margin-top:4px;
                font-size:11px;
                color:#475569;
            ">
                <span>{row['InvestedBy']}</span>
                {f"<a href='{row['FileURL']}' target='_blank' style='text-decoration:none;'>📎</a>" if row['FileURL'] else "<span></span>"}
            </div>
        
        </div>
        """,
                        height=125,
                    )




    elif page=="Payment":
        st.title("Payment")
    
    #----Billing------
    elif page == "Billing":

        st.title("🧾 Billing")

        # =========================================================
        # CONSTANTS
        # =========================================================
        BILLING_HEADER = [
            "BillID","CustomerID","CustomerName",
            "FromDate","ToDate",
            "MorningMilk","EveningMilk","TotalMilk",
            "RatePerLitre","BillAmount",
            "PaidAmount","BalanceAmount",
            "BillStatus","DueDate",
            "GeneratedBy","GeneratedOn"
        ]

        # =========================================================
        # SHEET HELPERS
        # =========================================================
        def open_billing_sheet():
            return open_sheet(MAIN_SHEET_ID, BILLING_TAB)

        def load_bills():
            ws = open_billing_sheet()
            rows = ws.get_all_values()

            if not rows or rows[0] != BILLING_HEADER:
                ws.clear()
                ws.insert_row(BILLING_HEADER, 1)
                return pd.DataFrame(columns=BILLING_HEADER)

            return pd.DataFrame(rows[1:], columns=rows[0])

        def calculate_milk(customer_id, from_date, to_date):
            ws = open_sheet(MAIN_SHEET_ID, BITRAN_TAB)
            rows = ws.get_all_values()

            if len(rows) <= 1:
                return 0, 0, 0

            df = pd.DataFrame(rows[1:], columns=rows[0])
            df["MilkDelivered"] = pd.to_numeric(df["MilkDelivered"], errors="coerce").fillna(0)
            df["Date"] = pd.to_datetime(df["Date"])

            df = df[
                (df["CustomerID"] == customer_id) &
                (df["Date"] >= pd.to_datetime(from_date)) &
                (df["Date"] <= pd.to_datetime(to_date))
            ]

            morning = df[df["Shift"] == "Morning"]["MilkDelivered"].sum()
            evening = df[df["Shift"] == "Evening"]["MilkDelivered"].sum()
            total = morning + evening

            return round(morning,2), round(evening,2), round(total,2)

        # =========================================================
        # LOAD DATA
        # =========================================================
        customers_df = get_customers_df()
        bills_df = load_bills()

        customers_df["RatePerLitre"] = pd.to_numeric(
            customers_df.get("RatePerLitre", 0), errors="coerce"
        ).fillna(0)

        # =========================================================
        # BILLING MODE
        # =========================================================
        billing_mode = st.radio(
            "Billing Type",
            ["Monthly Bulk Billing", "Individual Billing"],
            horizontal=True
        )

        today = dt.date.today()

        # =========================================================
        # BULK BILLING
        # =========================================================
        if billing_mode == "Monthly Bulk Billing":

            month_str = st.selectbox(
                "Select Month",
                pd.date_range(end=today, periods=12, freq="M").strftime("%Y-%m")
            )

            year, month = map(int, month_str.split("-"))
            from_date = dt.date(year, month, 1)
            to_date = (from_date + pd.offsets.MonthEnd(1)).date()
            due_date = to_date + dt.timedelta(days=7)

            st.info("Bulk billing will generate bills for all active customers (excluding Dairy-CMS).")

            if st.button("📄 Generate Bulk Bills"):
                ws = open_billing_sheet()
                generated = 0

                eligible_customers = customers_df[
                    (customers_df["Status"] == "Active") &
                    (customers_df["Name"] != "Dairy-CMS") &
                    (customers_df["RatePerLitre"] > 0)
                ]

                for _, cust in eligible_customers.iterrows():
                    cid = cust["CustomerID"]
                    cname = cust["Name"]
                    rate = float(cust["RatePerLitre"])

                    # Duplicate check
                    if not bills_df.empty and (
                        (bills_df["CustomerID"] == cid) &
                        (bills_df["FromDate"] == from_date.strftime("%Y-%m-%d")) &
                        (bills_df["ToDate"] == to_date.strftime("%Y-%m-%d"))
                    ).any():
                        continue

                    morning, evening, total = calculate_milk(cid, from_date, to_date)
                    if total == 0:
                        continue

                    amount = round(total * rate, 2)

                    ws.append_row(
                        [
                            f"BILL{dt.datetime.now().strftime('%Y%m%d%H%M%S')}",
                            cid, cname,
                            from_date.strftime("%Y-%m-%d"),
                            to_date.strftime("%Y-%m-%d"),
                            morning, evening, total,
                            rate, amount,
                            0, amount,
                            "Payment Pending",
                            due_date.strftime("%Y-%m-%d"),
                            st.session_state.user_name,
                            dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ],
                        value_input_option="USER_ENTERED"
                    )
                    generated += 1

                st.success(f"✅ {generated} bill(s) generated")
                st.rerun()

        # =========================================================
        # INDIVIDUAL BILLING
        # =========================================================
        else:
            customer_name = st.selectbox(
                "Select Customer",
                customers_df["Name"].tolist()
            )

            customer = customers_df[customers_df["Name"] == customer_name].iloc[0]
            from_date = st.date_input("From Date")
            to_date = st.date_input("To Date")
            due_date = to_date + dt.timedelta(days=7)

            is_dairy_cms = customer_name == "Dairy-CMS"

            if is_dairy_cms:
                manual_amount = st.number_input(
                    "Enter Bill Amount",
                    min_value=0.0,
                    placeholder="Enter total bill amount"
                )
            else:
                rate = float(customer["RatePerLitre"])
                morning, evening, total = calculate_milk(
                    customer["CustomerID"], from_date, to_date
                )
                amount = round(total * rate, 2)

                st.info(f"Milk: {total} L × ₹{rate} = ₹{amount}")

            if st.button("📄 Generate Bill"):
                ws = open_billing_sheet()

                bill_amount = manual_amount if is_dairy_cms else amount

                ws.append_row(
                    [
                        f"BILL{dt.datetime.now().strftime('%Y%m%d%H%M%S')}",
                        customer["CustomerID"],
                        customer_name,
                        from_date.strftime("%Y-%m-%d"),
                        to_date.strftime("%Y-%m-%d"),
                        morning if not is_dairy_cms else 0,
                        evening if not is_dairy_cms else 0,
                        total if not is_dairy_cms else 0,
                        customer["RatePerLitre"] if not is_dairy_cms else "",
                        bill_amount,
                        0,
                        bill_amount,
                        "Payment Pending",
                        due_date.strftime("%Y-%m-%d"),
                        st.session_state.user_name,
                        dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ],
                    value_input_option="USER_ENTERED"
                )

                st.success("✅ Bill generated successfully")
                st.rerun()

        # =========================================================
        # BILL LIST
        # =========================================================
        st.divider()
        st.subheader("📋 Bills")

        bills_df = load_bills()

        if bills_df.empty:
            st.info("No bills generated yet.")
        else:
            bills_df = bills_df.sort_values("GeneratedOn", ascending=False)

            for _, row in bills_df.iterrows():
                st.markdown(
                    f"""
                    <div style="
                        background:#f9fafb;
                        border:1px solid #e5e7eb;
                        border-radius:10px;
                        padding:10px;
                        margin-bottom:10px;
                    ">
                        <b>{row['CustomerName']}</b>
                        <div style="font-size:13px;">
                            {row['FromDate']} → {row['ToDate']}
                        </div>
                        <div>
                            🥛 {row['TotalMilk']} L × ₹{row['RatePerLitre']} =
                            <b>₹ {row['BillAmount']}</b>
                        </div>
                        <div style="font-size:12px;color:#475569;">
                            Status: {row['BillStatus']} | Balance: ₹{row['BalanceAmount']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )



    
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

        col1, col2 = st.columns([1, 5])

        with col1:
            if st.session_state.cow_view_mode == "display":
                if st.button("✏️ Edit View"):
                    st.session_state.cow_view_mode = "edit"
                    st.rerun()
            else:
                if st.button("👁️ Display View"):
                    st.session_state.cow_view_mode = "display"
                    st.session_state.edit_cow_id = None
                    st.rerun()

        df = load_cows()
    
        if df.empty:
            st.info("No cow records found.")
        else:
            if st.session_state.cow_view_mode == "edit" and st.session_state.edit_cow_id:

                st.markdown("---")
                st.markdown("## ✏️ Edit Cow Profile")

                row = st.session_state.edit_cow_row
                age = CURRENT_YEAR - int(row["BirthYear"])

                with st.form("edit_cow_form"):
                    c1, c2, c3 = st.columns(3)

                    with c1:
                        e_breed = st.text_input("Breed", row["Breed"])
                        e_age = st.number_input("Age (Years)", min_value=0, value=age, step=1)

                    with c2:
                        e_status = st.selectbox(
                            "Status",
                            ["Active", "Sick", "Sold", "Dead"],
                            index=["Active","Sick","Sold","Dead"].index(row["Status"])
                        )
                        e_milking = st.selectbox(
                            "Milking Status",
                            ["Milking","Dry","Pregnant","Not Pregnant","Heifer"],
                            index=["Milking","Dry","Pregnant","Not Pregnant","Heifer"].index(row["MilkingStatus"])
                        )

                    with c3:
                        e_sold_price = ""
                        e_sold_date = ""

                        if e_status == "Sold":
                            e_sold_price = st.number_input(
                                "Sold Price",
                                min_value=0.0,
                                value=float(row["SoldPrice"]) if row["SoldPrice"] else 0.0,
                                step=100.0
                            )
                            e_sold_date = st.date_input(
                                "Sold Date",
                                value=pd.to_datetime(row["SoldDate"]).date()
                                if row["SoldDate"] else dt.date.today()
                            )

                    e_notes = st.text_area("Notes", row["Notes"])

                    u, c = st.columns(2)
                    update = u.form_submit_button("✅ Update")
                    cancel = c.form_submit_button("❌ Cancel")

                if cancel:
                    st.session_state.edit_cow_id = None
                    st.rerun()

                if update:
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
                        }
                    )
                    st.success("Cow profile updated ✅")
                    st.session_state.edit_cow_id = None
                    st.rerun()
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

                card_html = f"""
                <div style="
                    height:165px;
                    padding:14px;
                    border-radius:16px;
                    background:{gradient};
                    color:white;
                    box-shadow:0 6px 18px rgba(0,0,0,0.28);
                    display:flex;
                    flex-direction:column;
                    justify-content:space-between;
                    margin-bottom:16px;
                    overflow:hidden;
                ">

                    <div style="font-size:15px;font-weight:800;display:flex;gap:6px;">
                        {'🐄' if row['AnimalType']=='Cow' else '🐃'}
                        <span>{row['CowID']}</span>
                    </div>

                    <div style="font-size:13px;">🧬 <b>Breed:</b> {row['Breed']}</div>
                    <div style="font-size:13px;">⚥ <b>Gender:</b> {row['Gender']}</div>
                    <div style="font-size:13px;">🎂 <b>Age:</b> {age} yrs</div>

                    <div style="
                        display:flex;
                        justify-content:space-between;
                        font-size:12.5px;
                        font-weight:700;
                        border-top:1px solid rgba(255,255,255,0.25);
                        padding-top:6px;
                    ">
                        <span>🩺 {row['Status']}</span>
                        <span>🥛 {row['MilkingStatus']}</span>
                    </div>

                </div>
                """


                with cols[i % 4]:
                    st.markdown(card_html, unsafe_allow_html=True)

            

    elif page == "Customers":   

        st.title("👥 Manage Customers")

        # ---------- STATE ----------
        if "show_add_form" not in st.session_state:
            st.session_state.show_add_form = False

        if "edit_customer_id" not in st.session_state:
            st.session_state.edit_customer_id = None

    

        

        

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
                    rate = st.number_input(
                        "Rate per Litre (₹)",
                        min_value=0.0,
                        step=1.0,
                        value=None,
                        placeholder="Optional"
                    )
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
                    shift,rate if rate > 0 else "", status,
                    dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ])
                st.success("Customer added")
                st.session_state.show_add_form = False
                st.rerun()

        # ---------- CUSTOMER CARDS ----------
        st.markdown("### 📋 Customers List")

        col1, col2 = st.columns([1, 5])

        with col1:
            if st.session_state.view_mode == "display":
                if st.button("✏️ Edit View"):
                    st.session_state.view_mode = "edit"
                    st.rerun()
            else:
                if st.button("👁️ Display View"):
                    st.session_state.view_mode = "display"
                    st.session_state.edit_customer_id = None
                    st.session_state.edit_row_index = None
                    st.rerun()

        df = get_customers_df()
        if st.session_state.view_mode == "edit" and st.session_state.edit_customer_id:

            st.markdown("---")
            st.markdown("## ✏️ Edit Customer")

            row = st.session_state.edit_customer_row

            with st.form("edit_customer_form"):
                c1, c2, c3 = st.columns(3)

                with c1:
                    e_name = st.text_input("Name", row["Name"])
                    e_phone = st.text_input("Phone", row["Phone"])

                with c2:
                    e_email = st.text_input("Email", row["Email"])
                    e_rate = st.number_input(
                        "Rate per Litre (₹)",
                        min_value=0.0,
                        step=1.0,
                        value=float(row["RatePerLitre"]) if row.get("RatePerLitre") not in ("", None) else 0.0
                    )

                with c3:
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
                update = u.form_submit_button("✅ Update")
                cancel = c.form_submit_button("❌ Cancel")

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
                        "Shift": e_shift,
                        "RatePerLitre": e_rate if e_rate > 0 else "",
                        "Status": e_status,
                    }
                )
                st.success("✅ Customer updated successfully")
                st.session_state.edit_customer_id = None
                st.rerun()


        

        for i, row in df.iterrows():

            if i % 4 == 0:
                cols = st.columns(4)
            
            rate = row.get("RatePerLitre", "")
            rate_text = f"₹{float(rate):.2f}/L" if rate not in ("", None) else "₹—/L"

            shift = row["Shift"]
            gradient = {
                "Morning": "linear-gradient(135deg,#43cea2,#185a9d)",
                "Evening": "linear-gradient(135deg,#7F00FF,#E100FF)",
                "Both": "linear-gradient(135deg,#f7971e,#ffd200)"
            }.get(shift, "linear-gradient(135deg,#757f9a,#d7dde8)")

            card_html = textwrap.dedent(f"""
                <div style="
                    height:160px;
                    padding:14px;
                    border-radius:16px;
                    background:{gradient};
                    color:white;
                    box-shadow:0 6px 16px rgba(0,0,0,0.25);
                    line-height:1.35;
                    display:flex;
                    flex-direction:column;
                    justify-content:space-between;
                    margin-bottom:14px;
                    cursor:{'pointer' if st.session_state.view_mode=='edit' else 'default'};
                    opacity:{'1' if st.session_state.view_mode=='edit' else '0.95'};
                ">

                <div style="font-size:15px;font-weight:800;">👤 {row['Name']}</div>

                <div style="font-size:12px;">📞 {row['Phone']}</div>
                <div style="font-size:12px;">✉️ {row['Email']}</div>

                <div style="font-size:12px;display:flex;justify-content:space-between;">
                <span>🆔 {row['CustomerID']}</span>
                <span style="font-weight:700;">💰 {rate_text}</span>
                </div>

                <div style="font-size:12px;">📅 {row['DateOfJoining']}</div>

                <div style="font-size:13px;font-weight:700;">
                ⏰ {row['Shift']} • {row['Status']}
                </div>

                </div>
                """)




            with cols[i % 4]:
                # Always render card correctly
                st.markdown(card_html, unsafe_allow_html=True)

                # Only allow edit in Edit View
                if st.session_state.view_mode == "edit":
                    if st.button(
                        "✏️ Edit",
                        key=f"edit_{row['CustomerID']}",
                        use_container_width=True
                    ):
                        st.session_state.edit_customer_id = row["CustomerID"]
                        st.session_state.edit_customer_row = row.to_dict()
                        st.session_state.edit_row_index = i // 4
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

    elif page=="Transaction":
        st.title("Transaction")
        
    elif page=="Medication":
        st.title("Medication")

    

        
    # ----------------------------
    # REFRESH BUTTON
    # ----------------------------
    if st.sidebar.button("🔁 Refresh"):
        st.rerun()
