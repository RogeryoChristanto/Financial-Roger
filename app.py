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
# INISIALISASI SESSION STATE (HIDE BALANCE)
# ==========================================
if 'hide_balance' not in st.session_state:
    st.session_state.hide_balance = False

def format_currency(value):
    if st.session_state.hide_balance:
        return "Rp ••••••••"
    return f"Rp {value:,.0f}"

# ==========================================
# INJEKSI CUSTOM CSS: OPTIMASI MOBILE & LUXURY
# ==========================================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700;900&display=swap');

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background: radial-gradient(circle at 20% 30%, #1a1a1a 0%, #050505 100%);
        color: #e0e0e0;
    }

    /* HEADER MOBILE OPTIMIZATION */
    .title-glow {
        font-size: clamp(28px, 8vw, 52px); /* Font fleksibel sesuai layar */
        font-weight: 900;
        background: linear-gradient(to right, #bf953f, #fcf6ba, #b38728, #fbf5b7, #aa771c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding-top: 10px;
    }
    
    .subtitle {
        text-align: center;
        color: rgba(255,255,255,0.4);
        font-size: clamp(10px, 3vw, 14px);
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 20px;
    }

    /* METRIC CARD MOBILE RESPONSIVE */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(191, 149, 63, 0.2);
        padding: 15px !important;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }

    /* FORCING HORIZONTAL SCROLL ON MOBILE (Agar tidak menumpuk vertikal) */
    @media (max-width: 768px) {
        /* Metrik Utama (Total Kekayaan, dll) */
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            overflow-x: auto !important;
            gap: 10px !important;
            padding-bottom: 10px !important;
        }
        
        div[data-testid="column"] {
            min-width: 280px !important; /* Lebar kartu di HP agar pas */
            flex: 0 0 auto !important;
        }

        /* Menghilangkan padding berlebih di HP */
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* Form input agar lebih rapi di HP */
        .stButton button {
            width: 100% !important;
        }
    }

    /* TABS SCROLLABLE */
    .stTabs [data-baseweb="tab-list"] {
        overflow-x: auto;
        justify-content: flex-start;
        white-space: nowrap;
    }

    /* LUXURY TAB STYLE */
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255,255,255,0.02);
        color: #888;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(191, 149, 63, 0.2) !important;
        color: #fcf6ba !important;
        border-bottom: 2px solid #bf953f !important;
    }

    /* SCROLLBAR STYLE */
    ::-webkit-scrollbar { height: 4px; width: 4px; }
    ::-webkit-scrollbar-thumb { background: #bf953f; border-radius: 10px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Judul Utama
st.markdown("<div class='title-glow'>💎 ROGERYO FINANCE</div>", unsafe_allow_html=True)
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
    except:
        return None

db = init_connection()
if db:
    ws_transaksi = db.worksheet("Transaksi")
    ws_saham = db.worksheet("Saham")
    df_transaksi = get_as_dataframe(ws_transaksi).dropna(how='all').dropna(axis=1, how='all')
    df_saham = get_as_dataframe(ws_saham).dropna(how='all').dropna(axis=1, how='all')
else:
    st.error("Koneksi Database Terputus")
    st.stop()

# Perbaikan dataframe kosong
if df_transaksi.empty:
    df_transaksi = pd.DataFrame(columns=["Tanggal", "Kategori", "Jenis", "Sumber Dana", "Nominal"])
if df_saham.empty:
    df_saham = pd.DataFrame(columns=["Ticker", "Harga Beli", "Jumlah Lembar"])

# ==========================================
# AUTO-KALKULASI SALDO
# ==========================================
porto = {"BCA": 0, "BRI": 0, "Bank Jago": 0, "Dompet (Cash)": 0}
for _, row in df_transaksi.iterrows():
    try:
        sumber = str(row['Sumber Dana'])
        nom = float(row['Nominal'])
        if sumber in porto:
            porto[sumber] += nom if row['Jenis'] == "Pemasukan" else -nom
    except: pass

# ==========================================
# MESIN SAHAM REAL-TIME
# ==========================================
total_nilai_saham = 0
harga_sekarang_dict = {}

if not df_saham.empty:
    try:
        kurs_usd = yf.Ticker("USDIDR=X").history(period="1d")['Close'].iloc[-1]
        tickers = [str(t).upper() for t in df_saham['Ticker'].unique() if str(t) != "NAN"]
        # Ambil data sekaligus agar cepat
        data_yf = yf.download(tickers, period="1d", progress=False)['Close']
        
        for t in tickers:
            try:
                cp = data_yf[t].iloc[-1] if len(tickers) > 1 else data_yf.iloc[-1]
                harga_sekarang_dict[t] = cp * kurs_usd if not t.endswith('.JK') else cp
            except: harga_sekarang_dict[t] = 0
    except: pass

    for _, row in df_saham.iterrows():
        try:
            t, hb, jl = str(row['Ticker']).upper(), float(row['Harga Beli']), float(row['Jumlah Lembar'])
            cp = harga_sekarang_dict.get(t, hb)
            total_nilai_saham += (cp * jl)
        except: pass

# ==========================================
# UI TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(["🏦 Dashboard", "📈 Portofolio", "🧾 AI Scanner"])

with tab1:
    total_fiat = sum(porto.values())
    total_net = total_fiat + total_nilai_saham
    
    # Toggle Hide Balance (Mobile Friendly Placement)
    btn_label = "🙈 Hide" if not st.session_state.hide_balance else "👁️ Show"
    if st.button(btn_label):
        st.session_state.hide_balance = not st.session_state.hide_balance
        st.rerun()

    # Metrics Section (Auto-Scroll Horizontal di HP)
    col_tot, col_fiat, col_saham = st.columns(3)
    col_tot.metric("🌟 TOTAL NET WORTH", format_currency(total_net))
    col_fiat.metric("💵 LIQUID CASH", format_currency(total_fiat))
    col_saham.metric("📈 STOCK VALUE", format_currency(total_nilai_saham))
    
    # Detail Saldo
    st.write("") 
    c1, c2, c3, c4 = st.columns(4)
    c1.info(f"**BCA**\n{format_currency(porto['BCA'])}")
    c2.info(f"**BRI**\n{format_currency(porto['BRI'])}")
    c3.info(f"**JAGO**\n{format_currency(porto['Bank Jago'])}")
    c4.info(f"**CASH**\n{format_currency(porto['Dompet (Cash)'])}")
    
    st.markdown("---")
    
    # Grid Transaksi & Grafik
    col_kiri, col_kanan = st.columns([1, 1.5])
    
    with col_kiri:
        st.subheader("➕ Catat Transaksi")
        with st.form("form_transaksi", clear_on_submit=True):
            input_tanggal = st.date_input("Tanggal", date.today())
            input_kategori = st.selectbox("Kategori", ["Gaji", "Usaha", "Makan", "Transport", "Investasi", "Lainnya"])
            input_jenis = st.radio("Jenis", ["Pemasukan", "Pengeluaran"], horizontal=True)
            input_sumber = st.selectbox("Sumber", list(porto.keys()))
            input_nominal = st.number_input("Nominal", min_value=0.0, step=50000.0)
            if st.form_submit_button("Simpan Data"):
                if input_nominal > 0:
                    data_baru = pd.DataFrame([{"Tanggal": str(input_tanggal), "Kategori": input_kategori, "Jenis": input_jenis, "Sumber Dana": input_sumber, "Nominal": input_nominal}])
                    df_update = pd.concat([df_transaksi, data_baru], ignore_index=True)
                    ws_transaksi.clear()
                    set_with_dataframe(ws_transaksi, df_update)
                    if input_jenis == "Pemasukan": st.balloons()
                    st.rerun()

    with col_kanan:
        st.subheader("📊 Chart")
        t_g1, t_g2 = st.tabs(["Cashflow", "Aset"])
        with t_g1:
            if not df_transaksi.empty:
                df_cf = df_transaksi.groupby('Jenis')['Nominal'].sum().reset_index()
                fig_cf = px.bar(df_cf, x='Jenis', y='Nominal', color='Jenis', template="plotly_dark",
                                color_discrete_map={'Pemasukan':'#2ecc71', 'Pengeluaran':'#e74c3c'})
                fig_cf.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
                st.plotly_chart(fig_cf, use_container_width=True)
        with t_g2:
            aset_data = {**porto, "Saham": total_nilai_saham}
            df_aset = pd.DataFrame([{"Aset": k, "Nilai": v} for k, v in aset_data.items() if v > 0])
            fig_p = px.pie(df_aset, values='Nilai', names='Aset', hole=0.5, template="plotly_dark")
            fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=300)
            st.plotly_chart(fig_p, use_container_width=True)

    st.subheader("📋 Ledger")
    st.data_editor(df_transaksi, use_container_width=True, height=250)

with tab2:
    st.subheader("💼 Equity Portfolio")
    if not df_saham.empty:
        display_data = []
        for _, row in df_saham.iterrows():
            try:
                t, hb, jl = str(row['Ticker']).upper(), float(row['Harga Beli']), float(row['Jumlah Lembar'])
                cp = harga_sekarang_dict.get(t, hb)
                profit_pct = ((cp - hb) / hb) * 100 if hb > 0 else 0
                status = "🟢" if profit_pct > 0 else "🔴"
                display_data.append({
                    "Kode": f"{t} {status}",
                    "Lot": f"{jl/100:.0f}",
                    "Avg": format_currency(hb),
                    "Price": format_currency(cp),
                    "Value": format_currency(cp * jl),
                    "Return": f"{profit_pct:.2f}%" if not st.session_state.hide_balance else "•••"
                })
            except: pass
        st.table(pd.DataFrame(display_data))

    st.markdown("---")
    st.subheader("🤖 AI Analysis")
    ticker_ai = st.text_input("Kode Saham (Contoh: BBCA.JK)", "BBCA.JK").upper()
    try:
        data_ai = yf.Ticker(ticker_ai).history(period="6mo")
        if not data_ai.empty:
            fig_ai = go.Figure(data=[go.Candlestick(x=data_ai.index, open=data_ai['Open'], high=data_ai['High'], low=data_ai['Low'], close=data_ai['Close'])])
            fig_ai.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', height=400, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_ai, use_container_width=True)
            
            rsi = ta.rsi(data_ai['Close'], length=14).iloc[-1]
            st.metric("RSI (14D)", f"{rsi:.2f}")
            if rsi < 30: st.success("🎯 BUY AREA")
            elif rsi > 70: st.error("⚠️ SELL AREA")
            else: st.info("⚖️ HOLD")
    except: st.error("Data tidak ditemukan")

with tab3:
    st.subheader("🧾 Receipt AI")
    up = st.file_uploader("Upload Foto", type=["jpg", "png", "jpeg"])
    if up:
        img = Image.open(up)
        st.image(img, use_container_width=True)
        if st.button("Jalankan Scanner"):
            with st.spinner("Memindai..."):
                try:
                    res = pytesseract.image_to_string(img)
                    st.text_area("Hasil Scan", res, height=300)
                except: st.error("Gagal Scan")
