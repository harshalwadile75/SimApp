import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Page config
st.set_page_config(
    page_title="Solar PV System Analyzer - Professional Report Generator",
    page_icon="☀️",
    layout="wide"
)

# Enhanced styling
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

.info-box {
    background: #f8f9fa;
    border-left: 5px solid #2E86AB;
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 5px;
}

.warning-box {
    background: #fff3cd;
    border-left: 5px solid #ffc107;
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 5px;
}

.success-box {
    background: #d4edda;
    border-left: 5px solid #28a745;
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 5px;
}

.data-table {
    background: white;
    border-radius: 10px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

def main():
    # Enhanced title
    st.markdown("""
    <div class="main-header">
        <h1>☀️ Professional Solar PV System Analyzer</h1>
        <p>Comprehensive System Design, Analysis & Reporting Tool</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar configuration
    st.sidebar.header("🔧 System Configuration")
    
    # Project Information
    st.sidebar.subheader("📋 Project Information")
    project_name = st.sidebar.text_input("Project Name", "Solar PV System")
    author_name = st.sidebar.text_input("Author", "System Designer")
    
    # Location settings
    st.sidebar.subheader("📍 Geographic Location")
    location_name = st.sidebar.text_input("Location", "Geneva, Switzerland")
    latitude = st.sidebar.slider("Latitude", -60.0, 60.0, 46.2, help="Positive for North, negative for South")
    longitude = st.sidebar.slider("Longitude", -180.0, 180.0, 6.15)
    altitude = st.sidebar.number_input("Altitude (m)", 0, 5000, 398)
    timezone = st.sidebar.selectbox("Time Zone", ["UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8", "UTC-7", "UTC-6", "UTC-5", "UTC-4", "UTC-3", "UTC-2", "UTC-1", "UTC+0", "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6", "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12"], index=13)
    
    # PV Array Configuration
    st.sidebar.subheader("🔋 PV Array Configuration")
    panel_power = st.sidebar.number_input("Panel Power (Wp)", 100, 1000, 595)
    num_panels = st.sidebar.number_input("Number of Panels", 1, 100, 21)
    panel_tilt = st.sidebar.slider("Panel Tilt (°)", 0, 90, 20)
    panel_azimuth = st.sidebar.slider("Panel Azimuth (°)", -180, 180, 0, help="-180 to 180°, 0=South, 90=West, -90=East")
    panel_area = st.sidebar.number_input("Panel Area (m²)", 1.0, 5.0, 2.79, step=0.01)
    
    # Battery System Configuration
    st.sidebar.subheader("🔋 Battery System")
    battery_enabled = st.sidebar.checkbox("Enable Battery Storage", True)
    
    if battery_enabled:
        battery_type = st.sidebar.selectbox("Battery Technology", 
            ["Lead-acid, vented, tubular", "Lead-acid, sealed (AGM)", "Lithium-ion", "Lithium Iron Phosphate"])
        battery_voltage = st.sidebar.selectbox("Battery Voltage (V)", [12, 24, 48], index=1)
        battery_capacity = st.sidebar.number_input("Battery Capacity per Unit (Ah)", 50, 2000, 140)
        num_batteries_series = st.sidebar.number_input("Batteries in Series", 1, 10, 2)
        num_batteries_parallel = st.sidebar.number_input("Batteries in Parallel", 1, 20, 13)
        min_soc = st.sidebar.slider("Minimum SOC (%)", 10, 50, 20)
        max_soc = st.sidebar.slider("Maximum SOC (%)", 80, 100, 95)
    
    # Load Configuration
    st.sidebar.subheader("⚡ Load Configuration")
    daily_energy_need = st.sidebar.number_input("Daily Energy Need (kWh)", 1.0, 50.0, 6.6)
    load_profile = st.sidebar.selectbox("Load Profile", ["Constant", "Residential", "Commercial", "Custom"])
    
    # Performance Parameters
    st.sidebar.subheader("📊 Performance Parameters")
    temp_coeff = st.sidebar.slider("Temperature Coefficient (%/°C)", -1.0, 0.0, -0.4)
    dc_wiring_loss = st.sidebar.slider("DC Wiring Losses (%)", 0.5, 5.0, 1.5)
    converter_efficiency = st.sidebar.slider("Converter Efficiency (%)", 85.0, 98.0, 95.0)
    module_mismatch = st.sidebar.slider("Module Mismatch (%)", 0.0, 5.0, 2.0)
    soiling_loss = st.sidebar.slider("Soiling Losses (%)", 0.0, 10.0, 2.0)
    
    # Analysis Period
    analysis_days = st.sidebar.selectbox("Analysis Period", [30, 90, 365], index=2)
    
    # Calculate system parameters
    total_power = panel_power * num_panels / 1000  # kW
    total_area = panel_area * num_panels
    
    if battery_enabled:
        battery_pack_voltage = battery_voltage * num_batteries_series
        total_battery_capacity = battery_capacity * num_batteries_parallel
        total_stored_energy = battery_pack_voltage * total_battery_capacity / 1000  # kWh
    else:
        battery_pack_voltage = 0
        total_battery_capacity = 0
        total_stored_energy = 0
    
    # Generate enhanced synthetic data
    @st.cache_data
    def generate_enhanced_data(days, lat, tilt, azimuth, total_pwr, daily_need, batt_enabled, batt_capacity, min_soc_pct, max_soc_pct):
        data = []
        np.random.seed(42)
        
        # Battery state tracking
        if batt_enabled:
            battery_soc = 0.8  # Start at 80% SOC
            battery_kwh = total_stored_energy
        else:
            battery_soc = 0
            battery_kwh = 0
        
        daily_load = daily_need * 1000 / 24  # Hourly load in Wh
        
        for day in range(days):
            # Seasonal temperature and irradiance variation
            day_angle = 2 * math.pi * day / 365
            temp_base = 15 + 15 * math.sin(day_angle - math.pi/2)  # Seasonal temperature
            declination = 23.45 * math.sin(day_angle - math.pi/2)  # Solar declination
            
            daily_energy_produced = 0
            daily_energy_consumed = 0
            daily_battery_charge = 0
            daily_battery_discharge = 0
            
            for hour in range(24):
                # Enhanced temperature model
                hour_angle = 2 * math.pi * (hour - 6) / 24
                temp = temp_base + 8 * math.sin(hour_angle) + np.random.normal(0, 1.5)
                
                # Enhanced solar irradiance model
                if 5 <= hour <= 19:
                    # Solar elevation calculation
                    hour_angle_solar = 15 * (hour - 12)
                    elevation = math.asin(
                        math.sin(math.radians(lat)) * math.sin(math.radians(declination)) +
                        math.cos(math.radians(lat)) * math.cos(math.radians(declination)) * 
                        math.cos(math.radians(hour_angle_solar))
                    )
                    
                    if elevation > 0:
                        # Direct normal irradiance
                        air_mass = 1 / math.sin(elevation)
                        dni = 900 * math.exp(-0.357 * (air_mass ** 0.678)) if air_mass < 10 else 0
                        
                        # Diffuse horizontal irradiance
                        dhi = 100 + 50 * math.sin(elevation)
                        
                        # Global horizontal irradiance
                        ghi = dni * math.sin(elevation) + dhi
                        
                        # Panel orientation adjustment
                        panel_elevation = elevation + math.radians(tilt)
                        azimuth_factor = math.cos(math.radians(azimuth - 180))  # South = 0
                        
                        # Global irradiance on tilted surface
                        irradiance = ghi * (math.sin(panel_elevation) / math.sin(elevation)) * azimuth_factor
                        irradiance = max(0, irradiance) * np.random.uniform(0.7, 1.0)  # Weather factor
                    else:
                        irradiance = 0
                else:
                    irradiance = 0
                
                # PV power calculation with losses
                if irradiance > 0:
                    # Base power
                    pv_power = total_pwr * 1000 * (irradiance / 1000)
                    
                    # Temperature derating
                    temp_derating = 1 + temp_coeff * (temp - 25) / 100
                    pv_power *= temp_derating
                    
                    # Apply losses
                    pv_power *= (1 - dc_wiring_loss/100)  # DC wiring
                    pv_power *= (1 - module_mismatch/100)  # Mismatch
                    pv_power *= (1 - soiling_loss/100)  # Soiling
                    pv_power *= (converter_efficiency/100)  # Converter
                    
                    pv_power = max(0, pv_power)
                else:
                    pv_power = 0
                
                # Load calculation (vary by hour and load profile)
                if load_profile == "Residential":
                    load_factors = [0.6, 0.5, 0.5, 0.5, 0.7, 0.8, 1.0, 1.2, 1.0, 0.8, 0.7, 0.8, 
                                   0.9, 0.8, 0.7, 0.8, 1.0, 1.4, 1.6, 1.5, 1.3, 1.2, 1.0, 0.8]
                    load_power = daily_load * load_factors[hour]
                elif load_profile == "Commercial":
                    load_factors = [0.3, 0.3, 0.3, 0.3, 0.4, 0.6, 0.8, 1.0, 1.2, 1.3, 1.2, 1.1,
                                   1.0, 1.1, 1.2, 1.3, 1.2, 1.0, 0.8, 0.6, 0.4, 0.3, 0.3, 0.3]
                    load_power = daily_load * load_factors[hour]
                else:  # Constant
                    load_power = daily_load
                
                # Battery and energy balance
                if batt_enabled:
                    energy_balance = pv_power - load_power
                    battery_charge_power = 0
                    battery_discharge_power = 0
                    
                    if energy_balance > 0:  # Excess energy - charge battery
                        if battery_soc < max_soc_pct/100:
                            charge_power = min(energy_balance, battery_kwh * 1000 * 0.2)  # Max 20% C-rate
                            battery_charge_power = charge_power
                            battery_soc += (charge_power / (battery_kwh * 1000)) * 0.9  # 90% efficiency
                            battery_soc = min(battery_soc, max_soc_pct/100)
                            daily_battery_charge += charge_power
                        excess_energy = max(0, energy_balance - battery_charge_power)
                    else:  # Energy deficit - discharge battery
                        if battery_soc > min_soc_pct/100:
                            discharge_power = min(abs(energy_balance), battery_kwh * 1000 * 0.2)  # Max 20% C-rate
                            available_energy = battery_kwh * 1000 * (battery_soc - min_soc_pct/100)
                            discharge_power = min(discharge_power, available_energy)
                            battery_discharge_power = discharge_power
                            battery_soc -= discharge_power / (battery_kwh * 1000)
                            daily_battery_discharge += discharge_power
                        excess_energy = 0
                    
                    # Self-discharge (0.1% per hour)
                    battery_soc *= 0.999
                    
                    energy_supplied = min(load_power, pv_power + battery_discharge_power)
                    missing_energy = max(0, load_power - energy_supplied)
                else:
                    energy_supplied = min(load_power, pv_power)
                    missing_energy = max(0, load_power - pv_power)
                    excess_energy = max(0, pv_power - load_power)
                    battery_charge_power = 0
                    battery_discharge_power = 0
                
                daily_energy_produced += pv_power
                daily_energy_consumed += energy_supplied
                
                data.append({
                    'day': day + 1,
                    'hour': hour,
                    'temperature': round(temp, 1),
                    'irradiance': round(irradiance, 1),
                    'pv_power': round(pv_power, 1),
                    'load_power': round(load_power, 1),
                    'energy_supplied': round(energy_supplied, 1),
                    'missing_energy': round(missing_energy, 1),
                    'excess_energy': round(excess_energy, 1),
                    'battery_soc': round(battery_soc * 100, 1),
                    'battery_charge': round(battery_charge_power, 1),
                    'battery_discharge': round(battery_discharge_power, 1)
                })
        
        return pd.DataFrame(data)
    
    # Generate enhanced data
    with st.spinner("🔄 Generating comprehensive system analysis..."):
        df = generate_enhanced_data(
            analysis_days, latitude, panel_tilt, panel_azimuth, 
            total_power, daily_energy_need, battery_enabled, 
            total_stored_energy, min_soc, max_soc
        )
    
    # Calculate key metrics
    total_pv_energy = df['pv_power'].sum() / 1000  # kWh
    total_energy_supplied = df['energy_supplied'].sum() / 1000  # kWh
    total_missing_energy = df['missing_energy'].sum() / 1000  # kWh
    total_excess_energy = df['excess_energy'].sum() / 1000  # kWh
    
    # Performance metrics
    specific_production = total_pv_energy / total_power if total_power > 0 else 0
    capacity_factor = (total_pv_energy / (total_power * 24 * analysis_days)) * 100
    solar_fraction = (total_energy_supplied / (daily_energy_need * analysis_days)) * 100 if daily_energy_need > 0 else 0
    system_efficiency = (total_energy_supplied / total_pv_energy) * 100 if total_pv_energy > 0 else 0
    
    # Display main metrics
    st.markdown('<div class="section-header">📊 System Performance Overview</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h4>System Size</h4>
            <h2>{total_power:.1f} kWp</h2>
            <small>{num_panels} panels</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h4>Energy Production</h4>
            <h2>{total_pv_energy:.0f} kWh</h2>
            <small>{specific_production:.0f} kWh/kWp</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h4>Solar Fraction</h4>
            <h2>{solar_fraction:.1f}%</h2>
            <small>Energy independence</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h4>Capacity Factor</h4>
            <h2>{capacity_factor:.1f}%</h2>
            <small>System utilization</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        if battery_enabled:
            st.markdown(f"""
            <div class="metric-card">
                <h4>Battery Storage</h4>
                <h2>{total_stored_energy:.1f} kWh</h2>
                <small>{num_batteries_series}S{num_batteries_parallel}P</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="metric-card">
                <h4>System Efficiency</h4>
                <h2>{system_efficiency:.1f}%</h2>
                <small>Overall performance</small>
            </div>
            """, unsafe_allow_html=True)
    
    # Tabs for detailed analysis
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Performance Analysis", 
        "🔋 Battery Analysis", 
        "📊 Loss Analysis", 
        "🌍 Environmental Data",
        "📋 System Configuration", 
        "📄 Professional Report"
    ])
    
    with tab1:
        st.markdown('<div class="section-header">📈 System Performance Analysis</div>', unsafe_allow_html=True)
        
        # Monthly analysis
        if analysis_days >= 90:
            df['month'] = ((df['day'] - 1) // 30) + 1
            monthly_data = df.groupby('month').agg({
                'pv_power': 'sum',
                'energy_supplied': 'sum',
                'missing_energy': 'sum',
                'excess_energy': 'sum',
                'irradiance': 'mean',
                'temperature': 'mean'
            }).reset_index()
            
            monthly_data['pv_energy_kwh'] = monthly_data['pv_power'] / 1000
            monthly_data['supplied_kwh'] = monthly_data['energy_supplied'] / 1000
            monthly_data['missing_kwh'] = monthly_data['missing_energy'] / 1000
            monthly_data['excess_kwh'] = monthly_data['excess_energy'] / 1000
            
            # Monthly energy balance chart
            fig = make_subplots(rows=2, cols=2, 
                              subplot_titles=('Monthly Energy Production', 'Energy Balance', 
                                            'Average Irradiance', 'Average Temperature'))
            
            fig.add_trace(go.Bar(x=monthly_data['month'], y=monthly_data['pv_energy_kwh'], 
                               name='PV Production', marker_color='orange'), row=1, col=1)
            
            fig.add_trace(go.Bar(x=monthly_data['month'], y=monthly_data['supplied_kwh'], 
                               name='Energy Supplied', marker_color='green'), row=1, col=2)
            fig.add_trace(go.Bar(x=monthly_data['month'], y=monthly_data['excess_kwh'], 
                               name='Excess Energy', marker_color='blue'), row=1, col=2)
            fig.add_trace(go.Bar(x=monthly_data['month'], y=monthly_data['missing_kwh'], 
                               name='Missing Energy', marker_color='red'), row=1, col=2)
            
            fig.add_trace(go.Scatter(x=monthly_data['month'], y=monthly_data['irradiance'], 
                                   mode='lines+markers', name='Irradiance', line_color='yellow'), row=2, col=1)
            
            fig.add_trace(go.Scatter(x=monthly_data['month'], y=monthly_data['temperature'], 
                                   mode='lines+markers', name='Temperature', line_color='red'), row=2, col=2)
            
            fig.update_layout(height=600, showlegend=True, title_text="Monthly Performance Overview")
            st.plotly_chart(fig, use_container_width=True)
        
        # Daily profile analysis
        st.subheader("Average Daily Profile")
        hourly_avg = df.groupby('hour').agg({
            'pv_power': 'mean',
            'load_power': 'mean',
            'energy_supplied': 'mean',
            'irradiance': 'mean'
        }).reset_index()
        
        fig = make_subplots(rows=1, cols=2, subplot_titles=('Power Profile', 'Irradiance Profile'))
        
        fig.add_trace(go.Scatter(x=hourly_avg['hour'], y=hourly_avg['pv_power'], 
                               mode='lines', name='PV Generation', line_color='orange'), row=1, col=1)
        fig.add_trace(go.Scatter(x=hourly_avg['hour'], y=hourly_avg['load_power'], 
                               mode='lines', name='Load Demand', line_color='blue'), row=1, col=1)
        fig.add_trace(go.Scatter(x=hourly_avg['hour'], y=hourly_avg['energy_supplied'], 
                               mode='lines', name='Energy Supplied', line_color='green'), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=hourly_avg['hour'], y=hourly_avg['irradiance'], 
                               mode='lines', name='Solar Irradiance', line_color='red'), row=1, col=2)
        
        fig.update_layout(height=400, title_text="Average Daily Profiles")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        if battery_enabled:
            st.markdown('<div class="section-header">🔋 Battery System Analysis</div>', unsafe_allow_html=True)
            
            # Battery SOC analysis
            daily_battery = df.groupby('day').agg({
                'battery_soc': ['min', 'max', 'mean'],
                'battery_charge': 'sum',
                'battery_discharge': 'sum'
            }).reset_index()
            
            daily_battery.columns = ['day', 'soc_min', 'soc_max', 'soc_avg', 'daily_charge', 'daily_discharge']
            
            # Battery performance metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                avg_soc = df['battery_soc'].mean()
                st.metric("Average SOC", f"{avg_soc:.1f}%")
            
            with col2:
                min_soc = df['battery_soc'].min()
                st.metric("Minimum SOC", f"{min_soc:.1f}%")
            
            with col3:
                total_charge = df['battery_charge'].sum() / 1000
                st.metric("Total Charge", f"{total_charge:.1f} kWh")
            
            with col4:
                total_discharge = df['battery_discharge'].sum() / 1000
                st.metric("Total Discharge", f"{total_discharge:.1f} kWh")
            
            # Battery SOC over time
            fig = make_subplots(rows=2, cols=1, 
                              subplot_titles=('Battery State of Charge', 'Daily Charge/Discharge'))
            
            sample_data = df[df['day'] <= min(30, analysis_days)]  # Show first 30 days
            fig.add_trace(go.Scatter(x=sample_data.index, y=sample_data['battery_soc'], 
                                   mode='lines', name='SOC (%)', line_color='blue'), row=1, col=1)
            
            fig.add_trace(go.Bar(x=daily_battery['day'][:30], y=daily_battery['daily_charge']/1000, 
                               name='Daily Charge (kWh)', marker_color='green'), row=2, col=1)
            fig.add_trace(go.Bar(x=daily_battery['day'][:30], y=-daily_battery['daily_discharge']/1000, 
                               name='Daily Discharge (kWh)', marker_color='red'), row=2, col=1)
            
            fig.update_layout(height=600, title_text="Battery Performance Analysis")
            st.plotly_chart(fig, use_container_width=True)
            
            # Battery efficiency analysis
            st.subheader("Battery Efficiency Analysis")
            if total_charge > 0:
                roundtrip_efficiency = (total_discharge / total_charge) * 100
                st.info(f"📊 **Battery Round-trip Efficiency:** {roundtrip_efficiency:.1f}%")
            
            # Battery aging estimation
            total_throughput = (total_charge + total_discharge) / 2
            estimated_cycles = total_throughput / (total_stored_energy * 0.8)  # 80% DOD
            st.info(f"📊 **Estimated Equivalent Cycles:** {estimated_cycles:.1f} cycles")
            
        else:
            st.markdown('<div class="warning-box">⚠️ Battery system is disabled. Enable battery storage in the sidebar to see battery analysis.</div>', unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<div class="section-header">📊 System Loss Analysis</div>', unsafe_allow_html=True)
        
        # Calculate losses
        theoretical_energy = total_power * analysis_days * 24 * 0.2  # Assume 20% capacity factor for theoretical
        
        losses = {
            'Theoretical Maximum': theoretical_energy,
            'Available Solar Energy': total_pv_energy + (total_pv_energy * 0.3),  # Estimate
            'DC Wiring Losses': total_pv_energy * (dc_wiring_loss/100),
            'Temperature Losses': total_pv_energy * 0.05,  # Estimate 5%
            'Module Mismatch': total_pv_energy * (module_mismatch/100),
            'Soiling Losses': total_pv_energy * (soiling_loss/100),
            'Converter Losses': total_pv_energy * ((100-converter_efficiency)/100),
            'Unused Energy (Battery Full)': total_excess_energy,
            'Final Useful Energy': total_energy_supplied
        }
        
        # Create loss diagram
        loss_df = pd.DataFrame(list(losses.items()), columns=['Loss Type', 'Energy (kWh)'])
        
        fig = go.Figure(data=[
            go.Bar(x=loss_df['Loss Type'], y=loss_df['Energy (kWh)'], 
                   marker_color=['green', 'lightgreen', 'orange', 'orange', 'orange', 'orange', 'red', 'blue', 'darkgreen'])
        ])
        
        fig.update_layout(
            title="System Loss Analysis - Energy Flow Diagram",
            xaxis_title="Loss Components",
            yaxis_title="Energy (kWh)",
            height=500,
            xaxis_tickangle=45
        )
        st.plotly_chart(fig, use_container_
