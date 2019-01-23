import serial
from time import sleep
import platform

class GBPrinter:

    def __init__(self,port=None):
        if port == None:
            port = self.find_gbp_serial()
        self.gbp_serial = serial.Serial(port,timeout=.2)
        print('sleep for 2 seconds to prep serial...')
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

        print('good ports are',good_ports)

        best_port = None
        for port in good_ports:
            with serial.Serial(port,timeout=.2) as self.gbp_serial:
                print('checking port',port)
                sleep(2.5)
                response = self.cmd_status()
                if response[0] in [0x80,0x81]:
                    best_port = port
                    break

        if best_port == None:
            raise IOError("Can't find printer!")

        print('GBP found on port', best_port)
        return best_port

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

    def send_command(self,cmd,compression=0,packet=None,text_status=False):
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
        if text_status:
            return self.translate_status(response)
        else:
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

    def cmd_print(self,top_margin=0,bottom_margin=0,palette=0xE4,exposure=0x40):
        margin = ( (top_margin % 16) << 4 )| (bottom_margin % 16)
        packet = bytes([0x01,margin,palette,exposure])
        return self.send_command(0x02,packet=packet)

    def cmd_data(self,packet=None):
        return self.send_command(0x04,packet=packet)

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
        if keepalive not in [0x80,0x81]:
            return ['Not connected']
        elif not any(status_bits):
            return ['OK']
        else:
            return [s for i,s in enumerate(self.statuses) if status_bits[i]]


if __name__ == '__main__':

    printer = GBPrinter()

    payload = bytes([i%256 for i in range(640)])
    payload2 = bytes([0xFF,0x00,0x7E,0xFF,0x85,0x81,0x89,0x83,0x93,0x85,0xA5,0x8B,0xC9,0x97,0x7E,0xFF]*40)

    paylel = [payload,payload2]

    print('send command STATUS')
    response = printer.cmd_status()
    print('got response',response)
    print(printer.translate_status(response))

    for i in range(12):
        print('send command DATA',i+1)
        load = paylel[i%2]
        printer.cmd_data(load)
        response = printer.cmd_status()
        print('got response',response)
        print(printer.translate_status(response))

    print('send command DATA')
    printer.cmd_data()
    response = printer.cmd_status()
    print('got response',response)
    print(printer.translate_status(response))


    print('send command PRINT')
    printer.cmd_print(0x0,0x4)
    response = printer.cmd_status()
    print('got response',response)
    print(printer.translate_status(response))

    for i in range(12):
        sleep(1.5)
        print('send command STATUS',i+1)
        response = printer.cmd_status()
        print('got response',response)
        print(printer.translate_status(response))
