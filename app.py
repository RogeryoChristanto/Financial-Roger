import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
import pytesseract
from PIL import Image
from datetime import timedelta, datetime
import json, os, gspread, re, math, numpy as np, calendar
import io
from sklearn.linear_model import LinearRegression
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# ══════════════════════════════════════════
#  1. PAGE CONFIG & SESSION STATE
# ══════════════════════════════════════════
st.set_page_config(
    page_title="ROGER Marine",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded"
)

DEFAULTS = {
    "hide_balance": False, "authenticated": False,
    "page": "Dashboard", "chat_messages": [], "scan_status": None,
    "auto_nominal": "", "daily_recs_cache": None, "daily_recs_date": None,
    "theme": "dark", "trigger_anim": None
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

CONFIG_FILE = "roger_config_v3.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "budgets": {"Makan & Minum": 900000, "Kebutuhan Mandi": 150000,
                    "Kebutuhan Pokok & Beras": 300000, "Ngopi & Nongkrong": 250000,
                    "Transportasi": 100000, "Laundry": 100000, "Skincare": 325000},
        "kategori_list": ["Uang Saku Bulanan","Dividen","Bayar Kost","Makan & Minum",
                          "Transportasi","Kuota Internet","Kebutuhan Mandi",
                          "Kebutuhan Pokok & Beras","Ngopi & Nongkrong","Olahraga",
                          "Jajan & Camilan","Laundry","Kost","Skincare","Investasi"],
        "saved_pin": "120224",
        "target_harta": 100000000
    }

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump({"budgets": st.session_state.budgets,
                   "kategori_list": st.session_state.kategori_list,
                   "saved_pin": st.session_state.saved_pin,
                   "target_harta": st.session_state.get("target_harta", 100000000)
                   }, f)

cfg = load_config()
for key, default in [("budgets", cfg["budgets"]), ("kategori_list", cfg["kategori_list"]),
                     ("saved_pin", cfg["saved_pin"]), ("target_harta", cfg["target_harta"])]:
    if key not in st.session_state:
        st.session_state[key] = default

NAMA_BULAN = ["Semua Waktu","Januari","Februari","Maret","April","Mei","Juni",
              "Juli","Agustus","September","Oktober","November","Desember"]

def fmt(v):
    if st.session_state.hide_balance: return "Rp ••••••"
    return f"Rp {v:,.0f}".replace(",", ".")

def fmt_tbl(df):
    st.markdown(f'<div class="tbl-wrap">{df.to_html(classes="ctbl",index=False,escape=False)}</div>',
                unsafe_allow_html=True)

def bersihkan_angka(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    v = re.sub(r'[^\d]', '', str(val).upper().replace('RP','').split(',')[0])
    try: return float(v) if v else 0.0
    except: return 0.0

def bersihkan_tgl(val):
    if pd.isna(val) or str(val).strip() == "": return pd.NaT
    try:
        v = str(val).strip()
        d, t = (v.split(' ', 1) if ' ' in v else (v, ""))
        for sep in ['/', '-']:
            if sep in d:
                p = d.split(sep)
                if len(p) == 3:
                    d = f"{p[2]}-{p[1]}-{p[0]}" if len(p[2]) == 4 else f"{p[0]}-{p[1]}-{p[2]}"
                break
        return pd.to_datetime(f"{d} {t}".strip())
    except: return pd.NaT

def fmt_tgl_sheet(x):
    try:
        dt = pd.to_datetime(x)
        if pd.isna(dt): return ""
        return dt.strftime('%Y-%m-%d') if (dt.hour == 0 and dt.minute == 0) else dt.strftime('%Y-%m-%d %H:%M:%S')
    except: return ""

# ══════════════════════════════════════════
#  2. CSS NATIVE — THEMA MARITIME & NAVAL 🌊⚓
# ══════════════════════════════════════════
def get_theme_vars():
    if st.session_state.get("theme", "dark") == "light":
        return """
        <style>
        html, body, .stApp, [data-testid="stAppViewContainer"] { background: #E0F2FE !important; color: #0F172A !important; }
        .stApp::before { background: radial-gradient(circle, rgba(14,165,233,0.15) 0%, transparent 65%) !important; }
        .stApp::after  { background: radial-gradient(circle, rgba(2,132,199,0.1) 0%, transparent 65%) !important; }
        .topbar { background: rgba(255,255,255,0.95) !important; border-bottom: 2px solid #38BDF8 !important; }
        .topbar-stat-label, .topbar-date { color: #64748B !important; } .topbar-stat-value { color: #0284C7 !important; }
        div[data-testid="metric-container"] { background: linear-gradient(145deg,#FFFFFF,#F0F9FF) !important; border: 1px solid #BAE6FD !important; }
        [data-testid="stMetricValue"] { color: #0284C7 !important; } [data-testid="stMetricLabel"] { color: #0369A1 !important; font-weight:700 !important; }
        .ctbl { color: #334155 !important; } .ctbl thead th { background: #E0F2FE !important; color: #0284C7 !important; border-bottom: 2px solid #7DD3FC !important; }
        .tbl-wrap { background: #FFFFFF !important; border: 1px solid #BAE6FD !important; }
        .bgt-card { background: #FFFFFF !important; border: 1px solid #BAE6FD !important; }
        .insight-card { background: #F0F9FF !important; border: 1px solid #7DD3FC !important; }
        .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input, .stSelectbox div[data-baseweb="select"] { background: #FFFFFF !important; border: 1px solid #7DD3FC !important; color: #0F172A !important; border-radius: 8px !important; }
        label, .sec-txt { color: #0284C7 !important; font-weight: 700 !important; }
        [data-testid="stTabs"] div[data-baseweb="tab-list"] { background: #F0F9FF !important; border: 1px solid #BAE6FD !important; border-radius: 8px !important; }
        </style>"""
    return ""

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700&display=swap');

*,*::before,*::after{box-sizing:border-box;}
.stApp,[data-testid="stAppViewContainer"]{font-family:'Inter',sans-serif!important;background:#020914!important;color:#E2E8F0!important;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#031224 0%,#020914 100%)!important;border-right:1px solid rgba(14,165,233,0.2)!important;box-shadow: 2px 0 15px rgba(0,0,0,0.5)!important;}

/* Animasi Latar Maritim (Underwater Currents & Radar Glow) */
.stApp::before{content:'';position:fixed;top:-20%;left:-10%;width:70%;height:70%; background:radial-gradient(ellipse,rgba(14,165,233,0.07) 0%,transparent 60%); pointer-events:none;z-index:0;animation:floatWave 15s infinite alternate ease-in-out; filter:blur(40px);}
.stApp::after{content:'';position:fixed;bottom:-20%;right:-10%;width:75%;height:75%; background:radial-gradient(ellipse,rgba(16,185,129,0.05) 0%,transparent 60%); pointer-events:none;z-index:0;animation:floatWave 18s infinite alternate-reverse ease-in-out; filter:blur(50px);}
@keyframes floatWave { 0% { transform: translateY(0px) scale(1); } 100% { transform: translateY(30px) scale(1.05); } }
@keyframes radarSweep { 0% { opacity: 0; transform: translateY(10px); } 100% { opacity: 1; transform: translateY(0); } }

/* Header & Topbar Native ala Panel Navigasi Kapal */
header[data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; z-index: 1000 !important; }
.stAppDeployButton, #MainMenu, footer { display: none !important; }

.topbar {
    position: fixed; top: 0; left: 0; width: 100%; height: 62px;
    background: rgba(3, 15, 30, 0.95); backdrop-filter: blur(12px);
    border-bottom: 2px solid rgba(14,165,233,0.4); z-index: 999;
    display: flex; align-items: center; padding: 0 20px 0 65px;
    box-shadow: 0 4px 25px rgba(0,0,0,0.6), inset 0 -1px 5px rgba(14,165,233,0.2);
}
.topbar-divider { width: 1px; height: 28px; background: rgba(14,165,233,0.3); margin: 0 14px; }
.topbar-stat { display: flex; flex-direction: column; flex-shrink: 0; }
.topbar-stat-label { font-size: 9px; color: #94A3B8; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; font-family: 'Montserrat', sans-serif; }
.topbar-stat-value { font-size: 14px; font-weight: 800; margin-top: 1px; font-family: 'Montserrat', sans-serif; text-shadow: 0 0 8px rgba(14,165,233,0.4); }
.topbar-right { margin-left: auto; display: flex; align-items: center; gap: 6px; }
.topbar-date { font-size: 11.5px; color: #CBD5E1; font-weight: 600; font-family: 'Inter', sans-serif; letter-spacing: 0.5px;}
.live-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#10B981;margin-right:8px;box-shadow: 0 0 8px #10B981; animation: blink 1.5s infinite;}
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.block-container { padding-top: 85px !important; padding-bottom: 20px !important; max-width: 100% !important; }

/* Menu Navigasi Radar Style */
[data-testid="stSidebar"] [role="radiogroup"] { gap: 6px; }
[data-testid="stSidebar"] [role="radiogroup"] > label {
    width: 100%; padding: 12px 18px; border-radius: 8px; margin: 0;
    background: transparent; border: 1px solid transparent; border-left: 3px solid transparent;
    transition: all 0.2s ease; cursor: pointer;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:hover {
    background: rgba(14,165,233,0.06); border-left-color: rgba(14,165,233,0.4);
}
[data-testid="stSidebar"] [role="radiogroup"] > label [data-baseweb="radio"] > div:first-child { display: none !important; }
[data-testid="stSidebar"] [role="radiogroup"] > label p {
    color: #94A3B8; font-weight: 600; font-size: 13.5px; margin: 0; font-family: 'Montserrat', sans-serif; letter-spacing: 0.5px;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(90deg, rgba(14,165,233,0.15), transparent) !important;
    border-left: 3px solid #0EA5E9 !important; box-shadow: inset 20px 0 20px -20px rgba(14,165,233,0.5) !important;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p { color: #0EA5E9 !important; font-weight: 700 !important; text-shadow: 0 0 8px rgba(14,165,233,0.3); }

/* Tombol Aksi Bawah Sidebar (Saklar/Switch Panel) */
[data-testid="stSidebar"] button[kind="secondary"] {
    background: rgba(3,15,30,0.6) !important; border: 1px solid rgba(14,165,233,0.3) !important;
    color: #7DD3FC !important; padding: 10px 16px !important; font-weight: 600 !important; font-family: 'Montserrat', sans-serif !important;
    border-radius: 6px !important; transition: all 0.2s !important; text-align: left !important;
}
[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: rgba(14,165,233,0.15) !important; border-color: #0EA5E9 !important; color: #FFF !important; box-shadow: 0 0 10px rgba(14,165,233,0.3) !important;
}

/* KARTU & METRIK (HUD / Glassmorphism Laut Dalam) */
.stButton>button{background:linear-gradient(135deg,#0284C7 0%,#0EA5E9 100%)!important;color:#fff!important;font-weight:700!important;font-size:13px!important;border-radius:6px!important;border:1px solid #38BDF8!important;padding:10px 24px!important;font-family:'Montserrat',sans-serif!important;box-shadow: 0 4px 15px rgba(2,132,199,0.4)!important;}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 6px 20px rgba(2,132,199,0.6), inset 0 0 10px rgba(255,255,255,0.2)!important;}

div[data-testid="metric-container"]{background:rgba(4,20,40,0.8)!important;backdrop-filter:blur(10px)!important;border:1px solid rgba(14,165,233,0.2)!important;border-left:3px solid #0EA5E9!important;border-radius:8px!important;padding:16px!important;box-shadow:0 8px 24px rgba(0,0,0,0.4)!important;transition:all .2s ease!important;animation:radarSweep .5s ease-out both;}
div[data-testid="metric-container"]:hover{border-color:rgba(14,165,233,0.5)!important;transform:translateY(-3px)!important;box-shadow:0 12px 30px rgba(0,0,0,0.5), 0 0 15px rgba(14,165,233,0.1)!important;}
[data-testid="stMetricValue"]{font-size:1.6rem!important;font-weight:800!important;color:#F8FAFC!important;font-family:'Montserrat',sans-serif!important;letter-spacing:-0.5px!important;text-shadow: 0 0 10px rgba(255,255,255,0.1)!important;}
[data-testid="stMetricLabel"]{font-size:10px!important;font-weight:700!important;color:#7DD3FC!important;text-transform:uppercase!important;letter-spacing:1.5px!important;}

.wallet-row{display:flex;gap:16px;flex-wrap:nowrap;overflow-x:auto;padding-bottom:12px;scrollbar-width:none;}
.wcard{min-width:210px;flex:1;border-radius:12px;padding:20px 18px;position:relative;overflow:hidden;transition:all .3s ease!important;animation:radarSweep .6s ease-out both; border:1px solid rgba(14,165,233,0.3);}
.wcard::before{content:'';position:absolute;top:0;left:-100%;width:50%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.1),transparent);transform:skewX(-25deg);transition:0.5s;}
.wcard:hover::before{left:200%;}
.wcard:hover{transform:translateY(-5px); box-shadow: 0 10px 25px rgba(0,0,0,0.6), 0 0 15px rgba(14,165,233,0.2); border-color:#0EA5E9;}
.wcard-chip{position:absolute;top:16px;right:16px;width:30px;height:22px;border-radius:4px;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.3);}
.wcard-icon{font-size:24px;margin-bottom:12px;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.5));}
.wcard-lbl{font-size:9px;font-weight:700;color:rgba(255,255,255,.6);text-transform:uppercase;letter-spacing:2px;margin-bottom:4px;font-family:'Montserrat',sans-serif;}
.wcard-bal{font-size:19px;font-weight:800;color:#fff;font-family:'Montserrat',sans-serif;letter-spacing:-0.5px;}

/* Palet Warna Mesin Kapal & Laut */
.wcard-bca{background:linear-gradient(145deg, #07294D 0%, #031326 100%);} /* Deep Navy */
.wcard-bri{background:linear-gradient(145deg, #033C47 0%, #01181D 100%);} /* Deep Teal */
.wcard-jago{background:linear-gradient(145deg, #422006 0%, #170A01 100%);} /* Brass/Rust */
.wcard-cash{background:linear-gradient(145deg, #064E3B 0%, #021C15 100%);} /* Deep Emerald */

.sec{display:flex;align-items:center;gap:12px;margin:28px 0 16px;}
.sec-txt{font-size:10px;font-weight:800;color:#38BDF8;text-transform:uppercase;letter-spacing:3px;font-family:'Montserrat',sans-serif;}
.sec-line{flex:1;height:1px;background:linear-gradient(90deg,rgba(14,165,233,0.5),rgba(255,255,255,0.05),transparent);}

/* Tabel Log Pelayaran (Transaksi) */
.tbl-wrap{background:rgba(4,20,40,.8);border:1px solid rgba(14,165,233,0.2);border-radius:8px;overflow:auto;max-height:400px;box-shadow:0 8px 32px rgba(0,0,0,0.5);}
.ctbl{width:100%;border-collapse:collapse;color:#CBD5E1;font-size:12px;font-family:'Inter',sans-serif;}
.ctbl thead th{position:sticky;top:0;background:#031224;padding:12px 16px;font-weight:700;color:#7DD3FC;text-transform:uppercase;letter-spacing:1.5px;font-size:9px;border-bottom:1px solid rgba(14,165,233,0.4);z-index:1;}
.ctbl td{padding:12px 16px;border-bottom:1px solid rgba(255,255,255,.03);}
.ctbl tbody tr:hover td{background:rgba(14,165,233,.05);color:#FFF;}
[data-testid="stTabs"] div[data-baseweb="tab-list"]{gap:4px;background:rgba(3,15,30,0.8);border-radius:6px;padding:4px;border:1px solid rgba(14,165,233,0.2);}
[data-testid="stTabs"] button[data-baseweb="tab"]{background:transparent;border-radius:4px;padding:8px 16px;font-weight:600;font-size:12px;color:#64748B;border:none;font-family:'Montserrat',sans-serif;}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"]{background:rgba(14,165,233,0.15);color:#0EA5E9;border:1px solid rgba(14,165,233,0.4);box-shadow:0 0 10px rgba(14,165,233,0.1);}

/* Input Data Kendali (Form) */
.stTextInput input,.stNumberInput input,.stTextArea textarea,.stDateInput input, .stSelectbox div[data-baseweb="select"] {background:rgba(3,15,30,0.8)!important;border:1px solid rgba(14,165,233,0.3)!important;border-radius:6px!important;color:#E2E8F0!important;font-size:13px!important;font-family:'Inter',sans-serif!important;}
.stTextInput input:focus,.stNumberInput input:focus,.stTextArea textarea:focus{border-color:#0EA5E9!important;box-shadow:0 0 0 2px rgba(14,165,233,.3)!important;}
label{color:#7DD3FC!important;font-size:10px!important;font-weight:700!important;text-transform:uppercase;letter-spacing:1px;font-family:'Montserrat',sans-serif!important;}

/* Progress Bar Panel Kapal */
.stProgress>div>div{background:linear-gradient(90deg,#0284C7,#38BDF8)!important;border-radius:4px!important;box-shadow:0 0 8px #38BDF8;}
.stProgress>div{background:rgba(255,255,255,0.05)!important;border-radius:4px!important;height:8px!important;}

/* Insight / Sonar Card */
.insight-card{background:rgba(4,20,40,0.6);border:1px solid rgba(14,165,233,0.2);border-left:3px solid #0EA5E9;border-radius:6px;padding:14px 16px;margin-bottom:8px;display:flex;align-items:flex-start;gap:12px;transition:all .2s;}
.insight-card:hover{background:rgba(14,165,233,0.05);border-color:rgba(14,165,233,0.4);transform:translateX(4px);}
.bgt-card{background:rgba(4,20,40,0.6);border:1px solid rgba(14,165,233,0.15);border-radius:8px;padding:14px 16px;margin-bottom:10px;transition:all .2s;}
.bgt-card:hover{border-color:#0EA5E9;box-shadow:0 4px 15px rgba(0,0,0,0.4), 0 0 10px rgba(14,165,233,0.1);transform:translateY(-2px);}
.bar-track{width:100%;background:rgba(0,0,0,0.5);border-radius:4px;height:6px;margin-top:8px;overflow:hidden;border:1px solid rgba(255,255,255,0.05);}
.bar-fill{height:100%;border-radius:4px;transition:width 1s ease-out;}
::-webkit-scrollbar{width:5px;height:5px;} ::-webkit-scrollbar-track{background:transparent;} ::-webkit-scrollbar-thumb{background:rgba(14,165,233,0.4);border-radius:10px;} ::-webkit-scrollbar-thumb:hover{background:#0EA5E9;}
</style>
""", unsafe_allow_html=True)

st.markdown(get_theme_vars(), unsafe_allow_html=True)

# ══════════════════════════════════════════
#  LOGIN MARITIME (TANPA TOMBOL, CUKUP ENTER)
# ══════════════════════════════════════════
if not st.session_state.authenticated:
    st.markdown("<style>[data-testid='collapsedControl']{display:none!important} section[data-testid='stSidebar']{display:none!important} .topbar{display:none!important;}</style>", unsafe_allow_html=True)
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.2, 1])
    
    with mid:
        st.markdown("""
        <div style='text-align:center;margin-bottom:30px;animation:radarSweep 0.8s ease-out both;'>
            <div style='font-size:52px;font-weight:900;letter-spacing:-2px;font-family:"Montserrat",sans-serif;color:#F8FAFC;text-shadow: 0 0 20px rgba(14,165,233,0.8);'>
                <span style='color:#0EA5E9;'>⚓</span> ROGER
            </div>
            <div style='font-size:11px;color:#7DD3FC;letter-spacing:5px;text-transform:uppercase;font-weight:700;margin-top:8px;'>Naval Finance Command</div>
        </div>
        """, unsafe_allow_html=True)
        
        pin_input = st.text_input("Kode Akses Ruang Kendali (Enter untuk konfirmasi)", type="password", placeholder="Input PIN & tekan Enter ➔", key="pin_login_input")
        
        if pin_input:
            if pin_input == st.session_state.saved_pin:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Akses Ditolak. Kode Navigasi Tidak Valid.")
    st.stop()


# ══════════════════════════════════════════
#  DATA LOADING
# ══════════════════════════════════════════
@st.cache_resource
def init_gsheets():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(json.loads(st.secrets["GOOGLE_JSON"]), scopes=scopes)
        return gspread.authorize(creds).open("Database Finance Pro")
    except: return None

db = init_gsheets()
if not db: st.error("❌ Gagal terhubung ke Database. Periksa konfigurasi transmisi."); st.stop()

@st.cache_data(ttl=60)
def load_sheets():
    try:
        dft = get_as_dataframe(db.worksheet("Transaksi")).dropna(how='all')
        dfs = get_as_dataframe(db.worksheet("Saham")).dropna(how='all')
        return dft, dfs
    except: return pd.DataFrame(), pd.DataFrame()

ws_t = db.worksheet("Transaksi"); ws_s = db.worksheet("Saham")
df_t_raw, df_s_raw = load_sheets(); df_t = df_t_raw.copy(); df_s = df_s_raw.copy()
if not df_t.empty:
    if 'Nominal' in df_t.columns: df_t['Nominal'] = df_t['Nominal'].apply(bersihkan_angka)
    if 'Tanggal' in df_t.columns: df_t['Tanggal'] = df_t['Tanggal'].apply(bersihkan_tgl); df_t = df_t.dropna(subset=['Tanggal'])

porto = {"BCA": 0.0, "BRI": 0.0, "Bank Jago": 0.0, "Dompet (Cash)": 0.0}
if not df_t.empty:
    for _, r in df_t.iterrows():
        s = str(r.get('Sumber Dana','')); j = str(r.get('Jenis','')).lower().strip(); n = float(r.get('Nominal', 0))
        if s in porto: porto[s] += n if j == 'pemasukan' else -n

harga_dict = {}; total_saham = 0.0; df_s_agg = pd.DataFrame()
if not df_s.empty:
    try:
        kurs = 15500.0
        try:
            k = yf.Ticker("USDIDR=X").history(period="2d")
            if not k.empty: kurs = float(k['Close'].iloc[-1])
        except: pass
        tks = [str(t).upper().strip() for t in df_s['Ticker'].unique() if pd.notna(t) and str(t).strip()]
        if tks:
            raw = yf.download(tks, period="5d", progress=False, auto_adjust=True)
            for t in tks:
                try:
                    if isinstance(raw.columns, pd.MultiIndex): cls = raw[('Close', t)].dropna() if len(tks) > 1 else raw['Close'].dropna()
                    else: cls = raw['Close'][t].dropna() if len(tks) > 1 else raw['Close'].dropna()
                    cp = float(cls.iloc[-1]); harga_dict[t] = cp * kurs if not t.endswith('.JK') else cp
                except: harga_dict[t] = 0
    except: pass
    df_s['Ticker'] = df_s['Ticker'].astype(str).str.upper().str.strip()
    df_s['Jumlah Lembar'] = pd.to_numeric(df_s['Jumlah Lembar'], errors='coerce').fillna(0)
    df_s['Harga Beli']    = pd.to_numeric(df_s['Harga Beli'],    errors='coerce').fillna(0)
    df_s['Total Modal']   = df_s['Jumlah Lembar'] * df_s['Harga Beli']
    df_s_agg = df_s.groupby('Ticker').agg({'Jumlah Lembar':'sum','Total Modal':'sum'}).reset_index()
    df_s_agg['Avg Beli'] = df_s_agg['Total Modal'] / df_s_agg['Jumlah Lembar']
    df_s_agg = df_s_agg[df_s_agg['Jumlah Lembar'] > 0]
    for _, r in df_s_agg.iterrows():
        hs = harga_dict.get(r['Ticker'], r['Avg Beli'])
        if pd.isna(hs) or hs == 0: hs = r['Avg Beli']
        total_saham += hs * r['Jumlah Lembar']

total_cash = sum(porto.values()); total_net = total_cash + total_saham

def _fmt_top(v):
    if st.session_state.hide_balance: return "Rp ••••"
    if v >= 1_000_000_000: return f"Rp {v/1_000_000_000:.1f}M"
    if v >= 1_000_000:     return f"Rp {v/1_000_000:.1f}Jt"
    return f"Rp {v:,.0f}".replace(",",".")

now = pd.Timestamp.now('Asia/Jakarta')

# ══════════════════════════════════════════
#  3. TOPBAR NATIVE (PANEL NAVIGASI ATAS)
# ══════════════════════════════════════════
st.markdown(f"""
<div class="topbar">
    <div class="topbar-stat"><span class="topbar-stat-label">Harta Karun</span><span class="topbar-stat-value" style="color:#0EA5E9;">{_fmt_top(total_net)}</span></div>
    <div class="topbar-divider"></div>
    <div class="topbar-stat"><span class="topbar-stat-label">Kas Tunai</span><span class="topbar-stat-value" style="color:#10B981;">{_fmt_top(total_cash)}</span></div>
    <div class="topbar-divider"></div>
    <div class="topbar-stat"><span class="topbar-stat-label">Aset Saham</span><span class="topbar-stat-value" style="color:#FBBF24;">{_fmt_top(total_saham)}</span></div>
    <div class="topbar-right">
        <span class="topbar-date"><span class="live-dot"></span>{now.strftime("%H:%M")} · {now.strftime("%d %b %Y")}</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════
#  4. SIDEBAR NATIVE
# ══════════════════════════════════════════
NAV_PAGES = [
    ("Dashboard",   "🧭"), ("Kendali Dana", "💳"),
    ("Aset Saham",  "📈"), ("AI Sonar",     "🤖"),
    ("Radar Saham", "📡"), ("Screener",     "⚡"),
    ("Log Nota",    "🧾"), ("Sistem Panel", "⚙️")
]

with st.sidebar:
    st.markdown('''
    <div style="text-align:center; padding: 15px 0 25px;">
        <div style="font-size: 28px; font-weight: 900; color: #F8FAFC; letter-spacing: 1px; font-family: 'Montserrat', sans-serif; text-shadow: 0 0 15px rgba(14,165,233,0.8);">
            <span style='color:#0EA5E9;'>⚓</span> ROGER
        </div>
        <div style="font-size:9px;color:#7DD3FC;letter-spacing:3px;margin-top:6px;font-weight:700;text-transform:uppercase;">Naval Command</div>
    </div>
    ''', unsafe_allow_html=True)
    
    radio_opts = [f"{icon} {name}" for name, icon in NAV_PAGES]
    cur_idx = next((i for i, (name, _) in enumerate(NAV_PAGES) if name == st.session_state.page), 0)
    
    selected_menu = st.radio("Sistem Navigasi", radio_opts, index=cur_idx, label_visibility="collapsed")
    
    for name, icon in NAV_PAGES:
        if f"{icon} {name}" == selected_menu:
            if st.session_state.page != name:
                st.session_state.page = name
                st.rerun()
            break
            
    st.markdown("<hr style='border: 1px solid rgba(14,165,233,0.2); margin: 20px 0;'>", unsafe_allow_html=True)
    
    label_mata = "👁️ Aktifkan Sonar Saldo" if st.session_state.hide_balance else "🙈 Mode Senyap (Hide)"
    if st.button(label_mata, use_container_width=True):
        st.session_state.hide_balance = not st.session_state.hide_balance
        st.rerun()
        
    if st.button("🌓 Kalibrasi Visual", use_container_width=True):
        st.session_state.theme = "light" if st.session_state.get("theme", "dark") == "dark" else "dark"
        st.rerun()
        
    if st.button("🔒 Kunci Sistem", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ══════════════════════════════════════════
#  FUNGSI PENDUKUNG
# ══════════════════════════════════════════
def generate_insights(df_curr, in_curr, out_curr, budgets):
    insights = []
    if df_curr.empty or in_curr == 0: return insights
    df = df_curr.copy(); df['Jenis'] = df['Jenis'].str.lower().str.strip(); df['Kategori'] = df['Kategori'].str.strip().str.title()
    out_df = df[df['Jenis'] == 'pengeluaran']; rasio_hemat = (in_curr - out_curr) / in_curr * 100
    if rasio_hemat >= 30: insights.append(("🔱","Pelayaran Aman",f"Berhasil menahan logistik sebesar <strong>{rasio_hemat:.1f}%</strong> dari suplai bulan ini."))
    elif rasio_hemat < 0: insights.append(("🚨","Kebocoran Lambung",f"Pengeluaran melebihi suplai sebesar <strong>{fmt(abs(out_curr-in_curr))}</strong>. Segera tambal!"))
    elif rasio_hemat < 10: insights.append(("⚠️","Cadangan Menipis",f"Rasio logistik hanya <strong>{rasio_hemat:.1f}%</strong>. Kurangi kecepatan mesin."))
    if not out_df.empty:
        top_kat = out_df.groupby('Kategori')['Nominal'].sum().idxmax()
        top_val = out_df.groupby('Kategori')['Nominal'].sum().max()
        insights.append(("⚓","Beban Terberat",f"Beban terbesar pada sistem: <strong>{top_kat}</strong> sebesar <strong>{fmt(top_val)}</strong>."))
    for kat, limit in budgets.items():
        spent = out_df[out_df['Kategori'] == kat.strip().title()]['Nominal'].sum()
        if limit > 0 and spent > limit: insights.append(("🔴","Overheat Sistem",f"Sektor <strong>{kat}</strong> over-limit! Kelebihan <strong>{fmt(spent-limit)}</strong>."))
    inv = out_df[out_df['Kategori'] == 'Investasi']['Nominal'].sum(); inv_pct = inv / in_curr * 100
    if inv_pct < 10: insights.append(("🧭","Ekspansi Lambat",f"Armada investasi baru <strong>{inv_pct:.1f}%</strong>. Naikkan ke level 20%."))
    elif inv_pct >= 20: insights.append(("🚢","Laksamana Sukses",f"Ekspansi investasi mencapai <strong>{inv_pct:.1f}%</strong>. Stabilitas finansial terjamin!"))
    return insights[:6]

def project_monthend(df_curr, bulan_idx, tahun):
    if df_curr.empty: return 0.0, [], []
    dim = calendar.monthrange(tahun, bulan_idx)[1]
    out_df = df_curr[df_curr['Jenis'].str.lower() == 'pengeluaran'].copy()
    if out_df.empty: return 0.0, [], []
    out_df['Hari'] = out_df['Tanggal'].dt.day
    daily = out_df.groupby('Hari')['Nominal'].sum().reindex(range(1, dim+1), fill_value=0)
    daily_cum = daily.cumsum().reset_index(); daily_cum.columns = ['Hari','Kumulatif']
    today_day = min(now.day, dim); hist = daily_cum[daily_cum['Hari'] <= today_day]
    if len(hist) < 3: return float(daily_cum[daily_cum['Hari'] <= today_day]['Kumulatif'].max()), daily_cum['Hari'].tolist(), daily_cum['Kumulatif'].tolist()
    X = hist['Hari'].values.reshape(-1,1); y = hist['Kumulatif'].values
    m = LinearRegression().fit(X, y); fd = np.arange(today_day+1, dim+1).reshape(-1,1); yf = m.predict(fd)
    all_days = list(hist['Hari']) + list(range(today_day+1, dim+1)); all_cum = list(hist['Kumulatif']) + list(yf)
    proj_end = max(0.0, float(yf[-1]) if len(yf) > 0 else float(hist['Kumulatif'].max()))
    return proj_end, all_days, all_cum

# ══════════════════════════════════════════
#  8. PAGE — DASHBOARD
# ══════════════════════════════════════════
def page_dashboard():
    st.markdown('<h2 style="font-size:22px;font-weight:800;color:#F8FAFC;margin-bottom:0;font-family:\'Montserrat\',sans-serif;text-transform:uppercase;letter-spacing:1px;">🧭 Ruang Kemudi (Dashboard)</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#94A3B8;font-size:12px;margin-top:2px;">Waktu Lokal: {now.strftime("%A, %d %B %Y · %H:%M")} WIB</p>', unsafe_allow_html=True)

    today_mask = (df_t['Tanggal'].dt.date == now.date()) if not df_t.empty else pd.Series(dtype=bool)
    df_today   = df_t[today_mask].copy() if not df_t.empty else pd.DataFrame()
    if not df_today.empty:
        df_today['Jenis'] = df_today['Jenis'].str.lower().str.strip(); df_today['Kategori'] = df_today['Kategori'].str.strip().str.title()
        df_today = df_today.sort_values('Tanggal', ascending=False)
    ti  = df_today[df_today['Jenis']=='pemasukan']['Nominal'].sum()   if not df_today.empty else 0.0
    to_ = df_today[df_today['Jenis']=='pengeluaran']['Nominal'].sum() if not df_today.empty else 0.0

    m1,m2,m3 = st.columns(3)
    m1.metric("⚓ HARTA KARUN TOTAL", fmt(total_net)); m2.metric("💵 KAS KAPAL (CASH)", fmt(total_cash)); m3.metric("📈 VALUASI SAHAM", fmt(total_saham))
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec"><span class="sec-txt">Palka & Ruang Penyimpanan</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
    wc = st.columns(4)
    for i,(key,name,icon,cls) in enumerate([("BCA","Bank BCA","🏦","wcard-bca"),("BRI","Bank BRI","🏢","wcard-bri"),("Bank Jago","Bank Jago","🦊","wcard-jago"),("Dompet (Cash)","Uang Tunai","💵","wcard-cash")]):
        with wc[i]: st.markdown(f'<div class="wcard {cls}"><div class="wcard-chip"></div><div class="wcard-icon">{icon}</div><div class="wcard-lbl">{name}</div><div class="wcard-bal">{fmt(porto[key])}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True); col_left, col_right = st.columns([2,1])
    with col_left:
        st.markdown('<div class="sec"><span class="sec-txt">Jangkar Harta Bersih (Target)</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        tgt = st.number_input("Target Harta (Rp)", value=int(st.session_state.target_harta), step=1000000, label_visibility="collapsed", format="%d")
        st.session_state.target_harta = tgt; save_config()
        rasio_t = max(0.0, min(total_net/tgt, 1.0)) if tgt > 0 else 0.0; pct_t = rasio_t * 100
        pc = "#0EA5E9" if pct_t>=80 else "#38BDF8" if pct_t>=50 else "#FBBF24" if pct_t>=25 else "#EF4444"
        st.progress(rasio_t); st.markdown(f'<p style="font-size:12px;color:{pc};font-weight:700;margin-top:6px;font-family:\'Montserrat\',sans-serif;">⚓ {pct_t:.1f}% Menuju Kordinat — {fmt(total_net)} dari {fmt(tgt)}</p>', unsafe_allow_html=True)
        
        st.markdown('<div class="sec"><span class="sec-txt">Proyeksi Bahan Bakar (Bulan Ini)</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        b_proj = st.selectbox("Bulan Proyeksi:", NAMA_BULAN[1:], index=now.month-1, key="db_proj", label_visibility="collapsed")
        bln_p = NAMA_BULAN.index(b_proj); df_p2 = pd.DataFrame(); in_p2 = out_p2 = 0.0
        if not df_t.empty:
            dc2 = df_t.copy(); dc2['Jenis'] = dc2['Jenis'].str.lower().str.strip(); dc2['Kategori'] = dc2['Kategori'].str.strip().str.title()
            df_p2 = dc2[(dc2['Tanggal'].dt.month==bln_p)&(dc2['Tanggal'].dt.year==now.year)]
            in_p2 = df_p2[df_p2['Jenis']=='pemasukan']['Nominal'].sum(); out_p2 = df_p2[df_p2['Jenis']=='pengeluaran']['Nominal'].sum()
        proj_end, all_days, all_cum = project_monthend(df_p2, bln_p, now.year)
        c1p,c2p,c3p = st.columns(3); c1p.metric("Terpakai Saat Ini", fmt(out_p2)); c2p.metric("Proyeksi Pengeluaran Total", fmt(proj_end)); c3p.metric("Estimasi Sisa Cadangan", fmt(in_p2 - proj_end))

    with col_right:
        st.markdown('<div class="sec"><span class="sec-txt">Kondisi Lambung Kapal (Skor Sehat)</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        score = 0
        if not df_p2.empty and in_p2 > 0:
            rt = (in_p2-out_p2)/in_p2; ri = df_p2[(df_p2['Jenis']=='pengeluaran')&(df_p2['Kategori']=='Investasi')]['Nominal'].sum()/in_p2
            if rt>=0.3: score+=35
            elif rt>=0.1: score+=20
            elif rt>0: score+=10
            if ri>=0.2: score+=30
            elif ri>=0.1: score+=18
            elif ri>0: score+=8
            for kat,lim in st.session_state.budgets.items():
                sk = df_p2[(df_p2['Jenis']=='pengeluaran')&(df_p2['Kategori']==kat.strip().title())]['Nominal'].sum()
                if lim>0 and sk<=lim: score+=4
            score += min(int(rasio_t*30),30); score = min(score,100)
        gc_clr = "#0EA5E9" if score>=80 else "#FBBF24" if score>=60 else "#F87171" if score>=40 else "#EF4444"
        rad = math.radians((score/100)*180); x_e = 80+60*math.cos(math.pi-rad); y_e = 80-60*math.sin(rad)
        st.markdown(f"""
        <div style="text-align:center; padding-bottom:5px;">
        <svg width="160" height="95" viewBox="0 0 160 95">
            <path d="M 20 80 A 60 60 0 0 1 140 80" fill="none" stroke="rgba(14,165,233,0.15)" stroke-width="12" stroke-linecap="round"/>
            <path d="M 20 80 A 60 60 0 0 1 {x_e:.1f} {y_e:.1f}" fill="none" stroke="{gc_clr}" stroke-width="12" stroke-linecap="round" style="filter: drop-shadow(0 0 8px {gc_clr});"/>
            <text x="80" y="70" text-anchor="middle" fill="{gc_clr}" font-size="28" font-weight="800" font-family="Montserrat">{score}</text>
            <text x="80" y="86" text-anchor="middle" fill="#94A3B8" font-size="9" font-family="Inter" font-weight="700">INTEGRITAS / 100</text>
          </svg></div>""", unsafe_allow_html=True)
        
        st.markdown('<div class="sec" style="margin-top:0;"><span class="sec-txt">Hasil Pemindaian Sonar</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        for icon,title,txt in generate_insights(df_p2, in_p2, out_p2, st.session_state.budgets):
            st.markdown(f'<div class="insight-card"><div class="insight-icon" style="font-size:18px;">{icon}</div><div class="insight-txt" style="color:#CBD5E1;"><strong style="color:#38BDF8;">{title}</strong> — {txt}</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════
#  9. PAGE — KEUANGAN
# ══════════════════════════════════════════
def page_keuangan():
    if st.session_state.trigger_anim:
        anim_type = st.session_state.trigger_anim
        st.session_state.trigger_anim = None
        if anim_type == "Pemasukan": st.balloons()
        else: st.toast("⚓ Log Pengeluaran Terkirim.")

    st.markdown('<h2 style="font-size:22px;font-weight:800;color:#0EA5E9;font-family:\'Montserrat\',sans-serif;text-transform:uppercase;">💳 Panel Kendali Dana</h2>', unsafe_allow_html=True)
    tab_trx, tab_bgt, tab_cmp = st.tabs(["📋 Log Transaksi","🚨 Monitor Daya (Budget)","📅 Radar Perbandingan"])

    with tab_trx:
        c_form, c_list = st.columns([1, 1.8])
        with c_form:
            st.markdown('<div class="sec"><span class="sec-txt">➕ Input Log Baru</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
            with st.form("trx_v3", clear_on_submit=True):
                f_tgl = st.date_input("Waktu Kejadian", now.date())
                f_kat = st.selectbox("Sektor / Kategori", st.session_state.kategori_list)
                f_jen = st.radio("Jenis Aliran", ["Pemasukan","Pengeluaran"], horizontal=True)
                f_src = st.selectbox("Sumber Palka", list(porto.keys()))
                f_nom = st.text_input("Jumlah (Rp)", value=st.session_state.auto_nominal, placeholder="Contoh: 50.000")
                f_note= st.text_area("Keterangan Tambahan", placeholder="Masukkan rincian log...", height=64)
                
                if st.form_submit_button("🚀 TRANSMISI LOG", use_container_width=True):
                    try: nom = float(f_nom.replace(".","").replace(",","")) if f_nom else 0.0
                    except: nom = 0.0
                    tgl_s = f"{f_tgl.strftime('%Y-%m-%d')} {now.strftime('%H:%M:%S')}"
                    nr = pd.DataFrame([{"Tanggal":tgl_s,"Kategori":f_kat,"Jenis":f_jen,"Sumber Dana":f_src,"Nominal":nom,"Catatan":f_note}])
                    df_up = pd.concat([df_t, nr], ignore_index=True)
                    df_up['Tanggal'] = pd.to_datetime(df_up['Tanggal']).apply(fmt_tgl_sheet)
                    set_with_dataframe(ws_t, df_up)
                    st.session_state.auto_nominal = ""
                    st.session_state.trigger_anim = f_jen
                    st.cache_data.clear(); st.rerun()

        with c_list:
            st.markdown('<div class="sec"><span class="sec-txt">🔍 Pemindaian Riwayat</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
            sc1,sc2,sc3=st.columns([2,1,1])
            with sc1: q=st.text_input("Cari...",placeholder="Filter log...",label_visibility="collapsed")
            with sc2: fil_jen=st.selectbox("Jenis",["Semua","Pemasukan","Pengeluaran"],label_visibility="collapsed")
            with sc3: fil_kat=st.selectbox("Kat",["Semua"]+st.session_state.kategori_list,label_visibility="collapsed")
            
            if not df_t.empty:
                df_f=df_t.copy(); df_f['Jenis']=df_f['Jenis'].astype(str).str.strip().str.capitalize(); df_f['Kategori']=df_f['Kategori'].astype(str).str.strip().str.title()
                if fil_jen!="Semua": df_f=df_f[df_f['Jenis']==fil_jen]
                if fil_kat!="Semua": df_f=df_f[df_f['Kategori']==fil_kat]
                if q:
                    mask=(df_f['Kategori'].str.contains(q,case=False)|df_f.get('Catatan',pd.Series()).astype(str).str.contains(q,case=False)|df_f['Nominal'].astype(str).str.contains(q,case=False))
                    df_f=df_f[mask]
                df_f=df_f.sort_values('Tanggal',ascending=False).reset_index(); df_f['ID_Asli']=df_f['index']; df_f.index=range(1,len(df_f)+1)
                st.markdown(f'<p style="font-size:11px;color:#7DD3FC;margin-bottom:8px;font-weight:600;">Sistem mendeteksi {len(df_f)} log transaksi.</p>', unsafe_allow_html=True)
                
                df_show=df_f[['Tanggal','Kategori','Jenis','Sumber Dana','Nominal','Catatan']].copy()
                df_show['Tanggal']=df_show['Tanggal'].apply(lambda x:pd.to_datetime(x).strftime('%Y-%m-%d') if pd.notna(x) else "")
                df_show['Nominal']=df_show['Nominal'].apply(fmt)
                df_show=df_show.reset_index(); df_show.rename(columns={'index':'No'},inplace=True)
                fmt_tbl(df_show)

    with tab_bgt:
        b2=st.selectbox("Bulan Kendali:",NAMA_BULAN[1:],index=now.month-1,key="bgt_b"); bln2=NAMA_BULAN.index(b2); df_bgt=pd.DataFrame()
        if not df_t.empty:
            db2=df_t.copy(); db2['Jenis']=db2['Jenis'].str.lower().str.strip(); db2['Kategori']=db2['Kategori'].str.strip().str.title()
            df_bgt=db2[(db2['Tanggal'].dt.month==bln2)&(db2['Tanggal'].dt.year==now.year)]
        spent_bgt=df_bgt[df_bgt['Jenis']=='pengeluaran'].groupby('Kategori')['Nominal'].sum().to_dict() if not df_bgt.empty else {}
        cols_bgt=st.columns(min(len(st.session_state.budgets),4))
        for i,(kat,lim) in enumerate(st.session_state.budgets.items()):
            terpakai=spent_bgt.get(str(kat).strip().title(),0.0); rasio_b=min(terpakai/lim,1.0) if lim>0 else 1.0; sisa=lim-terpakai
            bc=("#0EA5E9" if rasio_b<0.5 else "#FBBF24" if rasio_b<0.85 else "#EF4444"); ico=("🟢" if rasio_b<0.5 else "🟡" if rasio_b<0.85 else "🔴")
            with cols_bgt[i%4]: st.markdown(f'<div class="bgt-card"><div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:11px;font-weight:700;color:#7DD3FC;text-transform:uppercase;">{ico} {kat}</span><span style="font-size:12px;color:{bc};font-weight:800;">{rasio_b*100:.0f}%</span></div><div style="font-size:15px;font-weight:800;color:#F8FAFC;font-family:\'Montserrat\',sans-serif;">{fmt(terpakai)}</div><div class="bar-track"><div class="bar-fill" style="width:{rasio_b*100:.0f}%;background:{bc};box-shadow:0 0 8px {bc};"></div></div><div style="font-size:11px;margin-top:8px;color:{"#0EA5E9" if sisa>=0 else "#EF4444"};font-weight:700;">{"✅ Daya Tersisa: "+fmt(sisa) if sisa>=0 else "🔥 Overload: "+fmt(abs(sisa))}</div><div style="font-size:9px;color:#64748B;font-weight:600;margin-top:2px;">Kapasitas Maksimal: {fmt(lim)}</div></div>', unsafe_allow_html=True)


# Mapping Halaman
PAGE_MAP = {
    "Dashboard":    page_dashboard,
    "Keuangan":     page_keuangan
    # Anda bisa tambahkan mapping halaman lain jika fungsi halamannya sudah dibuat
}

# Jika Anda berada di halaman yang fungsinya belum ada di kode ini, otomatis arahkan ke dashboard
fn = PAGE_MAP.get(st.session_state.page, page_dashboard)
fn()
