from PIL import Image
import time

def gray_resize(image,rotate='auto',align='center'):
    """
    Resizes an image (either a PIL image object or a filepath) to fit in 160
    pixels wide, optionally rotating in the process to be larger, and converts
    to grayscale     
    """

    if type(image) == str:
        image = Image.open(image)

    #first, rotation
    if rotate in ['auto','portrait']:
        w,h = image.size
        if w>h:
            image = image.transpose(Image.ROTATE_90)
    elif rotate == 'landscape':
        w,h = image.size
        if h>w:
            image = image.transpose(Image.ROTATE_90)
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

    image = image_new.convert('L')

    return image

def image_to_matrix(image):
    """
    converts a PIL image object into a matrix of grayscale values
    matrix = list of lists, no numpy here
    """
    width,height = image.size

    raw_bytes = image.tobytes()
    raw_num = [i for i in raw_bytes]
    #matrix = [[0]*16]*len(raw_num//16)
    #for i in range(len(raw_num//16)):
    #    matrix[i] = raw_num[16*i:16*(i+1)]
    matrix = [raw_num[width*i:width*(i+1)] for i in range(len(raw_num)//width)]
    return matrix

def bayer_dither(matrix):
    """
    Performs Bayer dithering on an image matrix (created from image_to_matrix)
    """
    width = len(matrix[0])

    coeff = [[ 0, 8, 2,10],
             [12, 4,14, 6],
             [ 3,11, 1, 9],
             [15, 7,13, 5]]

    unpacked = [x for y in coeff for x in y]

    out_matrix = [[0 for i in range(width)] for i in range(len(matrix))]

    for y in range(len(matrix)):
        for x in range(width):
            n = matrix[y][x]
            c = coeff[y%4][x%4] + .5
            r = 82
            out_matrix[y][x] = round(n + r*(c/16 - 1/2))

    out_matrix = convert_2bit(out_matrix)
    return(out_matrix)


def convert_2bit(matrix):
    """
    Converts grayscale to 2 bit gray palette (0/85/170/255).
    Colors are rounded to nearest color, so grays are more likely
    """

    width = len(matrix[0])

    out_matrix = [[0 for i in range(width)] for i in range(len(matrix))]

    for y in range(len(matrix)):
        for x in range(width):
            n = matrix[y][x]
            out_matrix[y][x] = 3 - round(n/85)
    return out_matrix

def convert_2bit_direct(matrix):
    """
    Converts grayscale to 2 bit gray palette (0/85/170/255).
    Colors are divided into equal bins, so all 4 shades are equally likely
    """

    width = len(matrix[0])
    out_matrix = [[0 for i in range(width)] for i in range(len(matrix))]

    for y in range(len(matrix)):
        for x in range(width):
            n = matrix[y][x]
            o = n//64
            if o > 3:
                o = 3
            if o < 0:
                o = 0
            out_matrix[y][x] = 3 - o
    return out_matrix

def matrix_to_gbtile(matrix):
    """
    Converts a 2-bit image matrix from convert_2bit or whatnot into the Game Boy
    tile format. The output is a bytestring (almost) ready to send to the GB Printer,
    you'll have to chop it into 640-byte sections on your own.
    """

    #convert to 0-3, where 0 is white and 3 is black
    #nope, done by conversion to 2bit now
    raw_num = [x for y in matrix for x in y]

    gbtile = b''
    B = 160*8 #pixels in a 160x8 strip
    num_strips = len(raw_num)//B
    num_tiles = len(raw_num)//64
    for s in range(num_strips):
        strip = raw_num[B*s:B*(s+1)]
        for t in range(20):
            tile_hex = b''
            for r in range(8):
                start = 160*r + 8*t
                row = strip[start:start+8]
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



def image_to_gbtile(image,dither='bayer',rotate='auto',align='center'):
    """
    Does the full conversion, image file/object goes in, gbtile bytestring 
    comes out. This is what you want to use tor everyday processing
    """
    image = gray_resize(image,rotate=rotate,align=align)
    mat = image_to_matrix(image)
    if dither == 'bayer':
        new_mat = bayer_dither(mat)
    elif dither == 'none':
        new_mat = convert_2bit_direct(mat)
    else:
        raise IOError('dither must be "bayer" or "none"')
    gb_tiles = matrix_to_gbtile(new_mat)

    return gb_tiles
