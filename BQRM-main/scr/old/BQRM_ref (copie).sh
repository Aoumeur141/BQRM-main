#!/bin/bash

########################################################################
#                                                                      #
#   Bufr and Arpege Data Retrieval and Processing Script               #
#                                                                      #
#   This script connects to FTP and SFTP servers to retrieve BUFR      #
#   and Arpege data files. It then downloads these files, processes    #
#   them using Python scripts, and performs necessary operations       #
#   such as plotting geopotential height and mean sea level pressure,  #
#   and converting BUFR data to Excel format.                          #
#                                                                      #
#   AUTHOR:                                                            #
#   - Nour El Isslam KERROUMI                                          #
#                                                                      #
#   LAST MODIFICATION:                                                 #
#   - Date: 24th March 2024                                            #
#                                                                      #
########################################################################
BUFR_BASE_DIR_DD="${LOCAL_DIRECTORY}/../../data/observations/${MM}/${DD}"
BUFR_BASE_DIR_DDprec="${LOCAL_DIRECTORY}/../../data/observations/${MM}/${DDprec}"
# Informations sur le serveur FTP
# Répertoire sur le serveur FTP contenant les fichiers
REMOTE_DIRECTORY="/share/ARPEGE+01+SP1"
# Répertoire local où vous voulez sauvegarder les fichiers
LOCAL_DIRECTORY=${PWD}
# Informations sur le serveur FTP
FTP_SERVER="ftp1.meteo.dz"
FTP_USERNAME="messir"
FTP_PASSWORD="123Messir123"
# Informations sur le serveur SFTP
#SFTP_SERVER="192.168.0.122"
#SFTP_USERNAME="pnt"

#SFTP_REMOTE_DIRECTORY_DD="/home/cnpm/BDO/out/SYNOP/CONV-BUFR/${AA}/${MM}/${DD}/06/alg"
#SFTP_REMOTE_DIRECTORY_DDprec="/home/cnpm/BDO/out/SYNOP/CONV-BUFR/${AA}/${MM}/${DDprec}/18/alg"
# Connexion au serveur FTP et téléchargement des fichiers
ftp -n  $FTP_SERVER <<END_SCRIPT
quote USER $FTP_USERNAME
quote PASS $FTP_PASSWORD
lcd $LOCAL_DIRECTORY
cd $REMOTE_DIRECTORY
binary  # Switch to binary mode
prompt off
mget YMID41_LFPW_${DD}*
quit
END_SCRIPT

mv $LOCAL_DIRECTORY/YMID41_LFPW_${DD}00* $LOCAL_DIRECTORY/../arpege_geopotentiel_temperature 
mv $LOCAL_DIRECTORY/YMID41_LFPW_${DD}06* $LOCAL_DIRECTORY/../arpege_mslp 

cd 
######l'identifiant de la station jijel-port  est attribué à la station Bouharoun###### 
#cat /bqrm_data/observations/${AAprec}/${MMprec}/${DDprec}/SMAL*${DDprec}1800* | sed '/^60.*NIL=/d' > Synop_${AAprec}${MMprec}${DDprec}1800
#sed -E -i  ':a;N;$!ba;s/(AAXX.*\n)(60377 )/\1'60353' /g;s/(=\^M\n)(60377 )/\1'60353' /g'  Synop_${AAprec}${MMprec}${DDprec}1800
#cat SMAL*${DDprec}1800*  > Synop_${AA}${MM}${DDprec}1800
#./synop2bufr.exe -i Synop_${AAprec}${MMprec}${DDprec}1800 -o Synop_${AAprec}${MMprec}${DDprec}1800.bufr -c 21 
#cat SMAL*${DD}0600*  > Synop_${AA}${MM}${DD}0600
#cat /bqrm_data/observations/${AA}/${MM}/${DD}/SMAL*${DD}0600* | sed '/^60.*NIL=/d' > Synop_${AA}${MM}${DD}0600

#sed -E -i  ':a;N;$!ba;s/(AAXX.*\n)(60377 )/\1'60353' /g;s/(=\^M\n)(60377 )/\1'60353' /g' Synop_${AA}${MM}${DD}0600
#./synop2bufr.exe -i Synop_${AA}${MM}${DD}0600 -o Synop_${AA}${MM}${DD}0600.bufr -c 21
+-/8*/
cd $LOCAL_DIRECTORY
# Vérification si le téléchargement FTP a réussi
if [ $? -eq 0 ]; then
#    echo "Téléchargement des fichiers depuis le serveur FTP réussi."

    # Connexion au serveur SFTP et téléchargement du fichier supplémentaire
    #cp $SFTP_USERNAME@$SFTP_SERVER:$SFTP_REMOTE_DIRECTORY_DD/* $LOCAL_DIRECTORY/..
    #cp $SFTP_USERNAME@$SFTP_SERVER:$SFTP_REMOTE_DIRECTORY_DDprec/* $LOCAL_DIRECTORY/..
    cp $LOCAL_DIRECTORY/../../Synop_${AAprec}${MMprec}${DDprec}1800.bufr  $LOCAL_DIRECTORY/../synop_alg_${AAprec}${MMprec}${DDprec}1800.bufr
    cp $LOCAL_DIRECTORY/../../Synop_${AA}${MM}${DD}0600.bufr $LOCAL_DIRECTORY/../synop_alg_${AA}${MM}${DD}0600.bufr
    echo "INFO: $(date '+%Y-%m-%d %H:%M:%S') - Moving BUFR files to $LOCAL_DIRECTORY"

#    cp /home/bqrm/Synop_${AAprec}${MMprec}${DDprec}1800.bufr $LOCAL_DIRECTORY/../synop_alg_${AAprec}${MMprec}${DDprec}1800.bufr
#    cp /home/bqrm/Synop_${AA}${MM}${DD}0600.bufr $LOCAL_DIRECTORY/../synop_alg_${AA}${MM}${DD}0600.bufr
    # Vérification si le téléchargement SFTP a réussi
    if [ $? -eq 0 ]; then
        echo "Téléchargement des fichiers synops réussi."
        # Exécuter les scripts Python une fois les fichiers téléchargés
        python3 Arpege_geopotentiel_temperature_plot.py $LOCAL_DIRECTORY/../arpege_geopotentiel_temperature 
        python3 Arpege_mslp_plot.py $LOCAL_DIRECTORY/../arpege_mslp 
        python3 BufrToXLS_ref.py 
	python3 send_MSG.py
    else
        echo "Échec du téléchargement du fichier depuis le serveur SFTP."
    fi
else
    echo "Échec du téléchargement des fichiers depuis le serveur FTP."
fi
rm $LOCAL_DIRECTORY/../arpege_mslp 
rm $LOCAL_DIRECTORY/../arpege_geopotentiel_temperature 
rm $LOCAL_DIRECTORY/../../Synop_${AAprec}${MMprec}${DDprec}1800*
rm $LOCAL_DIRECTORY/../../Synop_${AA}${MM}${DD}0600*
rm $LOCAL_DIRECTORY/../output.xlsx
rm $LOCAL_DIRECTORY/../Bulletin_*.xlsx 
rm $LOCAL_DIRECTORY/../geopotential_and_temperature_*.png
rm $LOCAL_DIRECTORY/../mslp_*.png 
rm $LOCAL_DIRECTORY/YMID*
mkdir -p /bqrm_data/bulletins/BQRM/${AA}/${MM}/${DD}
mkdir -p /bqrm_data/data/${AAprec}/${MMprec}/${DDprec}
mkdir -p /bqrm_data/data/${AA}/${MM}/${DD}
mv $LOCAL_DIRECTORY/../synop_alg_${AAprec}${MMprec}${DDprec}1800.bufr /bqrm_data/data/${AAprec}/${MMprec}/${DDprec}/. 
mv $LOCAL_DIRECTORY/../synop_alg_${AA}${MM}${DD}0600.bufr /bqrm_data/data/${AA}/${MM}/${DD}/.
mv BQRM_${AA}${MM}${DD}0600.docx /bqrm_data/bulletins/BQRM/${AA}/${MM}/${DD}/.
#cd 
#mkdir -p backup/${AA}${MM}${DD}

#cp SMAL*${DD}0600*  backup/${AA}${MM}${DD}/.
#mv SMAL*${DDprec}1800* backup/${AA}${MM}${DD}/. 
