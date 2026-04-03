import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
import pytesseract
from PIL import Image
from datetime import date
import json
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# ==========================================
# KONFIGURASI HALAMAN UTAMA
# ==========================================
st.set_page_config(page_title="ROGER WEALTH OS", page_icon="💎", layout="wide")

# ==========================================
# INJEKSI CUSTOM CSS: LUXURY MIDNIGHT GOLD
# ==========================================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&display=swap');

    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background: radial-gradient(circle at 20% 30%, #1a1a1a 0%, #050505 100%);
        color: #e0e0e0;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* TITLE DESIGN */
    .title-glow {
        font-size: 48px;
        font-weight: 900;
        background: linear-gradient(to right, #bf953f, #fcf6ba, #b38728, #fbf5b7, #aa771c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        letter-spacing: -1px;
        padding-top: 20px;
    }
    
    .subtitle {
        text-align: center;
        color: rgba(255,255,255,0.4);
        font-size: 13px;
        font-weight: 400;
        text-transform: uppercase;
        letter-spacing: 6px;
        margin-bottom: 40px;
    }

    /* LUXURY METRIC CARDS */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(191, 149, 63, 0.3);
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    div[data-testid="metric-container"]:hover {
        border: 1px solid rgba(191, 149, 63, 0.9);
        background: rgba(191, 149, 63, 0.05);
        transform: translateY(-8px);
    }

    /* TABS STYLING */
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 30px;
        background-color: rgba(255,255,255,0.03);
        border-radius: 10px 10px 0 0;
        color: #888;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(191, 149, 63, 0.2) !important;
        color: #fcf6ba !important;
        border-bottom: 2px solid #bf953f !important;
    }

    /* BUTTON LUXE */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #bf953f 0%, #aa771c 100%);
        color: #000 !important;
        font-weight: 800;
        border: none;
        border-radius: 12px;
        padding: 12px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        box-shadow: 0 0 25px rgba(191, 149, 63, 0.5);
        transform: translateY(-2px);
    }

    /* DATAFRAME STYLING */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 15px;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Judul Utama
st.markdown("<div class='title-glow'>ROGER WEALTH OS</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Elite Portfolio Intelligence</div>", unsafe_allow_html=True)

# ==========================================
# KONEKSI KE GOOGLE SHEETS
# ==========================================
@st.cache_resource
def init_connection():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(st.secrets["GOOGLE_JSON"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("Database Finance Pro")
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
        return None

db = init_connection()
if db:
    ws_transaksi = db.worksheet("Transaksi")
    ws_saham = db.worksheet("Saham")
    df_transaksi = get_as_dataframe(ws_transaksi).dropna(how='all', axis=0).dropna(how='all', axis=1)
    df_saham = get_as_dataframe(ws_saham).dropna(how='all', axis=0).dropna(how='all', axis=1)
else:
    st.stop()

# ==========================================
# PERHITUNGAN SALDO & MARKET DATA
# ==========================================
porto = {"BCA": 0, "BRI": 0, "Bank Jago": 0, "Dompet (Cash)": 0}
for _, row in df_transaksi.iterrows():
    try:
        sumber, jenis, nom = str(row['Sumber Dana']), row['Jenis'], float(row['Nominal'])
        if sumber in porto:
            porto[sumber] += nom if jenis == "Pemasukan" else -nom
    except: pass

# Optimized yfinance (Bulk Download)
total_nilai_saham = 0
harga_sekarang_dict = {}
tickers = [str(t).upper() for t in df_saham['Ticker'].unique() if str(t) != "nan" and t != ""]

if tickers:
    try:
        market_data = yf.download(tickers, period="1d", progress=False)['Close'].iloc[-1]
        kurs_usd = yf.Ticker("USDIDR=X").history(period="1d")['Close'].iloc[-1]
        for t in tickers:
            price = market_data[t] if len(tickers) > 1 else market_data
            harga_sekarang_dict[t] = price * kurs_usd if not t.endswith('.JK') else price
    except: pass

for _, row in df_saham.iterrows():
    try:
        t, jl = str(row['Ticker']).upper(), float(row['Jumlah Lembar'])
        total_nilai_saham += (harga_sekarang_dict.get(t, float(row['Harga Beli'])) * jl)
    except: pass

# ==========================================
# UI TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(["🏦 EXECUTIVE DASHBOARD", "📈 EQUITY TERMINAL", "🔍 AI SCANNER"])

with tab1:
    total_fiat = sum(porto.values())
    total_net = total_fiat + total_nilai_saham
    
    # Hero Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("🌟 NET WORTH", f"Rp {total_net:,.0f}")
    c2.metric("💵 LIQUID CASH", f"Rp {total_fiat:,.0f}")
    c3.metric("📊 STOCK ASSETS", f"Rp {total_nilai_saham:,.0f}")

    st.write("")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.info(f"**BCA**\n\nRp {porto['BCA']:,.0f}")
    mc2.info(f"**BRI**\n\nRp {porto['BRI']:,.0f}")
    mc3.info(f"**JAGO**\n\nRp {porto['Bank Jago']:,.0f}")
    mc4.info(f"**CASH**\n\nRp {porto['Dompet (Cash)']:,.0f}")

    st.markdown("---")
    
    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.subheader("🖋️ New Transaction")
        with st.form("trx_form"):
            tgl = st.date_input("Date", date.today())
            kat = st.selectbox("Category", ["Gaji", "Investasi", "Makan", "Transport", "Lainnya"])
            jen = st.radio("Type", ["Pemasukan", "Pengeluaran"], horizontal=True)
            src = st.selectbox("Wallet", list(porto.keys()))
            nom = st.number_input("Amount (IDR)", min_value=0, step=10000)
            if st.form_submit_button("EXECUTE"):
                new_data = pd.DataFrame([{"Tanggal": str(tgl), "Kategori": kat, "Jenis": jen, "Sumber Dana": src, "Nominal": nom}])
                set_with_dataframe(ws_transaksi, pd.concat([df_transaksi, new_data]), row=1)
                st.rerun()

    with col_r:
        st.subheader("📊 Asset Distribution")
        df_pie = pd.DataFrame([{"Aset": k, "Nilai": v} for k, v in porto.items()] + [{"Aset": "Stocks", "Nilai": total_nilai_saham}])
        fig = px.pie(df_pie, values='Nilai', names='Aset', hole=0.6, template="plotly_dark",
                     color_discrete_sequence=['#bf953f', '#aa771c', '#555', '#222', '#888'])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', showlegend=False, height=350, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("💼 Equity Portfolio")
    if not df_saham.empty:
        rows = []
        for _, r in df_saham.iterrows():
            t = str(r['Ticker']).upper()
            cp = harga_sekarang_dict.get(t, r['Harga Beli'])
            gain = (cp - r['Harga Beli']) / r['Harga Beli'] * 100
            rows.append({"Ticker": t, "Avg": r['Harga Beli'], "Last": cp, "Gain %": f"{gain:.2f}%", "Value": cp * r['Jumlah Lembar']})
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.markdown("---")
    st.subheader("🤖 Technical Analysis")
    target = st.text_input("Enter Ticker (e.g. BBCA.JK)", "BBCA.JK").upper()
    if target:
        hist = yf.Ticker(target).history(period="6mo")
        if not hist.empty:
            fig_stk = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'])])
            fig_stk.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=400, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_stk, use_container_width=True)

with tab3:
    st.subheader("🧾 Smart Receipt Scanner")
    up_file = st.file_uploader("Upload Receipt", type=["jpg", "png"])
    if up_file:
        img = Image.open(up_file)
        st.image(img, width=400)
        if st.button("RUN AI EXTRACTION"):
            with st.spinner("Analyzing..."):
                try:
                    txt = pytesseract.image_to_string(img)
                    st.text_area("Extracted Text", txt, height=300)
                except: st.error("Tesseract not found. Please install via packages.txt")

# Sinkronisasi Global
if st.sidebar.button("☁️ FULL CLOUD SYNC"):
    st.cache_resource.clear()
    st.rerun()
