"""Landschaftsschutzgebiete kommen nur aus den UBA-Daten (LSG_AT_2024), nie aus OSM.

Nutzerentscheidung 2026-10-12: der OSM-Naturfilter (`_build_osm_nature_mask`)
darf Flaechen mit "Landschaftsschutz" in protection_title oder name nicht
selektieren - auch nicht ueber protect_class 5. Andere Klasse-5-Gebiete
(z. B. Geschuetzter Landschaftsteil) bleiben drin.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from affine import Affine
from shapely.geometry import Polygon

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from calc.abschichtung_common import TARGET_CRS  # noqa: E402
from pipeline.layers import geo  # noqa: E402

CELL_M = 25.0
X0, Y0 = 500_000.0, 400_000.0


def _grid(cells: int = 40) -> dict:
    size = cells * CELL_M
    return {
        "shape": (cells, cells),
        "transform": Affine(CELL_M, 0.0, X0, 0.0, -CELL_M, Y0 + size),
        "crs": TARGET_CRS,
        "bounds": (X0, Y0, X0 + size, Y0 + size),
    }


def _poly(col: int) -> Polygon:
    x = X0 + col * 10 * CELL_M
    return Polygon([(x, Y0), (x + 5 * CELL_M, Y0), (x + 5 * CELL_M, Y0 + 5 * CELL_M), (x, Y0 + 5 * CELL_M)])


def _mask(monkeypatch, rows: list[dict]) -> np.ndarray:
    gdf = gpd.GeoDataFrame(rows, geometry=[_poly(i) for i in range(len(rows))], crs=TARGET_CRS)
    monkeypatch.setattr(geo, "_read_prep_vector", lambda path, bounds=None: gdf)
    return geo._build_osm_nature_mask(_grid())


def _covered(mask: np.ndarray, col: int) -> bool:
    c0 = col * 10
    return bool(mask[-5:, c0:c0 + 5].any())


def test_lsg_mit_protect_class_5_wird_ausgeschlossen(monkeypatch):
    mask = _mask(monkeypatch, [
        {"protect_class": "5", "protection_title": "Landschaftsschutzgebiet X", "name": ""},
        {"protect_class": "5", "protection_title": "", "name": "Landschaftsschutzgebiet Y"},
        {"protect_class": "5", "protection_title": "Geschützter Landschaftsteil", "name": "Z"},
        {"leisure": "nature_reserve", "name": "Naturschutzgebiet W"},
    ])
    assert not _covered(mask, 0)
    assert not _covered(mask, 1)
    assert not _covered(mask, 2)  # pc5 ohne Schutztext: seit Siebtem Referenzwechsel raus
    assert _covered(mask, 3)


def test_lsg_nur_ueber_titeltext_wird_nicht_mehr_gewaehlt(monkeypatch):
    mask = _mask(monkeypatch, [{"protection_title": "Landschaftsschutzgebiet", "name": "A"}])
    assert not mask.any()


def test_config_liest_lsg_layer():
    cfg = json.loads((PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))
    assert "LSG_AT_2024" in cfg["paths"]["nsg_layers"]


def test_naturpark_und_biosphaerenpark_raus(monkeypatch):
    mask = _mask(monkeypatch, [
        {"protect_class": "4", "name": "Naturpark Karwendel"},
        {"protect_class": "4", "protection_title": "Biosphärenpark Wienerwald", "name": ""},
        {"protect_class": "4", "name": "Wildruhefläche X"},
    ])
    assert not _covered(mask, 0)
    assert not _covered(mask, 1)
    assert _covered(mask, 2)


def test_protect_class_5_nur_mit_schutztext(monkeypatch):
    mask = _mask(monkeypatch, [
        {"protect_class": "5", "name": "Irgendein Gebiet"},
        {"protect_class": "5", "name": "Naturschutzgebiet A"},
        {"protect_class": "5", "protection_title": "Ruhegebiet B", "name": ""},
        {"protect_class": "5", "name": "Natura 2000 C"},
    ])
    assert not _covered(mask, 0)
    assert _covered(mask, 1)
    assert _covered(mask, 2)
    assert _covered(mask, 3)
