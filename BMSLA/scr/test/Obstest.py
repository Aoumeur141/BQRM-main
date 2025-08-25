import pandas as pd
import pdbufr
import os
from datetime import datetime, timedelta
from pathlib import Path
#from modules.module import run_next_program

source_dir = "/home/ibousri/AROME_DUST/Projet_Nationale/Sonelgaz/sonelgaz_oper/" 

# Function to prepare dates
def prepare_date():
    # Modify the following lines to use a fixed date if needed:
    #today = datetime.now()  # Use the current date or manually set it below
    today = datetime(2025, 4, 10)  # Example of a fixed date for testing
    yesterday = today - timedelta(days=1)
    
    # Return the date parts as strings
    return today.strftime('%Y'), today.strftime('%m'), today.strftime('%d'), \
           yesterday.strftime('%Y'), yesterday.strftime('%m'), yesterday.strftime('%d')

# Manually define the dates (you can modify these manually as needed)
AA_today, MM_today, DD_today, AA_yesterday, MM_yesterday, DD_yesterday = prepare_date()

# Manually define the stations (replace with your own list of stations)
stations_list = [
    "NAAMA", "EL-BAYADH", "LAGHOUAT", "DJELFA", "MSILA", "BISKRA", 
    "BATNA", "KHENCHELLA", "TEBESSA", "OULED-DJELLAL", "EL-MGHAIR", 
    "EL-OUED", "TOUGGOURT", "OUARGLA", "GHARDAIA", "EL-GOLEA", "TIMIMOUN", 
    "BECHAR", "BENI-ABBES", "TINDOUF", "ADRAR", "IN-SALAH", "ILLIZI", 
    "DJANET", "TAMANRASSET", "B-B-MOKHTAR", "IN-GUEZZAM"
]

# ✅ Create a DataFrame containing all the stations
stations_df = pd.DataFrame({"stationOrSiteName": stations_list})

# Manually set the paths (you can modify these paths as needed)
f_today = f"/home/ibousri/AROME_DUST/Projet_Nationale/Sonelgaz/sonelgaz_oper/Arpg/synop_alg_{AA_today}{MM_today}{DD_today}0600.bufr"
f_ystd = f"/home/ibousri/AROME_DUST/Projet_Nationale/Sonelgaz/sonelgaz_oper/Arpg/synop_alg_{AA_yesterday}{MM_yesterday}{DD_yesterday}1800.bufr"

# Check if the files exist
if not os.path.exists(f_today) and not os.path.exists(f_ystd):
    print(f"❌ The file {f_ystd} or {f_today} could not be found. Aborting processing.")
else:
    print(f"✅ Processing files: {f_ystd} and {f_today}")

    # Read BUFR file for Tmin
    if os.path.exists(f_today):
        df = pdbufr.read_bufr(
            f_today,
            columns=["stationOrSiteName", "minimumTemperatureAtHeightAndOverPeriodSpecified"]
        )
        df["tmin"] = df["minimumTemperatureAtHeightAndOverPeriodSpecified"] - 273.15  # Convert from Kelvin to Celsius
        df.drop(columns=["minimumTemperatureAtHeightAndOverPeriodSpecified"], inplace=True)
        stations_df = pd.merge(stations_df, df, on="stationOrSiteName", how="left")

    # Read BUFR file for Tmax
    if os.path.exists(f_ystd):
        df_18 = pdbufr.read_bufr(
            f_ystd,
            columns=["stationOrSiteName", "maximumTemperatureAtHeightAndOverPeriodSpecified"]
        )
        df_18["tmax"] = df_18["maximumTemperatureAtHeightAndOverPeriodSpecified"] - 273.15  # Convert from Kelvin to Celsius
        df_18.drop(columns=["maximumTemperatureAtHeightAndOverPeriodSpecified"], inplace=True)
        stations_df = pd.merge(stations_df, df_18, on="stationOrSiteName", how="left")

    # Clean the DataFrame by selecting only relevant columns
    selected_columns = ["stationOrSiteName", "tmin", "tmax"]
    existing_columns = [col for col in selected_columns if col in stations_df.columns]

    # Filter columns and drop duplicates
    filtered_df = stations_df[existing_columns].drop_duplicates()

    # Filter only the stations from the manually defined list
    filtered_df = filtered_df[filtered_df["stationOrSiteName"].isin(stations_list)]

    # Keep only the first valid entry per station (if there are multiple entries)
    df_cleaned = filtered_df.loc[filtered_df.isna().sum(axis=1).groupby(filtered_df['stationOrSiteName']).idxmin()]

    # Display the cleaned data for verification
    print(df_cleaned.head())

    # Create output directory if it doesn't exist
    output_dir = "/home/ibousri/AROME_DUST/Projet_Nationale/Sonelgaz/sonelgaz_oper/Arpg"
    os.makedirs(output_dir, exist_ok=True)

    # Save the cleaned data to a CSV file
    output_file = f"{output_dir}/tmin_tmax_{AA_today}{MM_today}{DD_today}.csv"
    df_cleaned.to_csv(output_file, index=False)
    print(f"✅ Data saved to {output_file}")

# Run the next program (you can change the script name as needed)
#os.chdir(os.path.join(source_dir, "scr"))
#run_next_program("6-create_tables.py")