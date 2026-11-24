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

# --- MOBILE-RESPONSIVE HIGH-CONTRAST UI (TOP HEADER & PHONE SCREEN FIXED) ---
CSS_STYLE = (
    "<style>"
    "[data-testid='stHeader'] { background: transparent !important; height: 2.5rem !important; }"
    ".stApp, [data-testid='stAppViewContainer'] { background-color: #0D141F !important; color: #FFFFFF !important; overflow-x: hidden !important; }"
    ".block-container { padding: 3.8rem 0.8rem 2rem 0.8rem !important; max-width: 100% !important; }"
    "p, span, label, div, li, .stMarkdown, [data-testid='stWidgetLabel'] p { color: #F1F5F9 !important; }"
    "h1, h2, h3, h4, h5 { color: #4ADE80 !important; font-weight: 800 !important; }"
    "input, textarea, [data-baseweb='select'] > div, [data-baseweb='input'] > div { background-color: #1A2636 !important; color: #FFFFFF !important; border: 1px solid #34D399 !important; border-radius: 10px !important; font-size: 16px !important; min-height: 44px !important; }"
    "[data-baseweb='select'] span { color: #FFFFFF !important; }"
    "ul[role='listbox'] { background-color: #1A2636 !important; color: #FFFFFF !important; }"
    "ul[role='listbox'] li:hover { background-color: #22C55E !important; color: #09131D !important; }"
    ".hero-card { background: linear-gradient(135deg, #132032, #0B121C); border: 1.5px solid #22C55E; border-radius: 14px; padding: 16px 18px; margin-bottom: 14px; }"
    ".hero-title { font-size: 1.6rem; font-weight: 900; margin: 0; line-height: 1.2; }"
    ".hero-green { color: #4ADE80 !important; }"
    ".hero-white { color: #FFFFFF !important; }"
    ".version-badge { background-color: #22C55E; color: #07111A !important; font-size: 0.85rem; font-weight: 900; padding: 3px 8px; border-radius: 8px; margin-left: 6px; }"
    ".hero-sub { color: #CBD5E1 !important; font-size: 0.88rem; margin-top: 6px; }"
    ".stTabs [data-baseweb='tab-list'] { gap: 6px; background-color: #152132; padding: 6px; border-radius: 12px; border: 1px solid rgba(74, 222, 128, 0.35); flex-wrap: wrap !important; }"
    ".stTabs [data-baseweb='tab'] { background-color: #1E2D42; border-radius: 8px; color: #FFFFFF !important; font-weight: 700; padding: 8px 10px; font-size: 0.85rem !important; flex-grow: 1; justify-content: center; }"
    ".stTabs [aria-selected='true'] { background: #22C55E !important; color: #061019 !important; font-weight: 800 !important; }"
    ".stTabs [aria-selected='true'] p { color: #061019 !important; }"
    "[data-testid='stMetric'] { background-color: #152233 !important; border: 1px solid #22C55E !important; border-radius: 12px; padding: 12px 14px; }"
    "[data-testid='stMetricLabel'] p { color: #94A3B8 !important; font-size: 0.85rem !important; }"
    "[data-testid='stMetricValue'] div { color: #4ADE80 !important; font-size: 1.4rem !important; font-weight: 900 !important; }"
    "[data-testid='stForm'], [data-testid='stExpander'] { background-color: #131E2E !important; border: 1px solid rgba(52, 211, 153, 0.35) !important; border-radius: 12px; padding: 14px; }"
    ".stButton > button, .stFormSubmitButton > button, .stDownloadButton > button { background: #22C55E !important; color: #061019 !important; font-weight: 800 !important; border: none !important; border-radius: 10px !important; min-height: 46px !important; width: 100% !important; font-size: 1rem !important; }"
    ".stButton > button p, .stFormSubmitButton > button p, .stDownloadButton > button p { color: #061019 !important; font-weight: 800 !important; }"
    "@media (max-width: 768px) { .block-container { padding-top: 4.2rem !important; } .hero-title { font-size: 1.4rem !important; } .stTabs [data-baseweb='tab'] { width: 48% !important; } [data-testid='column'] { width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important; } }"
    "</style>"
)
st.markdown(CSS_STYLE, unsafe_allow_html=True)


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

    c.execute(
        "CREATE TABLE IF NOT EXISTS advisory_logs ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, plot_name TEXT, "
        "soil_type TEXT, environment TEXT, crop_selected TEXT, "
        "soil_moisture REAL, irrigation_liters REAL, notes TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS workers ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, "
        "role TEXT, daily_wage REAL, phone TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS attendance ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, work_date TEXT, worker_name TEXT, "
        "status TEXT, task_assigned TEXT, wage_earned REAL)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS farm_expenses ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, exp_date TEXT, crop_name TEXT, "
        "category TEXT, amount REAL, notes TEXT)"
    )
    conn.commit()
    conn.close()


init_db()

# --- DISTRICTS & LIVE OPEN-METEO WEATHER API ---
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
        "hourly": "precipitation_probability,precipitation",
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


# --- COMPLETE FERTILIZER & CHEMICAL KNOWLEDGE BASE ---
ALL_FERTILIZERS = [
    {"Name": "Urea (46-0-0)", "Type": "Granular N", "Bag": "45 kg", "Role": "Fast leaf & stem growth", "Acre Dose": "50–110 kg/acre"},
    {"Name": "DAP (18-46-0)", "Type": "Granular P+N", "Bag": "50 kg", "Role": "Root growth & flowering", "Acre Dose": "45–85 kg/acre"},
    {"Name": "MOP (0-0-60)", "Type": "Granular K", "Bag": "50 kg", "Role": "Grain weight & fruit shine", "Acre Dose": "30–65 kg/acre"},
    {"Name": "SSP (16% P + 11% S)", "Type": "Granular P+S", "Bag": "50 kg", "Role": "Best for oilseeds & pulses", "Acre Dose": "100–150 kg/acre"},
    {"Name": "NPK 10:26:26 / 12:32:16", "Type": "Complex NPK", "Bag": "50 kg", "Role": "All-in-one basal nutrition", "Acre Dose": "50–100 kg/acre"},
    {"Name": "NPK 19:19:19", "Type": "Water Soluble", "Bag": "1 / 25 kg", "Role": "Quick foliar/drip boost", "Acre Dose": "5 g/L (75 g/pump)"},
    {"Name": "NPK 00:52:34", "Type": "Water Soluble", "Bag": "1 / 25 kg", "Role": "Stops flower drop", "Acre Dose": "5 g/L (75 g/pump)"},
    {"Name": "NPK 00:00:50 (SOP)", "Type": "Water Soluble", "Bag": "1 / 25 kg", "Role": "Fruit/bulb size & sweetness", "Acre Dose": "5 g/L (75 g/pump)"},
    {"Name": "Zinc Sulphate + Boron", "Type": "Micronutrient", "Bag": "1 / 5 kg", "Role": "Cures leaf yellowing", "Acre Dose": "10 kg/acre or 1.5 g/L"},
]

ALL_CHEMICALS = {
    "Fungal Leaf Spot / Early & Late Blight": {
        "best_chemical": "Mancozeb 75% WP OR Azoxystrobin + Difenoconazole",
        "dose_per_liter": 2.5,
        "unit": "g / ml",
        "foliar_booster": "Add 19:19:19 (3 g/L) + Spreader-Sticker (0.5 ml/L)",
        "precaution": "Ensure 4-hour rain-free window; avoid midday heat.",
    },
    "Powdery Mildew / Rust (White/Orange Powder)": {
        "best_chemical": "Wettable Sulphur 80% WDG OR Hexaconazole 5% EC",
        "dose_per_liter": 2.0,
        "unit": "g / ml",
        "foliar_booster": "Potassium Silicate (2 ml/L) to strengthen leaves",
        "precaution": "Do not apply Sulphur when temp exceeds 35°C.",
    },
    "Sucking Pests (Thrips, Aphids, Whitefly, Leaf Curl)": {
        "best_chemical": "Imidacloprid 17.8% SL OR Thiamethoxam + Neem Oil",
        "dose_per_liter": 0.5,
        "unit": "ml / g",
        "foliar_booster": "Seaweed Extract (2 ml/L) + Boron (1 g/L)",
        "precaution": "Spray underside of leaves in early morning or evening.",
    },
    "Caterpillars / Bollworm / Stem & Fruit Borer": {
        "best_chemical": "Emamectin Benzoate 5% SG OR Chlorantraniliprole 18.5% SC",
        "dose_per_liter": 0.4,
        "unit": "g / ml",
        "foliar_booster": "Calcium Nitrate (3 g/L) to harden fruit/boll skin",
        "precaution": "Wait 7–10 days Pre-Harvest Interval before picking.",
    },
    "Nitrogen / Iron / Zinc Deficiency (Yellowing Leaves)": {
        "best_chemical": "Chelated Micronutrient Mix (Zn+Fe+Mn+Mg) + 19:19:19 Foliar",
        "dose_per_liter": 2.0,
        "unit": "g",
        "foliar_booster": "Soil basal: DAP (50 kg/acre) + Zinc Sulphate (10 kg/acre)",
        "precaution": "Check soil drainage first; waterlogging causes yellowing.",
    },
    "Root Rot / Wilt (Soil-Borne Fungal Infection)": {
        "best_chemical": "Copper Oxychloride 50% WP OR Carbendazim + Trichoderma",
        "dose_per_liter": 3.0,
        "unit": "g",
        "foliar_booster": "Humic Acid (2 ml/L) root drench for new white roots",
        "precaution": "Apply directly to the root zone (soil drenching).",
    },
}


def analyze_plant_photo(img: Image.Image):
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
        summary = f"Detected {brown_spots:.1f}% brown leaf spot lesions."
    elif yellow_chlorosis > 18.0:
        condition = "Nitrogen / Iron / Zinc Deficiency (Yellowing Leaves)"
        summary = f"Detected {yellow_chlorosis:.1f}% yellowing leaf tissue."
    elif pale_white > 24.0 and healthy_green < 40.0:
        condition = "Powdery Mildew / Rust (White/Orange Powder)"
        summary = f"Detected {pale_white:.1f}% powdery coating on leaves."
    elif healthy_green < 22.0:
        condition = "Sucking Pests (Thrips, Aphids, Whitefly, Leaf Curl)"
        summary = f"Low healthy green coverage ({healthy_green:.1f}%)—possible pest stress."
    else:
        condition = "Healthy Crop Foliage (Preventive Growth Stage)"
        summary = f"Strong healthy green foliage ({healthy_green:.1f}% chlorophyll index)."

    return condition, summary, healthy_green, yellow_chlorosis, brown_spots


SOIL_PROFILES = {
    "Black Cotton Soil (Regur)": {
        "water_holding": "High (Retains moisture long)",
        "best_crops": ["Sugarcane", "Cotton", "Soybean", "Jowar", "Chickpea", "Turmeric"],
        "fertilizer_tip": "Apply split Nitrogen + DAP/SSP.",
    },
    "Red Loamy Soil": {
        "water_holding": "Moderate (Needs regular scheduled irrigation)",
        "best_crops": ["Groundnut", "Maize", "Ragi", "Chilli", "Tomato", "Pomegranate"],
        "fertilizer_tip": "Apply organic compost + NPK (19:19:19) + Zinc/Boron.",
    },
    "Alluvial / Silt Loam Soil": {
        "water_holding": "Moderate-High (Very fertile)",
        "best_crops": ["Paddy", "Wheat", "Banana", "Sugarcane", "Onion", "Vegetables"],
        "fertilizer_tip": "Focus on Nitrogen split doses & green manuring.",
    },
    "Sandy / Light Soil": {
        "water_holding": "Low (Ideal for drip irrigation)",
        "best_crops": ["Watermelon", "Groundnut", "Bajra", "Carrot", "Coconut"],
        "fertilizer_tip": "Frequent small fertigation doses + organic compost.",
    },
    "Laterite / Hilly Soil": {
        "water_holding": "Moderate (Well-drained)",
        "best_crops": ["Coffee", "Black Pepper", "Arecanut", "Cashew", "Ginger"],
        "fertilizer_tip": "Apply agricultural lime if pH < 5.5 + neem cake.",
    },
}

ENV_CONDITIONS = {
    "Hot & Dry (Summer / High Temp > 34°C)": {
        "irrigation_factor": 1.30,
        "sowing_advice": "Sow early morning/evening & use mulching.",
        "spray_warning": "Spray only before 9:30 AM or after 5:00 PM.",
    },
    "Warm & Humid (Pre-Monsoon / Moderate)": {
        "irrigation_factor": 1.00,
        "sowing_advice": "Ideal window for seed germination & basal fertilizer.",
        "spray_warning": "Monitor for fungal spots & sucking pests.",
    },
    "Monsoon / Heavy Rain (High Moisture)": {
        "irrigation_factor": 0.20,
        "sowing_advice": "Use raised beds/ridges to prevent waterlogging.",
        "spray_warning": "Ensure 4-hour rain-free window after spraying.",
    },
    "Cool & Dry (Rabi / Winter)": {
        "irrigation_factor": 0.80,
        "sowing_advice": "Best season for pulses, wheat, onion & leafy crops.",
        "spray_warning": "Watch for powdery mildew; sulfur/neem sprays work best.",
    },
}

CROP_GUIDES = {
    "Sugarcane": {"spacing": "4 ft x 1.5 ft", "seed_rate": "25,000–30,000 setts/acre", "npk_per_acre": (100, 40, 40), "yield_booster": "Humic acid + 00:52:34 foliar spray."},
    "Maize": {"spacing": "60 cm x 20 cm", "seed_rate": "8 kg/acre", "npk_per_acre": (60, 30, 20), "yield_booster": "Zinc Sulphate 10 kg/acre + 19:19:19 spray."},
    "Cotton": {"spacing": "90 cm x 60 cm", "seed_rate": "1.0 kg Bt seeds/acre", "npk_per_acre": (50, 25, 25), "yield_booster": "Magnesium Sulphate + Boron spray at flowering."},
    "Tomato / Chilli": {"spacing": "60 cm x 45 cm", "seed_rate": "60–80 g seeds/acre", "npk_per_acre": (50, 30, 30), "yield_booster": "Calcium Nitrate + Boron spray at flowering."},
    "Onion": {"spacing": "15 cm x 10 cm", "seed_rate": "3–4 kg/acre", "npk_per_acre": (40, 20, 30), "yield_booster": "Sulphur 15 kg/acre + 00:00:50 (SOP) spray."},
    "Soybean / Groundnut": {"spacing": "30 cm x 10 cm", "seed_rate": "30–40 kg/acre", "npk_per_acre": (15, 30, 20), "yield_booster": "Rhizobium seed treatment + Gypsum 200 kg/acre."},
    "Paddy (Rice)": {"spacing": "20 cm x 15 cm", "seed_rate": "20–25 kg/acre", "npk_per_acre": (45, 20, 20), "yield_booster": "Neem-coated Urea in 3 splits + 00:52:34 spray."},
    "Banana / Arecanut": {"spacing": "6x6 ft / 9x9 ft", "seed_rate": "1,200 / 540 plants/acre", "npk_per_acre": (120, 40, 140), "yield_booster": "13:00:45 (Potassium Nitrate) + Micronutrients."},
}

# --- HERO HEADER BANNER ---
HERO_HTML = (
    '<div class="hero-card">'
    '<div class="hero-title"><span class="hero-green">SMART FARM</span> '
    '<span class="hero-white">ASSISTANT</span>'
    '<span class="version-badge">V3.0</span></div>'
    '<div class="hero-sub">📷 Plant Photo Scanner • 🧪 All Fertilizers & Chemicals • 🌦️ Live Weather • 💰 Mandi ROI</div>'
    '</div>'
)
st.markdown(HERO_HTML, unsafe_allow_html=True)

# --- LIVE WEATHER & SPRAY SAFETY ---
st.markdown("### 🌦️ Live Weather & Spray Safety")
w_sel1, w_sel2, w_sel3 = st.columns([1.5, 1, 1])
with w_sel1:
    chosen_district = st.selectbox("Select Farm District / Region", list(DISTRICTS.keys()), index=0)
default_lat, default_lon = DISTRICTS[chosen_district]
with w_sel2:
    farm_lat = st.number_input("GPS Latitude", value=default_lat, format="%.4f", disabled=(chosen_district != "Custom GPS Coordinates"))
with w_sel3:
    farm_lon = st.number_input("GPS Longitude", value=default_lon, format="%.4f", disabled=(chosen_district != "Custom GPS Coordinates"))

weather_data = fetch_live_weather(farm_lat, farm_lon)
auto_env = "Warm & Humid (Pre-Monsoon / Moderate)"

if weather_data and "current" in weather_data:
    curr = weather_data["current"]
    hourly = weather_data.get("hourly", {})
    temp_now = curr.get("temperature_2m", 28.0)
    hum_now = curr.get("relative_humidity_2m", 60)
    wind_now = curr.get("wind_speed_10m", 8.0)
    next_4h_probs = hourly.get("precipitation_probability", [0, 0, 0, 0])[:4]
    next_4h_rain = hourly.get("precipitation", [0, 0, 0, 0])[:4]
    max_prob_4h = max(next_4h_probs) if next_4h_probs else 0
    total_rain_4h = sum(next_4h_rain) if next_4h_rain else 0.0
    auto_env = classify_environment(temp_now, total_rain_4h, max_prob_4h)

    wm1, wm2, wm3, wm4 = st.columns(4)
    wm1.metric("🌡️ Temp", f"{temp_now:.1f} °C")
    wm2.metric("💧 Humidity", f"{hum_now}%")
    wm3.metric("💨 Wind", f"{wind_now:.1f} km/h")
    wm4.metric("🌧️ 4-Hr Rain", f"{max_prob_4h}%", f"{total_rain_4h:.1f} mm")

    if max_prob_4h >= 50 or total_rain_4h >= 0.5:
        st.error(f"🚨 DO NOT SPRAY: {max_prob_4h}% rain risk ({total_rain_4h:.1f} mm) in next 4 hours!")
    elif wind_now > 15.0:
        st.warning(f"⚠️ HIGH WIND ({wind_now:.1f} km/h): Delay spraying to avoid drift.")
    else:
        st.success(f"✅ SAFE TO SPRAY: Low rain risk ({max_prob_4h}%) & calm wind ({wind_now:.1f} km/h).")

env_keys = list(ENV_CONDITIONS.keys())
default_env_idx = env_keys.index(auto_env) if auto_env in env_keys else 1

st.markdown("---")

# --- 6 MOBILE-WRAPPING FUNCTION TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📷 1. Photo Scan",
    "🧪 2. Chemicals",
    "🌱 3. Crop & Soil",
    "💧 4. Irrigation",
    "👷 5. Workers",
    "💰 6. Profit & CSV",
])

# === TAB 1: CAMERA PLANT PHOTO SCANNER ===
with tab1:
    st.subheader("📷 Plant Photo Scanner & Chemical Advisor")
    cam_col1, cam_col2 = st.columns(2)
    with cam_col1:
        camera_photo = st.camera_input("📸 Take Plant / Leaf Photo")
    with cam_col2:
        uploaded_photo = st.file_uploader("📁 Or Upload Leaf Image", type=["jpg", "jpeg", "png"])

    active_photo = camera_photo if camera_photo is not None else uploaded_photo

    if active_photo is not None:
        pil_img = Image.open(active_photo)
        condition, summary, g_pct, y_pct, b_pct = analyze_plant_photo(pil_img)

        res_c1, res_c2 = st.columns([1, 1.4])
        with res_c1:
            st.image(pil_img, caption="Captured Plant Sample", use_container_width=True)
            m_a, m_b, m_c = st.columns(3)
            m_a.metric("Healthy Green", f"{g_pct:.0f}%")
            m_b.metric("Yellowing", f"{y_pct:.0f}%")
            m_c.metric("Spot / Lesion", f"{b_pct:.0f}%")

        with res_c2:
            st.markdown(f"#### 🔍 Detected: **{condition}**")
            st.info(f"**Leaf Scan Summary:** {summary}")

            if condition == "Healthy Crop Foliage (Preventive Growth Stage)":
                st.success("✅ **Best Preventive Spray:** NPK 19:19:19 (5 g/L) + Seaweed Extract (2 ml/L) + Neem Oil 1500 ppm (2 ml/L).")
                st.metric("15L Pump Mix", "75 g NPK + 30 ml Neem Oil")
                st.metric("200L Tank Mix", "1.0 kg NPK + 400 ml Neem Oil")
            else:
                rec = ALL_CHEMICALS[condition]
                st.warning(f"💊 **Best Chemical:** {rec['best_chemical']}")
                st.write(f"**🚀 Recovery Booster:** {rec['foliar_booster']}")
                st.write(f"**⚠️ Precaution:** {rec['precaution']}")

                d_col1, d_col2 = st.columns(2)
                d_col1.metric("15L Knapsack Pump", f"{15 * rec['dose_per_liter']:.1f} {rec['unit']}")
                d_col2.metric("200L Tractor Tank", f"{200 * rec['dose_per_liter']:.0f} {rec['unit']}")
    else:
        st.info("👆 Capture a leaf photo above or check any disease/chemical below:")
        manual_issue = st.selectbox("Manual Disease / Pest Lookup", list(ALL_CHEMICALS.keys()))
        m_rec = ALL_CHEMICALS[manual_issue]
        st.success(f"**Best Chemical:** {m_rec['best_chemical']} — **Dose:** {m_rec['dose_per_liter']} {m_rec['unit']}/L ({15 * m_rec['dose_per_liter']:.1f} {m_rec['unit']} per 15L pump)")

# === TAB 2: ALL FERTILIZERS & CHEMICAL CALCULATOR ===
with tab2:
    st.subheader("🧪 Fertilizer (Urea, DAP, MOP, NPK) & Chemical Calculator")
    fcol1, fcol2 = st.columns(2)
    with fcol1:
        calc_crop = st.selectbox("Select Crop", list(CROP_GUIDES.keys()), key="fert_crop")
        area_acres = st.number_input("Field Area (Acres)", min_value=0.25, max_value=500.0, value=2.0, step=0.25)
    with fcol2:
        tank_liters = st.number_input("Spray Tank Size (Liters)", min_value=10, max_value=2000, value=200, step=10)
        chem_select = st.selectbox("Select Chemical Spray", list(ALL_CHEMICALS.keys()))

    req_n, req_p, req_k = CROP_GUIDES[calc_crop]["npk_per_acre"]
    total_n, total_p, total_k = req_n * area_acres, req_p * area_acres, req_k * area_acres

    dap_kg = total_p / 0.46
    urea_kg = max(0.0, total_n - (dap_kg * 0.18)) / 0.46
    mop_kg = total_k / 0.60
    ssp_kg = total_p / 0.16

    fc1, fc2, fc3, fc4 = st.columns(4)
    fc1.metric("Urea (46% N)", f"{urea_kg:.1f} kg", f"{urea_kg/45:.1f} Bags")
    fc2.metric("DAP (18-46-0)", f"{dap_kg:.1f} kg", f"{dap_kg/50:.1f} Bags")
    fc3.metric("MOP Potash (60%)", f"{mop_kg:.1f} kg", f"{mop_kg/50:.1f} Bags")
    fc4.metric("SSP Alternative", f"{ssp_kg:.1f} kg", f"{ssp_kg/50:.1f} Bags")

    sel_chem_info = ALL_CHEMICALS[chem_select]
    dose_l = sel_chem_info["dose_per_liter"]
    unit_l = sel_chem_info["unit"]
    st.success(f"**Recommended Chemical:** {sel_chem_info['best_chemical']}")
    sc1, sc2 = st.columns(2)
    sc1.metric(f"{tank_liters}L Tank Dose", f"{tank_liters * dose_l:.1f} {unit_l}")
    sc2.metric("15L Pump Dose", f"{15 * dose_l:.1f} {unit_l}")

    with st.expander("📋 Full Directory of Fertilizers & Micronutrients", expanded=False):
        st.dataframe(pd.DataFrame(ALL_FERTILIZERS), use_container_width=True, hide_index=True)

# === TAB 3: SOIL, WEATHER & CROP SOWING ===
with tab3:
    st.subheader("🌱 Soil & Weather Crop Sowing Guide")
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_soil = st.selectbox("1. Soil Type", list(SOIL_PROFILES.keys()))
    with col2:
        selected_env = st.selectbox("2. Weather", env_keys, index=default_env_idx)
    with col3:
        selected_crop = st.selectbox("3. Target Crop", list(CROP_GUIDES.keys()))

    soil_info = SOIL_PROFILES[selected_soil]
    env_info = ENV_CONDITIONS[selected_env]
    crop_info = CROP_GUIDES[selected_crop]

    st.info(f"**Best Crops for {selected_soil}:** " + ", ".join(soil_info["best_crops"]))
    st.warning(f"**🌦️ Sowing Advice:** {env_info['sowing_advice']}")

    m1, m2, m3 = st.columns(3)
    m1.metric("Spacing", crop_info["spacing"])
    m2.metric("Seed Rate / Acre", crop_info["seed_rate"])
    m3.metric("Water Factor", f"{int(env_info['irrigation_factor']*100)}%")
    st.success(f"**🚀 Growth Booster:** {crop_info['yield_booster']}")

# === TAB 4: IRRIGATION & FIELD LOG ===
with tab4:
    st.subheader("💧 Daily Moisture & Irrigation Log")
    with st.form("irrigation_form", clear_on_submit=True):
        log_date = st.date_input("Date", date.today())
        plot_name = st.text_input("Plot Name", placeholder="e.g., North Plot")
        soil_t = st.selectbox("Soil Type", list(SOIL_PROFILES.keys()))
        env_t = st.selectbox("Weather", env_keys, index=default_env_idx)
        crop_t = st.selectbox("Crop", list(CROP_GUIDES.keys()))
        moisture_pct = st.slider("Soil Moisture (%)", 5, 100, 38)

        factor = ENV_CONDITIONS[env_t]["irrigation_factor"]
        rec_liters = round(12000 * factor * (1 - moisture_pct / 120), 0) if moisture_pct < 65 else 0

        st.info(f"💧 **Apply:** {rec_liters:,.0f} Liters/acre")
        notes = st.text_input("Field Note", placeholder="e.g., 2 hrs drip completed")

        if st.form_submit_button("💾 Save Irrigation Log"):
            conn = sqlite3.connect("smart_farm.db")
            conn.execute(
                "INSERT INTO advisory_logs (log_date, plot_name, soil_type, environment, crop_selected, soil_moisture, irrigation_liters, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (str(log_date), plot_name or "Main Plot", soil_t, env_t, crop_t, moisture_pct, rec_liters, notes),
            )
            conn.commit()
            conn.close()
            st.success("✅ Saved!")

# === TAB 5: WORKERS & WAGES ===
with tab5:
    st.subheader("👷 Worker Attendance & Wages")
    with st.form("add_worker_form", clear_on_submit=True):
        st.markdown("#### ➕ Add New Worker")
        w_name = st.text_input("Worker Name")
        w_role = st.selectbox("Role", ["Field Labor", "Tractor Operator", "Spray Specialist", "Irrigation Tech"])
        w_wage = st.number_input("Daily Wage (₹)", min_value=100, max_value=5000, value=500, step=50)
        if st.form_submit_button("Save Worker"):
            if w_name.strip():
                try:
                    conn = sqlite3.connect("smart_farm.db")
                    conn.execute("INSERT INTO workers (name, role, daily_wage, phone) VALUES (?, ?, ?, ?)", (w_name.strip(), w_role, w_wage, ""))
                    conn.commit()
                    conn.close()
                    st.success(f"Added {w_name}!")
                except sqlite3.IntegrityError:
                    st.error("Worker already exists.")

    conn = sqlite3.connect("smart_farm.db")
    workers_df = pd.read_sql_query("SELECT * FROM workers", conn)
    conn.close()

    if not workers_df.empty:
        with st.form("attendance_form"):
            st.markdown("#### ✅ Mark Attendance")
            att_date = st.date_input("Work Date", date.today())
            sel_worker = st.selectbox("Select Worker", workers_df["name"].tolist())
            att_status = st.selectbox("Status", ["Present (Full Day)", "Half Day", "Absent"])
            work_done = st.text_input("Task Done", placeholder="e.g., Weeding & spraying")
            base_wage = float(workers_df.loc[workers_df["name"] == sel_worker, "daily_wage"].values[0])
            earned = base_wage if att_status == "Present (Full Day)" else (base_wage * 0.5 if att_status == "Half Day" else 0.0)
            if st.form_submit_button("Record Attendance"):
                conn = sqlite3.connect("smart_farm.db")
                conn.execute("INSERT INTO attendance (work_date, worker_name, status, task_assigned, wage_earned) VALUES (?, ?, ?, ?, ?)", (str(att_date), sel_worker, att_status, work_done, earned))
                conn.commit()
                conn.close()
                st.success(f"Saved! Wage: ₹{earned:.0f}")

# === TAB 6: PROFIT, MANDI ROI & CSV REPORTS ===
with tab6:
    st.subheader("💰 Mandi Profit & CSV Reports")
    with st.form("expense_form", clear_on_submit=True):
        exp_date = st.date_input("Date", date.today())
        exp_crop = st.selectbox("Crop", list(CROP_GUIDES.keys()), key="exp_crop")
        exp_cat = st.selectbox("Category", ["Seeds", "Fertilizers", "Chemicals", "Diesel / Machinery", "Transport"])
        exp_amt = st.number_input("Amount (₹)", min_value=50, max_value=1000000, value=2000)
        exp_note = st.text_input("Note", placeholder="e.g., 3 Bags DAP")
        if st.form_submit_button("💾 Save Expense"):
            conn = sqlite3.connect("smart_farm.db")
            conn.execute("INSERT INTO farm_expenses (exp_date, crop_name, category, amount, notes) VALUES (?, ?, ?, ?, ?)", (str(exp_date), exp_crop, exp_cat, exp_amt, exp_note))
            conn.commit()
            conn.close()
            st.success("✅ Expense saved!")

    conn = sqlite3.connect("smart_farm.db")
    total_wages = float(pd.read_sql_query("SELECT COALESCE(SUM(wage_earned), 0) AS w FROM attendance", conn)["w"][0])
    total_inputs = float(pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) AS a FROM farm_expenses", conn)["a"][0])
    adv_df = pd.read_sql_query("SELECT * FROM advisory_logs ORDER BY id DESC", conn)
    att_df = pd.read_sql_query("SELECT * FROM attendance ORDER BY id DESC", conn)
    exp_df = pd.read_sql_query("SELECT * FROM farm_expenses ORDER BY id DESC", conn)
    conn.close()

    total_cost = total_wages + total_inputs
    yield_qtl = st.number_input("Harvest Yield (Quintals)", min_value=1.0, value=45.0)
    mandi_price = st.number_input("Mandi Price (₹ / Quintal)", min_value=100, value=2400)

    revenue = yield_qtl * mandi_price
    profit = revenue - total_cost
    pm1, pm2, pm3 = st.columns(3)
    pm1.metric("Total Cost", f"₹ {total_cost:,.0f}")
    pm2.metric("Mandi Revenue", f"₹ {revenue:,.0f}")
    pm3.metric("Net Profit", f"₹ {profit:,.0f}")

    st.markdown("#### 📥 Download CSV Reports")
    st.download_button("📥 Irrigation CSV", adv_df.to_csv(index=False).encode("utf-8"), "irrigation_logs.csv", "text/csv")
    st.download_button("📥 Worker Wages CSV", att_df.to_csv(index=False).encode("utf-8"), "worker_wages.csv", "text/csv")
    st.download_button("📥 Expenses CSV", exp_df.to_csv(index=False).encode("utf-8"), "farm_expenses.csv", "text/csv")