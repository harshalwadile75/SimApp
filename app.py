import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from pv_calculations import PVSystemCalculator
from reliability_models import ReliabilityAnalyzer
from config import APP_CONFIG

# Page configuration
st.set_page_config(
    page_title="PV System Simulator",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Header
    st.markdown('<h1 class="main-header">☀️ PV System Simulator & Material Quality Analyzer</h1>', 
                unsafe_allow_html=True)
    
    # Sidebar for system parameters
    with st.sidebar:
        st.header("🔧 System Configuration")
        
        # Basic system parameters
        st.subheader("Panel Specifications")
        panel_power = st.number_input("Panel Power (W)", min_value=100, max_value=600, value=400)
        panel_efficiency = st.slider("Panel Efficiency (%)", min_value=15.0, max_value=25.0, value=20.0, step=0.1)
        num_panels = st.number_input("Number of Panels", min_value=1, max_value=1000, value=20)
        
        st.subheader("System Configuration")
        tilt_angle = st.slider("Tilt Angle (°)", min_value=0, max_value=90, value=30)
        azimuth = st.slider("Azimuth (°)", min_value=0, max_value=360, value=180)
        
        st.subheader("Location")
        latitude = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=40.7128)
        longitude = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-74.0060)
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 System Overview", "🔋 Energy Simulation", "🔬 Material Quality", "📈 Performance Analysis"])
    
    # Initialize calculators
    pv_calc = PVSystemCalculator()
    reliability_analyzer = ReliabilityAnalyzer()
    
    with tab1:
        st.header("System Overview")
        
        # System metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_power = panel_power * num_panels / 1000  # kW
        estimated_area = num_panels * 2.0  # Approximate area per panel
        
        with col1:
            st.metric("Total System Power", f"{total_power:.1f} kW")
        with col2:
            st.metric("Number of Panels", f"{num_panels}")
        with col3:
            st.metric("Estimated Area", f"{estimated_area:.1f} m²")
        with col4:
            st.metric("System Efficiency", f"{panel_efficiency:.1f}%")
        
        # System visualization
        st.subheader("System Layout Visualization")
        
        # Create a simple system layout plot
        fig = go.Figure()
        
        # Calculate panel positions (simple grid layout)
        panels_per_row = int(np.sqrt(num_panels))
        rows = int(np.ceil(num_panels / panels_per_row))
        
        x_positions = []
        y_positions = []
        for i in range(num_panels):
            row = i // panels_per_row
            col = i % panels_per_row
            x_positions.append(col * 2)
            y_positions.append(row * 1)
        
        fig.add_trace(go.Scatter(
            x=x_positions,
            y=y_positions,
            mode='markers',
            marker=dict(size=20, color='blue', symbol='square'),
            name='Solar Panels',
            text=[f'Panel {i+1}' for i in range(num_panels)],
            hovertemplate='<b>%{text}</b><br>Power: {}W<extra></extra>'.format(panel_power)
        ))
        
        fig.update_layout(
            title="System Layout",
            xaxis_title="Position (m)",
            yaxis_title="Position (m)",
            showlegend=True,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header("Energy Simulation")
        
        # Generate sample weather data
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        
        # Simulate weather data (in real app, you'd load actual weather data)
        np.random.seed(42)
        irradiance = 800 + 400 * np.sin(2 * np.pi * np.arange(len(dates)) / 365) + np.random.normal(0, 100, len(dates))
        irradiance = np.clip(irradiance, 0, 1200)
        
        temperature = 20 + 15 * np.sin(2 * np.pi * np.arange(len(dates)) / 365) + np.random.normal(0, 5, len(dates))
        
        weather_data = pd.DataFrame({
            'date': dates,
            'irradiance': irradiance,
            'temperature': temperature
        })
        
        # Calculate energy production
        system_params = {
            'panel_power': panel_power,
            'num_panels': num_panels,
            'efficiency': panel_efficiency / 100,
            'tilt': tilt_angle,
            'azimuth': azimuth
        }
        
        daily_energy = pv_calc.calculate_daily_energy(weather_data, system_params)
        weather_data['energy_kwh'] = daily_energy
        
        # Monthly aggregation
        weather_data['month'] = weather_data['date'].dt.month
        monthly_energy = weather_data.groupby('month')['energy_kwh'].sum()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Annual energy chart
            fig_monthly = px.bar(
                x=monthly_energy.index,
                y=monthly_energy.values,
                title="Monthly Energy Production",
                labels={'x': 'Month', 'y': 'Energy (kWh)'}
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
        
        with col2:
            # Daily energy over time
            fig_daily = px.line(
                weather_data,
                x='date',
                y='energy_kwh',
                title="Daily Energy Production",
                labels={'energy_kwh': 'Energy (kWh)', 'date': 'Date'}
            )
            st.plotly_chart(fig_daily, use_container_width=True)
        
        # Key metrics
        total_annual_energy = weather_data['energy_kwh'].sum()
        avg_daily_energy = weather_data['energy_kwh'].mean()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Annual Energy Production", f"{total_annual_energy:.1f} kWh")
        with col2:
            st.metric("Average Daily Energy", f"{avg_daily_energy:.1f} kWh")
        with col3:
            st.metric("Capacity Factor", f"{(total_annual_energy / (total_power * 8760)) * 100:.1f}%")
    
    with tab3:
        st.header("Material Quality & Reliability Analysis")
        
        # Module selection
        st.subheader("PV Module Selection")
        module_type = st.selectbox(
            "Select Module Type",
            ["Monocrystalline Silicon", "Polycrystalline Silicon", "Thin Film (CdTe)", "PERC", "Bifacial"]
        )
        
        manufacturer = st.selectbox(
            "Manufacturer",
            ["Tier 1 - Premium", "Tier 1 - Standard", "Tier 2", "Tier 3"]
        )
        
        # Reliability analysis
        reliability_data = reliability_analyzer.analyze_module_reliability(module_type, manufacturer)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Degradation Analysis")
            
            # Create degradation curve
            years = np.arange(0, 26)
            degradation_rate = reliability_data['annual_degradation']
            power_output = 100 * (1 - degradation_rate/100) ** years
            
            fig_deg = go.Figure()
            fig_deg.add_trace(go.Scatter(
                x=years,
                y=power_output,
                mode='lines+markers',
                name='Power Output',
                line=dict(color='red', width=3)
            ))
            
            fig_deg.update_layout(
                title="Power Degradation Over Time",
                xaxis_title="Years",
                yaxis_title="Power Output (%)",
                height=400
            )
            
            st.plotly_chart(fig_deg, use_container_width=True)
        
        with col2:
            st.subheader("Reliability Metrics")
            
            # Display reliability metrics
            metrics = [
                ("Annual Degradation Rate", f"{reliability_data['annual_degradation']:.2f}%"),
                ("25-Year Performance", f"{reliability_data['performance_25y']:.1f}%"),
                ("Expected Lifetime", f"{reliability_data['lifetime']:.0f} years"),
                ("Failure Rate", f"{reliability_data['failure_rate']:.3f}%/year"),
                ("Quality Grade", reliability_data['quality_grade'])
            ]
            
            for metric, value in metrics:
                st.metric(metric, value)
        
        # Test results simulation
        st.subheader("Certified Test Results")
        
        test_results = {
            "IEC 61215 (Thermal Cycling)": "PASS",
            "IEC 61215 (Humidity Freeze)": "PASS",
            "IEC 61215 (Damp Heat)": "PASS",
            "IEC 61730 (Safety)": "PASS",
            "Salt Mist Test": "PASS" if reliability_data['quality_grade'] in ['A', 'B'] else "MARGINAL",
            "UV Test": "PASS",
            "Mechanical Load Test": "PASS"
        }
        
        for test, result in test_results.items():
            color = "🟢" if result == "PASS" else "🟡" if result == "MARGINAL" else "🔴"
            st.write(f"{color} **{test}**: {result}")
    
    with tab4:
        st.header("Performance Analysis & Financial Metrics")
        
        # Economic parameters
        st.subheader("Economic Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            electricity_price = st.number_input("Electricity Price ($/kWh)", min_value=0.05, max_value=0.50, value=0.12, step=0.01)
            system_cost = st.number_input("System Cost ($/W)", min_value=1.0, max_value=5.0, value=2.5, step=0.1)
        
        with col2:
            maintenance_cost = st.number_input("Annual Maintenance ($/kW)", min_value=10, max_value=100, value=25)
            discount_rate = st.slider("Discount Rate (%)", min_value=3.0, max_value=10.0, value=6.0, step=0.1)
        
        # Financial calculations
        total_system_cost = system_cost * total_power * 1000  # Total cost in $
        annual_revenue = total_annual_energy * electricity_price
        annual_maintenance = maintenance_cost * total_power
        net_annual_revenue = annual_revenue - annual_maintenance
        
        # Simple payback period
        payback_period = total_system_cost / net_annual_revenue
        
        # NPV calculation (simplified)
        years_analysis = 25
        cash_flows = []
        for year in range(1, years_analysis + 1):
            # Account for degradation
            yearly_energy = total_annual_energy * (1 - reliability_data['annual_degradation']/100) ** year
            yearly_revenue = yearly_energy * electricity_price - annual_maintenance
            discounted_revenue = yearly_revenue / (1 + discount_rate/100) ** year
            cash_flows.append(discounted_revenue)
        
        npv = sum(cash_flows) - total_system_cost
        
        # Display financial metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("System Cost", f"${total_system_cost:,.0f}")
        with col2:
            st.metric("Annual Revenue", f"${annual_revenue:,.0f}")
        with col3:
            st.metric("Payback Period", f"{payback_period:.1f} years")
        with col4:
            st.metric("25-Year NPV", f"${npv:,.0f}")
        
        # Cash flow chart
        st.subheader("25-Year Cash Flow Analysis")
        
        cumulative_cash_flow = [-total_system_cost]
        yearly_cash_flows = [0]  # Year 0
        
        for year in range(1, years_analysis + 1):
            yearly_energy = total_annual_energy * (1 - reliability_data['annual_degradation']/100) ** year
            yearly_revenue = yearly_energy * electricity_price - annual_maintenance
            yearly_cash_flows.append(yearly_revenue)
            cumulative_cash_flow.append(cumulative_cash_flow[-1] + yearly_revenue)
        
        fig_cash = go.Figure()
        fig_cash.add_trace(go.Scatter(
            x=list(range(years_analysis + 1)),
            y=cumulative_cash_flow,
            mode='lines+markers',
            name='Cumulative Cash Flow',
            line=dict(color='green', width=3)
        ))
        
        fig_cash.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Break-even")
        
        fig_cash.update_layout(
            title="Cumulative Cash Flow Over 25 Years",
            xaxis_title="Years",
            yaxis_title="Cash Flow ($)",
            height=400
        )
        
        st.plotly_chart(fig_cash, use_container_width=True)

# Health check endpoint for deployment
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    # Add health check route (for deployment monitoring)
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        print(health_check())
    else:
        main()
