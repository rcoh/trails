import math

# import rasterio

from trails.settings import SRTMV4_BASE_DIR

BASE = SRTMV4_BASE_DIR


def srtm1_tile_ilonlat(lon, lat):
    return int(math.floor(lon)), int(math.floor(lat))


def srtm3_tile_ilonlat(lon, lat):
    ilon, ilat = srtm1_tile_ilonlat(lon, lat)
    return (ilon + 180) // 5 + 1, (64 - ilat) // 5


def get_elevation(lat, lon):
    index_lon, index_lat = srtm3_tile_ilonlat(lon, lat)
    tile_file = f"srtm_{index_lon:02d}_{index_lat:02d}.tif"
    coords = ((lon, lat), (lon, lat))
    elev = next(rasterio.open(tile_file).sample(coords))[0]
    if elev == -32768:
        raise Exception("Elevation undefined at point")
    return elev
