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

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

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
		opts, args = getopt.getopt(sys.argv[1:],"b:t:a:h:r:f:",["TargetBitrate=","VidFileIn="])
	except getopt.GetoptError:
		print 'recode.py -b <Target Bitrate Type> -t <test duration to encode> -a <how to process the audio> -h <new or backup> -r <width to rescal to, e.g. 1280> -f <Input Video File>'
		sys.exit(2)

	TargetBitrate=""
	TestDuration=""
	VidFileIn=""
	AudioType="one"
	fileProcess="new"
	RescaleWidth = None
	
	for opt, arg in opts:    
		if opt in ("-b", "--bitrate"):
			TargetBitrate = arg
			
		if opt in ("-f", "--filein"):
			VidFileIn = arg
			
		if opt in ("-t", "--test"):
			TestDuration = arg
			
		if opt in ("-a", "--audio"):
			AudioType = arg
			if AudioType not in ("pass", "all", "one", "best"):
				AudioType = "one"
				
		if opt in ("-h"):
			fileProcess = arg
			
		if opt in ("-r"):
			RescaleWidth = arg
	
	# check for missing values
	if TargetBitrate=="" or VidFileIn=="":
		print 'recode.py -b <Target Bitrate Type> -t <test duration to encode> -f <Input Video File>'
		sys.exit(2)
	
	return (TargetBitrate, TestDuration, AudioType, fileProcess, RescaleWidth, VidFileIn)


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
		codec = ['-c:v:0', 'copy', '-an']
	if Type == 'A':
		codec = ['-c:a:0', 'copy', '-vn']
		
	ffCommand = ['ffmpeg_g.exe',  '-i',  VidFileIn] + codec + [VidFileTemp]
	
	# show the command
	print bcolors.OKBLUE + 'ffmpeg command : %r' % ' '.join(ffCommand) + bcolors.ENDC

	# and run it
	subprocess.call(ffCommand)
	
	# read the data
	media_info = MediaInfo.parse(VidFileTemp)

	for track in media_info.tracks:
		if track.track_type == 'General':
			print bcolors.OKBLUE + "Temp bitrate is %s" % (track.overall_bit_rate) + bcolors.ENDC
			if track.overall_bit_rate is not None:
				tmpBitrate = track.overall_bit_rate
			else:
				print bcolors.FAIL + "Still 0 Bitrate." + bcolors.ENDC
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
			try:
				tmpBitRate = int(track.bit_rate)
			except:
				tmpBitRate = 0
			
			if track.frame_rate_mode == 'VFR':
				track.frame_rate = 25
			if (track.bit_rate is None or track.bit_rate == "0" or tmpBitRate == 0):
				if TargetBitrate <> "pass":
					print bcolors.WARNING + "Video Got a 0 Bitrate so extracting the data to new file." + bcolors.ENDC
					track.bit_rate = ZeroBitrate(VidFileIn, 0, 'V')
				else:
					track.bit_rate = 10000
			if track.duration is None:
				track.duration = 0
			VideoInfo.append ({ 'ID': track.track_id, 'Format': track.format, 'BitRate': float(track.bit_rate)/1000, 'Width': track.width, 'Height': track.height, 'FrameRate': track.frame_rate, 'Duration': datetime.timedelta(milliseconds=float(track.duration)), 'ScanType': track.scan_type })
		elif track.track_type == 'Audio':
			if track.bit_rate is None:
				print bcolors.WARNING + "Audio Got a 0 Bitrate so extracting the data to new file." + bcolors.ENDC
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
		print bcolors.WARNING + "New Bitrate lower than acceptable so using default low value of %d." % LowBitRate + bcolors.ENDC
		NewBitrate = LowBitRate
	
	# check its lower than the source
	if NewBitrate >= BitRate:
		print bcolors.WARNING + "New Bitrate lower than the source so using source bitrate of %d." % BitRate + bcolors.ENDC
		NewBitrate = BitRate
		
	return (NewBitrate)


def RescaleCalc(Width, Height):
	if int(RescaleWidth) < int(Width):
		NewWidth = RescaleWidth
		HewHeight = int(round((int(RescaleWidth) * int(Height)) / int(Width), 0))
		print bcolors.WARNING + "Asked to rescale, will go from %sx%s to %sx%s" % (Width, Height, NewWidth, HewHeight) + bcolors.ENDC
	else:
		NewWidth = Width
		HewHeight = Height
		print bcolors.WARNING + "Asked to rescale, but New Width of %s is greater than start Width of %s so not changing" % (RescaleWidth, Width) + bcolors.ENDC
	return (NewWidth, HewHeight)
	
	
def VideoParameters(VideoInfo):
# work out all the video encoding parameters
	
	# if we've been asked to pass the video through then just do that
	if TargetBitrate == "pass":
		ffVid = ['-c:v', 'copy']
		print bcolors.OKGREEN + "Video : %s at %dbps %s long and will be passed through" % (VideoInfo[0]['Format'], VideoInfo[0]['BitRate'], VideoInfo[0]['Duration']) + bcolors.ENDC
	else:
		# should we change the framerate?
		VideoInfo[0]['FrameRate'] = float(VideoInfo[0]['FrameRate'])
		if VideoInfo[0]['FrameRate'] == 50:
			TargetFrameRate = 25
		elif VideoInfo[0]['FrameRate'] == 59.94:
			TargetFrameRate = 29.97
		elif VideoInfo[0]['FrameRate'] == 59.88:
			TargetFrameRate = 29.94
		elif VideoInfo[0]['FrameRate'] == 59.940:
			TargetFrameRate = 29.97
		elif VideoInfo[0]['FrameRate'] == 60:
			TargetFrameRate = 30
		elif VideoInfo[0]['FrameRate'] == 100:
			TargetFrameRate = 25
		elif VideoInfo[0]['FrameRate'] == 24.97:
			TargetFrameRate = 25
		else:
			TargetFrameRate = VideoInfo[0]['FrameRate']
		
		if TargetFrameRate <> VideoInfo[0]['FrameRate']:
			Resample = ['-r', str(TargetFrameRate)]
			print bcolors.WARNING + "Got a framerate of %s So resampling with -r %s." % (VideoInfo[0]['FrameRate'], TargetFrameRate) + bcolors.ENDC
		else:
			Resample = []
			print bcolors.WARNING + "Got a framerate of %s So no change required" % VideoInfo[0]['FrameRate'] + bcolors.ENDC
			
		# Should we deinterlace?
		if VideoInfo[0]['ScanType'] == 'Interlaced':
			Deinterlace = ['-deinterlace']
			print bcolors.WARNING + "Got an interlaced file so will deinterlace" + bcolors.ENDC
		else:
			Deinterlace= []
			print bcolors.WARNING + "Got a progressive file so no change required" + bcolors.ENDC
		
		NewBitrate = BitRateCalc(VideoInfo[0]['Width'], VideoInfo[0]['Height'], TargetFrameRate, VideoInfo[0]['BitRate'])
		
		# create the bits of the ffmpeg command for the video
		ffVid = ['-c:v', 'nvenc_hevc', '-b:v', str(NewBitrate)+'k', '-maxrate', '20000k', '-preset', 'hq']

		ffVid = ffVid + Resample + Deinterlace
		
		print bcolors.OKGREEN + "Video : %s %sx%s at %dk %s long new HEVC file will be bitrate (%s) %dk" % (VideoInfo[0]['Format'], VideoInfo[0]['Width'], VideoInfo[0]['Height'], VideoInfo[0]['BitRate'], VideoInfo[0]['Duration'], TargetBitrate, NewBitrate) + bcolors.ENDC
	
	mapping = ['-map', '0:'+str(VideoInfo[0]['ID'] - 1)]
	
	return mapping, ffVid


def AudioParameters(AudioInfo):
# work out what to do with the audio
	ffAud=[]
	mapping=[]
	counter = 0
	format = 'mp4'
	
	# loop through all the audio tracks
	for track in AudioInfo:
		# fix the meta data if required
		if track['Channels'] == '8 / 6':
			track['Channels'] = 8
		if track['Channels'] == '7 / 6':
			track['Channels'] = 7
		try:
			track['BitRate']=int(track['BitRate'])
		except:
			track['BitRate']=int(384000)
	
	# work out which is the best track
	bestTrack=0
	channels=int(AudioInfo[0]['Channels'])
	
	for track in AudioInfo:
		if int(track['Channels']) > channels:
			bestTrack=track['ID'] - 1
			counter+=1

	print bcolors.OKGREEN + "Audio : Best track is :%s %sk %s channel %s" % (str(AudioInfo[bestTrack]['ID'] - 1), AudioInfo[bestTrack]['BitRate']/1000, AudioInfo[bestTrack]['Channels'], AudioInfo[counter]['Format']) + bcolors.ENDC
	
	# now figure out what to do with all the tracks
	if AudioType == "one":
		mapping = ['-map', '0:' + str(AudioInfo[bestTrack]['ID']-1)]
		if AudioInfo[bestTrack]['Channels'] < 6:
			ffAud = ['-c:a:'+ str(bestTrack), 'libfdk_aac', '-b:a:'+ str(bestTrack), '128k', '-ar:'+ str(bestTrack), '48000']
			print bcolors.OKGREEN + "Audio : Keeping track :%s %sk %s channel %s, will recode to 128k AAC" % (str(AudioInfo[bestTrack]['ID'] - 1), AudioInfo[bestTrack]['BitRate']/1000, AudioInfo[bestTrack]['Channels'], AudioInfo[bestTrack]['Format']) + bcolors.ENDC
		elif AudioInfo[bestTrack]['Channels'] >= 6:
			ffAud = ['-c:a:'+ str(bestTrack), 'ac3', '-b:a:'+ str(bestTrack), '384k', '-ar:'+ str(bestTrack), '48000']
			format = 'mkv'
			print bcolors.OKGREEN + "Audio : Keeping track :%s %sk %s channel %s, will recode to 384k AC3" % (str(AudioInfo[bestTrack]['ID'] - 1), AudioInfo[bestTrack]['BitRate']/1000, AudioInfo[bestTrack]['Channels'], AudioInfo[bestTrack]['Format']) + bcolors.ENDC
	
	# for the others we need to look at all the tracks
	counter = 0
	if AudioType in ("best", "pass", "all"):
		format = 'mkv'
		for track in AudioInfo:
			mapping = mapping + ['-map', '0:' + str(track['ID']-1)]
			if (counter == bestTrack and AudioType == "best") or AudioType == "pass":
				ffAud = ffAud + ['-c:a:'+ str(counter), 'copy']
				print bcolors.OKGREEN + "Audio : Keeping track %s %sk %s channel %s and passing it through" % (str(AudioInfo[counter]['ID'] - 1), AudioInfo[counter]['BitRate']/1000, AudioInfo[counter]['Channels'], AudioInfo[counter]['Format']) + bcolors.ENDC
			else:
				if track['Channels'] == 2:
					ffAud = ffAud + ['-c:a:'+ str(counter), 'libfdk_aac', '-b:a:'+ str(counter), '128k', '-ar:'+ str(counter), '48000']
					print bcolors.OKGREEN + "Audio : Keeping track :%s %sk %s channel %s, will recode to 128k AAC" % (str(AudioInfo[counter]['ID'] - 1), AudioInfo[counter]['BitRate']/1000, AudioInfo[counter]['Channels'], AudioInfo[counter]['Format']) + bcolors.ENDC
				elif track['Channels'] >= 6:
					ffAud = ffAud + ['-c:a:'+ str(counter), 'ac3', '-b:a:'+ str(counter), '384k', '-ar:'+ str(counter), '48000']
					format = 'mkv'
					print bcolors.OKGREEN + "Audio : Keeping track :%s %sk %s channel %s, will recode to 384k AC3" % (str(AudioInfo[counter]['ID'] - 1), AudioInfo[counter]['BitRate']/1000, AudioInfo[counter]['Channels'], AudioInfo[counter]['Format']) + bcolors.ENDC
			counter += 1
	
	return (mapping, ffAud, format)


def SubParameters(SubInfo):
	ffSub=[]
	mapping=[]
	counter = 0
	format = 'mp4'
	
	for track in SubInfo:
		if track['Language'] == 'en' or track['Forced'] == 'Yes':
		#or track['Default'] == 'Yes' 
		# subtitle is english, default or forced, so we'll keep it
			mapping = mapping + ['-map', '0:' + str(track['ID'] - 1)]
			if track['Format'] in ("ASS", "UTF-8", "SSA"):
			# a format we can recode so we will
				ffSub = ffSub + ['-c:s:'+str(counter), 'ass']
				format = 'mkv'
				print bcolors.OKGREEN + "SubTitle : Keeping track %s %s %s, will recode to Advanced SubStation Alpha" % (str(track['ID'] - 1), track['Language'], track['Format']) + bcolors.ENDC
			if track['Format'] in ("PGS", "VobSub"):
			# a format we can't code, so we'll just pass it through
				ffSub = ffSub + ['-c:s:'+str(counter), 'copy']
				format = 'mkv'
				print bcolors.OKGREEN + "SubTitle : Keeping track %s %s %s, will be passed through unchanged" % (str(track['ID'] - 1), track['Language'], track['Format']) + bcolors.ENDC
		counter += 1
			
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
			
		print bcolors.OKBLUE + "backing up file" + bcolors.ENDC
		copy_large_file(VidFileIn, VidFileBackup)
		os.remove(VidFileIn)
		print bcolors.OKBLUE + "backup complete" + bcolors.ENDC
		# work out the in and out filenames
		VidFileOutName, VidFileOutExt = ntpath.splitext(VidFileIn)
		VidFileOut = VidFileOutName + '.' + format
		if os.name in ("posix"):
		# if in cygwin then convert the filepath format
			VidFileIn = posix2win(VidFileBackup)
		else:
			VidFileIn = VidFileBackup
		
	if fileProcess == 'new':
		VidFileIn = VidFileIn
		VidFileOutName, VidFileOutExt = ntpath.splitext(VidFileIn)
		VidFileOut = VidFileOutName + '_new' + '.' + format
	
	return (VidFileIn, VidFileOut)


def RecodeFile (VidFileIn):
	print bcolors.OKBLUE + 'Processing File :%s' %(VidFileIn) + bcolors.ENDC
	
	if os.name in ("posix"):
	# if in cygwin then convert the filepath format
		VidFileInWin = posix2win(VidFileIn)
	else:
		VidFileInWin = VidFileIn
	
	# get the info all all the tracks in the file
	VideoInfo, AudioInfo, SubInfo = GetVideoInfo(VidFileInWin)

	# Check work is required
	if VideoInfo[0]['Format'] == 'HEVC':
		print bcolors.FAIL + "Video already in HEVC, nothing to do." + bcolors.ENDC
	else:
		# have we been asked to rescale
		ffRescale=[]
		if RescaleWidth <> None:
			NewWidth, NewHeight = RescaleCalc(VideoInfo[0]['Width'], VideoInfo[0]['Height'])
			VideoInfo[0]['Height'] = NewHeight
			VideoInfo[0]['Width'] = NewWidth
			ffRescale = ['-vf', 'scale='+str(NewWidth)+':'+str(NewHeight)]
				
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
		ffCommand = ffCommand + mapping + ffVid + ffRescale + ffAud + ffSub + [VidFileOut]

		# show the command
		print bcolors.OKBLUE + 'ffmpeg command : %r' % ' '.join(ffCommand) + bcolors.ENDC

		# and run it
		subprocess.call(ffCommand)
	

def RecodeFolder (VidFileIn):
	print bcolors.OKBLUE + 'Processing Folder :%s' %(VidFileIn) + bcolors.ENDC
	Files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(VidFileIn) for f in filenames if os.path.splitext(f)[1] in ('.mp4', '.mkv', '.m4v', '.avi', '.mov', '.flv', '.wmv')]
	Files.sort()
	for File in Files:
		RecodeFile(File)

		
# starts here
# constants
TmpDir = '/tmp/vidtemp/'
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
TargetBitrate, TestDuration, AudioType, fileProcess, RescaleWidth, VidFileIn = ReadInputVariables()

# check the TargetBitrate makes sense
try:
	TargetBitrate = int(TargetBitrate)
	print bcolors.OKBLUE + "Numeric bitrate (%d) provided and will be used" % TargetBitrate + bcolors.ENDC
except:
	if TargetBitrate not in ("calc", "calc2", "calc3", "half", "pass"):
		print bcolors.FAIL + "Invalid target bitrate provided (%s) exiting." % TargetBitrate + bcolors.ENDC
		sys.exit(2)
	if TargetBitrate == 'half' and RescaleWidth <> None:
		print bcolors.FAIL + "Cannot rescale and half the bitrate." + bcolors.ENDC
		sys.exit(2)

print bcolors.OKBLUE + "Will encode %s using bitrate %s ,will process the audio as %s and will use a %s file" \
	% (VidFileIn, TargetBitrate, AudioType, fileProcess) + bcolors.ENDC


# have we been given a file or a folder
if os.path.isfile(VidFileIn) == True:
	RecodeFile(VidFileIn)
elif os.path.isdir(VidFileIn) == True:
	RecodeFolder(VidFileIn)
else:
	print "Error not supplied with a valid file or folder"
	




