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

# CSS Tambahan untuk menyembunyikan menu bawaan Streamlit agar terlihat seperti Web Asli
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title("💼 Finance Pro Master v2")
st.markdown("Sistem manajemen keuangan cerdas dengan integrasi analisis teknikal saham dan OCR.")
st.divider()

# ==========================================
# DATABASE SEMENTARA (SESSION STATE)
# ==========================================
# Ini agar tabel kosong di awal, tapi bisa ditambah datanya dan tidak hilang saat refresh
if 'df_transaksi' not in st.session_state:
    st.session_state['df_transaksi'] = pd.DataFrame(columns=["Tanggal", "Kategori", "Jenis", "Nominal"])

# ==========================================
# MEMBUAT TAB MENU
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 Dashboard Keuangan", "📈 Analisis Saham", "🧾 Scan Struk"])

# ==========================================
# TAB 1: DASHBOARD KEUANGAN
# ==========================================
with tab1:
    # Mengambil data dari memory
    df = st.session_state['df_transaksi']
    
    # Menghitung Total
    total_pemasukan = df[df['Jenis'] == 'Pemasukan']['Nominal'].sum() if not df.empty else 0
    total_pengeluaran = df[df['Jenis'] == 'Pengeluaran']['Nominal'].sum() if not df.empty else 0
    saldo = total_pemasukan - total_pengeluaran
    
    # 1. MENAMPILKAN METRIK KEUANGAN (Tampilan Profesional)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="💰 Total Pemasukan", value=f"Rp {total_pemasukan:,.0f}")
    with col2:
        st.metric(label="📉 Total Pengeluaran", value=f"Rp {total_pengeluaran:,.0f}")
    with col3:
        st.metric(label="💳 Saldo Saat Ini", value=f"Rp {saldo:,.0f}", delta=f"{saldo:,.0f}")
        
    st.markdown("---")
    
    # 2. MEMBAGI LAYAR: KIRI (FORM INPUT) & KANAN (GRAFIK)
    col_kiri, col_kanan = st.columns([1, 2])
    
    with col_kiri:
        st.subheader("➕ Tambah Transaksi")
        with st.form("form_transaksi", clear_on_submit=True):
            input_tanggal = st.date_input("Tanggal", date.today())
            input_kategori = st.selectbox("Kategori", ["Gaji", "Makan & Minum", "Transportasi", "Investasi", "Lainnya"])
            input_jenis = st.radio("Jenis Transaksi", ["Pemasukan", "Pengeluaran"], horizontal=True)
            input_nominal = st.number_input("Nominal (Rp)", min_value=0, step=10000)
            
            submit_btn = st.form_submit_button("Simpan Data")
            
            if submit_btn:
                # Menambah data baru ke memory
                data_baru = pd.DataFrame([{
                    "Tanggal": input_tanggal, 
                    "Kategori": input_kategori, 
                    "Jenis": input_jenis, 
                    "Nominal": input_nominal
                }])
                st.session_state['df_transaksi'] = pd.concat([st.session_state['df_transaksi'], data_baru], ignore_index=True)
                st.success("Data berhasil ditambahkan!")
                st.rerun() # Refresh agar grafik langsung update

    with col_kanan:
        st.subheader("📈 Analisis Arus Kas")
        if df.empty:
            st.info("Belum ada data transaksi. Silakan input data di sebelah kiri untuk melihat grafik.")
        else:
            # Membuat Grafik Pie (Donut Chart)
            ringkasan = df.groupby('Jenis')['Nominal'].sum().reset_index()
            fig_pie = px.pie(ringkasan, values='Nominal', names='Jenis', hole=0.4, 
                             color='Jenis', color_discrete_map={'Pemasukan':'#2ecc71', 'Pengeluaran':'#e74c3c'})
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)

    # 3. TABEL RIWAYAT TRANSAKSI
    st.subheader("📋 Riwayat Transaksi")
    if not df.empty:
        # Menampilkan tabel dengan gaya format Rupiah
        st.dataframe(df.style.format({"Nominal": "Rp {:,.0f}"}), use_container_width=True)
        
        # Tombol Hapus Data
        if st.button("🗑️ Hapus Semua Data"):
            st.session_state['df_transaksi'] = pd.DataFrame(columns=["Tanggal", "Kategori", "Jenis", "Nominal"])
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
