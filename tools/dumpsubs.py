"""자막 CSV 영어 칸 추출 -> translation/subs_src_NN.txt (내용이 같은 파일은 한 번만)
형식: '## 파일명' 다음 줄부터 큐마다 한 줄(이스케이프)"""
import csv, io, collections
from get import get, ents
from tsvesc import esc
SKIP = ('time correction', 'position', 'size')

def cues(data):
    rows = list(csv.reader(io.StringIO(data.decode('latin1'))))
    return [r[1] for r in rows[1:] if len(r) > 1 and r[1] not in SKIP]

if __name__ == '__main__':
    subs = sorted(set(e[0] for e in ents() if e[0].startswith('tune/subtitle/') and e[0].endswith('.csv')))
    uniq = collections.OrderedDict()
    for s in subs:
        c = tuple(cues(get(s)))
        if c and c not in uniq: uniq[c] = s
    items = list(uniq.items())
    n = 4; per = (len(items) + n - 1) // n
    for k in range(n):
        with open('../translation/subs_src_%02d.txt' % (k + 1), 'w', encoding='utf-8', newline='\n') as f:
            for c, s in items[k * per:(k + 1) * per]:
                f.write('## %s\n' % s)
                for x in c: f.write(esc(x) + '\n')
    print(len(items))
