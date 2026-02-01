#!/usr/bin/env -S uv run
import cartopy.io.shapereader as shpreader
import sys

# resolution: 110m 50m 10m
# category: cultural physical
# name: admin_0_countries

def search_name(a):
    for field in ["NAME_LONG", "ADM0_NAME", "NAME", "name", "sr_geounit", "adm1_code", "sr_subunit", "sr_br_name"]:
        r = a.get(field)
        if r:
            return f"{field}={r}"

    return None

def dump(resolution, name, category="cultural"):
    print(f"{resolution}-{category}-{name}.txt")
    shpfilename = shpreader.natural_earth(resolution=resolution, category=category, name=name)
    reader = shpreader.Reader(shpfilename)
    with open(f"{resolution}-{category}-{name}.txt", "w") as f:
        for item in reader.records():
            s = search_name(item.attributes)
            if s:
                f.write(s + "\n")
            else:
                print("Omitting item!")

#dump("110m", "admin_0_boundary_lines_land") # no names :(
dump("110m", "admin_0_countries")
dump("110m", "admin_0_countries_lakes")
dump("110m", "admin_0_map_units")
#dump("110m", "admin_0_pacific_groupings")
dump("110m", "admin_0_scale_rank")
dump("110m", "admin_0_sovereignty")
dump("110m", "admin_0_tiny_countries")  # Madeira, Azores, Micronesia
dump("110m", "admin_1_states_provinces")  # name="Alaska", "Hawaii"
dump("110m", "admin_1_states_provinces_lakes")
dump("110m", "admin_1_states_provinces_lines")
dump("110m", "admin_1_states_provinces_scale_rank")
dump("110m", "populated_places")
dump("50m", "admin_0_countries")
dump("50m", "admin_0_tiny_countries")
dump("10m", "admin_0_countries")
#dump("10m", "admin_0_sovereignty")
#dump("10m", "admin_0_scale_rank")
#dump("10m", "admin_0_scale_rank_minor_islands")  # too detailed, has many of everything
dump("10m", "admin_0_map_units")
dump("10m", "admin_0_countries_iso")
#dump("10m", "admin_0_disputed_areas_scale_rank_minor_islands")
#dump("10m", "admin_1_states_provinces_scale_rank_minor_islands")  # 404 :(
dump("10m", "admin_2_counties_scale_rank_minor_islands")
#dump("10m", "admin_0_map_subunits")
