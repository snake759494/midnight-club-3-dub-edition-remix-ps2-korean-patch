#!/bin/bash
# 설치된 pnach = 배포용 pnach + 테스트용 가상 패드 섹션
cd "$(dirname "$0")"
{ cat ../widescreen/SLUS-21355_3021E351.pnach; echo; PYTHONIOENCODING=utf-8 python vpad.py section; } > ~/Documents/PCSX2/patches/SLUS-21355_3021E351.pnach
printf '[Patches]\nEnable = Widescreen 16:9\nEnable = Widescreen 16:9 HUD fix\nEnable = DEV virtual pad\n' > ~/Documents/PCSX2/gamesettings/SLUS-21355_3021E351.ini
