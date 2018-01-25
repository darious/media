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

	helpstring = 'recode.py -b <Target Bitrate Type> -t <test duration to encode> -a <how to process the audio> -h <new or backup> -r <width to rescal to, e.g. 1280> -o Y <ignore the check that we have already coded> -f <Input Video File> -v <Video codec h264 or h265>'
	try:
		opts, args = getopt.getopt(sys.argv[1:],"b:t:a:h:r:f:o:v:p",["TargetBitrate=","VidFileIn="])
	except getopt.GetoptError:
		print helpstring
		sys.exit(2)

	TargetBitrate=""
	TestDuration=""
	VidFileIn=""
	AudioType="one"
	fileProcess="new"
	RescaleWidth = None
	VideoCodec = "h265"
	PrintMode = 0
	
	for opt, arg in opts:    
		if opt in ("-b", "--bitrate"):
			TargetBitrate = arg
			
		if opt in ("-f", "--filein"):
			VidFileIn = arg
			
		if opt in ("-t", "--test"):
			TestDuration = arg
			
		if opt in ("-a", "--audio"):
			AudioType = arg
			if AudioType not in ("passall", "all", "one", "passbest", "aac", "64k"):
				AudioType = "one"
				
		if opt in ("-h"):
			fileProcess = arg
			
		if opt in ("-r"):
			RescaleWidth = arg

		if opt in ("-v"):
			VideoCodec = arg
			if VideoCodec not in ("h264", "h265"):
				VideoCodec = "h265"
				
		if opt in ("-p", "--print"):
			PrintMode = 1
			fileProcess = "new"
	
	# check for missing values
	if TargetBitrate=="" or VidFileIn=="":
		print helpstring
		sys.exit(2)
	
	return (TargetBitrate, TestDuration, AudioType, fileProcess, RescaleWidth, VidFileIn, VideoCodec, PrintMode)


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
	AllInfo = []
	
	counter = - 1
	
	for track in media_info.tracks:
		if track.track_type in ('Audio', 'Video', 'Text'):
			counter += 1
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
			AllInfo.append ({ 'Type':'Video', 'ID': track.track_id, 'counter':counter })
		elif track.track_type == 'Audio':
			if track.bit_rate is None:
				print bcolors.WARNING + "Audio Got a 0 Bitrate so extracting the data to new file." + bcolors.ENDC
				track.bit_rate = ZeroBitrate(VidFileIn, int(track.track_id) - 1, 'A')
			AudioInfo.append ({ 'ID': track.track_id, 'Format': track.format, 'BitRate': track.bit_rate, 'Channels': track.channel_s })
			AllInfo.append ({ 'Type':'Audio', 'ID': track.track_id, 'counter':counter })
		elif track.track_type == 'Text':
			SubInfo.append ({ 'ID': track.track_id, 'Format': track.format, 'Language': track.language, 'Default': track.default, 'Forced': track.forced })
			AllInfo.append ({ 'Type':'Sub', 'ID': track.track_id, 'counter':counter })
	
	return (VideoInfo, AudioInfo, SubInfo, AllInfo)

	
def BitRateCalc(Width, Height, FrameRate, BitRate, VideoCodec):
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
	
	if VideoCodec == "h264":
		NewBitrate = NewBitrate * 2.5
	
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
	
	
def VideoParameters(VideoInfo, fileExt, VideoCodec, AllInfo):
# work out all the video encoding parameters
	
	NewBitrate = 0
	
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
		
		NewBitrate = BitRateCalc(VideoInfo[0]['Width'], VideoInfo[0]['Height'], TargetFrameRate, VideoInfo[0]['BitRate'], VideoCodec)
		
		# deal with the formats
		if VideoCodec == "h265":
			ffcodec = 'nvenc_hevc'
		elif VideoCodec == "h264":
			ffcodec = 'nvenc'
		
		# create the bits of the ffmpeg command for the video
		ffVid = ['-c:v', ffcodec, '-b:v', str(NewBitrate)+'k', '-maxrate', '20000k', '-preset', 'hq']

		ffVid = ffVid + Resample + Deinterlace
		
		print bcolors.OKGREEN + "Video : %s %sx%s at %dk %s long new %s file will be bitrate (%s) %dk" % (VideoInfo[0]['Format'], VideoInfo[0]['Width'], VideoInfo[0]['Height'], VideoInfo[0]['BitRate'], VideoInfo[0]['Duration'], VideoCodec, TargetBitrate, NewBitrate) + bcolors.ENDC
	
	# calculate the mapping
	for c in AllInfo:
		if c['ID'] == VideoInfo[0]['ID']:
			mapping = ['-map', '0:'+str(c['counter'])]
	
	return mapping, ffVid, NewBitrate


def AudioParameters(AudioInfo, fileExt, AllInfo):
# work out what to do with the audio
	ffAud=[]
	mapping=[]
	counter = -1
	format = 'mp4'
	AudioTypeTemp = AudioType
	
	if not AudioInfo:
		# no audio so say so and do nothing
		print bcolors.OKGREEN + "Audio : No audio tracks found." + bcolors.ENDC
	else:
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
		bestTrackID=AudioInfo[0]['ID']
		bestTrackIx=0
		channels=int(AudioInfo[0]['Channels'])
		
		for track in AudioInfo:
			counter+=1
			if int(track['Channels']) > channels:
				bestTrackID=AudioInfo[0]['ID']
				bestTrackIx=counter
		
		# recode one track
		if AudioTypeTemp in ("one", "aac", "64k"):
			if AudioInfo[bestTrackIx]['Channels'] >= 6:
				AudioBitrate = '384k'
				AudioCodec = 'ac3'
				format = 'mkv'
			else:
				AudioBitrate = '128k'
				AudioCodec = 'libfdk_aac'
				format = 'mp4'
			
			if AudioTypeTemp == '64k':
				AudioBitrate = '64k'
			
			ffAud = ['-c:a:0', AudioCodec, '-b:a:0', AudioBitrate, '-ar:0', '48000']
			
			# calculate the mapping
			for c in AllInfo:
				if c['ID'] == AudioInfo[bestTrackIx]['ID']:
					mapping = ['-map', '0:'+str(c['counter'])]
			
			print bcolors.OKGREEN + "Audio : Keeping track :%s %sk %s channel %s, will recode to %s AAC" % (str(AudioInfo[bestTrackIx]['ID'] - 1), AudioInfo[bestTrackIx]['BitRate']/1000, AudioInfo[bestTrackIx]['Channels'], AudioInfo[bestTrackIx]['Format'], AudioBitrate) + bcolors.ENDC
		
		# pass throught the best track
		elif AudioTypeTemp == "passbest":
			ffAud = ['-c:a:0', 'copy']
			format = 'mkv'
			
			# calculate the mapping
			for c in AllInfo:
				if c['ID'] == AudioInfo[bestTrackIx]['ID']:
					mapping = ['-map', '0:'+str(c['counter'])]
					
			print bcolors.OKGREEN + "Audio : Keeping track %s %sk %s channel %s and passing it through" % (str(AudioInfo[counter]['ID'] - 1), AudioInfo[counter]['BitRate']/1000, AudioInfo[counter]['Channels'], AudioInfo[counter]['Format']) + bcolors.ENDC
		
		elif AudioTypeTemp == "passall":
			counter = 0
			format = 'mkv'
			for track in AudioInfo:
				ffAud = ffAud + ['-c:a:'+ str(counter), 'copy']
				print bcolors.OKGREEN + "Audio : Keeping track %s %sk %s channel %s and passing it through" % (str(AudioInfo[counter]['ID'] - 1), AudioInfo[counter]['BitRate']/1000, AudioInfo[counter]['Channels'], AudioInfo[counter]['Format']) + bcolors.ENDC
				# calculate the mapping
				for c in AllInfo:
					if c['ID'] == AudioInfo[counter]['ID']:
						mapping += ['-map', '0:'+str(c['counter'])]
				counter += 1
				
		elif AudioTypeTemp == "all":
			counter = 0
			format = 'mkv'
			for track in AudioInfo:
				if AudioInfo[counter]['Channels'] >= 6:
					AudioBitrate = '384k'
					AudioCodec = 'ac3'
				else:
					AudioBitrate = '128k'
					AudioCodec = 'libfdk_aac'
					
				ffAud += ['-c:a:' + str(counter), AudioCodec, '-b:a:' + str(counter), AudioBitrate, '-ar:' + str(counter), '48000']
			
				print bcolors.OKGREEN + "Audio : Keeping track :%s %sk %s channel %s, will recode to %s AAC" % (str(AudioInfo[counter]['ID'] - 1), AudioInfo[counter]['BitRate']/1000, AudioInfo[counter]['Channels'], AudioInfo[counter]['Format'], AudioBitrate) + bcolors.ENDC
				# calculate the mapping
				for c in AllInfo:
					if c['ID'] == AudioInfo[counter]['ID']:
						mapping += ['-map', '0:'+str(c['counter'])]
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
		
	if fileProcess == 'replace':
		tmpRandom = base64.b64encode(os.urandom(12), '__')
		VidFileOutName, VidFileOutExt = ntpath.splitext(VidFileIn)
		VidFileOut = VidFileOutName + '.' + format
		VidFileIn = VidFileOutName + '_' + tmpRandom + VidFileOutExt
		# rename the file
		os.rename(VidFileOut, VidFileIn)
		print bcolors.OKBLUE + "File renamed from %s to %s" %(VidFileOut, VidFileIn) + bcolors.ENDC
	
	return (VidFileIn, VidFileOut)


def RecodeFile (VidFileIn):
	print bcolors.OKBLUE + 'Processing File :%s' %(VidFileIn) + bcolors.ENDC
	
	workreq=0
	workreas=''
	
	if os.name in ("posix"):
	# if in cygwin then convert the filepath format
		VidFileInWin = posix2win(VidFileIn)
	else:
		VidFileInWin = VidFileIn
		
	# stash the file extension
	fileExt = ntpath.splitext(VidFileInWin)[1]
	
	# get the info all all the tracks in the file
	VideoInfo, AudioInfo, SubInfo, AllInfo = GetVideoInfo(VidFileInWin)
	
	#debug
	#print VideoInfo
	#print AudioInfo
	#print SubInfo
	#print AllInfo

	# have we been asked to rescale
	OldWidth=VideoInfo[0]['Width']
	ffRescale=[]
	if RescaleWidth <> None and TargetBitrate <> "pass":
		NewWidth, NewHeight = RescaleCalc(VideoInfo[0]['Width'], VideoInfo[0]['Height'])
		VideoInfo[0]['Height'] = NewHeight
		VideoInfo[0]['Width'] = NewWidth
		ffRescale = ['-vf', 'scale='+str(NewWidth)+':'+str(NewHeight)]
	else:
		NewWidth=VideoInfo[0]['Width']
	
	# work out what to do with the Video
	mapVid, ffVid, NewBitrate = VideoParameters(VideoInfo, fileExt, VideoCodec, AllInfo)
	
	# Check work is required
	if VideoInfo[0]['Format'] <> 'HEVC':
		workreq=1
		workreas='video is not encoded in HEVC'
	elif int(NewWidth) < int(OldWidth):
		workreq=1
		workreas='video will be recaled to smaller size'
	elif (NewBitrate / VideoInfo[0]['BitRate']) < 0.93:
		workreq=1
		workreas='video will be encoded to a lower bitrate'
	
	if workreq==1:
		# work out what to do with the Audio
		mapAud, ffAud, formatAud = AudioParameters(AudioInfo, fileExt, AllInfo)

		print bcolors.WARNING + "Recoding as %s" % (workreas) + bcolors.ENDC
		
		# work out what to do with the subtitles
		# if an avi then skip this
		if fileExt == '.avi':
			print bcolors.OKBLUE + 'AVI file so skipping subs' + bcolors.ENDC
			mapSub = []
			ffSub = []
			formatSub = []
		else:		
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
		if PrintMode == 0:
			subprocess.call(ffCommand)
			# if we are replacing the file then remove the temp file now
			if fileProcess == 'replace':
				os.remove(VidFileIn)
		else:
			print bcolors.FAIL + "Print mode used no recode performed." + bcolors.ENDC
	else:
		print bcolors.FAIL + "No work required" + bcolors.ENDC
	

def RecodeFolder (VidFileIn):
	print bcolors.OKBLUE + 'Processing Folder :%s' %(VidFileIn) + bcolors.ENDC
	Files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(VidFileIn) for f in filenames if os.path.splitext(f)[1] in ('.mp4', '.mkv', '.m4v', '.avi', '.mov', '.flv', '.wmv', '.mpg', '.3gp')]
	Files.sort()
	#Files.sort(reverse=True)
	for File in Files:
		RecodeFile(File)

		
# starts here
# constants
TmpDir = '/tmp/vidtemp/'
LowBitRate = 500
#BackupLocation = "//192.168.0.206/share/backup/"
#BackupLocation = "//tank02/download/backup/"
BackupLocation = "//tank03/backup/video/"

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
TargetBitrate, TestDuration, AudioType, fileProcess, RescaleWidth, VidFileIn, VideoCodec, PrintMode = ReadInputVariables()

print PrintMode

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
	if VideoCodec == "h264" and TargetBitrate not in ("calc", "calc2", "calc3"):
		print bcolors.FAIL + "h264 can only be used with calc, calc2 and calc3." + bcolors.ENDC
		sys.exit(2)

print bcolors.OKBLUE + "Will encode %s into %s using bitrate %s ,will process the audio as %s and will use a %s file" \
	% (VidFileIn, VideoCodec, TargetBitrate, AudioType, fileProcess) + bcolors.ENDC


# have we been given a file or a folder
if os.path.isfile(VidFileIn) == True:
	RecodeFile(VidFileIn)
elif os.path.isdir(VidFileIn) == True:
	RecodeFolder(VidFileIn)
else:
	print "Error not supplied with a valid file or folder"
	
