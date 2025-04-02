import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# Google Sheets Authentication
SHEET_ID = "1UaxMdDoNHFXd1CNP0Exm2IN0KOiKtBKM-YK3q5FWe0A"
SHEET_NAME = "SalePurchaseData"

# Load credentials from Streamlit Secrets (create a copy)
creds_dict = dict(st.secrets["gcp_service_account"])  # ✅ Create a mutable copy

# Fix private key formatting
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

# ✅ Fix: Ensure correct Google API scopes
try:
    creds = Credentials.from_service_account_info(
        creds_dict, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
except Exception as e:
    st.error(f"❌ Failed to connect to Google Sheets: {e}")
    st.stop()

# Streamlit UI
st.title("📋 Sale & Purchase Data")

# Form to add new data
st.header("➕ Add New Entry")

with st.form(key="entry_form"):
    date = st.date_input("📅 Select Date")
    entry_type = st.selectbox("📌 Type", ["Sale", "Purchase"])
    
    if entry_type == "Sale":
        sale_amount = st.number_input("💲 Sale Amount", min_value=0.0, format="%.2f")
        sale_comment = st.text_input("📝 Sale Comment")
        purchase_amount = ""
        purchase_comment = ""
    else:
        sale_amount = ""
        sale_comment = ""
        purchase_amount = st.number_input("💲 Purchase Amount", min_value=0.0, format="%.2f")
        purchase_comment = st.text_input("📝 Purchase Comment")
    
    submit_button = st.form_submit_button(label="✅ Submit")

    if submit_button:
        try:
            new_row = [str(pd.Timestamp.now()), str(date), entry_type, sale_amount, sale_comment, "", purchase_amount, purchase_comment, ""]
            sheet.append_row(new_row)
            st.success("✅ Data added successfully!")
        except Exception as e:
            st.error(f"❌ Failed to add data: {e}")

# Display Google Sheet Data
st.header("📊 View Submitted Data")

try:
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty:
        st.dataframe(df)
    else:
        st.warning("⚠ No data found!")
except Exception as e:
    st.error(f"❌ Failed to fetch data: {e}")
