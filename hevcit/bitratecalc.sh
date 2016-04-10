#!/bin/bash

ContBitRateLow=500

echo "Working on : $1"

xpath=${1%/*} 
xbase=${1##*/}
xfext=${xbase##*.}
xpref=${xbase%.*}

VideoW=$(mediainfo --inform="Video;%Width%" "$1")
VideoH=$(mediainfo --inform="Video;%Height%" "$1")
#VideoF=$(mediainfo --inform="Video;%FrameRate%" "$1")
VideoF=$(ffmpeg -i "$1" 2>&1 | sed -n "s/.*, \(.*\) fp.*/\1/p")
VideoD=$(mediainfo --inform="General;%Duration%" "$1")
VideoD=$((VideoD / 1000))

echo "Video is $VideoSource ${VideoW}x${VideoH} at ${VideoF}fps & $VideoD seconds long"

# get the video bitrate
BitRateSource=$(mediainfo --inform="Video;%BitRate%" "$1")
# convert to Kbps
BitRateSource=$((BitRateSource / 1000))

# deal with a 0 bitrate
if [ "$BitRateSource" = 0 ]; then
	# extract the video	
	TempVideoFile=`echo "/tmp/$xpref.h264"`
	echo "Got a 0 BitRate so extracting Video to $TempVideoFile"
	ffmpeg -i "$1" -vcodec copy -an "$TempVideoFile"
	
	# get the new file size and work out the bitrate from it
	TempVideoFileSize=$(mediainfo --inform="General;%FileSize%" "$TempVideoFile")
	TempVideoFileSize=$((TempVideoFileSize / 1000))
	BitRateSource=$(((TempVideoFileSize / VideoD) * 8))
	echo "$BitRateSource"
	rm "$TempVideoFile"
fi

# Calculate the target bit rate as the 1/2 the source 
BitRateTarget=$((BitRateSource / 2))

echo "$BitRateTarget"

# check the bitrate is ok
if [ "$BitRateTarget" -lt $ContBitRateLow ]; then
	echo "Target Bitrate seems low at $BitRateTarget"
	BitRateTarget="$ContBitRateLow"
	if [ $BitRateTarget -gt $BitRateSource ]; then
		echo "Target BitRate of $BitRateTarget would be lower than source bitrate of $BitRateSource. So Using source bitrate"
		#echo `date +%Y-%m-%d_%H:%M:%S` ": $1 - Exit - Target bitrate of $BitRateTarget lower than source bitrate of $BitRateSource. So using source bitrate" >> hevcit.log
		BitRateTarget="$BitRateSource"
		exit 0
	fi
fi

echo "BitRateSource : $BitRateSource, Width : $VideoW, Height : $VideoH, FrameRate : $VideoF, Duration : $VideoD"

echo "Video is $VideoSource ${VideoW}x${VideoH} at ${VideoF}fps & $VideoD seconds long"

# calculate the bitrate from the video parameters
BitRateCalc=$(echo "((($VideoH * $VideoW * $VideoF) / 1000000) + 11) * 37" | bc)

echo "$BitRateCalc"
