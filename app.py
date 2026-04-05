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
# 2. DESAIN ULTRA-MODERN & ANIMASI WOW (CSS)
# ==========================================
custom_css = """
<style>
    /* Font premium bergaya Fintech Modern */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800;900&display=swap');

    #MainMenu, footer, header {visibility: hidden;}
    
    /* 1. ANIMATED BACKGROUND (Cahaya bergerak perlahan) */
    @keyframes gradientMove {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    [data-testid="stAppViewContainer"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        /* Gradien Midnight Aurora */
        background: linear-gradient(-45deg, #020617, #0F172A, #171026, #050505);
        background-size: 400% 400%;
        animation: gradientMove 15s ease infinite;
        color: #E2E8F0;
    }

    /* 2. GLOWING TITLE DENGAN EFEK 3D */
    .title-glow {
        font-size: clamp(35px, 8vw, 60px);
        font-weight: 900;
        background: linear-gradient(135deg, #FFD700 0%, #D4AF37 50%, #FF8C00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding-top: 15px;
        filter: drop-shadow(0px 10px 15px rgba(212, 175, 55, 0.4));
        letter-spacing: -1.5px;
    }
    
    .subtitle {
        text-align: center; color: #94A3B8; font-size: 12px; font-weight: 800;
        letter-spacing: 6px; text-transform: uppercase; margin-bottom: 45px;
        text-shadow: 0 0 10px rgba(255,255,255,0.1);
    }

    /* 3. STYLING TABS STREAMLIT MENJADI TOMBOL PREMIUM */
    [data-testid="stTabs"] button[data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 50px;
        margin-right: 10px;
        padding: 10px 24px;
        font-weight: 600;
        color: #94A3B8;
        border: 1px solid rgba(255,255,255,0.1);
        transition: all 0.3s ease;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"]:hover {
        background-color: rgba(255, 255, 255, 0.05);
        color: #fff;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #D4AF37 0%, #AA771C 100%);
        color: #000;
        border: none;
        box-shadow: 0 5px 15px rgba(212, 175, 55, 0.4);
    }
    /* Sembunyikan garis bawah tab bawaan Streamlit */
    [data-testid="stTabs"] div[data-baseweb="tab-list"] { gap: 10px; padding-bottom: 5px; }
    [data-testid="stTabs"] div[data-baseweb="tab-highlight"] { display: none; }

    /* 4. KARTU SALDO (ULTRA GLASSMORPHISM) */
    .wallet-container {
        display: flex; gap: 20px; overflow-x: auto; padding: 15px 10px 40px 10px;
        scrollbar-width: none; /* Hide scrollbar for a cleaner look */
    }
    .wallet-container::-webkit-scrollbar { display: none; }

    .wallet-card {
        min-width: 270px;
        padding: 25px;
        border-radius: 24px;
        background: rgba(20, 25, 40, 0.6);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
        position: relative;
        overflow: hidden;
        transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
    }
    
    .wallet-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
        border: 1px solid rgba(212, 175, 55, 0.3);
    }

    /* Garis aksen elegan di atas kartu */
    .wallet-card::before {
        content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 5px;
    }
    .bca-card::before { background: linear-gradient(90deg, #0066AE, #00B4DB); }
    .bri-card::before { background: linear-gradient(90deg, #F26522, #f5af19); }
    .jago-card::before { background: linear-gradient(90deg, #F4A300, #ffe259); }
    .cash-card::before { background: linear-gradient(90deg, #11998e, #38ef7d); }

    .wallet-icon { font-size: 32px; margin-bottom: 15px; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.3)); }
    .wallet-label { font-size: 11px; font-weight: 800; color: #94A3B8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; }
    .wallet-balance { font-size: 28px; font-weight: 900; color: #F8FAFC; letter-spacing: -0.5px; }

    /* 5. METRIK KEKAYAAN BERNAPAS (PULSING ANIMATION) */
    @keyframes pulseGlow {
        0% { text-shadow: 0 0 10px rgba(212, 175, 55, 0.2); }
        50% { text-shadow: 0 0 25px rgba(212, 175, 55, 0.8), 0 0 10px rgba(212, 175, 55, 0.4); }
        100% { text-shadow: 0 0 10px rgba(212, 175, 55, 0.2); }
    }
    
    /* Mengubah metrik pertama (Total Harta) menjadi warna emas dan bernapas */
    div[data-testid="metric-container"]:nth-child(1) [data-testid="stMetricValue"] {
        background: linear-gradient(to right, #F8E287, #D4AF37);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: pulseGlow 3s infinite alternate;
    }

    [data-testid="stMetricValue"] {
        font-size: 2.2rem !important; font-weight: 900 !important; color: #FFFFFF !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.95rem !important; font-weight: 600 !important; color: #CBD5E1 !important; letter-spacing: 0.5px; text-transform: uppercase;
    }

    /* 6. TOMBOL "SIMPAN SEKARANG" & INPUT FORM */
    .stButton button {
        background: linear-gradient(135deg, #1A1A24 0%, #0F172A 100%) !important;
        color: #D4AF37 !important;
        font-weight: 800 !important;
        letter-spacing: 1px !important;
        border-radius: 16px !important;
        border: 1px solid rgba(212, 175, 55, 0.4) !important;
        padding: 20px !important;
        transition: all 0.4s ease !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #D4AF37 0%, #AA771C 100%) !important;
        color: #000 !important;
        transform: translateY(-3px);
        box-shadow: 0 15px 25px rgba(212, 175, 55, 0.4) !important;
        border: 1px solid transparent !important;
    }

    /* Efek fokus pada input teks & dropdown */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
        background-color: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: white !important;
        transition: all 0.3s ease;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border: 1px solid #D4AF37 !important;
        box-shadow: 0 0 10px rgba(212, 175, 55, 0.3) !important;
        background-color: rgba(0, 0, 0, 0.2) !important;
    }

    /* Responsif untuk HP */
    @media (max-width: 768px) {
        div[data-testid="column"] { min-width: 100% !important; }
        .wallet-card { min-width: 85vw; }
        [data-testid="stTabs"] button[data-baseweb="tab"] { width: 100%; text-align: center; margin-bottom: 5px; }
        [data-testid="stTabs"] div[data-baseweb="tab-list"] { flex-direction: column; }
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)
# ==========================================
# 3. KONEKSI DATA (GOOGLE SHEETS)
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

try:
    ws_transaksi = db.worksheet("Transaksi")
    ws_saham = db.worksheet("Saham")
    df_transaksi = get_as_dataframe(ws_transaksi).dropna(how='all', axis=0).dropna(how='all', axis=1)
    df_saham = get_as_dataframe(ws_saham).dropna(how='all', axis=0).dropna(how='all', axis=1)
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
                    harga_sekarang_dict[t] = cp * kurs if not t.endswith('.JK') else cp
                except Exception: harga_sekarang_dict[t] = 0
                    
            for _, row in df_saham.iterrows():
                ticker, jumlah = str(row.get('Ticker', '')).upper().strip(), float(row.get('Jumlah Lembar', 0))
                total_nilai_saham += (harga_sekarang_dict.get(ticker, 0) * jumlah)
    except Exception as e: 
        st.warning("Kendala memuat harga saham realtime.")

# ==========================================
# 5. TAMPILAN MENU UTAMA
# ==========================================
tab1, tab2, tab3 = st.tabs(["🏦 DASHBOARD KEKAYAAN", "📈 Portofolio Saham", "🧾 AI Smart Scanner"])

# --- (Kode di atasnya biarkan sama, mulai ganti dari sini) ---

with tab1:
    c_btn1, c_btn2 = st.columns([2, 1])
    with c_btn2:
        if st.button("🙈 Sembunyikan Angka" if not st.session_state.hide_balance else "👁️ Tampilkan Angka", use_container_width=True):
            st.session_state.hide_balance = not st.session_state.hide_balance
            st.rerun()

    total_net = sum(porto.values()) + total_nilai_saham
    
    # --- FITUR TARGET TABUNGAN ---
    st.markdown("##### 🎯 Target Pencapaian Harta Bersih")
    target_harta = st.number_input("Atur Target Finansial Anda (Rp)", min_value=1000000, value=50000000, step=5000000, label_visibility="collapsed")
    rasio = total_net / target_harta if target_harta > 0 else 0.0
    progress_val = max(0.0, min(rasio, 1.0)) 
    st.progress(progress_val)
    st.caption(f"Tercapai: **{progress_val*100:.1f}%** dari target {format_currency(target_harta)}")
    st.markdown("---")

    m1, m2, m3 = st.columns(3)
    m1.metric("🌟 TOTAL HARTA BERSIH", format_currency(total_net))
    m2.metric("💵 TOTAL UANG TUNAI", format_currency(sum(porto.values())))
    m3.metric("📈 TOTAL NILAI SAHAM", format_currency(total_nilai_saham))

    # --- FITUR BARU 1: RINGKASAN BULAN INI ---
    pemasukan_bulan_ini = 0
    pengeluaran_bulan_ini = 0
    if not df_transaksi.empty:
        # Konversi kolom tanggal ke format datetime agar bisa difilter
        df_transaksi['Tanggal'] = pd.to_datetime(df_transaksi['Tanggal'], errors='coerce')
        current_month = date.today().month
        current_year = date.today().year
        
        # Filter data hanya untuk bulan & tahun ini
        df_bulan_ini = df_transaksi[(df_transaksi['Tanggal'].dt.month == current_month) & (df_transaksi['Tanggal'].dt.year == current_year)]
        
        pemasukan_bulan_ini = df_bulan_ini[df_bulan_ini['Jenis'].str.lower() == 'pemasukan']['Nominal'].sum()
        pengeluaran_bulan_ini = df_bulan_ini[df_bulan_ini['Jenis'].str.lower() == 'pengeluaran']['Nominal'].sum()
    
    sisa_anggaran = pemasukan_bulan_ini - pengeluaran_bulan_ini
    
    st.markdown(f"<br><h6>📅 Arus Kas Bulan Ini ({date.today().strftime('%B %Y')})</h6>", unsafe_allow_html=True)
    cm1, cm2, cm3 = st.columns(3)
    cm1.metric("Pemasukan Bulan Ini", format_currency(pemasukan_bulan_ini), delta="Inflow", delta_color="normal")
    cm2.metric("Pengeluaran Bulan Ini", format_currency(pengeluaran_bulan_ini), delta="Outflow", delta_color="inverse")
    cm3.metric("Sisa Cashflow", format_currency(sisa_anggaran), delta="Sisa Uang", delta_color="off")
    st.markdown("---")

    # Kartu Saldo
    st.markdown('<div class="wallet-container">', unsafe_allow_html=True)
    wc = st.columns(4)
    wallets = [
        {"name": "BANK CENTRAL ASIA", "val": porto["BCA"], "class": "bca-card", "icon": "🏦"},
        {"name": "BANK RAKYAT INDONESIA", "val": porto["BRI"], "class": "bri-card", "icon": "🏢"},
        {"name": "BANK JAGO DIGITAL", "val": porto["Bank Jago"], "class": "jago-card", "icon": "🦊"},
        {"name": "UANG TUNAI (DOMPET)", "val": porto["Dompet (Cash)"], "class": "cash-card", "icon": "💵"}
    ]
    for i, w in enumerate(wallets):
        with wc[i]:
            st.markdown(f'''<div class="wallet-card {w['class']}">
                <div class="wallet-icon">{w['icon']}</div>
                <div class="wallet-label">{w['name']}</div>
                <div class="wallet-balance">{format_currency(w['val'])}</div>
            </div>''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    col_l, col_r = st.columns([1, 1.5])
    with col_l:
        st.subheader("➕ Tambah Transaksi")
        with st.form("trx_form", clear_on_submit=True):
            f_tgl = st.date_input("Tanggal", date.today())
            f_kat = st.selectbox("Kategori", ["Gaji", "Makan & Minum", "Belanja", "Transport", "Investasi", "Parfum", "Bayar Kost", "Skincare", "Lainnya"])
            f_jen = st.radio("Jenis", ["Pemasukan", "Pengeluaran"], horizontal=True)
            f_src = st.selectbox("Pilih Dompet", list(porto.keys()))
            f_nom = st.number_input("Jumlah Uang (Rp)", min_value=0.0, step=50000.0)
            f_note = st.text_area("Catatan / Rincian", placeholder="Contoh: Beli kemeja hitam, dll")
            
            if st.form_submit_button("SIMPAN SEKARANG"):
                new_row = pd.DataFrame([{
                    "Tanggal": f_tgl.strftime('%Y-%m-%d'), 
                    "Kategori": f_kat, "Jenis": f_jen, "Sumber Dana": f_src, 
                    "Nominal": f_nom, "Catatan": f_note
                }])
                df_updated = pd.concat([df_transaksi, new_row], ignore_index=True)
                set_with_dataframe(ws_transaksi, df_updated, row=1)
                if f_jen == "Pemasukan": st.balloons()
                st.rerun()

    with col_r:
        st.subheader("📊 Analisis Visual")
        # --- FITUR BARU 2: TAB KATEGORI PENGELUARAN ---
        g1, g2, g3 = st.tabs(["Arus Kas", "Pembagian Aset", "Rincian Pengeluaran"])
        with g1:
            if not df_transaksi.empty:
                df_grouped = df_transaksi.groupby('Jenis')['Nominal'].sum().reset_index()
                fig = px.bar(df_grouped, x='Jenis', y='Nominal', color='Jenis', template="plotly_dark", color_discrete_map={'Pemasukan':'#2ecc71', 'Pengeluaran':'#e74c3c'})
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
                st.plotly_chart(fig, use_container_width=True)
        with g2:
            df_p = pd.DataFrame([{"Aset": k, "Nilai": v} for k, v in {**porto, "Saham": total_nilai_saham}.items() if v > 0])
            if not df_p.empty:
                asset_color_map = {'BCA': '#0066AE', 'BRI': '#F26522', 'Bank Jago': '#F4A300', 'Dompet (Cash)': '#27AE60', 'Saham': '#8E44AD'}
                fig_p = px.pie(df_p, values='Nilai', names='Aset', hole=0.5, template="plotly_dark", color='Aset', color_discrete_map=asset_color_map)
                fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=320, showlegend=True)
                st.plotly_chart(fig_p, use_container_width=True)
        with g3:
            if not df_transaksi.empty:
                df_pengeluaran = df_transaksi[df_transaksi['Jenis'].str.lower() == 'pengeluaran']
                if not df_pengeluaran.empty:
                    df_kat = df_pengeluaran.groupby('Kategori')['Nominal'].sum().reset_index()
                    fig_kat = px.pie(df_kat, values='Nominal', names='Kategori', hole=0.4, template="plotly_dark")
                    fig_kat.update_traces(textposition='inside', textinfo='percent+label')
                    fig_kat.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=320, showlegend=False)
                    st.plotly_chart(fig_kat, use_container_width=True)
                else:
                    st.info("Belum ada data pengeluaran.")

    st.subheader("📋 Riwayat Transaksi")
    if not df_transaksi.empty:
        # Tampilkan DataFrame dengan urutan terbaru di atas
        st.dataframe(df_transaksi.sort_values(by='Tanggal', ascending=False), use_container_width=True, height=250)
        csv_trx = df_transaksi.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel/CSV Transaksi", data=csv_trx, file_name="Riwayat_Transaksi_ROGER.csv", mime="text/csv")
    else:
        st.info("Data transaksi kosong.")

with tab2:
    st.subheader("💼 Portofolio & Input Saham")
    with st.expander("➕ Tambah Data Saham Baru", expanded=False):
        with st.form("form_saham", clear_on_submit=True):
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1: new_ticker = st.text_input("Kode Ticker", help="Akhiri .JK untuk Indonesia").upper()
            with col_s2: new_lembar = st.number_input("Jumlah Lembar", min_value=1, step=100)
            with col_s3: new_harga = st.number_input("Harga Beli Rata-rata (Rp)", min_value=0.0)
            
            if st.form_submit_button("SIMPAN KE PORTOFOLIO"):
                if new_ticker:
                    new_stock_data = pd.DataFrame([{"Ticker": new_ticker.strip(), "Jumlah Lembar": new_lembar, "Harga Beli": new_harga}])
                    df_saham_updated = pd.concat([df_saham, new_stock_data], ignore_index=True)
                    set_with_dataframe(ws_saham, df_saham_updated, row=1)
                    st.success(f"Tersimpan: {new_ticker}!")
                    st.rerun()

    if not df_saham.empty:
        rows = []
        pie_data_saham = [] # Menyimpan data untuk grafik pie saham
        
        for _, r in df_saham.iterrows():
            t, harga_beli, lembar = str(r.get('Ticker', '')).upper(), float(r.get('Harga Beli', 0)), float(r.get('Jumlah Lembar', 0))
            
            harga_skrg = harga_sekarang_dict.get(t, 0)
            if pd.isna(harga_skrg) or harga_skrg == 0:
                harga_skrg = harga_beli
                
            gain = ((harga_skrg - harga_beli) / harga_beli) * 100 if harga_beli > 0 else 0.0
            total_nilai = harga_skrg * lembar
            
            rows.append({"Kode Saham": t, "Total Lot": f"{lembar/100:.0f} Lot", "Harga Beli": format_currency(harga_beli), "Harga Sekarang": format_currency(harga_skrg), "Keuntungan (%)": f"{gain:.2f}%"})
            
            if total_nilai > 0:
                pie_data_saham.append({"Ticker": t, "Nilai": total_nilai})
        
        # Tampilkan tabel portofolio
        df_tampil_saham = pd.DataFrame(rows)
        st.dataframe(df_tampil_saham, use_container_width=True)
        
        col_sd1, col_sd2 = st.columns([1, 1])
        with col_sd1:
            csv_saham = df_tampil_saham.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Laporan Portofolio", data=csv_saham, file_name="Portofolio_Saham_ROGER.csv", mime="text/csv")
        
        # --- FITUR BARU 3: GRAFIK ALOKASI SAHAM ---
        with col_sd2:
            with st.expander("📊 Lihat Alokasi Diversifikasi Saham"):
                if pie_data_saham:
                    fig_saham = px.pie(pd.DataFrame(pie_data_saham), values='Nilai', names='Ticker', hole=0.4, template="plotly_dark")
                    fig_saham.update_traces(textposition='inside', textinfo='percent+label')
                    fig_saham.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_saham, use_container_width=True)
        
    st.markdown("---")
    st.subheader("📈 Analisis Pergerakan Saham Pro")
    target = st.text_input("Ketik Kode Ticker (Contoh: BMRI.JK, AAPL):", "BBCA.JK").upper()
    try:
        h = yf.Ticker(target).history(period="6mo")
        if not h.empty:
            fig_h = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'], name='Harga')])
            
            if len(h) >= 50:
                h['SMA_20'] = ta.sma(h['Close'], length=20)
                h['SMA_50'] = ta.sma(h['Close'], length=50)
                fig_h.add_trace(go.Scatter(x=h.index, y=h['SMA_20'], line=dict(color='#3498db', width=2), name='SMA 20 (Jangka Pendek)'))
                fig_h.add_trace(go.Scatter(x=h.index, y=h['SMA_50'], line=dict(color='#f1c40f', width=2), name='SMA 50 (Jangka Menengah)'))

            fig_h.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', height=450, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_h, use_container_width=True)
            
            c_rsi, c_info = st.columns([1, 2])
            with c_rsi:
                if len(h) >= 15:
                    rsi = ta.rsi(h['Close'], length=14).iloc[-1]
                    st.metric("Skor RSI-14", f"{rsi:.2f}")
                    if rsi < 30: st.success("🎯 OVERSOLD (Potensi Beli)")
                    elif rsi > 70: st.error("⚠️ OVERBOUGHT (Potensi Jual)")
                    else: st.info("⚖️ NETRAL")
            with c_info:
                st.markdown("**💡 Tips Analisis:** Jika Garis Biru (SMA 20) memotong Garis Kuning (SMA 50) ke arah atas, itu adalah sinyal **Uptrend / Beli** (Golden Cross).")
        else:
            st.warning("Data saham tidak ditemukan.")
    except Exception as e:
        st.error("Gagal memuat grafik saham.")

# --- (Bagian with tab3: biarkan sama seperti sebelumnya) ---

with tab3:
    st.subheader("🧾 Scan Nota Otomatis (Robot AI)")
    up = st.file_uploader("Upload Foto Nota (JPG/PNG)", type=["jpg", "png", "jpeg"])
    if up:
        img = Image.open(up)
        st.image(img, use_container_width=True, caption="Nota Terupload")
        if st.button("MULAI BACA NOTA", use_container_width=True):
            with st.spinner("Mengekstrak teks..."):
                try:
                    res = pytesseract.image_to_string(img)
                    if res.strip(): st.text_area("Hasil Ekstraksi Teks:", res, height=300)
                    else: st.warning("Teks tidak terdeteksi.")
                except Exception as e:
                    st.error("Error: Pastikan Tesseract OCR terinstal.")
