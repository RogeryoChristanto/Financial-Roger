import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
import pytesseract
from PIL import Image
from datetime import timedelta
import json
import os
import gspread
import re
import numpy as np
from sklearn.linear_model import LinearRegression
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="ROGER Finance", page_icon="💎", layout="wide")

if 'hide_balance' not in st.session_state:
    st.session_state.hide_balance = False

# ==========================================
# 1A. SISTEM PENYIMPANAN PENGATURAN (JSON)
# ==========================================
CONFIG_FILE = "roger_config_v2.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "budgets": {
            "Makan & Minum": 900000,
            "Kebutuhan Mandi": 150000,
            "Kebutuhan Pokok & Beras": 300000,
            "Ngopi & Nongkrong": 250000,
            "Transportasi": 100000,
            "Laundry": 100000,
            "Skincare": 325000
        },
        "kategori_list": [
            "Uang Saku Bulanan", "Dividen", "Bayar Kost", "Makan & Minum",
            "Transportasi", "Kuota Internet", "Kebutuhan Mandi",
            "Kebutuhan Pokok & Beras", "Ngopi & Nongkrong", "Olahraga",
            "Jajan & Camilan", "Laundry", "Kost", "Skincare", "Investasi"
        ],
        "saved_pin": "120224"
    }

def save_config():
    config_data = {
        "budgets": st.session_state.budgets,
        "kategori_list": st.session_state.kategori_list,
        "saved_pin": st.session_state.saved_pin
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f)

config = load_config()

if 'budgets' not in st.session_state:
    st.session_state.budgets = config["budgets"]
if 'kategori_list' not in st.session_state:
    st.session_state.kategori_list = config["kategori_list"]
if 'saved_pin' not in st.session_state:
    st.session_state.saved_pin = config["saved_pin"]

def format_currency(value):
    if st.session_state.hide_balance:
        return "Rp ••••••••"
    return f"Rp {value:,.0f}".replace(",", ".")

def render_beautiful_table(df):
    html_table = df.to_html(classes='custom-table', index=False, escape=False)
    st.markdown(f'<div class="table-wrapper">{html_table}</div>', unsafe_allow_html=True)

# ==========================================
# 2. DESAIN "AURORA MIDNIGHT" — CSS PREMIUM
# ==========================================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    header, footer { visibility: hidden !important; }

    /* ── Base ── */
    .stApp, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif !important;
        background: #060D1A !important;
        color: #F1F5F9 !important;
    }
    [data-testid="stSidebar"] { background: #0B1525 !important; }

    /* ── Aurora Background Glow ── */
    .stApp::before {
        content: '';
        position: fixed; top: -200px; left: -200px;
        width: 600px; height: 600px;
        background: radial-gradient(circle, rgba(56,189,248,0.06) 0%, transparent 70%);
        pointer-events: none; z-index: 0;
    }
    .stApp::after {
        content: '';
        position: fixed; bottom: -200px; right: -200px;
        width: 700px; height: 700px;
        background: radial-gradient(circle, rgba(139,92,246,0.05) 0%, transparent 70%);
        pointer-events: none; z-index: 0;
    }

    /* ── Logo / Title ── */
    .app-logo {
        font-size: clamp(32px, 5vw, 48px);
        font-weight: 900;
        text-align: center;
        background: linear-gradient(135deg, #38BDF8 0%, #818CF8 50%, #C084FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -2px;
        margin-bottom: 4px;
    }
    .app-subtitle {
        text-align: center;
        font-size: 13px;
        color: #475569;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 30px;
    }

    /* ── Section Headers ── */
    h1, h2, h3 { color: #F1F5F9 !important; }
    .section-title {
        font-size: 16px; font-weight: 700;
        color: #94A3B8; text-transform: uppercase;
        letter-spacing: 1.5px; margin: 20px 0 12px 0;
        display: flex; align-items: center; gap: 8px;
    }
    .section-title::after {
        content: ''; flex: 1;
        height: 1px; background: #1E293B;
    }

    /* ── Glassmorphism Card ── */
    .glass-card {
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .glass-card:hover {
        border-color: rgba(56,189,248,0.2);
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.4);
    }

    /* ── Wallet Cards ── */
    .wallet-container {
        display: flex; gap: 14px;
        overflow-x: auto; padding: 8px 4px 20px 4px;
        scrollbar-width: none;
    }
    .wallet-container::-webkit-scrollbar { display: none; }

    .wallet-card {
        min-width: 220px; flex: 1;
        padding: 22px 20px; border-radius: 20px;
        position: relative; overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: default;
    }
    .wallet-card::before {
        content: ''; position: absolute;
        inset: 0; opacity: 0.06;
        background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    }
    .wallet-card:hover { transform: translateY(-5px) scale(1.01); }

    .bca-card  { background: linear-gradient(135deg, #1a3a6c 0%, #0f2244 100%); border: 1px solid rgba(59,130,246,0.3); box-shadow: 0 4px 20px rgba(59,130,246,0.15); }
    .bri-card  { background: linear-gradient(135deg, #6b2a0a 0%, #431a05 100%); border: 1px solid rgba(249,115,22,0.3); box-shadow: 0 4px 20px rgba(249,115,22,0.15); }
    .jago-card { background: linear-gradient(135deg, #6b4c00 0%, #3d2d00 100%); border: 1px solid rgba(245,158,11,0.3); box-shadow: 0 4px 20px rgba(245,158,11,0.15); }
    .cash-card { background: linear-gradient(135deg, #064e3b 0%, #022c22 100%); border: 1px solid rgba(16,185,129,0.3); box-shadow: 0 4px 20px rgba(16,185,129,0.15); }

    .wallet-icon  { font-size: 28px; margin-bottom: 14px; }
    .wallet-label { font-size: 10px; font-weight: 700; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px; }
    .wallet-balance { font-size: 24px; font-weight: 800; color: #fff; letter-spacing: -0.5px; text-shadow: 0 2px 8px rgba(0,0,0,0.3); }
    .wallet-chip { position: absolute; top: 16px; right: 16px; width: 32px; height: 24px; border-radius: 4px; background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.15); }

    /* ── Metric Containers ── */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.9) 100%);
        border: 1px solid #1E293B;
        border-radius: 16px; padding: 20px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        transition: all 0.2s ease;
    }
    div[data-testid="metric-container"]:hover { border-color: #334155; }
    [data-testid="stMetricValue"]  { font-size: 1.8rem !important; font-weight: 800 !important; color: #F1F5F9 !important; }
    [data-testid="stMetricLabel"]  { font-size: 11px !important; font-weight: 600 !important; color: #64748B !important; text-transform: uppercase; letter-spacing: 1px; }
    [data-testid="stMetricDelta"]  { font-size: 13px !important; font-weight: 600 !important; }

    /* ── Colored Metric Borders ── */
    div[data-testid="metric-container"]:nth-child(1) { border-top: 3px solid #38BDF8; }
    div[data-testid="metric-container"]:nth-child(2) { border-top: 3px solid #10B981; }
    div[data-testid="metric-container"]:nth-child(3) { border-top: 3px solid #8B5CF6; }

    /* ── Table ── */
    .table-wrapper {
        background: rgba(15,23,42,0.8);
        border: 1px solid #1E293B; border-radius: 16px;
        overflow: auto; max-height: 380px;
        margin-bottom: 16px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    }
    .table-wrapper::-webkit-scrollbar { width: 6px; height: 6px; }
    .table-wrapper::-webkit-scrollbar-track { background: transparent; }
    .table-wrapper::-webkit-scrollbar-thumb { background: #1E293B; border-radius: 10px; }

    .custom-table { width: 100%; border-collapse: collapse; color: #CBD5E1; font-size: 13px; }
    .custom-table thead th {
        position: sticky; top: 0; z-index: 1;
        background: #070E1B;
        padding: 12px 16px; font-weight: 600;
        color: #475569; text-transform: uppercase;
        letter-spacing: 0.8px; font-size: 11px;
        border-bottom: 1px solid #1E293B;
    }
    .custom-table td { padding: 12px 16px; border-bottom: 1px solid #0F172A; vertical-align: middle; }
    .custom-table tbody tr:hover td { background: rgba(56,189,248,0.03); }
    .custom-table tbody tr:last-of-type td { border-bottom: none; }

    /* ── Tabs ── */
    [data-testid="stTabs"] div[data-baseweb="tab-list"] {
        gap: 4px; padding-bottom: 12px;
        border-bottom: 1px solid #1E293B;
        background: transparent;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"] {
        background: transparent; border-radius: 10px;
        padding: 10px 18px; font-weight: 600;
        font-size: 13px; color: #475569;
        border: 1px solid transparent;
        transition: all 0.2s ease;
    }
    [data-testid="stTabs"] button[data-baseweb="tab"]:hover {
        color: #94A3B8; background: rgba(30,41,59,0.5);
    }
    [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, rgba(56,189,248,0.12), rgba(139,92,246,0.12));
        color: #38BDF8;
        border: 1px solid rgba(56,189,248,0.2);
    }
    [data-testid="stTabs"] div[data-baseweb="tab-highlight"] { display: none; }

    /* ── Buttons ── */
    .stButton button {
        background: linear-gradient(135deg, #0EA5E9, #6366F1) !important;
        color: #fff !important;
        font-weight: 700 !important; font-size: 13px !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 11px 22px !important;
        transition: all 0.25s cubic-bezier(0.4,0,0.2,1) !important;
        box-shadow: 0 4px 15px rgba(14,165,233,0.25) !important;
        letter-spacing: 0.3px !important;
    }
    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(14,165,233,0.35) !important;
        background: linear-gradient(135deg, #38BDF8, #818CF8) !important;
    }
    .stButton button:active { transform: translateY(0px) !important; }

    /* ── Danger Button (hapus) ── */
    .danger-btn .stButton button {
        background: linear-gradient(135deg, #DC2626, #9F1239) !important;
        box-shadow: 0 4px 15px rgba(220,38,38,0.25) !important;
    }
    .danger-btn .stButton button:hover {
        box-shadow: 0 8px 25px rgba(220,38,38,0.4) !important;
        background: linear-gradient(135deg, #EF4444, #BE123C) !important;
    }

    /* ── Input Fields ── */
    .stTextInput input, .stNumberInput input,
    .stSelectbox div[data-baseweb="select"],
    .stTextArea textarea, .stDateInput input {
        background: rgba(15,23,42,0.9) !important;
        border: 1px solid #1E293B !important;
        border-radius: 10px !important;
        color: #F1F5F9 !important;
        font-size: 14px !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 0 2px rgba(56,189,248,0.15) !important;
    }
    .stTextInput label, .stNumberInput label,
    .stSelectbox label, .stTextArea label,
    .stDateInput label, .stFileUploader label { color: #64748B !important; font-size: 12px !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.5px; }

    /* ── Radio (Segmented) ── */
    div[role="radiogroup"] { gap: 8px !important; margin-top: 6px !important; }
    div[role="radiogroup"] > label {
        background: rgba(15,23,42,0.8) !important;
        border: 1px solid #1E293B !important;
        padding: 10px 18px !important; border-radius: 10px !important;
        transition: all 0.2s !important; cursor: pointer !important;
    }
    div[role="radiogroup"] > label:hover { border-color: #334155 !important; }
    div[role="radiogroup"] > label > div:first-child { display: none !important; }
    div[role="radiogroup"] > label:nth-child(1):has(input:checked) {
        background: rgba(16,185,129,0.1) !important;
        border-color: #10B981 !important;
    }
    div[role="radiogroup"] > label:nth-child(1):has(input:checked) p { color: #34D399 !important; font-weight: 700 !important; }
    div[role="radiogroup"] > label:nth-child(2):has(input:checked) {
        background: rgba(239,68,68,0.1) !important;
        border-color: #EF4444 !important;
    }
    div[role="radiogroup"] > label:nth-child(2):has(input:checked) p { color: #F87171 !important; font-weight: 700 !important; }

    /* ── Progress Bar ── */
    .stProgress > div > div { background: linear-gradient(90deg, #38BDF8, #818CF8) !important; border-radius: 10px !important; }
    .stProgress > div { background: #1E293B !important; border-radius: 10px !important; }

    /* ── Alert / Info ── */
    .stInfo, [data-baseweb="notification"] { background: rgba(56,189,248,0.06) !important; border: 1px solid rgba(56,189,248,0.15) !important; border-radius: 12px !important; }
    .stSuccess { background: rgba(16,185,129,0.06) !important; border: 1px solid rgba(16,185,129,0.2) !important; border-radius: 12px !important; }
    .stError   { background: rgba(239,68,68,0.06) !important; border: 1px solid rgba(239,68,68,0.2) !important; border-radius: 12px !important; }
    .stWarning { background: rgba(245,158,11,0.06) !important; border: 1px solid rgba(245,158,11,0.2) !important; border-radius: 12px !important; }

    /* ── Expander ── */
    [data-testid="stExpander"] {
        background: rgba(15,23,42,0.6) !important;
        border: 1px solid #1E293B !important;
        border-radius: 14px !important;
    }
    [data-testid="stExpander"] summary { color: #94A3B8 !important; font-weight: 600 !important; }

    /* ── Financial Health Score Widget ── */
    .health-score-ring {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center;
    }
    .score-badge {
        display: inline-flex; align-items: center; gap: 8px;
        padding: 6px 16px; border-radius: 999px;
        font-size: 12px; font-weight: 700;
        letter-spacing: 0.5px;
        margin-top: 8px;
    }
    .score-excellent { background: rgba(16,185,129,0.12); color: #34D399; border: 1px solid rgba(16,185,129,0.2); }
    .score-good      { background: rgba(56,189,248,0.12); color: #38BDF8; border: 1px solid rgba(56,189,248,0.2); }
    .score-fair      { background: rgba(245,158,11,0.12); color: #FBBF24; border: 1px solid rgba(245,158,11,0.2); }
    .score-poor      { background: rgba(239,68,68,0.12); color: #F87171; border: 1px solid rgba(239,68,68,0.2); }

    /* ── Budget Bar Card ── */
    .budget-card {
        background: rgba(15,23,42,0.7);
        border: 1px solid #1E293B;
        border-radius: 14px; padding: 14px 16px;
        margin-bottom: 10px;
        transition: border-color 0.2s;
    }
    .budget-card:hover { border-color: #334155; }

    /* ── Quick Amount Chip ── */
    .quick-chip {
        display: inline-block; padding: 5px 12px;
        background: rgba(30,41,59,0.8); border: 1px solid #1E293B;
        border-radius: 999px; font-size: 12px;
        color: #94A3B8; cursor: pointer;
        transition: all 0.2s; margin: 3px;
    }
    .quick-chip:hover { background: rgba(56,189,248,0.1); border-color: #38BDF8; color: #38BDF8; }

    /* ── Today Summary Banner ── */
    .today-banner {
        background: linear-gradient(135deg, rgba(14,165,233,0.08), rgba(139,92,246,0.08));
        border: 1px solid rgba(56,189,248,0.12);
        border-radius: 16px; padding: 16px 20px;
        display: flex; gap: 24px; align-items: center;
        margin-bottom: 16px; flex-wrap: wrap;
    }
    .today-item { display: flex; flex-direction: column; }
    .today-label { font-size: 10px; color: #475569; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .today-value { font-size: 18px; font-weight: 800; margin-top: 2px; }
    .today-in   { color: #34D399; }
    .today-out  { color: #F87171; }
    .today-net  { color: #38BDF8; }

    /* ── Saham P&L Card ── */
    .saham-card {
        background: rgba(15,23,42,0.8);
        border-radius: 14px; padding: 16px 18px;
        border: 1px solid #1E293B;
        transition: all 0.2s;
    }
    .saham-card:hover { border-color: #334155; transform: translateY(-1px); }
    .saham-ticker { font-size: 18px; font-weight: 800; color: #F1F5F9; }
    .saham-lot    { font-size: 12px; color: #64748B; font-weight: 600; }
    .gain-badge   { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 13px; font-weight: 700; }
    .gain-pos { background: rgba(16,185,129,0.12); color: #34D399; border: 1px solid rgba(16,185,129,0.2); }
    .gain-neg { background: rgba(239,68,68,0.12); color: #F87171; border: 1px solid rgba(239,68,68,0.2); }
    .gain-neu { background: rgba(100,116,139,0.12); color: #94A3B8; border: 1px solid rgba(100,116,139,0.2); }

    /* ── Screener Result Card ── */
    .screener-card {
        background: rgba(15,23,42,0.85);
        border: 1px solid #1E293B;
        border-radius: 18px; padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
        transition: all 0.2s;
    }
    .screener-card:hover { border-color: #334155; }
    .screener-ticker { font-size: 22px; font-weight: 900; color: #F1F5F9; }
    .screener-price  { font-size: 16px; font-weight: 600; color: #64748B; }
    .status-buy      { background: rgba(16,185,129,0.12); color: #34D399; border: 1px solid rgba(16,185,129,0.25); padding: 4px 14px; border-radius: 999px; font-weight: 700; font-size: 13px; }
    .status-strong   { background: rgba(56,189,248,0.12); color: #38BDF8; border: 1px solid rgba(56,189,248,0.25); padding: 4px 14px; border-radius: 999px; font-weight: 700; font-size: 13px; }
    .status-wait     { background: rgba(245,158,11,0.12); color: #FBBF24; border: 1px solid rgba(245,158,11,0.25); padding: 4px 14px; border-radius: 999px; font-weight: 700; font-size: 13px; }
    .status-sell     { background: rgba(239,68,68,0.12); color: #F87171; border: 1px solid rgba(239,68,68,0.25); padding: 4px 14px; border-radius: 999px; font-weight: 700; font-size: 13px; }

    /* ── PIN Keypad ── */
    div[data-testid="stElementContainer"]:has(#keypad-marker) + div[data-testid="stHorizontalBlock"] {
        display: flex !important; flex-direction: row !important;
        flex-wrap: nowrap !important; justify-content: center !important;
        gap: 10px !important;
    }
    div[data-testid="stElementContainer"]:has(#keypad-marker) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        width: 33.33% !important; min-width: 33.33% !important;
    }
    div[data-testid="stElementContainer"]:has(#keypad-marker) + div[data-testid="stHorizontalBlock"] button {
        height: 64px !important; font-size: 22px !important;
        border-radius: 14px !important; padding: 0 !important;
        background: rgba(30,41,59,0.8) !important;
        color: #F1F5F9 !important;
        border: 1px solid #1E293B !important;
        box-shadow: none !important;
    }
    div[data-testid="stElementContainer"]:has(#keypad-marker) + div[data-testid="stHorizontalBlock"] button:hover {
        background: rgba(56,189,248,0.1) !important;
        border-color: rgba(56,189,248,0.3) !important;
        transform: none !important;
    }

    /* ── Vitals Bar ── */
    .vitals-card {
        background: rgba(15,23,42,0.75);
        padding: 16px 18px; border-radius: 14px;
        border: 1px solid #1E293B; margin-bottom: 10px;
        transition: border-color 0.2s;
    }
    .vitals-card:hover { border-color: #334155; }
    .vitals-bar-track { width:100%; background:#0F172A; border-radius:10px; height:10px; margin-top: 10px; }
    .vitals-bar-fill  { height:100%; border-radius:10px; transition: width 0.8s cubic-bezier(0.4,0,0.2,1); }

    /* ── Checkbox ── */
    [data-testid="stCheckbox"] label { color: #94A3B8 !important; font-weight: 500 !important; }

    /* ── Scrollbar (global) ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #1E293B; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #334155; }

    /* ── Decoration ── */
    [data-testid="stDecoration"] { display: none; }
    hr { border-color: #1E293B !important; margin: 20px 0 !important; }

    /* ── Responsive ── */
    @media (max-width: 768px) {
        [data-testid="stTabs"] div[data-baseweb="tab-list"] {
            overflow-x: auto !important; scrollbar-width: none !important;
        }
        [data-testid="stTabs"] button[data-baseweb="tab"] { flex: 0 0 auto !important; padding: 8px 14px !important; }
        .wallet-card { min-width: 75vw !important; }
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# SISTEM LOGIN — KEYPAD PIN
# ==========================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'pin_input' not in st.session_state:
    st.session_state.pin_input = ""

if not st.session_state.authenticated:
    st.markdown("""<style>[data-testid="collapsedControl"] { display: none; }</style>""", unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col_mid, _ = st.columns([1, 1.1, 1])

    with col_mid:
        # Logo + Judul
        st.markdown('<div class="app-logo">ROGER</div>', unsafe_allow_html=True)
        st.markdown('<div class="app-subtitle">Personal Finance Dashboard</div>', unsafe_allow_html=True)

        # PIN Dots
        pin_len = len(st.session_state.pin_input)
        dots_html = '<div style="display:flex; justify-content:center; gap:14px; margin-bottom:28px;">'
        for i in range(6):
            if i < pin_len:
                dots_html += '<div style="width:14px; height:14px; border-radius:50%; background:linear-gradient(135deg,#38BDF8,#818CF8); box-shadow:0 0 10px rgba(56,189,248,0.5);"></div>'
            else:
                dots_html += '<div style="width:14px; height:14px; border-radius:50%; background:#0F172A; border:2px solid #1E293B;"></div>'
        dots_html += '</div>'
        st.markdown(dots_html, unsafe_allow_html=True)

        if pin_len == 6:
            if st.session_state.pin_input == st.session_state.saved_pin:
                st.session_state.authenticated = True
                st.session_state.pin_input = ""
                st.rerun()
            else:
                st.markdown('<p style="text-align:center; color:#F87171; font-weight:600;">❌ PIN Salah. Coba lagi.</p>', unsafe_allow_html=True)
                if st.button("Ulangi", use_container_width=True):
                    st.session_state.pin_input = ""
                    st.rerun()
                st.stop()

        st.markdown('<div id="keypad-marker"></div>', unsafe_allow_html=True)
        k1, k2, k3 = st.columns(3)
        with k1:
            if st.button("1", use_container_width=True): st.session_state.pin_input += "1"; st.rerun()
            if st.button("4", use_container_width=True): st.session_state.pin_input += "4"; st.rerun()
            if st.button("7", use_container_width=True): st.session_state.pin_input += "7"; st.rerun()
            if st.button("C", use_container_width=True): st.session_state.pin_input = ""; st.rerun()
        with k2:
            if st.button("2", use_container_width=True): st.session_state.pin_input += "2"; st.rerun()
            if st.button("5", use_container_width=True): st.session_state.pin_input += "5"; st.rerun()
            if st.button("8", use_container_width=True): st.session_state.pin_input += "8"; st.rerun()
            if st.button("0", use_container_width=True): st.session_state.pin_input += "0"; st.rerun()
        with k3:
            if st.button("3", use_container_width=True): st.session_state.pin_input += "3"; st.rerun()
            if st.button("6", use_container_width=True): st.session_state.pin_input += "6"; st.rerun()
            if st.button("9", use_container_width=True): st.session_state.pin_input += "9"; st.rerun()
            if st.button("⌫", use_container_width=True): st.session_state.pin_input = st.session_state.pin_input[:-1]; st.rerun()
    st.stop()

# ==========================================
# KONEKSI GOOGLE SHEETS
# ==========================================
@st.cache_resource
def init_connection():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(st.secrets["GOOGLE_JSON"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("Database Finance Pro")
    except Exception:
        return None

db = init_connection()
if not db:
    st.error("Gagal terhubung ke Cloud Database. Silakan cek koneksi atau konfigurasi st.secrets.")
    st.stop()

@st.cache_data(ttl=60)
def load_data_from_sheets():
    _df_t = get_as_dataframe(db.worksheet("Transaksi")).dropna(how='all', axis=0).dropna(how='all', axis=1)
    _df_s = get_as_dataframe(db.worksheet("Saham")).dropna(how='all', axis=0).dropna(how='all', axis=1)
    return _df_t, _df_s

def bersihkan_angka_indo(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    v = str(val).upper().replace('RP', '').strip()
    if ',' in v and len(v.split(',')[-1]) <= 2: v = v.split(',')[0]
    v = v.replace('.', '').replace(' ', '')
    bersih = re.sub(r'[^\d]', '', v)
    try: return float(bersih) if bersih else 0.0
    except: return 0.0

def bersihkan_tanggal_indo(val):
    if pd.isna(val) or str(val).strip() == "": return pd.NaT
    val_str = str(val).strip()
    if ' ' in val_str: d_str, t_str = val_str.split(' ', 1)
    else: d_str, t_str = val_str, ""
    try:
        if '/' in d_str:
            parts = d_str.split('/')
            if len(parts) == 3:
                if len(parts[2]) == 4: d_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
                elif len(parts[0]) == 4: d_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
        elif '-' in d_str:
            parts = d_str.split('-')
            if len(parts) == 3:
                if len(parts[0]) == 4: d_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
                elif len(parts[2]) == 4: d_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
        if t_str: return pd.to_datetime(f"{d_str} {t_str}")
        else: return pd.to_datetime(d_str)
    except: return pd.NaT

def format_tgl_for_sheet(x):
    try:
        dt = pd.to_datetime(x)
        if pd.isna(dt): return ""
        if dt.hour == 0 and dt.minute == 0 and dt.second == 0: return dt.strftime('%Y-%m-%d')
        else: return dt.strftime('%Y-%m-%d %H:%M:%S')
    except: return ""

try:
    ws_transaksi = db.worksheet("Transaksi")
    ws_saham = db.worksheet("Saham")
    df_t_raw, df_s_raw = load_data_from_sheets()
    df_transaksi = df_t_raw.copy()
    df_saham = df_s_raw.copy()
    if not df_transaksi.empty:
        if 'Nominal' in df_transaksi.columns:
            df_transaksi['Nominal'] = df_transaksi['Nominal'].apply(bersihkan_angka_indo)
        if 'Tanggal' in df_transaksi.columns:
            df_transaksi['Tanggal'] = df_transaksi['Tanggal'].apply(bersihkan_tanggal_indo)
            df_transaksi = df_transaksi.dropna(subset=['Tanggal'])
except Exception as e:
    st.error(f"Gagal memuat worksheet: {e}")
    st.stop()

# ==========================================
# HITUNG SALDO & HARGA SAHAM
# ==========================================
porto = {"BCA": 0, "BRI": 0, "Bank Jago": 0, "Dompet (Cash)": 0}
if not df_transaksi.empty:
    for _, row in df_transaksi.iterrows():
        try:
            s, j, n = str(row.get('Sumber Dana', '')), str(row.get('Jenis', '')), float(row.get('Nominal', 0))
            if s in porto: porto[s] += n if j.lower() == "pemasukan" else -n
        except ValueError: pass

total_nilai_saham = 0
harga_sekarang_dict = {}
df_saham_agg = pd.DataFrame()

if not df_saham.empty:
    try:
        kurs_data = yf.Ticker("USDIDR=X").history(period="1d")
        kurs = kurs_data['Close'].iloc[-1] if not kurs_data.empty else 15000
        tks = [str(t).upper().strip() for t in df_saham['Ticker'].unique() if pd.notna(t) and str(t).strip() != ""]
        if tks:
            data_yf = yf.download(tks, period="5d", progress=False)
            for t in tks:
                try:
                    cp = float(data_yf['Close'][t].dropna().iloc[-1]) if len(tks) > 1 else float(data_yf['Close'].dropna().iloc[-1])
                    if pd.isna(cp): cp = 0
                    harga_sekarang_dict[t] = cp * kurs if not t.endswith('.JK') else cp
                except Exception: harga_sekarang_dict[t] = 0
    except Exception: pass

    df_saham['Ticker'] = df_saham['Ticker'].astype(str).str.upper().str.strip()
    df_saham['Jumlah Lembar'] = pd.to_numeric(df_saham['Jumlah Lembar'], errors='coerce').fillna(0)
    df_saham['Harga Beli'] = pd.to_numeric(df_saham['Harga Beli'], errors='coerce').fillna(0)
    df_saham['Total Modal'] = df_saham['Jumlah Lembar'] * df_saham['Harga Beli']
    df_saham_agg = df_saham.groupby('Ticker').agg({'Jumlah Lembar': 'sum', 'Total Modal': 'sum'}).reset_index()
    df_saham_agg['Harga Beli Rata-rata'] = df_saham_agg['Total Modal'] / df_saham_agg['Jumlah Lembar']
    df_saham_agg = df_saham_agg[df_saham_agg['Jumlah Lembar'] > 0]
    for _, row in df_saham_agg.iterrows():
        ticker = row['Ticker']
        jumlah = row['Jumlah Lembar']
        harga_beli = row['Harga Beli Rata-rata']
        harga_skrg = harga_sekarang_dict.get(ticker, 0)
        if pd.isna(harga_skrg) or harga_skrg == 0: harga_skrg = harga_beli
        total_nilai_saham += (harga_skrg * jumlah)

# ==========================================
# HEADER APP
# ==========================================
col_h1, col_h2, col_h3 = st.columns([3, 1, 1])
with col_h1:
    st.markdown('<div class="app-logo" style="text-align:left; font-size:28px; padding:8px 0;">💎 ROGER Finance</div>', unsafe_allow_html=True)
with col_h2:
    if st.button("👁️ Sembunyikan" if not st.session_state.hide_balance else "👁️ Tampilkan", use_container_width=True):
        st.session_state.hide_balance = not st.session_state.hide_balance
        st.rerun()
with col_h3:
    if st.button("🔒 Kunci", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.pin_input = ""
        st.rerun()

st.markdown('<hr style="margin:8px 0 16px 0;">', unsafe_allow_html=True)

# ==========================================
# MAIN TABS
# ==========================================
tab1, tab3, tab4, tab5, tab6 = st.tabs([
    "🏦  Dashboard",
    "📈  Portofolio",
    "🧾  AI Scanner",
    "⚡  Screener",
    "⚙️  Pengaturan"
])

# ==========================================
# TAB 1 — DASHBOARD KEKAYAAN
# ==========================================
with tab1:
    today_indo = pd.Timestamp.now('Asia/Jakarta')
    total_net = sum(porto.values()) + total_nilai_saham

    # ── Today's Summary Banner ──
    today_trx = pd.DataFrame()
    today_in = today_out = 0.0
    if not df_transaksi.empty:
        df_today_mask = (df_transaksi['Tanggal'].dt.date == today_indo.date())
        today_trx = df_transaksi[df_today_mask].copy()
        today_trx['Jenis'] = today_trx['Jenis'].astype(str).str.lower().str.strip()
        today_in  = today_trx[today_trx['Jenis'] == 'pemasukan']['Nominal'].sum()
        today_out = today_trx[today_trx['Jenis'] == 'pengeluaran']['Nominal'].sum()

    net_today = today_in - today_out
    net_today_color = "#34D399" if net_today >= 0 else "#F87171"
    st.markdown(f'''
    <div class="today-banner">
        <div style="margin-right:8px; font-size:28px;">📅</div>
        <div class="today-item">
            <div class="today-label">Hari Ini</div>
            <div class="today-value" style="color:#94A3B8; font-size:14px;">{today_indo.strftime('%A, %d %b %Y')}</div>
        </div>
        <div style="width:1px; background:#1E293B; height:40px; margin:0 4px;"></div>
        <div class="today-item">
            <div class="today-label">Pemasukan Hari Ini</div>
            <div class="today-value today-in">{format_currency(today_in)}</div>
        </div>
        <div class="today-item">
            <div class="today-label">Pengeluaran Hari Ini</div>
            <div class="today-value today-out">{format_currency(today_out)}</div>
        </div>
        <div class="today-item">
            <div class="today-label">Net Hari Ini</div>
            <div class="today-value" style="color:{net_today_color};">{format_currency(net_today)}</div>
        </div>
        <div class="today-item" style="margin-left:auto;">
            <div class="today-label">Transaksi</div>
            <div class="today-value" style="color:#94A3B8;">{len(today_trx)} item</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # ── Target Progress ──
    col_target, col_health = st.columns([2, 1])
    with col_target:
        st.markdown('<div class="section-title">🎯 Target Finansial</div>', unsafe_allow_html=True)
        target_teks = st.text_input("Target Harta Bersih (Rp)", value="100.000.000", label_visibility="collapsed")
        try: target_harta = float(target_teks.replace(".", "").replace(",", ""))
        except ValueError: target_harta = 100_000_000.0
        rasio = max(0.0, min(total_net / target_harta, 1.0)) if target_harta > 0 else 0.0
        persen = rasio * 100
        pct_color = "#34D399" if persen >= 80 else "#38BDF8" if persen >= 50 else "#FBBF24" if persen >= 25 else "#F87171"
        st.progress(rasio)
        st.markdown(f'<p style="font-size:13px; color:{pct_color}; font-weight:600; margin-top:4px;">✅ {persen:.1f}% tercapai — {format_currency(total_net)} dari {format_currency(target_harta)}</p>', unsafe_allow_html=True)

    with col_health:
        # ── Financial Health Score ──
        st.markdown('<div class="section-title">💪 Health Score</div>', unsafe_allow_html=True)
        score = 0
        nama_bulan = ["Semua Waktu", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        curr_m = today_indo.month
        if not df_transaksi.empty:
            df_h = df_transaksi.copy()
            df_h['Jenis'] = df_h['Jenis'].astype(str).str.lower().str.strip()
            df_h['Kategori'] = df_h['Kategori'].astype(str).str.strip().str.title()
            df_m = df_h[(df_h['Tanggal'].dt.month == curr_m) & (df_h['Tanggal'].dt.year == today_indo.year)]
            in_m  = df_m[df_m['Jenis'] == 'pemasukan']['Nominal'].sum()
            out_m = df_m[df_m['Jenis'] == 'pengeluaran']['Nominal'].sum()
            inv_m = df_m[(df_m['Jenis'] == 'pengeluaran') & (df_m['Kategori'] == 'Investasi')]['Nominal'].sum()
            if in_m > 0:
                rasio_tabung = (in_m - out_m) / in_m
                rasio_invest = inv_m / in_m
                if rasio_tabung >= 0.3: score += 35
                elif rasio_tabung >= 0.1: score += 20
                elif rasio_tabung > 0: score += 10
                if rasio_invest >= 0.2: score += 30
                elif rasio_invest >= 0.1: score += 18
                elif rasio_invest > 0: score += 8
                for kat, limit in st.session_state.budgets.items():
                    spent_kat = df_m[(df_m['Jenis'] == 'pengeluaran') & (df_m['Kategori'] == kat.strip().title())]['Nominal'].sum()
                    if limit > 0 and spent_kat <= limit: score += 5
                score += min(int(rasio * 35), 35)
            score = min(score, 100)

        if score >= 80: grade, grade_class, grade_emoji = "Excellent", "score-excellent", "🌟"
        elif score >= 60: grade, grade_class, grade_emoji = "Good", "score-good", "👍"
        elif score >= 40: grade, grade_class, grade_emoji = "Fair", "score-fair", "⚠️"
        else: grade, grade_class, grade_emoji = "Poor", "score-poor", "🚨"

        gauge_color = "#34D399" if score >= 80 else "#38BDF8" if score >= 60 else "#FBBF24" if score >= 40 else "#EF4444"
        # SVG Gauge
        angle = (score / 100) * 180
        import math
        rad = math.radians(angle)
        cx, cy, r = 80, 80, 60
        x_end = cx + r * math.cos(math.pi - rad)
        y_end = cy - r * math.sin(rad)
        st.markdown(f'''
        <div style="display:flex; flex-direction:column; align-items:center;">
        <svg width="160" height="90" viewBox="0 0 160 90">
          <path d="M 20 80 A 60 60 0 0 1 140 80" fill="none" stroke="#1E293B" stroke-width="12" stroke-linecap="round"/>
          <path d="M 20 80 A 60 60 0 0 1 {x_end:.1f} {y_end:.1f}" fill="none" stroke="{gauge_color}" stroke-width="12" stroke-linecap="round"/>
          <text x="80" y="72" text-anchor="middle" fill="{gauge_color}" font-size="24" font-weight="900" font-family="Inter">{score}</text>
          <text x="80" y="85" text-anchor="middle" fill="#475569" font-size="10" font-family="Inter">/ 100</text>
        </svg>
        <span class="score-badge {grade_class}">{grade_emoji} {grade}</span>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Metrics ──
    m1, m2, m3 = st.columns(3)
    m1.metric("🌟 Total Harta Bersih", format_currency(total_net))
    m2.metric("💵 Total Uang Tunai",   format_currency(sum(porto.values())))
    m3.metric("📈 Total Nilai Saham",  format_currency(total_nilai_saham))

    st.markdown('<br>', unsafe_allow_html=True)

    # ── Wallet Cards ──
    st.markdown('<div class="section-title">💳 Dompet & Rekening</div>', unsafe_allow_html=True)
    st.markdown('<div class="wallet-container">', unsafe_allow_html=True)
    wallets = [
        {"name": "BANK BCA",   "val": porto["BCA"],           "class": "bca-card",  "icon": "🏦"},
        {"name": "BANK BRI",   "val": porto["BRI"],           "class": "bri-card",  "icon": "🏢"},
        {"name": "BANK JAGO",  "val": porto["Bank Jago"],     "class": "jago-card", "icon": "🦊"},
        {"name": "UANG TUNAI", "val": porto["Dompet (Cash)"], "class": "cash-card", "icon": "💵"},
    ]
    wc = st.columns(4)
    for i, w in enumerate(wallets):
        with wc[i]:
            st.markdown(f'''
            <div class="wallet-card {w["class"]}">
                <div class="wallet-chip"></div>
                <div class="wallet-icon">{w["icon"]}</div>
                <div class="wallet-label">{w["name"]}</div>
                <div class="wallet-balance">{format_currency(w["val"])}</div>
            </div>
            ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Filter Bulan ──
    col_f1, col_f2 = st.columns(2)
    with col_f1: pilih_bulan = st.selectbox("Pilih Laporan Bulan", nama_bulan, index=today_indo.month)
    with col_f2: pilih_tahun = st.selectbox("Tahun", list(range(2020, today_indo.year + 5)), index=list(range(2020, today_indo.year + 5)).index(today_indo.year))

    df_curr = pd.DataFrame()
    in_curr = out_curr = 0.0
    if not df_transaksi.empty:
        df_calc = df_transaksi.copy()
        df_calc['Jenis']    = df_calc['Jenis'].astype(str).str.strip().str.lower()
        df_calc['Kategori'] = df_calc['Kategori'].astype(str).str.strip().str.title()
        if pilih_bulan == "Semua Waktu":
            df_curr = df_calc.copy()
        else:
            curr_m = nama_bulan.index(pilih_bulan)
            df_curr = df_calc[(df_calc['Tanggal'].dt.month == curr_m) & (df_calc['Tanggal'].dt.year == pilih_tahun)]
        in_curr  = df_curr[df_curr['Jenis'] == 'pemasukan']['Nominal'].sum()
        out_curr = df_curr[df_curr['Jenis'] == 'pengeluaran']['Nominal'].sum()

    st.markdown('<br>', unsafe_allow_html=True)

    # ── Dua Kolom: Form + Visual ──
    col_l, col_r = st.columns([1, 1.6])

    with col_l:
        st.markdown('<div class="section-title">➕ Tambah Transaksi</div>', unsafe_allow_html=True)
        with st.form("trx_form", clear_on_submit=True):
            f_tgl = st.date_input("Tanggal", pd.Timestamp.now('Asia/Jakarta').date())
            f_kat = st.selectbox("Kategori", st.session_state.kategori_list)
            f_jen = st.radio("Jenis", ["Pemasukan", "Pengeluaran"], horizontal=True)
            f_src = st.selectbox("Dompet / Rekening", list(porto.keys()))
            default_nom = st.session_state.get('auto_nominal', "")
            f_nom_teks = st.text_input("Jumlah (Rp)", value=default_nom, placeholder="Contoh: 50.000")
            f_note = st.text_area("Catatan", placeholder="Rincian transaksi...", height=80)

            if st.form_submit_button("💾  SIMPAN TRANSAKSI", use_container_width=True):
                try: f_nom = float(f_nom_teks.replace(".", "").replace(",", "")) if f_nom_teks else 0.0
                except ValueError: f_nom = 0.0
                waktu_skrg = pd.Timestamp.now('Asia/Jakarta').strftime('%H:%M:%S')
                tgl_simpan = f"{f_tgl.strftime('%Y-%m-%d')} {waktu_skrg}"
                new_row = pd.DataFrame([{"Tanggal": tgl_simpan, "Kategori": f_kat, "Jenis": f_jen, "Sumber Dana": f_src, "Nominal": f_nom, "Catatan": f_note}])
                df_updated = pd.concat([df_transaksi, new_row], ignore_index=True)
                df_updated['Tanggal'] = pd.to_datetime(df_updated['Tanggal']).apply(format_tgl_for_sheet)
                set_with_dataframe(ws_transaksi, df_updated, row=1)
                if f_jen == "Pemasukan": st.balloons()
                st.session_state.auto_nominal = ""
                if 'scan_status' in st.session_state: del st.session_state.scan_status
                st.cache_data.clear(); st.rerun()

        # ── Quick Bills ──
        st.markdown('<br>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">⚡ Tagihan Rutin 1-Klik</div>', unsafe_allow_html=True)
        with st.expander("Bayar tagihan bulanan wajib", expanded=False):
            with st.form("rutin_form"):
                st.markdown("Centang tagihan yang sudah dibayar hari ini:")
                rutin_kost = st.checkbox("🏠 Bayar Kost — Rp 400.000")
                rutin_inet = st.checkbox("🌐 Kuota Internet — Rp 100.000")
                rutin_kopi = st.checkbox("☕ Kopi 1KG — Rp 200.000")
                rutin_src  = st.selectbox("Bayar via:", list(porto.keys()))
                if st.form_submit_button("✅  LUNASI TAGIHAN TERPILIH", use_container_width=True):
                    new_rows = []
                    today_str = pd.Timestamp.now('Asia/Jakarta').strftime('%Y-%m-%d %H:%M:%S')
                    if rutin_kost: new_rows.append({"Tanggal": today_str, "Kategori": "Kost", "Jenis": "Pengeluaran", "Sumber Dana": rutin_src, "Nominal": 400000.0, "Catatan": "Auto-Bayar Kost Rutin"})
                    if rutin_inet: new_rows.append({"Tanggal": today_str, "Kategori": "Kuota Internet", "Jenis": "Pengeluaran", "Sumber Dana": rutin_src, "Nominal": 100000.0, "Catatan": "Auto-Beli Kuota Rutin"})
                    if rutin_kopi: new_rows.append({"Tanggal": today_str, "Kategori": "Kebutuhan Pokok & Beras", "Jenis": "Pengeluaran", "Sumber Dana": rutin_src, "Nominal": 200000.0, "Catatan": "Auto-Beli Kopi 1KG Rutin"})
                    if new_rows:
                        df_updated = pd.concat([df_transaksi, pd.DataFrame(new_rows)], ignore_index=True)
                        df_updated['Tanggal'] = pd.to_datetime(df_updated['Tanggal']).apply(format_tgl_for_sheet)
                        set_with_dataframe(ws_transaksi, df_updated, row=1)
                        st.success("✅ Tagihan berhasil dilunasi & dicatat!")
                        st.cache_data.clear(); st.rerun()
                    else: st.warning("Pilih minimal 1 tagihan.")

    with col_r:
        st.markdown('<div class="section-title">📊 Analisis Visual</div>', unsafe_allow_html=True)
        g1, g2, g3, g4, g5, g6 = st.tabs(["📉 Arus Kas", "🧬 50/30/20", "🧛 Top Boros", "🗓️ Heatmap", "🥧 Aset", "📅 Tren Tahunan"])

        with g1:
            if not df_curr.empty:
                df_trend = df_curr.copy()
                df_trend['Tgl'] = df_trend['Tanggal'].dt.day
                trend_data = df_trend.groupby(['Tgl', 'Jenis'])['Nominal'].sum().reset_index()
                max_day = trend_data['Tgl'].max() if not trend_data.empty else today_indo.day
                all_days = pd.DataFrame({'Tgl': range(1, max_day + 1)})
                pemasukan_data   = pd.merge(all_days, trend_data[trend_data['Jenis'] == 'pemasukan'], on='Tgl', how='left').fillna({'Nominal': 0, 'Jenis': 'pemasukan'})
                pengeluaran_data = pd.merge(all_days, trend_data[trend_data['Jenis'] == 'pengeluaran'], on='Tgl', how='left').fillna({'Nominal': 0, 'Jenis': 'pengeluaran'})
                final_trend = pd.concat([pemasukan_data, pengeluaran_data])
                fig_trend = px.line(final_trend, x='Tgl', y='Nominal', color='Jenis',
                                    color_discrete_map={'pemasukan': '#10B981', 'pengeluaran': '#EF4444'},
                                    markers=True, template="plotly_dark")
                fig_trend.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350,
                                        margin=dict(l=0, r=0, t=10, b=0),
                                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                fig_trend.update_xaxes(showgrid=False)
                fig_trend.update_yaxes(showgrid=True, gridcolor='#1E293B')
                st.plotly_chart(fig_trend, use_container_width=True)
                # Mini summary
                selisih = in_curr - out_curr
                sel_color = "#34D399" if selisih >= 0 else "#F87171"
                st.markdown(f'''
                <div style="display:flex; gap:16px; margin-top:-8px;">
                  <div style="flex:1; text-align:center; padding:10px; background:rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.12); border-radius:10px;">
                    <div style="font-size:10px; color:#475569; text-transform:uppercase; letter-spacing:1px;">Pemasukan</div>
                    <div style="font-size:16px; font-weight:800; color:#34D399;">{format_currency(in_curr)}</div>
                  </div>
                  <div style="flex:1; text-align:center; padding:10px; background:rgba(239,68,68,0.06); border:1px solid rgba(239,68,68,0.12); border-radius:10px;">
                    <div style="font-size:10px; color:#475569; text-transform:uppercase; letter-spacing:1px;">Pengeluaran</div>
                    <div style="font-size:16px; font-weight:800; color:#F87171;">{format_currency(out_curr)}</div>
                  </div>
                  <div style="flex:1; text-align:center; padding:10px; background:rgba(56,189,248,0.06); border:1px solid rgba(56,189,248,0.12); border-radius:10px;">
                    <div style="font-size:10px; color:#475569; text-transform:uppercase; letter-spacing:1px;">Sisa / Net</div>
                    <div style="font-size:16px; font-weight:800; color:{sel_color};">{format_currency(selisih)}</div>
                  </div>
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.info("Belum ada data untuk periode ini.")

        with g2:
            if not df_curr.empty and in_curr > 0:
                kebutuhan_list   = ['Bayar Kost', 'Kost', 'Makan & Minum', 'Transportasi', 'Kuota Internet', 'Kebutuhan Mandi', 'Kebutuhan Pokok & Beras', 'Laundry']
                masa_depan_list  = ['Investasi']
                pokok      = df_curr[(df_curr['Jenis'] == 'pengeluaran') & (df_curr['Kategori'].isin(kebutuhan_list))]['Nominal'].sum()
                masa_depan = df_curr[(df_curr['Jenis'] == 'pengeluaran') & (df_curr['Kategori'].isin(masa_depan_list))]['Nominal'].sum()
                keinginan  = out_curr - pokok - masa_depan
                p_pokok      = min((pokok / in_curr) * 100, 100)
                p_keinginan  = min((keinginan / in_curr) * 100, 100)
                p_masa_depan = min((masa_depan / in_curr) * 100, 100)

                vitals = [
                    ("🏠", "KEBUTUHAN POKOK", "Ideal: < 50%", pokok, p_pokok, p_pokok <= 50, "#3B82F6"),
                    ("🛍️", "GAYA HIDUP", "Ideal: < 30%", keinginan, p_keinginan, p_keinginan <= 30, "#8B5CF6"),
                    ("🌱", "MASA DEPAN", "Ideal: > 20%", masa_depan, p_masa_depan, p_masa_depan >= 20, "#10B981"),
                ]
                for icon, label, ideal, value, pct, is_ok, accent in vitals:
                    bar_color = "#34D399" if is_ok else "#F87171"
                    st.markdown(f'''
                    <div class="vitals-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="font-size:11px; color:#475569; font-weight:700; text-transform:uppercase; letter-spacing:1px;">{icon} {label}</span>
                                <span style="font-size:10px; color:#334155; margin-left:6px;">— {ideal}</span>
                            </div>
                            <span style="font-size:13px; font-weight:800; color:{bar_color};">{pct:.1f}%</span>
                        </div>
                        <div style="font-size:18px; font-weight:800; color:#F1F5F9; margin-top:6px;">{format_currency(value)}</div>
                        <div class="vitals-bar-track">
                            <div class="vitals-bar-fill" style="width:{pct}%; background:{bar_color};"></div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                st.info("Catat pemasukan bulan ini terlebih dahulu.")

        with g3:
            if not df_curr.empty and out_curr > 0:
                top_5 = df_curr[df_curr['Jenis'] == 'pengeluaran'].groupby('Kategori')['Nominal'].sum().nlargest(5).reset_index()
                top_5 = top_5.sort_values('Nominal', ascending=True)
                colors = ['#EF4444', '#F97316', '#F59E0B', '#FBBF24', '#FCD34D'][:len(top_5)]
                fig_top = go.Figure(go.Bar(
                    y=top_5['Kategori'], x=top_5['Nominal'],
                    orientation='h',
                    marker_color=colors,
                    text=[format_currency(v) for v in top_5['Nominal']],
                    textposition='outside',
                    textfont=dict(color='#94A3B8', size=11),
                ))
                fig_top.update_layout(
                    template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    height=300, margin=dict(l=0, r=100, t=10, b=0),
                    xaxis=dict(showgrid=False, showticklabels=False, title=None),
                    yaxis=dict(title=None, tickfont=dict(size=12)),
                )
                st.plotly_chart(fig_top, use_container_width=True)
            else:
                st.info("Belum ada pengeluaran dicatat.")

        with g4:
            if not df_curr.empty and not df_curr[df_curr['Jenis'] == 'pengeluaran'].empty:
                df_out = df_curr[df_curr['Jenis'] == 'pengeluaran'].copy()
                df_out['Tgl'] = pd.to_datetime(df_out['Tanggal']).dt.day
                daily_spend = df_out.groupby('Tgl')['Nominal'].sum().reset_index()
                max_day = daily_spend['Tgl'].max()
                all_days = pd.DataFrame({'Tgl': range(1, max_day + 1)})
                daily_spend = pd.merge(all_days, daily_spend, on='Tgl', how='left').fillna(0)
                fig_h = px.bar(daily_spend, x='Tgl', y='Nominal', color='Nominal',
                               color_continuous_scale='Reds',
                               labels={'Tgl': 'Tanggal', 'Nominal': 'Total Pengeluaran (Rp)'})
                fig_h.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                    height=300, margin=dict(l=10, r=10, t=30, b=10),
                                    title=dict(text="Pola Pengeluaran Harian", font=dict(size=13, color='#64748B'), x=0.5),
                                    coloraxis_showscale=False)
                fig_h.update_xaxes(showgrid=False)
                fig_h.update_yaxes(showgrid=True, gridcolor='#1E293B', showticklabels=False, title=None)
                st.plotly_chart(fig_h, use_container_width=True)
            else:
                st.info("Belum ada rekam pengeluaran bulan ini.")

        with g5:
            df_p = pd.DataFrame([{"Aset": k, "Nilai": max(0, v)} for k, v in {**porto, "Saham": total_nilai_saham}.items() if v > 0])
            if not df_p.empty:
                fig_p = px.pie(df_p, values='Nilai', names='Aset', hole=0.55, template="plotly_dark",
                               color_discrete_map={'BCA': '#3B82F6', 'BRI': '#F97316', 'Bank Jago': '#F59E0B', 'Dompet (Cash)': '#10B981', 'Saham': '#8B5CF6'})
                fig_p.update_traces(textfont_size=11)
                fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=320,
                                    showlegend=True, legend=dict(font=dict(size=11, color='#94A3B8')),
                                    annotations=[dict(text=f'<b>{format_currency(sum(porto.values()) + total_nilai_saham)}</b>', x=0.5, y=0.5, font_size=12, showarrow=False, font_color='#F1F5F9')])
                st.plotly_chart(fig_p, use_container_width=True)
            else: st.info("Belum ada data aset.")

        with g6:
            if not df_transaksi.empty:
                df_year = df_transaksi.copy()
                df_year['Jenis'] = df_year['Jenis'].astype(str).str.strip().str.capitalize()
                df_year['Bulan_Angka'] = df_year['Tanggal'].dt.month
                df_year['Tahun'] = df_year['Tanggal'].dt.year
                df_year = df_year[df_year['Tahun'] == pilih_tahun]
                if not df_year.empty:
                    monthly_data = df_year.groupby(['Bulan_Angka', 'Jenis'])['Nominal'].sum().reset_index()
                    bulan_map = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"Mei",6:"Jun",7:"Jul",8:"Ags",9:"Sep",10:"Okt",11:"Nov",12:"Des"}
                    monthly_data['Bulan'] = monthly_data['Bulan_Angka'].map(bulan_map)
                    fig_month = px.bar(monthly_data, x='Bulan', y='Nominal', color='Jenis', barmode='group',
                                       color_discrete_map={'Pemasukan': '#10B981', 'Pengeluaran': '#EF4444'},
                                       template="plotly_dark")
                    fig_month.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300,
                                            margin=dict(l=0, r=0, t=10, b=0),
                                            legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                    fig_month.update_xaxes(title=None, categoryorder='array', categoryarray=list(bulan_map.values()))
                    fig_month.update_yaxes(title=None, showgrid=True, gridcolor='#1E293B')
                    st.plotly_chart(fig_month, use_container_width=True)
                else: st.info(f"Belum ada catatan untuk tahun {pilih_tahun}.")
            else: st.info("Belum ada data historis.")

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Budget Monitor ──
    if st.session_state.budgets:
        st.markdown('<div class="section-title">🚨 Monitor Budget Bulanan</div>', unsafe_allow_html=True)
        spent = df_curr[df_curr['Jenis'] == 'pengeluaran'].groupby('Kategori')['Nominal'].sum().to_dict() if not df_curr.empty else {}
        bc = st.columns(min(len(st.session_state.budgets), 4))
        for i, (kat, limit) in enumerate(st.session_state.budgets.items()):
            terpakai = spent.get(str(kat).strip().title(), 0.0)
            rasio_b  = min(terpakai / limit, 1.0) if limit > 0 else 1.0
            sisa     = limit - terpakai
            color    = "#34D399" if rasio_b < 0.5 else "#FBBF24" if rasio_b < 0.85 else "#F87171"
            icon     = "🟢" if rasio_b < 0.5 else "🟡" if rasio_b < 0.85 else "🔴"
            with bc[i % 4]:
                st.markdown(f'''
                <div class="budget-card">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:12px; font-weight:700; color:#94A3B8;">{icon} {kat}</span>
                    <span style="font-size:11px; color:{color}; font-weight:600;">{rasio_b*100:.0f}%</span>
                  </div>
                  <div style="width:100%; background:#0F172A; border-radius:6px; height:6px;">
                    <div style="width:{rasio_b*100}%; height:100%; background:{color}; border-radius:6px;"></div>
                  </div>
                  <div style="margin-top:8px; font-size:12px; color:{"#34D399" if sisa >= 0 else "#F87171"}; font-weight:600;">
                    {"Sisa: " + format_currency(sisa) if sisa >= 0 else "⚠️ OVER: " + format_currency(abs(sisa))}
                  </div>
                  <div style="font-size:10px; color:#334155; margin-top:2px;">Limit: {format_currency(limit)}</div>
                </div>
                ''', unsafe_allow_html=True)
        st.markdown('<hr>', unsafe_allow_html=True)

    # ── Riwayat Transaksi ──
    with st.expander("📋 Riwayat & Kelola Transaksi"):
        if not df_transaksi.empty:
            df_display = df_transaksi.copy()
            def format_display(x):
                dt = pd.to_datetime(x)
                if pd.isna(dt): return ""
                return dt.strftime('%Y-%m-%d') if dt.hour == 0 and dt.minute == 0 and dt.second == 0 else dt.strftime('%Y-%m-%d %H:%M')
            df_display['Tanggal'] = df_display['Tanggal'].apply(format_display)
            df_display = df_display.sort_values(by='Tanggal', ascending=False)
            df_display['ID_Asli'] = df_display.index
            df_display = df_display.reset_index(drop=True)
            df_html = df_display.copy()
            df_html.index = df_html.index + 1
            df_html.reset_index(inplace=True)
            df_html.rename(columns={'index': 'No'}, inplace=True)
            df_tabel_bersih = df_html.drop(columns=['ID_Asli'])
            df_tabel_bersih['Nominal'] = df_tabel_bersih['Nominal'].apply(lambda x: format_currency(x))
            render_beautiful_table(df_tabel_bersih)
            st.download_button("📥 Download CSV", data=df_transaksi.to_csv(index=False).encode('utf-8'), file_name="Riwayat_ROGER.csv", mime="text/csv")
            st.markdown('<hr>', unsafe_allow_html=True)
            st.markdown('##### ✏️ Edit / Hapus Transaksi')
            pilih_no = st.selectbox("Pilih No. Transaksi:", [None] + df_html['No'].tolist())
            if pilih_no is not None:
                row_terpilih = df_display[df_display.index == (pilih_no - 1)].iloc[0]
                idx_asli = row_terpilih['ID_Asli']
                tgl_asli = df_transaksi.loc[idx_asli, 'Tanggal']
                dt_obj = pd.to_datetime(tgl_asli)
                with st.form("form_edit_transaksi"):
                    c_ed1, c_ed2, c_ed3 = st.columns(3)
                    with c_ed1:
                        ed_tgl = st.date_input("Tanggal", dt_obj.date())
                        ed_jen = st.selectbox("Jenis", ["Pemasukan", "Pengeluaran"], index=0 if str(row_terpilih['Jenis']).lower() == "pemasukan" else 1)
                    with c_ed2:
                        try: idx_kat = st.session_state.kategori_list.index(row_terpilih['Kategori'])
                        except ValueError: idx_kat = 0
                        ed_kat = st.selectbox("Kategori", st.session_state.kategori_list, index=idx_kat)
                        ed_src = st.selectbox("Sumber Dana", list(porto.keys()), index=list(porto.keys()).index(row_terpilih['Sumber Dana']) if row_terpilih['Sumber Dana'] in porto else 0)
                    with c_ed3:
                        ed_nom  = st.number_input("Nominal (Rp)", value=float(row_terpilih['Nominal']), step=10000.0)
                        ed_note = st.text_input("Catatan", value=str(row_terpilih['Catatan']))
                    c_btn_simpan, c_btn_hapus = st.columns(2)
                    with c_btn_simpan: btn_update = st.form_submit_button("💾 UPDATE", use_container_width=True)
                    with c_btn_hapus:  btn_delete = st.form_submit_button("🗑️ HAPUS",  use_container_width=True)
                    if btn_update:
                        waktu_asli = dt_obj.strftime('%H:%M:%S')
                        ed_tgl_full = ed_tgl.strftime('%Y-%m-%d') if waktu_asli == "00:00:00" else f"{ed_tgl.strftime('%Y-%m-%d')} {waktu_asli}"
                        df_transaksi.at[idx_asli, 'Tanggal']    = ed_tgl_full
                        df_transaksi.at[idx_asli, 'Jenis']      = ed_jen
                        df_transaksi.at[idx_asli, 'Kategori']   = ed_kat
                        df_transaksi.at[idx_asli, 'Sumber Dana']= ed_src
                        df_transaksi.at[idx_asli, 'Nominal']    = ed_nom
                        df_transaksi.at[idx_asli, 'Catatan']    = ed_note
                        df_transaksi['Tanggal'] = pd.to_datetime(df_transaksi['Tanggal']).apply(format_tgl_for_sheet)
                        ws_transaksi.clear()
                        set_with_dataframe(ws_transaksi, df_transaksi, row=1)
                        st.success(f"✅ Transaksi No.{pilih_no} diperbarui!"); st.cache_data.clear(); st.rerun()
                    if btn_delete:
                        df_transaksi = df_transaksi.drop(idx_asli)
                        df_transaksi['Tanggal'] = pd.to_datetime(df_transaksi['Tanggal']).apply(format_tgl_for_sheet)
                        ws_transaksi.clear()
                        set_with_dataframe(ws_transaksi, df_transaksi, row=1)
                        st.error(f"🗑️ Transaksi No.{pilih_no} dihapus."); st.cache_data.clear(); st.rerun()
        else:
            st.info("Belum ada transaksi tercatat.")


# ==========================================
# TAB 3 — PORTOFOLIO SAHAM
# ==========================================
with tab3:
    st.markdown('<div class="section-title">💼 Portofolio Saham</div>', unsafe_allow_html=True)

    col_port1, col_port2 = st.columns(2)
    with col_port1:
        with st.expander("➕ Tambah Beli Saham", expanded=False):
            with st.form("form_saham_beli", clear_on_submit=True):
                new_ticker = st.text_input("Kode Ticker", help="Akhiri .JK untuk saham Indonesia").upper()
                new_lot    = st.number_input("Jumlah Lot DIBELI", min_value=1, step=1)
                new_harga_teks = st.text_input("Harga Beli per Lembar (Rp)")
                if st.form_submit_button("💾 SIMPAN PEMBELIAN", use_container_width=True):
                    try: new_harga = float(new_harga_teks.replace(".", "").replace(",", "")) if new_harga_teks else 0.0
                    except ValueError: new_harga = 0.0
                    if new_ticker:
                        new_lembar = new_lot * 100
                        df_saham_updated = pd.concat([df_saham, pd.DataFrame([{"Ticker": new_ticker.strip(), "Jumlah Lembar": new_lembar, "Harga Beli": new_harga}])], ignore_index=True)
                        set_with_dataframe(ws_saham, df_saham_updated, row=1)
                        st.success(f"✅ Pembelian {new_ticker} tersimpan!"); st.cache_data.clear(); st.rerun()

    with col_port2:
        with st.expander("➖ Catat Penjualan Saham", expanded=False):
            if not df_saham_agg.empty:
                with st.form("form_saham_jual", clear_on_submit=True):
                    ticker_jual = st.selectbox("Pilih Saham", df_saham_agg['Ticker'].tolist())
                    lot_jual    = st.number_input("Jumlah Lot DIJUAL", min_value=1, step=1)
                    if st.form_submit_button("📤 CATAT PENJUALAN", use_container_width=True):
                        lembar_jual = lot_jual * 100
                        df_saham_updated = pd.concat([df_saham, pd.DataFrame([{"Ticker": ticker_jual, "Jumlah Lembar": -lembar_jual, "Harga Beli": 0}])], ignore_index=True)
                        set_with_dataframe(ws_saham, df_saham_updated, row=1)
                        st.success(f"✅ Penjualan {ticker_jual} dicatat!"); st.cache_data.clear(); st.rerun()
            else: st.info("Portofolio masih kosong.")

    st.markdown('<br>', unsafe_allow_html=True)

    # ── Portfolio Cards ──
    if not df_saham_agg.empty:
        total_modal_all = 0.0
        total_nilai_all = 0.0
        saham_rows = []
        pie_data_saham = []

        for _, r in df_saham_agg.iterrows():
            t = str(r.get('Ticker', '')).upper()
            harga_beli = float(r.get('Harga Beli Rata-rata', 0))
            lembar     = float(r.get('Jumlah Lembar', 0))
            harga_skrg = harga_sekarang_dict.get(t, harga_beli)
            if pd.isna(harga_skrg) or harga_skrg == 0: harga_skrg = harga_beli
            total_modal = harga_beli * lembar
            total_nilai = harga_skrg * lembar
            gain_rp  = total_nilai - total_modal
            gain_pct = ((harga_skrg - harga_beli) / harga_beli) * 100 if harga_beli > 0 else 0.0
            total_modal_all += total_modal
            total_nilai_all += total_nilai
            saham_rows.append({"t": t, "harga_beli": harga_beli, "harga_skrg": harga_skrg, "lembar": lembar, "gain_rp": gain_rp, "gain_pct": gain_pct, "total_nilai": total_nilai, "total_modal": total_modal})
            if total_nilai > 0: pie_data_saham.append({"Ticker": t, "Nilai": total_nilai})

        # Summary bar
        total_gain_rp  = total_nilai_all - total_modal_all
        total_gain_pct = ((total_nilai_all - total_modal_all) / total_modal_all * 100) if total_modal_all > 0 else 0
        gain_color = "#34D399" if total_gain_rp >= 0 else "#F87171"
        st.markdown(f'''
        <div style="background:linear-gradient(135deg,rgba(14,165,233,0.07),rgba(139,92,246,0.07)); border:1px solid rgba(56,189,248,0.1); border-radius:16px; padding:16px 20px; display:flex; gap:24px; flex-wrap:wrap; margin-bottom:20px;">
          <div><div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:1px;font-weight:700;">Total Modal</div><div style="font-size:18px;font-weight:800;color:#F1F5F9;">{format_currency(total_modal_all)}</div></div>
          <div><div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:1px;font-weight:700;">Nilai Sekarang</div><div style="font-size:18px;font-weight:800;color:#38BDF8;">{format_currency(total_nilai_all)}</div></div>
          <div><div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:1px;font-weight:700;">Total Gain/Loss</div><div style="font-size:18px;font-weight:800;color:{gain_color};">{"+" if total_gain_rp >= 0 else ""}{format_currency(total_gain_rp)} ({total_gain_pct:+.2f}%)</div></div>
          <div style="margin-left:auto;"><div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:1px;font-weight:700;">Saham Dipegang</div><div style="font-size:18px;font-weight:800;color:#94A3B8;">{len(saham_rows)} emiten</div></div>
        </div>
        ''', unsafe_allow_html=True)

        # Cards Grid
        cols_saham = st.columns(min(len(saham_rows), 3))
        for i, s in enumerate(saham_rows):
            gain_pct = s['gain_pct']
            gain_rp  = s['gain_rp']
            badge_class = "gain-pos" if gain_pct > 0 else "gain-neg" if gain_pct < 0 else "gain-neu"
            gain_arrow  = "▲" if gain_pct > 0 else "▼" if gain_pct < 0 else "—"
            border_color = "rgba(16,185,129,0.2)" if gain_pct > 0 else "rgba(239,68,68,0.2)" if gain_pct < 0 else "rgba(100,116,139,0.2)"
            with cols_saham[i % min(len(saham_rows), 3)]:
                st.markdown(f'''
                <div class="saham-card" style="border-color:{border_color};">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
                    <div>
                      <div class="saham-ticker">{s["t"]}</div>
                      <div class="saham-lot">{s["lembar"]/100:.0f} lot ({s["lembar"]:.0f} lembar)</div>
                    </div>
                    <span class="gain-badge {badge_class}">{gain_arrow} {abs(gain_pct):.2f}%</span>
                  </div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px;">
                    <div style="background:#0F172A;border-radius:8px;padding:8px 10px;">
                      <div style="font-size:10px;color:#334155;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Avg Beli</div>
                      <div style="font-size:14px;font-weight:700;color:#94A3B8;">{format_currency(s["harga_beli"])}</div>
                    </div>
                    <div style="background:#0F172A;border-radius:8px;padding:8px 10px;">
                      <div style="font-size:10px;color:#334155;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Harga Skrg</div>
                      <div style="font-size:14px;font-weight:700;color:#F1F5F9;">{format_currency(s["harga_skrg"])}</div>
                    </div>
                    <div style="background:#0F172A;border-radius:8px;padding:8px 10px;">
                      <div style="font-size:10px;color:#334155;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Modal</div>
                      <div style="font-size:14px;font-weight:700;color:#64748B;">{format_currency(s["total_modal"])}</div>
                    </div>
                    <div style="background:#0F172A;border-radius:8px;padding:8px 10px;">
                      <div style="font-size:10px;color:#334155;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Gain/Loss</div>
                      <div style="font-size:14px;font-weight:700;color:{"#34D399" if gain_rp>=0 else "#F87171"};">{"+" if gain_rp>=0 else ""}{format_currency(gain_rp)}</div>
                    </div>
                  </div>
                </div>
                <br>
                ''', unsafe_allow_html=True)

        # Pie Alokasi
        if pie_data_saham:
            with st.expander("📊 Lihat Alokasi Portofolio"):
                fig_saham = px.pie(pd.DataFrame(pie_data_saham), values='Nilai', names='Ticker', hole=0.5, template="plotly_dark")
                fig_saham.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig_saham, use_container_width=True)

        # Download
        if saham_rows:
            df_csv_saham = pd.DataFrame([{
                "Kode Saham": s["t"], "Total Lot": f"{s['lembar']/100:.0f}",
                "Avg Beli": s["harga_beli"], "Harga Sekarang": s["harga_skrg"],
                "Gain/Loss (%)": f"{s['gain_pct']:.2f}%", "Gain/Loss (Rp)": s["gain_rp"]
            } for s in saham_rows])
            st.download_button("📥 Download Portofolio CSV", data=df_csv_saham.to_csv(index=False).encode('utf-8'), file_name="Portofolio_ROGER.csv", mime="text/csv")
    else:
        st.info("Portofolio masih kosong. Tambahkan saham via form di atas.")

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Analisis Grafik + AI Prediksi ──
    st.markdown('<div class="section-title">🤖 Analisis Grafik + Prediksi AI</div>', unsafe_allow_html=True)
    target = st.text_input("Kode Ticker:", "BBCA.JK", placeholder="Contoh: BBCA.JK / AAPL").upper()
    try:
        h = yf.Ticker(target).history(period="6mo")
        if not h.empty:
            h.index = h.index.tz_localize(None)
            fig_h = go.Figure(data=[go.Candlestick(
                x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'],
                name='Harga', increasing_line_color='#10B981', decreasing_line_color='#EF4444'
            )])
            if len(h) >= 50:
                h['SMA_20'], h['SMA_50'] = ta.sma(h['Close'], length=20), ta.sma(h['Close'], length=50)
                fig_h.add_trace(go.Scatter(x=h.index, y=h['SMA_20'], line=dict(color='#38BDF8', width=1.5), name='MA 20'))
                fig_h.add_trace(go.Scatter(x=h.index, y=h['SMA_50'], line=dict(color='#F59E0B', width=1.5), name='MA 50'))
                df_ml = h[['Close']].copy()
                df_ml['Hari_Ke'] = np.arange(len(df_ml))
                model = LinearRegression().fit(df_ml[['Hari_Ke']], df_ml['Close'])
                hari_terakhir = df_ml['Hari_Ke'].max()
                future_dates  = pd.bdate_range(start=h.index[-1] + timedelta(days=1), periods=7)
                y_pred_future = model.predict(pd.DataFrame({'Hari_Ke': np.arange(hari_terakhir + 1, hari_terakhir + 8)}))
                fig_h.add_trace(go.Scatter(
                    x=[h.index[-1]] + list(future_dates), y=[df_ml['Close'].iloc[-1]] + list(y_pred_future),
                    mode='lines+markers', line=dict(color='#C084FC', width=2.5, dash='dot'),
                    name='Prediksi AI (7 Hari)'
                ))
            fig_h.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                height=450, xaxis_rangeslider_visible=False,
                                margin=dict(l=10, r=10, t=10, b=10),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig_h.update_xaxes(showgrid=False)
            fig_h.update_yaxes(showgrid=True, gridcolor='#1E293B')
            st.plotly_chart(fig_h, use_container_width=True)
            c_rsi, c_info = st.columns([1, 2])
            with c_rsi:
                if len(h) >= 15:
                    rsi_val = ta.rsi(h['Close'], length=14).iloc[-1]
                    rsi_color = "#F87171" if rsi_val >= 70 else "#34D399" if rsi_val <= 30 else "#FBBF24"
                    st.markdown(f'''
                    <div style="text-align:center; padding:16px; background:rgba(15,23,42,0.8); border:1px solid #1E293B; border-radius:14px;">
                      <div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:1px;font-weight:700;">RSI-14</div>
                      <div style="font-size:36px;font-weight:900;color:{rsi_color};">{rsi_val:.1f}</div>
                      <div style="font-size:11px;color:{rsi_color};font-weight:600;">{"🔴 Overbought" if rsi_val >= 70 else "🟢 Oversold" if rsi_val <= 30 else "🟡 Netral"}</div>
                    </div>
                    ''', unsafe_allow_html=True)
            with c_info:
                st.info("🤖 **Prediksi AI Aktif** — Garis ungu putus-putus adalah proyeksi regresi linier untuk 7 hari ke depan. Gunakan sebagai referensi, bukan sebagai satu-satunya acuan keputusan investasi.")
    except Exception: st.error("Gagal memuat grafik. Pastikan ticker valid.")


# ==========================================
# TAB 4 — AI SMART SCANNER
# ==========================================
with tab4:
    st.markdown('<div class="section-title">🧾 AI Smart Scanner — Auto-Fill Nota</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#64748B; font-size:13px; margin-bottom:20px;">Unggah foto struk belanja. AI akan mendeteksi total belanja dan mengisi form transaksi secara otomatis.</p>', unsafe_allow_html=True)

    if "scan_status" in st.session_state:
        status, val, raw_text = st.session_state.scan_status
        if status == "success":
            st.markdown(f'''
            <div style="background:rgba(16,185,129,0.07); border:1px solid rgba(16,185,129,0.2); border-radius:14px; padding:16px 20px; margin-bottom:16px;">
              <div style="font-size:12px; color:#34D399; font-weight:700; text-transform:uppercase; letter-spacing:1px;">✨ Pemindaian Berhasil</div>
              <div style="font-size:28px; font-weight:900; color:#F1F5F9; margin-top:4px;">{format_currency(val)}</div>
              <div style="font-size:12px; color:#64748B; margin-top:4px;">Angka telah disalin ke form. Pindah ke tab 🏦 Dashboard untuk menyimpan.</div>
            </div>
            ''', unsafe_allow_html=True)
            with st.expander("🔍 Lihat Teks Mentah (Raw OCR)"):
                st.text_area("Teks dari gambar:", raw_text, height=150)
        elif status == "fail":
            st.warning("⚠️ AI tidak menemukan angka total yang valid. Silakan input manual.")
            with st.expander("🔍 Lihat Teks Mentah"):
                st.text_area("Teks dari gambar:", raw_text, height=150)

    up = st.file_uploader("Upload Foto Nota (JPG / PNG)", type=["jpg", "png", "jpeg"])
    if up:
        col_img, col_res = st.columns([1, 1.5])
        with col_img:
            st.image(Image.open(up), use_container_width=True, caption="Preview Nota")
        with col_res:
            if st.button("🧠  EKSTRAK TOTAL & AUTO-FILL", use_container_width=True):
                with st.spinner("AI memindai nota..."):
                    try:
                        res = pytesseract.image_to_string(Image.open(up))
                        if res.strip():
                            lines = res.lower().split('\n')
                            possible_totals = []
                            for line in lines:
                                if any(kw in line for kw in ['total', 'jumlah', 'amount', 'pay', 'bayar', 'tagihan', 'rp']):
                                    nums = re.findall(r'\d{1,3}(?:[.,]\d{3})*', line)
                                    for num in nums:
                                        clean_num = re.sub(r'[^\d]', '', num)
                                        if clean_num: possible_totals.append(float(clean_num))
                            total_akhir = max(possible_totals) if possible_totals else 0.0
                            if total_akhir == 0.0:
                                all_nums = re.findall(r'\d{1,3}(?:[.,]\d{3})*', res)
                                valid_nums = [float(re.sub(r'[^\d]', '', n)) for n in all_nums if re.sub(r'[^\d]', '', n)]
                                if valid_nums: total_akhir = max(valid_nums)
                            if total_akhir > 0:
                                st.session_state.auto_nominal = f"{total_akhir:,.0f}".replace(",", ".")
                                st.session_state.scan_status  = ("success", total_akhir, res)
                            else:
                                st.session_state.scan_status  = ("fail", 0, res)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error OCR: Pastikan packages.txt berisi 'tesseract-ocr'. Detail: {e}")


# ==========================================
# TAB 5 — LIVE SCREENER
# ==========================================
with tab5:
    st.markdown('<div class="section-title">⚡ Live Market Screener</div>', unsafe_allow_html=True)
    col_sc1, col_sc2 = st.columns([2, 1])
    with col_sc1:
        watchlist_input = st.text_area("Daftar Ticker (pisah koma):", value="GOTO.JK, BUMI.JK, BBCA.JK, PNLF.JK", height=80)
    with col_sc2:
        max_price = st.number_input("Batas Harga Max (Rp, isi 0 = no limit)", value=0)
        st.markdown('<br>', unsafe_allow_html=True)
        scan_btn = st.button("🔍  MULAI SCAN & ANALISA", use_container_width=True)

    if scan_btn:
        with st.spinner("Mengunduh data & menganalisis..."):
            try:
                tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]
                rekomendasi_beli, netral_jual = [], []

                for ticker in tickers:
                    try:
                        ticker_obj = yf.Ticker(ticker)
                        df_hist = ticker_obj.history(period="6mo")
                        if len(df_hist) >= 50:
                            df_hist.index = df_hist.index.tz_localize(None)
                            close_price = float(df_hist['Close'].iloc[-1])
                            if max_price > 0 and close_price > max_price: continue

                            df_hist['SMA_20'] = ta.sma(df_hist['Close'], length=20)
                            df_hist['SMA_50'] = ta.sma(df_hist['Close'], length=50)
                            df_hist['RSI_14'] = ta.rsi(df_hist['Close'], length=14)
                            macd_df = ta.macd(df_hist['Close'])
                            macd_line, macd_hist, macd_signal = float(macd_df.iloc[-1, 0]), float(macd_df.iloc[-1, 1]), float(macd_df.iloc[-1, 2])
                            ma20, ma50, rsi_14 = float(df_hist['SMA_20'].iloc[-1]), float(df_hist['SMA_50'].iloc[-1]), float(df_hist['RSI_14'].iloc[-1])
                            vol_avg_20, vol_today = float(df_hist['Volume'][-20:].mean()), float(df_hist['Volume'].iloc[-1])
                            ada_lonjakan_volume = vol_today > (vol_avg_20 * 1.5)
                            target_naik = float(df_hist['High'][-40:].max())
                            if target_naik <= close_price * 1.02: target_naik = close_price * 1.12
                            stop_loss = float(df_hist['Low'][-20:].min())
                            if stop_loss >= close_price * 0.98: stop_loss = close_price * 0.95

                            alasan, is_buy = [], False
                            if rsi_14 < 35: alasan.append(f"📉 RSI Jenuh Jual ({rsi_14:.1f})"); is_buy = True
                            elif 35 <= rsi_14 <= 70: alasan.append(f"⚖️ RSI Netral ({rsi_14:.1f})")
                            if ma20 > ma50: alasan.append("📈 MA20 > MA50 (Uptrend)"); is_buy = True
                            if macd_line > macd_signal and macd_hist > 0: alasan.append("📊 MACD Bullish Cross"); is_buy = True
                            if ada_lonjakan_volume: alasan.append(f"🔥 Volume Spike {vol_today/vol_avg_20:.1f}x"); is_buy = True

                            if rsi_14 >= 70: is_buy, status_akhir = False, "SELL"
                            elif ada_lonjakan_volume and (ma20 > ma50 or (macd_line > macd_signal and macd_hist > 0)): status_akhir = "STRONG BUY"
                            elif is_buy: status_akhir = "BUY"
                            else: status_akhir = "WAIT"

                            list_berita = []
                            try:
                                news_data = ticker_obj.news
                                if isinstance(news_data, list) and len(news_data) > 0:
                                    for artikel in news_data[:3]:
                                        raw_title = artikel.get('title')
                                        if raw_title and raw_title.lower() != 'none':
                                            judul     = str(raw_title).strip().replace('[', '').replace(']', '')
                                            link      = artikel.get('link', '#')
                                            publisher = artikel.get('publisher', '').strip()
                                            list_berita.append(f"• [{judul}]({link}){' — ' + publisher if publisher else ''}")
                            except Exception: pass
                            teks_berita = "\n\n".join(list_berita) if list_berita else "_Tidak ada berita tersedia._"

                            h_aman = close_price if close_price > 0 else 1
                            rr = (target_naik - close_price) / (close_price - stop_loss) if (close_price - stop_loss) > 0 else 0

                            rekomendasi_beli.append({
                                "Ticker": ticker, "Harga": close_price, "Target": target_naik, "SL": stop_loss,
                                "Alasan": alasan, "Status": status_akhir, "Berita": teks_berita,
                                "df_chart": df_hist.tail(90), "RSI": rsi_14, "RR": rr,
                                "TP_pct": ((target_naik - close_price) / h_aman) * 100,
                                "SL_pct": ((stop_loss - close_price) / h_aman) * 100,
                            })
                    except Exception: pass

                if rekomendasi_beli:
                    buy_count = sum(1 for r in rekomendasi_beli if "BUY" in r["Status"])
                    st.markdown(f'''
                    <div style="background:rgba(16,185,129,0.07); border:1px solid rgba(16,185,129,0.15); border-radius:14px; padding:14px 18px; margin-bottom:16px; display:flex; gap:20px; flex-wrap:wrap;">
                      <div><div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:1px;font-weight:700;">Saham Dianalisis</div><div style="font-size:20px;font-weight:800;color:#F1F5F9;">{len(rekomendasi_beli)}</div></div>
                      <div><div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:1px;font-weight:700;">Sinyal Beli</div><div style="font-size:20px;font-weight:800;color:#34D399;">{buy_count}</div></div>
                      <div><div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:1px;font-weight:700;">Perlu Dipantau</div><div style="font-size:20px;font-weight:800;color:#FBBF24;">{len(rekomendasi_beli) - buy_count}</div></div>
                    </div>
                    ''', unsafe_allow_html=True)

                    for rec in rekomendasi_beli:
                        status = rec["Status"]
                        status_class = "status-strong" if status == "STRONG BUY" else "status-buy" if status == "BUY" else "status-wait" if status == "WAIT" else "status-sell"
                        status_label = {"STRONG BUY": "🟢 STRONG BUY", "BUY": "🟢 BUY / CICIL", "WAIT": "🟡 WAIT & SEE", "SELL": "🔴 JUAL / HINDARI"}.get(status, status)

                        with st.container():
                            st.markdown(f'''
                            <div class="screener-card">
                              <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:14px;">
                                <div>
                                  <span class="screener-ticker">{rec["Ticker"]}</span>
                                  <span class="screener-price" style="margin-left:10px;">Rp {rec["Harga"]:,.0f}</span>
                                </div>
                                <span class="{status_class}">{status_label}</span>
                              </div>
                              <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-bottom:14px;">
                                <div style="background:#0A1020; border-radius:10px; padding:10px 12px;">
                                  <div style="font-size:9px;color:#334155;text-transform:uppercase;letter-spacing:1px;font-weight:700;">Target TP</div>
                                  <div style="font-size:14px;font-weight:800;color:#34D399;">Rp {rec["Target"]:,.0f}</div>
                                  <div style="font-size:11px;color:#34D399;">+{rec["TP_pct"]:.1f}%</div>
                                </div>
                                <div style="background:#0A1020; border-radius:10px; padding:10px 12px;">
                                  <div style="font-size:9px;color:#334155;text-transform:uppercase;letter-spacing:1px;font-weight:700;">Stop Loss</div>
                                  <div style="font-size:14px;font-weight:800;color:#F87171;">Rp {rec["SL"]:,.0f}</div>
                                  <div style="font-size:11px;color:#F87171;">{rec["SL_pct"]:.1f}%</div>
                                </div>
                                <div style="background:#0A1020; border-radius:10px; padding:10px 12px;">
                                  <div style="font-size:9px;color:#334155;text-transform:uppercase;letter-spacing:1px;font-weight:700;">RSI / R:R</div>
                                  <div style="font-size:14px;font-weight:800;color:#FBBF24;">{rec["RSI"]:.1f}</div>
                                  <div style="font-size:11px;color:#64748B;">Ratio {rec["RR"]:.1f}x</div>
                                </div>
                              </div>
                              <div style="display:flex; gap:6px; flex-wrap:wrap;">
                                {''.join([f'<span style="background:#0A1020;border:1px solid #1E293B;border-radius:6px;padding:4px 10px;font-size:11px;color:#94A3B8;">{a}</span>' for a in rec["Alasan"]])}
                              </div>
                            </div>
                            ''', unsafe_allow_html=True)

                            df_plot = rec['df_chart']
                            fig_sc = go.Figure()
                            fig_sc.add_trace(go.Candlestick(
                                x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                                low=df_plot['Low'], close=df_plot['Close'], name='Harga',
                                increasing_line_color='#10B981', decreasing_line_color='#EF4444'
                            ))
                            fig_sc.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA_20'], line=dict(color='#38BDF8', width=1.5), name='MA20'))
                            fig_sc.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA_50'], line=dict(color='#F59E0B', width=1.5), name='MA50'))
                            fig_sc.add_hline(y=rec['Target'], line=dict(color='#34D399', dash='dot', width=1), annotation_text="TP", annotation_font_color="#34D399")
                            fig_sc.add_hline(y=rec['SL'],     line=dict(color='#F87171', dash='dot', width=1), annotation_text="SL", annotation_font_color="#F87171")
                            fig_sc.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                                height=360, margin=dict(l=10, r=10, t=10, b=10),
                                                xaxis_rangeslider_visible=False,
                                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                            fig_sc.update_xaxes(showgrid=False)
                            fig_sc.update_yaxes(showgrid=True, gridcolor='#1E293B')
                            st.plotly_chart(fig_sc, use_container_width=True)

                            with st.expander(f"📰 Berita Terkini {rec['Ticker']}"):
                                st.markdown(rec['Berita'])
                            st.markdown('<hr>', unsafe_allow_html=True)
                else:
                    st.info("Tidak ada saham yang memenuhi kriteria scan saat ini.")

            except Exception as e:
                st.error(f"Kesalahan saat scanning: {e}")


# ==========================================
# TAB 6 — PENGATURAN
# ==========================================
with tab6:
    st.markdown('<div class="section-title">⚙️ Pengaturan Sistem</div>', unsafe_allow_html=True)
    col_set1, col_set2, col_set3 = st.columns(3)

    with col_set1:
        with st.expander("🏷️ Kelola Kategori Transaksi", expanded=True):
            new_kat = st.text_input("Nama Kategori Baru", placeholder="Contoh: Bensin")
            if st.button("➕ Tambah Kategori", use_container_width=True):
                if new_kat and new_kat not in st.session_state.kategori_list:
                    st.session_state.kategori_list.append(new_kat)
                    save_config()
                    st.success(f"✅ '{new_kat}' ditambahkan!")
                    st.rerun()
                elif new_kat in st.session_state.kategori_list:
                    st.warning("Kategori sudah ada.")
            st.markdown('<br>', unsafe_allow_html=True)
            kat_hapus = st.selectbox("Kategori yang ingin dihapus:", st.session_state.kategori_list)
            if st.button("❌ Hapus Kategori", use_container_width=True):
                if len(st.session_state.kategori_list) > 1:
                    st.session_state.kategori_list.remove(kat_hapus)
                    save_config()
                    st.success(f"✅ '{kat_hapus}' dihapus!")
                    st.rerun()
                else: st.error("Minimal 1 kategori harus tersisa.")

            st.markdown('<br>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:11px;color:#475569;">Total: {len(st.session_state.kategori_list)} kategori aktif</div>', unsafe_allow_html=True)
            for k in st.session_state.kategori_list:
                st.markdown(f'<span style="display:inline-block;margin:2px;padding:3px 10px;background:#0F172A;border:1px solid #1E293B;border-radius:999px;font-size:11px;color:#64748B;">{k}</span>', unsafe_allow_html=True)

    with col_set2:
        with st.expander("🚨 Atur Limit Alarm Budget", expanded=True):
            kategori_budget = st.selectbox("Pilih Kategori", st.session_state.kategori_list, key="cat_budget")
            limit_baru = st.number_input("Limit per Bulan (Rp)", min_value=0, step=50000, value=500000)
            if st.button("💾 Simpan Limit", use_container_width=True):
                st.session_state.budgets[kategori_budget] = limit_baru
                save_config()
                st.success("✅ Limit disimpan!")
                st.rerun()
            st.markdown('<br>', unsafe_allow_html=True)
            if st.session_state.budgets:
                st.markdown('<div style="font-size:11px;color:#475569;margin-bottom:8px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">Alarm Aktif:</div>', unsafe_allow_html=True)
                for kat, lim in st.session_state.budgets.items():
                    st.markdown(f'<div style="display:flex;justify-content:space-between;padding:6px 10px;background:#0F172A;border:1px solid #1E293B;border-radius:8px;margin-bottom:4px;"><span style="font-size:12px;color:#94A3B8;">{kat}</span><span style="font-size:12px;font-weight:700;color:#FBBF24;">{format_currency(lim)}</span></div>', unsafe_allow_html=True)
                budget_hapus = st.selectbox("Hapus alarm untuk:", list(st.session_state.budgets.keys()))
                if st.button("❌ Matikan Alarm", use_container_width=True):
                    del st.session_state.budgets[budget_hapus]
                    save_config()
                    st.success("✅ Alarm dimatikan!"); st.rerun()
            else: st.info("Belum ada alarm aktif.")

    with col_set3:
        with st.expander("🔐 Keamanan & PIN", expanded=True):
            old_pin = st.text_input("PIN Lama", type="password", max_chars=6)
            new_pin = st.text_input("PIN Baru (6 angka)", type="password", max_chars=6)
            new_pin2 = st.text_input("Konfirmasi PIN Baru", type="password", max_chars=6)
            if st.button("🔑 Ubah PIN Sekarang", use_container_width=True):
                if old_pin != st.session_state.saved_pin:
                    st.error("❌ PIN lama salah.")
                elif len(new_pin) != 6 or not new_pin.isdigit():
                    st.error("❌ PIN baru harus 6 digit angka.")
                elif new_pin != new_pin2:
                    st.error("❌ Konfirmasi PIN tidak cocok.")
                else:
                    st.session_state.saved_pin = new_pin
                    save_config()
                    st.success("✅ PIN berhasil diubah!")

            st.markdown('<br>', unsafe_allow_html=True)
            st.markdown('''
            <div style="background:#0F172A; border:1px solid #1E293B; border-radius:12px; padding:12px 14px;">
              <div style="font-size:11px; color:#475569; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">Info Sesi</div>
              <div style="font-size:12px; color:#64748B;">Sesi: <span style="color:#94A3B8; font-weight:600;">Aktif</span></div>
              <div style="font-size:12px; color:#64748B; margin-top:4px;">Proteksi: <span style="color:#34D399; font-weight:600;">PIN 6-Digit ✓</span></div>
            </div>
            ''', unsafe_allow_html=True)
