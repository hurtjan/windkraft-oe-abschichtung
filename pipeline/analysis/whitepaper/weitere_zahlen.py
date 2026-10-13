"""Weitere Einzelzahlen des Papers, die direkt aus dem TIF kommen.

* Seilbahnstationen-Zone (Band 11) im 150-m-Streifen der Personenseilbahnen
  (Band 17): Anteil der Zellen von Band 11, die auch in Band 17 liegen.
* OSM-Schutzgebiete (``osm_nature_protection_areas``) ausserhalb der amtlichen
  Schutzgebiete (``nature_protection_areas``), nur im Staatsgebiet
  (Bundeslandmaske per Zellmittelpunkt, wie ``zaehlen.py``).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from . import wp_common as wc
from . import zahlen as Z


def anteil_in(a: np.ndarray, b: np.ndarray) -> tuple[int, int]:
    """(Zellen von a, davon auch in b)."""
    return int(a.sum()), int((a & b).sum())


BLOCK_ROWS = 1000


def osm_ausserhalb_amtlich(tif_path: Path, manifest: dict, grenzen_path: Path) -> tuple[int, float]:
    """(Zellen, km2) mit OSM-Schutzgebiet, aber ohne amtliches Band, im Staatsgebiet."""
    i_off = wc.band_index(manifest, "nature_protection_areas")
    i_osm = wc.band_index(manifest, "osm_nature_protection_areas")
    regions = wc.load_bundeslaender(grenzen_path)
    n = 0
    with rasterio.open(tif_path) as ds:
        for _off, block_h, window in wc.iter_windows(ds.height, ds.width, BLOCK_ROWS):
            wt = wc.block_transform(ds.transform, window)
            region_raster, _codes = wc.make_region_raster(regions, (block_h, ds.width), wt)
            m = ds.read(indexes=[i_off, i_osm], window=window) == 1
            n += int(((region_raster != 0) & m[1] & ~m[0]).sum())
    pix = float(manifest["raster"]["pixel_size_m"]) ** 2
    return n, n * pix / 1e6


def run(tif_path: Path, manifest_path: Path, grenzen_path: Path | None = None) -> None:
    manifest = wc.load_manifest(manifest_path)
    if grenzen_path is not None:
        _n, km2 = osm_ausserhalb_amtlich(tif_path, manifest, grenzen_path)
        Z.register("natur_osm_ausserhalb_amtlich_km2", km2, "km²",
                   "Zellen mit Band osm_nature_protection_areas ohne Band nature_protection_areas "
                   "im Staatsgebiet (Bundeslandmaske, Zellmittelpunkt)")
        print(f"[weitere_zahlen] OSM-Schutzgebiete ausserhalb amtlicher: {km2:.1f} km2")
    with rasterio.open(tif_path) as ds:
        a = ds.read(wc.band_index(manifest, "cableway_buildings_buffer")).astype(bool)
        b = ds.read(wc.band_index(manifest, "cableway_people_150m")).astype(bool)
    n, k = anteil_in(a, b)
    pct = k / n * 100.0 if n else float("nan")
    Z.register("seilbahn_station_in_150m_pct", pct, "%",
               "Anteil Band cableway_buildings_buffer innerhalb cableway_people_150m (Zellzahl, ganzes Raster)")
    print(f"[weitere_zahlen] Seilbahnstationen-Zone in 150-m-Streifen: {pct:.2f} %")
