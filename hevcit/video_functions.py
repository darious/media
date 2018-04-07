"""video_functions.py

Video functions

Ver  Date        Author      Comment
1.00 2018-04-02  Chris Cook  Initial version
"""

import datetime
import sys
import os
import subprocess
import base64

# import mediainfo
from pymediainfo import MediaInfo

# import core func for logger
import core_functions as core

_logger=core.module_null_logger(__name__)


def ZeroBitrate(VidFileIn, TrackID, Type, TmpDir):
    _logger.info("Got a 0 bitrate so creating temp file to check %s track %s", VidFileIn, TrackID)
    # deal with a 0 bitrate and work out what it is
    tmpRandom = base64.b64encode(os.urandom(12), '__')
    VidFileTemp = TmpDir + os.path.basename(VidFileIn) + '_' + tmpRandom + '.mkv'

    # create a new file with just this stream
    if Type == 'V':
        codec = ['-c:v:0', 'copy', '-an']
    if Type == 'A':
        codec = ['-c:a:0', 'copy', '-vn']

    ffCommand = ['ffmpeg_g.exe',  '-i',  VidFileIn] + codec + [VidFileTemp]

    # show the command
    _logger.info("Creating temp file with ffmpeg command : %s", ' '.join(ffCommand))

    # and run it
    subprocess.check_call(ffCommand)

    # read the data
    media_info = MediaInfo.parse(VidFileTemp)

    tmpBitrate = None
    for track in media_info.tracks:
        #for key, value in track.to_data().iteritems():
        #    print str(key).ljust(30) + ' : ' + str(value)
        if track.overall_bit_rate is not None:
            tmpBitrate = track.overall_bit_rate
        
    if tmpBitrate == None:
        _logger.critical("Still Got a 0 bitrate from demux file. Exiting")
        sys.exit(2)

    _logger.debug("Bitrate from demux for %s", tmpBitrate)

    # drop the temp file
    try:
        os.remove(VidFileTemp)
        _logger.debug("Temp file %s dropped", VidFileTemp)
    except OSError:
        pass

    return tmpBitrate


def GetVideoInfo(VidFileIn, TmpDir, ludicrous):
    """Get all the info about a given media file
    Parameters : Path to a media file
    Returns: Four list of dicts describing the video, audio, subtitle and all track info
    """

    VideoInfo = []
    AudioInfo = []
    SubInfo = []
    AllInfo = []

    counter = - 1

    _logger.info("Reading mediainfo from %s", VidFileIn)
    try:
        media_info = MediaInfo.parse(VidFileIn)
    except OSError:
        _logger.debug("Using hardcode mediainfo library file")
        media_info = MediaInfo.parse(VidFileIn, library_file="C:\\Program Files\\MediaInfo\\MediaInfo.dll")

    for track in media_info.tracks:
        _logger.debug("Processing track %s type %s", track.track_id, track.track_type)

        if ludicrous:
            for key, value in track.to_data().iteritems():
                _logger.debug("Track ID : %s Type : %s %s = %s", track.track_id, track.track_type, key.ljust(40), value)

        if track.track_type in ('Audio', 'Video', 'Text'):
            counter += 1
            # clean up the stream info and append to the allinfo list           
            try:
                streamorder = int(track.streamorder)
            except:
                streamorder = int(track.streamorder.split('-')[1])
            _logger.debug("Stream order for track %s type %s is %s", track.track_id, track.track_type, streamorder)
            AllInfo.append ({ 'Type':track.track_type, 'ID': track.track_id, 'counter':counter, 'streamorder':streamorder })

        # if a video track grab the details
        if track.track_type == 'Video':
            # Check the bitrate makes sense by trying to convert it to an integer
            try:
                tmpBitRate = int(track.bit_rate)
                _logger.info("Bitrate for track %s type %s is %s", track.track_id, track.track_type, tmpBitRate)
            except:
                _logger.debug("Bitrate cannot be determined from MediaInfo for track %s type %s", track.track_id, track.track_type)
                # guess based on the filesize and other info
                tmpBitRate = ZeroBitrate(VidFileIn, 0, 'V', TmpDir)
                _logger.info("Bitrate from demux for track %s type %s is %s", track.track_id, track.track_type, tmpBitRate)

            # if the file is a varible framerate pretend its 25 fps
            if track.frame_rate_mode == 'VFR':
                track.frame_rate = 25

            # default the duration if there is none
            if track.duration is None:
                track.duration = 0

            # append the information to the arrays
            VideoInfo.append ({ 'ID': track.track_id, 'Format': track.format, 'BitRate': float(tmpBitRate)/1000, 'Width': track.width, 'Height': track.height, 'FrameRate': track.frame_rate, 'Duration': datetime.timedelta(milliseconds=float(track.duration)), 'ScanType': track.scan_type, 'streamorder':streamorder })

        # if an Audio track grab the details
        elif track.track_type == 'Audio':
            if track.bit_rate is None:
                _logger.debug("Bitrate cannot be determined from MediaInfo for track %s type %s", track.track_id, track.track_type)
                tmpBitRate = ZeroBitrate(VidFileIn, int(track.track_id) - 1, 'A', TmpDir)
                _logger.debug("Bitrate from demux for track %s type %s is %s", track.track_id, track.track_type, tmpBitRate)
            else:
                tmpBitRate = track.bit_rate
                _logger.debug("Bitrate from mediainfo for track %s type %s is %s", track.track_id, track.track_type, tmpBitRate)

            # tidy up the bitrate
            if "/" in str(track.bit_rate):
                try:
                    tmpBitRate = int(str(track.bit_rate).split(" / ")[0])
                except:
                    try:
                        tmpBitRate = int(str(track.bit_rate).split(" / ")[1])
                    except:
                        _logger.debug("Bitrate cannot be determined from MediaInfo for track %s type %s", track.track_id, track.track_type)
                        tmpBitRate = ZeroBitrate(VidFileIn, int(track.track_id) - 1, 'A', TmpDir)
            
            _logger.info("Bitrate for track %s type %s is %s", track.track_id, track.track_type, tmpBitRate)
            
            # tidy up the channels
            if track.channel_s == '8 / 6':              tmpChannels = 8
            elif track.channel_s == '7 / 6':            tmpChannels = 7
            elif track.channel_s == '20 / 6':           tmpChannels = 6
            elif track.channel_s == '7 / 7 / 6':        tmpChannels = 6
            elif track.channel_s == '8 / 7 / 6':        tmpChannels = 6
            elif track.channel_s == 'Object Based / 8': tmpChannels = 8
            else: tmpChannels = track.channel_s

            AudioInfo.append ({ 'ID': track.track_id, 'Format': track.format, 'BitRate': tmpBitRate, 'Channels': tmpChannels, 'Language': track.language, 'streamorder':streamorder })

        # and finally text tracks (subtitles)
        elif track.track_type == 'Text':
            SubInfo.append ({ 'ID': track.track_id, 'Format': track.format, 'Language': track.language, 'Default': track.default, 'Forced': track.forced, 'streamorder':streamorder })
        
    return (VideoInfo, AudioInfo, SubInfo, AllInfo)



def VideoRescaleCalc(OldWidth, OldHeight, RescaleWidth):
    """Work out the new size of the a video file
    Parameters : Oldwidth - Current file width
               : OldHeight - Current file height
               : RescaleWidth - Width the file should be rescaled to
    Returns: List containing the addition to the ffmpeg command to instruct it to rescale
    """
    _logger.info("Calculating rescale from %s to %s", OldWidth, RescaleWidth)

    if int(RescaleWidth) < int(OldWidth):
        NewWidth = RescaleWidth
        HewHeight = int(round((int(RescaleWidth) * int(OldHeight)) / int(OldWidth), 0))
        _logger.info("Asked to rescale, will go from %sx%s to %sx%s", OldWidth, OldHeight, RescaleWidth, HewHeight)
    else:
        NewWidth = OldWidth
        HewHeight = OldHeight
        _logger.info("Asked to rescale, but New Width of %s is greater than start Width of %s so not changing", RescaleWidth, OldWidth)

    ffRescale = ['-vf', 'scale='+str(NewWidth)+':'+str(HewHeight)]
    return ffRescale, NewWidth


def VideoParameters(VideoInfo, TargetBitrate, VideoCodec, AllInfo, LowBitRate):
    """Work out the video parameters to use in the recode
    Parameters : VideoInfo - The videoinfo to use (dict)
               : TargetBitrate - TargetBitrate to use
               : VideoCodec - Codec to recode to
               : AllInfo - List of dicts that describes the media
    Returns:   : mapping - The mapping of input streams to output for ffmpeg
               : ffVid - The Video section of the ffmpeg command to use for the recode
               : NewBitrate - The new bitrate that will be used for the encode
    """
    _logger.info("Determining Video Parameters")
    
    # if we've been asked to pass the video through then just do that
    if TargetBitrate == "pass":
        ffVid = ['-c:v', 'copy']
        NewBitrate = VideoInfo[0]['BitRate'] + 1
        _logger.info("Video : %s at %dbps %s long and will be passed through", VideoInfo[0]['Format'], VideoInfo[0]['BitRate'], VideoInfo[0]['Duration'])
    else:
        # should we change the framerate?
        VideoInfo[0]['FrameRate'] = float(VideoInfo[0]['FrameRate'])
        if VideoInfo[0]['FrameRate'] == 50: TargetFrameRate = 25
        elif VideoInfo[0]['FrameRate'] == 59.94: TargetFrameRate = 29.97
        elif VideoInfo[0]['FrameRate'] == 59.88: TargetFrameRate = 29.94
        elif VideoInfo[0]['FrameRate'] == 59.940: TargetFrameRate = 29.97
        elif VideoInfo[0]['FrameRate'] == 60: TargetFrameRate = 30
        elif VideoInfo[0]['FrameRate'] == 100: TargetFrameRate = 25
        elif VideoInfo[0]['FrameRate'] == 24.97: TargetFrameRate = 25
        else: TargetFrameRate = VideoInfo[0]['FrameRate']

        if TargetFrameRate <> VideoInfo[0]['FrameRate']:
            _logger.warning("Got a framerate of %s So resampling with -r %s.", VideoInfo[0]['FrameRate'], TargetFrameRate)
            Resample = ['-r', str(TargetFrameRate)]
        else:
            _logger.info("Got a framerate of %s So no change required", VideoInfo[0]['FrameRate'])
            Resample = []
        
        # Should we deinterlace?
        if VideoInfo[0]['ScanType'] == 'Interlaced':
            _logger.warning("Got an interlaced file so will deinterlace")
            Deinterlace = ['-deinterlace']
        else:
            _logger.info("Got a progressive file so no change required")
            Deinterlace= []

        # calculate the new bitrate
        if TargetBitrate == "calc":
            NewBitrate = int(round((((int(VideoInfo[0]['Width']) * int(VideoInfo[0]['Height']) * float(TargetFrameRate)) / 1000000) + 11) * 37, 0))
        elif TargetBitrate == "calc2":
            NewBitrate = int(round((((int(VideoInfo[0]['Width']) * int(VideoInfo[0]['Height']) * float(TargetFrameRate)) / 1000000) + 11) * 83, 0))
        elif TargetBitrate == "calc3":
            NewBitrate = int(round((((int(VideoInfo[0]['Width']) * int(VideoInfo[0]['Height']) * float(TargetFrameRate)) / 1000000) + 11) * 132, 0))
        elif TargetBitrate == "half":
            NewBitrate = int(round(float(VideoInfo[0]['BitRate']) / 2))
        else:
            NewBitrate = int(TargetBitrate)

        if VideoCodec == "h264":
            NewBitrate = NewBitrate * 2.5

        # check the calculated bit is ok
        if NewBitrate < LowBitRate:
            _logger.warning("New Bitrate lower than acceptable so using default low value of %d", LowBitRate)
            NewBitrate = LowBitRate

        # check its lower than the source
        if NewBitrate >= VideoInfo[0]['BitRate']:
            _logger.warning("New Bitrate lower than the source so using source bitrate of %d", VideoInfo[0]['BitRate'])
            NewBitrate = VideoInfo[0]['BitRate']

        # deal with the formats
        if VideoCodec == "h265":
            ffcodec = 'nvenc_hevc'
        elif VideoCodec == "h264":
            ffcodec = 'nvenc'
        
        # create the bits of the ffmpeg command for the video
        ffVid = ['-c:v', ffcodec, '-b:v', str(NewBitrate)+'k', '-maxrate', '20000k', '-preset', 'hq']
        # add any extra parts
        ffVid = ffVid + Resample + Deinterlace

        _logger.info("Video : %s %sx%s at %dk %s long new %s file will be bitrate (%s) %dk", VideoInfo[0]['Format'], VideoInfo[0]['Width'], VideoInfo[0]['Height'], VideoInfo[0]['BitRate'], VideoInfo[0]['Duration'], VideoCodec, TargetBitrate, NewBitrate)

    # calculate the mapping
    mapping = ['-map', '0:'+str(VideoInfo[0]['streamorder'])]
    
    return mapping, ffVid, NewBitrate


def AudioParameters(AudioInfo, fileExt, AudioProcess, AllInfo):
    """Work out the audio parameters to use in the recode
    Parameters : AudioInfo - The audioInfo to use (dict)
               : fileExt - File extension of the incoming file
               : AudioProcess - Process to use for the audio
               : AllInfo - List of dicts that describes the media
    Returns:   : mapping - The mapping of input streams to output for ffmpeg
               : ffAud - The Audio section of the ffmpeg command to use for the recode
               : formatAud - The video container required to be used by the audio
    """
    _logger.info("Determining Audio Parameters")

    # set some constants and defaults
    format = 'mp4'
    counter = -1
    ffAud = []
    mapping = []

    if not AudioInfo:
        # no audio
        _logger.warning("No audio tracks found")
    else:
        # fix the channel metadata if required
        for track in AudioInfo:
            try:
                track['BitRate']=int(track['BitRate'])
            except:
                track['BitRate']=int(384000)
            
        # calculate the best track
        _logger.info("Calculating best Audio track")
        bestTrackID=AudioInfo[0]['ID']
        bestTrackIx=0

        if len(AudioInfo) > 1:
            bestChannels=int(AudioInfo[0]['Channels'])
            bestBitrate=int(AudioInfo[0]['BitRate'])
            bestLang=AudioInfo[0]['Language']
            bestFormat=0

            for track in AudioInfo:
                _logger.debug("Audio track %s, %s Channels, %sk %s", track['ID'], track['Channels'], track['BitRate']/1000, track['Format'])
                counter += 1
                if   track['Format'] == 'MPEG Audio': currFormat = 0
                elif track['Format'] == 'AAC':        currFormat = 1
                elif track['Format'] == 'Vorbis':     currFormat = 2
                elif track['Format'] == 'Opus':       currFormat = 3
                elif track['Format'] == 'FLAC':       currFormat = 4
                elif track['Format'] == 'AC-3':       currFormat = 5
                elif track['Format'] == 'E-AC-3':     currFormat = 6
                elif track['Format'] == 'DTS':        currFormat = 7
                elif track['Format'] == 'TrueHD':     currFormat = 8
                elif track['Format'] == 'DTS-HD':     currFormat = 9
                else: 
                    print 'Error format %s not catered for' %track['Format']
                    sys.exit(2)
                if int(track['Channels']) >= bestChannels:
                    if int(track['BitRate']) > bestBitrate or (bestLang != 'en' and track['Language'] == 'en') or currFormat > bestFormat:
                        bestTrackID=AudioInfo[0]['ID']
                        bestTrackIx=counter


        _logger.info("Best track ID : %s, Index : %s which is %sk %s channel %s in %s", bestTrackID, bestTrackIx, AudioInfo[bestTrackIx]['BitRate']/1000, AudioInfo[bestTrackIx]['Channels'], AudioInfo[bestTrackIx]['Format'], AudioInfo[bestTrackIx]['Language'])
        
        # just the one track required
        if AudioProcess in ("one", "aac", "64k"):
            if AudioInfo[bestTrackIx]['Channels'] >= 6:
                AudioBitrate = '384k'
                AudioCodec = 'ac3'
                format = 'mkv'
            else:
                AudioBitrate = '128k'
                AudioCodec = 'libfdk_aac'
                format = 'mp4'

            if AudioProcess == '64k':
                AudioBitrate = '64k'

            ffAud = ['-c:a:0', AudioCodec, '-b:a:0', AudioBitrate, '-ar:0', '48000']

            # calculate the mapping
            mapping = ['-map', '0:'+str(AudioInfo[bestTrackIx]['streamorder'])]

            _logger.info("Keeping Audio track :%s %sk %s channel %s, will recode to %s %s", str(AudioInfo[bestTrackIx]['ID'] - 1), AudioInfo[bestTrackIx]['BitRate']/1000, AudioInfo[bestTrackIx]['Channels'], AudioInfo[bestTrackIx]['Format'], AudioBitrate, AudioCodec)

        # pass throught the best track
        elif AudioProcess == "passbest":
            ffAud = ['-c:a:0', 'copy']
            format = 'mkv'
            
            # calculate the mapping
            mapping = ['-map', '0:'+str(AudioInfo[bestTrackIx]['streamorder'])]
                    
            _logger.info("Keeping Audio track %s %sk %s channel %s and passing it through", str(AudioInfo[counter]['ID'] - 1), AudioInfo[counter]['BitRate']/1000, AudioInfo[counter]['Channels'], AudioInfo[counter]['Format'])
            
        elif AudioProcess == "passall":
            counter = 0
            format = 'mkv'
            for track in AudioInfo:
                ffAud = ffAud + ['-c:a:'+ str(counter), 'copy']
                _logger.info("Keeping Audio track %s %sk %s channel %s and passing it through", str(AudioInfo[counter]['ID'] - 1), AudioInfo[counter]['BitRate']/1000, AudioInfo[counter]['Channels'], AudioInfo[counter]['Format'])
                # calculate the mapping
                mapping += ['-map', '0:'+str(track['streamorder'])]
            counter += 1
        
        elif AudioProcess == "all":
            counter = 0
            for track in AudioInfo:
                if AudioInfo[counter]['Channels'] >= 6:
                    AudioBitrate = '384k'
                    AudioCodec = 'ac3'
                    format = 'mkv'
                else:
                    AudioBitrate = '128k'
                    AudioCodec = 'libfdk_aac'
                
                # if more than one track then we have to use mkv
                if counter > 0 and format != 'mkv':
                    format = 'mkv'

                ffAud += ['-c:a:' + str(counter), AudioCodec, '-b:a:' + str(counter), AudioBitrate, '-ar:' + str(counter), '48000']

                _logger.info("Keeping Audio track :%s %sk %s channel %s, will recode to %s %s", str(AudioInfo[counter]['ID'] - 1), AudioInfo[counter]['BitRate']/1000, AudioInfo[counter]['Channels'], AudioInfo[counter]['Format'], AudioBitrate, AudioCodec)
                # calculate the mapping
                mapping += ['-map', '0:'+str(track['streamorder'])]
                counter =+ 1
            
    return (mapping, ffAud, format)


def SubParameters(SubInfo):
    """Work out the subtitle parameters to use in the recode
    Parameters : SubInfo - The SubInfo to use (dict)
    Returns:   : mapping - The mapping of input streams to output for ffmpeg
               : ffSub - The Subtitle section of the ffmpeg command to use for the recode
               : formatSub - The video container required to be used by the subtitles
    """
    ffSub=[]
    mapping=[]
    counter = 0
    format = 'mp4'

    for track in SubInfo:
        if track['Language'] == 'en' or track['Forced'] == 'Yes':
            #or track['Default'] == 'Yes' 
            # subtitle is english, default or forced, so we'll keep it
            mapping += ['-map', '0:'+str(track['streamorder'])]
            if track['Format'] in ("ASS", "UTF-8", "SSA"):
                # a format we can recode so we will
                ffSub = ffSub + ['-c:s:'+str(counter), 'ass']
                format = 'mkv'
                _logger.info("Keeping Subtitle track %s %s %s, will recode to Advanced SubStation Alpha", str(track['ID'] - 1), track['Language'], track['Format'])
            if track['Format'] in ("PGS", "VobSub"):
                # a format we can't code, so we'll just pass it through
                ffSub = ffSub + ['-c:s:'+str(counter), 'copy']
                format = 'mkv'
                _logger.info("Keeping Subtitle track %s %s %s, will be passed through unchanged", str(track['ID'] - 1), track['Language'], track['Format'])
            counter += 1

    return (mapping, ffSub, format)


