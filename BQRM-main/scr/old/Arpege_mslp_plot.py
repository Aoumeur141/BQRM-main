#!/usr/bin/env python3
########################################################################
#                                                                      #
#   Mean Sea Level Pressure Plotter Script                             #
#                                                                      #
#   This script reads GRIB1 files containing mean sea level pressure   #
#   data, plots contours on a map, annotates the lowest and highest    #
#   pressure values, and saves the plot as an image.                   #
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

def plot_mslp(filename):
    # Open the GRIB1 file
    grbs = pygrib.open(filename)
    # Select the desired parameter and level (geopotential height at 500 hPa)
    grb = grbs.select(name='Mean sea level pressure', level=0)[0]
    # Extract data and metadata
    data = grb.values / 100
    lats, lons = grb.latlons()
    # Close the GRIB1 file
    grbs.close()
    # Plotting
    plt.figure(figsize=(15,13))
    # Basemap projection
    m = Basemap(projection='merc', llcrnrlat=lats.min(), urcrnrlat=lats.max(),
                llcrnrlon=lons.min(), urcrnrlon=lons.max(), resolution='l')
    # Draw coastlines and countries
    m.drawcoastlines()
    m.drawcountries()
    # Convert lat/lon values to map coordinates
    x, y = m(lons, lats)
    # Define contour levels
    contour_levels = np.arange(data.min(), data.max(), 5)
    # Plot contours with black color
    contour = m.contour(x, y, data, levels=contour_levels, colors='blue')
    plt.clabel(contour, inline=True, fontsize=12, fmt='%1.0f')
    # Get the path to your home directory
    home_directory = os.path.expanduser(f'{PWD}/..')
    save_filename = os.path.join(home_directory, 'mslp_{AA}{MM}{DD}0600.png')
    plt.title('Situation genérale à 6 heures T.U au Niveau de la Mer', loc='left', fontsize=24)
    # Save the plot
    try:
        plt.savefig(f'{PWD}/../mslp_{AA}{MM}{DD}0600.png')
        print("Plot saved successfully.")
    except Exception as e:
        print(f"Error occurred while saving the plot: {e}")
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py filename.GB")
        sys.exit(1)
    filename = sys.argv[1]
    plot_mslp(filename)

