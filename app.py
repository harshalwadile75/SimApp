import streamlit as st
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Solar PV Analyzer",
    page_icon="☀️",
    layout="wide"
)

# Simple styling
st.markdown("""
<style>
.metric-card {
    background: linear-gradient(90deg, #FF6B35 0%, #F7931E 100%);
    padding: 1rem;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin: 0.5rem 0;
}
.header {
    color: #2E86AB;
    font-size: 1.5rem;
    font-weight: bold;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

def main():
    # Title
    st.title("☀️ Solar PV System Analyzer")
    st.markdown("---")
    
    # Sidebar inputs
    st.sidebar.header("System Configuration")
    
    # Location
    st.sidebar.subheader("📍 Location")
    latitude = st.sidebar.slider("Latitude", -60.0, 60.0, 40.0)
    
    # System specs
    st.sidebar.subheader("🔧 PV System")
    panel_power = st.sidebar.number_input("Panel Power (W)", 100, 1000, 400)
    num_panels = st.sidebar.number_input("Number of Panels", 1, 100, 20)
    panel_tilt = st.sidebar.slider("Panel Tilt (°)", 0, 90, 30)
    
    # Performance parameters
    st.sidebar.subheader("⚡ Performance")
    temp_coeff = st.sidebar.slider("Temperature Coefficient (%/°C)", -1.0, 0.0, -0.4)
    system_losses = st.sidebar.slider("Total System Losses (%)", 5, 25, 15)
    
    # Analysis period
    analysis_days = st.sidebar.selectbox("Analysis Period", [30, 90, 180, 365])
    
    # Calculate system size
    total_power = panel_power * num_panels
    system_efficiency = (100 - system_losses) / 100
    
    # Generate simple synthetic data
    @st.cache_data
    def generate_simple_data(days, lat, tilt):
        data = []
        np.random.seed(42)
        
        for day in range(days):
            # Simple seasonal temperature variation
            temp_base = 20 + 10 * math.sin(2 * math.pi * day / 365)
            
            for hour in range(24):
                # Daily temperature variation
                temp = temp_base + 5 * math.sin(2 * math.pi * (hour - 6) / 24) + np.random.normal(0, 2)
                
                # Simple solar irradiance model
                if 6 <= hour <= 18:
                    # Peak irradiance at solar noon
                    hour_angle = abs(hour - 12)
                    base_irradiance = 1000 * math.cos(math.radians(hour_angle * 15)) * 0.8
                    
                    # Seasonal and latitude adjustment
                    seasonal_factor = 0.8 + 0.4 * math.sin(2 * math.pi * (day - 80) / 365)
                    latitude_factor = math.cos(math.radians(abs(lat - 23.5)))
                    
                    # Tilt bonus (simplified)
                    tilt_factor = 1 + (tilt / 90) * 0.2
                    
                    # Random weather variation
                    weather_factor = np.random.uniform(0.3, 1.0)
                    
                    irradiance = base_irradiance * seasonal_factor * latitude_factor * tilt_factor * weather_factor
                else:
                    irradiance = 0
                
                # Calculate power output
                if irradiance > 0:
                    # Temperature derating
                    temp_derating = 1 + temp_coeff * (temp - 25) / 100
                    
                    # Power calculation
                    dc_power = total_power * (irradiance / 1000) * temp_derating
                    ac_power = dc_power * system_efficiency
                else:
                    dc_power = ac_power = 0
                
                data.append({
                    'day': day + 1,
                    'hour': hour,
                    'temperature': round(temp, 1),
                    'irradiance': round(max(0, irradiance), 1),
                    'dc_power': round(max(0, dc_power), 1),
                    'ac_power': round(max(0, ac_power), 1)
                })
        
        return pd.DataFrame(data)
    
    # Generate data
    with st.spinner("Calculating system performance..."):
        df = generate_simple_data(analysis_days, latitude, panel_tilt)
    
    # Key metrics
    total_energy = df['ac_power'].sum() / 1000  # kWh
    daily_avg = total_energy / analysis_days
    peak_power = df['ac_power'].max()
    capacity_factor = (total_energy / (total_power/1000 * 24 * analysis_days)) * 100
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>System Size</h3>
            <h2>{total_power/1000:.1f} kW</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Total Energy</h3>
            <h2>{total_energy:.0f} kWh</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Daily Average</h3>
            <h2>{daily_avg:.1f} kWh</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Capacity Factor</h3>
            <h2>{capacity_factor:.1f}%</h2>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Tabs for analysis
    tab1, tab2, tab3 = st.tabs(["📊 Performance", "🌤️ Weather", "📋 Data"])
    
    with tab1:
        st.markdown('<div class="header">Performance Analysis</div>', unsafe_allow_html=True)
        
        # Monthly summary (if analysis period is long enough)
        if analysis_days >= 90:
            df['month'] = ((df['day'] - 1) // 30) + 1
            monthly = df.groupby('month').agg({
                'ac_power': 'sum',
                'irradiance': 'mean',
                'temperature': 'mean'
            }).reset_index()
            monthly['energy_kwh'] = monthly['ac_power'] / 1000
            
            st.subheader("Monthly Performance")
            st.bar_chart(monthly.set_index('month')['energy_kwh'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Monthly Energy Production (kWh)**")
                st.dataframe(monthly[['month', 'energy_kwh']])
            
            with col2:
                st.write("**Monthly Averages**")
                st.dataframe(monthly[['month', 'irradiance', 'temperature']].round(1))
        
        # Daily profile
        st.subheader("Average Daily Profile")
        hourly_avg = df.groupby('hour').agg({
            'ac_power': 'mean',
            'irradiance': 'mean'
        }).reset_index()
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Average Power by Hour**")
            st.line_chart(hourly_avg.set_index('hour')['ac_power'])
        
        with col2:
            st.write("**Average Irradiance by Hour**")
            st.line_chart(hourly_avg.set_index('hour')['irradiance'])
        
        # Peak performance info
        peak_day = df.loc[df['ac_power'].idxmax(), 'day']
        peak_hour = df.loc[df['ac_power'].idxmax(), 'hour']
        st.info(f"🏆 **Peak Performance:** {peak_power:.0f} W on day {peak_day} at hour {peak_hour}")
    
    with tab2:
        st.markdown('<div class="header">Weather Analysis</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Irradiance Distribution")
            irradiance_data = df[df['irradiance'] > 0]['irradiance']
            st.bar_chart(pd.cut(irradiance_data, bins=20).value_counts().sort_index())
            
            st.write(f"**Average Irradiance:** {df['irradiance'].mean():.0f} W/m²")
            st.write(f"**Peak Irradiance:** {df['irradiance'].max():.0f} W/m²")
        
        with col2:
            st.subheader("Temperature Distribution")
            temp_data = df['temperature']
            st.bar_chart(pd.cut(temp_data, bins=20).value_counts().sort_index())
            
            st.write(f"**Average Temperature:** {df['temperature'].mean():.1f}°C")
            st.write(f"**Temperature Range:** {df['temperature'].min():.1f}°C to {df['temperature'].max():.1f}°C")
        
        # Weather summary
        st.subheader("Weather Summary")
        weather_summary = df[['temperature', 'irradiance']].describe()
        st.dataframe(weather_summary.round(1))
    
    with tab3:
        st.markdown('<div class="header">System Data & Export</div>', unsafe_allow_html=True)
        
        # System summary
        st.subheader("System Configuration Summary")
        config_data = {
            'Parameter': [
                'Location (Latitude)',
                'System Size (kW)',
                'Panel Power (W)',
                'Number of Panels',
                'Panel Tilt (°)',
                'Temperature Coefficient (%/°C)',
                'System Losses (%)',
                'Analysis Period (days)'
            ],
            'Value': [
                f"{latitude}°",
                f"{total_power/1000:.1f}",
                f"{panel_power}",
                f"{num_panels}",
                f"{panel_tilt}",
                f"{temp_coeff}",
                f"{system_losses}",
                f"{analysis_days}"
            ]
        }
        
        config_df = pd.DataFrame(config_data)
        st.dataframe(config_df, use_container_width=True)
        
        # Performance summary
        st.subheader("Performance Summary")
        perf_data = {
            'Metric': [
                'Total Energy Production (kWh)',
                'Average Daily Production (kWh/day)',
                'Peak Power Output (kW)',
                'Capacity Factor (%)',
                'System Efficiency (%)'
            ],
            'Value': [
                f"{total_energy:.1f}",
                f"{daily_avg:.1f}",
                f"{peak_power/1000:.1f}",
                f"{capacity_factor:.1f}",
                f"{system_efficiency*100:.1f}"
            ]
        }
        
        perf_df = pd.DataFrame(perf_data)
        st.dataframe(perf_df, use_container_width=True)
        
        # Download data
        st.subheader("📥 Download Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="Download Performance Data (CSV)",
                data=csv_data,
                file_name=f"solar_pv_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Combine config and performance summaries
            summary_data = pd.concat([config_df, perf_df], ignore_index=True)
            summary_csv = summary_data.to_csv(index=False)
            st.download_button(
                label="Download System Summary (CSV)",
                data=summary_csv,
                file_name=f"solar_system_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        # Show sample data
        st.subheader("Sample Performance Data (First 24 Hours)")
        st.dataframe(df.head(24), use_container_width=True)
        
        # Show data statistics
        st.subheader("Data Statistics")
        st.dataframe(df.describe().round(2))

if __name__ == "__main__":
    main()
