import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import plotly.express as px
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import bcrypt

# Google Sheets Authentication
SHEET_ID = "1UaxMdDoNHFXd1CNP0Exm2IN0KOiKtBKM-YK3q5FWe0A"
SHEET_NAME = "SalePurchaseData"
SALE_FOLDER_ID = "1nfaIvzdqQAAV77pus1wehJUAxXpCnGx1jtEqz3kK1LWd6z5F1-1KsklvX9ReFNIB-_Ad9iIW"
PURCHASE_FOLDER_ID = "1sN7U7rFNbv0dtZwXnQT18ZqgpJq3Hr5yFYxpE9oKXVSZLXLupYYQ-I3B6_iD-LxT5jh21jUq"
AUTH_SHEET_ID = st.secrets["sheets"]["AUTH_SHEET_ID"]
AUTH_SHEET_NAME = "Sheet1"

# Load credentials
creds_dict = dict(st.secrets["gcp_service_account"])
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

try:
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    AUTH_sheet = client.open_by_key(AUTH_SHEET_ID).worksheet(AUTH_SHEET_NAME)
    drive_service = build("drive", "v3", credentials=creds)
except Exception as e:
    st.error(f"❌ Connection error: {e}")
    st.stop()

# Fetch authentication data
def load_auth_data():
    data = AUTH_sheet.get_all_records()
    return pd.DataFrame(data)

auth_df = load_auth_data()

def verify_password(stored_hash, entered_password):
    return bcrypt.checkpw(entered_password.encode(), stored_hash.encode())

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.user_name = None

if not st.session_state.authenticated:
    st.title("🔒 Secure Login")
    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")
    login_button = st.button("Login")

    if login_button:
        user_data = auth_df[auth_df["Username"] == username]
        if not user_data.empty:
            stored_hash = user_data.iloc[0]["Password"]
            role = user_data.iloc[0]["Role"]
            name = user_data.iloc[0]["Name"]
            if verify_password(stored_hash, password):
                st.session_state.authenticated = True
                st.session_state.user_role = role
                st.session_state.username = username
                st.session_state.user_name = name
                st.experimental_set_query_params(logged_in="true")
                st.success(f"✅ Welcome, {name}!")
                st.rerun()
            else:
                st.error("❌ Invalid Credentials")
        else:
            st.error("❌ User not found")
else:
    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.username = None
        st.session_state.user_name = None
        st.experimental_set_query_params(logged_in="false")
        st.rerun()

    st.sidebar.write(f"👤 **Welcome, {st.session_state.user_name}!**")

    # Fetch data
    def fetch_data():
        data = sheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()

    df = fetch_data()

    # Layout
    st.sidebar.title("📊 Dashboard Navigation")
    page = st.sidebar.radio("Go to", ["📈 Dashboard", "📋 Form Entry", "📊 Data Table"])

    if page == "📈 Dashboard":
        st.header("📊 Business Overview")
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Year"] = df["Date"].dt.year
        df["Month"] = df["Date"].dt.month

        df["Sale Amount"] = pd.to_numeric(df["Sale Amount"], errors="coerce").fillna(0)
        df["Purchase Amount"] = pd.to_numeric(df["Purchase Amount"], errors="coerce").fillna(0)

        # Current Month Sales & Purchases
        today = pd.Timestamp.now()
        current_month_sales = df[(df["Year"] == today.year) & (df["Month"] == today.month)]["Sale Amount"].sum()
        current_month_purchases = df[(df["Year"] == today.year) & (df["Month"] == today.month)]["Purchase Amount"].sum()

        st.subheader("📅 Monthly Overview")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📈 Total Sales This Month", f"₹ {current_month_sales:.2f}")
        with col2:
            st.metric("📉 Total Purchases This Month", f"₹ {current_month_purchases:.2f}")

        # Sales vs Date Graph
        st.subheader("📈 Sales vs Date")
        fig = px.bar(df, x="Date", y="Sale Amount", title="Sales Amount per Date", labels={"Sale Amount": "Sales (₹)"})
        st.plotly_chart(fig)

        # Monthly Sales & Purchase Summary
        st.subheader("📊 Monthly Sales & Purchase Summary")
        monthly_summary = df.groupby(["Year", "Month"]).agg({"Sale Amount": "sum", "Purchase Amount": "sum"}).reset_index()
        st.dataframe(monthly_summary)

    elif page == "📊 Data Table":
        st.header("📄 Submitted Data")
        st.dataframe(df)
