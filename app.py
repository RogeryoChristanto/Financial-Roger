import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import pytesseract
from PIL import Image

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Finance Pro Master", page_icon="📈", layout="wide")

st.title("📈 Finance Pro Master v2")
st.write("Sistem manajemen keuangan dan analisis teknikal otomatis.")

# --- MEMBUAT TAB MENU ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard Keuangan", "📈 Analisis Saham", "🧾 Scan Struk"])

# ==========================================
# TAB 1: DASHBOARD KEUANGAN
# ==========================================
with tab1:
    st.header("Catatan Transaksi")
    
    # Contoh data dummy (Tabel awal)
    data_transaksi = pd.DataFrame({
        "Tanggal": ["2026-04-01", "2026-04-02", "2026-04-03"],
        "Kategori": ["Gaji Bulanan", "Makan Siang", "Transport"],
        "Jenis": ["Pemasukan", "Pengeluaran", "Pengeluaran"],
        "Nominal (Rp)": [5000000, 45000, 20000]
    })
    
    st.dataframe(data_transaksi, use_container_width=True)

# ==========================================
# TAB 2: ANALISIS SAHAM (SUDAH DIPERBAIKI)
# ==========================================
with tab2:
    st.header("Grafik Saham & Sinyal RSI")
    ticker = st.text_input("Masukkan Kode Saham (Contoh: BBRI.JK atau BBCA.JK)", "BBCA.JK")
    
    try:
        # Mengambil data saham 6 bulan terakhir
        stock = yf.Ticker(ticker)
        data = stock.history(period="6mo")
        
        if len(data) > 0:
            # Menghitung Indikator RSI (Relative Strength Index)
            data['RSI'] = ta.rsi(data['Close'], length=14)
            
            # Membuat Visualisasi Candlestick dengan Plotly
            fig_stock = go.Figure(data=[go.Candlestick(
                x=data.index, 
                open=data['Open'], 
                high=data['High'], 
                low=data['Low'], 
                close=data['Close'],
                name="Harga"
            )])
            fig_stock.update_layout(title=f"Pergerakan Saham {ticker.upper()}", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_stock, use_container_width=True)
            
            # Membaca sinyal RSI terbaru
            if data['RSI'].count() > 0:
                # Memaksa format data menjadi desimal murni
                latest_rsi = float(data['RSI'].dropna().iloc[-1])
                st.write(f"RSI Saat Ini: **{latest_rsi:.2f}**")
                
                # Logika Trading Sederhana
                if latest_rsi < 30: 
                    st.success("🔔 Sinyal: OVERSOLD (Banyak yang jual, potensi harga naik -> Waktunya Beli)")
                elif latest_rsi > 70: 
                    st.error("🔔 Sinyal: OVERBOUGHT (Banyak yang beli, potensi harga turun -> Waktunya Jual)")
                else:
                    st.info("🔔 Sinyal: NETRAL (Tahan posisi)")
            else:
                st.warning("Data belum cukup untuk menghitung RSI (Minimal butuh 14 hari perdagangan).")
        else:
            st.error("❌ Data tidak ditemukan. Pastikan kode saham benar dan tambahkan .JK untuk saham Indonesia.")
            
    except Exception as e:
        st.error(f"Terjadi kesalahan pada sistem saham: {e}")

# ==========================================
# TAB 3: SCAN STRUK OCR
# ==========================================
with tab3:
    st.header("Fitur Scan Struk Otomatis")
    st.info("Upload foto struk belanja untuk membaca teksnya secara otomatis.")
    
    uploaded_file = st.file_uploader("Pilih Foto (JPG/PNG)", type=["jpg", "png", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        # Menampilkan gambar dengan ukuran yang disesuaikan
        st.image(image, caption="Foto yang diupload", width=400)
        
        if st.button("🔍 Scan Teks Sekarang"):
            with st.spinner("Sedang membaca teks..."):
                try:
                    # Proses mengubah gambar menjadi teks (OCR)
                    extracted_text = pytesseract.image_to_string(image)
                    
                    st.success("✅ Berhasil membaca dokumen!")
                    st.text_area("Hasil Ekstraksi Teks:", extracted_text, height=250)
                except Exception as e:
                    st.error("❌ Gagal membaca gambar.")
                    st.warning("Pastikan file packages.txt sudah berisi 'tesseract-ocr' dan 'libtesseract-dev'.")
