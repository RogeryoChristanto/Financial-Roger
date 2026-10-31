import streamlit as st
import streamlit.components.v1 as components
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

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

try:
    from google import genai as genai_client
    from google.genai import types as genai_types
    GEMINI_OK = True
except ImportError:
    GEMINI_OK = False

# ══════════════════════════════════════════
#  1. PAGE CONFIG & SESSION STATE
# ══════════════════════════════════════════
st.set_page_config(
    page_title="ROGER Finance",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
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

def get_theme_vars():
    if st.session_state.get("theme", "dark") == "light":
        return """
        <style>
        html, body, .stApp, [data-testid="stAppViewContainer"] { background: #F1F5F9 !important; color: #0F172A !important; }
        .stApp::before { background: radial-gradient(ellipse, rgba(14,165,233,0.08) 0%, transparent 65%) !important; }
        .stApp::after  { background: radial-gradient(ellipse, rgba(99,102,241,0.06) 0%, transparent 65%) !important; }
        .topbar { background: rgba(248,250,252,0.94) !important; border-bottom: 1px solid rgba(14,165,233,0.15) !important; }
        .topbar-stat-label { color: #64748B !important; } .topbar-stat-value { color: #0F172A !important; } .topbar-date { color: #64748B !important; }
        div[data-testid="metric-container"] { background: linear-gradient(145deg,rgba(255,255,255,0.95),rgba(248,250,252,0.9)) !important; border: 1px solid rgba(0,0,0,0.08) !important; }
        [data-testid="stMetricValue"] { color: #0F172A !important; } [data-testid="stMetricLabel"] { color: #64748B !important; }
        .wcard-bca { background: linear-gradient(145deg,#1a3a6c,#0d1f3d,#060f22) !important; }
        .ctbl { color: #334155 !important; } .ctbl thead th { background: rgba(248,250,252,0.98) !important; color: #475569 !important; } .ctbl td { border-bottom-color: rgba(0,0,0,0.06) !important; }
        .tbl-wrap { background: rgba(255,255,255,0.97) !important; border: 1px solid rgba(0,0,0,0.08) !important; }
        .bgt-card { background: linear-gradient(135deg,rgba(255,255,255,0.92),rgba(248,250,252,0.88)) !important; border: 1px solid rgba(0,0,0,0.07) !important; }
        .insight-card { background: linear-gradient(135deg,rgba(14,165,233,0.06),rgba(99,102,241,0.04)) !important; border: 1px solid rgba(14,165,233,0.15) !important; }
        .insight-txt { color: #475569 !important; } .insight-txt strong { color: #0F172A !important; }
        .sk-card, .rec-card { background: linear-gradient(145deg,rgba(255,255,255,0.96),rgba(248,250,252,0.9)) !important; border: 1px solid rgba(0,0,0,0.07) !important; }
        [data-testid="stExpander"] { background: rgba(255,255,255,0.8) !important; border: 1px solid rgba(0,0,0,0.07) !important; }
        .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input, .stSelectbox div[data-baseweb="select"] { background: rgba(255,255,255,0.98) !important; border: 1px solid rgba(0,0,0,0.1) !important; color: #0F172A !important; }
        label { color: #475569 !important; }
        [data-testid="stTabs"] div[data-baseweb="tab-list"] { background: rgba(255,255,255,0.95) !important; border: 1px solid rgba(0,0,0,0.07) !important; }
        [data-testid="stTabs"] button[data-baseweb="tab"] { color: #64748B !important; } [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] { color: #0EA5E9 !important; background: rgba(14,165,233,0.07) !important; }
        .sec-txt { color: #64748B !important; }
        </style>"""
    return ""

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

*,*::before,*::after{box-sizing:border-box;}
header,footer{visibility:hidden!important;}
.stApp,[data-testid="stAppViewContainer"]{font-family:'DM Sans',sans-serif!important;background:#020712!important;color:#E2E8F0!important;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#060E1A 0%,#020712 100%)!important;border-right:1px solid rgba(56,189,248,0.06)!important;}

.stApp::before{content:'';position:fixed;top:-30%;left:-15%;width:70%;height:70%;
  background:radial-gradient(ellipse,rgba(56,189,248,0.055) 0%,rgba(56,189,248,0.015) 40%,transparent 65%);
  pointer-events:none;z-index:0;animation:aurora1 20s ease-in-out infinite alternate; filter:blur(40px);
  will-change: transform; transform: translateZ(0);}
.stApp::after{content:'';position:fixed;bottom:-30%;right:-15%;width:75%;height:75%;
  background:radial-gradient(ellipse,rgba(139,92,246,0.05) 0%,rgba(192,132,252,0.02) 40%,transparent 65%);
  pointer-events:none;z-index:0;animation:aurora2 26s ease-in-out infinite alternate; filter:blur(50px);
  will-change: transform; transform: translateZ(0);}

@keyframes aurora1{from{transform:translate3d(0,0,0) scale(1) rotate(0deg);}to{transform:translate3d(80px,60px,0) scale(1.2) rotate(5deg);}}
@keyframes aurora2{from{transform:translate3d(0,0,0) scale(1) rotate(0deg);}to{transform:translate3d(-70px,-50px,0) scale(1.25) rotate(-5deg);}}
@keyframes fadeUp{from{opacity:0;transform:translate3d(0,16px,0);}to{opacity:1;transform:translate3d(0,0,0);}}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1);}50%{opacity:0.4;transform:scale(1.6);}}
@keyframes shineCard{0%{left:-150%;}20%{left:150%;}100%{left:150%;}}

.stButton>button{background:linear-gradient(135deg,#0EA5E9 0%,#6366F1 100%)!important;color:#fff!important;font-weight:700!important;font-size:13px!important;border-radius:11px!important;border:none!important;padding:10px 20px!important;transition:transform .2s cubic-bezier(.4,0,.2,1), box-shadow .2s ease, filter .2s ease!important;will-change:transform;}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 8px 28px rgba(14,165,233,.4),0 0 0 3px rgba(14,165,233,0.08)!important;filter:brightness(1.12)!important;}

div[data-testid="metric-container"]{background:linear-gradient(145deg,rgba(7,11,22,0.95),rgba(5,9,18,0.9))!important;border:1px solid rgba(255,255,255,0.05)!important;border-radius:16px!important;padding:18px!important;box-shadow:0 4px 24px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,0.03)!important;transition:transform .3s cubic-bezier(.4,0,.2,1), border-color .3s ease!important;animation:fadeUp .5s ease both;position:relative!important;overflow:hidden!important;will-change:transform;}
div[data-testid="metric-container"]:hover{border-color:rgba(56,189,248,.18)!important;transform:translateY(-3px)!important;box-shadow:0 12px 36px rgba(0,0,0,.4),0 0 0 1px rgba(56,189,248,0.06)!important;}
[data-testid="stMetricValue"]{font-size:1.65rem!important;font-weight:800!important;color:#F1F5F9!important;letter-spacing:-.5px!important;font-family:'Syne',sans-serif!important;}
[data-testid="stMetricLabel"]{font-size:9.5px!important;font-weight:700!important;color:#2A4A6B!important;text-transform:uppercase!important;letter-spacing:1.5px!important;}

.wallet-row{display:flex;gap:14px;flex-wrap:nowrap;overflow-x:auto;padding-bottom:10px;scrollbar-width:none;}
.wallet-row::-webkit-scrollbar{display:none;}
.wcard{min-width:190px;flex:1;border-radius:20px;padding:22px 18px;position:relative;overflow:hidden;transition:transform .3s cubic-bezier(.4,0,.2,1)!important;animation:fadeUp .6s ease both;will-change:transform;}
.wcard::before{content:'';position:absolute;inset:0;background:url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23fff' fill-opacity='0.025'%3E%3Cpath d='M30 30.5V27H0v7.5h30v31h3V34.5h27V27H33V30.5h-3z'/%3E%3C/g%3E%3C/svg%3E");}
.wcard::after{content:'';position:absolute;top:0;left:-150%;width:50%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.4),transparent);transform:skewX(-25deg);animation:shineCard 4s cubic-bezier(0.4,0,0.2,1) infinite;pointer-events:none;}
.wcard:hover{transform:translateY(-5px) scale(1.01);}
.wcard-chip{position:absolute;top:14px;right:14px;width:28px;height:21px;border-radius:5px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.1);box-shadow:inset 0 1px 0 rgba(255,255,255,0.08);}
.wcard-icon{font-size:24px;margin-bottom:14px;filter:drop-shadow(0 2px 8px rgba(0,0,0,0.4));}
.wcard-lbl{font-size:9px;font-weight:700;color:rgba(255,255,255,.38);text-transform:uppercase;letter-spacing:2px;margin-bottom:5px;font-family:'DM Sans',sans-serif;}
.wcard-bal{font-size:19px;font-weight:800;color:#fff;letter-spacing:-.5px;font-family:'Syne',sans-serif;}
.wcard-bca{background:linear-gradient(145deg,#1a3a6c,#0d1f3d,#060f22);border:1px solid rgba(59,130,246,.25);box-shadow:0 8px 32px rgba(59,130,246,.12);}
.wcard-bri{background:linear-gradient(145deg,#7c2d12,#431a05,#220d02);border:1px solid rgba(249,115,22,.25);box-shadow:0 8px 32px rgba(249,115,22,.12);}
.wcard-jago{background:linear-gradient(145deg,#78350f,#3d2000,#1e1000);border:1px solid rgba(245,158,11,.25);box-shadow:0 8px 32px rgba(245,158,11,.12);}
.wcard-cash{background:linear-gradient(145deg,#064e3b,#022c22,#011410);border:1px solid rgba(16,185,129,.25);box-shadow:0 8px 32px rgba(16,185,129,.12);}

.sec{display:flex;align-items:center;gap:10px;margin:24px 0 14px;}
.sec-txt{font-size:9.5px;font-weight:800;color:#1E3A52;text-transform:uppercase;letter-spacing:2.5px;white-space:nowrap;font-family:'DM Sans',sans-serif;}
.sec-line{flex:1;height:1px;background:linear-gradient(90deg,rgba(56,189,248,0.12),rgba(139,92,246,0.06),transparent);}

.tbl-wrap{background:rgba(2,7,18,.97);border:1px solid rgba(255,255,255,0.04);border-radius:14px;overflow:auto;max-height:380px;box-shadow:0 8px 32px rgba(0,0,0,0.3);}
.ctbl{width:100%;border-collapse:collapse;color:#4A6080;font-size:12.5px;font-family:'DM Sans',sans-serif;}
.ctbl thead th{position:sticky;top:0;background:rgba(2,5,14,0.98);padding:11px 16px;font-weight:700;color:#1E3A52;text-transform:uppercase;letter-spacing:1.2px;font-size:9.5px;border-bottom:1px solid rgba(56,189,248,0.06);z-index:1;}
.ctbl td{padding:11px 16px;border-bottom:1px solid rgba(8,15,30,.8);}
.ctbl tbody tr:hover td{background:rgba(56,189,248,.028);color:#64748B;}
.ctbl tbody tr:last-of-type td{border-bottom:none;}

[data-testid="stTabs"] div[data-baseweb="tab-list"]{gap:2px;background:rgba(2,7,18,.95);border-radius:12px;padding:5px;border:1px solid rgba(255,255,255,0.04);}
[data-testid="stTabs"] button[data-baseweb="tab"]{background:transparent;border-radius:9px;padding:8px 16px;font-weight:600;font-size:12px;color:#1E3A52;border:none;font-family:'DM Sans',sans-serif;}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(135deg,rgba(14,165,233,.1),rgba(99,102,241,.1));color:#38BDF8;box-shadow:0 2px 12px rgba(0,0,0,.4);border:1px solid rgba(56,189,248,0.12);}

.stTextInput input,.stNumberInput input,.stTextArea textarea,.stDateInput input{background:rgba(3,7,18,.98)!important;border:1px solid rgba(255,255,255,0.06)!important;border-radius:11px!important;color:#C8D8E8!important;font-size:13px!important;transition:border-color .25s,box-shadow .25s!important;font-family:'DM Sans',sans-serif!important;}
.stTextInput input:focus,.stNumberInput input:focus,.stTextArea textarea:focus{border-color:rgba(56,189,248,0.4)!important;box-shadow:0 0 0 3px rgba(56,189,248,.07)!important;}
.stSelectbox div[data-baseweb="select"]{background:rgba(3,7,18,.98)!important;border:1px solid rgba(255,255,255,0.06)!important;border-radius:11px!important;}
label{color:#2A4A6B!important;font-size:10px!important;font-weight:700!important;text-transform:uppercase;letter-spacing:.7px;font-family:'DM Sans',sans-serif!important;}

.stProgress>div>div{background:linear-gradient(90deg,#38BDF8,#818CF8)!important;border-radius:10px!important;}
.stProgress>div{background:#080F1E!important;border-radius:10px!important;}
.insight-card{background:linear-gradient(135deg,rgba(56,189,248,.04),rgba(139,92,246,.03));border:1px solid rgba(56,189,248,.09);border-radius:13px;padding:13px 15px;margin-bottom:8px;display:flex;align-items:flex-start;gap:11px;transition:transform .25s ease;will-change:transform;}
.insight-card:hover{border-color:rgba(56,189,248,.16);transform:translateX(4px);}
.insight-icon{font-size:18px;flex-shrink:0;margin-top:1px;}
.insight-txt{font-size:12.5px;color:#4A6080;line-height:1.6;font-family:'DM Sans',sans-serif;}
.insight-txt strong{color:#8AA4C0;}

.bgt-card{background:linear-gradient(135deg,rgba(3,7,18,.9),rgba(5,10,22,.85));border:1px solid rgba(255,255,255,0.04);border-radius:12px;padding:12px 14px;margin-bottom:8px;transition:transform .2s ease;will-change:transform;}
.bgt-card:hover{border-color:rgba(56,189,248,0.1);transform:translateY(-2px);}
.bar-track{width:100%;background:rgba(2,5,14,0.8);border-radius:10px;height:5px;margin-top:8px;overflow:hidden;}
.bar-fill{height:100%;border-radius:10px;transition:width .9s cubic-bezier(.4,0,.2,1);position:relative;}

.live-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#10B981;animation:pulse 2s ease-in-out infinite;margin-right:6px;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:#0D1A2E;border-radius:10px;}
::-webkit-scrollbar-thumb:hover{background:#1A2E48;}
hr{border-color:rgba(255,255,255,0.04)!important;margin:16px 0!important;}
@media(max-width:768px){.wcard{min-width:80vw!important;} [data-testid="stTabs"] div[data-baseweb="tab-list"]{overflow-x:auto!important;scrollbar-width:none!important;} [data-testid="stTabs"] button[data-baseweb="tab"]{flex:0 0 auto!important;}}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════
#  FORM LOGIN PIN BARU (TIPE TEXT/PASSWORD)
# ══════════════════════════════════════════
if not st.session_state.authenticated:
    st.markdown("<style>[data-testid='collapsedControl']{display:none!important} section[data-testid='stSidebar']{display:none!important}</style>", unsafe_allow_html=True)
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.2, 1])
    
    with mid:
        st.markdown("""
        <div style='text-align:center;margin-bottom:20px;'>
            <div style='font-size:46px;font-weight:900;letter-spacing:-3px;background:linear-gradient(135deg,#38BDF8,#818CF8,#C084FC);-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>ROGER</div>
            <div style='font-size:10px;color:#64748B;letter-spacing:3px;text-transform:uppercase;font-weight:700;margin-top:4px;'>Personal Finance Dashboard</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("form_login"):
            pin_input = st.text_input("Masukan PIN Akses", type="password", placeholder="Ketik PIN Anda disini...")
            submit_btn = st.form_submit_button("Masuk ➔", use_container_width=True)
            
            if submit_btn:
                if pin_input == st.session_state.saved_pin:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ PIN Salah. Silakan coba lagi.")
    st.stop()

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

NAV = [
    ("Dashboard",   "🏠", "Ringkasan"), ("Keuangan",    "💳", "Transaksi"),
    ("Portofolio",  "📈", "Saham"), ("AI Advisor",  "🤖", "AI Chat"),
    ("Rekomendasi", "⭐", "Saham Murah"), ("Screener",    "⚡", "Screener"),
    ("Scanner",     "🧾", "Scan Nota"), ("Pengaturan",  "⚙️", "Settings"),
]

# PERBAIKAN: collapsedControl sekarang dibuat invisible, BUKAN display none, agar tetap bisa diklik JS
st.markdown("""<style>[data-testid="collapsedControl"] { opacity: 0 !important; position: absolute !important; left: -9999px !important; z-index: -1 !important; } [data-testid="stSidebarNav"], .stAppDeployButton, #MainMenu, header[data-testid="stHeader"], footer { display:none !important; } .block-container { padding-top: 0 !important; padding-bottom: 20px !important; max-width: 100% !important; } [data-testid="stAppViewContainer"] > section > div:first-child { padding-top: 0 !important; }</style>""", unsafe_allow_html=True)

now = pd.Timestamp.now('Asia/Jakarta')
svg_eye_open = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>'
svg_eye_closed = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92C21.42 15.57 22.78 13.89 23 12c-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z"/></svg>'
svg_lock = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg>'
svg_menu = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>'
svg_eye = svg_eye_closed if st.session_state.hide_balance else svg_eye_open
is_light = st.session_state.get("theme", "dark") == "light"
svg_theme = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0 .39-.39.39-1.03 0-1.41l-1.06-1.06zm1.06-12.37l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06c.39-.39.39-1.03 0-1.41s-1.03-.39-1.41 0zM7.05 18.36l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06c.39-.39.39-1.03 0-1.41s-1.03-.39-1.41 0z"/></svg>' if is_light else '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/></svg>'

st.markdown(get_theme_vars(), unsafe_allow_html=True)
def _fmt_top(v):
    if st.session_state.hide_balance: return "Rp ••••"
    if v >= 1_000_000_000: return f"Rp {v/1_000_000_000:.1f}M"
    if v >= 1_000_000:     return f"Rp {v/1_000_000:.1f}Jt"
    return f"Rp {v:,.0f}".replace(",",".")

side_html_list = []
for pg, icon, _ in NAV:
    if st.session_state.page == pg:
        side_html_list.append(f'<div class="sidetab-active"><span class="side-ico">{icon}</span><span class="side-txt">{pg}</span></div>')
    else:
        side_html_list.append(f'<div class="sidetab-item" data-page="{pg}"><span class="side-ico">{icon}</span><span class="side-txt">{pg}</span></div>')
side_html_str = "".join(side_html_list)

st.markdown(f"""
<style>
.topbar {{ position: sticky; top: 0; z-index: 999; background: rgba(2,7,18,0.94); backdrop-filter: blur(24px) saturate(200%); border-bottom: 1px solid rgba(56,189,248,0.08); padding: 0 20px; display: flex; align-items: center; gap: 0; height: 62px; box-shadow: 0 1px 0 rgba(56,189,248,0.04), 0 4px 40px rgba(0,0,0,0.6); }}
.topbar-divider {{ width: 1px; height: 28px; background: rgba(255,255,255,0.06); margin: 0 14px; flex-shrink: 0; }}
.topbar-stat {{ display: flex; flex-direction: column; flex-shrink: 0; }}
.topbar-stat-label {{ font-size: 8.5px; color: #1E3A52; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; font-family: 'DM Sans', sans-serif; }}
.topbar-stat-value {{ font-size: 13.5px; font-weight: 800; margin-top: 2px; letter-spacing: -0.5px; font-family: 'Syne', sans-serif; }}
.topbar-right {{ margin-left: auto; display: flex; align-items: center; gap: 6px; }}
.topbar-date {{ font-size: 11px; color: #1E3A52; font-weight: 600; margin-right: 8px; font-family: 'DM Sans', sans-serif; }}
.hdr-action {{ display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 8px; cursor: pointer; background: transparent; transition: all 0.2s ease; }}
.hdr-action:hover {{ background: rgba(255,255,255,0.06); }} .hdr-action svg {{ width: 20px; height: 20px; fill: #64748B; transition: fill 0.2s ease; }} .hdr-action:hover svg {{ fill: #E2E8F0; }}
</style>
<div class="topbar">
<div class="hdr-action" id="btn-menu" style="margin-right: 14px;" title="Buka/Tutup Sidebar">{svg_menu}</div>
<div class="topbar-stat"><span class="topbar-stat-label">Net Worth</span><span class="topbar-stat-value" style="color:#38BDF8;">{_fmt_top(total_net)}</span></div>
<div class="topbar-divider"></div>
<div class="topbar-stat"><span class="topbar-stat-label">Kas</span><span class="topbar-stat-value" style="color:#34D399;">{_fmt_top(total_cash)}</span></div>
<div class="topbar-divider"></div>
<div class="topbar-stat"><span class="topbar-stat-label">Saham</span><span class="topbar-stat-value" style="color:#818CF8;">{_fmt_top(total_saham)}</span></div>
<div class="topbar-right"><span class="topbar-date"><span class="live-dot"></span>{now.strftime("%H:%M")} · {now.strftime("%d %b %Y")}</span><div class="topbar-divider" style="margin: 0 4px; height: 20px;"></div>
<div class="hdr-action" id="btn-theme" title="Ubah Tema">{svg_theme}</div><div class="hdr-action" id="btn-eye" title="Sembunyikan Saldo">{svg_eye}</div><div class="hdr-action" id="btn-lock" title="Kunci Aplikasi">{svg_lock}</div></div></div>
""", unsafe_allow_html=True)

# PERBAIKAN: JS Listener untuk Hamburger Menu (#btn-menu)
components.html("""
<script>
const parentDoc = window.parent.document;
if (!parentDoc.getElementById('roger-js-injected')) {
    const scriptFlag = parentDoc.createElement('div');
    scriptFlag.id = 'roger-js-injected';
    scriptFlag.style.display = 'none';
    parentDoc.body.appendChild(scriptFlag);

    parentDoc.addEventListener('click', function(event) {
        
        // 1. Toggle Navigasi Sidebar (Hamburger Menu)
        if (event.target.closest('#btn-menu')) {
            const expandWrapper = parentDoc.querySelector('[data-testid="collapsedControl"]');
            const sidebar = parentDoc.querySelector('[data-testid="stSidebar"]');
            
            let isSidebarOpen = false;
            if (sidebar) {
                const rect = sidebar.getBoundingClientRect();
                if (rect.left >= 0 && rect.width > 0) { isSidebarOpen = true; }
            }
            
            if (isSidebarOpen && sidebar) {
                // Cari tombol close (silang) asli Streamlit yg biasanya tdk ada teksnya
                const closeBtn = Array.from(sidebar.querySelectorAll('button')).find(b => b.textContent.trim() === '');
                if (closeBtn) closeBtn.click();
            } else if (expandWrapper) {
                // Cari tombol open asli
                const openBtn = expandWrapper.querySelector('button') || expandWrapper;
                openBtn.click();
            }
        }
        
        // 2. Pindah Halaman Menu di dalam Sidebar
        const sideItem = event.target.closest('.sidetab-item');
        if (sideItem) { const page = sideItem.getAttribute('data-page'); if (page) { clickHiddenButton('TRIG_' + page); } }
        
        // 3. Tombol Atas Lainnya
        if (event.target.closest('#btn-eye')) { clickHiddenButton('TRIG_EYE'); }
        if (event.target.closest('#btn-lock')) { clickHiddenButton('TRIG_LOCK'); }
        if (event.target.closest('#btn-theme')) { clickHiddenButton('TRIG_THEME'); }
    });

    function clickHiddenButton(triggerName) {
        const buttons = parentDoc.querySelectorAll('button');
        for (let i = 0; i < buttons.length; i++) {
            if (buttons[i].textContent.includes(triggerName)) { buttons[i].click(); break; }
        }
    }
}
</script>
""", height=0, width=0)

with st.sidebar:
    st.markdown(f'''
    <style>
    .side-logo-wrap {{ text-align:center; padding: 10px 0 30px; border-bottom: 1px solid rgba(255,255,255,0.05); margin-bottom: 20px; }}
    .side-logo {{ font-size: 26px; font-weight: 900; letter-spacing: -1px; font-family: 'Syne', sans-serif; background: linear-gradient(135deg, #38BDF8 0%, #818CF8 55%, #C084FC 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; filter: drop-shadow(0 0 10px rgba(56,189,248,0.2)); }}
    .sidetab-wrap {{ display: flex; flex-direction: column; gap: 8px; padding: 0 10px; }}
    .sidetab-item {{ display: flex; align-items: center; gap: 14px; padding: 12px 18px; border-radius: 12px; color: #64748B; font-weight: 600; font-size: 14px; cursor: pointer; transition: all 0.25s ease; font-family: 'DM Sans', sans-serif; border: 1px solid transparent; }}
    .sidetab-item:hover {{ background: rgba(56,189,248,0.04); color: #E2E8F0; border-color: rgba(56,189,248,0.1); transform: translateX(4px); }}
    .sidetab-active {{ display: flex; align-items: center; gap: 14px; padding: 12px 18px; border-radius: 12px; background: linear-gradient(135deg, rgba(56,189,248,0.12), rgba(99,102,241,0.12)); color: #38BDF8; font-weight: 700; font-size: 14px; border: 1px solid rgba(56,189,248,0.25); box-shadow: 0 4px 15px rgba(0,0,0,0.2); font-family: 'DM Sans', sans-serif; position: relative; }}
    .sidetab-active::before {{ content: ''; position: absolute; left: -6px; top: 20%; height: 60%; width: 4px; background: #38BDF8; border-radius: 4px; box-shadow: 0 0 10px #38BDF8; }}
    .side-ico {{ font-size: 18px; width: 24px; text-align: center; }}
    </style>
    <div class="side-logo-wrap"><div class="side-logo">💎 ROGER</div><div style="font-size:10px;color:#64748B;letter-spacing:2px;margin-top:4px;font-weight:700;">FINANCE DASHBOARD</div></div>
    <div class="sidetab-wrap">{side_html_str}</div>
    ''', unsafe_allow_html=True)
    
    st.markdown("<style>div[data-testid='stSidebar'] .stButton { display: none !important; }</style>", unsafe_allow_html=True)
    for _pg, _icon, _desc in NAV:
        if st.button(f"TRIG_{_pg}", key=f"sidenav_{_pg}"): st.session_state.page = _pg; st.rerun()
    if st.button("TRIG_EYE", key="sbtn_eye"): st.session_state.hide_balance = not st.session_state.hide_balance; st.rerun()
    if st.button("TRIG_LOCK", key="sbtn_lock"): st.session_state.authenticated = False; st.rerun()
    if st.button("TRIG_THEME", key="sbtn_theme"): st.session_state.theme = "light" if st.session_state.get("theme", "dark") == "dark" else "dark"; st.rerun()

def generate_insights(df_curr, in_curr, out_curr, budgets):
    insights = []
    if df_curr.empty or in_curr == 0: return insights
    df = df_curr.copy(); df['Jenis'] = df['Jenis'].str.lower().str.strip(); df['Kategori'] = df['Kategori'].str.strip().str.title()
    out_df = df[df['Jenis'] == 'pengeluaran']; rasio_hemat = (in_curr - out_curr) / in_curr * 100
    if rasio_hemat >= 30: insights.append(("🎉","Tabungan",f"Berhasil menabung <strong>{rasio_hemat:.1f}%</strong> dari pemasukan bulan ini."))
    elif rasio_hemat < 0: insights.append(("🚨","Defisit",f"Pengeluaran melebihi pemasukan <strong>{fmt(abs(out_curr-in_curr))}</strong>."))
    elif rasio_hemat < 10: insights.append(("⚠️","Hemat",f"Rasio tabungan hanya <strong>{rasio_hemat:.1f}%</strong>."))
    if not out_df.empty:
        top_kat = out_df.groupby('Kategori')['Nominal'].sum().idxmax()
        top_val = out_df.groupby('Kategori')['Nominal'].sum().max()
        insights.append(("📊","Top Spend",f"Pengeluaran terbesar: <strong>{top_kat}</strong> sebesar <strong>{fmt(top_val)}</strong>."))
    for kat, limit in budgets.items():
        spent = out_df[out_df['Kategori'] == kat.strip().title()]['Nominal'].sum()
        if limit > 0 and spent > limit: insights.append(("🔴","Budget Jebol",f"Budget <strong>{kat}</strong> jebol <strong>{fmt(spent-limit)}</strong> di atas limit."))
    inv = out_df[out_df['Kategori'] == 'Investasi']['Nominal'].sum(); inv_pct = inv / in_curr * 100
    if inv_pct < 10: insights.append(("💡","Investasi",f"Porsi investasi <strong>{inv_pct:.1f}%</strong>. Coba tingkatkan ke 20%."))
    elif inv_pct >= 20: insights.append(("🌱","Investasi",f"Porsi investasi <strong>{inv_pct:.1f}%</strong> — sudah sangat baik!"))
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
    st.markdown('<h2 style="font-size:21px;font-weight:900;color:#F1F5F9;margin-bottom:0;">🏠 Dashboard</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#1E293B;font-size:12px;margin-top:2px;">{now.strftime("%A, %d %B %Y · %H:%M")} WIB</p>', unsafe_allow_html=True)

    today_mask = (df_t['Tanggal'].dt.date == now.date()) if not df_t.empty else pd.Series(dtype=bool)
    df_today   = df_t[today_mask].copy() if not df_t.empty else pd.DataFrame()
    if not df_today.empty:
        df_today['Jenis'] = df_today['Jenis'].str.lower().str.strip(); df_today['Kategori'] = df_today['Kategori'].str.strip().str.title()
        df_today = df_today.sort_values('Tanggal', ascending=False)
    ti  = df_today[df_today['Jenis']=='pemasukan']['Nominal'].sum()   if not df_today.empty else 0.0
    to_ = df_today[df_today['Jenis']=='pengeluaran']['Nominal'].sum() if not df_today.empty else 0.0
    nd  = ti - to_; nc = "#34D399" if nd >= 0 else "#F87171"

    m1,m2,m3 = st.columns(3)
    m1.metric("🌟 Net Worth", fmt(total_net)); m2.metric("💵 Uang Tunai", fmt(total_cash)); m3.metric("📈 Nilai Saham", fmt(total_saham))
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec"><span class="sec-txt">💳 Dompet & Rekening</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
    wc = st.columns(4)
    for i,(key,name,icon,cls) in enumerate([("BCA","Bank BCA","🏦","wcard-bca"),("BRI","Bank BRI","🏢","wcard-bri"),("Bank Jago","Bank Jago","🦊","wcard-jago"),("Dompet (Cash)","Uang Tunai","💵","wcard-cash")]):
        with wc[i]: st.markdown(f'<div class="wcard {cls}"><div class="wcard-chip"></div><div class="wcard-icon">{icon}</div><div class="wcard-lbl">{name}</div><div class="wcard-bal">{fmt(porto[key])}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True); col_left, col_right = st.columns([2,1])
    with col_left:
        st.markdown('<div class="sec"><span class="sec-txt">🎯 Target Finansial</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        tgt = st.number_input("Target Harta Bersih (Rp)", value=int(st.session_state.target_harta), step=1000000, label_visibility="collapsed", format="%d")
        st.session_state.target_harta = tgt; save_config()
        rasio_t = max(0.0, min(total_net/tgt, 1.0)) if tgt > 0 else 0.0; pct_t = rasio_t * 100
        pc = "#34D399" if pct_t>=80 else "#38BDF8" if pct_t>=50 else "#FBBF24" if pct_t>=25 else "#F87171"
        st.progress(rasio_t); st.markdown(f'<p style="font-size:12px;color:{pc};font-weight:700;margin-top:4px;">✅ {pct_t:.1f}% tercapai — {fmt(total_net)} dari {fmt(tgt)}</p>', unsafe_allow_html=True)
        
        st.markdown('<div class="sec"><span class="sec-txt">🔮 Proyeksi Akhir Bulan</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        b_proj = st.selectbox("Bulan Proyeksi:", NAMA_BULAN[1:], index=now.month-1, key="db_proj", label_visibility="collapsed")
        bln_p = NAMA_BULAN.index(b_proj); df_p2 = pd.DataFrame(); in_p2 = out_p2 = 0.0
        if not df_t.empty:
            dc2 = df_t.copy(); dc2['Jenis'] = dc2['Jenis'].str.lower().str.strip(); dc2['Kategori'] = dc2['Kategori'].str.strip().str.title()
            df_p2 = dc2[(dc2['Tanggal'].dt.month==bln_p)&(dc2['Tanggal'].dt.year==now.year)]
            in_p2 = df_p2[df_p2['Jenis']=='pemasukan']['Nominal'].sum(); out_p2 = df_p2[df_p2['Jenis']=='pengeluaran']['Nominal'].sum()
        proj_end, all_days, all_cum = project_monthend(df_p2, bln_p, now.year)
        c1p,c2p,c3p = st.columns(3); c1p.metric("Pengeluaran s/d Kini", fmt(out_p2)); c2p.metric("Proyeksi Akhir Bulan", fmt(proj_end)); c3p.metric("Estimasi Sisa", fmt(in_p2 - proj_end))

    with col_right:
        st.markdown('<div class="sec"><span class="sec-txt">💪 Health Score</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
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
        gc_clr = "#34D399" if score>=80 else "#38BDF8" if score>=60 else "#FBBF24" if score>=40 else "#EF4444"
        grade,gcls,gem = ("Excellent","grade-ex","🌟") if score>=80 else ("Good","grade-gd","👍") if score>=60 else ("Fair","grade-fa","⚠️") if score>=40 else ("Poor","grade-po","🚨")
        rad = math.radians((score/100)*180); x_e = 80+60*math.cos(math.pi-rad); y_e = 80-60*math.sin(rad)
        st.markdown(f"""
        <div class="gauge-wrap"><svg width="160" height="95" viewBox="0 0 160 95">
            <path d="M 20 80 A 60 60 0 0 1 140 80" fill="none" stroke="#080F1E" stroke-width="12" stroke-linecap="round"/>
            <path d="M 20 80 A 60 60 0 0 1 {x_e:.1f} {y_e:.1f}" fill="none" stroke="{gc_clr}" stroke-width="12" stroke-linecap="round"/>
            <text x="80" y="70" text-anchor="middle" fill="{gc_clr}" font-size="26" font-weight="900" font-family="Inter">{score}</text><text x="80" y="83" text-anchor="middle" fill="#1E293B" font-size="9" font-family="Inter">/ 100</text>
          </svg><span class="grade-badge {gcls}">{gem} {grade}</span></div>""", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec"><span class="sec-txt">💡 Smart Insights</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        for icon,title,txt in generate_insights(df_p2, in_p2, out_p2, st.session_state.budgets):
            st.markdown(f'<div class="insight-card"><div class="insight-icon">{icon}</div><div class="insight-txt"><strong>{title}</strong> — {txt}</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════
#  9. PAGE — KEUANGAN
# ══════════════════════════════════════════
def page_keuangan():
    if st.session_state.trigger_anim:
        anim_type = st.session_state.trigger_anim
        st.session_state.trigger_anim = None
        if anim_type == "Pemasukan":
            components.html("""
            <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
            <script>
            var duration = 2.5 * 1000;
            var end = Date.now() + duration;
            (function frame() {
              confetti({ particleCount: 5, angle: 60, spread: 55, origin: { x: 0 }, colors: ['#10B981', '#34D399', '#FBBF24'] });
              confetti({ particleCount: 5, angle: 120, spread: 55, origin: { x: 1 }, colors: ['#10B981', '#34D399', '#FBBF24'] });
              if (Date.now() < end) requestAnimationFrame(frame);
            }());
            </script>""", height=0)
        else:
            components.html("""
            <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
            <script>
            confetti({ particleCount: 80, spread: 100, origin: { y: 0.6 }, colors: ['#EF4444', '#F87171', '#64748B'] });
            </script>""", height=0)

    st.markdown('<h2 style="font-size:21px;font-weight:900;color:#F1F5F9;">💳 Keuangan</h2>', unsafe_allow_html=True)
    tab_trx, tab_bgt, tab_cmp = st.tabs(["📋 Transaksi","🚨 Budget Monitor","📅 Perbandingan"])

    with tab_trx:
        c_form, c_list = st.columns([1, 1.8])
        with c_form:
            st.markdown('<div class="sec"><span class="sec-txt">➕ Tambah Transaksi</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
            with st.form("trx_v3", clear_on_submit=True):
                f_tgl = st.date_input("Tanggal", now.date())
                f_kat = st.selectbox("Kategori", st.session_state.kategori_list)
                f_jen = st.radio("Jenis", ["Pemasukan","Pengeluaran"], horizontal=True)
                f_src = st.selectbox("Sumber Dana", list(porto.keys()))
                f_nom = st.text_input("Jumlah (Rp)", value=st.session_state.auto_nominal, placeholder="Contoh: 50.000")
                f_note= st.text_area("Catatan", placeholder="Rincian...", height=64)
                
                if st.form_submit_button("💾  SIMPAN TRANSAKSI", use_container_width=True):
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
            st.markdown('<div class="sec"><span class="sec-txt">🔍 Riwayat & Filter</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
            sc1,sc2,sc3=st.columns([2,1,1])
            with sc1: q=st.text_input("Cari...",placeholder="Kategori, catatan...",label_visibility="collapsed")
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
                st.markdown(f'<p style="font-size:10.5px;color:#1E293B;margin-bottom:5px;">{len(df_f)} transaksi ditemukan.</p>', unsafe_allow_html=True)
                
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
            bc=("#34D399" if rasio_b<0.5 else "#FBBF24" if rasio_b<0.85 else "#F87171"); ico=("🟢" if rasio_b<0.5 else "🟡" if rasio_b<0.85 else "🔴")
            with cols_bgt[i%4]: st.markdown(f'<div class="bgt-card"><div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="font-size:11px;font-weight:700;color:#475569;">{ico} {kat}</span><span style="font-size:11px;color:{bc};font-weight:800;">{rasio_b*100:.0f}%</span></div><div style="font-size:13px;font-weight:800;color:#F1F5F9;">{fmt(terpakai)}</div><div class="bar-track"><div class="bar-fill" style="width:{rasio_b*100:.0f}%;background:{bc};"></div></div><div style="font-size:11px;margin-top:5px;color:{"#34D399" if sisa>=0 else "#F87171"};font-weight:600;">{"Sisa: "+fmt(sisa) if sisa>=0 else "⚠️ Over: "+fmt(abs(sisa))}</div><div style="font-size:9.5px;color:#0F172A;">Limit: {fmt(lim)}</div></div>', unsafe_allow_html=True)

PAGE_MAP = {
    "Dashboard":    page_dashboard,
    "Keuangan":     page_keuangan
}
fn = PAGE_MAP.get(st.session_state.page, page_dashboard)
fn()
