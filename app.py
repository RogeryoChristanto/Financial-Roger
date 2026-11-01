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
    page_title="ROGER Finance",
    page_icon="🍭",
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
#  2. CSS NATIVE — THEMA FUN & BUBBLY 🎨
# ══════════════════════════════════════════
def get_theme_vars():
    if st.session_state.get("theme", "dark") == "light":
        return """
        <style>
        html, body, .stApp, [data-testid="stAppViewContainer"] { background: #FFF0F5 !important; color: #4A4A4A !important; }
        .stApp::before { background: radial-gradient(circle, rgba(255,105,180,0.15) 0%, transparent 65%) !important; }
        .stApp::after  { background: radial-gradient(circle, rgba(0,242,254,0.15) 0%, transparent 65%) !important; }
        .topbar { background: rgba(255,255,255,0.95) !important; border-bottom: 2px dashed #FF9A9E !important; }
        .topbar-stat-label, .topbar-date { color: #888 !important; } .topbar-stat-value { color: #333 !important; }
        div[data-testid="metric-container"] { background: linear-gradient(145deg,#FFFFFF,#FFF0F5) !important; border: 2px solid #FFD1DC !important; }
        [data-testid="stMetricValue"] { color: #FF1493 !important; } [data-testid="stMetricLabel"] { color: #FF69B4 !important; font-weight:800 !important; }
        .ctbl { color: #555 !important; } .ctbl thead th { background: #FFE4E1 !important; color: #FF1493 !important; border-bottom: 2px dashed #FF9A9E !important; }
        .tbl-wrap { background: #FFFFFF !important; border: 2px solid #FFD1DC !important; }
        .bgt-card { background: #FFFFFF !important; border: 2px solid #FFD1DC !important; }
        .insight-card { background: #FFF0F5 !important; border: 2px solid #FFB6C1 !important; }
        .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input, .stSelectbox div[data-baseweb="select"] { background: #FFFFFF !important; border: 2px solid #FFB6C1 !important; color: #333 !important; border-radius: 16px !important; }
        label, .sec-txt { color: #FF1493 !important; font-weight: 800 !important; }
        [data-testid="stTabs"] div[data-baseweb="tab-list"] { background: #FFF0F5 !important; border: 2px solid #FFD1DC !important; border-radius: 20px !important; }
        </style>"""
    return ""

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&family=Nunito:wght@400;600;700;800;900&display=swap');

*,*::before,*::after{box-sizing:border-box;}
.stApp,[data-testid="stAppViewContainer"]{font-family:'Nunito',sans-serif!important;background:#1A0B2E!important;color:#F8F9FA!important;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#241542 0%,#1A0B2E 100%)!important;border-right:2px dashed rgba(255,0,127,0.3)!important;}

/* Animasi Background Fun */
.stApp::before{content:'';position:fixed;top:-20%;left:-10%;width:60%;height:60%; background:radial-gradient(circle,rgba(255,0,127,0.15) 0%,transparent 60%); pointer-events:none;z-index:0;animation:aurora1 15s ease-in-out infinite alternate; filter:blur(30px);}
.stApp::after{content:'';position:fixed;bottom:-20%;right:-10%;width:65%;height:65%; background:radial-gradient(circle,rgba(0,242,254,0.15) 0%,transparent 60%); pointer-events:none;z-index:0;animation:aurora2 18s ease-in-out infinite alternate; filter:blur(40px);}
@keyframes aurora1{from{transform:translate3d(0,0,0) scale(1);}to{transform:translate3d(60px,40px,0) scale(1.3);}}
@keyframes aurora2{from{transform:translate3d(0,0,0) scale(1);}to{transform:translate3d(-50px,-30px,0) scale(1.2);}}
@keyframes bounceUp{0%{opacity:0;transform:translate3d(0,20px,0);}100%{opacity:1;transform:translate3d(0,0,0);}}

/* Header & Topbar Native */
header[data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; z-index: 1000 !important; }
.stAppDeployButton, #MainMenu, footer { display: none !important; }

.topbar {
    position: fixed; top: 0; left: 0; width: 100%; height: 62px;
    background: rgba(26,11,46,0.9); backdrop-filter: blur(12px);
    border-bottom: 2px dashed rgba(0,242,254,0.3); z-index: 999;
    display: flex; align-items: center; padding: 0 20px 0 65px;
    box-shadow: 0 4px 30px rgba(255,0,127,0.15);
}
.topbar-divider { width: 2px; height: 28px; background: rgba(255,255,255,0.1); margin: 0 14px; border-radius:2px; }
.topbar-stat { display: flex; flex-direction: column; flex-shrink: 0; }
.topbar-stat-label { font-size: 9px; color: #A78BFA; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; font-family: 'Fredoka', sans-serif; }
.topbar-stat-value { font-size: 14px; font-weight: 900; margin-top: 1px; font-family: 'Fredoka', sans-serif; text-shadow: 0 2px 4px rgba(0,0,0,0.3); }
.topbar-right { margin-left: auto; display: flex; align-items: center; gap: 6px; }
.topbar-date { font-size: 12px; color: #FBCFE8; font-weight: 700; font-family: 'Nunito', sans-serif; }
.live-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#38ef7d;margin-right:8px;box-shadow: 0 0 10px #38ef7d;}
.block-container { padding-top: 85px !important; padding-bottom: 20px !important; max-width: 100% !important; }

/* Sulap st.radio jadi Tombol Menu Bubbly */
[data-testid="stSidebar"] [role="radiogroup"] { gap: 10px; }
[data-testid="stSidebar"] [role="radiogroup"] > label {
    width: 100%; padding: 14px 20px; border-radius: 20px; margin: 0;
    background: rgba(255,255,255,0.03); border: 2px solid transparent;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:hover {
    background: rgba(255,0,127,0.1); border-color: rgba(255,0,127,0.3); transform: scale(1.02);
}
[data-testid="stSidebar"] [role="radiogroup"] > label [data-baseweb="radio"] > div:first-child { display: none !important; }
[data-testid="stSidebar"] [role="radiogroup"] > label p {
    color: #E2E8F0; font-weight: 700; font-size: 15px; margin: 0; font-family: 'Fredoka', sans-serif;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(135deg, rgba(255,0,127,0.2), rgba(0,242,254,0.2)) !important;
    border: 2px solid #FF007F !important; box-shadow: 0 6px 20px rgba(255,0,127,0.25) !important;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p { color: #00F2FE !important; font-weight: 800 !important; text-shadow: 0 1px 2px rgba(0,0,0,0.5); }

/* Tombol Aksi Bawah Sidebar */
[data-testid="stSidebar"] button[kind="secondary"] {
    background: rgba(255,255,255,0.05) !important; border: 2px dashed rgba(255,255,255,0.15) !important;
    color: #F8B4D9 !important; padding: 12px 18px !important; font-weight: 700 !important; font-family: 'Fredoka', sans-serif !important;
    border-radius: 16px !important; transition: all 0.3s bounce !important;
}
[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: #FF007F !important; color: #FFF !important; border-style: solid !important; border-color: #FF007F !important; transform: translateY(-3px) !important; box-shadow: 0 8px 20px rgba(255,0,127,0.4) !important;
}

/* KARTU, TABEL, DAN METRIK FUN */
.stButton>button{background:linear-gradient(135deg,#FF007F 0%,#00F2FE 100%)!important;color:#fff!important;font-weight:800!important;font-size:14px!important;border-radius:18px!important;border:none!important;padding:12px 24px!important;font-family:'Fredoka',sans-serif!important;}
.stButton>button:hover{transform:translateY(-3px) scale(1.02)!important;box-shadow:0 10px 25px rgba(0,242,254,0.4)!important;}

div[data-testid="metric-container"]{background:rgba(255,255,255,0.03)!important;border:2px solid rgba(255,0,127,0.2)!important;border-radius:24px!important;padding:20px!important;box-shadow:0 8px 32px rgba(0,0,0,0.2)!important;transition:all .3s ease!important;animation:bounceUp .6s cubic-bezier(0.68, -0.55, 0.265, 1.55) both;}
div[data-testid="metric-container"]:hover{border-color:#00F2FE!important;transform:translateY(-5px)!important;box-shadow:0 12px 40px rgba(0,242,254,0.2)!important;}
[data-testid="stMetricValue"]{font-size:1.8rem!important;font-weight:900!important;color:#FEE140!important;font-family:'Fredoka',sans-serif!important;text-shadow:0 2px 4px rgba(0,0,0,0.4)!important;}
[data-testid="stMetricLabel"]{font-size:11px!important;font-weight:800!important;color:#FBCFE8!important;text-transform:uppercase!important;letter-spacing:1.5px!important;}

.wallet-row{display:flex;gap:16px;flex-wrap:nowrap;overflow-x:auto;padding-bottom:12px;scrollbar-width:none;}
.wcard{min-width:200px;flex:1;border-radius:28px;padding:24px 20px;position:relative;overflow:hidden;transition:all .3s cubic-bezier(.4,0,.2,1)!important;animation:bounceUp .7s cubic-bezier(0.68, -0.55, 0.265, 1.55) both; border:none;}
.wcard::before{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(circle,rgba(255,255,255,0.15) 0%,transparent 60%); pointer-events:none;}
.wcard:hover{transform:translateY(-8px) scale(1.02); box-shadow: 0 15px 35px rgba(0,0,0,0.3);}
.wcard-chip{position:absolute;top:16px;right:16px;width:32px;height:24px;border-radius:6px;background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.4);}
.wcard-icon{font-size:28px;margin-bottom:16px;filter:drop-shadow(0 4px 6px rgba(0,0,0,0.3));}
.wcard-lbl{font-size:10px;font-weight:800;color:rgba(255,255,255,.9);text-transform:uppercase;letter-spacing:2px;margin-bottom:6px;font-family:'Nunito',sans-serif;}
.wcard-bal{font-size:21px;font-weight:900;color:#fff;font-family:'Fredoka',sans-serif;text-shadow:0 3px 6px rgba(0,0,0,0.3);}
/* Warna Gradient Wcard Super Bubbly */
.wcard-bca{background:linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);}
.wcard-bri{background:linear-gradient(135deg, #ff0844 0%, #ffb199 100%);}
.wcard-jago{background:linear-gradient(135deg, #f83600 0%, #f9d423 100%);}
.wcard-cash{background:linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);}

.sec{display:flex;align-items:center;gap:12px;margin:28px 0 16px;}
.sec-txt{font-size:11px;font-weight:900;color:#00F2FE;text-transform:uppercase;letter-spacing:3px;font-family:'Fredoka',sans-serif;}
.sec-line{flex:1;height:2px;background:linear-gradient(90deg,rgba(0,242,254,0.5),rgba(255,0,127,0.2),transparent); border-radius:2px;}
.tbl-wrap{background:rgba(26,11,46,.8);border:2px solid rgba(255,0,127,0.2);border-radius:24px;overflow:auto;max-height:400px;box-shadow:0 8px 32px rgba(0,0,0,0.4);}
.ctbl{width:100%;border-collapse:collapse;color:#E2E8F0;font-size:13px;font-family:'Nunito',sans-serif;}
.ctbl thead th{position:sticky;top:0;background:#241542;padding:14px 18px;font-weight:800;color:#FEE140;text-transform:uppercase;letter-spacing:1.5px;font-size:10px;border-bottom:2px dashed rgba(255,0,127,0.3);z-index:1;}
.ctbl td{padding:12px 18px;border-bottom:1px solid rgba(255,255,255,.05);}
.ctbl tbody tr:hover td{background:rgba(0,242,254,.1);color:#FFF;}
[data-testid="stTabs"] div[data-baseweb="tab-list"]{gap:4px;background:rgba(0,0,0,.2);border-radius:18px;padding:6px;border:2px solid rgba(255,255,255,0.05);}
[data-testid="stTabs"] button[data-baseweb="tab"]{background:transparent;border-radius:14px;padding:10px 20px;font-weight:700;font-size:13px;color:#A78BFA;border:none;font-family:'Fredoka',sans-serif;}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(135deg,#FF007F,#7928CA);color:#FFF;box-shadow:0 4px 15px rgba(255,0,127,.4);border:none;}

/* Input Forms Bubbly */
.stTextInput input,.stNumberInput input,.stTextArea textarea,.stDateInput input, .stSelectbox div[data-baseweb="select"] {background:rgba(0,0,0,.2)!important;border:2px solid rgba(255,0,127,0.3)!important;border-radius:16px!important;color:#FFF!important;font-size:14px!important;font-family:'Nunito',sans-serif!important;font-weight:600!important;}
.stTextInput input:focus,.stNumberInput input:focus,.stTextArea textarea:focus{border-color:#00F2FE!important;box-shadow:0 0 0 4px rgba(0,242,254,.2)!important;}
label{color:#FBCFE8!important;font-size:11px!important;font-weight:800!important;text-transform:uppercase;letter-spacing:1px;}
.stProgress>div>div{background:linear-gradient(90deg,#00F2FE,#4facfe)!important;border-radius:12px!important;box-shadow:0 0 10px #00F2FE;}
.stProgress>div{background:rgba(255,255,255,0.05)!important;border-radius:12px!important;}

.insight-card{background:rgba(255,255,255,0.03);border:2px solid rgba(0,242,254,0.2);border-radius:20px;padding:16px 18px;margin-bottom:10px;display:flex;align-items:flex-start;gap:12px;transition:all .3s cubic-bezier(0.68,-0.55,0.265,1.55);}
.insight-card:hover{border-color:#00F2FE;transform:translateX(6px) scale(1.01);box-shadow:0 5px 15px rgba(0,242,254,0.15);}
.bgt-card{background:rgba(255,255,255,0.02);border:2px dashed rgba(255,0,127,0.2);border-radius:20px;padding:16px 18px;margin-bottom:10px;transition:transform .3s;}
.bgt-card:hover{border-style:solid;border-color:#FF007F;transform:translateY(-3px);box-shadow:0 5px 15px rgba(255,0,127,0.15);}
.bar-track{width:100%;background:rgba(0,0,0,0.3);border-radius:12px;height:8px;margin-top:10px;}
.bar-fill{height:100%;border-radius:12px;transition:width 1s cubic-bezier(0.68,-0.55,0.265,1.55);}
::-webkit-scrollbar{width:6px;height:6px;} ::-webkit-scrollbar-track{background:transparent;} ::-webkit-scrollbar-thumb{background:rgba(255,0,127,0.4);border-radius:10px;} ::-webkit-scrollbar-thumb:hover{background:#FF007F;}
</style>
""", unsafe_allow_html=True)

st.markdown(get_theme_vars(), unsafe_allow_html=True)

# ══════════════════════════════════════════
#  LOGIN FUN (TANPA TOMBOL, CUKUP ENTER)
# ══════════════════════════════════════════
if not st.session_state.authenticated:
    st.markdown("<style>[data-testid='collapsedControl']{display:none!important} section[data-testid='stSidebar']{display:none!important} .topbar{display:none!important;}</style>", unsafe_allow_html=True)
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.2, 1])
    
    with mid:
        st.markdown("""
        <div style='text-align:center;margin-bottom:30px;animation:bounceUp 0.8s cubic-bezier(0.68, -0.55, 0.265, 1.55) both;'>
            <div style='font-size:56px;font-weight:900;letter-spacing:-2px;font-family:"Fredoka",sans-serif;background:linear-gradient(135deg,#FF007F,#00F2FE,#FEE140);-webkit-background-clip:text;-webkit-text-fill-color:transparent;filter:drop-shadow(0 4px 10px rgba(255,0,127,0.4));'>ROGER</div>
            <div style='font-size:12px;color:#FBCFE8;letter-spacing:4px;text-transform:uppercase;font-weight:800;margin-top:8px;'>✨ Fun Finance Dashboard ✨</div>
        </div>
        """, unsafe_allow_html=True)
        
        # HANYA TEXT INPUT (Tanpa st.form). Otomatis trigger rerun saat ditekan Enter!
        pin_input = st.text_input("Masukan PIN Akses (Lalu tekan Enter)", type="password", placeholder="Ketik PIN & tekan Enter ➔", key="pin_login_input")
        
        if pin_input:
            if pin_input == st.session_state.saved_pin:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Oops! PIN-nya keliru nih. Coba cek lagi ya! 🧐")
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
if not db: st.error("❌ Gagal koneksi ke Google Sheets. Cek secrets konfigurasi."); st.stop()

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
#  3. TOPBAR FIXED NATIVE HTML
# ══════════════════════════════════════════
st.markdown(f"""
<div class="topbar">
    <div class="topbar-stat"><span class="topbar-stat-label">Net Worth</span><span class="topbar-stat-value" style="color:#00F2FE;">{_fmt_top(total_net)}</span></div>
    <div class="topbar-divider"></div>
    <div class="topbar-stat"><span class="topbar-stat-label">Kas</span><span class="topbar-stat-value" style="color:#38ef7d;">{_fmt_top(total_cash)}</span></div>
    <div class="topbar-divider"></div>
    <div class="topbar-stat"><span class="topbar-stat-label">Saham</span><span class="topbar-stat-value" style="color:#FEE140;">{_fmt_top(total_saham)}</span></div>
    <div class="topbar-right">
        <span class="topbar-date"><span class="live-dot"></span>{now.strftime("%H:%M")} · {now.strftime("%d %b %Y")}</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════
#  4. SIDEBAR NATIVE BERSAMA ST.RADIO
# ══════════════════════════════════════════
NAV_PAGES = [
    ("Dashboard",   "🏠"), ("Keuangan",    "💳"),
    ("Portofolio",  "📈"), ("AI Advisor",  "🤖"),
    ("Rekomendasi", "⭐"), ("Screener",    "⚡"),
    ("Scanner",     "🧾"), ("Pengaturan",  "⚙️")
]

with st.sidebar:
    st.markdown('''
    <div style="text-align:center; padding: 10px 0 25px;">
        <div style="font-size: 32px; font-weight: 900; background: linear-gradient(135deg, #FF007F, #00F2FE, #FEE140); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -1px; font-family: 'Fredoka', sans-serif;">💎 ROGER</div>
        <div style="font-size:10px;color:#FBCFE8;letter-spacing:3px;margin-top:4px;font-weight:800;text-transform:uppercase;">Fun Dashboard</div>
    </div>
    ''', unsafe_allow_html=True)
    
    # 4a. Navigasi Pakai st.radio murni Python
    radio_opts = [f"{icon} {name}" for name, icon in NAV_PAGES]
    cur_idx = next((i for i, (name, _) in enumerate(NAV_PAGES) if name == st.session_state.page), 0)
    
    selected_menu = st.radio("Menu Navigasi", radio_opts, index=cur_idx, label_visibility="collapsed")
    
    for name, icon in NAV_PAGES:
        if f"{icon} {name}" == selected_menu:
            if st.session_state.page != name:
                st.session_state.page = name
                st.rerun()
            break
            
    st.markdown("<hr style='border: 1px dashed rgba(255,0,127,0.3); margin: 20px 0;'>", unsafe_allow_html=True)
    
    # 4b. Action Buttons Pakai st.button
    label_mata = "👀 Tampilkan Saldo" if st.session_state.hide_balance else "🙈 Sembunyikan Saldo"
    if st.button(label_mata, use_container_width=True):
        st.session_state.hide_balance = not st.session_state.hide_balance
        st.rerun()
        
    if st.button("🎨 Ubah Tema Biasa", use_container_width=True):
        st.session_state.theme = "light" if st.session_state.get("theme", "dark") == "dark" else "dark"
        st.rerun()
        
    if st.button("🔒 Kunci Aplikasi", use_container_width=True):
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
    if rasio_hemat >= 30: insights.append(("🎉","Mantap Nabung!",f"Berhasil simpan <strong>{rasio_hemat:.1f}%</strong> cuan bulan ini."))
    elif rasio_hemat < 0: insights.append(("🚨","Boncos Alert!",f"Pengeluaran bablas melebihi pemasukan <strong>{fmt(abs(out_curr-in_curr))}</strong>. Rem dikit bos!"))
    elif rasio_hemat < 10: insights.append(("⚠️","Pas-pasan",f"Rasio tabungan sisa <strong>{rasio_hemat:.1f}%</strong>. Hati-hati kantong kering."))
    if not out_df.empty:
        top_kat = out_df.groupby('Kategori')['Nominal'].sum().idxmax()
        top_val = out_df.groupby('Kategori')['Nominal'].sum().max()
        insights.append(("🛍️","Raja Belanja",f"Sering banget jajan di: <strong>{top_kat}</strong> habis <strong>{fmt(top_val)}</strong>."))
    for kat, limit in budgets.items():
        spent = out_df[out_df['Kategori'] == kat.strip().title()]['Nominal'].sum()
        if limit > 0 and spent > limit: insights.append(("🔴","Jebol Dong",f"Budget <strong>{kat}</strong> tembus limit! Kelebihan <strong>{fmt(spent-limit)}</strong>."))
    inv = out_df[out_df['Kategori'] == 'Investasi']['Nominal'].sum(); inv_pct = inv / in_curr * 100
    if inv_pct < 10: insights.append(("💡","Yuk Invest",f"Baru <strong>{inv_pct:.1f}%</strong> buat invest. Naikin ke 20% biar masa depan cerah!"))
    elif inv_pct >= 20: insights.append(("🌱","Investor Sejati",f"Mantul! Porsi investasi udah <strong>{inv_pct:.1f}%</strong>. Keep it up!"))
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
    st.markdown('<h2 style="font-size:24px;font-weight:900;color:#00F2FE;margin-bottom:0;font-family:\'Fredoka\',sans-serif;">👋 Halo, ROGER!</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#FBCFE8;font-size:13px;margin-top:2px;">{now.strftime("%A, %d %B %Y · %H:%M")} WIB</p>', unsafe_allow_html=True)

    today_mask = (df_t['Tanggal'].dt.date == now.date()) if not df_t.empty else pd.Series(dtype=bool)
    df_today   = df_t[today_mask].copy() if not df_t.empty else pd.DataFrame()
    if not df_today.empty:
        df_today['Jenis'] = df_today['Jenis'].str.lower().str.strip(); df_today['Kategori'] = df_today['Kategori'].str.strip().str.title()
        df_today = df_today.sort_values('Tanggal', ascending=False)
    ti  = df_today[df_today['Jenis']=='pemasukan']['Nominal'].sum()   if not df_today.empty else 0.0
    to_ = df_today[df_today['Jenis']=='pengeluaran']['Nominal'].sum() if not df_today.empty else 0.0
    nd  = ti - to_; nc = "#34D399" if nd >= 0 else "#F87171"

    m1,m2,m3 = st.columns(3)
    m1.metric("🌟 Harta Karun (Net Worth)", fmt(total_net)); m2.metric("💵 Duit Dingin (Tunai)", fmt(total_cash)); m3.metric("📈 Total Saham", fmt(total_saham))
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec"><span class="sec-txt">💳 Dompet Ajaib</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
    wc = st.columns(4)
    for i,(key,name,icon,cls) in enumerate([("BCA","Bank BCA","🏦","wcard-bca"),("BRI","Bank BRI","🏢","wcard-bri"),("Bank Jago","Bank Jago","🦊","wcard-jago"),("Dompet (Cash)","Uang Tunai","💵","wcard-cash")]):
        with wc[i]: st.markdown(f'<div class="wcard {cls}"><div class="wcard-chip"></div><div class="wcard-icon">{icon}</div><div class="wcard-lbl">{name}</div><div class="wcard-bal">{fmt(porto[key])}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True); col_left, col_right = st.columns([2,1])
    with col_left:
        st.markdown('<div class="sec"><span class="sec-txt">🎯 Target Jadi Sultan</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        tgt = st.number_input("Target Harta Bersih (Rp)", value=int(st.session_state.target_harta), step=1000000, label_visibility="collapsed", format="%d")
        st.session_state.target_harta = tgt; save_config()
        rasio_t = max(0.0, min(total_net/tgt, 1.0)) if tgt > 0 else 0.0; pct_t = rasio_t * 100
        pc = "#00F2FE" if pct_t>=80 else "#FF007F" if pct_t>=50 else "#FEE140" if pct_t>=25 else "#F87171"
        st.progress(rasio_t); st.markdown(f'<p style="font-size:13px;color:{pc};font-weight:800;margin-top:6px;">🚀 {pct_t:.1f}% on the way jadi Sultan! — {fmt(total_net)} dari {fmt(tgt)}</p>', unsafe_allow_html=True)
        
        st.markdown('<div class="sec"><span class="sec-txt">🔮 Ramalan Akhir Bulan</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        b_proj = st.selectbox("Bulan Proyeksi:", NAMA_BULAN[1:], index=now.month-1, key="db_proj", label_visibility="collapsed")
        bln_p = NAMA_BULAN.index(b_proj); df_p2 = pd.DataFrame(); in_p2 = out_p2 = 0.0
        if not df_t.empty:
            dc2 = df_t.copy(); dc2['Jenis'] = dc2['Jenis'].str.lower().str.strip(); dc2['Kategori'] = dc2['Kategori'].str.strip().str.title()
            df_p2 = dc2[(dc2['Tanggal'].dt.month==bln_p)&(dc2['Tanggal'].dt.year==now.year)]
            in_p2 = df_p2[df_p2['Jenis']=='pemasukan']['Nominal'].sum(); out_p2 = df_p2[df_p2['Jenis']=='pengeluaran']['Nominal'].sum()
        proj_end, all_days, all_cum = project_monthend(df_p2, bln_p, now.year)
        c1p,c2p,c3p = st.columns(3); c1p.metric("Habis s/d Kini", fmt(out_p2)); c2p.metric("Bakal Habis Segini", fmt(proj_end)); c3p.metric("Sisa Dompet", fmt(in_p2 - proj_end))

    with col_right:
        st.markdown('<div class="sec"><span class="sec-txt">💪 Skor Sehat Keuangan</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
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
        gc_clr = "#00F2FE" if score>=80 else "#FEE140" if score>=60 else "#FF9A9E" if score>=40 else "#FF0844"
        rad = math.radians((score/100)*180); x_e = 80+60*math.cos(math.pi-rad); y_e = 80-60*math.sin(rad)
        st.markdown(f"""
        <div style="text-align:center; padding-bottom:10px;">
        <svg width="160" height="95" viewBox="0 0 160 95">
            <path d="M 20 80 A 60 60 0 0 1 140 80" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="16" stroke-linecap="round"/>
            <path d="M 20 80 A 60 60 0 0 1 {x_e:.1f} {y_e:.1f}" fill="none" stroke="{gc_clr}" stroke-width="16" stroke-linecap="round"/>
            <text x="80" y="70" text-anchor="middle" fill="{gc_clr}" font-size="28" font-weight="900" font-family="Fredoka">{score}</text>
            <text x="80" y="86" text-anchor="middle" fill="#FBCFE8" font-size="10" font-family="Nunito" font-weight="800">/ 100 POINT</text>
          </svg></div>""", unsafe_allow_html=True)
        
        st.markdown('<div class="sec" style="margin-top:0;"><span class="sec-txt">💡 Insight Pintar</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        for icon,title,txt in generate_insights(df_p2, in_p2, out_p2, st.session_state.budgets):
            st.markdown(f'<div class="insight-card"><div class="insight-icon" style="font-size:20px;">{icon}</div><div class="insight-txt" style="color:#E2E8F0;"><strong style="color:#00F2FE;">{title}</strong> — {txt}</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════
#  9. PAGE — KEUANGAN
# ══════════════════════════════════════════
def page_keuangan():
    if st.session_state.trigger_anim:
        anim_type = st.session_state.trigger_anim
        st.session_state.trigger_anim = None
        if anim_type == "Pemasukan": st.balloons()
        else: st.toast("💸 Yaaah, duit keluar! Berhasil dicatat ya.")

    st.markdown('<h2 style="font-size:24px;font-weight:900;color:#FF007F;font-family:\'Fredoka\',sans-serif;">💳 Catat & Pantau Keuangan</h2>', unsafe_allow_html=True)
    tab_trx, tab_bgt, tab_cmp = st.tabs(["📋 Catat Transaksi","🚨 Pengingat Budget","📅 Perbandingan"])

    with tab_trx:
        c_form, c_list = st.columns([1, 1.8])
        with c_form:
            st.markdown('<div class="sec"><span class="sec-txt">➕ Input Duit Baru</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
            with st.form("trx_v3", clear_on_submit=True):
                f_tgl = st.date_input("Tanggal Transaksi", now.date())
                f_kat = st.selectbox("Buat Apaan tuh?", st.session_state.kategori_list)
                f_jen = st.radio("Jenis", ["Pemasukan","Pengeluaran"], horizontal=True)
                f_src = st.selectbox("Dari Dompet Mana?", list(porto.keys()))
                f_nom = st.text_input("Berapa Banyak (Rp)?", value=st.session_state.auto_nominal, placeholder="Contoh: 50.000")
                f_note= st.text_area("Catatan Biar Inget", placeholder="Tulis rinciannya di sini...", height=64)
                
                if st.form_submit_button("🚀 SIMPAN TRANSAKSI", use_container_width=True):
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
            st.markdown('<div class="sec"><span class="sec-txt">🔍 Jejak Pengeluaran</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
            sc1,sc2,sc3=st.columns([2,1,1])
            with sc1: q=st.text_input("Cari...",placeholder="Mau cari apa?...",label_visibility="collapsed")
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
                st.markdown(f'<p style="font-size:12px;color:#FBCFE8;margin-bottom:8px;font-weight:700;">Ketemu {len(df_f)} transaksi nih.</p>', unsafe_allow_html=True)
                
                df_show=df_f[['Tanggal','Kategori','Jenis','Sumber Dana','Nominal','Catatan']].copy()
                df_show['Tanggal']=df_show['Tanggal'].apply(lambda x:pd.to_datetime(x).strftime('%Y-%m-%d') if pd.notna(x) else "")
                df_show['Nominal']=df_show['Nominal'].apply(fmt)
                df_show=df_show.reset_index(); df_show.rename(columns={'index':'No'},inplace=True)
                fmt_tbl(df_show)

    with tab_bgt:
        b2=st.selectbox("Bulan:",NAMA_BULAN[1:],index=now.month-1,key="bgt_b"); bln2=NAMA_BULAN.index(b2); df_bgt=pd.DataFrame()
        if not df_t.empty:
            db2=df_t.copy(); db2['Jenis']=db2['Jenis'].str.lower().str.strip(); db2['Kategori']=db2['Kategori'].str.strip().str.title()
            df_bgt=db2[(db2['Tanggal'].dt.month==bln2)&(db2['Tanggal'].dt.year==now.year)]
        spent_bgt=df_bgt[df_bgt['Jenis']=='pengeluaran'].groupby('Kategori')['Nominal'].sum().to_dict() if not df_bgt.empty else {}
        cols_bgt=st.columns(min(len(st.session_state.budgets),4))
        for i,(kat,lim) in enumerate(st.session_state.budgets.items()):
            terpakai=spent_bgt.get(str(kat).strip().title(),0.0); rasio_b=min(terpakai/lim,1.0) if lim>0 else 1.0; sisa=lim-terpakai
            bc=("#00F2FE" if rasio_b<0.5 else "#FEE140" if rasio_b<0.85 else "#FF0844"); ico=("🟢" if rasio_b<0.5 else "🟡" if rasio_b<0.85 else "🔴")
            with cols_bgt[i%4]: st.markdown(f'<div class="bgt-card"><div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:12px;font-weight:800;color:#FBCFE8;text-transform:uppercase;">{ico} {kat}</span><span style="font-size:13px;color:{bc};font-weight:900;">{rasio_b*100:.0f}%</span></div><div style="font-size:16px;font-weight:900;color:#FFF;font-family:\'Fredoka\',sans-serif;">{fmt(terpakai)}</div><div class="bar-track"><div class="bar-fill" style="width:{rasio_b*100:.0f}%;background:{bc};"></div></div><div style="font-size:12px;margin-top:8px;color:{"#00F2FE" if sisa>=0 else "#FF0844"};font-weight:800;">{"✅ Sisa Aman: "+fmt(sisa) if sisa>=0 else "🔥 Minus: "+fmt(abs(sisa))}</div><div style="font-size:10px;color:#A78BFA;font-weight:700;">Jatah Awal: {fmt(lim)}</div></div>', unsafe_allow_html=True)


# Mapping Halaman
PAGE_MAP = {
    "Dashboard":    page_dashboard,
    "Keuangan":     page_keuangan
}
fn = PAGE_MAP.get(st.session_state.page, page_dashboard)
fn()
