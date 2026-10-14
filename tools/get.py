import dave,zlib,sys
_E=None
import os,struct
ISO=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'Midnight Club 3 - DUB Edition Remix (USA).iso')
class _Sub:
    """원본 ISO 안의 ASSETS.DAT 를 파일처럼 읽기"""
    def __init__(s):
        from build import iso_records
        s.f=open(ISO,'rb'); s.b=iso_records(s.f)['ASSETS.DAT'][0]*2048
    def seek(s,o): s.f.seek(s.b+o)
    def read(s,n): return s.f.read(n)
_A=None
def ents():
    global _E,_A
    if _E is None: _A=_Sub(); _E=dave.read_fobj(_A)
    return _E
def get(name,idx=0):
    r=[e for e in ents() if e[0]==name][idx]
    _A.seek(r[1]);c=_A.read(r[3]);return zlib.decompress(c,-15) if r[3]!=r[2] else c
if __name__=='__main__':
    for n in sys.argv[2:]: open(sys.argv[1]+'/'+n.split('/')[-1],'wb').write(get(n))
