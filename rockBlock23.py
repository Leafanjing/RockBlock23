from __future__ import print_function
from __future__ import division
from builtins import chr
from builtins import str
from builtins import range
from builtins import bytes
# from past.utils import old_div
from builtins import object
import glob
import signal
import sys
import time

import serial


class rockBlockProtocol(object):

    def rockBlockConnected(self): pass

    def rockBlockDisconnected(self): pass

    # SIGNAL
    def rockBlockSignalUpdate(self, signal): pass

    def rockBlockSignalPass(self): pass

    def rockBlockSignalFail(self): pass

    # MT
    def rockBlockRxStarted(self): pass

    def rockBlockRxFailed(self): pass

    def rockBlockRxReceived(self, mtmsn, data): pass

    def rockBlockRxMessageQueue(self, count): pass

    # MO
    def rockBlockTxStarted(self): pass

    def rockBlockTxFailed(self):
        print("Failure")

    def rockBlockTxSuccess(self, momsn): pass


class rockBlockException(Exception):
    pass


class rockBlock(object):
    IRIDIUM_EPOCH = 1399818235000  # May 11, 2014, at 14:23:55 (This will be 're-epoched' every couple of years!)

    def __init__(self, portId, callback):

        self.s = None
        self.portId = portId
        self.callback = callback
        self.autoSession = True
        # When True, we'll automatically initiate additional sessions if more messages to download

        try:

            self.s = serial.Serial(self.portId, 19200, timeout=5)

            if (self._configurePort()):

                self.ping()  # KEEP SACRIFICIAL!

                self.s.timeout = 60

                if (self.ping()):

                    if (self.callback != None and callable(self.callback.rockBlockConnected)):
                        self.callback.rockBlockConnected()

                        return

            self.close()
            raise rockBlockException()

        except (Exception):

            raise rockBlockException

    # Ensure that the connection is still alive
    def ping(self):
        self._ensureConnectionStatus()

        command = "AT"

        self.s.write(f"{command}\r".encode())

        if (self.s.readline().decode().strip() == command):

            if (self.s.readline().decode().strip() == "OK"):
                return True

        return False

    # Handy function to check the connection is still alive, else throw an Exception
    def pingception(self):
        self._ensureConnectionStatus()

        self.s.timeout = 5
        if (self.ping() == False):
            raise rockBlockException

        self.s.timeout = 60

    def requestSignalStrength(self):
        print("113 start requestSignalStrength")
        self._ensureConnectionStatus()

        command = "AT+CSQ"

        self.s.write(f"{command}\r".encode())
        print("119 start readline if statement")
        if (self.s.readline().decode.strip() == command):
            print("121 after readline if statement")
            response = self.s.readline().decode().strip()

            if (response.find("+CSQ") >= 0):
                print("125 if statement passed")
                self.s.readline().decode().strip()  # OK
                self.s.readline().decode().strip()  # BLANK

                if (len(response) == 6):
                    print("130 length of response was equal to 6 returning response[5]")
                    return int(response[5])

        print("133 bad signal returning -1")
        return -1

    def messageCheck(self):
        self._ensureConnectionStatus()

        if (self.callback != None and callable(self.callback.rockBlockRxStarted)):
            self.callback.rockBlockRxStarted()

        if (self._attemptConnection() and self._attemptSession()):

            return True

        else:

            if (self.callback != None and callable(self.callback.rockBlockRxFailed)):
                self.callback.rockBlockRxFailed()

    def networkTime(self):
        self._ensureConnectionStatus()

        command = "AT-MSSTM"

        self.s.write(f"{command}\r".encode())

        if (self.s.readline().decode().strip() == command):

            response = self.s.readline().decode().strip()

            self.s.readline().decode().strip()  # BLANK
            self.s.readline().decode().strip()  # OK

            if (not "no network service" in response):

                utc = int(response[8:], 16)

                utc = int(((self.IRIDIUM_EPOCH + (utc * 90)), 1000))

                return utc

            else:

                return 0;

    def sendMessage(self, msg):
        self._ensureConnectionStatus()

        if (self.callback != None and callable(self.callback.rockBlockTxStarted)):
            self.callback.rockBlockTxStarted()
            print("179 starting if check on sendMessage")
        try:
            print("181 before queueMessage and AttemptConnection")
            if (self._queueMessage(msg) and self._attemptConnection()):
                print("182 while true section")

                SESSION_DELAY = 1
                SESSION_ATTEMPTS = 3

                while (True):
                    print("188 subtracting session_attempts")
                    SESSION_ATTEMPTS = SESSION_ATTEMPTS - 1

                    if (SESSION_ATTEMPTS == 0):
                        print("192 broke becuase of 0 attempts left")
                        break

                    if (self._attemptSession()):

                        return True

                    else:

                        time.sleep(SESSION_DELAY)

        except Exception as e: print(f"203 sendMessage error {e}")

        if (self.callback != None and callable(self.callback.rockBlockTxFailed)):
            self.callback.rockBlockTxFailed()

        return False

    def getSerialIdentifier(self):
        self._ensureConnectionStatus()

        command = "AT+GSN"

        self.s.write(f"{command}\r".encode())

        if (self.s.readline().decode().strip() == command):
            response = self.s.readline().decode().strip()

            self.s.readline().decode().strip()  # BLANK
            self.s.readline().decode().strip()  # OK

            return response

    # One-time initial setup function (Disables Flow Control)
    # This only needs to be called once, as is stored in non-volitile memory

    # Make sure you DISCONNECT RockBLOCK from power for a few minutes after this command has been issued...
    def setup(self):
        self._ensureConnectionStatus()

        # Disable Flow Control
        command = "AT&K0"

        self.s.write(f"{command}\r".encode())

        if (self.s.readline().decode().strip() == command and self.s.readline().decode().strip() == "OK"):

            # Store Configuration into Profile0
            command = "AT&W0"

            self.s.write(f"{command}\r".encode())

            if (self.s.readline().decode().strip() == command and self.s.readline().decode().strip() == "OK"):

                # Use Profile0 as default
                command = "AT&Y0"

                self.s.write(f"{command}\r".encode())

                if (self.s.readline().decode().strip() == command and self.s.readline().decode().strip() == "OK"):

                    # Flush Memory
                    command = "AT*F"

                    self.s.write(f"{command}\r".encode())

                    if (self.s.readline().decode().strip() == command and self.s.readline().decode().strip() == "OK"):
                        # self.close()

                        return True

        return False

    def close(self):

        if (self.s != None):
            self.s.close()
            self.s = None

    @staticmethod
    def listPorts():

        if sys.platform.startswith('win'):

            ports = ['COM' + str(i + 1) for i in range(256)]

        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):

            ports = glob.glob('/dev/tty[A-Za-z]*')

        elif sys.platform.startswith('darwin'):

            ports = glob.glob('/dev/tty.*')

        result = []

        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass

        return result

    # Private Methods - Don't call these directly!
    def _queueMessage(self, msg):
        try:
            self._ensureConnectionStatus()

            if (len(msg) > 340):
                print("sendMessageWithBytes bytes should be <= 340 bytes")

                return False

            command = f"AT+SBDWB={len(msg)}"

            self.s.write(f"{command}\r".encode())
            # print("directly before the strip function")
            try:
                if (self.s.readline().decode().strip() == command):
                    # print("after strip function")
                    try:
                        # print("before READY check")
                        if (self.s.readline().decode().strip() == "READY"):

                            checksum = 0

                            for c in msg:
                                self.s.write(ord(c))
                                checksum += ord(c)

                            # self.s.write(msg.encode())

                            self.s.write(checksum >> 8)
                            self.s.write(checksum & 0xFF)


                            self.s.readline().decode().strip()  # BLANK

                            result = False

                            resTest = self.s.readline().decode().strip()

                            if (resTest == "0"):
                                result = True
                            print(f"339 command response message {resTest}")

                            self.s.readline().decode().strip()  # BLANK
                            self.s.readline().decode().strip()  # OK

                            print("345 queue message done returning result")
                            return result

                    except Exception as e:
                        print(f"try block looking for READY: {e}")
            except Exception as e:
                print(f"try block before readline/strip looking for command{e}")

        except Exception as e:
            print(f"Queue Message error: {e}")

        return False

    def _configurePort(self):

        if (self._enableEcho() and self._disableFlowControl and self._disableRingAlerts() and self.ping()):

            return True

        else:

            return False

    def _enableEcho(self):
        self._ensureConnectionStatus()

        command = "ATE1"

        self.s.write(f"{command}\r".encode())

        response = self.s.readline().decode().strip()

        if (response == command or response == ""):

            if (self.s.readline().decode().strip() == "OK"):
                return True

        return False

    def _disableFlowControl(self):
        self._ensureConnectionStatus()

        command = "AT&K0"

        self.s.write(f"{command}\r".encode())

        if (self.s.readline().decode().strip() == command):

            if (self.s.readline().decode().strip() == "OK"):
                return True

        return False

    def _disableRingAlerts(self):
        self._ensureConnectionStatus()

        command = "AT+SBDMTA=0"

        self.s.write(f"{command}\r".encode())

        if (self.s.readline().decode().strip() == command):

            if (self.s.readline().decode().strip() == "OK"):
                return True

        return False

    def _attemptSession(self):
        self._ensureConnectionStatus()

        SESSION_ATTEMPTS = 3

        while (True):

            if (SESSION_ATTEMPTS == 0):
                return False

            SESSION_ATTEMPTS = SESSION_ATTEMPTS - 1

            command = "AT+SBDIX"

            self.s.write(f"{command}\r".encode())

            if (self.s.readline().decode().strip() == command):

                response = self.s.readline().decode().strip()

                if (response.find("+SBDIX:") >= 0):

                    self.s.readline().decode().strip()  # BLANK
                    self.s.readline().decode().strip()  # OK

                    response = response.replace("+SBDIX: ","")
                    # +SBDIX:<MO status>,<MOMSN>,<MT status>,<MTMSN>,<MT length>,<MTqueued>

                    parts = response.split(",")

                    moStatus = int(parts[0])
                    moMsn = int(parts[1])
                    mtStatus = int(parts[2])
                    mtMsn = int(parts[3])
                    mtLength = int(parts[4])
                    mtQueued = int(parts[5])

                    # Mobile Originated
                    if (moStatus <= 4):

                        self._clearMoBuffer()

                        if (self.callback != None and callable(self.callback.rockBlockTxSuccess)):
                            self.callback.rockBlockTxSuccess(moMsn)

                        pass

                    else:

                        if (self.callback != None and callable(self.callback.rockBlockTxFailed)):
                            self.callback.rockBlockTxFailed()

                    if (mtStatus == 1 and mtLength > 0):  # SBD message successfully received from the GSS.

                        self._processMtMessage(mtMsn)

                    # AUTOGET NEXT MESSAGE

                    if (self.callback != None and callable(self.callback.rockBlockRxMessageQueue)):
                        self.callback.rockBlockRxMessageQueue(mtQueued)

                    # There are additional MT messages to queued to download
                    if (mtQueued > 0 and self.autoSession == True):
                        self._attemptSession()

                    if (moStatus <= 4):
                        return True

        return False

    def _attemptConnection(self):
        print("482 attempt connnection started")
        self._ensureConnectionStatus()

        TIME_ATTEMPTS = 20
        TIME_DELAY = 1

        SIGNAL_ATTEMPTS = 10
        RESCAN_DELAY = 10
        SIGNAL_THRESHOLD = 2

        print(" 492 attempt connection 2")
        # Wait for valid Network Time
        while True:
            print("495 while true started")
            if (TIME_ATTEMPTS == 0):
                print("497 time_attempts = 0")
                if (self.callback != None and callable(self.callback.rockBlockSignalFail)):
                    print("issue 1")
                    self.callback.rockBlockSignalFail()

                return False

            if (self._isNetworkTimeValid()):
                print("505 break 1")
                break

            TIME_ATTEMPTS = TIME_ATTEMPTS - 1;

            time.sleep(TIME_DELAY)
        print("512 starting second while true statement attemptConnection")
        # Wait for acceptable signal strength
        while True:
            print("515 requesting signal strength")
            signal = self.requestSignalStrength()
            print(f"516 while true started {signal}")
            if (SIGNAL_ATTEMPTS == 0 or signal < 0):

                print("NO SIGNAL")

                if (self.callback != None and callable(self.callback.rockBlockSignalFail)):
                    print(" 522 if failure 1")
                    self.callback.rockBlockSignalFail()

                return False

            self.callback.rockBlockSignalUpdate(signal)

            if (signal >= SIGNAL_THRESHOLD):

                if (self.callback != None and callable(self.callback.rockBlockSignalPass)):
                    self.callback.rockBlockSignalPass()

                return True;

            SIGNAL_ATTEMPTS = SIGNAL_ATTEMPTS - 1

            time.sleep(RESCAN_DELAY)

    def _processMtMessage(self, mtMsn):
        self._ensureConnectionStatus()

        self.s.write("AT+SBDRB\r")

        response = self.s.readline().decode().strip().replace("AT+SBDRB\r", "").strip()

        if (response == "OK"):

            print("No message content.. strange!")

            if (self.callback != None and callable(self.callback.rockBlockRxReceived)):
                self.callback.rockBlockRxReceived(mtMsn, "")

        else:

            content = response[2:-2]

            if (self.callback != None and callable(self.callback.rockBlockRxReceived)):
                self.callback.rockBlockRxReceived(mtMsn, content)

            self.s.readline().decode().strip()  # BLANK?

    def _isNetworkTimeValid(self):
        self._ensureConnectionStatus()

        command = "AT-MSSTM"

        self.s.write(f"{command}\r".encode())

        if (self.s.readline().decode().strip() == command):  # Echo

            response = self.s.readline().decode().strip()

            if (response.startswith("-MSSTM")):  # -MSSTM: a5cb42ad / no network service

                self.s.readline().decode()  # OK
                self.s.readline().decode()  # BLANK

                if (len(response) == 16):
                    print("581 isNetworkTimeValid returning true")
                    return True

        print("584 isNetworkTimeValid returning False")
        return False

    def _clearMoBuffer(self):
        self._ensureConnectionStatus()

        command = "AT+SBDD0"

        self.s.write(f"{command}\r".encode())

        if (self.s.readline().decode().strip() == command):

            if (self.s.readline().decode().strip() == "0"):

                self.s.readline().decode().strip()  # BLANK

                if (self.s.readline().decode().strip() == "OK"):
                    return True

        return False

    def _ensureConnectionStatus(self):
        if (self.s == None or self.s.isOpen() == False):
            print("ensureConnectionStatus failed")
            raise rockBlockException()