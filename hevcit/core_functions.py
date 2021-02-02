"""core_functions.py

Core functions

Ver  Date        Author      Comment
1.00 2018-02-20  cdf00209    Initial version
"""

import tempfile
import subprocess
import logging
from logging.handlers import RotatingFileHandler
import platform
import os
import time
import sys
import threading


class __LoggingNullHandler(logging.Handler):
    def emit(self, record):
        pass

def module_null_logger(logger_name):
    """Initialise a null logger - used by libraries to send their debug content to null, leaving the calling
        function to establish a root logger if it wants their logging content
        
        Option Parameters:
            logger_name: the name for the logger

        Returns: The logger class
    """
        
    logging.getLogger(logger_name).addHandler(__LoggingNullHandler())
    return logging.getLogger(logger_name)

_logger=module_null_logger(__name__)

def GetLogger(logfile=None, debug=False):
    """Initialise the root logger
        
        Option Parameters:
            logfile: the full path to the logfile to write, if not supplied logging will be to console only
            debug: enable the output of debug log messages
        
        Returns: The root logger class
    """

    # setup a root logger - this will capture output from all loggers
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # create formatter
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(module)-16s %(funcName)-20s %(message)s')

    if logfile != None:
        # create file handler which logs even debug messages
        fh = RotatingFileHandler(logfile, maxBytes=0, backupCount=14)
        fh.doRollover()
        fh.setFormatter(formatter)
        
        if debug:
            fh.setLevel(logging.DEBUG)
        else:
            fh.setLevel(logging.INFO)
        
        logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()    
    ch.setFormatter(formatter)
    
    if debug:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)
        
    logger.addHandler(ch)
    
    return logger

class RunCLI():
    """Execute a cli command, wait for it to finish and collect the results
    """
    
    def __init__(self, command, std_out_file=None, die_on_fail=True, use_shell=False, background=False, merge_out_and_err=True):
        """Execute a cli command, wait for it to finish and collect the results
                
        Parameters:
            command: the command to execute as a list of strings (['command','-ls','-f','/foo/bar'])

        OptionalParameters:
            std_out_file: write stdout to this file, a temp file will be used if not specified
            die_on_fail: raise an exception if the command returns an exit code not equal to 0 (default true)
            use_shell: execute the process in a shell (default false)
            background: run the process in the background - in order to collect results you must call poll() (default false)
        """

        self._command=command
        self._die_on_fail=die_on_fail
        self._use_shell=use_shell
        self._background=background
        self._merge_out_and_err=merge_out_and_err
        self._std_out_file=std_out_file

        self._stdout=None
        self._stderr=None
        self._exitcode=None

        self._pid=None

        #write stdout and stderr to a temp file, as using subprocess.PIPE hangs python
        if self._std_out_file==None:
            self._tmp_outfile=tempfile.TemporaryFile()
        else:
            self._tmp_outfile=open(self._std_out_file,"w+")

        if merge_out_and_err:
            self._tmp_errfile=subprocess.STDOUT
        else:
            self._tmp_errfile=tempfile.TemporaryFile()
        
        _logger.debug("Executing:%s", " ".join(self._command))
        self._pid = subprocess.Popen(self._command, shell=self._use_shell, stdout=self._tmp_outfile, stderr=self._tmp_errfile)

        #are we waiting for the process to finish:
        if self._background==False:
            while self._exitcode==None:
                self.poll()

    def stdout(self):
        """Return std out from the process"""
        return self._stdout

    def stderr(self):
        """Return std out from the process"""
        
        if self._merge_out_and_err:
            return None
        else:
            return self._stderr

    def exitcode(self):
        """Return the exitcode from the process"""
        return self._exitcode

    def poll(self):
        """Poll the process - updating class attributes if finished"""

        self._exitcode=self._pid.poll()

        if self._exitcode != None:       
            self._tmp_outfile.seek(0)
            self._stdout=self._tmp_outfile.read()
            self._tmp_outfile.close()

            if self._merge_out_and_err==False:
                self._tmp_errfile.seek(0)
                self._stderr=self._tmp_errfile.read()
                self._tmp_errfile.close() 

            if self._exitcode != 0 and self._die_on_fail:
                raise RuntimeError("CLI Command failed (exitcode=%s): %s\nSTDOUT:\n%s\n\nSTDERR:\n%s" %(" ".join(self._command), self._exitcode, self._stdout, self._stderr))


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

def ExecuteFFmpeg(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = ''

    # Poll process for new output until finished
    for line in iter(process.stderr.readline, ""):
#        if line[0:5] == 'frame':
        print(line),
        output += line


    process.wait()
    exitCode = process.returncode

    if (exitCode == 0):
        return output
    else:
        raise Exception(command, exitCode, output)


class MyClass(threading.Thread):
    def __init__(self, command):
        self.stdout = None
        self.stderr = None
        threading.Thread.__init__(self)

    def run(self, command):
        p = subprocess.Popen(command.split(),
                             shell=False,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        self.stdout, self.stderr = p.communicate()
