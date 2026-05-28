import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
import pytesseract
from PIL import Image
from datetime import timedelta
import json, os, gspread, re, math, numpy as np, calendar
from sklearn.linear_model import LinearRegression
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

try:
    import anthropic
    ANTHROPIC_OK = True
except ImportError:
    ANTHROPIC_OK = False

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
    "hide_balance": False, "pin_input": "", "authenticated": False,
    "page": "Dashboard", "chat_messages": [], "scan_status": None,
    "auto_nominal": "", "daily_recs_cache": None, "daily_recs_date": None,
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
        "target_harta": 100000000,
    }

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump({"budgets": st.session_state.budgets,
                   "kategori_list": st.session_state.kategori_list,
                   "saved_pin": st.session_state.saved_pin,
                   "target_harta": st.session_state.get("target_harta", 100000000)}, f)

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
#  2. CSS — OBSIDIAN AURORA v3
# ══════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');

*,*::before,*::after{box-sizing:border-box;}
header,footer{visibility:hidden!important;}
.stApp,[data-testid="stAppViewContainer"]{font-family:'Inter',sans-serif!important;background:#04080F!important;color:#E2E8F0!important;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#07111E 0%,#04080F 100%)!important;border-right:1px solid rgba(56,189,248,0.07)!important;}
[data-testid="stSidebarUserContent"]{padding:0 10px!important;}

.stApp::before{content:'';position:fixed;top:-250px;left:-150px;width:700px;height:700px;background:radial-gradient(ellipse,rgba(56,189,248,0.04) 0%,transparent 65%);pointer-events:none;z-index:0;animation:drift1 22s ease-in-out infinite alternate;}
.stApp::after{content:'';position:fixed;bottom:-250px;right:-150px;width:800px;height:800px;background:radial-gradient(ellipse,rgba(139,92,246,0.04) 0%,transparent 65%);pointer-events:none;z-index:0;animation:drift2 28s ease-in-out infinite alternate;}
@keyframes drift1{from{transform:translate(0,0) scale(1);}to{transform:translate(60px,40px) scale(1.1);}}
@keyframes drift2{from{transform:translate(0,0) scale(1);}to{transform:translate(-50px,-30px) scale(1.15);}}
@keyframes fadeUp{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1);}50%{opacity:0.6;transform:scale(1.4);}}

.sidebar-logo{padding:20px 14px 14px;border-bottom:1px solid rgba(255,255,255,0.04);margin-bottom:8px;}
.logo-text{font-size:24px;font-weight:900;letter-spacing:-1.5px;background:linear-gradient(135deg,#38BDF8,#818CF8,#C084FC);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.logo-sub{font-size:9px;color:#1E293B;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;margin-top:2px;}

.stButton>button{background:linear-gradient(135deg,#0EA5E9,#6366F1)!important;color:#fff!important;font-weight:700!important;font-size:13px!important;border-radius:11px!important;border:none!important;padding:10px 20px!important;transition:all .25s cubic-bezier(.4,0,.2,1)!important;box-shadow:0 4px 14px rgba(14,165,233,.2)!important;letter-spacing:.2px!important;}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 8px 24px rgba(14,165,233,.3)!important;filter:brightness(1.1)!important;}
.stButton>button:active{transform:translateY(0)!important;}

/* ── Sidebar Radio Nav ── */
div[data-testid="stSidebar"] div[data-testid="stRadio"] label {
    display: flex !important;
    align-items: center !important;
    padding: 9px 12px !important;
    border-radius: 10px !important;
    margin-bottom: 2px !important;
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #475569 !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    transition: all 0.18s ease !important;
    cursor: pointer !important;
}
div[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
    background: rgba(30,41,59,.5) !important;
    color: #94A3B8 !important;
    border-color: rgba(255,255,255,.05) !important;
}
div[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) {
    background: linear-gradient(135deg,rgba(56,189,248,.1),rgba(139,92,246,.1)) !important;
    color: #38BDF8 !important;
    border: 1px solid rgba(56,189,248,.22) !important;
    box-shadow: 0 0 14px rgba(56,189,248,.05) !important;
}
div[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) p {
    color: #38BDF8 !important;
    font-weight: 700 !important;
}
div[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-child {
    display: none !important;
}
div[data-testid="stSidebar"] div[data-testid="stRadio"] > div {
    gap: 0 !important;
}

/* ── Sidebar Buttons (lock/eye) ── */
div[data-testid="stSidebar"] .stButton>button{
    background:rgba(7,11,22,.8)!important;
    color:#475569!important;
    font-size:12px!important;
    font-weight:600!important;
    border:1px solid #0A1020!important;
    border-radius:9px!important;
    padding:8px 12px!important;
    box-shadow:none!important;
    letter-spacing:0!important;
}
div[data-testid="stSidebar"] .stButton>button:hover{
    background:rgba(30,41,59,.8)!important;
    color:#94A3B8!important;
    transform:none!important;
    box-shadow:none!important;
    filter:none!important;
    border-color:#1E293B!important;
}

div[data-testid="metric-container"]{background:rgba(7,11,22,0.85)!important;border:1px solid rgba(255,255,255,0.05)!important;border-radius:16px!important;padding:18px!important;box-shadow:0 4px 18px rgba(0,0,0,.25)!important;transition:all .25s ease!important;animation:fadeUp .4s ease both;}
div[data-testid="metric-container"]:hover{border-color:rgba(56,189,248,.15)!important;transform:translateY(-2px)!important;}
[data-testid="stMetricValue"]{font-size:1.65rem!important;font-weight:900!important;color:#F1F5F9!important;letter-spacing:-.5px!important;}
[data-testid="stMetricLabel"]{font-size:10px!important;font-weight:700!important;color:#334155!important;text-transform:uppercase!important;letter-spacing:1.2px!important;}

.wallet-row{display:flex;gap:12px;flex-wrap:nowrap;overflow-x:auto;padding-bottom:8px;scrollbar-width:none;}
.wallet-row::-webkit-scrollbar{display:none;}
.wcard{min-width:185px;flex:1;border-radius:18px;padding:20px 16px;position:relative;overflow:hidden;transition:all .3s cubic-bezier(.4,0,.2,1);animation:fadeUp .5s ease both;}
.wcard::before{content:'';position:absolute;inset:0;background:url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23fff' fill-opacity='0.04'%3E%3Cpath d='M20 20.5V18H0v5h20v20.5h2V23h20v-5H22V20.5h-2z'/%3E%3C/g%3E%3C/svg%3E");}
.wcard:hover{transform:translateY(-5px) scale(1.015);}
.wcard-chip{position:absolute;top:12px;right:12px;width:26px;height:20px;border-radius:4px;background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.11);}
.wcard-icon{font-size:22px;margin-bottom:12px;}
.wcard-lbl{font-size:9px;font-weight:700;color:rgba(255,255,255,.4);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:4px;}
.wcard-bal{font-size:18px;font-weight:900;color:#fff;letter-spacing:-.5px;}
.wcard-bca{background:linear-gradient(145deg,#1a3a6c,#0d1f3d);border:1px solid rgba(59,130,246,.22);box-shadow:0 6px 28px rgba(59,130,246,.1);}
.wcard-bri{background:linear-gradient(145deg,#7c2d12,#431a05);border:1px solid rgba(249,115,22,.22);box-shadow:0 6px 28px rgba(249,115,22,.1);}
.wcard-jago{background:linear-gradient(145deg,#78350f,#3d2000);border:1px solid rgba(245,158,11,.22);box-shadow:0 6px 28px rgba(245,158,11,.1);}
.wcard-cash{background:linear-gradient(145deg,#064e3b,#022c22);border:1px solid rgba(16,185,129,.22);box-shadow:0 6px 28px rgba(16,185,129,.1);}

.sec{display:flex;align-items:center;gap:10px;margin:20px 0 12px;}
.sec-txt{font-size:10px;font-weight:800;color:#334155;text-transform:uppercase;letter-spacing:2px;white-space:nowrap;}
.sec-line{flex:1;height:1px;background:linear-gradient(90deg,rgba(255,255,255,.05),transparent);}

.banner{background:linear-gradient(135deg,rgba(14,165,233,.06),rgba(139,92,246,.06));border:1px solid rgba(56,189,248,.09);border-radius:14px;padding:14px 18px;display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-bottom:14px;animation:fadeUp .4s ease;}
.bitem{display:flex;flex-direction:column;}
.blbl{font-size:9px;color:#1E293B;font-weight:800;text-transform:uppercase;letter-spacing:1.2px;}
.bval{font-size:17px;font-weight:900;margin-top:2px;}
.divider-v{width:1px;background:#0F172A;height:34px;flex-shrink:0;}

.tbl-wrap{background:rgba(4,8,15,.95);border:1px solid #0A1020;border-radius:12px;overflow:auto;max-height:380px;}
.tbl-wrap::-webkit-scrollbar{width:4px;height:4px;}
.tbl-wrap::-webkit-scrollbar-thumb{background:#0F172A;border-radius:10px;}
.ctbl{width:100%;border-collapse:collapse;color:#64748B;font-size:12.5px;}
.ctbl thead th{position:sticky;top:0;background:#020508;padding:10px 14px;font-weight:700;color:#1E293B;text-transform:uppercase;letter-spacing:1px;font-size:10px;border-bottom:1px solid #0A1020;z-index:1;}
.ctbl td{padding:10px 14px;border-bottom:1px solid rgba(10,16,32,.8);}
.ctbl tbody tr:hover td{background:rgba(56,189,248,.025);}
.ctbl tbody tr:last-of-type td{border-bottom:none;}

[data-testid="stTabs"] div[data-baseweb="tab-list"]{gap:2px;background:rgba(4,8,15,.9);border-radius:11px;padding:4px;border:1px solid #0A1020;}
[data-testid="stTabs"] button[data-baseweb="tab"]{background:transparent;border-radius:8px;padding:8px 14px;font-weight:600;font-size:12px;color:#1E293B;border:none;transition:all .2s;}
[data-testid="stTabs"] button[data-baseweb="tab"]:hover{color:#475569;}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"]{background:rgba(20,30,50,.95);color:#38BDF8;box-shadow:0 2px 8px rgba(0,0,0,.35);}
[data-testid="stTabs"] div[data-baseweb="tab-highlight"]{display:none;}

.stTextInput input,.stNumberInput input,.stTextArea textarea,.stDateInput input{background:rgba(4,8,15,.95)!important;border:1px solid #0A1020!important;border-radius:10px!important;color:#E2E8F0!important;font-size:13px!important;transition:border-color .2s,box-shadow .2s!important;}
.stTextInput input:focus,.stNumberInput input:focus,.stTextArea textarea:focus{border-color:#38BDF8!important;box-shadow:0 0 0 3px rgba(56,189,248,.08)!important;}
.stSelectbox div[data-baseweb="select"]{background:rgba(4,8,15,.95)!important;border:1px solid #0A1020!important;border-radius:10px!important;}
label{color:#334155!important;font-size:10px!important;font-weight:700!important;text-transform:uppercase;letter-spacing:.5px;}

div[role="radiogroup"]{gap:8px!important;}
div[role="radiogroup"]>label{background:rgba(4,8,15,.9)!important;border:1px solid #0A1020!important;padding:9px 14px!important;border-radius:10px!important;transition:all .2s!important;cursor:pointer!important;}
div[role="radiogroup"]>label>div:first-child{display:none!important;}
div[role="radiogroup"]>label:nth-child(1):has(input:checked){background:rgba(16,185,129,.07)!important;border-color:#10B981!important;}
div[role="radiogroup"]>label:nth-child(1):has(input:checked) p{color:#34D399!important;font-weight:700!important;}
div[role="radiogroup"]>label:nth-child(2):has(input:checked){background:rgba(239,68,68,.07)!important;border-color:#EF4444!important;}
div[role="radiogroup"]>label:nth-child(2):has(input:checked) p{color:#F87171!important;font-weight:700!important;}

.stProgress>div>div{background:linear-gradient(90deg,#38BDF8,#818CF8)!important;border-radius:10px!important;}
.stProgress>div{background:#080F1E!important;border-radius:10px!important;}

.stInfo,[data-baseweb="notification"]{background:rgba(56,189,248,.04)!important;border:1px solid rgba(56,189,248,.1)!important;border-radius:12px!important;}
.stSuccess{background:rgba(16,185,129,.04)!important;border:1px solid rgba(16,185,129,.12)!important;border-radius:12px!important;}
.stError{background:rgba(239,68,68,.04)!important;border:1px solid rgba(239,68,68,.12)!important;border-radius:12px!important;}
.stWarning{background:rgba(245,158,11,.04)!important;border:1px solid rgba(245,158,11,.12)!important;border-radius:12px!important;}

[data-testid="stExpander"]{background:rgba(4,8,15,.8)!important;border:1px solid #0A1020!important;border-radius:14px!important;}
[data-testid="stExpander"] summary{color:#475569!important;font-weight:700!important;font-size:13px!important;}

[data-testid="stChatMessage"]{background:rgba(7,11,22,.85)!important;border:1px solid #0A1020!important;border-radius:14px!important;}
[data-testid="stChatInput"]>div>div{background:rgba(4,8,15,.95)!important;border:1px solid rgba(56,189,248,.12)!important;border-radius:12px!important;}

.insight-card{background:linear-gradient(135deg,rgba(56,189,248,.03),rgba(139,92,246,.03));border:1px solid rgba(56,189,248,.08);border-radius:12px;padding:12px 14px;margin-bottom:7px;display:flex;align-items:flex-start;gap:10px;animation:fadeUp .4s ease both;}
.insight-icon{font-size:18px;flex-shrink:0;margin-top:1px;}
.insight-txt{font-size:12.5px;color:#64748B;line-height:1.55;}
.insight-txt strong{color:#94A3B8;}

.bgt-card{background:rgba(4,8,15,.85);border:1px solid #0A1020;border-radius:11px;padding:11px 13px;margin-bottom:7px;transition:border-color .2s;}
.bgt-card:hover{border-color:#0F172A;}
.bar-track{width:100%;background:#040810;border-radius:10px;height:6px;margin-top:7px;}
.bar-fill{height:100%;border-radius:10px;transition:width .8s cubic-bezier(.4,0,.2,1);}

.sk-card{background:rgba(4,8,15,.9);border-radius:14px;padding:15px 16px;border:1px solid #0A1020;transition:all .25s;animation:fadeUp .4s ease both;}
.sk-card:hover{border-color:#0F172A;transform:translateY(-2px);}
.sk-ticker{font-size:17px;font-weight:900;color:#F1F5F9;font-family:'JetBrains Mono',monospace;}
.gl-pos{background:rgba(16,185,129,.09);color:#34D399;border:1px solid rgba(16,185,129,.16);padding:2px 9px;border-radius:999px;font-weight:700;font-size:11.5px;}
.gl-neg{background:rgba(239,68,68,.09);color:#F87171;border:1px solid rgba(239,68,68,.16);padding:2px 9px;border-radius:999px;font-weight:700;font-size:11.5px;}
.gl-neu{background:rgba(100,116,139,.09);color:#94A3B8;border:1px solid rgba(100,116,139,.16);padding:2px 9px;border-radius:999px;font-weight:700;font-size:11.5px;}

.rec-card{background:rgba(4,8,15,.92);border:1px solid #0A1020;border-radius:16px;padding:18px;margin-bottom:12px;box-shadow:0 4px 22px rgba(0,0,0,.3);transition:all .2s;animation:fadeUp .45s ease both;}
.rec-card:hover{border-color:#0F172A;}
.st-buy{background:rgba(16,185,129,.09);color:#34D399;border:1px solid rgba(16,185,129,.18);padding:3px 12px;border-radius:999px;font-weight:800;font-size:11.5px;}
.st-strong{background:rgba(56,189,248,.09);color:#38BDF8;border:1px solid rgba(56,189,248,.18);padding:3px 12px;border-radius:999px;font-weight:800;font-size:11.5px;}
.st-wait{background:rgba(245,158,11,.09);color:#FBBF24;border:1px solid rgba(245,158,11,.18);padding:3px 12px;border-radius:999px;font-weight:800;font-size:11.5px;}
.st-sell{background:rgba(239,68,68,.09);color:#F87171;border:1px solid rgba(239,68,68,.18);padding:3px 12px;border-radius:999px;font-weight:800;font-size:11.5px;}
.mini-stat{background:#040810;border-radius:9px;padding:9px 11px;}
.ms-lbl{font-size:8.5px;color:#1E293B;text-transform:uppercase;letter-spacing:1px;font-weight:800;}

.gauge-wrap{display:flex;flex-direction:column;align-items:center;}
.grade-badge{display:inline-flex;align-items:center;gap:6px;padding:4px 13px;border-radius:999px;font-size:11px;font-weight:800;letter-spacing:.5px;margin-top:5px;}
.grade-ex{background:rgba(16,185,129,.09);color:#34D399;border:1px solid rgba(16,185,129,.16);}
.grade-gd{background:rgba(56,189,248,.09);color:#38BDF8;border:1px solid rgba(56,189,248,.16);}
.grade-fa{background:rgba(245,158,11,.09);color:#FBBF24;border:1px solid rgba(245,158,11,.16);}
.grade-po{background:rgba(239,68,68,.09);color:#F87171;border:1px solid rgba(239,68,68,.16);}

.vital-bar{background:rgba(4,8,15,.85);border:1px solid #0A1020;border-radius:11px;padding:11px 14px;margin-bottom:7px;}
.pin-key button{height:60px!important;font-size:20px!important;font-weight:700!important;border-radius:13px!important;padding:0!important;background:rgba(10,16,30,.9)!important;color:#E2E8F0!important;border:1px solid #0A1020!important;box-shadow:none!important;}
.pin-key button:hover{background:rgba(56,189,248,.07)!important;border-color:rgba(56,189,248,.18)!important;transform:none!important;}

.live-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#10B981;animation:pulse 2s ease-in-out infinite;margin-right:5px;}
.mono{font-family:'JetBrains Mono',monospace!important;}
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:#0A1020;border-radius:10px;}
hr{border-color:#0A1020!important;margin:14px 0!important;}
[data-testid="stDecoration"]{display:none;}
@media(max-width:768px){.wcard{min-width:78vw!important;} [data-testid="stTabs"] div[data-baseweb="tab-list"]{overflow-x:auto!important;scrollbar-width:none!important;} [data-testid="stTabs"] button[data-baseweb="tab"]{flex:0 0 auto!important;}}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════
#  3. LOGIN — PIN KEYPAD
# ══════════════════════════════════════════
if not st.session_state.authenticated:
    st.markdown("<style>[data-testid='collapsedControl']{display:none!important} section[data-testid='stSidebar']{display:none!important}</style>", unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        st.markdown("""
        <div style='text-align:center;margin-bottom:26px;'>
          <div style='font-size:42px;font-weight:900;letter-spacing:-3px;background:linear-gradient(135deg,#38BDF8,#818CF8,#C084FC);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;'>ROGER</div>
          <div style='font-size:9px;color:#1E293B;letter-spacing:3px;text-transform:uppercase;font-weight:700;margin-top:3px;'>Personal Finance Dashboard v3</div>
        </div>
        """, unsafe_allow_html=True)
        pin_len = len(st.session_state.pin_input)
        dots = '<div style="display:flex;justify-content:center;gap:14px;margin-bottom:28px;">'
        for i in range(6):
            if i < pin_len:
                dots += '<div style="width:12px;height:12px;border-radius:50%;background:linear-gradient(135deg,#38BDF8,#818CF8);box-shadow:0 0 10px rgba(56,189,248,.5);"></div>'
            else:
                dots += '<div style="width:12px;height:12px;border-radius:50%;background:#080F1E;border:1.5px solid #0F172A;"></div>'
        dots += '</div>'
        st.markdown(dots, unsafe_allow_html=True)

        if pin_len == 6:
            if st.session_state.pin_input == st.session_state.saved_pin:
                st.session_state.authenticated = True
                st.session_state.pin_input = ""
                st.rerun()
            else:
                st.markdown('<p style="text-align:center;color:#F87171;font-weight:700;font-size:13px;">❌ PIN Salah. Coba lagi.</p>', unsafe_allow_html=True)
                if st.button("↩ Ulangi", use_container_width=True):
                    st.session_state.pin_input = ""; st.rerun()
                st.stop()

        KEYS = [["1","2","3"],["4","5","6"],["7","8","9"],["C","0","⌫"]]
        for row in KEYS:
            c1, c2, c3 = st.columns(3)
            for col_obj, k in zip([c1,c2,c3], row):
                with col_obj:
                    st.markdown('<div class="pin-key">', unsafe_allow_html=True)
                    if st.button(k, use_container_width=True, key=f"pk_{k}_{row[0]}"):
                        if k == "⌫": st.session_state.pin_input = st.session_state.pin_input[:-1]
                        elif k == "C": st.session_state.pin_input = ""
                        else: st.session_state.pin_input += k
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════
#  4. GOOGLE SHEETS + DATA LOAD
# ══════════════════════════════════════════
@st.cache_resource
def init_gsheets():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(json.loads(st.secrets["GOOGLE_JSON"]), scopes=scopes)
        return gspread.authorize(creds).open("Database Finance Pro")
    except: return None

db = init_gsheets()
if not db:
    st.error("❌ Gagal koneksi ke Google Sheets. Cek secrets konfigurasi.")
    st.stop()

@st.cache_data(ttl=60)
def load_sheets():
    try:
        dft = get_as_dataframe(db.worksheet("Transaksi")).dropna(how='all')
        dfs = get_as_dataframe(db.worksheet("Saham")).dropna(how='all')
        return dft, dfs
    except: return pd.DataFrame(), pd.DataFrame()

ws_t = db.worksheet("Transaksi")
ws_s = db.worksheet("Saham")
df_t_raw, df_s_raw = load_sheets()
df_t = df_t_raw.copy()
df_s = df_s_raw.copy()
if not df_t.empty:
    if 'Nominal' in df_t.columns: df_t['Nominal'] = df_t['Nominal'].apply(bersihkan_angka)
    if 'Tanggal' in df_t.columns:
        df_t['Tanggal'] = df_t['Tanggal'].apply(bersihkan_tgl)
        df_t = df_t.dropna(subset=['Tanggal'])

# ══════════════════════════════════════════
#  5. HITUNG SALDO & PORTOFOLIO
# ══════════════════════════════════════════
porto = {"BCA": 0.0, "BRI": 0.0, "Bank Jago": 0.0, "Dompet (Cash)": 0.0}
if not df_t.empty:
    for _, r in df_t.iterrows():
        s = str(r.get('Sumber Dana',''))
        j = str(r.get('Jenis','')).lower().strip()
        n = float(r.get('Nominal', 0))
        if s in porto: porto[s] += n if j == 'pemasukan' else -n

harga_dict = {}
total_saham = 0.0
df_s_agg = pd.DataFrame()

if not df_s.empty:
    try:
        kurs = 15500.0
        try:
            k = yf.Ticker("USDIDR=X").history(period="2d")
            if not k.empty: kurs = float(k['Close'].iloc[-1])
        except: pass
        tks = [str(t).upper().strip() for t in df_s['Ticker'].unique() if pd.notna(t) and str(t).strip()]
        if tks:
            raw = yf.download(tks, period="5d", progress=False)
            for t in tks:
                try:
                    cls = raw['Close'][t].dropna() if len(tks) > 1 else raw['Close'].dropna()
                    cp = float(cls.iloc[-1])
                    harga_dict[t] = cp * kurs if not t.endswith('.JK') else cp
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

total_cash = sum(porto.values())
total_net  = total_cash + total_saham
now = pd.Timestamp.now('Asia/Jakarta')


# ══════════════════════════════════════════
#  6. SIDEBAR NAVIGATION
# ══════════════════════════════════════════

# ══════════════════════════════════════════
#  6. NAVIGATION SETUP
# ══════════════════════════════════════════
NAV = [
    ("Dashboard",   "🏠", "Ringkasan & Insight"),
    ("Keuangan",    "💳", "Transaksi & Budget"),
    ("Portofolio",  "📈", "Saham & Investasi"),
    ("AI Advisor",  "🤖", "Chat Keuangan AI"),
    ("Rekomendasi", "⭐", "Saham Murah Harian"),
    ("Screener",    "⚡", "Technical Screener"),
    ("Scanner",     "🧾", "Scan Nota Otomatis"),
    ("Pengaturan",  "⚙️", "Konfigurasi Sistem"),
]

# ── Sidebar: hanya info & aksi (bukan navigasi) ──

# ══════════════════════════════════════════
#  NAV CONFIG
# ══════════════════════════════════════════
NAV = [
    ("Dashboard",   "🏠", "Ringkasan"),
    ("Keuangan",    "💳", "Transaksi"),
    ("Portofolio",  "📈", "Saham"),
    ("AI Advisor",  "🤖", "AI Chat"),
    ("Rekomendasi", "⭐", "Saham Murah"),
    ("Screener",    "⚡", "Screener"),
    ("Scanner",     "🧾", "Scan Nota"),
    ("Pengaturan",  "⚙️", "Settings"),
]

# Sembunyikan sidebar sepenuhnya
st.markdown("""
<style>
section[data-testid="stSidebar"]          { display:none !important; }
[data-testid="collapsedControl"]           { display:none !important; }
[data-testid="stSidebarNav"]              { display:none !important; }
.stAppDeployButton                         { display:none !important; }
#MainMenu                                  { display:none !important; }
header[data-testid="stHeader"]             { display:none !important; }
footer                                     { display:none !important; }

/* Hilangkan padding default streamlit atas */
.block-container {
    padding-top: 0 !important;
    padding-bottom: 20px !important;
    max-width: 100% !important;
}
[data-testid="stAppViewContainer"] > section > div:first-child {
    padding-top: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════
#  PREMIUM TOP BAR — Logo + Stats + Actions
# ══════════════════════════════════════════
now = pd.Timestamp.now('Asia/Jakarta')

# Top header bar HTML
_hide_char = "••••••" if st.session_state.hide_balance else ""

def _fmt_top(v):
    if st.session_state.hide_balance: return "Rp ••••"
    if v >= 1_000_000_000: return f"Rp {v/1_000_000_000:.1f}M"
    if v >= 1_000_000:     return f"Rp {v/1_000_000:.1f}Jt"
    return f"Rp {v:,.0f}".replace(",",".")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');

/* ── Global Reset ── */
*, *::before, *::after {{ box-sizing: border-box; }}
html, body, .stApp {{ font-family: 'Inter', sans-serif !important; background: #030712 !important; color: #E2E8F0 !important; }}

/* ── Animated Background ── */
.stApp::before {{
    content: ''; position: fixed; top: -20%; left: -10%; width: 55%; height: 55%;
    background: radial-gradient(ellipse, rgba(56,189,248,0.035) 0%, transparent 65%);
    pointer-events: none; z-index: 0;
    animation: aurora1 25s ease-in-out infinite alternate;
}}
.stApp::after {{
    content: ''; position: fixed; bottom: -20%; right: -10%; width: 60%; height: 60%;
    background: radial-gradient(ellipse, rgba(139,92,246,0.035) 0%, transparent 65%);
    pointer-events: none; z-index: 0;
    animation: aurora2 30s ease-in-out infinite alternate;
}}
@keyframes aurora1 {{ from {{ transform: translate(0,0) scale(1); }} to {{ transform: translate(80px,60px) scale(1.15); }} }}
@keyframes aurora2 {{ from {{ transform: translate(0,0) scale(1); }} to {{ transform: translate(-60px,-40px) scale(1.2); }} }}
@keyframes fadeUp  {{ from {{ opacity:0; transform:translateY(14px); }} to {{ opacity:1; transform:translateY(0); }} }}
@keyframes pulse   {{ 0%,100% {{ opacity:1; transform:scale(1); }} 50% {{ opacity:0.5; transform:scale(1.5); }} }}
@keyframes shimmer {{ 0% {{ background-position: -200% 0; }} 100% {{ background-position: 200% 0; }} }}

/* ── Top Header Bar ── */
.topbar {{
    position: sticky; top: 0; z-index: 999;
    background: rgba(3,7,18,0.92);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border-bottom: 1px solid rgba(56,189,248,0.07);
    padding: 0 24px;
    display: flex; align-items: center; gap: 0;
    height: 60px;
    box-shadow: 0 1px 40px rgba(0,0,0,0.5);
}}
.topbar-logo {{
    font-size: 20px; font-weight: 900; letter-spacing: -1px;
    background: linear-gradient(135deg, #38BDF8 0%, #818CF8 55%, #C084FC 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    flex-shrink: 0; margin-right: 28px;
    filter: drop-shadow(0 0 12px rgba(56,189,248,0.3));
}}
.topbar-divider {{ width: 1px; height: 28px; background: rgba(255,255,255,0.07); margin: 0 20px; flex-shrink: 0; }}
.topbar-stat {{ display: flex; flex-direction: column; margin-right: 20px; flex-shrink: 0; }}
.topbar-stat-label {{ font-size: 8.5px; color: #1E293B; font-weight: 800; text-transform: uppercase; letter-spacing: 1.2px; }}
.topbar-stat-value {{ font-size: 13px; font-weight: 800; margin-top: 1px; letter-spacing: -0.3px; }}
.topbar-right {{ margin-left: auto; display: flex; align-items: center; gap: 8px; }}
.topbar-date {{ font-size: 11px; color: #1E293B; font-weight: 600; margin-right: 8px; }}
.live-dot {{ display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #10B981; animation: pulse 2s ease-in-out infinite; margin-right: 5px; vertical-align: middle; }}

/* ── Navigation Tab Bar ── */
.navtab-wrap {{
    background: rgba(3,7,18,0.7);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(255,255,255,0.04);
    padding: 0 24px;
    display: flex; align-items: stretch; gap: 0;
    height: 48px;
    position: sticky; top: 60px; z-index: 998;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
}}
.navtab-item {{
    display: flex; align-items: center; gap: 7px;
    padding: 0 16px; height: 100%;
    font-size: 12.5px; font-weight: 600;
    color: #334155; cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s cubic-bezier(0.4,0,0.2,1);
    white-space: nowrap; text-decoration: none;
    position: relative;
}}
.navtab-item:hover {{ color: #64748B; border-bottom-color: rgba(56,189,248,0.3); }}
.navtab-item .nav-ico {{ font-size: 14px; }}
.navtab-active {{
    display: flex; align-items: center; gap: 7px;
    padding: 0 16px; height: 100%;
    font-size: 12.5px; font-weight: 700;
    color: #38BDF8;
    border-bottom: 2px solid #38BDF8;
    position: relative; white-space: nowrap;
    background: linear-gradient(180deg, transparent 0%, rgba(56,189,248,0.05) 100%);
}}
.navtab-active::after {{
    content: ''; position: absolute;
    bottom: -1px; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #38BDF8, #818CF8);
    border-radius: 2px 2px 0 0;
    box-shadow: 0 0 10px rgba(56,189,248,0.5);
}}
.navtab-active .nav-ico {{ font-size: 14px; }}

/* ── Action Buttons in Header ── */
.hdr-btn {{
    display: inline-flex; align-items: center; gap: 5px;
    padding: 6px 12px; border-radius: 8px;
    font-size: 11.5px; font-weight: 700;
    cursor: pointer; transition: all 0.2s ease;
    border: 1px solid rgba(255,255,255,0.07);
    background: rgba(15,23,42,0.8);
    color: #475569;
    text-decoration: none;
    font-family: 'Inter', sans-serif;
}}
.hdr-btn:hover {{ background: rgba(30,41,59,0.9); color: #94A3B8; border-color: rgba(255,255,255,0.1); }}
.hdr-btn-danger {{ color: #F87171; border-color: rgba(239,68,68,0.15); }}
.hdr-btn-danger:hover {{ background: rgba(239,68,68,0.08); border-color: rgba(239,68,68,0.25); }}

/* ── Main Content Padding ── */
.main-content {{ padding: 22px 8px 0 8px; animation: fadeUp 0.35s ease both; }}

/* ── Metric Cards ── */
div[data-testid="metric-container"] {{
    background: rgba(7,11,22,0.85) !important; border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 16px !important; padding: 18px !important;
    box-shadow: 0 4px 18px rgba(0,0,0,0.25) !important; transition: all .25s ease !important;
    animation: fadeUp .4s ease both;
}}
div[data-testid="metric-container"]:hover {{ border-color: rgba(56,189,248,.12) !important; transform: translateY(-2px) !important; }}
[data-testid="stMetricValue"]  {{ font-size: 1.6rem !important; font-weight: 900 !important; color: #F1F5F9 !important; letter-spacing: -.5px !important; }}
[data-testid="stMetricLabel"]  {{ font-size: 10px !important; font-weight: 700 !important; color: #1E293B !important; text-transform: uppercase !important; letter-spacing: 1.2px !important; }}
[data-testid="stMetricDelta"]  {{ font-size: 12px !important; font-weight: 700 !important; }}

/* ── Cards ── */
.card {{
    background: rgba(7,11,22,0.8); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.05); border-radius: 18px;
    padding: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    transition: all 0.3s ease; animation: fadeUp 0.4s ease both;
}}
.card:hover {{ border-color: rgba(56,189,248,0.1); transform: translateY(-2px); }}

/* ── Wallet Cards ── */
.wcard {{ min-width: 180px; flex: 1; border-radius: 16px; padding: 18px 15px; position: relative; overflow: hidden; transition: all .3s cubic-bezier(.4,0,.2,1); animation: fadeUp .5s ease both; }}
.wcard::before {{ content: ''; position: absolute; inset: 0; background: url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23fff' fill-opacity='0.03'%3E%3Cpath d='M20 20.5V18H0v5h20v20.5h2V23h20v-5H22V20.5h-2z'/%3E%3C/g%3E%3C/svg%3E"); }}
.wcard:hover {{ transform: translateY(-5px) scale(1.015); }}
.wcard-chip {{ position:absolute;top:11px;right:11px;width:24px;height:18px;border-radius:3px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.1); }}
.wcard-icon {{ font-size:20px;margin-bottom:10px; }}
.wcard-lbl {{ font-size:8.5px;font-weight:700;color:rgba(255,255,255,.38);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:3px; }}
.wcard-bal {{ font-size:16px;font-weight:900;color:#fff;letter-spacing:-.3px;font-family:'JetBrains Mono',monospace; }}
.wcard-bca  {{ background:linear-gradient(145deg,#1a3a6c,#0d1f3d); border:1px solid rgba(59,130,246,.2); box-shadow:0 6px 24px rgba(59,130,246,.1); }}
.wcard-bri  {{ background:linear-gradient(145deg,#7c2d12,#431a05); border:1px solid rgba(249,115,22,.2); box-shadow:0 6px 24px rgba(249,115,22,.1); }}
.wcard-jago {{ background:linear-gradient(145deg,#78350f,#3d2000); border:1px solid rgba(245,158,11,.2); box-shadow:0 6px 24px rgba(245,158,11,.1); }}
.wcard-cash {{ background:linear-gradient(145deg,#064e3b,#022c22); border:1px solid rgba(16,185,129,.2); box-shadow:0 6px 24px rgba(16,185,129,.1); }}

/* ── Section Dividers ── */
.sec {{ display:flex; align-items:center; gap:10px; margin:20px 0 12px; }}
.sec-txt {{ font-size:10px; font-weight:800; color:#1E293B; text-transform:uppercase; letter-spacing:2px; white-space:nowrap; }}
.sec-line {{ flex:1; height:1px; background:linear-gradient(90deg,rgba(255,255,255,.05),transparent); }}

/* ── Banner ── */
.banner {{ background:linear-gradient(135deg,rgba(14,165,233,.06),rgba(139,92,246,.06)); border:1px solid rgba(56,189,248,.08); border-radius:14px; padding:14px 18px; display:flex; gap:18px; flex-wrap:wrap; align-items:center; margin-bottom:14px; animation:fadeUp .4s ease; }}
.bitem {{ display:flex; flex-direction:column; }}
.blbl {{ font-size:8.5px; color:#1E293B; font-weight:800; text-transform:uppercase; letter-spacing:1.2px; }}
.bval {{ font-size:16px; font-weight:900; margin-top:2px; }}
.divider-v {{ width:1px; background:#0A1020; height:32px; flex-shrink:0; }}

/* ── Table ── */
.tbl-wrap {{ background:rgba(3,7,18,.95); border:1px solid #080F1E; border-radius:12px; overflow:auto; max-height:380px; }}
.tbl-wrap::-webkit-scrollbar {{ width:4px; height:4px; }}
.tbl-wrap::-webkit-scrollbar-thumb {{ background:#0F172A; border-radius:10px; }}
.ctbl {{ width:100%; border-collapse:collapse; color:#475569; font-size:12px; }}
.ctbl thead th {{ position:sticky; top:0; background:#020508; padding:10px 14px; font-weight:700; color:#1E293B; text-transform:uppercase; letter-spacing:.8px; font-size:9.5px; border-bottom:1px solid #080F1E; z-index:1; }}
.ctbl td {{ padding:10px 14px; border-bottom:1px solid rgba(8,15,30,.9); }}
.ctbl tbody tr:hover td {{ background:rgba(56,189,248,.02); }}
.ctbl tbody tr:last-of-type td {{ border-bottom:none; }}

/* ── Tabs ── */
[data-testid="stTabs"] div[data-baseweb="tab-list"] {{ gap:2px; background:rgba(3,7,18,.9); border-radius:10px; padding:4px; border:1px solid #080F1E; }}
[data-testid="stTabs"] button[data-baseweb="tab"] {{ background:transparent; border-radius:7px; padding:7px 13px; font-weight:600; font-size:12px; color:#1E293B; border:none; transition:all .2s; }}
[data-testid="stTabs"] button[data-baseweb="tab"]:hover {{ color:#475569; }}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {{ background:rgba(15,23,42,.95); color:#38BDF8; box-shadow:0 2px 8px rgba(0,0,0,.35); }}
[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {{ display:none; }}

/* ── Buttons ── */
.stButton>button {{ background:linear-gradient(135deg,#0EA5E9,#6366F1)!important; color:#fff!important; font-weight:700!important; font-size:13px!important; border-radius:10px!important; border:none!important; padding:10px 20px!important; transition:all .25s cubic-bezier(.4,0,.2,1)!important; box-shadow:0 4px 14px rgba(14,165,233,.2)!important; letter-spacing:.2px!important; }}
.stButton>button:hover {{ transform:translateY(-2px)!important; box-shadow:0 8px 24px rgba(14,165,233,.3)!important; filter:brightness(1.1)!important; }}
.stButton>button:active {{ transform:translateY(0)!important; }}

/* ── Inputs ── */
.stTextInput input,.stNumberInput input,.stTextArea textarea,.stDateInput input {{ background:rgba(3,7,18,.95)!important; border:1px solid #080F1E!important; border-radius:10px!important; color:#E2E8F0!important; font-size:13px!important; transition:border-color .2s,box-shadow .2s!important; }}
.stTextInput input:focus,.stNumberInput input:focus,.stTextArea textarea:focus {{ border-color:#38BDF8!important; box-shadow:0 0 0 3px rgba(56,189,248,.07)!important; }}
.stSelectbox div[data-baseweb="select"] {{ background:rgba(3,7,18,.95)!important; border:1px solid #080F1E!important; border-radius:10px!important; }}
label {{ color:#334155!important; font-size:10px!important; font-weight:700!important; text-transform:uppercase; letter-spacing:.5px; }}

/* ── Radio ── */
div[role="radiogroup"] {{ gap:7px!important; }}
div[role="radiogroup"]>label {{ background:rgba(3,7,18,.9)!important; border:1px solid #080F1E!important; padding:8px 14px!important; border-radius:9px!important; transition:all .2s!important; cursor:pointer!important; }}
div[role="radiogroup"]>label>div:first-child {{ display:none!important; }}
div[role="radiogroup"]>label:nth-child(1):has(input:checked) {{ background:rgba(16,185,129,.07)!important; border-color:#10B981!important; }}
div[role="radiogroup"]>label:nth-child(1):has(input:checked) p {{ color:#34D399!important; font-weight:700!important; }}
div[role="radiogroup"]>label:nth-child(2):has(input:checked) {{ background:rgba(239,68,68,.07)!important; border-color:#EF4444!important; }}
div[role="radiogroup"]>label:nth-child(2):has(input:checked) p {{ color:#F87171!important; font-weight:700!important; }}

/* ── Progress ── */
.stProgress>div>div {{ background:linear-gradient(90deg,#38BDF8,#818CF8)!important; border-radius:10px!important; }}
.stProgress>div {{ background:#080F1E!important; border-radius:10px!important; }}

/* ── Alerts ── */
.stInfo {{ background:rgba(56,189,248,.04)!important; border:1px solid rgba(56,189,248,.1)!important; border-radius:12px!important; }}
.stSuccess {{ background:rgba(16,185,129,.04)!important; border:1px solid rgba(16,185,129,.12)!important; border-radius:12px!important; }}
.stError   {{ background:rgba(239,68,68,.04)!important;  border:1px solid rgba(239,68,68,.12)!important;  border-radius:12px!important; }}
.stWarning {{ background:rgba(245,158,11,.04)!important; border:1px solid rgba(245,158,11,.12)!important; border-radius:12px!important; }}

/* ── Expander ── */
[data-testid="stExpander"] {{ background:rgba(3,7,18,.8)!important; border:1px solid #080F1E!important; border-radius:13px!important; }}
[data-testid="stExpander"] summary {{ color:#475569!important; font-weight:700!important; font-size:12.5px!important; }}

/* ── Chat ── */
[data-testid="stChatMessage"] {{ background:rgba(7,11,22,.85)!important; border:1px solid #080F1E!important; border-radius:13px!important; }}
[data-testid="stChatInput"]>div>div {{ background:rgba(3,7,18,.95)!important; border:1px solid rgba(56,189,248,.12)!important; border-radius:12px!important; }}

/* ── Mini components ── */
.insight-card {{ background:linear-gradient(135deg,rgba(56,189,248,.03),rgba(139,92,246,.03)); border:1px solid rgba(56,189,248,.07); border-radius:12px; padding:11px 13px; margin-bottom:7px; display:flex; align-items:flex-start; gap:10px; }}
.insight-icon {{ font-size:17px; flex-shrink:0; margin-top:1px; }}
.insight-txt {{ font-size:12px; color:#475569; line-height:1.55; }}
.insight-txt strong {{ color:#64748B; }}

.bgt-card {{ background:rgba(3,7,18,.85); border:1px solid #080F1E; border-radius:11px; padding:11px 13px; margin-bottom:7px; }}
.bar-track {{ width:100%; background:#020508; border-radius:10px; height:5px; margin-top:6px; }}
.bar-fill {{ height:100%; border-radius:10px; transition:width .8s cubic-bezier(.4,0,.2,1); }}

.sk-card {{ background:rgba(3,7,18,.9); border-radius:14px; padding:14px 16px; border:1px solid #080F1E; transition:all .25s; animation:fadeUp .4s ease both; }}
.sk-card:hover {{ border-color:#0F172A; transform:translateY(-2px); }}
.sk-ticker {{ font-size:17px; font-weight:900; color:#F1F5F9; font-family:'JetBrains Mono',monospace; }}
.gl-pos {{ background:rgba(16,185,129,.09);color:#34D399;border:1px solid rgba(16,185,129,.15);padding:2px 9px;border-radius:999px;font-weight:700;font-size:11px; }}
.gl-neg {{ background:rgba(239,68,68,.09);color:#F87171;border:1px solid rgba(239,68,68,.15);padding:2px 9px;border-radius:999px;font-weight:700;font-size:11px; }}
.gl-neu {{ background:rgba(100,116,139,.09);color:#94A3B8;border:1px solid rgba(100,116,139,.15);padding:2px 9px;border-radius:999px;font-weight:700;font-size:11px; }}

.rec-card {{ background:rgba(3,7,18,.92); border:1px solid #080F1E; border-radius:16px; padding:18px; margin-bottom:12px; box-shadow:0 4px 22px rgba(0,0,0,.3); transition:all .2s; animation:fadeUp .45s ease both; }}
.rec-card:hover {{ border-color:#0F172A; }}
.st-buy    {{ background:rgba(16,185,129,.09);color:#34D399;border:1px solid rgba(16,185,129,.17);padding:3px 12px;border-radius:999px;font-weight:800;font-size:11px; }}
.st-strong {{ background:rgba(56,189,248,.09);color:#38BDF8;border:1px solid rgba(56,189,248,.17);padding:3px 12px;border-radius:999px;font-weight:800;font-size:11px; }}
.st-wait   {{ background:rgba(245,158,11,.09);color:#FBBF24;border:1px solid rgba(245,158,11,.17);padding:3px 12px;border-radius:999px;font-weight:800;font-size:11px; }}
.st-sell   {{ background:rgba(239,68,68,.09);color:#F87171;border:1px solid rgba(239,68,68,.17);padding:3px 12px;border-radius:999px;font-weight:800;font-size:11px; }}
.mini-stat {{ background:#020508; border-radius:8px; padding:8px 10px; }}
.ms-lbl {{ font-size:8px; color:#0F172A; text-transform:uppercase; letter-spacing:1px; font-weight:800; }}

.gauge-wrap {{ display:flex; flex-direction:column; align-items:center; }}
.grade-badge {{ display:inline-flex; align-items:center; gap:5px; padding:4px 12px; border-radius:999px; font-size:10.5px; font-weight:800; letter-spacing:.5px; margin-top:4px; }}
.grade-ex {{ background:rgba(16,185,129,.09);color:#34D399;border:1px solid rgba(16,185,129,.15); }}
.grade-gd {{ background:rgba(56,189,248,.09);color:#38BDF8;border:1px solid rgba(56,189,248,.15); }}
.grade-fa {{ background:rgba(245,158,11,.09);color:#FBBF24;border:1px solid rgba(245,158,11,.15); }}
.grade-po {{ background:rgba(239,68,68,.09);color:#F87171;border:1px solid rgba(239,68,68,.15); }}

.vital-bar {{ background:rgba(3,7,18,.85); border:1px solid #080F1E; border-radius:11px; padding:11px 14px; margin-bottom:7px; }}
.mono {{ font-family:'JetBrains Mono',monospace!important; }}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width:5px; height:5px; }}
::-webkit-scrollbar-track {{ background:transparent; }}
::-webkit-scrollbar-thumb {{ background:#080F1E; border-radius:10px; }}
::-webkit-scrollbar-thumb:hover {{ background:#0F172A; }}
hr {{ border-color:#080F1E!important; margin:14px 0!important; }}

/* ── PIN keypad ── */
.pin-key button {{ height:58px!important; font-size:20px!important; font-weight:700!important; border-radius:12px!important; padding:0!important; background:rgba(7,11,22,.9)!important; color:#E2E8F0!important; border:1px solid #080F1E!important; box-shadow:none!important; }}
.pin-key button:hover {{ background:rgba(56,189,248,.06)!important; border-color:rgba(56,189,248,.15)!important; transform:none!important; }}

/* ── Mobile ── */
@media(max-width:768px) {{
    .wcard {{ min-width: 78vw!important; }}
    .topbar {{ padding: 0 12px!important; height: 54px!important; }}
    .navtab-wrap {{ padding: 0 8px!important; overflow-x: auto!important; scrollbar-width: none!important; }}
    .navtab-wrap::-webkit-scrollbar {{ display:none; }}
    .navtab-item, .navtab-active {{ padding: 0 12px!important; font-size: 11.5px!important; }}
}}
</style>

<!-- ═══════════════════════════════════════════════
     TOP HEADER BAR
════════════════════════════════════════════════ -->
<div class="topbar">
  <!-- Logo -->
  <div class="topbar-logo">💎 ROGER</div>

  <!-- Divider -->
  <div class="topbar-divider"></div>

  <!-- Stats -->
  <div class="topbar-stat">
    <span class="topbar-stat-label">Net Worth</span>
    <span class="topbar-stat-value" style="color:#38BDF8;">{_fmt_top(total_net)}</span>
  </div>
  <div class="topbar-stat">
    <span class="topbar-stat-label">Kas</span>
    <span class="topbar-stat-value" style="color:#34D399;">{_fmt_top(total_cash)}</span>
  </div>
  <div class="topbar-stat">
    <span class="topbar-stat-label">Saham</span>
    <span class="topbar-stat-value" style="color:#818CF8;">{_fmt_top(total_saham)}</span>
  </div>

  <!-- Right side -->
  <div class="topbar-right">
    <span class="topbar-date"><span class="live-dot"></span>{now.strftime("%H:%M")} · {now.strftime("%d %b %Y")}</span>
  </div>
</div>

<!-- ═══════════════════════════════════════════════
     NAVIGATION TAB BAR
════════════════════════════════════════════════ -->
<div class="navtab-wrap" id="navtab-bar">
  {''.join([
    f'<div class="navtab-active"><span class="nav-ico">{icon}</span>{pg}</div>'
    if st.session_state.page == pg else
    f'<div class="navtab-item" data-page="{pg}" onclick="triggerNav(\'{pg}\')"><span class="nav-ico">{icon}</span>{pg}</div>'
    for pg, icon, _ in NAV
  ])}
</div>

<script>
function triggerNav(page) {{
  // Cari button tersembunyi dan klik
  var allBtns = window.parent.document.querySelectorAll('button');
  for (var btn of allBtns) {{
    if (btn.innerText.trim() === page || btn.getAttribute('data-nav') === page) {{
      btn.click(); return;
    }}
  }}
  // Fallback: cari dengan key
  var hidden = window.parent.document.querySelector('[data-testid="stButton"] button');
  if (hidden) hidden.click();
}}
</script>
""", unsafe_allow_html=True)

# ── Hidden Streamlit nav buttons (trigger rerun) ──
_hcols = st.columns(len(NAV))
for _i, (_pg, _icon, _desc) in enumerate(NAV):
    if st.session_state.page != _pg:
        with _hcols[_i]:
            if st.button(_pg, key=f"topnav_{_pg}", help=_desc, use_container_width=True):
                st.session_state.page = _pg
                st.rerun()

# ── Quick‑action bar (eye + lock) proporsional di bawah nav ──
st.markdown("""
<style>
/* Sembunyikan tombol hidden nav tapi tetap clickable via JS */
div[data-testid="stHorizontalBlock"]:has(button[data-testid^="baseButton"]) {
    height: 0; overflow: hidden; position: absolute; opacity: 0; pointer-events: none;
}
/* Kecuali yang benar-benar kita tampilkan */
.action-bar-visible div[data-testid="stHorizontalBlock"] {
    height: auto !important; overflow: visible !important;
    position: relative !important; opacity: 1 !important; pointer-events: auto !important;
}
</style>
""", unsafe_allow_html=True)

# Action bar visible
_a1, _a2, _spacer = st.columns([1, 1, 10])
with _a1:
    _eye_lbl = "👁️ Tampil" if st.session_state.hide_balance else "🙈 Sembunyi"
    if st.button(_eye_lbl, key="btn_eye", use_container_width=True):
        st.session_state.hide_balance = not st.session_state.hide_balance
        st.rerun()
with _a2:
    if st.button("🔒 Kunci", key="btn_lock", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.pin_input = ""
        st.rerun()

st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

def generate_insights(df_curr, in_curr, out_curr, budgets):
    insights = []
    if df_curr.empty or in_curr == 0: return insights
    df = df_curr.copy()
    df['Jenis']    = df['Jenis'].str.lower().str.strip()
    df['Kategori'] = df['Kategori'].str.strip().str.title()
    out_df = df[df['Jenis'] == 'pengeluaran']
    rasio_hemat = (in_curr - out_curr) / in_curr * 100
    if rasio_hemat >= 30:
        insights.append(("🎉","Tabungan",f"Kamu berhasil menabung <strong>{rasio_hemat:.1f}%</strong> dari pemasukan bulan ini. Luar biasa!"))
    elif rasio_hemat < 0:
        insights.append(("🚨","Defisit",f"Pengeluaran melebihi pemasukan <strong>{fmt(abs(out_curr-in_curr))}</strong>. Segera kurangi!"))
    elif rasio_hemat < 10:
        insights.append(("⚠️","Hemat",f"Rasio tabungan hanya <strong>{rasio_hemat:.1f}%</strong>. Target minimal 20%."))
    if not out_df.empty:
        top_kat = out_df.groupby('Kategori')['Nominal'].sum().idxmax()
        top_val = out_df.groupby('Kategori')['Nominal'].sum().max()
        insights.append(("📊","Top Spend",f"Pengeluaran terbesar: <strong>{top_kat}</strong> sebesar <strong>{fmt(top_val)}</strong>."))
    for kat, limit in budgets.items():
        spent = out_df[out_df['Kategori'] == kat.strip().title()]['Nominal'].sum()
        if limit > 0 and spent > limit:
            insights.append(("🔴","Budget Jebol",f"Budget <strong>{kat}</strong> jebol <strong>{fmt(spent-limit)}</strong> di atas limit {fmt(limit)}."))
    inv = out_df[out_df['Kategori'] == 'Investasi']['Nominal'].sum()
    inv_pct = inv / in_curr * 100
    if inv_pct < 10:
        insights.append(("💡","Investasi",f"Porsi investasi <strong>{inv_pct:.1f}%</strong> dari pemasukan. Coba tingkatkan ke 20%."))
    elif inv_pct >= 20:
        insights.append(("🌱","Investasi",f"Porsi investasi <strong>{inv_pct:.1f}%</strong> — sudah sangat baik!"))
    return insights[:6]

def project_monthend(df_curr, bulan_idx, tahun):
    if df_curr.empty: return 0.0, [], []
    dim = calendar.monthrange(tahun, bulan_idx)[1]
    out_df = df_curr[df_curr['Jenis'].str.lower() == 'pengeluaran'].copy()
    if out_df.empty: return 0.0, [], []
    out_df['Hari'] = out_df['Tanggal'].dt.day
    daily = out_df.groupby('Hari')['Nominal'].sum().reindex(range(1, dim+1), fill_value=0)
    daily_cum = daily.cumsum().reset_index(); daily_cum.columns = ['Hari','Kumulatif']
    today_day = min(now.day, dim)
    hist = daily_cum[daily_cum['Hari'] <= today_day]
    if len(hist) < 3:
        return float(daily_cum[daily_cum['Hari'] <= today_day]['Kumulatif'].max()), daily_cum['Hari'].tolist(), daily_cum['Kumulatif'].tolist()
    X = hist['Hari'].values.reshape(-1,1); y = hist['Kumulatif'].values
    m = LinearRegression().fit(X, y)
    fd = np.arange(today_day+1, dim+1).reshape(-1,1); yf = m.predict(fd)
    all_days = list(hist['Hari']) + list(range(today_day+1, dim+1))
    all_cum  = list(hist['Kumulatif']) + list(yf)
    proj_end = max(0.0, float(yf[-1]) if len(yf) > 0 else float(hist['Kumulatif'].max()))
    return proj_end, all_days, all_cum


# ══════════════════════════════════════════
#  8. PAGE — DASHBOARD
# ══════════════════════════════════════════
def page_dashboard():
    st.markdown('<h2 style="font-size:21px;font-weight:900;color:#F1F5F9;margin-bottom:0;">🏠 Dashboard</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#1E293B;font-size:12px;margin-top:2px;">{now.strftime("%A, %d %B %Y · %H:%M")} WIB</p>', unsafe_allow_html=True)

    # Today banner
    today_mask = (df_t['Tanggal'].dt.date == now.date()) if not df_t.empty else pd.Series(dtype=bool)
    df_today   = df_t[today_mask].copy() if not df_t.empty else pd.DataFrame()
    ti  = df_today[df_today['Jenis'].str.lower()=='pemasukan']['Nominal'].sum()   if not df_today.empty else 0.0
    to_ = df_today[df_today['Jenis'].str.lower()=='pengeluaran']['Nominal'].sum() if not df_today.empty else 0.0
    nd  = ti - to_; nc = "#34D399" if nd >= 0 else "#F87171"
    st.markdown(f"""
    <div class="banner">
      <div class="bitem"><div class="blbl">Hari Ini</div><div class="bval" style="color:#475569;font-size:13px;">{now.strftime('%d %b')}</div></div>
      <div class="divider-v"></div>
      <div class="bitem"><div class="blbl">Masuk</div><div class="bval" style="color:#34D399;">{fmt(ti)}</div></div>
      <div class="bitem"><div class="blbl">Keluar</div><div class="bval" style="color:#F87171;">{fmt(to_)}</div></div>
      <div class="bitem"><div class="blbl">Net</div><div class="bval" style="color:{nc};">{fmt(nd)}</div></div>
      <div style="margin-left:auto;" class="bitem"><div class="blbl">Transaksi</div><div class="bval" style="color:#475569;">{len(df_today)}</div></div>
    </div>""", unsafe_allow_html=True)

    m1,m2,m3 = st.columns(3)
    m1.metric("🌟 Net Worth", fmt(total_net))
    m2.metric("💵 Uang Tunai", fmt(total_cash))
    m3.metric("📈 Nilai Saham", fmt(total_saham))
    st.markdown("<br>", unsafe_allow_html=True)

    # Wallet cards
    st.markdown('<div class="sec"><span class="sec-txt">💳 Dompet & Rekening</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
    wc = st.columns(4)
    for i,(key,name,icon,cls) in enumerate([("BCA","Bank BCA","🏦","wcard-bca"),("BRI","Bank BRI","🏢","wcard-bri"),("Bank Jago","Bank Jago","🦊","wcard-jago"),("Dompet (Cash)","Uang Tunai","💵","wcard-cash")]):
        with wc[i]:
            st.markdown(f'<div class="wcard {cls}"><div class="wcard-chip"></div><div class="wcard-icon">{icon}</div><div class="wcard-lbl">{name}</div><div class="wcard-bal">{fmt(porto[key])}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_left, col_right = st.columns([2,1])

    with col_left:
        # Target + Projection
        st.markdown('<div class="sec"><span class="sec-txt">🎯 Target Finansial</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        tgt = st.number_input("Target Harta Bersih (Rp)", value=int(st.session_state.target_harta), step=1000000, label_visibility="collapsed", format="%d")
        st.session_state.target_harta = tgt; save_config()
        rasio_t = max(0.0, min(total_net/tgt, 1.0)) if tgt > 0 else 0.0
        pct_t   = rasio_t * 100
        pc = "#34D399" if pct_t>=80 else "#38BDF8" if pct_t>=50 else "#FBBF24" if pct_t>=25 else "#F87171"
        st.progress(rasio_t)
        st.markdown(f'<p style="font-size:12px;color:{pc};font-weight:700;margin-top:4px;">✅ {pct_t:.1f}% tercapai — {fmt(total_net)} dari {fmt(tgt)}</p>', unsafe_allow_html=True)

        st.markdown('<div class="sec"><span class="sec-txt">🔮 Proyeksi Akhir Bulan</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        b_proj = st.selectbox("Bulan Proyeksi:", NAMA_BULAN[1:], index=now.month-1, key="db_proj", label_visibility="collapsed")
        bln_p  = NAMA_BULAN.index(b_proj)
        df_p2  = pd.DataFrame()
        in_p2 = out_p2 = 0.0
        if not df_t.empty:
            dc2 = df_t.copy(); dc2['Jenis'] = dc2['Jenis'].str.lower().str.strip()
            dc2['Kategori'] = dc2['Kategori'].str.strip().str.title()
            df_p2  = dc2[(dc2['Tanggal'].dt.month==bln_p)&(dc2['Tanggal'].dt.year==now.year)]
            in_p2  = df_p2[df_p2['Jenis']=='pemasukan']['Nominal'].sum()
            out_p2 = df_p2[df_p2['Jenis']=='pengeluaran']['Nominal'].sum()
        proj_end, all_days, all_cum = project_monthend(df_p2, bln_p, now.year)
        c1p,c2p,c3p = st.columns(3)
        c1p.metric("Pengeluaran s/d Kini", fmt(out_p2))
        c2p.metric("Proyeksi Akhir Bulan", fmt(proj_end))
        c3p.metric("Estimasi Sisa", fmt(in_p2 - proj_end))
        if all_days and len(all_days) > 3:
            td = now.day
            fig_pj = go.Figure()
            fig_pj.add_trace(go.Scatter(
                x=[d for d in all_days if d<=td], y=[all_cum[i] for i,d in enumerate(all_days) if d<=td],
                name="Aktual", mode="lines+markers", line=dict(color="#38BDF8",width=2.5), marker=dict(size=4)))
            fig_pj.add_trace(go.Scatter(
                x=[d for d in all_days if d>=td], y=[all_cum[i] for i,d in enumerate(all_days) if d>=td],
                name="Proyeksi AI", mode="lines", line=dict(color="#C084FC",width=2.5,dash="dot")))
            fig_pj.add_vline(x=td, line=dict(color="#FBBF24",dash="dash",width=1),annotation_text="Hari Ini",annotation_font_color="#FBBF24")
            fig_pj.update_layout(template="plotly_dark",paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                height=185,margin=dict(l=0,r=0,t=10,b=0),
                legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1,font=dict(size=10)),
                xaxis=dict(showgrid=False,title=None),yaxis=dict(showgrid=True,gridcolor='#080F1E',title=None))
            st.plotly_chart(fig_pj, use_container_width=True)

    with col_right:
        # Health Score
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
        if score>=80: grade,gcls,gem="Excellent","grade-ex","🌟"
        elif score>=60: grade,gcls,gem="Good","grade-gd","👍"
        elif score>=40: grade,gcls,gem="Fair","grade-fa","⚠️"
        else: grade,gcls,gem="Poor","grade-po","🚨"
        rad = math.radians((score/100)*180)
        x_e = 80+60*math.cos(math.pi-rad); y_e = 80-60*math.sin(rad)
        st.markdown(f"""
        <div class="gauge-wrap">
          <svg width="160" height="95" viewBox="0 0 160 95">
            <path d="M 20 80 A 60 60 0 0 1 140 80" fill="none" stroke="#080F1E" stroke-width="12" stroke-linecap="round"/>
            <path d="M 20 80 A 60 60 0 0 1 {x_e:.1f} {y_e:.1f}" fill="none" stroke="{gc_clr}" stroke-width="12" stroke-linecap="round"/>
            <text x="80" y="70" text-anchor="middle" fill="{gc_clr}" font-size="26" font-weight="900" font-family="Inter">{score}</text>
            <text x="80" y="83" text-anchor="middle" fill="#1E293B" font-size="9" font-family="Inter">/ 100</text>
          </svg>
          <span class="grade-badge {gcls}">{gem} {grade}</span>
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Smart Insights
        st.markdown('<div class="sec"><span class="sec-txt">💡 Smart Insights</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        for icon,title,txt in generate_insights(df_p2, in_p2, out_p2, st.session_state.budgets):
            st.markdown(f'<div class="insight-card"><div class="insight-icon">{icon}</div><div class="insight-txt"><strong>{title}</strong> — {txt}</div></div>', unsafe_allow_html=True)
        if not generate_insights(df_p2, in_p2, out_p2, st.session_state.budgets):
            st.info("Catat transaksi bulan ini untuk mendapat insight otomatis.")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Charts
    st.markdown('<div class="sec"><span class="sec-txt">📊 Analisis Visual</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
    gT1,gT2,gT3,gT4,gT5 = st.tabs(["📉 Arus Kas","🧬 50/30/20","🏆 Top Boros","🗓️ Daily Spend","🥧 Alokasi Aset"])
    with gT1:
        if not df_p2.empty:
            dp2 = df_p2.copy(); dp2['Hari']=dp2['Tanggal'].dt.day
            td2 = dp2.groupby(['Hari','Jenis'])['Nominal'].sum().reset_index()
            md2 = dp2['Hari'].max()
            ad2 = pd.DataFrame({'Hari':range(1,md2+1)})
            in_d  = pd.merge(ad2, td2[td2['Jenis']=='pemasukan'],   on='Hari',how='left').fillna({'Nominal':0,'Jenis':'pemasukan'})
            out_d = pd.merge(ad2, td2[td2['Jenis']=='pengeluaran'], on='Hari',how='left').fillna({'Nominal':0,'Jenis':'pengeluaran'})
            fig_ak = px.line(pd.concat([in_d,out_d]),x='Hari',y='Nominal',color='Jenis',
                             color_discrete_map={'pemasukan':'#10B981','pengeluaran':'#EF4444'},markers=True,template="plotly_dark")
            fig_ak.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',height=280,margin=dict(l=0,r=0,t=10,b=0),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            fig_ak.update_xaxes(showgrid=False); fig_ak.update_yaxes(showgrid=True,gridcolor='#080F1E')
            st.plotly_chart(fig_ak,use_container_width=True)
            ca,cb,cc = st.columns(3)
            ca.metric("Pemasukan",fmt(in_p2)); cb.metric("Pengeluaran",fmt(out_p2)); cc.metric("Selisih",fmt(in_p2-out_p2))
        else: st.info("Belum ada data.")
    with gT2:
        if not df_p2.empty and in_p2>0:
            kbthn = ['Bayar Kost','Kost','Makan & Minum','Transportasi','Kuota Internet','Kebutuhan Mandi','Kebutuhan Pokok & Beras','Laundry']
            ox = df_p2[df_p2['Jenis']=='pengeluaran']
            pokok  = ox[ox['Kategori'].isin(kbthn)]['Nominal'].sum()
            invest = ox[ox['Kategori']=='Investasi']['Nominal'].sum()
            keing  = out_p2-pokok-invest
            for ico2,lbl2,ideal2,val2,ok_fn,clr2 in [
                ("🏠","Kebutuhan Pokok","< 50%",pokok,lambda p:p<=50,"#3B82F6"),
                ("🛍️","Gaya Hidup","< 30%",keing,lambda p:p<=30,"#8B5CF6"),
                ("🌱","Masa Depan","≥ 20%",invest,lambda p:p>=20,"#10B981"),
            ]:
                pct2=min((val2/in_p2)*100,100) if in_p2>0 else 0
                bc2="#34D399" if ok_fn(pct2) else "#F87171"
                st.markdown(f'<div class="vital-bar"><div style="display:flex;justify-content:space-between;align-items:center;"><span style="font-size:12px;font-weight:700;color:#475569;">{ico2} {lbl2} <span style="color:#1E293B;">— {ideal2}</span></span><span style="font-size:13px;font-weight:900;color:{bc2};">{pct2:.1f}%</span></div><div style="font-size:16px;font-weight:800;color:#F1F5F9;margin-top:5px;">{fmt(val2)}</div><div class="bar-track"><div class="bar-fill" style="width:{pct2:.0f}%;background:{bc2};"></div></div></div>', unsafe_allow_html=True)
        else: st.info("Catat pemasukan bulan ini.")
    with gT3:
        if not df_p2.empty and out_p2>0:
            t5=df_p2[df_p2['Jenis']=='pengeluaran'].groupby('Kategori')['Nominal'].sum().nlargest(6).reset_index().sort_values('Nominal')
            fig_t5=go.Figure(go.Bar(y=t5['Kategori'],x=t5['Nominal'],orientation='h',marker_color=['#EF4444','#F97316','#F59E0B','#FBBF24','#FCD34D','#FDE68A'][:len(t5)],text=[fmt(v) for v in t5['Nominal']],textposition='outside',textfont=dict(color='#475569',size=11)))
            fig_t5.update_layout(template="plotly_dark",paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',height=280,margin=dict(l=0,r=110,t=10,b=0),xaxis=dict(showgrid=False,showticklabels=False,title=None),yaxis=dict(title=None))
            st.plotly_chart(fig_t5,use_container_width=True)
        else: st.info("Belum ada pengeluaran.")
    with gT4:
        if not df_p2.empty:
            oh=df_p2[df_p2['Jenis']=='pengeluaran'].copy(); oh['Hari']=oh['Tanggal'].dt.day
            dh=oh.groupby('Hari')['Nominal'].sum().reset_index()
            dim2=calendar.monthrange(now.year,bln_p)[1]
            dh=pd.merge(pd.DataFrame({'Hari':range(1,dim2+1)}),dh,on='Hari',how='left').fillna(0)
            fig_hm=px.bar(dh,x='Hari',y='Nominal',color='Nominal',color_continuous_scale='Reds',template="plotly_dark")
            fig_hm.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',height=260,margin=dict(l=0,r=0,t=10,b=0),coloraxis_showscale=False)
            fig_hm.update_xaxes(showgrid=False); fig_hm.update_yaxes(showgrid=True,gridcolor='#080F1E',showticklabels=False,title=None)
            st.plotly_chart(fig_hm,use_container_width=True)
        else: st.info("Belum ada data.")
    with gT5:
        aset={"BCA":porto["BCA"],"BRI":porto["BRI"],"Jago":porto["Bank Jago"],"Cash":porto["Dompet (Cash)"],"Saham":total_saham}
        aset={k:v for k,v in aset.items() if v>0}
        if aset:
            fig_pie=px.pie(pd.DataFrame(list(aset.items()),columns=['Aset','Nilai']),values='Nilai',names='Aset',hole=0.58,template="plotly_dark",color_discrete_map={'BCA':'#3B82F6','BRI':'#F97316','Jago':'#F59E0B','Cash':'#10B981','Saham':'#8B5CF6'})
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)',height=290,margin=dict(l=0,r=0,t=0,b=0),legend=dict(font=dict(size=11,color='#475569')),annotations=[dict(text=f'<b>{fmt(total_net)}</b>',x=0.5,y=0.5,font_size=11,showarrow=False,font_color='#64748B')])
            st.plotly_chart(fig_pie,use_container_width=True)
        else: st.info("Belum ada data aset.")


# ══════════════════════════════════════════
#  9. PAGE — KEUANGAN
# ══════════════════════════════════════════
def page_keuangan():
    st.markdown('<h2 style="font-size:21px;font-weight:900;color:#F1F5F9;">💳 Keuangan</h2>', unsafe_allow_html=True)
    tab_trx, tab_bgt, tab_cmp = st.tabs(["📋 Transaksi","🚨 Budget Monitor","📅 Perbandingan Bulan"])

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
                    if f_jen=="Pemasukan": st.balloons()
                    st.cache_data.clear(); st.rerun()

            st.markdown('<div class="sec"><span class="sec-txt">⚡ Tagihan 1-Klik</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
            with st.expander("Bayar tagihan rutin bulanan"):
                with st.form("bills_v3"):
                    cb_kost=st.checkbox("🏠 Kost — Rp 400.000")
                    cb_inet=st.checkbox("🌐 Kuota — Rp 100.000")
                    cb_kopi=st.checkbox("☕ Kopi 1KG — Rp 200.000")
                    sb_src2=st.selectbox("Bayar via:", list(porto.keys()))
                    if st.form_submit_button("✅ BAYAR SEKARANG", use_container_width=True):
                        nr2=[]; ts=now.strftime('%Y-%m-%d %H:%M:%S')
                        if cb_kost: nr2.append({"Tanggal":ts,"Kategori":"Kost","Jenis":"Pengeluaran","Sumber Dana":sb_src2,"Nominal":400000.0,"Catatan":"Auto-Kost"})
                        if cb_inet: nr2.append({"Tanggal":ts,"Kategori":"Kuota Internet","Jenis":"Pengeluaran","Sumber Dana":sb_src2,"Nominal":100000.0,"Catatan":"Auto-Kuota"})
                        if cb_kopi: nr2.append({"Tanggal":ts,"Kategori":"Kebutuhan Pokok & Beras","Jenis":"Pengeluaran","Sumber Dana":sb_src2,"Nominal":200000.0,"Catatan":"Auto-Kopi"})
                        if nr2:
                            df_up=pd.concat([df_t,pd.DataFrame(nr2)],ignore_index=True)
                            df_up['Tanggal']=pd.to_datetime(df_up['Tanggal']).apply(fmt_tgl_sheet)
                            set_with_dataframe(ws_t,df_up); st.success("✅ Tersimpan!"); st.cache_data.clear(); st.rerun()

        with c_list:
            st.markdown('<div class="sec"><span class="sec-txt">🔍 Riwayat & Filter</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
            sc1,sc2,sc3=st.columns([2,1,1])
            with sc1: q=st.text_input("Cari...",placeholder="Kategori, catatan, atau nominal",label_visibility="collapsed")
            with sc2: fil_jen=st.selectbox("Jenis",["Semua","Pemasukan","Pengeluaran"],label_visibility="collapsed")
            with sc3: fil_kat=st.selectbox("Kat",["Semua"]+st.session_state.kategori_list,label_visibility="collapsed")
            sd1,sd2=st.columns(2)
            with sd1: date_from=st.date_input("Dari",value=now.replace(day=1).date(),label_visibility="collapsed")
            with sd2: date_to=st.date_input("Sampai",value=now.date(),label_visibility="collapsed")
            if not df_t.empty:
                df_f=df_t.copy()
                df_f['Jenis']=df_f['Jenis'].astype(str).str.strip().str.capitalize()
                df_f['Kategori']=df_f['Kategori'].astype(str).str.strip().str.title()
                df_f=df_f[(df_f['Tanggal'].dt.date>=date_from)&(df_f['Tanggal'].dt.date<=date_to)]
                if fil_jen!="Semua": df_f=df_f[df_f['Jenis']==fil_jen]
                if fil_kat!="Semua": df_f=df_f[df_f['Kategori']==fil_kat]
                if q:
                    mask=(df_f['Kategori'].str.contains(q,case=False,na=False)|
                          df_f.get('Catatan',pd.Series()).astype(str).str.contains(q,case=False,na=False)|
                          df_f['Nominal'].astype(str).str.contains(q,case=False,na=False))
                    df_f=df_f[mask]
                df_f=df_f.sort_values('Tanggal',ascending=False).reset_index()
                df_f['ID_Asli']=df_f['index']; df_f.index=range(1,len(df_f)+1)
                st.markdown(f'<p style="font-size:10.5px;color:#1E293B;margin-bottom:5px;">{len(df_f)} transaksi · Out: <span style="color:#F87171;">{fmt(df_f[df_f["Jenis"]=="Pengeluaran"]["Nominal"].sum())}</span> · In: <span style="color:#34D399;">{fmt(df_f[df_f["Jenis"]=="Pemasukan"]["Nominal"].sum())}</span></p>', unsafe_allow_html=True)
                df_show=df_f[['Tanggal','Kategori','Jenis','Sumber Dana','Nominal','Catatan']].copy()
                df_show['Tanggal']=df_show['Tanggal'].apply(lambda x:pd.to_datetime(x).strftime('%Y-%m-%d') if pd.notna(x) else "")
                df_show['Nominal']=df_show['Nominal'].apply(fmt)
                df_show=df_show.reset_index(); df_show.rename(columns={'index':'No'},inplace=True)
                fmt_tbl(df_show)
                st.download_button("📥 Download CSV", data=df_t.to_csv(index=False).encode('utf-8'), file_name="ROGER_Transaksi.csv", mime="text/csv")
                st.markdown('<div class="sec"><span class="sec-txt">✏️ Edit / Hapus</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
                pilih_no=st.selectbox("Pilih No. Transaksi:",[None]+list(df_f.index),key="edit_no_v3")
                if pilih_no:
                    row=df_f.loc[pilih_no]; idx_asli=row['ID_Asli']
                    dt_obj=pd.to_datetime(df_t.loc[idx_asli,'Tanggal'])
                    with st.form("form_edit_v3"):
                        e1,e2,e3=st.columns(3)
                        with e1:
                            ed_tgl=st.date_input("Tanggal",dt_obj.date())
                            try: ei=st.session_state.kategori_list.index(row['Kategori'])
                            except: ei=0
                            ed_kat=st.selectbox("Kategori",st.session_state.kategori_list,index=ei)
                        with e2:
                            ed_jen=st.selectbox("Jenis",["Pemasukan","Pengeluaran"],index=0 if str(row['Jenis']).lower()=="pemasukan" else 1)
                            ed_src=st.selectbox("Sumber",list(porto.keys()),index=list(porto.keys()).index(row['Sumber Dana']) if row['Sumber Dana'] in porto else 0)
                        with e3:
                            ed_nom=st.number_input("Nominal",value=float(row['Nominal']),step=10000.0)
                            ed_note=st.text_input("Catatan",value=str(row.get('Catatan','')))
                        sb_u,sb_d=st.columns(2)
                        with sb_u: btn_upd=st.form_submit_button("💾 UPDATE",use_container_width=True)
                        with sb_d: btn_del=st.form_submit_button("🗑️ HAPUS", use_container_width=True)
                        if btn_upd:
                            tgl_f=ed_tgl.strftime('%Y-%m-%d') if dt_obj.hour==0 else f"{ed_tgl.strftime('%Y-%m-%d')} {dt_obj.strftime('%H:%M:%S')}"
                            df_t.at[idx_asli,'Tanggal']=tgl_f; df_t.at[idx_asli,'Kategori']=ed_kat
                            df_t.at[idx_asli,'Jenis']=ed_jen; df_t.at[idx_asli,'Sumber Dana']=ed_src
                            df_t.at[idx_asli,'Nominal']=ed_nom; df_t.at[idx_asli,'Catatan']=ed_note
                            df_t['Tanggal']=pd.to_datetime(df_t['Tanggal']).apply(fmt_tgl_sheet)
                            ws_t.clear(); set_with_dataframe(ws_t,df_t); st.success("✅ Diperbarui!"); st.cache_data.clear(); st.rerun()
                        if btn_del:
                            df_upd=df_t.drop(idx_asli); df_upd['Tanggal']=pd.to_datetime(df_upd['Tanggal']).apply(fmt_tgl_sheet)
                            ws_t.clear(); set_with_dataframe(ws_t,df_upd); st.error("🗑️ Dihapus."); st.cache_data.clear(); st.rerun()
            else: st.info("Belum ada transaksi.")

    with tab_bgt:
        b2=st.selectbox("Bulan:",NAMA_BULAN[1:],index=now.month-1,key="bgt_b")
        bln2=NAMA_BULAN.index(b2)
        df_bgt=pd.DataFrame()
        if not df_t.empty:
            db2=df_t.copy(); db2['Jenis']=db2['Jenis'].str.lower().str.strip(); db2['Kategori']=db2['Kategori'].str.strip().str.title()
            df_bgt=db2[(db2['Tanggal'].dt.month==bln2)&(db2['Tanggal'].dt.year==now.year)]
        spent_bgt=df_bgt[df_bgt['Jenis']=='pengeluaran'].groupby('Kategori')['Nominal'].sum().to_dict() if not df_bgt.empty else {}
        cols_bgt=st.columns(min(len(st.session_state.budgets),4))
        for i,(kat,lim) in enumerate(st.session_state.budgets.items()):
            terpakai=spent_bgt.get(str(kat).strip().title(),0.0); rasio_b=min(terpakai/lim,1.0) if lim>0 else 1.0
            sisa=lim-terpakai; bc=("#34D399" if rasio_b<0.5 else "#FBBF24" if rasio_b<0.85 else "#F87171")
            ico=("🟢" if rasio_b<0.5 else "🟡" if rasio_b<0.85 else "🔴")
            with cols_bgt[i%4]:
                st.markdown(f'<div class="bgt-card"><div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="font-size:11px;font-weight:700;color:#475569;">{ico} {kat}</span><span style="font-size:11px;color:{bc};font-weight:800;">{rasio_b*100:.0f}%</span></div><div style="font-size:13px;font-weight:800;color:#F1F5F9;">{fmt(terpakai)}</div><div class="bar-track"><div class="bar-fill" style="width:{rasio_b*100:.0f}%;background:{bc};"></div></div><div style="font-size:11px;margin-top:5px;color:{"#34D399" if sisa>=0 else "#F87171"};font-weight:600;">{"Sisa: "+fmt(sisa) if sisa>=0 else "⚠️ Over: "+fmt(abs(sisa))}</div><div style="font-size:9.5px;color:#0F172A;">Limit: {fmt(lim)}</div></div>', unsafe_allow_html=True)

    with tab_cmp:
        cc1,cc2=st.columns(2)
        with cc1: bn_c=NAMA_BULAN.index(st.selectbox("Bulan Ini:",NAMA_BULAN[1:],index=now.month-1,key="cmp_c"))
        with cc2: bn_p=NAMA_BULAN.index(st.selectbox("Banding Dengan:",NAMA_BULAN[1:],index=max(0,now.month-2),key="cmp_p"))
        def get_md(bi):
            if df_t.empty: return pd.DataFrame(),0.0,0.0
            dc=df_t.copy(); dc['Jenis']=dc['Jenis'].str.lower().str.strip(); dc['Kategori']=dc['Kategori'].str.strip().str.title()
            dm=dc[(dc['Tanggal'].dt.month==bi)&(dc['Tanggal'].dt.year==now.year)]
            return dm, dm[dm['Jenis']=='pemasukan']['Nominal'].sum(), dm[dm['Jenis']=='pengeluaran']['Nominal'].sum()
        dm_c,inc,outc=get_md(bn_c); dm_p,inp,outp=get_md(bn_p)
        bn_cn=NAMA_BULAN[bn_c]; bn_pn=NAMA_BULAN[bn_p]
        cp1,cp2,cp3,cp4=st.columns(4)
        cp1.metric(f"In {bn_cn}",fmt(inc),delta=fmt(inc-inp) if inp>0 else None)
        cp2.metric(f"Out {bn_cn}",fmt(outc),delta=fmt(outc-outp) if outp>0 else None,delta_color="inverse")
        cp3.metric(f"In {bn_pn}",fmt(inp))
        cp4.metric(f"Out {bn_pn}",fmt(outp))
        st.markdown("<br>",unsafe_allow_html=True)
        if not dm_c.empty or not dm_p.empty:
            all_k=list(set(
                (dm_c[dm_c['Jenis']=='pengeluaran']['Kategori'].unique().tolist() if not dm_c.empty else [])+
                (dm_p[dm_p['Jenis']=='pengeluaran']['Kategori'].unique().tolist() if not dm_p.empty else [])
            ))
            sc_c=dm_c[dm_c['Jenis']=='pengeluaran'].groupby('Kategori')['Nominal'].sum().to_dict() if not dm_c.empty else {}
            sp_c=dm_p[dm_p['Jenis']=='pengeluaran'].groupby('Kategori')['Nominal'].sum().to_dict() if not dm_p.empty else {}
            max_v=max([max(sc_c.values(),default=0),max(sp_c.values(),default=0)],default=1)
            st.markdown('<div class="sec"><span class="sec-txt">📊 Perbandingan Per Kategori</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
            for kat in sorted(all_k):
                cv=sc_c.get(kat,0); pv=sp_c.get(kat,0)
                cv_p=min((cv/max_v)*100,100) if max_v>0 else 0
                pv_p=min((pv/max_v)*100,100) if max_v>0 else 0
                diff=cv-pv; dc_=("#F87171" if diff>0 else "#34D399" if diff<0 else "#475569")
                st.markdown(f'<div style="margin-bottom:12px;"><div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="font-size:12px;font-weight:700;color:#475569;">{kat}</span><span style="font-size:11px;font-weight:700;color:{dc_};">{"+" if diff>0 else ""}{fmt(diff) if diff!=0 else "Sama"}</span></div><div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;"><span style="font-size:9.5px;color:#1E293B;width:60px;flex-shrink:0;">{bn_cn[:3]}</span><div style="flex:1;background:#040810;border-radius:8px;height:6px;"><div style="width:{cv_p:.0f}%;height:100%;border-radius:8px;background:#38BDF8;"></div></div><span style="font-size:9.5px;color:#334155;width:85px;text-align:right;">{fmt(cv)}</span></div><div style="display:flex;align-items:center;gap:6px;"><span style="font-size:9.5px;color:#1E293B;width:60px;flex-shrink:0;">{bn_pn[:3]}</span><div style="flex:1;background:#040810;border-radius:8px;height:6px;"><div style="width:{pv_p:.0f}%;height:100%;border-radius:8px;background:#8B5CF6;"></div></div><span style="font-size:9.5px;color:#334155;width:85px;text-align:right;">{fmt(pv)}</span></div></div>', unsafe_allow_html=True)
            df_chart_cmp=pd.DataFrame({'Kategori':all_k,bn_cn:[sc_c.get(k,0) for k in all_k],bn_pn:[sp_c.get(k,0) for k in all_k]}).sort_values(bn_cn,ascending=False).head(10)
            fig_cmp=go.Figure()
            fig_cmp.add_trace(go.Bar(name=bn_cn,x=df_chart_cmp['Kategori'],y=df_chart_cmp[bn_cn],marker_color='#38BDF8'))
            fig_cmp.add_trace(go.Bar(name=bn_pn,x=df_chart_cmp['Kategori'],y=df_chart_cmp[bn_pn],marker_color='#8B5CF6'))
            fig_cmp.update_layout(barmode='group',template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',height=300,margin=dict(l=0,r=0,t=10,b=0),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            fig_cmp.update_xaxes(showgrid=False); fig_cmp.update_yaxes(showgrid=True,gridcolor='#080F1E',title=None)
            st.plotly_chart(fig_cmp,use_container_width=True)
        else: st.info("Belum ada data untuk kedua bulan.")


# ══════════════════════════════════════════
#  10. PAGE — PORTOFOLIO
# ══════════════════════════════════════════
def page_portofolio():
    st.markdown('<h2 style="font-size:21px;font-weight:900;color:#F1F5F9;">📈 Portofolio Saham</h2>', unsafe_allow_html=True)
    c_add,c_sell=st.columns(2)
    with c_add:
        with st.expander("➕ Tambah Pembelian"):
            with st.form("beli_v3",clear_on_submit=True):
                nt=st.text_input("Ticker (akhiri .JK untuk IDX)").upper()
                nl=st.number_input("Lot Dibeli",min_value=1,step=1)
                nh=st.text_input("Harga Beli/Lembar (Rp)")
                if st.form_submit_button("💾 Simpan",use_container_width=True):
                    try: nhv=float(nh.replace(".","").replace(",","")) if nh else 0.0
                    except: nhv=0.0
                    if nt:
                        df_up=pd.concat([df_s,pd.DataFrame([{"Ticker":nt.strip(),"Jumlah Lembar":nl*100,"Harga Beli":nhv}])],ignore_index=True)
                        set_with_dataframe(ws_s,df_up); st.success(f"✅ {nt}!"); st.cache_data.clear(); st.rerun()
    with c_sell:
        with st.expander("➖ Catat Penjualan"):
            if not df_s_agg.empty:
                with st.form("jual_v3",clear_on_submit=True):
                    tj=st.selectbox("Pilih Saham",df_s_agg['Ticker'].tolist())
                    lj=st.number_input("Lot Dijual",min_value=1,step=1)
                    if st.form_submit_button("📤 Catat",use_container_width=True):
                        df_up=pd.concat([df_s,pd.DataFrame([{"Ticker":tj,"Jumlah Lembar":-lj*100,"Harga Beli":0}])],ignore_index=True)
                        set_with_dataframe(ws_s,df_up); st.success("✅ Dicatat!"); st.cache_data.clear(); st.rerun()
            else: st.info("Portofolio kosong.")

    st.markdown("<br>",unsafe_allow_html=True)
    if not df_s_agg.empty:
        rows_sk=[]; tm_all=tn_all=0.0
        for _,r in df_s_agg.iterrows():
            t=str(r['Ticker']); hb=float(r['Avg Beli']); lb=float(r['Jumlah Lembar'])
            hs=harga_dict.get(t,hb)
            if pd.isna(hs) or hs==0: hs=hb
            tm=hb*lb; tn=hs*lb; tm_all+=tm; tn_all+=tn
            rows_sk.append({"t":t,"hb":hb,"hs":hs,"lb":lb,"tm":tm,"tn":tn,"gain":tn-tm,"pct":((hs-hb)/hb*100) if hb>0 else 0})
        tg_rp=tn_all-tm_all; tg_pct=(tg_rp/tm_all*100) if tm_all>0 else 0; gc2="#34D399" if tg_rp>=0 else "#F87171"
        st.markdown(f'<div class="banner"><div class="bitem"><div class="blbl">Total Modal</div><div class="bval" style="color:#64748B;">{fmt(tm_all)}</div></div><div class="divider-v"></div><div class="bitem"><div class="blbl">Nilai Kini</div><div class="bval" style="color:#38BDF8;">{fmt(tn_all)}</div></div><div class="bitem"><div class="blbl">Total G/L</div><div class="bval" style="color:{gc2};">{"+" if tg_rp>=0 else ""}{fmt(tg_rp)} ({tg_pct:+.2f}%)</div></div><div style="margin-left:auto;" class="bitem"><div class="blbl">Emiten</div><div class="bval" style="color:#475569;">{len(rows_sk)}</div></div></div>', unsafe_allow_html=True)
        cols_sk=st.columns(min(len(rows_sk),3))
        for i,s in enumerate(rows_sk):
            badge="gl-pos" if s['pct']>0 else "gl-neg" if s['pct']<0 else "gl-neu"
            arr="▲" if s['pct']>0 else "▼" if s['pct']<0 else "—"
            bc3=("rgba(16,185,129,.12)" if s['pct']>0 else "rgba(239,68,68,.12)" if s['pct']<0 else "#080F1E")
            with cols_sk[i%3]:
                st.markdown(f'<div class="sk-card" style="border-color:{"rgba(16,185,129,.12)" if s["pct"]>0 else "rgba(239,68,68,.12)" if s["pct"]<0 else "#0A1020"}"><div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;"><div><div class="sk-ticker">{s["t"]}</div><div style="font-size:10.5px;color:#1E293B;">{s["lb"]/100:.0f} lot</div></div><span class="{badge}">{arr} {abs(s["pct"]):.2f}%</span></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;"><div class="mini-stat"><div class="ms-lbl">Avg Beli</div><div style="font-size:13px;font-weight:800;color:#475569;">{fmt(s["hb"])}</div></div><div class="mini-stat"><div class="ms-lbl">Harga Kini</div><div style="font-size:13px;font-weight:800;color:#F1F5F9;">{fmt(s["hs"])}</div></div><div class="mini-stat"><div class="ms-lbl">Modal</div><div style="font-size:13px;font-weight:800;color:#334155;">{fmt(s["tm"])}</div></div><div class="mini-stat"><div class="ms-lbl">Gain/Loss</div><div style="font-size:13px;font-weight:800;color:{"#34D399" if s["gain"]>=0 else "#F87171"};">{"+" if s["gain"]>=0 else ""}{fmt(s["gain"])}</div></div></div></div><br>', unsafe_allow_html=True)
        if rows_sk:
            with st.expander("📊 Alokasi Portofolio"):
                pie_d=[{"Ticker":s["t"],"Nilai":s["tn"]} for s in rows_sk if s["tn"]>0]
                if pie_d:
                    fig_sk_pie=px.pie(pd.DataFrame(pie_d),values='Nilai',names='Ticker',hole=0.5,template="plotly_dark")
                    fig_sk_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)',height=280,margin=dict(t=10,b=10,l=10,r=10))
                    st.plotly_chart(fig_sk_pie,use_container_width=True)

    st.markdown('<div class="sec"><span class="sec-txt">🤖 Grafik + Prediksi AI</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
    target_tk=st.text_input("Ticker:","BBCA.JK",key="tk_porto").upper()
    try:
        h=yf.Ticker(target_tk).history(period="6mo")
        if not h.empty:
            h.index=h.index.tz_localize(None)
            fig_c=go.Figure(data=[go.Candlestick(x=h.index,open=h['Open'],high=h['High'],low=h['Low'],close=h['Close'],increasing_line_color='#10B981',decreasing_line_color='#EF4444')])
            if len(h)>=50:
                h['SMA20']=ta.sma(h['Close'],length=20); h['SMA50']=ta.sma(h['Close'],length=50)
                fig_c.add_trace(go.Scatter(x=h.index,y=h['SMA20'],line=dict(color='#38BDF8',width=1.5),name='MA20'))
                fig_c.add_trace(go.Scatter(x=h.index,y=h['SMA50'],line=dict(color='#F59E0B',width=1.5),name='MA50'))
                df_ml=h[['Close']].copy(); df_ml['Hari']=np.arange(len(df_ml))
                mdl=LinearRegression().fit(df_ml[['Hari']],df_ml['Close'])
                ld=df_ml['Hari'].max(); fd=pd.bdate_range(h.index[-1]+timedelta(days=1),periods=10)
                yp=mdl.predict(pd.DataFrame({'Hari':np.arange(ld+1,ld+11)}))
                fig_c.add_trace(go.Scatter(x=[h.index[-1]]+list(fd),y=[float(df_ml['Close'].iloc[-1])]+list(yp),mode='lines+markers',line=dict(color='#C084FC',width=2.5,dash='dot'),name='Prediksi AI (10H)'))
            fig_c.update_layout(template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',height=400,xaxis_rangeslider_visible=False,margin=dict(l=0,r=0,t=10,b=0),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            fig_c.update_xaxes(showgrid=False); fig_c.update_yaxes(showgrid=True,gridcolor='#080F1E')
            st.plotly_chart(fig_c,use_container_width=True)
            if len(h)>=15:
                rv=ta.rsi(h['Close'],length=14).iloc[-1]; rc="#F87171" if rv>=70 else "#34D399" if rv<=30 else "#FBBF24"
                ri,ri_inf=st.columns([1,3])
                with ri: st.markdown(f'<div style="text-align:center;padding:14px;background:rgba(4,8,15,.9);border:1px solid #0A1020;border-radius:12px;"><div style="font-size:9px;color:#0F172A;text-transform:uppercase;letter-spacing:1px;font-weight:800;">RSI-14</div><div style="font-size:30px;font-weight:900;color:{rc};">{rv:.1f}</div><div style="font-size:10px;color:{rc};font-weight:700;">{"🔴 Overbought" if rv>=70 else "🟢 Oversold" if rv<=30 else "🟡 Netral"}</div></div>', unsafe_allow_html=True)
                with ri_inf: st.info("🤖 **Prediksi AI Aktif** — Garis ungu putus-putus adalah proyeksi regresi linier 10 hari ke depan. Selalu kombinasikan dengan analisis fundamental sebelum memutuskan investasi.")
    except Exception as e: st.error(f"Gagal memuat grafik: {e}")


# ══════════════════════════════════════════
#  11. PAGE — AI ADVISOR
# ══════════════════════════════════════════
def page_ai_advisor():
    st.markdown('<h2 style="font-size:21px;font-weight:900;color:#F1F5F9;">🤖 AI Financial Advisor</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#1E293B;font-size:12.5px;margin-bottom:14px;">Chat langsung dengan ROGER AI yang mengetahui kondisi keuangan kamu secara real-time.</p>', unsafe_allow_html=True)
    if not ANTHROPIC_OK:
        st.error("Package `anthropic` belum terinstall. Tambahkan ke requirements.txt."); return
    try:
        api_key=st.secrets.get("ANTHROPIC_API_KEY","")
        if not api_key: st.warning("⚠️ `ANTHROPIC_API_KEY` belum ada di Streamlit Secrets."); return
    except: st.warning("Konfigurasi secrets belum lengkap."); return

    def build_ctx():
        lines=["Kamu adalah ROGER AI, asisten keuangan pribadi yang cerdas dan berbahasa Indonesia.",
               "Gunakan data di bawah sebagai referensi utama jawaban. Jawab singkat, padat, gunakan angka konkret dan emoji.",
               "","== SALDO ==",f"Net Worth: {fmt(total_net)}",f"BCA: {fmt(porto['BCA'])}",f"BRI: {fmt(porto['BRI'])}",
               f"Bank Jago: {fmt(porto['Bank Jago'])}",f"Cash: {fmt(porto['Dompet (Cash)'])}",f"Saham: {fmt(total_saham)}",""]
        if not df_t.empty:
            dc=df_t.copy(); dc['Jenis']=dc['Jenis'].str.lower().str.strip(); dc['Kategori']=dc['Kategori'].str.strip().str.title()
            dm=dc[(dc['Tanggal'].dt.month==now.month)&(dc['Tanggal'].dt.year==now.year)]
            inn=dm[dm['Jenis']=='pemasukan']['Nominal'].sum(); outn=dm[dm['Jenis']=='pengeluaran']['Nominal'].sum()
            lines+=[f"== BULAN INI ({NAMA_BULAN[now.month]}) ==",f"Pemasukan: {fmt(inn)}",f"Pengeluaran: {fmt(outn)}",f"Sisa: {fmt(inn-outn)}"]
            tp5=dm[dm['Jenis']=='pengeluaran'].groupby('Kategori')['Nominal'].sum().nlargest(5)
            if not tp5.empty: lines+=["Top Pengeluaran:"]+[f"  - {k}: {fmt(v)}" for k,v in tp5.items()]
        lines+=["","== BUDGET =="]+[f"  - {k}: limit {fmt(v)}" for k,v in st.session_state.budgets.items()]
        lines+=["","== SAHAM =="]
        if not df_s_agg.empty:
            for _,r in df_s_agg.iterrows():
                hs2=harga_dict.get(r['Ticker'],r['Avg Beli']); gl2=((hs2-r['Avg Beli'])/r['Avg Beli']*100) if r['Avg Beli']>0 else 0
                lines.append(f"  - {r['Ticker']}: {r['Jumlah Lembar']/100:.0f}lot, beli {fmt(r['Avg Beli'])}, kini {fmt(hs2)}, G/L:{gl2:+.1f}%")
        else: lines.append("  Tidak ada saham.")
        return "\n".join(lines)

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg['role'],avatar="🤖" if msg['role']=="assistant" else "👤"):
            st.markdown(msg['content'])

    if not st.session_state.chat_messages:
        st.markdown('<div class="sec"><span class="sec-txt">💬 Pertanyaan Cepat</span><div class="sec-line"></div></div>', unsafe_allow_html=True)
        sug=["📊 Bagaimana kondisi keuanganku bulan ini?","💡 Di mana pengeluaran yang bisa dikurangi?",
             "🌱 Berapa idealnya aku investasikan bulan ini?","📈 Saham mana yang performanya terbaik?",
             "🎯 Seberapa jauh dari target net worth?","💳 Rekening mana yang paling banyak dipakai?"]
        sc=st.columns(3)
        for i,s in enumerate(sug):
            with sc[i%3]:
                if st.button(s,use_container_width=True,key=f"sg_{i}"):
                    st.session_state.chat_messages.append({"role":"user","content":s}); st.rerun()

    if prompt:=st.chat_input("Tanya sesuatu tentang keuanganmu..."):
        st.session_state.chat_messages.append({"role":"user","content":prompt})
        with st.chat_message("user",avatar="👤"): st.markdown(prompt)
        with st.chat_message("assistant",avatar="🤖"):
            with st.spinner("ROGER AI sedang menganalisis..."):
                try:
                    client=anthropic.Anthropic(api_key=api_key)
                    hist=[{"role":m['role'],"content":m['content']} for m in st.session_state.chat_messages]
                    resp=client.messages.create(model="claude-sonnet-4-20250514",max_tokens=1000,system=build_ctx(),messages=hist)
                    ans=resp.content[0].text
                    st.markdown(ans); st.session_state.chat_messages.append({"role":"assistant","content":ans})
                except Exception as e:
                    err=f"❌ Gagal: {e}"; st.error(err); st.session_state.chat_messages.append({"role":"assistant","content":err})

    if st.session_state.chat_messages:
        if st.button("🗑️ Hapus Riwayat Chat"): st.session_state.chat_messages=[]; st.rerun()


# ══════════════════════════════════════════
#  12. PAGE — REKOMENDASI SAHAM HARIAN
# ══════════════════════════════════════════
def page_rekomendasi():
    st.markdown('<h2 style="font-size:21px;font-weight:900;color:#F1F5F9;">⭐ Rekomendasi Saham Murah Harian</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#1E293B;font-size:12px;margin-bottom:14px;"><span class="live-dot"></span>Auto-refresh setiap hari · {now.strftime("%d %b %Y")}</p>', unsafe_allow_html=True)

    fc1,fc2,fc3=st.columns(3)
    with fc1: max_harga=st.number_input("Harga Max/Lembar (Rp)",value=1000,step=100)
    with fc2: min_vol=st.number_input("Min Avg Volume (juta lembar)",value=5,step=1)
    with fc3: min_score=st.slider("Min Skor",0,100,45)

    IDX_WL=["GOTO.JK","BUMI.JK","BRPT.JK","ELSA.JK","PTBA.JK","ANTM.JK","TINS.JK","SMGR.JK","WIKA.JK","WSKT.JK",
            "TOTL.JK","SIDO.JK","EXCL.JK","ISAT.JK","TLKM.JK","INKP.JK","TKIM.JK","INDY.JK","ADRO.JK","ITMG.JK",
            "HRUM.JK","PTPP.JK","WTON.JK","ACST.JK","JSMR.JK","PGAS.JK","ERAA.JK","MNCN.JK","BSDE.JK","SMRA.JK",
            "CTRA.JK","LPKR.JK","DILD.JK","APLN.JK","ASRI.JK","MDLN.JK","EMTK.JK","KIJA.JK","SSIA.JK","NRCA.JK",
            "BNGA.JK","MAYA.JK","BBTN.JK","BJTM.JK","BNII.JK","BTPS.JK","BDMN.JK","PNBN.JK","NISP.JK","BBRI.JK"]

    cache_today=str(now.date())
    all_recs=st.session_state.daily_recs_cache if (st.session_state.daily_recs_cache and st.session_state.daily_recs_date==cache_today) else None

    if st.button("🔄  REFRESH REKOMENDASI",use_container_width=False) or all_recs is None:
        prog=st.progress(0); prog_txt=st.empty(); all_recs=[]
        for ix,ticker in enumerate(IDX_WL):
            prog.progress((ix+1)/len(IDX_WL))
            prog_txt.markdown(f'<span style="font-size:11px;color:#1E293B;">Menganalisis {ticker}...</span>',unsafe_allow_html=True)
            try:
                h=yf.Ticker(ticker).history(period="3mo")
                if len(h)<30: continue
                close=float(h['Close'].iloc[-1])
                if close>max_harga: continue
                vol_avg=float(h['Volume'][-20:].mean())
                if vol_avg<min_vol*1_000_000: continue
                h.index=h.index.tz_localize(None)
                h['SMA20']=ta.sma(h['Close'],length=20); h['SMA50']=ta.sma(h['Close'],length=50)
                h['RSI']=ta.rsi(h['Close'],length=14)
                atr_df=ta.atr(h['High'],h['Low'],h['Close'],length=14)
                macd_df=ta.macd(h['Close'])
                sma20=float(h['SMA20'].iloc[-1]) if not pd.isna(h['SMA20'].iloc[-1]) else close
                sma50=float(h['SMA50'].iloc[-1]) if not pd.isna(h['SMA50'].iloc[-1]) else close
                rsi=float(h['RSI'].iloc[-1]) if not pd.isna(h['RSI'].iloc[-1]) else 50
                atr=float(atr_df.iloc[-1]) if atr_df is not None and not pd.isna(atr_df.iloc[-1]) else close*0.03
                vol_t=float(h['Volume'].iloc[-1])
                ml=float(macd_df.iloc[-1,0]); ms=float(macd_df.iloc[-1,2]); mh=float(macd_df.iloc[-1,1])
                tp1=close+1.5*atr; tp2=close+2.5*atr; sl=close-1.0*atr
                score=0; signals=[]
                if rsi<35:     score+=30; signals.append(f"📉 RSI Oversold {rsi:.1f}")
                elif rsi<50:   score+=15; signals.append(f"⚖️ RSI Netral {rsi:.1f}")
                if sma20>sma50: score+=25; signals.append("📈 Golden Cross MA20>MA50")
                if ml>ms and mh>0: score+=25; signals.append("📊 MACD Bullish")
                if vol_t>vol_avg*1.5: score+=20; signals.append(f"🔥 Vol Spike {vol_t/vol_avg:.1f}x")
                if close<sma20*0.95: score+=15; signals.append("💎 Di bawah MA20")
                if score<min_score: continue
                rr=(tp1-close)/(close-sl) if (close-sl)>0 else 0
                status_r="STRONG BUY" if score>=75 else "BUY" if score>=50 else "WATCH"
                all_recs.append({"ticker":ticker,"close":close,"tp1":tp1,"tp2":tp2,"sl":sl,"rsi":rsi,"score":score,
                    "status":status_r,"signals":signals,"rr":rr,"atr":atr,
                    "tp1_pct":(tp1-close)/close*100,"tp2_pct":(tp2-close)/close*100,"sl_pct":(sl-close)/close*100,"df":h.tail(60)})
            except: pass
        all_recs.sort(key=lambda x:x['score'],reverse=True)
        st.session_state.daily_recs_cache=all_recs; st.session_state.daily_recs_date=cache_today
        prog.empty(); prog_txt.empty()

    if all_recs:
        sb_cnt=sum(1 for r in all_recs if r['status']=='STRONG BUY')
        buy_cnt=sum(1 for r in all_recs if r['status']=='BUY')
        st.markdown(f'<div class="banner"><div class="bitem"><div class="blbl">Dianalisis</div><div class="bval" style="color:#64748B;">{len(IDX_WL)}</div></div><div class="divider-v"></div><div class="bitem"><div class="blbl">Lolos Filter</div><div class="bval" style="color:#38BDF8;">{len(all_recs)}</div></div><div class="bitem"><div class="blbl">Strong Buy</div><div class="bval" style="color:#34D399;">{sb_cnt}</div></div><div class="bitem"><div class="blbl">Buy/Cicil</div><div class="bval" style="color:#38BDF8;">{buy_cnt}</div></div><div class="bitem"><div class="blbl">Max Harga</div><div class="bval" style="color:#475569;">Rp {max_harga:,}</div></div></div>', unsafe_allow_html=True)

        for rec in all_recs:
            sc_m={"STRONG BUY":"st-strong","BUY":"st-buy","WATCH":"st-wait"}.get(rec['status'],"st-wait")
            lb_m={"STRONG BUY":"🟢 STRONG BUY","BUY":"🟢 BUY / CICIL","WATCH":"🟡 PANTAU"}.get(rec['status'],rec['status'])
            st.markdown(f"""
            <div class="rec-card">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
                <div><span class="sk-ticker" style="font-size:20px;">{rec['ticker']}</span><span style="margin-left:8px;color:#334155;font-family:'JetBrains Mono',monospace;font-size:14px;">Rp {rec['close']:,.0f}</span></div>
                <div style="display:flex;flex-direction:column;align-items:flex-end;gap:5px;"><span class="{sc_m}">{lb_m}</span><span style="font-size:10px;color:#1E293B;font-weight:700;">Skor {rec['score']}/100</span></div>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:7px;margin-bottom:12px;">
                <div class="mini-stat"><div class="ms-lbl">TP 1</div><div style="font-size:13px;font-weight:900;color:#34D399;">Rp {rec['tp1']:,.0f}</div><div style="font-size:9.5px;color:#34D399;">+{rec['tp1_pct']:.1f}%</div></div>
                <div class="mini-stat"><div class="ms-lbl">TP 2</div><div style="font-size:13px;font-weight:900;color:#22C55E;">Rp {rec['tp2']:,.0f}</div><div style="font-size:9.5px;color:#22C55E;">+{rec['tp2_pct']:.1f}%</div></div>
                <div class="mini-stat"><div class="ms-lbl">Stop Loss</div><div style="font-size:13px;font-weight:900;color:#F87171;">Rp {rec['sl']:,.0f}</div><div style="font-size:9.5px;color:#F87171;">{rec['sl_pct']:.1f}%</div></div>
                <div class="mini-stat"><div class="ms-lbl">RSI · R:R</div><div style="font-size:13px;font-weight:900;color:#FBBF24;">{rec['rsi']:.1f}</div><div style="font-size:9.5px;color:#475569;">{rec['rr']:.1f}x</div></div>
              </div>
              <div style="display:flex;gap:5px;flex-wrap:wrap;">{''.join([f"<span style='background:#040810;border:1px solid #0A1020;border-radius:5px;padding:2px 9px;font-size:10.5px;color:#475569;'>{sg}</span>" for sg in rec['signals']])}</div>
            </div>""", unsafe_allow_html=True)

            dfp=rec['df']
            fig_r=go.Figure()
            fig_r.add_trace(go.Candlestick(x=dfp.index,open=dfp['Open'],high=dfp['High'],low=dfp['Low'],close=dfp['Close'],increasing_line_color='#10B981',decreasing_line_color='#EF4444',name='Harga'))
            if 'SMA20' in dfp.columns: fig_r.add_trace(go.Scatter(x=dfp.index,y=dfp['SMA20'],line=dict(color='#38BDF8',width=1.5),name='MA20'))
            if 'SMA50' in dfp.columns: fig_r.add_trace(go.Scatter(x=dfp.index,y=dfp['SMA50'],line=dict(color='#F59E0B',width=1.5),name='MA50'))
            fig_r.add_hline(y=rec['tp1'],line=dict(color='#34D399',dash='dot',width=1),annotation_text="TP1",annotation_font_color="#34D399",annotation_position="top right")
            fig_r.add_hline(y=rec['tp2'],line=dict(color='#22C55E',dash='dot',width=1),annotation_text="TP2",annotation_font_color="#22C55E",annotation_position="top right")
            fig_r.add_hline(y=rec['sl'], line=dict(color='#F87171',dash='dot',width=1),annotation_text="SL", annotation_font_color="#F87171",annotation_position="bottom right")
            fig_r.update_layout(template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',height=320,xaxis_rangeslider_visible=False,margin=dict(l=0,r=0,t=10,b=0),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1,font=dict(size=10)))
            fig_r.update_xaxes(showgrid=False); fig_r.update_yaxes(showgrid=True,gridcolor='#080F1E')
            st.plotly_chart(fig_r,use_container_width=True)
            st.markdown('<hr>',unsafe_allow_html=True)
    else:
        st.info("Tidak ada saham yang memenuhi kriteria. Coba longgarkan filter.")


# ══════════════════════════════════════════
#  13. PAGE — SCREENER
# ══════════════════════════════════════════
def page_screener():
    st.markdown('<h2 style="font-size:21px;font-weight:900;color:#F1F5F9;">⚡ Live Technical Screener</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#1E293B;font-size:12px;margin-bottom:14px;">Masukkan daftar ticker, klik scan — AI akan memberikan sinyal beli/jual dengan TP & SL berbasis ATR.</p>', unsafe_allow_html=True)

    wl_input = st.text_area("Daftar Ticker (pisah koma):", "GOTO.JK, BUMI.JK, BBCA.JK, PNLF.JK, ANTM.JK, TLKM.JK", height=70)
    sc_c1, sc_c2 = st.columns([1,1])
    with sc_c1: max_p = st.number_input("Batas Harga Max (0 = tanpa batas)", value=0)
    with sc_c2: st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🔍  MULAI ANALISA TEKNIKAL", use_container_width=False):
        tickers = [t.strip().upper() for t in wl_input.split(",") if t.strip()]
        results = []; prog2 = st.progress(0)
        for ik, ticker in enumerate(tickers):
            prog2.progress((ik+1)/len(tickers))
            try:
                h = yf.Ticker(ticker).history(period="6mo")
                if len(h) < 50: continue
                h.index = h.index.tz_localize(None)
                close = float(h['Close'].iloc[-1])
                if max_p > 0 and close > max_p: continue
                h['SMA20'] = ta.sma(h['Close'],length=20); h['SMA50'] = ta.sma(h['Close'],length=50)
                h['RSI']   = ta.rsi(h['Close'],length=14)
                atr_s = ta.atr(h['High'],h['Low'],h['Close'],length=14)
                macd_s = ta.macd(h['Close'])
                sma20 = float(h['SMA20'].iloc[-1]); sma50 = float(h['SMA50'].iloc[-1])
                rsi_v = float(h['RSI'].iloc[-1])
                atr_v = float(atr_s.iloc[-1]) if atr_s is not None else close*0.03
                ml2 = float(macd_s.iloc[-1,0]); ms2 = float(macd_s.iloc[-1,2]); mh2 = float(macd_s.iloc[-1,1])
                vol_avg2 = float(h['Volume'][-20:].mean()); vol_t2 = float(h['Volume'].iloc[-1])
                tp1_s = close+1.5*atr_v; tp2_s = close+2.5*atr_v; sl_s = close-1.0*atr_v
                alasan_s = []; is_buy_s = False; score_s = 0
                if rsi_v<35:     alasan_s.append(f"📉 RSI Oversold {rsi_v:.1f}"); is_buy_s=True; score_s+=30
                elif rsi_v<=70:  alasan_s.append(f"⚖️ RSI Netral {rsi_v:.1f}")
                if sma20>sma50:  alasan_s.append("📈 MA Uptrend"); is_buy_s=True; score_s+=25
                if ml2>ms2 and mh2>0: alasan_s.append("📊 MACD Bullish"); is_buy_s=True; score_s+=25
                if vol_t2>vol_avg2*1.5: alasan_s.append(f"🔥 Vol {vol_t2/vol_avg2:.1f}x"); score_s+=20
                rr_s = (tp1_s-close)/(close-sl_s) if (close-sl_s)>0 else 0
                if rsi_v>=70: status_s="SELL"
                elif score_s>=75 and is_buy_s: status_s="STRONG BUY"
                elif is_buy_s: status_s="BUY"
                else: status_s="WAIT"
                results.append({"ticker":ticker,"close":close,"tp1":tp1_s,"tp2":tp2_s,"sl":sl_s,"rsi":rsi_v,
                    "score":score_s,"status":status_s,"alasan":alasan_s,"rr":rr_s,
                    "tp1_pct":(tp1_s-close)/close*100,"sl_pct":(sl_s-close)/close*100,"df":h.tail(90)})
            except: pass
        prog2.empty()

        if results:
            for rec in sorted(results,key=lambda x:x['score'],reverse=True):
                sc2 = {"STRONG BUY":"st-strong","BUY":"st-buy","WAIT":"st-wait","SELL":"st-sell"}.get(rec['status'],"st-wait")
                lb2 = {"STRONG BUY":"🟢 STRONG BUY","BUY":"🟢 BUY","WAIT":"🟡 WAIT","SELL":"🔴 SELL"}.get(rec['status'],rec['status'])
                st.markdown(f"""
                <div class="rec-card">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
                    <div><span class="sk-ticker" style="font-size:19px;">{rec['ticker']}</span><span style="margin-left:8px;color:#1E293B;font-family:'JetBrains Mono',monospace;font-size:13px;">Rp {rec['close']:,.0f}</span></div>
                    <span class="{sc2}">{lb2}</span>
                  </div>
                  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-bottom:12px;">
                    <div class="mini-stat"><div class="ms-lbl">TP1 / TP2</div>
                      <div style="font-size:12.5px;font-weight:900;color:#34D399;">Rp {rec['tp1']:,.0f}</div>
                      <div style="font-size:11px;font-weight:700;color:#22C55E;">Rp {rec['tp2']:,.0f}</div>
                    </div>
                    <div class="mini-stat"><div class="ms-lbl">Stop Loss</div>
                      <div style="font-size:12.5px;font-weight:900;color:#F87171;">Rp {rec['sl']:,.0f}</div>
                      <div style="font-size:10px;color:#F87171;">{rec['sl_pct']:.1f}%</div>
                    </div>
                    <div class="mini-stat"><div class="ms-lbl">RSI · R:R</div>
                      <div style="font-size:12.5px;font-weight:900;color:#FBBF24;">{rec['rsi']:.1f}</div>
                      <div style="font-size:10px;color:#475569;">{rec['rr']:.1f}x</div>
                    </div>
                  </div>
                  <div style="display:flex;gap:5px;flex-wrap:wrap;">
                    {''.join([f"<span style='background:#040810;border:1px solid #0A1020;border-radius:5px;padding:2px 8px;font-size:10.5px;color:#475569;'>{a}</span>" for a in rec['alasan']])}
                  </div>
                </div>""", unsafe_allow_html=True)

                df_sc = rec['df']
                fig_sc2 = go.Figure()
                fig_sc2.add_trace(go.Candlestick(x=df_sc.index,open=df_sc['Open'],high=df_sc['High'],low=df_sc['Low'],close=df_sc['Close'],increasing_line_color='#10B981',decreasing_line_color='#EF4444'))
                if 'SMA20' in df_sc.columns: fig_sc2.add_trace(go.Scatter(x=df_sc.index,y=df_sc['SMA20'],line=dict(color='#38BDF8',width=1.5),name='MA20'))
                if 'SMA50' in df_sc.columns: fig_sc2.add_trace(go.Scatter(x=df_sc.index,y=df_sc['SMA50'],line=dict(color='#F59E0B',width=1.5),name='MA50'))
                fig_sc2.add_hline(y=rec['tp1'],line=dict(color='#34D399',dash='dot',width=1),annotation_text="TP1",annotation_font_color="#34D399",annotation_position="top right")
                fig_sc2.add_hline(y=rec['tp2'],line=dict(color='#22C55E',dash='dot',width=1),annotation_text="TP2",annotation_font_color="#22C55E",annotation_position="top right")
                fig_sc2.add_hline(y=rec['sl'], line=dict(color='#F87171',dash='dot',width=1),annotation_text="SL", annotation_font_color="#F87171",annotation_position="bottom right")
                fig_sc2.update_layout(template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',height=320,xaxis_rangeslider_visible=False,margin=dict(l=0,r=0,t=10,b=0),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1,font=dict(size=10)))
                fig_sc2.update_xaxes(showgrid=False); fig_sc2.update_yaxes(showgrid=True,gridcolor='#080F1E')
                st.plotly_chart(fig_sc2,use_container_width=True)
                st.markdown('<hr>', unsafe_allow_html=True)
        else:
            st.info("Tidak ada saham yang memenuhi kriteria saat ini.")


# ══════════════════════════════════════════
#  14. PAGE — SCANNER NOTA
# ══════════════════════════════════════════
def page_scanner():
    st.markdown('<h2 style="font-size:21px;font-weight:900;color:#F1F5F9;">🧾 AI Smart Scanner</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#1E293B;font-size:12.5px;margin-bottom:16px;">Upload foto struk belanja — AI akan otomatis membaca total dan siap mengisi form transaksi.</p>', unsafe_allow_html=True)

    if st.session_state.scan_status:
        status_sc, val_sc, raw_sc = st.session_state.scan_status
        if status_sc == "success":
            st.markdown(f"""
            <div style="background:rgba(16,185,129,.05);border:1px solid rgba(16,185,129,.14);border-radius:13px;padding:15px 18px;margin-bottom:14px;">
              <div style="font-size:10px;color:#34D399;font-weight:800;text-transform:uppercase;letter-spacing:1.2px;">✨ Scan Berhasil</div>
              <div style="font-size:26px;font-weight:900;color:#F1F5F9;margin-top:4px;">{fmt(val_sc)}</div>
              <div style="font-size:11.5px;color:#1E293B;margin-top:3px;">Nominal sudah disalin. Buka halaman <b>Keuangan</b> → form Tambah Transaksi untuk menyimpan.</div>
            </div>""", unsafe_allow_html=True)
            with st.expander("🔍 Lihat Raw OCR Text"):
                st.text_area("", raw_sc, height=120, label_visibility="collapsed")
        else:
            st.warning("⚠️ AI tidak menemukan total yang valid. Silakan input manual.")
            with st.expander("🔍 Raw OCR Text"):
                st.text_area("", raw_sc, height=120, label_visibility="collapsed")

    up = st.file_uploader("Upload Foto Nota (JPG / PNG / JPEG)", type=["jpg","jpeg","png"])
    if up:
        col_img, col_res = st.columns([1, 1.5])
        with col_img:
            st.image(Image.open(up), use_container_width=True, caption="Preview Struk")
        with col_res:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🧠  EKSTRAK TOTAL OTOMATIS", use_container_width=True):
                with st.spinner("AI memindai struk..."):
                    try:
                        res_text = pytesseract.image_to_string(Image.open(up))
                        if res_text.strip():
                            lines2 = res_text.lower().split('\n')
                            poss = []
                            for line in lines2:
                                if any(kw in line for kw in ['total','jumlah','amount','bayar','tagihan','rp']):
                                    nums = re.findall(r'\d{1,3}(?:[.,]\d{3})*', line)
                                    for n in nums:
                                        nc = re.sub(r'[^\d]','',n)
                                        if nc: poss.append(float(nc))
                            if not poss:
                                all_n = re.findall(r'\d{1,3}(?:[.,]\d{3})*', res_text)
                                poss  = [float(re.sub(r'[^\d]','',n)) for n in all_n if re.sub(r'[^\d]','',n)]
                            total_sc = max(poss) if poss else 0.0
                            if total_sc > 0:
                                st.session_state.auto_nominal = f"{total_sc:,.0f}".replace(",",".")
                                st.session_state.scan_status  = ("success", total_sc, res_text)
                            else:
                                st.session_state.scan_status  = ("fail", 0, res_text)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error OCR: Pastikan 'tesseract-ocr' ada di packages.txt. Detail: {e}")


# ══════════════════════════════════════════
#  15. PAGE — PENGATURAN
# ══════════════════════════════════════════
def page_pengaturan():
    st.markdown('<h2 style="font-size:21px;font-weight:900;color:#F1F5F9;">⚙️ Pengaturan Sistem</h2>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    with c1:
        with st.expander("🏷️ Kelola Kategori Transaksi", expanded=True):
            nk = st.text_input("Nama Kategori Baru", placeholder="Contoh: Bensin")
            if st.button("➕ Tambah Kategori", use_container_width=True):
                if nk and nk not in st.session_state.kategori_list:
                    st.session_state.kategori_list.append(nk); save_config()
                    st.success(f"✅ '{nk}' ditambahkan!"); st.rerun()
                elif nk in st.session_state.kategori_list:
                    st.warning("Kategori sudah ada.")
            st.markdown("<br>", unsafe_allow_html=True)
            hk = st.selectbox("Hapus kategori:", st.session_state.kategori_list, key="hk_set")
            if st.button("❌ Hapus Kategori", use_container_width=True):
                if len(st.session_state.kategori_list) > 1:
                    st.session_state.kategori_list.remove(hk); save_config()
                    st.success(f"✅ '{hk}' dihapus!"); st.rerun()
                else:
                    st.error("Minimal 1 kategori harus tersisa.")
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:10px;color:#1E293B;margin-bottom:6px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">{len(st.session_state.kategori_list)} Kategori Aktif</div>', unsafe_allow_html=True)
            for k in st.session_state.kategori_list:
                st.markdown(f'<span style="display:inline-block;margin:2px;padding:3px 9px;background:#040810;border:1px solid #0A1020;border-radius:999px;font-size:11px;color:#334155;">{k}</span>', unsafe_allow_html=True)

    with c2:
        with st.expander("🚨 Atur Limit Budget", expanded=True):
            kb = st.selectbox("Kategori Budget:", st.session_state.kategori_list, key="kb_set")
            lb = st.number_input("Limit per Bulan (Rp)", min_value=0, step=25000, value=500000)
            if st.button("💾 Simpan Limit", use_container_width=True):
                st.session_state.budgets[kb] = lb; save_config()
                st.success("✅ Limit disimpan!"); st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)
            if st.session_state.budgets:
                st.markdown('<div style="font-size:10px;color:#1E293B;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Alarm Budget Aktif</div>', unsafe_allow_html=True)
                for kat, lim in st.session_state.budgets.items():
                    st.markdown(f'<div style="display:flex;justify-content:space-between;padding:6px 10px;background:#040810;border:1px solid #0A1020;border-radius:8px;margin-bottom:4px;"><span style="font-size:11px;color:#475569;">{kat}</span><span style="font-size:11px;font-weight:800;color:#FBBF24;">{fmt(lim)}</span></div>', unsafe_allow_html=True)
                bh = st.selectbox("Hapus alarm:", list(st.session_state.budgets.keys()), key="bh_set")
                if st.button("🗑️ Hapus Alarm", use_container_width=True):
                    del st.session_state.budgets[bh]; save_config()
                    st.success("✅ Alarm dihapus!"); st.rerun()
            else:
                st.info("Belum ada alarm aktif.")

    with c3:
        with st.expander("🔐 Keamanan & PIN", expanded=True):
            op  = st.text_input("PIN Lama", type="password", max_chars=6)
            np1 = st.text_input("PIN Baru (6 angka)", type="password", max_chars=6)
            np2 = st.text_input("Konfirmasi PIN Baru", type="password", max_chars=6)
            if st.button("🔑 Ubah PIN Sekarang", use_container_width=True):
                if op != st.session_state.saved_pin:
                    st.error("❌ PIN lama salah.")
                elif len(np1) != 6 or not np1.isdigit():
                    st.error("❌ PIN baru harus 6 digit angka.")
                elif np1 != np2:
                    st.error("❌ Konfirmasi PIN tidak cocok.")
                else:
                    st.session_state.saved_pin = np1; save_config()
                    st.success("✅ PIN berhasil diubah!")

            st.markdown(f"""
            <div style="margin-top:14px;background:#040810;border:1px solid #0A1020;border-radius:11px;padding:12px 14px;">
              <div style="font-size:9.5px;color:#0F172A;font-weight:800;text-transform:uppercase;letter-spacing:1.2px;margin-bottom:8px;">Info Sesi Aktif</div>
              <div style="font-size:11.5px;color:#475569;margin-bottom:3px;">Sesi: <span style="color:#34D399;font-weight:700;">✅ Aktif</span></div>
              <div style="font-size:11.5px;color:#475569;margin-bottom:3px;">Proteksi: <span style="color:#34D399;font-weight:700;">🔐 PIN 6-Digit</span></div>
              <div style="font-size:11.5px;color:#475569;margin-bottom:3px;">Login: <span style="color:#64748B;">{now.strftime('%H:%M WIB')}</span></div>
              <div style="font-size:11.5px;color:#475569;">Versi: <span style="color:#38BDF8;font-weight:700;">ROGER Finance v3.0</span></div>
            </div>""", unsafe_allow_html=True)

        with st.expander("🗄️ Manajemen Data"):
            st.markdown('<p style="font-size:12px;color:#334155;">Refresh cache data dari Google Sheets secara manual.</p>', unsafe_allow_html=True)
            if st.button("🔄 Refresh Cache Data", use_container_width=True):
                st.cache_data.clear(); st.success("✅ Cache dikosongkan! Halaman akan reload."); st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#040810;border:1px solid #0A1020;border-radius:11px;padding:12px 14px;">
              <div style="font-size:9.5px;color:#0F172A;font-weight:800;text-transform:uppercase;letter-spacing:1.2px;margin-bottom:8px;">Statistik Database</div>
              <div style="font-size:11.5px;color:#475569;margin-bottom:3px;">Total Transaksi: <span style="color:#38BDF8;font-weight:700;">{len(df_t) if not df_t.empty else 0}</span></div>
              <div style="font-size:11.5px;color:#475569;margin-bottom:3px;">Total Baris Saham: <span style="color:#8B5CF6;font-weight:700;">{len(df_s) if not df_s.empty else 0}</span></div>
              <div style="font-size:11.5px;color:#475569;">Emiten di Porto: <span style="color:#F59E0B;font-weight:700;">{len(df_s_agg) if not df_s_agg.empty else 0}</span></div>
            </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════
#  16. ROUTER — Render Page
# ══════════════════════════════════════════
PAGE_MAP = {
    "Dashboard":    page_dashboard,
    "Keuangan":     page_keuangan,
    "Portofolio":   page_portofolio,
    "AI Advisor":   page_ai_advisor,
    "Rekomendasi":  page_rekomendasi,
    "Screener":     page_screener,
    "Scanner":      page_scanner,
    "Pengaturan":   page_pengaturan,
}

fn = PAGE_MAP.get(st.session_state.page, page_dashboard)
fn()
