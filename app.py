import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from PIL import Image
import pytesseract
import sqlite3
import datetime

# --- DATABASE SETUP ---
conn = sqlite3.connect('finance_pro.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS transactions 
             (id INTEGER PRIMARY KEY, date TEXT, desc TEXT, category TEXT, amount REAL)''')
conn.commit()

# --- KONFIGURASI ---
st.set_page_config(page_title="Finance Pro Master v2", layout="wide")

# --- FITUR 1: ADVANCED AI CLASSIFIER ---
def advanced_ai_classifier(text):
    text = text.lower()
    # Logika berbasis bobot kata (Bisa dikembangkan ke ML Scikit-Learn nantinya)
    mapping = {
        'Konsumsi': ['makan', 'minum', 'nasi', 'kopi', 'warung', 'gojek', 'grab'],
        'Transportasi': ['bensin', 'pertamina', 'parkir', 'service', 'oli'],
        'Edukasi': ['buku', 'ukt', 'ppns', 'fotocopy', 'kursus'],
        'Investasi': ['saham', 'crypto', 'reksadana', 'bibit'],
        'Kebutuhan': ['listrik', 'token', 'kos', 'sabun', 'belanja']
    }
    for category, keywords in mapping.items():
        if any(key in text for key in keywords):
            return category
    return "Lain-lain"

# --- SIDEBAR: INPUT CERDAS ---
st.sidebar.header("📥 Input Transaksi")
with st.sidebar.expander("Manual Entry", expanded=True):
    input_desc = st.text_input("Deskripsi")
    input_amount = st.number_input("Nominal (Rp)", min_value=0, step=5000)
    input_date = st.date_input("Tanggal", datetime.date.today())
    
    if input_desc:
        suggested_cat = advanced_ai_classifier(input_desc)
        st.caption(f"🤖 AI Suggestion: **{suggested_cat}**")
    
    if st.button("Simpan ke Database"):
        c.execute("INSERT INTO transactions (date, desc, category, amount) VALUES (?,?,?,?)", 
                  (input_date, input_desc, advanced_ai_classifier(input_desc), input_amount))
        conn.commit()
        st.sidebar.success("Data Berhasil Disimpan!")

# --- MAIN INTERFACE ---
st.title("🚀 Finance Pro Master v2")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "💹 Stock Analysis", "🔍 OCR Scanner", "📜 History"])

# TAB 1: DASHBOARD INTERAKTIF
with tab1:
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    if not df.empty:
        st.subheader("Financial Overview")
        col1, col2, col3 = st.columns(3)
        total_spent = df['amount'].sum()
        col1.metric("Total Pengeluaran", f"Rp {total_spent:,.0f}")
        col2.metric("Transaksi Terbanyak", df['category'].mode()[0])
        col3.metric("Rata-rata Harian", f"Rp {total_spent/30:,.0f}")

        # Grafik Pengeluaran per Kategori
        fig = go.Figure(data=[go.Pie(labels=df['category'], values=df['amount'], hole=.4)])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Belum ada data di database.")

# TAB 2: STOCK ANALYSIS (FITUR 3 - ADVANCED)
with tab2:
    st.subheader("Professional Stock Monitor")
    symbol = st.text_input("Kode Saham (e.g., BBRI.JK, ASII.JK)", "BBCA.JK")
    if symbol:
        stock_data = yf.download(symbol, period="6mo", interval="1d")
        
        # Tambahkan RSI (Relative Strength Index)
        stock_data['RSI'] = ta.rsi(stock_data['Close'], length=14)
        
        # Plot Candlestick
        fig_stock = go.Figure(data=[go.Candlestick(x=stock_data.index,
                        open=stock_data['Open'], high=stock_data['High'],
                        low=stock_data['Low'], close=stock_data['Close'], name='Price')])
        
        st.plotly_chart(fig_stock, use_container_width=True)
        
        # Signal Canggih
        latest_rsi = stock_data['RSI'].iloc[-1]
        st.write(f"**RSI Saat Ini: {latest_rsi:.2f}**")
        if latest_rsi < 30:
            st.success("💡 Signal: **OVERSOLD** (Potensi Rebound/Beli)")
        elif latest_rsi > 70:
            st.error("⚠️ Signal: **OVERBOUGHT** (Potensi Koreksi/Jual)")
        else:
            st.info("💡 Signal: **NEUTRAL**")



# TAB 3: OCR SCANNER (FITUR 5)
with tab3:
    st.subheader("AI Receipt Scanner")
    uploaded_file = st.file_uploader("Upload Struk Belanja", type=['jpg', 'jpeg', 'png'])
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Struk Anda", width=400)
        
        if st.button("Extract Data"):
            with st.spinner("AI sedang membaca struk..."):
                raw_text = pytesseract.image_to_string(img)
                st.text_area("Hasil Scan:", raw_text, height=150)
                st.info("Tips: Salin nominal dari teks di atas ke menu sidebar.")



# TAB 4: HISTORY & DELETE
with tab4:
    st.subheader("Riwayat Transaksi Lengkap")
    history_df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC", conn)
    st.dataframe(history_df, use_container_width=True)
    if st.button("Hapus Semua Data (Reset)"):
        c.execute("DELETE FROM transactions")
        conn.commit()
        st.rerun()