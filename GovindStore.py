import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import plotly.express as px
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# Google Sheets Authentication
SHEET_ID = "1UaxMdDoNHFXd1CNP0Exm2IN0KOiKtBKM-YK3q5FWe0A"
SHEET_NAME = "SalePurchaseData"
SALE_FOLDER_ID = "1nfaIvzdqQAAV77pus1wehJUAxXpCnGx1jtEqz3kK1LWd6z5F1-1KsklvX9ReFNIB-_Ad9iIW"
PURCHASE_FOLDER_ID = "1sN7U7rFNbv0dtZwXnQT18ZqgpJq3Hr5yFYxpE9oKXVSZLXLupYYQ-I3B6_iD-LxT5jh21jUq"

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
    drive_service = build("drive", "v3", credentials=creds)
except Exception as e:
    st.error(f"❌ Connection error: {e}")
    st.stop()

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

if page == "📋 Form Entry":
    st.header("➕ Add New Entry")
    date = st.date_input("📅 Select Date")
    entry_type = st.selectbox("📌 Type", ["Sale", "Purchase"])
    doc_file = None
    if entry_type == "Sale":
        amount = st.number_input("💲 Sale Amount", min_value=0.0, format="%.2f")
        comment = st.text_input("📝 Sale Comment")
        doc_file = st.file_uploader("📂 Upload Sale Document", type=["jpg", "jpeg", "png", "pdf"])
        folder_id = SALE_FOLDER_ID
    else:
        amount = st.number_input("💲 Purchase Amount", min_value=0.0, format="%.2f")
        comment = st.text_input("📝 Purchase Comment")
        doc_file = st.file_uploader("📂 Upload Purchase Document", type=["jpg", "jpeg", "png", "pdf"])
        folder_id = PURCHASE_FOLDER_ID

    if st.button("✅ Submit"):
        doc_url = upload_to_drive(f"/tmp/{doc_file.name}", doc_file.name, folder_id) if doc_file else ""
        new_row = [str(pd.Timestamp.now()), str(date), entry_type, amount if entry_type == "Sale" else "", comment if entry_type == "Sale" else "", doc_url if entry_type == "Sale" else "", amount if entry_type == "Purchase" else "", comment if entry_type == "Purchase" else "", doc_url if entry_type == "Purchase" else ""]
        sheet.append_row(new_row)
        st.success("✅ Data added successfully!")

elif page == "📊 Data Table":
    st.header("📄 Submitted Data")
    st.dataframe(df)