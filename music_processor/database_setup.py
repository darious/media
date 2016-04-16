#!/usr/bin/python

# ---------------------------------------------------------------------------------------
# Music Processor
#
# Database setup
#
# Sets up the database to store the backlog
#
# Version	Date		Descripiton
# 1.00		2016-04-16	Initial Version
# ---------------------------------------------------------------------------------------

# import libraies
import sqlite3 as lite
import sys

# create or connect to the database
conn=lite.connect('music_backlog.db')
print "Database created and opened succesfully"

# create the required tables (if they are not there)
with conn:
	cur = conn.cursor()    
	cur.execute("CREATE TABLE IF NOT EXISTS BACKLOG(create_ts TIMESTAMP, artist TEXT, album TEST, status INT)")

print "BACKLOG table created"


