"""Analyse-Raster (zweites Produkt): ns->Band, Profilgleichheit, Manifest."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine
from shapely.geometry import box

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import analyse_raster as ar  # noqa: E402


def test_ns_mapping():
    expect = {"56": 0, "55": 0, "58": 1, "48": 2, "54": 3, "40": 4, "53": 4, "57": 4, "52": 5, "41": 6, "83": 6}
    for code, band in expect.items():
        assert ar.NS_TO_BANDS[code] == [band]
    assert ar.band_indices(["99", "56"]) == [[], [0]]
    assert [b[0] for b in ar.BANDS][0] == "kataster_wald" and len(ar.BANDS) == 7


def test_burn_zellmittelpunkt_und_klassen():
    tr = Affine(25, 0, 0, 0, -25, 250)  # 10x10
    stack = np.zeros((7, 10, 10), np.uint8)
    # Box deckt Zellmittelpunkte von Spalte 1..2, Zeilen 7..8 (y 25..75)
    geoms = [box(26, 26, 74, 74), box(100, 100, 124, 124)]
    ar.burn_geometries(stack, geoms, ["56", "52"], tr)
    assert stack[0].sum() == 4 and stack[0, 7:9, 1:3].all()
    assert stack[5].sum() == 0 or stack[5].sum() == 1  # 24 m Box: hoechstens eine Zelle
    assert stack[1:5].sum() == 0 and stack[6].sum() == 0


def test_manifest_struktur():
    prof = {"width": 10, "height": 10, "transform": Affine(25, 0, 0, 0, -25, 250)}
    m = ar.build_manifest(prof, (0, 0, 250, 250), Path("abschichtung.tif"), "abc")
    assert m["band_count"] == 7 and len(m["bands"]) == 7
    assert [b["index"] for b in m["bands"]] == list(range(1, 8))
    for b in m["bands"]:
        assert {"name", "label_de", "description_de"} <= set(b)
        assert "Digitale Katastralmappe BEV" in b["description_de"]
    assert m["referenz"]["sha256"] == "abc" and m["raster"]["crs"] == "EPSG:31287"
    json.dumps(m)


def test_profil_gleich_hauptraster():
    if not (ar.MAIN_TIF.exists() and ar.OUT_TIF.exists()):
        pytest.skip("out/ fehlt")
    with rasterio.open(ar.MAIN_TIF) as a, rasterio.open(ar.OUT_TIF) as b:
        pa_, pb = a.profile, b.profile
        for k in ("crs", "transform", "width", "height", "blockxsize", "blockysize", "tiled", "compress", "dtype", "interleave"):
            assert pa_[k] == pb[k], k
        assert b.count == 7
