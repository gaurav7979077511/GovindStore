import streamlit as st
import pandas as pd
import urllib.parse
import streamlit.components.v1 as components
import datetime as dt
from google.oauth2.service_account import Credentials
import bcrypt
import gspread
import textwrap
import numpy as np
import datetime as dt
import cloudinary
import cloudinary.uploader
import random
import smtplib
from email.message import EmailMessage  
from datetime import datetime, timedelta 



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
MEDICATION_MASTER_TAB = "Medication_Master"
MEDICATION_LOG_TAB = "Medication_Log"
TRANSACTION_TAB="Transaction"
WALLET_TRANSACTION_TAB="Wallet_Transaction"

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

cloudinary.config(
    cloud_name=st.secrets["cloudinary"]["cloud_name"],
    api_key=st.secrets["cloudinary"]["api_key"],
    api_secret=st.secrets["cloudinary"]["api_secret"],
    secure=True
    )

def open_sheet(sheet_id: str, tab: str):
    client = init_gsheets()
    sh = client.open_by_key(sheet_id)
    try:
        return sh.worksheet(tab)
    except gspread.WorksheetNotFound:
        return sh.get_worksheet(0)
        
@st.cache_resource
def open_customer_sheet():
    client = init_gsheets()
    sh = client.open_by_key(MAIN_SHEET_ID)
    return sh.worksheet(CUSTOMER_TAB)

@st.cache_data(ttl=300)  # cache for 5 minutes
def get_customers_df():
    ws = open_customer_sheet()
    data = ws.get_all_values()

    if len(data) <= 1:
        return pd.DataFrame(columns=[
            "CustomerID","Name","Phone","Email",
            "DateOfJoining","Shift","RatePerLitre","Status","Timestamp"
        ])

    df = pd.DataFrame(data[1:], columns=data[0])
    df.columns = df.columns.astype(str).str.strip()
    return df
def open_billing_sheet():
            try:
                return open_sheet(MAIN_SHEET_ID, BILLING_TAB)
            except Exception:
                st.error("❌ Unable to access Billing sheet. Please retry.")
                st.stop()

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

#--helper for billing----

def safe_cell(val):
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val)
    if isinstance(val, (dt.date, dt.datetime)):
        return val.strftime("%Y-%m-%d")
    if pd.isna(val):
        return ""
    return val

@st.cache_data(ttl=30)
def load_bills():
            ws = open_billing_sheet()
            rows = ws.get_all_values()


            if not rows or rows[0] != BILLING_HEADER:
                ws.insert_row(BILLING_HEADER, 1)
                return pd.DataFrame(columns=BILLING_HEADER)

            return pd.DataFrame(rows[1:], columns=rows[0])

BILLING_HEADER = [
            "BillID","CustomerID","CustomerName",
            "FromDate","ToDate",
            "MorningMilk","EveningMilk","TotalMilk",
            "RatePerLitre","BillAmount",
            "PaidAmount","BalanceAmount",
            "BillStatus","DueDate","PaidDate",
            "DailyMilkPattern",
            "GeneratedBy","GeneratedOn"
        ]



# ============================================================
# LOAD AUTH DATA
# ============================================================
@st.cache_resource
def get_auth_sheet():
    try:
        client = init_gsheets()
        return client.open_by_key(AUTH_SHEET_ID).worksheet(AUTH_SHEET_NAME)
    except Exception:
        st.error("❌ AUTH sheet access denied")
        st.stop()

AUTH_SHEET = get_auth_sheet()

@st.cache_data(ttl=60)
def load_auth_data():
    df = pd.DataFrame(AUTH_SHEET.get_all_records())
    df.columns = df.columns.astype(str).str.strip().str.lower()
    return df

auth_df = load_auth_data()

def open_wallet_sheet():
            return open_sheet(MAIN_SHEET_ID, WALLET_TRANSACTION_TAB)
# ============================================================
# HELPERS
# ============================================================
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(stored_hash, password):
    return bcrypt.checkpw(password.encode(), stored_hash.encode())

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp):
    msg = EmailMessage()
    msg["Subject"] = "Password Reset OTP"
    msg["From"] = st.secrets["EMAIL_USER"]
    msg["To"] = email
    msg.set_content(f"""
Your OTP for password reset is:

{otp}

Valid for 5 minutes.

If you did not request this, please ignore this email.
""")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(
            st.secrets["EMAIL_USER"],
            st.secrets["EMAIL_PASS"]
        )
        smtp.send_message(msg)


def send_temp_password_email(to_email,name, username, temp_password):
    msg = EmailMessage()
    msg["Subject"] = f"Dear {name}, Your Account Has Been Created"
    msg["From"] = st.secrets["EMAIL_USER"]
    msg["To"] = to_email

    msg.set_content(f"""
        Hello {name},

        Your account has been created successfully.

            Temporary Login Credentials:
            --------------------------------
            Username: {username}
            Temporary Password: {temp_password}
            --------------------------------

        Please log in and change your password 
        immediately.

        Regards,
        Dairy Farm Management Team
        """)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
        smtp.send_message(msg)



# ============================================================
# SESSION STATE INIT
# ============================================================
defaults = {
    "authenticated": False,
    "user_id": None,
    "username": None,
    "user_name": None,
    "user_role": None,
    "user_accesslevel": None,
    "otp_sent": False,
    "otp_verified": False
}
if "reset_step" not in st.session_state:
    st.session_state.reset_step = "username"

def get_col_index(df, col_name):
    return df.columns.tolist().index(col_name.lower()) + 1


for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ============================================================
# QUERY PARAM (SAFE)
# ============================================================
forgot_mode = st.query_params.get("forgot", "false") == "true"

# ============================================================
# AUTH FLOW
# ============================================================
if not st.session_state.authenticated:

    # =================== FORGOT PASSWORD ===================
    # =================== FORGOT PASSWORD ===================
    if forgot_mode:
        st.subheader("🔐 Forgot Password")

        # STEP 1 — ENTER USERNAME
        if st.session_state.reset_step == "username":

            username_input = st.text_input("Username", key="reset_username")

            if st.button("Send OTP"):

                user = auth_df[auth_df["username"] == username_input]

                if user.empty:
                    st.error("❌ Username not found")
                    st.stop()

                registered_email = user.iloc[0]["email"]

                otp = generate_otp()

                st.session_state.reset_userid = user.iloc[0]["userid"]
                st.session_state.otp = otp
                st.session_state.otp_expiry = datetime.now() + timedelta(minutes=5)

                # 👉 move to OTP screen
                st.session_state.reset_step = "otp"

                # 👉 clear username field
                st.session_state.pop("reset_username", None)

                send_otp_email(registered_email, otp)

                st.success(
                    f"✅ OTP sent to your registered email ({registered_email}). "
                    "Please check your inbox."
                )

                st.rerun()

        # STEP 2 — VERIFY OTP
        elif st.session_state.reset_step == "otp":

            entered_otp = st.text_input("Enter OTP", key="reset_otp")

            if st.button("Verify OTP"):

                if entered_otp != st.session_state.otp:
                    st.error("❌ Invalid OTP")
                    st.stop()

                if datetime.now() > st.session_state.otp_expiry:
                    st.error("❌ OTP expired")
                    st.stop()

                # 👉 move to password screen
                st.session_state.reset_step = "password"

                # 👉 clear OTP field
                st.session_state.pop("reset_otp", None)

                st.success("✅ OTP verified")
                st.rerun()

        # STEP 3 — RESET PASSWORD
        elif st.session_state.reset_step == "password":

            new_pass = st.text_input("New Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")

            if st.button("Update Password"):

                if new_pass != confirm:
                    st.error("❌ Passwords do not match")
                    st.stop()

                hashed = hash_password(new_pass)

                row_idx = auth_df[auth_df["userid"] == st.session_state.reset_userid].index[0] + 2
                password_col = get_col_index(auth_df, "passwordhash")
                date_col = get_col_index(auth_df, "lastpasswordchange")

                AUTH_SHEET.update_cell(row_idx, password_col, hashed)
                AUTH_SHEET.update_cell(
                    row_idx,
                    date_col,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )

                load_auth_data.clear()

                st.success("✅ Password updated successfully")

                # 👉 CLEAN ALL RESET STATE
                for k in [
                    "reset_step",
                    "reset_userid",
                    "otp",
                    "otp_expiry"
                ]:
                    st.session_state.pop(k, None)

                load_auth_data.clear()
                st.query_params.clear()
                st.rerun()

        st.markdown("⬅️ [Back to Login](?)")
        st.stop()


    # =================== LOGIN ===================
    st.title("🔒 Secure Login")

    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")

    if st.button("Login"):
        user = auth_df[auth_df["username"] == username]

        if user.empty:
            st.error("❌ User not found")
            st.stop()

        row = user.iloc[0]

        if row["status"] != "Active":
            st.error("❌ Account inactive")
            st.stop()

        if not verify_password(row["passwordhash"], password):
            st.error("❌ Invalid credentials")
            st.stop()

        # SUCCESS
        st.session_state.authenticated = True
        st.session_state.user_id = row["userid"]
        st.session_state.username = row["username"]
        st.session_state.user_name = row["name"]
        st.session_state.user_role = row["role"]
        st.session_state.user_accesslevel = row["accesslevel"]

        st.success(f"✅ Welcome, {row['name']}")
        st.rerun()

    st.markdown(
        "<div style='text-align:right;font-size:13px;'>"
        "<a href='?forgot=true'>Forgot Password?</a>"
        "</div>",
        unsafe_allow_html=True
    )

# ============================================================
# DASHBOARD
# ============================================================
else:
    if st.sidebar.button("🚪 Logout"):
        for k in list(st.session_state.keys()):
            st.session_state.pop(k)
        st.query_params.clear()
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
            "Medicine",
            "Medication",
            "Transaction",
            "Profile"

            
        ],
    )

    # ============================================================
    # GLOBAL COW HELPERS (USED BY MULTIPLE MODULES)
    # ============================================================
    
    COW_HEADER = [
        "CowID","ParentCowID","TagNumber","Gender","Breed",
        "AgeYears","PurchaseDate","PurchasePrice",
        "SoldPrice","SoldDate",
        "Status","MilkingStatus",
        "Notes","BirthYear","Timestamp"
    ]
    
    MEDICATION_LOG_HEADER = [
        "LogID",
        "CowID",
        "MedicineID",
        "MedicineName",
        "DoseGiven",
        "DoseUnit",
        "GivenOn",
        "GivenBy",
        "FrequencyType",
        "FrequencyValue",
        "FrequencyUnit",
        "Notes",
        "NextDueDate"
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
            "Date", "Shift", "CowID", "TagNumber", "MilkQuantity", "Timestamp"
        ]
    
        # ================== SHEET HELPERS ==================
        def open_milking_sheet():
            return open_sheet(MAIN_SHEET_ID, MILKING_TAB)
    
        def load_milking_data():
            ws = open_milking_sheet()
            rows = ws.get_all_values()
    
            if not rows or rows[0] != MILKING_HEADER:
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
                            f"COW: {cow['TagNumber']}",
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
                            st.error(f"Milk quantity required for {cow['TagNumber']}")
                            has_error = True
                            break
    
                        # ❌ Duplicate check
                        if (
                            (df_existing["Date"] == date_str) &
                            (df_existing["Shift"] == shift) &
                            (df_existing["CowID"] == cow["CowID"])
                        ).any():
                            st.error(f"Duplicate entry found for {cow['TagNumber']}")
                            has_error = True
                            break
    
                        rows_to_insert.append([
                            date_str,
                            shift,
                            cow["CowID"],
                            cow["TagNumber"],
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

                # ---- WALLET TXN ----
                open_wallet_sheet().append_row(
                        [
                            f"WTXN{dt.datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                            st.session_state.user_id,
                            st.session_state.user_name,
                            amount,
                            "DEBIT",
                            expense_id,
                            f"Amount used for  {category}",
                            dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
                ws.insert_row(INVESTMENT_HEADER, 1)
                return pd.DataFrame(columns=INVESTMENT_HEADER)
    
            return pd.DataFrame(rows[1:], columns=rows[0])
    
        # =========================================================
        # CLOUDINARY UPLOAD
        # =========================================================

    
    
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
        dairy_users_df = auth_df[
            auth_df["accesslevel"]
            .fillna("")
            .str.contains(r"\bdairy\b", case=False)
        ][["userid", "name"]]

        # userid -> display label
        user_label_map = {
            row["userid"]: f"{row['name']}"
            for _, row in dairy_users_df.iterrows()
        }

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
        for u in dairy_users_df:
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
                    st.text_input(
                        "invested_by",
                        value=st.session_state.user_name,
                        disabled=True
                    )

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
                        options=["Company Account"] + list(user_label_map.keys()),
                        format_func=lambda x: (
                            "Company Account"
                            if x == "Company Account"
                            else user_label_map[x]
                        ),
                    )



                # Single source of truth
                wallet_user_id = None
                wallet_user_name = None

                if destination != "Company Account":
                    wallet_user_id = destination
                    wallet_user_name = auth_df.loc[
                        auth_df["userid"] == destination, "name"
                    ].iloc[0]


    
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
    
                wallet_user_name = ""

                if destination != "Company Account" and wallet_user_id:
                    wallet_user_name = auth_df.loc[
                        auth_df["userid"] == wallet_user_id, "name"
                    ].iloc[0]

                final_destination = (
                    f"User Wallet: {wallet_user_name}"
                    if destination != "Company Account"
                    else "Company Account"
                )

    
                file_url = upload_to_cloudinary(proof) if proof else ""
                InvestmentID=f"INV{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"
    
                open_investment_sheet().append_row(
                    [
                        InvestmentID,
                        dt.date.today().strftime("%Y-%m-%d"),
                        st.session_state.user_name,
                        amount,
                        inv_type,
                        final_destination,
                        file_url,
                        notes,
                        dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ],
                    value_input_option="USER_ENTERED",
                )

                # ---- WALLET TXN ----
                open_wallet_sheet().append_row(
                        [
                            f"WTXN{dt.datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                            wallet_user_id,
                            wallet_user_name,
                            amount,
                            "CREDIT",
                            InvestmentID,
                            f"Investment Amount From {st.session_state.user_name}",
                            dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ],
                        value_input_option="USER_ENTERED"
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




    # ======================================================
    # PAYMENT PAGE
    # ======================================================
    elif page == "Payment":

        st.title("💳 Payments")

        # ======================================================
        # HELPERS
        # ======================================================
        def open_payment_sheet():
            return open_sheet(MAIN_SHEET_ID, PAYMENT_TAB)


        @st.cache_data(ttl=30)
        def load_payments():
            ws = open_payment_sheet()
            rows = ws.get_all_values()
            if len(rows) <= 1:
                return pd.DataFrame(columns=[
                    "PaymentID","BillID","CustomerID","CustomerName",
                    "PaidAmount","PaymentMode","ReceivedBy","ReceivedOn","Remarks"
                ])
            return pd.DataFrame(rows[1:], columns=rows[0])

        payments_df = load_payments()
        bills_df = load_bills()
        # ================= CLEAN TYPES (STEP 4) =================
        if not bills_df.empty:
            bills_df["FromDate"] = pd.to_datetime(bills_df["FromDate"], errors="coerce")
            bills_df["ToDate"] = pd.to_datetime(bills_df["ToDate"], errors="coerce")
            bills_df["DueDate"] = pd.to_datetime(bills_df["DueDate"], errors="coerce")
            bills_df["PaidDate"] = pd.to_datetime(bills_df["PaidDate"], errors="coerce")


        # ================= CLEAN TYPES =================
        if not payments_df.empty:
            payments_df["PaidAmount"] = pd.to_numeric(payments_df["PaidAmount"], errors="coerce").fillna(0)
            payments_df["ReceivedOn"] = pd.to_datetime(payments_df["ReceivedOn"], errors="coerce")

        bills_df["BillAmount"] = pd.to_numeric(bills_df["BillAmount"])
        bills_df["PaidAmount"] = pd.to_numeric(bills_df["PaidAmount"])
        bills_df["BalanceAmount"] = pd.to_numeric(bills_df["BalanceAmount"])
        bills_df["DueDate"] = pd.to_datetime(bills_df["DueDate"])

        # ======================================================
        # KPI SECTION
        # ======================================================
        st.subheader("📊 Payment Summary")

        total_received = payments_df["PaidAmount"].sum() if not payments_df.empty else 0

        this_month = pd.Timestamp.today().strftime("%Y-%m")
        this_month_received = payments_df[
            payments_df["ReceivedOn"].dt.strftime("%Y-%m") == this_month
        ]["PaidAmount"].sum() if not payments_df.empty else 0

        monthly_avg = (
            payments_df.groupby(payments_df["ReceivedOn"].dt.to_period("M"))["PaidAmount"].sum().mean()
            if not payments_df.empty else 0
        )

        k1, k2, k3 = st.columns(3)

        def kpi(title, value):
            st.markdown(
                f"""
                <div style="padding:14px;border-radius:12px;
                background:#0f172a;color:white;margin-bottom:14px;">
                    <div style="font-size:13px;opacity:.8">{title}</div>
                    <div style="font-size:22px;font-weight:800">₹ {value:,.0f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with k1: kpi("Total Received", total_received)
        with k2: kpi("Received This Month", this_month_received)
        with k3: kpi("Avg Monthly Received", monthly_avg)

        st.divider()

        # ======================================================
        # PENDING BILLS (QUICK PICK)
        # ======================================================
        st.subheader("🧾 Pending Bills")

        pending_bills = bills_df[bills_df["BalanceAmount"] > 0]

        if pending_bills.empty:
            st.success("🎉 No pending bills")
        else:
            PER_ROW = 4  # change to 3 / 5 if you want
            rows = [
                pending_bills.iloc[i:i + PER_ROW]
                for i in range(0, len(pending_bills), PER_ROW)
            ]

            for row in rows:
                cols = st.columns(len(row))
                for col, (_, r) in zip(cols, row.iterrows()):
                    first_name = str(r["CustomerName"]).strip().split()[0]
                    with col:
                        if st.button(
                            f"""{first_name}
        || ₹ {float(r['BillAmount']):,.0f}
        || ₹ {float(r['BalanceAmount']):,.0f}""",
                            key=f"pick_{r['BillID']}",
                            use_container_width=True
                        ):
                            st.session_state.selected_bill_id = r["BillID"]
                            st.session_state.show_payment_window = True
                            st.rerun()


        # ======================================================
        # TOGGLE RECEIVE PAYMENT WINDOW
        # ======================================================
        if "show_payment_window" not in st.session_state:
            st.session_state.show_payment_window = False

        # ======================================================
        # RECEIVE PAYMENT
        # ======================================================
        if st.session_state.show_payment_window:

            st.subheader("💰 Receive Payment")

            selected_bill = st.session_state.get("selected_bill_id")

            if not selected_bill:
                st.warning("⚠️ Please select a bill to collect payment.")
                st.stop()



            bill = bills_df[bills_df["BillID"] == selected_bill].iloc[0]
            

            st.markdown(
                f"""
                **Bill ID:** `{bill['BillID']}`  
                **Customer:** {bill['CustomerName']}  
                **Total Bill:** ₹ {float(bill['BillAmount']):,.0f}  
                **Already Paid:** ₹ {float(bill['PaidAmount']):,.0f}  
                **Pending Amount:** ₹ {float(bill['BalanceAmount']):,.0f}
                """
            )


            received_amt = st.number_input(
                "Received Amount *",
                value=None,
                placeholder=f"Enter amount (Max ₹ {float(bill['BalanceAmount']):,.0f})",
                step=1.0
            )


            payment_mode = st.selectbox("Payment Mode", ["Cash", "UPI", "Bank Transfer"])
            remarks = st.text_input("Remarks (optional)")

            col1, col2 = st.columns(2)

            # ================= CONFIRM =================
            with col1:
                if st.button("✅ Collect Payment"):
                    if received_amt is None:
                        st.error("❌ Please enter received amount")
                        st.stop()

                    if received_amt <= 0:
                        st.error("❌ Amount must be greater than 0")
                        st.stop()

                    if received_amt > float(bill["BalanceAmount"]):
                        st.error("❌ Amount cannot exceed pending balance")
                        st.stop()


                    now = dt.datetime.now()


                    # ---- INSERT PAYMENT ----
                    open_payment_sheet().append_row(
                        [
                            f"PAY{now.strftime('%Y%m%d%H%M%S%f')}",
                            bill["BillID"],
                            bill["CustomerID"],
                            bill["CustomerName"],
                            received_amt,
                            payment_mode,
                            st.session_state.user_name,
                            now.strftime("%Y-%m-%d %H:%M:%S"),
                            remarks
                        ],
                        value_input_option="USER_ENTERED"
                    )

                    # ---- UPDATE BILL ----
                    new_paid = bill["PaidAmount"] + received_amt
                    new_balance = bill["BillAmount"] - new_paid
                    if new_balance == 0:
                        status = "Paid"
                        paid_date = now.strftime("%Y-%m-%d")
                    else:
                        status = "Partially Paid"
                        paid_date = ""   # keep blank


                    ws = open_billing_sheet()
                    bill_row = bills_df.index[bills_df["BillID"] == bill["BillID"]][0] + 2

                    ws.update(
                        f"K{bill_row}:O{bill_row}",
                        [[
                            new_paid,
                            new_balance,
                            status,
                            bill["DueDate"].strftime("%Y-%m-%d"),
                            paid_date
                        ]]
                    )



                    # ---- WALLET TXN ----
                    open_wallet_sheet().append_row(
                        [
                            f"WTXN{now.strftime('%Y%m%d%H%M%S%f')}",
                            st.session_state.user_id,
                            st.session_state.user_name,
                            received_amt,
                            "CREDIT",
                            bill["BillID"],
                            f"Payment received from {bill['CustomerName']}",
                            now.strftime("%Y-%m-%d %H:%M:%S")
                        ],
                        value_input_option="USER_ENTERED"
                    )

                    st.success("✅ Payment recorded successfully")
                    st.cache_data.clear()
                    st.session_state.show_payment_window = False
                    st.session_state.pop("selected_bill_id", None)
                    st.rerun()

            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.show_payment_window = False
                    st.rerun()

        st.divider()

        # ======================================================
        # PAYMENT HISTORY
        # ======================================================
        st.subheader("📜 Payment History")

        if payments_df.empty:
            st.info("No payments recorded yet.")
        else:
            st.dataframe(
                payments_df.sort_values("ReceivedOn", ascending=False),
                use_container_width=True
            )


    
    #----Billing------
    elif page == "Billing":

        st.title("🧾 Billing")

        # ======================================================
        # CONSTANTS
        # ======================================================
        

        # ======================================================
        # SHEET HELPERS
        # ======================================================
        


        @st.cache_data(ttl=300)
        def load_bitran_df():
            ws = open_sheet(MAIN_SHEET_ID, BITRAN_TAB)
            rows = ws.get_all_values()

            if len(rows) <= 1:
                return pd.DataFrame()

            df = pd.DataFrame(rows[1:], columns=rows[0])
            df["MilkDelivered"] = pd.to_numeric(df["MilkDelivered"], errors="coerce").fillna(0)
            df["Date"] = pd.to_datetime(df["Date"])
            return df

        
        

        # ======================================================
        # SAFE VALUE (CRITICAL FIX)
        # ======================================================
        def safe(val):
            if pd.isna(val):
                return ""
            if isinstance(val, (int, float)):
                return float(val)
            return str(val)

        # ======================================================
        # MILK CALCULATION + MISSING DATES
        # ======================================================
        def calculate_milk(bitran_df, customer_id, from_date, to_date):
            if bitran_df.empty:
                return 0, 0, 0, [], []

            df = bitran_df[
                (bitran_df["CustomerID"] == customer_id) &
                (bitran_df["Date"] >= pd.to_datetime(from_date)) &
                (bitran_df["Date"] <= pd.to_datetime(to_date))
            ]

            df["day"] = df["Date"].dt.date

            morning = df[df["Shift"] == "Morning"]["MilkDelivered"].sum()
            evening = df[df["Shift"] == "Evening"]["MilkDelivered"].sum()
            total = morning + evening

            # ---- DAILY PATTERN LOGIC ----
            all_dates = pd.date_range(from_date, to_date)
            daily_pattern = []
            missing_dates = []

            for d in all_dates:
                day_total = df[df["day"] == d.date()]["MilkDelivered"].sum()
                daily_pattern.append(round(day_total, 2))
                if day_total == 0:
                    missing_dates.append(d.day)

            return (
                round(morning, 2),
                round(evening, 2),
                round(total, 2),
                missing_dates,
                daily_pattern
            )



        # ======================================================
        # LOAD DATA
        # ======================================================
        customers_df = get_customers_df()
        bills_df = load_bills()
        bitran_df = load_bitran_df()


        customers_df["RatePerLitre"] = pd.to_numeric(
            customers_df.get("RatePerLitre", 0), errors="coerce"
        ).fillna(0)

        if not bills_df.empty:
            bills_df["FromDate"] = pd.to_datetime(bills_df["FromDate"])
            bills_df["ToDate"] = pd.to_datetime(bills_df["ToDate"])

        # ======================================================
        # KPI SECTION
        # ======================================================
        st.subheader("📊 Billing Summary")

        pending_df = bills_df[bills_df["BillStatus"] != "Paid"] if not bills_df.empty else pd.DataFrame()
        total_pending_amt = pending_df["BalanceAmount"].astype(float).sum() if not pending_df.empty else 0

        last_month = (dt.date.today().replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
        last_month_df = bills_df[bills_df["FromDate"].dt.strftime("%Y-%m") == last_month] if not bills_df.empty else pd.DataFrame()

        k1, k2, k3, k4 = st.columns(4)

        def kpi(title, value):
            st.markdown(
                f"""
                <div style="padding:14px;border-radius:12px;
                background:#0f172a;color:white;margin-bottom:14px;">
                <div style="font-size:13px;opacity:.8">{title}</div>
                <div style="font-size:22px;font-weight:800">₹ {value:,.0f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with k1: kpi("Pending Bills", len(pending_df))
        with k2: kpi("Pending Amount", total_pending_amt)
        with k3: kpi("Last Month Billed", last_month_df["BillAmount"].astype(float).sum() if not last_month_df.empty else 0)
        with k4: kpi("Last Month Received", last_month_df["PaidAmount"].astype(float).sum() if not last_month_df.empty else 0)

        st.divider()

        # ======================================================
        # TOGGLE BILL WINDOW
        # ======================================================
        if "show_bill_window" not in st.session_state:
            st.session_state.show_bill_window = False

        if st.button("➕ Generate Bill"):
            st.session_state.show_bill_window = not st.session_state.show_bill_window

        
        # ======================================================
        # BILL GENERATION
        # ======================================================


        if st.session_state.show_bill_window:

            mode = st.radio("Billing Mode", ["Bulk Monthly", "Individual"], horizontal=True)

            today = dt.date.today()

            # ================= BULK BILLING =================
            if mode == "Bulk Monthly":

                month = st.selectbox(
                    "Select Month",
                    pd.date_range(end=today, periods=12, freq="M").strftime("%Y-%m")
                )

                y, m = map(int, month.split("-"))
                from_date = dt.date(y, m, 1)
                to_date = (from_date + pd.offsets.MonthEnd(1)).date()
                due_date = dt.date.today() + dt.timedelta(days=7)

                st.subheader("🔍 Preview")

                preview = []

                for _, c in customers_df.iterrows():
                    if c["Status"] != "Active":
                        continue
                    if c["Name"] == "Dairy-CMS":
                        continue

                    # overlap check
                    if not bills_df.empty and (
                        (bills_df["CustomerID"] == c["CustomerID"]) &
                        (bills_df["FromDate"] <= pd.to_datetime(to_date)) &
                        (bills_df["ToDate"] >= pd.to_datetime(from_date))
                    ).any():
                        continue

                    morning, evening, total, missing ,daily_pattern= calculate_milk(bitran_df,
                        c["CustomerID"], from_date, to_date
                    )

                    if total == 0 or c["RatePerLitre"] <= 0:
                        continue

                    amount = round(total * c["RatePerLitre"], 2)

                    preview.append({
                        "cust": c,
                        "morning": morning,
                        "evening": evening,
                        "total": total,
                        "amount": amount,
                        "missing": missing,
                        "daily_pattern":daily_pattern
                    })

                if not preview:
                    st.info("No eligible customers for this month.")

                else:
                    selected = {}
                    for p in preview:
                        chk = st.checkbox(
                            f"{p['cust']['Name']} | 🥛 {p['total']} L | ₹ {p['cust']['RatePerLitre']}/L | 💰 ₹ {p['amount']}",
                            value=True,
                            key=f"bulk_{p['cust']['CustomerID']}"
                        )



                        selected[p["cust"]["CustomerID"]] = chk

                        if p["missing"]:
                            st.caption(f"No milk on: {', '.join(map(str,p['missing']))}")

                    if st.button("✅ Generate Bills"):
                        ws = open_billing_sheet()
                        count = 0

                        
                        rows_to_add = []
                        for p in preview:
                            c = p["cust"]
                            if not selected.get(c["CustomerID"]):
                                continue
                            daily_pattern_str = ",".join(map(str, p["daily_pattern"]))
                            rows_to_add.append([
                                f"BILL{dt.datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                                safe(c["CustomerID"]),
                                safe(c["Name"]),
                                from_date.strftime("%Y-%m-%d"),
                                to_date.strftime("%Y-%m-%d"),
                                safe(p["morning"]),
                                safe(p["evening"]),
                                safe(p["total"]),
                                safe(c["RatePerLitre"]),
                                safe(p["amount"]),
                                0,
                                safe(p["amount"]),
                                "Payment Pending",
                                due_date.strftime("%Y-%m-%d"),
                                "",
                                daily_pattern_str, 
                                safe(st.session_state.user_name),
                                dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            ])

                            count += 1
                        ws.append_rows(rows_to_add, value_input_option="USER_ENTERED")
                        st.cache_data.clear()
                        st.success(f"✅ {count} bill(s) generated")
                        st.session_state.show_bill_window = False
                        st.rerun()

            # ================= INDIVIDUAL =================
            else:
                customer = st.selectbox("Customer", customers_df["Name"].tolist())
                cust = customers_df[customers_df["Name"] == customer].iloc[0]

                from_date = st.date_input(
                    "From Date",
                    value=dt.date.today()
                )

                to_date = st.date_input(
                    "To Date",
                    value=from_date,
                    min_value=from_date
                )
                if to_date < from_date:
                    st.error("❌ To Date cannot be earlier than From Date.")
                    st.stop()


                due_date = dt.date.today() + dt.timedelta(days=7)

                # overlap validation
                overlap_df = bills_df[
                    (bills_df["CustomerID"] == cust["CustomerID"]) &
                    (bills_df["FromDate"] <= pd.to_datetime(to_date)) &
                    (bills_df["ToDate"] >= pd.to_datetime(from_date))
                ]

                if not overlap_df.empty:
                    last_to_date = overlap_df["ToDate"].max().date()
                    st.error(
                        f"❌ Bill already exists up to {last_to_date.strftime('%d/%m/%Y')}. "
                        f"Please generate the bill after this date."
                    )
                else:
                    morning, evening, total, missing, daily_pattern = calculate_milk(bitran_df,
                        cust["CustomerID"], from_date, to_date
                    )

                    if total <= 0:
                        st.error("❌ Cannot generate bill. No milk delivered in selected date range.")
                        st.stop()

                    rate = cust["RatePerLitre"]
                    if rate <= 0:
                        rate = st.number_input("Enter Rate", min_value=1,value=1)

                    amount = round(total * rate, 2)
                    if amount <= 0:
                        st.error("❌ Bill amount is zero. Please check milk delivery or rate.")
                        st.stop()


                    st.info(
                        f"🥛 Milk: {total} L | 💵 Rate: ₹ {rate} / L | 💰 Amount: ₹ {amount}"
                    )

                    if missing:
                        st.caption(f"No milk on: {', '.join(map(str,missing))}")

                    if st.button("✅ Generate Bill"):
                        ws = open_billing_sheet()
                        daily_pattern_str = ",".join(map(str, daily_pattern))
                        ws.append_row(
                            [
                                f"BILL{dt.datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                                safe(cust["CustomerID"]),
                                safe(cust["Name"]),
                                from_date.strftime("%Y-%m-%d"),
                                to_date.strftime("%Y-%m-%d"),
                                safe(morning),
                                safe(evening),
                                safe(total),
                                safe(rate),
                                safe(amount),
                                0,
                                safe(amount),
                                "Payment Pending",
                                due_date.strftime("%Y-%m-%d"),
                                "",
                                daily_pattern_str,
                                safe(st.session_state.user_name),
                                dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            ],
                            value_input_option="USER_ENTERED"
                        )

                        st.success("Bill generated")
                        st.cache_data.clear()
                        st.session_state.show_bill_window = False
                        st.rerun()
        # ======================================================
        # BILL LIST (ALWAYS VISIBLE)
        # ======================================================

        st.subheader("📋 Bills")

        # ---------- Safety checks ----------
        if bills_df.empty:
            st.info("No bills available.")
            st.stop()

        # ---------- Ensure datetime ----------
        bills_df["FromDate"] = pd.to_datetime(bills_df["FromDate"])
        bills_df["ToDate"] = pd.to_datetime(bills_df["ToDate"])
        bills_df["DueDate"] = pd.to_datetime(bills_df["DueDate"])
        bills_df["GeneratedOn"] = pd.to_datetime(bills_df["GeneratedOn"])

        today = pd.Timestamp.today().normalize()

        # ---------- Show pending + last 4 months paid ----------
        show_df = bills_df[
            (bills_df["BillStatus"] != "Paid") |
            (bills_df["FromDate"] >= today - pd.DateOffset(months=4))
        ].sort_values("GeneratedOn", ascending=False)

        cols = st.columns(3)

        for i, r in show_df.iterrows():

            # ---------- Card color ----------
            if r["BillStatus"] == "Paid":
                gradient = "linear-gradient(135deg,#22c55e,#15803d)"
                status_badge = "🟢 Paid"

            elif r["BillStatus"] == "Partially Paid":
                gradient = "linear-gradient(135deg,#fb923c,#ea580c)"  # orange
                status_badge = "🟠 Partially Paid"

            elif r["DueDate"] < today:
                gradient = "linear-gradient(135deg,#ef4444,#991b1b)"
                status_badge = "🔴 Overdue"

            else:
                gradient = "linear-gradient(135deg,#facc15,#ca8a04)"
                status_badge = "🟡 Pending"


            # ---------- daily_pattern  ----------
            # Default → show Due Date
            date_label = f"Due: {r['DueDate'].date()}"

            # If PaidDate exists and is NOT blank → override
            if "PaidDate" in r and pd.notna(r["PaidDate"]) and str(r["PaidDate"]).strip() != "":
                date_label = f"Paid on: {pd.to_datetime(r['PaidDate']).date()}"

            balance_html = ""
            if float(r["BalanceAmount"]) > 0:
                balance_html = f"""
                <span style="
                    font-size:12px;
                    font-weight:700;
                    background:#00000033;
                    padding:4px 8px;
                    border-radius:8px;
                ">
                    Pending ₹ {float(r['BalanceAmount']):,.0f}
                </span>
                """

            DailyMilkPattern_html = ""
            if "DailyMilkPattern" in r and pd.notna(r["DailyMilkPattern"]) and r["DailyMilkPattern"]:
                for d in str(r["DailyMilkPattern"]).split(","):
                    DailyMilkPattern_html += f"""
                    <span style="
                        padding:2px 6px;
                        background:#ffffff33;
                        border-radius:6px;
                        font-size:11px;
                        margin-right:4px;
                        margin-top:4px;
                        display:inline-block;
                    ">{d.strip()}</span>
                    """
            else:
                DailyMilkPattern_html = "<span style='font-size:11px;opacity:.9;'>No daily_pattern</span>"

            card_html = f"""
            <div style="
                background:{gradient};
                color:white;
                padding:14px;
                border-radius:16px;
                height:220px;
                box-shadow:0 6px 18px rgba(0,0,0,0.25);
                display:flex;
                flex-direction:column;
                justify-content:space-between;
                font-family:Inter,system-ui,sans-serif;
                box-sizing:border-box;
            ">

                <!-- Header -->
                <div>
                    <div style="font-size:15px;font-weight:800;word-wrap:break-word;">
                        {r['CustomerName']}
                    </div>
                    <div style="font-size:11px;opacity:0.9;word-wrap:break-word;">
                        {r['BillID']}
                    </div>
                </div>

                <!-- Period -->
                <div style="font-size:12px;margin-top:6px;">
                    📅 {r['FromDate'].date()} → {r['ToDate'].date()}
                </div>

                <!-- Milk, Rate & Amount -->
                <div style="margin-top:6px;">
                    <div style="
                        font-size:13px;
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                        opacity:0.95;
                    ">
                        <span>🥛 <b>{r['TotalMilk']} L</b></span>
                        <span style="font-size:12px;opacity:0.85;">₹ {float(r['RatePerLitre']):.2f} / L</span>
                    </div>

                    <div style="
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                        margin-top:2px;
                    ">
                        <div style="font-size:18px;font-weight:900;">
                            ₹ {float(r['BillAmount']):,.0f}
                        </div>
                        {balance_html}
                    </div>

                </div>


                <!--  DailyMilkPattern_html -->
                <div style="margin-top:6px;">
                    {DailyMilkPattern_html}
                </div>

                <!-- Footer -->
                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    margin-top:8px;
                    font-size:12px;
                ">
                    <span>{status_badge}</span>
                    <span>{date_label}</span>
                </div>

            </div>
            """

            with cols[i % 3]:
                components.html(card_html, height=235)



    
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
        if st.button("Create Cow Profile"):
            st.session_state.show_add_cow = True
    
        if st.session_state.show_add_cow:
            with st.form("add_cow"):
                c1, c2, c3 = st.columns(3)
    
                with c1:
                    tagnumber = st.text_input("Tag Number")
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
    
                prefix = "COW" 
                cow_id = f"{prefix}{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"
                birth_year = CURRENT_YEAR - int(age)
    
                open_cow_sheet().append_row(
                    [
                        cow_id,
                        parent,
                        tagnumber,
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

        col1, col2 = st.columns([6, 1])

        with col2:
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
                        e_tagnumber = st.text_input("TagNumber",value=row["TagNumber"])
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
                            "TagNumber": e_tagnumber,
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

                parent_id = row.get("ParentCowID", "").strip()
                purchase_price = row.get("PurchasePrice", "")
                sold_price = row.get("SoldPrice", "")

                # Line 1: Parent OR Purchase
                if parent_id:
                    source_line = f"👪 <span style='opacity:0.85;'>Parent:</span> {parent_id}"
                elif purchase_price:
                    source_line = f"💰 <span style='opacity:0.85;'>Bought:</span> ₹{purchase_price}"
                else:
                    source_line = ""

                # Line 2: Sold amount (only if sold)
                sold_line = ""
                if row["Status"] == "Sold" and sold_price:
                    sold_line = f"🏷️ <span style='opacity:0.85;'>Sold:</span> ₹{sold_price}"


                card_html = f"""
                <div style="
                    height:130px;
                    padding:14px 16px;
                    border-radius:14px;
                    background:{gradient};
                    color:white;
                    box-shadow:0 6px 18px rgba(0,0,0,0.22);
                    display:flex;
                    flex-direction:column;
                    justify-content:space-between;
                    margin-bottom:14px;
                    font-family:Inter, system-ui, sans-serif;
                ">

                    <!-- Header -->
                    <div style="
                        font-size:14.5px;
                        font-weight:600;
                        display:flex;
                        align-items:center;
                        gap:6px;
                    ">
                        🐄 
                        <span>{row['TagNumber']}</span>
                    </div>

                    <!-- Info -->
                    <div style="
                        font-size:12px;
                        line-height:1.35;
                        opacity:0.95;
                    ">
                        <div>🧬 <span style="opacity:0.85;">Breed:</span> {row['Breed']}</div>
                        <div>⚥ <span style="opacity:0.85;">Gender:</span> {row['Gender']}</div>
                        <div>🎂 <span style="opacity:0.85;">Age:</span> {age} yrs</div>

                        {f"<div>{source_line}</div>" if source_line else ""}
                        {f"<div>{sold_line}</div>" if sold_line else ""}
                    </div>

                    <!-- Footer -->
                    <div style="
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                        font-size:11.5px;
                        font-weight:600;
                        margin-top:4px;
                    ">
                        <span style="
                            padding:3px 8px;
                            border-radius:999px;
                            background:rgba(255,255,255,0.18);
                        ">
                            🩺 {row['Status']}
                        </span>

                        <span style="
                            padding:3px 8px;
                            border-radius:999px;
                            background:rgba(0,0,0,0.22);
                        ">
                            🥛 {row['MilkingStatus']}
                        </span>
                    </div>

                </div>
                """





                with cols[i % 4]:
                    components.html(card_html, height=170)

                    # Render Edit button ONLY in edit mode
                    if st.session_state.cow_view_mode == "edit":
                        if st.button(
                            "✏️ Edit",
                            key=f"edit_cow_{row['CowID']}",
                            use_container_width=True
                        ):
                            st.session_state.edit_cow_id = row["CowID"]
                            st.session_state.edit_cow_row = row.to_dict()
                            st.rerun()







            

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

        col1, col2 = st.columns([6, 1])

        with col2:
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


    elif page == "Medicine":

        st.title("🧪 Medicine Master")

        if "medicine_view_mode" not in st.session_state:
            st.session_state.medicine_view_mode = "view"   # view | edit

        if "editing_med_id" not in st.session_state:
            st.session_state.editing_med_id = None

        if "show_add_medicine" not in st.session_state:
            st.session_state.show_add_medicine = False


        # ======================================================
        # CONSTANTS
        # ======================================================
        MEDECINE_HEADER = [
            "MedicineID","MedicineName","MedicineType","ApplicableFor",
            "DefaultDose","DoseUnit",
            "FrequencyType","FrequencyValue","FrequencyUnit",
            "TotalCost","TotalUnits","CostPerDose",
            "StockAvailable","Status","MedicineImageURL",
            "Notes","CreatedBy","CreatedOn"
        ]

        # ======================================================
        # cloudinary uploader
        # ======================================================
        def upload_to_cloudinary(file):
            result = cloudinary.uploader.upload(
                file,
                folder="dairy/medicine",  
                resource_type="image"
            )
            return result["secure_url"]

        # ======================================================
        # HELPERS
        # ======================================================
        def open_medicine_sheet():
            return open_sheet(MAIN_SHEET_ID, MEDICATION_MASTER_TAB)

        @st.cache_data(ttl=30)
        def load_medicine_df():
            ws = open_medicine_sheet()
            rows = ws.get_all_values()

            if not rows or rows[0] != MEDECINE_HEADER:
                ws.insert_row(MEDECINE_HEADER, 1)
                return pd.DataFrame(columns=MEDECINE_HEADER)

            return pd.DataFrame(rows[1:], columns=rows[0])

        medicine_df = load_medicine_df()

        # ======================================================
        # CLEAN TYPES
        # ======================================================
        if not medicine_df.empty:
            medicine_df["TotalCost"] = pd.to_numeric(medicine_df["TotalCost"], errors="coerce").fillna(0)
            medicine_df["TotalUnits"] = pd.to_numeric(medicine_df["TotalUnits"], errors="coerce").fillna(0)
            medicine_df["CostPerDose"] = pd.to_numeric(medicine_df["CostPerDose"], errors="coerce").fillna(0)
            medicine_df["StockAvailable"] = pd.to_numeric(medicine_df["StockAvailable"], errors="coerce").fillna(0)

        # ======================================================
        # KPI SECTION
        # ======================================================
        st.subheader("📊 Medicine Overview")

        total_meds = len(medicine_df)
        active_meds = len(medicine_df[medicine_df["Status"] == "Active"]) if not medicine_df.empty else 0
        low_stock = len(medicine_df[medicine_df["StockAvailable"] <= 5]) if not medicine_df.empty else 0

        k1, k2, k3 = st.columns(3)

        def kpi(title, value):
            st.markdown(
                f"""
                <div style="
                    padding:14px;
                    border-radius:14px;
                    background:#0f172a;
                    color:white;
                    margin-bottom:14px;">
                    <div style="font-size:13px;opacity:.8">{title}</div>
                    <div style="font-size:22px;font-weight:900">{value}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with k1: kpi("Total Medicines", total_meds)
        with k2: kpi("Active Medicines", active_meds)
        with k3: kpi("Low Stock (≤5)", low_stock)

        st.divider()

        # ======================================================
        # TOGGLE ADD FORM
        # ======================================================
        if "show_add_medicine" not in st.session_state:
            st.session_state.show_add_medicine = False

        if st.button("➕ Add Medicine"):
            st.session_state.show_add_medicine = not st.session_state.show_add_medicine

        # ======================================================
        # ADD MEDICINE FORM
        # ======================================================
        if st.session_state.show_add_medicine:

            st.subheader("🧾 Add New Medicine")

            with st.form("medicine_form"):

                name = st.text_input("Medicine Name", placeholder="Eg: FMD Vaccine")
                mtype = st.selectbox("Medicine Type", ["Vaccine", "Injection", "Tablet", "Syrup"])
                applicable = st.selectbox("Applicable For", ["Kid", "Adult"])

                col1, col2 = st.columns(2)
                with col1:
                    default_dose = st.number_input(
                        "Default Dose",
                        value=None,
                        placeholder="Eg: 5",
                        step=0.1
                    )
                with col2:
                    dose_unit = st.selectbox("Dose Unit", ["ml", "tablet", "mg"])

                freq_type = st.selectbox("Frequency Type", ["OneTime", "Recurring"])

                col3, col4 = st.columns(2)
                with col3:
                    freq_value = st.number_input(
                        "Frequency Value",
                        value=None,
                        placeholder="Eg: 90"
                    )
                with col4:
                    freq_unit = st.selectbox("Frequency Unit", ["Hour","Days", "Weeks", "Months"])

                col5, col6 = st.columns(2)
                with col5:
                    total_cost = st.number_input(
                        "Total Cost (₹)",
                        value=None,
                        placeholder="Eg: 1200"
                    )
                with col6:
                    total_units = st.number_input(
                        "Total Units",
                        value=None,
                        placeholder="Eg: 10"
                    )
                image_file = st.file_uploader(
                    "Medicine Image (optional)",
                    type=["png", "jpg", "jpeg"]
                )


                notes = st.text_area("Notes (optional)", placeholder="Any additional details")

                c1, c2 = st.columns(2)
                submit = c1.form_submit_button("✅ Save")
                cancel = c2.form_submit_button("❌ Cancel")

            if cancel:
                st.session_state.show_add_medicine = False
                st.rerun()

            if submit:
                if not name:
                    st.error("Medicine name is required")
                    st.stop()

                cost_per_dose = round(total_cost / total_units, 2) if total_cost and total_units else ""

                now = dt.datetime.now()
                med_id = f"MED{now.strftime('%Y%m%d%H%M%S%f')}"

                image_url = ""
                if image_file:
                    image_url = upload_to_cloudinary(image_file)


                open_medicine_sheet().append_row(
                    [
                        f"MED{now.strftime('%Y%m%d%H%M%S%f')}",
                        name,
                        mtype,
                        applicable,
                        default_dose,
                        dose_unit,
                        freq_type,
                        freq_value if freq_type == "Recurring" else "",
                        "Days" if freq_type == "Recurring" else "",
                        total_cost,
                        total_units,
                        cost_per_dose,
                        total_units,
                        "Active",
                        image_url,
                        notes,
                        st.session_state.user_name,
                        now.strftime("%Y-%m-%d %H:%M:%S")
                    ],
                    value_input_option="USER_ENTERED"
                )

                st.cache_data.clear()
                st.success("✅ Medicine added successfully")
                st.session_state.show_add_medicine = False
                st.rerun()

        
        if (
            st.session_state.medicine_view_mode == "edit"
            and st.session_state.editing_med_id is not None
        ):
            med = medicine_df[
                medicine_df["MedicineID"] == st.session_state.editing_med_id
            ].iloc[0]

            st.subheader("✏️ Edit Medicine")

            with st.form("edit_medicine_form"):

                st.markdown(f"**Medicine:** {med['MedicineName']}")

                col1, col2 = st.columns(2)

                with col1:
                    status = st.selectbox(
                        "Status",
                        ["Active", "Inactive"],
                        index=0 if med["Status"] == "Active" else 1
                    )

                    stock = st.number_input(
                        "Stock Available",
                        value=float(med["StockAvailable"]),
                        step=1.0
                    )

                with col2:
                    total_cost = st.number_input(
                        "Total Cost (₹)",
                        value=float(med["TotalCost"]),
                        step=1.0
                    )

                    total_units = st.number_input(
                        "Total Units",
                        value=float(med["TotalUnits"]),
                        step=1.0
                    )

                col3, col4 = st.columns(2)
                with col3:
                    freq_value = st.number_input(
                        "Frequency Value",
                        value=float(med["FrequencyValue"]) if med["FrequencyValue"] else 0
                    )
                with col4:
                    freq_unit = st.selectbox(
                        "Frequency Unit",
                        ["Hour", "Days", "Weeks", "Months"],
                        index=["Hour","Days","Weeks","Months"].index(med["FrequencyUnit"])
                        if med["FrequencyUnit"] else 1
                    )

                c1, c2 = st.columns(2)
                save = c1.form_submit_button("💾 Update")
                cancel = c2.form_submit_button("❌ Cancel")

            if cancel:
                st.session_state.editing_med_id = None
                st.rerun()

            if save:
                cost_per_dose = round(total_cost / total_units, 2) if total_units else 0

                ws = open_medicine_sheet()
                row_idx = medicine_df.index[
                    medicine_df["MedicineID"] == med["MedicineID"]
                ][0] + 2

                ws.update(
                    f"L{row_idx}:J{row_idx}",
                    [[total_cost, total_units, cost_per_dose]]
                )
                ws.update(
                    f"O{row_idx}:M{row_idx}",
                    [[stock, status]]
                )
                ws.update(
                    f"H{row_idx}:I{row_idx}",
                    [[freq_value, freq_unit]]
                )

                st.cache_data.clear()
                st.success("✅ Medicine updated")
                st.session_state.editing_med_id = None
                st.rerun()



        # ======================================================
        # MEDICINE CARDS
        # ======================================================
        # ======================================================
        st.subheader("💊 Medicine List")

        col1, col2 = st.columns([6, 1])

        with col2:
            if st.session_state.medicine_view_mode == "view":
                if st.button("✏️ Edit Mode"):
                    st.session_state.medicine_view_mode = "edit"
                    st.session_state.editing_med_id = None
                    st.rerun()
            else:
                if st.button("👁️ View Mode"):
                    st.session_state.medicine_view_mode = "view"
                    st.session_state.editing_med_id = None
                    st.rerun()


        if medicine_df.empty:
            st.info("No medicines added yet.")
            st.stop()

        cols = st.columns(4)  # 4 cards per row

        for i, r in medicine_df.iterrows():

            # --------- Colors by Status ----------
            if r["Status"] == "Active":
                gradient = "linear-gradient(135deg,#3b82f6,#6366f1)"
                status_badge = "🟢 Active"
            else:
                gradient = "linear-gradient(135deg,#64748b,#334155)"
                status_badge = "⚪ Inactive"

            card_html = f"""
            <div style="
                background:{gradient};
                color:white;
                padding:10px 12px;
                border-radius:12px;
                height:90px;
                box-shadow:0 4px 10px rgba(0,0,0,.25);
                display:flex;
                flex-direction:column;
                justify-content:space-between;
                font-family:Inter,system-ui,sans-serif;
            ">

                <!-- Medicine Name -->
                <div>
                    <div style="font-size:13px;font-weight:800;line-height:1.1;">
                        {r['MedicineName']}
                    </div>
                    <div style="
                        font-size:10px;
                        opacity:.9;
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                    ">
                        <span>{r['MedicineType']} • {r['ApplicableFor']}</span>
                        <span style="font-size:11px;">📦 {r['StockAvailable']}</span>
                    </div>

                </div>

                <!-- Dose & Frequency -->
                <div style="font-size:11px;line-height:1.4;">
                    💉 <b>{r['DefaultDose']} {r['DoseUnit']}</b>
                    &nbsp;|&nbsp;
                    🔁 {r['FrequencyValue']} {r['FrequencyUnit']}
                </div>

                <!-- Cost & Stock -->
                <div style="font-size:11px;">
                   💰 ₹{r['CostPerDose']}
                </div>

                <!-- Footer -->
                <div style="
                    font-size:10px;
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    opacity:.95;
                ">
                    <span>{status_badge}</span>

                    {"<a href='" + r['MedicineImageURL'] + "' target='_blank' "
                    "style='color:white;text-decoration:none;font-size:15px;'>📄</a>"
                    if r.get("MedicineImageURL") else ""}
                </div>


            </div>
            """

            
            with cols[i % 4]:

                components.html(card_html, height=130)

                # 👇 ADD ONLY THIS PART
                if st.session_state.medicine_view_mode == "edit":
                    if st.button(
                        "✏️ Edit",
                        key=f"edit_{r['MedicineID']}",
                        use_container_width=True
                    ):
                        st.session_state.editing_med_id = r["MedicineID"]
                        st.rerun()


    elif page=="Transaction":
        st.title("Transaction")
        
    elif page == "Medication":

        st.title("💉 Medication")

        # ======================================================
        # HELPERS
        # ======================================================
        def open_med_master():
            return open_sheet(MAIN_SHEET_ID, MEDICATION_MASTER_TAB)

        def open_med_log():
            return open_sheet(MAIN_SHEET_ID, MEDICATION_LOG_TAB)

        @st.cache_data(ttl=30)
        def load_med_master():
            ws = open_med_master()
            rows = ws.get_all_values()
            if len(rows) <= 1:
                return pd.DataFrame()
            return pd.DataFrame(rows[1:], columns=rows[0])

        @st.cache_data(ttl=30)
        def load_med_logs():
            ws = open_med_log()
            rows = ws.get_all_values()

            # Sheet empty → initialize header
            if not rows:
                ws.insert_row(MEDICATION_LOG_HEADER, 1)
                return pd.DataFrame(columns=MEDICATION_LOG_HEADER)

            # Header exists but no data
            if len(rows) == 1:
                return pd.DataFrame(columns=rows[0])



            return pd.DataFrame(rows[1:], columns=rows[0])


        @st.cache_data(ttl=60)
        def get_cows_df():
            """
            Load Cow Master data safely.
            Returns empty DataFrame if sheet is missing or empty.
            """

            try:
                ws = open_sheet(MAIN_SHEET_ID, COW_PROFILE_TAB)
                rows = ws.get_all_values()
            except Exception as e:
                st.error("❌ Unable to load Cow Master sheet")
                st.stop()

            # No data or only header
            if not rows or len(rows) <= 1:
                return pd.DataFrame(columns=["CowID", "Status"])

            df = pd.DataFrame(rows[1:], columns=rows[0])

            # ---- Safety: ensure required columns ----
            if "CowID" not in df.columns:
                st.error("❌ CowID column missing in Cow Master")
                st.stop()

            if "Status" not in df.columns:
                df["Status"] = "Active"  # default fallback

            # ---- Clean values ----
            df["CowID"] = df["CowID"].astype(str).str.strip()
            df["Status"] = df["Status"].astype(str).str.strip()

            return df

        # ======================================================
        # LOAD DATA
        # ======================================================

        meds_df = load_med_master()
        logs_df = load_med_logs()
        cows_df = get_cows_df()
        

        # ---- filter cows (ACTIVE / SICK only) ----
        cows_df = cows_df[cows_df["Status"].isin(["Active", "Sick"])]

        # ---- clean numeric ----
        if not meds_df.empty:
            meds_df["StockAvailable"] = pd.to_numeric(
                meds_df["StockAvailable"], errors="coerce"
            ).fillna(0)

        if not logs_df.empty:
            logs_df["GivenOn"] = pd.to_datetime(logs_df["GivenOn"], errors="coerce")
            logs_df["NextDueDate"] = pd.to_datetime(logs_df["NextDueDate"], errors="coerce")

        # ======================================================
        # KPI SECTION
        # ======================================================
        st.subheader("📊 Overview")

        total_logs = len(logs_df)
        pending_due = (
            len(logs_df[logs_df["NextDueDate"] >= pd.Timestamp.today()])
            if not logs_df.empty else 0
        )

        k1, k2 = st.columns(2)

        def kpi(title, value):
            st.markdown(
                f"""
                <div style="padding:14px;border-radius:14px;
                background:#0f172a;color:white;margin-bottom:14px;">
                    <div style="font-size:13px;opacity:.8">{title}</div>
                    <div style="font-size:22px;font-weight:800">{value}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with k1: kpi("Total Medications Given", total_logs)
        with k2: kpi("Upcoming Doses", pending_due)

        st.divider()
        if "show_give_medication" not in st.session_state:
            st.session_state.show_give_medication = False
        if st.button("💉 Give Medication"):
            st.session_state.show_give_medication = not st.session_state.show_give_medication


        # ======================================================
        # ADD MEDICATION FORM
        # ======================================================
        if st.session_state.show_give_medication:
            st.subheader(" Give Medication")

            med_id = st.selectbox(
                "Medicine",
                meds_df["MedicineID"].tolist(),
                format_func=lambda x:
                    meds_df[meds_df["MedicineID"] == x]["MedicineName"].values[0],
                key="med_select"
            )

            med_row = meds_df[meds_df["MedicineID"] == med_id].iloc[0]
            medicine_name=med_row["MedicineName"]
            st.info(f"💊 Stock Available: **{med_row['StockAvailable']}**")

            with st.form("give_med_form"):

                cow_id = st.selectbox(
                    "Cow ID",
                    cows_df["CowID"].tolist()
                )

                dose_text = st.text_input(
                    "Dose Given",
                    placeholder=f"Only {med_row['StockAvailable']} stock available"
                )

                dose_given = None
                if dose_text:
                    try:
                        dose_given = float(dose_text)
                        if dose_given <= 0:
                            st.error("❌ Dose must be greater than 0")
                        elif dose_given > med_row["StockAvailable"]:
                            st.error("❌ Not enough stock available")
                    except ValueError:
                        st.error("❌ Enter a valid number")


                notes = st.text_input("Notes (optional)")

                c1, c2 = st.columns(2)
                save = c1.form_submit_button("✅ Save Medication")
                cancel = c2.form_submit_button("❌ Cancel")


            # ---------- CANCEL ----------
            if cancel:
                st.session_state.show_give_medication = False
                st.rerun()


            # ---------- SAVE ----------
            if save:

                if dose_given > med_row["StockAvailable"]:
                    st.error("❌ Not enough stock available")
                    st.stop()
                if save:
                    if dose_given is None:
                        st.error("❌ Please enter dose given")
                        st.stop()


                now = pd.Timestamp.now()

                # ---- NEXT DUE DATE ----
                next_due = ""
                if med_row["FrequencyType"] == "Recurring":
                    unit = med_row["FrequencyUnit"]
                    value = int(med_row["FrequencyValue"])

                    if unit == "Days":
                        next_due = now + pd.Timedelta(days=value)
                    elif unit == "Weeks":
                        next_due = now + pd.Timedelta(weeks=value)
                    elif unit == "Months":
                        next_due = now + pd.DateOffset(months=value)

                # ---- INSERT LOG ----
                open_med_log().append_row(
                    [
                        f"MEDLOG{now.strftime('%Y%m%d%H%M%S%f')}",
                        cow_id,
                        med_id,
                        medicine_name,
                        dose_given,
                        med_row["DoseUnit"],
                        now.strftime("%Y-%m-%d"),
                        st.session_state.user_name,
                        med_row["FrequencyType"],
                        med_row["FrequencyValue"],
                        med_row["FrequencyUnit"],
                        notes,
                        next_due.strftime("%Y-%m-%d") if next_due != "" else "",
                    ],
                    value_input_option="USER_ENTERED"
                )

                # ---- UPDATE STOCK ----
                new_stock = med_row["StockAvailable"] - dose_given
                row_idx = meds_df.index[meds_df["MedicineID"] == med_id][0] + 2

                open_med_master().update(
                    f"M{row_idx}",
                    [[new_stock]]
                )

                st.cache_data.clear()
                st.success("✅ Medication recorded & stock updated")

                st.session_state.show_give_medication = False
                st.rerun()

            st.divider()

        # ======================================================
        # MEDICATION HISTORY
        # ======================================================
        st.subheader("📋 Medication History")

        if logs_df.empty:
            st.info("No medication records found.")
        else:

            cols = st.columns(4)

            for i, r in logs_df.sort_values("GivenOn", ascending=False).iterrows():

                card_html = f"""
                <div style="
                    background:linear-gradient(135deg,#1e293b,#334155);
                    color:white;
                    padding:12px;
                    border-radius:14px;
                    height:95px;
                    box-shadow:0 6px 14px rgba(0,0,0,0.25);
                    display:flex;
                    flex-direction:column;
                    justify-content:space-between;
                    font-family:Inter,system-ui,sans-serif;
                ">
                    <div>
                        <div style="font-size:13px;font-weight:800;">
                            🐄 {r['CowID']}
                        </div>
                        <div style="font-size:12px;opacity:.9;">
                            💊 {r['MedicineName']}
                        </div>
                    </div>

                    <div style="font-size:12px;">
                        💉 {r['DoseGiven']} {r['DoseUnit']}
                    </div>

                    <div style="font-size:11px;opacity:.85;">
                        📅 Given: {r['GivenOn'].date()}
                    </div>

                    <div style="font-size:11px;">
                        ⏭ Next: {r['NextDueDate'].date() if pd.notna(r['NextDueDate']) else "-"}
                    </div>
                </div>
                """

                with cols[i % 4]:
                    components.html(card_html, height=135)


    elif page == "Profile":

        # ==================================================
        # SESSION UI STATE (SAFE INIT)
        # ==================================================
        if "edit_user_id" not in st.session_state:
            st.session_state.edit_user_id = None

        if "show_edit_user" not in st.session_state:
            st.session_state.show_edit_user = False

        ui_defaults = {
            "show_edit_info": False,
            "show_change_password": False,
            "show_create_user": False,
            "user_edit_mode": False,
        }
        for k, v in ui_defaults.items():
            st.session_state.setdefault(k, v)

        # ==================================================
        # LOAD CURRENT USER
        # ==================================================
        st.title("👤 My Profile")

        user_df = auth_df[auth_df["userid"] == st.session_state.user_id].iloc[0]

        # ==================================================
        # HEADER ACTION BUTTONS
        # ==================================================
        h1, h2 = st.columns([6, 1])

        # LEFT → Change Password
        with h1:
            if st.button(
                "🔐 Change Password"
                if not st.session_state.show_change_password
                else "❌ Cancel Password"
            ):
                st.session_state.show_change_password = not st.session_state.show_change_password
                st.session_state.show_edit_info = False
                st.rerun()

        # RIGHT → Edit Info
        with h2:
            if st.button(
                "✏️ Edit Info"
                if not st.session_state.show_edit_info
                else "❌ Cancel Edit"
            ):
                st.session_state.show_edit_info = not st.session_state.show_edit_info
                st.session_state.show_change_password = False
                st.rerun()


        # ==================================================
        # READ-ONLY PROFILE DETAILS
        # ==================================================
        st.subheader("📄 Personal Details")

        profile_html = f"""
        <div style="
            background: linear-gradient(135deg, #020617, #0f172a);
            border-radius: 18px;
            padding: 20px;
            color: #e5e7eb;
            box-shadow: 0 12px 30px rgba(0,0,0,0.4);
            font-family: Inter, system-ui, sans-serif;
            max-width: 100%;
        ">

            <!-- Header -->
            <div style="
                display:flex;
                align-items:center;
                justify-content:space-between;
                margin-bottom:18px;
            ">
                <div style="font-size:18px;font-weight:700;">
                    👤 {user_df["name"]}
                </div>

                <span style="
                    background:#2563eb;
                    color:white;
                    padding:6px 14px;
                    border-radius:999px;
                    font-size:12px;
                    font-weight:600;
                ">
                    {user_df["role"]}
                </span>
            </div>

            <!-- Grid -->
            <div style="
                display:grid;
                grid-template-columns: repeat(3, 1fr);
                gap:14px;
            ">

                <div>
                    <div style="font-size:11px;color:#94a3b8;">User ID</div>
                    <div style="font-size:14px;font-weight:600;">{user_df["userid"]}</div>
                </div>

                <div>
                    <div style="font-size:11px;color:#94a3b8;">Username</div>
                    <div style="font-size:14px;font-weight:600;">@{user_df["username"]}</div>
                </div>

                <div>
                    <div style="font-size:11px;color:#94a3b8;">Access Level</div>
                    <div style="font-size:14px;font-weight:600;">
                        {user_df["accesslevel"] if user_df["accesslevel"] else "-"}
                    </div>
                </div>

                <div>
                    <div style="font-size:11px;color:#94a3b8;">Email</div>
                    <div style="font-size:13px;font-weight:500;word-break:break-all;">
                        📧 {user_df["email"]}
                    </div>
                </div>

                <div>
                    <div style="font-size:11px;color:#94a3b8;">Phone</div>
                    <div style="font-size:14px;font-weight:600;">
                        📞 {user_df.get("phone", "-")}
                    </div>
                </div>

                <div>
                    <div style="font-size:11px;color:#94a3b8;">Status</div>
                    <div style="
                        display:inline-block;
                        margin-top:4px;
                        background:#22c55e;
                        color:#022c22;
                        padding:4px 10px;
                        border-radius:999px;
                        font-size:12px;
                        font-weight:600;
                    ">
                        Active
                    </div>
                </div>

            </div>
        </div>
        """

        components.html(profile_html, height=260)


        # ==================================================
        # EDIT CONTACT INFO (TOGGLE)
        # ==================================================
        if st.session_state.show_edit_info:
            st.divider()
            st.subheader("✏️ Edit Contact Information")

            email = st.text_input("Email", user_df["email"])
            phone = st.text_input("Phone", user_df.get("phone", ""))

            c1, c2 = st.columns(2)

            with c1:
                if st.button("💾 Save Changes"):
                    row_idx = (
                        auth_df[auth_df["userid"] == st.session_state.user_id].index[0] + 2
                    )

                    AUTH_SHEET.update_cell(
                        row_idx, get_col_index(auth_df, "email"), email
                    )
                    AUTH_SHEET.update_cell(
                        row_idx, get_col_index(auth_df, "phone"), phone
                    )

                    load_auth_data.clear()
                    st.success("✅ Contact details updated")
                    st.session_state.show_edit_info = False
                    st.rerun()

            with c2:
                if st.button("❌ Cancel"):
                    st.session_state.show_edit_info = False
                    st.rerun()

        # ==================================================
        # CHANGE PASSWORD (TOGGLE)
        # ==================================================
        if st.session_state.show_change_password:
            st.divider()
            st.subheader("🔐 Change Password")

            old_pass = st.text_input("Current Password", type="password")
            new_pass = st.text_input("New Password", type="password")
            confirm = st.text_input("Confirm New Password", type="password")

            c1, c2 = st.columns(2)

            with c1:
                if st.button("🔐 Update Password"):
                    if not verify_password(user_df["passwordhash"], old_pass):
                        st.error("❌ Current password incorrect")
                        st.stop()

                    if new_pass != confirm:
                        st.error("❌ Passwords do not match")
                        st.stop()

                    AUTH_SHEET.update_cell(
                        auth_df[auth_df["userid"] == st.session_state.user_id].index[0] + 2,
                        get_col_index(auth_df, "passwordhash"),
                        hash_password(new_pass),
                    )

                    load_auth_data.clear()
                    st.success("✅ Password updated successfully")
                    st.session_state.show_change_password = False
                    st.rerun()

            with c2:
                if st.button("❌ Cancel"):
                    st.session_state.show_change_password = False
                    st.rerun()

        # ==================================================
        # ADMIN SECTION
        # ==================================================
        if st.session_state.user_role == "Admin":
            st.divider()

            left, right = st.columns([6, 1])

            # LEFT SIDE → Create User
            with left:
                if st.button(
                    "➕ Create User"
                    if not st.session_state.show_create_user
                    else "❌ Cancel Create"
                ):
                    st.session_state.show_create_user = not st.session_state.show_create_user
                    st.rerun()

            # RIGHT SIDE → Edit / Display toggle
            with right:
                if st.button(
                    "✏️ Edit Mode"
                    if not st.session_state.user_edit_mode
                    else "👁 Display Mode"
                ):
                    st.session_state.user_edit_mode = not st.session_state.user_edit_mode
                    st.rerun()


            # ---------- CREATE USER FORM ----------
            if st.session_state.show_create_user:
                st.subheader("➕ Create New User")

                with st.form("create_user_form"):
                    username = st.text_input("Username")
                    name = st.text_input("Full Name")
                    email = st.text_input("Email")
                    phone = st.text_input("Phone")
                    role = st.selectbox("Role", ["User", "Manager"])
                    access_list = st.multiselect(
                        "Access Level",
                        ["E-riksha", "Dairy"],
                        default=[]
                    )
                    access = ",".join(access_list)
                    createdby=st.session_state.user_name


                    if st.form_submit_button("Create User"):
                        temp_password = generate_otp()
                        hashed = hash_password(temp_password)

                        AUTH_SHEET.append_row(
                            [
                                f"U{int(datetime.now().timestamp())}",
                                username,
                                name,
                                email,
                                phone,
                                hashed,
                                role,
                                access,
                                "Active",
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                createdby,
                            ]
                        )

                        load_auth_data.clear()

                        try:
                            send_temp_password_email(email,name, username, temp_password)
                            st.success("✅ User created & email sent")
                        except:
                            st.warning(
                                "⚠️ User created, but email failed. Share password manually."
                            )

                        st.session_state.show_create_user = False
                        st.rerun()

            # ---------- USER CARDS ----------
            st.subheader("👥 All Users")

            cols = st.columns(4)
            for i, r in auth_df.iterrows():
                with cols[i % 4]:
                    status_color = "#22c55e" if r["status"] == "Active" else "#94a3b8"
                    role_color = "#38bdf8" if r["role"] == "Admin" else "#a78bfa"

                    card_html = f"""
                    <div style="
                        background: linear-gradient(135deg, #1e293b, #0f172a);
                        color: #f8fafc;
                        margin-bottom:14px;
                        padding: 16px;
                        border-radius: 18px;
                        box-shadow: 0 12px 30px rgba(0,0,0,0.35);
                        border: 1px solid rgba(255,255,255,0.08);
                        min-height: 110px;
                        font-family: Inter, system-ui, sans-serif;
                        transition: transform .2s ease, box-shadow .2s ease;
                    ">

                        <!-- Header -->
                        <div style="
                            display:flex;
                            justify-content:space-between;
                            align-items:center;
                            margin-bottom:10px;
                        ">
                            <div style="font-size:15px;font-weight:700;">
                                {r['name']}
                            </div>

                            <span style="
                                background:{status_color};
                                color:#022c22;
                                padding:3px 10px;
                                font-size:11px;
                                border-radius:999px;
                                font-weight:600;
                            ">
                                {r['status']}
                            </span>
                        </div>

                        <!-- Username -->
                        <div style="
                            font-size:12px;
                            color:#cbd5f5;
                            margin-bottom:8px;
                        ">
                            @{r['username']}
                        </div>

                        <!-- Email -->
                        <div style="
                            font-size:12px;
                            color:#e5e7eb;
                            word-break:break-all;
                            margin-bottom:14px;
                        ">
                            📧 {r['email']}
                        </div>

                        <!-- Footer -->
                        <div style="
                            display:flex;
                            justify-content:space-between;
                            align-items:center;
                        ">
                            <span style="
                                background:{role_color};
                                color:#020617;
                                padding:4px 12px;
                                font-size:11px;
                                border-radius:999px;
                                font-weight:600;
                            ">
                                {r['role']}
                            </span>

                            <span style="
                                font-size:11px;
                                color:#94a3b8;
                            ">
                                👤 User
                            </span>
                        </div>
                    </div>
                    """

                    with cols[i % 4]:

                        components.html(card_html, height=160)

                        # Show Edit button ONLY if user is editable
                        # Full-width Edit button (always rendered for alignment)
                        if st.session_state.user_edit_mode:

                            allowed_roles = {"User", "Manager",""}
                            allowed_access = {"E-riksha", "Dairy",""}

                            user_role = r.get("role", "")
                            user_access = r.get("accesslevel", "") or ""

                            role_ok = user_role in allowed_roles
                            access_ok = any(a in user_access for a in allowed_access)

                            can_edit = role_ok and access_ok

                            # Reason message for disabled state
                            if not role_ok and not access_ok:
                                reason = "Role & Access level mismatch"
                            elif not role_ok:
                                reason = "Role mismatch"
                            elif not access_ok:
                                reason = "Access level mismatch"
                            else:
                                reason = "Edit user details"

                            if st.button(
                                "✏️ Edit",
                                key=f"edit_user_{r['userid']}",
                                use_container_width=True,
                                disabled=not can_edit,
                                help=reason
                            ):
                                if can_edit:
                                    st.session_state.edit_user_id = r["userid"]
                                    st.session_state.show_edit_user = True
                                    st.rerun()



            # ==================================================
            # ADMIN EDIT USER PANEL
            # ==================================================
            if st.session_state.show_edit_user and st.session_state.edit_user_id:

                st.divider()
                st.subheader("✏️ Edit User")

                edit_df = auth_df[auth_df["userid"] == st.session_state.edit_user_id].iloc[0]

                with st.form("admin_edit_user_form"):

                    st.text_input("User ID", edit_df["userid"], disabled=True)
                    st.text_input("Username", edit_df["username"], disabled=True)

                    name = st.text_input("Name", edit_df["name"])
                    email = st.text_input("Email", edit_df["email"])
                    phone = st.text_input("Phone", edit_df.get("phone", ""))

                    role = st.selectbox(
                        "Role",
                        ["User", "Manager"],
                        index=["User", "Manager"].index(edit_df["role"]),
                    )

                    # Fetch existing access level safely
                    existing_access = edit_df.get("accesslevel", "")

                    # Convert stored string → list
                    default_access = (
                        [x.strip() for x in existing_access.split(",")]
                        if existing_access else []
                    )

                    access_list = st.multiselect(
                        "Access Level",
                        ["E-riksha", "Dairy"],
                        default=default_access
                    )

                    access = ",".join(access_list)

                    status = st.selectbox(
                        "Status",
                        ["Active", "Inactive"],
                        index=["Active", "Inactive"].index(edit_df["status"]),
                    )

                    c1, c2 = st.columns(2)
                    save = c1.form_submit_button("💾 Save Changes")
                    cancel = c2.form_submit_button("❌ Cancel")

                if cancel:
                    st.session_state.show_edit_user = False
                    st.session_state.edit_user_id = None
                    st.rerun()

                if save:
                    row_idx = auth_df[auth_df["userid"] == edit_df["userid"]].index[0] + 2

                    AUTH_SHEET.update_cell(row_idx, get_col_index(auth_df, "name"), name)
                    AUTH_SHEET.update_cell(row_idx, get_col_index(auth_df, "email"), email)
                    AUTH_SHEET.update_cell(row_idx, get_col_index(auth_df, "phone"), phone)
                    AUTH_SHEET.update_cell(row_idx, get_col_index(auth_df, "role"), role)
                    AUTH_SHEET.update_cell(row_idx, get_col_index(auth_df, "accesslevel"), access)
                    AUTH_SHEET.update_cell(row_idx, get_col_index(auth_df, "status"), status)

                    load_auth_data.clear()

                    st.success("✅ User updated successfully")

                    st.session_state.show_edit_user = False
                    st.session_state.edit_user_id = None
                    st.rerun()




        
    # ----------------------------
    # REFRESH BUTTON
    # ----------------------------
    if st.sidebar.button("🔁 Refresh"):
        st.rerun()
