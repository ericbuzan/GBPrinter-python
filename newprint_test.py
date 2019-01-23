import serial
from time import sleep
import platform

payload = [0x88,0x33,0x01,0x00,0x00,0x00,0x01,0x00,0x00,0x00]
print(type(payload[0]))


find_gbp_serial()

s = serial.Serial(
    port='COM5',
    baudrate=9600,
    timeout=.2
)

for i in range(2):
    print('sleep...',i+1)
    sleep(1)


for i in range(20):
    print(str(i)*50)
    for bite in payload:
        print('sending byte:',hex(bite))
        num = s.write(bytes([bite]))
        #print('sent this many bytes:')
        resp = s.read(1)
        print('received byte:',hex(int.from_bytes(resp,byteorder='big')))


