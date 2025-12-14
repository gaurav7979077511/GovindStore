import streamlit as st
import pandas as pd
import urllib.parse
import streamlit.components.v1 as components

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(page_title="Dairy Farm Management", layout="wide")

# ============================================================
# GOOGLE SHEET IDS (from Streamlit Secrets)
# ============================================================
INVESTMENT_SHEET_ID = st.secrets["sheets"]["INVESTMENT_SHEET_ID"]
MILK_DIS_M_SHEET_ID = st.secrets["sheets"]["MILK_DIS_M_SHEET_ID"]
MILK_DIS_E_SHEET_ID = st.secrets["sheets"]["MILK_DIS_E_SHEET_ID"]
EXPENSE_SHEET_ID = st.secrets["sheets"]["EXPENSE_SHEET_ID"]
COW_LOG_SHEET_ID = st.secrets["sheets"]["COW_LOG_SHEET_ID"]
PAYMENT_SHEET_ID = st.secrets["sheets"]["PAYMENT_SHEET_ID"]

# ============================================================
# GOOGLE SHEET CSV EXPORT LINKS
# ============================================================
INVESTMENT_CSV_URL = f"https://docs.google.com/spreadsheets/d/{INVESTMENT_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=investment"
MILK_DIS_M_CSV_URL = f"https://docs.google.com/spreadsheets/d/{MILK_DIS_M_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=morning"
MILK_DIS_E_CSV_URL = f"https://docs.google.com/spreadsheets/d/{MILK_DIS_E_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=evening"
EXPENSE_CSV_URL = f"https://docs.google.com/spreadsheets/d/{EXPENSE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=expense"
COW_LOG_CSV_URL = f"https://docs.google.com/spreadsheets/d/{COW_LOG_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=dailylog"
PAYMENT_CSV_URL = f"https://docs.google.com/spreadsheets/d/{PAYMENT_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=payment"

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
        "🏠 Dashboard",
        "Milking & Feeding",
        "Milk Distribution",
        "Expense",
        "Payments",
        "Investments",
        "Manage Customers",
        "Milk Bitran",
    ],
)

# ============================================================
# 🏠 DASHBOARD PAGE
# ============================================================
if page == "🏠 Dashboard":

    # -------------------- Custom Dark Mode CSS --------------------
    st.markdown(
        """
        <style>
        :root {
            --bg-color: #0e1117;
            --card-bg: #1a1d23;
            --text-color: #f0f2f6;
            --accent: #00FFFF;
            --border-color: #00FFFF44;
            --shadow-color: #00FFFF22;
        }
        @media (prefers-color-scheme: light) {
            :root {
                --bg-color: #f9f9f9;
                --card-bg: #ffffff;
                --text-color: #000000;
                --accent: #0077ff;
                --border-color: #0077ff33;
                --shadow-color: #0077ff11;
            }
        }
        .main { background-color: var(--bg-color); color: var(--text-color); }
        div[data-testid="stMetric"] {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 0 8px var(--shadow-color);
            text-align: center;
        }
        h1, h2, h3 { color: var(--accent); }
        hr { border: 1px solid var(--border-color); }
        label, .stRadio { color: var(--text-color) !important; }
        @media (max-width: 768px) {
            div[data-testid="stMetric"] { padding: 10px; font-size: 0.85rem; }
            h1, h2, h3 { font-size: 1rem; }
        }
        .radio-center { display: flex; justify-content: center; margin-top: 10px; margin-bottom: 25px; }
        div[data-testid="stRadio"] > div { justify-content: center !important; }
        div[data-testid="stRadio"] label { color: var(--text-color) !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.header("🐄 Dairy Farm Dashboard")

    # -------------------- Load Data --------------------
    START_DATE = pd.Timestamp("2025-11-01")
    df_cow_log = load_csv(COW_LOG_CSV_URL, drop_cols=["Timestamp"])
    df_expense = load_csv(EXPENSE_CSV_URL, drop_cols=["Timestamp"])
    df_milk_m = load_csv(MILK_DIS_M_CSV_URL, drop_cols=["Timestamp"])
    df_milk_e = load_csv(MILK_DIS_E_CSV_URL, drop_cols=["Timestamp"])
    df_payment_received = load_csv(PAYMENT_CSV_URL, drop_cols=["Timestamp"])
    df_investment = load_csv(INVESTMENT_CSV_URL, drop_cols=["Timestamp"])

    # -------------------- Filter from 1 Nov 2025 --------------------
    for df in [df_cow_log, df_expense, df_milk_m, df_milk_e, df_payment_received, df_investment]:
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df.dropna(subset=["Date"], inplace=True)
            df = df[df["Date"] >= START_DATE]

    # -------------------- Lifetime Summary --------------------
    st.subheader("📊 Overall Summary")

    milk_col = next((c for c in df_cow_log.columns if "milk" in c.lower() or "दूध" in c), None)
    total_milk_produced = pd.to_numeric(df_cow_log[milk_col], errors="coerce").sum() if milk_col else 0

    total_milk_m = sum_numeric_columns(df_milk_m, exclude_cols=["Timestamp", "Date"])
    total_milk_e = sum_numeric_columns(df_milk_e, exclude_cols=["Timestamp", "Date"])
    total_milk_distributed = total_milk_m + total_milk_e
    remaining_milk = total_milk_produced - total_milk_distributed

    total_expense = pd.to_numeric(df_expense["Amount"], errors="coerce").sum() if not df_expense.empty else 0
    total_payment_received = pd.to_numeric(df_payment_received["Amount"], errors="coerce").sum() if not df_payment_received.empty else 0
    total_investment = pd.to_numeric(df_investment["Amount"], errors="coerce").sum() if not df_investment.empty else 0

    investment_bipin = (
        df_investment.loc[df_investment["Paid To"] == "Bipin Kumar", "Amount"].sum()
        if "Paid To" in df_investment.columns
        else 0
    )
    received_bipin = (
        df_payment_received.loc[df_payment_received["Received By"] == "Bipin Kumar", "Amount"].sum()
        if "Received By" in df_payment_received.columns
        else 0
    )
    expense_bipin = (
        df_expense.loc[df_expense["Expense By"] == "Bipin Kumar", "Amount"].sum()
        if "Expense By" in df_expense.columns
        else 0
    )
    fund_bipin = investment_bipin + received_bipin - expense_bipin

    # -------------------- Metrics --------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🥛 Total Milk Produced", f"{total_milk_produced:.2f} L")
    c2.metric("🚚 Total Milk Distributed", f"{total_milk_distributed:.2f} L")
    c3.metric("❗ Remaining / Lost Milk", f"{remaining_milk:.2f} L")
    c4.metric("💸 Total Expense", f"₹{total_expense:,.2f}")

    c5, c6, c7 = st.columns(3)
    c5.metric("💰 Total Payment Received", f"₹{total_payment_received:,.2f}")
    c6.metric("📈 Total Investment", f"₹{total_investment:,.2f}")
    c7.metric("🏦 Fund (Bipin Kumar)", f"₹{fund_bipin:,.2f}")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # -------------------- Latest Summary --------------------
    st.subheader("🕒 Latest Summary")
    
    # --- Find last 2 milk produced records ---
    df_sorted_prod = df_cow_log.sort_values("Date", ascending=False).head(2)
    
    def get_shift_total(row):
        shift = row["Shift - पहर"] if "Shift - पहर" in row else row.get("Shift", "")
        milk_value = row[milk_col] if milk_col in row else 0
        milk_value = pd.to_numeric(milk_value, errors="coerce")
        return shift, milk_value
    
    latest_prod_1 = df_sorted_prod.iloc[0]
    latest_prod_2 = df_sorted_prod.iloc[1]
    
    shift1, milk1 = get_shift_total(latest_prod_1)
    shift2, milk2 = get_shift_total(latest_prod_2)
    
    date1 = latest_prod_1["Date"].strftime("%d-%m-%Y")
    date2 = latest_prod_2["Date"].strftime("%d-%m-%Y")
    
    # --- Determine which distribution file to pick ---
    def get_latest_delivery(shift):
        target_df = df_milk_m if shift.lower() == "morning" else df_milk_e
        if target_df.empty:
            return None, shift, 0
    
        df_sorted = target_df.sort_values("Date", ascending=False)
    
        row = df_sorted.iloc[0]
    
        # Convert all columns except "Date" to numeric and sum
        total = pd.to_numeric(
            row.drop(labels=["Date"], errors="ignore"),
            errors="coerce"
        ).sum()
    
        date = row["Date"].strftime("%d-%m-%Y")
    
        return date, shift, total

    
    # Case based assignment:
    # If latest produced shift is Morning → order: P(M), D(M), P(E), D(E)
    # If Evening → order: P(E), D(E), P(M), D(M)
    is_morning_first = shift1.lower() == "morning"
    
    if is_morning_first:
        p1_date, p1_shift, p1_total = date1, shift1, milk1
        d1_date, d1_shift, d1_total = get_latest_delivery("morning")
        p2_date, p2_shift, p2_total = date2, shift2, milk2
        d2_date, d2_shift, d2_total = get_latest_delivery("evening")
    else:
        p1_date, p1_shift, p1_total = date1, shift1, milk1
        d1_date, d1_shift, d1_total = get_latest_delivery("evening")
        p2_date, p2_shift, p2_total = date2, shift2, milk2
        d2_date, d2_shift, d2_total = get_latest_delivery("morning")
    
    # --- Layout: 4 Metric Blocks in ONE ROW ---
    lc1, lc2, lc3, lc4 = st.columns(4)

    
    lc1.metric(f"🥛 Last Milk Produced ({p1_shift})", f"{p1_total} L", p1_date)
    lc2.metric(f"🚚 Last Milk Delivered ({d1_shift})", f"{d1_total} L", d1_date)
    
    lc3.metric(f"🥛 Previous Milk Produced ({p2_shift})", f"{p2_total} L", p2_date)
    lc4.metric(f"🚚 Previous Milk Delivered ({d2_shift})", f"{d2_total} L", d2_date)
    
    st.markdown("<hr/>", unsafe_allow_html=True)
    

    # -------------------- Current Month Summary --------------------
    today = pd.Timestamp.today()
    current_month_name = today.strftime("%B %Y")
    st.subheader(f"📅 Current Month Summary ({current_month_name})")

    def filter_month(df):
        if df.empty or "Date" not in df.columns:
            return df
        return df[df["Date"].dt.month == today.month]

    df_month_expense = filter_month(df_expense)
    df_month_milk_m = filter_month(df_milk_m)
    df_month_milk_e = filter_month(df_milk_e)
    df_month_cow_log = filter_month(df_cow_log)
    df_month_payment = filter_month(df_payment_received)

    milk_col = next((c for c in df_month_cow_log.columns if "milk" in c.lower() or "दूध" in c), None)
    milk_month = pd.to_numeric(df_month_cow_log[milk_col], errors="coerce").sum() if milk_col else 0
    milk_m_month = sum_numeric_columns(df_month_milk_m, exclude_cols=["Timestamp", "Date"])
    milk_e_month = sum_numeric_columns(df_month_milk_e, exclude_cols=["Timestamp", "Date"])
    milk_distributed_month = milk_m_month + milk_e_month
    remaining_milk_month = milk_month - milk_distributed_month

    expense_month = pd.to_numeric(df_month_expense["Amount"], errors="coerce").sum() if not df_month_expense.empty else 0
    payment_month = pd.to_numeric(df_month_payment["Amount"], errors="coerce").sum() if not df_month_payment.empty else 0

    cm1, cm2, cm3, cm4, cm5 = st.columns(5)
    cm1.metric("🥛 Milk Produced (This Month)", f"{milk_month:.2f} L")
    cm2.metric("🚚 Milk Distributed (This Month)", f"{milk_distributed_month:.2f} L")
    cm3.metric("❗ Remaining Milk (This Month)", f"{remaining_milk_month:.2f} L")
    cm4.metric("💸 Expense (This Month)", f"₹{expense_month:,.2f}")
    cm5.metric("💰 Payment Received (This Month)", f"₹{payment_month:,.2f}")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # -------------------- Milk Production vs Delivery Graph --------------------
    # -------------------- Milk Production vs Delivery Graph --------------------
    st.subheader("📈 Milk Production vs Delivery Trend")
    
    # --- Centered Radio Button for Date Range
    col1, col2, col3 = st.columns([1, 3, 1])  # Center alignment
    with col2:
        range_option = st.radio(
            "",
            ["1 Week", "1 Month", "3 Months", "6 Months", "1 Year", "3 Years", "5 Years", "Max"],
            horizontal=True,
            index=1,  # Default to "3 Months"
        )
    
    # --- Determine date range based on selection
    today = pd.Timestamp.today()
    date_limit = {
        "1 Week": today - pd.Timedelta(weeks=1),
        "1 Month": today - pd.DateOffset(months=1),
        "3 Months": today - pd.DateOffset(months=3),
        "6 Months": today - pd.DateOffset(months=6),
        "1 Year": today - pd.DateOffset(years=1),
        "3 Years": today - pd.DateOffset(years=3),
        "5 Years": today - pd.DateOffset(years=5),
        "Max": START_DATE,
    }[range_option]
    
    # --- Prepare production data
    if not df_cow_log.empty and milk_col:
        df_cow_log["Date"] = pd.to_datetime(df_cow_log["Date"], errors="coerce")
        df_cow_log = df_cow_log[df_cow_log["Date"] >= date_limit]
        daily_prod = df_cow_log.groupby("Date")[milk_col].sum().reset_index()
    else:
        daily_prod = pd.DataFrame(columns=["Date", "Produced"])
    
    # --- Combine morning & evening distribution
    def combine_distribution(df1, df2):
        df_all = pd.concat([df1, df2])
        df_all["Date"] = pd.to_datetime(df_all["Date"], errors="coerce")
        df_all["Total"] = df_all.select_dtypes(include="number").sum(axis=1)
        return df_all.groupby("Date")["Total"].sum().reset_index()
    
    df_delivery = combine_distribution(df_milk_m, df_milk_e)
    df_delivery = df_delivery[df_delivery["Date"] >= date_limit]
    
    # --- Display line chart
    if not daily_prod.empty and not df_delivery.empty:
        chart_df = pd.merge(daily_prod, df_delivery, on="Date", how="outer").fillna(0)
        chart_df = chart_df.rename(columns={milk_col: "Produced", "Total": "Delivered"})
        st.line_chart(chart_df.set_index("Date"))
    else:
        st.info("No sufficient data for chart.")

    # -------------------- Missing Entries CARDS (final colors + layout) --------------------
    
    st.markdown("### 📌 Pending Entries")
    
    VALIDATION_START = pd.Timestamp("2025-11-01")
    today_norm = pd.Timestamp.today().normalize()
    
    # Compact sizing
    CARD_WIDTH = "220px"
    CARD_HEIGHT = "90px"
    CARD_PADDING = "12px"
    
    BASE_CARD_STYLE = (
        f"border-radius:12px; padding:{CARD_PADDING}; text-decoration:none; display:block;"
        f"box-shadow:0 6px 18px rgba(0,0,0,0.18); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial;"
        f"width:{CARD_WIDTH}; height:{CARD_HEIGHT}; box-sizing:border-box; overflow:hidden;"
    )
    
    # All card text white now
    TITLE_STYLE = "font-size:12px; color:#ffffff; opacity:0.95; margin:0 0 6px 0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"
    COWID_STYLE = "font-size:18px; font-weight:700; color:#ffffff; margin:0; line-height:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"
    DATE_STYLE = "color:#ffffff; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"
    BOTTOM_ROW_STYLE = "display:flex; justify-content:space-between; align-items:center; gap:8px; width:100%;"
    
    # pill: dark semi-opaque background with white text (so pill readable on any gradient)
    PILL_STYLE = "background:rgba(0,0,0,0.18); color:#ffffff; padding:6px 10px; border-radius:999px; font-size:12px; font-weight:700; white-space:nowrap;"
    
    # Form URL templates (with CowID)
    cow_form_template = (
        "https://docs.google.com/forms/d/e/1FAIpQLSeTgPYBAXYFihUg6xMoZx8DkJfizPE1jAZlVMa9kgGTlhSEew/viewform"
        "?usp=pp_url&entry.1575375539={DATE}&entry.1560275875={SHIFT}&entry.1484558388={COWID}"
    )
    morning_milk_form = (
        "https://docs.google.com/forms/d/e/1FAIpQLSfULz5JiL--wG71GWq7_OED16pTu5fc4xPa3u1dyLo7Y1lURw/viewform"
        "?usp=pp_url&entry.1311650896={DATE}"
    )
    evening_milk_form = (
        "https://docs.google.com/forms/d/e/1FAIpQLSfX-E9AvffO9EHvWCRQD_JfDC2BA7qTLb3wk6KIlfUlsm4erA/viewform"
        "?usp=pp_url&entry.1311650896={DATE}"
    )
    
    # Final gradients per your request
    gradients = {
        # Milking & Feeding - pink gradient (same for morning & evening)
        "milking": "linear-gradient(135deg,#ff512f 0%,#dd2476 100%)",
        # Distribution - morning yellow, evening blue
        "dist_morning": "linear-gradient(135deg,#f7971e 0%,#ffd200 100%)",
        "dist_evening": "linear-gradient(135deg,#00c6ff 0%,#0072ff 100%)",
    }
    
    if VALIDATION_START > today_norm:
        st.info(f"Validation will start from {VALIDATION_START.strftime('%Y-%m-%d')}.")
    else:
        # Use copies of dataframes
        cow_log = df_cow_log.copy() if df_cow_log is not None else pd.DataFrame()
        milk_m = df_milk_m.copy() if df_milk_m is not None else pd.DataFrame()
        milk_e = df_milk_e.copy() if df_milk_e is not None else pd.DataFrame()
    
        # Normalize "Date" columns (day-first tolerant)
        for dfr in [cow_log, milk_m, milk_e]:
            if dfr is None or dfr.empty:
                continue
            if "Date" in dfr.columns:
                dfr["Date"] = pd.to_datetime(dfr["Date"], dayfirst=True, errors="coerce")
    
        # Detect shift & cowid columns
        shift_col = None
        cowid_col = None
        if not cow_log.empty:
            for c in cow_log.columns:
                if "shift" in c.lower() or "पहर" in c:
                    shift_col = c
                if "cow" in c.lower():
                    cowid_col = c
            if cowid_col is None:
                for c in cow_log.columns:
                    if c.strip().lower() in ["cowid", "cow id", "cow_id"]:
                        cowid_col = c
                        break
    
        # Helper functions
        def has_shift_on_date_for_cow(df, date, shift_col, cowid_col, cowid_value, shift_name):
            if df is None or df.empty or shift_col is None or cowid_col is None:
                return False
            mask = (df["Date"].dt.normalize() == date.normalize()) & (df[cowid_col].astype(str).str.strip() == str(cowid_value).strip())
            if not mask.any():
                return False
            vals = df.loc[mask, shift_col].dropna().astype(str).str.lower().str.strip().tolist()
            if not vals:
                return False
            joined = " ".join(vals)
            if shift_name.lower() == "morning":
                return any(k in joined for k in ["morning", "mor", "सुबह", "भोर", "am"])
            else:
                return any(k in joined for k in ["evening", "eve", "शाम", "pm", "even"])
    
        def has_any_on_date(df, date):
            if df is None or df.empty or "Date" not in df.columns:
                return False
            return not df[df["Date"].dt.normalize() == date.normalize()].empty
    
        missing_cards = []
    
        # Per-CowID Milking & Feeding validation (both shifts use same milking gradient)
        if cowid_col and not cow_log.empty:
            cow_ids = cow_log[cowid_col].dropna().astype(str).str.strip().unique().tolist()
            for cowid in cow_ids:
                cow_rows = cow_log[cow_log[cowid_col].astype(str).str.strip() == str(cowid).strip()]
                if cow_rows.empty or "Date" not in cow_rows.columns:
                    continue
                first_date = cow_rows["Date"].min()
                cow_start = max(VALIDATION_START, pd.to_datetime(first_date).normalize())
                if cow_start > today_norm:
                    continue
                for d in pd.date_range(start=cow_start, end=today_norm, freq="D"):
                    date_str = d.strftime("%Y-%m-%d")
                    # missing morning
                    if not has_shift_on_date_for_cow(cow_log, d, shift_col, cowid_col, cowid, "Morning"):
                        url = cow_form_template.format(
                            DATE=urllib.parse.quote(date_str, safe=""),
                            SHIFT=urllib.parse.quote("Morning", safe=""),
                            COWID=urllib.parse.quote(str(cowid).strip(), safe="")
                        )
                        missing_cards.append({
                            "kind": "milking",
                            "cowid": cowid,
                            "date": date_str,
                            "shift": "Morning",
                            "url": url,
                            "gradient": gradients["milking"]
                        })
                    # missing evening
                    if not has_shift_on_date_for_cow(cow_log, d, shift_col, cowid_col, cowid, "Evening"):
                        url = cow_form_template.format(
                            DATE=urllib.parse.quote(date_str, safe=""),
                            SHIFT=urllib.parse.quote("Evening", safe=""),
                            COWID=urllib.parse.quote(str(cowid).strip(), safe="")
                        )
                        missing_cards.append({
                            "kind": "milking",
                            "cowid": cowid,
                            "date": date_str,
                            "shift": "Evening",
                            "url": url,
                            "gradient": gradients["milking"]
                        })
        else:
            # fallback: date-based check without cowid
            for d in pd.date_range(start=VALIDATION_START, end=today_norm, freq="D"):
                date_str = d.strftime("%Y-%m-%d")
                if not has_shift_on_date_for_cow(cow_log, d, shift_col, cowid_col, "", "Morning"):
                    url = cow_form_template.format(DATE=urllib.parse.quote(date_str, safe=""), SHIFT=urllib.parse.quote("Morning", safe=""), COWID=urllib.parse.quote("", safe=""))
                    missing_cards.append({"kind":"milking","cowid":"","date":date_str,"shift":"Morning","url":url,"gradient":gradients["milking"]})
                if not has_shift_on_date_for_cow(cow_log, d, shift_col, cowid_col, "", "Evening"):
                    url = cow_form_template.format(DATE=urllib.parse.quote(date_str, safe=""), SHIFT=urllib.parse.quote("Evening", safe=""), COWID=urllib.parse.quote("", safe=""))
                    missing_cards.append({"kind":"milking","cowid":"","date":date_str,"shift":"Evening","url":url,"gradient":gradients["milking"]})
    
        # Global Milk Distribution validation (one per date)
        for d in pd.date_range(start=VALIDATION_START, end=today_norm, freq="D"):
            date_str = d.strftime("%Y-%m-%d")
            if not has_any_on_date(milk_m, d):
                url = morning_milk_form.format(DATE=urllib.parse.quote(date_str, safe=""))
                missing_cards.append({
                    "kind": "distribution",
                    "date": date_str,
                    "shift": "Morning",
                    "url": url,
                    "gradient": gradients["dist_morning"]
                })
            if not has_any_on_date(milk_e, d):
                url = evening_milk_form.format(DATE=urllib.parse.quote(date_str, safe=""))
                missing_cards.append({
                    "kind": "distribution",
                    "date": date_str,
                    "shift": "Evening",
                    "url": url,
                    "gradient": gradients["dist_evening"]
                })
    
        # ---------- Render ALL cards as a single HTML block (horizontal grid, wrapped rows) ----------
        if not missing_cards:
            st.success("No pending entries detected.")
        else:
            # Build a single HTML string for the whole container + cards
            html_parts = []
        
            # Styles (single st.markdown call)
            styles = (
                '<style>'
                '.card-container { display:flex; flex-wrap:wrap; gap:12px 14px; row-gap:16px; align-items:flex-start; }'
                '.card-item { flex:0 0 auto; }'
                '@media (max-width:600px) { .card-item { flex: 0 0 48%; } }'  # two columns on small screens
                '</style>'
            )
            html_parts.append(styles)
        
            # Open container
            html_parts.append('<div class="card-container">')
        
            # Build each card HTML and append
            for card in missing_cards:
                # choose gradient
                if card["kind"] == "milking":
                    gradient = "linear-gradient(135deg, #ff5f8d 0%, #ff8fb3 100%)"  # pink
                else:
                    if card["shift"] == "Morning":
                        gradient = "linear-gradient(135deg, #ffb300 0%, #ffd54f 100%)"  # yellow
                    else:
                        gradient = "linear-gradient(135deg, #0091ff 0%, #4fb3ff 100%)"  # blue
        
                # common card container style (fixed width, compact)
                card_style = (
                    'width:200px; padding:14px; border-radius:14px; '
                    f'background:{gradient}; color:#ffffff; '
                    'box-shadow:0 6px 16px rgba(0,0,0,0.28); '
                    'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Arial;'
                    'box-sizing:border-box;'
                )
        
                # inside elements styles
                title_html = '<div style="font-size:12px; opacity:0.95; margin-bottom:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">'
                # Build card inner HTML depending on type
                if card["kind"] == "milking":
                    inner = (
                        title_html + 'Milking & Feeding</div>'
                        f'<div style="font-size:18px; font-weight:800; margin-bottom:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{card.get("cowid","")}</div>'
                        '<div style="display:flex; justify-content:space-between; align-items:center;">'
                        f'<div style="font-size:12px; font-weight:600;">{card["date"]}</div>'
                        '<div style="background:rgba(0,0,0,0.18); padding:6px 10px; border-radius:999px; font-size:12px; font-weight:700; color:#ffffff;">'
                        f'{card["shift"]}</div>'
                        '</div>'
                    )
                else:
                    # Distribution: title centered, date left + shift pill right on same row visually
                    inner = (
                        title_html + 'Milk Distribution</div>'
                        f'<div style="font-size:15px; font-weight:800; margin-bottom:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{card["date"]}</div>'
                        '<div style="display:flex; justify-content:space-between; align-items:center;">'
                        '<div></div>'  # left spacer (keeps balance)
                        '<div style="background:rgba(0,0,0,0.18); padding:6px 10px; border-radius:999px; font-size:12px; font-weight:700; color:#ffffff;">'
                        f'{card["shift"]}</div>'
                        '</div>'
                    )
        
                # full card HTML (link wrapping)
                card_html = (
                    '<div class="card-item">'
                    f'<a href="{card["url"]}" target="_blank" style="text-decoration:none;">'
                    f'<div style="{card_style}">{inner}</div>'
                    '</a>'
                    '</div>'
                )
        
                html_parts.append(card_html)
        
            # Close container
            html_parts.append('</div>')
        
            # Render once
            full_html = ''.join(html_parts)
            st.markdown(full_html, unsafe_allow_html=True)
        
        


# ----------------------------
# MILKING & FEEDING PAGE
# ----------------------------
elif page == "Milking & Feeding":
    st.title("🐄 Milking & Feeding Analysis")

    # Add Milking & Feeding Button
    col1, col2 = st.columns([6, 1])
    with col2:
        st.markdown(
            f'<a href="https://forms.gle/4ywNpoYLr7LFQtxe8" target="_blank">'
            f'<button style="background-color:#81C7F5; color:white; padding:8px 16px; font-size:14px; border:none; border-radius:5px;">Milking & Feeding</button>'
            f'</a>',
            unsafe_allow_html=True
        )
    
        # ─────────────────────────────────────────────────────

    # --- Load data ---
    df = load_csv(COW_LOG_CSV_URL, drop_cols=["Timestamp"])
    df_morning = load_csv(MILK_DIS_M_CSV_URL, drop_cols=["Timestamp"])
    df_evening = load_csv(MILK_DIS_E_CSV_URL, drop_cols=["Timestamp"])

    # --- Date setup ---
    start_date = pd.Timestamp("2025-11-01")
    now = pd.Timestamp.now()
    this_month = now.month
    this_year = now.year

    # --- Clean and filter helper ---
    def clean_and_filter(df):
        if df.empty or "Date" not in df.columns:
            return df
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df[df["Date"] >= start_date]
        df["Date"] = df["Date"].dt.strftime("%d-%m-%Y")
        return df

    df = clean_and_filter(df)
    df_morning = clean_and_filter(df_morning)
    df_evening = clean_and_filter(df_evening)

    # --- Detect milk column dynamically ---
    milk_col = None
    for c in df.columns:
        if "milk" in c.lower() or "दूध" in c:
            milk_col = c
            break

    # --- Ensure numeric ---
    if not df.empty and milk_col:
        df[milk_col] = pd.to_numeric(df[milk_col], errors="coerce")

    # --- Total milk produced ---
    total_milk_produced = df[milk_col].sum() if not df.empty and milk_col else 0

    # --- Total milk this month ---
    total_milk_month = 0
    if not df.empty and milk_col:
        df["Date_dt"] = pd.to_datetime(df["Date"], format="%d-%m-%Y", errors="coerce")
        df_this_month = df[
            (df["Date_dt"].dt.month == this_month) & (df["Date_dt"].dt.year == this_year)
        ]
        if not df_this_month.empty:
            total_milk_month = df_this_month[milk_col].sum()

    # --- Cow-wise total ---
    cow_wise = pd.DataFrame()
    if not df.empty and "CowID" in df.columns and milk_col:
        cow_wise = (
            df.groupby("CowID")[milk_col]
            .sum()
            .reset_index()
            .rename(columns={milk_col: "Total Milk (L)"})
            .sort_values("Total Milk (L)", ascending=False)
        )

    # --- Total Milk Distributed ---
    def total_milk_distributed(df):
        if df.empty:
            return 0
        numeric_cols = [c for c in df.columns if c not in ["Timestamp", "Date"]]
        df_numeric = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        return df_numeric.sum().sum()

    total_distributed_morning = total_milk_distributed(df_morning)
    total_distributed_evening = total_milk_distributed(df_evening)
    total_distributed = total_distributed_morning + total_distributed_evening

    # --- KPIs ---
    st.subheader("📊 Key Metrics (From 1 Nov 2025)")
    col1, col2, col3 = st.columns(3)
    col1.metric("🥛 Total Milk Produced", f"{total_milk_produced:.2f} L")
    col2.metric("📅 Milk Produced This Month", f"{total_milk_month:.2f} L")
    col3.metric("🚚 Total Milk Delivered", f"{total_distributed:.2f} L")

    # --- Cow-wise production ---
    st.divider()
    st.subheader("🐮 Cow-wise Milk Production (From 1 Nov 2025)")
    if not cow_wise.empty:
        st.dataframe(cow_wise, use_container_width=True)
    else:
        st.info("No cow-wise milking data available yet.")

    # --- Daily trend ---
    st.divider()
    st.subheader("📅 Daily Milk Production Trend")
    if not df.empty and milk_col:
        df_daily = df.copy()
        df_daily["Date_dt"] = pd.to_datetime(df_daily["Date"], format="%d-%m-%Y", errors="coerce")
        daily_summary = (
            df_daily.groupby("Date_dt")[milk_col].sum().reset_index().sort_values("Date_dt")
        )
        st.line_chart(daily_summary.set_index("Date_dt"))
    else:
        st.info("No daily milking data to display.")

    # --- Raw data ---
    st.divider()
    st.subheader("📋 Raw Milking & Feeding Data (From 1 Nov 2025)")
    if not df.empty:
        df_display = df.sort_values(by="Date", ascending=False)
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("No milking & feeding data available after 1 Nov 2025.")


# ----------------------------
# MILK DISTRIBUTION PAGE
# ----------------------------
elif page == "Milk Distribution":
    st.title("🥛 Milk Distribution")

    # --- Load data ---
    df_morning = load_csv(MILK_DIS_M_CSV_URL, drop_cols=["Timestamp"])
    df_evening = load_csv(MILK_DIS_E_CSV_URL, drop_cols=["Timestamp"])
    df_cow_log = load_csv(COW_LOG_CSV_URL, drop_cols=["Timestamp"])

    # --- Date filtering: only include records from 1 Nov 2025 onward ---
    start_date = pd.Timestamp("2025-11-01")

    def clean_and_filter(df):
        if df.empty or "Date" not in df.columns:
            return df
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df[df["Date"] >= start_date]  # Filter only from 1 Nov 2025
        df["Date"] = df["Date"].dt.strftime("%d-%m-%Y")  # Format date
        return df

    df_morning = clean_and_filter(df_morning)
    df_evening = clean_and_filter(df_evening)

    # --- Total milk distributed (sum numeric columns except date) ---
    def total_milk_distributed(df):
        if df.empty:
            return 0
        numeric_cols = [c for c in df.columns if c not in ["Timestamp", "Date"]]
        df_numeric = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        return df_numeric.sum().sum()

    total_morning = total_milk_distributed(df_morning)
    total_evening = total_milk_distributed(df_evening)
    total_distributed = total_morning + total_evening

    # --- Monthly totals ---
    this_month = pd.Timestamp.now().month
    this_year = pd.Timestamp.now().year

    def monthly_distribution(df):
        if df.empty or "Date" not in df.columns:
            return 0
        df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y", errors="coerce")
        df_this_month = df[
            (df["Date"].dt.month == this_month) & (df["Date"].dt.year == this_year)
        ]
        return total_milk_distributed(df_this_month)

    monthly_morning = monthly_distribution(df_morning)
    monthly_evening = monthly_distribution(df_evening)
    monthly_distributed = monthly_morning + monthly_evening

    # --- Total milk produced this month from cow log (filter from 1 Nov 2025) ---
    total_milk_produced_month = 0
    if not df_cow_log.empty:
        df_cow_log.columns = [c.strip().lower() for c in df_cow_log.columns]
        if "date" in df_cow_log.columns and "milking -दूध" in df_cow_log.columns:
            df_cow_log["date"] = pd.to_datetime(df_cow_log["date"], errors="coerce")
            df_cow_log = df_cow_log[df_cow_log["date"] >= start_date]  # Filter Nov 1 onward
            df_cow_log["month"] = df_cow_log["date"].dt.month
            df_cow_log["year"] = df_cow_log["date"].dt.year
            df_month = df_cow_log[
                (df_cow_log["month"] == this_month) & (df_cow_log["year"] == this_year)
            ]
            total_milk_produced_month = pd.to_numeric(
                df_month["milking -दूध"], errors="coerce"
            ).sum()

    remaining_milk = total_milk_produced_month - monthly_distributed

    # --- KPI Metrics ---
    col1, col2, col3 = st.columns(3)
    col1.metric("🥛 Total Milk Distributed (from 1 Nov 2025)", f"{total_distributed:.2f} L")
    col2.metric("📅 This Month's Distribution", f"{monthly_distributed:.2f} L")
    col3.metric("🧾 Remaining Milk (This Month)", f"{remaining_milk:.2f} L")

    st.divider()

    # Add Morning Distribution Button
    col1, col2 = st.columns([6, 1])
    with col1:
        # --- Morning Distribution Table ---
        st.subheader("🌅 Morning Distribution")
    with col2:
        st.markdown(
            f'<a href="https://forms.gle/vWfoRDfPtzJiTKZw7" target="_blank">'
            f'<button style="background-color:#FFCA28; color:white; padding:8px 16px; font-size:14px; border:none; border-radius:5px;">Morning Distribution</button>'
            f'</a>',
            unsafe_allow_html=True
        )
    
        # ─────────────────────────────────────────────────────
    if not df_morning.empty:
        df_morning_display = df_morning.sort_values("Date", ascending=False)
        st.dataframe(df_morning_display, use_container_width=True)
    else:
        st.info("No morning distribution data available after 1 Nov 2025.")

    
    # Add Evening Distribution Button
    col1, col2 = st.columns([6, 1])
    with col1:
        # --- Evening Distribution Table ---
        st.subheader("🌇 Evening Distribution")
    with col2:
        st.markdown(
            f'<a href="https://forms.gle/5f6Wuh7TNLtC2z9o6" target="_blank">'
            f'<button style="background-color:#FF7043; color:white; padding:8px 16px; font-size:14px; border:none; border-radius:5px;">Evening Distribution</button>'
            f'</a>',
            unsafe_allow_html=True
        )
    
        # ─────────────────────────────────────────────────────

    if not df_evening.empty:
        df_evening_display = df_evening.sort_values("Date", ascending=False)
        st.dataframe(df_evening_display, use_container_width=True)
    else:
        st.info("No evening distribution data available after 1 Nov 2025.")

    # --- Trend Chart ---
    st.divider()
    st.subheader("📈 Daily Milk Distribution Trend (from 1 Nov 2025)")

    if not df_morning.empty or not df_evening.empty:
        df_morning_chart = df_morning.copy()
        df_evening_chart = df_evening.copy()

        for df_temp in [df_morning_chart, df_evening_chart]:
            df_temp["Date"] = pd.to_datetime(df_temp["Date"], format="%d-%m-%Y", errors="coerce")
            df_temp["Total"] = df_temp.select_dtypes(include=["number"]).sum(axis=1)

        df_chart = pd.concat([
            df_morning_chart[["Date", "Total"]],
            df_evening_chart[["Date", "Total"]],
        ])
        df_chart = df_chart.groupby("Date")["Total"].sum().reset_index().sort_values("Date")

        st.line_chart(df_chart.set_index("Date"))
    else:
        st.info("No distribution data available to plot.")


# ----------------------------
# EXPENSE, PAYMENTS, INVESTMENTS (unchanged)
# ----------------------------
elif page == "Expense":
    st.title("💸 Expense Tracker")

    # Add Expense  Button
    col1, col2 = st.columns([6, 1])
    with col2:
        st.markdown(
            f'<a href="https://forms.gle/1hCkiBgU8sQKw87S8" target="_blank">'
            f'<button style="background-color:#C62828; color:white; padding:8px 16px; font-size:14px; border:none; border-radius:5px;">Add Expense</button>'
            f'</a>',
            unsafe_allow_html=True
        )
    
        # ─────────────────────────────────────────────────────

    df_expense = load_csv(EXPENSE_CSV_URL, drop_cols=["Timestamp"])

    if not df_expense.empty:
        # --- Convert Date column properly ---
        if "Date" in df_expense.columns:
            df_expense["Date"] = pd.to_datetime(df_expense["Date"], errors="coerce")
            df_expense = df_expense.sort_values("Date", ascending=False)

        # --- Total Expense ---
        total_expense = df_expense["Amount"].sum()

        # --- Current Month Expense ---
        current_month = pd.Timestamp.now().month
        current_year = pd.Timestamp.now().year
        df_this_month = df_expense[
            (df_expense["Date"].dt.month == current_month)
            & (df_expense["Date"].dt.year == current_year)
        ]
        monthly_expense = df_this_month["Amount"].sum()

        # --- KPIs ---
        col1, col2 = st.columns(2)
        col1.metric("💰 Total Expense", f"₹{total_expense:,.2f}")
        col2.metric("📅 This Month's Expense", f"₹{monthly_expense:,.2f}")

        st.divider()

        # --- Expense by Type ---
        if "Expense Type" in df_expense.columns:
            expense_by_type = (
                df_expense.groupby("Expense Type")["Amount"].sum().sort_values(ascending=False)
            )
            st.subheader("📊 Expense by Type")
            st.bar_chart(expense_by_type)

        # --- Expense by Person ---
        if "Expense By" in df_expense.columns:
            expense_by_person = (
                df_expense.groupby("Expense By")["Amount"].sum().sort_values(ascending=False)
            )
            st.subheader("👤 Expense by Person")
            st.bar_chart(expense_by_person)

        st.divider()
        st.subheader("🧾 Detailed Expense Records")
        st.dataframe(df_expense, use_container_width=True)

    else:
        st.info("No expense records found.")


elif page == "Payments":
    st.title("💰 Payments Record")
    # Add Payment  Button
    col1, col2 = st.columns([6, 1])
    with col2:
        st.markdown(
            f'<a href="https://forms.gle/jjaWGAUeTKkkoabX6" target="_blank">'
            f'<button style="background-color:#9C27B0; color:white; padding:8px 16px; font-size:14px; border:none; border-radius:5px;">Add Payment</button>'
            f'</a>',
            unsafe_allow_html=True
        )
    
        # ─────────────────────────────────────────────────────
    
    df_payment = load_csv(PAYMENT_CSV_URL, drop_cols=["Timestamp"])
    st.dataframe(df_payment, use_container_width=True if not df_payment.empty else False)

elif page == "Investments":
    st.title("📈 Investment Log")
    # Add Investment  Button
    col1, col2 = st.columns([6, 1])
    with col2:
        st.markdown(
            f'<a href="https://forms.gle/usPuRopj64DuxVpJA" target="_blank">'
            f'<button style="background-color:#2E7D32; color:white; padding:8px 16px; font-size:14px; border:none; border-radius:5px;">Add Investment</button>'
            f'</a>',
            unsafe_allow_html=True
        )
    
        # ─────────────────────────────────────────────────────
    df_invest = load_csv(INVESTMENT_CSV_URL, drop_cols=["Timestamp"])
    st.dataframe(df_invest, use_container_width=True if not df_invest.empty else False)

# ----------------------------
# MANAGE CUSTOMERS PAGE
# ----------------------------
elif page == "Manage Customers":

    import streamlit as st
    import pandas as pd
    import streamlit.components.v1 as components
    import datetime as dt

    st.title("👥 Manage Customers")

    # ---------- STATE ----------
    if "show_add_form" not in st.session_state:
        st.session_state.show_add_form = False

    if "edit_customer_id" not in st.session_state:
        st.session_state.edit_customer_id = None

    # ---------- CONFIG ----------
    CUSTOMER_SHEET_ID = st.secrets.get("sheets", {}).get(
        "CUSTOMER_SHEET_ID",
        "13n7il7rrEHQ2kek1tIf1W2p0VdepfTkerfu1IeSe8Yc"
    )
    CUSTOMER_SHEET_TAB = "Sheet1"

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
        sh = client.open_by_key(CUSTOMER_SHEET_ID)
        return sh.worksheet(CUSTOMER_SHEET_TAB)

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

    # ================= CONFIG =================
    CUSTOMER_SHEET_ID = st.secrets["sheets"].get(
        "CUSTOMER_SHEET_ID",
        "13n7il7rrEHQ2kek1tIf1W2p0VdepfTkerfu1IeSe8Yc"
    )
    MILK_BITRAN_SHEET_ID = "1mXhh57VYHrdGS2c78jGXXzkUQ9LU104OCzpUuV6QDbE"

    CUSTOMER_TAB = "Sheet1"
    BITRAN_TAB = "Sheet1"

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
        ws = open_sheet(CUSTOMER_SHEET_ID, CUSTOMER_TAB)
        rows = ws.get_all_values()
        if len(rows) <= 1:
            return pd.DataFrame(columns=["CustomerID", "Name", "Shift", "Status"])
        return pd.DataFrame(rows[1:], columns=rows[0])

    def load_bitran_data():
        ws = open_sheet(MILK_BITRAN_SHEET_ID, BITRAN_TAB)
        rows = ws.get_all_values()
        if not rows or rows[0] != BITRAN_HEADER:
            ws.insert_row(BITRAN_HEADER, 1)
            return pd.DataFrame(columns=BITRAN_HEADER)
        return pd.DataFrame(rows[1:], columns=rows[0])

    def append_bitran_rows(rows):
        ws = open_sheet(MILK_BITRAN_SHEET_ID, BITRAN_TAB)
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
