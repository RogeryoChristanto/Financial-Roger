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
st.set_page_config(page_title="Rogeryo Finance", page_icon="💎", layout="wide")

# ==========================================
# INJEKSI CUSTOM CSS: DARK LUXURY & RESPONSIVE MOBILE
# ==========================================
custom_css = """
<style>
    body { font-family: 'Inter', sans-serif; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 50% 0%, #1a1a2e 0%, #000000 100%);
        color: #ffffff;
    }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }

    .header-container {
        display: flex; align-items: center; justify-content: center;
        padding: 20px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 30px;
    }
    .header-logo { font-size: 40px; margin-right: 15px; }
    .header-title {
        font-size: 36px; font-weight: 800; margin: 0;
        background: linear-gradient(45deg, #F9D423, #FF4E50);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .header-subtitle { font-size: 14px; color: #a0a0a0; font-weight: 300; margin-top: 5px; letter-spacing: 2px; }

    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.01));
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 5% 5% 5% 10%; border-radius: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(15px); transition: all 0.4s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px); box-shadow: 0 15px 30px rgba(249, 212, 35, 0.15);
        border: 1px solid rgba(249, 212, 35, 0.4);
    }
    
    .account-card {
        background-color: rgba(255,255,255,0.03); padding: 15px; border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.05); display: flex;
        align-items: center; justify-content: space-between; transition: 0.3s;
    }
    .account-card:hover { border-color: #F9D423; background-color: rgba(255,255,255,0.08); }
    .account-label { font-size: 14px; color: #aaa; display: flex; align-items: center; gap: 8px; }
    .account-value { font-size: 16px; font-weight: 700; color: #fff; }

    .stButton>button {
        background: linear-gradient(45deg, #1e1e2f, #2a2a40); border: 1px solid rgba(255, 255, 255, 0.2);
        color: white; border-radius: 30px; transition: all 0.3s ease; font-weight: 600;
    }
    .stButton>button:hover {
        transform: scale(1.02); border: 1px solid rgba(249, 212, 35, 0.8); color: #F9D423;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 15px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { height: 50px; border-radius: 12px 12px 0px 0px; background-color: rgba(255,255,255,0.02); }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #F9D423 !important; border-bottom-color: #F9D423 !important; }

    /* MOBILE RESPONSIVE */
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"] {
            flex-direction: row !important; flex-wrap: nowrap !important;
            overflow-x: auto !important; padding-bottom: 10px;
        }
        div[data-testid="column"] { min-width: 250px !important; flex: 0 0 auto !important; }
        .header-title { font-size: 28px; }
        .header-subtitle { font-size: 10px; }
    }
    div[data-testid="stHorizontalBlock"]::-webkit-scrollbar { height: 6px; }
    div[data-testid="stHorizontalBlock"]::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.05); border-radius: 10px; }
    div[data-testid="stHorizontalBlock"]::-webkit-scrollbar-thumb { background: rgba(249, 212, 35, 0.5); border-radius: 10px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# HEADER
st.markdown("""
<div class="header-container">
    <div class="header-logo">💎</div>
    <div style="text-align: center;">
        <h1 class="header-title">ROGERYO FINANCE</h1>
        <p class="header-subtitle">PRIVATE ASSET INTELLIGENCE</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# KONEKSI KE GOOGLE SHEETS CLOUD
# ==========================================
@st.cache_resource
def init_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_JSON"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("Database Finance Pro") 

try:
    db = init_connection()
    ws_transaksi = db.worksheet("Transaksi")
    ws_saham = db.worksheet("Saham")
except Exception as e:
    st.markdown(f"""
    <div style='background-color: #1a0808; border: 1px solid #dc3545; color: #dc3545; padding: 20px; border-radius: 15px;'>
        <h3>❌ Koneksi Database Terputus</h3>
        <p>{e}</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

df_transaksi = get_as_dataframe(ws_transaksi).dropna(how='all').dropna(axis=1, how='all')
df_saham = get_as_dataframe(ws_saham).dropna(how='all').dropna(axis=1, how='all')

if df_transaksi.empty or len(df_transaksi.columns) < 5:
    df_transaksi = pd.DataFrame(columns=["Tanggal", "Kategori", "Jenis", "Sumber Dana", "Nominal"])
if df_saham.empty or len(df_saham.columns) < 3:
    df_saham = pd.DataFrame(columns=["Ticker", "Harga Beli", "Jumlah Lembar"])

# ==========================================
# AUTO-KALKULASI SALDO (SSOT)
# ==========================================
porto = {"BCA": 0, "BRI": 0, "Bank Jago": 0, "Dompet (Cash)": 0}
if not df_transaksi.empty:
    for _, row in df_transaksi.iterrows():
        sumber = str(row['Sumber Dana'])
        try: nom = float(row['Nominal'])
        except: nom = 0
            
        if sumber in porto:
            if row['Jenis'] == "Pemasukan": porto[sumber] += nom
            elif row['Jenis'] == "Pengeluaran": porto[sumber] -= nom

# ==========================================
# MESIN SAHAM REAL-TIME
# ==========================================
total_nilai_saham = 0
harga_sekarang_dict = {}

if not df_saham.empty:
    try: kurs_usd = yf.Ticker("USDIDR=X").history(period="1d")['Close'].iloc[-1]
    except: kurs_usd = 15800 

    for t in df_saham['Ticker'].unique():
        t = str(t).upper()
        if t != "NAN" and t != "":
            try:
                current_price = yf.Ticker(t).history(period="1d")['Close'].iloc[-1]
                if not t.endswith('.JK'): current_price = current_price * kurs_usd
                harga_sekarang_dict[t] = current_price
            except: harga_sekarang_dict[t] = 0

    for _, row in df_saham.iterrows():
        try:
            hb = float(row['Harga Beli'])
            jl = float(row['Jumlah Lembar'])
            t = str(row['Ticker']).upper()
            cp = harga_sekarang_dict.get(t, hb)
            total_nilai_saham += (cp * jl)
        except: pass

# ==========================================
# MEMBUAT TAB MENU
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 Dashboard Kekayaan", "📈 Portofolio Saham", "🧾 AI Struk Scanner"])

# ==========================================
# TAB 1: DASHBOARD & KEKAYAAN
# ==========================================
with tab1:
    total_uang_fiat = sum(porto.values())
    total_kekayaan = total_uang_fiat + total_nilai_saham
    
    col_tot, col_fiat, col_saham = st.columns(3)
    col_tot.metric(label="🌟 TOTAL KEKAYAAN BERSIH", value=f"Rp {total_kekayaan:,.0f}")
    col_fiat.metric(label="💵 Uang Kas & Bank", value=f"Rp {total_uang_fiat:,.0f}")
    col_saham.metric(label="📈 Nilai Aset Saham", value=f"Rp {total_nilai_saham:,.0f}")
    
    st.write("") 
    a1, a2, a3, a4 = st.columns(4)
    with a1: st.markdown(f"<div class='account-card'><div class='account-label'>🔵 BCA</div><div class='account-value'>Rp {porto['BCA']:,.0f}</div></div>", unsafe_allow_html=True)
    with a2: st.markdown(f"<div class='account-card'><div class='account-label'>🟠 BRI</div><div class='account-value'>Rp {porto['BRI']:,.0f}</div></div>", unsafe_allow_html=True)
    with a3: st.markdown(f"<div class='account-card'><div class='account-label'>🟡 JAGO</div><div class='account-value'>Rp {porto['Bank Jago']:,.0f}</div></div>", unsafe_allow_html=True)
    with a4: st.markdown(f"<div class='account-card'><div class='account-label'>🟢 CASH</div><div class='account-value'>Rp {porto['Dompet (Cash)']:,.0f}</div></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_kiri, col_kanan = st.columns([1, 2.2])
    
    with col_kiri:
        st.subheader("➕ Catat Transaksi")
        with st.form("form_transaksi", clear_on_submit=True):
            input_tanggal = st.date_input("Tanggal", date.today())
            input_kategori = st.selectbox("Kategori", ["Gaji", "Usaha", "Makan & Minum", "Transportasi", "Pendidikan", "Investasi Saham", "Lainnya"])
            input_jenis = st.radio("Jenis", ["Pemasukan", "Pengeluaran"], horizontal=True)
            input_sumber = st.selectbox("Dompet/Bank", ["BCA", "BRI", "Bank Jago", "Dompet (Cash)"])
            input_nominal = st.number_input("Nominal (Rp)", min_value=0.0, step=50000.0)
            
            if st.form_submit_button("💾 Simpan Transaksi") and input_nominal > 0:
                if input_jenis == "Pengeluaran" and porto.get(input_sumber, 0) < input_nominal:
                    st.toast(f'Saldo {input_sumber} tidak cukup!', icon='⚠️')
                    st.stop()
                
                data_baru = pd.DataFrame([{"Tanggal": str(input_tanggal), "Kategori": input_kategori, "Jenis": input_jenis, "Sumber Dana": input_sumber, "Nominal": input_nominal}])
                df_update = pd.concat([df_transaksi, data_baru], ignore_index=True)
                
                ws_transaksi.clear()
                set_with_dataframe(ws_transaksi, df_update)
                if input_jenis == "Pemasukan": st.balloons()
                st.toast('Tersimpan di Cloud!', icon='✅')
                st.rerun()

    with col_kanan:
        st.subheader("📊 Visualisasi Keuangan")
        tab_grafik1, tab_grafik2 = st.tabs(["📉 Cashflow Bar", "🥧 Aset Donut"])
        
        with tab_grafik1:
            if not df_transaksi.empty:
                df_cashflow = df_transaksi.copy()
                df_cashflow['Nominal'] = pd.to_numeric(df_cashflow['Nominal'], errors='coerce')
                df_cf_group = df_cashflow.groupby('Jenis')['Nominal'].sum().reset_index()
                fig_cf = px.bar(df_cf_group, x='Jenis', y='Nominal', color='Jenis', color_discrete_map={'Pemasukan':'#2ecc71', 'Pengeluaran':'#e74c3c'}, text='Nominal')
                fig_cf.update_traces(texttemplate='Rp %{text:,.0f}', textposition='outside')
                fig_cf.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', uniformtext_minsize=8, uniformtext_mode='hide', height=320)
                st.plotly_chart(fig_cf, use_container_width=True)
                
        with tab_grafik2:
            aset_dict = porto.copy()
            aset_dict["Portofolio Saham"] = total_nilai_saham
            df_aset = pd.DataFrame(list(aset_dict.items()), columns=['Aset', 'Nilai'])
            df_aset = df_aset[df_aset['Nilai'] > 0] 
            if not df_aset.empty:
                fig_porto = px.pie(df_aset, values='Nilai', names='Aset', hole=0.5, color='Aset',
                                   color_discrete_map={'BCA':'#0066AE', 'BRI':'#F26522', 'Bank Jago':'#F4A300', 'Dompet (Cash)':'#27AE60', 'Portofolio Saham':'#8E44AD'})
                fig_porto.update_layout(paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=10, b=0, l=0, r=0), height=320)
                st.plotly_chart(fig_porto, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Database Transaksi (Live Edit)")
    edited_df_t = st.data_editor(df_transaksi, num_rows="dynamic", use_container_width=True, height=250)
    if st.button("☁️ Sinkronisasi Perubahan Transaksi"):
        ws_transaksi.clear()
        set_with_dataframe(ws_transaksi, edited_df_t)
        st.toast('Database ter-update!', icon='🔄')
        st.rerun()

# ==========================================
# TAB 2: PORTOFOLIO & ANALISIS SAHAM
# ==========================================
with tab2:
    col_in_saham, col_tb_saham = st.columns([1, 2.5])
    
    with col_in_saham:
        st.subheader("➕ Order Saham")
        with st.form("form_saham", clear_on_submit=True):
            in_ticker = st.text_input("Kode (Misal BELL.JK)", "BELL.JK").upper()
            in_harga_beli = st.number_input("Harga Beli / Lbr (Rp)", min_value=1.0, step=1.0)
            in_lot = st.number_input("Jumlah (Lot)", min_value=1, step=1)
            
            if st.form_submit_button("🛒 Beli Saham"):
                in_lembar = in_lot * 100 
                saham_baru = pd.DataFrame([{"Ticker": in_ticker, "Harga Beli": in_harga_beli, "Jumlah Lembar": in_lembar}])
                df_s_update = pd.concat([df_saham, saham_baru], ignore_index=True)
                ws_saham.clear()
                set_with_dataframe(ws_saham, df_s_update)
                st.snow() 
                st.toast(f'{in_ticker} ditambahkan!', icon='📈')
                st.rerun()
                
    with col_tb_saham:
        st.subheader("💼 Portofolio Real-Time")
        if not df_saham.empty:
            display_data = []
            for _, row in df_saham.iterrows():
                try:
                    t = str(row['Ticker']).upper()
                    if t == "NAN" or t == "": continue
                    hb = float(row['Harga Beli'])
                    jl = float(row['Jumlah Lembar'])
                    cp = harga_sekarang_dict.get(t, hb) 
                    
                    nilai_awal = hb * jl
                    nilai_sekarang = cp * jl
                    profit_rp = nilai_sekarang - nilai_awal
                    profit_pct = (profit_rp / nilai_awal) * 100 if nilai_awal > 0 else 0
                    status = "🟢" if profit_pct > 0 else "🔴" if profit_pct < 0 else "⚪"
                    
                    display_data.append({
                        "Kode": f"{t} {status}", "Volume": f"{jl/100:.0f} Lot",
                        "Avg Price": f"Rp {hb:,.0f}", "Last Price": f"Rp {cp:,.0f}",
                        "Market Value": f"Rp {nilai_sekarang:,.0f}", "Return (%)": f"{profit_pct:.2f}%"
                    })
                except: pass
            if display_data:
                st.dataframe(pd.DataFrame(display_data), use_container_width=True)

        with st.expander("⚙️ Edit Data Master Saham"):
            edited_df_s = st.data_editor(df_saham, num_rows="dynamic", use_container_width=True)
            if st.button("☁️ Sinkronisasi Perubahan Saham"):
                ws_saham.clear()
                set_with_dataframe(ws_saham, edited_df_s)
                st.rerun()

    st.markdown("---")
    st.subheader("🤖 AI Technical Analysis (RSI)")
    ticker_analisis = st.text_input("Cari Saham (Contoh: GOTO.JK)", "GOTO.JK").upper()
    try:
        stock = yf.Ticker(ticker_analisis)
        data = stock.history(period="6mo")
        if len(data) > 0:
            data['RSI'] = ta.rsi(data['Close'], length=14)
            fig_stock = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
            fig_stock.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.02)', xaxis_rangeslider_visible=False, height=400)
            st.plotly_chart(fig_stock, use_container_width=True)
            
            if data['RSI'].count() > 0:
                latest_rsi = float(data['RSI'].dropna().iloc[-1])
                st.metric(label="RSI (14 Hari)", value=f"{latest_rsi:.2f}")
                if latest_rsi < 30: st.success("🎯 REKOMENDASI: BUY (Area Oversold)")
                elif latest_rsi > 70: st.error("⚠️ REKOMENDASI: SELL (Area Overbought)")
                else: st.info("⚖️ REKOMENDASI: HOLD (Pergerakan Netral)")
    except: st.error("Gagal menarik grafik saham.")

# ==========================================
# TAB 3: SCAN STRUK OCR
# ==========================================
with tab3:
    st.subheader("🧾 AI Smart Scanner")
    col_upload, col_hasil = st.columns(2)
    with col_upload:
        uploaded_file = st.file_uploader("Upload Foto Nota (JPG/PNG)", type=["jpg", "png", "jpeg"])
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Dokumen Asli", use_container_width=True)
            if st.button("🔍 Jalankan AI Scanner", type="primary", use_container_width=True):
                with col_hasil:
                    with st.spinner("Memindai teks..."):
                        try:
                            extracted_text = pytesseract.image_to_string(image)
                            st.success("✅ Sukses!")
                            st.text_area("Teks Terdeteksi:", extracted_text, height=350)
                        except: st.error("❌ Gagal membaca gambar.")
