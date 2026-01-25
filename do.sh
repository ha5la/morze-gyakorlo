#!/bin/sh

set -uex

wpm=35
effective_wpm=13
total_letter_count=100

./gencw.sh "${wpm}" "${effective_wpm}"
./compose.py "${total_letter_count}"
convert -pointsize 40 -fill white -stroke black -font Courier-Bold -draw "text 20 40 'különálló, hívójeles karakterek'; text 20 80 '${wpm} WPM'" image.jpg x.jpg
ffmpeg -y -loop 1 -i x.jpg -i output.wav -c:a aac -ab 112k -c:v libx264 -shortest -strict -2 out.mp4
