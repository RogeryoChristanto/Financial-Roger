import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
import pytesseract
from PIL import Image
from datetime import timedelta
import json
import os
import gspread
import re
import numpy as np
from sklearn.linear_model import LinearRegression
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# ==========================================
# 1. KONFIGURASI HALAMAN & INGATAN APLIKASI
# ==========================================
st.set_page_config(page_title="ROGER-Finance", page_icon="💼", layout="wide")

if 'hide_balance' not in st.session_state:
    st.session_state.hide_balance = False

# ==========================================
# 1A. SISTEM PENYIMPANAN PENGATURAN (JSON)
# ==========================================
CONFIG_FILE = "roger_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "budgets": {"Makan & Minum": 1500000, "Belanja": 1000000, "Transport": 500000, "Parfum": 500000},
        "kategori_list": ["Gaji", "Makan & Minum", "Belanja", "Transport", "Investasi", "Parfum", "Bayar Kost", "Skincare", "Lainnya"],
        "saved_pin": "120224"
    }

def save_config():
    config_data = {
        "budgets": st.session_state.budgets,
        "kategori_list": st.session_state.kategori_list,
        "saved_pin": st.session_state.saved_pin
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f)

config = load_config()

# INGATAN DINAMIS UNTUK BUDGET, KATEGORI, DAN PIN
if 'budgets' not in st.session_state:
    st.session_state.budgets = config["budgets"]
if 'kategori_list' not in st.session_state:
    st.session_state.kategori_list = config["kategori_list"]
if 'saved_pin' not in st.session_state:
    st.session_state.saved_pin = config["saved_pin"]

def format_currency(value):
    if st.session_state.hide_balance:
        return "Rp ••••••••"
    return f"Rp {value:,.0f}".replace(",", ".")

def render_beautiful_table(df):
    html_table = df.to_html(classes='custom-table', index=False, escape=False)
    st.markdown(f'<div class="table-wrapper">{html_table}</div>', unsafe_allow_html=True)

# ==========================================
# 2. DESAIN "MODERN MIDNIGHT ONYX" (CSS)
# ==========================================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    header, footer {visibility: hidden !important;}
    
    /* Global Background */
    .stApp, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif !important;
        background-color: #0B1120 !important; /* Midnight Dark */
        color: #F8FAFC !important;
    }

    /* Clean Title */
    .new-title-style {
        font-size: clamp(28px, 5vw, 42px); font-weight: 800;
        text-align: center; padding-top: 15px; letter-spacing: -1px;
        color: #F8FAFC;
        margin-bottom: 10px;
    }

    /* Table Container */
    .table-wrapper {
        background-color: #1E293B;
        border: 1px solid #334155; border-radius: 12px;
        overflow-x: auto; overflow-y: auto; max-height: 350px;
        margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        -webkit-overflow-scrolling: touch;
    }
    .table-wrapper::-webkit-scrollbar { width: 8px; height: 8px; }
    .table-wrapper::-webkit-scrollbar-track { background: #0F172A; border-radius: 10px; }
    .table-wrapper::-webkit-scrollbar-thumb { background: #475569; border-radius: 10px; }
    .table-wrapper::-webkit-scrollbar-thumb:hover { background: #64748B; }
    
    /* Modern Table */
    .custom-table { width: 100%; border-collapse: collapse; color: #E2E8F0; font-size: 13.5px; text-align: left; }
    .custom-table thead th {
        position: sticky; top: 0; z-index: 1; background: #0F172A;
        padding: 14px 18px; font-weight: 600; color: #94A3B8;
        text-transform: uppercase; letter-spacing: 0.5px; font-size: 12px;
        border-bottom: 1px solid #334155;
    }
    .custom-table td { padding: 14px 18px; border-bottom: 1px solid #334155; }
    .custom-table tbody tr:hover td { background-color: #0F172A; }
    .custom-table tbody tr:last-of-type td { border-bottom: none; }

    /* Clean Tabs */
    [data-testid="stTabs"] button[data-baseweb="tab"] {
        background-color: transparent; border-radius: 6px; margin-right: 8px;
        padding: 10px 20px; font-weight: 600; color: #64748B;
        border: 1px solid transparent; transition: all 0.2s ease;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"]:hover { color: #F8FAFC; background-color: #1E293B; }
    [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #1E293B; color: #38BDF8; 
        border: 1px solid #334155;
    }
    [data-testid="stTabs"] div[data-baseweb="tab-list"] { gap: 5px; padding-bottom: 10px; }
    [data-testid="stTabs"] div[data-baseweb="tab-highlight"] { display: none; }

    /* Horizontal Scroll Wallet */
    .wallet-container { display: flex; gap: 15px; overflow-x: auto; padding: 10px 5px 25px 5px; scrollbar-width: none; }
    .wallet-container::-webkit-scrollbar { display: none; }
    
    /* Modern Wallet Cards */
    .wallet-card {
        min-width: 260px; padding: 20px; border-radius: 16px;
        background-color: #1E293B;
        border: 1px solid #334155; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        position: relative; overflow: hidden; transition: transform 0.2s ease, border-color 0.2s ease;
        flex: 1;
    }
    .wallet-card:hover {
        transform: translateY(-4px); 
        border-color: #475569;
    }
    
    .wallet-card::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px; }
    .bca-card::before { background: #3B82F6; }
    .bri-card::before { background: #F97316; }
    .jago-card::before { background: #F59E0B; }
    .cash-card::before { background: #10B981; }
    
    .wallet-icon { font-size: 26px; margin-bottom: 10px; }
    .wallet-label { font-size: 11px; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
    .wallet-balance { font-size: 26px; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px; }

    /* Metrics clean style */
    div[data-testid="metric-container"] {
        background-color: #1E293B; padding: 15px; border-radius: 12px;
        border: 1px solid #334155;
    }
    [data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 800 !important; color: #F8FAFC !important; }
    div[data-testid="metric-container"]:nth-child(1) [data-testid="stMetricValue"] { color: #38BDF8 !important; }
    [data-testid="stMetricLabel"] { font-size: 13px !important; font-weight: 600 !important; color: #94A3B8 !important; text-transform: uppercase; letter-spacing: 0.5px;}

    /* Flat Modern Buttons */
    .stButton button {
        background-color: #38BDF8 !important; color: #0F172A !important; 
        font-weight: 700 !important; border-radius: 8px !important;
        border: none !important; padding: 12px 24px !important; transition: all 0.2s ease !important;
    }
    .stButton button:hover { background-color: #7DD3FC !important; transform: translateY(-2px); }
    
    /* Clean Inputs */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
        background-color: #0F172A !important; border: 1px solid #334155 !important; 
        border-radius: 8px !important; color: #F8FAFC !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: #38BDF8 !important; box-shadow: 0 0 0 1px #38BDF8 !important;
    }
    
    /* Segmented Radio */
    div[role="radiogroup"] { gap: 10px !important; margin-top: 5px !important; }
    div[role="radiogroup"] > label {
        background-color: #1E293B !important; border: 1px solid #334155 !important;
        padding: 10px 20px !important; border-radius: 8px !important; transition: all 0.2s ease !important; cursor: pointer !important;
    }
    div[role="radiogroup"] > label:hover { background-color: #334155 !important; }
    div[role="radiogroup"] > label > div:first-child { display: none !important; }

    div[role="radiogroup"] > label:nth-child(1):has(input:checked) {
        background-color: rgba(16, 185, 129, 0.1) !important; border-color: #10B981 !important;
    }
    div[role="radiogroup"] > label:nth-child(1):has(input:checked) p { color: #34D399 !important; font-weight: 700 !important; }

    div[role="radiogroup"] > label:nth-child(2):has(input:checked) {
        background-color: rgba(239, 68, 68, 0.1) !important; border-color: #EF4444 !important;
    }
    div[role="radiogroup"] > label:nth-child(2):has(input:checked) p { color: #F87171 !important; font-weight: 700 !important; }

    [data-testid="stDecoration"] { display: none; }
    
    @media (max-width: 768px) {
        [data-testid="stTabs"] div[data-baseweb="tab-list"] {
            display: flex !important; flex-direction: row !important;
            overflow-x: auto !important; white-space: nowrap !important;
            scrollbar-width: none !important; padding-bottom: 5px !important;
        }
        [data-testid="stTabs"] div[data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
        [data-testid="stTabs"] button[data-baseweb="tab"] { flex: 0 0 auto !important; width: auto !important; padding: 8px 16px !important;}
        .wallet-card { min-width: 80vw !important; padding: 15px !important; }
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# FITUR KEAMANAN: GEMBOK LOGIN KEYPAD PRO
# ==========================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'pin_input' not in st.session_state:
    st.session_state.pin_input = ""

if not st.session_state.authenticated:
    st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none; }
        
        div[data-testid="stElementContainer"]:has(#keypad-marker) + div[data-testid="stHorizontalBlock"] {
            display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important;
            justify-content: center !important; gap: 10px !important;
        }
        div[data-testid="stElementContainer"]:has(#keypad-marker) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            width: 33.33% !important; min-width: 33.33% !important;
        }
        div[data-testid="stElementContainer"]:has(#keypad-marker) + div[data-testid="stHorizontalBlock"] button {
            height: 60px !important; font-size: 22px !important; border-radius: 10px !important; padding: 0 !important;
            background-color: #1E293B !important; color: #F8FAFC !important; border: 1px solid #334155 !important;
        }
        div[data-testid="stElementContainer"]:has(#keypad-marker) + div[data-testid="stHorizontalBlock"] button:hover {
            background-color: #334155 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True) 
    col_kiri, col_tengah, col_kanan = st.columns([1, 1.2, 1])
    
    with col_tengah:
        st.markdown('<p class="new-title-style">ROGER Finance</p>', unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94A3B8; margin-bottom: 25px;'>Otentikasi Keamanan 6-Digit PIN</p>", unsafe_allow_html=True)
        
        pin_length = len(st.session_state.pin_input)
        dots_html = '<div style="display: flex; justify-content: center; gap: 15px; margin-bottom: 30px;">'
        for i in range(6):
            if i < pin_length:
                dots_html += '<div style="width: 16px; height: 16px; border-radius: 50%; background-color: #38BDF8;"></div>'
            else:
                dots_html += '<div style="width: 16px; height: 16px; border-radius: 50%; background-color: #0F172A; border: 2px solid #334155;"></div>'
        dots_html += '</div>'
        st.markdown(dots_html, unsafe_allow_html=True)
        
        if pin_length == 6:
            if st.session_state.pin_input == st.session_state.saved_pin: 
                st.session_state.authenticated = True
                st.session_state.pin_input = "" 
                st.rerun() 
            else:
                st.error("❌ Akses Ditolak: PIN Salah.")
                if st.button("Coba Lagi", use_container_width=True):
                    st.session_state.pin_input = ""
                    st.rerun()
                st.stop()

        st.markdown('<div id="keypad-marker"></div>', unsafe_allow_html=True)
        
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
    if pd.isna(val) or str(val).strip() == "": return pd.Timestamp.now('Asia/Jakarta').date()
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
    except: return pd.Timestamp.now('Asia/Jakarta').date()

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
            df_transaksi['Tanggal'] = pd.to_datetime(df_transaksi['Tanggal'])
            df_transaksi['Tanggal'] = df_transaksi['Tanggal'].fillna(pd.Timestamp.now('Asia/Jakarta'))
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
            data_yf = yf.download(tks, period="5d", progress=False)
            for t in tks:
                try:
                    cp = float(data_yf['Close'][t].dropna().iloc[-1]) if len(tks) > 1 else float(data_yf['Close'].dropna().iloc[-1])
                    if pd.isna(cp): cp = 0
                    harga_sekarang_dict[t] = cp * kurs if not t.endswith('.JK') else cp
                except Exception: harga_sekarang_dict[t] = 0
    except Exception: pass 

    df_saham['Ticker'] = df_saham['Ticker'].astype(str).str.upper().str.strip()
    df_saham['Jumlah Lembar'] = pd.to_numeric(df_saham['Jumlah Lembar'], errors='coerce').fillna(0)
    df_saham['Harga Beli'] = pd.to_numeric(df_saham['Harga Beli'], errors='coerce').fillna(0)
    df_saham['Total Modal'] = df_saham['Jumlah Lembar'] * df_saham['Harga Beli']
    
    df_saham_agg = df_saham.groupby('Ticker').agg({'Jumlah Lembar': 'sum', 'Total Modal': 'sum'}).reset_index()
    df_saham_agg['Harga Beli Rata-rata'] = df_saham_agg['Total Modal'] / df_saham_agg['Jumlah Lembar']
    df_saham_agg = df_saham_agg[df_saham_agg['Jumlah Lembar'] > 0] 
    
    for _, row in df_saham_agg.iterrows():
        ticker = row['Ticker']
        jumlah = row['Jumlah Lembar']
        harga_beli = row['Harga Beli Rata-rata']
        
        harga_skrg = harga_sekarang_dict.get(ticker, 0)
        if pd.isna(harga_skrg) or harga_skrg == 0: harga_skrg = harga_beli
        total_nilai_saham += (harga_skrg * jumlah)

# ==========================================
# 5. TAMPILAN MENU UTAMA - NEW STRUKTUR TAB
# ==========================================
tab1, tab3, tab4, tab5, tab6 = st.tabs(["🏦 Dashboard Kekayaan", "📈 Portofolio Saham", "🧾 AI Scanner", "⚡ Screener Saham", "⚙️ Pengaturan"])

# ----------------- TAB 1: DASHBOARD KEKAYAAN & CATAT KAS -----------------
with tab1:
    c_btn1, c_btn2, c_btn3 = st.columns([2, 1, 1])
    with c_btn2:
        if st.button("🙈 Tampil/Sembunyi", use_container_width=True):
            st.session_state.hide_balance = not st.session_state.hide_balance
            st.rerun()
    with c_btn3:
        if st.button("🔒 Kunci Aplikasi", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.pin_input = "" 
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
    
    st.markdown('<div class="wallet-container">', unsafe_allow_html=True)
    wc = st.columns(4)
    wallets = [{"name": "BANK BCA", "val": porto["BCA"], "class": "bca-card", "icon": "🏦"}, {"name": "BANK BRI", "val": porto["BRI"], "class": "bri-card", "icon": "🏢"}, {"name": "BANK JAGO", "val": porto["Bank Jago"], "class": "jago-card", "icon": "🦊"}, {"name": "UANG TUNAI", "val": porto["Dompet (Cash)"], "class": "cash-card", "icon": "💵"}]
    for i, w in enumerate(wallets):
        with wc[i]: st.markdown(f'''<div class="wallet-card {w['class']}"><div class="wallet-icon">{w['icon']}</div><div class="wallet-label">{w['name']}</div><div class="wallet-balance">{format_currency(w['val'])}</div></div>''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")

    # Filter Bulan untuk Grafik
    col_f1, col_f2 = st.columns(2)
    nama_bulan = ["Semua Waktu", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    today_indo = pd.Timestamp.now('Asia/Jakarta')
    with col_f1: pilih_bulan = st.selectbox("Pilih Laporan Bulan", nama_bulan, index=today_indo.month)
    with col_f2: pilih_tahun = st.selectbox("Tahun", list(range(2020, today_indo.year + 10)), index=list(range(2020, today_indo.year + 10)).index(today_indo.year))

    df_curr = pd.DataFrame() 
    in_curr, out_curr = 0.0, 0.0
    if not df_transaksi.empty:
        df_calc = df_transaksi.copy()
        df_calc['Jenis'] = df_calc['Jenis'].astype(str).str.strip().str.lower()
        if pilih_bulan == "Semua Waktu":
            df_curr = df_calc.copy()
        else:
            curr_m = nama_bulan.index(pilih_bulan)
            df_curr = df_calc[(df_calc['Tanggal'].dt.month == curr_m) & (df_calc['Tanggal'].dt.year == pilih_tahun)]
            
        in_curr = df_curr[df_curr['Jenis'] == 'pemasukan']['Nominal'].sum()
        out_curr = df_curr[df_curr['Jenis'] == 'pengeluaran']['Nominal'].sum()

    st.markdown("<br>", unsafe_allow_html=True)

    # PEMBAGIAN LAYOUT KIRI DAN KANAN (FORM VS VISUAL)
    col_l, col_r = st.columns([1, 1.5])
    
    with col_l:
        st.subheader("➕ Tambah Transaksi")
        with st.form("trx_form", clear_on_submit=True):
            f_tgl = st.date_input("Tanggal", pd.Timestamp.now('Asia/Jakarta').date())
            f_kat = st.selectbox("Kategori", st.session_state.kategori_list)
            f_jen = st.radio("Jenis", ["Pemasukan", "Pengeluaran"], horizontal=True)
            f_src = st.selectbox("Pilih Dompet", list(porto.keys()))
            
            default_nom = st.session_state.get('auto_nominal', "")
            f_nom_teks = st.text_input("Jumlah Uang (Rp)", value=default_nom, placeholder="Contoh: 50.000")
            
            f_note = st.text_area("Catatan / Rincian", placeholder="Contoh: Modal Awal / Beli Kemeja")
            if st.form_submit_button("SIMPAN SEKARANG"):
                try: f_nom = float(f_nom_teks.replace(".", "").replace(",", "")) if f_nom_teks else 0.0
                except ValueError: f_nom = 0.0
                new_row = pd.DataFrame([{"Tanggal": f_tgl.strftime('%Y-%m-%d'), "Kategori": f_kat, "Jenis": f_jen, "Sumber Dana": f_src, "Nominal": f_nom, "Catatan": f_note}])
                df_updated = pd.concat([df_transaksi, new_row], ignore_index=True)
                df_updated['Tanggal'] = pd.to_datetime(df_updated['Tanggal']).dt.strftime('%Y-%m-%d')
                set_with_dataframe(ws_transaksi, df_updated, row=1)
                if f_jen == "Pemasukan": st.balloons()
                st.session_state.auto_nominal = "" 
                if 'scan_status' in st.session_state: del st.session_state.scan_status
                st.cache_data.clear(); st.rerun()

        # ================= FITUR 3: TRANSAKSI RUTIN 1-KLIK =================
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("⚡ Eksekusi Transaksi Rutin")
        with st.expander("Klik untuk mencatat tagihan bulanan wajib", expanded=False):
            with st.form("rutin_form"):
                st.markdown("Pilih tagihan yang sudah Anda bayar hari ini:")
                rutin_kost = st.checkbox("🏠 Bayar Kost (Rp 400.000)")
                rutin_inet = st.checkbox("🌐 Kuota Internet (Rp 100.000)")
                rutin_kopi = st.checkbox("☕ Kopi 1KG (Rp 200.000)")
                rutin_src = st.selectbox("Bayar Pakai Dompet:", list(porto.keys()))
                
                if st.form_submit_button("LUNASI TAGIHAN TERPILIH"):
                    new_rows = []
                    today_str = pd.Timestamp.now('Asia/Jakarta').strftime('%Y-%m-%d')
                    if rutin_kost: new_rows.append({"Tanggal": today_str, "Kategori": "Bayar Kost", "Jenis": "Pengeluaran", "Sumber Dana": rutin_src, "Nominal": 400000.0, "Catatan": "Auto-Bayar Kost Rutin"})
                    if rutin_inet: new_rows.append({"Tanggal": today_str, "Kategori": "Lainnya", "Jenis": "Pengeluaran", "Sumber Dana": rutin_src, "Nominal": 100000.0, "Catatan": "Auto-Beli Kuota Rutin"})
                    if rutin_kopi: new_rows.append({"Tanggal": today_str, "Kategori": "Lainnya", "Jenis": "Pengeluaran", "Sumber Dana": rutin_src, "Nominal": 200000.0, "Catatan": "Auto-Beli Kopi 1KG Rutin"})
                    
                    if new_rows:
                        df_updated = pd.concat([df_transaksi, pd.DataFrame(new_rows)], ignore_index=True)
                        df_updated['Tanggal'] = pd.to_datetime(df_updated['Tanggal']).dt.strftime('%Y-%m-%d')
                        set_with_dataframe(ws_transaksi, df_updated, row=1)
                        st.success("✅ Tagihan rutin berhasil dilunasi & dicatat!")
                        st.cache_data.clear(); st.rerun()
                    else:
                        st.warning("Harap pilih minimal 1 tagihan untuk dieksekusi.")

    with col_r:
        st.subheader(f"📊 Analisis Visual")
        g1, g2, g3, g4, g5 = st.tabs(["📉 Arus Kas", "🧬 Vitals 50/30/20", "🧛 Top Vampir", "🗓️ Heatmap", "🥧 Aset"])
        
        with g1:
            st.markdown("##### 📈 Cashflow Trendline Harian")
            if not df_curr.empty:
                df_trend = df_curr.copy()
                df_trend['Tgl'] = df_trend['Tanggal'].dt.day
                trend_data = df_trend.groupby(['Tgl', 'Jenis'])['Nominal'].sum().reset_index()
                
                max_day = trend_data['Tgl'].max() if not trend_data.empty else today_indo.day
                all_days = pd.DataFrame({'Tgl': range(1, max_day + 1)})
                
                pemasukan_data = pd.merge(all_days, trend_data[trend_data['Jenis'] == 'pemasukan'], on='Tgl', how='left').fillna({'Nominal': 0, 'Jenis': 'pemasukan'})
                pengeluaran_data = pd.merge(all_days, trend_data[trend_data['Jenis'] == 'pengeluaran'], on='Tgl', how='left').fillna({'Nominal': 0, 'Jenis': 'pengeluaran'})
                final_trend = pd.concat([pemasukan_data, pengeluaran_data])

                fig_trend = px.line(final_trend, x='Tgl', y='Nominal', color='Jenis', 
                                    color_discrete_map={'pemasukan': '#10B981', 'pengeluaran': '#EF4444'}, 
                                    markers=True, template="plotly_dark")
                fig_trend.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=380, margin=dict(l=0, r=0, t=10, b=0),
                                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                fig_trend.update_xaxes(showgrid=False)
                fig_trend.update_yaxes(showgrid=True, gridcolor='#334155')
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("Belum ada data untuk bulan ini.")

        with g2:
            st.markdown("##### 🧬 Analisis Vitals: Aturan 50/30/20")
            if not df_curr.empty and in_curr > 0:
                kebutuhan_list = ['Makan & Minum', 'Bayar Kost', 'Transport', 'Bensin', 'Listrik', 'Internet']
                masa_depan_list = ['Investasi']
                
                pokok = df_curr[(df_curr['Jenis'] == 'pengeluaran') & (df_curr['Kategori'].isin(kebutuhan_list))]['Nominal'].sum()
                masa_depan = df_curr[(df_curr['Jenis'] == 'pengeluaran') & (df_curr['Kategori'].isin(masa_depan_list))]['Nominal'].sum()
                keinginan = out_curr - pokok - masa_depan
                
                p_pokok = min((pokok / in_curr) * 100, 100)
                p_keinginan = min((keinginan / in_curr) * 100, 100)
                p_masa_depan = min((masa_depan / in_curr) * 100, 100)
                
                st.markdown(f'''
                <div style="background:#1E293B; padding:15px; border-radius:12px; border:1px solid #334155; margin-bottom:12px;">
                    <div style="font-size:12px; color:#94A3B8; font-weight:600; margin-bottom:4px;">🏠 KEBUTUHAN POKOK (Ideal: < 50%)</div>
                    <div style="font-size:18px; font-weight:bold; color:#F8FAFC; margin-bottom:8px;">{format_currency(pokok)} <span style="font-size:12px; color:{'#10B981' if p_pokok<=50 else '#EF4444'};">({p_pokok:.1f}%)</span></div>
                    <div style="width:100%;background:#334155;border-radius:10px;height:8px;"><div style="width:{p_pokok}%;background:{'#10B981' if p_pokok<=50 else '#EF4444'};height:8px;border-radius:10px;"></div></div>
                </div>
                
                <div style="background:#1E293B; padding:15px; border-radius:12px; border:1px solid #334155; margin-bottom:12px;">
                    <div style="font-size:12px; color:#94A3B8; font-weight:600; margin-bottom:4px;">🛍️ GAYA HIDUP (Ideal: < 30%)</div>
                    <div style="font-size:18px; font-weight:bold; color:#F8FAFC; margin-bottom:8px;">{format_currency(keinginan)} <span style="font-size:12px; color:{'#10B981' if p_keinginan<=30 else '#EF4444'};">({p_keinginan:.1f}%)</span></div>
                    <div style="width:100%;background:#334155;border-radius:10px;height:8px;"><div style="width:{p_keinginan}%;background:{'#10B981' if p_keinginan<=30 else '#EF4444'};height:8px;border-radius:10px;"></div></div>
                </div>
                
                <div style="background:#1E293B; padding:15px; border-radius:12px; border:1px solid #334155;">
                    <div style="font-size:12px; color:#94A3B8; font-weight:600; margin-bottom:4px;">🌱 MASA DEPAN (Ideal: > 20%)</div>
                    <div style="font-size:18px; font-weight:bold; color:#F8FAFC; margin-bottom:8px;">{format_currency(masa_depan)} <span style="font-size:12px; color:{'#10B981' if p_masa_depan>=20 else '#F59E0B'};">({p_masa_depan:.1f}%)</span></div>
                    <div style="width:100%;background:#334155;border-radius:10px;height:8px;"><div style="width:{p_masa_depan}%;background:{'#10B981' if p_masa_depan>=20 else '#F59E0B'};height:8px;border-radius:10px;"></div></div>
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.info("Catat pemasukan bulan ini terlebih dahulu.")

        with g3:
            st.markdown("##### 🧛‍♂️ Top 3 Vampir Uang (Kategori Terboros)")
            if not df_curr.empty and out_curr > 0:
                top_3 = df_curr[df_curr['Jenis'] == 'pengeluaran'].groupby('Kategori')['Nominal'].sum().nlargest(3).reset_index()
                top_3 = top_3.sort_values('Nominal', ascending=True) 
                fig_top = px.bar(top_3, x='Nominal', y='Kategori', orientation='h', template="plotly_dark", color_discrete_sequence=['#EF4444'])
                fig_top.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0, r=0, t=0, b=0))
                fig_top.update_yaxes(title=None)
                fig_top.update_xaxes(showgrid=False, showticklabels=False, title=None)
                st.plotly_chart(fig_top, use_container_width=True)
            else:
                st.info("Belum ada pengeluaran dicatat.")

        with g4:
            if not df_curr.empty and not df_curr[df_curr['Jenis'] == 'pengeluaran'].empty:
                df_out = df_curr[df_curr['Jenis'] == 'pengeluaran'].copy()
                df_out['Tgl'] = pd.to_datetime(df_out['Tanggal']).dt.day
                daily_spend = df_out.groupby('Tgl')['Nominal'].sum().reset_index()
                
                max_day = daily_spend['Tgl'].max()
                all_days = pd.DataFrame({'Tgl': range(1, max_day + 1)})
                daily_spend = pd.merge(all_days, daily_spend, on='Tgl', how='left').fillna(0)
                
                fig_h = px.bar(daily_spend, x='Tgl', y='Nominal', 
                               labels={'Tgl': 'Tanggal Bulan Ini', 'Nominal': 'Total Pengeluaran (Rp)'},
                               color='Nominal', color_continuous_scale='OrRd')
                fig_h.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=320,
                                    margin=dict(l=10, r=10, t=30, b=10), title="Detektor Pola Kebocoran Dana Harian")
                st.plotly_chart(fig_h, use_container_width=True)
            else:
                st.info("Belum ada rekam jejak pengeluaran untuk mendeteksi pola bulan ini.")
                
        with g5:
            df_p = pd.DataFrame([{"Aset": k, "Nilai": max(0, v)} for k, v in {**porto, "Saham": total_nilai_saham}.items() if v > 0])
            if not df_p.empty:
                fig_p = px.pie(df_p, values='Nilai', names='Aset', hole=0.5, template="plotly_dark", color='Aset', color_discrete_map={'BCA': '#3B82F6', 'BRI': '#F97316', 'Bank Jago': '#F59E0B', 'Dompet (Cash)': '#10B981', 'Saham': '#8B5CF6'})
                fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=320, showlegend=True)
                st.plotly_chart(fig_p, use_container_width=True)

    st.markdown("---")

    # ================= FITUR 1: SISTEM ALARM BUDGET (DINAMIS) =================
    if st.session_state.budgets:
        st.markdown("###### 🚨 Monitor Limit Budget (Bulan Ini)")
        spent = df_curr[df_curr['Jenis'] == 'pengeluaran'].groupby('Kategori')['Nominal'].sum().to_dict() if not df_curr.empty else {}
        
        bc = st.columns(4)
        for i, (kat, limit) in enumerate(st.session_state.budgets.items()):
            terpakai = spent.get(kat, 0.0)
            rasio = min(terpakai / limit, 1.0) if limit > 0 else 1.0
            sisa = limit - terpakai
            color = "#10B981" if rasio < 0.5 else "#F59E0B" if rasio < 0.8 else "#EF4444"
            
            with bc[i % 4]:
                st.markdown(f"<div style='font-size:13px; font-weight:600; color:#94A3B8;'>{kat}</div>", unsafe_allow_html=True)
                bar_html = f'''
                <div style="width: 100%; height: 8px; background-color: #334155; border-radius: 10px; margin: 6px 0;">
                  <div style="width: {rasio*100}%; height: 100%; background-color: {color}; border-radius: 10px; transition: 0.5s;"></div>
                </div>
                '''
                st.markdown(bar_html, unsafe_allow_html=True)
                if sisa >= 0:
                    st.markdown(f"<div style='font-size:12px; color:{color};'>Sisa: {format_currency(sisa)}</div><br>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='font-size:12px; color:#EF4444; font-weight:bold;'>OVER: {format_currency(abs(sisa))}</div><br>", unsafe_allow_html=True)
        st.markdown("---")
    # =================================================================
        
    with st.expander("📋 Tampilkan Seluruh Riwayat Transaksi"):
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


# ----------------- TAB 3: PORTOFOLIO SAHAM -----------------
with tab3:
    st.subheader("💼 Portofolio & Input Saham")
    
    col_port1, col_port2 = st.columns(2)
    with col_port1:
        with st.expander("➕ Tambah Beli Saham", expanded=False):
            with st.form("form_saham_beli", clear_on_submit=True):
                new_ticker = st.text_input("Kode Ticker", help="Akhiri .JK untuk Indonesia").upper()
                new_lot = st.number_input("Jumlah Lot DIBELI", min_value=1, step=1)
                new_harga_teks = st.text_input("Harga Beli (Rp)")
                if st.form_submit_button("SIMPAN PEMBELIAN"):
                    try: new_harga = float(new_harga_teks.replace(".", "").replace(",", "")) if new_harga_teks else 0.0
                    except ValueError: new_harga = 0.0
                    if new_ticker:
                        new_lembar = new_lot * 100
                        df_saham_updated = pd.concat([df_saham, pd.DataFrame([{"Ticker": new_ticker.strip(), "Jumlah Lembar": new_lembar, "Harga Beli": new_harga}])], ignore_index=True)
                        set_with_dataframe(ws_saham, df_saham_updated, row=1)
                        st.success(f"Pembelian {new_ticker} tersimpan!"); st.cache_data.clear(); st.rerun()

    with col_port2:
        with st.expander("➖ Jual / Kurangi Saham", expanded=False):
            if not df_saham_agg.empty:
                with st.form("form_saham_jual", clear_on_submit=True):
                    ticker_jual = st.selectbox("Pilih Saham", df_saham_agg['Ticker'].tolist())
                    lot_jual = st.number_input("Jumlah Lot DIJUAL", min_value=1, step=1)
                    if st.form_submit_button("CATAT PENJUALAN"):
                        lembar_jual = lot_jual * 100
                        df_saham_updated = pd.concat([df_saham, pd.DataFrame([{"Ticker": ticker_jual, "Jumlah Lembar": -lembar_jual, "Harga Beli": 0}])], ignore_index=True)
                        set_with_dataframe(ws_saham, df_saham_updated, row=1)
                        st.success(f"Penjualan {ticker_jual} tersimpan!"); st.cache_data.clear(); st.rerun()
            else:
                st.info("Portofolio masih kosong.")

    if not df_saham_agg.empty:
        rows, pie_data_saham = [], []
        for _, r in df_saham_agg.iterrows():
            t = str(r.get('Ticker', '')).upper()
            harga_beli = float(r.get('Harga Beli Rata-rata', 0))
            lembar = float(r.get('Jumlah Lembar', 0))
            harga_skrg = harga_sekarang_dict.get(t, harga_beli)
            gain = ((harga_skrg - harga_beli) / harga_beli) * 100 if harga_beli > 0 else 0.0
            total_nilai = harga_skrg * lembar
            
            gain_str = f"{gain:.2f}%"
            if gain > 0: gain_html = f'<span style="color:#10B981; font-weight:800;">▲ {gain_str}</span>'
            elif gain < 0: gain_html = f'<span style="color:#EF4444; font-weight:800;">▼ {gain_str}</span>'
            else: gain_html = f'<span style="color:#94A3B8;">{gain_str}</span>'

            rows.append({
                "Kode Saham": f"<b>{t}</b>", 
                "Total Lot": f"{lembar/100:.0f} Lot", 
                "Avg Beli": format_currency(harga_beli), 
                "Harga Skrg": format_currency(harga_skrg), 
                "Keuntungan (%)": gain_html,
                "_raw_gain": gain_str 
            })
            if total_nilai > 0: pie_data_saham.append({"Ticker": t, "Nilai": total_nilai})
            
        if rows:
            df_tampil = pd.DataFrame(rows)
            df_html_saham = df_tampil.drop(columns=['_raw_gain'])
            render_beautiful_table(df_html_saham)
            
            df_csv = df_tampil.drop(columns=['Keuntungan (%)']).rename(columns={'_raw_gain': 'Keuntungan (%)'})
            df_csv['Kode Saham'] = df_csv['Kode Saham'].str.replace('<b>', '').str.replace('</b>', '')
            
            col_sd1, col_sd2 = st.columns([1, 1])
            with col_sd1: st.download_button("📥 Download Portofolio", data=df_csv.to_csv(index=False).encode('utf-8'), file_name="Portofolio_ROGER.csv", mime="text/csv")
            with col_sd2:
                with st.expander("📊 Lihat Alokasi Sektoral Saham"):
                    if pie_data_saham:
                        fig_saham = px.pie(pd.DataFrame(pie_data_saham), values='Nilai', names='Ticker', hole=0.4, template="plotly_dark")
                        fig_saham.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(t=10, b=10, l=10, r=10))
                        st.plotly_chart(fig_saham, use_container_width=True)
        else:
             st.info("Semua saham telah dijual.")
             
    st.markdown("---")
    
    # KEMBALI FITUR AI PREDIKSI KE SINI
    st.subheader("📈 Analisis Pergerakan Saham Pro + Prediksi AI 🤖")
    target = st.text_input("Ketik Kode Ticker:", "BBCA.JK").upper()
    try:
        h = yf.Ticker(target).history(period="6mo")
        if not h.empty:
            h.index = h.index.tz_localize(None)
            fig_h = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], name='Harga Asli')])
            if len(h) >= 50:
                h['SMA_20'], h['SMA_50'] = ta.sma(h['Close'], length=20), ta.sma(h['Close'], length=50)
                fig_h.add_trace(go.Scatter(x=h.index, y=h['SMA_20'], line=dict(color='#38BDF8', width=2), name='SMA 20'))
                fig_h.add_trace(go.Scatter(x=h.index, y=h['SMA_50'], line=dict(color='#F59E0B', width=2), name='SMA 50'))
                
                df_ml = h[['Close']].copy()
                df_ml['Hari_Ke'] = np.arange(len(df_ml))
                model = LinearRegression().fit(df_ml[['Hari_Ke']], df_ml['Close'])
                hari_terakhir = df_ml['Hari_Ke'].max()
                future_dates = pd.bdate_range(start=h.index[-1] + timedelta(days=1), periods=7)
                y_pred_future = model.predict(pd.DataFrame({'Hari_Ke': np.arange(hari_terakhir + 1, hari_terakhir + 8)}))
                
                fig_h.add_trace(go.Scatter(x=[h.index[-1]] + list(future_dates), y=[df_ml['Close'].iloc[-1]] + list(y_pred_future), mode='lines+markers', line=dict(color='#8B5CF6', width=3, dash='dot'), name='Prediksi AI (7 Hari)'))

            fig_h.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', height=450, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_h, use_container_width=True)
            c_rsi, c_info = st.columns([1, 2])
            with c_rsi:
                if len(h) >= 15: st.metric("Skor RSI-14", f"{ta.rsi(h['Close'], length=14).iloc[-1]:.2f}")
            with c_info: st.info("🤖 **JARINGAN SARAF TIRUAN AKTIF:** Garis putus-putus *Ungu* di ujung grafik adalah proyeksi matematis Machine Learning untuk harga saham 7 hari ke depan.")
    except Exception: st.error("Gagal memuat grafik.")

# ----------------- TAB 4: AI SMART SCANNER -----------------
with tab4:
    st.subheader("🧾 AI Smart Extractor (Auto-Fill)")
    st.markdown("Unggah struk belanja Anda. AI akan mencari total belanja dan mengisinya otomatis ke form transaksi di Tab Dashboard Kekayaan!")
    
    if "scan_status" in st.session_state:
        status, val, raw_text = st.session_state.scan_status
        if status == "success":
            st.success("✨ Pindaian Selesai!")
            st.metric("💰 Total Ditemukan", format_currency(val))
            st.info("✅ **Angka berhasil disalin!** Silakan pindah ke Tab **🏦 Dashboard Kekayaan**, kolom Nominal sudah terisi otomatis.")
            with st.expander("🔍 Lihat Teks Mentah (Raw OCR)"):
                st.text_area("Teks dari Gambar:", raw_text, height=150)
        elif status == "fail":
            st.warning("⚠️ AI tidak dapat menemukan angka total yang valid. Silakan input manual.")
            with st.expander("🔍 Lihat Teks Mentah (Raw OCR)"):
                st.text_area("Teks dari Gambar:", raw_text, height=150)

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
                            
                            if total_akhir > 0:
                                st.session_state.auto_nominal = f"{total_akhir:,.0f}".replace(",", ".")
                                st.session_state.scan_status = ("success", total_akhir, res)
                            else:
                                st.session_state.scan_status = ("fail", 0, res)
                            st.rerun() 
                    except Exception as e: 
                        st.error(f"Error OCR: Pastikan file packages.txt sudah berisi 'tesseract-ocr'. Detail error: {e}")

# ----------------- TAB 5: LIVE SCREENER -----------------
with tab5:
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
                                news_data = ticker_obj.news
                                if isinstance(news_data, list) and len(news_data) > 0:
                                    for artikel in news_data[:3]:
                                        raw_title = artikel.get('title')
                                        if raw_title and raw_title.lower() != 'none':
                                            judul = str(raw_title).strip().replace('[', '').replace(']', '')
                                            link = artikel.get('link', '#')
                                            publisher = artikel.get('publisher', '').strip()
                                            list_berita.append(f"- [{judul}]({link}) *({publisher})*" if publisher else f"- [{judul}]({link})")
                            except Exception: pass
                            
                            teks_berita = "\n\n".join(list_berita) if list_berita else "_Tidak ada berita yang tersedia saat ini._"

                            if is_buy or len(tickers) == 1: 
                                rekomendasi_beli.append({
                                    "Ticker": ticker, "Harga": close_price, "Target": target_naik, "SL": stop_loss, 
                                    "Alasan": "\n\n".join(alasan), "Kesimpulan": status_akhir, "Berita": teks_berita, "df_chart": df_hist.tail(90)
                                })
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
                            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Harga', increasing_line_color='#10B981', decreasing_line_color='#EF4444'))
                            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA_20'], line=dict(color='#38BDF8', width=2), name='MA 20'))
                            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA_50'], line=dict(color='#F59E0B', width=2), name='MA 50'))
                            fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
                            st.plotly_chart(fig, use_container_width=True)
                            
                            col_info1, col_info2 = st.columns([1.2, 1])
                            with col_info1: st.info(f"**🧠 Analisis:**\n\n{rec['Alasan']}")
                            with col_info2: st.warning(f"**📰 Berita Terkini:**\n\n{rec['Berita']}")
                            st.markdown("---")
                
                with st.expander("Lihat Saham Lainnya (Kondisi Sedang Jelek / Sideways)"):
                    if netral_jual: 
                        df_netral = pd.DataFrame(netral_jual)
                        df_netral['Status'] = df_netral['Status'].apply(lambda x: f'<span style="color:#F59E0B; font-weight:800;">{x}</span>')
                        render_beautiful_table(df_netral)
            except Exception as e: st.error(f"Kesalahan: {e}")

# ----------------- TAB 6: PENGATURAN SISTEM -----------------
with tab6:
    st.subheader("⚙️ Pengaturan Sistem & Kendali")
    col_set1, col_set2, col_set3 = st.columns(3)
    
    with col_set1:
        with st.expander("🏷️ Kelola Kategori Transaksi", expanded=True):
            new_kat = st.text_input("Kategori Baru", placeholder="Contoh: Bensin")
            if st.button("➕ Tambah Kategori", use_container_width=True):
                if new_kat and new_kat not in st.session_state.kategori_list:
                    st.session_state.kategori_list.append(new_kat)
                    save_config()
                    st.success(f"Kategori '{new_kat}' ditambahkan!")
                    st.rerun()
                elif new_kat in st.session_state.kategori_list:
                    st.warning("Kategori sudah ada.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            kat_hapus = st.selectbox("Pilih kategori untuk dihapus", st.session_state.kategori_list)
            if st.button("❌ Hapus Kategori", use_container_width=True):
                if len(st.session_state.kategori_list) > 1:
                    st.session_state.kategori_list.remove(kat_hapus)
                    save_config()
                    st.success(f"Kategori {kat_hapus} dihapus!")
                    st.rerun()
                else:
                    st.error("Minimal tersisa 1 kategori!")
                    
    with col_set2:
        with st.expander("🚨 Atur Limit Alarm Budget", expanded=True):
            kategori_budget = st.selectbox("Pilih Kategori", st.session_state.kategori_list)
            limit_baru = st.number_input("Limit (Rp)", min_value=0, step=50000, value=500000)
            if st.button("💾 Simpan Limit", use_container_width=True):
                st.session_state.budgets[kategori_budget] = limit_baru
                save_config()
                st.success(f"Limit disimpan!")
                st.rerun()
                
            st.markdown("<br>", unsafe_allow_html=True)
            if st.session_state.budgets:
                budget_hapus = st.selectbox("Matikan Alarm untuk", list(st.session_state.budgets.keys()))
                if st.button("❌ Matikan Alarm Ini", use_container_width=True):
                    del st.session_state.budgets[budget_hapus]
                    save_config()
                    st.success("Alarm dimatikan!")
                    st.rerun()
            else:
                st.info("Belum ada alarm aktif.")
                
    with col_set3:
        with st.expander("🔐 Ganti PIN Rahasia", expanded=True):
            old_pin = st.text_input("PIN Lama", type="password", max_chars=6)
            new_pin = st.text_input("PIN Baru (6 Angka)", type="password", max_chars=6)
            if st.button("Ubah PIN Sekarang", use_container_width=True):
                if old_pin == st.session_state.saved_pin:
                    if len(new_pin) == 6 and new_pin.isdigit():
                        st.session_state.saved_pin = new_pin
                        save_config()
                        st.success("✅ PIN diubah!")
                    else:
                        st.error("Gagal! PIN baru harus 6 angka.")
                else:
                    st.error("Gagal! PIN Lama salah.")
