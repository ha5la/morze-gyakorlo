#!/usr/bin/env -S uv run
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
import logging
import matplotlib.pyplot as plt
import os
import subprocess
import sys
import urllib.request
import wave

from morse import Morse
from pyhamtools import LookupLib, Callinfo
from random import Random
from slugify import slugify
from threading import Thread
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

logger = logging.getLogger(__name__)

def natural_earth_list(resolution, name, field_name="NAME_LONG"):
    shpfilename = shpreader.natural_earth(resolution=resolution, category="cultural", name=name)
    reader = shpreader.Reader(shpfilename)
    for item in reader.records():
        yield item.attributes[field_name], item.geometry

def draw_natural_earth_item(output_path, geometry):
    fig = plt.figure(figsize=(16, 9), dpi=120)
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

    ax.stock_img()
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    ax.add_feature(cfeature.RIVERS)

    ax.add_geometries([geometry], ccrs.PlateCarree(), facecolor='red', edgecolor='darkred', linewidth=2, alpha=0.5)

    ax.set_global()
    ax.axis('off')
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(output_path, bbox_inches=None, pad_inches=0, facecolor='black', dpi=120)
    plt.close(fig)

def canonicalize_country_name(name):
    name = slugify(name.lower().replace("saint-", " saint ").replace("st.", " saint ").replace("&", " and ").replace("-", " and "))
    return {
        # name differences
        "cape-verde": "republic-of-cabo-verde",
        "cocos-keeling-islands": "cocos-islands",
        "falkland-islands": "falkland-islands-malvinas",
        "faroe-islands": "faeroe-islands",
        "fed-rep-of-germany": "germany",
        "guantanamo-bay": "us-naval-base-guantanamo-bay",
        "madeira-islands": "madeira",
        "pitcairn-island": "pitcairn-islands",
        "republic-of-kosovo": "kosovo",
        "reunion-island": "reunion",
        "saint-vincent": "saint-vincent-and-the-grenadines",
        "slovak-republic": "slovakia",
        "svalbard": "svalbard-islands",
        "us-virgin-islands": "united-states-virgin-islands",
        "vatican-city": "vatican",

        # dxccs belonging to countries
        "african-italy": "italy",
        "asiatic-russia": "russian-federation",
        "asiatic-turkey": "turkey",
        "east-malaysia": "malaysia",
        "eastern-kiribati": "kiribati",
        "european-russia": "russian-federation",
        "european-turkey": "turkey",
        "kaliningrad": "russian-federation",
        "south-cook-islands": "cook-islands",
        "uk-base-areas-on-cyprus": "cyprus",
        "west-malaysia": "malaysia",
        "western-kiribati": "kiribati",

        # special dxccs
        "itu-hq": "switzerland",
        "united-nations-hq": "new-york",

        # islands belonging to countries
        "agalega-and-saint-brandon": "mauritius",
        "balearic-islands": "spain",
        "ceuta-and-melilla": "spain",
        "chatham-islands": "new-zealand",
        "corsica": "france",
        "crete": "greece",
        "dodecanese": "greece",
        "easter-island": "chile",
        "fernando-de-noronha": "brazil",
        "galapagos-islands": "ecuador",
        "juan-fernandez-islands": "chile",
        "lakshadweep-islands": "india",
        "mariana-islands": "northern-mariana-islands",
        "market-reef": "sweden",
        "ogasawara": "japan",
        "rodriguez-island": "mauritius",
        "san-andres-and-providencia": "colombia",
        "sardinia": "italy",
        "sicily": "italy",
        "temotu-province": "solomon-islands",

        # nice approximation for drawing maps
        "bonaire": "venezuela",
        "saba-and-saint-eustatius": "saint-kitts-and-nevis",
    }.get(name, name)


def create_map_image(output_path, highlighted_country):
    logger.info(f"Creating map for {highlighted_country}")
    for name, geom in natural_earth_list("50m", "admin_0_countries"):
        if canonicalize_country_name(name) == highlighted_country:
            return draw_natural_earth_item(output_path, geom)
    for name, geom in natural_earth_list("50m", "admin_0_countries", "NAME"):
        if canonicalize_country_name(name) == highlighted_country:
            return draw_natural_earth_item(output_path, geom)
    for name, geom in natural_earth_list("10m", "admin_0_map_units"):
        if canonicalize_country_name(name) == highlighted_country:
            return draw_natural_earth_item(output_path, geom)
    for name, geom in natural_earth_list("50m", "admin_0_tiny_countries"):
        if canonicalize_country_name(name) == highlighted_country:
            return draw_natural_earth_item(output_path, geom)
    for name, geom in natural_earth_list("110m", "admin_1_states_provinces", "name"):
        if canonicalize_country_name(name) == highlighted_country:
            return draw_natural_earth_item(output_path, geom)
    raise RuntimeError(f"No geometry for {highlighted_country}")

def cache_map_image(country_name):
    os.makedirs("map.d", exist_ok=True)
    filename = f"map.d/{slugify(country_name)}.png"
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
    def __init__(self, output, fps=2):
        self.output = output
        self.fps = fps
        self.frames_written = 0

    def time(self):
        return self.frames_written / self.fps

    def write_frame(self, filename):
        with open(filename, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                self.output.write(chunk)
        self.frames_written += 1

    def write_country_frames_until(self, country, t):
        image = cache_map_image(country)

        frame_count = int(self.fps * t) - self.frames_written
        for i in range(frame_count):
            self.write_frame(image)

        logger.info(f"A-V: {t - self.time()}")

    def close(self):
        self.output.close()

class NoVideo:
    def write_country_frames_until(self, _country, _t):
        pass

    def close(self):
        pass

def append_callsign(name, morse, cic, video, callsign):
    try:
        country = canonicalize_country_name(cic.get_country_name(callsign))
        logger.info(f"{name}: Appending callsign {callsign} ({country})")
        morse.write_text(callsign)
        morse.write_silence(40 * morse.samples_per_dit)
        append_word(morse, callsign)
        morse.write_silence(15 * morse.samples_per_dit)
        video.write_country_frames_until(country, morse.time())

    except KeyError as e:
        logger.warning("Failed to get country for callsign: %s", callsign)

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

def process(name, cty_plist, audio_file, video, callsigns):
    my_lookuplib = LookupLib(lookuptype="countryfile", filename=cty_plist)
    cic = Callinfo(my_lookuplib)
    m = Morse(audio_file, wpm=int(sys.argv[1]))
    for callsign in tqdm(callsigns, desc=name):
        append_callsign(name, m, cic, video, callsign)

    video.close()
    audio_file.close()

class DevNull:
    def write(self, _):
        pass

    def close(self):
        pass

def main():
    logging.basicConfig(level=logging.INFO)

    callsigns = Random(0).sample(load_callsigns(), k=int(sys.argv[2]))
    cty_plist = cache_online_file("https://www.country-files.com/cty/cty.plist", "cty.plist")

    video_rd, video_wr = os.pipe()
    with subprocess.Popen([
        'ffmpeg',
        '-f', 's16le', '-ar', '48000', '-ac', '1',
        '-i', 'pipe:0',
        '-framerate', '2',
        '-f', 'image2pipe',
        '-i', f'pipe:{video_rd}',
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
    ], stdin=subprocess.PIPE, pass_fds=[video_rd], stderr=subprocess.DEVNULL) as ffmpeg:
        os.close(video_rd)
        video_file = os.fdopen(video_wr, "wb")
        video = VideoOutput(video_file)
        with logging_redirect_tqdm():
            video_thread = Thread(target=process, args=("video", cty_plist, DevNull(), video, callsigns))
            video_thread.start()
            process("audio", cty_plist, ffmpeg.stdin, NoVideo(), callsigns)
            video_thread.join()


if __name__ == "__main__":
    main()
