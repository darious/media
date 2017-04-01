# media
Code to deal with media

# to install pymediainfo to work in cygwin
wget http://peak.telecommunity.com/dist/ez_setup.pymediainfo
python ez_setup.py
easy_install pymediainfo

# then edit the code to work in cygwin
nano /usr/lib/python2.7/site-packages/pymediainfo-2.1.5-py2.7.egg/pymediainfo/__init__.py

# edit from line 78
		if os.name in ("nt", "dos", "os2", "ce", ):
            lib = windll.MediaInfo
        elif os.name in ("posix"):
            lib = cdll.LoadLibrary('mediainfo.dll')
        elif sys.platform == "darwin":
            try:
                lib = CDLL("libmediainfo.0.dylib")
            except OSError:
                lib = CDLL("libmediainfo.dylib")
        else:
            lib = CDLL("libmediainfo.so.0")
			
# put this in here

# edit the windows system environment varibles and add this to the path
C:\Program Files\MediaInfo

# then restart cygwin and it should work
