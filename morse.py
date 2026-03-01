import math

class Morse:
    def __init__(self, output, wpm=35, tone_hz=600, sample_rate=48000):
        self.output = output
        self.sample_rate = sample_rate
        self.delta_phi = 2 * math.pi * tone_hz / sample_rate
        self.samples_per_dit = int(sample_rate * 60 / (50 * wpm))  # PARIS = 50 dits: https://morsecode.world/international/timing/
        self.dit = self.compute_sinusoid(self.samples_per_dit)
        self.dah = self.compute_sinusoid(3 * self.samples_per_dit)
        self.audio_samples_written = 0

    def time(self):
        return self.audio_samples_written / self.sample_rate

    def compute_sinusoid(self, sample_count):
        result = bytearray(2 * sample_count)
        phi = 0
        fade_len = self.samples_per_dit // 5
        for i in range(sample_count):
            t = min(1, i / fade_len, (sample_count - 1 - i) / fade_len)
            t = t * t * (3 - 2 * t)
            sample = int(math.sin(phi) * 20000 * t)
            result[i * 2] = sample & 255
            result[i * 2 + 1] = (sample >> 8) & 255
            phi += self.delta_phi

        return result

    def write_samples(self, samples):
        self.output.write(samples)
        self.audio_samples_written += len(samples) // 2

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
