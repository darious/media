#!/bin/bash

# script to convert input video file into HEVC and AAC
# uses metadata to make the file half the size
# %1 - Filename
# -b|--bitrate		: Calulate the bitrate, default is to 1/2 the size
# -f|--fileformat 	: Skip the backup, appends _new to the end of the filename instead

# constants
ContBackupLocation="/media/stewie/backup/"
ContBitRateLow=500

# pull in our input args
InputFileName="$5"

if [ "$#" -ne 5 ]; then
	echo "Error wrong number of parameters passed"
	exit 0
fi

while [[ $# > 1 ]]
do
key="$1"
	case $key in
        	-b | --bitrate)
		case "$2" in
			calc)
				ParaBitRate="calc"
			;;
			half)
				ParaBitRate="half"
			;;
			*)
				echo "Error : Invalid parameters passed"
				exit 0
			;;
		esac
		shift
	;;
        -f | --fileformat)
		case "$2" in
			backup)
				ParaFile="backup"
			;;
			new)
				ParaFile="new"
			;;
			*)
				echo "Error : Invalid parameters passed"
				exit 0
			;;
		esac
		shift
	;;
	esac
	shift
done

echo "$InputFileName"
echo "$ParaBitRate"
echo "$ParaFile"


