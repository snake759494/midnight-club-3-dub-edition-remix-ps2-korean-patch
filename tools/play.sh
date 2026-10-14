#!/bin/bash
# 백그라운드 조작: play.sh 접두어 "키열"
# 키: U D L R X O T S(=START) Q(=사각) wN(대기) s(캡처) F(세이브1) G(로드1)
S=${SHOTS:-$(dirname $0)/../work/shots}; mkdir -p "$S"
E="powershell -ExecutionPolicy Bypass -File $(dirname $0)/emu.ps1"
V="python $(dirname $0)/vpad.py"
n=1
for k in $2; do
  case $k in
    U|D|L|R|X|O|T) $V press $k; sleep 0.6;;
    S) $V press START; sleep 0.6;;  Q) $V press S; sleep 0.6;;
    F) $V save 1 >/dev/null; sleep 2;;  G) $V load 1 >/dev/null; sleep 4;;
    w*) sleep ${k#w};;
    s) $E shot "$S/${1}$n.png" >/dev/null; n=$((n+1));;
  esac
done
