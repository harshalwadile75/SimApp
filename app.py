import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import math
from datetime import datetime, timedelta
import io

# Page configuration
st.set_page_config(
    page_title="Solar PV System Analyzer",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF6B35;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2E86AB;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f8ff;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #2E86AB;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def calculate_solar_position(latitude, day_of_year, hour):
    """Calculate solar position (elevation and azimuth)"""
    # Solar declination
    declination = 23.45 * np.sin(np.radians(360 * (284 + day_of_year) / 365))
    
    # Hour angle
    hour_angle = 15 * (hour - 12)
    
    # Solar elevation
    elevation = np.arcsin(
        np.sin(np.radians(declination)) * np.sin(np.radians(latitude)) +
        np.cos(np.radians(declination)) * np.cos(np.radians(latitude)) * np.cos(np.radians(hour_angle))
    )
    
    # Solar azimuth
    azimuth = np.arctan2(
        np.sin(np.radians(hour_angle)),
        np.cos(np.radians(hour_angle)) * np.sin(np.radians(latitude)) - 
        np.tan(np.radians(declination)) * np.cos(np.radians(latitude))
    )
    
    return np.degrees(elevation), np.degrees(azimuth)

def calculate_irradiance(dni, dhi, ghi, solar_elevation, panel_tilt, panel_azimuth, solar_azimuth):
    """Calculate irradiance on tilted surface"""
    if solar_elevation <= 0:
        return 0, 0, 0
    
    # Angle of incidence
    aoi = np.arccos(
        np.sin(np.radians(solar_elevation)) * np.cos(np.radians(panel_tilt)) +
        np.cos(np.radians(solar_elevation)) * np.sin(np.radians(panel_tilt)) * 
        np.cos(np.radians(solar_azimuth - panel_azimuth))
    )
    
    # Beam irradiance on tilted surface
    beam_tilted = dni * np.cos(aoi) if aoi < np.pi/2 else 0
    
    # Diffuse irradiance on tilted surface (isotropic sky model)
    diffuse_tilted = dhi * (1 + np.cos(np.radians(panel_tilt))) / 2
    
    # Ground reflected irradiance
    albedo = 0.2  # Ground reflectance
    ground_reflected = ghi * albedo * (1 - np.cos(np.radians(panel_tilt))) / 2
    
    # Total irradiance
    total_irradiance = beam_tilted + diffuse_tilted + ground_reflected
    
    return total_irradiance, beam_tilted, diffuse_tilted

def calculate_pv_power(irradiance, temperature, panel_power, temperature_coeff, noct):
    """Calculate PV power output"""
    # Cell temperature estimation
    cell_temp = temperature + (noct - 20) * irradiance / 800
    
    # Temperature derating
    temp_derating = 1 + temperature_coeff * (cell_temp - 25) / 100
    
    # Power output
    power = panel_power * (irradiance / 1000) * temp_derating
    
    return max(0, power), cell_temp

def generate_weather_data(latitude, days=365):
    """Generate synthetic weather data"""
    np.random.seed(42)  # For reproducible results
    
    data = []
    for day in range(1, days + 1):
        # Seasonal temperature variation
        temp_base = 20 + 15 * np.sin(2 * np.pi * (day - 80) / 365)
        
        for hour in range(24):
            # Daily temperature variation
            temp_variation = -5 * np.cos(2 * np.pi * hour / 24)
            temperature = temp_base + temp_variation + np.random.normal(0, 3)
            
            # Solar elevation for irradiance calculation
            solar_elev, solar_az = calculate_solar_position(latitude, day, hour)
            
            if solar_elev > 0:
                # Clear sky irradiance model
                ghi_clear = 1000 * np.sin(np.radians(solar_elev)) * 0.7
                
                # Add cloud effects
                cloud_factor = np.random.uniform(0.3, 1.0)
                ghi = ghi_clear * cloud_factor
                dni = ghi * 0.8 if ghi > 100 else 0
                dhi = ghi - dni * np.sin(np.radians(solar_elev))
            else:
                ghi = dni = dhi = 0
            
            data.append({
                'datetime': datetime(2024, 1, 1) + timedelta(days=day-1, hours=hour),
                'temperature': temperature,
                'ghi': max(0, ghi),
                'dni': max(0, dni),
                'dhi': max(0, dhi),
                'solar_elevation': solar_elev,
                'solar_azimuth': solar_az
            })
    
    return pd.DataFrame(data)

# Main application
def main():
    st.markdown('<h1 class="main-header">☀️ Solar PV System Analyzer</h1>', unsafe_allow_html=True)
    
    # Sidebar for system parameters
    st.sidebar.markdown("## System Configuration")
    
    # Location parameters
    st.sidebar.markdown("### Location")
    latitude = st.sidebar.slider("Latitude (°)", -90.0, 90.0, 40.7, 0.1)
    longitude = st.sidebar.slider("Longitude (°)", -180.0, 180.0, -74.0, 0.1)
    
    # PV System parameters
    st.sidebar.markdown("### PV System")
    panel_power = st.sidebar.number_input("Panel Power (W)", 100, 1000, 400)
    num_panels = st.sidebar.number_input("Number of Panels", 1, 1000, 20)
    panel_tilt = st.sidebar.slider("Panel Tilt (°)", 0, 90, 30)
    panel_azimuth = st.sidebar.slider("Panel Azimuth (°)", -180, 180, 180)
    
    # Panel specifications
    st.sidebar.markdown("### Panel Specifications")
    temperature_coeff = st.sidebar.slider("Temperature Coefficient (%/°C)", -1.0, 0.0, -0.4, 0.01)
    noct = st.sidebar.slider("NOCT (°C)", 40, 50, 45)
    
    # System losses
    st.sidebar.markdown("### System Losses")
    dc_losses = st.sidebar.slider("DC Losses (%)", 0, 20, 5)
    inverter_efficiency = st.sidebar.slider("Inverter Efficiency (%)", 80, 99, 96)
    ac_losses = st.sidebar.slider("AC Losses (%)", 0, 10, 3)
    
    # Analysis period
    st.sidebar.markdown("### Analysis")
    analysis_days = st.sidebar.selectbox("Analysis Period", [30, 90, 365], index=2)
    
    # Calculate system specifications
    total_power = panel_power * num_panels
    system_efficiency = (100 - dc_losses) * inverter_efficiency * (100 - ac_losses) / 10000
    
    # Generate weather data
    with st.spinner("Generating weather data..."):
        weather_df = generate_weather_data(latitude, analysis_days)
    
    # Calculate PV performance
    with st.spinner("Calculating PV performance..."):
        results = []
        
        for _, row in weather_df.iterrows():
            # Calculate irradiance on tilted surface
            total_irr, beam_irr, diff_irr = calculate_irradiance(
                row['dni'], row['dhi'], row['ghi'],
                row['solar_elevation'], panel_tilt, panel_azimuth, row['solar_azimuth']
            )
            
            # Calculate PV power
            dc_power, cell_temp = calculate_pv_power(
                total_irr, row['temperature'], total_power, temperature_coeff, noct
            )
            
            # Apply system losses
            ac_power = dc_power * system_efficiency
            
            results.append({
                'datetime': row['datetime'],
                'temperature': row['temperature'],
                'ghi': row['ghi'],
                'poa_irradiance': total_irr,
                'dc_power': dc_power,
                'ac_power': ac_power,
                'cell_temperature': cell_temp
            })
        
        results_df = pd.DataFrame(results)
    
    # Main content area
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("System Size", f"{total_power/1000:.1f} kW")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        annual_energy = results_df['ac_power'].sum() / 1000  # kWh
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Annual Energy", f"{annual_energy:.0f} kWh")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        specific_yield = annual_energy / (total_power/1000)  # kWh/kW
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Specific Yield", f"{specific_yield:.0f} kWh/kW")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        performance_ratio = specific_yield / (weather_df['ghi'].sum() / 1000) * 100
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Performance Ratio", f"{performance_ratio:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Performance Analysis", "📈 Time Series", "🌤️ Weather Data", "☀️ Solar Path", "📋 System Report"])
    
    with tab1:
        st.markdown('<h2 class="section-header">Performance Analysis</h2>', unsafe_allow_html=True)
        
        # Monthly analysis
        results_df['month'] = results_df['datetime'].dt.month
        monthly_stats = results_df.groupby('month').agg({
            'ac_power': 'sum',
            'ghi': 'sum',
            'poa_irradiance': 'sum',
            'temperature': 'mean'
        }).reset_index()
        
        monthly_stats['energy_kwh'] = monthly_stats['ac_power'] / 1000
        monthly_stats['month_name'] = pd.to_datetime(monthly_stats['month'], format='%m').dt.month_name()
        
        # Monthly energy chart
        fig_monthly = go.Figure()
        fig_monthly.add_trace(go.Bar(
            x=monthly_stats['month_name'],
            y=monthly_stats['energy_kwh'],
            name='AC Energy (kWh)',
            marker_color='#FF6B35'
        ))
        
        fig_monthly.update_layout(
            title="Monthly Energy Production",
            xaxis_title="Month",
            yaxis_title="Energy (kWh)",
            height=400
        )
        
        st.plotly_chart(fig_monthly, use_container_width=True)
        
        # Daily profile
        col1, col2 = st.columns(2)
        
        with col1:
            # Average daily profile
            results_df['hour'] = results_df['datetime'].dt.hour
            hourly_avg = results_df.groupby('hour')['ac_power'].mean().reset_index()
            
            fig_daily = go.Figure()
            fig_daily.add_trace(go.Scatter(
                x=hourly_avg['hour'],
                y=hourly_avg['ac_power'],
                mode='lines+markers',
                name='Average Power',
                line=dict(color='#2E86AB', width=3)
            ))
            
            fig_daily.update_layout(
                title="Average Daily Power Profile",
                xaxis_title="Hour of Day",
                yaxis_title="Power (W)",
                height=300
            )
            
            st.plotly_chart(fig_daily, use_container_width=True)
        
        with col2:
            # Irradiance vs Power scatter
            sample_data = results_df.sample(min(1000, len(results_df)))
            
            fig_scatter = go.Figure()
            fig_scatter.add_trace(go.Scatter(
                x=sample_data['poa_irradiance'],
                y=sample_data['ac_power'],
                mode='markers',
                name='Power vs Irradiance',
                marker=dict(color=sample_data['temperature'], colorscale='RdYlBu_r', size=4),
                text=sample_data['temperature'].round(1),
                hovertemplate='Irradiance: %{x:.0f} W/m²<br>Power: %{y:.0f} W<br>Temp: %{text}°C'
            ))
            
            fig_scatter.update_layout(
                title="Power vs Irradiance",
                xaxis_title="POA Irradiance (W/m²)",
                yaxis_title="AC Power (W)",
                height=300
            )
            
            st.plotly_chart(fig_scatter, use_container_width=True)
    
    with tab2:
        st.markdown('<h2 class="section-header">Time Series Analysis</h2>', unsafe_allow_html=True)
        
        # Time series plot
        fig_ts = make_subplots(
            rows=3, cols=1,
            subplot_titles=('Power Output', 'Solar Irradiance', 'Temperature'),
            vertical_spacing=0.08
        )
        
        # Sample data for visualization (every 24th point for daily resolution)
        sample_df = results_df.iloc[::24]
        
        fig_ts.add_trace(
            go.Scatter(x=sample_df['datetime'], y=sample_df['ac_power']/1000, 
                      name='AC Power', line=dict(color='#FF6B35')),
            row=1, col=1
        )
        
        fig_ts.add_trace(
            go.Scatter(x=sample_df['datetime'], y=sample_df['poa_irradiance'], 
                      name='POA Irradiance', line=dict(color='#F7931E')),
            row=2, col=1
        )
        
        fig_ts.add_trace(
            go.Scatter(x=sample_df['datetime'], y=sample_df['temperature'], 
                      name='Temperature', line=dict(color='#2E86AB')),
            row=3, col=1
        )
        
        fig_ts.update_yaxes(title_text="Power (kW)", row=1, col=1)
        fig_ts.update_yaxes(title_text="Irradiance (W/m²)", row=2, col=1)
        fig_ts.update_yaxes(title_text="Temperature (°C)", row=3, col=1)
        fig_ts.update_xaxes(title_text="Date", row=3, col=1)
        
        fig_ts.update_layout(height=600, showlegend=False)
        
        st.plotly_chart(fig_ts, use_container_width=True)
    
    with tab3:
        st.markdown('<h2 class="section-header">Weather Data Analysis</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # GHI distribution
            fig_ghi = go.Figure()
            fig_ghi.add_trace(go.Histogram(
                x=weather_df[weather_df['ghi'] > 0]['ghi'],
                nbinsx=50,
                name='GHI Distribution',
                marker_color='#F7931E'
            ))
            
            fig_ghi.update_layout(
                title="Global Horizontal Irradiance Distribution",
                xaxis_title="GHI (W/m²)",
                yaxis_title="Frequency",
                height=300
            )
            
            st.plotly_chart(fig_ghi, use_container_width=True)
        
        with col2:
            # Temperature distribution
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Histogram(
                x=weather_df['temperature'],
                nbinsx=50,
                name='Temperature Distribution',
                marker_color='#2E86AB'
            ))
            
            fig_temp.update_layout(
                title="Temperature Distribution",
                xaxis_title="Temperature (°C)",
                yaxis_title="Frequency",
                height=300
            )
            
            st.plotly_chart(fig_temp, use_container_width=True)
        
        # Weather summary statistics
        st.markdown("### Weather Summary Statistics")
        weather_stats = weather_df.describe()
        st.dataframe(weather_stats)
    
    with tab4:
        st.markdown('<h2 class="section-header">Solar Path Diagram</h2>', unsafe_allow_html=True)
        
        # Calculate solar path for different days of the year
        days_of_year = [21, 80, 172, 266]  # Solstices and equinoxes
        day_names = ["Winter Solstice", "Spring Equinox", "Summer Solstice", "Fall Equinox"]
        
        fig_solar = go.Figure()
        
        for i, day in enumerate(days_of_year):
            hours = np.arange(6, 19, 0.5)
            elevations = []
            azimuths = []
            
            for hour in hours:
                elev, azim = calculate_solar_position(latitude, day, hour)
                if elev > 0:
                    elevations.append(elev)
                    azimuths.append(azim)
            
            if elevations:
                fig_solar.add_trace(go.Scatter(
                    x=azimuths,
                    y=elevations,
                    mode='lines+markers',
                    name=day_names[i],
                    line=dict(width=3)
                ))
        
        fig_solar.update_layout(
            title=f"Solar Path Diagram (Latitude: {latitude}°)",
            xaxis_title="Solar Azimuth (°)",
            yaxis_title="Solar Elevation (°)",
            height=500
        )
        
        st.plotly_chart(fig_solar, use_container_width=True)
    
    with tab5:
        st.markdown('<h2 class="section-header">System Report</h2>', unsafe_allow_html=True)
        
        # System specifications
        st.markdown("### System Specifications")
        
        specs_data = {
            "Parameter": [
                "Location",
                "System Size",
                "Panel Power",
                "Number of Panels",
                "Panel Tilt",
                "Panel Azimuth",
                "Temperature Coefficient",
                "NOCT",
                "DC Losses",
                "Inverter Efficiency",
                "AC Losses",
                "Overall System Efficiency"
            ],
            "Value": [
                f"{latitude:.1f}°, {longitude:.1f}°",
                f"{total_power/1000:.1f} kW",
                f"{panel_power} W",
                f"{num_panels}",
                f"{panel_tilt}°",
                f"{panel_azimuth}°",
                f"{temperature_coeff}%/°C",
                f"{noct}°C",
                f"{dc_losses}%",
                f"{inverter_efficiency}%",
                f"{ac_losses}%",
                f"{system_efficiency*100:.1f}%"
            ]
        }
        
        specs_df = pd.DataFrame(specs_data)
        st.dataframe(specs_df, use_container_width=True)
        
        # Performance summary
        st.markdown("### Performance Summary")
        
        perf_data = {
            "Metric": [
                "Annual Energy Production",
                "Specific Yield",
                "Performance Ratio",
                "Average Daily Production",
                "Peak Power Output",
                "Capacity Factor"
            ],
            "Value": [
                f"{annual_energy:.0f} kWh",
                f"{specific_yield:.0f} kWh/kW",
                f"{performance_ratio:.1f}%",
                f"{annual_energy/365:.1f} kWh/day",
                f"{results_df['ac_power'].max()/1000:.1f} kW",
                f"{(annual_energy/(total_power/1000*8760))*100:.1f}%"
            ]
        }
        
        perf_df = pd.DataFrame(perf_data)
        st.dataframe(perf_df, use_container_width=True)
        
        # Download report
        if st.button("Generate CSV Report"):
            output = io.StringIO()
            
            # System info
            output.write("SOLAR PV SYSTEM ANALYSIS REPORT\n")
            output.write("="*50 + "\n\n")
            output.write("System Specifications:\n")
            specs_df.to_csv(output, index=False)
            output.write("\n\nPerformance Summary:\n")
            perf_df.to_csv(output, index=False)
            output.write("\n\nMonthly Energy Production:\n")
            monthly_stats[['month_name', 'energy_kwh']].to_csv(output, index=False)
            
            csv_data = output.getvalue()
            
            st.download_button(
                label="Download Report",
                data=csv_data,
                file_name=f"pv_system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
