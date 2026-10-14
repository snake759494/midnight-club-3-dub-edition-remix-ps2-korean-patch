import sys,numpy as np
from PIL import Image
from kfont import *
from get import get
from tex import img
def preview(text, st, out, scale=3):
    hdr,G,t=parse_fonttex(get('fonts/smallspace.fonttex'))
    pages=[(img(get('fonts/texture/smallspace_%02d.tex'%k)),img(get('fonts/texture/smallspace_%02ds.tex'%k))) for k in range(8)]
    gi={g[0]:(i,g) for i,g in enumerate(G)}
    def page_of(i): return [k for k in range(8) if (t[k-1] if k else 0)<=i<t[k]][0]
    canvas=Image.new('RGBA',(30*len(text)+20,40),(30,70,150,255))
    layers=[]; x=10; base=30
    for ch in text:
        if ord(ch) in gi:
            i,g=gi[ord(ch)];k=page_of(i);c,X,Y,w,h,yo,b=g
            m=pages[k][0].crop((X,Y,X+w,Y+h));s=pages[k][1].crop((X,Y,X+w,Y+h))
            layers.append((s,m,x,base+yo));x+=w+b
        elif ch==' ': x+=8
        else:
            fill,sh,inkw,pad=render(ch,st)
            h,w=fill.shape
            m=np.zeros((h,w,4),np.uint8);m[...,:3]=st.fill;m[...,3]=np.round(fill*15)*17
            s=np.zeros((h,w,4),np.uint8);s[...,3]=np.round(sh*15)*17
            layers.append((Image.fromarray(s,'RGBA'),Image.fromarray(m,'RGBA'),x,base-21));x+=inkw+1
    for s,m,X,Y in layers: canvas.alpha_composite(s,(X,Y))
    for s,m,X,Y in layers: canvas.alpha_composite(m,(X,Y))
    canvas=canvas.crop((0,0,x+10,40))
    canvas.resize((canvas.width*scale,canvas.height*scale),Image.NEAREST).save(out)
if __name__=='__main__':
    st=Style(ROOT+sys.argv[1],int(sys.argv[2]),26,3,2)
    preview(sys.argv[3],st,sys.argv[4])
