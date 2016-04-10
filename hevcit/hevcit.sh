#!/bin/bash

# script to convert input video file into HEVC and AAC
# uses metadata to make the file half the size
# %1 - Filename
# -b|--bitrate		: Calulate the bitrate, default is to 1/2 the size
# -f|--fileformat 	: Skip the backup, appends _new to the end of the filename instead

# constants
ContBackupLocation="/media/stewie/backup/"
ContLogLocation="/var/log/hevcit/hevcit.log"
ContBitRateLow=500

# pull in our input args
InputFileName="$5"

if [ "$#" -ne 5 ]; then
	echo -e "\e[41mError wrong number of parameters passed\e[0m"
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
				BitRateTarget="$2"
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
				echo -e "\e[41mError : Invalid parameters passed\e[0m"
				exit 0
			;;
		esac
		shift
	;;
	esac
	shift
done

echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Starting" >> $ContLogLocation

xpath=${1%/*} 
xbase=${1##*/}
xfext=${xbase##*.}
xpref=${xbase%.*}

# check the file exists
if [ -f "$InputFileName" ]
then
	echo -e "\e[44mWorking on : $InputFileName\e[0m"
else
	echo -e "\e[41m$InputFileName not found. Exiting\e[0m"
	echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Exit - File not found" >> $ContLogLocation
	exit 0
fi

# check the source video format
VideoSource=$(mediainfo --inform="Video;%Format%" "$InputFileName")

if [ "$VideoSource" = "HEVC" ]; then
	echo -e "\e[41mVideo is already HEVC. Exiting\e[0m"
	echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Exit - Video is already HEVC" >> $ContLogLocation
	exit 0
fi

# show some interesting information
VideoW=$(mediainfo --inform="Video;%Width%" "$InputFileName")
VideoH=$(mediainfo --inform="Video;%Height%" "$InputFileName")
VideoF=$(ffmpeg -i "$1" 2>&1 | sed -n "s/.*, \(.*\) fp.*/\1/p")
VideoD=$(mediainfo --inform="General;%Duration%" "$InputFileName")
VideoD=$((VideoD / 1000))

echo -e "\e[44mVideo is $VideoSource ${VideoW}x${VideoH} at ${VideoF}fps & $VideoD seconds long\e[0m"
echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Video is $VideoSource ${VideoW}x${VideoH} at ${VideoF}fps & $VideoD seconds long" >> $ContLogLocation

# if the file is 50fps then make it 25fps
if [ "$VideoF" = 50 ]; then
	VideoF=25
	Resample="-r 25"
	echo -e "\e[44mGot a 50fps file so wil resample to 25fps\e[0m"
	echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - is 50fps so will resample to 25fps" >> $ContLogLocation
else
	Resample=" "
fi

# if the video is interlace then add a deinterlace filter to the command
VideoScan=$(mediainfo --inform="Video;%ScanType%" "$InputFileName")
if [ "$VideoScan" = "Interlaced" ]; then
	#Deinterlace='-vf "yadif=0:-1:0"'
	Deinterlace="-deinterlace"
	echo -e "\e[44mGot an interlaced file so wil deinterlace\e[0m"
	echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - is interlaced so will deinterlace" >> $ContLogLocation
else
	Deinterlace=""
fi

# get the video bitrate
BitRateSource=$(mediainfo --inform="Video;%BitRate%" "$InputFileName")
# convert to Kbps
BitRateSource=$((BitRateSource / 1000))

# workout the target bitrate
if [ "$ParaBitRate" = "half" ]; then
	# Work out 1/2 the current

	# deal with a 0 bitrate
	if [ "$BitRateSource" = 0 ]; then
		# extract the video	
		TempVideoFile=`echo "/tmp/$xpref.h264"`
		echo -e "\e[44mGot a 0 BitRate so extracting Video to $TempVideoFile\e[0m"
		echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Got a 0 BitRate so extracting to temp file" >> $ContLogLocation
		ffmpeg -i "$InputFileName" -vcodec copy -an "$TempVideoFile"
	
		# get the new file size and work out the bitrate from it
		TempVideoFileSize=$(mediainfo --inform="General;%FileSize%" "$TempVideoFile")
		TempVideoFileSize=$((TempVideoFileSize / 1000))
		BitRateSource=$(((TempVideoFileSize / VideoD) * 8))
		rm "$TempVideoFile"
	fi

	# Calculate the target bit rate as the 1/2 the source 
	BitRateTarget=$((BitRateSource / 2))

	# check the bitrate is ok
	if [ "$BitRateTarget" -lt $ContBitRateLow ]; then
		BitRateTarget="$ContBitRateLow"
		if [ $BitRateTarget -gt $BitRateSource ]; then
			echo -e "\e[44mTarget BitRate of $BitRateTarget would be lower than source bitrate of $BitRateSource. So Using source bitrate\e[0m"
			echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Target bitrate of $BitRateTarget lower than source bitrate of $BitRateSource. So using source bitrate" >> $ContLogLocation
			BitRateTarget="$BitRateSource"
		fi
	fi
	echo -e "\e[44mSource $VideoSource video BitRate is : $BitRateSource, the Target BitRate will be 1/2 that at : $BitRateTarget\e[0m"
	echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - 1/2 Bitrate - Source Bitrate : $BitRateSource, Target Bitrate : $BitRateTarget" >> $ContLogLocation	
elif [ "$ParaBitRate" = "calc" ]; then
	# calculate the bitrate from the video file properties
	BitRateTarget=$(echo "((($VideoH * $VideoW * $VideoF) / 1000000) + 11) * 37" | bc)
	echo -e "\e[44mSource $VideoSource video BitRate is : $BitRateSource, the Target BitRate based video size : $BitRateTarget\e[0m"
	echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Bitrate calculated - Source Bitrate : $BitRateSource, Target Bitrate : $BitRateTarget" >> $ContLogLocation	
else
	echo -e "\e[44mSource $VideoSource video BitRate is : $BitRateSource, the Target BitRate given is : $BitRateTarget\e[0m"
	echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Bitrate given - Source Bitrate : $BitRateSource, Target Bitrate : $BitRateTarget" >> $ContLogLocation
fi

# work out the audio format in the source file
AudioFormat=$(mediainfo --inform="Audio;%Format%" "$InputFileName")
AudioChannels=$(mediainfo --inform="Audio;%Channels%" "$InputFileName")
AudioBitRate=$(mediainfo --inform="Audio;%BitRate%" "$InputFileName")
AudioSampleRate=$(mediainfo --inform="Audio;%SamplingRate%" "$InputFileName")

# and what should we do with the audio?
case "$AudioChannels" in
	1) 	AudioAction="converted"
		AudioConvert="-acodec libfdk_aac -b:a 128k -ac 2 -ar 48000 -sample_fmt s16"
		FileFormat=".mp4"
	;;
	2) 	AudioAction="converted"
		AudioConvert="-acodec libfdk_aac -b:a 128k -ac 2 -ar 48000 -sample_fmt s16"
		FileFormat=".mp4"
	;;
	6) 	case "$AudioFormat" in
			AC-3)	if [ "$AudioBitRate" -gt 384000 ]; then
					AudioAction="recoded to 384k"
					AudioConvert="-acodec ac3 -b:a 384k -ar 48000"
					FileFormat=".mkv"
				else
					AudioAction="passed through"
					AudioConvert="-acodec copy"
					FileFormat=".mkv"
				fi
			;;
			DTS)	AudioAction="passed through"
				AudioConvert="-acodec copy"
				FileFormat=".mkv"
			;;
			*) 	echo -e "\e[41mError - Strange audio format. Exiting\e[0m"
				echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Exit - Strange audio format" >> $ContLogLocation				
			;;
		esac
	;;
	*) 	echo -e "\e[41mStrange number of audio channels. Exiting\e[0m"
		echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Exit - Strange number of audio channels" >> $ContLogLocation

	;;
esac

echo -e "\e[44mSource Audio is $AudioChannels channel $AudioFormat at $AudioBitRate bps & $AudioSampleRate Khz and therefore will be $AudioAction\e[0m"
echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Audio is $AudioChannels channel $AudioFormat at $AudioBitRate bps & $AudioSampleRate Khz and will be $AudioAction." >> $ContLogLocation


# backup the current file or change the target name
if [ "$ParaFile" = "backup" ]; then
	BackupFile=`echo "$ContBackupLocation""$xbase"`
	echo -e "\e[44mBacking up file to $BackupFile\e[0m"
	mv "$InputFileName" "$BackupFile"
	echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Backup Complete" >> $ContLogLocation		

	# calculate file names
	if [ "$xpath" = "$xbase" ]; then
		TargetFile=`echo "$xpref$FileFormat"`	
	else
		TargetFile=`echo "$xpath/$xpref$FileFormat"`
	fi

	EncodeFile="$BackupFile"
elif [ "$ParaFile" = "new" ]; then
	FileNew="_new"
	EncodeFile=`echo "$InputFileName"`
	TargetFile=`echo "$xpath/$xpref$FileNew$FileFormat"`
else
	echo -e "\e[41mError in backup calculation - Exiting\e[0m"
	echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Exit - Error in backup calculation." >> $ContLogLocation	
	exit 0	
fi

# Encode the file
echo -e "\e[44mEncode from $EncodeFile to $TargetFile\e[0m"
# run ffmpeg with the correct settings we've just calculated
echo -e "\e[44mffmpeg -i "$EncodeFile" -vcodec nvenc_hevc -b:v "${BitRateTarget}"k -preset hq $Resample $Deinterlace ${AudioConvert} "$TargetFile"\e[0m"
echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Encoding with - ffmpeg -i "$EncodeFile" -vcodec nvenc_hevc -b:v "${BitRateTarget}"k -preset hq $Resample $Deinterlace ${AudioConvert} "$TargetFile"" >> $ContLogLocation
ffmpeg -i "$EncodeFile" -vcodec nvenc_hevc -b:v "${BitRateTarget}"k -preset hq $Resample $Deinterlace ${AudioConvert} "$TargetFile"

echo -e "\e[44m$InputFileName - Complete\e[0m\n\r"
echo `date +%Y-%m-%d_%H:%M:%S` ": $InputFileName - Complete" >> $ContLogLocation

exit 0


