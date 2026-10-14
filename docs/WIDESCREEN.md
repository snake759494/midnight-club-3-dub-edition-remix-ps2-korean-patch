# PCSX2 16:9 와이드 패치 사용법

`SLUS-21355_3021E351.pnach`는 한글 패치판 전용 PCSX2 와이드 패치입니다. 두 항목이 들어 있습니다.

| 항목 | 내용 |
|---|---|
| **Widescreen 16:9** | PCSX2 내장 패치 모음(`resources/patches.zip`)의 원본용 와이드 패치(`SLUS-21355_60A42FF5.pnach`)를 그대로 옮긴 것. 게임의 화면비 상수(4:3 = 1.3333)를 16:9 = 1.7778로 바꿔 3D 화면의 가로 시야를 넓힙니다(세로 시야 유지). |
| **Widescreen 16:9 HUD fix** | 이 프로젝트에서 직접 만든 보정. 와이드에서 가로로 늘어나던 주행 HUD(속도계·타코미터와 바늘, 미니맵, 3D 방향 화살표, 백미러, 시간·순위 글자)와 메뉴·차고·로딩 화면(플래시 UI)을 가운데 4:3 비율로 그립니다. 3D 배경은 16:9 전체로 나옵니다. |

**왜 따로 필요한가:** 한글 패치는 실행 파일(SLUS_213.55)을 수정하므로 PCSX2가 계산하는 게임 CRC가 원본 **60A42FF5**에서
**3021E351**로 바뀝니다. PCSX2 내장 패치는 CRC로 찾기 때문에 한글판에는 자동으로 붙지 않습니다.
화면비 상수 위치(0x527E14)는 한글판에서도 원본 값 그대로라 내장 패치 내용을 그대로 쓸 수 있습니다.

**두 항목을 함께 켜세요.** HUD fix만 켜면 화면은 4:3인데 HUD·메뉴만 좁아집니다.

## PCSX2 2.x (Qt) — 권장

1. 릴리즈에서 받은 `SLUS-21355_3021E351.pnach`를 PCSX2 사용자 폴더의 `patches` 폴더에 넣습니다.
   - 설치판: `문서\PCSX2\patches\`
   - 포터블판: `PCSX2 폴더\patches\`
   - 파일 이름을 바꾸지 마세요(PCSX2는 `시리얼_CRC.pnach` 이름으로 찾습니다).
2. PCSX2 게임 목록에서 **Midnight Club 3 - DUB Edition Remix**(한글 ISO)를 오른쪽 클릭 → **속성(Properties)**.
3. **패치(Patches)** 탭에서 **Widescreen 16:9**와 **Widescreen 16:9 HUD fix** 두 개에 모두 체크합니다.
   - 목록이 비어 있으면 1단계의 폴더 위치·파일 이름과, 한글 ISO로 실행했는지(CRC 3021E351) 확인하세요.
4. 화면 비율은 패치가 자동으로 16:9로 바꿉니다(`gsaspectratio=16:9`). 수동으로 정하려면
   **그래픽(Graphics) → 디스플레이(Display) → 화면 비율(Aspect Ratio)**을 **16:9**로,
   **FMV 화면 비율 전환(FMV Aspect Ratio Override)**은 **4:3**으로 둡니다(동영상은 원래 4:3).
5. 게임을 시작하면 화면에 “2개의 게임 패치가 활성화되었습니다”가 표시됩니다.

설정 파일로 켜려면 `문서\PCSX2\gamesettings\SLUS-21355_3021E351.ini`에 다음 내용을 저장합니다.

```ini
[Patches]
Enable = Widescreen 16:9
Enable = Widescreen 16:9 HUD fix

[EmuCore/GS]
AspectRatio = 16:9
FMVAspectRatioSwitch = 4:3
```

## PCSX2 1.6 (wxWidgets)

1. 파일 이름을 `3021E351.pnach`로 바꿔 `cheats_ws` 폴더에 넣습니다.
2. **시스템(System) → 와이드스크린 패치 사용(Enable Widescreen Patches)**을 켭니다.
3. **설정(Config) → 비디오(Video) → 창 설정(Window Settings)**에서 화면 비율을 16:9로 바꿉니다.

1.6은 항목별 선택이 없어 파일 안의 모든 항목이 적용됩니다(1.6에서는 미검증).

## 알려진 점

- 일시정지 메뉴는 원래 오른쪽 정렬 디자인이라 오른쪽에 붙어 나옵니다(보정 대상 아님, 깨짐 없음).
- 동영상(FMV)은 원래 4:3입니다.
- 원본(영문) ISO에는 PCSX2 내장 패치(60A42FF5)를 쓰면 됩니다. 이 파일은 한글판 전용이며, HUD fix는 한글 패치 코드 영역
  (RAM 0x1FFF000~)을 쓰므로 원본 ISO에는 쓰지 마세요.
- 끄려면 패치 탭의 체크를 해제하거나 위 `.ini`의 `Enable` 줄을 지웁니다.
- 동작 원리는 [TECHNICAL.md](TECHNICAL.md)의 “와이드 패치 구현”, 생성 도구는 `tools/hudfix.py`입니다.

## 확인 내역

PCSX2 2.2에서 확인(로그 `Enabled patch: Widescreen 16:9`, `Enabled patch: Widescreen 16:9 HUD fix`):
법적 고지, 타이틀, 프로필, 메인·커리어 메뉴, 로딩 화면, 차고(차량 관리·정보), 도시 주행 HUD, 일시정지 메뉴.
