
"""
ps1_chd.py

Extracts a 7z file containing a PS1 game and converts it to a CHD

Ver  Date       Author      Comment
1.00 2018-05-20 Chris Cook  Initial version

"""

import sys
import os
import argparse
import base64
import threading
import subprocess
import shutil

# import the core functions lib
import core_functions as core

# store some constants
#TmpDir = 'H:/temp/emu/temp/'
#TmpDir = 'G:/temp/'
TmpDir = 'H:/temp/emu/dc/'
#outDir = '//tank02/emulation/roms/Sega Dreamcast/'
#outDir = 'H:/temp/emu/dc_done/'
outDir = '//tank02/emulation1/roms1/Sega Dreamcast/'



# pick up the cli args
cli_parser = argparse.ArgumentParser(description='Extracts a 7z file containing a PS1 game and converts it to a CHD')
cli_parser.add_argument('-f','--file', metavar='<file>', help='File or folder to process', required=True)
cli_parser.add_argument('-d','--debug', help='Debug mode, very verbose', required=False,action='store_true')
cli_args = cli_parser.parse_args()


# setup a logger
logger=core.GetLogger(debug=cli_args.debug)

# log all the cli args
for arg in vars(cli_args):
    logger.debug("Cli argument - %s: %s", arg.ljust(10),getattr(cli_args, arg))

logger.debug("Dir to use as Temp = %s", TmpDir)

logger.info("Will process '%s' into CHD", cli_args.file)


def processFile(filename):

    # make a new temp folder
    tmpRandom = base64.b64encode(os.urandom(12), '__')
    tmpFolder = TmpDir + tmpRandom
    if not os.path.exists(tmpFolder):
        #os.makedirs(tmpFolder)
        print ""

    logger.debug("Created temp folder = %s", tmpFolder)

    # extract the 7z into the new temp folder
    logger.info("Extracting 7z file %s to temp folder %s", filename, tmpFolder)
    cmd = []
    cmd.append(r'C:\Program Files\7-Zip\7z.exe')
    cmd.append('e')
    cmd.append(filename)
    cmd.append('-aoa')
    cmd.append('-o'+tmpFolder)
    subprocess.call(cmd)


    # is there a cue file, if not create one
    cueFile = tmpFolder + '/' + os.path.splitext(os.path.basename(filename))[0] + "." + 'gdi'
#
#    if not os.path.isfile(cueFile):
#        logger.info("cue file %s not found, so has been crated", cueFile)
#        cueContent  = 'FILE "%s.bin" BINARY\n' %os.path.splitext(os.path.basename(filename))[0]
#        cueContent += '  TRACK 01 MODE2/2352\n'
#        cueContent += '    INDEX 01 00:00:00\n'
#        f = open( cueFile, 'w' )
#        f.write( cueContent )
#        f.close()
#    else:
#        logger.debug("cue file %s found", cueFile)


    # move to the temp folder
    os.chdir(tmpFolder)

    # convert the cue bin into chd
    cmd = []
    cmd.append(r'H:\emulators\tools\chdmanv4.exe')
    cmd.append('-createcd')
#    cmd.append('-i')
    cmd.append(cueFile)
#    cmd.append('-o')
    cmd.append(outDir + os.path.splitext(os.path.basename(filename))[0] + "." + 'chd')

    logger.debug("chd command to use : %s", ' '.join(cmd))

    subprocess.call(cmd)


    # done do drop the temp folder
    #logger.debug("Dropping temp folder: %s", tmpFolder)
    #shutil.rmtree(tmpFolder)


def processFolder (FolderName):
    logger.debug("Processing a folder : %s", FolderName)
    Files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(FolderName) for f in filenames if os.path.splitext(f)[1] in ('.7z')]
    Files.sort()
    
    for File in Files:
        logger.debug("Found in folder %s file %s", FolderName, File)
        processFile(File)


# have we been given a file or a folder
if os.path.isfile(cli_args.file) == True:
    processFile(cli_args.file)
elif os.path.isdir(cli_args.file) == True:
    processFolder(cli_args.file)
else:
	logger.critical("Error not supplied with a valid file or folder : %s", cli_args.file)
	


