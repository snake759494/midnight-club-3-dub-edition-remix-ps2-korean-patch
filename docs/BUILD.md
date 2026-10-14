# 재빌드

Python 3.13에서 검증했습니다. 저장소 루트에 해시가 일치하는 원본을 `Midnight Club 3 - DUB Edition Remix (USA).iso`라는
이름으로 두고, 나눔스퀘어 네오 폰트(`NanumSquareNeo-cBd.ttf`, `NanumSquareNeo-dEb.ttf`, `NanumSquareNeo-eHv.ttf`)를
루트에 별도로 준비합니다. 이 파일들은 Git에서 제외됩니다.

```powershell
python -m pip install -r requirements.txt
cd tools
python -X utf8 build.py      # 원본 ISO → Midnight Club 3 - DUB Edition Remix (Korean).iso (원본과 같은 폴더)
python -X utf8 verify.py     # 목차·데이터 검증
python -X utf8 check_ko.py   # 번역 검사(서식·줄바꿈·폰트에 없는 문자)
python -X utf8 hudfix.py     # widescreen/SLUS-21355_3021E351.pnach 의 HUD fix 섹션 재생성
```

번역 표에는 영어 원문이 없습니다. 첫 빌드 때 `dumpsrc.py`·`dumpsubs.py`가 원본 ISO에서 원문을 뽑아
`translation/src.tsv`, `translation/subs_src_*.txt`를 만들고(Git 제외), 번역 ID(원문 UTF-8 SHA-1 앞 16자리)로 짝을 맞춥니다.
완성 ISO SHA-256은 README와 일치해야 합니다.

## 구성

- `build.py`: 전체 빌드(문자열 표, 자막, 게임 폰트, 플래시 글꼴·문구, 텍스처, ELF 패치, ASSETS.DAT·ISO9660·UDF 갱신)
- `strtbl.py`, `subs.py`, `dumpsrc.py`, `dumpsubs.py`, `tsvesc.py`: 문자열 표·자막 처리
- `kfont.py`: 게임 폰트(.fonttex/.tex) 한글 글리프 추가
- `flashfont.py`, `flashtext.py`, `stext.py`, `aspool.py`, `flashtex.py`, `flashkeys.py`: 플래시 pck 글꼴·정적 텍스트·상수 풀
- `imgedit.py`, `imgspecs.py`, `gsimg.py`, `gsmem.py`, `swz.py`, `tex.py`: 텍스처 다시 그리기
- `elfpatch.py`: UTF-8 복원 루틴·플래시 문자열 조회·한글 아틀라스 적재(두 번째 LOAD 세그먼트)
- `dave.py`, `davew.py`, `udf.py`: ASSETS.DAT 아카이브와 디스크 파일 레코드
- `hudfix.py`: 16:9 HUD·플래시 UI 보정 pnach 섹션 생성
- `verify.py`, `check_ko.py`, `mipsim.py`(패치 코드 검증용 MIPS 해석기), `elf.py`, `get.py`, `preview.py`, `sstate.py`: 검증·분석
- `emu.ps1`, `play.sh`, `vpad.py`, `devpatch.sh`: PCSX2 자동 조작(백그라운드 창, PINE + 테스트 전용 가상 패드 섹션).
  배포 pnach에는 가상 패드가 없습니다.

## 패치 생성/복원

```powershell
xdelta3 -e -s "Midnight Club 3 - DUB Edition Remix (USA).iso" "Midnight Club 3 - DUB Edition Remix (Korean).iso" Midnight_Club_3_DUB_Remix_PS2_KO_v1.2.xdelta
xdelta3 -d -s "Midnight Club 3 - DUB Edition Remix (USA).iso" Midnight_Club_3_DUB_Remix_PS2_KO_v1.2.xdelta roundtrip.iso
```

xdelta는 압축 옵션 없이 만듭니다. 버전에 따라 패치 바이트는 달라질 수 있지만 복원 ISO는 같아야 합니다.
생성한 게임 자료나 폰트를 커밋하지 마세요.
