
"""
recode v2.py

Ver  Date       Author      Comment
2.00 2018-04-02 Chris Cook  Recoded to be more pythonic and split into modules

"""

import sys
import os
import argparse
import base64
import threading
import subprocess

# import mediainfo
from pymediainfo import MediaInfo

# import the core functions lib
import core_functions as core
import video_functions as video

# store some constants
TmpDir = 'H:/Video/temp/'
BackupDir = '//tank03/backup/video/'
LowBitRate = 500


# pick up the cli arguments
cli_parser = argparse.ArgumentParser(description='Recodes video into either h264 or h265 with various options')
cli_parser.add_argument('-b','--bitrate', metavar='<bitrate>', help='Bitrate to encode to, use calc, calc2 or calc3 to set automatically', required=True)
cli_parser.add_argument('-a','--audio', metavar='<audio>', help='Audio processing to use, passall, all, one, passbest, aac or 64k', required=True)
cli_parser.add_argument('-v','--video', metavar='<video>', help='Video codec to use, h264 or h265, defaults to h265 if not supplied', required=False, default='h265')
cli_parser.add_argument('-r','--rescale', metavar='<rescale>', help='Width to rescale the video to e.g. 1280', required=False)
cli_parser.add_argument('-t','--test', metavar='<test>', help='Duration of video to use as test in seconds, e.g. 60', required=False)
cli_parser.add_argument('-p','--printmode', help='Print the recode command, do not run it', required=False,action='store_true')
cli_parser.add_argument('-s','--process', metavar='<process>', help='Method to be used to process the file, new, backup, replace', required=True)
cli_parser.add_argument('-f','--file', metavar='<file>', help='File or folder to process', required=True)
cli_parser.add_argument('-d','--debug', help='Debug mode, very verbose', required=False,action='store_true')
cli_parser.add_argument('-l','--ludicrous', help='Print a ludicrous amount of information about the source tracks', required=False,action='store_true')
cli_args = cli_parser.parse_args()


# setup a logger
logger=core.GetLogger(debug=cli_args.debug)

# debug log all the cli args
for arg in vars(cli_args):
    logger.debug("Cli argument - %s: %s", arg.ljust(10),getattr(cli_args, arg))

logger.debug("Dir to use as Temp = %s", TmpDir)
logger.debug("Dir to use as backup = %s", BackupDir)
logger.debug("Min BitRate set as = %s", LowBitRate)

logger.info("Will encode '%s' into %s using bitrate '%s' ,will process the audio as %s and will use a %s file", cli_args.file, cli_args.video, cli_args.bitrate, cli_args.audio, cli_args.process)


def RecodeFile(filename):
    # will turn this into a procedure so that we can process folders as well as files
    logger.info("Starting processing on '%s'", filename)

    # grab the file extension
    FileExt = os.path.splitext(filename)[1]

    VideoInfo, AudioInfo, SubInfo, AllInfo = video.GetVideoInfo(filename, TmpDir, cli_args.ludicrous)

    # some debug logging
    logger.debug("VideoInfo : %s", VideoInfo)
    logger.debug("AudioInfo : %s", AudioInfo)
    logger.debug("SubInfo   : %s", SubInfo)
    logger.debug("AllInfo   : %s", AllInfo)

    # are we gonna rescale
    if cli_args.rescale <> None and cli_args.bitrate <> "pass":
        ffRescale, NewWidth = video.VideoRescaleCalc(VideoInfo[0]['Width'], VideoInfo[0]['Height'], cli_args.rescale)
    else:
        NewWidth = VideoInfo[0]['Width']
        ffRescale = []

    mapVid, ffVid, NewBitrate = video.VideoParameters(VideoInfo, cli_args.bitrate, cli_args.video, AllInfo, LowBitRate)

    # some debug logging
    logger.debug("mapVid     : %s", mapVid)
    logger.debug("ffVid      : %s", ffVid)
    logger.debug("NewBitrate : %s", NewBitrate)

    # check work is required
    workreq = 0
    if VideoInfo[0]['Format'] <> 'HEVC':
        workreq=1
        workreas='video is not encoded in HEVC'
    elif int(NewWidth) < int(VideoInfo[0]['Width']):
        workreq=1
        workreas='video will be recaled to smaller size'
    elif (NewBitrate / VideoInfo[0]['BitRate']) < 0.93:
        workreq=1
        workreas='video will be encoded to a lower bitrate'

    if workreq != 1:
        logger.warning("No work required on %s", filename)
    else:
        logger.info("Recoding as %s", workreas)

        mapAud, ffAud, formatAud = video.AudioParameters(AudioInfo, FileExt, cli_args.audio, AllInfo)

        # some debug logging
        logger.debug("mapAud    : %s", mapAud)
        logger.debug("ffAud     : %s", ffAud)
        logger.debug("formatAud : %s", formatAud)

        # work out what to do with the subs
        if FileExt == '.avi':
            logger.info("AVI file so skipping subs")
            mapSub = []
            ffSub = []
            formatSub = []
        else:		
            mapSub, ffSub, formatSub= video.SubParameters(SubInfo)
            # some debug logging
            logger.debug("mapSub    : %s", mapSub)
            logger.debug("ffSub     : %s", ffSub)
            logger.debug("formatSub : %s", formatSub)

        # work out the final file extension
        if formatAud == 'mkv' or formatSub == 'mkv':
            format = 'mkv'
        else:
            format = 'mp4'

        # PreProcess the files, create backups etc.
        #VidFileIn, VidFileOut = FilePreProcess (VidFileInWin, fileProcess, format)

        if cli_args.process == 'backup':
        # then backup the file
            VidFileBackup = BackupDir + os.path.basename(filename)
            try:
                os.remove(VidFileBackup)
            except OSError:
                pass

            if cli_args.printmode != True:
                logger.info("Backing up file from %s to %s", filename, VidFileBackup)
                core.copy_large_file(filename, VidFileBackup)
                os.remove(filename)
                logger.info("Backup from from %s to %s complete", filename, VidFileBackup)
            else:
                logger.info("Print mode : File will not be moved")

            # stash the filenames
            VidFileIn = VidFileBackup
            VifFileOt = filename

        elif cli_args.process == 'new':
            VidFileIn = filename
            VifFileOt = os.path.splitext(VidFileIn)[0]
            VifFileOt = VifFileOt + '_new' + '.' + format


        elif cli_args.process == 'replace':
            tmpRandom = base64.b64encode(os.urandom(12), '__')
            VidFileIn = os.path.splitext(filename)[0] + '_' + tmpRandom + os.path.splitext(filename)[1]
            VifFileOt = os.path.splitext(filename)[0] + '.' + format
            if cli_args.printmode != True:
                logger.info("Renaming file from %s to %s", VidFileIn, VifFileOt)
                os.rename(filename, VidFileIn)
            else:
                logger.info("Print mode : File will not be renamed")
        else:
            logger.critical("File process method of %s is not understood, exiting", cli_args.process)
            sys.exit(2)

        # some debug logging
        logger.debug("VidFileIn : %s", VidFileIn)
        logger.debug("VifFileOt : %s", VifFileOt)

        # sort out all the mappings
        mapping = mapVid + mapAud + mapSub
        logger.debug("Complete mapping : %s", mapping)

        # create the ffmpeg command
        ffCommand = ['ffmpeg_g.exe', '-hide_banner', '-y', '-i'] + [VidFileIn]
        if cli_args.test <> None:
            ffCommand = ffCommand + ['-t', cli_args.test]
        
        ffCommand = ffCommand + mapping + ffVid + ffRescale + ffAud + ffSub + [VifFileOt]


        # and run it
        if cli_args.printmode != True:
            logger.debug("Complete ffmpeg command : %s", ' '.join(ffCommand))
            logger.debug("Starting ffmpeg")
            subprocess.check_call(ffCommand)
            if cli_args.process == 'replace':
                logger.debug("Deleting temp file : %s", VidFileIn)
                os.remove(VidFileIn)
        else:
            logger.info("Print mode, no code will be executed")
            logger.info("Complete ffmpeg command : %s", ' '.join(ffCommand))


def RecodeFolder (FolderName):
    logger.debug("Processing a folder : %s", FolderName)
    Files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(FolderName) for f in filenames if os.path.splitext(f)[1] in ('.mp4', '.mkv', '.m4v', '.avi', '.mov', '.flv', '.wmv', '.mpg', '.3gp')]
    Files.sort()
    #Files.sort(reverse=True)
    for File in Files:
        logger.debug("Found in folder %s file %s", FolderName, File)
        RecodeFile(File)


# have we been given a file or a folder
if os.path.isfile(cli_args.file) == True:
    RecodeFile(cli_args.file)
elif os.path.isdir(cli_args.file) == True:
    RecodeFolder(cli_args.file)
else:
	logger.critical("Error not supplied with a valid file or folder : %s", cli_args.file)
	
