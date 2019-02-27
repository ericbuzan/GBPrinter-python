from . import image
import serial
from time import sleep
import platform
import logging
from enum import Enum
from collections import defaultdict

CHECKSUM_ERROR = 0
PRINTING = 1
IMAGE_FULL = 2
UNPROCESSED_DATA = 3
PACKET_ERROR = 4
PAPER_JAM = 5
OTHER_ERROR = 6
LOW_BATTERY = 7

class Emulator:

        def __init__(self,port=None,palette=image.PALETTES['gray']):
            self.logger = logging.getLogger(__name__)
            self.palette = palette
            self.current_packet = Packet()

            if port == None:
                self.find_serial()
            else:
                self.logger.info('Printer on {} you say?'.format(port))
                self.gbp_serial = serial.Serial(port,baudrate=115200,timeout=.2)
                self.logger.info('sleep for 2 seconds to prep serial...')
                sleep(2)
            self.init_buffer()
            self._fullimage = b''

        def init_buffer(self):
            self._status = b'\x00'
            self._buffer = b''
            self._print_fake = 0

        @property
        def status(self):
            return [self._status[0]>>i & 0x01 for i in range(8)]

        @property
        def state(self):
            return self._state

        @property
        def pages(self):
            return len(self._buffer)//640
        
        def set_status(self,bit,new_status=True):
            num = self._status[0]
            if new_status:
                num |= 2**bit
            else:
                num ^= 2**bit
            self._status = bytes([num])

        def get_status(self,bit):
            return bool(self._status[0] & 2**bit)
        
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

            good_ports = []
            for port in ports:
                try:
                    s = serial.Serial(port)
                    s.close()
                    good_ports.append(port)
                except (OSError, serial.SerialException):
                    pass

            self.logger.info('good ports are ' + ','.join(good_ports))

            best_port = None
            for port in good_ports:
                self.gbp_serial = serial.Serial(port,baudrate=115200,timeout=.2)
                self.logger.info('checking port ' + port)
                sleep(2)
                self.gbp_serial.write(bytes([105]))
                response = self.gbp_serial.read(4)
                if response == b'nice':
                    best_port = port
                    break
                else:
                    self.gbp_serial.close()

            if best_port == None:
                raise IOError("Can't find Arduino!")
            else:
                self.logger.info('Arduino found on port ' + best_port)

        def get_gb_data(self):
            packet = self.current_packet
            from_gb = self.gbp_serial.read(4)
            if from_gb:
                rx,tx,ard_state,data_remain = from_gb     
                packet.add_byte(rx)
                if packet.status == Status.COMPLETE:
                    self.handle_packet(packet)
                    self.current_packet = Packet()

        def handle_packet(self,packet):
            self.logger.info('Packet received, type {}, data size {}'.format(packet.type,packet.data_size))
            if packet.data_size == 4:
                self.logger.debug('Print data 0x{:02x} 0x{:02x} 0x{:02x} 0x{:02x}'.format(*packet.data))
            #self.logger.debug('Checksum is {}'.format(self.current_packet.verify_checksum()))

            if packet.type == 1: #init
                if not self.get_status(1): #if not currently printing
                    self.init_buffer()

            elif packet.type == 2: #print
                self.set_status(PRINTING)
                self.set_status(IMAGE_FULL)
                self.set_status(UNPROCESSED_DATA,False)
                end_margin = packet.data[1] % 16
                self._fullimage += self._buffer
                image_mat = image.gb_tile_to_matrix(self._fullimage)
                image_obj = image.matrix_to_image(image_mat,save=True,palette=self.palette)
                if end_margin != 0:
                    self.logger.info('Full image sent!')
                    self._fullimage = b''
                else:
                    self.logger.info('Partial image sent!')


            elif packet.type == 4: #data
                if not self.get_status(1): #if not currently printing
                    if packet.data_size == 0:
                        pass
                    elif self.pages >= 9:
                        self.set_status(PACKET_ERROR)
                    else:
                        if packet.header[1]: #if compression
                            data = self.decompress(packet.data)
                        else:
                            data = packet.data
                        self._buffer = self._buffer + bytes(data)
                        self.set_status(UNPROCESSED_DATA)
                    self.logger.debug('Number of pages in buffer: {}'.format(self.pages))
                    self.logger.debug('Number of bytes in buffer: {}'.format(len(self._buffer)))

            elif packet.type == 8: #break
                if self.get_status(PRINTING):
                    self.init_buffer()

            elif packet.type == 15: #status
                if self.get_status(PRINTING):
                    self._print_fake += 1
                    if self._print_fake == 5:
                        self.set_status(UNPROCESSED_DATA)
                    if self._print_fake > 10:
                        self.set_status(PRINTING,False)
                        self.set_status(IMAGE_FULL,False)
                        self.set_status(UNPROCESSED_DATA,False)
                        self.init_buffer()

            self.gbp_serial.write(self._status)
            self.logger.debug('My status is: {}'.format(self.status))

        def decompress(self,comp_data):
            len_comp = len(comp_data)
            raw_data = [0]*640
            comp_offset = 0
            raw_offset = 0
            while comp_offset < len(comp_data):
                command_byte = comp_data[comp_offset]
                #self.logger.debug('command byte {}/{}: {}'.format(comp_offset,len_comp, command_byte))
                comp_offset += 1
                if command_byte & 0x80: #compressed run
                    length = command_byte - 0x80 + 2
                    duped_byte = comp_data[comp_offset]
                    comp_offset += 1
                    raw_data[raw_offset:raw_offset+length] = [duped_byte]*length
                    raw_offset += length
                else: #uncompressed run
                    length = command_byte + 1
                    unduped_data = comp_data[comp_offset:comp_offset+length]
                    comp_offset += length
                    raw_data[raw_offset:raw_offset+length] = unduped_data
                    raw_offset += length
            return raw_data


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
p_type[0xF] = 'STATUS'


class Packet:
    def __init__(self):
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(__name__)
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
        return self._raw_data[2]

    @property
    def type_text(self):
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


        