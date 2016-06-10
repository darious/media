path=$1
shift

uuid=$(uuidgen)
TempScriptName="/tmp/hevcit_batch_$uuid.sh"

echo "$TempScriptName"

rm "$TempScriptName" > /dev/null

find "$path" -type f \( -iname \*.mp4 -o -iname \*.mkv -o -iname \*.m4v -o -iname \*.avi -o -iname \*.mov \) | sort | while read line; do
	echo -e "\e[43m./hevcit.sh -b half -f backup '$line'\e[0m"
	echo "./hevcit.sh -b half -f backup \"$line\"" >> $TempScriptName
done;

chmod +x "$TempScriptName"

"$TempScriptName"

rm "$TempScriptName"
