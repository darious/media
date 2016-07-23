
while getopts "b:h:f:" OPTION
do
    case $OPTION in
        b)
            bitrate=$OPTARG
            ;;
        h)
            option_h=$OPTARG
            ;;
		f)
            filepath=$OPTARG
            ;;
    esac
done



uuid=$(uuidgen)
TempScriptName="/tmp/hevcit_batch_$uuid.sh"

echo "$TempScriptName"

rm "$TempScriptName"

find "$filepath" -type f \( -iname \*.mp4 -o -iname \*.mkv -o -iname \*.m4v -o -iname \*.avi -o -iname \*.mov -o -iname \*.flv -o -iname \*.wmv  \) | sort | while read line; do
	echo -e "\e[43m\e[30m./hevcit.sh -b calc -f backup '$line'\e[0m"
	echo "./hevcit.sh -b $bitrate -h $option_h -f \"$line\"" >> $TempScriptName
done;

chmod +x "$TempScriptName"

"$TempScriptName"

rm "$TempScriptName"
