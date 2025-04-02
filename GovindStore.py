import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

# Google Sheets Authentication
SHEET_ID = "1UaxMdDoNHFXd1CNP0Exm2IN0KOiKtBKM-YK3q5FWe0A"
SHEET_NAME = "SalePurchaseData"
SALE_FOLDER_ID = "1nfaIvzdqQAAV77pus1wehJUAxXpCnGx1jtEqz3kK1LWd6z5F1-1KsklvX9ReFNIB-_Ad9iIW"
PURCHASE_FOLDER_ID = "1sN7U7rFNbv0dtZwXnQT18ZqgpJq3Hr5yFYxpE9oKXVSZLXLupYYQ-I3B6_iD-LxT5jh21jUq"

# Load credentials from Streamlit Secrets (create a copy)
creds_dict = dict(st.secrets["gcp_service_account"])  # ✅ Create a mutable copy

# Fix private key formatting
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

# ✅ Fix: Ensure correct Google API scopes
try:
    creds = Credentials.from_service_account_info(
        creds_dict, 
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets", 
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    drive_service = build("drive", "v3", credentials=creds)
except Exception as e:
    st.error(f"❌ Failed to connect to Google Sheets or Drive: {e}")
    st.stop()

# Function to upload file to Google Drive
def upload_to_drive(file_path, file_name, folder_id):
    try:
        file_metadata = {
            "name": file_name,
            "parents": [folder_id]
        }
        media = MediaFileUpload(file_path, resumable=True)
        file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        return f"https://drive.google.com/file/d/{file['id']}"
    except Exception as e:
        st.error(f"❌ Failed to upload file: {e}")
        return ""

# Streamlit UI
st.title("📋 Sale & Purchase Data")

# Form to add new data
st.header("➕ Add New Entry")

date = st.date_input("📅 Select Date")
entry_type = st.selectbox("📌 Type", ["Sale", "Purchase"])

doc_file = None
if entry_type == "Sale":
    sale_amount = st.number_input("💲 Sale Amount", min_value=0.0, format="%.2f", key="sale_amount")
    sale_comment = st.text_input("📝 Sale Comment", key="sale_comment")
    doc_file = st.file_uploader("📂 Upload Sale Document", type=["jpg", "jpeg", "png", "pdf"], key="sale_doc")
    purchase_amount = ""
    purchase_comment = ""
    folder_id = SALE_FOLDER_ID
elif entry_type == "Purchase":
    purchase_amount = st.number_input("💲 Purchase Amount", min_value=0.0, format="%.2f", key="purchase_amount")
    purchase_comment = st.text_input("📝 Purchase Comment", key="purchase_comment")
    doc_file = st.file_uploader("📂 Upload Purchase Document", type=["jpg", "jpeg", "png", "pdf"], key="purchase_doc")
    sale_amount = ""
    sale_comment = ""
    folder_id = PURCHASE_FOLDER_ID

submit_button = st.button("✅ Submit")

if submit_button:
    doc_url = ""
    if doc_file:
        file_path = os.path.join("/tmp", doc_file.name)
        with open(file_path, "wb") as f:
            f.write(doc_file.getbuffer())
        doc_url = upload_to_drive(file_path, doc_file.name, folder_id)
        os.remove(file_path)

    try:
        new_row = [
            str(pd.Timestamp.now()), str(date), entry_type, 
            sale_amount or "", sale_comment, doc_url if entry_type == "Sale" else "", 
            purchase_amount or "", purchase_comment, doc_url if entry_type == "Purchase" else ""
        ]
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