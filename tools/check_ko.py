import glob,re,collections,sys
from tsvesc import unesc
from get import get
from kfont import parse_fonttex
hdr,G,t=parse_fonttex(get('fonts/smallspace.fonttex'));have={g[0] for g in G}|{32,10,13,0xa0}
from build import src_strings, sid
byid={sid(x):x for x in src_strings()}
errs=0;n=0;seen={}
for fn in sorted(glob.glob('../translation/ko_*.tsv')):
    for ln,l in enumerate(open(fn,encoding='utf-8',newline='\n'),1):
        l=l.rstrip('\n')
        if not l: continue
        p=l.split('\t')
        def E(m):
            global errs;errs+=1;print('%s:%d %s | %s'%(fn[-9:],ln,m,l[:150]))
        if len(p)!=2: E('칸수');continue
        if p[0] not in byid: E('원문없음');continue
        en,ko=byid[p[0]],unesc(p[1]);n+=1
        if en in seen and seen[en]!=ko: E('중복 다른번역')
        seen[en]=ko
        if re.findall(r'%[sd]',en)!=re.findall(r'%[sd]',ko): E('서식')
        if en.count('\n')!=ko.count('\n') : E('줄바꿈수 %d/%d'%(en.count('\n'),ko.count('\n')))
        if en.count('\r')!=ko.count('\r'): E('CR수')
        bad=[c for c in ko if ord(c) not in have and not (0xac00<=ord(c)<=0xd7a3)]
        if bad: E('폰트없는문자 %r'%''.join(sorted(set(bad))))
        if (en[:1]==' ')!=(ko[:1]==' ') or (en[-1:]==' ')!=(ko[-1:]==' '): E('앞뒤공백')
print('검사 %d줄, 오류 %d'%(n,errs))
