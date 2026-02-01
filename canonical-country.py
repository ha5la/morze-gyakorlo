#!/usr/bin/env -S uv run
import cartopy.io.shapereader as shpreader
import logging
import os
import unittest
import subprocess

from pyhamtools import LookupLib, Callinfo
from slugify import slugify

logger = logging.getLogger(__name__)

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

class TestCanonicalize(unittest.TestCase):
    def test_st_barnhelemy(self):
        self.assertEqual(canonicalize_country_name("Saint-Barthélemy"), "saint-barthelemy")
        self.assertEqual(canonicalize_country_name("St. Barthelemy"), "saint-barthelemy")

def dump_canonicalized(filename, names):
    countries = sorted(set([canonicalize_country_name(name) for name in names]))
#    countries = sorted(names)
    with open(filename, "w") as f:
        f.writelines([f"{c}\n" for c in countries])

# resolution: 110m 50m 10m
# category: cultural physical
# name: admin_0_countries

def natural_earth_list(resolution, name, field_name="NAME_LONG"):
    shpfilename = shpreader.natural_earth(resolution=resolution, category="cultural", name=name)
    reader = shpreader.Reader(shpfilename)
    return [c.attributes[field_name] for c in reader.records()]

def dump_natural_earth():
    l = set()
    l = l.union(natural_earth_list("10m", "admin_0_countries"))
    l = l.union(natural_earth_list("10m", "admin_0_countries", "NAME"))
    l = l.union(natural_earth_list("10m", "admin_0_map_units"))  # Wales
    l = l.union(natural_earth_list("50m", "admin_0_tiny_countries"))  # Canary islands
    l = l.union(natural_earth_list("110m", "admin_1_states_provinces", "name"))  # Alaska, Hawaii
    dump_canonicalized("canonical-natural-earth-countries.txt", l)

def collect_dxccs(cic, callsigns):
    dxccs = set()
    for callsign in callsigns:
        try:
            dxccs.add(cic.get_country_name(callsign))
        except KeyError as e:
            logger.warning(f"Failed to get country for callsign \"{callsign}\": {str(e)}")

    return dxccs

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

def dump_dxccs():
    callsigns = load_callsigns()
    cty_plist = cache_online_file("https://www.country-files.com/cty/cty.plist", "cty.plist")
    my_lookuplib = LookupLib(lookuptype="countryfile", filename=cty_plist)
    cic = Callinfo(my_lookuplib)
    dump_canonicalized("canonical-dxccs.txt", collect_dxccs(cic, callsigns))

assert unittest.main(exit=False).result
dump_natural_earth()
dump_dxccs()
subprocess.run(["diff -u canonical-dxccs.txt canonical-natural-earth-countries.txt --color=never | diffstat"], shell=True, check=True)
