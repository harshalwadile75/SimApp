"""
Enhanced Solar PV System Simulation App
A comprehensive Streamlit application for solar photovoltaic system modeling and analysis.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import requests
import json
from typing import Dict, Tuple, Optional, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Solar modeling libraries
try:
    import pvlib
    from pvlib import location, irradiance, atmosphere, solarposition
    from pvlib.pvsystem import PVSystem
    from pvlib.modelchain import ModelChain
    PVLIB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"pvlib not available: {e}")
    PVLIB_AVAILABLE = False

try:
    import pvfactors
    from pvfactors.geometry import OrderedPVArray
    from pvfactors.irradiance import IsotropicOrdered
    from pvfactors.engine import PVEngine
    PVFACTORS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"pvfactors not available: {e}")
    PVFACTORS_AVAILABLE = False

try:
    import solarutils
    SOLARUTILS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"solarutils not available: {e}")
    SOLARUTILS_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Solar PV System Simulator",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    color: #ff6b35;
    text-align: center;
    margin-bottom: 2rem;
    background: linear-gradient(90deg, #ff6b35, #f7931e);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: bold;
}

.metric-container {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 10px;
    margin: 0.5rem 0;
}

.stAlert {
    border-radius: 10px;
}

.sidebar-content {
    background-color: #fafafa;
    padding: 1rem;
    border-radius: 10px;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

class SolarSimulator:
    """Enhanced Solar PV System Simulator with error handling and validation."""
    
    def __init__(self):
        self.location_data = None
        self.weather_data = None
        self.system_params = {}
        
    def validate_inputs(self, latitude: float, longitude: float) -> bool:
        """Validate geographic inputs."""
        if not (-90 <= latitude <= 90):
            st.error("Latitude must be between -90 and 90 degrees")
            return False
        if not (-180 <= longitude <= 180):
            st.error("Longitude must be between -180 and 180 degrees")
            return False
        return True
    
    def create_location(self, latitude: float, longitude: float, 
                       timezone: str = 'UTC', altitude: float = 0) -> Optional[object]:
        """Create pvlib Location object with error handling."""
        if not PVLIB_AVAILABLE:
            st.error("pvlib is not available. Please check the installation.")
            return None
            
        try:
            return location.Location(latitude, longitude, timezone, altitude)
        except Exception as e:
            st.error(f"Error creating location: {str(e)}")
            return None
    
    def get_solar_position(self, loc, times) -> Optional[pd.DataFrame]:
        """Calculate solar position with error handling."""
        try:
            return loc.get_solarposition(times)
        except Exception as e:
            st.error(f"Error calculating solar position: {str(e)}")
            return None
    
    def calculate_clear_sky_irradiance(self, loc, times) -> Optional[pd.DataFrame]:
        """Calculate clear sky irradiance with error handling."""
        try:
            return loc.get_clearsky(times)
        except Exception as e:
            st.error(f"Error calculating clear sky irradiance: {str(e)}")
            return None
    
    def simulate_pv_system(self, loc, system_params: Dict, times) -> Optional[pd.DataFrame]:
        """Simulate PV system performance."""
        if not PVLIB_AVAILABLE:
            return None
            
        try:
            # Create PV system
            system = PVSystem(
                surface_tilt=system_params.get('tilt', 30),
                surface_azimuth=system_params.get('azimuth', 180),
                module_parameters=system_params.get('module_params', {}),
                inverter_parameters=system_params.get('inverter_params', {}),
                modules_per_string=system_params.get('modules_per_string', 10),
                strings_per_inverter=system_params.get('strings_per_inverter', 2)
            )
            
            # Create model chain
            mc = ModelChain(system, loc, aoi_model='physical', 
                          spectral_model='sapm', temperature_model='sapm')
            
            # Get weather data (clear sky for demo)
            weather = loc.get_clearsky(times)
            
            # Run simulation
            mc.run_model(weather)
            
            return mc.results.ac
            
        except Exception as e:
            st.error(f"Error in PV system simulation: {str(e)}")
            return None

def create_sample_weather_data(times: pd.DatetimeIndex) -> pd.DataFrame:
    """Create sample weather data for demonstration."""
    np.random.seed(42)  # For reproducible results
    
    # Generate realistic solar irradiance patterns
    hour_of_day = times.hour
    day_of_year = times.dayofyear
    
    # Solar noon irradiance pattern
    solar_noon_ghi = 1000 * np.sin(np.pi * (hour_of_day - 6) / 12) ** 2
    solar_noon_ghi = np.maximum(solar_noon_ghi, 0)
    
    # Seasonal variation
    seasonal_factor = 0.8 + 0.4 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
    
    # Add some realistic noise
    noise = np.random.normal(0, 50, len(times))
    
    ghi = solar_noon_ghi * seasonal_factor + noise
    ghi = np.maximum(ghi, 0)  # No negative irradiance
    
    # DNI and DHI estimation
    dni = ghi * 0.8 + np.random.normal(0, 30, len(times))
    dni = np.maximum(dni, 0)
    
    dhi = ghi - dni * np.sin(np.radians(45))  # Simplified calculation
    dhi = np.maximum(dhi, 0)
    
    # Temperature variation
    temp_air = 20 + 15 * np.sin(2 * np.pi * (day_of_year - 80) / 365) + \
               10 * np.sin(2 * np.pi * hour_of_day / 24) + \
               np.random.normal(0, 2, len(times))
    
    wind_speed = 5 + np.random.exponential(3, len(times))
    
    return pd.DataFrame({
        'ghi': ghi,
        'dni': dni,
        'dhi': dhi,
        'temp_air': temp_air,
        'wind_speed': wind_speed
    }, index=times)

def main():
    """Main application function."""
    
    # Header
    st.markdown('<h1 class="main-header">☀️ Solar PV System Simulator</h1>', 
                unsafe_allow_html=True)
    
    # Check library availability
    if not PVLIB_AVAILABLE:
        st.error("⚠️ pvlib is not installed. Some features may not work properly.")
        st.info("To install pvlib, run: `pip install pvlib`")
    
    # Initialize simulator
    simulator = SolarSimulator()
    
    # Sidebar for inputs
    with st.sidebar:
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.header("🌍 Location Settings")
        
        # Location inputs
        latitude = st.number_input("Latitude (degrees)", 
                                 min_value=-90.0, max_value=90.0, 
                                 value=37.7749, step=0.1,
                                 help="Positive for North, negative for South")
        
        longitude = st.number_input("Longitude (degrees)", 
                                  min_value=-180.0, max_value=180.0, 
                                  value=-122.4194, step=0.1,
                                  help="Positive for East, negative for West")
        
        altitude = st.number_input("Altitude (meters)", 
                                 min_value=0, max_value=9000, 
                                 value=0, step=10)
        
        timezone = st.selectbox("Timezone", 
                              ['UTC', 'US/Pacific', 'US/Eastern', 'Europe/London', 
                               'Asia/Tokyo', 'Australia/Sydney'],
                              index=0)
        
        st.header("🔧 System Configuration")
        
        # System parameters
        system_capacity = st.number_input("System Capacity (kW)", 
                                        min_value=1.0, max_value=1000.0, 
                                        value=10.0, step=0.5)
        
        tilt = st.slider("Panel Tilt (degrees)", 
                        min_value=0, max_value=90, value=30)
        
        azimuth = st.slider("Panel Azimuth (degrees)", 
                          min_value=0, max_value=360, value=180,
                          help="0=North, 90=East, 180=South, 270=West")
        
        st.header("📅 Simulation Period")
        
        # Time range selection
        start_date = st.date_input("Start Date", 
                                 value=datetime.now().date())
        
        end_date = st.date_input("End Date", 
                               value=datetime.now().date() + timedelta(days=7))
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Validate inputs
    if not simulator.validate_inputs(latitude, longitude):
        return
    
    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📈 Analysis", "🌤️ Weather", "ℹ️ System Info"])
    
    with tab1:
        st.header("System Performance Dashboard")
        
        if PVLIB_AVAILABLE:
            # Create location
            loc = simulator.create_location(latitude, longitude, timezone, altitude)
            
            if loc is not None:
                # Generate time series
                times = pd.date_range(start=start_date, end=end_date, 
                                    freq='1H', tz=timezone)
                
                # Calculate solar position
                with st.spinner("Calculating solar position..."):
                    solar_pos = simulator.get_solar_position(loc, times)
                
                if solar_pos is not None:
                    # Display key metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        max_elevation = solar_pos['apparent_elevation'].max()
                        st.metric("Max Solar Elevation", f"{max_elevation:.1f}°")
                    
                    with col2:
                        daylight_hours = len(solar_pos[solar_pos['apparent_elevation'] > 0])
                        st.metric("Daylight Hours", f"{daylight_hours}")
                    
                    with col3:
                        st.metric("System Capacity", f"{system_capacity} kW")
                    
                    with col4:
                        st.metric("Panel Tilt", f"{tilt}°")
                    
                    # Solar path visualization
                    st.subheader("☀️ Solar Path Visualization")
                    
                    fig = px.scatter(solar_pos.reset_index(), 
                                   x='azimuth', y='apparent_elevation',
                                   color='apparent_elevation',
                                   size='apparent_elevation',
                                   hover_data=['index'],
                                   title="Solar Path Throughout Simulation Period",
                                   labels={'azimuth': 'Solar Azimuth (degrees)',
                                          'apparent_elevation': 'Solar Elevation (degrees)'})
                    
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Clear sky irradiance
                    st.subheader("🌞 Clear Sky Irradiance")
                    
                    with st.spinner("Calculating clear sky irradiance..."):
                        clearsky = simulator.calculate_clear_sky_irradiance(loc, times)
                    
                    if clearsky is not None:
                        fig_irr = make_subplots(rows=2, cols=1,
                                              subplot_titles=('Global Horizontal Irradiance', 
                                                            'Direct Normal Irradiance'))
                        
                        fig_irr.add_trace(
                            go.Scatter(x=clearsky.index, y=clearsky['ghi'],
                                     name='GHI', line=dict(color='orange')),
                            row=1, col=1
                        )
                        
                        fig_irr.add_trace(
                            go.Scatter(x=clearsky.index, y=clearsky['dni'],
                                     name='DNI', line=dict(color='red')),
                            row=2, col=1
                        )
                        
                        fig_irr.update_xaxes(title_text="Time")
                        fig_irr.update_yaxes(title_text="Irradiance (W/m²)")
                        fig_irr.update_layout(height=600)
                        
                        st.plotly_chart(fig_irr, use_container_width=True)
        else:
            st.warning("Advanced solar calculations require pvlib installation.")
            
            # Show sample data visualization
            st.subheader("📊 Sample Solar Data Visualization")
            
            # Generate sample time series
            times = pd.date_range(start=start_date, end=end_date, freq='1H')
            sample_data = create_sample_weather_data(times)
            
            fig = px.line(sample_data.reset_index(), x='index', y='ghi',
                         title='Sample Global Horizontal Irradiance',
                         labels={'index': 'Time', 'ghi': 'GHI (W/m²)'})
            
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header("Detailed Analysis")
        
        if PVLIB_AVAILABLE and 'loc' in locals():
            st.subheader("📈 Performance Metrics")
            
            # System parameters for simulation
            system_params = {
                'tilt': tilt,
                'azimuth': azimuth,
                'system_capacity': system_capacity
            }
            
            # Simulate PV system (simplified)
            times_analysis = pd.date_range(start=start_date, end=end_date, freq='1H', tz=timezone)
            
            with st.spinner("Running PV system simulation..."):
                # Create sample weather data for analysis
                weather_data = create_sample_weather_data(times_analysis)
                
                # Calculate basic PV output estimation
                # Simplified calculation: Power = Irradiance * System_Capacity * Efficiency
                efficiency = 0.15  # 15% system efficiency
                pv_output = weather_data['ghi'] * system_capacity * efficiency / 1000  # kW
                pv_output = np.maximum(pv_output, 0)
                
                # Daily energy production
                daily_energy = pv_output.resample('D').sum()
                
                # Create performance visualization
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_power = px.line(x=times_analysis, y=pv_output,
                                       title='Estimated PV Power Output',
                                       labels={'x': 'Time', 'y': 'Power (kW)'})
                    st.plotly_chart(fig_power, use_container_width=True)
                
                with col2:
                    if len(daily_energy) > 1:
                        fig_energy = px.bar(x=daily_energy.index, y=daily_energy.values,
                                          title='Daily Energy Production',
                                          labels={'x': 'Date', 'y': 'Energy (kWh)'})
                        st.plotly_chart(fig_energy, use_container_width=True)
                
                # Performance statistics
                st.subheader("📊 Performance Statistics")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total_energy = pv_output.sum()
                    st.metric("Total Energy Production", f"{total_energy:.1f} kWh")
                
                with col2:
                    avg_power = pv_output.mean()
                    st.metric("Average Power Output", f"{avg_power:.2f} kW")
                
                with col3:
                    peak_power = pv_output.max()
                    st.metric("Peak Power Output", f"{peak_power:.2f} kW")
        else:
            st.info("Detailed analysis requires location data from the Dashboard tab.")
    
    with tab3:
        st.header("Weather Data Analysis")
        
        # Weather data visualization
        times_weather = pd.date_range(start=start_date, end=end_date, freq='1H')
        weather_sample = create_sample_weather_data(times_weather)
        
        st.subheader("🌤️ Weather Parameters")
        
        # Weather metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_ghi = weather_sample['ghi'].mean()
            st.metric("Average GHI", f"{avg_ghi:.0f} W/m²")
        
        with col2:
            avg_temp = weather_sample['temp_air'].mean()
            st.metric("Average Temperature", f"{avg_temp:.1f}°C")
        
        with col3:
            avg_wind = weather_sample['wind_speed'].mean()
            st.metric("Average Wind Speed", f"{avg_wind:.1f} m/s")
        
        # Weather plots
        fig_weather = make_subplots(rows=2, cols=2,
                                  subplot_titles=('Solar Irradiance Components',
                                                'Temperature',
                                                'Wind Speed',
                                                'Irradiance vs Temperature'))
        
        # Irradiance components
        fig_weather.add_trace(
            go.Scatter(x=weather_sample.index, y=weather_sample['ghi'],
                     name='GHI', line=dict(color='orange')),
            row=1, col=1
        )
        
        fig_weather.add_trace(
            go.Scatter(x=weather_sample.index, y=weather_sample['dni'],
                     name='DNI', line=dict(color='red')),
            row=1, col=1
        )
        
        # Temperature
        fig_weather.add_trace(
            go.Scatter(x=weather_sample.index, y=weather_sample['temp_air'],
                     name='Temperature', line=dict(color='blue')),
            row=1, col=2
        )
        
        # Wind speed
        fig_weather.add_trace(
            go.Scatter(x=weather_sample.index, y=weather_sample['wind_speed'],
                     name='Wind Speed', line=dict(color='green')),
            row=2, col=1
        )
        
        # Scatter plot: Irradiance vs Temperature
        fig_weather.add_trace(
            go.Scatter(x=weather_sample['temp_air'], y=weather_sample['ghi'],
                     mode='markers', name='GHI vs Temp',
                     marker=dict(color='purple', size=4)),
            row=2, col=2
        )
        
        fig_weather.update_layout(height=800, showlegend=False)
        st.plotly_chart(fig_weather, use_container_width=True)
    
    with tab4:
        st.header("System Information")
        
        # Library status
        st.subheader("📚 Library Status")
        
        status_data = {
            'Library': ['pvlib', 'pvfactors', 'solarutils', 'streamlit', 'plotly', 'pandas'],
            'Status': [
                '✅ Available' if PVLIB_AVAILABLE else '❌ Not Available',
                '✅ Available' if PVFACTORS_AVAILABLE else '❌ Not Available',
                '✅ Available' if SOLARUTILS_AVAILABLE else '❌ Not Available',
                '✅ Available',
                '✅ Available',
                '✅ Available'
            ],
            'Purpose': [
                'Solar position and irradiance calculations',
                'Bifacial PV modeling with view factors',
                'Solar utility functions',
                'Web application framework',
                'Interactive plotting',
                'Data manipulation'
            ]
        }
        
        status_df = pd.DataFrame(status_data)
        st.dataframe(status_df, use_container_width=True)
        
        # System configuration summary
        st.subheader("⚙️ Current Configuration")
        
        config_data = {
            'Parameter': ['Latitude', 'Longitude', 'Altitude', 'Timezone', 
                         'System Capacity', 'Panel Tilt', 'Panel Azimuth'],
            'Value': [f"{latitude}°", f"{longitude}°", f"{altitude} m", timezone,
                     f"{system_capacity} kW", f"{tilt}°", f"{azimuth}°"]
        }
        
        config_df = pd.DataFrame(config_data)
        st.dataframe(config_df, use_container_width=True)
        
        # Recommendations
        st.subheader("💡 Recommendations")
        
        if latitude > 0:  # Northern hemisphere
            optimal_tilt = min(latitude + 15, 90)
            if abs(tilt - optimal_tilt) > 10:
                st.warning(f"Consider adjusting tilt to {optimal_tilt:.0f}° for better performance in your location.")
        
        if azimuth != 180 and latitude > 0:
            st.info("For northern hemisphere locations, south-facing panels (180°) typically provide optimal performance.")
        elif azimuth != 0 and latitude < 0:
            st.info("For southern hemisphere locations, north-facing panels (0°) typically provide optimal performance.")
        
        # Help section
        st.subheader("❓ Help & Documentation")
        
        with st.expander("How to use this application"):
            st.markdown("""
            1. **Location Settings**: Enter your geographic coordinates and timezone
            2. **System Configuration**: Set your PV system parameters
            3. **Simulation Period**: Choose the time range for analysis
            4. **Dashboard**: View real-time solar position and irradiance data
            5. **Analysis**: Examine detailed performance metrics
            6. **Weather**: Analyze weather patterns affecting your system
            """)
        
        with st.expander("Understanding the results"):
            st.markdown("""
            - **Solar Elevation**: Angle of the sun above the horizon
            - **Solar Azimuth**: Compass direction of the sun
            - **GHI**: Global Horizontal Irradiance (total solar radiation on horizontal surface)
            - **DNI**: Direct Normal Irradiance (direct solar radiation perpendicular to surface)
            - **DHI**: Diffuse Horizontal Irradiance (scattered solar radiation)
            """)

if __name__ == "__main__":
    main()
