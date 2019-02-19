import gbprinter.controller
from gbprinter.image import image_to_gbtile
import sys
from time import sleep
import logging

def main():
    try:
        image_filename = sys.argv[1]
    except IndexError:
        print('Give a file to convert!')
        sys.exit(1)
    try:
        dither = sys.argv[2]
    except IndexError:
        dither = 'bayer'
    try:
        rotate = sys.argv[3]
    except IndexError:
        rotate = 'auto'

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    payload = image_to_gbtile(image_filename,dither,rotate)
    logger.info('payload is ready')

    printer = gbprinter.controller.Controller()

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

    new_image.show()

if __name__ == '__main__':
    main()