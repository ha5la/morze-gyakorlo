#!/usr/bin/env -S uv run
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import cartopy.feature as cfeature
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
from tqdm import trange
from tqdm.contrib.logging import logging_redirect_tqdm

logger = logging.getLogger(__name__)

class Morse:
    def __init__(self, output, wpm=35, tone_hz=600, sample_rate=48000):
        self.output = output
        output.setparams((1, 2, sample_rate, 0, "NONE", "not compressed"))
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
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

    ax.stock_img()
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    ax.add_feature(cfeature.RIVERS)

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
            ax.add_geometries([country.geometry], ccrs.PlateCarree(), facecolor='red', edgecolor='darkred', linewidth=1, alpha=0.5)
            found = True
            break

    if not found:
        logger.warning(f"country not found: {highlighted_country} (mapped to {mapped_country})")

    ax.set_global()
    ax.axis('off')
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(output_path, bbox_inches=None, pad_inches=0, facecolor='black', dpi=120)
    plt.close(fig)

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
        append_wav(output, f"corpus/{output.sample_rate}/{mapped}.wav")

class VideoOutput:
    def __init__(self, filename, fps=2):
        self.filename = filename
        self.fps = fps
        self.writer = None
        self.frames_written = 0

    def time(self):
        return self.frames_written / self.fps

    def __enter__(self):
        fourcc = cv2.VideoWriter_fourcc(*'png ')
        self.writer = cv2.VideoWriter(self.filename, fourcc, self.fps, (1920, 1080))
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

    image = cv2.imread(cache_map_image(country))
    assert image.shape[:2] == (1080, 1920)

    frame_count = int(video.fps * morse.time()) - video.frames_written
    for i in range(frame_count):
        video.write_frame(image)

    logger.info(f"A-V: {morse.time() - video.time()}")


def cache_online_file(url, filename):
    if not os.path.isfile(filename):
        logger.info(f"Downloading {url}")
        urllib.request.urlretrieve(url, filename)
    return filename

def load_callsigns():
    master_scp = cache_online_file("https://supercheckpartial.com/MASTER.SCP", "MASTER.SCP")
    logger.info("Loading callsigns")
    result = [line.strip().lower() for line in open(master_scp) if not line.startswith('#')]
    logger.info(f"Total number of callsigns in MASTER.SCP: {len(result)}")
    return result

def main():
    logging.basicConfig(level=logging.INFO)

    callsigns = load_callsigns()
    cty_plist = cache_online_file("https://www.country-files.com/cty/cty.plist", "cty.plist")
    my_lookuplib = LookupLib(lookuptype="countryfile", filename=cty_plist)
    cic = Callinfo(my_lookuplib)

    with wave.open("audio.wav", "wb") as audio:
        m = Morse(audio, wpm=int(sys.argv[1]))
        with VideoOutput("video.mkv") as video:
            with logging_redirect_tqdm():
                for _ in trange(int(sys.argv[2])):
                    append_callsign(m, cic, video, random.choice(callsigns))

    logger.info("Multiplexing video and audio")
    subprocess.run([
        'ffmpeg',
        '-i', 'video.mkv',
        '-i', 'audio.wav',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-tune', 'stillimage',
        '-crf', '18',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'flac',
        '-compression_level', '12',  # this is for flac
        '-af', 'pan=stereo|c0=c0|c1=-1*c0,adelay=0|10',  # Stereoize with Haas
        '-cues_to_front', '1',  # "-movflags +faststart" equivalent for mkv
        '-shortest',
        '-y',
        'out.mkv'
    ], check=True)

if __name__ == "__main__":
    main()
