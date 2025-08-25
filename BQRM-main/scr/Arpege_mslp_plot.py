# Arpege_mslp_plot.py
import sys
import matplotlib.pyplot as plt
import numpy as np
import pygrib
from mpl_toolkits.basemap import Basemap
import os
import logging
from pathlib import Path
from typing import Union
import argparse

# Import the setup_logger function from your pytaps package
from pytaps.logging_utils import setup_logger
# Import the new utility function from pytaps.file_operations
from pytaps.file_operations import ensure_parent_directory_exists

# --- Logger Setup (using pytaps) ---
script_name = Path(sys.argv[0]).stem

parser = argparse.ArgumentParser(description="Generate Mean Sea Level Pressure (MSLP) plots from Arpege GRIB files.")
parser.add_argument('grib_file', type=str, help='Path to the input GRIB file.')
parser.add_argument('--shared-log-file', type=str, required=True,
                    help='Path to a shared log file for centralized logging.')
args = parser.parse_args()

# Configure the logger using the shared log file path received from the previous script
# TEMPORARY: Set to DEBUG for more verbose output during debugging
logger, log_file_path = setup_logger(
    script_name=script_name,
    log_level=logging.DEBUG, # <--- Changed to DEBUG for debugging purposes
    shared_log_file_path=args.shared_log_file
)

logger.info("-------------------------------------------------------------------")
logger.info(f"Script {script_name}.py started.")
logger.info(f"Logging to shared file: {log_file_path}")
logger.info("-------------------------------------------------------------------")
# --- End Logger Setup ---

mpl_logger = logging.getLogger('matplotlib')
# Set its level to WARNING to ignore DEBUG and INFO messages from all matplotlib sub-loggers
mpl_logger.setLevel(logging.WARNING)
# Optionally, prevent matplotlib logs from propagating to the root logger
# This is a good safeguard, though setting the level should usually be sufficient.
mpl_logger.propagate = False
logger.info("Suppressed Matplotlib DEBUG and INFO logs.")
# --- End suppression ---


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


def plot_mslp(filename: Union[str, Path], logger_instance: logging.Logger):
    """
    Reads GRIB1 file, plots Mean Sea Level Pressure (MSLP) contours,
    and saves the plot.

    Args:
        filename (Union[str, Path]): The path to the input GRIB1 file.
        logger_instance (logging.Logger): The logger instance to use for messages.

    Raises:
        FileNotFoundError: If the GRIB file does not exist or cannot be opened.
        ValueError: If required GRIB messages (MSLP) are not found.
        RuntimeError: For other critical errors during plotting or saving.
    """
    logger_instance.info(f"Starting MSLP plot generation for input file: {filename}")

    # Open the GRIB1 file
    try:
        grbs = pygrib.open(str(filename)) # pygrib.open expects a string path
        logger_instance.info(f"Successfully opened GRIB file: {filename}")
    except Exception as e:
        logger_instance.error(f"Failed to open GRIB file {filename}: {e}")
        raise FileNotFoundError(f"Failed to open GRIB file {filename}: {e}") from e

    # Select the desired parameter (Mean Sea Level Pressure)
    try:
        # Try common GRIB names for MSLP
        mslp_names_to_try = [
            'Mean sea level pressure',
            'Pressure reduced to MSL',
            'MSLP',
            'Pressure_reduced_to_MSL_grib1', # Sometimes grib1 specific names are used
            'MSL pressure' # Another common variant
        ]
        grb_mslp = None
        for name in mslp_names_to_try:
            # For surface parameters like MSLP, typically no 'level' is specified or level=0
            grb_mslp_list = grbs.select(name=name)
            if grb_mslp_list:
                grb_mslp = grb_mslp_list[0]
                logger_instance.info(f"Successfully selected MSLP data using name: '{name}'.")
                break
        
        if not grb_mslp:
            # If MSLP not found by common names, list all available messages for debugging
            logger_instance.error("Mean Sea Level Pressure data not found by common names. Listing all messages in GRIB file:")
            all_messages = []
            # Reset the GRIB file pointer to the beginning to iterate through all messages
            grbs.seek(0) 
            for i, grb in enumerate(grbs):
                all_messages.append(f"  Message {i+1}: name='{grb.name}', shortName='{grb.shortName}', level={grb.level}, typeOfLevel='{grb.typeOfLevel}'")
            logger_instance.error("\n".join(all_messages))
            raise ValueError("Mean Sea Level Pressure data not found in GRIB file. Check GRIB field name and level from the list above.")

    except Exception as e:
        logger_instance.error(f"Failed to select GRIB messages from {filename}: {e}", exc_info=True) # Log full traceback
        grbs.close()
        raise ValueError(f"Failed to select GRIB messages from {filename}: {e}") from e

    # Extract data and metadata for MSLP
    mslp_data = grb_mslp.values / 100 # Convert from Pa to hPa (millibars)
    lats, lons = grb_mslp.latlons()
    logger_instance.info("Extracted MSLP data and lat/lon coordinates.")

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
        logger_instance.error(f"Error initializing Basemap with provided coordinates: {e}", exc_info=True)
        raise RuntimeError(f"Error initializing Basemap: {e}") from e

    # Draw coastlines and countries
    m.drawcoastlines()
    m.drawcountries()
    logger_instance.info("Coastlines and countries drawn on the map.")

    # Convert lat/lon values to map coordinates
    x, y = m(lons, lats)
    logger_instance.info("Converted lat/lon to map coordinates.")

    # Plot MSLP contours
    logger_instance.info("Plotting MSLP contours.")
    if mslp_data.max() > mslp_data.min():
        # Adjust contour levels for MSLP, typically 4 hPa intervals
        contour_levels_mslp = np.arange(np.floor(mslp_data.min() / 4) * 4, np.ceil(mslp_data.max() / 4) * 4 + 4, 4)
        contour_mslp = m.contour(x, y, mslp_data, levels=contour_levels_mslp, colors='blue', linewidths=2.0)
        plt.clabel(contour_mslp, inline=True, fontsize=12, fmt='%1.0f')
        logger_instance.info("MSLP contours plotted and labeled.")
    else:
        logger_instance.warning("MSLP data has no range (min == max), skipping contour plot.")

    # Title and save
    plt.title('Mean Sea Level Pressure', loc='left', fontsize=24)
    logger_instance.info("Plot title set.")

    # Save the plot
    save_path = Path(PWD) / ".." / f"mslp_{AA}{MM}{DD}0600.png" # Assuming 0600 is the relevant time for MSLP
    logger_instance.info(f"Attempting to save plot to: {save_path}")
    try:
        ensure_parent_directory_exists(save_path, logger_instance=logger_instance)
        plt.savefig(str(save_path))
        logger_instance.info(f"Plot saved successfully at {save_path}")
    except Exception as e:
        logger_instance.error(f"Error occurred while saving the plot to {save_path}: {e}", exc_info=True)
        raise RuntimeError(f"Error saving plot to {save_path}: {e}") from e
    finally:
        plt.close()
        logger_instance.info("Plot figure closed to release resources.")

    logger_instance.info("Plot generation completed for file.")


if __name__ == "__main__":
    filename = Path(args.grib_file)
    logger.info(f"Input filename received from command line: {filename}")

    try:
        plot_mslp(filename, logger)
        logger.info("Script finished successfully.")
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        logger.critical(f"A critical error occurred during script execution: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An unexpected error occurred during script execution: {e}", exc_info=True)
        sys.exit(1)

