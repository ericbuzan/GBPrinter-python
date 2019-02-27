import gbprinter.controller
from gbprinter import image as gbimage
import argparse
from PIL import Image

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
    mat_in = gbimage.image_to_matrix(image_gray)

    if args.dither == 'bayer':
        new_mat = gbimage.bayer_dither(mat_in)
    elif args.dither == 'none':
        new_mat = gbimage.convert_2bit_direct(mat_in)
    else:
        raise IOError('dither must be "bayer" or "none"')

    im = gbimage.matrix_to_image(new_mat,palette=args.palette,save=True)
    im.show()

if __name__ == '__main__':
    main()