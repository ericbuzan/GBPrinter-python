import gbprinter.controller
from gbprinter import image as gbimage
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
                        choices=['bayer','none'],
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

    payload = gbimage.image_to_gbtile(args.filename,args.dither,args.rotate,args.align)

    matr = gbimage.gb_tile_to_matrix(payload)
    im = gbimage.matrix_to_image(matr,palette='camera',save=True)
    im.show()

if __name__ == '__main__':
    main()