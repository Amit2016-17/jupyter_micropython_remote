from ipykernel.kernelbase import Kernel

import logging, time, os, re
import subprocess
from . import pyboard, mprepl

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

serialtimeout = 0.5
serialtimeoutcount = 10

wifimessageignore = re.compile("(\x1b\[[\d;]*m)?[WI] \(\d+\) (wifi|system_api|modsocket|phy|event|cpu_start|heap_init|network|wpa): ")

# use of argparse for handling the %commands in the cells
import argparse, shlex

ap_connect = argparse.ArgumentParser(prog="%connect", add_help=False)
ap_connect.add_argument('device', type=str, help='Device Identifier')
ap_connect.add_argument('--port2', type=str, help='if provided, use second serial port for binary data')
ap_connect.add_argument('--baudrate', type=int, default=115200)
ap_connect.add_argument('--user', type=str, default='micro')
ap_connect.add_argument('--password', type=str, default='python')
ap_connect.add_argument('--wait', type=int, default=0)

ap_disconnect = argparse.ArgumentParser(prog="%disconnect", add_help=False)
ap_disconnect.add_argument('--raw', help='Close connection without exiting raw mode', action='store_true')

ap_writebytes = argparse.ArgumentParser(prog="%writebytes", add_help=False)
ap_writebytes.add_argument('--binary', '-b', action='store_true')
ap_writebytes.add_argument('--verbose', '-v', action='store_true')
ap_writebytes.add_argument('stringtosend', type=str)

ap_readbytes = argparse.ArgumentParser(prog="%readbytes", add_help=False)
ap_readbytes.add_argument('--binary', '-b', action='store_true')

ap_sendtofile = argparse.ArgumentParser(prog="%sendtofile", description="send a file to the microcontroller's file system", add_help=False)
ap_sendtofile.add_argument('--append', '-a', action='store_true')
ap_sendtofile.add_argument('--mkdir', '-d', action='store_true')
ap_sendtofile.add_argument('--binary', '-b', action='store_true')
ap_sendtofile.add_argument('--execute', '-x', action='store_true')
ap_sendtofile.add_argument('--source', help="source file", type=str, default="<<cellcontents>>", nargs="?")
ap_sendtofile.add_argument('--quiet', '-q', action='store_true')
ap_sendtofile.add_argument('--QUIET', '-Q', action='store_true')
ap_sendtofile.add_argument('destinationfilename', type=str, nargs="?")

ap_mpycross = argparse.ArgumentParser(prog="%mpy-cross", add_help=False)
ap_mpycross.add_argument('--set-exe', type=str)
ap_mpycross.add_argument('pyfile', type=str, nargs="?")

ap_shell = argparse.ArgumentParser(prog="%shell", add_help=False)
ap_shell.add_argument('args', nargs="*")

ap_local = argparse.ArgumentParser(prog="%local", add_help=False)

ap_capture = argparse.ArgumentParser(prog="%capture", description="capture output printed by device and save to a file", add_help=False)
ap_capture.add_argument('--quiet', '-q', action='store_true')
ap_capture.add_argument('--QUIET', '-Q', action='store_true')
ap_capture.add_argument('outputfilename', type=str)

ap_writefilepc = argparse.ArgumentParser(prog="%%writefile", description="write contents of cell to file on PC", add_help=False)
ap_writefilepc.add_argument('--append', '-a', action='store_true')
ap_writefilepc.add_argument('--execute', '-x', action='store_true')
ap_writefilepc.add_argument('destinationfilename', type=str)
 

def parseap(ap, percentstringargs1, extras=False):
    try:
        args, extra = ap.parse_known_args(percentstringargs1)
        if extras:
            return args, extra
        return args
    except SystemExit:  # argparse throws these because it assumes you only want to do the command line
        return None  # should be a default one
        

# Complete streaming of data to file with a quiet mode (listing number of lines)
# Set this up for pulse reading and plotting in a second jupyter page

# argparse to say --binary in the help for the tag

# 2. Complete the implementation of websockets on ESP32  -- nearly there
# 3. Create the streaming of pulse measurements to a simple javascript frontend and listing
# 4. Try implementing ESP32 webrepl over these websockets using exec()
# 6. Finish debugging the IR codes


# * upgrade picoweb to handle jpg and png and js
# * code that serves a websocket to a browser from picoweb

# then make the websocket from the ESP32 as well
# then make one that serves out sensor data just automatically
# and access and read that from javascript
# and get the webserving of webpages (and javascript) also to happen


# should also handle shell-scripting other commands, like arpscan for mac address to get to ip-numbers

# compress the websocket down to a single straightforward set of code
# take 1-second of data (100 bytes) and time the release of this string 
# to the web-browser


class MicroPythonKernel(Kernel):
    implementation = 'micropython_kernel'
    implementation_version = "v3"

    banner = "MicroPython Serializer"

    language_info = {'name': 'micropython',
                     'codemirror_mode': 'python',
                     'mimetype': 'text/python',
                     'file_extension': '.py'}

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self.silent = False
        self.repl = None  # type: mprepl.MpRepl
        self.mpycrossexe = None

        self.srescapturemode = 0            # 0 none, 1 print lines, 2 print on-going line count (--quiet), 3 print only final line count (--QUIET)
        self.srescapturedoutputfile = None  # used by %capture command
        self.srescapturedlinecount = 0
        self.srescapturedlasttime = 0       # to control the frequency of capturing reported

        self.localenv = dict(globals={'print': self.sres}, locals={})

    def mpycross(self, mpycrossexe, pyfile):
        pargs = [mpycrossexe, pyfile]
        self.sresSYS("Executing:  {}\n".format(" ".join(pargs)))
        process = subprocess.Popen(pargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in process.stdout:
            self.sres(line.decode())
        for line in process.stderr:
            self.sres(line.decode(), n04count=1)

    def interpretpercentline(self, percentline, cellcontents):
        try:
            percentstringargs = shlex.split(percentline)
        except ValueError as e:
            self.sres("\n\n***Bad percentcommand [%s]\n" % str(e), 31)
            self.sres(percentline)
            return None

        percentcommand = percentstringargs[0]

        if percentcommand == ap_connect.prog:

            apargs = parseap(ap_connect, percentstringargs[1:])
            
            if self.repl and self.repl.connected:
                self.repl.close()

            try:

                self.repl = mprepl.MpRepl(apargs.device,
                                          apargs.port2,
                                          baudrate=apargs.baudrate,
                                          user=apargs.user,
                                          password=apargs.password,
                                          wait=apargs.wait
                                          )

                # if not apargs.raw:
                self.repl.connect()
                self.sresSYS("Ready.\n")

                    # else:
                    #     self.sres("Disconnecting [paste mode not working]\n", 31)
                    #     self.dc.disconnect(verbose=apargs.verbose)
                    #     self.sresSYS("  (You may need to reset the device)")
                    #     cellcontents = ""

            except pyboard.PyboardError as ex:
                self.sresSYS("  Error connecting: %s" % ex)

                cellcontents = ""

            return cellcontents.strip() and cellcontents or None

        if percentcommand == ap_shell.prog:
            apargs, args = parseap(ap_shell, percentstringargs[1:], True)
            with subprocess.Popen(list(apargs.args) + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0) as proc:
                while proc.poll() is None:
                    self.sres(proc.stdout.readline().decode())
                self.sres(proc.stdout.read().decode())

            return cellcontents.strip() and cellcontents or None

        if percentcommand == ap_local.prog:
            try:
                self.sres(exec(cellcontents, self.localenv['globals'], self.localenv['locals']))
            except BaseException as ex:
                import traceback
                self.sres(traceback.format_exc(-1), n04count=1)
            return None

        if percentcommand == ap_writefilepc.prog:
            apargs = parseap(ap_writefilepc, percentstringargs[1:])
            if apargs:
                if apargs.append:
                    self.sres("Appending to {}\n\n".format(apargs.destinationfilename), asciigraphicscode=32)
                    fout = open(apargs.destinationfilename, ("a"))
                    fout.write("\n")
                else:
                    self.sres("Writing {}\n\n".format(apargs.destinationfilename), asciigraphicscode=32)
                    fout = open(apargs.destinationfilename, ("w"))
                    
                fout.write(cellcontents)
                fout.close()
            else:
                self.sres(ap_writefilepc.format_help())
            if not apargs.execute:
                return None
            return cellcontents # should add in some blank lines at top to get errors right

        if percentcommand == "%mpy-cross":
            apargs = parseap(ap_mpycross, percentstringargs[1:])
            if apargs and apargs.set_exe:
                self.mpycrossexe = apargs.set_exe
            elif apargs.pyfile:
                if self.mpycrossexe:
                    self.mpycross(self.mpycrossexe, apargs.pyfile)
                else:
                    self.sres("Cross compiler executable not yet set\n", 31)
                    self.sres("try: %mpy-cross --set-exe /home/julian/extrepositories/micropython/mpy-cross/mpy-cross\n")
                if self.mpycrossexe:
                    self.mpycrossexe = "/home/julian/extrepositories/micropython/mpy-cross/mpy-cross"
            else:
                self.sres(ap_mpycross.format_help())
            return cellcontents.strip() and cellcontents or None
            
        if percentcommand == "%comment":
            self.sres(" ".join(percentstringargs[1:]), asciigraphicscode=32)
            return cellcontents.strip() and cellcontents or None
            
        if percentcommand == "%lsmagic":
            self.sres(re.sub("usage: ", "", ap_capture.format_usage()))
            self.sres("    records output to a file\n\n")
            self.sres("%comment\n    print this into output\n\n")
            self.sres(re.sub("usage: ", "", ap_disconnect.format_usage()))
            self.sres("    disconnects from web/serial connection\n\n")
            self.sres(re.sub("usage: ", "", ap_shell.format_usage()))
            self.sres("    used to run a shell command\n\n")
            self.sres(re.sub("usage: ", "", ap_local.format_usage()))
            self.sres("    runs the cell in local environment instead\n\n")
            self.sres("%lsmagic\n    list magic commands\n\n")
            self.sres(re.sub("usage: ", "", ap_mpycross.format_usage()))
            self.sres("    cross-compile a .py file to a .mpy file\n\n")
            self.sres("%readbytes\n    does serial.read_all()\n\n")
            self.sres(re.sub("usage: ", "", ap_readbytes.format_usage()))
            self.sres("    does serial.read_all()\n\n")
            self.sres("%rebootdevice\n    reboots device\n\n")
            self.sres(re.sub("usage: ", "", ap_sendtofile.format_usage()))
            self.sres("    send cell contents or file from disk to device file or directory\n\n")
            self.sres(re.sub("usage: ", "", ap_connect.format_usage()))
            self.sres("    connects to a micropython device\n\n")
            self.sres("%suppressendcode\n    doesn't send x04 or wait to read after sending the contents of the cell\n")
            self.sres("  (assists for debugging using %writebytes and %readbytes)\n\n")
            self.sres(re.sub("usage: ", "", ap_writebytes.format_usage()))
            self.sres("    does serial.write() of the python quoted string given\n\n")
            self.sres(re.sub("usage: ", "", ap_writefilepc.format_usage()))
            self.sres("    write contents of cell to a file\n\n")
            
            return None

        if percentcommand == ap_disconnect.prog:
            apargs = parseap(ap_disconnect, percentstringargs[1:])
            if self.repl:
                self.repl.close()
            return None
        
        # remaining commands require a connection
        if not (self.repl and self.repl.connected):
            return cellcontents

        if percentcommand == ap_capture.prog:
            apargs = parseap(ap_capture, percentstringargs[1:])
            if apargs:
                self.sres("Writing output to file {}\n\n".format(apargs.outputfilename), asciigraphicscode=32)
                self.srescapturedoutputfile = open(apargs.outputfilename, "w")
                self.srescapturemode = (3 if apargs.QUIET else (2 if apargs.quiet else 1))
                self.srescapturedlinecount = 0
            else:
                self.sres(ap_capture.format_help())
            return cellcontents

        if percentcommand == ap_writebytes.prog:
            # (not effectively using the --binary setting)
            apargs = parseap(ap_writebytes, percentstringargs[1:])
            if apargs:
                bytestosend = apargs.stringtosend.encode().decode("unicode_escape").encode()
                res = self.repl.write(bytestosend)
                if apargs.verbose:
                    self.sres(res, asciigraphicscode=34)
            else:
                self.sres(ap_writebytes.format_help())
            return cellcontents.strip() and cellcontents or None

        if percentcommand == ap_readbytes.prog:
            # (not effectively using the --binary setting)
            apargs = parseap(ap_readbytes, percentstringargs[1:])
            time.sleep(0.1)   # just give it a moment if running on from a series of values (could use an --expect keyword)
            l = self.repl.read(timeout=5)
            if apargs.binary:
                self.sres(repr(l))
            elif isinstance(l, bytes):
                self.sres(l.decode(errors="ignore"))
            else:
                self.sres(l)   # strings come back from webrepl
            return cellcontents.strip() and cellcontents or None
            
        if percentcommand == "%rebootdevice":
            self.repl.pyb.exit_raw_repl()
            self.repl.connect()
            return cellcontents.strip() and cellcontents or None
            
        if percentcommand == "%reboot":
            self.sres("Did you mean %rebootdevice?\n", 31)
            return None

        if percentcommand == "%%writetofile" or percentcommand == "%writefile":
            self.sres("Did you mean %%writefile?\n", 31)
            return None

        if percentcommand == "%serialdisconnect":
            self.sres("Did you mean %disconnect?\n", 31)
            return None

        if percentcommand == "%sendbytes":
            self.sres("Did you mean %writebytes?\n", 31)
            return None
            
        if percentcommand == "%reboot":
            self.sres("Did you mean %rebootdevice?\n", 31)
            return None

        if percentcommand in ("%savetofile", "%savefile", "%sendfile"):
            self.sres("Did you mean to write %sendtofile?\n", 31)
            return None

        if percentcommand == ap_sendtofile.prog:
            apargs = parseap(ap_sendtofile, percentstringargs[1:])
            if apargs and not (apargs.source == "<<cellcontents>>" and not apargs.destinationfilename) and (apargs.source != None):

                destfn = apargs.destinationfilename
                def sendtofile(filename, contents):
                    raise NotImplementedError
                    self.dc.sendtofile(filename, apargs.mkdir, apargs.append, apargs.binary, apargs.quiet, contents)

                if apargs.source == "<<cellcontents>>":
                    filecontents = cellcontents
                    if not apargs.execute:
                        cellcontents = None
                    sendtofile(destfn, filecontents)

                else:
                    mode = "rb" if apargs.binary else "r"
                    if not destfn:
                        destfn = os.path.basename(apargs.source)
                    elif destfn[-1] == "/":
                        destfn += os.path.basename(apargs.source)

                    if os.path.isfile(apargs.source):
                        filecontents = open(apargs.source, mode).read()
                        if apargs.execute:
                            self.sres("Cannot excecute sourced file\n", 31)
                        sendtofile(destfn, filecontents)

                    elif os.path.isdir(apargs.source):
                        if apargs.execute:
                            self.sres("Cannot excecute folder\n", 31)
                        for root, dirs, files in os.walk(apargs.source):
                            for fn in files:
                                skip = False
                                fp = os.path.join(root, fn)
                                relpath = os.path.relpath(fp, apargs.source)
                                if relpath.endswith('.py'):
                                    # Check for compiled copy, skip py if exists
                                    if os.path.exists(fp[:-3] + '.mpy'):
                                        skip = True
                                if not skip:
                                    destpath = os.path.join(destfn, relpath).replace('\\', '/')
                                    filecontents = open(os.path.join(root, fn), mode).read()
                                    sendtofile(destpath, filecontents)
            else:
                self.sres(ap_sendtofile.format_help())
            return cellcontents   # allows for repeat %sendtofile in same cell

        self.sres("Unrecognized percentline {}\n".format([percentline]), 31)
        return cellcontents
        
    def runnormalcell(self, cellcontents, bsuppressendcode):
        # cmdlines = cellcontents.splitlines(True)
        # r = self.repl.read()
        # if r:
        #     self.sres('[priorstuff] ')
        #     self.sres(str(r))

        n04count = 0

        def follow(data):
            nonlocal n04count
            if not data:
                return
            if b"\x04" in data:
                data = data.strip(b"\x04")
                n04count += 1
            if data:
                self.sres(data.decode(), n04count=n04count)

        try:

            ret, ret_err = self.repl.exec_(cellcontents, follow)
            if ret_err:
                follow(ret_err)
            # if ret:
            #     self.sres(ret)
        except pyboard.PyboardError as ex:
            self.sres('Comms Exception %s' % ex)

        # for line in cmdlines:
        #     if line:
        #         if line[-2:] == '\r\n':
        #             line = line[:-2]
        #         elif line[-1] == '\n':
        #             line = line[:-1]
        #         self.dc.writeline(line)
        #         r = self.repl.read()
        #         if r:
        #             self.sres('[duringwriting] ')
        #             self.sres(str(r))
        #
        # if not bsuppressendcode:
        #     self.dc.writebytes(b'\r\x04')
        #     self.dc.receivestream(bseekokay=True)
        
    def sendcommand(self, cellcontents):
        bsuppressendcode = False  # can't yet see how to get this signal through
        
        if self.srescapturedoutputfile:
            self.srescapturedoutputfile.close()   # shouldn't normally get here
            self.sres("closing stuck open srescapturedoutputfile\n")
            self.srescapturedoutputfile = None
            
        # extract any %-commands we have here at the start (or ending?), tolerating pure comment lines and white space before the first % (if there's no %-command in there, then no lines at the front get dropped due to being comments)
        while True:
            mpercentline = re.match("(?:(?:\s*|(?:\s*#.*\n))*)(%.*)\n?(?:[ \r]*\n)?", cellcontents)
            if not mpercentline:
                break
            cellcontents = self.interpretpercentline(mpercentline.group(1), cellcontents[mpercentline.end():])   # discards the %command and a single blank line (if there is one) from the cell contents
            if cellcontents is None:
                return
                
        if not (self.repl and self.repl.connected):
            self.sres("No serial connected\n", 31)
            self.sres("  %connect to connect\n")
            self.sres("  %lsmagic to list commands")
            return
            
        # run the cell contents as normal
        if cellcontents:
            self.runnormalcell(cellcontents, bsuppressendcode)
            
    def sresSYS(self, output, clear_output=False):   # system call
        self.sres(output, asciigraphicscode=34, clear_output=clear_output)
    # 1=bold, 31=red, 32=green, 34=blue; from http://ascii-table.com/ansi-escape-sequences.php

    def sres(self, output, asciigraphicscode=None, n04count=0, clear_output=False):
        output = output.decode() if isinstance(output, bytes) else output
        if self.silent:
            return
            
        if self.srescapturedoutputfile and (n04count == 0) and not asciigraphicscode:
            self.srescapturedoutputfile.write(output)
            self.srescapturedlinecount += len(output.split("\n"))-1
            if self.srescapturemode == 3:            # 0 none, 1 print lines, 2 print on-going line count (--quiet), 3 print only final line count (--QUIET)
                return
                
            # changes the printing out to a lines captured statement every 1second.  
            if self.srescapturemode == 2:  # (allow stderrors to drop through to normal printing
                srescapturedtime = time.time()
                if srescapturedtime < self.srescapturedlasttime + 1:   # update no more frequently than once a second
                    return
                self.srescapturedlasttime = srescapturedtime
                clear_output = True
                output = "{} lines captured".format(self.srescapturedlinecount)

        if clear_output:  # used when updating lines printed
            self.send_response(self.iopub_socket, 'clear_output', {"wait":True})
        if asciigraphicscode:
            output = "\x1b[{}m{}\x1b[0m".format(asciigraphicscode, output)
        stream_content = {'name': ("stdout" if n04count == 0 else "stderr"), 'text': output}
        self.send_response(self.iopub_socket, 'stream', stream_content)

    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        self.silent = silent
        if not code.strip():
            return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [], 'user_expressions': {}}

        interrupted = False
        
        # # clear buffer out before executing any commands (except the readbytes one)
        # if self.repl and self.repl.connected and not re.match("\s*%readbytes|\s*%disconnect|\s*%connect|\s*websocketconnect", code):
        #     priorbuffer = None
        #     try:
        #         priorbuffer = self.repl.read()
        #     except KeyboardInterrupt:
        #         interrupted = True
        #     except OSError as e:
        #         priorbuffer = []
        #         self.sres("\n\n***Connection broken [%s]\n" % str(e.strerror), 31)
        #         self.sres("You may need to reconnect")
        #     except (pyboard.PyboardError, Exception) as e:
        #         priorbuffer = []
        #         self.sres("\n\n***Exception [%s]\n" % str(e), 31)
        #         self.sres("You may need to reconnect")
        #
        #     if priorbuffer:
        #         if isinstance(priorbuffer, bytes):
        #             try:
        #                 priorbuffer = priorbuffer.decode()
        #             except UnicodeDecodeError:
        #                 priorbuffer = str(priorbuffer)
        #
        #         for pbline in priorbuffer.splitlines():
        #             if wifimessageignore.match(pbline):
        #                 continue   # filter out boring wifi status messages
        #             if pbline:
        #                 self.sres('[leftinbuffer] ')
        #                 self.sres(str([pbline]))
        #                 self.sres('\n')

        try:
            if not interrupted:
                self.sendcommand(code)
        except KeyboardInterrupt:
            interrupted = True
        except OSError as e:
            self.sres("\n\n***OSError [%s]\n\n" % str(e.strerror))
        #except pexpect.EOF:
        #    self.sres(self.asyncmodule.before + 'Restarting Bash')
        #    self.startasyncmodule()

        if self.srescapturedoutputfile:
            if self.srescapturemode == 2:
                self.send_response(self.iopub_socket, 'clear_output', {"wait":True})
            if self.srescapturemode == 2 or self.srescapturemode == 3:
                output = "{} lines captured.".format(self.srescapturedlinecount)  # finish off by updating with the correct number captured
                stream_content = {'name': "stdout", 'text': output }
                self.send_response(self.iopub_socket, 'stream', stream_content)
                
            self.srescapturedoutputfile.close()
            self.srescapturedoutputfile = None
            self.srescapturemode = 0
            
        if interrupted:
            self.sresSYS("\n\n*** Sending Ctrl-C\n\n")
            if self.repl and self.repl.connected:
                self.repl.write(b'\r\x03\x03')
                interrupted = True
                try:
                    self.repl.read(timeout=5)
                    # self.dc.receivestream(bseekokay=False, b5secondtimeout=True)
                except KeyboardInterrupt:
                    self.sres("\n\nKeyboard interrupt while waiting response on Ctrl-C\n\n")
                except OSError as e:
                    self.sres("\n\n***OSError while issuing a Ctrl-C [%s]\n\n" % str(e.strerror))
            return {'status': 'abort', 'execution_count': self.execution_count}
            
        # everything already gone out with send_response(), but could detect errors (text between the two \x04s

        return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [], 'user_expressions': {}}
