import serial
from time import sleep
import platform
import logging

class GBPrinter:

    def __init__(self,port=None):
        self.logger = logging.getLogger(__name__)

        if port == None:
            self.find_gbp_serial()
        else:
            self.logger.info('Printer on {} you say?'.format(port))
            self.gbp_serial = serial.Serial(port,timeout=.2)
            self.logger.info('sleep for 2 seconds to prep serial...')
            sleep(2.5)
        


    def find_gbp_serial(self):
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
            self.gbp_serial = serial.Serial(port,timeout=.2)
            self.logger.info('checking port ' + port)
            sleep(2.5)
            response = self.cmd_status()
            if response[0] in [0x80,0x81]:
                best_port = port
                break

        if best_port == None:
            raise IOError("Can't find printer!")
        else:
            self.logger.info('GBP found on port ' + best_port)


    def send_byte(self,byte):
        if type(byte) == int:
            byte = bytes([byte])
        elif type(byte) == str:
            byte = byte.encode(encoding='ASCII')
        elif type(byte) == bytes:
            pass
        else:
            raise IOError('Must be bytes, int, or ASCII str')
        #print('sending', byte)
        self.gbp_serial.write(byte)
        response = self.gbp_serial.read()
        #print('received', response)
        return response

    commands = {
        1: 'INIT',
        2: 'PRINT',
        4: 'DATA',
        8: 'BREAK',
        15: 'STATUS'
    }

    def send_command(self,cmd,compression=0,packet=None):

        self.logger.info('Sending {} command'.format(self.commands[cmd]))

        #magic bytes
        self.send_byte(0x88)
        self.send_byte(0x33)

        #header
        self.send_byte(cmd)
        self.send_byte(compression)
        packet_size = 0 if packet == None else len(packet)
        size_chk = self.send_two_bytes(packet_size)

        #packet, if present
        packet_chk = 0
        if packet != None:
            for byte in packet:
                self.send_byte(byte)
                packet_chk += byte

        #checksum
        checksum = (cmd + compression + sum(size_chk) + packet_chk) % 0x10000
        self.send_two_bytes(checksum)

        #response
        response = self.get_response()

        self.logger.info('Received {} {}'.format(hex(response[0]),hex(response[1])))
        self.logger.debug(self.translate_status(response))

        return response       

    def send_two_bytes(self,num):
        low,high = (num % 0x100, (num >> 8) % 0x100)
        self.send_byte(low)
        self.send_byte(high)
        return (low,high)

    def get_response(self):
        high_b = self.send_byte(0)
        high = int.from_bytes(high_b,byteorder='big')
        low_b = self.send_byte(0)
        low = int.from_bytes(low_b,byteorder='big')
        return [high,low]

    def cmd_init(self):
        return self.send_command(0x01)

    def cmd_print(self,top_margin=0,bottom_margin=0,palette=0xE4,exposure=0x40,pages=1):
        margin = ( (top_margin % 16) << 4 )| (bottom_margin % 16)
        packet = bytes([pages,margin,palette,exposure])
        return self.send_command(0x02,packet=packet)

    def cmd_data(self,packet=None):
        return self.send_command(0x04,packet=packet)

    def cmd_break(self):
        return self.send_command(0x08)

    def cmd_status(self):
        return self.send_command(0x0F)

    statuses = [
        'Checksum Error',
        'Printer Busy',
        'Image Data Full',
        'Unprocessed Data',
        'Packet Error',
        'Paper Jam',
        'Other Error',
        'Battery Too Low'
    ]
    
    def translate_status(self,full_status):
        keepalive,status = full_status
        status_bits = [i=='1' for i in reversed('{:08b}'.format(status))]
        if full_status  == [0xFF,0xFF]:
            return ['Not connected']
        elif not any(status_bits):
            return ['OK']
        else:
            return [s for i,s in enumerate(self.statuses) if status_bits[i]]
