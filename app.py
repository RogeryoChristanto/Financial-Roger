import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
import pytesseract
from PIL import Image
from datetime import date, timedelta
import json
import gspread
import re
import numpy as np
from sklearn.linear_model import LinearRegression
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# ==========================================
# 1. KONFIGURASI HALAMAN & INGATAN APLIKASI
# ==========================================
st.set_page_config(page_title="R-Finance", page_icon="❄️", layout="wide")

if 'hide_balance' not in st.session_state:
    st.session_state.hide_balance = False

def format_currency(value):
    if st.session_state.hide_balance:
        return "Rp ••••••••"
    return f"Rp {value:,.0f}".replace(",", ".")

def render_beautiful_table(df):
    html_table = df.to_html(classes='custom-table', index=False, escape=False)
    st.markdown(f'<div class="table-wrapper">{html_table}</div>', unsafe_allow_html=True)

# ==========================================
# 2. DESAIN "DEEP OCEAN SAPPHIRE" + TABEL KACA (CSS)
# ==========================================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800;900&display=swap');
    
    header, footer {visibility: hidden !important;}
    
    @keyframes gradientMove {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .stApp, [data-testid="stAppViewContainer"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background: linear-gradient(-45deg, #020C1B, #0A192F, #112240, #0B132B) !important;
        background-size: 400% 400% !important;
        animation: gradientMove 15s ease infinite !important;
        color: #E2E8F0 !important;
    }

    .snow-overlay {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        pointer-events: none; z-index: 0; 
        background-image: 
            radial-gradient(circle, rgba(255,255,255,0.8) 1.5px, transparent 2px),
            radial-gradient(circle, rgba(255,255,255,0.5) 1px, transparent 2px),
            radial-gradient(circle, rgba(255,255,255,0.3) 2px, transparent 3px);
        background-size: 100px 100px, 200px 200px, 300px 300px;
        background-position: 0 0, 0 0, 0 0;
        animation: snowFall 15s linear infinite;
    }
    @keyframes snowFall {
        0% { background-position: 0px 0px, 0px 0px, 0px 0px; }
        100% { background-position: 100px 1000px, 200px 1000px, 300px 1000px; }
    }

    .new-title-style {
        font-size: clamp(30px, 7vw, 55px); font-weight: 900;
        text-align: center; padding-top: 20px; letter-spacing: -1px;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #FFFFFF;
        background: linear-gradient(to bottom, #FFFFFF 0%, #B4ECF3 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-shadow: 0px 0px 8px rgba(0, 198, 255, 0.8), 0px 0px 16px rgba(0, 198, 255, 0.4), 0px 0px 24px rgba(0, 198, 255, 0.2);
    }

    /* KUSTOMISASI TABEL GLASSMORPHISM BARU */
    .table-wrapper {
        background: linear-gradient(135deg, rgba(10, 25, 47, 0.5), rgba(17, 34, 64, 0.3));
        backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px);
        border: 1px solid rgba(0, 198, 255, 0.15); border-radius: 16px;
        overflow-x: auto; overflow-y: auto; max-height: 350px;
        margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }
    .table-wrapper::-webkit-scrollbar { width: 8px; height: 8px; }
    .table-wrapper::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.02); border-radius: 10px; }
    .table-wrapper::-webkit-scrollbar-thumb { background: rgba(0, 198, 255, 0.2); border-radius: 10px; }
    .table-wrapper::-webkit-scrollbar-thumb:hover { background: rgba(0, 198, 255, 0.5); }
    
    .custom-table {
        width: 100%; border-collapse: collapse; color: #E2E8F0; font-size: 13.5px; text-align: left;
    }
    .custom-table thead th {
        position: sticky; top: 0; z-index: 1; background: #061022;
        padding: 16px 20px; font-weight: 800; color: #00F2FE;
        text-transform: uppercase; letter-spacing: 1px;
        border-bottom: 1px solid rgba(0, 198, 255, 0.4);
    }
    .custom-table td {
        padding: 14px 20px; border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        transition: all 0.3s ease;
    }
    .custom-table tbody tr:hover td {
        background-color: rgba(0, 198, 255, 0.12); color: #FFF; cursor: pointer;
    }
    .custom-table tbody tr:last-of-type td { border-bottom: none; }

    [data-testid="stTabs"] button[data-baseweb="tab"] {
        background-color: rgba(255,255,255,0.05); border-radius: 50px; margin-right: 10px;
        padding: 10px 24px; font-weight: 600; color: #94A3B8;
        border: 1px solid rgba(255,255,255,0.1); transition: all 0.3s ease;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"]:hover { background-color: rgba(255,255,255,0.15); color: #FFF; }
    [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #4FACFE 0%, #00F2FE 100%);
        color: #020C1B; border: none; box-shadow: 0 5px 20px rgba(0, 198, 255, 0.4);
    }
    [data-testid="stTabs"] div[data-baseweb="tab-list"] { gap: 10px; padding-bottom: 5px; }
    [data-testid="stTabs"] div[data-baseweb="tab-highlight"] { display: none; }

    .wallet-container { display: flex; gap: 20px; overflow-x: auto; padding: 15px 10px 40px 10px; scrollbar-width: none; position: relative; z-index: 1;}
    .wallet-container::-webkit-scrollbar { display: none; }
    
    .wallet-card {
        min-width: 270px; padding: 25px; border-radius: 24px;
        background: linear-gradient(135deg, rgba(10, 25, 47, 0.7), rgba(17, 34, 64, 0.5)); 
        backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(100, 255, 218, 0.1); 
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.1);
        position: relative; overflow: hidden; transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
    }
    .wallet-card:hover {
        transform: translateY(-10px) scale(1.02); 
        box-shadow: 0 20px 40px rgba(0, 198, 255, 0.15); border: 1px solid rgba(0, 198, 255, 0.5);
    }
    
    .wallet-card::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 5px; }
    .bca-card::before { background: linear-gradient(90deg, #00C6FF, #0072FF); }
    .bri-card::before { background: linear-gradient(90deg, #F2994A, #F2C94C); }
    .jago-card::before { background: linear-gradient(90deg, #F4A300, #ffe259); }
    .cash-card::before { background: linear-gradient(90deg, #11998e, #38ef7d); }
    
    .wallet-icon { font-size: 32px; margin-bottom: 15px; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.4)); }
    .wallet-label { font-size: 11px; font-weight: 800; color: #94A3B8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; }
    .wallet-balance { font-size: 28px; font-weight: 900; color: #FFF; letter-spacing: -0.5px; }

    @keyframes pulseGlow {
        0% { text-shadow: 0 0 10px rgba(0, 198, 255, 0.2); }
        50% { text-shadow: 0 0 25px rgba(0, 198, 255, 0.9), 0 0 10px rgba(0, 198, 255, 0.5); }
        100% { text-shadow: 0 0 10px rgba(0, 198, 255, 0.2); }
    }
    div[data-testid="metric-container"]:nth-child(1) [data-testid="stMetricValue"] {
        background: linear-gradient(to right, #89F7FE, #66A6FF);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        animation: pulseGlow 3s infinite alternate;
    }
    [data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: 900 !important; color: #FFF !important; }
    [data-testid="stMetricLabel"] { font-size: 0.95rem !important; font-weight: 600 !important; color: #94A3B8 !important; letter-spacing: 0.5px; text-transform: uppercase; }

    .stButton button {
        background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%) !important; 
        color: #4FACFE !important; backdrop-filter: blur(10px);
        font-weight: 800 !important; letter-spacing: 1px !important; border-radius: 16px !important;
        border: 1px solid rgba(0, 198, 255, 0.3) !important; padding: 20px !important; transition: all 0.4s ease !important;
        position: relative; z-index: 2;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #4FACFE 0%, #00F2FE 100%) !important; color: #020C1B !important;
        transform: translateY(-3px); box-shadow: 0 15px 30px rgba(0, 198, 255, 0.4) !important; border: 1px solid transparent !important;
    }
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
        background-color: rgba(10, 25, 47, 0.6) !important; border: 1px solid rgba(100, 255, 218, 0.2) !important; 
        border-radius: 12px !important; color: white !important; box-shadow: inset 0 2px 5px rgba(0,0,0,0.5) !important;
        position: relative; z-index: 2;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border: 1px solid #4FACFE !important; box-shadow: 0 0 15px rgba(0, 198, 255, 0.3) !important; background-color: rgba(17, 34, 64, 0.8) !important;
    }
    
    div[role="radiogroup"] { gap: 15px !important; margin-top: 5px !important; }
    div[role="radiogroup"] > label {
        background-color: rgba(10, 25, 47, 0.6) !important; border: 1px solid rgba(100, 255, 218, 0.2) !important;
        padding: 12px 25px !important; border-radius: 12px !important; transition: all 0.3s ease !important; cursor: pointer !important;
    }
    div[role="radiogroup"] > label:hover { background-color: rgba(17, 34, 64, 0.8) !important; border: 1px solid rgba(0, 198, 255, 0.4) !important; }
    div[role="radiogroup"] > label > div:first-child { display: none !important; }

    div[role="radiogroup"] > label:nth-child(1):has(input:checked) {
        background: linear-gradient(135deg, rgba(0, 242, 254, 0.15) 0%, rgba(79, 172, 254, 0.25) 100%) !important;
        border: 1px solid #00F2FE !important; box-shadow: 0 0 15px rgba(0, 242, 254, 0.4) !important;
    }
    div[role="radiogroup"] > label:nth-child(1):has(input:checked) p { color: #00F2FE !important; font-weight: 800 !important; }

    div[role="radiogroup"] > label:nth-child(2):has(input:checked) {
        background: linear-gradient(135deg, rgba(255, 65, 108, 0.15) 0%, rgba(255, 75, 43, 0.25) 100%) !important;
        border: 1px solid #FF416C !important; box-shadow: 0 0 15px rgba(255, 65, 108, 0.4) !important;
    }
    div[role="radiogroup"] > label:nth-child(2):has(input:checked) p { color: #FF416C !important; font-weight: 800 !important; }

    [data-testid="stDecoration"] { display: none; }
    
    @media (max-width: 768px) {
        div[data-testid="column"] { min-width: 100% !important; } .wallet-card { min-width: 85vw; }
        [data-testid="stTabs"] button[data-baseweb="tab"] { width: 100%; text-align: center; margin-bottom: 5px; }
        [data-testid="stTabs"] div[data-baseweb="tab-list"] { flex-direction: column; }
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)
st.markdown('<div class="snow-overlay"></div>', unsafe_allow_html=True)

# ==========================================
# FITUR KEAMANAN: GEMBOK LOGIN KEYPAD PRO
# ==========================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'pin_input' not in st.session_state:
    st.session_state.pin_input = ""

if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True) 
    
    col_kiri, col_tengah, col_kanan = st.columns([1, 1.2, 1])
    
    with col_tengah:
        st.markdown('<p class="new-title-style">❄️ WELCOME</p>', unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94A3B8; margin-bottom: 20px;'>Masukkan 6 Digit PIN Rahasia</p>", unsafe_allow_html=True)
        
        pin_length = len(st.session_state.pin_input)
        dots_html = '<div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 30px;">'
        for i in range(6):
            if i < pin_length:
                dots_html += '<div style="width: 22px; height: 22px; border-radius: 50%; background: linear-gradient(135deg, #00F2FE, #4FACFE); box-shadow: 0 0 15px rgba(0, 242, 254, 0.8);"></div>'
            else:
                dots_html += '<div style="width: 22px; height: 22px; border-radius: 50%; background-color: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.2);"></div>'
        dots_html += '</div>'
        st.markdown(dots_html, unsafe_allow_html=True)
        
        if pin_length == 6:
            if st.session_state.pin_input == "120224": 
                st.session_state.authenticated = True
                st.session_state.pin_input = "" 
                st.rerun() 
            else:
                st.error("❌ AKSES DITOLAK: PIN SALAH!")
                if st.button("Coba Lagi", use_container_width=True):
                    st.session_state.pin_input = ""
                    st.rerun()
                st.stop()

        k1, k2, k3 = st.columns(3)
        with k1:
            if st.button("1", use_container_width=True): st.session_state.pin_input += "1"; st.rerun()
            if st.button("4", use_container_width=True): st.session_state.pin_input += "4"; st.rerun()
            if st.button("7", use_container_width=True): st.session_state.pin_input += "7"; st.rerun()
            if st.button("C", use_container_width=True): st.session_state.pin_input = ""; st.rerun()
        with k2:
            if st.button("2", use_container_width=True): st.session_state.pin_input += "2"; st.rerun()
            if st.button("5", use_container_width=True): st.session_state.pin_input += "5"; st.rerun()
            if st.button("8", use_container_width=True): st.session_state.pin_input += "8"; st.rerun()
            if st.button("0", use_container_width=True): st.session_state.pin_input += "0"; st.rerun()
        with k3:
            if st.button("3", use_container_width=True): st.session_state.pin_input += "3"; st.rerun()
            if st.button("6", use_container_width=True): st.session_state.pin_input += "6"; st.rerun()
            if st.button("9", use_container_width=True): st.session_state.pin_input += "9"; st.rerun()
            if st.button("⌫", use_container_width=True): st.session_state.pin_input = st.session_state.pin_input[:-1]; st.rerun()
    st.stop()

with st.sidebar:
    st.markdown("<h2 style='color:#00F2FE;'>⚙️ Sistem Kendali</h2>", unsafe_allow_html=True)
    if st.button("🔒 Kunci Kembali Aplikasi", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.pin_input = "" 
        st.rerun()

# ==========================================
# 3. KONEKSI & MESIN PEMBERSIH KHUSUS INDONESIA
# ==========================================
@st.cache_resource
def init_connection():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(st.secrets["GOOGLE_JSON"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("Database Finance Pro") 
    except Exception: return None

db = init_connection()
if not db:
    st.error("Gagal terhubung ke Cloud Database. Silakan cek koneksi atau konfigurasi st.secrets.")
    st.stop()

@st.cache_data(ttl=60)
def load_data_from_sheets():
    _df_t = get_as_dataframe(db.worksheet("Transaksi")).dropna(how='all', axis=0).dropna(how='all', axis=1)
    _df_s = get_as_dataframe(db.worksheet("Saham")).dropna(how='all', axis=0).dropna(how='all', axis=1)
    return _df_t, _df_s

def bersihkan_angka_indo(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    v = str(val).upper().replace('RP', '').strip()
    if ',' in v and len(v.split(',')[-1]) <= 2: v = v.split(',')[0] 
    v = v.replace('.', '').replace(' ', '')
    bersih = re.sub(r'[^\d]', '', v)
    try: return float(bersih) if bersih else 0.0
    except: return 0.0

def bersihkan_tanggal_indo(val):
    if pd.isna(val) or str(val).strip() == "": return pd.to_datetime(date.today())
    d_str = str(val).split(' ')[0].strip() 
    try:
        if '/' in d_str:
            parts = d_str.split('/')
            if len(parts) == 3:
                if len(parts[2]) == 4: return pd.to_datetime(f"{parts[2]}-{parts[1]}-{parts[0]}") 
                if len(parts[0]) == 4: return pd.to_datetime(f"{parts[0]}-{parts[1]}-{parts[2]}") 
        elif '-' in d_str:
            parts = d_str.split('-')
            if len(parts) == 3:
                if len(parts[0]) == 4: return pd.to_datetime(d_str) 
                if len(parts[2]) == 4: return pd.to_datetime(f"{parts[2]}-{parts[1]}-{parts[0]}") 
        return pd.to_datetime(d_str, dayfirst=True, errors='coerce')
    except: return pd.to_datetime(date.today())

try:
    ws_transaksi = db.worksheet("Transaksi")
    ws_saham = db.worksheet("Saham")
    df_t_raw, df_s_raw = load_data_from_sheets()
    df_transaksi = df_t_raw.copy()
    df_saham = df_s_raw.copy()
    
    if not df_transaksi.empty:
        if 'Nominal' in df_transaksi.columns:
            df_transaksi['Nominal'] = df_transaksi['Nominal'].apply(bersihkan_angka_indo)
        if 'Tanggal' in df_transaksi.columns:
            df_transaksi['Tanggal'] = df_transaksi['Tanggal'].apply(bersihkan_tanggal_indo)
            df_transaksi['Tanggal'] = df_transaksi['Tanggal'].fillna(pd.to_datetime(date.today()))
except Exception as e:
    st.error(f"Gagal memuat worksheet: {e}")
    st.stop()

# ==========================================
# 4. PENGHITUNG SALDO & HARGA SAHAM
# ==========================================
porto = {"BCA": 0, "BRI": 0, "Bank Jago": 0, "Dompet (Cash)": 0}

if not df_transaksi.empty:
    for _, row in df_transaksi.iterrows():
        try:
            s, j, n = str(row.get('Sumber Dana', '')), str(row.get('Jenis', '')), float(row.get('Nominal', 0))
            if s in porto: porto[s] += n if j.lower() == "pemasukan" else -n
        except ValueError: pass

total_nilai_saham = 0
harga_sekarang_dict = {}

if not df_saham.empty:
    try:
        kurs_data = yf.Ticker("USDIDR=X").history(period="1d")
        kurs = kurs_data['Close'].iloc[-1] if not kurs_data.empty else 15000 
        tks = [str(t).upper().strip() for t in df_saham['Ticker'].unique() if pd.notna(t) and str(t).strip() != ""]
        if tks:
            data_yf = yf.download(tks, period="1d", progress=False)
            for t in tks:
                try:
                    cp = float(data_yf['Close'][t].iloc[-1]) if len(tks) > 1 else float(data_yf['Close'].iloc[-1])
                    if pd.isna(cp): cp = 0
                    harga_sekarang_dict[t] = cp * kurs if not t.endswith('.JK') else cp
                except Exception: harga_sekarang_dict[t] = 0
    except Exception: pass 

    for _, row in df_saham.iterrows():
        ticker = str(row.get('Ticker', '')).upper().strip()
        try: jumlah = float(row.get('Jumlah Lembar', 0))
        except: jumlah = 0.0
        try: harga_beli = float(row.get('Harga Beli', 0))
        except: harga_beli = 0.0
        
        harga_skrg = harga_sekarang_dict.get(ticker, 0)
        if pd.isna(harga_skrg) or harga_skrg == 0: harga_skrg = harga_beli
        total_nilai_saham += (harga_skrg * jumlah)

# ==========================================
# 5. TAMPILAN MENU UTAMA
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["🏦 DASHBOARD KEKAYAAN", "📈 Portofolio Saham", "🧾 AI Smart Scanner", "⚡ Live Screener"])

with tab1:
    c_btn1, c_btn2 = st.columns([2, 1])
    with c_btn2:
        if st.button("🙈 Sembunyikan Angka" if not st.session_state.hide_balance else "👁️ Tampilkan Angka", use_container_width=True):
            st.session_state.hide_balance = not st.session_state.hide_balance
            st.rerun()

    total_net = sum(porto.values()) + total_nilai_saham
    st.markdown("##### 🎯 Target Pencapaian Harta Bersih")
    target_teks = st.text_input("Atur Target Finansial Anda (Rp)", value="100.000.000", label_visibility="collapsed")
    try: target_harta = float(target_teks.replace(".", "").replace(",", ""))
    except ValueError: target_harta = 100000000.0 

    rasio = total_net / target_harta if target_harta > 0 else 0.0
    st.progress(max(0.0, min(rasio, 1.0)))
    st.caption(f"Tercapai: **{max(0.0, min(rasio, 1.0))*100:.1f}%** dari target {format_currency(target_harta)}")
    st.markdown("---")

    m1, m2, m3 = st.columns(3)
    m1.metric("🌟 TOTAL HARTA BERSIH", format_currency(total_net))
    m2.metric("💵 TOTAL UANG TUNAI", format_currency(sum(porto.values())))
    m3.metric("📈 TOTAL NILAI SAHAM", format_currency(total_nilai_saham))
    st.markdown("---")
    
    st.markdown("###### 📅 Filter Laporan Arus Kas")
    col_f1, col_f2 = st.columns(2)
    nama_bulan = ["Semua Waktu", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    today = date.today()
    with col_f1: pilih_bulan = st.selectbox("Pilih Bulan", nama_bulan, index=today.month)
    with col_f2: pilih_tahun = st.selectbox("Pilih Tahun", list(range(2020, today.year + 10)), index=list(range(2020, today.year + 10)).index(today.year))

    in_curr, out_curr, in_prev, out_prev = 0.0, 0.0, 0.0, 0.0
    df_curr = pd.DataFrame() 

    if not df_transaksi.empty:
        df_calc = df_transaksi.copy()
        df_calc['Jenis'] = df_calc['Jenis'].astype(str).str.strip().str.lower()
        
        if pilih_bulan == "Semua Waktu":
            df_curr = df_calc.copy()
            in_curr = df_curr[df_curr['Jenis'] == 'pemasukan']['Nominal'].sum()
            out_curr = df_curr[df_curr['Jenis'] == 'pengeluaran']['Nominal'].sum()
            judul_lap = "Semua Riwayat"
        else:
            curr_m = nama_bulan.index(pilih_bulan)
            curr_y = pilih_tahun
            prev_m = 12 if curr_m == 1 else curr_m - 1
            prev_y = curr_y - 1 if curr_m == 1 else curr_y
            
            df_curr = df_calc[(df_calc['Tanggal'].dt.month == curr_m) & (df_calc['Tanggal'].dt.year == curr_y)]
            df_prev = df_calc[(df_calc['Tanggal'].dt.month == prev_m) & (df_calc['Tanggal'].dt.year == prev_y)]
            
            in_curr = df_curr[df_curr['Jenis'] == 'pemasukan']['Nominal'].sum()
            out_curr = df_curr[df_curr['Jenis'] == 'pengeluaran']['Nominal'].sum()
            in_prev = df_prev[df_prev['Jenis'] == 'pemasukan']['Nominal'].sum()
            out_prev = df_prev[df_prev['Jenis'] == 'pengeluaran']['Nominal'].sum()
            judul_lap = f"{pilih_bulan} {curr_y}"

    def calc_delta(curr, prev):
        if pilih_bulan == "Semua Waktu": return None
        if prev == 0 and curr > 0: return "100% (Bulan lalu Rp 0)"
        if prev == 0 and curr <= 0: return "0%"
        return f"{((curr - prev) / prev) * 100:+.1f}% vs Bulan Lalu"

    cm1, cm2, cm3 = st.columns(3)
    cm1.metric(f"Pemasukan", format_currency(in_curr), delta=calc_delta(in_curr, in_prev), delta_color="normal")
    cm2.metric(f"Pengeluaran", format_currency(out_curr), delta=calc_delta(out_curr, out_prev), delta_color="inverse")
    cm3.metric(f"Sisa Uang", format_currency(in_curr - out_curr), delta=calc_delta(in_curr - out_curr, in_prev - out_prev), delta_color="normal")
    st.markdown("---")

    st.markdown('<div class="wallet-container">', unsafe_allow_html=True)
    wc = st.columns(4)
    wallets = [{"name": "BANK BCA", "val": porto["BCA"], "class": "bca-card", "icon": "🏦"}, {"name": "BANK BRI", "val": porto["BRI"], "class": "bri-card", "icon": "🏢"}, {"name": "BANK JAGO", "val": porto["Bank Jago"], "class": "jago-card", "icon": "🦊"}, {"name": "UANG TUNAI", "val": porto["Dompet (Cash)"], "class": "cash-card", "icon": "💵"}]
    for i, w in enumerate(wallets):
        with wc[i]: st.markdown(f'''<div class="wallet-card {w['class']}"><div class="wallet-icon">{w['icon']}</div><div class="wallet-label">{w['name']}</div><div class="wallet-balance">{format_currency(w['val'])}</div></div>''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    col_l, col_r = st.columns([1, 1.5])
    with col_l:
        st.subheader("➕ Tambah Transaksi")
        with st.form("trx_form", clear_on_submit=True):
            f_tgl = st.date_input("Tanggal", date.today())
            f_kat = st.selectbox("Kategori", ["Gaji", "Makan & Minum", "Belanja", "Transport", "Investasi", "Parfum", "Bayar Kost", "Skincare", "Lainnya"])
            f_jen = st.radio("Jenis", ["Pemasukan", "Pengeluaran"], horizontal=True)
            f_src = st.selectbox("Pilih Dompet", list(porto.keys()))
            
            # Menarik nominal dari ingatan AI (jika ada)
            default_nom = st.session_state.get('auto_nominal', "")
            f_nom_teks = st.text_input("Jumlah Uang (Rp)", value=default_nom, placeholder="Contoh: 50.000")
            
            f_note = st.text_area("Catatan / Rincian", placeholder="Contoh: Beli kemeja")
            if st.form_submit_button("SIMPAN SEKARANG"):
                try: f_nom = float(f_nom_teks.replace(".", "").replace(",", "")) if f_nom_teks else 0.0
                except ValueError: f_nom = 0.0
                new_row = pd.DataFrame([{"Tanggal": f_tgl.strftime('%Y-%m-%d'), "Kategori": f_kat, "Jenis": f_jen, "Sumber Dana": f_src, "Nominal": f_nom, "Catatan": f_note}])
                df_updated = pd.concat([df_transaksi, new_row], ignore_index=True)
                df_updated['Tanggal'] = pd.to_datetime(df_updated['Tanggal']).dt.strftime('%Y-%m-%d')
                set_with_dataframe(ws_transaksi, df_updated, row=1)
                if f_jen == "Pemasukan": st.snow()
                st.session_state.auto_nominal = "" # Reset sesudah disimpan
                st.cache_data.clear(); st.rerun()

    with col_r:
        st.subheader(f"📊 Analisis Visual")
        g1, g2, g3 = st.tabs(["Arus Kas", "Pembagian Aset", "Rincian Pengeluaran"])
        with g1:
            if not df_curr.empty:
                df_grouped = df_curr.groupby('Jenis')['Nominal'].sum().reset_index()
                df_grouped['Jenis'] = df_grouped['Jenis'].str.title() 
                fig = px.bar(df_grouped, x='Jenis', y='Nominal', color='Jenis', template="plotly_dark", color_discrete_map={'Pemasukan':'#2ecc71', 'Pengeluaran':'#e74c3c'})
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
                st.plotly_chart(fig, use_container_width=True)
        with g2:
            df_p = pd.DataFrame([{"Aset": k, "Nilai": v} for k, v in {**porto, "Saham": total_nilai_saham}.items() if v > 0])
            if not df_p.empty:
                fig_p = px.pie(df_p, values='Nilai', names='Aset', hole=0.5, template="plotly_dark", color='Aset', color_discrete_map={'BCA': '#0066AE', 'BRI': '#F26522', 'Bank Jago': '#F4A300', 'Dompet (Cash)': '#27AE60', 'Saham': '#8E44AD'})
                fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=320, showlegend=True)
                st.plotly_chart(fig_p, use_container_width=True)
        with g3:
            if not df_curr.empty and not df_curr[df_curr['Jenis'] == 'pengeluaran'].empty:
                fig_kat = px.pie(df_curr[df_curr['Jenis'] == 'pengeluaran'].groupby('Kategori')['Nominal'].sum().reset_index(), values='Nominal', names='Kategori', hole=0.4, template="plotly_dark")
                fig_kat.update_traces(textposition='inside', textinfo='percent+label')
                fig_kat.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=320, showlegend=False)
                st.plotly_chart(fig_kat, use_container_width=True)

    st.subheader("📋 Riwayat Transaksi Lengkap")
    if not df_transaksi.empty:
        df_display = df_transaksi.copy()
        df_display['Tanggal'] = pd.to_datetime(df_display['Tanggal']).dt.strftime('%Y-%m-%d')
        df_display['Nominal'] = df_display['Nominal'].apply(lambda x: format_currency(x))
        df_display = df_display.sort_values(by='Tanggal', ascending=False).reset_index(drop=True)
        
        df_html = df_display.copy()
        df_html.index = df_html.index + 1
        df_html.reset_index(inplace=True)
        df_html.rename(columns={'index': 'No'}, inplace=True)
        
        render_beautiful_table(df_html)
        st.download_button("📥 Download Excel/CSV Transaksi", data=df_transaksi.to_csv(index=False).encode('utf-8'), file_name="Riwayat_Transaksi_ROGER.csv", mime="text/csv")

with tab2:
    st.subheader("💼 Portofolio & Input Saham")
    with st.expander("➕ Tambah Data Saham Baru", expanded=False):
        with st.form("form_saham", clear_on_submit=True):
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1: new_ticker = st.text_input("Kode Ticker", help="Akhiri .JK untuk Indonesia").upper()
            with col_s2: new_lembar = st.number_input("Jumlah Lembar", min_value=1, step=100)
            with col_s3: new_harga_teks = st.text_input("Harga Beli Rata-rata (Rp)")
            if st.form_submit_button("SIMPAN KE PORTOFOLIO"):
                try: new_harga = float(new_harga_teks.replace(".", "").replace(",", "")) if new_harga_teks else 0.0
                except ValueError: new_harga = 0.0
                if new_ticker:
                    df_saham_updated = pd.concat([df_saham, pd.DataFrame([{"Ticker": new_ticker.strip(), "Jumlah Lembar": new_lembar, "Harga Beli": new_harga}])], ignore_index=True)
                    set_with_dataframe(ws_saham, df_saham_updated, row=1)
                    st.success(f"Tersimpan: {new_ticker}!"); st.cache_data.clear(); st.rerun()

    if not df_saham.empty:
        rows, pie_data_saham = [], []
        for _, r in df_saham.iterrows():
            t = str(r.get('Ticker', '')).upper()
            harga_beli = float(r.get('Harga Beli', 0))
            lembar = float(r.get('Jumlah Lembar', 0))
            harga_skrg = harga_sekarang_dict.get(t, harga_beli)
            gain = ((harga_skrg - harga_beli) / harga_beli) * 100 if harga_beli > 0 else 0.0
            total_nilai = harga_skrg * lembar
            
            gain_str = f"{gain:.2f}%"
            if gain > 0: gain_html = f'<span style="color:#00F2FE; font-weight:800;">▲ {gain_str}</span>'
            elif gain < 0: gain_html = f'<span style="color:#FF416C; font-weight:800;">▼ {gain_str}</span>'
            else: gain_html = f'<span style="color:#94A3B8;">{gain_str}</span>'

            rows.append({
                "Kode Saham": f"<b>{t}</b>", 
                "Total Lot": f"{lembar/100:.0f} Lot", 
                "Harga Beli": format_currency(harga_beli), 
                "Harga Sekarang": format_currency(harga_skrg), 
                "Keuntungan (%)": gain_html,
                "_raw_gain": gain_str 
            })
            if total_nilai > 0: pie_data_saham.append({"Ticker": t, "Nilai": total_nilai})
            
        df_tampil = pd.DataFrame(rows)
        df_html_saham = df_tampil.drop(columns=['_raw_gain'])
        
        render_beautiful_table(df_html_saham)
        
        df_csv = df_tampil.drop(columns=['Keuntungan (%)']).rename(columns={'_raw_gain': 'Keuntungan (%)'})
        df_csv['Kode Saham'] = df_csv['Kode Saham'].str.replace('<b>', '').str.replace('</b>', '')
        
        col_sd1, col_sd2 = st.columns([1, 1])
        with col_sd1: st.download_button("📥 Download Portofolio", data=df_csv.to_csv(index=False).encode('utf-8'), file_name="Portofolio_ROGER.csv", mime="text/csv")
        with col_sd2:
            with st.expander("📊 Lihat Alokasi Saham"):
                if pie_data_saham:
                    fig_saham = px.pie(pd.DataFrame(pie_data_saham), values='Nilai', names='Ticker', hole=0.4, template="plotly_dark")
                    fig_saham.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_saham, use_container_width=True)
        
    st.markdown("---")
    st.subheader("📈 Analisis Pergerakan Saham Pro + Prediksi AI 🤖")
    target = st.text_input("Ketik Kode Ticker:", "BBCA.JK").upper()
    try:
        h = yf.Ticker(target).history(period="6mo")
        if not h.empty:
            h.index = h.index.tz_localize(None)
            fig_h = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], name='Harga Asli')])
            if len(h) >= 50:
                h['SMA_20'], h['SMA_50'] = ta.sma(h['Close'], length=20), ta.sma(h['Close'], length=50)
                fig_h.add_trace(go.Scatter(x=h.index, y=h['SMA_20'], line=dict(color='#3498db', width=2), name='SMA 20'))
                fig_h.add_trace(go.Scatter(x=h.index, y=h['SMA_50'], line=dict(color='#f1c40f', width=2), name='SMA 50'))
                
                df_ml = h[['Close']].copy()
                df_ml['Hari_Ke'] = np.arange(len(df_ml))
                model = LinearRegression().fit(df_ml[['Hari_Ke']], df_ml['Close'])
                hari_terakhir = df_ml['Hari_Ke'].max()
                future_dates = pd.bdate_range(start=h.index[-1] + timedelta(days=1), periods=7)
                y_pred_future = model.predict(pd.DataFrame({'Hari_Ke': np.arange(hari_terakhir + 1, hari_terakhir + 8)}))
                
                fig_h.add_trace(go.Scatter(x=[h.index[-1]] + list(future_dates), y=[df_ml['Close'].iloc[-1]] + list(y_pred_future), mode='lines+markers', line=dict(color='#00F2FE', width=3, dash='dot'), name='Prediksi AI (7 Hari)'))

            fig_h.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', height=450, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_h, use_container_width=True)
            c_rsi, c_info = st.columns([1, 2])
            with c_rsi:
                if len(h) >= 15: st.metric("Skor RSI-14", f"{ta.rsi(h['Close'], length=14).iloc[-1]:.2f}")
            with c_info: st.info("🤖 **JARINGAN SARAF TIRUAN AKTIF:** Garis putus-putus *Cyan* di ujung grafik adalah proyeksi matematis Machine Learning untuk harga saham 7 hari ke depan.")
    except Exception: st.error("Gagal memuat grafik.")

with tab3:
    st.subheader("🧾 AI Smart Extractor (Auto-Fill)")
    st.markdown("Unggah struk belanja Anda. AI akan mencari total belanja dan mengisinya otomatis ke form transaksi!")
    
    up = st.file_uploader("Upload Foto Nota", type=["jpg", "png", "jpeg"])
    if up:
        col_img, col_res = st.columns([1, 1.5])
        with col_img:
            st.image(Image.open(up), use_container_width=True, caption="Nota Original")
            
        with col_res:
            if st.button("🧠 EKSTRAK TOTAL & AUTO-FILL", use_container_width=True):
                with st.spinner("AI sedang memindai dan mencari angka total..."):
                    try:
                        res = pytesseract.image_to_string(Image.open(up))
                        
                        if res.strip():
                            lines = res.lower().split('\n')
                            possible_totals = []
                            
                            for line in lines:
                                if any(keyword in line for keyword in ['total', 'jumlah', 'amount', 'pay', 'bayar', 'tagihan', 'rp']):
                                    nums = re.findall(r'\d{1,3}(?:[.,]\d{3})*', line)
                                    for num in nums:
                                        clean_num = re.sub(r'[^\d]', '', num)
                                        if clean_num: possible_totals.append(float(clean_num))
                            
                            total_akhir = max(possible_totals) if possible_totals else 0.0
                            
                            if total_akhir == 0.0:
                                all_nums = re.findall(r'\d{1,3}(?:[.,]\d{3})*', res)
                                valid_nums = [float(re.sub(r'[^\d]', '', n)) for n in all_nums if re.sub(r'[^\d]', '', n)]
                                if valid_nums: total_akhir = max(valid_nums)
                            
                            st.success("✨ Pindaian Selesai!")
                            st.metric("💰 Total Ditemukan", format_currency(total_akhir))
                            
                            if total_akhir > 0:
                                st.session_state.auto_nominal = f"{total_akhir:,.0f}".replace(",", ".")
                                st.info("✅ **Angka berhasil disalin!** Silakan kembali ke tab **🏦 DASHBOARD KEKAYAAN**, kolom Nominal sudah terisi otomatis. Anda tinggal menyimpannya.")
                            else:
                                st.warning("⚠️ AI tidak dapat menemukan angka total yang valid. Silakan input manual.")
                            
                            with st.expander("🔍 Lihat Teks Mentah (Raw OCR)"):
                                st.text_area("Teks dari Gambar:", res, height=150)
                    except Exception as e: 
                        st.error(f"Error OCR: Pastikan file packages.txt sudah berisi 'tesseract-ocr'. Detail error: {e}")

with tab4:
    st.subheader("⚡ Live Market Screener & Charting Pro")
    watchlist_input = st.text_area("Daftar Ticker:", value="GOTO.JK, BUMI.JK, BBCA.JK, PNLF.JK")
    max_price = st.number_input("Batas Harga Maksimal (Opsional, Rp)", value=0)

    if st.button("MULAI SCAN & ANALISA GRAFIK", use_container_width=True):
        with st.spinner("Mengunduh data grafik & menganalisis teknikal..."):
            try:
                tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]
                rekomendasi_beli, netral_jual = [], []
                
                for ticker in tickers:
                    try:
                        ticker_obj = yf.Ticker(ticker)
                        df_hist = ticker_obj.history(period="6mo")
                        if len(df_hist) >= 50: 
                            df_hist.index = df_hist.index.tz_localize(None)
                            close_price = float(df_hist['Close'].iloc[-1])
                            if max_price > 0 and close_price > max_price: continue 
                                
                            df_hist['SMA_20'], df_hist['SMA_50'] = ta.sma(df_hist['Close'], length=20), ta.sma(df_hist['Close'], length=50)
                            df_hist['RSI_14'] = ta.rsi(df_hist['Close'], length=14)
                            macd_df = ta.macd(df_hist['Close'])
                            macd_line, macd_hist, macd_signal = float(macd_df.iloc[-1, 0]), float(macd_df.iloc[-1, 1]), float(macd_df.iloc[-1, 2])
                            ma20, ma50, rsi_14 = float(df_hist['SMA_20'].iloc[-1]), float(df_hist['SMA_50'].iloc[-1]), float(df_hist['RSI_14'].iloc[-1])
                            
                            vol_avg_20, vol_today = float(df_hist['Volume'][-20:].mean()), float(df_hist['Volume'].iloc[-1])
                            ada_lonjakan_volume = vol_today > (vol_avg_20 * 1.5) 
                            
                            target_naik = float(df_hist['High'][-40:].max())
                            if target_naik <= close_price * 1.02: target_naik = close_price * 1.12 
                            stop_loss = float(df_hist['Low'][-20:].min())
                            if stop_loss >= close_price * 0.98: stop_loss = close_price * 0.95
                            
                            alasan, is_buy = [], False
                            if rsi_14 < 35: alasan.append(f"📉 **RSI (Jenuh Jual):** Skor {rsi_14:.1f}"); is_buy = True
                            elif 35 <= rsi_14 <= 70: alasan.append(f"⚖️ **RSI (Netral):** Skor {rsi_14:.1f}")
                            if ma20 > ma50: alasan.append(f"📈 **MA (Uptrend):** Garis MA20 di atas MA50."); is_buy = True
                            if macd_line > macd_signal and macd_hist > 0: alasan.append(f"📊 **MACD (Bullish):** Momentum beli kuat."); is_buy = True
                            if ada_lonjakan_volume: alasan.append(f"🔥 **Volume:** Lonjakan {vol_today/vol_avg_20:.1f}x lipat."); is_buy = True
                            
                            if rsi_14 >= 70: is_buy, status_akhir = False, "🔴 JUAL / HINDARI (Overbought)"
                            elif ada_lonjakan_volume and (ma20 > ma50 or (macd_line > macd_signal and macd_hist > 0)): status_akhir = "🟢 STRONG BUY"
                            elif is_buy: status_akhir = "🟢 BUY / CICIL BELI"
                            else: status_akhir = "🟡 WAIT & SEE"
                            
                            list_berita = []
                            try:
                                for artikel in ticker_obj.news[:3]:
                                    judul = str(artikel.get('title', 'Judul')).replace('[', '').replace(']', '')
                                    list_berita.append(f"- [{judul}]({artikel.get('link', '#')}) *({artikel.get('publisher', '')})*")
                            except Exception: pass
                            
                            if is_buy or len(tickers) == 1: 
                                rekomendasi_beli.append({"Ticker": ticker, "Harga": close_price, "Target": target_naik, "SL": stop_loss, "Alasan": "\n\n".join(alasan), "Kesimpulan": status_akhir, "Berita": "\n".join(list_berita) if list_berita else "_Belum ada berita._", "df_chart": df_hist.tail(90)})
                            else: 
                                netral_jual.append({"Ticker": ticker, "Harga": format_currency(close_price), "Status": status_akhir})
                    except Exception: pass 
                
                if rekomendasi_beli:
                    st.success(f"🎯 ANALISIS SELESAI!")
                    for rec in rekomendasi_beli:
                        with st.container():
                            st.markdown(f"### 🏷️ {rec['Ticker']} (Rp {rec['Harga']:,.0f})")
                            st.markdown(f"##### 📌 KESIMPULAN AKHIR: {rec['Kesimpulan']}")
                            col_t1, col_t2 = st.columns(2)
                            h_aman = rec['Harga'] if rec['Harga'] > 0 else 1
                            col_t1.metric("🎯 Target Take Profit", format_currency(rec['Target']), delta=f"+{((rec['Target'] - rec['Harga']) / h_aman) * 100:.1f}%")
                            col_t2.metric("🛡️ Batas Stop Loss", format_currency(rec['SL']), delta=f"{((rec['SL'] - rec['Harga']) / h_aman) * 100:.1f}%", delta_color="inverse")
                            
                            df_plot = rec['df_chart']
                            fig = go.Figure()
                            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Harga', increasing_line_color='#2ecc71', decreasing_line_color='#e74c3c'))
                            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA_20'], line=dict(color='#3498db', width=2), name='MA 20'))
                            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA_50'], line=dict(color='#f1c40f', width=2), name='MA 50'))
                            fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
                            st.plotly_chart(fig, use_container_width=True)
                            
                            col_info1, col_info2 = st.columns([1.2, 1])
                            with col_info1: st.info(f"**🧠 Analisis:**\n\n{rec['Alasan']}")
                            with col_info2: st.warning(f"**📰 Berita:**\n\n{rec['Berita']}")
                            st.markdown("---")
                
                with st.expander("Lihat Saham Lainnya (Kondisi Sedang Jelek / Sideways)"):
                    if netral_jual: 
                        df_netral = pd.DataFrame(netral_jual)
                        df_netral['Status'] = df_netral['Status'].apply(lambda x: f'<span style="color:#F4A300; font-weight:800;">{x}</span>')
                        render_beautiful_table(df_netral)
            except Exception as e: st.error(f"Kesalahan: {e}")
