"""고유 영문 문자열 추출 -> translation/src.tsv (표 이름, 원문)"""
import os, collections
from strtbl import parse
from get import get
from tsvesc import esc

T = ['mcloadstrings', 'mcstrings01', 'mcstrings02', 'mcstrings04', 'mcstrings08',
     'mcstrings01_pal', 'mcstrings02_pal', 'mcstrings04_pal', 'mcstrings08_pal']
u = collections.OrderedDict()
for n in T:
    d = get('fonts/%s.strtbl' % n); offs, hdr, keys, langs = parse(d)
    for e in langs[0][2]:
        s = e[3].rstrip('\0')
        if s.strip() and s not in u: u[s] = n
os.makedirs('../translation', exist_ok=True)
with open('../translation/src.tsv', 'w', encoding='utf-8', newline='\n') as f:
    for s, n in u.items(): f.write('%s\t%s\n' % (n, esc(s)))
print(len(u))
