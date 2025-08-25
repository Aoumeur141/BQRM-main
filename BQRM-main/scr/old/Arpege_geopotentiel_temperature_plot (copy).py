import sys
import matplotlib.pyplot as plt
import numpy as np
import pygrib
from mpl_toolkits.basemap import Basemap
import os
import logging # Import the logging module

# --- Logger Setup ---
LOG_DIR = os.path.join('logs')
LOG_FILE = os.path.join(LOG_DIR, 'Arpege_geopotentiel_temperature_plot.log')

# Create the log directory if it doesn't exist
try:
    os.makedirs(LOG_DIR, exist_ok=True)
except OSError as e:
    print(f"Error creating log directory {LOG_DIR}: {e}", file=sys.stderr)
    sys.exit(1) # Exit if we can't even set up logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, # Set the minimum logging level (INFO, DEBUG, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE), # Log to file
        logging.StreamHandler(sys.stdout) # Also log to console
    ]
)
logger = logging.getLogger(__name__) # Get a logger for this module
# --- End Logger Setup ---

logger.info("Script started.")

# Get environment variables for the current and previous day
AA = os.environ.get('AA')
MM = os.environ.get('MM')
DD = os.environ.get('DD')
AAprec = os.environ.get('AAprec')
MMprec = os.environ.get('MMprec')
DDprec = os.environ.get('DDprec')
PWD = os.environ.get('PWD')

# Validate essential environment variables
if not PWD:
    logger.critical("Environment variable 'PWD' is not set. Cannot determine save path. Exiting.")
    sys.exit(1)
if not all([AA, MM, DD]):
    logger.critical("One or more date environment variables (AA, MM, DD) are not set. Cannot form output filename. Exiting.")
    sys.exit(1)

logger.info(f"Environment variables loaded: PWD={PWD}, AA={AA}, MM={MM}, DD={DD}")
if not all([AAprec, MMprec, DDprec]):
    logger.warning("Previous day environment variables (AAprec, MMprec, DDprec) are not set. This might not be critical depending on script's full context.")


def plot_geopotential_and_temperature(filename):
    """
    Reads GRIB1 file, plots geopotential height and temperature contours,
    and saves the plot.
    """
    logger.info(f"Starting plot generation for input file: {filename}")

    # Open the GRIB1 file
    try:
        grbs = pygrib.open(filename)
        logger.info(f"Successfully opened GRIB file: {filename}")
    except Exception as e:
        logger.error(f"Failed to open GRIB file {filename}: {e}")
        sys.exit(1) # Exit if file cannot be opened

    # Select the desired parameters (geopotential height and temperature at 500 hPa)
    try:
        # Select Geopotential
        grb_geopotential_list = grbs.select(name='Geopotential', level=500)
        if not grb_geopotential_list:
            raise ValueError("Geopotential data at 500 hPa not found in GRIB file.")
        grb_geopotential = grb_geopotential_list[0]
        logger.info("Successfully selected Geopotential data at 500 hPa.")

        # Select Temperature
        grb_temperature_list = grbs.select(name='Temperature', level=500)
        if not grb_temperature_list:
            raise ValueError("Temperature data at 500 hPa not found in GRIB file.")
        grb_temperature = grb_temperature_list[0]
        logger.info("Successfully selected Temperature data at 500 hPa.")

    except Exception as e:
        logger.error(f"Failed to select GRIB messages from {filename}: {e}")
        grbs.close()
        sys.exit(1)

    # Extract data and metadata for geopotential
    geopotential_data = grb_geopotential.values / 10 # Convert to decameters
    lats, lons = grb_geopotential.latlons()
    logger.info("Extracted geopotential data and lat/lon coordinates.")

    # Extract data for temperature
    temperature_data = grb_temperature.values - 273.15 # Convert from Kelvin to Celsius
    logger.info("Extracted temperature data and converted to Celsius.")

    # Close the GRIB1 file
    grbs.close()
    logger.info("Closed GRIB file.")

    # Plotting
    logger.info("Initializing plot figure.")
    plt.figure(figsize=(15, 13))

    # Basemap projection
    logger.info("Setting up Basemap projection.")
    try:
        # Ensure min/max values are valid for basemap
        # Check if lats or lons are single points or empty, which would make range zero
        if lats.size == 0 or lons.size == 0 or lats.min() == lats.max() or lons.min() == lons.max():
             raise ValueError("Latitude or Longitude range is zero or empty, cannot initialize Basemap.")
        m = Basemap(projection='merc', llcrnrlat=lats.min(), urcrnrlat=lats.max(),
                    llcrnrlon=lons.min(), urcrnrlon=lons.max(), resolution='l')
        logger.info("Basemap initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing Basemap with provided coordinates: {e}")
        sys.exit(1)

    # Draw coastlines and countries
    m.drawcoastlines()
    m.drawcountries()
    logger.info("Coastlines and countries drawn on the map.")

    # Convert lat/lon values to map coordinates
    x, y = m(lons, lats)
    logger.info("Converted lat/lon to map coordinates.")

    # Plot geopotential contours with black color and thicker lines
    logger.info("Plotting geopotential contours.")
    # Ensure there's a valid range for geopotential contours
    if geopotential_data.max() > geopotential_data.min():
        contour_levels_geopotential = np.arange(geopotential_data.min(), geopotential_data.max(), 40)
        contour_geopotential = m.contour(x, y, geopotential_data, levels=contour_levels_geopotential, colors='black', linewidths=2.0)
        plt.clabel(contour_geopotential, inline=True, fontsize=12, fmt='%1.0f')
        logger.info("Geopotential contours plotted and labeled.")
    else:
        logger.warning("Geopotential data has no range (min == max), skipping contour plot.")


    # Define levels for temperature contours below and above -16°C
    logger.info("Defining temperature contour levels around -16°C.")

    levels_below_minus_16 = np.array([])
    levels_above_minus_16 = np.array([])

    # Case 1: Temperatures span across -16°C
    if temperature_data.min() < -16 and temperature_data.max() > -16:
        levels_below_minus_16 = np.linspace(temperature_data.min(), -16, 5)
        levels_above_minus_16 = np.linspace(-16, temperature_data.max(), 5)
        # Remove duplicate -16 from the start of levels_above_minus_16 if it exists
        if levels_above_minus_16.size > 0 and levels_above_minus_16[0] == -16:
            levels_above_minus_16 = levels_above_minus_16[1:]
    # Case 2: All temperatures are below or equal to -16°C
    elif temperature_data.max() <= -16:
        levels_below_minus_16 = np.linspace(temperature_data.min(), temperature_data.max(), 5)
    # Case 3: All temperatures are above or equal to -16°C
    elif temperature_data.min() >= -16:
        levels_above_minus_16 = np.linspace(temperature_data.min(), temperature_data.max(), 5)

    logger.info("Temperature contour levels defined.")

    # Plot temperature contours below -16°C in blue
    if levels_below_minus_16.size > 0: # Check if the array is not empty
        logger.info("Plotting temperature contours below -16°C (blue).")
        contour_below_minus_16 = m.contour(x, y, temperature_data, levels=levels_below_minus_16, colors='blue', linestyles='-', linewidths=2.0)
        plt.clabel(contour_below_minus_16, inline=True, fontsize=12, fmt='%1.0f')
    else:
        logger.info("No temperature contours below -16°C to plot.")

    # Plot temperature contours above or equal to -16°C in red
    if levels_above_minus_16.size > 0: # Check if the array is not empty
        logger.info("Plotting temperature contours above or equal to -16°C (red).")
        contour_above_minus_16 = m.contour(x, y, temperature_data, levels=levels_above_minus_16, colors='red', linestyles='-', linewidths=2.0)
        plt.clabel(contour_above_minus_16, inline=True, fontsize=12, fmt='%1.0f')
    else:
        logger.info("No temperature contours above or equal to -16°C to plot.")

    logger.info("Temperature contours plotted and labeled.")

    # Title and save
    plt.title('Geopotential Height and Temperature at 500 hPa', loc='left', fontsize=24)
    logger.info("Plot title set.")

    # Save the plot
    # Construct save path using environment variables
    save_path = f'{PWD}/../geopotential_and_temperature_{AA}{MM}{DD}0000.png'
    logger.info(f"Attempting to save plot to: {save_path}")
    try:
        plt.savefig(save_path)
        logger.info(f"Plot saved successfully at {save_path}")
    except Exception as e:
        logger.error(f"Error occurred while saving the plot to {save_path}: {e}")
        sys.exit(1)
    finally:
        plt.close() # Close the plot to free memory
        logger.info("Plot figure closed to release resources.")

    logger.info("Plot generation completed for file.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("Usage: python script_name.py <filename.GB>")
        sys.exit(1)

    filename = sys.argv[1]
    logger.info(f"Input filename received from command line: {filename}")

    try:
        plot_geopotential_and_temperature(filename)
        logger.info("Script finished successfully.")
    except Exception as e:
        logger.critical(f"An unhandled error occurred during script execution: {e}", exc_info=True)
        sys.exit(1)


