path=$1

find "$path" -type f \( -iname \*.mp4 -o -iname \*.mkv -o -iname \*.m4v -o -iname \*.avi -o -iname \*.mov \) | sort | while read line; do
	./hevcit.sh -b half -f backup "$line"
	#echo "$line"
done;

