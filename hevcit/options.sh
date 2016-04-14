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
InputFileName="$1"

echo -e "$InputFileName"

AudioInfoRaw=$(ffprobe -i "$InputFileName" 2>&1 | grep -i "Audio:")

# default this so the comparison works later
KeepAudioTrackChannels=0

while read -r AudioTrack; do
	AudioTrack="$(echo -e "${AudioTrack}" | sed -e 's/^[[:space:]]*//')"

	# grab the info we need, format, channels, sample rate and bitrate
	AudioTrackStream=`echo "$AudioTrack" | cut -c9-11`

	AudioTrackFormat=`echo "$AudioTrack" | grep -io "audio:...."|cut -d ' ' -f2`

	AudioTrackChannels=`echo "$AudioTrack" | cut -d ',' -f3`
	set -- $AudioTrackChannels
	AudioTrackChannels=$1
	# reformat the channels to make it easier later

	case "$AudioTrackChannels" in
		mono) AudioTrackChannels=1
		;;
		stereo) AudioTrackChannels=2
		;;
		"5.1(side)") AudioTrackChannels=6
		;;
		"7.1") AudioTrackChannels=8
		;;
		*) 	echo -e "\e[41mStrange number of audio channels. Exiting\e[0m"
			echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Exit - Strange number of audio channels" >> $ContLogLocation
			exit 0
		;;
	esac

	AudioTrackSampleRate=`echo "$AudioTrack" | cut -d ',' -f2`
	set -- $AudioTrackSampleRate
	AudioTrackSampleRate=$1

	AudioTrackBitRate=`echo "$AudioTrack" | cut -d ',' -f5`
	set -- $AudioTrackBitRate
	AudioTrackBitRate=$1

	echo -e "\e[44mAudio track $AudioTrackStream is $AudioTrackFormat with $AudioTrackChannels channels in ${AudioTrackSampleRate}Khz at ${AudioTrackBitRate}kbps\e[0m"
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Audio track $AudioTrackStream is $AudioTrackFormat with $AudioTrackChannels channels in ${AudioTrackSampleRate}Khz at ${AudioTrackBitRate}kbps" >> $ContLogLocation
	
	# figure out what to so with this track
	case "$AudioTrackChannels" in
		1) 	AudioAction="recoded to 128k AAC"
			AudioConvert="-acodec libfdk_aac -b:a 128k -ac 2 -ar 48000 -sample_fmt s16"
			FileFormat=".mp4"
		;;
		2)	AudioAction="recoded to 128k AAC"
			AudioConvert="-acodec libfdk_aac -b:a 128k -ac 2 -ar 48000 -sample_fmt s16"
			FileFormat=".mp4"
		;;
		6) 	case "$AudioTrackFormat" in
				ac3)	if [ "$AudioTrackBitRate" -gt 384 ]; then
						AudioAction="recoded to 384k AC3"
						AudioConvert="-acodec ac3 -b:a 384k -ar 48000"
						FileFormat=".mkv"
					else
						AudioAction="passed through"
						AudioConvert="-acodec copy"
						FileFormat=".mkv"
					fi
				;;
				dts)	AudioAction="recoded to 384k AC3"
					AudioConvert="-acodec ac3 -b:a 384k -ar 48000"
					FileFormat=".mkv"
				;;
				*) 	echo -e "\e[41mError - Strange audio format. Exiting\e[0m"
					echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Exit - Strange audio format" >> $ContLogLocation
					exit 0
				;;
			esac
					
		;;
		8)	AudioAction="passed through"
			AudioConvert="-acodec copy"
			FileFormat=".mkv"
		;;			
		*) 	echo -e "\e[41mStrange number of audio channels. Exiting\e[0m"
			echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Exit - Strange number of audio channels" >> $ContLogLocation
			exit 0
		;;
	esac

	# if this is the 1st track then we should keep the values for use
	if [ "$AudioTrackStream" = 1 ]; then
		KeepAudioTrackStream=$AudioTrackStream
		KeepAudioTrackFormat=$AudioTrackFormat
		KeepAudioTrackChannels=$AudioTrackChannels
		KeepAudioTrackSampleRate=$AudioTrackSampleRate
		KeepAudioTrackBitRate=$AudioTrackBitRate
		KeepAudioAction=$AudioAction
		KeepAudioConvert=$AudioConvert
	else
		# does this track have more channels than the last one? If so then we should keep this one instead
		if [ "$AudioTrackChannels" -gt "$KeepAudioTrackChannels" ]; then
			KeepAudioTrackStream=$AudioTrackStream
			KeepAudioTrackFormat=$AudioTrackFormat
			KeepAudioTrackChannels=$AudioTrackChannels
			KeepAudioTrackSampleRate=$AudioTrackSampleRate
			KeepAudioTrackBitRate=$AudioTrackBitRate
			KeepAudioAction=$AudioAction
			KeepAudioConvert=$AudioConvert
		fi
	fi
	
done <<< "$AudioInfoRaw"

echo -e "\e[44mKeeping audio track $KeepAudioTrackStream ($KeepAudioTrackFormat with $KeepAudioTrackChannels channels in ${KeepAudioTrackSampleRate}Khz at ${KeepAudioTrackBitRate}kbps and it will be $KeepAudioAction\e[0m"
echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Keeping audio track $KeepAudioTrackStream ($KeepAudioTrackFormat with $KeepAudioTrackChannels channels in ${KeepAudioTrackSampleRate}Khz at ${KeepAudioTrackBitRate}kbps and it will be $KeepAudioAction" >> $ContLogLocation


# figure out which track is the video and stash the stream number
VideoInfoRaw=$(ffprobe -i "$InputFileName" 2>&1 | grep -i "Video:")
VideoInfoRaw="$(echo -e "${VideoInfoRaw}" | sed -e 's/^[[:space:]]*//')"
VideoTrackStream=`echo "$VideoInfoRaw" | cut -c9-11`

echo "$VideoInfoRaw"
echo "$AudioInfoRaw"

# work out what subtitles to keep
SubInfoRaw=$(ffprobe -i "$InputFileName" 2>&1 | grep -i "Subtitle:")

echo "$SubInfoRaw"

KeepSubMap=""

while read -r SubTrack; do
	SubTrack="$(echo -e "${SubTrack}" | sed -e 's/^[[:space:]]*//')"
	echo "$SubTrack"
	# find the language
	SubStream=`echo "$SubTrack" | cut -c9-11`
	SubLang=`echo "$SubTrack" | cut -c13-15`
	echo "$SubStream"	
	echo "$SubLang"

	if [ "$SubLang" = "eng" ]; then
		KeepSubMap="$KeepSubMap -map $SubStream"
		echo -e "\e[44mSubtitle track ${SubStream} is English and will be kept\e[0m"
		echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Keeping subtitle track $SubStream as it is in English" >> $ContLogLocation
	elif [ "$SubLang" = " Su" ]; then
		KeepSubMap="$KeepSubMap -map $SubStream"
		echo -e "\e[44mSubtitle track ${SubStream} is set to default and will be kept\e[0m"
		echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Keeping subtitle track $SubStream as it is set to default language" >> $ContLogLocation
	fi

done <<< "$SubInfoRaw"

echo "$KeepSubMap"

# calculate the mapping strings for ffmpeg
OutputMapping="-map ${VideoTrackStream} -map ${KeepAudioTrackStream}${KeepSubMap}"

echo "$OutputMapping"







