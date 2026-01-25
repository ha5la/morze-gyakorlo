#!/usr/bin/env python3

import random
import sys
import wave

items = [
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j",
    "k", "l", "m", "n", "o", "p", "q", "r", "s", "t",
    "u", "v", "w", "x", "y", "z",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "stroke",
]

def append_wav(output, filename):
    with wave.open(filename, "rb") as w:
        try:
            output.setparams(w.getparams())
        except wave.Error:
            pass

        while True:
            frames = w.readframes(4096)
            if not frames:
                break
            output.writeframes(frames)


with wave.open("output.wav", "wb") as output:
    for _ in range(int(sys.argv[1])):
        item = random.choice(items)
        append_wav(output, f"cw-{item}.wav")
        append_wav(output, f"{item}.wav")
