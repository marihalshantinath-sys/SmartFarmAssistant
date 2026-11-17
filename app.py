import sqlite3
from datetime import datetime, date
import pandas as pd
import streamlit as st

st.set_page_config(page_title="SmartFarmAssistant", page_icon="🌱", layout="wide")

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("smart_farm.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS advisory_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            soil_type TEXT,
            environment TEXT,
            crop TEXT,
            area_acres REAL,
            water_liters REAL,
            fertilizer_plan TEXT,
            spray_plan TEXT,
            notes TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            skill TEXT,
            daily_wage REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_date TEXT,
            worker_name TEXT,
            status TEXT,
            wage_earned REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT,
            assigned_worker TEXT,
            due_date TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- AGRONOMIC KNOWLEDGE BASE ---
SOIL_ENV_CROPS = {
    ("Black Cotton Soil", "Hot & Dry"): ["Cotton", "Sorghum (Jowar)", "Sunflower", "Tur (Pigeon Pea)"],
    ("Black Cotton Soil", "Warm & Humid"): ["Sugarcane", "Soybean", "Cotton", "Turmeric"],
    ("Black Cotton Soil", "Monsoon / Heavy Rain"): ["Sugarcane", "Paddy (Rice)", "Soybean", "Maize"],
    ("Black Cotton Soil", "Cool & Moderate"): ["Wheat", "Chickpea (Bengal Gram)", "Safflower", "Onion"],
    ("Red Loamy Soil", "Hot & Dry"): ["Groundnut", "Ragi (Finger Millet)", "Castor", "Watermelon"],
    ("Red Loamy Soil", "Warm & Humid"): ["Tomato", "Chilli", "Arecanut", "Banana"],
    ("Red Loamy Soil", "Monsoon / Heavy Rain"): ["Maize", "Ragi (Finger Millet)", "Paddy (Rice)", "Ginger"],
    ("Red Loamy Soil", "Cool & Moderate"): ["Tomato", "Potato", "Cabbage", "Beans"],
    ("Alluvial Soil", "Hot & Dry"): ["Maize", "Sesame", "Watermelon", "Muskmelon"],
    ("Alluvial Soil", "Warm & Humid"): ["Sugarcane", "Banana", "Paddy (Rice)", "Tomato"],
    ("Alluvial Soil", "Monsoon / Heavy Rain"): ["Paddy (Rice)", "Sugarcane", "Jute", "Maize"],
    ("Alluvial Soil", "Cool & Moderate"): ["Wheat", "Potato", "Mustard", "Onion"],
    ("Sandy Soil", "Hot & Dry"): ["Pearl Millet (Bajra)", "Watermelon", "Cluster Bean", "Groundnut"],
    ("Sandy Soil", "Warm & Humid"): ["Coconut", "Cashew", "Sweet Potato", "Groundnut"],
    ("Sandy Soil", "Monsoon / Heavy Rain"): ["Groundnut", "Pearl Millet (Bajra)", "Green Gram"],
    ("Sandy Soil", "Cool & Moderate"): ["Carrot", "Radish", "Potato", "Cumin"],
    ("Laterite Soil", "Hot & Dry"): ["Cashew", "Mango", "Tapioca"],
    ("Laterite Soil", "Warm & Humid"): ["Arecanut", "Black Pepper", "Coconut", "Banana"],
    ("Laterite Soil", "Monsoon / Heavy Rain"): ["Paddy (Rice)", "Ginger", "Turmeric", "Arecanut"],
    ("Laterite Soil", "Cool & Moderate"): ["Coffee", "Tea", "Cardamom", "Beans"],
}

SOIL_NUTRIENT_FACTOR = {
    "Black Cotton Soil": {"n_mult": 1.0, "p_mult": 1.1, "k_mult": 0.9, "water_mult": 0.90},
    "Red Loamy Soil": {"n_mult": 1.1, "p_mult": 1.15, "k_mult": 1.0, "water_mult": 1.00},
    "Alluvial Soil": {"n_mult": 0.95, "p_mult": 1.0, "k_mult": 0.95, "water_mult": 0.95},
    "Sandy Soil": {"n_mult": 1.25, "p_mult": 1.2, "k_mult": 1.2, "water_mult": 1.25},
    "Laterite Soil": {"n_mult": 1.2, "p_mult": 1.25, "k_mult": 1.15, "water_mult": 1.10},
}

CROP_SPECS = {
    "Sugarcane": {"moisture": 65, "npk": (100, 40, 40), "spray_ml_per_l": 2.5, "water_l_acre": 200, "base_yield_q": 400},
    "Tomato": {"moisture": 60, "npk": (60, 30, 30), "spray_ml_per_l": 2.0, "water_l_acre": 180, "base_yield_q": 120},
    "Arecanut": {"moisture": 55, "npk": (40, 16, 56), "spray_ml_per_l": 2.0, "water_l_acre": 220, "base_yield_q": 14},
    "Maize": {"moisture": 50, "npk": (50, 25, 15), "spray_ml_per_l": 1.5, "water_l_acre": 150, "base_yield_q": 28},
    "Cotton": {"moisture": 45, "npk": (40, 20, 20), "spray_ml_per_l": 2.0, "water_l_acre": 160, "base_yield_q": 12},
    "Paddy (Rice)": {"moisture": 75, "npk": (50, 25, 25), "spray_ml_per_l": 1.8, "water_l_acre": 180, "base_yield_q": 25},
    "Wheat": {"moisture": 50, "npk": (48, 24, 16), "spray_ml_per_l": 1.5, "water_l_acre": 150, "base_yield_q": 20},
    "Groundnut": {"moisture": 45, "npk": (10, 20, 15), "spray_ml_per_l": 1.5, "water_l_acre": 140, "base_yield_q": 12},
    "Chilli": {"moisture": 55, "npk": (60, 30, 30), "spray_ml_per_l": 2.0, "water_l_acre": 180, "base_yield_q": 18},
    "Onion": {"moisture": 55, "npk": (45, 20, 25), "spray_ml_per_l": 1.8, "water_l_acre": 160, "base_yield_q": 90},
}

# --- HEADER ---
st.title("🌱 SmartFarmAssistant")
st.caption("Complete Soil & Crop Sowing Advisor, High-Yield Fertilizer/Spray Planner & Farm Workforce Manager")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌍 Soil, Environment & Sowing",
    "🧪 High-Yield Fertilizer & Spray",
    "💧 Irrigation & Field Log",
    "👷 Workers & Attendance",
    "📅 Farm Tasks",
    "📊 Reports & CSV Download"
])

# --- TAB 1: SOIL, ENVIRONMENT & CROP SOWING ADVISOR ---
with tab1:
    st.subheader("1. Field Soil & Atmosphere Assessment")
    c1, c2 = st.columns(2)
    with c1:
        soil_type = st.selectbox("Select Soil Type Present in Field", list(SOIL_NUTRIENT_FACTOR.keys()))
        environment = st.selectbox(
            "Select Environment / Atmosphere Condition",
            ["Hot & Dry", "Warm & Humid", "Monsoon / Heavy Rain", "Cool & Moderate"]
        )
        humidity = st.slider("Relative Atmospheric Humidity (%)", 15, 100, 60)
        temp_c = st.number_input("Current Atmosphere Temperature (°C)", value=29.0, step=0.5)

    with c2:
        st.subheader("2. Recommended Crops for Sowing")
        recommended_crops = SOIL_ENV_CROPS.get((soil_type, environment), ["Maize", "Pulses", "Vegetables"])
        st.success(f"**Best Crops to Sow in {soil_type} under {environment} Atmosphere:**")
        for idx, rc in enumerate(recommended_crops, 1):
            st.markdown(f"**{idx}. {rc}**")

        if humidity > 80 and temp_c > 25:
            st.warning("⚠️ High humidity & warmth detected: Elevated fungal/blight risk. Ensure wider row spacing and preventive bio-fungicide seed treatment before sowing.")
        elif temp_c > 36:
            st.warning("⚠️ High heat stress atmosphere: Prefer drought-tolerant varieties and mulching after sowing.")
        else:
            st.info("✅ Atmospheric conditions are favorable for seed germination and early root establishment.")

# --- TAB 2: HIGH-YIELD FERTILIZER & CHEMICAL SPRAY CALCULATOR ---
with tab2:
    st.subheader("High-Yield Nutrient & Chemical Spray Dosing")
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        selected_crop = st.selectbox("Select Crop to Grow", list(CROP_SPECS.keys()))
        field_acres = st.number_input("Field Area (Acres)", min_value=0.1, value=2.0, step=0.1)
        soil_for_calc = st.selectbox("Confirm Soil Type", list(SOIL_NUTRIENT_FACTOR.keys()), key="soil_calc")
        yield_goal = st.radio("Target Production Level", ["Standard Yield", "High Yield (+20% Intensive Nutrition)"], horizontal=True)
        tank_liters = st.number_input("Sprayer Tank Capacity (Liters)", min_value=5, value=16, step=1)

    with f_col2:
        specs = CROP_SPECS[selected_crop]
        s_mult = SOIL_NUTRIENT_FACTOR[soil_for_calc]
        y_mult = 1.20 if "High Yield" in yield_goal else 1.0

        n_kg = round(specs["npk"][0] * field_acres * s_mult["n_mult"] * y_mult, 1)
        p_kg = round(specs["npk"][1] * field_acres * s_mult["p_mult"] * y_mult, 1)
        k_kg = round(specs["npk"][2] * field_acres * s_mult["k_mult"] * y_mult, 1)

        urea_kg = round(n_kg / 0.46, 1)
        ssp_kg = round(p_kg / 0.16, 1)
        mop_kg = round(k_kg / 0.60, 1)

        total_spray_water = specs["water_l_acre"] * field_acres
        spray_dose_ml_l = round(specs["spray_ml_per_l"] * (1.1 if "High Yield" in yield_goal else 1.0), 2)
        total_chem_ml = round(total_spray_water * spray_dose_ml_l, 0)
        num_tanks = round(total_spray_water / tank_liters, 1)
        expected_yield = round(specs["base_yield_q"] * field_acres * (1.22 if "High Yield" in yield_goal else 1.0), 1)

        st.markdown("### 📦 Fertilizer Quantity Required")
        m1, m2, m3 = st.columns(3)
        m1.metric("Urea (Nitrogen)", f"{urea_kg} kg", f"{n_kg} kg N")
        m2.metric("SSP (Phosphorus)", f"{ssp_kg} kg", f"{p_kg} kg P")
        m3.metric("MOP (Potassium)", f"{mop_kg} kg", f"{k_kg} kg K")

        st.markdown("### 🚜 Foliar / Chemical Spray Quantity")
        s1, s2, s3 = st.columns(3)
        s1.metric("Spray Water", f"{total_spray_water:,.0f} L")
        s2.metric("Chemical / Tonic", f"{total_chem_ml:,.0f} ml", f"{spray_dose_ml_l} ml/L")
        s3.metric("Tank Refills", f"{num_tanks} Tanks")

        st.success(f"🌾 **Projected Harvest Output:** ~**{expected_yield} Quintals** across {field_acres} acres with this feeding schedule.")

# --- TAB 3: IRRIGATION & FIELD ADVISORY LOGGER ---
with tab3:
    st.subheader("Smart Irrigation & Field Advisory Logger")
    i_col1, i_col2 = st.columns(2)
    with i_col1:
        i_crop = st.selectbox("Crop", list(CROP_SPECS.keys()), key="i_crop")
        i_soil = st.selectbox("Soil Type", list(SOIL_NUTRIENT_FACTOR.keys()), key="i_soil")
        i_env = st.selectbox("Atmosphere", ["Hot & Dry", "Warm & Humid", "Monsoon / Heavy Rain", "Cool & Moderate"], key="i_env")
        i_area = st.number_input("Area (Acres)", min_value=0.1, value=2.0, step=0.1, key="i_area")
        i_moisture = st.slider("Current Soil Moisture (%)", 0, 100, 40)

    with i_col2:
        target_m = CROP_SPECS[i_crop]["moisture"]
        deficit = max(0, target_m - i_moisture)
        env_mult = 1.2 if i_env == "Hot & Dry" else (0.5 if i_env == "Monsoon / Heavy Rain" else 1.0)
        soil_w_mult = SOIL_NUTRIENT_FACTOR[i_soil]["water_mult"]
        rec_water = round(deficit * i_area * 90.0 * env_mult * soil_w_mult, 1)

        st.metric("Target Soil Moisture", f"{target_m}%")
        st.metric("Recommended Irrigation", f"{rec_water:,.1f} Liters")

        obs_notes = st.text_input("Field Observation / Notes", placeholder="e.g., Applied first Urea split dose; drip pressure normal.")
        if st.button("Save Advisory Log"):
            conn = sqlite3.connect("smart_farm.db")
            c = conn.cursor()
            c.execute(
                "INSERT INTO advisory_logs (timestamp, soil_type, environment, crop, area_acres, water_liters, fertilizer_plan, spray_plan, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    i_soil,
                    i_env,
                    i_crop,
                    i_area,
                    rec_water,
                    f"NPK {CROP_SPECS[i_crop]['npk']}",
                    f"{CROP_SPECS[i_crop]['spray_ml_per_l']} ml/L",
                    obs_notes,
                ),
            )
            conn.commit()
            conn.close()
            st.success("Field advisory saved to database!")

# --- TAB 4: WORKERS, ATTENDANCE & WAGES ---
with tab4:
    w_col1, w_col2 = st.columns(2)
    with w_col1:
        st.subheader("Register Farm Worker")
        w_name = st.text_input("Worker Name")
        w_skill = st.selectbox("Primary Skill", ["Spraying & Fertilizer", "Sowing & Planting", "Irrigation & Drip", "Harvesting", "General Labor"])
        w_wage = st.number_input("Daily Wage (₹)", min_value=100, value=450, step=50)
        if st.button("Add Worker") and w_name.strip():
            conn = sqlite3.connect("smart_farm.db")
            conn.execute("INSERT INTO workers (name, skill, daily_wage) VALUES (?, ?, ?)", (w_name.strip(), w_skill, w_wage))
            conn.commit()
            conn.close()
            st.success(f"Added worker: {w_name}")

    with w_col2:
        st.subheader("Mark Daily Attendance")
        conn = sqlite3.connect("smart_farm.db")
        workers_df = pd.read_sql_query("SELECT * FROM workers", conn)
        conn.close()

        if not workers_df.empty:
            att_date = st.date_input("Date", value=date.today())
            sel_worker = st.selectbox("Select Worker", workers_df["name"].tolist())
            att_status = st.selectbox("Attendance Status", ["Present (Full Day)", "Half-Day", "Absent"])
            base_wage = float(workers_df.loc[workers_df["name"] == sel_worker, "daily_wage"].values[0])
            earned = base_wage if "Present" in att_status else (base_wage * 0.5 if att_status == "Half-Day" else 0.0)

            st.info(f"Calculated Wage for {sel_worker}: **₹ {earned:.0f}**")
            if st.button("Save Attendance"):
                conn = sqlite3.connect("smart_farm.db")
                conn.execute(
                    "INSERT INTO attendance (work_date, worker_name, status, wage_earned) VALUES (?, ?, ?, ?)",
                    (str(att_date), sel_worker, att_status, earned),
                )
                conn.commit()
                conn.close()
                st.success("Attendance & wage recorded!")
        else:
            st.info("Add at least one worker on the left to record attendance.")

# --- TAB 5: FARM TASKS & REMINDERS ---
with tab5:
    st.subheader("Assign Farming Activities & Reminders")
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        t_name = st.text_input("Activity / Task Description", placeholder="e.g., Spray foliar micronutrient on Tomato plot")
        conn = sqlite3.connect("smart_farm.db")
        w_list = pd.read_sql_query("SELECT name FROM workers", conn)["name"].tolist()
        conn.close()
        t_worker = st.selectbox("Assign To", w_list if w_list else ["Self / Unassigned"])
        t_due = st.date_input("Due Date", value=date.today(), key="t_due")
        if st.button("Create Task") and t_name.strip():
            conn = sqlite3.connect("smart_farm.db")
            conn.execute("INSERT INTO tasks (task_name, assigned_worker, due_date, status) VALUES (?, ?, ?, ?)", (t_name.strip(), t_worker, str(t_due), "Pending"))
            conn.commit()
            conn.close()
            st.success("Task scheduled!")

    with t_col2:
        conn = sqlite3.connect("smart_farm.db")
        tasks_df = pd.read_sql_query("SELECT * FROM tasks ORDER BY id DESC", conn)
        conn.close()
        if not tasks_df.empty:
            st.dataframe(tasks_df, use_container_width=True)
        else:
            st.info("No scheduled tasks yet.")

# --- TAB 6: REPORTS & CSV EXPORT ---
with tab6:
    st.subheader("Download Farm Reports (CSV)")
    conn = sqlite3.connect("smart_farm.db")
    adv_df = pd.read_sql_query("SELECT * FROM advisory_logs ORDER BY id DESC", conn)
    att_df = pd.read_sql_query("SELECT * FROM attendance ORDER BY id DESC", conn)
    conn.close()

    st.markdown("#### 1. Soil, Irrigation & Crop Advisory Logs")
    if not adv_df.empty:
        st.dataframe(adv_df, use_container_width=True)
        st.download_button("📥 Download Advisory Report (CSV)", adv_df.to_csv(index=False).encode("utf-8"), "advisory_report.csv", "text/csv")
    else:
        st.info("No advisory logs saved yet.")

    st.markdown("#### 2. Worker Attendance & Wage Expenses")
    if not att_df.empty:
        total_wages = att_df["wage_earned"].sum()
        st.metric("Total Recorded Wage Expense", f"₹ {total_wages:,.0f}")
        st.dataframe(att_df, use_container_width=True)
        st.download_button("📥 Download Wage & Attendance Report (CSV)", att_df.to_csv(index=False).encode("utf-8"), "wage_report.csv", "text/csv")
    else:
        st.info("No attendance records saved yet.")