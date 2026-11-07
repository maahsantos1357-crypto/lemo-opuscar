#!/bin/sh
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
LIB=${LIB:-$(cd "$HERE/../.." && pwd)}; export LIB; cd "$LIB"
node core/render/events.mjs "$HERE" --size 1080x1920
node core/render/video.mjs "$HERE" --size 1080x1920 --fps 24 --workers ${WORKERS:-4} --out "$HERE/out/video.mp4"
"$LIB/.venv/bin/python" "$HERE/mix.py"
# mux com loudnorm em duas passagens (o mux.sh da biblioteca recusa áudio com ffmpeg 6)
cd "$HERE"
M=$(ffmpeg -hide_banner -i out/mix.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
v() { echo "$M" | grep "\"$1\"" | cut -d'"' -f4; }
ffmpeg -v error -y -i out/video.mp4 -i out/mix.wav -map 0:v -map 1:a -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(v input_i):measured_TP=$(v input_tp):measured_LRA=$(v input_lra):measured_thresh=$(v input_thresh):offset=$(v target_offset):linear=true,aresample=48000" -c:a aac -b:a 256k -movflags +faststart -shortest quem-ganha-com-as-bets-desenho-longo.mp4
ffmpeg -hide_banner -i quem-ganha-com-as-bets-desenho-longo.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "I:|Peak:" | tail -2
