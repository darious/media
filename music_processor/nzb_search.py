#!/usr/bin/python

# ---------------------------------------------------------------------------------------
# Music Processor
#
# Search for NZBs on nzbs.org that are in the backlog
#
# Pulls the top 40 from itunes and maintains the backlog of stuff to download
#
# Version	Date		Descripiton
# 1.00		2016-04-16	Initial Version
# ---------------------------------------------------------------------------------------

import feedparser

# create the url to use
# constants
nzburl = 'https://nzbs.org/api'
nzbapikey = '48b1c75e7885d8d27ee57e45f1432e0f'

# test data
artist = "Kings of Leon"
artist = "Coldplay"
album = "Only by the Night"

searchurl = nzburl + "?t=music&artist=" + artist + "&cat=3040&minsize=100&password=0&apikey=" + nzbapikey

print searchurl

d = feedparser.parse(searchurl)

print d

for i in d.entries:
	print "Found " + i.title + " published " 

