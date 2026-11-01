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
    page_title="ROGER Fun Marine",
    page_icon="🐠",
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
    st.markdown(f'<div class="tbl-wrap">{df.to_html(classes="ctbl",index=False,escape=False)}</div>', unsafe_allow_html=True)

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
                if len(p) == 3: d = f"{p[2]}-{p[1]}-{p[0]}" if len(p[2]) == 4 else f"{p[0]}-{p[1]}-{p[2]}"
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
#  2. CSS NATIVE — THEMA FUN MARITIME (KARTUN) 🐠🦀
# ══════════════════════════════════════════
def get_theme_vars():
    # Mengosongkan karena kita pakai Custom CSS tebal di bawah
    return ""

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&family=Nunito:wght@400;600;700;800;900&display=swap');

*,*::before,*::after{box-sizing:border-box;}

/* 1. WALLPAPER LAUT KARTUN CERIA */
.stApp,[data-testid="stAppViewContainer"]{
    font-family:'Nunito',sans-serif!important;
    background-color: #0093E9 !important;
    background-image: linear-gradient(160deg, #0093E9 0%, #80D0C7 100%) !important;
    color: #0B2A4A !important;
}

/* 2. ANIMASI GELEMBUNG (BUBBLES) */
.stApp::before {
    content: ''; position: fixed; inset: 0;
    background-image: 
        radial-gradient(rgba(255,255,255,0.4) 2px, transparent 4px),
        radial-gradient(rgba(255,255,255,0.2) 1px, transparent 3px);
    background-size: 100px 100px, 60px 60px;
    background-position: 0 0, 30px 30px;
    animation: bubbleUp 20s linear infinite;
    pointer-events: none; z-index: 0;
}
@keyframes bubbleUp { 100% { background-position: 0 -1000px, 30px -1000px; } }

/* SIDEBAR KACA TEBAL (GLASSMORPHISM) */
[data-testid="stSidebar"]{
    background: rgba(255, 255, 255, 0.4) !important;
    backdrop-filter: blur(20px) !important;
    border-right: 3px solid rgba(255,255,255,0.7) !important;
    box-shadow: 5px 0 20px rgba(0, 147, 233, 0.3) !important;
}

/* Header & Topbar Native ala Papan Pengumuman Kartun */
header[data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; z-index: 1000 !important; }
.stAppDeployButton, #MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }

.topbar {
    position: fixed; top: 0; left: 0; width: 100%; height: 65px;
    background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(15px);
    border-bottom: 4px solid #0093E9; z-index: 999;
    display: flex; align-items: center; 
    padding: 0 90px 0 65px; /* Jarak aman di kanan */
    box-shadow: 0 6px 15px rgba(0, 147, 233, 0.2);
    border-radius: 0 0 20px 20px; /* Bawah membulat */
}
.topbar-divider { width: 3px; height: 30px; background: #80D0C7; margin: 0 16px; border-radius: 5px; }
.topbar-stat { display: flex; flex-direction: column; flex-shrink: 0; }
.topbar-stat-label { font-size: 10px; color: #005C97; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; font-family: 'Fredoka', sans-serif; }
.topbar-stat-value { font-size: 15px; font-weight: 900; margin-top: 2px; color: #FF7F50; font-family: 'Fredoka', sans-serif; }
.topbar-right { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.topbar-date { font-size: 12px; color: #005C97; font-weight: 700; font-family: 'Nunito', sans-serif;}

/* BUBBLE PING */
.live-dot { position: relative; display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #FF7F50; margin-right: 8px; }
@keyframes pingSonar { 0% { transform: scale(1); opacity: 1; } 100% { transform: scale(3); opacity: 0; } }
.live-dot::after { content: ''; position: absolute; inset: -4px; border-radius: 50%; border: 3px solid #FF7F50; animation: pingSonar 1.5s ease-out infinite; pointer-events: none; }

.block-container { padding-top: 90px !important; padding-bottom: 20px !important; max-width: 100% !important; z-index: 2; position: relative;}

/* Menu Navigasi Bubbly */
[data-testid="stSidebar"] [role="radiogroup"] { gap: 10px; }
[data-testid="stSidebar"] [role="radiogroup"] > label {
    width: 100%; padding: 12px 18px; border-radius: 20px; margin: 0;
    background: rgba(255,255,255,0.3); border: 2px solid transparent;
    transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55); cursor: pointer;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:hover {
    background: rgba(255,255,255,0.7); transform: scale(1.03); border-color: #80D0C7;
}
[data-testid="stSidebar"] [role="radiogroup"] > label [data-baseweb="radio"] > div:first-child { display: none !important; }
[data-testid="stSidebar"] [role="radiogroup"] > label p {
    color: #005C97; font-weight: 800; font-size: 15px; margin: 0; font-family: 'Fredoka', sans-serif;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
    background: #0093E9 !important; border: 3px solid #FFF !important; box-shadow: 0 5px 15px rgba(0, 147, 233, 0.5) !important;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p { color: #FFF !important; font-size: 16px !important; }

/* Tombol Aksi Bawah Sidebar */
[data-testid="stSidebar"] button[kind="secondary"] {
    background: rgba(255,255,255,0.6) !important; border: 3px solid #80D0C7 !important;
    color: #005C97 !important; padding: 12px 16px !important; font-weight: 800 !important; font-family: 'Fredoka', sans-serif !important;
    border-radius: 18px !important; transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55) !important;
}
[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: #0093E9 !important; border-color: #FFF !important; color: #FFF !important; transform: translateY(-5px) !important; box-shadow: 0 8px 15px rgba(0, 147, 233, 0.4) !important;
}

/* BUTTON UTAMA (TOMBOL EMAS) */
.stButton>button{background:#FFD700 !important; color:#0B2A4A !important;font-weight:900!important;font-size:15px!important;border-radius:20px!important;border:3px solid #FFF !important;padding:12px 24px!important;font-family:'Fredoka',sans-serif!important;box-shadow: 0 5px 0 #D4AF37 !important; transition:all 0.1s ease!important;}
.stButton>button:hover{transform:translateY(3px)!important;box-shadow: 0 2px 0 #D4AF37 !important; filter: brightness(1.1);}

/* KARTU METRIK ATAS */
@keyframes bounceInUp { from { opacity:0; transform: translateY(30px); } to { opacity:1; transform: translateY(0); } }
div[data-testid="metric-container"]{
    background: rgba(255,255,255,0.85) !important; border: 3px solid #FFF !important; border-radius: 24px !important; padding: 18px !important;
    box-shadow: 0 10px 25px rgba(0, 92, 151, 0.2) !important;
    animation: bounceInUp 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55) both;
    transition: transform .3s ease !important;
}
div[data-testid="metric-container"]:hover{transform:translateY(-8px) scale(1.02)!important;}
[data-testid="stMetricValue"]{font-size:1.8rem!important;font-weight:900!important;color:#0093E9!important;font-family:'Fredoka',sans-serif!important;}
[data-testid="stMetricLabel"]{font-size:12px!important;font-weight:800!important;color:#FF7F50!important;text-transform:uppercase!important;letter-spacing:1px!important;}

/* KARTU DOMPET KARTUN */
.wallet-row{display:flex;gap:16px;flex-wrap:nowrap;overflow-x:auto;padding-bottom:12px;scrollbar-width:none;}
.wcard{
    min-width:210px;flex:1;border-radius:24px;padding:22px 20px;position:relative;overflow:hidden;
    transition:all .3s cubic-bezier(0.68, -0.55, 0.265, 1.55)!important; border:3px solid rgba(255,255,255,0.6);
    animation: bounceInUp 0.7s cubic-bezier(0.68, -0.55, 0.265, 1.55) both;
}
/* Efek Kilat / Ombak di Kartu */
@keyframes waveShine { 0% { left: -150%; } 100% { left: 150%; } }
.wcard::after{
    content:''; position:absolute; top:0; left:-150%; width:100%; height:100%;
    background:linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
    transform:skewX(-25deg); animation: waveShine 4s infinite; pointer-events: none;
}
.wcard:hover{transform:translateY(-8px); box-shadow: 0 15px 30px rgba(0, 92, 151, 0.3); border-color:#FFF;}
.wcard-icon{font-size:32px;margin-bottom:10px;filter:drop-shadow(0 4px 4px rgba(0,0,0,0.2));}
.wcard-lbl{font-size:11px;font-weight:800;color:rgba(255,255,255,0.9);text-transform:uppercase;letter-spacing:1px;font-family:'Nunito',sans-serif;}
.wcard-bal{font-size:22px;font-weight:900;color:#fff;font-family:'Fredoka',sans-serif;}

/* Palet Warna Laut Tropis (Cerah) */
.wcard-bca{background:linear-gradient(135deg, #1CB5E0 0%, #000046 100%);} /* Biru Tua-Muda */
.wcard-bri{background:linear-gradient(135deg, #f12711 0%, #f5af19 100%);} /* Oranye Karang */
.wcard-jago{background:linear-gradient(135deg, #8A2387 0%, #E94057 50%, #F27121 100%);} /* Ungu Bintang Laut */
.wcard-cash{background:linear-gradient(135deg, #11998e 0%, #38ef7d 100%);} /* Hijau Rumput Laut */

.sec{display:flex;align-items:center;gap:12px;margin:28px 0 16px; animation: bounceInUp 0.8s ease-out both;}
.sec-txt{font-size:13px;font-weight:900;color:#FFF;text-transform:uppercase;letter-spacing:2px;font-family:'Fredoka',sans-serif; text-shadow: 0 2px 4px rgba(0,0,0,0.2);}
.sec-line{flex:1;height:4px;background:#FFF; border-radius:10px;}

/* Tabel Papan Tulis Kapal */
.tbl-wrap{background:rgba(255,255,255,0.9); border:3px solid #FFF; border-radius:20px;overflow:auto;max-height:400px;box-shadow:0 10px 25px rgba(0,92,151,0.2); animation: bounceInUp 0.9s ease-out both;}
.ctbl{width:100%;border-collapse:collapse;color:#0B2A4A;font-size:13px;font-family:'Nunito',sans-serif;}
.ctbl thead th{position:sticky;top:0;background:#0093E9;padding:14px 16px;font-weight:800;color:#FFF;text-transform:uppercase;font-size:11px;border-bottom:3px solid #FFF;z-index:1;}
.ctbl td{padding:14px 16px;border-bottom:2px dashed rgba(0,147,233,0.3);}
.ctbl tbody tr:hover td{background:rgba(0,147,233,0.1);}

/* Tabs Bubbly */
[data-testid="stTabs"] div[data-baseweb="tab-list"]{gap:8px;background:rgba(255,255,255,0.4); border-radius:20px;padding:8px;border:3px solid #FFF;}
[data-testid="stTabs"] button[data-baseweb="tab"]{background:transparent;border-radius:14px;padding:10px 20px;font-weight:800;font-size:14px;color:#005C97;border:none;font-family:'Fredoka',sans-serif; transition: all 0.3s;}
[data-testid="stTabs"] button[data-baseweb="tab"]:hover{background:rgba(255,255,255,0.5);}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"]{background:#0093E9;color:#FFF;border:2px solid #FFF;box-shadow:0 5px 15px rgba(0,147,233,0.4);}

/* Input Data (Form Membulat) */
.stTextInput input,.stNumberInput input,.stTextArea textarea,.stDateInput input, .stSelectbox div[data-baseweb="select"] {background:rgba(255,255,255,0.9)!important; border:3px solid #80D0C7!important;border-radius:18px!important;color:#0B2A4A!important;font-size:14px!important;font-family:'Nunito',sans-serif!important;font-weight:700!important;}
.stTextInput input:focus,.stNumberInput input:focus,.stTextArea textarea:focus{border-color:#0093E9!important;box-shadow:0 0 0 4px rgba(0,147,233,.3)!important;}
label{color:#FFF!important;font-size:12px!important;font-weight:800!important;text-transform:uppercase;letter-spacing:1px;font-family:'Fredoka',sans-serif!important; text-shadow: 0 2px 2px rgba(0,0,0,0.2);}

/* Progress Bar Kapal */
.stProgress>div>div{background:linear-gradient(90deg,#FFD700,#FF7F50)!important;border-radius:10px!important;}
.stProgress>div{background:rgba(255,255,255,0.5)!important;border-radius:10px!important;height:12px!important;}

/* Insight / Sonar Card & Budget Card (FADE IN UP) */
.insight-card{background:rgba(255,255,255,0.9); border:3px solid #FFF; border-radius:20px;padding:16px 18px;margin-bottom:10px;display:flex;align-items:flex-start;gap:15px;transition:all .3s; animation: bounceInUp 0.8s ease-out both;}
.insight-card:hover{transform:translateX(5px) scale(1.02); box-shadow:0 8px 20px rgba(0,92,151,0.2);}
.bgt-card{background:rgba(255,255,255,0.9); border:3px solid #FFF; border-radius:24px;padding:16px 18px;margin-bottom:12px;transition:all .3s; animation: bounceInUp 0.8s ease-out both;}
.bgt-card:hover{border-color:#0093E9;box-shadow:0 10px 25px rgba(0,92,151,0.2);transform:translateY(-5px);}
.bar-track{width:100%;background:rgba(0,147,233,0.1);border-radius:10px;height:10px;margin-top:10px;overflow:hidden;}
.bar-fill{height:100%;border-radius:10px;transition:width 1.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);}
::-webkit-scrollbar{width:8px;height:8px;} ::-webkit-scrollbar-track{background:transparent;} ::-webkit-scrollbar-thumb{background:#80D0C7;border-radius:10px;} ::-webkit-scrollbar-thumb:hover{background:#0093E9;}
</style>
""", unsafe_allow_html=True)

st.markdown(get_theme_vars(), unsafe_allow_html=True)

# ══════════════════════════════════════════
#  LOGIN FUN KARTUN (ENTER UNTUK MASUK)
# ══════════════════════════════════════════
if not st.session_state.authenticated:
    st.markdown("<style>[data-testid='collapsedControl']{display:none!important} section[data-testid='stSidebar']{display:none!important} .topbar{display:none!important;}</style>", unsafe_allow_html=True)
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.2, 1])
    
    with mid:
        st.markdown("""
        <div style='text-align:center;margin-bottom:30px; position:relative; z-index:10; animation: bounceInUp 0.8s cubic-bezier(0.68, -0.55, 0.265, 1.55) both;'>
            <div style='font-size:64px;font-weight:900;letter-spacing:-1px;font-family:"Fredoka",sans-serif;color:#FFF;text-shadow: 0 8px 15px rgba(0,92,151,0.5);'>
                <span style='font-size:72px;'>🐡</span> ROGER
            </div>
            <div style='font-size:14px;color:#FFD700;letter-spacing:4px;text-transform:uppercase;font-weight:800;margin-top:8px;text-shadow: 0 2px 5px rgba(0,0,0,0.2);'>Istana Pasir Keuangan</div>
        </div>
        """, unsafe_allow_html=True)
        
        pin_input = st.text_input("Kunci Gembok Harta (Ketik lalu tekan Enter)", type="password", placeholder="Masukan PIN & Enter ➔", key="pin_login_input")
        
        if pin_input:
            if pin_input == st.session_state.saved_pin:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Aww! Kuncinya patah. Coba masukkan PIN yang benar ya.")
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
if not db: st.error("❌ Gagal terhubung ke Database. Periksa setelan rahasia lautmu."); st.stop()

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
#  3. TOPBAR NATIVE (DENGAN PADDING KANAN)
# ══════════════════════════════════════════
st.markdown(f"""
<div class="topbar">
    <div class="topbar-stat"><span class="topbar-stat-label">Harta Karun</span><span class="topbar-stat-value">{_fmt_top(total_net)}</span></div>
    <div class="topbar-divider"></div>
    <div class="topbar-stat"><span class="topbar-stat-label">Koin Terkumpul</span><span class="topbar-stat-value" style="color:#0093E9;">{_fmt_top(total_cash)}</span></div>
    <div class="topbar-divider"></div>
    <div class="topbar-stat"><span class="topbar-stat-label">Ladang Rumput Laut</span><span class="topbar-stat-value" style="color:#11998e;">{_fmt_top(total_saham)}</span></div>
    <div class="topbar-right">
        <span class="topbar-date"><span class="live-dot"></span>{now.strftime("%H:%M")} | {now.strftime("%d %b %Y")}</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════
#  4. SIDEBAR NATIVE & PEMETAAN HALAMAN YANG BENAR
# ══════════════════════════════════════════
# INI ADALAH DAFTAR MENU YANG AKAN TAMPIL DI SIDEBAR
NAV_PAGES = [
    ("Istana Pasir",  "🏰"), 
    ("Catat Koin",    "💸"),
    ("Peti Saham",    "📈"), 
    ("Kerang Ajaib",  "🐚"),
    ("Radar Cuan",    "🔭"), 
    ("Screener",      "⚡"),
    ("Buku Log",      "📜"), 
    ("Setir Kapal",   "⚙️")
]

with st.sidebar:
    st.markdown('''
    <div style="text-align:center; padding: 15px 0 25px;">
        <div style="font-size: 32px; font-weight: 900; color: #0093E9; font-family: 'Fredoka', sans-serif;">
            <span style='font-size:38px;'>🐡</span> ROGER
        </div>
        <div style="font-size:10px;color:#FF7F50;letter-spacing:3px;margin-top:2px;font-weight:800;text-transform:uppercase;">Ocean Dashboard</div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Cari index menu yang sedang aktif
    cur_idx = next((i for i, (name, _) in enumerate(NAV_PAGES) if name == st.session_state.page), 0)
    
    # Menyatukan icon dan nama untuk st.radio
    radio_opts = [f"{icon} {name}" for name, icon in NAV_PAGES]
    selected_menu = st.radio("Navigasi Kelautan", radio_opts, index=cur_idx, label_visibility="collapsed")
    
    # Update state saat menu diklik
    for name, icon in NAV_PAGES:
        if f"{icon} {name}" == selected_menu:
            if st.session_state.page != name:
                st.session_state.page = name
                st.rerun()
            break
            
    st.markdown("<hr style='border: 2px dashed rgba(255,255,255,0.5); margin: 20px 0;'>", unsafe_allow_html=True)
    
    label_mata = "👁️ Tampilkan Harta" if st.session_state.hide_balance else "🙈 Sembunyikan Harta"
    if st.button(label_mata, use_container_width=True):
        st.session_state.hide_balance = not st.session_state.hide_balance
        st.rerun()
        
    if st.button("🌓 Sulap Layar", use_container_width=True):
        st.session_state.theme = "light" if st.session_state.get("theme", "dark") == "dark" else "dark"
        st.rerun()
        
    if st.button("🔒 Gembok Istana", use_container_width=True):
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
    if rasio_hemat >= 30: insights.append(("🎉","Luar Biasa!",f"Kamu berhasil mengubur <strong>{rasio_hemat:.1f}%</strong> koin bulan ini."))
    elif rasio_hemat < 0: insights.append(("🚨","Bocor Halus!",f"Awas! Koin keluar lebih banyak <strong>{fmt(abs(out_curr-in_curr))}</strong> dari yang masuk."))
    elif rasio_hemat < 10: insights.append(("⚠️","Mepet Banget",f"Sisa koinmu hanya <strong>{rasio_hemat:.1f}%</strong>. Hati-hati kelaparan di dasar laut."))
    if not out_df.empty:
        top_kat = out_df.groupby('Kategori')['Nominal'].sum().idxmax()
        top_val = out_df.groupby('Kategori')['Nominal'].sum().max()
        insights.append(("🍔","Raja Jajan",f"Koin terbanyak dihabiskan untuk: <strong>{top_kat}</strong> sebesar <strong>{fmt(top_val)}</strong>."))
    for kat, limit in budgets.items():
        spent = out_df[out_df['Kategori'] == kat.strip().title()]['Nominal'].sum()
        if limit > 0 and spent > limit: insights.append(("🔴","Jebol Terus",f"Jatah <strong>{kat}</strong> sudah meluap! Kelebihan <strong>{fmt(spent-limit)}</strong>."))
    inv = out_df[out_df['Kategori'] == 'Investasi']['Nominal'].sum(); inv_pct = inv / in_curr * 100
    if inv_pct < 10: insights.append(("🌱","Yuk Tanam Modal",f"Baru <strong>{inv_pct:.1f}%</strong> koin yang ditanam. Tambah lagi biar panen besar!"))
    elif inv_pct >= 20: insights.append(("👑","Juragan Laut",f"Mantap! Bibit investasi sudah <strong>{inv_pct:.1f}%</strong>. Masa depan cerah!"))
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
    st.markdown('<h2 style="font-size:26px;font-weight:900;color:#FFF;margin-bottom:0;font-family:\'Fredoka\',sans-serif;text-shadow:0 4px 8px rgba(0,0,0,0.2);animation: bounceInUp 0.5s ease-out both;">🏰 Selamat Datang di Istana Pasir!</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#FFF;font-size:14px;font-weight:700;margin-top:2px;animation: bounceInUp 0.6s ease-out both;">📅 {now.strftime("%A, %d %B %Y")}</p>', unsafe_allow_html=True)

    today_mask = (df_t['Tanggal'].dt.date == now.date()) if not df_t.empty else pd.Series(dtype=bool)
    df_today   = df_t[today_mask].copy() if not df_t.empty else pd.DataFrame()
    if not df_today.empty:
        df_today['Jenis'] = df_today['Jenis'].str.lower().str.strip(); df_today['Kategori'] = df_today['Kategori'].str.strip().str.title()
        df_today = df_today.sort_values('Tanggal', ascending=False)
    ti  = df_today[df_today['Jenis']=='pemasukan']['Nominal'].sum()   if not df_today.empty else 0.0
    to_ = df_today[df_today['Jenis']=='pengeluaran']['Nominal'].sum() if not df_today.empty else 0.0

    m1,m2,m3 = st.columns(3)
    m1.metric("⚓ TOTAL KEKAYAAN", fmt(total_net)); m2.metric("💵 KOIN DI TANGAN", fmt(total_cash)); m3.metric("📈 NILAI KEBUN SAHAM", fmt(total_saham))
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown('<div class="sec"><span class="sec-txt">Peti Penyimpanan</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
    wc = st.columns(4)
    for i,(key,name,icon,cls) in enumerate([("BCA","Bank BCA","🏦","wcard-bca"),("BRI","Bank BRI","🏢","wcard-bri"),("Bank Jago","Bank Jago","🦊","wcard-jago"),("Dompet (Cash)","Uang Tunai","💰","wcard-cash")]):
        with wc[i]: st.markdown(f'<div class="wcard {cls}"><div class="wcard-icon">{icon}</div><div class="wcard-lbl">{name}</div><div class="wcard-bal">{fmt(porto[key])}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True); col_left, col_right = st.columns([2,1])
    with col_left:
        st.markdown('<div class="sec"><span class="sec-txt">Mimpi Jadi Raja Bajak Laut (Target)</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        tgt = st.number_input("Target Harta (Rp)", value=int(st.session_state.target_harta), step=1000000, label_visibility="collapsed", format="%d")
        st.session_state.target_harta = tgt; save_config()
        rasio_t = max(0.0, min(total_net/tgt, 1.0)) if tgt > 0 else 0.0; pct_t = rasio_t * 100
        st.progress(rasio_t); st.markdown(f'<p style="font-size:13px;color:#FFF;font-weight:800;margin-top:8px;font-family:\'Nunito\',sans-serif;text-shadow: 0 2px 4px rgba(0,0,0,0.3);animation: bounceInUp 0.7s ease-out both;">🚀 Wow! Sudah {pct_t:.1f}% tercapai — {fmt(total_net)} dari {fmt(tgt)}</p>', unsafe_allow_html=True)
        
        st.markdown('<div class="sec"><span class="sec-txt">Ramalan Si Kerang Ajaib</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        b_proj = st.selectbox("Bulan Proyeksi:", NAMA_BULAN[1:], index=now.month-1, key="db_proj", label_visibility="collapsed")
        bln_p = NAMA_BULAN.index(b_proj); df_p2 = pd.DataFrame(); in_p2 = out_p2 = 0.0
        if not df_t.empty:
            dc2 = df_t.copy(); dc2['Jenis'] = dc2['Jenis'].str.lower().str.strip(); dc2['Kategori'] = dc2['Kategori'].str.strip().str.title()
            df_p2 = dc2[(dc2['Tanggal'].dt.month==bln_p)&(dc2['Tanggal'].dt.year==now.year)]
            in_p2 = df_p2[df_p2['Jenis']=='pemasukan']['Nominal'].sum(); out_p2 = df_p2[df_p2['Jenis']=='pengeluaran']['Nominal'].sum()
        proj_end, all_days, all_cum = project_monthend(df_p2, bln_p, now.year)
        c1p,c2p,c3p = st.columns(3); c1p.metric("Sudah Habis", fmt(out_p2)); c2p.metric("Bakal Habis", fmt(proj_end)); c3p.metric("Sisa Akhir", fmt(in_p2 - proj_end))

    with col_right:
        st.markdown('<div class="sec"><span class="sec-txt">Skor Kesejahteraan Bawah Laut</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
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
        gc_clr = "#0093E9" if score>=80 else "#FFD700" if score>=60 else "#FF7F50" if score>=40 else "#FF416C"
        rad = math.radians((score/100)*180); x_e = 80+60*math.cos(math.pi-rad); y_e = 80-60*math.sin(rad)
        st.markdown(f"""
        <div style="text-align:center; padding-bottom:5px; animation: bounceInUp 0.8s ease-out both;">
        <svg width="160" height="95" viewBox="0 0 160 95">
            <path d="M 20 80 A 60 60 0 0 1 140 80" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="16" stroke-linecap="round"/>
            <path d="M 20 80 A 60 60 0 0 1 {x_e:.1f} {y_e:.1f}" fill="none" stroke="{gc_clr}" stroke-width="16" stroke-linecap="round" style="filter: drop-shadow(0 4px 6px rgba(0,0,0,0.2));"/>
            <text x="80" y="70" text-anchor="middle" fill="#FFF" font-size="32" font-weight="900" font-family="Fredoka" style="text-shadow: 0 2px 4px rgba(0,0,0,0.3);">{score}</text>
            <text x="80" y="88" text-anchor="middle" fill="#FFF" font-size="12" font-family="Nunito" font-weight="800">POIN BINTANG</text>
          </svg></div>""", unsafe_allow_html=True)
        
        st.markdown('<div class="sec" style="margin-top:0;"><span class="sec-txt">Bisikan Rahasia Laut</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        for icon,title,txt in generate_insights(df_p2, in_p2, out_p2, st.session_state.budgets):
            st.markdown(f'<div class="insight-card"><div style="font-size:24px;">{icon}</div><div><strong style="color:#005C97;font-family:\'Fredoka\',sans-serif;font-size:14px;">{title}</strong><br><span style="color:#0B2A4A;font-size:12px;">{txt}</span></div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════
#  9. PAGE — KEUANGAN
# ══════════════════════════════════════════
def page_keuangan():
    if st.session_state.trigger_anim:
        anim_type = st.session_state.trigger_anim
        st.session_state.trigger_anim = None
        if anim_type == "Pemasukan": st.balloons()
        else: st.toast("💸 Ups! Koin meluncur keluar.")

    st.markdown('<h2 style="font-size:26px;font-weight:900;color:#FFF;font-family:\'Fredoka\',sans-serif;text-shadow:0 4px 8px rgba(0,0,0,0.2);animation: bounceInUp 0.5s ease-out both;">💸 Buku Catatan Koin</h2>', unsafe_allow_html=True)
    tab_trx, tab_bgt, tab_cmp = st.tabs(["📋 Tulis Transaksi","🚨 Penjaga Jatah","📅 Radar Cuan"])

    with tab_trx:
        c_form, c_list = st.columns([1, 1.8])
        with c_form:
            st.markdown('<div class="sec"><span class="sec-txt">➕ Tambah Koin</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
            with st.form("trx_v3", clear_on_submit=True):
                f_tgl = st.date_input("Kapan Terjadinya?", now.date())
                f_kat = st.selectbox("Buat Apaan Tuh?", st.session_state.kategori_list)
                f_jen = st.radio("Masuk Atau Keluar?", ["Pemasukan","Pengeluaran"], horizontal=True)
                f_src = st.selectbox("Dari Peti Mana?", list(porto.keys()))
                f_nom = st.text_input("Berapa Banyak (Rp)?", value=st.session_state.auto_nominal, placeholder="Contoh: 50000")
                f_note= st.text_area("Catatan Rahasia", placeholder="Biar nggak lupa...", height=64)
                
                if st.form_submit_button("🚀 SIMPAN KE BUKU", use_container_width=True):
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
            st.markdown('<div class="sec"><span class="sec-txt">🔍 Cari Jejak Transaksi</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
            sc1,sc2,sc3=st.columns([2,1,1])
            with sc1: q=st.text_input("Cari...",placeholder="Cari kata apa aja...",label_visibility="collapsed")
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
                st.markdown(f'<p style="font-size:12px;color:#FFF;margin-bottom:8px;font-weight:700;">Hore! Ketemu {len(df_f)} jejak koin.</p>', unsafe_allow_html=True)
                
                df_show=df_f[['Tanggal','Kategori','Jenis','Sumber Dana','Nominal','Catatan']].copy()
                df_show['Tanggal']=df_show['Tanggal'].apply(lambda x:pd.to_datetime(x).strftime('%Y-%m-%d') if pd.notna(x) else "")
                df_show['Nominal']=df_show['Nominal'].apply(fmt)
                df_show=df_show.reset_index(); df_show.rename(columns={'index':'No'},inplace=True)
                fmt_tbl(df_show)

    with tab_bgt:
        b2=st.selectbox("Bulan Jaga-jaga:",NAMA_BULAN[1:],index=now.month-1,key="bgt_b"); bln2=NAMA_BULAN.index(b2); df_bgt=pd.DataFrame()
        if not df_t.empty:
            db2=df_t.copy(); db2['Jenis']=db2['Jenis'].str.lower().str.strip(); db2['Kategori']=db2['Kategori'].str.strip().str.title()
            df_bgt=db2[(db2['Tanggal'].dt.month==bln2)&(db2['Tanggal'].dt.year==now.year)]
        spent_bgt=df_bgt[df_bgt['Jenis']=='pengeluaran'].groupby('Kategori')['Nominal'].sum().to_dict() if not df_bgt.empty else {}
        cols_bgt=st.columns(min(len(st.session_state.budgets),4))
        for i,(kat,lim) in enumerate(st.session_state.budgets.items()):
            terpakai=spent_bgt.get(str(kat).strip().title(),0.0); rasio_b=min(terpakai/lim,1.0) if lim>0 else 1.0; sisa=lim-terpakai
            bc=("#0093E9" if rasio_b<0.5 else "#FF7F50" if rasio_b<0.85 else "#FF416C"); ico=("🟢" if rasio_b<0.5 else "🟡" if rasio_b<0.85 else "🔴")
            with cols_bgt[i%4]: st.markdown(f'<div class="bgt-card"><div style="display:flex;justify-content:space-between;margin-bottom:8px;"><span style="font-size:12px;font-weight:800;color:#005C97;text-transform:uppercase;">{ico} {kat}</span><span style="font-size:14px;color:{bc};font-weight:900;">{rasio_b*100:.0f}%</span></div><div style="font-size:18px;font-weight:900;color:#0B2A4A;font-family:\'Fredoka\',sans-serif;">{fmt(terpakai)}</div><div class="bar-track"><div class="bar-fill" style="width:{rasio_b*100:.0f}%;background:{bc};"></div></div><div style="font-size:12px;margin-top:10px;color:{"#0093E9" if sisa>=0 else "#FF416C"};font-weight:800;">{"✅ Sisa Jatah: "+fmt(sisa) if sisa>=0 else "🔥 Defisit: "+fmt(abs(sisa))}</div><div style="font-size:10px;color:#888;font-weight:700;margin-top:4px;">Batas Maksimal: {fmt(lim)}</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════
#  10. HALAMAN "SEDANG DIBANGUN" (PLACEHOLDER)
# ══════════════════════════════════════════
# Fungsi ini dipanggil jika menu yang di-klik belum ada kodenya (seperti Portofolio dll)
def page_under_construction():
    st.markdown('<br><br>', unsafe_allow_html=True)
    _, col, _ = st.columns([1,2,1])
    with col:
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.9); border-radius:24px; padding:40px; text-align:center; border: 4px dashed #80D0C7; box-shadow: 0 10px 30px rgba(0,92,151,0.3); animation: bounceInUp 0.6s ease-out;">
            <div style="font-size:80px; margin-bottom:10px;">🚧🐡</div>
            <h2 style="color:#0093E9; font-family:'Fredoka',sans-serif; font-weight:900; font-size:32px;">Halaman {st.session_state.page}</h2>
            <p style="color:#0B2A4A; font-size:16px; font-weight:700;">Masih dalam tahap pembangunan oleh para kepiting dan kuda laut pekerja keras! Kembali lagi nanti ya.</p>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════
#  PEMETAAN HALAMAN (MENJODOHKAN MENU DAN FUNGSI)
# ══════════════════════════════════════════
# PASTI COCOK DENGAN NAMA DI NAV_PAGES
PAGE_MAP = {
    "Istana Pasir": page_dashboard,
    "Catat Koin":   page_keuangan
}

# Ambil fungsi berdasarkan halaman yang diklik. Jika belum ada di PAGE_MAP, jalankan page_under_construction
fn = PAGE_MAP.get(st.session_state.page, page_under_construction)
fn()
