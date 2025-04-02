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

# Function to upload file
def upload_to_drive(file_path, file_name, folder_id):
    try:
        file_metadata = {"name": file_name, "parents": [folder_id]}
        media = MediaFileUpload(file_path, resumable=True)
        file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        return f"https://drive.google.com/file/d/{file['id']}"
    except Exception as e:
        st.error(f"❌ File upload failed: {e}")
        return ""

# Fetch data
def fetch_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data) if data else pd.DataFrame()

df = fetch_data()

# Layout
st.sidebar.title("📊 Dashboard Navigation")
page = st.sidebar.radio("Go to", ["📋 Form Entry", "📊 Data Table", "📈 Analytics & Forecast"])

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

elif page == "📈 Analytics & Forecast":
    st.header("📊 Sales & Purchase Analytics")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    
    # Monthly sales & purchase trend
    monthly_summary = df.groupby(["Year", "Month"]).agg({"Sale Amount": "sum", "Purchase Amount": "sum"}).reset_index()
    fig = px.line(monthly_summary, x=monthly_summary.index, y=["Sale Amount", "Purchase Amount"], markers=True, title="Monthly Sales & Purchase Trend")
    st.plotly_chart(fig)
    
    # Yearly totals
    yearly_summary = df.groupby("Year").agg({"Sale Amount": "sum", "Purchase Amount": "sum"}).reset_index()
    fig2 = px.bar(yearly_summary, x="Year", y=["Sale Amount", "Purchase Amount"], barmode="group", title="Yearly Sales vs Purchase")
    st.plotly_chart(fig2)
    
    # Sales & Purchase Projection (Next Month)
    def forecast_next_month(data, column):
        data = data[["Date", column]].dropna()
        data.set_index("Date", inplace=True)
        model = ExponentialSmoothing(data[column], seasonal="add", seasonal_periods=12)
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=1)
        return forecast.iloc[0]
    
    next_month_sales = forecast_next_month(df, "Sale Amount")
    next_month_purchases = forecast_next_month(df, "Purchase Amount")
    
    st.subheader("🔮 Sales & Purchase Projection")
    st.metric("📈 Projected Sales for Next Month", f"₹ {next_month_sales:.2f}")
    st.metric("📉 Projected Purchases for Next Month", f"₹ {next_month_purchases:.2f}")
