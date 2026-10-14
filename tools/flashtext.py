"""플래시 UI(.pck) 안의 고정 문구 한글화
1) ActionScript 상수 풀: 언어별 배열의 영어 항목을 한국어로. 쓰지 않는 독/서/불/이 문자열을 비워
   풀 전체 바이트 길이를 그대로 유지한다(재배치 불필요).
2) 정적 텍스트(태그 6): 글리프 번호를 한글 글리프로 바꾼다(명령 수·길이 유지)."""
import struct
import aspool, stext
from flashfont import Pck, add_global

# (풀에 반드시 있어야 하는 표식, 영→한, 비워도 되는 다른 언어 문자열)
POOLS = [
    (b'ProfileClassVehiculeoriginal',
     {b'Class': '클래스', b'Specialty': '스페셜', b'Luxury Sedans': '고급 세단', b'Exotics': '이그조틱',
      b'Choppers': '초퍼', b'Tuners': '튜너', b'Sport Bikes': '스포츠 바이크', b'SUV/Trucks': 'SUV/트럭',
      b'Muscle Cars': '머슬카'},
     [b'Klasse', b'Spezial', b'Luxuslimos', b'Exoten', b'Tuner', b'clase', b'Especialidad', b'Sedanes de lujo',
      'Exóticos'.encode('utf-8'), b'Moto deport.', b'4x4/Camiones', 'Coches clásicos'.encode('utf-8'), b'Tuneados',
      b'classe', 'Spécialités'.encode('utf-8'), b'Berlines', b'Exotiques', b'Motos sport', b'SUV/Camions',
      'Specialità'.encode('utf-8'), b'Berline di lusso', b'Auto esotiche', b'Moto sport.', b'SUV/camion', b'Fuori serie']),
    (b'NumberOfEvent',
     {b'RACE ': '레이스 ', b' OF ': ' / '},
     [b'CARRERA ', b'COURSE ', b'GARA ', b'RENNEN ', b' DE ', b' SUR ', b' DI ', b' VON ',
      b'RacetypeID: ', b'ModeID: ', b'GameID: ']),   # 마지막 셋은 디버그 패널(panelbottom) 표시용
]

# 정적 텍스트: 줄들을 '|'로 이은 영문 -> 한글. 세로(한 줄에 한 글자)는 'V:' 접두
STEXT = {
    'A|C|C|E|L|E|R|A|T|I|O|N': 'V:가속',
    'T|O|P|S|P|E|E|D': 'V:최고속도',
    'H|A|N|D|L|I|N|G': 'V:핸들링',
    'BACK': '뒤로',
    'ATLANTA': '애틀랜타',
    'DETROIT': '디트로이트',
    'SAN DIEGO': '샌디에이고',
    'LOADING': '로딩 중',
}

def all_korean():
    s = set()
    for _, m, _ in POOLS: s.update(c for v in m.values() for c in v)
    for v in STEXT.values(): s.update(v.replace('V:', ''))
    return {c for c in s if 0xac00 <= ord(c) <= 0xd7a3}


def fix_pools(d):
    n = 0
    for at, L, ss in aspool.pools(bytes(d)):
        for mark, tr, foreign in POOLS:
            if mark not in ss or not any(k in ss for k in tr): continue
            new = [tr[s].encode('utf-8') if s in tr else (b'' if s in foreign else s) for s in ss]
            used = sum(len(x) + 1 for x in new)
            room = (L - 2) - used
            if room < 0:
                print('  상수 풀 공간 부족, 건너뜀:', mark, room, ss[:40]); continue
            # 남는 바이트는 비운 다른 언어 문자열 하나에 공백으로 채움
            k = next(i for i, s in enumerate(ss) if s in foreign)
            new[k] = b' ' * room
            aspool.rewrite(d, at, L, new); n += 1
    return n


def add_space(pck, fo):
    """공백(32)이 없는 장식 글꼴에 크기 0 글리프로 공백을 덧붙인다"""
    i = pck.font_info(fo)
    codes = i['codes'] + [32]; advs = i['advs'] + [0]
    recs = i['recs'] + [[0] * 8]; pages = i['pages'] + [0]; n1 = len(codes)
    o_code = pck.append(struct.pack('<%dH' % n1, *codes), 16)
    o_adv = pck.append(struct.pack('<%dH' % n1, *advs), 16)
    o_rec = pck.append(b''.join(struct.pack('<4B4h', *r) for r in recs), 16)
    o_pg = pck.append(bytes(pages), 16)
    t = i['tg']
    struct.pack_into('<h', pck.d, fo + 8, n1)
    pck.setW(fo + 0x10, pck.V(o_code)); pck.setW(fo + 0x14, pck.V(o_adv))
    pck.setW(t + 4, pck.V(o_rec)); struct.pack_into('<H', pck.d, t + 0xa, n1)
    pck.setW(t + 0xc, pck.V(o_pg))


def slot_fonts(pck, fos):
    """정적 텍스트의 slot 번호(문자 사전 순번) -> 글꼴 객체 순번"""
    if not fos: return {}
    inr = lambda v: v == 0 or pck.base <= v < pck.base + len(pck.d)
    n = len(pck.d) - 4
    o = next((o for o in range(0, n, 4) if pck.W(o) == pck.V(fos[0])), None)
    if o is None: return {}
    s = o
    while s >= 4 and inr(pck.W(s - 4)): s -= 4
    e = o
    while e < n and inr(pck.W(e)): e += 4
    pos = {pck.W(q): (q - s) // 4 for q in range(s, e, 4)}
    return {pos[pck.V(f)]: j for j, f in enumerate(fos) if pck.V(f) in pos}


def fix_stext(pck, atlas):
    n = 0
    fos = pck.fonts(); infos = [pck.font_info(f) for f in fos]
    smap = slot_fonts(pck, fos)
    for r in stext.records(pck):
        sl = stext.slot_of(r)
        cand = [smap[sl]] if sl in smap else []
        for j in cand:
            fi = infos[j]
            lines = stext.text(r, fi['codes'])
            key = '|'.join(lines)
            if key not in STEXT: continue
            ko = STEXT[key]
            codes = fi['codes']; advs = fi['advs']
            ci = {c: i for i, c in enumerate(codes)}
            sp = ci.get(32)
            if any(ord(c) not in ci for c in ko.replace('V:', '')):
                # 장식용 글꼴(본문 글꼴 아님): 이때만 한글 글리프 표를 붙인다
                if not add_global(pck, fos[j], atlas): break
                fi = infos[j] = pck.font_info(fos[j])
                codes = fi['codes']; advs = fi['advs']; ci = {c: i for i, c in enumerate(codes)}
            if sp is None:
                add_space(pck, fos[j]); fi = infos[j] = pck.font_info(fos[j])
                codes = fi['codes']; advs = fi['advs']; ci = {c: i for i, c in enumerate(codes)}
            sp = ci[32]
            d = pck.d
            height = next(a[1] for op, a, q in r['cmds'] if op == 1)
            g5 = [(args, q) for op, args, q in r['cmds'] if op == 5]
            if ko.startswith('V:'):
                chars = ko[2:]; slots = len(g5); k = len(chars)
                pick = {slots - k + i: c for i, c in enumerate(chars)}      # 막대 아래쪽에 연속 배치
                for s_i, (args, q) in enumerate(g5):
                    c = pick.get(s_i)
                    g = ci[ord(c)] if c else sp
                    a = advs[g] * height // 1024 if c else 0
                    struct.pack_into('<HH', d, q + 4, g, a)
            else:
                (args, q), = g5
                assert len(ko) <= len(args), (key, ko)
                for i in range(len(args)):
                    if i < len(ko): g = ci[ord(ko[i])]; a = max(advs[g] * height // 1024, height // 4 if ko[i] == ' ' else 0)
                    else: g, a = sp, 0
                    struct.pack_into('<HH', d, q + 4 + 4 * i, g, a)
            n += 1
            break
    return n


def apply(data, atlas):
    """-> (새 바이트 또는 None, 풀 수, 정적 텍스트 수)"""
    pck = Pck(data)
    np_ = fix_pools(pck.d)
    ns = fix_stext(pck, atlas) if pck.fonts() else 0
    return (pck.finish() if np_ or ns else None), np_, ns
