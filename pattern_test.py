from time import sleep
import gbprinter

printer = gbprinter.GBPrinter()

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

while printer.cmd_status()[1] != 0:
    sleep(2)
    print('send command STATUS')
    response = printer.cmd_status()
    print('got response',response)
    print(printer.translate_status(response))