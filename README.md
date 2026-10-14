# 미드나이트 클럽 3: DUB 에디션 리믹스 · PS2 북미판 한글 패치 v1.2

대상: **Midnight Club 3 - DUB Edition Remix (USA), SLUS-21355**

비공식 팬 한글 패치입니다. 적법하게 보유한 북미판 원본 ISO에 xdelta 패치를 적용해 사용합니다.
릴리즈 첨부 파일은 xdelta와 PCSX2용 16:9 와이드 패치(pnach)이며 원본·완성 ISO, 게임 파일, 폰트는 배포하지 않습니다.

## 패치 적용

| 파일 | SHA-256 |
|---|---|
| 원본 `Midnight Club 3 - DUB Edition Remix (USA).iso` (8,539,963,392바이트) | `de199f7e7f57b7cb603a129217f7482d50644fd66558450dfeb5612857b732f9` |
| 완성 `Midnight Club 3 - DUB Edition Remix (Korean).iso` (8,539,963,392바이트) | `a1738d7ecd1d14b3abb7f27fb2065ffb5252ac3630903269df6a00fb167530b5` |
| `Midnight_Club_3_DUB_Remix_PS2_KO_v1.2.xdelta` | `1527f2d702f8c407e13e8438a32204c5e78f99f2e0e4ce50d0e04a14677b1981` |
| `SLUS-21355_3021E351.pnach` (와이드 패치) | `8946eac3d67c0984d3ee31932d122883a40f2d5b591fd4248f98f9d5c8173309` |

```powershell
xdelta3 -d -s ".\Midnight Club 3 - DUB Edition Remix (USA).iso" .\Midnight_Club_3_DUB_Remix_PS2_KO_v1.2.xdelta ".\Midnight Club 3 - DUB Edition Remix (Korean).iso"
```

영상 자막은 기본값이 꺼짐입니다. 옵션 → 게임 옵션 → **영상 자막 켬**으로 바꾸면 한글 자막이 나옵니다.

## 16:9 와이드 패치

한글 패치는 실행 파일을 수정하므로 게임 CRC가 원본(60A42FF5)과 달리 **3021E351**이 됩니다. PCSX2 내장 와이드 패치는
CRC로 찾기 때문에 한글판에는 자동 적용되지 않아, 한글판 CRC용 `SLUS-21355_3021E351.pnach`를 릴리즈에 함께 첨부합니다.

- **Widescreen 16:9**: PCSX2 내장 패치를 그대로 옮긴 것(3D 시야를 16:9로 넓힘).
- **Widescreen 16:9 HUD fix**: 이 프로젝트에서 직접 만든 보정. 주행 HUD(속도계·타코미터·미니맵·화살표·시간)와
  메뉴·차고·로딩 화면이 가로로 늘어나지 않고 가운데 4:3 비율로 나옵니다.

사용법은 [docs/WIDESCREEN.md](docs/WIDESCREEN.md)를 보세요.

## 번역 범위

- 게임 문자열 표 고유 문자열 3,982개 중 3,204개: 메뉴·옵션, 커리어·도쿄 챌린지·아케이드, 레이스 설명·대결 상대 소개,
  보상·해제 안내, 레이스 에디터, 메모리 카드·네트워크(DNAS) 안내 등.
- 영상·컷신 자막 524개 파일(고유 182개, 1,569큐): 튜토리얼·스토리·보상 영상.
- 플래시 UI(차고·상단 배너·하단 버튼 안내·대화상자·타이틀·내비 시스템·로딩·보상/레이스 종료 화면) 전부 한글 표시.
- 차량·바이크 이름 한글 표기(예: 64 임팔라, 닷지 차저 SRT8). H1·350Z처럼 기호·숫자뿐인 모델명은 그대로.
- 게임 텍스처 51장(내비 시스템 제목·아이콘, 레이스 종류 그림, 출발, 로딩 로고, 안내판, 튜토리얼 배경)과
  고정 문구(가속/최고속도/핸들링 세로 표기, 뒤로, 도시명, 차종 이름, 레이스 n / m)를 한글로 다시 그림.
- 외부 번역기·기계 번역 없이 직접 번역했습니다. 용어는 [translation/glossary.md](translation/glossary.md) 기준.

## 영어로 남은 부분

인명, 곡명·아티스트, 브랜드·클럽 로고, 제작진 크레딧, 로딩 화면 오른쪽 위 LOADING(벡터 도형), 기존 세이브에 저장된 차 별명.

## 검증

- PCSX2 2.2: 부팅, 법적 고지, 타이틀, 프로필, 메인 메뉴, 옵션, 커리어·도쿄 챌린지 메뉴, 로딩 화면, 차고(관리·구매·성능 숍),
  도시 주행·레이스 HUD, 일시정지 메뉴, 튜토리얼 영상 자막, 내비 시스템, 16:9 와이드 패치(HUD·메뉴·차고 보정).
- 공개 소스 재빌드 결과와 xdelta 복원 ISO SHA-256 일치.
- **미검증**: 전체 플레이, 온라인, 레이스 에디터 세부 화면, 실기.

## 저장소 구성

- `translation/ko_*.tsv`: 원문 ID(영문 UTF-8의 SHA-1 앞 16자리) + 한국어. 영어 원문은 빌드 때 원본 ISO에서 추출
- `translation/subs_ko_*.txt`: 자막 한국어 큐, `translation/cars.tsv`: 차 이름 표기, `translation/glossary.md`: 용어집
- `tools/`: 빌드·분석 도구, 재빌드는 [docs/BUILD.md](docs/BUILD.md), 구조는 [docs/TECHNICAL.md](docs/TECHNICAL.md)
- `widescreen/`: PCSX2 16:9 와이드 패치
- 권리 고지 [RIGHTS.md](RIGHTS.md), 변경 내역 [CHANGELOG.md](CHANGELOG.md)
