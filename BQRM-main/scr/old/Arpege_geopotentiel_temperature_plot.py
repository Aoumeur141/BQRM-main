#!/usr/bin/env python3
########################################################################
#                                                                      #
#   Geopotential Height and Temperature Plotter Script                 #
#                                                                      #
#   This script reads GRIB1 files containing geopotential height and   #
#   temperature data at 500 hPa level, plots contours on a map, and    #
#   saves the plot as an image.                                        #
#                                                                      #
#   AUTHOR:                                                            #
#   - Nour El Isslam KERROUMI                                          #
#                                                                      #
#   LAST MODIFICATION:                                                 #
#   - Date: 24th March 2024                                            #
#                                                                      #
########################################################################

import sys
import matplotlib.pyplot as plt
import numpy as np
import pygrib
from mpl_toolkits.basemap import Basemap
import os
# Get environment variables for the current and previous day
AA = os.environ.get('AA')
MM = os.environ.get('MM')
DD = os.environ.get('DD')
AAprec = os.environ.get('AAprec')
MMprec = os.environ.get('MMprec')
DDprec = os.environ.get('DDprec')
PWD = os.environ.get('PWD')

def plot_geopotential_and_temperature(filename):
    # Open the GRIB1 file
    grbs = pygrib.open(filename)
    # Select the desired parameters (geopotential height and temperature at 500 hPa)
    grb_geopotential = grbs.select(name='Geopotential', level=500)[0]
    grb_temperature = grbs.select(name='Temperature', level=500)[0]
    # Extract data and metadata for geopotential
    geopotential_data = grb_geopotential.values / 10
    lats, lons = grb_geopotential.latlons()
    # Extract data for temperature
    temperature_data = grb_temperature.values - 273.15
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
    # Plot geopotential contours with black color and thicker lines
    contour_levels_geopotential = np.arange(geopotential_data.min(), geopotential_data.max(), 40)
    contour_geopotential = m.contour(x, y, geopotential_data, levels=contour_levels_geopotential, colors='black', linewidths=2.0)
    plt.clabel(contour_geopotential, inline=True, fontsize=12, fmt='%1.0f')
    # Define levels for temperature contours below and above -16°C
    levels_below_minus_16 = np.linspace(temperature_data.min(), -16, 5)
    levels_above_minus_16 = np.linspace(-16, temperature_data.max(), 5)[1:]
    # Plot temperature contours below -16°C in red
    contour_below_minus_16 = m.contour(x, y, temperature_data, levels=levels_below_minus_16, colors='blue', linestyles='-', linewidths=2.0)
    # Plot temperature contours above or equal to -16°C in blue
    contour_above_minus_16 = m.contour(x, y, temperature_data, levels=levels_above_minus_16, colors='red', linestyles='-', linewidths=2.0)
    # Add contour labels if needed
    plt.clabel(contour_below_minus_16, inline=True, fontsize=12, fmt='%1.0f')
    plt.clabel(contour_above_minus_16, inline=True, fontsize=12, fmt='%1.0f')
    # Title and save
    plt.title('Geopotential Height and Temperature at 500 hPa', loc='left', fontsize=24)
    # Save the plot
    save_path = f'{PWD}/../geopotential_and_temperature_{AA}{MM}{DD}0000.png'
    try:
        plt.savefig(save_path)
        print("Plot saved successfully at", save_path)
    except Exception as e:
        print(f"Error occurred while saving the plot: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py filename.GB")
        sys.exit(1)

    filename = sys.argv[1]
    plot_geopotential_and_temperature(filename)

