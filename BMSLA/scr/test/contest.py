import os
import subprocess
from datetime import datetime
#from modules.module import run_next_program

# Définir manuellement le répertoire parent et la date ici
dir_parent = "/home/ibousri/AROME_DUST/Projet_Nationale/Sonelgaz/sonelgaz_oper"  # Remplacez par le chemin réel du répertoire parent
date_input = "20250410"  # Remplacez par la date que vous souhaitez tester (au format YYYYMMDD)

# List of files and time ranges (same as before)
files = [
    ("t2m00-12.grib", "ARPEGE+01+SP1+00H12H"),
    ("t2m13-24.grib", "ARPEGE+01+SP1+13H24H"),
    ("t2m25-36.grib", "ARPEGE+01+SP1+25H36H"),
    ("t2m37-48.grib", "ARPEGE+01+SP1+37H48H"),
]

# Assurer que les fichiers sont dans le répertoire parent ou tout autre répertoire de votre choix
grib_directory = os.path.join(dir_parent, "Arpg")  # Modifier ce chemin selon l'emplacement de vos fichiers GRIB

# Exécuter grib_copy pour chaque fichier
for output_file, time_range in files:
    input_file = os.path.join(grib_directory, f"W_fr-meteofrance,MODEL,{time_range}_C_LFPW_{date_input}0000--.grib2")
    
    if not os.path.exists(input_file):
        print(f"Le fichier {input_file} n'existe pas. Vérifiez le chemin et le nom du fichier.")
        continue
    
    print(f"Exécution de grib_copy pour {input_file}...")
    subprocess.run(["/usr/bin/grib_copy", "-w", "shortName=2t", input_file, output_file])

print("Début de la fusion de tous les grib de température en un seul fichier :")
# Fusionner les fichiers manuellement
output_grib = f"2t_{date_input}.grib"
with open(output_grib, "wb") as outfile:
    for output_file, _ in files:
        temp_file = os.path.join(grib_directory, output_file)
        
        if not os.path.exists(temp_file):
            print(f"Le fichier {temp_file} n'existe pas pour la fusion.")
            continue
        
        with open(temp_file, "rb") as infile:
            outfile.write(infile.read())

# Supprimer les fichiers temporaires
for output_file, _ in files:
    temp_file = os.path.join(grib_directory, output_file)
    if os.path.exists(temp_file):
        os.remove(temp_file)

# Retourner au répertoire 'scr' et lancer le prochain programme
#os.chdir(os.path.join(dir_parent, "scr"))
#run_next_program("3-create_forecast_table.py")
