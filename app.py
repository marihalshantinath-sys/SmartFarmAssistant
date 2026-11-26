import sqlite3
from datetime import date
import numpy as np
import pandas as pd
from PIL import Image
import requests
import streamlit as st

st.set_page_config(
    page_title="SmartFarmAssistant V3.0",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- STRUCTURED HIGH-CONTRAST CARD & STEP-BADGE UI ---
CSS_STYLE = (
    "<style>"
    "[data-testid='stHeader'] { background: transparent !important; height: 2.5rem !important; }"
    ".stApp, [data-testid='stAppViewContainer'] { background-color: #0B111A !important; color: #FFFFFF !important; overflow-x: hidden !important; }"
    ".block-container { padding: 3.8rem 0.85rem 2rem 0.85rem !important; max-width: 100% !important; }"
    "p, span, label, div, li, .stMarkdown, [data-testid='stWidgetLabel'] p { color: #F1F5F9 !important; }"
    "h1, h2, h3, h4, h5 { color: #4ADE80 !important; font-weight: 800 !important; }"
    "input, textarea, [data-baseweb='select'] > div, [data-baseweb='input'] > div { background-color: #162232 !important; color: #FFFFFF !important; border: 1.5px solid #2DD4BF !important; border-radius: 10px !important; font-size: 16px !important; min-height: 44px !important; }"
    "[data-baseweb='select'] span { color: #FFFFFF !important; }"
    "ul[role='listbox'] { background-color: #162232 !important; color: #FFFFFF !important; }"
    "ul[role='listbox'] li:hover { background-color: #22C55E !important; color: #09131D !important; }"
    ".hero-card { background: linear-gradient(135deg, #102438, #09131E); border: 1.5px solid #22C55E; border-radius: 16px; padding: 18px 20px; margin-bottom: 14px; box-shadow: 0 4px 20px rgba(34,197,94,0.12); }"
    ".hero-title { font-size: 1.65rem; font-weight: 900; margin: 0; line-height: 1.2; }"
    ".hero-green { color: #4ADE80 !important; }"
    ".hero-white { color: #FFFFFF !important; }"
    ".version-badge { background-color: #22C55E; color: #061019 !important; font-size: 0.82rem; font-weight: 900; padding: 3px 9px; border-radius: 8px; margin-left: 6px; }"
    ".hero-sub { color: #CBD5E1 !important; font-size: 0.9rem; margin-top: 6px; }"
    ".step-header { background: #132234; border-left: 4px solid #38BDF8; padding: 8px 12px; border-radius: 0 8px 8px 0; margin: 10px 0 8px 0; font-weight: 800; color: #E0F2FE !important; font-size: 0.95rem; }"
    ".step-pill { background: #0284C7; color: #FFFFFF !important; padding: 2px 8px; border-radius: 6px; font-size: 0.76rem; font-weight: 900; margin-right: 8px; text-transform: uppercase; }"
    ".zone-worker { background: #102622; border: 1.5px solid #22C55E; border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; }"
    ".zone-farmer { background: #101E33; border: 1.5px solid #38BDF8; border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; }"
    ".worker-card { background-color: #142234; border: 1.5px solid #22C55E; border-radius: 12px; padding: 14px; margin-bottom: 10px; }"
    ".badge-verified { background-color: #22C55E; color: #061019 !important; padding: 2px 8px; border-radius: 6px; font-weight: 800; font-size: 0.76rem; }"
    ".badge-free { background-color: #0284C7; color: #FFFFFF !important; padding: 2px 8px; border-radius: 6px; font-weight: 800; font-size: 0.76rem; margin-left: 6px; }"
    ".call-btn { display: inline-block; background: #22C55E; color: #061019 !important; font-weight: 900; padding: 5px 12px; border-radius: 8