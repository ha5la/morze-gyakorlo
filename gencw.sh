#!/bin/sh

set -uex

wpm=$1
effective_wpm=$2

for i in a b c d e f g h i j k l m n o p q r s t u v w x y z 1 2 3 4 5 6 7 8 9 0; do
    echo $i | ebook2cw -w "${wpm}" -e "${effective_wpm}" -s 44100 -o "cw-$i-"
    ffmpeg -y -i "cw-$i-0000.mp3" "cw-$i.wav"
done
echo / | ebook2cw -w "${wpm}" -e "${effective_wpm}" -s 44100 -o "cw-stroke-"
    ffmpeg -y -i "cw-stroke-0000.mp3" "cw-stroke.wav"
