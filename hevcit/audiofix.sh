# work out the audio format in the source file
AudioFormat=$(mediainfo --inform="Audio;%Format%" "$1")
AudioChannels=$(mediainfo --inform="Audio;%Channels%" "$1")
AudioBitRate=$(mediainfo --inform="Audio;%BitRate%" "$1")

case "$AudioChannels" in
	1) 	AudioAction="converted"
		AudioConvert="-acodec libfdk_aac -b:a -ac 2 128k -sample_rate 48000"
		FileFormat=".mp4"
	;;
	2) 	AudioAction="converted"
		AudioConvert="-acodec libfdk_aac -b:a 128k -sample_rate 48000"
		FileFormat=".mp4"
	;;
	6) 	case "$AudioFormat" in
			AC-3)	if [ "$AudioBitRate" -gt 384000 ]; then
					AudioAction="recoded to 384k"
					AudioConvert="-acodec ac3 -b:a 384k -sample_rate 48000"
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
			*) 	echo "Strange audio format. Exiting"
				echo `date +%Y-%m-%d_%H:%M:%S` ": $1 - Exit - Strange audio format" >> hevcit.log				
			;;
		esac
	;;
	*) 	echo "Strange number of audio channels. Exiting"
		echo `date +%Y-%m-%d_%H:%M:%S` ": $1 - Exit - Strange number of audio channels" >> hevcit.log

	;;
esac

echo "Source Audio is $AudioChannels channel $AudioFormat at $AudioBitRate bps and therefore will be $AudioAction."
