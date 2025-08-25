# ~/bqrm/BMSLA/scr/2-conv.py
import os
import logging
from datetime import datetime
import sys
import argparse # Keep this import for command-line arguments
import subprocess

# Import functions from your pytap package
# from pytaps.file_operations import merge_binary_files, delete_files # Keep these if you use them elsewhere
from pytaps.system_utils import execute_command
from pytaps.grib_processor import process_grib_parameter_extraction
from pytaps.logging_utils import setup_logger # Crucial import for shared logging

# --- Dynamically Determine Paths for DATA/TEMP files ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR) # This is ~/bqrm/BMSLA/
TMP_DIR = os.path.join(PARENT_DIR, "tmp") # This should be consistent with 1-get_arpege.py

# --- Setup Logging ---
script_name = os.path.basename(__file__)

# Parse command-line arguments for a shared log file path
parser = argparse.ArgumentParser(description="2-conv.py script for GRIB file processing.")
# IMPORTANT: This script MUST receive the shared log file path from the previous script
parser.add_argument('--shared-log-file', type=str, required=True,
                    help='Path to a shared log file for chained scripts.')
args = parser.parse_args()

# Configure the logger using the shared log file path received from the previous script
logger, current_log_file_path = setup_logger(
    script_name=script_name,
    log_directory_base=SCRIPT_DIR, # This argument is effectively ignored if shared_log_file_path is provided
    log_level=logging.INFO,
    shared_log_file_path=args.shared_log_file
)

# --- End Logging Configuration ---

def main():
   logger.info(f"--- Script '{script_name}' started ---") # Clear start message for separation
   logger.info(f"Using shared log file: {current_log_file_path}")
   logger.info(f"Current working directory: {os.getcwd()}")
   logger.info(f"Script directory: {SCRIPT_DIR}")
   logger.info(f"Parent directory dynamically set to: {PARENT_DIR}")
   logger.info(f"Temporary directory for GRIB files: {TMP_DIR}")

   # The dir_parent and tmp_path calculations below are redundant and potentially inconsistent
   # with the global TMP_DIR if os.getcwd() is not where the script expects.
   # Always use the globally defined TMP_DIR for consistency.
   # dir_parent = os.path.dirname(os.getcwd()) # REMOVE THIS LINE
   # logger.info(f"Determined parent directory: {dir_parent}") # REMOVE THIS LINE
   # tmp_path = os.path.join(dir_parent, "tmp") # REMOVE THIS LINE
   
   date = datetime.now().strftime("%Y%m%d")
   logger.info(f"Processing for date: {date}")
   logger.info("Starting extraction of temperature from ARPEGE files.")

   # Define the GRIB_COPY executable path (adjust if different on your system)
   GRIB_COPY_EXECUTABLE = "grib_copy"

   # Use the globally defined TMP_DIR consistently
   arpege_primary_input_file = os.path.join(TMP_DIR, f"W_fr-meteofrance,MODEL,ARPEGE+01+SP1+00H12H_C_LFPW_{date}0000--.grib2")

   if os.path.exists(arpege_primary_input_file):
       logger.info(f"Found primary ARPEGE file: {arpege_primary_input_file}. Processing this branch.")
       
       input_files_info_arpege = []
       arpege_time_ranges = [
           "00H12H", "13H24H", "25H36H", "37H48H"
       ]
       for i, time_range in enumerate(arpege_time_ranges):
           input_filename = f"W_fr-meteofrance,MODEL,ARPEGE+01+SP1+{time_range}_C_LFPW_{date}0000--.grib2"
           temp_output_filename = f"t2m{str(i*12).zfill(2)}-{str((i+1)*12).zfill(2)}.grib"
           input_files_info_arpege.append(
               (os.path.join(TMP_DIR, input_filename), temp_output_filename) # Use TMP_DIR
           )

       final_output_grib = os.path.join(TMP_DIR, f"2t_{date}.grib") # Use TMP_DIR
       
       try:
           process_grib_parameter_extraction(
               grib_copy_path=GRIB_COPY_EXECUTABLE,
               input_grib_files_info=input_files_info_arpege,
               temp_output_dir=TMP_DIR, # Use TMP_DIR
               final_output_filepath=final_output_grib,
               grib_parameter_filter="shortName=2t",
               delete_temp_files=True,
               logger=logger # Pass the logger to the utility function for consistent logging
           )
           logger.info(f"ARPEGE GRIB processing completed successfully. Final file: {final_output_grib}")
       except Exception as e:
           logger.critical(f"Critical error during ARPEGE GRIB processing: {e}. Exiting.")
           sys.exit(1) # Use sys.exit(1) for consistent exit codes

   elif os.path.exists(os.path.join(TMP_DIR, f'grib_{date}00_0000')):
       logger.info(f"Primary ARPEGE file not found. Found alternative GRIB file: grib_{date}00_0000. Processing this branch.")
       
       input_files_info_alternative = []
       for i in range(49):
           input_filename = f"grib_{date}00_{str(i).zfill(4)}"
           temp_output_filename = f"t2m{str(i).zfill(2)}.grib"
           input_files_info_alternative.append(
               (os.path.join(TMP_DIR, input_filename), temp_output_filename) # Use TMP_DIR
           )

       final_output_grib = os.path.join(TMP_DIR, f"2t_{date}.grib") # Use TMP_DIR

       try:
           process_grib_parameter_extraction(
               grib_copy_path=GRIB_COPY_EXECUTABLE,
               input_grib_files_info=input_files_info_alternative,
               temp_output_dir=TMP_DIR, # Use TMP_DIR
               final_output_filepath=final_output_grib,
               grib_parameter_filter="shortName=2t",
               delete_temp_files=True,
               logger=logger # Pass the logger to the utility function for consistent logging
           )
           logger.info(f"Alternative GRIB processing completed successfully. Final file: {final_output_grib}")
       except Exception as e:
           logger.critical(f"Critical error during alternative GRIB processing: {e}. Exiting.")
           sys.exit(1) # Use sys.exit(1) for consistent exit codes

   else:
       logger.error("No ARPEGE or alternative GRIB model found for the specified date. Exiting.")
       sys.exit(1) # Use sys.exit(1) for consistent exit codes

   logger.info(f"Attempting to run next program: 3-create_forecast_table.py")
   try:
       # --- KEY CHANGE: Pass the shared log file path to the next script ---
       execute_command(
           [sys.executable, os.path.join(SCRIPT_DIR, "3-create_forecast_table.py"), "--shared-log-file", current_log_file_path],
           cwd=SCRIPT_DIR # Ensure the working directory is correct for the next script
       )
       logger.info("Successfully executed 3-create_forecast_table.py.")
   except (subprocess.CalledProcessError, FileNotFoundError) as e:
       logger.exception(f"An error occurred while running 3-create_forecast_table.py: {e}")
       sys.exit(1) # Use sys.exit(1) for consistent exit codes

   logger.info(f"--- Script '{script_name}' finished. ---") # Clear end message

if __name__ == "__main__":
   main()
