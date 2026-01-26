#!/bin/sh

set -uex

wpm=35
total_count=1000

curl -SL -C- -o MASTER.SCP https://supercheckpartial.com/MASTER.SCP
./main.py "${wpm}" "${total_count}"
convert -pointsize 40 -fill white -stroke black -font Courier-Bold -draw "text 20 40 'hívójelek'; text 20 80 '${wpm} WPM'" image.jpg x.jpg
ffmpeg -y -loop 1 -i x.jpg -i output.wav -c:a aac -ab 112k -c:v libx264 -shortest -strict -2 out.mp4
