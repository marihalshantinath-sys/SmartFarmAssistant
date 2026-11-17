import sqlite3
from datetime import date, datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="SmartFarmAssistant V2.0",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- CUSTOM DARK GRID & EMERALD THEME (MATCHING TEMPLATE) ---
st.markdown(
    """
<style>
    /* Main dark navy background with subtle blueprint grid */
    .stApp {
        background-color: #111822;
        background-image: 
            linear-gradient(rgba(52, 211, 153, 0.06) 1px, transparent 1px),
            linear-gradient(90deg, rgba(52, 211, 153, 0.06) 1px, transparent 1px);
        background-size: 32px 32px;
        color: #F3F4F6;
    }

    /* Hero Banner Styling */
    .hero-card {
        background: linear-gradient(135deg, rgba(20, 31, 46, 0.95), rgba(15, 23, 34, 0.98));
        border: 1px solid rgba(52, 211, 153, 0.35);
        border-radius: 16px;
        padding: 22px 28px;
        margin-bottom: 20px;
        box-shadow: 0 8px 30px rgba(16, 185, 129, 0.12);
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 16px;
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: 0.5px;
        margin: 0;
        line-height: 1.15;
    }
    .hero-green {
        color: #4ADE80;
    }
    .hero-white {
        color: #FFFFFF;
    }
    .version-badge {
        background-color: #22C55E;
        color: #09131D;
        font-size: 0.95rem;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 8px;
        vertical-align: middle;
        margin-left: 8px;
    }
    .hero-sub {
        color: #9CA3AF;
        font-size: 0.95rem;
        margin-top: 6px;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #16202E;
        padding: 8px;
        border-radius: 12px;
        border: 1px solid rgba(74, 222, 128, 0.2);
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        color: #CBD5E1;
        font-weight: 600;
        padding: 8px 14px;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #22C55E, #10B981) !important;
        color: #08121C !important;
        font-weight: 700 !important;
    }

    /* Metric & Container Cards */
    [data-testid="stMetric"] {
        background-color: #162231;
        border: 1px solid rgba(74, 222, 128, 0.3);
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
    }
    [data-testid="stMetricValue"] {
        color: #4ADE80 !important;
        font-weight: 800;
    }
    [data-testid="stForm"] {
        background-color: #15202E;
        border: 1px solid rgba(52, 211, 153, 0.25);
        border-radius: 14px;
        padding: 20px;
    }

    /* Primary Emerald Buttons */
    .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
        background: linear-gradient(90deg, #22C55E, #16A34A) !important;
        color: #07111A !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.55rem 1.2rem !important;
        box-shadow: 0 4px 14px rgba(34, 197, 94, 0.3);
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        background: linear-gradient(90deg, #4ADE80, #22C55E) !important;
        transform: translateY(-1px);
    }

    /* Headings */
    h1, h2, h3, h4 {
        color: #E2E8F0 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("smart_farm.db")
    c = conn.cursor()
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
    conn.commit()
    conn.close()


init_db()

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
            <span class="hero-green">SMART FARM</span><br>
            <span class="hero-white">ASSISTANT</span>
            <span class="version-badge">V2.0</span>
        </div>
        <div class="hero-sub">
            ⚙️ Precision Soil & Crop Advisor &nbsp;•&nbsp; 🧪 High-Yield Dosing Engine &nbsp;•&nbsp; 👷 Workforce & Wage Control
        </div>
    </div>
    <div style="text-align:right; color:#4ADE80; font-weight:700; font-size:0.9rem;">
        ● SYSTEM ONLINE &nbsp;|&nbsp; SQLITE SYNCED
    </div>
</div>
""",
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌱 Soil & Sowing",
    "🧪 Fertilizer & Spray",
    "💧 Irrigation Log",
    "👷 Workers & Wages",
    "📋 Farm Tasks",
    "📊 Reports & Export",
])

# === TAB 1: SOIL, ENVIRONMENT & CROP SOWING ===
with tab1:
    st.subheader("Soil & Weather-Based Crop Sowing Recommendation")
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_soil = st.selectbox(
            "1. Select Field Soil Type", list(SOIL_PROFILES.keys())
        )
    with col2:
        selected_env = st.selectbox(
            "2. Current Environment / Weather", list(ENV_CONDITIONS.keys())
        )
    with col3:
        selected_crop = st.selectbox(
            "3. Target Crop for Sowing Guide", list(CROP_GUIDES.keys())
        )

    soil_info = SOIL_PROFILES[selected_soil]
    env_info = ENV_CONDITIONS[selected_env]
    crop_info = CROP_GUIDES[selected_crop]

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.info(
            f"**Best Suited Crops for {selected_soil}:**\n\n"
            + ", ".join(soil_info["best_crops"])
        )
        st.write(f"**💧 Moisture Retention:** {soil_info['water_holding']}")
        st.write(f"**🧪 Soil Nutrition Note:** {soil_info['fertilizer_tip']}")
    with c2:
        st.warning(
            f"**🌦️ Weather & Sowing Advisory ({selected_env}):**\n\n{env_info['sowing_advice']}"
        )
        st.write(f"**⚠️ Spray Timing Precaution:** {env_info['spray_warning']}")

    st.markdown(f"#### 🌾 Precision Sowing Blueprint: **{selected_crop}**")
    m1, m2, m3 = st.columns(3)
    m1.metric("Recommended Spacing", crop_info["spacing"])
    m2.metric("Seed Rate / Acre", crop_info["seed_rate"])
    m3.metric(
        "Irrigation Multiplier", f"{int(env_info['irrigation_factor']*100)}%"
    )
    st.success(f"**🚀 High-Yield Growth Booster:** {crop_info['yield_booster']}")

# === TAB 2: HIGH-YIELD FERTILIZER & CHEMICAL DOSING CALCULATOR ===
with tab2:
    st.subheader("High-Yield Fertilizer & Spray Dosing Calculator")
    fcol1, fcol2 = st.columns(2)
    with fcol1:
        calc_crop = st.selectbox(
            "Select Crop", list(CROP_GUIDES.keys()), key="fert_crop"
        )
        area_acres = st.number_input(
            "Field Area (in Acres)",
            min_value=0.25,
            max_value=500.0,
            value=2.0,
            step=0.25,
        )
    with fcol2:
        tank_liters = st.number_input(
            "Spray Pump / Tank Capacity (Liters)",
            min_value=10,
            max_value=2000,
            value=200,
            step=10,
        )
        chem_dose_per_liter = st.number_input(
            "Chemical / Foliar Dose (ml or grams per Liter)",
            min_value=0.1,
            max_value=50.0,
            value=2.5,
            step=0.5,
        )

    req_n, req_p, req_k = CROP_GUIDES[calc_crop]["npk_per_acre"]
    total_n = req_n * area_acres
    total_p = req_p * area_acres
    total_k = req_k * area_acres

    # Convert NPK to standard commercial bags (DAP 18-46-0, Urea 46-0-0, MOP 0-0-60)
    dap_kg = total_p / 0.46
    n_from_dap = dap_kg * 0.18
    remaining_n = max(0.0, total_n - n_from_dap)
    urea_kg = remaining_n / 0.46
    mop_kg = total_k / 0.60

    st.markdown(
        f"#### 📦 Exact Commercial Fertilizer Required for **{area_acres} Acres of {calc_crop}**"
    )
    fc1, fc2, fc3 = st.columns(3)
    fc1.metric("Urea (46% N)", f"{urea_kg:.1f} kg", f"{urea_kg/45:.1f} Bags")
    fc2.metric("DAP (18-46-0)", f"{dap_kg:.1f} kg", f"{dap_kg/50:.1f} Bags")
    fc3.metric("MOP Potash (60%)", f"{mop_kg:.1f} kg", f"{mop_kg/50:.1f} Bags")

    total_chem_needed = tank_liters * chem_dose_per_liter
    st.markdown("#### 🧴 Spray Tank Mixing Calculation")
    sc1, sc2 = st.columns(2)
    sc1.metric(
        "Total Chemical / Nutrient to Add",
        f"{total_chem_needed:.0f} ml / g",
        f"For {tank_liters} L tank",
    )
    sc2.metric(
        "15-Liter Knapsack Pump Dose",
        f"{15 * chem_dose_per_liter:.1f} ml / g",
        "Per 15L battery sprayer",
    )

# === TAB 3: IRRIGATION & FIELD LOGS ===
with tab3:
    st.subheader("Daily Soil Moisture & Irrigation Log")
    with st.form("irrigation_form", clear_on_submit=True):
        ic1, ic2, ic3 = st.columns(3)
        with ic1:
            log_date = st.date_input("Date", date.today())
            plot_name = st.text_input(
                "Plot / Field Name", placeholder="e.g., North Sugarcane Plot"
            )
        with ic2:
            soil_t = st.selectbox("Soil Type", list(SOIL_PROFILES.keys()))
            env_t = st.selectbox("Weather", list(ENV_CONDITIONS.keys()))
        with ic3:
            crop_t = st.selectbox("Crop", list(CROP_GUIDES.keys()))
            moisture_pct = st.slider("Current Soil Moisture (%)", 5, 100, 38)

        base_water = 12000  # liters per acre baseline
        factor = ENV_CONDITIONS[env_t]["irrigation_factor"]
        rec_liters = (
            round(base_water * factor * (1 - moisture_pct / 120), 0)
            if moisture_pct < 65
            else 0
        )

        st.info(
            f"💧 **Smart Irrigation Recommendation:** Apply **{rec_liters:,.0f} Liters/acre** based on {moisture_pct}% moisture & {env_t}."
        )
        notes = st.text_input(
            "Field Observation / Pest Note",
            placeholder="e.g., Drip run for 2 hours, healthy leaf color",
        )

        if st.form_submit_button("💾 Save Irrigation & Field Log"):
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
            st.success("✅ Field & irrigation log saved!")

# === TAB 4: WORKERS & DAILY ATTENDANCE ===
with tab4:
    st.subheader("Farm Workforce & Wage Management")
    wcol1, wcol2 = st.columns([1, 1.3])

    with wcol1:
        st.markdown("#### ➕ Register New Worker")
        with st.form("add_worker_form", clear_on_submit=True):
            w_name = st.text_input("Worker Full Name")
            w_role = st.selectbox(
                "Primary Role",
                [
                    "Field Labor",
                    "Tractor / Harvester Operator",
                    "Spraying Specialist",
                    "Irrigation Technician",
                    "Supervisor",
                ],
            )
            w_wage = st.number_input(
                "Daily Wage (₹)", min_value=100, max_value=5000, value=500, step=50
            )
            w_phone = st.text_input("Mobile Number (Optional)")
            if st.form_submit_button("Save Worker"):
                if w_name.strip():
                    try:
                        conn = sqlite3.connect("smart_farm.db")
                        conn.execute(
                            "INSERT INTO workers (name, role, daily_wage, phone) VALUES (?, ?, ?, ?)",
                            (w_name.strip(), w_role, w_wage, w_phone.strip()),
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"Added {w_name}!")
                    except sqlite3.IntegrityError:
                        st.error("Worker name already exists.")

    with wcol2:
        st.markdown("#### ✅ Mark Today's Attendance & Wages")
        conn = sqlite3.connect("smart_farm.db")
        workers_df = pd.read_sql_query("SELECT * FROM workers", conn)
        conn.close()

        if workers_df.empty:
            st.warning(
                "No workers registered yet. Add your workers on the left first."
            )
        else:
            with st.form("attendance_form"):
                att_date = st.date_input("Work Date", date.today())
                sel_worker = st.selectbox(
                    "Select Worker", workers_df["name"].tolist()
                )
                att_status = st.selectbox(
                    "Attendance Status",
                    ["Present (Full Day)", "Half Day", "Absent"],
                )
                work_done = st.text_input(
                    "Work / Task Performed",
                    placeholder="e.g., Fertilizer application & weeding",
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
                    st.success(
                        f"Recorded {att_status} for {sel_worker} (Wage: ₹{earned:.0f})"
                    )

# === TAB 5: FARM TASKS & SCHEDULE ===
with tab5:
    st.subheader("Farm Operations & Task Planner")
    with st.form("task_form", clear_on_submit=True):
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            t_date = st.date_input("Target Date", date.today())
            t_plot = st.text_input("Plot Name", placeholder="e.g., East Plot")
        with tc2:
            t_title = st.text_input(
                "Operation / Task",
                placeholder="e.g., Foliar spray 19:19:19 + Micronutrients",
            )
            t_assign = st.text_input(
                "Assigned Worker / Team", placeholder="e.g., Ramesh & Team"
            )
        with tc3:
            t_prio = st.selectbox("Priority", ["High", "Medium", "Low"])
            t_stat = st.selectbox(
                "Status", ["Pending", "In Progress", "Completed"]
            )

        if st.form_submit_button("➕ Add Farm Task"):
            if t_title.strip():
                conn = sqlite3.connect("smart_farm.db")
                conn.execute(
                    "INSERT INTO farm_tasks (due_date, plot_name, task_title, assigned_to, priority, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(t_date),
                        t_plot,
                        t_title.strip(),
                        t_assign,
                        t_prio,
                        t_stat,
                    ),
                )
                conn.commit()
                conn.close()
                st.success("Task added to farm schedule!")

    conn = sqlite3.connect("smart_farm.db")
    tasks_df = pd.read_sql_query(
        "SELECT id, due_date, plot_name, task_title, assigned_to, priority, status FROM farm_tasks ORDER BY due_date ASC",
        conn,
    )
    conn.close()
    if not tasks_df.empty:
        st.dataframe(tasks_df, use_container_width=True)

# === TAB 6: REPORTS & CSV EXPORT ===
with tab6:
    st.subheader("Download Farm Reports (CSV)")
    conn = sqlite3.connect("smart_farm.db")
    adv_df = pd.read_sql_query(
        "SELECT * FROM advisory_logs ORDER BY id DESC", conn
    )
    att_df = pd.read_sql_query(
        "SELECT * FROM attendance ORDER BY id DESC", conn
    )
    conn.close()

    st.markdown("#### 1. Soil, Irrigation & Crop Advisory Logs")
    if not adv_df.empty:
        st.dataframe(adv_df, use_container_width=True)
        st.download_button(
            "📥 Download Advisory Report (CSV)",
            adv_df.to_csv(index=False).encode("utf-8"),
            "advisory_report.csv",
            "text/csv",
        )
    else:
        st.info("No advisory logs saved yet.")

    st.markdown("#### 2. Worker Attendance & Wage Expenses")
    if not att_df.empty:
        total_wages = att_df["wage_earned"].sum()
        st.metric("Total Recorded Wage Expense", f"₹ {total_wages:,.0f}")
        st.dataframe(att_df, use_container_width=True)
        st.download_button(
            "📥 Download Wage & Attendance Report (CSV)",
            att_df.to_csv(index=False).encode("utf-8"),
            "wage_report.csv",
            "text/csv",
        )
    else:
        st.info("No attendance records saved yet.")