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
st.set_page_config(page_title="ROGER WEALTH OS", page_icon="💎", layout="wide")

if 'hide_balance' not in st.session_state:
    st.session_state.hide_balance = False

def format_currency(value):
    if st.session_state.hide_balance:
        return "Rp ••••••••"
    return f"Rp {value:,.0f}"

# ==========================================
# 2. DESAIN MEWAH (CSS)
# ==========================================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&display=swap');

    #MainMenu, footer, header {visibility: hidden;}
    
    [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background: radial-gradient(circle at 20% 30%, #1a1a1a 0%, #050505 100%);
        color: #e0e0e0;
    }

    .title-glow {
        font-size: clamp(30px, 8vw, 52px);
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
        font-size: 11px;
        letter-spacing: 4px;
        text-transform: uppercase;
        margin-bottom: 30px;
    }

    .wallet-container {
        display: flex;
        flex-direction: row;
        overflow-x: auto;
        gap: 15px;
        padding: 10px 5px 25px 5px;
        scrollbar-width: none;
    }
    .wallet-container::-webkit-scrollbar { display: none; }

    .wallet-card {
        min-width: 280px;
        padding: 25px;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        transition: 0.3s;
    }
    
    .bca-card { background: linear-gradient(135deg, #003366 0%, #0059b3 100%); border-left: 6px solid #fff; }
    .bri-card { background: linear-gradient(135deg, #b33c00 0%, #ff661a 100%); border-left: 6px solid #fff; }
    .jago-card { background: linear-gradient(135deg, #cca300 0%, #ffcc00 100%); color: #000; border-left: 6px solid #222; }
    .cash-card { background: linear-gradient(135deg, #143314 0%, #286628 100%); border-left: 6px solid #4ade80; }

    .wallet-label { font-size: 10px; font-weight: 600; opacity: 0.8; letter-spacing: 1px; margin-bottom: 5px; }
    .wallet-balance { font-size: 22px; font-weight: 900; }
    .wallet-icon { font-size: 26px; margin-bottom: 8px; }

    .stButton button {
        background: linear-gradient(135deg, #bf953f 0%, #aa771c 100%) !important;
        color: black !important;
        font-weight: 800 !important;
        border-radius: 12px !important;
        border: none !important;
    }

    @media (max-width: 768px) {
        div[data-testid="column"] { min-width: 100% !important; }
        .wallet-card { min-width: 250px; }
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

st.markdown("<div class='title-glow'>ROGER WEALTH OS</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Aplikasi Pengatur Kekayaan Pribadi</div>", unsafe_allow_html=True)

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
    except: return None

db = init_connection()
if not db:
    st.error("Gagal terhubung ke Cloud Database. Silakan cek koneksi.")
    st.stop()

ws_transaksi = db.worksheet("Transaksi")
ws_saham = db.worksheet("Saham")
df_transaksi = get_as_dataframe(ws_transaksi).dropna(how='all', axis=0).dropna(how='all', axis=1)
df_saham = get_as_dataframe(ws_saham).dropna(how='all', axis=0).dropna(how='all', axis=1)

# ==========================================
# 4. PENGHITUNG SALDO & HARGA SAHAM
# ==========================================
porto = {"BCA": 0, "BRI": 0, "Bank Jago": 0, "Dompet (Cash)": 0}
for _, row in df_transaksi.iterrows():
    try:
        s, j, n = str(row['Sumber Dana']), row['Jenis'], float(row['Nominal'])
        if s in porto: porto[s] += n if j == "Pemasukan" else -n
    except: pass

total_nilai_saham = 0
harga_sekarang_dict = {}
if not df_saham.empty:
    try:
        kurs = yf.Ticker("USDIDR=X").history(period="1d")['Close'].iloc[-1]
        tks = [str(t).upper() for t in df_saham['Ticker'].unique() if str(t) != "NAN"]
        data_yf = yf.download(tks, period="1d", progress=False)['Close']
        for t in tks:
            try:
                cp = data_yf[t].iloc[-1] if len(tks) > 1 else data_yf.iloc[-1]
                harga_sekarang_dict[t] = cp * kurs if not t.endswith('.JK') else cp
            except: harga_sekarang_dict[t] = 0
        for _, row in df_saham.iterrows():
            total_nilai_saham += (harga_sekarang_dict.get(str(row['Ticker']).upper(), 0) * float(row['Jumlah Lembar']))
    except: pass

# ==========================================
# 5. TAMPILAN MENU UTAMA
# ==========================================
tab1, tab2, tab3 = st.tabs(["🏦 Ringkasan Tabungan", "📈 Daftar Saham", "🧾 Scan Nota"])

with tab1:
    # Kontrol Atas
    c_btn1, c_btn2 = st.columns([2, 1])
    with c_btn2:
        lbl = "🙈 Sembunyikan Angka" if not st.session_state.hide_balance else "👁️ Tampilkan Angka"
        if st.button(lbl, use_container_width=True):
            st.session_state.hide_balance = not st.session_state.hide_balance
            st.rerun()

    # Total Kekayaan
    total_net = sum(porto.values()) + total_nilai_saham
    m1, m2, m3 = st.columns(3)
    m1.metric("🌟 TOTAL HARTA BERSIH", format_currency(total_net))
    m2.metric("💵 TOTAL UANG TUNAI", format_currency(sum(porto.values())))
    m3.metric("📈 TOTAL NILAI SAHAM", format_currency(total_nilai_saham))

    # KARTU SALDO MEWAH
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

    # Form & Grafik
    col_l, col_r = st.columns([1, 1.5])
    with col_l:
        st.subheader("➕ Tambah Catatan")
        with st.form("trx_form", clear_on_submit=True):
            f_tgl = st.date_input("Tanggal", date.today())
            f_kat = st.selectbox("Kategori", ["Gaji", "Makan & Minum", "Belanja", "Transport", "Investasi", "Lain-lain"])
            f_jen = st.radio("Jenis", ["Pemasukan", "Pengeluaran"], horizontal=True)
            f_src = st.selectbox("Pilih Dompet", list(porto.keys()))
            f_nom = st.number_input("Jumlah Uang (Rp)", min_value=0.0, step=50000.0)
            if st.form_submit_button("SIMPAN SEKARANG"):
                new_row = pd.DataFrame([{"Tanggal": str(f_tgl), "Kategori": f_kat, "Jenis": f_jen, "Sumber Dana": f_src, "Nominal": f_nom}])
                set_with_dataframe(ws_transaksi, pd.concat([df_transaksi, new_row]), row=1)
                if f_jen == "Pemasukan": st.balloons()
                st.rerun()

    with col_r:
        st.subheader("📊 Analisis Visual")
        g1, g2 = st.tabs(["Uang Masuk vs Keluar", "Pembagian Harta"])
        with g1:
            if not df_transaksi.empty:
                fig = px.bar(df_transaksi.groupby('Jenis')['Nominal'].sum().reset_index(), x='Jenis', y='Nominal', color='Jenis', template="plotly_dark", color_discrete_map={'Pemasukan':'#2ecc71', 'Pengeluaran':'#e74c3c'})
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
                st.plotly_chart(fig, use_container_width=True)
        with g2:
            # MEMBUAT DATA UNTUK DONUT CHART
            df_p = pd.DataFrame([{"Aset": k, "Nilai": v} for k, v in {**porto, "Saham": total_nilai_saham}.items() if v > 0])
            
            # PENATAAN WARNA PER ASET (IDENTITAS BRAND)
            asset_color_map = {
                'BCA': '#0066AE',        # Biru BCA
                'BRI': '#F26522',        # Oranye BRI
                'Bank Jago': '#F4A300',  # Kuning Emas Jago
                'Dompet (Cash)': '#27AE60', # Hijau Cash
                'Saham': '#8E44AD'       # Ungu Investasi Saham
            }

            fig_p = px.pie(
                df_p, 
                values='Nilai', 
                names='Aset', 
                hole=0.5, 
                template="plotly_dark",
                color='Aset', # Memberitahu plotly untuk menggunakan kolom 'Aset' sebagai kunci warna
                color_discrete_map=asset_color_map # Menerapkan peta warna yang kita buat
            )
            
            fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=320, showlegend=True)
            # Memberi garis putih tipis antar potongan agar lebih rapi
            fig_p.update_traces(marker=dict(line=dict(color='#1a1a1a', width=2)))
            st.plotly_chart(fig_p, use_container_width=True)

    st.subheader("📋 Riwayat Catatan Pengeluaran & Pemasukan")
    st.write("Gunakan tabel di bawah ini untuk melihat atau mengubah catatan lama secara langsung.")
    st.data_editor(df_transaksi, use_container_width=True, height=250)

with tab2:
    # ... (Bagian Tab Saham tetap sama seperti sebelumnya)
    st.subheader("💼 Daftar Investasi Saham Saya")
    if not df_saham.empty:
        rows = []
        for _, r in df_saham.iterrows():
            t = str(r['Ticker']).upper()
            cp = harga_sekarang_dict.get(t, r['Harga Beli'])
            gain = ((cp - r['Harga Beli']) / r['Harga Beli']) * 100
            rows.append({"Kode": t, "Total Lot": f"{r['Jumlah Lembar']/100:.0f}", "Harga Skrg": format_currency(cp), "Keuntungan": f"{gain:.2f}%"})
        st.table(pd.DataFrame(rows))

    target = st.text_input("Ketik Kode Saham untuk Dianalisis (Contoh: BBCA.JK)", "BBCA.JK").upper()
    try:
        h = yf.Ticker(target).history(period="6mo")
        fig_h = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'])])
        fig_h.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', height=400, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_h, use_container_width=True)
        rsi = ta.rsi(h['Close'], length=14).iloc[-1]
        st.metric("Skor Kecepatan Harga (RSI)", f"{rsi:.2f}")
        if rsi < 30: st.success("🎯 HARGA MURAH - Waktunya Beli")
        elif rsi > 70: st.error("⚠️ HARGA MAHAL - Siap-siap Jual")
        else: st.info("⚖️ HARGA NORMAL - Pantau Dulu")
    except: pass

with tab3:
    # ... (Bagian Scan Nota tetap sama seperti sebelumnya)
    st.subheader("🧾 Scan Nota Otomatis (Robot AI)")
    st.write("Foto nota belanja Anda dan biarkan AI yang membaca teksnya.")
    up = st.file_uploader("Upload Foto Nota", type=["jpg", "png", "jpeg"])
    if up:
        img = Image.open(up)
        st.image(img, use_container_width=True, caption="Nota Terupload")
        if st.button("MULAI BACA NOTA"):
            with st.spinner("Robot AI sedang membaca tulisan..."):
                try:
                    res = pytesseract.image_to_string(img)
                    st.text_area("Hasil Bacaan AI:", res, height=300)
                except Exception as e:
                    st.error("Pastikan layanan Tesseract sudah terpasang di sistem.")
