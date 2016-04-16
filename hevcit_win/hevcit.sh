#!/bin/bash

# script to convert input video file into HEVC and AAC
# uses metadata to make the file half the size
# %1 - Filename
# -b|--bitrate		: Calulate the bitrate, default is to 1/2 the size
# -f|--fileformat 	: Skip the backup, appends _new to the end of the filename instead


convertsecs() {
 ((h=${1}/3600))
 ((m=(${1}%3600)/60))
 ((s=${1}%60))
 printf "%02d:%02d:%02d\n" $h $m $s
}

# constants
#ContBackupLocation="/media/stewie/backup/"
ContBackupLocation="//192.168.0.206/share/backup/"
ContLogLocation="/cygdrive/c/Users/Chris/bin/hevcit/hevcit.log"
ContBitRateLow=500
ffmpegBin="ffmpeg_g.exe"
ffprobeBin="ffprobe_g.exe"

# pull in our input args
InputFileName="$5"
WinInputFile=`cygpath -w "$InputFileName"`

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

echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Starting" >> $ContLogLocation

xpath=${InputFileName%/*} 
xbase=${InputFileName##*/}
xfext=${xbase##*.}
xpref=${xbase%.*}

# check the file exists
if [ -f "$InputFileName" ]
then
	echo -e "\e[44mWorking on : $InputFileName\e[0m"
else
	echo -e "\e[41m$InputFileName not found. Exiting\e[0m"
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Exit - File not found" >> $ContLogLocation
	exit 0
fi

# check the source video format
VideoSource=$(mediainfo --inform="Video;%Format%" "$InputFileName")

if [ "$VideoSource" = "HEVC" ]; then
	echo -e "\e[41mVideo is already HEVC. Exiting\e[0m"
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Exit - Video is already HEVC" >> $ContLogLocation
	exit 0
fi

# show some interesting information
VideoW=$(mediainfo --inform="Video;%Width%" "$InputFileName")
VideoH=$(mediainfo --inform="Video;%Height%" "$InputFileName")
VideoF=$($ffmpegBin -i "$WinInputFile" 2>&1 | sed -n "s/.*, \(.*\) fp.*/\1/p")
VideoD=$(mediainfo --inform="General;%Duration%" "$InputFileName")
VideoD=$((VideoD / 1000))
VideoDT=$(convertsecs $VideoD)

echo -e "\e[44mVideo is $VideoSource ${VideoW}x${VideoH} at ${VideoF}fps & $VideoDT in length\e[0m"
echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Video is $VideoSource ${VideoW}x${VideoH} at ${VideoF}fps & $VideoDT in length" >> $ContLogLocation

# fiddle with the framerate 
case "$VideoF" in
	50)
		VideoFNew=25
		Resample="-r 25"
		echo -e "\e[44mGot a ${VideoF}fps file so wil resample to ${VideoFNew}fps\e[0m"
		echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - is ${VideoF}fps so will resample to ${VideoFNew}fps" >> $ContLogLocation
	;;
	59.94)
		VideoFNew=29.97
		Resample="-r 29.97"
		echo -e "\e[44mGot a ${VideoF}fps file so wil resample to ${VideoFNew}fps\e[0m"
		echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - is ${VideoF}fps so will resample to ${VideoFNew}fps" >> $ContLogLocation
	;;
	60)
		VideoFNew=30
		Resample="-r 30"
		echo -e "\e[44mGot a ${VideoF}fps file so wil resample to ${VideoFNew}fps\e[0m"
		echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - is ${VideoF}fps so will resample to ${VideoFNew}fps" >> $ContLogLocation
	;;
	100)
		VideoFNew=25
		Resample="-r 25"
		echo -e "\e[44mGot a ${VideoF}fps file so wil resample to ${VideoFNew}fps\e[0m"
		echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - is ${VideoF}fps so will resample to ${VideoFNew}fps" >> $ContLogLocation
	;;
	24.97)
		VideoFNew=25
		Resample="-r 25"
		echo -e "\e[44mGot a ${VideoF}fps file so wil resample to ${VideoFNew}fps\e[0m"
		echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - is ${VideoF}fps so will resample to ${VideoFNew}fps" >> $ContLogLocation
	;;
	*)
		VideoFNew=$VideoF
	;;
esac 


# if the video is interlace then add a deinterlace filter to the command
VideoScan=$(mediainfo --inform="Video;%ScanType%" "$InputFileName")
if [ "$VideoScan" = "Interlaced" ]; then
	#Deinterlace='-vf "yadif=0:-1:0"'
	Deinterlace="-deinterlace"
	echo -e "\e[44mGot an interlaced file so wil deinterlace\e[0m"
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - is interlaced so will deinterlace" >> $ContLogLocation
else
	Deinterlace=""
fi

# get the video bitrate
BitRateSource=$(mediainfo --inform="Video;%BitRate%" "$InputFileName")
# convert to Kbps
BitRateSource=$((BitRateSource / 1000))

# deal with a 0 bitrate
if [ "$BitRateSource" = 0 ]; then
	# extract the video	
	TempVideoFile=`echo "/tmp/$xpref.h264"`
	echo -e "\e[44mGot a 0 BitRate so extracting Video to $TempVideoFile\e[0m"
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Got a 0 BitRate so extracting to temp file" >> $ContLogLocation
	rm "$TempVideoFile"
	echo -e "\e[46m$ffmpegBin -i '$InputFileName' -vcodec copy -an '$TempVideoFile'\e[0m"
	$ffmpegBin -i "$InputFileName" -vcodec copy -an "$TempVideoFile"

	# get the new file size and work out the bitrate from it
	TempVideoFileSize=$(mediainfo --inform="General;%FileSize%" "$TempVideoFile")
	TempVideoFileSize=$((TempVideoFileSize / 1000))
	BitRateSource=$(((TempVideoFileSize / VideoD) * 8))
	rm "$TempVideoFile"
fi

# workout the target bitrate
if [ "$ParaBitRate" = "half" ]; then
	# Calculate the target bit rate as the 1/2 the source 
	BitRateTarget=$((BitRateSource / 2))
	echo -e "\e[44mSource $VideoSource video BitRate is : $BitRateSource, the Target BitRate will be 1/2 that : $BitRateTarget\e[0m"
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Source $VideoSource video BitRate is : $BitRateSource, the Target BitRate will be 1/2 that : $BitRateTarget"  >> $ContLogLocation

elif [ "$ParaBitRate" = "calc" ]; then
	# calculate the bitrate from the video file properties
	BitRateTarget=$(echo "((($VideoH * $VideoW * $VideoFNew) / 1000000) + 11) * 37" | bc)
	echo -e "\e[44mSource $VideoSource video BitRate is : $BitRateSource, the Target BitRate based on our calculation : $BitRateTarget\e[0m"
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Source $VideoSource video BitRate is : $BitRateSource, the Target BitRate based on our calculation : $BitRateTarget" >> $ContLogLocation	

else
	echo -e "\e[44mSource $VideoSource video BitRate is : $BitRateSource, the Target BitRate given is : $BitRateTarget\e[0m"
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Source $VideoSource video BitRate is : $BitRateSource, the Target BitRate given is : $BitRateTarget" >> $ContLogLocation
fi

# check the bitrate is ok
# look for a low bitrate
if [ "$BitRateTarget" -lt $ContBitRateLow ]; then
	BitRateTarget="$ContBitRateLow"
	echo -e "\e[44mTarget Bitrate of $BitRateTarget overriden as would be lower than acceptable. Using low bitrate of ${ContBitRateLow}Kbps\e[0m"
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Target Bitrate of $BitRateTarget overriden as would be lower than acceptable Using low bitrate of ${ContBitRateLow}Kbps" >> $ContLogLocation

# make sure the target is less than the source
elif	[ $BitRateTarget -gt $BitRateSource ]; then
	echo -e "\e[44mTarget Bitrate of $BitRateTarget overriden as would be higher than source. Using source bitrate of ${BitRateSource}\e[0m"
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Target Bitrate of $BitRateTarget overriden as would be higher than source. Using source bitrate of ${BitRateSource}" >> $ContLogLocation
	BitRateTarget="$BitRateSource"
fi


# work out what to do with the audio
AudioInfoRaw=$($ffprobeBin -i "$WinInputFile" 2>&1 | grep -i "Audio:")

if [ "$AudioInfoRaw" = "" ]; then
	echo -e "\e[44mNo Audio in source file so no audio will be added to target\e[0m"
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - No Audio in source file so no audio will be added to target" >> $ContLogLocation

	KeepAudioAction="No audio"
	KeepAudioConvert="-acodec none"
	KeepAudioTrackStream=""
	FileFormat=".mp4"
else

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
			"5.1") AudioTrackChannels=6
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
				AudioMetaTitle="-metadata:s:a:0= title=\"English AAC 128k\""
			;;
			2)	AudioAction="recoded to 128k AAC"
				AudioConvert="-acodec libfdk_aac -b:a 128k -ac 2 -ar 48000 -sample_fmt s16"
				AudioMetaTitle="-metadata:s:a:0= title=\"English AAC 128k\""
				FileFormat=".mp4"
			;;
			6) 	case "$AudioTrackFormat" in
					ac3)	if [ "$AudioTrackBitRate" -gt 384 ]; then
							AudioAction="recoded to 384k AC3"
							AudioConvert="-acodec ac3 -b:a 384k -ar 48000"
							AudioMetaTitle="-metadata:s:a:0= title=\"English AC3 384k\""
							FileFormat=".mkv"
						else
							AudioAction="passed through"
							AudioConvert="-acodec copy"
							AudioMetaTitle="-metadata:s:a:0= title=\"English AC3 384k\""
							FileFormat=".mkv"
						fi
					;;
					dts)	AudioAction="recoded to 384k AC3"
						AudioConvert="-acodec ac3 -b:a 384k -ar 48000"
						AudioMetaTitle="-metadata:s:a:0= title=\"English AC3 384k\""
						FileFormat=".mkv"
					;;
					aac)	AudioAction="recoded to 128k AAC"
						AudioConvert="-acodec libfdk_aac -b:a 128k -ac 2 -ar 48000 -sample_fmt s16"
						AudioMetaTitle="-metadata:s:a:0= title=\"English AAC 128k\""
						FileFormat=".mp4"
					;;
					*) 	echo -e "\e[41mError - Strange audio format. Exiting\e[0m"
						echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Exit - Strange audio format" >> $ContLogLocation
						exit 0
					;;
				esac
					
			;;
			8)	AudioAction="passed through"
				AudioConvert="-acodec copy"
				AudioMetaTitle="-metadata:s:a:0= title=\"English ${KeepAudioTrackFormat} ${KeepAudioTrackBitRate}k\""
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

	echo -e "\e[44mKeeping audio track $KeepAudioTrackStream ($KeepAudioTrackFormat with $KeepAudioTrackChannels channels in ${KeepAudioTrackSampleRate}Khz at ${KeepAudioTrackBitRate}kbps) and it will be $KeepAudioAction\e[0m"
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Keeping audio track $KeepAudioTrackStream ($KeepAudioTrackFormat with $KeepAudioTrackChannels channels in ${KeepAudioTrackSampleRate}Khz at ${KeepAudioTrackBitRate}kbps and it will be $KeepAudioAction" >> $ContLogLocation

	KeepAudioTrackStream="-map $KeepAudioTrackStream"

fi



# figure out which track is the video and stash the stream number
VideoInfoRaw=$($ffprobeBin -i "$WinInputFile" 2>&1 | grep -i -m 1 "Video:")
VideoInfoRaw="$(echo -e "${VideoInfoRaw}" | sed -e 's/^[[:space:]]*//')"
VideoTrackStream=`echo "$VideoInfoRaw" | cut -c9-11`


# work out what subtitles to keep
SubInfoRaw=$($ffprobeBin -i "$WinInputFile" 2>&1 | grep -i "Subtitle:")
KeepSubMap=""

while read -r SubTrack; do
	SubTrack="$(echo -e "${SubTrack}" | sed -e 's/^[[:space:]]*//')"
	# find the language
	SubStream=`echo "$SubTrack" | cut -c9-11`
	SubLang=`echo "$SubTrack" | cut -c13-15`
	# should we keep the subtitles?
	if [ "$SubLang" = "eng" ]; then
		KeepSubMap="$KeepSubMap -map $SubStream"
		FileFormat=".mkv"
		echo -e "\e[44mSubtitle track ${SubStream} is English and will be kept\e[0m"
		echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Keeping subtitle track $SubStream as it is in English" >> $ContLogLocation
	elif [ "$SubLang" = " Su" ]; then
		KeepSubMap="$KeepSubMap -map $SubStream"
		FileFormat=".mkv"
		echo -e "\e[44mSubtitle track ${SubStream} is set to default and will be kept\e[0m"
		echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Keeping subtitle track $SubStream as it is set to default language" >> $ContLogLocation
	fi

done <<< "$SubInfoRaw"

# calculate the mapping strings for ffmpeg
OutputMapping="-map ${VideoTrackStream} ${KeepAudioTrackStream}${KeepSubMap}"


# backup the current file or change the target name
if [ "$ParaFile" = "backup" ]; then
	BackupFile=`echo "$ContBackupLocation""$xbase"`
	echo -e "\e[44mBacking up file to $BackupFile\e[0m"
	mv "$InputFileName" "$BackupFile"
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Backup Complete" >> $ContLogLocation		

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
	echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Exit - Error in backup calculation." >> $ContLogLocation	
	exit 0	
fi


# as we're on windows we need to fiddle with the file names
WinEncodeFile=`cygpath -w "$EncodeFile"`
WinTargetFile=`cygpath -w "$TargetFile"`

# Encode the file
echo -e "\e[44m"
echo "Encode from $WinEncodeFile to $WinTargetFile"

# run ffmpeg with the correct settings we've just calculated
EncodeDate=$(date +%Y-%m-%d\ %H:%M:%S)

# create ffmpeg command
ffmpegCMD=$(echo "'$WinEncodeFile' ${OutputMapping} -vcodec nvenc_hevc -b:v ${BitRateTarget}k -maxrate 20000k -preset hq $Resample $Deinterlace ${KeepAudioConvert} -metadata creation_time=\"$EncodeDate\" ${AudioMetaTitle} '$WinTargetFile'")

uuid=$(uuidgen)
TempScriptName="/tmp/hevcit_$uuid.sh"

echo "$ffmpegBin -i $ffmpegCMD" > $TempScriptName

ffcmd=`cat $TempScriptName`

#echo -e "\e[46m$ffmpegBin -i $ffmpegCMD\e[0m"
echo -e "\e[46m\e[30m"
echo $ffcmd
echo -e "\e[0m"

chmod +x "$TempScriptName"

echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - $ffmpegBin -i $ffmpegCMD" >> $ContLogLocation	

# do the encode
"$TempScriptName"

rm "$TempScriptName"

echo -e "\e[44m$InputFileName - Complete\e[0m\n\r"
echo `date +%Y-%m-%d\ %H:%M:%S` ": $InputFileName - Complete" >> $ContLogLocation

exit 0

