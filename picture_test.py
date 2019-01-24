from PIL import Image,ImageOps
from time import sleep
import gbprinter

printer = gbprinter.GBPrinter()

squid = Image.open('squid.bmp').convert('RGB')
flip_squid = ImageOps.invert(squid)
squid_bytes = flip_squid.convert('1').tobytes()
#print(squid_bytes)
print(len(squid_bytes))

squid_gb = [0]*len(squid_bytes)*2
for c in range(len(squid_bytes)//160):
    chunk = squid_bytes[160*c:160*(c+1)]
    chunk_gb = [0]*320
    for r in range(160):
        chunk_gb[2*r] = chunk[20*(r%8) + r//8]
        chunk_gb[2*r+1] = chunk[20*(r%8) + r//8]
    squid_gb[320*c:320*(c+1)] = chunk_gb

print(len(squid_gb))

print('send command STATUS')
response = printer.cmd_status()
print('got response',response)
print(printer.translate_status(response))

for i in range(9):
    print('send command DATA',i+1)
    payload = squid_gb[640*i:640*(i+1)]
    printer.cmd_data(payload)
    response = printer.cmd_status()
    print('got response',response)
    print(printer.translate_status(response))

print('send command DATA')
printer.cmd_data()
response = printer.cmd_status()
print('got response',response)
print(printer.translate_status(response))

print('send command PRINT')
printer.cmd_print(0x0,0x0)
response = printer.cmd_status()
print('got response',response)
print(printer.translate_status(response))

while printer.cmd_status()[1] != 0:
    sleep(2)
    print('send command STATUS')
    response = printer.cmd_status()
    print('got response',response)
    print(printer.translate_status(response))


for i in range(9,11):
    print('send command DATA',i+1)
    payload = squid_gb[640*i:640*(i+1)]
    printer.cmd_data(payload)
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

while printer.cmd_status()[1] != 0:
    sleep(2)
    print('send command STATUS')
    response = printer.cmd_status()
    print('got response',response)
    print(printer.translate_status(response))