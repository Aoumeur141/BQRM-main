##Arpege_geopotentiel_temperature_plot
import sys
import matplotlib.pyplot as plt
import numpy as np
import pygrib
from mpl_toolkits.basemap import Basemap
import os
import logging
import argparse
from pathlib import Path

# Import the setup_logger function from your pytaps package
from pytaps.logging_utils import setup_logger
# Import the new utility function from pytaps.file_operations
from pytaps.file_operations import ensure_parent_directory_exists

# --- Logger Setup (using pytaps) ---
script_name = Path(sys.argv[0]).stem

parser = argparse.ArgumentParser(description="Generate geopotential and temperature plots from Arpege GRIB files.")
parser.add_argument('grib_file', type=str, help='Path to the input GRIB file.')
parser.add_argument('--shared-log-file', type=str, required=True, # Made required for clarity
                    help='Path to a shared log file for chained scripts. This script expects it to be provided.')

args = parser.parse_args()

logger, current_log_file_path = setup_logger(
    script_name=script_name,
    log_level=logging.INFO,
    shared_log_file_path=args.shared_log_file
)
logger.info("-------------------------------------------------------------------")
logger.info(f"Script {script_name}.py started.")
logger.info(f"Logging to shared file: {current_log_file_path}")
logger.info("-------------------------------------------------------------------")
# --- End Logger Setup ---


# Get environment variables for the current and previous day
AA = os.environ.get('AA')
MM = os.environ.get('MM')
DD = os.environ.get('DD')
AAprec = os.environ.get('AAprec')
MMprec = os.environ.get('MMprec')
DDprec = os.environ.get('DDprec')
PWD = os.environ.get('PWD') # This should be the local_directory from BQRM_ref.py

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


def plot_geopotential_and_temperature(filename: Path, logger_instance: logging.Logger):
    """
    Reads GRIB1 file, plots geopotential height and temperature contours,
    and saves the plot.

    Args:
        filename (Path): The path to the input GRIB1 file.
        logger_instance (logging.Logger): The logger instance to use for messages.

    Raises:
        FileNotFoundError: If the GRIB file does not exist or cannot be opened.
        ValueError: If required GRIB messages (Geopotential, Temperature) are not found.
        RuntimeError: For other critical errors during plotting or saving.
    """
    logger_instance.info(f"Starting plot generation for input file: {filename}")

    # Open the GRIB1 file
    try:
        grbs = pygrib.open(str(filename)) # pygrib.open expects a string path
        logger_instance.info(f"Successfully opened GRIB file: {filename}")
    except Exception as e:
        logger_instance.error(f"Failed to open GRIB file {filename}: {e}")
        raise FileNotFoundError(f"Failed to open GRIB file {filename}: {e}") from e

    # Select the desired parameters (geopotential height and temperature at 500 hPa)
    try:
        # Select Geopotential
        grb_geopotential_list = grbs.select(name='Geopotential', level=500)
        if not grb_geopotential_list:
            raise ValueError("Geopotential data at 500 hPa not found in GRIB file.")
        grb_geopotential = grb_geopotential_list[0]
        logger_instance.info("Successfully selected Geopotential data at 500 hPa.")

        # Select Temperature
        grb_temperature_list = grbs.select(name='Temperature', level=500)
        if not grb_temperature_list:
            raise ValueError("Temperature data at 500 hPa not found in GRIB file.")
        grb_temperature = grb_temperature_list[0]
        logger_instance.info("Successfully selected Temperature data at 500 hPa.")

    except Exception as e:
        logger_instance.error(f"Failed to select GRIB messages from {filename}: {e}")
        grbs.close()
        raise ValueError(f"Failed to select GRIB messages from {filename}: {e}") from e

    # Extract data and metadata for geopotential
    geopotential_data = grb_geopotential.values / 10 # Convert to decameters
    lats, lons = grb_geopotential.latlons()
    logger_instance.info("Extracted geopotential data and lat/lon coordinates.")

    # Extract data for temperature
    temperature_data = grb_temperature.values - 273.15 # Convert from Kelvin to Celsius
    logger_instance.info("Extracted temperature data and converted to Celsius.")

    # Close the GRIB1 file
    grbs.close()
    logger_instance.info("Closed GRIB file.")

    # Plotting
    logger_instance.info("Initializing plot figure.")
    plt.figure(figsize=(15, 13))

    # Basemap projection
    logger_instance.info("Setting up Basemap projection.")
    try:
        if lats.size == 0 or lons.size == 0 or lats.min() == lats.max() or lons.min() == lons.max():
             raise RuntimeError("Latitude or Longitude range is zero or empty, cannot initialize Basemap.")
        m = Basemap(projection='merc', llcrnrlat=lats.min(), urcrnrlat=lats.max(),
                    llcrnrlon=lons.min(), urcrnrlon=lons.max(), resolution='l')
        logger_instance.info("Basemap initialized successfully.")
    except Exception as e:
        logger_instance.error(f"Error initializing Basemap with provided coordinates: {e}")
        raise RuntimeError(f"Error initializing Basemap: {e}") from e

    # Draw coastlines and countries
    m.drawcoastlines()
    m.drawcountries()
    logger_instance.info("Coastlines and countries drawn on the map.")

    # Convert lat/lon values to map coordinates
    x, y = m(lons, lats)
    logger_instance.info("Converted lat/lon to map coordinates.")

    # Plot geopotential contours with black color and thicker lines
    logger_instance.info("Plotting geopotential contours.")
    if geopotential_data.max() > geopotential_data.min():
        contour_levels_geopotential = np.arange(geopotential_data.min(), geopotential_data.max(), 40)
        contour_geopotential = m.contour(x, y, geopotential_data, levels=contour_levels_geopotential, colors='black', linewidths=2.0)
        plt.clabel(contour_geopotential, inline=True, fontsize=12, fmt='%1.0f')
        logger_instance.info("Geopotential contours plotted and labeled.")
    else:
        logger_instance.warning("Geopotential data has no range (min == max), skipping contour plot.")

    # Define levels for temperature contours below and above -16°C
    logger_instance.info("Defining temperature contour levels around -16°C.")
    levels_below_minus_16 = np.array([])
    levels_above_minus_16 = np.array([])

    if temperature_data.min() < -16 and temperature_data.max() > -16:
        levels_below_minus_16 = np.linspace(temperature_data.min(), -16, 5)
        levels_above_minus_16 = np.linspace(-16, temperature_data.max(), 5)
        if levels_above_minus_16.size > 0 and levels_above_minus_16[0] == -16:
            levels_above_minus_16 = levels_above_minus_16[1:]
    elif temperature_data.max() <= -16:
        levels_below_minus_16 = np.linspace(temperature_data.min(), temperature_data.max(), 5)
    elif temperature_data.min() >= -16:
        levels_above_minus_16 = np.linspace(temperature_data.min(), temperature_data.max(), 5)

    logger_instance.info("Temperature contour levels defined.")

    # Plot temperature contours below -16°C in blue
    if levels_below_minus_16.size > 0:
        logger_instance.info("Plotting temperature contours below -16°C (blue).")
        contour_below_minus_16 = m.contour(x, y, temperature_data, levels=levels_below_minus_16, colors='blue', linestyles='-', linewidths=2.0)
        plt.clabel(contour_below_minus_16, inline=True, fontsize=12, fmt='%1.0f')
    else:
        logger_instance.info("No temperature contours below -16°C to plot.")

    # Plot temperature contours above or equal to -16°C in red
    if levels_above_minus_16.size > 0:
        logger_instance.info("Plotting temperature contours above or equal to -16°C (red).")
        contour_above_minus_16 = m.contour(x, y, temperature_data, levels=levels_above_minus_16, colors='red', linestyles='-', linewidths=2.0)
        plt.clabel(contour_above_minus_16, inline=True, fontsize=12, fmt='%1.0f')
    else:
        logger_instance.info("No temperature contours above or equal to -16°C to plot.")

    logger_instance.info("Temperature contours plotted and labeled.")

    # Title and save
    plt.title('Geopotential Height and Temperature at 500 hPa', loc='left', fontsize=24)
    logger_instance.info("Plot title set.")

    # Save the plot
    # Construct save path using environment variables
    # PWD is expected to be the local_directory (where BQRM_ref.py is)
    # So, PWD/../ means one level up from local_directory, which is bqrm_output_root
    save_path = Path(PWD) / ".." / f"geopotential_and_temperature_{AA}{MM}{DD}0000.png"
    logger_instance.info(f"Attempting to save plot to: {save_path}")
    try:
        # Use the pytaps utility to ensure the parent directory exists
        ensure_parent_directory_exists(save_path, logger_instance=logger_instance)
        plt.savefig(str(save_path)) # plt.savefig expects a string path
        logger_instance.info(f"Plot saved successfully at {save_path}")
    except Exception as e:
        logger_instance.error(f"Error occurred while saving the plot to {save_path}: {e}")
        raise RuntimeError(f"Error saving plot to {save_path}: {e}") from e
    finally:
        plt.close() # Close the plot to free memory
        logger_instance.info("Plot figure closed to release resources.")

    logger_instance.info("Plot generation completed for file.")


if __name__ == "__main__":
    filename = Path(args.grib_file) # Convert input filename to a Path object
    logger.info(f"Input filename received from command line: {filename}")

    try:
        plot_geopotential_and_temperature(filename, logger)
        logger.info("Script finished successfully.")
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        logger.critical(f"A critical error occurred during script execution: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An unexpected error occurred during script execution: {e}", exc_info=True)
        sys.exit(1)
