from PIL import Image

def gray_resize(image,rotate='auto',align='center'):
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
    raw_bytes = image.tobytes()
    raw_num = [i for i in raw_bytes]
    #matrix = [[0]*16]*len(raw_num//16)
    #for i in range(len(raw_num//16)):
    #    matrix[i] = raw_num[16*i:16*(i+1)]
    matrix = [raw_num[160*i:160*(i+1)] for i in range(len(raw_num)//160)]
    return matrix

def bayer_dither(matrix):
    coeff = [[ 0, 8, 2,10],
             [12, 4,14, 6],
             [ 3,11, 1, 9],
             [15, 7,13, 5]]

    unpacked = [x for y in coeff for x in y]

    out_matrix = [[0 for i in range(160)] for i in range(len(matrix))]

    for y in range(len(matrix)):
        for x in range(160):
            n = matrix[y][x]
            c = coeff[y%4][x%4] + .5
            r = 82
            out_matrix[y][x] = round(n + r*(c/16 - 1/2))

    out_matrix = convert_2bit(out_matrix)
    return(out_matrix)


def convert_2bit(matrix):
    """
    Converts grayscale to 2 bit gray palette ()0/85/170/255).
    Colors are rounded to nearest color, so grays are more likely
    """

    out_matrix = [[0 for i in range(160)] for i in range(len(matrix))]

    for y in range(len(matrix)):
        for x in range(160):
            n = matrix[y][x]
            out_matrix[y][x] = 85 * round(n/85)
    return out_matrix

def convert_2bit_direct(matrix):
    """
    Converts grayscale to 2 bit gray palette (0/85/170/255).
    Colors are divided into equal bins, so all 4 shades are equally likely
    """
    out_matrix = [[0 for i in range(160)] for i in range(len(matrix))]

    for y in range(len(matrix)):
        for x in range(160):
            n = matrix[y][x]
            o = n//64
            if o > 3:
                o = 3
            if o < 0:
                o = 0
            out_matrix[y][x] = 85*o
    return out_matrix

def matrix_to_gbtile(matrix):

    #convert to 0-3, where 0 is white and 3 is black
    raw_num_2bit = [(3-x//85) for y in matrix for x in y]

    gbtile = b''
    B = 160*8 #pixels in a 160x8 strip
    num_strips = len(raw_num_2bit)//B
    num_tiles = len(raw_num_2bit)//64
    for s in range(num_strips):
        strip = raw_num_2bit[B*s:B*(s+1)]
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

def matrix_to_image(matrix):
    raw_bytes = bytes([x for y in matrix for x in y])
    s = (160,len(raw_bytes)//160)
    image = Image.frombytes('L',s,raw_bytes)
    return image

def image_to_gbtile(image,dither='bayer',rotate='auto'):
    image = gray_resize(image,rotate=rotate)
    mat = image_to_matrix(image)
    if dither == 'bayer':
        new_mat = bayer_dither(mat)
    elif dither == 'none':
        new_mat = convert_2bit_direct(mat)
    else:
        raise IOError('dither must be "bayer" or "none"')
    new_image = matrix_to_image(new_mat)
    gb_tiles = matrix_to_gbtile(new_mat)

    return gb_tiles
