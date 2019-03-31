from PIL import Image
import time
import numpy as np
import math

def gray_resize(in_image,rotate='auto',align='center'):
    """
    Resizes an image (either a PIL image object or a filepath) to fit in 160
    pixels wide, optionally rotating in the process to be larger, and converts
    to grayscale     
    """

    if type(in_image) == str:
        in_image = Image.open(in_image)

    if in_image.mode == 'RGBA':
        image = clear_transparent(in_image)
    else:
            image = in_image
    
    #then, rotation
    if rotate in ['auto','portrait']:
        w,h = image.size
        if w>h:
            image = image.transpose(Image.ROTATE_270)
    elif rotate == 'landscape':
        w,h = image.size
        if h>w:
            image = image.transpose(Image.ROTATE_270)
    elif rotate == 'none':
        pass
    else:
        raise ValueError('rotate must be auto, portrait, landscape, or none')

    #resize to 160 px wide
    w,h = image.size
    new_h = int(160 * h / w)
    image = image.resize((160,new_h),resample=Image.LANCZOS)

    #pad height to a multiple of 16
    final_h = (new_h-1) // 16 * 16 + 16
    image_new = Image.new('RGB',(160,final_h),(255,255,255))
    if align == 'top':
        image_new.paste(image,(0,0))
    elif align == 'center':
        image_new.paste(image,(0,(final_h-new_h)//2))
    elif align == 'bottom':
        image_new.paste(image,(0,final_h-new_h))

    return to_gray(image_new)

def clear_transparent(in_image):
    """
    get rid of transparent pixels in image, make then white
    """
    image = Image.new('RGBA',in_image.size,(255,255,255,255))
    image.paste(in_image,(0,0),in_image)
    image = image.convert('RGB')
    return image

def to_gray(image):
    """
    Just convert it to grayscale
    """

    if type(image) == str:
        image = Image.open(image)

    return image.convert('L')

def bayer(image):
    if type(image) == type(Image.new('RGB',(1,1))):
        image = np.array(image)

    coeff = np.array([[ 0, 8, 2,10],
                      [12, 4,14, 6],
                      [ 3,11, 1, 9],
                      [15, 7,13, 5]])

    h,w = image.shape
    num_tiles = tuple([math.ceil(x/4) for x in image.shape])
    c = np.tile(coeff,num_tiles)[:h,:w]
    r = 82 #magic number

    image = image + r*(c/16 - 1/2)
    image = 85 * np.round(image/85).astype(int)
    return image

def equal_bins(image):
    if type(image) == type(Image.new('RGB',(1,1))):
        image = np.array(image)
    return image // 64 * 85

def nearest_color(image):
    if type(image) == type(Image.new('RGB',(1,1))):
        image = np.array(image)
    return 85 * np.round(image/85).astype(int)

class DitherFactory:
    def __init__(self):
        self._modes = {}

    def register(self, key, func):
        self._modes[key] = func

    def select(self, key, **kwargs):
        mode = self._modes.get(key)
        if not mode:
            raise ValueError(key)
        return mode

    @property
    def modes(self):
        return self._modes.keys()

dither_factory = DitherFactory()
dither_factory.register('bayer',bayer)
dither_factory.register('equalbins',equal_bins)
dither_factory.register('nearest',nearest_color)

def dither(image,mode='bayer'):
    """
    Dither the image with the selected algorithm and return a 
    numpy array of grayscale values (0/85/170/255)
    """

    im_arr = np.array(image)

    if mode not in dither_factory.modes:
        raise ValueError('Invalid dithering method')
    dither_func = dither_factory.select(mode)
    return dither_func(image)

def convert_gray_to_2bit(arr):
    """
    Converts grayscale array to 2 bit gray palette.
    Will probably look weird if array isn't already 0/85/170/255.
    """
    return 3 - arr // 85


def convert_gray_to_gbtile(arr):
    """
    Converts a gray array to the gb tile format almost ready to send to the
    GB Printer, you'll have to chop it into 640-byte sections on your own.
    """

    twobit_arr = 3 - arr // 85

    gbtile = b''
    num_strips = twobit_arr.shape[0]
    for strip in np.vsplit(twobit_arr,num_strips//8):
        for tile in np.hsplit(strip,20):
            tile_hex = b''
            for row in tile:
                low = bytes([sum([(x%2)*(2**(7-i)) for i,x in enumerate(row)])])
                high = bytes([sum([(x//2)*(2**(7-i)) for i,x in enumerate(row)])])
                tile_hex = tile_hex + low + high
            gbtile = gbtile + tile_hex

    return gbtile

PALETTES = {
    'gray': ('000000','555555','AAAAAA','FFFFFF'),
    'gbcamera' : ('000000','0063C5','7BFF31','FFFFFF'),
    'gbred': ('000000','943A3A','FF8484','FFFFFF'),
    'gborange': ('000000','843100','FFAD63','FFFFFF'),
    'gbyellow' : ('000000','7B4A00','FFFF00','FFFFFF'),
    'gbgreen': ('000000','008400','7BFF31','FFFFFF'),
    'gbblue': ('000000','0000FF','63A5FF','FFFFFF'),
    'gbpurple': ('000000','52528C','8C8CDE','FFFFFF'),
    'gbbrown': ('5A3108','846B29','CE9C84','FFE6C5'),
    'gbrby': ('000000','9494FF','FF9494','FFFFA5'),
    'gbredyellow': ('000000','FF0000','FFF00','FFFFFF'),
    'gbgreenorange': ('000000','FF4200','52FF00','FFFFFF'),
    'gbinverse': ('FFFFFF','FFDE00','008484','000000'),
    'gbreinverse': ('000000','008484','FFDE00','FFFFFF'),
    'bluepurple': ('000000','0042C5','B494FF','FFFFFF'),

}

def palette_convert(palette_tuple):
    palette_str = ''.join(palette_tuple)
    palette_pairs = [palette_str[2*i:2*i+2] for i in range(12)]
    palette_list = [int(color,16) for color in palette_pairs]
    return palette_list

def matrix_to_image(matrix_2bit,palette='gray',save=False):
    """
    Convert an image matrix back into a PIL image object
    """

    matrix = [[(3-x) for x in row] for row in matrix_2bit]
    width = len(matrix[0])
    raw_bytes = bytes([x for y in matrix for x in y])
    dim = (width,len(raw_bytes)//width)
    image = Image.frombytes('P',dim,raw_bytes)
    if type(palette) == tuple:
        image.putpalette(palette_convert(palette))
    else:
        image.putpalette(palette_convert(PALETTES[palette]))
        
    if save:
        image.save(time.strftime('gbp_out/gbp_%Y%m%d_%H%M%S.png'),'PNG')
    return image

def gb_tile_to_matrix(gbtile_bytes):
    """
    converts bytes in GB tile format to 2-bit matrix
    """

    #only needed for dealing with compressed data that's not uncompressed
    #testing only, probably no longer needed
    #padding = bytes(640-(len(gbtile_bytes)%640))
    #gbtile_bytes = gbtile_bytes + bytes(padding)

    num_pages = len(gbtile_bytes)//640
    matrix_2bit = [[0]*160 for i in range(16*num_pages)]
    for s in range(num_pages*2):
        strip_bytes = gbtile_bytes[320*s:320*(s+1)]
        for t in range(20):
            tile_bytes = strip_bytes[16*t:16*(t+1)]
            for r in range(8):
                row_bytes = tile_bytes[2*r:2*(r+1)]
                low, high = row_bytes
                mat_row = [(low>>i & 1) + 2*(high>>i & 1) for i in reversed(range(8))]
                matrix_2bit[s*8+r][t*8:(t+1)*8] = mat_row

    #flip color order from gbtile format
    #matrix = [[(3-x) for x in row] for row in matrix_2bit]
    return matrix_2bit



def image_to_gbtile(image,dither_mode='bayer',rotate='auto',align='center'):
    """
    Does the full conversion, image file/object goes in, gbtile bytestring 
    comes out. This is what you want to use tor everyday processing
    """
    image = gray_resize(image,rotate=rotate,align=align)
    im_dith = dither(image,dither_mode)
    gb_tiles = convert_gray_to_gbtile(im_dith)

    return gb_tiles
