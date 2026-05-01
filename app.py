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
import gspread
import re
import numpy as np
from sklearn.linear_model import LinearRegression
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# ==========================================
# 1. KONFIGURASI HALAMAN & INGATAN APLIKASI
# ==========================================
st.set_page_config(page_title="ROGER-Finance Pro", page_icon="💼", layout="wide", initial_sidebar_state="expanded")

if 'hide_balance' not in st.session_state:
    st.session_state.hide_balance = False

# INGATAN DINAMIS UNTUK BUDGET, KATEGORI, DAN PIN
if 'budgets' not in st.session_state:
    st.session_state.budgets = {"Makan & Minum": 1500000, "Belanja": 1000000, "Transport": 500000, "Parfum": 500000}
if 'kategori_list' not in st.session_state:
    st.session_state.kategori_list = ["Gaji", "Makan & Minum", "Belanja", "Transport", "Investasi", "Parfum", "Bayar Kost", "Skincare", "Lainnya"]
if 'saved_pin' not in st.session_state:
    st.session_state.saved_pin = "120224"

def format_currency(value):
    if st.session_state.hide_balance:
        return "Rp ••••••••"
    return f"Rp {value:,.0f}".replace(",", ".")

def render_beautiful_table(df):
    html_table = df.to_html(classes='custom-table', index=False, escape=False)
    st.markdown(f'<div class="table-wrapper">{html_table}</div>', unsafe_allow_html=True)

# ==========================================
# 2. DESAIN "EXECUTIVE SLATE" (UI/UX PROFESIONAL)
# ==========================================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    header, footer {visibility: hidden !important;}
    
    /* Background & Base */
    .stApp, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif !important;
        background-color: #0f172a !important; /* Dark Slate */
        color: #f8fafc !important;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid #334155 !important;
    }

    /* Minimalist Title */
    .new-title-style {
        font-size: 2.2rem; font-weight: 800;
        padding-top: 10px; margin-bottom: 5px;
        color: #f8fafc; letter-spacing: -0.5px;
    }
    
    /* Executive Cards */
    .exec-card {
        background-color: #1e293b;
        border-radius: 12px;
        padding: 24px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 20px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .exec-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        border-color: #475569;
    }
    
    .card-title { font-size: 0.85rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;}
    .card-value { font-size: 1.8rem; font-weight: 800; color: #f8fafc; margin-bottom: 4px; }
    
    /* Specific accents */
    .accent-emerald { border-top: 4px solid #10b981; }
    .accent-blue { border-top: 4px solid #3b82f6; }
    .accent-orange { border-top: 4px solid #f59e0b; }
    .accent-rose { border-top: 4px solid #e11d48; }

    /* Tables */
    .table-wrapper {
        background-color: #1e293b; border-radius: 12px; border: 1px solid #334155;
        overflow: hidden; margin-bottom: 20px;
    }
    .custom-table { width: 100%; border-collapse: collapse; color: #e2e8f0; font-size: 0.9rem; text-align: left; }
    .custom-table thead th { background: #0f172a; padding: 14px 16px; font-weight: 600; color: #94a3b8; border-bottom: 1px solid #334155; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.5px;}
    .custom-table td { padding: 14px 16px; border-bottom: 1px solid #334155; }
    .custom-table tbody tr:hover td { background-color: #334155; }

    /* Buttons */
    .stButton button {
        background-color: #3b82f6 !important; color: #ffffff !important;
        font-weight: 600 !important; border-radius: 8px !important;
        border: none !important; padding: 12px 24px !important; transition: all 0.2s !important;
    }
    .stButton button:hover { background-color: #2563eb !important; transform: scale(1.02); }
    
    /* Inputs */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
        background-color: #0f172a !important; border: 1px solid #334155 !important; 
        border-radius: 8px !important; color: white !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: #3b82f6 !important; box-shadow: 0 0 0 1px #3b82f6 !important;
    }
    
    /* Radio/Segmented Control */
    div[role="radiogroup"] > label {
        background-color: #1e293b !important; border: 1px solid #334155 !important;
        padding: 10px 20px !important; border-radius: 8px !important;
    }
    div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #3b82f6 !important; border-color: #3b82f6 !important;
    }

    [data-testid="stDecoration"] { display: none; }
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
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        div[data-testid="stHorizontalBlock"] button { height: 70px !important; font-size: 24px !important; border-radius: 12px !important; background-color: #1e293b !important; border: 1px solid #334155 !important;}
        div[data-testid="stHorizontalBlock"] button:hover { background-color: #334155 !important; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<br><br><br>", unsafe_allow_html=True) 
    col_kiri, col_tengah, col_kanan = st.columns([1, 1.2, 1])
    
    with col_tengah:
        st.markdown('<p class="new-title-style" style="text-align:center;">ROGER Finance</p>', unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94A3B8; margin-bottom: 30px; font-size: 0.9rem;'>Sistem Manajemen Kekayaan Pribadi</p>", unsafe_allow_html=True)
        
        pin_length = len(st.session_state.pin_input)
        dots_html = '<div style="display: flex; justify-content: center; gap: 15px; margin-bottom: 40px;">'
        for i in range(6):
            if i < pin_length:
                dots_html += '<div style="width: 16px; height: 16px; border-radius: 50%; background-color: #3b82f6; box-shadow: 0 0 8px #3b82f6;"></div>'
            else:
                dots_html += '<div style="width: 16px; height: 16px; border-radius: 50%; background-color: #1e293b; border: 2px solid #334155;"></div>'
        dots_html += '</div>'
        st.markdown(dots_html, unsafe_allow_html=True)
        
        if pin_length == 6:
            if st.session_state.pin_input == st.session_state.saved_pin: 
                st.session_state.authenticated = True
                st.session_state.pin_input = "" 
                st.rerun() 
            else:
                st.error("❌ PIN Salah. Silakan coba lagi.")
                if st.button("Ulangi", use_container_width=True):
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

# ==========================================
# 3. KONEKSI & MESIN PEMBERSIH
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
    st.error("Gagal terhubung ke Database. Periksa konfigurasi st.secrets.")
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
    st.error(f"Gagal memuat data: {e}")
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
# SIDEBAR NAVIGATION (ENTERPRISE LAYOUT)
# ==========================================
with st.sidebar:
    st.markdown("<h3 style='color:#f8fafc; font-weight:800; margin-bottom: 20px;'>💼 ROGER Finance</h3>", unsafe_allow_html=True)
    
    # Action Buttons Mini
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("👁️ Tampil/Sembunyi", help="Tampilkan atau sembunyikan nominal saldo"):
            st.session_state.hide_balance = not st.session_state.hide_balance
            st.rerun()
    with c_btn2:
        if st.button("🔒 Lock App", help="Kunci kembali aplikasi"):
            st.session_state.authenticated = False
            st.session_state.pin_input = "" 
            st.rerun()
            
    st.markdown("<hr style='border-color: #334155; margin: 15px 0;'>", unsafe_allow_html=True)
    
    menu_selection = st.radio(
        "Menu Utama",
        ["📊 Dashboard Kekayaan", "📝 Catat Arus Kas", "💼 Portofolio Saham", "🧾 AI Smart Scanner", "⚡ Live Screener", "⚙️ Pengaturan Sistem"],
        label_visibility="collapsed"
    )
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.caption("Version 2.0 - Executive Build")


# ==========================================
# PAGE ROUTING (BASED ON SIDEBAR SELECTION)
# ==========================================

# ----------------- PAGE: DASHBOARD KEKAYAAN -----------------
if menu_selection == "📊 Dashboard Kekayaan":
    st.markdown("<p class='new-title-style'>Ringkasan Eksekutif</p>", unsafe_allow_html=True)
    
    total_net = sum(porto.values()) + total_nilai_saham
    
    # ROW 1: Target Harta
    st.markdown("##### 🎯 Target Portofolio")
    target_teks = st.text_input("Target Finansial (Rp)", value="100.000.000", label_visibility="collapsed")
    try: target_harta = float(target_teks.replace(".", "").replace(",", ""))
    except ValueError: target_harta = 100000000.0 
    rasio = total_net / target_harta if target_harta > 0 else 0.0
    st.progress(max(0.0, min(rasio, 1.0)))
    st.caption(f"Tercapai: **{max(0.0, min(rasio, 1.0))*100:.1f}%** dari {format_currency(target_harta)}")
    
    # ROW 2: Wallet Cards
    w1, w2, w3, w4 = st.columns(4)
    with w1: st.markdown(f'''<div class="exec-card accent-emerald"><div class="card-title">Harta Bersih</div><div class="card-value">{format_currency(total_net)}</div></div>''', unsafe_allow_html=True)
    with w2: st.markdown(f'''<div class="exec-card accent-blue"><div class="card-title">Aset Saham</div><div class="card-value">{format_currency(total_nilai_saham)}</div></div>''', unsafe_allow_html=True)
    with w3: st.markdown(f'''<div class="exec-card accent-blue"><div class="card-title">Saldo Bank (BCA+BRI+JAGO)</div><div class="card-value">{format_currency(porto["BCA"]+porto["BRI"]+porto["Bank Jago"])}</div></div>''', unsafe_allow_html=True)
    with w4: st.markdown(f'''<div class="exec-card accent-orange"><div class="card-title">Uang Tunai</div><div class="card-value">{format_currency(porto["Dompet (Cash)"])}</div></div>''', unsafe_allow_html=True)

    # Filter Bulan
    today_indo = pd.Timestamp.now('Asia/Jakarta')
    nama_bulan = ["Semua Waktu", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    
    col_f1, col_f2, _, _ = st.columns(4)
    with col_f1: pilih_bulan = st.selectbox("Laporan Bulan", nama_bulan, index=today_indo.month)
    with col_f2: pilih_tahun = st.selectbox("Tahun", list(range(2020, today_indo.year + 10)), index=list(range(2020, today_indo.year + 10)).index(today_indo.year))

    df_curr = pd.DataFrame() 
    in_curr, out_curr = 0.0, 0.0
    if not df_transaksi.empty:
        df_calc = df_transaksi.copy()
        df_calc['Jenis'] = df_calc['Jenis'].astype(str).str.strip().str.lower()
        if pilih_bulan == "Semua Waktu": df_curr = df_calc.copy()
        else:
            curr_m = nama_bulan.index(pilih_bulan)
            df_curr = df_calc[(df_calc['Tanggal'].dt.month == curr_m) & (df_calc['Tanggal'].dt.year == pilih_tahun)]
        in_curr = df_curr[df_curr['Jenis'] == 'pemasukan']['Nominal'].sum()
        out_curr = df_curr[df_curr['Jenis'] == 'pengeluaran']['Nominal'].sum()

    # ROW 3: Visual Analytics (70% Trendline, 30% 50/30/20)
    col_chart, col_health = st.columns([7, 3])
    
    with col_chart:
        st.markdown("<h4 style='font-size:1.1rem; font-weight:700;'>📈 Cashflow Trendline Harian</h4>", unsafe_allow_html=True)
        if not df_curr.empty:
            df_trend = df_curr.copy()
            df_trend['Tgl'] = df_trend['Tanggal'].dt.day
            trend_data = df_trend.groupby(['Tgl', 'Jenis'])['Nominal'].sum().reset_index()
            # Pisahkan data untuk mengisi hari yang kosong
            max_day = trend_data['Tgl'].max() if not trend_data.empty else today_indo.day
            all_days = pd.DataFrame({'Tgl': range(1, max_day + 1)})
            
            pemasukan_data = pd.merge(all_days, trend_data[trend_data['Jenis'] == 'pemasukan'], on='Tgl', how='left').fillna({'Nominal': 0, 'Jenis': 'pemasukan'})
            pengeluaran_data = pd.merge(all_days, trend_data[trend_data['Jenis'] == 'pengeluaran'], on='Tgl', how='left').fillna({'Nominal': 0, 'Jenis': 'pengeluaran'})
            final_trend = pd.concat([pemasukan_data, pengeluaran_data])

            fig_trend = px.line(final_trend, x='Tgl', y='Nominal', color='Jenis', 
                                color_discrete_map={'pemasukan': '#10b981', 'pengeluaran': '#f43f5e'}, 
                                markers=True, template="plotly_dark")
            fig_trend.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=380, margin=dict(l=0, r=0, t=10, b=0),
                                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig_trend.update_xaxes(showgrid=False)
            fig_trend.update_yaxes(showgrid=True, gridcolor='#334155')
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Belum ada data untuk bulan ini.")

    with col_health:
        st.markdown("<h4 style='font-size:1.1rem; font-weight:700;'>🧬 Analisis 50/30/20</h4>", unsafe_allow_html=True)
        if not df_curr.empty and in_curr > 0:
            kebutuhan_list = ['Makan & Minum', 'Bayar Kost', 'Transport', 'Bensin', 'Listrik', 'Internet']
            masa_depan_list = ['Investasi']
            
            pokok = df_curr[(df_curr['Jenis'] == 'pengeluaran') & (df_curr['Kategori'].isin(kebutuhan_list))]['Nominal'].sum()
            masa_depan = df_curr[(df_curr['Jenis'] == 'pengeluaran') & (df_curr['Kategori'].isin(masa_depan_list))]['Nominal'].sum()
            keinginan = out_curr - pokok - masa_depan
            
            p_pokok = min((pokok / in_curr) * 100, 100)
            p_keinginan = min((keinginan / in_curr) * 100, 100)
            p_masa_depan = min((masa_depan / in_curr) * 100, 100)
            
            # Draw custom mini cards
            st.markdown(f'''
            <div style="background:#1e293b; padding:15px; border-radius:8px; border:1px solid #334155; margin-bottom:10px;">
                <div style="font-size:0.8rem; color:#94a3b8; font-weight:600; margin-bottom:5px;">🏠 KEBUTUHAN (Max 50%)</div>
                <div style="font-size:1.1rem; font-weight:bold; color:#f8fafc; margin-bottom:8px;">{format_currency(pokok)} <span style="font-size:0.8rem; color:{'#10b981' if p_pokok<=50 else '#f43f5e'};">({p_pokok:.1f}%)</span></div>
                <div style="width:100%;background:#334155;border-radius:10px;height:6px;"><div style="width:{p_pokok}%;background:{'#10b981' if p_pokok<=50 else '#f43f5e'};height:6px;border-radius:10px;"></div></div>
            </div>
            
            <div style="background:#1e293b; padding:15px; border-radius:8px; border:1px solid #334155; margin-bottom:10px;">
                <div style="font-size:0.8rem; color:#94a3b8; font-weight:600; margin-bottom:5px;">🛍️ GAYA HIDUP (Max 30%)</div>
                <div style="font-size:1.1rem; font-weight:bold; color:#f8fafc; margin-bottom:8px;">{format_currency(keinginan)} <span style="font-size:0.8rem; color:{'#10b981' if p_keinginan<=30 else '#f43f5e'};">({p_keinginan:.1f}%)</span></div>
                <div style="width:100%;background:#334155;border-radius:10px;height:6px;"><div style="width:{p_keinginan}%;background:{'#10b981' if p_keinginan<=30 else '#f43f5e'};height:6px;border-radius:10px;"></div></div>
            </div>
            
            <div style="background:#1e293b; padding:15px; border-radius:8px; border:1px solid #334155;">
                <div style="font-size:0.8rem; color:#94a3b8; font-weight:600; margin-bottom:5px;">🌱 INVESTASI (Min 20%)</div>
                <div style="font-size:1.1rem; font-weight:bold; color:#f8fafc; margin-bottom:8px;">{format_currency(masa_depan)} <span style="font-size:0.8rem; color:{'#10b981' if p_masa_depan>=20 else '#f59e0b'};">({p_masa_depan:.1f}%)</span></div>
                <div style="width:100%;background:#334155;border-radius:10px;height:6px;"><div style="width:{p_masa_depan}%;background:{'#10b981' if p_masa_depan>=20 else '#f59e0b'};height:6px;border-radius:10px;"></div></div>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.info("Catat pemasukan bulan ini untuk melihat rasio kesehatan keuangan.")

    # ROW 4: Alarm Budget & Top Vampires
    st.markdown("<br>", unsafe_allow_html=True)
    col_alarm, col_vampire = st.columns([6, 4])
    
    with col_alarm:
        st.markdown("<h4 style='font-size:1.1rem; font-weight:700;'>🚨 Alarm Status Budget</h4>", unsafe_allow_html=True)
        if st.session_state.budgets:
            spent = df_curr[df_curr['Jenis'] == 'pengeluaran'].groupby('Kategori')['Nominal'].sum().to_dict() if not df_curr.empty else {}
            
            bc = st.columns(3) # 3 columns for budgets to fit nicely
            for i, (kat, limit) in enumerate(st.session_state.budgets.items()):
                terpakai = spent.get(kat, 0.0)
                rasio = min(terpakai / limit, 1.0) if limit > 0 else 1.0
                sisa = limit - terpakai
                color = "#10b981" if rasio < 0.5 else "#f59e0b" if rasio < 0.8 else "#e11d48"
                
                with bc[i % 3]:
                    st.markdown(f'''
                    <div style="background:#1e293b; padding:15px; border-radius:8px; border:1px solid #334155; margin-bottom:15px;">
                        <div style="font-size:0.85rem; font-weight:bold; color:#f8fafc; margin-bottom:5px;">{kat}</div>
                        <div style="width:100%;background:#334155;border-radius:10px;height:6px;margin-bottom:8px;"><div style="width:{rasio*100}%;background:{color};height:6px;border-radius:10px;"></div></div>
                        <div style="font-size:0.75rem; color:{color}; font-weight:600;">{'Sisa: '+format_currency(sisa) if sisa>=0 else 'OVER: '+format_currency(abs(sisa))}</div>
                    </div>
                    ''', unsafe_allow_html=True)
        else:
            st.info("Tidak ada alarm aktif.")
            
    with col_vampire:
        st.markdown("<h4 style='font-size:1.1rem; font-weight:700;'>🧛‍♂️ Top 3 Pengeluaran</h4>", unsafe_allow_html=True)
        if not df_curr.empty and out_curr > 0:
            top_3 = df_curr[df_curr['Jenis'] == 'pengeluaran'].groupby('Kategori')['Nominal'].sum().nlargest(3).reset_index()
            top_3 = top_3.sort_values('Nominal', ascending=True) 
            fig_top = px.bar(top_3, x='Nominal', y='Kategori', orientation='h', template="plotly_dark", color_discrete_sequence=['#f43f5e'])
            fig_top.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=220, margin=dict(l=0, r=0, t=0, b=0))
            fig_top.update_yaxes(title=None)
            fig_top.update_xaxes(showgrid=False, showticklabels=False, title=None)
            st.plotly_chart(fig_top, use_container_width=True)
        else:
            st.info("Belum ada pengeluaran dicatat.")

    # Expandable Transaction History
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
            st.download_button("📥 Download Data Excel", data=df_transaksi.to_csv(index=False).encode('utf-8'), file_name="Riwayat_Transaksi_ROGER.csv", mime="text/csv")


# ----------------- PAGE: CATAT ARUS KAS -----------------
elif menu_selection == "📝 Catat Arus Kas":
    st.markdown("<p class='new-title-style'>Pencatatan Keuangan</p>", unsafe_allow_html=True)
    
    col_input1, col_input2 = st.columns([1.2, 1])
    
    with col_input1:
        st.markdown("<div class='exec-card accent-emerald'>", unsafe_allow_html=True)
        st.markdown("#### ➕ Form Transaksi Manual")
        with st.form("trx_form", clear_on_submit=True):
            f_tgl = st.date_input("Tanggal Transaksi", pd.Timestamp.now('Asia/Jakarta').date())
            f_kat = st.selectbox("Kategori", st.session_state.kategori_list)
            f_jen = st.radio("Jenis Arus Kas", ["Pemasukan", "Pengeluaran"], horizontal=True)
            f_src = st.selectbox("Pilih Sumber Dompet", list(porto.keys()))
            
            default_nom = st.session_state.get('auto_nominal', "")
            f_nom_teks = st.text_input("Jumlah Uang (Rp)", value=default_nom, placeholder="Contoh: 50.000")
            
            f_note = st.text_area("Catatan / Rincian", placeholder="Contoh: Gaji bulanan / Beli makan siang")
            if st.form_submit_button("SIMPAN TRANSAKSI SEKARANG"):
                try: f_nom = float(f_nom_teks.replace(".", "").replace(",", "")) if f_nom_teks else 0.0
                except ValueError: f_nom = 0.0
                new_row = pd.DataFrame([{"Tanggal": f_tgl.strftime('%Y-%m-%d'), "Kategori": f_kat, "Jenis": f_jen, "Sumber Dana": f_src, "Nominal": f_nom, "Catatan": f_note}])
                df_updated = pd.concat([df_transaksi, new_row], ignore_index=True)
                df_updated['Tanggal'] = pd.to_datetime(df_updated['Tanggal']).dt.strftime('%Y-%m-%d')
                set_with_dataframe(ws_transaksi, df_updated, row=1)
                st.session_state.auto_nominal = "" 
                if 'scan_status' in st.session_state: del st.session_state.scan_status
                st.success("✅ Transaksi berhasil dicatat!")
                st.cache_data.clear()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_input2:
        st.markdown("<div class='exec-card accent-blue'>", unsafe_allow_html=True)
        st.markdown("#### ⚡ Eksekusi Tagihan Rutin")
        st.caption("Pilih tagihan wajib yang sudah Anda bayar hari ini.")
        with st.form("rutin_form"):
            rutin_kost = st.checkbox("🏠 Bayar Kost (Rp 400.000)")
            rutin_inet = st.checkbox("🌐 Kuota Internet (Rp 100.000)")
            rutin_kopi = st.checkbox("☕ Kopi 1KG (Rp 200.000)")
            
            st.markdown("<br>", unsafe_allow_html=True)
            rutin_src = st.selectbox("Bayar Menggunakan Dompet:", list(porto.keys()))
            
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
        st.markdown("</div>", unsafe_allow_html=True)


# ----------------- PAGE: PORTOFOLIO SAHAM -----------------
elif menu_selection == "💼 Portofolio Saham":
    st.markdown("<p class='new-title-style'>Manajemen Portofolio Saham</p>", unsafe_allow_html=True)
    
    # Forms in single row
    col_port1, col_port2 = st.columns(2)
    with col_port1:
        st.markdown("<div class='exec-card accent-emerald'>", unsafe_allow_html=True)
        st.markdown("#### ➕ Tambah Beli Saham")
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
        st.markdown("</div>", unsafe_allow_html=True)

    with col_port2:
        st.markdown("<div class='exec-card accent-orange'>", unsafe_allow_html=True)
        st.markdown("#### ➖ Jual / Kurangi Saham")
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
            st.info("Portofolio masih kosong. Belum ada saham yang bisa dijual.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("#### 📋 Daftar Aset Saat Ini")
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
            if gain > 0: gain_html = f'<span style="color:#10b981; font-weight:800;">▲ {gain_str}</span>'
            elif gain < 0: gain_html = f'<span style="color:#f43f5e; font-weight:800;">▼ {gain_str}</span>'
            else: gain_html = f'<span style="color:#94a3b8;">{gain_str}</span>'

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
            
            col_sd1, col_sd2 = st.columns([1, 1.5])
            with col_sd1:
                df_csv = df_tampil.drop(columns=['Keuntungan (%)']).rename(columns={'_raw_gain': 'Keuntungan (%)'})
                df_csv['Kode Saham'] = df_csv['Kode Saham'].str.replace('<b>', '').str.replace('</b>', '')
                st.download_button("📥 Download Portofolio CSV", data=df_csv.to_csv(index=False).encode('utf-8'), file_name="Portofolio_ROGER.csv", mime="text/csv")
            with col_sd2:
                with st.expander("📊 Lihat Chart Alokasi Sektoral Saham"):
                    if pie_data_saham:
                        fig_saham = px.pie(pd.DataFrame(pie_data_saham), values='Nilai', names='Ticker', hole=0.4, template="plotly_dark")
                        fig_saham.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(t=10, b=10, l=10, r=10))
                        st.plotly_chart(fig_saham, use_container_width=True)


# ----------------- PAGE: AI SMART SCANNER -----------------
elif menu_selection == "🧾 AI Smart Scanner":
    st.markdown("<p class='new-title-style'>AI Smart Scanner OCR</p>", unsafe_allow_html=True)
    st.markdown("Unggah struk belanja atau invoice. AI akan membaca teks dalam gambar, mencari total tagihan, dan menyiapkannya untuk diisi otomatis di form **Catat Kas**.")
    
    if "scan_status" in st.session_state:
        status, val, raw_text = st.session_state.scan_status
        if status == "success":
            st.success("✨ Pindaian Berhasil!")
            st.metric("💰 Total Terdeteksi", format_currency(val))
            st.info("✅ **Angka berhasil disalin ke memori!** Silakan buka menu **📝 Catat Arus Kas**, kolom nominal sudah terisi otomatis.")
            with st.expander("🔍 Lihat Hasil Teks Mentah (Raw OCR)"):
                st.text_area("Teks dari Gambar:", raw_text, height=150)
        elif status == "fail":
            st.warning("⚠️ AI tidak dapat menemukan format angka total yang valid. Silakan input manual.")
            with st.expander("🔍 Lihat Hasil Teks Mentah (Raw OCR)"):
                st.text_area("Teks dari Gambar:", raw_text, height=150)

    st.markdown("<div class='exec-card accent-blue'>", unsafe_allow_html=True)
    up = st.file_uploader("Upload Foto Struk / Nota (JPG/PNG)", type=["jpg", "png", "jpeg"])
    if up:
        col_img, col_res = st.columns([1, 1.5])
        with col_img:
            st.image(Image.open(up), use_container_width=True, caption="Pratinjau Nota")
            
        with col_res:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if st.button("🧠 EKSTRAK TOTAL & AUTO-FILL TRANSAKSI", use_container_width=True):
                with st.spinner("AI sedang memindai piksel gambar dan mencari angka..."):
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
                        st.error(f"Error AI Processing: Pastikan server mendukung library Tesseract OCR. Detail error: {e}")
    st.markdown("</div>", unsafe_allow_html=True)


# ----------------- PAGE: LIVE SCREENER -----------------
elif menu_selection == "⚡ Live Screener":
    st.markdown("<p class='new-title-style'>Live Market Screener & Prediksi AI</p>", unsafe_allow_html=True)
    
    st.markdown("<div class='exec-card accent-emerald'>", unsafe_allow_html=True)
    watchlist_input = st.text_area("Masukkan Daftar Ticker Saham (Dipisahkan koma):", value="GOTO.JK, BUMI.JK, BBCA.JK, PNLF.JK, BMRI.JK")
    max_price = st.number_input("Batas Harga Maksimal Saham (Opsional, 0 untuk abaikan)", value=0)

    if st.button("🚀 MULAI DEEP SCAN TIKER TERPILIH", use_container_width=True):
        with st.spinner("Mengunduh ribuan baris data grafik & memproses model Machine Learning..."):
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
                            if rsi_14 < 35: alasan.append(f"📉 **RSI (Oversold):** Skor {rsi_14:.1f} (Peluang Beli)"); is_buy = True
                            elif 35 <= rsi_14 <= 70: alasan.append(f"⚖️ **RSI (Netral):** Skor {rsi_14:.1f}")
                            if ma20 > ma50: alasan.append(f"📈 **MA (Uptrend):** MA20 memotong MA50 ke atas."); is_buy = True
                            if macd_line > macd_signal and macd_hist > 0: alasan.append(f"📊 **MACD (Bullish):** Histogram Hijau, momentum beli kuat."); is_buy = True
                            if ada_lonjakan_volume: alasan.append(f"🔥 **Volume:** Ledakan {vol_today/vol_avg_20:.1f}x dari rata-rata 20 hari."); is_buy = True
                            
                            if rsi_14 >= 70: is_buy, status_akhir = False, "🔴 OVERBOUGHT / JUAL"
                            elif ada_lonjakan_volume and (ma20 > ma50 or (macd_line > macd_signal and macd_hist > 0)): status_akhir = "🟢 STRONG BUY"
                            elif is_buy: status_akhir = "🟢 CICIL BELI"
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
                            
                            teks_berita = "\n\n".join(list_berita) if list_berita else "_Data sentimen berita tidak tersedia saat ini._"

                            if is_buy or len(tickers) == 1: 
                                # Tambahkan ML linear reg
                                df_ml = df_hist[['Close']].copy()
                                df_ml['Hari_Ke'] = np.arange(len(df_ml))
                                model = LinearRegression().fit(df_ml[['Hari_Ke']], df_ml['Close'])
                                hari_terakhir = df_ml['Hari_Ke'].max()
                                future_dates = pd.bdate_range(start=df_hist.index[-1] + timedelta(days=1), periods=7)
                                y_pred_future = model.predict(pd.DataFrame({'Hari_Ke': np.arange(hari_terakhir + 1, hari_terakhir + 8)}))

                                rekomendasi_beli.append({
                                    "Ticker": ticker, "Harga": close_price, "Target": target_naik, "SL": stop_loss, 
                                    "Alasan": "\n\n".join(alasan), "Kesimpulan": status_akhir, "Berita": teks_berita, 
                                    "df_chart": df_hist.tail(90), "pred_dates": future_dates, "pred_y": y_pred_future
                                })
                            else: 
                                netral_jual.append({"Ticker": ticker, "Harga": format_currency(close_price), "Status": status_akhir})
                    except Exception: pass 
                
                if rekomendasi_beli:
                    st.success(f"🎯 PEMINDAIAN ALGORITMA SELESAI!")
                    for rec in rekomendasi_beli:
                        st.markdown(f"<div class='exec-card accent-blue'>", unsafe_allow_html=True)
                        st.markdown(f"<h3 style='margin-bottom:0;'>🏷️ {rec['Ticker']} <span style='font-size:1.2rem; color:#94a3b8;'>(Rp {rec['Harga']:,.0f})</span></h3>", unsafe_allow_html=True)
                        
                        col_t1, col_t2, col_t3 = st.columns(3)
                        h_aman = rec['Harga'] if rec['Harga'] > 0 else 1
                        col_t1.markdown(f"**STATUS:** {rec['Kesimpulan']}")
                        col_t2.markdown(f"**🎯 Target:** {format_currency(rec['Target'])} (+{((rec['Target'] - rec['Harga']) / h_aman) * 100:.1f}%)")
                        col_t3.markdown(f"**🛡️ Stop Loss:** {format_currency(rec['SL'])} ({((rec['SL'] - rec['Harga']) / h_aman) * 100:.1f}%)")
                        
                        df_plot = rec['df_chart']
                        fig = go.Figure()
                        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Realisasi Harga'))
                        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA_20'], line=dict(color='#3b82f6', width=2), name='MA 20'))
                        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA_50'], line=dict(color='#f59e0b', width=2), name='MA 50'))
                        fig.add_trace(go.Scatter(x=[df_plot.index[-1]] + list(rec['pred_dates']), y=[df_plot['Close'].iloc[-1]] + list(rec['pred_y']), mode='lines+markers', line=dict(color='#10b981', width=3, dash='dot'), name='AI Forecast 7 Hari'))
                        
                        fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=380, margin=dict(l=0, r=0, t=20, b=0), xaxis_rangeslider_visible=False)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        col_info1, col_info2 = st.columns([1.5, 1])
                        with col_info1: 
                            st.markdown("**🧠 Logika Analisis AI:**")
                            st.info(rec['Alasan'])
                        with col_info2: 
                            st.markdown("**📰 Sentimen Berita Global:**")
                            st.warning(rec['Berita'])
                        st.markdown("</div>", unsafe_allow_html=True)
                
                if netral_jual:
                    with st.expander("Lihat Saham Tertahan (Kondisi Sideways/Jelek)"):
                        df_netral = pd.DataFrame(netral_jual)
                        df_netral['Status'] = df_netral['Status'].apply(lambda x: f'<span style="color:#f59e0b; font-weight:800;">{x}</span>')
                        render_beautiful_table(df_netral)
            except Exception as e: st.error(f"Kesalahan Proses: {e}")
    st.markdown("</div>", unsafe_allow_html=True)


# ----------------- PAGE: PENGATURAN SISTEM -----------------
elif menu_selection == "⚙️ Pengaturan Sistem":
    st.markdown("<p class='new-title-style'>Pengaturan Sistem Induk</p>", unsafe_allow_html=True)
    
    col_set1, col_set2 = st.columns(2)
    
    with col_set1:
        st.markdown("<div class='exec-card accent-emerald'>", unsafe_allow_html=True)
        st.markdown("#### 🏷️ Master Kategori Transaksi")
        st.caption("Kelola kategori kas agar laporan visual Anda rapi.")
        new_kat = st.text_input("Buat Kategori Baru", placeholder="Contoh: Belanja Online")
        if st.button("➕ Tambah Ke Database", use_container_width=True):
            if new_kat and new_kat not in st.session_state.kategori_list:
                st.session_state.kategori_list.append(new_kat)
                st.success(f"Kategori '{new_kat}' berhasil ditambahkan!")
                st.rerun()
            elif new_kat in st.session_state.kategori_list:
                st.warning("Kategori sudah terdaftar.")
        
        st.markdown("<hr style='border-color: #334155;'>", unsafe_allow_html=True)
        kat_hapus = st.selectbox("Hapus Kategori Lama", st.session_state.kategori_list)
        if st.button("❌ Eksekusi Hapus", use_container_width=True):
            if len(st.session_state.kategori_list) > 1:
                st.session_state.kategori_list.remove(kat_hapus)
                st.success(f"Kategori {kat_hapus} telah dihapus!")
                st.rerun()
            else:
                st.error("Gagal: Sistem membutuhkan minimal 1 kategori!")
        st.markdown("</div>", unsafe_allow_html=True)
                    
    with col_set2:
        st.markdown("<div class='exec-card accent-rose'>", unsafe_allow_html=True)
        st.markdown("#### 🚨 Manajemen Alarm Budget")
        st.caption("Atur limit maksimal belanja bulanan. Alarm akan muncul di Dashboard.")
        kategori_budget = st.selectbox("Pilih Kategori untuk Dilimit", st.session_state.kategori_list)
        limit_baru = st.number_input("Limit Maksimal (Rp)", min_value=0, step=50000, value=500000)
        if st.button("💾 Simpan Limit/Update", use_container_width=True):
            st.session_state.budgets[kategori_budget] = limit_baru
            st.success(f"Limit berhasil diterapkan pada kategori {kategori_budget}.")
            st.rerun()
            
        st.markdown("<hr style='border-color: #334155;'>", unsafe_allow_html=True)
        if st.session_state.budgets:
            budget_hapus = st.selectbox("Cabut Alarm Budget", list(st.session_state.budgets.keys()))
            if st.button("❌ Matikan Alarm Ini", use_container_width=True):
                del st.session_state.budgets[budget_hapus]
                st.success("Alarm berhasil dicabut!")
                st.rerun()
        else:
            st.info("Semua alarm sedang tidak aktif.")
        st.markdown("</div>", unsafe_allow_html=True)
                
    st.markdown("<div class='exec-card accent-blue'>", unsafe_allow_html=True)
    st.markdown("#### 🔐 Kredensial & Autentikasi")
    st.caption("Ubah PIN login 6 digit Anda di sini untuk menjaga keamanan data.")
    c_pin1, c_pin2 = st.columns(2)
    with c_pin1: old_pin = st.text_input("PIN Konfirmasi (Lama)", type="password", max_chars=6)
    with c_pin2: new_pin = st.text_input("Masukkan PIN Baru (Wajib 6 Angka)", type="password", max_chars=6)
    
    if st.button("PERBARUI PIN SEKARANG", use_container_width=True):
        if old_pin == st.session_state.saved_pin:
            if len(new_pin) == 6 and new_pin.isdigit():
                st.session_state.saved_pin = new_pin
                st.success("✅ Autentikasi diperbarui! Silakan gunakan PIN baru untuk login selanjutnya.")
            else:
                st.error("Gagal! Format PIN baru harus murni 6 angka tanpa karakter khusus.")
        else:
            st.error("Gagal! PIN lama yang Anda masukkan tidak cocok dengan sistem.")
    st.markdown("</div>", unsafe_allow_html=True)
