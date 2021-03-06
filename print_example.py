import gbprinter.controller
from gbprinter import image as gbimage
import sys
from time import sleep
import logging
import argparse

def main():
    parser = argparse.ArgumentParser(description='Print on a Game Boy Printer!')
    parser.add_argument('-r', '--rotate',
                        dest="rotate", 
                        default='auto', 
                        choices=['auto','portrait','landscape','none'],
                        help="How to rotate the image"
                        )
    parser.add_argument('-d', '--dithering',
                        dest="dither", 
                        default='bayer', 
                        choices=gbimage.dither_factory.modes,
                        help="Dithering algorithm to use"
                        )
    parser.add_argument('-a', '--align',
                        dest="align", 
                        default='center', 
                        choices=['center','top','bottom'],
                        help="Alignment of image with padding"
                        )
    parser.add_argument('filename')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    printer = gbprinter.controller.Controller()

    payload = gbimage.image_to_gbtile(args.filename,args.dither,args.rotate,args.align)
    logger.info('payload is ready')

    num_strips = len(payload)//640
    strips_done = 0

    while strips_done < num_strips:

        printer.cmd_init()
        printer.cmd_status()

        end_strip = min(strips_done + 9, num_strips)

        for i in range(strips_done,end_strip):
            logger.info('sending data {}/{}'.format(i+1,num_strips))
            strip = payload[640*i:640*(i+1)]
            printer.cmd_data(strip)
            printer.cmd_status()

        strips_done = end_strip

        printer.cmd_data()
        printer.cmd_status()

        logger.info('sending print command'.format(i+1,num_strips))

        if strips_done == num_strips:
            printer.cmd_print(0x0,0x4)
        else:
            printer.cmd_print(0x0,0x0)
        printer.cmd_status()
        

        while printer.cmd_status()[1] != 0:
            sleep(.5)

if __name__ == '__main__':
    main()