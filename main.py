#!/usr/bin/env python3
import math
import random
import sys
import wave

class Morse:
    def __init__(self, output, wpm=35, tone_hz=600, sample_rate=44100):
        self.output = output
        self.delta_phi = 2 * math.pi * tone_hz / sample_rate
        self.samples_per_dit = int(sample_rate * 60 / (50 * wpm))  # PARIS = 50 dits: https://morsecode.world/international/timing/
        self.dit = self.compute_sinusoid(self.samples_per_dit)
        self.dah = self.compute_sinusoid(3 * self.samples_per_dit)

    def compute_sinusoid(self, sample_count):
        result = bytearray(2 * sample_count)
        phi = 0
        fade_len = self.samples_per_dit // 10
        for i in range(sample_count):
            fade = min(1, i / fade_len, (sample_count - 1 - i) / fade_len)
            sample = int(math.sin(phi) * 20000 * fade)
            result[i * 2] = sample & 255
            result[i * 2 + 1] = (sample >> 8) & 255
            phi += self.delta_phi

        return result

    def write_samples(self, samples):
        self.output.writeframes(samples)

    def write_silence(self, sample_count):
        self.write_samples(bytearray(2 * sample_count))

    def write_character(self, ch):
        mapping = {
            "A": ".-",
            "B": "-...",
            "C": "-.-.",
            "D": "-..",
            "E": ".",
            "F": "..-.",
            "G": "--.",
            "H": "....",
            "I": "..",
            "J": ".---",
            "K": "-.-",
            "L": ".-..",
            "M": "--",
            "N": "-.",
            "O": "---",
            "P": ".--.",
            "Q": "--.-",
            "R": ".-.",
            "S": "...",
            "T": "-",
            "U": "..-",
            "V": "...-",
            "W": ".--",
            "X": "-..-",
            "Y": "-.--",
            "Z": "--..",
            "1": ".----",
            "2": "..---",
            "3": "...--",
            "4": "....-",
            "5": ".....",
            "6": "-....",
            "7": "--...",
            "8": "---..",
            "9": "----.",
            "0": "-----",
            "/": "-..-.",
            " ": " ",
        }
        mapped = mapping[ch]
        for bit in mapped:
            if bit == ".":
                self.write_samples(self.dit)
            elif bit == "-":
                self.write_samples(self.dah)
            elif bit == " ":
                self.write_silence(4 * self.samples_per_dit)
            self.write_silence(self.samples_per_dit)
        self.write_silence(2 * self.samples_per_dit)

    def write_text(self, text):
        for c in text.upper():
           self.write_character(c)

def append_wav(output, filename):
    with wave.open(filename, "rb") as w:
        while True:
            frames = w.readframes(4096)
            if not frames:
                break
            output.writeframes(frames)

def append_word(output, word):
    for ch in word:
        mapped = {"/": "stroke"}.get(ch, ch)
        append_wav(output, f"corpus/{mapped}.wav")

def append_callsign(output, morse, callsign):
    print(f"Appending callsign {callsign}")
    morse.write_text(callsign)
    morse.write_silence(40 * morse.samples_per_dit)
    append_word(output, callsign)
    morse.write_silence(15 * morse.samples_per_dit)

def main():
    with wave.open("output.wav", "wb") as output:
        output.setparams((1, 2, 44100, 0, "NONE", "not compressed"))
        m = Morse(output, wpm=int(sys.argv[1]))
        callsigns = [line.strip().lower() for line in open("MASTER.SCP")]
        for _ in range(int(sys.argv[2])):
            append_callsign(output, m, random.choice(callsigns))

if __name__ == "__main__":
    main()
