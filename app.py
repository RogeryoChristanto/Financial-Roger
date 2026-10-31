import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json, os, gspread, re
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

try:
    from google import genai as genai_client
    GEMINI_OK = True
except ImportError:
    GEMINI_OK = False

# ══════════════════════════════════════════
#  1. CONFIG & SESSION STATE
# ══════════════════════════════════════════
st.set_page_config(page_title="ROGER Finance", page_icon="💎", layout="wide", initial_sidebar_state="expanded")

DEFAULTS = {
    "authenticated": False, "page": "Dashboard", "hide_balance": False
}
for k, v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k] = v

CONFIG_FILE = "roger_config_v5.json"
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f: return json.load(f)
    return {
        "budgets": {"Makan & Minum": 900000, "Kebutuhan Pokok": 300000, "Transportasi": 100000},
        "kategori_list": ["Uang Saku", "Makan & Minum", "Transportasi", "Kuota Internet", "Kebutuhan Pokok", "Investasi"],
        "saved_pin": "120224"
    }

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump({"budgets": st.session_state.budgets, "kategori_list": st.session_state.kategori_list, "saved_pin": st.session_state.saved_pin}, f)

cfg = load_config()
for key in ["budgets", "kategori_list", "saved_pin"]:
    if key not in st.session_state: st.session_state[key] = cfg[key]

now = pd.Timestamp.now('Asia/Jakarta')
def fmt(v):
    if st.session_state.hide_balance: return "Rp ••••••"
    return f"Rp {v:,.0f}".replace(",", ".")

# ══════════════════════════════════════════
#  2. CSS — CLEAN ADMIN DASHBOARD
# ══════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Reset */
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background-color: #F3F4F6 !important; }

/* ── Sidebar (KOSKU Style) ── */
[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E5E7EB !important; padding-top: 20px !important; }
[data-testid="stSidebarNav"] { display: none !important; } /* Sembunyikan default nav */

/* ── Cards & Metrics ── */
div[data-testid="metric-container"], .clean-card {
    background: #FFFFFF !important; border: 1px solid #E5E7EB !important;
    border-radius: 12px !important; padding: 20px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
div[data-testid="metric-container"]:hover, .clean-card:hover {
    transform: translateY(-2px) !important; box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
}
[data-testid="stMetricValue"] { color: #111827 !important; font-weight: 700 !important; font-size: 1.8rem !important; }
[data-testid="stMetricLabel"] { color: #6B7280 !important; font-weight: 600 !important; font-size: 12px !important; }

/* ── Custom Dashboard Cards ── */
.dash-card { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px; padding: 16px; display: flex; align-items: center; gap: 16px; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.05); }
.dash-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; }
.ic-blue { background: #E0F2FE; color: #0284C7; }
.ic-green { background: #DCFCE7; color: #16A34A; }
.ic-orange { background: #FFEDD5; color: #EA580C; }
.ic-teal { background: #CCFBF1; color: #0D9488; }
.dash-info h3 { margin: 0; font-size: 20px; color: #111827; font-weight: 700; font-family:'Inter', sans-serif; }
.dash-info p { margin: 0; font-size: 12px; color: #6B7280; font-weight: 500; }

/* ── Form & Buttons ── */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
    background-color: #F9FAFB !important; border: 1px solid #D1D5DB !important; border-radius: 8px !important; color: #111827 !important;
}
.stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within {
    border-color: #0D9488 !important; box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.2) !important; background-color: #FFFFFF !important;
}
.stButton > button { background-color: #0D9488 !important; color: #FFFFFF !important; font-weight: 600 !important; border-radius: 8px !important; border: none !important; }
.stButton > button:hover { background-color: #0F766E !important; }
.btn-outline > button { background-color: transparent !important; color: #0D9488 !important; border: 1px solid #0D9488 !important; }

/* ── Dataframes ── */
.stDataFrame { background: #FFFFFF !important; border-radius: 12px !important; border: 1px solid #E5E7EB !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════
#  3. EFFICIENT PIN LOGIN (Smart Input)
# ══════════════════════════════════════════
if not st.session_state.authenticated:
    st.markdown("<style>[data-testid='stSidebar']{display:none!important}</style>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="clean-card" style="text-align:center;">
            <h2 style="color:#0D9488; font-weight:800; margin-bottom:5px;">ROGER</h2>
            <p style="color:#6B7280; font-size:14px; margin-bottom:20px;">Sistem Manajemen Finansial Pribadi</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Menggunakan native text_input dengan on_change agar sangat efisien
        def check_pin():
            if st.session_state.pin_form_input == st.session_state.saved_pin:
                st.session_state.authenticated = True
                st.session_state.pin_form_input = "" # bersihkan
            else:
                st.session_state.pin_error = True

        pin = st.text_input("🔑 Masukkan PIN (6 Digit)", type="password", max_chars=6, key="pin_form_input", on_change=check_pin, placeholder="Ketik PIN lalu tekan Enter")
        
        if st.session_state.get("pin_error", False):
            st.error("❌ PIN Salah. Silakan coba lagi.")
            st.session_state.pin_error = False

    st.stop()


# ══════════════════════════════════════════
#  4. GOOGLE SHEETS & DATA PREP
# ══════════════════════════════════════════
@st.cache_resource
def init_gsheets():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(json.loads(st.secrets["GOOGLE_JSON"]), scopes=scopes)
        return gspread.authorize(creds).open("Database Finance Pro")
    except: return None

db = init_gsheets()
if not db: st.error("❌ Gagal koneksi Google Sheets."); st.stop()

@st.cache_data(ttl=60)
def load_data():
    try:
        df_t = get_as_dataframe(db.worksheet("Transaksi")).dropna(how='all')
        if not df_t.empty and 'Tanggal' in df_t.columns:
            df_t['Tanggal'] = pd.to_datetime(df_t['Tanggal'], errors='coerce')
            df_t['Nominal'] = pd.to_numeric(df_t['Nominal'], errors='coerce').fillna(0)
            df_t = df_t.dropna(subset=['Tanggal'])
        return df_t
    except: return pd.DataFrame()

df_t = load_data()
porto = {"BCA": 0.0, "BRI": 0.0, "Bank Jago": 0.0, "Dompet (Cash)": 0.0}
if not df_t.empty:
    for _, r in df_t.iterrows():
        s = str(r.get('Sumber Dana',''))
        j = str(r.get('Jenis','')).lower().strip()
        if s in porto: porto[s] += float(r.get('Nominal', 0)) if j == 'pemasukan' else -float(r.get('Nominal', 0))
total_cash = sum(porto.values())

# ══════════════════════════════════════════
#  5. NATIVE SIDEBAR NAVIGATION
# ══════════════════════════════════════════
with st.sidebar:
    st.markdown('<h2 style="color:#0D9488; font-weight:800; text-align:center;">ROGER</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#6B7280; font-size:12px; text-align:center; margin-bottom:30px;">Admin Dashboard</p>', unsafe_allow_html=True)
    
    # Custom Radio Styling for Navigation
    st.markdown("""
    <style>
    div[role="radiogroup"] > label { padding: 10px 15px; border-radius: 8px; margin-bottom: 5px; cursor: pointer; transition: all 0.2s; }
    div[role="radiogroup"] > label:hover { background-color: #F3F4F6; }
    div[role="radiogroup"] > label[data-checked="true"] { background-color: #F0FDFA; border-left: 4px solid #0D9488; }
    div[role="radiogroup"] > label > div:first-child { display: none; } /* Hide radio circles */
    div[role="radiogroup"] > label p { font-weight: 600; color: #4B5563; font-size: 14px; margin: 0; }
    div[role="radiogroup"] > label[data-checked="true"] p { color: #0D9488; }
    </style>
    """, unsafe_allow_html=True)

    nav_options = ["🏠 Dashboard", "💳 Keuangan", "📈 Portofolio", "⚙️ Pengaturan"]
    selected_nav = st.radio("Menu", nav_options, label_visibility="collapsed")
    
    st.markdown("<hr style='margin: 30px 0 15px 0;'>", unsafe_allow_html=True)
    if st.button("🔒 Keluar", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ══════════════════════════════════════════
#  6. PAGES
# ══════════════════════════════════════════

def page_dashboard():
    # Top Action Bar
    t1, t2 = st.columns([3, 1])
    with t1: st.markdown(f'<h3 style="color:#111827; margin:0;">Selamat Datang, Roger 👋</h3><p style="color:#6B7280; font-size:14px;">Ringkasan finansial Anda per {now.strftime("%d %B %Y")}</p>', unsafe_allow_html=True)
    with t2: 
        if st.button("👁️ Toggle Saldo", use_container_width=True):
            st.session_state.hide_balance = not st.session_state.hide_balance
            st.rerun()

    # Cards ala KOSKU
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; margin-top: 10px;">
        <div class="dash-card"><div class="dash-icon ic-blue">🏦</div><div class="dash-info"><h3>{fmt(porto['BCA'])}</h3><p>Bank BCA</p></div></div>
        <div class="dash-card"><div class="dash-icon ic-orange">🦊</div><div class="dash-info"><h3>{fmt(porto['Bank Jago'])}</h3><p>Bank Jago</p></div></div>
        <div class="dash-card"><div class="dash-icon ic-green">💵</div><div class="dash-info"><h3>{fmt(porto['Dompet (Cash)'])}</h3><p>Uang Tunai</p></div></div>
        <div class="dash-card" style="background:#0D9488; border:none;"><div class="dash-info"><p style="color:#CCFBF1;">Total Kas Aktif</p><h3 style="color:#FFF;">{fmt(total_cash)}</h3></div></div>
    </div>
    """, unsafe_allow_html=True)

    # Main Dashboard Content
    c_left, c_right = st.columns([2, 1])
    
    with c_left:
        st.markdown("#### 📊 Arus Kas Bulan Ini")
        df_bln = df_t[(df_t['Tanggal'].dt.month == now.month) & (df_t['Tanggal'].dt.year == now.year)] if not df_t.empty else pd.DataFrame()
        if not df_bln.empty:
            df_bln['Hari'] = df_bln['Tanggal'].dt.day
            df_bln['Jenis'] = df_bln['Jenis'].str.lower().str.strip()
            td = df_bln.groupby(['Hari','Jenis'])['Nominal'].sum().reset_index()
            fig = px.bar(td, x='Hari', y='Nominal', color='Jenis', barmode='group', color_discrete_map={'pemasukan':'#10B981','pengeluaran':'#EF4444'})
            fig.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=320, margin=dict(l=0,r=0,t=10,b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Belum ada transaksi bulan ini.")

        st.markdown("#### 🕒 Transaksi Terakhir")
        if not df_t.empty:
            df_show = df_t.sort_values('Tanggal', ascending=False).head(5).copy()
            df_show['Tanggal'] = df_show['Tanggal'].dt.strftime('%d %b %Y')
            df_show['Nominal'] = df_show['Nominal'].apply(lambda x: f"Rp {x:,.0f}".replace(',','.'))
            st.dataframe(df_show[['Tanggal','Kategori','Jenis','Sumber Dana','Nominal']], use_container_width=True, hide_index=True)

    with c_right:
        st.markdown("#### ⚡ Aksi Cepat")
        with st.form("quick_add", clear_on_submit=True):
            st.markdown("<p style='font-size:13px; color:#4B5563;'>Catat pengeluaran instan</p>", unsafe_allow_html=True)
            q_nom = st.text_input("Nominal (Rp)", placeholder="Contoh: 50000")
            q_kat = st.selectbox("Kategori", st.session_state.kategori_list)
            q_src = st.selectbox("Sumber", list(porto.keys()))
            if st.form_submit_button("Simpan Pengeluaran", use_container_width=True):
                try: 
                    nom = float(q_nom.replace(".","").replace(",",""))
                    tgl_s = pd.Timestamp.now('Asia/Jakarta').strftime('%Y-%m-%d %H:%M:%S')
                    nr = pd.DataFrame([{"Tanggal":tgl_s, "Kategori":q_kat, "Jenis":"Pengeluaran", "Sumber Dana":q_src, "Nominal":nom, "Catatan":"Quick Add"}])
                    set_with_dataframe(db.worksheet("Transaksi"), pd.concat([df_t, nr], ignore_index=True))
                    st.cache_data.clear()
                    st.success("Tersimpan!")
                    st.rerun()
                except: st.error("Nominal tidak valid.")

        st.markdown("<br>#### 💡 AI Insight", unsafe_allow_html=True)
        if st.button("Generate Saran", use_container_width=True):
            if GEMINI_OK:
                with st.spinner("Menyiapkan..."):
                    client = genai_client.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    prompt = f"Kondisi kas Rp {total_cash:,.0f}. Berikan 1 saran hemat singkat dalam 2 kalimat."
                    ans = client.models.generate_content(model="gemini-1.5-flash", contents=prompt).text
                    st.info(ans)
            else:
                st.warning("Google GenAI belum dikonfigurasi.")


def page_keuangan():
    st.markdown('<h3>Manajemen Keuangan</h3>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Daftar Transaksi", "Budget Monitor"])
    with tab1:
        c1, c2 = st.columns([3, 1])
        with c1:
            if not df_t.empty:
                df_show = df_t.copy().sort_values('Tanggal', ascending=False)
                df_show['Tanggal'] = df_show['Tanggal'].dt.strftime('%d %b %Y %H:%M')
                st.dataframe(df_show, use_container_width=True, height=500, hide_index=True)
            else:
                st.info("Belum ada data.")
        with c2:
            st.markdown("#### Filter")
            f_jenis = st.selectbox("Jenis", ["Semua", "Pemasukan", "Pengeluaran"])
            st.download_button("📥 Download Excel (CSV)", data=df_t.to_csv(index=False).encode('utf-8'), file_name="roger_finance.csv", mime="text/csv", use_container_width=True)

    with tab2:
        st.markdown("#### Status Budget Bulan Ini")
        df_bgt = df_t[(df_t['Tanggal'].dt.month == now.month) & (df_t['Tanggal'].dt.year == now.year)] if not df_t.empty else pd.DataFrame()
        spent_bgt = df_bgt[df_bgt['Jenis'].str.lower() == 'pengeluaran'].groupby('Kategori')['Nominal'].sum().to_dict() if not df_bgt.empty else {}
        
        b_cols = st.columns(3)
        for i, (kat, lim) in enumerate(st.session_state.budgets.items()):
            terpakai = spent_bgt.get(kat, 0.0)
            pct = min(terpakai / lim * 100, 100) if lim > 0 else 0
            color = "#10B981" if pct < 60 else "#F59E0B" if pct < 85 else "#EF4444"
            with b_cols[i%3]:
                st.markdown(f"""
                <div class="clean-card" style="margin-bottom:15px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span style="font-weight:600; color:#374151;">{kat}</span>
                        <span style="font-weight:700; color:{color};">{pct:.0f}%</span>
                    </div>
                    <div style="background:#E5E7EB; height:8px; border-radius:4px; overflow:hidden; margin-bottom:8px;">
                        <div style="background:{color}; width:{pct}%; height:100%;"></div>
                    </div>
                    <div style="font-size:12px; color:#6B7280;">Terpakai: Rp {terpakai:,.0f} / Rp {lim:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)


def page_pengaturan():
    st.markdown('<h3>Pengaturan Sistem</h3>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Kategori Transaksi")
        nk = st.text_input("Tambah Kategori Baru")
        if st.button("Tambah"):
            if nk and nk not in st.session_state.kategori_list:
                st.session_state.kategori_list.append(nk); save_config(); st.rerun()
        
        st.markdown("#### Ubah PIN")
        np = st.text_input("PIN Baru (6 Digit)", type="password", max_chars=6)
        if st.button("Simpan PIN"):
            if len(np) == 6 and np.isdigit():
                st.session_state.saved_pin = np; save_config(); st.success("PIN Diperbarui!")
            else: st.error("Harus 6 digit angka.")

# ══════════════════════════════════════════
#  7. ROUTER
# ══════════════════════════════════════════
if selected_nav == "🏠 Dashboard": page_dashboard()
elif selected_nav == "💳 Keuangan": page_keuangan()
elif selected_nav == "⚙️ Pengaturan": page_pengaturan()
else: st.info("Halaman sedang dalam pengembangan.")
