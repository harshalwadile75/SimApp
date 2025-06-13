import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import math

# Set page config
st.set_page_config(
    page_title="Solar PV System Analyzer",
    page_icon="☀️",
    layout="wide"
)

# Custom styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF6B35;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-box {
        background-color: #f0f8ff;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #2E86AB;
        margin: 0.5rem 0;
    }
    .section-header {
        color: #2E86AB;
        font-weight: bold;
        font-size: 1.3rem;
        margin-top: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
@st.cache_data
def calculate_solar_angles(latitude, day_of_year, hour):
    """Calculate solar elevation and azimuth angles"""
    # Solar declination angle
    declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
    
    # Hour angle
    hour_angle = 15 * (hour - 12)
    
    # Convert to radians
    lat_rad = math.radians(latitude)
    dec_rad = math.radians(declination)
    hour_rad = math.radians(hour_angle)
    
    # Solar elevation angle
    elevation_rad = math.asin(
        math.sin(dec_rad) * math.sin(lat_rad) + 
        math.cos(dec_rad) * math.cos(lat_rad) * math.cos(hour_rad)
    )
    elevation = math.degrees(elevation_rad)
    
    # Solar azimuth angle
    if elevation > 0:
        azimuth_rad = math.atan2(
            math.sin(hour_rad),
            math.cos(hour_rad) * math.sin(lat_rad) - math.tan(dec_rad) * math.cos(lat_rad)
        )
        azimuth = math.degrees(azimuth_rad)
    else:
        azimuth = 0
    
    return max(0, elevation), azimuth

@st.cache_data
def calculate_panel_irradiance(ghi, solar_elevation, panel_tilt, solar_azimuth, panel_azimuth):
    """Calculate irradiance on tilted panel surface"""
    if solar_elevation <= 0 or ghi <= 0:
        return 0
    
    # Convert angles to radians
    panel_tilt_rad = math.radians(panel_tilt)
    solar_elev_rad = math.radians(solar_elevation)
    angle_diff_rad = math.radians(solar_azimuth - panel_azimuth)
    
    # Calculate angle of incidence
    cos_incidence = (
        math.sin(solar_elev_rad) * math.cos(panel_tilt_rad) +
        math.cos(solar_elev_rad) * math.sin(panel_tilt_rad) * math.cos(angle_diff_rad)
    )
    
    # Ensure we don't get negative values
    cos_incidence = max(0, cos_incidence)
    
    # Simple tilted surface irradiance model
    # Direct component
    direct_normal = ghi / math.sin(solar_elev_rad) if math.sin(solar_elev_rad) > 0 else 0
    direct_tilted = direct_normal * cos_incidence
    
    # Diffuse component (isotropic sky model)
    diffuse_horizontal = ghi * 0.1  # Simplified assumption
    diffuse_tilted = diffuse_horizontal * (1 + math.cos(panel_tilt_rad)) / 2
    
    # Ground reflected component
    albedo = 0.2
    reflected = ghi * albedo * (1 - math.cos(panel_tilt_rad)) / 2
    
    total_irradiance = direct_tilted + diffuse_tilted + reflected
    return max(0, total_irradiance)

@st.cache_data
def generate_weather_data(latitude, num_days=365):
    """Generate synthetic weather data"""
    np.random.seed(42)  # For reproducible results
    
    weather_data = []
    
    for day in range(1, num_days + 1):
        # Base temperature with seasonal variation
        temp_base = 20 + 15 * math.sin(2 * math.pi * (day - 80) / 365)
        
        for hour in range(24):
            # Daily temperature variation
            temp_daily = -8 * math.cos(2 * math.pi * hour / 24)
            temperature = temp_base + temp_daily + np.random.normal(0, 2)
            
            # Calculate solar position
            solar_elev, solar_azim = calculate_solar_angles(latitude, day, hour)
            
            # Generate irradiance based on solar elevation
            if solar_elev > 0:
                # Clear sky irradiance
                clear_sky_ghi = 1000 * math.sin(math.radians(solar_elev)) * 0.75
                
                # Add random cloud effects
                cloud_factor = np.random.uniform(0.2, 1.0)
                ghi = clear_sky_ghi * cloud_factor
            else:
                ghi = 0
            
            weather_data.append({
                'day': day,
                'hour': hour,
                'datetime': datetime(2024, 1, 1) + timedelta(days=day-1, hours=hour),
                'temperature': round(temperature, 1),
                'ghi': round(max(0, ghi), 1),
                'solar_elevation': round(solar_elev, 1),
                'solar_azimuth': round(solar_azim, 1)
            })
    
    return pd.DataFrame(weather_data)

def calculate_pv_performance(weather_df, system_params):
    """Calculate PV system performance"""
    results = []
    
    for _, row in weather_df.iterrows():
        # Calculate panel irradiance
        panel_irradiance = calculate_panel_irradiance(
            row['ghi'], 
            row['solar_elevation'],
            system_params['panel_tilt'],
            row['solar_azimuth'],
            system_params['panel_azimuth']
        )
        
        # Calculate cell temperature
        cell_temp = row['temperature'] + (system_params['noct'] - 20) * panel_irradiance / 800
        
        # Temperature derating
        temp_coeff = system_params['temp_coeff'] / 100  # Convert to decimal
        temp_derating = 1 + temp_coeff * (cell_temp - 25)
        
        # DC power calculation
        dc_power = (
            system_params['total_power'] * 
            (panel_irradiance / 1000) * 
            temp_derating
        )
        dc_power = max(0, dc_power)
        
        # AC power calculation (apply system losses)
        system_efficiency = (
            (100 - system_params['dc_losses']) / 100 *
            system_params['inverter_eff'] / 100 *
            (100 - system_params['ac_losses']) / 100
        )
        ac_power = dc_power * system_efficiency
        
        results.append({
            'datetime': row['datetime'],
            'day': row['day'],
            'hour': row['hour'],
            'temperature': row['temperature'],
            'ghi': row['ghi'],
            'panel_irradiance': round(panel_irradiance, 1),
            'cell_temperature': round(cell_temp, 1),
            'dc_power': round(dc_power, 1),
            'ac_power': round(ac_power, 1)
        })
    
    return pd.DataFrame(results)

# Main application
def main():
    st.markdown('<h1 class="main-header">☀️ Solar PV System Analyzer</h1>', unsafe_allow_html=True)
    
    # Sidebar configuration
    st.sidebar.header("⚙️ System Configuration")
    
    # Location settings
    st.sidebar.subheader("📍 Location")
    latitude = st.sidebar.slider("Latitude (°)", -60.0, 60.0, 40.7, 0.1)
    longitude = st.sidebar.slider("Longitude (°)", -180.0, 180.0, -74.0, 0.1)
    
    # System specifications
    st.sidebar.subheader("🔧 PV System")
    panel_power = st.sidebar.number_input("Panel Power (W)", 100, 1000, 400, 50)
    num_panels = st.sidebar.number_input("Number of Panels", 1, 500, 25, 1)
    panel_tilt = st.sidebar.slider("Panel Tilt (°)", 0, 90, 30, 1)
    panel_azimuth = st.sidebar.slider("Panel Azimuth (°)", 0, 360, 180, 5)
    
    # Advanced parameters
    st.sidebar.subheader("⚡ Performance Parameters")
    temp_coeff = st.sidebar.slider("Temperature Coefficient (%/°C)", -1.0, 0.0, -0.4, 0.05)
    noct = st.sidebar.slider("NOCT (°C)", 40, 50, 45, 1)
    
    # System losses
    st.sidebar.subheader("📉 System Losses")
    dc_losses = st.sidebar.slider("DC Losses (%)", 0, 15, 5, 1)
    inverter_eff = st.sidebar.slider("Inverter Efficiency (%)", 85, 99, 96, 1)
    ac_losses = st.sidebar.slider("AC Losses (%)", 0, 10, 3, 1)
    
    # Analysis period
    analysis_period = st.sidebar.selectbox("Analysis Period (days)", [30, 90, 180, 365], index=0)
    
    # Calculate total system power
    total_power = panel_power * num_panels
    
    # System parameters dictionary
    system_params = {
        'total_power': total_power,
        'panel_tilt': panel_tilt,
        'panel_azimuth': panel_azimuth,
        'temp_coeff': temp_coeff,
        'noct': noct,
        'dc_losses': dc_losses,
        'inverter_eff': inverter_eff,
        'ac_losses': ac_losses
    }
    
    # Generate data and calculate performance
    with st.spinner("🔄 Generating weather data and calculating performance..."):
        weather_df = generate_weather_data(latitude, analysis_period)
        performance_df = calculate_pv_performance(weather_df, system_params)
    
    # Key metrics
    st.markdown('<div class="section-header">📊 System Overview</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_energy = performance_df['ac_power'].sum() / 1000  # kWh
    avg_daily_energy = total_energy / analysis_period
    specific_yield = total_energy / (total_power / 1000) if total_power > 0 else 0
    max_power = performance_df['ac_power'].max()
    
    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <h3>System Size</h3>
            <h2>{total_power/1000:.1f} kW</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-box">
            <h3>Total Energy</h3>
            <h2>{total_energy:.0f} kWh</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-box">
            <h3>Daily Average</h3>
            <h2>{avg_daily_energy:.1f} kWh/day</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-box">
            <h3>Peak Power</h3>
            <h2>{max_power/1000:.1f} kW</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Create tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Performance", "🌤️ Weather", "📅 Daily Profile", "📋 Data Export"])
    
    with tab1:
        st.markdown('<div class="section-header">Performance Analysis</div>', unsafe_allow_html=True)
        
        # Monthly summary
        performance_df['month'] = performance_df['datetime'].dt.month
        monthly_summary = performance_df.groupby('month').agg({
            'ac_power': 'sum',
            'ghi': 'mean',
            'temperature': 'mean'
        }).reset_index()
        monthly_summary['energy_kwh'] = monthly_summary['ac_power'] / 1000
        monthly_summary['month_name'] = monthly_summary['month'].map({
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
        })
        
        if len(monthly_summary) > 1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Monthly Energy Production")
                fig, ax = plt.subplots(figsize=(10, 6))
                bars = ax.bar(monthly_summary['month_name'], monthly_summary['energy_kwh'], 
                             color='#FF6B35', alpha=0.8)
                ax.set_ylabel('Energy (kWh)')
                ax.set_title('Monthly Energy Production')
                plt.xticks(rotation=45)
                
                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.0f}', ha='center', va='bottom')
                
                st.pyplot(fig)
                plt.close()
            
            with col2:
                st.subheader("Performance Metrics")
                st.dataframe(monthly_summary[['month_name', 'energy_kwh', 'ghi', 'temperature']].rename(columns={
                    'month_name': 'Month',
                    'energy_kwh': 'Energy (kWh)',
                    'ghi': 'Avg GHI (W/m²)',
                    'temperature': 'Avg Temp (°C)'
                }))
        
        # Power vs Irradiance plot
        st.subheader("Power vs Irradiance Relationship")
        sample_data = performance_df[performance_df['panel_irradiance'] > 0].sample(min(500, len(performance_df)))
        
        fig, ax = plt.subplots(figsize=(10, 6))
        scatter = ax.scatter(sample_data['panel_irradiance'], sample_data['ac_power'], 
                           c=sample_data['temperature'], cmap='RdYlBu_r', alpha=0.6)
        ax.set_xlabel('Panel Irradiance (W/m²)')
        ax.set_ylabel('AC Power (W)')
        ax.set_title('AC Power vs Panel Irradiance (colored by temperature)')
        plt.colorbar(scatter, label='Temperature (°C)')
        st.pyplot(fig)
        plt.close()
    
    with tab2:
        st.markdown('<div class="section-header">Weather Analysis</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Global Horizontal Irradiance")
            fig, ax = plt.subplots(figsize=(10, 6))
            ghi_data = weather_df[weather_df['ghi'] > 0]['ghi']
            ax.hist(ghi_data, bins=30, color='#F7931E', alpha=0.7, edgecolor='black')
            ax.set_xlabel('GHI (W/m²)')
            ax.set_ylabel('Frequency')
            ax.set_title('GHI Distribution')
            st.pyplot(fig)
            plt.close()
            
            st.write(f"**Average GHI:** {weather_df['ghi'].mean():.1f} W/m²")
            st.write(f"**Maximum GHI:** {weather_df['ghi'].max():.1f} W/m²")
        
        with col2:
            st.subheader("Temperature Distribution")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(weather_df['temperature'], bins=30, color='#2E86AB', alpha=0.7, edgecolor='black')
            ax.set_xlabel('Temperature (°C)')
            ax.set_ylabel('Frequency')
            ax.set_title('Temperature Distribution')
            st.pyplot(fig)
            plt.close()
            
            st.write(f"**Average Temperature:** {weather_df['temperature'].mean():.1f}°C")
            st.write(f"**Temperature Range:** {weather_df['temperature'].min():.1f}°C to {weather_df['temperature'].max():.1f}°C")
    
    with tab3:
        st.markdown('<div class="section-header">Daily Profile Analysis</div>', unsafe_allow_html=True)
        
        # Average hourly profile
        hourly_avg = performance_df.groupby('hour').agg({
            'ac_power': 'mean',
            'ghi': 'mean',
            'panel_irradiance': 'mean'
        }).reset_index()
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Power profile
        ax1.plot(hourly_avg['hour'], hourly_avg['ac_power'], 'o-', color='#FF6B35', linewidth=2, label='AC Power')
        ax1.set_xlabel('Hour of Day')
        ax1.set_ylabel('Average AC Power (W)')
        ax1.set_title('Average Daily Power Profile')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(0, 23)
        
        # Irradiance profile
        ax2.plot(hourly_avg['hour'], hourly_avg['ghi'], 'o-', color='#F7931E', linewidth=2, label='GHI')
        ax2.plot(hourly_avg['hour'], hourly_avg['panel_irradiance'], 'o-', color='#2E86AB', linewidth=2, label='Panel Irradiance')
        ax2.set_xlabel('Hour of Day')
        ax2.set_ylabel('Average Irradiance (W/m²)')
        ax2.set_title('Average Daily Irradiance Profile')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(0, 23)
        
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()
        
        # Show peak production hour
        peak_hour = hourly_avg.loc[hourly_avg['ac_power'].idxmax(), 'hour']
        peak_power = hourly_avg['ac_power'].max()
        st.info(f"🏆 **Peak Production:** {peak_power:.0f} W at {peak_hour}:00")
    
    with tab4:
        st.markdown('<div class="section-header">Data Export & Summary</div>', unsafe_allow_html=True)
        
        # System summary
        st.subheader("System Summary")
        summary_data = {
            'Parameter': [
                'Location',
                'System Size (kW)',
                'Panel Power (W)',
                'Number of Panels',
                'Panel Tilt (°)',
                'Panel Azimuth (°)',
                'Temperature Coefficient (%/°C)',
                'NOCT (°C)',
                'DC Losses (%)',
                'Inverter Efficiency (%)',
                'AC Losses (%)',
                'Analysis Period (days)',
                'Total Energy Production (kWh)',
                'Average Daily Production (kWh/day)',
                'Specific Yield (kWh/kW)',
                'Peak AC Power (kW)'
            ],
            'Value': [
                f"{latitude:.1f}°N, {abs(longitude):.1f}°{'W' if longitude < 0 else 'E'}",
                f"{total_power/1000:.1f}",
                f"{panel_power}",
                f"{num_panels}",
                f"{panel_tilt}",
                f"{panel_azimuth}",
                f"{temp_coeff}",
                f"{noct}",
                f"{dc_losses}",
                f"{inverter_eff}",
                f"{ac_losses}",
                f"{analysis_period}",
                f"{total_energy:.1f}",
                f"{avg_daily_energy:.1f}",
                f"{specific_yield:.1f}",
                f"{max_power/1000:.1f}"
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
        
        # Download options
        st.subheader("📥 Download Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Convert performance data to CSV
            csv_data = performance_df.to_csv(index=False)
            st.download_button(
                label="📊 Download Performance Data (CSV)",
                data=csv_data,
                file_name=f"pv_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Convert summary to CSV
            summary_csv = summary_df.to_csv(index=False)
            st.download_button(
                label="📋 Download System Summary (CSV)",
                data=summary_csv,
                file_name=f"pv_system_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        # Show sample data
        st.subheader("Sample Performance Data")
        st.dataframe(performance_df.head(24), use_container_width=True)

if __name__ == "__main__":
    main()
