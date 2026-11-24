import sqlite3
from datetime import date
import pandas as pd
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
    /* Force dark background & high-contrast white text globally */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0D141F !important;
        background-image: 
            linear-gradient(rgba(52, 211, 153, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(52, 211, 153, 0.05) 1px, transparent 1px);
        background-size: 30px 30px;
        color: #FFFFFF !important;
    }

    /* Make all labels, paragraphs, markdown, and widget titles bright white */
    p, span, label, div, li, .stMarkdown, [data-testid="stWidgetLabel"] p {
        color: #F1F5F9 !important;
    }
    h1, h2, h3, h4, h5 {
        color: #4ADE80 !important;
        font-weight: 800 !important;
    }

    /* Input boxes, Selectboxes, Number inputs - dark card with crisp white text */
    input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div {
        background-color: #1A2636 !important;
        color: #FFFFFF !important;
        border: 1px solid #34D399 !important;
        border-radius: 8px !important;
    }
    [data-baseweb="select"] span {
        color: #FFFFFF !important;
    }
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
    .hero-title {
        font-size: 2.0rem;
        font-weight: 900;
        margin: 0;
        line-height: 1.15;
    }
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
    .hero-sub {
        color: #CBD5E1 !important;
        font-size: 0.95rem;
        margin-top: 6px;
    }

    /* Navigation Tabs */
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
    .stTabs [aria-selected="true"] p {
        color: #061019 !important;
    }

    /* Metric Cards */
    [data-testid="stMetric"] {
        background-color: #152233 !important;
        border: 1px solid #22C55E !important;
        border-radius: 12px;
        padding: 14px 18px;
    }
    [data-testid="stMetricLabel"] p {
        color: #94A3B8 !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] div {
        color: #4ADE80 !important;
        font-weight: 900 !important;
    }

    /* Forms & Expanders */
    [data-testid="stForm"], [data-testid="stExpander"] {
        background-color: #131E2E !important;
        border: 1px solid rgba(52, 211, 153, 0.35) !important;
        border-radius: 14px;
        padding: 16px;
    }

    /* Bright Emerald Action Buttons */
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
        "id",
        "log_date",
        "plot_name",
        "soil_type",
        "environment",
        "crop_selected",
        "soil_moisture",
        "irrigation_liters",
        "notes",
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
    c.execute("""CREATE TABLE IF NOT EXISTS farm_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            due_date TEXT, plot_name TEXT, task_title TEXT, assigned_to TEXT, priority TEXT, status TEXT
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


# --- AGRONOMY KNOWLEDGE BASE ---
SOIL_PROFILES = {
    "Black Cotton Soil (Regur)": {
        "water_holding": "High (Retains moisture long; avoid over-irrigation)",
        "best_crops": [
            "Sugarcane",
            "Cotton",
            "Soybean",
            "Jowar (Sorghum)",
            "Chickpea (Chana)",
            "Turmeric",
        ],
        "fertilizer_tip": "Rich in calcium & magnesium, low in nitrogen & phosphorus. Apply split Nitrogen + DAP/SSP.",
    },
    "Red Loamy Soil": {
        "water_holding": "Moderate (Good drainage; needs regular scheduled irrigation)",
        "best_crops": [
            "Groundnut",
            "Maize",
            "Ragi",
            "Chilli",
            "Tomato",
            "Pomegranate",
            "Arecanut",
        ],
        "fertilizer_tip": "Responds well to organic FYM/compost + balanced NPK (19:19:19) and micronutrients (Zinc/Boron).",
    },
    "Alluvial / Silt Loam Soil": {
        "water_holding": "Moderate-High (Very fertile & easy to till)",
        "best_crops": [
            "Paddy (Rice)",
            "Wheat",
            "Banana",
            "Sugarcane",
            "Onion",
            "Potato",
            "Vegetables",
        ],
        "fertilizer_tip": "High potash availability; focus on Nitrogen split doses and organic green manuring.",
    },
    "Sandy / Light Soil": {
        "water_holding": "Low (Drains fast; ideal for drip irrigation)",
        "best_crops": [
            "Watermelon",
            "Muskmelon",
            "Groundnut",
            "Bajra (Pearl Millet)",
            "Carrot",
            "Coconut",
        ],
        "fertilizer_tip": "Use frequent small fertigation doses (drip) + heavy organic compost to prevent nutrient leaching.",
    },
    "Laterite / Hilly Plantation Soil": {
        "water_holding": "Moderate (Acidic pH; well-drained)",
        "best_crops": [
            "Coffee",
            "Black Pepper",
            "Arecanut",
            "Cashew",
            "Ginger",
            "Pineapple",
        ],
        "fertilizer_tip": "Apply agricultural lime if pH < 5.5, plus rock phosphate and neem cake.",
    },
}

ENV_CONDITIONS = {
    "Hot & Dry (Summer / High Temp > 34°C)": {
        "irrigation_factor": 1.30,
        "sowing_advice": "Sow heat-tolerant varieties early morning or late evening. Use mulching to cut evaporation by 40%.",
        "spray_warning": "Spray only before 9:30 AM or after 5:00 PM to prevent leaf scorching.",
    },
    "Warm & Humid (Pre-Monsoon / Moderate)": {
        "irrigation_factor": 1.00,
        "sowing_advice": "Ideal window for seed germination and basal fertilizer application.",
        "spray_warning": "Monitor for fungal leaf spot & sucking pests (thrips/aphids); add spreader-sticker to sprays.",
    },
    "Monsoon / Heavy Rain (High Moisture)": {
        "irrigation_factor": 0.20,
        "sowing_advice": "Use raised beds/ridges for sowing to prevent waterlogging and root rot.",
        "spray_warning": "Ensure a 4-hour rain-free window after foliar spraying; use preventive bio-fungicides (Trichoderma).",
    },
    "Cool & Dry (Rabi / Winter)": {
        "irrigation_factor": 0.80,
        "sowing_advice": "Best season for pulses, wheat, onion, and leafy vegetables. Irrigate lightly during noon.",
        "spray_warning": "Watch for powdery mildew and mites; sulfur/neem-based sprays work best.",
    },
}

CROP_GUIDES = {
    "Sugarcane": {
        "spacing": "4 ft x 1.5 ft (Paired row ideal for drip)",
        "seed_rate": "25,000–30,000 two-budded setts/acre",
        "npk_per_acre": (100, 40, 40),
        "yield_booster": "Humic acid + Seaweed extract at 45 & 75 days + 00:52:34 foliar spray at grand growth stage.",
    },
    "Maize": {
        "spacing": "60 cm x 20 cm",
        "seed_rate": "8 kg/acre",
        "npk_per_acre": (60, 30, 20),
        "yield_booster": "Zinc Sulphate 10 kg/acre basal + 19:19:19 foliar spray at knee-high stage.",
    },
    "Cotton": {
        "spacing": "90 cm x 60 cm",
        "seed_rate": "900 g – 1.2 kg Bt seeds/acre",
        "npk_per_acre": (50, 25, 25),
        "yield_booster": "Magnesium Sulphate (1%) + Boron (0.1%) foliar spray at flowering & boll formation to stop boll drop.",
    },
    "Tomato / Chilli": {
        "spacing": "60 cm x 45 cm (Raised bed + mulch)",
        "seed_rate": "60–80 g nursery seeds/acre",
        "npk_per_acre": (50, 30, 30),
        "yield_booster": "Calcium Nitrate + Boron spray at flowering to prevent blossom end rot & flower drop.",
    },
    "Onion": {
        "spacing": "15 cm x 10 cm",
        "seed_rate": "3–4 kg/acre",
        "npk_per_acre": (40, 20, 30),
        "yield_booster": "Sulphur 15 kg/acre basal + 00:00:50 (SOP) spray at bulb enlargement for size & storage life.",
    },
    "Soybean / Groundnut": {
        "spacing": "30 cm x 10 cm",
        "seed_rate": "25–30 kg (Soybean) / 40–45 kg (Groundnut)/acre",
        "npk_per_acre": (15, 30, 20),
        "yield_booster": "Rhizobium + PSB seed treatment + Gypsum 200 kg/acre at pegging/pod stage.",
    },
    "Paddy (Rice)": {
        "spacing": "20 cm x 15 cm",
        "seed_rate": "20–25 kg/acre",
        "npk_per_acre": (45, 20, 20),
        "yield_booster": "Neem-coated Urea split in 3 stages + Potassium Silicate / 00:52:34 at panicle initiation.",
    },
    "Banana / Arecanut": {
        "spacing": "6 ft x 6 ft (Banana) / 9 ft x 9 ft (Arecanut)",
        "seed_rate": "1,200 suckers (Banana) / 540 palms (Arecanut)/acre",
        "npk_per_acre": (120, 40, 140),
        "yield_booster": "13:00:45 (Potassium Nitrate) + Micronutrient mix via drip/foliar for bunch weight & shine.",
    },
}

# --- HERO HEADER BANNER ---
st.markdown(
    """
<div class="hero-card">
    <div>
        <div class="hero-title">
            <span class="hero-green">SMART FARM</span>
            <span class="hero-white">ASSISTANT</span>
            <span class="version-badge">V3.0</span>
        </div>
        <div class="hero-sub">
            🌦️ Live GPS Weather & Spray Guard &nbsp;•&nbsp; 🧪 Commercial Fertilizer Calculator &nbsp;•&nbsp; 👷 Worker Wages &nbsp;•&nbsp; 💰 Mandi ROI
        </div>
    </div>
    <div style="color:#4ADE80; font-weight:800; font-size:0.95rem;">
        ● SYSTEM ONLINE &nbsp;|&nbsp; ALL FUNCTIONS ACTIVE
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# --- LIVE WEATHER & SPRAY SAFETY MONITOR ---
st.markdown("### 🌦️ Live Farm Weather & 4-Hour Spray Safety Check")
w_sel1, w_sel2, w_sel3 = st.columns([1.5, 1, 1])
with w_sel1:
    chosen_district = st.selectbox(
        "Select Farm District / Region", list(DISTRICTS.keys()), index=0
    )
default_lat, default_lon = DISTRICTS[chosen_district]
with w_sel2:
    farm_lat = st.number_input(
        "GPS Latitude",
        value=default_lat,
        format="%.4f",
        disabled=(chosen_district != "Custom GPS Coordinates"),
    )
with w_sel3:
    farm_lon = st.number_input(
        "GPS Longitude",
        value=default_lon,
        format="%.4f",
        disabled=(chosen_district != "Custom GPS Coordinates"),
    )

weather_data = fetch_live_weather(farm_lat, farm_lon)
auto_env = "Warm & Humid (Pre-Monsoon / Moderate)"

if weather_data and "current" in weather_data:
    curr = weather_data["current"]
    hourly = weather_data.get("hourly", {})
    daily = weather_data.get("daily", {})

    temp_now = curr.get("temperature_2m", 28.0)
    hum_now = curr.get("relative_humidity_2m", 60)
    wind_now = curr.get("wind_speed_10m", 8.0)

    next_4h_probs = hourly.get("precipitation_probability", [0, 0, 0, 0])[:4]
    next_4h_rain = hourly.get("precipitation", [0, 0, 0, 0])[:4]
    max_prob_4h = max(next_4h_probs) if next_4h_probs else 0
    total_rain_4h = sum(next_4h_rain) if next_4h_rain else 0.0

    auto_env = classify_environment(temp_now, total_rain_4h, max_prob_4h)

    wm1, wm2, wm3, wm4 = st.columns(4)
    wm1.metric("🌡️ Temperature", f"{temp_now:.1f} °C")
    wm2.metric("💧 Humidity", f"{hum_now}%")
    wm3.metric("💨 Wind Speed", f"{wind_now:.1f} km/h")
    wm4.metric("🌧️ 4-Hr Rain Risk", f"{max_prob_4h}%", f"{total_rain_4h:.1f} mm")

    if max_prob_4h >= 50 or total_rain_4h >= 0.5:
        st.error(
            f"🚨 DO NOT SPRAY ALERT: {max_prob_4h}% chance of rain ({total_rain_4h:.1f} mm) in the next 4 hours. Delay spraying to avoid wash-off!"
        )
    elif wind_now > 15.0:
        st.warning(
            f"⚠️ HIGH WIND WARNING ({wind_now:.1f} km/h): Wind exceeds 15 km/h. High spray drift risk—wait for calm air."
        )
    else:
        st.success(
            f"✅ SAFE TO SPRAY: Low rain risk ({max_prob_4h}%) & calm wind ({wind_now:.1f} km/h). Active Weather Mode: {auto_env}"
        )

    if daily and "time" in daily:
        with st.expander(
            "📅 View 3-Day District Rainfall & Temperature Forecast",
            expanded=False,
        ):
            forecast_df = pd.DataFrame({
                "Date": daily["time"],
                "Max Temp (°C)": daily["temperature_2m_max"],
                "Min Temp (°C)": daily["temperature_2m_min"],
                "Rain Sum (mm)": daily["precipitation_sum"],
                "Rain Chance (%)": daily["precipitation_probability_max"],
            })
            st.dataframe(forecast_df, use_container_width=True, hide_index=True)

env_keys = list(ENV_CONDITIONS.keys())
default_env_idx = env_keys.index(auto_env) if auto_env in env_keys else 1

st.markdown("---")
st.markdown("### 🧭 Select Farm Function Module")

# --- CLEAN 6-MODULE NAVIGATION (CLEAR & EASY TO READ ON MOBILE + LAPTOP) ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌱 1. Crop & Soil",
    "🧪 2. Fertilizer & Spray",
    "💧 3. Irrigation Log",
    "👷 4. Workers & Wages",
    "💰 5. Profit & Mandi",
    "🚜 6. Machinery & Reports",
])

# === TAB 1: SOIL, WEATHER & CROP SOWING ===
with tab1:
    st.subheader("Soil & Weather Crop Sowing Guide")
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_soil = st.selectbox(
            "Step 1: Select Soil Type", list(SOIL_PROFILES.keys())
        )
    with col2:
        selected_env = st.selectbox(
            "Step 2: Weather Condition", env_keys, index=default_env_idx
        )
    with col3:
        selected_crop = st.selectbox(
            "Step 3: Select Target Crop", list(CROP_GUIDES.keys())
        )

    soil_info = SOIL_PROFILES[selected_soil]
    env_info = ENV_CONDITIONS[selected_env]
    crop_info = CROP_GUIDES[selected_crop]

    c1, c2 = st.columns(2)
    with c1:
        st.info(
            f"**Recommended Crops for {selected_soil}:**\n\n"
            + ", ".join(soil_info["best_crops"])
        )
        st.write(f"**💧 Moisture Retention:** {soil_info['water_holding']}")
        st.write(f"**🧪 Fertilizer Advice:** {soil_info['fertilizer_tip']}")
    with c2:
        st.warning(
            f"**🌦️ Sowing Advice ({selected_env}):**\n\n{env_info['sowing_advice']}"
        )
        st.write(f"**⚠️ Spray Precaution:** {env_info['spray_warning']}")

    m1, m2, m3 = st.columns(3)
    m1.metric("Row & Plant Spacing", crop_info["spacing"])
    m2.metric("Seed Rate / Acre", crop_info["seed_rate"])
    m3.metric("Water Requirement", f"{int(env_info['irrigation_factor']*100)}%")
    st.success(f"**🚀 High-Yield Booster:** {crop_info['yield_booster']}")

# === TAB 2: FERTILIZER & SPRAY CALCULATOR ===
with tab2:
    st.subheader("Exact Fertilizer Bag & Spray Tank Calculator")
    fcol1, fcol2 = st.columns(2)
    with fcol1:
        calc_crop = st.selectbox(
            "Select Crop", list(CROP_GUIDES.keys()), key="fert_crop"
        )
        area_acres = st.number_input(
            "Field Area (Acres)",
            min_value=0.25,
            max_value=500.0,
            value=2.0,
            step=0.25,
        )
    with fcol2:
        tank_liters = st.number_input(
            "Spray Tank Capacity (Liters)",
            min_value=10,
            max_value=2000,
            value=200,
            step=10,
        )
        chem_dose_per_liter = st.number_input(
            "Chemical Dose (ml or g per Liter)",
            min_value=0.1,
            max_value=50.0,
            value=2.5,
            step=0.5,
        )

    req_n, req_p, req_k = CROP_GUIDES[calc_crop]["npk_per_acre"]
    total_n, total_p, total_k = (
        req_n * area_acres,
        req_p * area_acres,
        req_k * area_acres,
    )

    dap_kg = total_p / 0.46
    urea_kg = max(0.0, total_n - (dap_kg * 0.18)) / 0.46
    mop_kg = total_k / 0.60

    fc1, fc2, fc3 = st.columns(3)
    fc1.metric("Urea (46% N)", f"{urea_kg:.1f} kg", f"{urea_kg/45:.1f} Bags")
    fc2.metric("DAP (18-46-0)", f"{dap_kg:.1f} kg", f"{dap_kg/50:.1f} Bags")
    fc3.metric("MOP Potash (60%)", f"{mop_kg:.1f} kg", f"{mop_kg/50:.1f} Bags")

    sc1, sc2 = st.columns(2)
    sc1.metric(
        f"Total Dose for {tank_liters}L Tank",
        f"{tank_liters * chem_dose_per_liter:.0f} ml / g",
    )
    sc2.metric(
        "Dose per 15L Knapsack Pump",
        f"{15 * chem_dose_per_liter:.1f} ml / g",
    )

# === TAB 3: IRRIGATION & FIELD LOG ===
with tab3:
    st.subheader("Daily Moisture & Irrigation Scheduler")
    with st.form("irrigation_form", clear_on_submit=True):
        ic1, ic2, ic3 = st.columns(3)
        with ic1:
            log_date = st.date_input("Date", date.today())
            plot_name = st.text_input(
                "Plot Name", placeholder="e.g., North Plot"
            )
        with ic2:
            soil_t = st.selectbox("Soil Type", list(SOIL_PROFILES.keys()))
            env_t = st.selectbox("Weather", env_keys, index=default_env_idx)
        with ic3:
            crop_t = st.selectbox("Crop", list(CROP_GUIDES.keys()))
            moisture_pct = st.slider("Soil Moisture (%)", 5, 100, 38)

        factor = ENV_CONDITIONS[env_t]["irrigation_factor"]
        rec_liters = (
            round(12000 * factor * (1 - moisture_pct / 120), 0)
            if moisture_pct < 65
            else 0
        )

        st.info(
            f"💧 **Recommended Irrigation:** Apply **{rec_liters:,.0f} Liters/acre**."
        )
        notes = st.text_input(
            "Field Note", placeholder="e.g., 2 hrs drip irrigation completed"
        )

        if st.form_submit_button("💾 Save Irrigation Log"):
            conn = sqlite3.connect("smart_farm.db")
            conn.execute(
                "INSERT INTO advisory_logs (log_date, plot_name, soil_type, environment, crop_selected, soil_moisture, irrigation_liters, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(log_date),
                    plot_name or "Main Plot",
                    soil_t,
                    env_t,
                    crop_t,
                    moisture_pct,
                    rec_liters,
                    notes,
                ),
            )
            conn.commit()
            conn.close()
            st.success("✅ Irrigation log saved!")

# === TAB 4: WORKERS, WAGES & TASKS ===
with tab4:
    st.subheader("Worker Attendance, Wages & Daily Tasks")
    wcol1, wcol2 = st.columns(2)
    with wcol1:
        st.markdown("#### ➕ Add Worker")
        with st.form("add_worker_form", clear_on_submit=True):
            w_name = st.text_input("Worker Name")
            w_role = st.selectbox(
                "Role",
                [
                    "Field Labor",
                    "Tractor Operator",
                    "Spray Specialist",
                    "Irrigation Tech",
                ],
            )
            w_wage = st.number_input(
                "Daily Wage (₹)", min_value=100, max_value=5000, value=500, step=50
            )
            if st.form_submit_button("Save Worker"):
                if w_name.strip():
                    try:
                        conn = sqlite3.connect("smart_farm.db")
                        conn.execute(
                            "INSERT INTO workers (name, role, daily_wage, phone) VALUES (?, ?, ?, ?)",
                            (w_name.strip(), w_role, w_wage, ""),
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"Added {w_name}!")
                    except sqlite3.IntegrityError:
                        st.error("Worker already exists.")

    with wcol2:
        st.markdown("#### ✅ Mark Attendance")
        conn = sqlite3.connect("smart_farm.db")
        workers_df = pd.read_sql_query("SELECT * FROM workers", conn)
        conn.close()

        if workers_df.empty:
            st.warning("Add a worker on the left first.")
        else:
            with st.form("attendance_form"):
                att_date = st.date_input("Work Date", date.today())
                sel_worker = st.selectbox(
                    "Select Worker", workers_df["name"].tolist()
                )
                att_status = st.selectbox(
                    "Status", ["Present (Full Day)", "Half Day", "Absent"]
                )
                work_done = st.text_input(
                    "Task Done", placeholder="e.g., Weeding & spraying"
                )
                base_wage = float(
                    workers_df.loc[
                        workers_df["name"] == sel_worker, "daily_wage"
                    ].values[0]
                )
                earned = (
                    base_wage
                    if att_status == "Present (Full Day)"
                    else (base_wage * 0.5 if att_status == "Half Day" else 0.0)
                )
                if st.form_submit_button("Record Attendance"):
                    conn = sqlite3.connect("smart_farm.db")
                    conn.execute(
                        "INSERT INTO attendance (work_date, worker_name, status, task_assigned, wage_earned) VALUES (?, ?, ?, ?, ?)",
                        (
                            str(att_date),
                            sel_worker,
                            att_status,
                            work_done,
                            earned,
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Saved! Wage: ₹{earned:.0f}")

# === TAB 5: PROFIT / LOSS & MANDI ROI ===
with tab5:
    st.subheader("💰 Expense Ledger & Mandi Net Profit Calculator")
    with st.form("expense_form", clear_on_submit=True):
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            exp_date = st.date_input("Date", date.today())
            exp_crop = st.selectbox(
                "Crop", list(CROP_GUIDES.keys()), key="exp_crop"
            )
        with ec2:
            exp_cat = st.selectbox(
                "Category",
                ["Seeds", "Fertilizers", "Pesticides", "Irrigation", "Transport"],
            )
            exp_amt = st.number_input(
                "Amount (₹)", min_value=50, max_value=1000000, value=2000
            )
        with ec3:
            exp_note = st.text_input("Note", placeholder="e.g., 3 Bags Urea")
        if st.form_submit_button("💾 Save Expense"):
            conn = sqlite3.connect("smart_farm.db")
            conn.execute(
                "INSERT INTO farm_expenses (exp_date, crop_name, category, amount, notes) VALUES (?, ?, ?, ?, ?)",
                (str(exp_date), exp_crop, exp_cat, exp_amt, exp_note),
            )
            conn.commit()
            conn.close()
            st.success("✅ Expense saved!")

    conn = sqlite3.connect("smart_farm.db")
    total_wages = float(
        pd.read_sql_query(
            "SELECT COALESCE(SUM(wage_earned), 0) AS w FROM attendance", conn
        )["w"][0]
    )
    total_fuel = float(
        pd.read_sql_query(
            "SELECT COALESCE(SUM(fuel_cost), 0) AS f FROM machinery_logs", conn
        )["f"][0]
    )
    total_inputs = float(
        pd.read_sql_query(
            "SELECT COALESCE(SUM(amount), 0) AS a FROM farm_expenses", conn
        )["a"][0]
    )
    conn.close()

    total_cost = total_wages + total_fuel + total_inputs
    rc1, rc2 = st.columns(2)
    with rc1:
        yield_qtl = st.number_input(
            "Harvest Yield (Quintals)", min_value=1.0, value=45.0
        )
    with rc2:
        mandi_price = st.number_input(
            "Mandi Price (₹ / Quintal)", min_value=100, value=2400
        )

    revenue = yield_qtl * mandi_price
    profit = revenue - total_cost
    pm1, pm2, pm3 = st.columns(3)
    pm1.metric("Total Farm Cost", f"₹ {total_cost:,.0f}")
    pm2.metric("Gross Mandi Revenue", f"₹ {revenue:,.0f}")
    pm3.metric("Net Profit", f"₹ {profit:,.0f}")

# === TAB 6: MACHINERY TELEMETRY & CSV REPORTS ===
with tab6:
    st.subheader("🚜 Machinery Telemetry & CSV Report Downloads")
    with st.form("machinery_form", clear_on_submit=True):
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            m_date = st.date_input("Date", date.today())
            m_name = st.selectbox(
                "Machine",
                ["Tractor (45 HP)", "Mini Power Tiller", "Battery Sprayer", "Drip Pump"],
            )
        with mc2:
            m_op = st.text_input("Operation", placeholder="e.g., Inter-cultivation")
            m_hrs = st.number_input("Run Hours", min_value=0.5, value=3.0)
        with mc3:
            m_fuel = st.number_input("Diesel Used (L)", min_value=0.0, value=6.0)
            m_cost = st.number_input("Fuel Cost (₹)", min_value=0, value=570)
        if st.form_submit_button("💾 Save Machinery Log"):
            conn = sqlite3.connect("smart_farm.db")
            conn.execute(
                "INSERT INTO machinery_logs (log_date, machine_name, operation_type, hours_run, fuel_liters, fuel_cost, next_service_hrs) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(m_date), m_name, m_op, m_hrs, m_fuel, m_cost, 250.0),
            )
            conn.commit()
            conn.close()
            st.success("✅ Machinery log saved!")

    conn = sqlite3.connect("smart_farm.db")
    adv_df = pd.read_sql_query("SELECT * FROM advisory_logs ORDER BY id DESC", conn)
    att_df = pd.read_sql_query("SELECT * FROM attendance ORDER BY id DESC", conn)
    exp_df = pd.read_sql_query("SELECT * FROM farm_expenses ORDER BY id DESC", conn)
    conn.close()

    d1, d2, d3 = st.columns(3)
    with d1:
        st.download_button(
            "📥 Download Irrigation CSV",
            adv_df.to_csv(index=False).encode("utf-8"),
            "irrigation_logs.csv",
            "text/csv",
        )
    with d2:
        st.download_button(
            "📥 Download Wages CSV",
            att_df.to_csv(index=False).encode("utf-8"),
            "worker_wages.csv",
            "text/csv",
        )
    with d3:
        st.download_button(
            "📥 Download Expenses CSV",
            exp_df.to_csv(index=False).encode("utf-8"),
            "farm_expenses.csv",
            "text/csv",
        )