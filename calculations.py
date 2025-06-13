"""
PV System Calculations Module

This module contains core calculations for photovoltaic system performance,
including solar irradiance, temperature effects, and energy production.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import math


class PVSystemCalculator:
    """
    Core calculator for PV system performance and energy production.
    
    This class implements industry-standard calculations for solar energy
    systems, including temperature corrections, irradiance calculations,
    and system efficiency modeling.
    """
    
    def __init__(self):
        """Initialize the PV calculator with standard constants."""
        self.SOLAR_CONSTANT = 1361  # W/m² - Solar constant
        self.STANDARD_CONDITIONS = {
            'irradiance': 1000,  # W/m²
            'temperature': 25,   # °C
            'air_mass': 1.5
        }
        
        # Temperature coefficients (typical values)
        self.TEMP_COEFFICIENTS = {
            'monocrystalline': -0.004,  # %/°C
            'polycrystalline': -0.004,  # %/°C
            'thin_film': -0.002,        # %/°C
            'perc': -0.0037,           # %/°C
            'bifacial': -0.0035        # %/°C
        }
    
    def calculate_solar_position(self, latitude: float, longitude: float, 
                               datetime_obj: datetime) -> Dict[str, float]:
        """
        Calculate sun position (elevation and azimuth) for given location and time.
        
        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            datetime_obj: DateTime object
            
        Returns:
            Dictionary containing solar elevation and azimuth angles
        """
        # Convert to radians
        lat_rad = math.radians(latitude)
        
        # Calculate day of year
        day_of_year = datetime_obj.timetuple().tm_yday
        
        # Solar declination angle
        declination = math.radians(23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365)))
        
        # Hour angle
        hour_angle = math.radians(15 * (datetime_obj.hour + datetime_obj.minute/60 - 12))
        
        # Solar elevation angle
        elevation = math.asin(
            math.sin(declination) * math.sin(lat_rad) + 
            math.cos(declination) * math.cos(lat_rad) * math.cos(hour_angle)
        )
        
        # Solar azimuth angle
        azimuth = math.atan2(
            math.sin(hour_angle),
            math.cos(hour_angle) * math.sin(lat_rad) - 
            math.tan(declination) * math.cos(lat_rad)
        )
        
        return {
            'elevation': math.degrees(elevation),
            'azimuth': math.degrees(azimuth) + 180,  # Convert to 0-360°
            'declination': math.degrees(declination)
        }
    
    def calculate_irradiance_on_tilted_surface(self, ghi: float, dni: float, dhi: float,
                                             solar_elevation: float, solar_azimuth: float,
                                             surface_tilt: float, surface_azimuth: float) -> float:
        """
        Calculate irradiance on a tilted surface.
        
        Args:
            ghi: Global Horizontal Irradiance (W/m²)
            dni: Direct Normal Irradiance (W/m²)
            dhi: Diffuse Horizontal Irradiance (W/m²)
            solar_elevation: Solar elevation angle (degrees)
            solar_azimuth: Solar azimuth angle (degrees)
            surface_tilt: Surface tilt angle (degrees)
            surface_azimuth: Surface azimuth angle (degrees)
            
        Returns:
            Plane of Array (POA) irradiance (W/m²)
        """
        # Convert angles to radians
        solar_elev_rad = math.radians(solar_elevation)
        solar_azim_rad = math.radians(solar_azimuth)
        surf_tilt_rad = math.radians(surface_tilt)
        surf_azim_rad = math.radians(surface_azimuth)
        
        # Calculate angle of incidence
        cos_incidence = (
            math.sin(solar_elev_rad) * math.cos(surf_tilt_rad) +
            math.cos(solar_elev_rad) * math.sin(surf_tilt_rad) * 
            math.cos(solar_azim_rad - surf_azim_rad)
        )
        
        # Ensure cos_incidence is not negative
        cos_incidence = max(cos_incidence, 0)
        
        # Direct component on tilted surface
        direct_tilted = dni * cos_incidence
        
        # Diffuse component (isotropic sky model)
        diffuse_tilted = dhi * (1 + math.cos(surf_tilt_rad)) / 2
        
        # Ground reflected component (assuming 20% albedo)
        albedo = 0.2
        ground_reflected = ghi * albedo * (1 - math.cos(surf_tilt_rad)) / 2
        
        # Total POA irradiance
        poa_irradiance = direct_tilted + diffuse_tilted + ground_reflected
        
        return max(poa_irradiance, 0)
    
    def calculate_temperature_effect(self, ambient_temp: float, irradiance: float,
                                   module_type: str = 'monocrystalline') -> float:
        """
        Calculate module temperature and temperature coefficient effect.
        
        Args:
            ambient_temp: Ambient temperature (°C)
            irradiance: Irradiance on module (W/m²)
            module_type: Type of PV module
            
        Returns:
            Temperature correction factor (dimensionless)
        """
        # Calculate cell temperature using NOCT model
        noct = 45  # Nominal Operating Cell Temperature (°C)
        module_temp = ambient_temp + (noct - 20) * irradiance / 800
        
        # Temperature coefficient
        temp_coeff = self.TEMP_COEFFICIENTS.get(module_type, -0.004)
        
        # Temperature correction factor
        temp_correction = 1 + temp_coeff * (module_temp - 25)
        
        return temp_correction
    
    def calculate_dc_power(self, irradiance: float, temperature: float,
                          panel_power: float, efficiency: float,
                          module_type: str = 'monocrystalline') -> float:
        """
        Calculate DC power output from PV module.
        
        Args:
            irradiance: Irradiance on module (W/m²)
            temperature: Ambient temperature (°C)
            panel_power: Rated panel power (W)
            efficiency: Panel efficiency (fraction)
            module_type: Type of PV module
            
        Returns:
            DC power output (W)
        """
        # Irradiance correction
        irradiance_factor = irradiance / self.STANDARD_CONDITIONS['irradiance']
        
        # Temperature correction
        temp_correction = self.calculate_temperature_effect(temperature, irradiance, module_type)
        
        # DC power calculation
        dc_power = panel_power * irradiance_factor * temp_correction
        
        return max(dc_power, 0)
    
    def calculate_system_losses(self, dc_power: float, loss_factors: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate system losses and AC power output.
        
        Args:
            dc_power: DC power from modules (W)
            loss_factors: Dictionary of loss factors
            
        Returns:
            AC power output (W)
        """
        if loss_factors is None:
            loss_factors = {
                'inverter_efficiency': 0.96,
                'dc_wiring_loss': 0.02,
                'ac_wiring_loss': 0.01,
                'soiling_loss': 0.02,
                'shading_loss': 0.03,
                'mismatch_loss': 0.02,
                'availability_loss': 0.01
            }
        
        # Apply losses sequentially
        power = dc_power
        
        # DC losses
        power *= (1 - loss_factors['dc_wiring_loss'])
        power *= (1 - loss_factors['soiling_loss'])
        power *= (1 - loss_factors['shading_loss'])
        power *= (1 - loss_factors['mismatch_loss'])
        
        # Inverter conversion
        power *= loss_factors['inverter_efficiency']
        
        # AC losses
        power *= (1 - loss_factors['ac_wiring_loss'])
        power *= (1 - loss_factors['availability_loss'])
        
        return max(power, 0)
    
    def calculate_daily_energy(self, weather_data: pd.DataFrame, 
                             system_params: Dict) -> np.ndarray:
        """
        Calculate daily energy production for a PV system.
        
        Args:
            weather_data: DataFrame with weather data (irradiance, temperature)
            system_params: Dictionary with system parameters
            
        Returns:
            Array of daily energy production (kWh)
        """
        daily_energy = []
        
        for _, row in weather_data.iterrows():
            # Extract weather parameters
            irradiance = row['irradiance']  # W/m²
            temperature = row['temperature']  # °C
            
            # Calculate instantaneous power (assuming peak sun hours)
            peak_sun_hours = irradiance / 1000  # Convert W/m² to equivalent sun hours
            
            # DC power calculation
            dc_power = self.calculate_dc_power(
                irradiance=irradiance,
                temperature=temperature,
                panel_power=system_params['panel_power'],
                efficiency=system_params['efficiency']
            )
            
            # System power (multiple panels)
            system_dc_power
