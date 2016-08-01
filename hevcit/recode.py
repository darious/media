#!/usr/bin/python

#
# ----------------------------------------------------- #
# recode video                                          #
# ----------------------------------------------------- #
# Ver	Date		Author		Comment                 #
# 0.01	2016-07-30	C Cook		Initial Version         #
# ----------------------------------------------------- #

# imports
import sys
import os
import shutil
import getopt
from pymediainfo import MediaInfo
from ctypes import cdll, c_void_p, c_int32, cast, c_char_p, c_wchar_p
from sys import version_info
import time
import datetime
import subprocess
import base64
import ntpath
from subprocess import Popen, PIPE, STDOUT
import select

def copy_large_file(src, dst):
    '''
    Copy a large file showing progress.
    '''
    print('copying "{}" --> "{}"'.format(src, dst))
    if os.path.exists(src) is False:
        print('ERROR: file does not exist: "{}"'.format(src))
        sys.exit(1)
    if os.path.exists(dst) is True:
        os.remove(dst)
    if os.path.exists(dst) is True:
        print('ERROR: file exists, cannot overwrite it: "{}"'.format(dst))
        sys.exit(1)

    # Start the timer and get the size.
    start = time.time()
    size = os.stat(src).st_size
    print('{} bytes'.format(size))

    # Adjust the chunk size to the input size.
    divisor = 10000  # .1%
    chunk_size = size / divisor
    while chunk_size == 0 and divisor > 0:
        divisor /= 10
        chunk_size = size / divisor
    print('chunk size is {}'.format(chunk_size))

    # Copy.
    try:
        with open(src, 'rb') as ifp:
            with open(dst, 'wb') as ofp:
                copied = 0  # bytes
                chunk = ifp.read(chunk_size)
                while chunk:
                    # Write and calculate how much has been written so far.
                    ofp.write(chunk)
                    copied += len(chunk)
                    per = 100. * float(copied) / float(size)

                    # Calculate the estimated time remaining.
                    elapsed = time.time() - start  # elapsed so far
                    avg_time_per_byte = elapsed / float(copied)
                    remaining = size - copied
                    est = remaining * avg_time_per_byte
                    est1 = size * avg_time_per_byte
                    eststr = 'rem={:>.1f}s, tot={:>.1f}s'.format(est, est1)

                    # Write out the status.
                    sys.stdout.write('\r\033[K{:>6.1f}%  {}  {} --> {} '.format(per, eststr, src, dst))
                    sys.stdout.flush()

                    # Read in the next chunk.
                    chunk = ifp.read(chunk_size)

    except IOError as obj:
        print('\nERROR: {}'.format(obj))
        sys.exit(1)

    sys.stdout.write('\r\033[K')  # clear to EOL
    elapsed = time.time() - start
    print('copied "{}" --> "{}" in {:>.1f}s"'.format(src, dst, elapsed))
	
def win2posix(path):
# convert from windows to cygwin format
    result = cygwin_create_path(CCP_WIN_W_TO_POSIX,xunicode(path))
    if result is None:
        raise Exception("cygwin_create_path failed")
    value = cast(result,c_char_p).value
    free(result)
    return value

def posix2win(path):
# convert from cygwin to windows format
    result = cygwin_create_path(CCP_POSIX_TO_WIN_W,str(path))
    if result is None:
        raise Exception("cygwin_create_path failed")
    value = cast(result,c_wchar_p).value
    free(result)
    return value
	
def ReadInputVariables():
# read in the input arguments
	try:
		opts, args = getopt.getopt(sys.argv[1:],"b:t:a:h:f:",["TargetBitrate=","VidFileIn="])
	except getopt.GetoptError:
		print 'recode.py -b <Target Bitrate Type> -t <test duration to encode> -a <how to process the audio> -h <new or backup> -f <Input Video File>'
		sys.exit(2)

	TargetBitrate=""
	TestDuration=""
	VidFileIn=""
	AudioType="one"
	fileProcess="new"
	for opt, arg in opts:    
		if opt in ("-b", "--bitrate"):
			TargetBitrate = arg
			
		if opt in ("-f", "--filein"):
			VidFileIn = arg
			
		if opt in ("-t", "--test"):
			TestDuration = arg
			
		if opt in ("-a", "--audio"):
			AudioType = arg
			if AudioType not in ("pass", "all", "one"):
				AudioType = "one"
				
		if opt in ("-h"):
			fileProcess = arg
	
	# check for missing values
	if TargetBitrate=="" or VidFileIn=="":
		print 'recode.py -b <Target Bitrate Type> -t <test duration to encode> -f <Input Video File>'
		sys.exit(2)
	
	return (TargetBitrate, TestDuration, AudioType, fileProcess, VidFileIn)


def ZeroBitrate(VidFileIn, TrackID, Type):
# deal with a 0 bitrate and work out what it is
	tmpRandom = base64.b64encode(os.urandom(12), '__')

	if os.name in ("posix"):
	# if in cygwin then convert the filepath format
		VidFileTemp = posix2win(TmpDir+"zerobitrate%s.mkv" % tmpRandom	)
	else:
		VidFileTemp = TmpDir+"zerobitrate%s.mkv" % tmpRandom
	
	# create a new file with just this stream
	if Type == 'V':
		codec = ['-c:v:'+str(TrackID), 'copy', '-an']
	if Type == 'A':
		codec = ['-c:a:0', 'copy', '-vn']
		
	ffCommand = ['ffmpeg_g.exe',  '-i',  VidFileIn, '-map', '0:' + str(TrackID)] + codec + [VidFileTemp]
	
	# show the command
	print 'ffmpeg command : %r' % ' '.join(ffCommand)

	# and run it
	subprocess.call(ffCommand)
	
	# read the data
	media_info = MediaInfo.parse(VidFileTemp)

	for track in media_info.tracks:
		if track.track_type == 'General':
			print "Temp bitrate is %s" % (track.overall_bit_rate)
			if track.overall_bit_rate is not None:
				tmpBitrate = track.overall_bit_rate
			else:
				print "Still 0 Bitrate."
				sys.exit(2)
	
	# drop the temp file
	try:
		os.remove(VidFileTemp)
	except OSError:
		pass
		
	return tmpBitrate

	
	
def GetVideoInfo(VidFileIn):
# get information about the given video file
	media_info = MediaInfo.parse(VidFileIn)
	VideoInfo = []
	AudioInfo = []
	SubInfo = []
	
	for track in media_info.tracks:
		if track.track_type == 'Video':
			if track.frame_rate_mode == 'VFR':
				track.frame_rate = 25
			if track.bit_rate is None:
				print "Video Got a 0 Bitrate so extracting the data to new file."
				track.bit_rate = ZeroBitrate(VidFileIn, 0, 'V')
			VideoInfo.append ({ 'ID': track.track_id, 'Format': track.format, 'BitRate': round(int(track.bit_rate) / 1000, 0), 'Width': track.width, 'Height': track.height, 'FrameRate': track.frame_rate, 'Duration': track.duration, 'ScanType': track.scan_type })
		elif track.track_type == 'Audio':
			if track.bit_rate is None:
				print "Audio Got a 0 Bitrate so extracting the data to new file."
				track.bit_rate = ZeroBitrate(VidFileIn, int(track.track_id) - 1, 'A')
			AudioInfo.append ({ 'ID': track.track_id, 'Format': track.format, 'BitRate': track.bit_rate, 'Channels': track.channel_s })
		elif track.track_type == 'Text':
			SubInfo.append ({ 'ID': track.track_id, 'Format': track.format, 'Language': track.language, 'Default': track.default, 'Forced': track.forced })

	return (VideoInfo, AudioInfo, SubInfo)

	
def BitRateCalc(Width, Height, FrameRate, BitRate):
# Calculate the bitrate based on the request type

	if TargetBitrate == "calc":
		NewBitrate = int(round((((int(Width) * int(Height) * float(FrameRate)) / 1000000) + 11) * 37, 0))
	elif TargetBitrate == "calc2":
		NewBitrate = int(round((((int(Width) * int(Height) * float(FrameRate)) / 1000000) + 11) * 83, 0))
	elif TargetBitrate == "calc3":
		NewBitrate = int(round((((int(Width) * int(Height) * float(FrameRate)) / 1000000) + 11) * 132, 0))
	elif TargetBitrate == "half":
		NewBitrate = int(round(float(BitRate) / 2))
	else:
		NewBitrate = int(TargetBitrate)
	
	# check the calculated bit is ok
	if NewBitrate < LowBitRate:
		print "New Bitrate lower than acceptable so using default low value of %d." % LowBitRate
		NewBitrate = LowBitRate
	
	# check its lower than the source
	if NewBitrate > BitRate:
		print "New Bitrate lower than the source so using source bitrate of %d." % BitRate
		NewBitrate = BitRate
		
	return (NewBitrate)

	
def VideoParameters(VideoInfo):
# work out all the video encoding parameters
	
	# should we change the framerate?
	if VideoInfo[0]['FrameRate'] == 50:
		TargetFrameRate = 25
	elif VideoInfo[0]['FrameRate'] == 59.94:
		TargetFrameRate = 29.97
	elif VideoInfo[0]['FrameRate'] == 59.88:
		TargetFrameRate = 29.94
	elif VideoInfo[0]['FrameRate'] == 60:
		TargetFrameRate = 30
	elif VideoInfo[0]['FrameRate'] == 100:
		TargetFrameRate = 25
	elif VideoInfo[0]['FrameRate'] == 24.97:
		TargetFrameRate = 25
	else:
		TargetFrameRate = VideoInfo[0]['FrameRate']
	
	if TargetFrameRate <> VideoInfo[0]['FrameRate']:
		Resample = "-r %d" % TargetFrameRate
		print "Got a framerate of %s So resampling with %s." % (VideoInfo[0]['FrameRate'], Resample)
	else:
		Resample = ""
		print "Got a framerate of %s So no change required" % VideoInfo[0]['FrameRate']
		
	# Should we deinterlace?
	if VideoInfo[0]['ScanType'] == 'Interlaced':
		Deinterlace = '-deinterlace'
		print "Got an interlaced file so will deinterlace"
	else:
		Deinterlace= ''
		print "Got a progressive file so no change required"
	
	NewBitrate = BitRateCalc(VideoInfo[0]['Width'], VideoInfo[0]['Height'], TargetFrameRate, VideoInfo[0]['BitRate'])
	
	# create the bits of the ffmpeg command for the video
	ffVid = ['-c:v', 'nvenc_hevc', '-b:v', str(NewBitrate)+'k', '-maxrate', '20000k', '-preset', 'hq']

	if Resample <> "":
		ffVid = ffVid + [Resample]
	
	if Deinterlace <> "":
		ffVid = ffVid + [Deinterlace]
	
	mapping = ['-map', '0:'+str(VideoInfo[0]['ID'] - 1)]
	
	print "Video : %s at %dk %s long new HEVC file will be bitrate (%s) %dk" % (VideoInfo[0]['Format'], VideoInfo[0]['BitRate'], VideoInfo[0]['Duration'], TargetBitrate, NewBitrate)
	
	return mapping, ffVid


def AudioParameters(AudioInfo):
# work out what to do with the audio
	ffAud=[]
	mapping=[]
	counter = 0
	format = 'mp4'
	
	if AudioType == "pass":
	# pass though all the audio tracks
		for track in AudioInfo:
			if track['Channels'] == '8 / 6':
				track['Channels'] = 8
			mapping = mapping + ['-map', '0:' + str(track['ID'] - 1)]
			ffAud = ffAud + ['-c:a:'+ str(counter), 'copy']
			if track['Format'] <> 'AAC':
				format = 'mkv'
			print "Audio : Keeping track %s %sk %s, will pass through unchanged" % (str(track['ID'] - 1), int(track['BitRate']) / 1000, track['Format'])
			counter =+ 1
	
	if AudioType == "all":
	# Keep all the tracks but recode to the best formats for each
		for track in AudioInfo:
			if track['Channels'] == '8 / 6':
				track['Channels'] = 8
			mapping = mapping + ['-map', '0:' + str(track['ID'] - 1)]
			if track['Channels'] == 2:
				ffAud = ffAud + ['-c:a:'+ str(counter), 'libfdk_aac', '-b:a:'+ str(counter), '128k', '-ar:'+ str(counter), '48000', '-metadata:s:a:'+ str(counter), 'title="English AAC 128k"']
				print "Audio : Keeping track %s %sk %s, will recode to 128k AAC" % (str(track['ID'] - 1), int(track['BitRate']) / 1000, track['Format'])
			elif track['Channels'] >= 6:
				ffAud = ffAud + ['-c:a:'+ str(counter), 'ac3', '-b:a:'+ str(counter), '384k', '-ar:'+ str(counter), '48000', '-metadata:s:a:'+ str(counter), 'title="English AC3 384k"']
				format = 'mkv'
				print "Audio : Keeping track %s %sk %s, will recode to 384k AC3" % (str(track['ID'] - 1), int(track['BitRate']) / 1000, track['Format'])
			counter =+ 1
	
	if AudioType == "one":
	# pick the best track and encode to the best format
		channels=0
		for track in AudioInfo:
			if track['Channels'] == '8 / 6':
				track['Channels'] = 8
			if int(track['Channels']) > channels:
				mapping = ['-map', '0:' + str(track['ID'] - 1)]
				if track['Channels'] == 2:
					ffAud + ['-c:a:'+ str(counter), 'libfdk_aac', '-b:a:'+ str(counter), '128k', '-ar:'+ str(counter), '48000', '-metadata:s:a:'+ str(counter), 'title="English AAC 128k"']
					print "Audio : Keeping track %s %sk %s, will recode to 128k AAC" % (str(track['ID'] - 1), int(track['BitRate']) / 1000, track['Format'])
				elif track['Channels'] >= 6:
					ffAud = ffAud + ['-c:a:'+ str(counter), 'ac3', '-b:a:'+ str(counter), '384k', '-ar:'+ str(counter), '48000', '-metadata:s:a:'+ str(counter), 'title="English AC3 384k"']
					format = 'mkv'
					print "Audio : Keeping track %s %sk %s, will recode to 384k AC3" % (str(track['ID'] - 1), int(track['BitRate']) / 1000, track['Format'])
				channels=track['Channels']
				counter =+ 1

	return (mapping, ffAud, format)


def SubParameters(SubInfo):
	ffSub=[]
	mapping=[]
	counter = 0
	format = 'mp4'
	
	for track in SubInfo:
		#print track['Format'], track['Language'], track['Default'], track['Forced']
		if track['Language'] == 'en' or track['Default'] == 'Yes' or track['Forced'] == 'Yes':
		# subtitle is english, default or forced, so we'll keep it
			mapping = ['-map', '0:' + str(track['ID'] - 1)]
			if track['Format'] in ("ASS", "UTF-8", "SSA"):
			# a format we can recode so we will
				ffSub = ffSub + ['-c:s:'+str(counter), 'ass']
				format = 'mkv'
				print "SubTitle : Keeping track %s %s %s, will recode to Advanced SubStation Alpha" % (str(track['ID'] - 1), track['Language'], track['Format'])
			if track['Format'] in ("PGS", "VobSub"):
			# a format we can't code, so we'll just pass it through
				ffSub = ffSub + ['-c:s:'+str(counter), 'copy']
				format = 'mkv'
				print "SubTitle : Keeping track %s %s %s, will be passed through unchanged" % (str(track['ID'] - 1), track['Language'], track['Format'])
		counter =+ 1
		
	return (mapping, ffSub, format)


def FileNameCalc(VidFileIn, fileProcess, format):
# work out what to do with the files and calclate the names to use
	
	if fileProcess == 'backup':
	# then backup the file
		VidFileBackup = BackupLocation + ntpath.basename(VidFileIn)
		try:
			os.remove(VidFileBackup)
		except OSError:
			pass
			
		print "backing up file"
		print VidFileBackup
		copy_large_file(VidFileIn, VidFileBackup)
		os.remove(VidFileIn)
		print "backup complete"
		# work out the in and out filenames
		VidFileOutName, VidFileOutExt = ntpath.splitext(VidFileIn)
		VidFileOut = VidFileOutName + '.' + format
		VidFileIn = VidFileBackup
		
	if fileProcess == 'new':
		VidFileIn = VidFileIn
		VidFileOutName, VidFileOutExt = ntpath.splitext(VidFileIn)
		VidFileOut = VidFileOutName + '_new' + '.' + format
	
	return (VidFileIn, VidFileOut)
	
# starts here
# constants
TmpDir = '/tmp/'
LowBitRate = 500
BackupLocation = "//192.168.0.206/share/backup/"

TargetBitrate = ""
TestDuration = ""
AudioType = ""
VidFileIn = ""

xunicode = str if version_info[0] > 2 else eval("unicode")

cygwin = cdll.LoadLibrary("cygwin1.dll")
cygwin_create_path = cygwin.cygwin_create_path
cygwin_create_path.restype = c_void_p
cygwin_create_path.argtypes = [c_int32, c_void_p]

free = cygwin.free
free.restype = None
free.argtypes = [c_void_p]

CCP_POSIX_TO_WIN_A = 0
CCP_POSIX_TO_WIN_W = 1
CCP_WIN_A_TO_POSIX = 2
CCP_WIN_W_TO_POSIX = 3

# get the input values
TargetBitrate, TestDuration, AudioType, fileProcess, VidFileIn = ReadInputVariables()

# check the TargetBitrate makes sense
try:
	TargetBitrate = int(TargetBitrate)
	print "Numeric bitrate (%d) provided and will be used" % TargetBitrate
except:
	if TargetBitrate not in ("calc", "calc2", "calc3", "half"):
		print "Invalid target bitrate provided (%s) exiting." % TargetBitrate
		sys.exit(2)

print "Will encode %s using bitrate %s ,will process the audio as %s and will use a %s file" \
	% (VidFileIn, TargetBitrate, AudioType, fileProcess)

if os.name in ("posix"):
# if in cygwin then convert the filepath format
	VidFileInWin = posix2win(VidFileIn)
else:
	VidFileInWin = VidFileIn


# check the file exists



# get the info all all the tracks in the file
VideoInfo, AudioInfo, SubInfo = GetVideoInfo(VidFileInWin)

# Check work is required
if VideoInfo[0]['Format'] == 'HEVC':
	print "Video already in HEVC, nothing to do."
	sys.exit(2)

# work out what to do with the Video
mapVid, ffVid = VideoParameters(VideoInfo)

# work out what to do with the Audio
mapAud, ffAud, formatAud = AudioParameters(AudioInfo)

# work out what to do with the subtitles
mapSub, ffSub, formatSub= SubParameters(SubInfo)

# calculate the fileformat to use
if formatAud == 'mkv' or formatSub == 'mkv':
	format = 'mkv'
else:
	format = 'mp4'

# prep the filenames
VidFileIn, VidFileOut = FileNameCalc (VidFileInWin, fileProcess, format)


# calculate all the mappings
mapping = mapVid + mapAud + mapSub

# calcualte the metadata timestamp
DateTimeStr = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

# create the ffmpeg command
ffCommand = ['ffmpeg_g.exe', '-i'] + [VidFileIn]
if TestDuration <> "":
	ffCommand = ffCommand + ['-t', TestDuration]
ffCommand = ffCommand + mapping + ffVid + ffAud + ffSub + [VidFileOut]

# show the command
print 'ffmpeg command : %r' % ' '.join(ffCommand)

# and run it
subprocess.call(ffCommand)

#tmpRandom = base64.b64encode(os.urandom(12), '__')
#VidFileOutWin="testout_%s.mkv" % tmpRandom	