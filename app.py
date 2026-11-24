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

# --- MOBILE-FIRST HIGH-CONTRAST DARK BLUEPRINT & EMERALD UI ---
st.markdown(
    """
<style>
    /* Global dark background & crisp white text */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0D141F !important;
        background-image: 
            linear-gradient(rgba(52, 211, 153, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(52, 211, 153, 0.05) 1px, transparent 1px);
        background-size: 28px 28px;
        color: #FFFFFF !important;
        overflow-x: hidden !important;
    }

    /* Reduce excessive side padding on mobile & desktop */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    p, span, label, div, li, .stMarkdown, [data-testid="stWidgetLabel"] p {
        color: #F1F5F9 !important;
    }
    h1, h2, h3, h4, h5 {
        color: #4ADE80 !important;
        font-weight: 800 !important;
    }

    /* 16px font on inputs prevents unwanted auto-zoom on mobile phones */
    input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div {
        background-color: #1A2636 !important;
        color: #FFFFFF !important;
        border: 1px solid #34D399 !important;
        border-radius: 10px !important;
        font-size: 16px !important;
        min-height: 44px !important;
    }
    [data-baseweb="select"] span { color: #FFFFFF !important; font-size: 15px !important; }
    ul[role="listbox"] {
        background-color: #1A2636 !important;
        color: #FFFFFF !important;
    }
    ul[role="listbox"] li:hover {
        background-color: #22C55E !important;
        color: #09131D !important;
    }

    /* Hero Banner */
    .hero-card {
        background: linear-gradient(135deg, #132032, #0B121C);
        border: 1.5px solid #22C55E;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 6px 24px rgba(34, 197, 94, 0.18);
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 10px;
    }
    .hero-title { font-size: 1.85rem; font-weight: 900; margin: 0; line-height: 1.2; }
    .hero-green { color: #4ADE80 !important; }
    .hero-white { color: #FFFFFF !important; }
    .version-badge {
        background-color: #22C55E;
        color: #07111A !important;
        font-size: 0.85rem;
        font-weight: 900;
        padding: 3px 9px;
        border-radius: 8px;
        margin-left: 6px;
        vertical-align: middle;
    }
    .hero-sub { color: #CBD5E1 !important; font-size: 0.9rem; margin-top: 6px; line-height: 1.4; }

    /* Mobile-Friendly Wrapping Navigation Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #152132;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(74, 222, 128, 0.35);
        flex-wrap: wrap !important;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E2D42;
        border-radius: 8px;
        color: #FFFFFF !important;
        font-weight: 700;
        padding: 10px 12px;
        font-size: 0.9rem !important;
        flex-grow: 1;
        justify-content: center;
    }
    .stTabs [aria-selected="true"] {
        background: #22C55E !important;
        color: #061019 !important;
        font-weight: 800 !important;
    }
    .stTabs [aria-selected="true"] p { color: #061019 !important; }

    /* Metric Cards */
    [data-testid="stMetric"] {
        background-color: #152233 !important;
        border: 1px solid #22C55E !important;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 6px;
    }
    [data-testid="stMetricLabel"] p { color: #94A3B8 !important; font-size: 0.85rem !important; }
    [data-testid="stMetricValue"] div { color: #4ADE80 !important; font-size: 1.45rem !important; font-weight: 900 !important; }

    /* Forms & Expanders */
    [data-testid="stForm"],