from gbprinter import emulator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

emu = emulator.Emulator(palette = 'gbcamera')

while True:
    emu.get_gb_data()