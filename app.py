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
import re
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# ==========================================
# 1. KONFIGURASI HALAMAN & INGATAN APLIKASI
# ==========================================
st.set_page_config(page_title="ROGER-Finance", page_icon="💎", layout="wide")

if 'hide_balance' not in st.session_state:
    st.session_state.hide_balance = False

def format_currency(value):
    if st.session_state.hide_balance:
        return "Rp ••••••••"
    return f"Rp {value:,.0f}"

# ==========================================
# 2. DESAIN PREMIUM LIGHT MODE (CSS)
# ==========================================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800;900&display=swap');
    footer {visibility: hidden;}
    
    /* 1. ANIMATED BACKGROUND (Putih Mutiara Berjalan) */
    @keyframes gradientMove {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    [data-testid="stAppViewContainer"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        /* Gradien Elegan Terang */
        background: linear-gradient(-45deg, #F8FAFC, #F1F5F9, #EBEFF5, #FFFFFF);
        background-size: 400% 400%;
        animation: gradientMove 15s ease infinite;
        color: #0F172A; /* Teks berubah jadi gelap */
    }
    
    /* Judul Aplikasi */
    .title-glow {
        font-size: clamp(35px, 8vw, 60px); font-weight: 900;
        background: linear-gradient(135deg, #D4AF37 0%, #AA771C 50%, #FF8C00 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; padding-top: 15px;
        filter: drop-shadow(0px 4px 8px rgba(212, 175, 55, 0.2));
        letter-spacing: -1.5px;
    }
    
    /* Tab Menu Custom */
    [data-testid="stTabs"] button[data-baseweb="tab"] {
        background-color: transparent; border-radius: 50px; margin-right: 10px;
        padding: 10px 24px; font-weight: 600; color: #64748B;
        border: 1px solid rgba(0,0,0,0.1); transition: all 0.3s ease;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"]:hover {
        background-color: rgba(0, 0, 0, 0.05); color: #0F172A;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #D4AF37 0%, #AA771C 100%);
        color: #FFFFFF; border: none; box-shadow: 0 5px 15px rgba(212, 175, 55, 0.3);
    }
    [data-testid="stTabs"] div[data-baseweb="tab-list"] { gap: 10px; padding-bottom: 5px; }
    [data-testid="stTabs"] div[data-baseweb="tab-highlight"] { display: none; }

    /* KARTU SALDO (Light Glassmorphism) */
    .wallet-container {
        display: flex; gap: 20px; overflow-x: auto; padding: 15px 10px 40px 10px; scrollbar-width: none;
    }
    .wallet-container::-webkit-scrollbar { display: none; }
    
    .wallet-card {
        min-width: 270px; padding: 25px; border-radius: 24px;
        /* Kaca putih transparan */
        background: rgba(255, 255, 255, 0.7); 
        backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 1); 
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
        position: relative; overflow: hidden; transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
    }
    .wallet-card:hover {
        transform: translateY(-10px) scale(1.02); 
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(212, 175, 55, 0.4);
    }
    .wallet-card::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 5px; }
    .bca-card::before { background: linear-gradient(90deg, #0066AE, #00B4DB); }
    .bri-card::before { background: linear-gradient(90deg, #F26522, #f5af19); }
    .jago-card::before { background: linear-gradient(90deg, #F4A300, #ffe259); }
    .cash-card::before { background: linear-gradient(90deg, #11998e, #38ef7d); }
    
    .wallet-icon { font-size: 32px; margin-bottom: 15px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1)); }
    .wallet-label { font-size: 11px; font-weight: 800; color: #64748B; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; }
    .wallet-balance { font-size: 28px; font-weight: 900; color: #0F172A; letter-spacing: -0.5px; } /* Angka hitam */

    /* EFEK METRIK KEKAYAAN (Teks Gelap) */
    @keyframes pulseGlowLight {
        0% { text-shadow: 0 0 10px rgba(212, 175, 55, 0.1); }
        50% { text-shadow: 0 0 20px rgba(212, 175, 55, 0.4), 0 0 10px rgba(212, 175, 55, 0.2); }
        100% { text-shadow: 0 0 10px rgba(212, 175, 55, 0.1); }
    }
    div[data-testid="metric-container"]:nth-child(1) [data-testid="stMetricValue"] {
        background: linear-gradient(to right, #AA771C, #D4AF37); /* Emas lebih pekat untuk light mode */
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        animation: pulseGlowLight 3s infinite alternate;
    }
    [data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: 900 !important; color: #0F172A !important; } 
    [data-testid="stMetricLabel"] { font-size: 0.95rem !important; font-weight: 600 !important; color: #475569 !important; letter-spacing: 0.5px; text-transform: uppercase; }

    /* TOMBOL & INPUT (Gaya Mewah) */
    .stButton button {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%) !important; color: #D4AF37 !important;
        font-weight: 800 !important; letter-spacing: 1px !important; border-radius: 16px !important;
        border: none !important; padding: 20px !important; transition: all 0.4s ease !important;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1) !important;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #D4AF37 0%, #AA771C 100%) !important; color: #FFFFFF !important;
        transform: translateY(-3px); box-shadow: 0 15px 25px rgba(212, 175, 55, 0.3) !important;
    }
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
        background-color: rgba(255, 255, 255, 0.8) !important; 
        border: 1px solid rgba(0, 0, 0, 0.1) !important; 
        border-radius: 12px !important; color: #0F172A !important;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.02) !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border: 1px solid #D4AF37 !important; box-shadow: 0 0 10px rgba(212, 175, 55, 0.2) !important; background-color: #FFFFFF !important;
    }

    @media (max-width: 768px) {
        div[data-testid="column"] { min-width: 100% !important; } .wallet-card { min-width: 85vw; }
        [data-testid="stTabs"] button[data-baseweb="tab"] { width: 100%; text-align: center; margin-bottom: 5px; }
        [data-testid="stTabs"] div[data-baseweb="tab-list"] { flex-direction: column; }
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

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
    except Exception as e: 
        return None

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
    
    # Hapus koma desimal ke belakang (contoh: 1.000,00 -> 1.000)
    if ',' in v and len(v.split(',')[-1]) <= 2: 
        v = v.split(',')[0] 
    
    # Hapus semua titik (contoh: 1.058.049 -> 1058049)
    v = v.replace('.', '').replace(' ', '')
    
    # Ekstrak hanya angka murni
    bersih = re.sub(r'[^\d]', '', v)
    try: return float(bersih) if bersih else 0.0
    except: return 0.0

def bersihkan_tanggal_indo(val):
    if pd.isna(val) or str(val).strip() == "": return pd.to_datetime(date.today())
    d_str = str(val).split(' ')[0].strip() # Ambil cuma tanggalnya, buang jam 0:00:00
    
    try:
        if '/' in d_str:
            parts = d_str.split('/')
            if len(parts) == 3:
                # Secara paksa mengurutkan Format Indonesia DD/MM/YYYY
                if len(parts[2]) == 4: return pd.to_datetime(f"{parts[2]}-{parts[1]}-{parts[0]}") 
                if len(parts[0]) == 4: return pd.to_datetime(f"{parts[0]}-{parts[1]}-{parts[2]}") 
        elif '-' in d_str:
            parts = d_str.split('-')
            if len(parts) == 3:
                if len(parts[0]) == 4: return pd.to_datetime(d_str) 
                if len(parts[2]) == 4: return pd.to_datetime(f"{parts[2]}-{parts[1]}-{parts[0]}") 
        
        # Fallback terakhir
        return pd.to_datetime(d_str, dayfirst=True, errors='coerce')
    except:
        return pd.to_datetime(date.today())

try:
    ws_transaksi = db.worksheet("Transaksi")
    ws_saham = db.worksheet("Saham")
    df_t_raw, df_s_raw = load_data_from_sheets()
    df_transaksi = df_t_raw.copy()
    df_saham = df_s_raw.copy()
    
    # TERAPKAN MESIN PEMBERSIH KEPADA DATA MENTAH
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
            if s in porto: 
                porto[s] += n if j.lower() == "pemasukan" else -n
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
            for _, row in df_saham.iterrows():
                ticker = str(row.get('Ticker', '')).upper().strip()
                jumlah = float(row.get('Jumlah Lembar', 0))
                harga_beli = float(row.get('Harga Beli', 0))
                harga_skrg = harga_sekarang_dict.get(ticker, 0)
                if pd.isna(harga_skrg) or harga_skrg == 0: harga_skrg = harga_beli
                total_nilai_saham += (harga_skrg * jumlah)
    except Exception: pass

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
    target_teks = st.text_input("Atur Target Finansial Anda (Rp)", value="100.000.000", help="Bebas ketik menggunakan titik", label_visibility="collapsed")
    try: target_harta = float(target_teks.replace(".", "").replace(",", ""))
    except ValueError: target_harta = 100000000.0 

    rasio = total_net / target_harta if target_harta > 0 else 0.0
    progress_val = max(0.0, min(rasio, 1.0)) 
    st.progress(progress_val)
    st.caption(f"Tercapai: **{progress_val*100:.1f}%** dari target {format_currency(target_harta)}")
    st.markdown("---")

    m1, m2, m3 = st.columns(3)
    m1.metric("🌟 TOTAL HARTA BERSIH", format_currency(total_net))
    m2.metric("💵 TOTAL UANG TUNAI", format_currency(sum(porto.values())))
    m3.metric("📈 TOTAL NILAI SAHAM", format_currency(total_nilai_saham))
    st.markdown("---")
    
    st.markdown("###### 📅 Filter Laporan Arus Kas & Grafik")
    col_f1, col_f2 = st.columns(2)
    nama_bulan = ["Semua Waktu", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    
    today = date.today()
    with col_f1:
        pilih_bulan = st.selectbox("Pilih Bulan / Tampilan", nama_bulan, index=today.month)
    with col_f2:
        list_tahun = list(range(2020, today.year + 10))
        pilih_tahun = st.selectbox("Pilih Tahun", list_tahun, index=list_tahun.index(today.year))

    in_curr, out_curr, in_prev, out_prev = 0.0, 0.0, 0.0, 0.0
    df_curr = pd.DataFrame() 

    if not df_transaksi.empty:
        df_calc = df_transaksi.copy()
        df_calc['Jenis'] = df_calc['Jenis'].astype(str).str.strip().str.lower()
        
        if pilih_bulan == "Semua Waktu":
            df_curr = df_calc.copy()
            in_curr = df_curr[df_curr['Jenis'] == 'pemasukan']['Nominal'].sum()
            out_curr = df_curr[df_curr['Jenis'] == 'pengeluaran']['Nominal'].sum()
            in_prev, out_prev = 0.0, 0.0
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

    sisa_curr = in_curr - out_curr
    sisa_prev = in_prev - out_prev

    def calc_delta(curr, prev):
        if pilih_bulan == "Semua Waktu": return None
        if prev == 0 and curr > 0: return "100% (Bulan lalu Rp 0)"
        if prev == 0 and curr <= 0: return "0%"
        return f"{((curr - prev) / prev) * 100:+.1f}% vs Bulan Lalu"

    st.markdown(f"<br><h6>📊 Rangkuman Kas: {judul_lap}</h6>", unsafe_allow_html=True)
    cm1, cm2, cm3 = st.columns(3)
    cm1.metric(f"Pemasukan", format_currency(in_curr), delta=calc_delta(in_curr, in_prev), delta_color="normal")
    cm2.metric(f"Pengeluaran", format_currency(out_curr), delta=calc_delta(out_curr, out_prev), delta_color="inverse")
    cm3.metric(f"Sisa Uang", format_currency(sisa_curr), delta=calc_delta(sisa_curr, sisa_prev), delta_color="normal")
    st.markdown("---")

    st.markdown('<div class="wallet-container">', unsafe_allow_html=True)
    wc = st.columns(4)
    wallets = [{"name": "BANK CENTRAL ASIA", "val": porto["BCA"], "class": "bca-card", "icon": "🏦"}, {"name": "BANK RAKYAT INDONESIA", "val": porto["BRI"], "class": "bri-card", "icon": "🏢"}, {"name": "BANK JAGO DIGITAL", "val": porto["Bank Jago"], "class": "jago-card", "icon": "🦊"}, {"name": "UANG TUNAI (DOMPET)", "val": porto["Dompet (Cash)"], "class": "cash-card", "icon": "💵"}]
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
            f_nom_teks = st.text_input("Jumlah Uang (Rp)", placeholder="Contoh: 50.000")
            f_note = st.text_area("Catatan / Rincian", placeholder="Contoh: Beli kemeja")
            if st.form_submit_button("SIMPAN SEKARANG"):
                try: f_nom = float(f_nom_teks.replace(".", "").replace(",", "")) if f_nom_teks else 0.0
                except ValueError: f_nom = 0.0
                
                new_row = pd.DataFrame([{"Tanggal": f_tgl.strftime('%Y-%m-%d'), "Kategori": f_kat, "Jenis": f_jen, "Sumber Dana": f_src, "Nominal": f_nom, "Catatan": f_note}])
                df_updated = pd.concat([df_transaksi, new_row], ignore_index=True)
                
                df_updated['Tanggal'] = pd.to_datetime(df_updated['Tanggal']).dt.strftime('%Y-%m-%d')
                
                set_with_dataframe(ws_transaksi, df_updated, row=1)
                if f_jen == "Pemasukan": st.balloons()
                st.cache_data.clear()
                st.rerun()

    with col_r:
        st.subheader(f"📊 Analisis Visual ({judul_lap})")
        g1, g2, g3 = st.tabs(["Arus Kas", "Pembagian Aset", "Rincian Pengeluaran"])
        with g1:
            if not df_curr.empty:
                df_grouped = df_curr.groupby('Jenis')['Nominal'].sum().reset_index()
                df_grouped['Jenis'] = df_grouped['Jenis'].str.title() 
                fig = px.bar(df_grouped, x='Jenis', y='Nominal', color='Jenis', template="plotly_dark", color_discrete_map={'Pemasukan':'#2ecc71', 'Pengeluaran':'#e74c3c'})
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
                fig.update_traces(hovertemplate='<b>%{x}</b><br>Nominal: Rp %{y:,.0f}<extra></extra>')
                fig.update_yaxes(tickformat=",.0f")
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("Belum ada data.")
        with g2:
            df_p = pd.DataFrame([{"Aset": k, "Nilai": v} for k, v in {**porto, "Saham": total_nilai_saham}.items() if v > 0])
            if not df_p.empty:
                asset_color_map = {'BCA': '#0066AE', 'BRI': '#F26522', 'Bank Jago': '#F4A300', 'Dompet (Cash)': '#27AE60', 'Saham': '#8E44AD'}
                fig_p = px.pie(df_p, values='Nilai', names='Aset', hole=0.5, template="plotly_dark", color='Aset', color_discrete_map=asset_color_map)
                fig_p.update_traces(hovertemplate='<b>%{label}</b><br>Total: Rp %{value:,.0f}<extra></extra>')
                fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=320, showlegend=True)
                st.plotly_chart(fig_p, use_container_width=True)
        with g3:
            if not df_curr.empty:
                df_pengeluaran = df_curr[df_curr['Jenis'] == 'pengeluaran']
                if not df_pengeluaran.empty:
                    df_kat = df_pengeluaran.groupby('Kategori')['Nominal'].sum().reset_index()
                    fig_kat = px.pie(df_kat, values='Nominal', names='Kategori', hole=0.4, template="plotly_dark")
                    fig_kat.update_traces(textposition='inside', textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Total: Rp %{value:,.0f}<extra></extra>')
                    fig_kat.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=320, showlegend=False)
                    st.plotly_chart(fig_kat, use_container_width=True)
                else: st.info("Belum ada pengeluaran.")

    st.subheader("📋 Riwayat Transaksi Lengkap")
    if not df_transaksi.empty:
        df_display = df_transaksi.copy()
        df_display['Tanggal'] = df_display['Tanggal'].dt.strftime('%Y-%m-%d')
        
        # --- PERBAIKAN RESET INDEX DI SINI ---
        df_display = df_display.sort_values(by='Tanggal', ascending=False)
        df_display = df_display.reset_index(drop=True) # Menghapus ID urutan lama
        df_display.index = df_display.index + 1 # Memaksa nomor baris dimulai dari 1
        
        st.dataframe(df_display, use_container_width=True, height=250)
        csv_trx = df_transaksi.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel/CSV Transaksi", data=csv_trx, file_name="Riwayat_Transaksi_ROGER.csv", mime="text/csv")

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
                    new_stock_data = pd.DataFrame([{"Ticker": new_ticker.strip(), "Jumlah Lembar": new_lembar, "Harga Beli": new_harga}])
                    df_saham_updated = pd.concat([df_saham, new_stock_data], ignore_index=True)
                    set_with_dataframe(ws_saham, df_saham_updated, row=1)
                    st.success(f"Tersimpan: {new_ticker}!")
                    st.cache_data.clear()
                    st.rerun()

    if not df_saham.empty:
        rows, pie_data_saham = [], []
        for _, r in df_saham.iterrows():
            t, harga_beli, lembar = str(r.get('Ticker', '')).upper(), float(r.get('Harga Beli', 0)), float(r.get('Jumlah Lembar', 0))
            harga_skrg = harga_sekarang_dict.get(t, 0)
            if pd.isna(harga_skrg) or harga_skrg == 0: harga_skrg = harga_beli
            gain = ((harga_skrg - harga_beli) / harga_beli) * 100 if harga_beli > 0 else 0.0
            total_nilai = harga_skrg * lembar
            rows.append({"Kode Saham": t, "Total Lot": f"{lembar/100:.0f} Lot", "Harga Beli": format_currency(harga_beli), "Harga Sekarang": format_currency(harga_skrg), "Keuntungan (%)": f"{gain:.2f}%"})
            if total_nilai > 0: pie_data_saham.append({"Ticker": t, "Nilai": total_nilai})
        df_tampil_saham = pd.DataFrame(rows)
        st.dataframe(df_tampil_saham, use_container_width=True)
        col_sd1, col_sd2 = st.columns([1, 1])
        with col_sd1: st.download_button("📥 Download Portofolio", data=df_tampil_saham.to_csv(index=False).encode('utf-8'), file_name="Portofolio_ROGER.csv", mime="text/csv")
        with col_sd2:
            with st.expander("📊 Lihat Alokasi Saham"):
                if pie_data_saham:
                    fig_saham = px.pie(pd.DataFrame(pie_data_saham), values='Nilai', names='Ticker', hole=0.4, template="plotly_dark")
                    fig_saham.update_traces(textposition='inside', textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Total: Rp %{value:,.0f}<extra></extra>')
                    fig_saham.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_saham, use_container_width=True)
        
    st.markdown("---")
    st.subheader("📈 Analisis Pergerakan Saham Pro")
    target = st.text_input("Ketik Kode Ticker:", "BBCA.JK").upper()
    try:
        h = yf.Ticker(target).history(period="6mo")
        if not h.empty:
            fig_h = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], name='Harga')])
            if len(h) >= 50:
                h['SMA_20'], h['SMA_50'] = ta.sma(h['Close'], length=20), ta.sma(h['Close'], length=50)
                fig_h.add_trace(go.Scatter(x=h.index, y=h['SMA_20'], line=dict(color='#3498db', width=2), name='SMA 20 (Tren Cepat)'))
                fig_h.add_trace(go.Scatter(x=h.index, y=h['SMA_50'], line=dict(color='#f1c40f', width=2), name='SMA 50 (Tren Menengah)'))
            fig_h.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', height=450, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_h, use_container_width=True)
            c_rsi, c_info = st.columns([1, 2])
            with c_rsi:
                if len(h) >= 15: st.metric("Skor RSI-14", f"{ta.rsi(h['Close'], length=14).iloc[-1]:.2f}")
            with c_info: st.info("💡 Jika Garis Biru memotong Kuning ke atas = Sinyal Uptrend (Golden Cross).")
    except Exception: st.error("Gagal memuat grafik.")

with tab3:
    st.subheader("🧾 Scan Nota Otomatis (Robot AI)")
    up = st.file_uploader("Upload Foto Nota", type=["jpg", "png", "jpeg"])
    if up:
        img = Image.open(up)
        st.image(img, use_container_width=True)
        if st.button("MULAI BACA NOTA", use_container_width=True):
            try:
                res = pytesseract.image_to_string(img)
                if res.strip(): st.text_area("Hasil Teks:", res, height=300)
            except Exception: st.error("Error OCR.")

with tab4:
    st.subheader("⚡ Live Market Screener & Charting Pro")
    st.markdown("Pindai pasar untuk mencari saham potensial. Dilengkapi **Grafik Interaktif**, **Bedah Analisis Teknikal**, dan **Sentimen Berita Terkini**.")
    
    col_sc1, col_sc2 = st.columns([2, 1])
    with col_sc1: 
        watchlist_input = st.text_area("Daftar Ticker (Ketik 1 atau banyak saham, pisahkan dengan koma):", value="GOTO.JK, BUMI.JK, BBCA.JK, PNLF.JK")
    with col_sc2:
        st.markdown("<br>", unsafe_allow_html=True)
        max_price = st.number_input("Batas Harga Maksimal (Opsional, Rp)", value=0)

    if st.button("MULAI SCAN & ANALISA GRAFIK", use_container_width=True):
        with st.spinner("Mengunduh data grafik, menganalisis teknikal, dan mencari berita terbaru..."):
            try:
                tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]
                rekomendasi_beli, netral_jual = [], []
                
                for ticker in tickers:
                    try:
                        ticker_obj = yf.Ticker(ticker)
                        df_hist = ticker_obj.history(period="6mo")
                        
                        if len(df_hist) >= 50: 
                            close_price = float(df_hist['Close'].iloc[-1])
                            if max_price > 0 and close_price > max_price: continue 
                                
                            # 1. Kalkulasi Indikator Teknikal
                            df_hist['SMA_20'] = ta.sma(df_hist['Close'], length=20)
                            df_hist['SMA_50'] = ta.sma(df_hist['Close'], length=50)
                            df_hist['RSI_14'] = ta.rsi(df_hist['Close'], length=14)
                            
                            macd_df = ta.macd(df_hist['Close'])
                            macd_line = float(macd_df.iloc[-1, 0])     
                            macd_hist = float(macd_df.iloc[-1, 1])     
                            macd_signal = float(macd_df.iloc[-1, 2])   
                            
                            ma20 = float(df_hist['SMA_20'].iloc[-1])
                            ma50 = float(df_hist['SMA_50'].iloc[-1])
                            rsi_14 = float(df_hist['RSI_14'].iloc[-1])
                            
                            vol_avg_20 = float(df_hist['Volume'][-20:].mean())
                            vol_today = float(df_hist['Volume'].iloc[-1])
                            ada_lonjakan_volume = vol_today > (vol_avg_20 * 1.5) 
                            
                            target_naik = float(df_hist['High'][-40:].max())
                            if target_naik <= close_price * 1.02: target_naik = close_price * 1.12 
                            stop_loss = float(df_hist['Low'][-20:].min())
                            if stop_loss >= close_price * 0.98: stop_loss = close_price * 0.95
                            
                            alasan = []
                            is_buy = False
                            
                            if rsi_14 < 35:
                                alasan.append(f"📉 **RSI (Jenuh Jual/Oversold):** Skor {rsi_14:.1f}. Harga sangat murah (diskon).")
                                is_buy = True
                            elif 35 <= rsi_14 <= 70:
                                alasan.append(f"⚖️ **RSI (Netral):** Skor {rsi_14:.1f}. Momentum harga sedang stabil.")
                            
                            if ma20 > ma50:
                                alasan.append(f"📈 **MA (Uptrend/Golden Cross):** Garis MA20 di atas MA50. Tren naik terkonfirmasi.")
                                is_buy = True
                            elif close_price > ma20:
                                alasan.append(f"🚀 **MA (Breakout Pendek):** Harga menembus MA20. Daya beli mulai melawan.")
                                is_buy = True
                                
                            if macd_line > macd_signal and macd_hist > 0:
                                alasan.append(f"📊 **MACD (Bullish Convergence):** Momentum beli kuat, MACD memotong sinyal ke atas.")
                                is_buy = True
                            elif macd_line < macd_signal:
                                alasan.append(f"⚠️ **MACD (Bearish Divergence):** Tekanan turun masih ada.")
                                
                            if ada_lonjakan_volume:
                                alasan.append(f"🔥 **Volume (Akumulasi Bandar):** Lonjakan {vol_today/vol_avg_20:.1f}x lipat dari rata-rata.")
                                is_buy = True
                            
                            if rsi_14 >= 70:
                                is_buy = False 
                                status_akhir = "🔴 JUAL / HINDARI DULU (Harga sudah Overbought)"
                            elif ada_lonjakan_volume and (ma20 > ma50 or (macd_line > macd_signal and macd_hist > 0)):
                                status_akhir = "🟢 STRONG BUY (Momentum sangat kuat didukung akumulasi institusi)"
                            elif is_buy:
                                status_akhir = "🟢 BUY / CICIL BELI (Peluang bagus untuk masuk bertahap)"
                            else:
                                status_akhir = "🟡 WAIT & SEE (Tunggu momentum lebih jelas)"
                            
                            # 2. TARIK DATA BERITA TERKINI DARI YAHOO FINANCE
                            list_berita = []
                            try:
                                news_data = ticker_obj.news
                                # Ambil maksimal 3 berita teratas
                                for artikel in news_data[:3]:
                                    judul = artikel.get('title', 'Judul Tidak Diketahui')
                                    link = artikel.get('link', '#')
                                    sumber = artikel.get('publisher', 'Media Berita')
                                    list_berita.append(f"- [{judul}]({link}) *(Sumber: {sumber})*")
                            except Exception:
                                pass
                            
                            teks_berita = "\n".join(list_berita) if list_berita else "_Belum ada berita terbaru yang relevan di Yahoo Finance._"

                            if is_buy or len(tickers) == 1: 
                                rekomendasi_beli.append({
                                    "Ticker": ticker, "Harga": close_price, 
                                    "Target": target_naik, "SL": stop_loss, 
                                    "Alasan": "\n\n".join(alasan),
                                    "Kesimpulan": status_akhir,
                                    "Berita": teks_berita,
                                    "df_chart": df_hist.tail(90) 
                                })
                            else: 
                                netral_jual.append({"Ticker": ticker, "Harga": format_currency(close_price), "Status": "⏳ Wait & See"})
                    except Exception: pass 
                
                # --- RENDER TAMPILAN HASIL ---
                if rekomendasi_beli:
                    st.success(f"🎯 ANALISIS SELESAI! Menampilkan detail teknikal & berita sentimen:")
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
                            
                            # TAMPILAN ANALISIS & BERITA (DIBAGI 2 KOLOM AGAR RAPI)
                            col_info1, col_info2 = st.columns([1.2, 1])
                            with col_info1:
                                st.info(f"**🧠 Detail Bedah Analisis Teknikal:**\n\n{rec['Alasan']}")
                            with col_info2:
                                st.warning(f"**📰 Sentimen Berita Terkini:**\n\n{rec['Berita']}")
                            
                            st.markdown("---")
                else: 
                    st.warning("Belum ada saham yang memenuhi kriteria Uptrend/Undervalued hari ini.")
                
                with st.expander("Lihat Saham Lainnya (Kondisi Sedang Jelek / Sideways)"):
                    if netral_jual: 
                        df_netral = pd.DataFrame(netral_jual)
                        st.dataframe(df_netral, use_container_width=True)
            except Exception as e: st.error(f"Kesalahan pemindaian: {e}")
