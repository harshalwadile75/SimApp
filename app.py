import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page configuration
st.set_page_config(
    page_title="Solar PV System Analyzer - Professional Report Generator",
    page_icon="☀️",
    layout="wide"
)

# Custom CSS styling
st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem;
    border-radius: 15px;
    color: white;
    text-align: center;
    margin-bottom: 2rem;
    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
}
.metric-card {
    background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
    padding: 1.5rem;
    border-radius: 15px;
    color: white;
    text-align: center;
    margin: 0.5rem 0;
    box-shadow: 0 8px 25px rgba(255,107,53,0.3);
    transition: transform 0.3s ease;
}
.metric-card:hover {
    transform: translateY(-5px);
}
.section-header {
    background: linear-gradient(90deg, #2E86AB 0%, #A23B72 100%);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    font-size: 1.2rem;
    font-weight: bold;
    margin: 1rem 0;
    text-align: center;
}
.warning-box {
    background: #fff3cd;
    border-left: 5px solid #ffc107;
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 5px;
}
</style>
""", unsafe_allow_html=True)

def main():
    st.markdown("""
    <div class="main-header">
        <h1>☀️ Professional Solar PV System Analyzer</h1>
        <p>Comprehensive System Design, Analysis & Reporting Tool</p>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.header("🔧 System Configuration")
    project_name = st.sidebar.text_input("Project Name", "Solar PV System")
    author_name = st.sidebar.text_input("Author", "System Designer")
    location = st.sidebar.text_input("Location", "Geneva, Switzerland")
    latitude = st.sidebar.slider("Latitude", -60.0, 60.0, 46.2)
    longitude = st.sidebar.slider("Longitude", -180.0, 180.0, 6.15)
    altitude = st.sidebar.number_input("Altitude (m)", 0, 5000, 398)
    timezone = st.sidebar.selectbox("Time Zone", [f"UTC{offset:+d}" for offset in range(-12, 13)], index=12)

    # PV Array
    panel_power = st.sidebar.number_input("Panel Power (Wp)", 100, 1000, 595)
    num_panels = st.sidebar.number_input("Number of Panels", 1, 100, 21)
    panel_tilt = st.sidebar.slider("Tilt (°)", 0, 90, 20)
    panel_azimuth = st.sidebar.slider("Azimuth (°)", -180, 180, 0)
    panel_area = st.sidebar.number_input("Panel Area (m²)", 1.0, 5.0, 2.79, step=0.01)

    # Battery
    battery_enabled = st.sidebar.checkbox("Enable Battery Storage", True)
    if battery_enabled:
        battery_type = st.sidebar.selectbox("Battery Type", ["Lead-acid", "Lithium-ion", "LFP"])
        battery_voltage = st.sidebar.selectbox("Battery Voltage (V)", [12, 24, 48], index=1)
        battery_capacity = st.sidebar.number_input("Capacity (Ah)", 50, 2000, 140)
        num_batt_series = st.sidebar.number_input("Batteries in Series", 1, 10, 2)
        num_batt_parallel = st.sidebar.number_input("Batteries in Parallel", 1, 20, 13)
        min_soc = st.sidebar.slider("Min SOC (%)", 10, 50, 20)
        max_soc = st.sidebar.slider("Max SOC (%)", 80, 100, 95)
    else:
        battery_type = None
        battery_voltage = battery_capacity = num_batt_series = num_batt_parallel = min_soc = max_soc = 0

    # Load
    daily_load = st.sidebar.number_input("Daily Energy Need (kWh)", 1.0, 50.0, 6.6)
    load_profile = st.sidebar.selectbox("Load Profile", ["Constant", "Residential", "Commercial"])

    # Performance
    temp_coeff = st.sidebar.slider("Temp Coefficient (%/°C)", -1.0, 0.0, -0.4)
    dc_loss = st.sidebar.slider("DC Losses (%)", 0.5, 5.0, 1.5)
    inverter_eff = st.sidebar.slider("Inverter Efficiency (%)", 85.0, 98.0, 95.0)
    mismatch = st.sidebar.slider("Module Mismatch (%)", 0.0, 5.0, 2.0)
    soiling = st.sidebar.slider("Soiling Loss (%)", 0.0, 10.0, 2.0)
    analysis_days = st.sidebar.selectbox("Analysis Period", [30, 90, 365], index=2)

    # Derived
    system_size = panel_power * num_panels / 1000  # kWp
    system_area = panel_area * num_panels
    battery_energy = (battery_voltage * battery_capacity * num_batt_series * num_batt_parallel) / 1000 if battery_enabled else 0

    @st.cache_data
    def simulate(days, lat, tilt, azimuth, system_kw, load_kwh, batt_enabled, batt_kwh):
        np.random.seed(42)
        data = []
        for d in range(days):
            day_angle = 2 * math.pi * d / 365
            temp = 15 + 10 * math.sin(day_angle)
            irradiance = 1000 * max(0, math.cos(math.radians(tilt)))
            pv_energy = irradiance * system_kw * 4 / 1000  # Simple estimate
            load = load_kwh
            supplied = min(pv_energy, load)
            excess = max(0, pv_energy - load)
            missing = max(0, load - pv_energy)
            data.append({
                'Day': d+1,
                'Irradiance': irradiance,
                'Temperature': temp,
                'PV_Energy': pv_energy,
                'Load': load,
                'Supplied': supplied,
                'Excess': excess,
                'Missing': missing
            })
        return pd.DataFrame(data)

    with st.spinner("🔄 Simulating system performance..."):
        df = simulate(analysis_days, latitude, panel_tilt, panel_azimuth, system_size, daily_load, battery_enabled, battery_energy)

    total_pv = df['PV_Energy'].sum()
    total_supplied = df['Supplied'].sum()
    total_excess = df['Excess'].sum()
    total_missing = df['Missing'].sum()

    capacity_factor = (total_pv / (system_size * 24 * analysis_days)) * 100 if system_size > 0 else 0
    solar_fraction = (total_supplied / (daily_load * analysis_days)) * 100
    efficiency = (total_supplied / total_pv) * 100 if total_pv > 0 else 0

    st.markdown('<div class="section-header">📊 System Performance Overview</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("System Size (kWp)", f"{system_size:.1f}")
    col2.metric("Total PV Energy (kWh)", f"{total_pv:.1f}")
    col3.metric("Solar Fraction (%)", f"{solar_fraction:.1f}")
    col4.metric("Capacity Factor (%)", f"{capacity_factor:.1f}")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📈 Daily Overview", "📊 Loss Summary", "📋 System Details"])

    with tab1:
        st.subheader("PV Generation & Load")
        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(go.Scatter(x=df['Day'], y=df['PV_Energy'], name='PV Energy', line_color='orange'))
        fig.add_trace(go.Scatter(x=df['Day'], y=df['Load'], name='Load', line_color='blue'))
        fig.add_trace(go.Scatter(x=df['Day'], y=df['Supplied'], name='Supplied', line_color='green'))
        fig.update_layout(title="Daily Energy Flows", height=400)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Estimated Losses")
        loss_data = {
            "DC Loss (kWh)": total_pv * (dc_loss/100),
            "Mismatch (kWh)": total_pv * (mismatch/100),
            "Soiling (kWh)": total_pv * (soiling/100),
            "Inverter (kWh)": total_pv * ((100 - inverter_eff)/100),
            "Excess (kWh)": total_excess,
            "Missing (kWh)": total_missing
        }
        loss_df = pd.DataFrame(list(loss_data.items()), columns=["Loss Type", "Energy (kWh)"])
        fig = go.Figure(data=[
            go.Bar(x=loss_df["Loss Type"], y=loss_df["Energy (kWh)"], marker_color='crimson')
        ])
        fig.update_layout(title="Loss Breakdown", height=400)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("System Configuration Summary")
        config = {
            "Project": project_name,
            "Author": author_name,
            "Location": location,
            "System Size (kWp)": system_size,
            "Total Area (m²)": system_area,
            "Battery Storage (kWh)": battery_energy,
            "Analysis Period (days)": analysis_days
        }
        st.dataframe(pd.DataFrame(list(config.items()), columns=["Parameter", "Value"]))

if __name__ == "__main__":
    main()
