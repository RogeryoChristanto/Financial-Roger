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

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title("💼 Finance Pro Master: Wealth Dashboard")
st.markdown("Sistem manajemen kekayaan cerdas, integrasi multi-rekening, dan portofolio saham real-time.")
st.divider()

# ==========================================
# DATABASE SEMENTARA (SESSION STATE) - DATA BERSIH (NOL)
# ==========================================
if 'df_transaksi' not in st.session_state:
    st.session_state['df_transaksi'] = pd.DataFrame(columns=["Tanggal", "Kategori", "Jenis", "Sumber Dana", "Nominal"])

if 'portofolio' not in st.session_state:
    st.session_state['portofolio'] = {
        "BCA": 0,
        "BRI": 0,
        "Bank Jago": 0,
        "Dompet (Cash)": 0
    }

if 'df_saham' not in st.session_state:
    st.session_state['df_saham'] = pd.DataFrame(columns=["Ticker", "Harga Beli", "Jumlah Lembar"])

# ==========================================
# PERHITUNGAN SAHAM REAL-TIME (GLOBAL)
# ==========================================
total_nilai_saham = 0
df_saham = st.session_state['df_saham']
harga_sekarang_dict = {}

if not df_saham.empty:
    for t in df_saham['Ticker'].unique():
        try:
            current_price = yf.Ticker(t).history(period="1d")['Close'].iloc[-1]
            harga_sekarang_dict[t] = current_price
        except:
            harga_sekarang_dict[t] = 0

    for _, row in df_saham.iterrows():
        cp = harga_sekarang_dict.get(row['Ticker'], row['Harga Beli'])
        total_nilai_saham += (cp * row['Jumlah Lembar'])

# ==========================================
# MEMBUAT TAB MENU
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Kekayaan", "📈 Portofolio & Analisis Saham", "🧾 Scan Struk"])

# ==========================================
# TAB 1: DASHBOARD & KEKAYAAN
# ==========================================
with tab1:
    df = st.session_state['df_transaksi']
    porto = st.session_state['portofolio']
    
    # --- SECTION 1: PORTOFOLIO KEKAYAAN ---
    st.subheader("💳 Ringkasan Kekayaan Bersih (Net Worth)")
    total_uang_fiat = sum(porto.values())
    total_kekayaan = total_uang_fiat + total_nilai_saham
    
    col_tot, col_fiat, col_saham = st.columns(3)
    col_tot.metric(label="🌟 TOTAL KEKAYAAN BERSIH", value=f"Rp {total_kekayaan:,.0f}")
    col_fiat.metric(label="💵 Total Uang Kas & Bank", value=f"Rp {total_uang_fiat:,.0f}")
    col_saham.metric(label="📈 Total Nilai Saham (Real-Time)", value=f"Rp {total_nilai_saham:,.0f}")
    
    # Sub-Metrik Saldo Masing-masing Bank
    st.markdown("<small>Rincian Saldo Bank & Tunai:</small>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.info(f"**BCA:** Rp {porto['BCA']:,.0f}")
    c2.info(f"**BRI:** Rp {porto['BRI']:,.0f}")
    c3.info(f"**Bank Jago:** Rp {porto['Bank Jago']:,.0f}")
    c4.info(f"**Dompet:** Rp {porto['Dompet (Cash)']:,.0f}")
    
    st.markdown("---")
    
    # --- SECTION 2: INPUT TRANSAKSI & GRAFIK ---
    col_kiri, col_kanan = st.columns([1, 2])
    
    with col_kiri:
        st.subheader("➕ Transaksi Uang Kas")
        with st.form("form_transaksi", clear_on_submit=True):
            input_tanggal = st.date_input("Tanggal", date.today())
            input_kategori = st.selectbox("Kategori", ["Gaji", "Makan & Minum", "Transportasi", "Pendidikan", "Investasi", "Lainnya"])
            input_jenis = st.radio("Jenis Transaksi", ["Pemasukan", "Pengeluaran"], horizontal=True)
            input_sumber = st.selectbox("Sumber Dana (Dompet/Bank)", ["BCA", "BRI", "Bank Jago", "Dompet (Cash)"])
            input_nominal = st.number_input("Nominal (Rp)", min_value=0, step=10000)
            submit_btn = st.form_submit_button("Simpan Transaksi")
            
            if submit_btn and input_nominal > 0:
                if input_jenis == "Pemasukan":
                    st.session_state['portofolio'][input_sumber] += input_nominal
                elif input_jenis == "Pengeluaran":
                    # Cegah saldo minus
                    if st.session_state['portofolio'][input_sumber] >= input_nominal:
                        st.session_state['portofolio'][input_sumber] -= input_nominal
                    else:
                        st.error(f"❌ Transaksi Ditolak: Saldo {input_sumber} tidak cukup!")
                        st.stop()
                
                data_baru = pd.DataFrame([{"Tanggal": input_tanggal, "Kategori": input_kategori, "Jenis": input_jenis, "Sumber Dana": input_sumber, "Nominal": input_nominal}])
                st.session_state['df_transaksi'] = pd.concat([st.session_state['df_transaksi'], data_baru], ignore_index=True)
                st.rerun()

    with col_kanan:
        st.subheader("📊 Analisis Keuangan")
        
        tab_grafik1, tab_grafik2 = st.tabs(["📉 Arus Kas (Masuk vs Keluar)", "🥧 Alokasi Aset"])
        
        with tab_grafik1:
            if not df.empty:
                df_cashflow = df.groupby('Jenis')['Nominal'].sum().reset_index()
                fig_cf = px.bar(df_cashflow, x='Jenis', y='Nominal', color='Jenis',
                                color_discrete_map={'Pemasukan':'#2ecc71', 'Pengeluaran':'#e74c3c'},
                                text='Nominal', title="Perbandingan Pemasukan & Pengeluaran")
                fig_cf.update_traces(texttemplate='Rp %{text:,.0f}', textposition='outside')
                fig_cf.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', height=350)
                st.plotly_chart(fig_cf, use_container_width=True)
            else:
                st.info("Belum ada data transaksi untuk menampilkan grafik arus kas.")
                
        with tab_grafik2:
            aset_dict = porto.copy()
            aset_dict["Portofolio Saham"] = total_nilai_saham
            df_aset = pd.DataFrame(list(aset_dict.items()), columns=['Aset', 'Nilai'])
            df_aset = df_aset[df_aset['Nilai'] > 0] 
            
            if not df_aset.empty:
                fig_porto = px.pie(df_aset, values='Nilai', names='Aset', hole=0.4,
                                   color='Aset',
                                   color_discrete_map={'BCA':'#0066AE', 'BRI':'#F26522', 'Bank Jago':'#F4A300', 'Dompet (Cash)':'#27AE60', 'Portofolio Saham':'#8E44AD'})
                fig_porto.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=350)
                st.plotly_chart(fig_porto, use_container_width=True)
            else:
                st.info("Sistem akan menampilkan grafik donat setelah Anda memiliki saldo di aset Anda.")

    # --- SECTION 3: TABEL RIWAYAT TRANSAKSI ---
    st.markdown("---")
    st.subheader("📋 Riwayat Transaksi")
    if not df.empty:
        st.dataframe(df.style.format({"Nominal": "Rp {:,.0f}"}), use_container_width=True)
        
        if st.button("⚠️ Hapus & Reset Semua Transaksi (Mulai dari Nol)"):
            st.session_state['df_transaksi'] = pd.DataFrame(columns=["Tanggal", "Kategori", "Jenis", "Sumber Dana", "Nominal"])
            st.session_state['portofolio'] = {"BCA": 0, "BRI": 0, "Bank Jago": 0, "Dompet (Cash)": 0}
            st.rerun()

# ==========================================
# TAB 2: PORTOFOLIO & ANALISIS SAHAM
# ==========================================
with tab2:
    st.header("💼 Portofolio Saham Saya (Real-Time)")
    
    col_input_saham, col_tabel_saham = st.columns([1, 2.5])
    
    with col_input_saham:
        st.subheader("➕ Beli / Tambah Saham")
        with st.form("form_saham", clear_on_submit=True):
            in_ticker = st.text_input("Kode Saham (wajib pakai .JK, misal BBCA.JK)", "BBCA.JK").upper()
            in_harga_beli = st.number_input("Harga Beli Rata-Rata (Rp)", min_value=1.0, step=10.0)
            in_lembar = st.number_input("Jumlah Lembar (1 Lot = 100 Lembar)", min_value=1, step=100)
            
            submit_saham = st.form_submit_button("Tambahkan ke Portofolio")
            if submit_saham:
                saham_baru = pd.DataFrame([{"Ticker": in_ticker, "Harga Beli": in_harga_beli, "Jumlah Lembar": in_lembar}])
                st.session_state['df_saham'] = pd.concat([st.session_state['df_saham'], saham_baru], ignore_index=True)
                st.success(f"{in_ticker} berhasil ditambahkan!")
                st.rerun()
                
    with col_tabel_saham:
        if not df_saham.empty:
            display_data = []
            for _, row in df_saham.iterrows():
                t = row['Ticker']
                hb = row['Harga Beli']
                jl = row['Jumlah Lembar']
                cp = harga_sekarang_dict.get(t, hb) 
                
                nilai_awal = hb * jl
                nilai_sekarang = cp * jl
                profit_rp = nilai_sekarang - nilai_awal
                profit_pct = (profit_rp / nilai_awal) * 100 if nilai_awal > 0 else 0
                
                display_data.append({
                    "Kode Saham": t,
                    "Total Lembar": jl,
                    "Harga Beli": f"Rp {hb:,.0f}",
                    "Harga Real-Time": f"Rp {cp:,.0f}",
                    "Nilai Aset": f"Rp {nilai_sekarang:,.0f}",
                    "Return": f"{profit_pct:.2f}%"
                })
            
            df_display = pd.DataFrame(display_data)
            st.dataframe(df_display, use_container_width=True)
            
            if st.button("🗑️ Jual/Reset Semua Kepemilikan Saham"):
                st.session_state['df_saham'] = pd.DataFrame(columns=["Ticker", "Harga Beli", "Jumlah Lembar"])
                st.rerun()
        else:
            st.info("Portofolio saham masih kosong. Silakan input pembelian saham di sebelah kiri.")

    st.markdown("---")
    
    st.header("📈 Analisis Teknikal Saham")
    ticker_analisis = st.text_input("Cari Saham untuk Dianalisis (Contoh: BBRI.JK)", "BBRI.JK").upper()
    try:
        stock = yf.Ticker(ticker_analisis)
        data = stock.history(period="6mo")
        if len(data) > 0:
            data['RSI'] = ta.rsi(data['Close'], length=14)
            fig_stock = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Harga")])
            fig_stock.update_layout(title=f"Pergerakan Saham {ticker_analisis}", xaxis_rangeslider_visible=False, height=400)
            st.plotly_chart(fig_stock, use_container_width=True)
            
            if data['RSI'].count() > 0:
                latest_rsi = float(data['RSI'].dropna().iloc[-1])
                st.metric(label="RSI (14 Hari)", value=f"{latest_rsi:.2f}")
                if latest_rsi < 30: st.success("🔔 Sinyal: OVERSOLD (Waktunya Beli - Harga Sedang Murah)")
                elif latest_rsi > 70: st.error("🔔 Sinyal: OVERBOUGHT (Waktunya Jual - Harga Sedang Puncak)")
                else: st.info("🔔 Sinyal: NETRAL")
        else:
            st.error("Data saham tidak ditemukan.")
    except:
        st.error("Gagal menarik data saham. Periksa koneksi atau penulisan kode saham.")

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
                    with st.spinner("Mesin AI sedang membaca teks gambar..."):
                        try:
                            extracted_text = pytesseract.image_to_string(image)
                            st.success("✅ Ekstraksi Selesai!")
                            st.text_area("Hasil Ekstraksi Teks:", extracted_text, height=400)
                        except Exception as e:
                            st.error("❌ Mesin OCR gagal membaca gambar.")
