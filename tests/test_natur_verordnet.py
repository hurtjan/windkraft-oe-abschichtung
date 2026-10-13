"""Natur-Ausschluss nur fuer per Verordnung festgelegte Kategorien.

Prueft den KAT_SUB-Filter der Prep-Stufe (S_AT_2024), die Config und dass
exclusion_nature (Band 28) nur aus dem amtlichen Band 21 komponiert wird.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from calc import abschichtung_common as common  # noqa: E402
from calc import band_manifest  # noqa: E402
from pipeline.prep import natur  # noqa: E402

CFG = json.loads((PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))["paths"]


def test_config_layer_und_filter():
    assert "GLT_AT_2024" in CFG["nsg_layers"]
    assert "S_AT_2024" in CFG["nsg_layers"]
    assert "NDKM_AT_2024" in CFG["nsg_layers"]
    assert CFG["nsg_layer_filter"]["S_AT_2024"]["KAT_SUB"] == ["RG", "RZ", "PSG", "SSG", "SAFM", "SG §26", "GB", "GLR", "GNÖB", "ÖE", "ÖSG"]


def test_kat_sub_filter_laesst_nur_gueltige_codes_durch():
    codes = ["RG", "RZ", "PSG", "SSG", "SAFM", "SG §26", "GB", "ÖSG", "GNÖB", "ÖE", "GLR", "SGNOG", "SZSFFG"]
    gdf = gpd.GeoDataFrame({"KAT_SUB": codes}, geometry=[Point(i, 0) for i in range(len(codes))])
    out = natur.apply_layer_filter(gdf, CFG["nsg_layer_filter"]["S_AT_2024"])
    assert list(out["KAT_SUB"]) == codes[:-2]


def test_layer_ohne_filter_unveraendert():
    gdf = gpd.GeoDataFrame({"KAT_SUB": ["GB"]}, geometry=[Point(0, 0)])
    assert len(natur.apply_layer_filter(gdf, None)) == 1
    assert len(natur.apply_layer_filter(gdf, {})) == 1


def test_exclusion_nature_nur_amtlich():
    assert common.NATURE_EXCLUSION_BANDS == ["nature_protection_areas"]
    assert band_manifest._NATURE_EXCLUSION_BANDS == ["nature_protection_areas"]


def test_compose_nature_nur_amtliche_maske(tmp_path, monkeypatch):
    official = np.zeros((4, 4), bool); official[0, 0] = True
    osm = np.zeros((4, 4), bool); osm[3, 3] = True
    masks = {"nature_protection_areas": official, "osm_nature_protection_areas": osm}
    nature = np.zeros((4, 4), bool)
    for name, arr in masks.items():  # gleiche Regel wie compose_exclusion_geotiff
        if name in common.NATURE_EXCLUSION_BANDS:
            nature |= arr
    assert nature[0, 0] and not nature[3, 3]
