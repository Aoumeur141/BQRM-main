import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from pathlib import Path
from datetime import datetime, timedelta
#from modules.module import run_next_program
import os 

# Define your base source directory
source_dir =  "/home/ibousri/AROME_DUST/Projet_Nationale/Sonelgaz/sonelgaz_oper/" 


# Function to create a workbook with a specified sheet name
def create_workbook_with_sheet(sheet_name):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    return wb, ws

# Function to prepare the dates
def prepare_date():
    #today = datetime.now()
    today = datetime(2025, 4, 10)  # Example of a fixed date for testing
    yesterday = today - timedelta(days=1)

    AA_today = today.strftime('%Y')   # Year as 'AAAA'
    MM_today = today.strftime('%m')   # Month as 'MM'
    DD_today = today.strftime('%d')   # Day as 'DD'

    AA_yesterday = yesterday.strftime('%Y')   # Year as 'AAAA'
    MM_yesterday = yesterday.strftime('%m')   # Month as 'MM'
    DD_yesterday = yesterday.strftime('%d')   # Day as 'DD'

    return AA_today, MM_today, DD_today, AA_yesterday, MM_yesterday, DD_yesterday

# Date retrieval - you can modify these if you need specific dates
AA_today, MM_today, DD_today, AA_yesterday, MM_yesterday, DD_yesterday = prepare_date()

# Specify the paths (these can be modified)
outputs_dir = Path("/home/ibousri/AROME_DUST/Projet_Nationale/Sonelgaz/sonelgaz_oper")
arpege_file = outputs_dir / f"Arpg/station_arpege_{AA_today}{MM_today}{DD_today}.csv"
tmin_max_file = outputs_dir / f"Arpg/tmin_tmax_{AA_today}{MM_today}{DD_today}.csv"

# List of stations to be used
stations_list = [
    "NAAMA", "EL-BAYADH", "LAGHOUAT", "DJELFA", "MSILA", "BISKRA", 
    "BATNA", "KHENCHELLA", "TEBESSA", "OULED-DJELLAL", "EL-MGHAIR", 
    "EL-OUED", "TOUGGOURT", "OUARGLA", "GHARDAIA", "EL-GOLEA", "TIMIMOUN", 
    "BECHAR", "BENI-ABBES", "TINDOUF", "ADRAR", "IN-SALAH", "ILLIZI", 
    "DJANET", "TAMANRASSET", "B-B-MOKHTAR", "IN-GUEZZAM"
]

# Load data
arpege = pd.read_csv(arpege_file)
tmin_max = pd.read_csv(tmin_max_file)

# Process arpege data
t_demain_arp = arpege[["station", "t2m_min", "t2m_max", "t2m_max_48"]].rename(
    columns={
        "station": "Station",
        "t2m_min": "prev_min",
        "t2m_max": "prev_max",
        "t2m_max_48": "prev_max_48"
    }
).round(0)

# Observations
station_mapping = {
    "EL-MENIAA": "EL-GOLEA",
    "M'SILA": "MSILA"
}

# Observations min/max
obs_minmax = pd.read_csv(tmin_max_file)
obs_minmax["stationOrSiteName"] = obs_minmax["stationOrSiteName"].replace(station_mapping)

t_obs_minmax = obs_minmax[["stationOrSiteName", "tmin", "tmax"]].rename(
    columns={
        "stationOrSiteName": "Station",
        "tmin": "tmin_obs",
        "tmax": "tmax_obs"
    }
).round(0)

# Merge all data
full_table = pd.merge(t_demain_arp, t_obs_minmax, on="Station", how="outer")

# Set column order and fill missing values
columns_order = ["Station", "tmin_obs", "prev_min", "tmax_obs", "prev_max",  "prev_max_48"]
full_table = full_table.reindex(columns=columns_order).fillna("/")

# Ensure only the stations in the list are included and fill missing ones
final_table = full_table.set_index("Station").reindex(stations_list).reset_index().fillna("/")

# Sort by station list order
final_table["Station"] = pd.Categorical(final_table["Station"], categories=stations_list, ordered=True)
final_table = final_table.sort_values("Station")

# Save to Excel file (one table)
wb, ws = create_workbook_with_sheet("All Stations")
for row in dataframe_to_rows(final_table, index=False, header=True):
    ws.append(row)
wb.save(outputs_dir / f"Arpg/all_stations.xlsx")

print("Excel file created successfully.")

#os.chdir(os.path.join(source_dir, "scr"))
#run_next_program("7-create_word.py")