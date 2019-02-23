import serial
from time import sleep
import platform
import logging
from enum import Enum
from collections import defaultdict


class Emulator:

        def __init__(self,port=None):
            self.logger = logging.getLogger(__name__)
            self.current_packet = Packet()

            if port == None:
                self.find_serial()
            else:
                self.logger.info('Printer on {} you say?'.format(port))
                self.gbp_serial = serial.Serial(port,baudrate=115200,timeout=.2)
            self.logger.info('sleep for 2 seconds to prep serial...')
            sleep(2)


        def find_serial(self):
            opsys = platform.system()
            if opsys == 'Windows':
                ports = ['COM%s' % (i + 1) for i in range(2,256)]
            elif opsys == 'Linux':
                ports = glob.glob('/dev/tty[A-Za-z]*')
            elif opsys == 'Darwin':
                ports = glob.glob('/dev/tty.*')
            else:
                raise EnvironmentError('Not Windows, Mac, or Linux, dunno where your serial ports would be')

            for port in ports:
                try:
                    self.gbp_serial = serial.Serial(port,baudrate=115200,timeout=.2)
                    self.logger.info('Arduino (I assume) found on port {}'.format(port))
                    break
                except (OSError, serial.SerialException):
                    pass

        def get_gb_data(self):
            packet = self.current_packet
            from_gb = self.gbp_serial.read(4)
            if from_gb:
                rx,tx,ard_state,data_remain = from_gb
                        
                packet.add_byte(rx)

                #print('Byte received: {}, Packet status: {}'.format(rx,packet.status.name))

                if packet.status == Status.COMPLETE:
                    print('Packet complete, type {}, data size {}'.format(packet.type,packet.data_size))
                    if packet.data_size == 4:
                        print('Print data 0x{:02x} 0x{:02x} 0x{:02x} 0x{:02x}'.format(*packet.data))
                    print('Checksum is {}'.format(self.current_packet.verify_checksum()))
                    self.current_packet = Packet()

class Status(Enum):
    EMPTY = 0
    PREAMBLE_PARTIAL = 1
    PREAMBLE_DONE = 2
    HEADER_PARTIAL = 3
    HEADER_DONE = 4
    DATA_PARTIAL = 5
    DATA_DONE = 6
    CHECKSUM_PARTIAL = 7
    CHECKSUM_DONE = 8
    RESPONSE_PARTIAL = 9
    COMPLETE = 10

def unknown(): return 'UNKNOWN'

p_type = defaultdict(unknown)
p_type[0] = 'NULL'
p_type[1] = 'INIT'
p_type[2] = 'PRINT'
p_type[4] = 'DATA'
p_type[8] = 'BREAK'
p_type[15] = 'STATUS'


class Packet:
    def __init__(self):
        self._raw_data = [0]*10 # size of a dataless packet
        self._status = Status.EMPTY
        self._bytes_stored = 0
        self._checksum = 0

    @property
    def raw_data(self):
        return self._raw_data

    @property
    def status(self):
        return self._status

    @property
    def header(self):
        return self._raw_data[2:6]
    
    @property
    def data(self):
        return self._raw_data[6:6+self.data_size]

    @property
    def checksum(self):
        return sum(self._raw_data[2:6+self.data_size]) % (256*256)
    
    @property
    def rx_checksum(self):
        return self._raw_data[-4] + self._raw_data[-3]*256

    @property
    def data_size(self):
        return self._raw_data[4] + self._raw_data[5]*256

    @property
    def type(self):
        return p_type[self._raw_data[2]]    

    def verify_checksum(self):
        return self.checksum == self.rx_checksum

    def _raw_add_byte(self,byte):
        if self._bytes_stored >= len(self._raw_data):
            raise ValueError('Packet cannot accept more bytes (raw)')
        self._raw_data[self._bytes_stored] = byte
        self._bytes_stored += 1
    
    def add_bytes(self,*bytes):
        for byte in bytes:
            self.add_byte(byte)

    def add_byte(self,rx):
        if self._status == [Status.COMPLETE]:
            raise ValueError('Packet cannot accept more bytes')

        if self._status == Status.EMPTY:
            if rx == 0x88:
                self._raw_add_byte(rx)
                self._status = Status.PREAMBLE_PARTIAL

        elif self._status == Status.PREAMBLE_PARTIAL:
            if rx == 0x33:
                self._raw_add_byte(rx)
                self._status = Status.PREAMBLE_DONE
            else:
                self.__init__()

        elif self._status in [Status.PREAMBLE_DONE,Status.HEADER_PARTIAL]:
            self._status = Status.HEADER_PARTIAL
            self._raw_add_byte(rx)
            if self._bytes_stored >= 6: #header is done
                if self.data_size == 0:
                    self._status = Status.DATA_DONE
                else:
                    temp_data = self._raw_data
                    self._raw_data = [0]*(10+self.data_size)
                    self._raw_data[0:6] = temp_data[0:6]
                    self._status = Status.HEADER_DONE

        elif self._status in [Status.HEADER_DONE,Status.DATA_PARTIAL]:
            self._status = Status.DATA_PARTIAL
            self._raw_add_byte(rx)
            if self._bytes_stored >= 6 + self.data_size:
                self._status = Status.DATA_DONE

        elif self._status == Status.DATA_DONE:
            self._raw_add_byte(rx)
            self._status = Status.CHECKSUM_PARTIAL

        elif self._status == Status.CHECKSUM_PARTIAL:
            self._raw_add_byte(rx)
            self._status = Status.CHECKSUM_DONE

        elif self._status == Status.CHECKSUM_DONE:
            self._raw_add_byte(rx)
            self._status = Status.RESPONSE_PARTIAL

        elif self._status == Status.RESPONSE_PARTIAL:
            self._raw_add_byte(rx)
            self._status = Status.COMPLETE


        