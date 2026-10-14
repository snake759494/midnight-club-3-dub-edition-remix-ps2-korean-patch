"""PCSX2 상태 파일(.p2s, zip+zstd)에서 EE 메모리 추출"""
import zipfile, glob, os, struct, zstandard

def latest(serial='SLUS-21355'):
    return max(glob.glob(os.path.expanduser('~/Documents/PCSX2/sstates/%s*.p2s' % serial)), key=os.path.getmtime)

def read_member(path, name):
    z = zipfile.ZipFile(path); i = z.getinfo(name)
    f = open(path, 'rb'); f.seek(i.header_offset)
    h = f.read(30); nl, el = struct.unpack_from('<HH', h, 26)
    f.seek(i.header_offset + 30 + nl + el)
    raw = f.read(i.compress_size)
    if i.compress_type == 0: return raw
    return zstandard.ZstdDecompressor().decompress(raw, max_output_size=i.file_size)

def ee(path=None):
    return read_member(path or latest(), 'eeMemory.bin')

if __name__ == '__main__':
    import sys
    m = ee(); out = sys.argv[1] if len(sys.argv) > 1 else '../work/ee.bin'
    open(out, 'wb').write(m); print(len(m), out)
