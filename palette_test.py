import gbprinter.controller
from gbprinter import image as gbimage
import argparse
from PIL import Image
import numpy as np

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
    parser.add_argument('-p', '--palette',
                        dest="palette", 
                        default='gray', 
                        choices=gbimage.PALETTES.keys(),
                        help="Color palette to use"
                        )
    parser.add_argument('-w', '--width',
                        dest="width", 
                        default=0, 
                        type=int,
                        help="Resize pic to width"
                        )
    parser.add_argument('filename')
    args = parser.parse_args()

    image_in = Image.open(args.filename)

    if args.width != 0:
        pass

    image_gray = image_in.convert('L')
    dithered = gbimage.dither(image_gray,args.dither)
    twobit = gbimage.gray_to_twobit(dithered)
    im = gbimage.twobit_to_image(twobit,palette=args.palette,save=True)
    im.show()

if __name__ == '__main__':
    main()