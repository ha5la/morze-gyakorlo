#!/usr/bin/env -S uv run
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import cv2
import logging
import math
import matplotlib.pyplot as plt
import os
import random
import subprocess
import sys
import urllib.request
import wave

from pyhamtools import LookupLib, Callinfo
from slugify import slugify

logger = logging.getLogger(__name__)

class Morse:
    def __init__(self, output, wpm=35, tone_hz=600, sample_rate=44100):
        self.output = output
        self.delta_phi = 2 * math.pi * tone_hz / sample_rate
        self.samples_per_dit = int(sample_rate * 60 / (50 * wpm))  # PARIS = 50 dits: https://morsecode.world/international/timing/
        self.dit = self.compute_sinusoid(self.samples_per_dit)
        self.dah = self.compute_sinusoid(3 * self.samples_per_dit)
        self.audio_samples_written = 0

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

def create_map_image(output_path, highlighted_country):
    logger.info(f"Creating map for {highlighted_country}")
    fig = plt.figure(figsize=(16, 9), dpi=120)
    ax = plt.axes(projection=ccrs.PlateCarree())

    shpfilename = shpreader.natural_earth(resolution='110m', category='cultural', name='admin_0_countries')

    reader = shpreader.Reader(shpfilename)
    countries = reader.records()

    mapped_country = {
        "African Italy": "Italy",
        "Aland Islands": "Finland",
        "Alaska": "United States",
        "Antigua & Barbuda": None,
        "Aruba": None,
        "Asiatic Russia": "Russian Federation",
        "Asiatic Turkey": "Turkey",
        "Azores": "Portugal",
        "Balearic Islands": "Spain",
        "Barbados": None,
        "Bosnia-Herzegovina": "Bosnia and Herzegovina",
        "Canary Islands": "Spain",
        "Cayman Islands": "United States",
        "Ceuta & Melilla": "Spain",
        "Corsica": "France",
        "Crete": "Greece",
        "Curacao": "Venezuela",
        "Dodecanese": None,
        "East Malaysia": "Malaysia",
        "England": "United Kingdom",
        "European Turkey": "Turkey",
        "European Russia": "Russian Federation",
        "Falkland Islands": None,
        "Fed. Rep. of Germany": "Germany",
        "French Guiana": "United States",
        "Guam": None,
        "Guantanamo Bay": "Cuba",
        "Guernsey": None,
        "Hawaii": "United States",
        "Hong Kong": "China",
        "Isle of Man": "United Kingdom",
        "Jersey": None,
        "Kaliningrad": "Russian Federation",
        "Madeira Islands": "Portugal",
        "Malta": None,
        "Market Reef": "Sweden",
        "Montserrat": "Spain",
        "Norfolk Island": "New Caledonia",
        "Northern Ireland": "Ireland",
        "Saba & St. Eustatius": None,
        "Sardinia": None,
        "Seychelles": "Madagascar",
        "Sicily": "Italy",
        "Singapore": "Malaysia",
        "Sint Maarten": None,
        "St. Barthelemy": None,
        "St. Kitts & Nevis": None,
        "St. Martin": "Puerto Rico",
        "St. Vincent": None,
        "Svalbard": "Norway",
        "Trinidad & Tobago": "Venezuela",
        "Turks & Caicos Islands": "Dominican Republic",
        "US Virgin Islands": "United States",
        "Wales": "United Kingdom",
        "West Malaysia": "Malaysia",
	}.get(highlighted_country, highlighted_country)

#    country_names = sorted([c.attributes['NAME_LONG'] for c in countries])
#    if mapped_country is not None and mapped_country not in country_names:
#        raise RuntimeError(f"{mapped_country} is not in {country_names}")
    found = False
    for country in countries:
        if mapped_country and country.attributes['NAME_LONG'] == mapped_country:
            ax.add_geometries([country.geometry], ccrs.PlateCarree(), facecolor='red', edgecolor='darkred', linewidth=2)
            found = True
        else:
            ax.add_geometries([country.geometry], ccrs.PlateCarree(), facecolor='lightgray', edgecolor='gray', linewidth=0.5, alpha=0.3)

    if not found:
        logger.warning(f"country not found: {highlighted_country} (mapped to {mapped_country})")

    ax.set_global()
    plt.axis('off')
    plt.tight_layout(pad=0)
    plt.savefig(output_path, bbox_inches=None, pad_inches=0, facecolor='black', dpi=120)
    plt.close()

def cache_map_image(country_name):
    filename = f"map-{slugify(country_name)}.png"
    if not os.path.isfile(filename):
        create_map_image(filename, country_name)

    return filename

def append_wav(output, filename):
    with wave.open(filename, "rb") as w:
        while True:
            samples = w.readframes(4096)
            if not samples:
                break
            output.write_samples(samples)

def append_word(output, word):
    for ch in word:
        mapped = {"/": "stroke"}.get(ch, ch)
        append_wav(output, f"corpus/{mapped}.wav")

class VideoOutput:
    def __init__(self, filename):
        self.filename = filename
        self.writer = None
        self.frames_written = 0

    def __enter__(self):
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(self.filename, fourcc, 30, (1920, 1080))
        if not self.writer.isOpened():
            raise RuntimeError(f"Failed to open output video file {self.filename}")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.writer:
            self.writer.release()

    def write_frame(self, frame):
        self.writer.write(frame)
        self.frames_written += 1

def append_callsign(morse, cic, video, callsign):
    country = cic.get_country_name(callsign)
    logger.info(f"Appending callsign {callsign} ({country})")
    morse.write_text(callsign)
    morse.write_silence(40 * morse.samples_per_dit)
    append_word(morse, callsign)
    morse.write_silence(15 * morse.samples_per_dit)

    map_filename = cache_map_image(country)
    img = cv2.imread(map_filename)
    assert img.shape[:2] == (1080, 1920)
    frame_count = 30 * morse.audio_samples_written // 44100 - video.frames_written
    for i in range(frame_count):
        video.write_frame(img)

    logger.info(f"A-V: {morse.audio_samples_written/44100 - video.frames_written/30}")


def cache_online_file(url, filename):
    if not os.path.isfile(filename):
        logger.info(f"Downloading {url}")
        urllib.request.urlretrieve(url, filename)
    return filename

def load_callsigns():
    master_scp = cache_online_file("https://supercheckpartial.com/MASTER.SCP", "MASTER.SCP")
    logger.info("Loading callsigns")
    return [line.strip().lower() for line in open(master_scp)]

def main():
    logging.basicConfig(level=logging.INFO)

    cty_plist = cache_online_file("https://www.country-files.com/cty/cty.plist", "cty.plist")
    my_lookuplib = LookupLib(lookuptype="countryfile", filename=cty_plist)
    cic = Callinfo(my_lookuplib)

    with wave.open("audio.wav", "wb") as audio:
        audio.setparams((1, 2, 44100, 0, "NONE", "not compressed"))
        m = Morse(audio, wpm=int(sys.argv[1]))
        with VideoOutput("video.mp4") as video:
            callsigns = load_callsigns()
            for _ in range(int(sys.argv[2])):
                callsign = random.choice(callsigns)
                append_callsign(m, cic, video, callsign)

    logger.info("Multiplexing video and audio")
    subprocess.run([
        'ffmpeg',
        '-i', 'video.mp4',
        '-i', 'audio.wav',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-shortest',
        '-y',
        'out.mp4'
    ], check=True)

if __name__ == "__main__":
    main()
