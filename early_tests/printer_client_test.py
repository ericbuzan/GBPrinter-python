import serial
from time import sleep

payload = bytes([i%256 for i in range(1280)])
black = bytes([0xFF,0xFF]*320)
dark = bytes([0x00,0xFF]*320)
light = bytes([0xFF,0x00]*320)
white =  bytes([0x00,0x00]*320)

print(type(payload),len(payload))
send_bytes = (1280*3).to_bytes(4,byteorder='big')


s = serial.Serial(
    port='COM5',
    baudrate=9600,
    timeout=10
)
print('starting serial connection...')
sleep(2)

print('sending payload size...')
s.write(send_bytes)

print('reading response...')
print(s.read(4))

print('sending acknowlegement...')
s.write(b'OK')

print('reading response...')
print(s.read(2))

print('writing payload...')
s.write(payload)

print('reading response...')
print(s.read(4))

print('sending light colors...')
s.write(white)
s.write(light)

print('reading response...')
print(s.read(4))

print('sending dark colors...')
s.write(dark)
s.write(black)

print('reading response...')
print(s.read(4))