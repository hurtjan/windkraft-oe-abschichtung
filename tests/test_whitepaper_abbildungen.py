"""Tests fuer pipeline/analysis/whitepaper/abbildungen.py: Palettenvarianten,

Streifengeometrie und Smoke-Test der Balken- und Methodenuebersichtsabbildung
mit synthetischen Daten (ohne TIF).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import geopandas as gpd
from shapely.geometry import box

from pipeline.analysis.whitepaper import abbildungen as ab
from pipeline.analysis.whitepaper import wp_common as wc

KEYS = set(ab.PALETTE_VARIANTS["aktuell"])


@pytest.fixture(autouse=True)
def _restore_palette():
    yield
    ab.set_palette(ab.DEFAULT_PALETTE)


def test_all_variants_complete_and_valid_hex():
    for name, pal in ab.PALETTE_VARIANTS.items():
        assert set(pal) == KEYS, name
        for h in pal.values():
            assert len(h) == 7 and h.startswith("#"), (name, h)
            int(h[1:], 16)


def test_set_palette_switches_in_place_and_rejects_unknown():
    ref = ab.PALETTE
    ab.set_palette("A")
    assert ab.PALETTE is ref and ab.PALETTE["mensch"] == ab.PALETTE_VARIANTS["A"]["mensch"]
    with pytest.raises(KeyError):
        ab.set_palette("gibt-es-nicht")


def test_stripe_polys_cover_rect_and_alternate_colors():
    polys = ab._stripe_polys(w=1.0, h=0.5, ncol=3, width=0.1)
    assert len(polys) == 3 and all(polys)
    # Streifen k hat Farbe k % ncol; Streifen 0 beginnt bei u = 0 (linke untere Ecke)
    assert any(abs(p[0][0]) < 1e-9 and p[0][1] == 0.0 for p in polys[0])
    for plist in polys:
        for p in plist:
            assert abs((p[3][0] - p[0][0]) - 0.5) < 1e-9  # 45 Grad: dx == dy == h


def _synthetic_counts():
    keys = ["nur_mensch", "mensch_geografie", "nur_geografie", "natur_geografie", "nur_natur",
            "mensch_natur", "alle_drei", "kleinflaechen", "available_cleaned_min_10ha"]
    n = len(keys)
    cells = 1000
    per = cells // n
    counters = {k: {c: per for c in wc.REGION_ORDER} for k in keys}
    return {
        "at_cells": per * n * 9,
        "at_counts": {k: per * 9 for k in keys},
        "region_cells": {c: per * n for c in wc.REGION_ORDER},
        "counters": counters,
    }


@pytest.mark.parametrize("variant", ["A", "C"])
def test_fig_bars_writes_png_and_svg(tmp_path, variant):
    ab.set_palette(variant)
    ab.fig_bars(_synthetic_counts(), {"figure_source_line": "Test"}, tmp_path)
    png, svg = tmp_path / "abb2_balken.png", tmp_path / "abb2_balken.svg"
    assert png.stat().st_size > 5000 and svg.stat().st_size > 5000
    assert "clipPath" in svg.read_text(encoding="utf-8")  # Streifen sind geclippt


def test_fig_methoden_uebersicht_writes_png(tmp_path):
    rng = np.random.default_rng(0)
    shape = (40, 60)
    H = rng.random(shape) > 0.5
    N = rng.random(shape) > 0.8
    G = rng.random(shape) > 0.6
    class_ds = rng.integers(0, 10, size=shape).astype(np.uint8)
    npz = {"H_ds": H, "N_ds": N, "G_ds": G, "class_ds": class_ds,
           "bounds": np.array([0.0, 0.0, 60.0, 40.0])}
    borders = gpd.GeoDataFrame({"code": ["X"], "name": ["X"]}, geometry=[box(0, 0, 60, 40)])
    ab.fig_methoden_uebersicht(npz, {"figure_source_line": "Test"}, borders, tmp_path)
    assert (tmp_path / "abb_methoden_uebersicht.png").stat().st_size > 5000
