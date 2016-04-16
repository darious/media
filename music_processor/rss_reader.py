#!/usr/bin/python

# ---------------------------------------------------------------------------------------
# Music Processor
#
# RSS Reader
#
# Pulls the top 40 from itunes and maintains the backlog of stuff to download
#
# Version	Date		Descripiton
# 1.00		2016-04-16	Initial Version
# ---------------------------------------------------------------------------------------

# import libraries
import feedparser
import sqlite3 as lite
import sys
import re

# Read the rss data
d = feedparser.parse('http://ax.phobos.apple.com.edgesuite.net/WebObjects/MZStore.woa/wpa/MRSS/topalbums/sf=143444/limit=100/rss.xml')

# connect to the database
conn = lite.connect('music_backlog.db')

# loop through the entries and add them to the backlog
for i in d.entries:
	# clean up some on the name elements
	album = re.sub("[\(\[].*?[\)\]]", "", i.itms_artist)
	album = album.strip()

	# ignore various artists, don't want those
	if i.itms_artist <> 'Various Artists':
		# look for the record in the backlog
		with conn:
			cur = conn.cursor()
			cur.execute("SELECT COUNT(*) FROM BACKLOG WHERE artist = ? AND album = ?", (i.itms_artist, album))       
			result=cur.fetchone()
		
		# if the rowcount is -1 then no records found and we should at it to the backlog
		if result[0] == 0:
			with conn:
				cur = conn.cursor()
				cur.execute("INSERT INTO BACKLOG SELECT current_timestamp, ?, ?, 0", (i.itms_artist, album))       
				print "Added " + album + " by " + i.itms_artist + " to backlog"
		else:
			print "Not added " + album + " by " + i.itms_artist + " to backlog as is already in there"
	else:
		print "Not added " + album + " by " + i.itms_artist + " to backlog as is a various"
	

