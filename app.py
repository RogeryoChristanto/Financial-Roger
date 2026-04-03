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
st.set_page_config(page_title="Finance Pro Master", page_icon="💼", layout="wide")

hide_st_style = """<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>"""
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title("💼 Finance Pro Master: Cloud Edition")
st.markdown("Sistem manajemen kekayaan dengan Cloud Database, multi-rekening, dan portofolio saham real-time.")
st.divider()

# ==========================================
# KONEKSI KE GOOGLE SHEETS CLOUD
# ==========================================
@st.cache_resource
def init_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_JSON"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("Database Finance Pro") # Pastikan nama file GSheets persis ini!

try:
    db = init_connection()
    ws_transaksi = db.worksheet("Transaksi")
    ws_saham = db.worksheet("Saham")
except Exception as e:
    st.error(f"❌ Gagal terhubung ke Database Google Sheets. Cek kembali penamaan Sheet atau isi Secrets. Error: {e}")
    st.stop()

# Tarik data dari Cloud ke DataFrame
df_transaksi = get_as_dataframe(ws_transaksi).dropna(how='all').dropna(axis=1, how='all')
df_saham = get_as_dataframe(ws_saham).dropna(how='all').dropna(axis=1, how='all')

# Format dasar jika Sheet benar-benar kosong
if df_transaksi.empty or len(df_transaksi.columns) < 5:
    df_transaksi = pd.DataFrame(columns=["Tanggal", "Kategori", "Jenis", "Sumber Dana", "Nominal"])
if df_saham.empty or len(df_saham.columns) < 3:
    df_saham = pd.DataFrame(columns=["Ticker", "Harga Beli", "Jumlah Lembar"])

# ==========================================
# AUTO-KALKULASI SALDO (SINGLE SOURCE OF TRUTH)
# ==========================================
porto = {"BCA": 0, "BRI": 0, "Bank Jago": 0, "Dompet (Cash)": 0}
if not df_transaksi.empty:
    for _, row in df_transaksi.iterrows():
        sumber = str(row['Sumber Dana'])
        try:
            nom = float(row['Nominal'])
        except:
            nom = 0
            
        if sumber in porto:
            if row['Jenis'] == "Pemasukan":
                porto[sumber] += nom
            elif row['Jenis'] == "Pengeluaran":
                porto[sumber] -= nom

# ==========================================
# MESIN SAHAM REAL-TIME
# ==========================================
total_nilai_saham = 0
harga_sekarang_dict = {}

if not df_saham.empty:
    try:
        kurs_usd = yf.Ticker("USDIDR=X").history(period="1d")['Close'].iloc[-1]
    except:
        kurs_usd = 15800 

    for t in df_saham['Ticker'].unique():
        t = str(t).upper()
        if t != "NAN" and t != "":
            try:
                current_price = yf.Ticker(t).history(period="1d")['Close'].iloc[-1]
                if not t.endswith('.JK'):
                    current_price = current_price * kurs_usd
                harga_sekarang_dict[t] = current_price
            except:
                harga_sekarang_dict[t] = 0

    for _, row in df_saham.iterrows():
        try:
            hb = float(row['Harga Beli'])
            jl = float(row['Jumlah Lembar'])
            t = str(row['Ticker']).upper()
            cp = harga_sekarang_dict.get(t, hb)
            total_nilai_saham += (cp * jl)
        except:
            pass

# ==========================================
# MEMBUAT TAB MENU
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Kekayaan", "📈 Portofolio & Analisis Saham", "🧾 Scan Struk"])

# ==========================================
# TAB 1: DASHBOARD & KEKAYAAN
# ==========================================
with tab1:
    total_uang_fiat = sum(porto.values())
    total_kekayaan = total_uang_fiat + total_nilai_saham
    
    st.subheader("💳 Ringkasan Kekayaan Bersih (Net Worth)")
    col_tot, col_fiat, col_saham = st.columns(3)
    col_tot.metric(label="🌟 TOTAL KEKAYAAN BERSIH", value=f"Rp {total_kekayaan:,.0f}")
    col_fiat.metric(label="💵 Total Uang Kas & Bank", value=f"Rp {total_uang_fiat:,.0f}")
    col_saham.metric(label="📈 Total Nilai Saham (Real-Time)", value=f"Rp {total_nilai_saham:,.0f}")
    
    st.markdown("<small>Rincian Saldo Bank & Tunai:</small>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.info(f"**BCA:** Rp {porto['BCA']:,.0f}")
    c2.info(f"**BRI:** Rp {porto['BRI']:,.0f}")
    c3.info(f"**Bank Jago:** Rp {porto['Bank Jago']:,.0f}")
    c4.info(f"**Dompet:** Rp {porto['Dompet (Cash)']:,.0f}")
    
    st.markdown("---")
    
    col_kiri, col_kanan = st.columns([1, 2])
    
    with col_kiri:
        st.subheader("➕ Transaksi Baru")
        with st.form("form_transaksi", clear_on_submit=True):
            input_tanggal = st.date_input("Tanggal", date.today())
            input_kategori = st.selectbox("Kategori", ["Gaji", "Makan & Minum", "Transportasi", "Pendidikan", "Investasi Saham", "Lainnya"])
            input_jenis = st.radio("Jenis Transaksi", ["Pemasukan", "Pengeluaran"], horizontal=True)
            input_sumber = st.selectbox("Sumber Dana (Dompet/Bank)", ["BCA", "BRI", "Bank Jago", "Dompet (Cash)"])
            input_nominal = st.number_input("Nominal (Rp)", min_value=0.0, step=10000.0)
            submit_btn = st.form_submit_button("Simpan Transaksi")
            
            if submit_btn and input_nominal > 0:
                if input_jenis == "Pengeluaran" and porto.get(input_sumber, 0) < input_nominal:
                    st.error(f"❌ Ditolak: Saldo {input_sumber} tidak cukup!")
                    st.stop()
                
                data_baru = pd.DataFrame([{"Tanggal": str(input_tanggal), "Kategori": input_kategori, "Jenis": input_jenis, "Sumber Dana": input_sumber, "Nominal": input_nominal}])
                df_update = pd.concat([df_transaksi, data_baru], ignore_index=True)
                
                with st.spinner("Menyimpan ke Google Sheets..."):
                    ws_transaksi.clear()
                    set_with_dataframe(ws_transaksi, df_update)
                st.success("Tersimpan di Cloud!")
                st.rerun()

    with col_kanan:
        st.subheader("📊 Analisis Keuangan")
        tab_grafik1, tab_grafik2 = st.tabs(["📉 Arus Kas", "🥧 Alokasi Aset"])
        
        with tab_grafik1:
            if not df_transaksi.empty:
                df_cashflow = df_transaksi.copy()
                df_cashflow['Nominal'] = pd.to_numeric(df_cashflow['Nominal'], errors='coerce')
                df_cf_group = df_cashflow.groupby('Jenis')['Nominal'].sum().reset_index()
                fig_cf = px.bar(df_cf_group, x='Jenis', y='Nominal', color='Jenis',
                                color_discrete_map={'Pemasukan':'#2ecc71', 'Pengeluaran':'#e74c3c'},
                                text='Nominal', title="Perbandingan Masuk & Keluar")
                fig_cf.update_traces(texttemplate='Rp %{text:,.0f}', textposition='outside')
                fig_cf.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', height=350)
                st.plotly_chart(fig_cf, use_container_width=True)
                
        with tab_grafik2:
            aset_dict = porto.copy()
            aset_dict["Portofolio Saham"] = total_nilai_saham
            df_aset = pd.DataFrame(list(aset_dict.items()), columns=['Aset', 'Nilai'])
            df_aset = df_aset[df_aset['Nilai'] > 0] 
            
            if not df_aset.empty:
                fig_porto = px.pie(df_aset, values='Nilai', names='Aset', hole=0.4, color='Aset',
                                   color_discrete_map={'BCA':'#0066AE', 'BRI':'#F26522', 'Bank Jago':'#F4A300', 'Dompet (Cash)':'#27AE60', 'Portofolio Saham':'#8E44AD'})
                fig_porto.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=350)
                st.plotly_chart(fig_porto, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Riwayat Transaksi (Edit & Hapus)")
    st.info("💡 Edit angka langsung pada tabel, atau centang kotak di kiri untuk menghapus. Jangan lupa klik tombol Simpan di bawah!")
    
    edited_df_t = st.data_editor(df_transaksi, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Simpan Perubahan Database Transaksi", type="primary"):
        with st.spinner("Mengupdate Cloud..."):
            ws_transaksi.clear()
            set_with_dataframe(ws_transaksi, edited_df_t)
        st.success("Database berhasil di-update!")
        st.rerun()

# ==========================================
# TAB 2: PORTOFOLIO & ANALISIS SAHAM
# ==========================================
with tab2:
    st.header("💼 Portofolio Saham (Terhubung ke Cloud)")
    col_in_saham, col_tb_saham = st.columns([1, 2.5])
    
    with col_in_saham:
        st.subheader("➕ Beli Saham")
        with st.form("form_saham", clear_on_submit=True):
            in_ticker = st.text_input("Kode Saham (Misal BELL.JK)", "BELL.JK").upper()
            in_harga_beli = st.number_input("Harga Beli PER 1 LEMBAR (Rp)", min_value=1.0, step=1.0)
            in_lot = st.number_input("Jumlah Beli (Berapa Lot?)", min_value=1, step=1)
            
            if st.form_submit_button("Tambahkan Saham"):
                in_lembar = in_lot * 100 
                saham_baru = pd.DataFrame([{"Ticker": in_ticker, "Harga Beli": in_harga_beli, "Jumlah Lembar": in_lembar}])
                df_s_update = pd.concat([df_saham, saham_baru], ignore_index=True)
                
                with st.spinner("Mencatat ke Google Sheets..."):
                    ws_saham.clear()
                    set_with_dataframe(ws_saham, df_s_update)
                st.success(f"Saham tersimpan!")
                st.rerun()
                
    with col_tb_saham:
        st.write("**Data Master Saham (Edit / Hapus di sini):**")
        edited_df_s = st.data_editor(df_saham, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Simpan Perubahan Database Saham", type="primary"):
            with st.spinner("Mengupdate Cloud..."):
                ws_saham.clear()
                set_with_dataframe(ws_saham, edited_df_s)
            st.success("Database Saham di-update!")
            st.rerun()

        st.markdown("---")
        st.write("**Kalkulasi Real-Time (Tidak dapat diedit):**")
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
                    
                    display_data.append({
                        "Kode": t,
                        "Lot": f"{jl/100:.0f}",
                        "Beli/Lbr": f"Rp {hb:,.0f}",
                        "Harga Saat Ini": f"Rp {cp:,.0f}",
                        "Total Aset": f"Rp {nilai_sekarang:,.0f}",
                        "Return": f"{profit_pct:.2f}%"
                    })
                except:
                    pass
            if display_data:
                st.dataframe(pd.DataFrame(display_data), use_container_width=True)

    st.markdown("---")
    st.header("📈 Analisis Teknikal Saham")
    ticker_analisis = st.text_input("Cari Saham (Contoh: BBRI.JK)", "BELL.JK").upper()
    try:
        stock = yf.Ticker(ticker_analisis)
        data = stock.history(period="6mo")
        if len(data) > 0:
            data['RSI'] = ta.rsi(data['Close'], length=14)
            fig_stock = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
            fig_stock.update_layout(title=f"Pergerakan {ticker_analisis}", xaxis_rangeslider_visible=False, height=400)
            st.plotly_chart(fig_stock, use_container_width=True)
            
            if data['RSI'].count() > 0:
                latest_rsi = float(data['RSI'].dropna().iloc[-1])
                st.metric(label="RSI (14 Hari)", value=f"{latest_rsi:.2f}")
                if latest_rsi < 30: st.success("🔔 Sinyal: OVERSOLD (Murah)")
                elif latest_rsi > 70: st.error("🔔 Sinyal: OVERBOUGHT (Mahal)")
                else: st.info("🔔 Sinyal: NETRAL")
    except:
        st.error("Gagal menarik data.")

# ==========================================
# TAB 3: SCAN STRUK OCR
# ==========================================
with tab3:
    st.header("Scanner Struk Otomatis")
    col_upload, col_hasil = st.columns(2)
    with col_upload:
        uploaded_file = st.file_uploader("Upload Foto Struk (JPG/PNG)", type=["jpg", "png", "jpeg"])
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Preview Dokumen", use_container_width=True)
            
            if st.button("🔍 Ekstrak Teks Sekarang", type="primary", use_container_width=True):
                with col_hasil:
                    with st.spinner("Membaca teks..."):
                        try:
                            extracted_text = pytesseract.image_to_string(image)
                            st.success("✅ Selesai!")
                            st.text_area("Hasil:", extracted_text, height=400)
                        except Exception as e:
                            st.error("❌ Mesin OCR gagal membaca gambar.")
