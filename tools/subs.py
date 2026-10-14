"""자막 CSV 주입: 영어 칸(2번째)만 한국어(UTF-8 바이트)로 교체"""
import csv, io, glob, os
from tsvesc import unesc
from dumpsubs import cues, SKIP

def load_pairs(tdir):
    """subs_src_NN.txt / subs_ko_NN.txt -> {영문 큐 튜플: 한국어 큐 리스트}"""
    out = {}
    if not glob.glob(os.path.join(tdir, 'subs_src_*.txt')):      # 영문 큐는 원본 ISO 에서 추출
        import subprocess, sys
        subprocess.check_call([sys.executable, 'dumpsubs.py'], cwd=os.path.dirname(os.path.abspath(__file__)))
    for src in sorted(glob.glob(os.path.join(tdir, 'subs_src_*.txt'))):
        ko = src.replace('subs_src_', 'subs_ko_')
        if not os.path.exists(ko): continue
        a = open(src, encoding='utf-8', newline='\n').read().rstrip('\n').split('\n')
        b = open(ko, encoding='utf-8', newline='\n').read().rstrip('\n').split('\n')
        assert len(a) == len(b), (src, len(a), len(b))
        cur_e = cur_k = None
        for x, y in zip(a, b):
            if x.startswith('## '):
                assert x == y, (src, x, y)
                if cur_e: out[tuple(cur_e)] = cur_k
                cur_e, cur_k = [], []
            else:
                cur_e.append(unesc(x)); cur_k.append(unesc(y).strip())
        if cur_e: out[tuple(cur_e)] = cur_k
    return out

def rewrite(data, pairs):
    c = tuple(cues(data))
    if c not in pairs: return None
    ko = iter(pairs[c])
    rows = list(csv.reader(io.StringIO(data.decode('latin1'))))
    for r in rows[1:]:
        if len(r) > 1 and r[1] not in SKIP:
            k = next(ko)
            if os.environ.get('KSUBTEST'): k = os.environ['KSUBTEST']
            assert ',' not in k and '"' not in k, k
            r[1] = (k + ' ').encode('utf-8').decode('latin1')
    buf = io.StringIO()
    csv.writer(buf, lineterminator='\r\n').writerows(rows)
    return buf.getvalue().encode('latin1')
