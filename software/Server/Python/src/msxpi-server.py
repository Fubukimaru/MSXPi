# External module imports
import RPi.GPIO as GPIO
import time
import subprocess
import urllib
from HTMLParser import HTMLParser

version = 0.1
build   = 20171110

# Pin Definitons
csPin   = 21
sclkPin = 20
mosiPin = 16
misoPin = 12
rdyPin  = 25

SPI_SCLK_LOW_TIME = 0.001
SPI_SCLK_HIGH_TIME = 0.001

GLOBALRETRIES       =    5
SPI_INT_TIME        =    3000
PIWAITTIMEOUTOTHER  =    120     # seconds
PIWAITTIMEOUTBIOS   =    60      # seconds
SYNCTIMEOUT         =    5
BYTETRANSFTIMEOUT   =    5
SYNCTRANSFTIMEOUT   =    3
STARTTRANSFER       = 0xA0
SENDNEXT            = 0xA1
ENDTRANSFER         = 0xA2
READY               = 0xAA
ABORT               = 0xAD
WAIT                = 0xAE

RC_SUCCESS          =    0xE0
RC_INVALIDCOMMAND   =    0xE1
RC_CRCERROR         =    0xE2
RC_TIMEOUT          =    0xE3
RC_INVALIDDATASIZE  =    0xE4
RC_OUTOFSYNC        =    0xE5
RC_FILENOTFOUND     =    0xE6
RC_FAILED           =    0xE7
RC_INFORESPONSE     =    0xE8
RC_WAIT             =    0xE9
RC_READY            =    0xEA
RC_SUCCNOSTD        =    0XEB
RC_FAILNOSTD        =    0XEC
RC_UNDEFINED        =    0xEF

st_init             =    0       # waiting loop, waiting for a command
st_cmd              =    1       # transfering data for a command
st_recvdata         =    2
st_senddata         =    4
st_synch            =    5       # running a command received from MSX
st_runcmd           =    6
st_shutdown         =    99

NoTimeOutCheck      = False
TimeOutCheck        = True

def init_spi_bitbang():
# Pin Setup:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(csPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(sclkPin, GPIO.OUT)
    GPIO.setup(mosiPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(misoPin, GPIO.OUT)
    GPIO.setup(rdyPin, GPIO.OUT)

def tick_sclk():
    GPIO.output(sclkPin, GPIO.HIGH)
    #time.sleep(SPI_SCLK_HIGH_TIME)
    GPIO.output(sclkPin, GPIO.LOW)
    #time.sleep(SPI_SCLK_LOW_TIME)

def SPI_MASTER_transfer_byte(byte_out):
    #print "transfer_byte:sending",hex(byte_out)
    byte_in = 0
    tick_sclk();
    for bit in [0x80,0x40,0x20,0x10,0x8,0x4,0x2,0x1]:
        if (byte_out & bit):
            GPIO.output(misoPin, GPIO.HIGH)
        else:
            GPIO.output(misoPin, GPIO.LOW)

        GPIO.output(sclkPin, GPIO.HIGH)
        #time.sleep(SPI_SCLK_HIGH_TIME)
        
        if GPIO.input(mosiPin):
            byte_in |= bit
    
        GPIO.output(sclkPin, GPIO.LOW)
        #time.sleep(SPI_SCLK_LOW_TIME)

    tick_sclk();
    #print "transfer_byte:received",hex(byte_in),":",chr(byte_in)
    return byte_in

def piexchangebyte(checktimeout,mypibyte):
    time_start = time.time()
    timeout = False
    rc = RC_SUCCESS
    
    GPIO.output(rdyPin, GPIO.HIGH)
    #GPIO.wait_for_edge(csPin, GPIO.FALLING)
    if (checktimeout):
        while(GPIO.input(csPin)):
            if (time.time() - time_start > BYTETRANSFTIMEOUT):
                timeout = True
    else:
        while(GPIO.input(csPin)):
            ()

    mymsxbyte = SPI_MASTER_transfer_byte(mypibyte);
    GPIO.output(rdyPin, GPIO.LOW)

    if (timeout):
        rc = RC_TIMEOUT

    return [rc,mymsxbyte]

def senderror(rc, message):
    piexchangebyte(False,rc)
    return senddatablock(True,message,len(message),True);

def recvdatablock(checktimeout):
    buffer = bytearray()
    bytecounter = 0
    crc = 0
    rc = RC_SUCCESS
    
    mymsxbyte = piexchangebyte(False,SENDNEXT)
    if (mymsxbyte[1] != SENDNEXT):
        print "recvdatablock:Out of sync with MSX, waiting SENDNEXT, received",mymsxbyte
        rc = RC_OUTOFSYNC;
    else:
        dsL = piexchangebyte(True,SENDNEXT)
        dsM = piexchangebyte(True,SENDNEXT)
        datasize = dsL[1] + 256 * dsM[1]
        
        #print "recvdatablock:Received blocksize =",datasize;
        while(datasize>bytecounter and rc == RC_SUCCESS):
            mymsxbyte = piexchangebyte(False,SENDNEXT)
            if (mymsxbyte[0] == RC_SUCCESS):
                #print "recvdatablock:Received byte:",chr(mymsxbyte[1]);
                buffer.append(mymsxbyte[1])
                crc ^= mymsxbyte[1]
                bytecounter += 1
            else:
                print "recvdatablock:Error during transfer"
                rc = RC_TIMEOUT

    if (rc == RC_SUCCESS):
        #print "crc = ",crc
        mymsxbyte = piexchangebyte(False,crc)
        if (mymsxbyte[1] != crc):
            rc = RC_CRCERROR
        #else:
            #print "recvdatablock:CRC verified"

    print "recvdatablock:exiting with rc = ",hex(rc)
    return [rc,buffer]

def senddatablock(checktimeout,buffer,datasize,sendsize):
    #buffer = bytearray()
    bytecounter = 0
    crc = 0
    rc = RC_SUCCESS
    
    mymsxbyte = piexchangebyte(False,SENDNEXT)
    if (mymsxbyte[1] != SENDNEXT):
        print "senddatablock:Out of sync with MSX, waiting SENDNEXT, received",mymsxbyte
        rc = RC_OUTOFSYNC;
    else:
        if (sendsize):
            print "senddatablock:Sending blocksize ",datasize
            piexchangebyte(True,datasize % 256)
            piexchangebyte(True,datasize / 256)
    
        while(datasize>bytecounter and rc == RC_SUCCESS):
            mypibyte = ord(buffer[bytecounter])
            #print "senddatablock:",mypibyte
            mymsxbyte = piexchangebyte(True,mypibyte)
            if (mymsxbyte[0] == RC_SUCCESS):
                #print "senddatablock:byte sent successfully"
                crc ^= mypibyte
                bytecounter += 1
            else:
                print "senddatablock:Error during transfer"
                rc = RC_TIMEOUT

    if (rc == RC_SUCCESS):
        mymsxbyte = piexchangebyte(False,crc)
        print "senddatablock:CRC local:remote = ",crc,":",mymsxbyte[1]
        if (mymsxbyte[1] != crc):
            rc = RC_CRCERROR;
        #else:
        #    print "senddatablock:CRC verified"

    print "senddatablock:Exiting with rc=",hex(rc)
    return rc

def runpicmd(msxcommand):
    #print "runpicmd:starting command:",msxcommand
    msxcommand = msxcommand.decode().split(" ")
    piexchangebyte(False,RC_WAIT);
    buf = subprocess.check_output(msxcommand)
    #print "runpicmd:result is ",buf
    #print "runpicmd:Sending output to MSX. Size is:",len(buf)
    piexchangebyte(False,RC_SUCCESS);
    rc = senddatablock(True,buf,len(buf),True);

    print "runpicmd:exiting rc:",hex(rc)
    return rc;

def secsenddata(basepath, file):
    rc = RC_SUCCESS
    
    print "ploadrom:starting"
    
    msxbyte = piexchangebyte(False,RC_WAIT)
    if (msxbyte[1]==SENDNEXT):
        file = file.decode().split(" ")
        if (file[0] <> ""):
            filepath = basepath + "/" + file[0]
            print "ploadrom:full file path is:",filepath
            
            try:
                fh = open(filepath, 'rb')
                buf = fh.read()
                fh.close()
                
                filesize = len(buf)
                
                print "ploadrom:len of buf:",filesize
                
                if (buf[0]=='A' and buf[1]=='B'):
                    msxbyte = piexchangebyte(False,RC_SUCCNOSTD)
                    if (msxbyte[1]==SENDNEXT):
                        
                        msxbyte = piexchangebyte(False,STARTTRANSFER)
                        if (msxbyte[1]==STARTTRANSFER):
                            piexchangebyte(True,filesize % 256)
                            piexchangebyte(True,filesize / 256)
                            
                            if (filesize>512):
                                blocksize = 512
                            else:
                                blocksize = filesize
                        
                            index = 0
                            retries = 0
                            while(blocksize and retries <= GLOBALRETRIES):
                                retries = 0
                                rc = RC_UNDEFINED
                                
                                lastindex = index+blocksize
                                
                                while(retries < GLOBALRETRIES and rc <> RC_SUCCESS):
                                    print "ploadrom:sending block:blocksize ",index,":",blocksize
                                    print "ploadrom:data range:",index,":",lastindex
                                    rc = senddatablock(True,buf[index:lastindex],blocksize,True)
                                    retries += 1

                                index += blocksize
                                if (filesize - index > 512):
                                    blocksize = 512
                                else:
                                    blocksize = filesize - index
                                                                
                            if(retries>=GLOBALRETRIES):
                                print "load:Transfer interrupted due to CRC error"
                                rc = ABORT
                                senderror(rc,"Pi:CRC Error")
                            else:
                                print "ploadrom:successful"
                                rc = RC_SUCCESS
                                senderror(rc,"Pi:Ok")
                        else:
                            rc = RC_FAILED
                            senderror(rc,"ploadrom:out of sync in STARTTRANSFER")
                    else:
                        rc = RC_FAILED;
                        print "ploadrom:out of sync: RC_SUCCNOSTD"
                else:
                    print "ploadrom::Not a .rom program. Aborting"
                    rc = RC_FAILED
                    senderror(rc,"Pi:Not a .rom file")
        
            except IOError:
                rc = RC_FAILED
                print "Error opening file"
                senderror(rc,"Pi:Error opening file")
        else:
            print "ploadrom:syntax error in command"
            rc = RC_FAILED
            senderror(rc,"Pi:Missing parameters.\nSyntax:\nploadrom file|url <A:>|<B:>file")
    else:
        print "ploadrom:out of sync"
        piexchangebyte(False,RC_FAILNOSTD)
        rc = RC_FAILNOSTD

    print "ploadrom:Exiting with rc = ",hex(rc)

def ploadr(basepath, file):
    rc = RC_SUCCESS
    
    print "pload:starting"
    
    msxbyte = piexchangebyte(False,RC_WAIT)
    if (msxbyte[1]==SENDNEXT):
        file = file.decode().split(" ")
        if (file[0] <> ""):
            filepath = basepath + "/" + file[0]
            print "pload:full file path is:",filepath
            
            try:
                fh = open(filepath, 'rb')
                buf = fh.read()
                fh.close()
                
                print "pload:len of buf:",len(buf)
                
                if (buf[0]=='A' and buf[1]=='B'):
                    msxbyte = piexchangebyte(False,RC_SUCCNOSTD)
                    if (msxbyte[1]==SENDNEXT):
                        
                        msxbyte = piexchangebyte(False,STARTTRANSFER)
                        if (msxbyte[1]==STARTTRANSFER):
                            rc = senddatablock(True,buf,len(buf),True)
                        if (rc == RC_SUCCESS):
                            print "pload:successful"
                            senderror(rc,"Pi:Ok")
                        else:
                            rc = RC_FAILED
                            senderror(rc,"pload:out of sync in STARTTRANSFER")
    
            except IOError:
                rc = RC_FAILED
                print "Error opening file"
                senderror(rc,"Pi:Error opening file")
        else:
            print "pload:syntax error in command"
            rc = RC_FAILED
            senderror(rc,"Pi:Missing parameters.\nSyntax:\nploadrom file|url <A:>|<B:>file")

    print "pload:Exiting with rc = ",hex(rc)

def getpath(basepath, path):
    if  path.startswith('/'):
        urltype = 0 # this is an absolute local path
        newpath = path
    elif (path.startswith('http') or \
          path.startswith('ftp') or \
          path.startswith('nfs') or \
          path.startswith('smb')):
        urltype = 1 # this is an absolute network path
        newpath = path
    elif basepath.startswith('/'):
        urltype = 2 # this is an absolute local path
        newpath = basepath + "/" + path
    elif (basepath.startswith('http') or \
          basepath.startswith('ftp') or \
          basepath.startswith('nfs') or \
          basepath.startswith('smb')):
        urltype = 3 # this is an absolute network path
        newpath = basepath + "/" + path

    return [urltype, newpath]

# create a subclass and override the handler methods
class MyHTMLParser(HTMLParser):
    def __init__(self):
        self.reset()
        self.NEWTAGS = []
        self.NEWATTRS = []
        self.HTMLDATA = []
    def handle_starttag(self, tag, attrs):
        self.NEWTAGS.append(tag)
        self.NEWATTRS.append(attrs)
    def handle_data(self, data):
        self.HTMLDATA.append(data)
    def clean(self):
        self.NEWTAGS = []
        self.NEWATTRS = []
        self.HTMLDATA = []

def pdir(basepath, path):
    rc = RC_SUCCESS
    print "pdir:starting"

    msxbyte = piexchangebyte(False,RC_WAIT)
    urltype = 1 # realtive path is assumed default
    if (msxbyte[1]==SENDNEXT):
        urlcheck = getpath(basepath, path)
        if (urlcheck[0] == 0 or urlcheck[0] == 2):
            cmd = "ls -l " +  urlcheck[1]
            cmd = cmd.decode().split(" ")
            buf = subprocess.check_output(cmd)
            piexchangebyte(False,RC_SUCCESS);
            rc = senddatablock(True,buf,len(buf),True);
        else:
            #cmd = "/usr/bin/wget --no-check-certificate  -O /tmp/msxpifile1.tmp -o /tmp/msxpi_error.log " +  urltype[1]
            print "pdir:network access:"+urlcheck[1].decode()
            parser = MyHTMLParser()
            htmldata = urllib.urlopen(urlcheck[1].decode()).read()
            parser = MyHTMLParser()
            parser.feed(htmldata)
            buf = " ".join(parser.HTMLDATA)
            print buf
            piexchangebyte(False,RC_SUCCESS);
            rc = senddatablock(True,buf,len(buf),True);
    else:
        rc = RC_FAILNOSTD
        print "pdir:out of sync in RC_WAIT"

    print "runpicmd:exiting rc:",hex(rc)
    return rc;


init_spi_bitbang()
GPIO.output(rdyPin, GPIO.LOW)

print "GPIO Initialized\n"
print "Starting MSXPi Server Version ",version,"Build",build

psetvar = [['PATH','/home/msxpi'], \
           ['DRIVE0','disks/msxpiboot.dsk'], \
           ['DRIVE1','disks/msxpitools.dsk'], \
           ['WIDTH','80'], \
           ['free',''], \
           ['WIFISSID','MYWIFI'], \
           ['WIFIPWD','MYWFIPASSWORD'], \
           ['DSKTMPL','disks/msxpi_720KB_template.dsk'], \
           ['free',''], \
           ['free',''] \
           ]

appstate = st_init

try:
    while (appstate != st_shutdown):
        if (appstate == st_init):
            print "Entered init state. Syncying with MSX..."
            appstate = st_cmd

        if (appstate == st_cmd):
            print "st_recvcmd: waiting command"
            rc = recvdatablock(NoTimeOutCheck);

            if (rc[0] == RC_SUCCESS):
                print "Received command ",rc[1]
                appstate = st_runcmd
            else:
                print "Erro receiving command:",rc[0]
                    
        if (appstate == st_runcmd):
            msxcommand = rc[1]
            print "st_runcmd:",msxcommand
            if (msxcommand[:4] == "prun" or msxcommand[:4] == "PRUN"):
                runpicmd(msxcommand[5:])
                appstate = st_cmd
            if (msxcommand[:8] == "ploadrom" or msxcommand[:8] == "PLOADROM"):
                ploadrom(psetvar[0][1],msxcommand[9:])
                appstate = st_cmd
            if (msxcommand[:6] == "ploadr" or msxcommand[:6] == "PLOADR"):
                ploadr(psetvar[0][1],msxcommand[7:])
                appstate = st_cmd
            if (msxcommand[:4] == "pdir" or msxcommand[:4] == "PDIR"):
                pdir(psetvar[0][1],msxcommand[5:])
                appstate = st_cmd
                
        if (appstate == st_runcmd):
            print "Error"
            piexchangebyte(False,RC_FAILNOSTD)

        appstate = st_cmd

except KeyboardInterrupt:
    GPIO.cleanup() # cleanup all GPIO
    print "Terminating msxpi-server"

