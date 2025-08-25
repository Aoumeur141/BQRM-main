#!/usr/bin/env python3

import sys
import os
import logging
# from datetime import datetime, timedelta # No longer needed, handled by date_utils
from pathlib import Path
import shutil

# Import functions from your pytaps package
from pytaps.logging_utils import setup_logger
from pytaps.system_utils import execute_command
from pytaps.file_operations import (
    move_files_by_pattern,
    delete_files,
    check_file_exists_and_log,
    clean_directory
)
# Import the date_utils functions
from pytaps.date_time_utils import get_ymd_for_today_and_yesterday
# Import the fetchdata functions
from pytaps.fetchdata import list_remote_files, fetch_remote_files

def main():
    # --- Logging Configuration for the Main Script ---
    script_name = Path(sys.argv[0]).stem
    log_directory_base = Path.cwd() # Log files will go into Path.cwd()/logs

    logger, shared_log_file_path = setup_logger(
        script_name=script_name,
        log_directory_base=str(log_directory_base),
        log_level=logging.INFO
    )

    logger.info("-------------------------------------------------------------------")
    logger.info(f"Script {script_name}.py started.")
    logger.info(f"Shared log file for this run: {shared_log_file_path}")
    logger.info("-------------------------------------------------------------------")

    # --- Environment Variables (Pythonic Date Handling) ---
    # Refactor: Use get_ymd_for_today_and_yesterday from pytaps.date_utils
    today_year, today_month, today_day, \
    yesterday_year, yesterday_month, yesterday_day = get_ymd_for_today_and_yesterday(logger_instance=logger)

    AA = today_year
    MM = today_month
    DD = today_day
    AAprec = yesterday_year
    MMprec = yesterday_month
    DDprec = yesterday_day

    local_directory = Path.cwd()
    
    logger.info("Environment variables set:")
    logger.info(f"  Current Date: {AA}-{MM}-{DD}")
    logger.info(f"  Previous Date: {AAprec}-{MMprec}-{DDprec}")
    logger.info(f"  Current Working Directory (local_directory): {local_directory}")

    bqrm_output_root = local_directory.parent
    bufr_input_root_absolute = local_directory.parent.parent / "bufr_data" / "observations"

    logger.info("Configuration variables loaded:")
    logger.info(f"  BUFR_INPUT_ROOT (absolute): {bufr_input_root_absolute}")
    logger.info(f"  local_directory: {local_directory}")
    logger.info(f"  bqrm_output_root: {bqrm_output_root}")

    # FTP Server Information
    ftp_server = "ftp1.meteo.dz"
    ftp_username = "messir"
    ftp_password = "123Messir123"
    remote_directory = "/share/ARPEGE+01+SP1" # This is the base directory on the FTP server

    logger.info(f"FTP Server details: Server={ftp_server}, Remote Directory={remote_directory}")

    # --- Prepare Environment Variables for Child Processes ---
    env_vars_for_scripts = os.environ.copy() # Start with current environment
    env_vars_for_scripts['AA'] = AA
    env_vars_for_scripts['MM'] = MM
    env_vars_for_scripts['DD'] = DD
    env_vars_for_scripts['AAprec'] = AAprec
    env_vars_for_scripts['MMprec'] = MMprec
    env_vars_for_scripts['DDprec'] = DDprec
    # The PWD variable in the child scripts expects the directory where the main script is located,
    # which is `local_directory` in BQRM_ref.py.
    env_vars_for_scripts['PWD'] = str(local_directory)

    logger.info("Environment variables prepared for child scripts.")

    # --- FTP Connection and Arpege File Download ---
    logger.info(f"Initiating FTP connection to {ftp_server} to download Arpege files...")
    
    arpege_geopotentiel_temp_dir = bqrm_output_root / "arpege_geopotentiel_temperature"
    arpege_mslp_dir = bqrm_output_root / "arpege_mslp"

    try:
        arpege_geopotentiel_temp_dir.mkdir(parents=True, exist_ok=True)
        arpege_mslp_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured target directories for Arpege files exist: {arpege_geopotentiel_temp_dir}, {arpege_mslp_dir}")
    except Exception as e:
        logger.critical(f"Failed to create Arpege temporary directories: {e}. Exiting.", exc_info=True)
        sys.exit(1)

    try:
        # Refactor: Replace the old fetch_files with list_remote_files and fetch_remote_files
        # The original filename_pattern_template was "YMID41_LFPW_{date}*"
        # This implies it downloads all files for 'today' (DD)
        
        # 1. List files on the remote server matching the pattern
        filename_pattern = f"YMID41_LFPW_{DD}*" # This pattern applies to the actual filenames
        
        logger.info(f"Listing remote files with pattern: '{filename_pattern}' in remote directory: '{remote_directory}'")
        remote_file_names = list_remote_files(
            host=ftp_server,
            username=ftp_username,
            password=ftp_password,
            remote_dir=remote_directory,
            filename_pattern=filename_pattern
        )

        if not remote_file_names:
            logger.warning(f"No files found matching pattern '{filename_pattern}' in remote directory '{remote_directory}'.")
        
        # 2. Prepare the files_to_process list for fetch_remote_files
        files_to_download = []
        for filename in remote_file_names:
            # Construct full remote path (FTP uses forward slashes)
            remote_full_path = f"{remote_directory}/{filename}" 
            # Construct full local path where the file will be downloaded initially
            local_full_path = local_directory / filename
            files_to_download.append({
                'remote_path': remote_full_path,
                'local_path': local_full_path
            })

        # 3. Call fetch_remote_files to download the identified files
        if files_to_download:
            logger.info(f"Initiating download of {len(files_to_download)} Arpege files using FTP.")
            fetch_remote_files(
                protocol='ftp',
                host=ftp_server,
                port=None, # Use default FTP port 21
                username=ftp_username,
                password=ftp_password,
                files_to_process=files_to_download,
                logger_instance=logger # Pass the main logger
            )
            logger.info("FTP download of Arpege files successful.")
        else:
            logger.info("No Arpege files were identified for download based on the pattern and remote listing.")


        # Move downloaded files to their specific destination directories
        moved_00_files = move_files_by_pattern(
            source_dir=str(local_directory),
            filename_pattern=f"YMID41_LFPW_{DD}00*",
            destination_dir=str(arpege_geopotentiel_temp_dir),
            logger_instance=logger # Pass the main logger
        )
        if not moved_00_files:
            logger.warning(f"No YMID41_LFPW_{DD}00* files found or moved to {arpege_geopotentiel_temp_dir}. This might affect Arpege_geopotentiel_temperature_plot.py.")

        moved_06_files = move_files_by_pattern(
            source_dir=str(local_directory),
            filename_pattern=f"YMID41_LFPW_{DD}06*",
            destination_dir=str(arpege_mslp_dir),
            logger_instance=logger # Pass the main logger
        )
        if not moved_06_files:
            logger.warning(f"No YMID41_LFPW_{DD}06* files found or moved to {arpege_mslp_dir}. This might affect Arpege_mslp_plot.py.")

    except Exception as e:
        logger.critical(f"Failed to download or move Arpege files from FTP server. Error: {e}", exc_info=True)
        sys.exit(1)

    # --- BUFR File Processing (Local Generation Block - Placeholder) ---
    logger.info("Placeholder: Processing SMAL files to generate local BUFR files (this section was commented out in original code).")

    # --- Main Processing Logic ---
    source_bufr_18_path = bufr_input_root_absolute / AAprec / MMprec / DDprec / f"Synop_{AAprec}{MMprec}{DDprec}1800.bufr"
    source_bufr_06_path = bufr_input_root_absolute / AA / MM / DD / f"Synop_{AA}{MM}{DD}0600.bufr"

    dest_bufr_18_path = bqrm_output_root / f"synop_alg_{AAprec}{MMprec}{DDprec}1800.bufr"
    dest_bufr_06_path = bqrm_output_root / f"synop_alg_{AA}{MM}{DD}0600.bufr"

    logger.info(f"Attempting to copy BUFR files from: {source_bufr_18_path} and {source_bufr_06_path}")

    bufr_copy_success = True
    try:
        if check_file_exists_and_log(source_bufr_18_path, logger): # Pass the main logger
            shutil.copy2(source_bufr_18_path, dest_bufr_18_path)
            logger.info(f"Successfully copied {source_bufr_18_path.name} to {dest_bufr_18_path}.")
        else:
            bufr_copy_success = False
            logger.error(f"Source BUFR file not found: {source_bufr_18_path}. Skipping copy of this file.")

        if check_file_exists_and_log(source_bufr_06_path, logger): # Pass the main logger
            shutil.copy2(source_bufr_06_path, dest_bufr_06_path)
            logger.info(f"Successfully copied {source_bufr_06_path.name} to {dest_bufr_06_path}.")
        else:
            bufr_copy_success = False
            logger.error(f"Source BUFR file not found: {source_bufr_06_path}. Skipping copy of this file.")

    except Exception as e:
        logger.critical(f"An unexpected error occurred during BUFR file copy: {e}", exc_info=True)
        bufr_copy_success = False

    if not bufr_copy_success:
        logger.critical("Failed to copy one or both required BUFR files. Cannot proceed with Python scripts. Exiting.")
        sys.exit(1)

    # Execute Python scripts once files are downloaded/copied
    logger.info("Executing Python processing scripts.")

    arpege_geopotentiel_script = local_directory / "Arpege_geopotentiel_temperature_plot.py"
    arpege_mslp_script = local_directory / "Arpege_mslp_plot.py"
    bufr_to_xls_script = local_directory / "BufrToXLS_ref.py"
    send_msg_script = local_directory / "send_MSG.py" # Commented out in shell, but defined for completeness

    # Python script: Arpege_geopotentiel_temperature_plot.py
    geopotential_grib_files = list(arpege_geopotentiel_temp_dir.glob(f"YMID41_LFPW_{DD}00*"))
    
    if not geopotential_grib_files:
        logger.warning(f"No Arpege geopotential GRIB files found in {arpege_geopotentiel_temp_dir} matching pattern YMID41_LFPW_{DD}00*. Skipping plot generation for geopotential.")
    else:
        for grib_file_path in geopotential_grib_files:
            logger.info(f"Running {arpege_geopotentiel_script.name} for file: {grib_file_path.name}...")
            try:
                execute_command(
                    ['python3', str(arpege_geopotentiel_script), str(grib_file_path),'--shared-log-file', str(shared_log_file_path)],
                    logger_instance=logger, # Pass the main logger for execute_command's own logging
                    cwd=str(local_directory),
                    env=env_vars_for_scripts # Pass the environment variables
                )
                logger.info(f"{arpege_geopotentiel_script.name} executed successfully for {grib_file_path.name}.")
            except Exception as e:
                logger.error(f"{arpege_geopotentiel_script.name} failed for {grib_file_path.name}: {e}. This might affect output.", exc_info=True)

    # Python script: Arpege_mslp_plot.py
    mslp_grib_files = list(arpege_mslp_dir.glob(f"YMID41_LFPW_{DD}06*"))

    if not mslp_grib_files:
        logger.warning(f"No Arpege MSLP GRIB files found in {arpege_mslp_dir} matching pattern YMID41_LFPW_{DD}06*. Skipping plot generation for MSLP.")
    else:
        for grib_file_path in mslp_grib_files:
            logger.info(f"Running {arpege_mslp_script.name} for file: {grib_file_path.name}...")
            try:
                execute_command(
                    ['python3', str(arpege_mslp_script), str(grib_file_path), '--shared-log-file', str(shared_log_file_path)],
                    logger_instance=logger, # Pass the main logger for execute_command's own logging
                    cwd=str(local_directory),
                    env=env_vars_for_scripts # Pass the environment variables
                )
                logger.info(f"{arpege_mslp_script.name} executed successfully for {grib_file_path.name}.")
            except Exception as e:
                logger.error(f"{arpege_mslp_script.name} failed for {grib_file_path.name}: {e}. This might affect output.", exc_info=True)

    # Python script: BufrToXLS_ref.py
    logger.info(f"Running {bufr_to_xls_script.name}...")
    try:
        execute_command(
            ['python3', str(bufr_to_xls_script), '--shared-log-file', str(shared_log_file_path)],
            logger_instance=logger, # Pass the main logger for execute_command's own logging
            cwd=str(local_directory),
            env=env_vars_for_scripts # Pass the environment variables
        )
        logger.info(f"{bufr_to_xls_script.name} executed successfully.")
    except Exception as e:
        logger.error(f"{bufr_to_xls_script.name} failed: {e}. This is a critical step.", exc_info=True)



    # Python script: send_MSG.py
    logger.info(f"Running {send_msg_script.name}...")
    try:
        execute_command(
            ['python3', str(send_msg_script), '--shared-log-file', str(shared_log_file_path)],
            logger_instance=logger, # Pass the main logger for execute_command's own logging
            cwd=str(local_directory),
            env=env_vars_for_scripts # Pass the environment variables
        )
        logger.info(f"{send_msg_script.name} executed successfully.")
    except Exception as e:
        logger.error(f"{send_msg_script.name} failed: {e}. This is a critical step.", exc_info=True)



    # --- Cleanup and Archiving ---
    logger.info("Starting cleanup and archiving operations.")

    # Remove temporary Arpege files and directories
    logger.info("Removing temporary Arpege directories: arpege_mslp and arpege_geopotentiel_temperature.")
    try:
        clean_directory(arpege_mslp_dir, logger_instance=logger, ignore_errors=True) # Pass the main logger
        arpege_mslp_dir.rmdir() 
        logger.info(f"Removed directory: {arpege_mslp_dir}")
    except OSError as e:
        logger.warning(f"Failed to remove directory {arpege_mslp_dir}. (Non-critical): {e}")
    except Exception as e:
        logger.warning(f"An unexpected error occurred during removal of {arpege_mslp_dir}. (Non-critical): {e}", exc_info=True)

    try:
        clean_directory(arpege_geopotentiel_temp_dir, logger_instance=logger, ignore_errors=True) # Pass the main logger
        arpege_geopotentiel_temp_dir.rmdir()
        logger.info(f"Removed directory: {arpege_geopotentiel_temp_dir}")
    except OSError as e:
        logger.warning(f"Failed to remove directory {arpege_geopotentiel_temp_dir}. (Non-critical): {e}")
    except Exception as e:
        logger.warning(f"An unexpected error occurred during removal of {arpege_geopotentiel_temp_dir}. (Non-critical): {e}", exc_info=True)

    logger.info("Removing temporary Synop text and BUFR files from local_directory.")
    clean_directory(local_directory, file_pattern=f"Synop_{AAprec}{MMprec}{DDprec}1800*", logger_instance=logger, ignore_errors=True) # Pass the main logger
    clean_directory(local_directory, file_pattern=f"Synop_{AA}{MM}{DD}0600*", logger_instance=logger, ignore_errors=True) # Pass the main logger
    clean_directory(local_directory, file_pattern=f"YMID*", logger_instance=logger, ignore_errors=True) # Pass the main logger
    
    logger.info("Removing other temporary output files (xlsx, png) from bqrm_output_root.")
    temp_output_files_to_delete_exact = [
        bqrm_output_root / "output.xlsx",
    ]
    delete_files(temp_output_files_to_delete_exact, ignore_errors=True, logger_instance=logger) # Pass the main logger

    clean_directory(bqrm_output_root, file_pattern="Bulletin_*.xlsx", logger_instance=logger, ignore_errors=True) # Pass the main logger
    clean_directory(bqrm_output_root, file_pattern="geopotential_and_temperature_*.png", logger_instance=logger, ignore_errors=True) # Pass the main logger
    clean_directory(bqrm_output_root, file_pattern="mslp_*.png", logger_instance=logger, ignore_errors=True) # Pass the main logger


    logger.info(f"Creating final output directories under {bqrm_output_root}.")
    bulletins_dir = bqrm_output_root / "bulletins" / AA / MM / DD
    data_prec_dir = bqrm_output_root / "data" / AAprec / MMprec / DDprec
    data_today_dir = bqrm_output_root / "data" / AA / MM / DD

    try:
        bulletins_dir.mkdir(parents=True, exist_ok=True)
        data_prec_dir.mkdir(parents=True, exist_ok=True)
        data_today_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Final output directories created successfully.")
    except Exception as e:
        logger.critical(f"Failed to create final output directories: {e}. Exiting.", exc_info=True)
        sys.exit(1)

    logger.info("Moving processed BUFR files and generated documents to archive locations.")
    
    try:
        if check_file_exists_and_log(dest_bufr_18_path, logger): # Pass the main logger
            shutil.move(dest_bufr_18_path, data_prec_dir / dest_bufr_18_path.name)
            logger.info(f"Moved {dest_bufr_18_path.name} to {data_prec_dir}.")
        else:
            logger.warning(f"Expected BUFR file {dest_bufr_18_path.name} not found for archiving.")

        if check_file_exists_and_log(dest_bufr_06_path, logger): # Pass the main logger
            shutil.move(dest_bufr_06_path, data_today_dir / dest_bufr_06_path.name)
            logger.info(f"Moved {dest_bufr_06_path.name} to {data_today_dir}.")
        else:
            logger.warning(f"Expected BUFR file {dest_bufr_06_path.name} not found for archiving.")
        
        docx_file = bqrm_output_root / f"BQRM_{AA}{MM}{DD}0600.docx"
        if check_file_exists_and_log(docx_file, logger): # Pass the main logger
            shutil.move(docx_file, bulletins_dir / docx_file.name)
            logger.info(f"Moved {docx_file.name} to {bulletins_dir}.")
        else:
            logger.warning(f"Expected DOCX file {docx_file.name} not found for archiving.")

    except Exception as e:
        logger.critical(f"Failed to move final output files to archive locations: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Performing backup operations (currently commented out in original script).")

    logger.info("-------------------------------------------------------------------")
    logger.info("Script BQRM_ref.py finished successfully.")
    logger.info("-------------------------------------------------------------------")

if __name__ == "__main__":
    main()
