"""한글로 다시 그릴 게임 텍스처 목록과 배치(화면 기준 원본 픽셀 좌표)"""
import os
import numpy as np
import imgedit as E

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAVY = os.path.join(ROOT, 'NanumSquareNeo-eHv.ttf')
BOLD = os.path.join(ROOT, 'NanumSquareNeo-dEb.ttf')

# 일러스트(소문자 둥근 글씨 + 그림): 지울 사각형들, 줄(문구, 중심, 높이, 기울기)
ILLUS = {
    'illustration_garage': dict(clear=[(0, 22, 80, 52)], circle=[(101, 37, 17, (104, 30))],
                                lines=[('차고', (42, 37), 17, 0)], font=HEAVY),
    'illustration_moving': dict(clear=[(0, 22, 80, 52)], circle=[(101, 37, 17, (104, 30))],
                                lines=[('차고', (42, 37), 17, 0)], font=HEAVY),
    'illustration_race': dict(clear=[(0, 12, 44, 64), (44, 36, 66, 64)],
                              lines=[('SUV', (22, 25), 12, 18), ('레이스', (32, 48), 12, 18)]),
    'illustration_race_suv': dict(clear=[(0, 12, 44, 64), (44, 36, 66, 64)],
                                  lines=[('SUV', (22, 25), 12, 18), ('레이스', (32, 48), 12, 18)]),
    'illustration_race_chopper': dict(clear=[(0, 10, 76, 60)],
                                      lines=[('초퍼', (28, 24), 12, 14), ('레이스', (36, 44), 12, 14)]),
    'illustration_race_circuit': dict(clear=[(30, 23, 108, 54)],
                                      lines=[('서킷', (68, 31), 12, 0), ('레이스', (68, 47), 12, 0)]),
    'illustration_race_culture': dict(clear=[(4, 6, 82, 22), (4, 22, 56, 31)],
                                      lines=[('튜너', (24, 12), 10, 0), ('레이스', (28, 25), 10, 0)]),
    'illustration_race_highend': dict(clear=[(2, 2, 86, 30), (2, 30, 60, 46)],
                                      lines=[('하이엔드', (40, 17), 11, -10), ('레이스', (32, 35), 11, -10)]),
    'illustration_race_hookman': dict(clear=[(0, 2, 116, 62)],
                                      lines=[('후크맨', (54, 20), 18, 8), ('레이스', (52, 46), 18, 8)]),
    'illustration_race_luxury': dict(clear=[(6, 4, 72, 27), (6, 27, 34, 42)],
                                     lines=[('고급 세단', (36, 16), 10, -10), ('레이스', (24, 33), 9, -10)]),
    'illustration_race_muscle': dict(clear=[(0, 2, 72, 24), (0, 24, 52, 32)],
                                     lines=[('머슬카', (34, 11), 11, 0), ('레이스', (28, 25), 9, 0)]),
    'illustration_race_ordered': dict(clear=[(2, 33, 95, 64)],
                                      lines=[('순서', (44, 41), 12, 0), ('레이스', (42, 56), 12, 0)]),
    'illustration_race_sportbikes': dict(clear=[(2, 22, 56, 60)],
                                         lines=[('바이크', (28, 32), 11, 5), ('레이스', (30, 49), 11, 5)]),
    'illustration_race_supercars': dict(clear=[(4, 28, 60, 64), (60, 44, 112, 64)],
                                        lines=[('슈퍼카', (36, 38), 11, 8), ('레이스', (46, 54), 11, 8)]),
    'illustration_race_timerace': dict(clear=[(0, 24, 95, 64)],
                                       lines=[('타임', (40, 34), 12, -10), ('레이스', (28, 52), 12, -10)]),
    'illustration_race_tournament': dict(clear=[(2, 27, 66, 50)], bright_only=[(66, 27, 106, 50)],
                                         lines=[('토너먼트', (34, 33), 11, 0), ('레이스', (24, 46), 10, 0)]),
}

# 내비 아이콘 문구 상자: 지울 사각형(좌상단이 배경), 한글
NAVBOX = {
    'navsys_illustration_cityrace': ((41, 18, 125, 45), '시티 레이스'),
    'navsys_illustration_cutscene': ((47, 20, 117, 48), '튜토리얼'),
    'navsys_illustration_garage': ((40, 18, 123, 44), '차고'),
    'navsys_illustration_movers': ((39, 20, 123, 46), '이동 업체'),
    'navsys_illustration_race_autocross': ((39, 21, 121, 42), '오토크로스'),
    'navsys_illustration_race_circuit': ((41, 17, 125, 44), '서킷'),
    'navsys_illustration_race_cruise': ((43, 19, 118, 44), '크루즈'),
    'navsys_illustration_race_ctf': ((50, 19, 120, 46), '깃발 뺏기'),
    'navsys_illustration_race_dash': ((45, 17, 120, 40), '대시'),
    'navsys_illustration_race_frenzy': ((51, 22, 121, 43), '광란'),
    'navsys_illustration_race_hookman': ((37, 24, 127, 46), '스트리트 레이서'),
    'navsys_illustration_race_ordered': ((41, 19, 125, 42), '순서'),
    'navsys_illustration_race_tag': ((51, 16, 113, 47), '태그'),
    'navsys_illustration_race_time': ((41, 21, 122, 48), '타임 레이스'),
    'navsys_illustration_race_tournament': ((33, 17, 123, 42), '토너먼트'),
    'navsys_illustration_race_unordered': ((41, 19, 121, 46), '자유 순서'),
    'navsys_illustration_tutorial': ((45, 23, 116, 48), '튜토리얼'),
}


def illus(t, spec):
    img = t.rgba()
    col = E.dominant(img, spec['clear'][0])
    for r in spec['clear']: E.clear(img, r)
    for r in spec.get('bright_only', []):
        x0, y0, x1, y1 = r
        sub = img[y0:y1, x0:x1]
        m = (sub[..., :3].mean(-1) * sub[..., 3] / 128 > 70)
        sub[m] = (0, 0, 0, 0)
    for cx, cy, r, (sx, sy) in spec.get('circle', []):
        c = img[sy, sx].copy()
        yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
        m = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
        img[m] = c
    for txt, c, h, ang in spec['lines']:
        m, S = E.text_layer(txt, spec.get('font', BOLD), (0, 0, 120, 64), h, ang)
        E.stamp(img, m, S, c, col)
    return t.write(img)


def navbox(t, rect, txt):
    img = t.rgba()
    x0, y0, x1, y1 = rect
    col = E.dominant(img, rect)
    ring = np.concatenate([img[y0, x0:x1], img[y1 - 1, x0:x1], img[y0:y1, x0], img[y0:y1, x1 - 1]])
    bg = ring[np.argmin(ring[:, :3].mean(1) * ring[:, 3])].copy()
    E.clear(img, rect, bg)
    m, S = E.text_layer(txt, HEAVY, (x0 + 2, y0, x1 - 2, y1), (y1 - y0) * 0.62)
    E.stamp(img, m, S, ((x0 + x1) / 2, (y0 + y1) / 2), col)
    return t.write(img)


def tokyo(t):
    img = t.rgba(); col = E.dominant(img, (46, 14, 104, 36))
    E.clear(img, (44, 12, 108, 48), img[12, 44].copy())
    m, S = E.text_layer('도쿄', HEAVY, (46, 12, 106, 36), 18); E.stamp(img, m, S, (76, 25), col)
    m, S = E.text_layer('시티 레이스', BOLD, (48, 38, 104, 48), 7); E.stamp(img, m, S, (76, 43), col)
    return t.write(img)


def message(t, bottom):
    """PRESS / [버튼] / SELECT 안내판: PRESS -> 누르세요, BACK -> 뒤로"""
    img = t.rgba()
    top = (46, 9, 108, 29)
    col = E.dominant(img, top)
    E.inpaint(img, top)
    m, S = E.text_layer('누르세요', HEAVY, top, 11); E.stamp(img, m, S, (77, 19), col)
    if bottom:
        r = (62, 40, 102, 51)
        c2 = E.dominant(img, r, bright=False)
        E.inpaint(img, r)
        m, S = E.text_layer(bottom, HEAVY, r, 10); E.stamp(img, m, S, (82, 45.5), c2)
    return t.write(img)


def go(t):
    img = t.rgba()
    green = E.dominant(img, (24, 8, 104, 56))
    E.clear(img, (0, 0, t.w, t.h))
    m, S = E.text_layer('출발', HEAVY, (6, 4, 122, 60), 40)
    E.stamp(img, m, S, (64, 32), green, outline=3, ocolor=(10, 10, 10, 128))
    return t.write(img)


def loading(t):
    img = t.rgba()
    col = E.dominant(img, (0, 0, t.w, t.h))
    E.clear(img, (0, 0, t.w, t.h), img[0, 0].copy())
    m, S = E.text_layer('로딩 중', HEAVY, (4, 2, 124, 30), 22, italic=0.2)
    E.stamp(img, m, S, (64, 16), col, outline=1, ocolor=(70, 70, 70, 128))
    return t.write(img)


def navtitle(t):
    img = t.rgba()
    col = E.dominant(img, (0, 0, t.w, t.h))
    E.clear(img, (0, 0, t.w, t.h))
    m, S = E.text_layer('내비게이션', HEAVY, (4, 0, 252, 32), 28)
    E.stamp(img, m, S, (128, 16), col, outline=1, ocolor=(60, 60, 60, 128))
    return t.write(img)


def navtitle_tiles(texs):
    """navsys_title01..04: 256x32 한 장을 64x32 네 조각으로"""
    big = np.concatenate([t.rgba() for t in texs], 1)
    col = E.dominant(big, (0, 0, 256, 32))
    E.clear(big, (0, 0, 256, 32))
    m, S = E.text_layer('내비게이션', HEAVY, (4, 0, 252, 32), 30)
    E.stamp(big, m, S, (128, 16), col)
    return [t.write(big[:, 64 * k:64 * k + 64].copy()) for k, t in enumerate(texs)]


def tutorial_bg(t):
    img = t.rgba()
    r = (20, 92, 238, 140)
    col = (235, 235, 235, 128)
    E.inpaint(img, r)
    m, S = E.text_layer('튜토리얼', HEAVY, r, 34); E.stamp(img, m, S, (129, 116), col)
    return t.write(img)


def build(get):
    """-> {자산 이름: 새 바이트}"""
    out = {}
    T = lambda n: E.Tex(get('texture/%s.tex' % n))
    for n, s in ILLUS.items(): out['texture/%s.tex' % n] = illus(T(n), s)
    for n, (r, txt) in NAVBOX.items(): out['texture/%s.tex' % n] = navbox(T(n), r, txt)
    out['texture/navsys_illustration_tokyocityrace.tex'] = tokyo(T('navsys_illustration_tokyocityrace'))
    for n, b in (('hud_messageoff', None), ('hud_messageon', None), ('hud_messageon_en', None), ('hud_messageon_en_x', '뒤로')):
        out['texture/%s.tex' % n] = message(T(n), b)
    out['texture/msg_go.tex'] = go(T('msg_go'))
    for n in ('ui_mc3load_logo', 'ui_mc3load_nowloading'): out['texture/%s.tex' % n] = loading(T(n))
    out['texture/navsys_title.tex'] = navtitle(T('navsys_title'))
    for suf in ('', '_en'):
        names = ['navsys_title%02d%s' % (k, suf) for k in range(1, 5)]
        try: texs = [T(n) for n in names]
        except Exception: continue
        for n, b in zip(names, navtitle_tiles(texs)): out['texture/%s.tex' % n] = b
    out['texture/tutorials01.tex'] = tutorial_bg(T('tutorials01'))
    return out
