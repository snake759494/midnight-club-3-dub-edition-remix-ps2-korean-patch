import struct,numpy as np
from PIL import Image
def unswz(i): return i  # placeholder
def read(d):
    w,h,fmt=struct.unpack_from('<3H',d,0)
    if fmt==0x0e:
        pal=np.frombuffer(d[14:14+1024],np.uint8).reshape(256,4).copy()
        # CSM1 swizzle of 8bpp clut
        idx=np.arange(256); sw=(idx&0xe7)|((idx&8)<<1)|((idx&0x10)>>1)
        pal=pal[sw]
        px=np.frombuffer(d[14+1024:14+1024+w*h],np.uint8).reshape(h,w)
    else:
        pal=np.frombuffer(d[14:14+64],np.uint8).reshape(16,4)
        b=np.frombuffer(d[78:78+w*h//2],np.uint8)
        px=np.stack([b&15,b>>4],1).reshape(h,w)
    return w,h,fmt,pal,px
def img(d):
    w,h,fmt,pal,px=read(d); rgba=pal[px].astype(np.int32); pass
    return Image.fromarray(rgba.astype(np.uint8),'RGBA')
