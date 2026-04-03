import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
import pytesseract
from PIL import Image
from datetime import date

# ==========================================
# KONFIGURASI HALAMAN UTAMA
# ==========================================
st.set_page_config(page_title="Finance Pro Master", page_icon="💼", layout="wide")

# CSS Tambahan untuk menyembunyikan menu bawaan Streamlit
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title("💼 Finance Pro Master v3")
st.markdown("Sistem manajemen kekayaan cerdas, integrasi multi-rekening, dan analisis teknikal.")
st.divider()

# ==========================================
# DATABASE SEMENTARA (SESSION STATE)
# ==========================================
# 1. Database Transaksi
if 'df_transaksi' not in st.session_state:
    st.session_state['df_transaksi'] = pd.DataFrame(columns=["Tanggal", "Kategori", "Jenis", "Sumber Dana", "Nominal"])

# 2. Database Saldo Portofolio (Bisa kamu ganti nilai awalnya jika mau)
if 'portofolio' not in st.session_state:
    st.session_state['portofolio'] = {
        "BCA": 1500000,
        "BRI": 500000,
        "Bank Jago": 2500000,
        "Dompet (Cash)": 300000
    }

# ==========================================
# MEMBUAT TAB MENU
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Portofolio", "📈 Analisis Saham", "🧾 Scan Struk"])

# ==========================================
# TAB 1: DASHBOARD & PORTOFOLIO
# ==========================================
with tab1:
    df = st.session_state['df_transaksi']
    porto = st.session_state['portofolio']
    
    # --- SECTION 1: PORTOFOLIO KEKAYAAN ---
    st.subheader("💳 Portofolio & Aset Saat Ini")
    total_kekayaan = sum(porto.values())
    
    # Layout Metrik Portofolio
    col_tot, col_bca, col_bri, col_jago, col_cash = st.columns(5)
    col_tot.metric(label="🌟 TOTAL KEKAYAAN", value=f"Rp {total_kekayaan:,.0f}")
    col_bca.metric(label="🔵 BCA", value=f"Rp {porto['BCA']:,.0f}")
    col_bri.metric(label="🟠 BRI", value=f"Rp {porto['BRI']:,.0f}")
    col_jago.metric(label="🟡 Bank Jago", value=f"Rp {porto['Bank Jago']:,.0f}")
    col_cash.metric(label="💵 Dompet (Cash)", value=f"Rp {porto['Dompet (Cash)']:,.0f}")
    
    st.markdown("---")
    
    # --- SECTION 2: INPUT TRANSAKSI & GRAFIK ---
    col_kiri, col_kanan = st.columns([1, 2])
    
    with col_kiri:
        st.subheader("➕ Tambah Transaksi")
        with st.form("form_transaksi", clear_on_submit=True):
            input_tanggal = st.date_input("Tanggal", date.today())
            input_kategori = st.selectbox("Kategori", ["Gaji", "Makan & Minum", "Transportasi", "Investasi", "Lainnya"])
            input_jenis = st.radio("Jenis Transaksi", ["Pemasukan", "Pengeluaran"], horizontal=True)
            
            # Pilihan rekening yang akan bertambah/berkurang saldonya
            input_sumber = st.selectbox("Sumber Dana / Tujuan Simpanan", ["BCA", "BRI", "Bank Jago", "Dompet (Cash)"])
            
            input_nominal = st.number_input("Nominal (Rp)", min_value=0, step=10000)
            submit_btn = st.form_submit_button("Simpan Data")
            
            if submit_btn:
                if input_nominal > 0:
                    # Logika Pemotongan/Penambahan Saldo
                    if input_jenis == "Pemasukan":
                        st.session_state['portofolio'][input_sumber] += input_nominal
                    elif input_jenis == "Pengeluaran":
                        # Cek apakah saldo cukup
                        if st.session_state['portofolio'][input_sumber] >= input_nominal:
                            st.session_state['portofolio'][input_sumber] -= input_nominal
                        else:
                            st.error(f"❌ Saldo {input_sumber} tidak cukup untuk transaksi ini!")
                            st.stop() # Hentikan proses jika saldo kurang
                    
                    # Simpan Riwayat
                    data_baru = pd.DataFrame([{
                        "Tanggal": input_tanggal, 
                        "Kategori": input_kategori, 
                        "Jenis": input_jenis, 
                        "Sumber Dana": input_sumber,
                        "Nominal": input_nominal
                    }])
                    st.session_state['df_transaksi'] = pd.concat([st.session_state['df_transaksi'], data_baru], ignore_index=True)
                    st.success("Transaksi berhasil dicatat dan saldo otomatis diupdate!")
                    st.rerun() # Refresh tampilan

    with col_kanan:
        st.subheader("📈 Distribusi Aset")
        # Menampilkan Grafik Donut dari Saldo Portofolio
        df_porto = pd.DataFrame(list(porto.items()), columns=['Rekening', 'Saldo'])
        
        fig_porto = px.pie(df_porto, values='Saldo', names='Rekening', hole=0.4,
                           color='Rekening',
                           color_discrete_map={
                               'BCA':'#0066AE', 
                               'BRI':'#F26522', 
                               'Bank Jago':'#F4A300', 
                               'Dompet (Cash)':'#27AE60'})
        fig_porto.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_porto, use_container_width=True)

    # --- SECTION 3: TABEL RIWAYAT TRANSAKSI ---
    st.subheader("📋 Riwayat Transaksi")
    if not df.empty:
        st.dataframe(df.style.format({"Nominal": "Rp {:,.0f}"}), use_container_width=True)
        
        if st.button("🗑️ Reset Semua Data Transaksi"):
            st.session_state['df_transaksi'] = pd.DataFrame(columns=["Tanggal", "Kategori", "Jenis", "Sumber Dana", "Nominal"])
            # Reset Saldo ke awal
            st.session_state['portofolio'] = {"BCA": 1500000, "BRI": 500000, "Bank Jago": 2500000, "Dompet (Cash)": 300000}
            st.rerun()

# ==========================================
# TAB 2: ANALISIS SAHAM
# ==========================================
with tab2:
    st.header("Grafik Saham & Sinyal RSI Otomatis")
    col_search, _ = st.columns([1, 2])
    with col_search:
        ticker = st.text_input("Kode Saham (Contoh: BBCA.JK)", "BBCA.JK")
    
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="6mo")
        
        if len(data) > 0:
            data['RSI'] = ta.rsi(data['Close'], length=14)
            
            fig_stock = go.Figure(data=[go.Candlestick(
                x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Harga"
            )])
            fig_stock.update_layout(title=f"Pergerakan Saham {ticker.upper()}", xaxis_rangeslider_visible=False, height=500)
            st.plotly_chart(fig_stock, use_container_width=True)
            
            if data['RSI'].count() > 0:
                latest_rsi = float(data['RSI'].dropna().iloc[-1])
                st.metric(label="Indikator RSI (14 Hari)", value=f"{latest_rsi:.2f}")
                
                if latest_rsi < 30: 
                    st.success("🔔 **Sinyal: OVERSOLD** - Potensi harga naik (Momentum Beli)")
                elif latest_rsi > 70: 
                    st.error("🔔 **Sinyal: OVERBOUGHT** - Potensi harga turun (Momentum Jual)")
                else:
                    st.info("🔔 **Sinyal: NETRAL** - Pergerakan harga stabil")
            else:
                st.warning("Data belum cukup untuk kalkulasi RSI.")
        else:
            st.error("❌ Data tidak ditemukan. Cek kembali kode saham.")
    except Exception as e:
        st.error(f"Sistem sedang mengalami gangguan jaringan: {e}")

# ==========================================
# TAB 3: SCAN STRUK OCR
# ==========================================
with tab3:
    st.header("Scanner Struk Otomatis")
    st.write("Teknologi OCR untuk mengekstraksi teks dari gambar struk belanja.")
    
    col_upload, col_hasil = st.columns(2)
    
    with col_upload:
        uploaded_file = st.file_uploader("Upload Foto Struk (JPG/PNG)", type=["jpg", "png", "jpeg"])
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Preview Dokumen", use_container_width=True)
            
            if st.button("🔍 Ekstrak Teks Sekarang", type="primary", use_container_width=True):
                with col_hasil:
                    with st.spinner("Memproses gambar dengan Tesseract OCR..."):
                        try:
                            extracted_text = pytesseract.image_to_string(image)
                            st.success("✅ Ekstraksi Selesai!")
                            st.text_area("Hasil Teks:", extracted_text, height=400)
                        except Exception as e:
                            st.error("❌ Mesin OCR gagal membaca gambar.")
