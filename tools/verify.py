import sys,zlib,struct,dave,strtbl
from build import iso_records,SRC,DST,SEC
f=open(DST,'rb');rec=iso_records(f);lba,sz,_=rec['ASSETS.DAT'];print('size',sz)
class Sub:
    def __init__(s,f,b): s.f,s.b=f,b
    def seek(s,o): s.f.seek(s.b+o)
    def read(s,n): return s.f.read(n)
A=Sub(f,lba*SEC);E=dave.read_fobj(A)
N=[e[0] for e in E];print(len(N),sum(1 for i in range(1,len(N)) if N[i-1]>N[i]))
o=dave.read_fobj(Sub(open(SRC,'rb'),lba*SEC));on=set(e[0] for e in o)
print('new names',[n for n in set(N)-on],'lost',[n for n in on-set(N)])
bad=0
for nm,off,u,c in E:
    if c==0: continue
    if off+c>sz: bad+=1
print('out of range',bad)
for nm,off,u,c in E:
    if nm=='fonts/mcstrings01.strtbl':
        A.seek(off);d=zlib.decompress(A.read(c),-15);ent=strtbl.parse(d)[3][0][2];print([e[3] for e in ent if e[3] in('커리어\0','옵션\0')][:3])
from udf import UDF
u=UDF(f);b,t,ad0,l,adt=u._fe(u.files['/ASSETS.DAT']);print(struct.unpack_from('<QQ',b,56))
