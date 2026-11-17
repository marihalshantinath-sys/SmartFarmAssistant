import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="SmartFarmAssistant", page_icon="🌱", layout="wide")

# --- Database Setup (SQLite) ---
conn = sqlite3.connect("smartfarm.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS farm_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        crop TEXT,
        area_acres REAL,
        soil_moisture REAL,
        irrigation_liters REAL,
        notes TEXT
    )
""")
conn.commit()

# --- Crop Reference Data ---
CROP_DATA = {
    "Sugarcane": {"moisture_min": 65, "water_l_per_acre": 18000, "npk": "100:40:40 kg/acre"},
    "Paddy (Rice)": {"moisture_min": 75, "water_l_per_acre": 22000, "npk": "60:30:30 kg/acre"},
    "Maize": {"moisture_min": 55, "water_l_per_acre": 12000, "npk": "60:30:20 kg/acre"},
    "Tomato": {"moisture_min": 60, "water_l_per_acre": 10000, "npk": "50:25:25 kg/acre"},
    "Arecanut / Horticulture": {"moisture_min": 60, "water_l_per_acre": 14000, "npk": "40:16:56 kg/acre"},
}

st.title("🌱 SmartFarmAssistant")
st.caption("Smart Irrigation, Nutrient Calculator & Farm Activity Logger")

tab1, tab2, tab3 = st.tabs(["💧 Irrigation & Advisory", "🧪 Fertilizer Calculator", "📋 Farm Logs"])

# --- Tab 1: Irrigation & Advisory ---
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        crop = st.selectbox("Select Crop", list(CROP_DATA.keys()))
        area = st.number_input("Field Area (Acres)", min_value=0.1, max_value=500.0, value=1.0, step=0.5)
        moisture = st.slider("Current Soil Moisture (%)", 0, 100, 45)
        temp = st.number_input("Ambient Temperature (°C)", min_value=5.0, max_value=50.0, value=28.0)

    info = CROP_DATA[crop]
    deficit = max(0, info["moisture_min"] - moisture)
    temp_factor = 1.15 if temp > 32 else 1.0
    recommended_water = round(info["water_l_per_acre"] * area * (deficit / 100.0) * temp_factor, 1)

    with col2:
        st.subheader("Advisory Output")
        st.metric("Target Soil Moisture", f"{info['moisture_min']}%")
        st.metric("Recommended Irrigation", f"{recommended_water:,.1f} Liters")

        if moisture < info["moisture_min"]:
            st.warning(f"Soil moisture is {deficit}% below optimal for {crop}. Irrigation recommended.")
        else:
            st.success(f"Soil moisture is optimal for {crop}. No irrigation needed today.")

        notes = st.text_input("Field Observation / Notes", placeholder="e.g., Drip line checked, morning session")
        if st.button("Save Log to Database"):
            c.execute(
                "INSERT INTO farm_logs (date, crop, area_acres, soil_moisture, irrigation_liters, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M"), crop, area, moisture, recommended_water, notes),
            )
            conn.commit()
            st.success("Farm log saved!")

# --- Tab 2: Fertilizer Calculator ---
with tab2:
    st.subheader("NPK Requirement Estimator")
    calc_crop = st.selectbox("Choose Crop for Nutrient Plan", list(CROP_DATA.keys()), key="fert_crop")
    calc_area = st.number_input("Area (Acres)", min_value=0.1, max_value=500.0, value=1.0, step=0.5, key="fert_area")

    npk_str = CROP_DATA[calc_crop]["npk"].split()[0]
    n_val, p_val, k_val = [float(x) for x in npk_str.split(":")]

    c1, c2, c3 = st.columns(3)
    c1.metric("Nitrogen (N)", f"{n_val * calc_area:.1f} kg")
    c2.metric("Phosphorus (P)", f"{p_val * calc_area:.1f} kg")
    c3.metric("Potassium (K)", f"{k_val * calc_area:.1f} kg")

# --- Tab 3: Farm Logs ---
with tab3:
    st.subheader("Recorded Field History")
    df = pd.read_sql_query("SELECT * FROM farm_logs ORDER BY id DESC", conn)
    if df.empty:
        st.info("No logs recorded yet. Save a reading in the 'Irrigation & Advisory' tab.")
    else:
        st.dataframe(df, use_container_width=True)
