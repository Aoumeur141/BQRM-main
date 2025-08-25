import sys
import matplotlib.pyplot as plt
import numpy as np
import pygrib
from mpl_toolkits.basemap import Basemap
import os

# Set the date and path manually
AA = '2025'  # Year
MM = '04'    # Month
DD = '08'    # Day

# Set the path for the GRIB file and the output save path
grib_file_path = f'/home/ibousri/AROME_DUST/Projet_Nationale/Sonelgaz/sonelgaz_oper/Arpg/2t_{AA}{MM}{DD}.grib'  # Modify this path
save_path = f'/home/ibousri/AROME_DUST/Projet_Nationale/Sonelgaz/sonelgaz_oper/Arpg/temperature_{AA}{MM}{DD}0000.png'  # Modify this path

def plot_temperature(filename, save_path):
    # Open the GRIB1 file
    grbs = pygrib.open(filename)
    # Select the desired parameter (temperature at 500 hPa)
    grb_temperature = grbs.select(name='2t')
    
    # Extract data and metadata for temperature
    temperature_data = grb_temperature.values - 273.15  # Convert Kelvin to Celsius
    lats, lons = grb_temperature.latlons()

    # Close the GRIB1 file
    grbs.close()
    
    # Plotting
    plt.figure(figsize=(15, 13))
    # Basemap projection
    m = Basemap(projection='merc', llcrnrlat=lats.min(), urcrnrlat=lats.max(),
                llcrnrlon=lons.min(), urcrnrlon=lons.max(), resolution='l')
    
    # Draw coastlines and countries
    m.drawcoastlines()
    m.drawcountries()
    
    # Convert lat/lon values to map coordinates
    x, y = m(lons, lats)
    
    # Define levels for temperature contours
    levels = np.linspace(temperature_data.min(), temperature_data.max(), 10)
    
    # Plot temperature contours
    contour = m.contour(x, y, temperature_data, levels=levels, cmap='coolwarm', linewidths=2.0)
    plt.clabel(contour, inline=True, fontsize=12, fmt='%1.0f')
    
    # Title and save
    plt.title(f'Temperature at 500 hPa: {AA}-{MM}-{DD}', loc='left', fontsize=24)
    
    # Save the plot
    try:
        plt.savefig(save_path)
        print("Plot saved successfully at", save_path)
    except Exception as e:
        print(f"Error occurred while saving the plot: {e}")

if __name__ == "__main__":
    plot_temperature(grib_file_path, save_path)