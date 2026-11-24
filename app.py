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

# --- HIGH-CONTRAST DARK BLUEPRINT & EMERALD UI (100% VISIBLE TEXT) ---
st.markdown(
    """
<style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0D141F !important;
        background-image: 
            linear-gradient(rgba(52, 211, 153, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(52, 211, 153, 0.05) 1px, transparent 1px);
        background-size: 30px 30px;
        color: #FFFFFF !important;
    }
    p, span, label, div, li, .stMarkdown, [data-testid="stWidgetLabel"] p {
        color: #F1F5F9 !important;
    }
    h1, h2, h3, h4, h5 {
        color: #4ADE80 !important;
        font-weight: 800 !important;
    }
    input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div {
        background-color: #1A2636 !important;
        color: #FFFFFF !important;
        border: 1px solid #34D399 !important;
        border-radius: 8px !important;
    }
    [data-baseweb="select"] span { color: #FFFFFF !important; }
    ul[role="listbox"] {
        background-color: #1A2636 !important;
        color: #FFFFFF !important;
    }
    ul[role="listbox"] li:hover {
        background-color: #22C55E !important;
        color: #09131D !important;
    }
    .hero-card {
        background: linear-gradient(135deg, #132032, #0B121C);
        border: 1.5px solid #22C55E;
        border-radius: 16px;
        padding: 20px 26px;
        margin-bottom: 18px;
        box-shadow: 0 6px 24px rgba(34, 197, 94, 0.18);
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 14px;
    }
    .hero-title { font-size: 2.0rem; font-weight: 900; margin: 0; line-height: 1.15; }
    .hero-green { color: #4ADE80 !important; }
    .hero-white { color: #FFFFFF !important; }
    .version-badge {
        background-color: #22C55E;
        color: #07111A !important;
        font-size: 0.9rem;
        font-weight: 900;
        padding: 4px 10px;
        border-radius: 8px;
        margin-left: 8px;
    }
    .hero-sub { color: #CBD5E1 !important; font-size: 0.95rem; margin-top: 6px; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #152132;
        padding: 8px;
        border-radius: 12px;
        border: 1px solid rgba(74, 222, 128, 0.35);
        flex-wrap: wrap;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1E2D42;
        border-radius: 8px;
        color: #FFFFFF !important;
        font-weight: 600;
        padding: 8px 14px;
    }
    .stTabs [aria-selected="true"] {
        background: #22C55E !important;
        color: #061019 !important;
        font-weight: 800 !important;
    }
    .stTabs [aria-selected="true"] p { color: #061019 !important; }
    [data-testid="stMetric"] {
        background-color: #152233 !important;
        border: 1px solid #22C55E !important;
        border-radius: 12px;
        padding: 14px 18px;
    }
    [data-testid="stMetricLabel"] p { color: #94A3B8 !important; font-weight: 600 !important; }
    [data-testid="stMetricValue"] div { color: #4ADE80 !important; font-weight: 900 !important; }
    [data-testid="stForm"], [data-testid="stExpander"] {
        background-color: #131E2E !important;
        border: 1px solid rgba(52, 211, 153, 0.35) !important;
        border-radius: 14px;
        padding: 16px;
    }
    .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
        background: #22C55E !important;
        color: #061019 !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.3rem !important;
    }
    .stButton > button p, .stFormSubmitButton > button p, .stDownloadButton > button p {
        color: #061019 !important;
        font-weight: 800 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


# --- DATABASE SETUP WITH AUTO-SCHEMA MIGRATION ---
def init_db():
    conn = sqlite3.connect("smart_farm.db")
    c = conn.cursor()
    c.execute("PRAGMA table_info(advisory_logs)")
    existing_cols = [row[1] for row in c.fetchall()]
    required_cols = [
        "id", "log_date", "plot_name", "soil_type", "environment",
        "crop_selected", "soil_moisture", "irrigation_liters", "notes",
    ]
    if existing_cols and existing_cols != required_cols:
        c.execute("DROP TABLE IF EXISTS advisory_logs")

    c.execute("""CREATE TABLE IF NOT EXISTS advisory_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT, plot_name TEXT, soil_type TEXT, environment TEXT,
            crop_selected TEXT, soil_moisture REAL, irrigation_liters REAL, notes TEXT
        )""")
    c.execute("""CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE, role TEXT, daily_wage REAL, phone TEXT
        )""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_date TEXT, worker_name TEXT, status TEXT, task_assigned TEXT, wage_earned REAL
        )""")
    c.execute("""CREATE TABLE IF NOT EXISTS machinery_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT, machine_name TEXT, operation_type TEXT,
            hours_run REAL, fuel_liters REAL, fuel_cost REAL, next_service_hrs REAL
        )""")
    c.execute("""CREATE TABLE IF NOT EXISTS farm_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exp_date TEXT, crop_name TEXT, category TEXT, amount REAL, notes TEXT
        )""")
    conn.commit()
    conn.close()


init_db()

# --- DISTRICT COORDINATES & LIVE OPEN-METEO WEATHER API ---
DISTRICTS = {
    "Belagavi, Karnataka": (15.8497, 74.4977),
    "Dharwad / Hubballi, Karnataka": (15.4589, 75.0078),
    "Vijayapura, Karnataka": (16.8302, 75.7100),
    "Bagalkot, Karnataka": (16.1691, 75.6615),
    "Chikkamagaluru, Karnataka": (13.3161, 75.7720),
    "Bengaluru Rural, Karnataka": (13.2846, 77.6078),
    "Kolhapur, Maharashtra": (16.7050, 74.2433),
    "Custom GPS Coordinates": (15.8497, 74.4977),
}


@st.cache_data(ttl=900)
def fetch_live_weather(lat: float, lon: float):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        "hourly": "precipitation_probability,precipitation,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "forecast_days": 3,
        "timezone": "auto",
    }
    try:
        res = requests.get(url, params=params, timeout=6)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None


def classify_environment(temp_c: float, rain_4h_mm: float, rain_prob_4h: float):
    if rain_4h_mm >= 1.0 or rain_prob_4h >= 60:
        return "Monsoon / Heavy Rain (High Moisture)"
    elif temp_c >= 34.0:
        return "Hot & Dry (Summer / High Temp > 34°C)"
    elif temp_c <= 22.0:
        return "Cool & Dry (Rabi / Winter)"
    return "Warm & Humid (Pre-Monsoon / Moderate)"


# --- COMPLETE COMMERCIAL FERTILIZER & AGRO-CHEMICAL DATABASE ---
ALL_FERTILIZERS = [
    {"Name": "Urea (46-0-0)", "Type": "Granular Nitrogen", "Bag Size": "45 kg", "Primary Role": "Fast vegetative leaf & stem growth", "Standard Acre Dose": "50–110 kg/acre (split doses)"},
    {"Name": "DAP (18-46-0)", "Type": "Granular Phosphorus + N", "Bag Size": "50 kg", "Primary Role": "Strong root establishment & flowering", "Standard Acre Dose": "45–85 kg/acre (basal dose)"},
    {"Name": "MOP - Muriate of Potash (0-0-60)", "Type": "Granular Potassium", "Bag Size": "50 kg", "Primary Role": "Grain weight, fruit shine & drought resistance", "Standard Acre Dose": "30–65 kg/acre"},
    {"Name": "SSP - Single Super Phosphate (16% P + 11% S)", "Type": "Granular P + Sulphur + Ca", "Bag Size": "50 kg", "Primary Role": "Best for oilseeds (Groundnut/Soybean) & pulses", "Standard Acre Dose": "100–150 kg/acre"},
    {"Name": "NPK 10:26:26 / 12:32:16 Complex", "Type": "Balanced Granular NPK", "Bag Size": "50 kg", "Primary Role": "All-in-one basal nutrition for vegetables & cash crops", "Standard Acre Dose": "50–100 kg/acre"},
    {"Name": "NPK 20:20:0:13 (Ammonium Phosphate Sulphate)", "Type": "Granular N + P + Sulphur", "Bag Size": "50 kg", "Primary Role": "Boosts protein/oil content & early vigor", "Standard Acre Dose": "50–100 kg/acre"},
    {"Name": "NPK 19:19:19 (Water Soluble)", "Type": "Foliar / Drip Soluble", "Bag Size": "1 kg / 25 kg", "Primary Role": "Quick vegetative boost via foliar spray or drip", "Standard Acre Dose": "5 g/Liter (75 g per 15L pump)"},
    {"Name": "NPK 00:52:34 (Mono Potassium Phosphate)", "Type": "Foliar / Drip Soluble", "Bag Size": "1 kg / 25 kg", "Primary Role": "Prevents flower drop & boosts fruit/grain setting", "Standard Acre Dose": "5 g/Liter (75 g per 15L pump)"},
    {"Name": "NPK 00:00:50 (Sulphate of Potash - SOP)", "Type": "Foliar / Drip Soluble", "Bag Size": "1 kg / 25 kg", "Primary Role": "Bulb/fruit enlargement, sweetness & shelf life", "Standard Acre Dose": "5 g/Liter (75 g per 15L pump)"},
    {"Name": "Zinc Sulphate (21% / 33%) + Boron (20%)", "Type": "Micronutrient Mix", "Bag Size": "5 kg / 1 kg", "Primary Role": "Cures leaf yellowing & hollow fruit/pod issues", "Standard Acre Dose": "10 kg/acre soil OR 1.5 g/L foliar"},
]

ALL_CHEMICALS = {
    "Fungal Leaf Spot / Early & Late Blight": {
        "best_chemical": "Mancozeb 75% WP (Contact) OR Azoxystrobin + Difenoconazole (Systemic)",
        "dose_per_liter": 2.5,
        "unit": "g / ml",
        "foliar_booster": "Add 19:19:19 (3 g/L) + Spreader-Sticker (0.5 ml/L) for faster leaf recovery",
        "precaution": "Ensure 4-hour rain-free window; avoid spraying in midday heat.",
    },
    "Powdery Mildew / Rust (White/Orange Powder on Leaves)": {
        "best_chemical": "Wettable Sulphur 80% WDG OR Hexaconazole 5% EC",
        "dose_per_liter": 2.0,
        "unit": "g / ml",
        "foliar_booster": "Potassium Silicate (2 ml/L) to strengthen leaf cuticle",
        "precaution": "Do not apply Sulphur when temperature exceeds 35°C.",
    },
    "Sucking Pests (Thrips, Aphids, Whitefly, Leaf Curl)": {
        "best_chemical": "Imidacloprid 17.8% SL OR Thiamethoxam 25% WG + Neem Oil (1500 ppm)",
        "dose_per_liter": 0.5,
        "unit": "ml / g",
        "foliar_booster": "Seaweed Extract (2 ml/L) + Boron (1 g/L) to revive curled new shoots",
        "precaution": "Spray underside of leaves thoroughly during early morning or evening.",
    },
    "Caterpillars / Bollworm / Stem Borer / Fruit Borer": {
        "best_chemical": "Emamectin Benzoate 5% SG OR Chlorantraniliprole 18.5% SC",
        "dose_per_liter": 0.4,
        "unit": "g / ml",
        "foliar_booster": "Calcium Nitrate (3 g/L) to harden fruit/boll skin against boring",
        "precaution": "Observe 7–10 days Pre-Harvest Interval (PHI) before picking produce.",
    },
    "Nitrogen / Iron / Zinc Deficiency (Yellowing Leaves)": {
        "best_chemical": "Chelated Micronutrient Mix (Zn + Fe + Mn + Mg) + Urea / 19:19:19 Foliar",
        "dose_per_liter": 2.0,
        "unit": "g",
        "foliar_booster": "Soil basal: DAP (50 kg/acre) + Zinc Sulphate (10 kg/acre)",
        "precaution": "Check soil drainage first; waterlogging also causes yellowing.",
    },
    "Root Rot / Wilt (Soil-Borne Fungal Infection)": {
        "best_chemical": "Copper Oxychloride 50% WP (Drenching) OR Carbendazim 50% WP + Trichoderma",
        "dose_per_liter": 3.0,
        "unit": "g",
        "foliar_booster": "Humic Acid (2 ml/L) root drench to stimulate new white roots",
        "precaution": "Apply directly to the root zone (soil drenching), not on dry leaves.",
    },
}


def analyze_plant_photo(img: Image.Image):
    """Analyzes leaf RGB color distribution to detect healthy green vs yellowing/blight/spots."""
    small = img.convert("RGB").resize((160, 160))
    arr = np.asarray(small, dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    total_pixels = arr.shape[0] * arr.shape[1]
    healthy_green = np.sum((g > r * 1.08) & (g > b * 1.15) & (g > 55)) / total_pixels * 100
    yellow_chlorosis = np.sum((r > 135) & (g > 125) & (b < 95) & (np.abs(r - g) < 45)) / total_pixels * 100
    brown_spots = np.sum((r > 70) & (r < 175) & (g > 40) & (g < 125) & (b < 75) & (r > g * 1.18)) / total_pixels * 100
    pale_white = np.sum((r > 185) & (g > 185) & (b > 175)) / total_pixels * 100

    if brown_spots > 14.0:
        condition = "Fungal Leaf Spot / Early & Late Blight"
        summary = f"Detected {brown_spots:.1f}% brown/necrotic leaf spot lesions."
    elif yellow_chlorosis > 18.0:
        condition = "Nitrogen / Iron / Zinc Deficiency (Yellowing Leaves)"
        summary = f"Detected {yellow_chlorosis:.1f}% leaf chlorosis (yellowing tissue)."
    elif pale_white > 24.0 and healthy_green < 40.0:
        condition = "Powdery Mildew / Rust (White/Orange Powder on Leaves)"
        summary = f"Detected {pale_white:.1f}% pale/powdery surface coating on foliage."
    elif healthy_green < 22.0:
        condition = "Sucking Pests (Thrips, Aphids, Whitefly, Leaf Curl)"
        summary = f"Low healthy chlorophyll coverage ({healthy_green:.1f}%)—possible leaf curl or pest stress."
    else:
        condition = "Healthy Crop Foliage (Preventive Growth Stage)"
        summary = f"Strong healthy green foliage ({healthy_green:.1f}% chlorophyll index)."

    return condition, summary, healthy_green, yellow_chlorosis, brown_spots


# --- AGRONOMY KNOWLEDGE BASE ---
SOIL_PROFILES = {
    "Black Cotton Soil (Regur)": {
        "water_holding": "High (Retains moisture long; avoid over-irrigation)",
        "best_crops": ["Sugarcane", "Cotton", "Soybean", "Jowar (Sorghum)", "Chickpea (Chana)", "Turmeric"],
        "fertilizer_tip": "Rich in calcium & magnesium, low in nitrogen & phosphorus. Apply split Nitrogen + DAP/SSP.",
    },
    "Red Loamy Soil": {
        "water_holding": "Moderate (Good drainage; needs regular scheduled irrigation)",
        "best_crops": ["Groundnut", "Maize", "Ragi", "Chilli", "Tomato", "Pomegranate", "Arecanut"],
        "fertilizer_tip": "Responds well to organic FYM/compost + balanced NPK (19:19:19) and micronutrients (Zinc/Boron).",
    },
    "Alluvial / Silt Loam Soil": {
        "water_holding": "Moderate-High (Very fertile & easy to till)",
        "best_crops": ["Paddy (Rice)", "Wheat", "Banana", "Sugarcane", "Onion", "Potato", "Vegetables"],
        "fertilizer_tip": "High potash availability; focus on Nitrogen split doses and organic green manuring.",
    },
    "Sandy / Light Soil": {
        "water_holding": "Low (Drains fast; ideal for drip irrigation)",
        "best_crops": ["Watermelon", "Muskmelon", "Groundnut", "Bajra (Pearl Millet)", "Carrot", "Coconut"],
        "fertilizer_tip": "Use frequent small fertigation doses (drip) + heavy organic compost to prevent nutrient leaching.",
    },
    "Laterite / Hilly Plantation Soil": {
        "water_holding": "Moderate (Acidic pH; well-drained)",
        "best_crops": ["Coffee", "Black Pepper", "Arecanut", "Cashew", "Ginger", "Pineapple"],
        "fertilizer_tip": "Apply agricultural lime if pH < 5.5, plus rock phosphate and neem cake.",
    },
}

ENV_CONDITIONS = {
    "Hot & Dry (Summer / High Temp > 34°C)": {
        "irrigation_factor":
