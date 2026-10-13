"""Weitergabe ohne Rohdaten (pipeline/prep/share.py) und Streusiedlungs-Produkt."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from affine import Affine
from shapely.geometry import Point, box

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from calc.hig_detection import CandidateScan, load_candidate_scan, write_candidate_scan  # noqa: E402
from pipeline import contract  # noqa: E402
from pipeline.prep.share import skip_without_raw  # noqa: E402


def test_raw_present_runs_normally(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text("x")
    assert skip_without_raw("admin", [raw], products=[tmp_path / "fehlt"]) is False


def test_raw_missing_products_present_skips(tmp_path, capsys):
    prod = tmp_path / "p.parquet"
    prod.write_text("x")
    assert skip_without_raw("admin", [tmp_path / "weg"], products=[prod]) is True
    out = capsys.readouterr().out
    assert "Produkt vorhanden, Rohdaten fehlen" in out


def test_raw_and_products_missing_is_clear_error(tmp_path):
    with pytest.raises(SystemExit) as e:
        skip_without_raw("admin", [tmp_path / "weg"], products=[tmp_path / "p"], hint="data/admin/")
    assert "data/admin/" in str(e.value) and "Produkt fehlt" in str(e.value)


def test_alt_products_allow_skip(tmp_path):
    alt = tmp_path / "klein.parquet"
    alt.write_text("x")
    assert skip_without_raw("kataster", [tmp_path / "weg"], products=[tmp_path / "gross"], alt_products=[alt]) is True


def test_candidate_scan_roundtrip(tmp_path):
    grid = {"bounds": (0.0, 0.0, 1000.0, 1000.0), "transform": Affine(25, 0, 0, 0, -25, 1000), "shape": (40, 40)}
    geoms = np.empty(3, dtype=object)
    geoms[:] = [box(10.123456789, 10, 20, 20.987654321), Point(500, 500).buffer(5.0), box(-5000, 0, -4990, 10)]
    scan = CandidateScan(
        geometries=geoms,
        centroids=np.array([[15.0, 15.5], [500.0, 500.0], [-4995.0, 5.0]]),
        bundesland=np.array(["Kärnten", "Tirol", "Wien"], dtype=object),
        garden_xy=np.array([[1.5, 2.5], [900.0, 900.0]]),
        garden_bundesland=np.array(["Tirol", "Kärnten"], dtype=object),
        n_buildings_total=10, n_filtered=7, n_oversized=1, n_addressless_dropped=0,
    )
    c, g, r = tmp_path / "c.parquet", tmp_path / "g.parquet", tmp_path / "r.json"
    write_candidate_scan(scan, c, g, r, {"X": 1})
    back = load_candidate_scan(c, g, r, grid, margin_m=0.0)
    assert len(back) == 2  # Wien-Zentroid liegt außerhalb
    assert back.geometries[0].equals_exact(geoms[0], 0.0)
    assert np.array_equal(back.centroids, scan.centroids[:2])
    assert back.n_filtered == 7
    only = load_candidate_scan(c, g, r, grid, bl_filter={"Kärnten"})
    assert len(only) == 1 and only.garden_xy.shape == (1, 2)
    with pytest.raises(FileNotFoundError, match="prep-kataster"):
        load_candidate_scan(tmp_path / "nein.parquet", g, r, grid)


def test_contract_has_streusiedlung_products():
    f = contract.PREP_FILES["kataster"]
    assert f["streusiedlung_kandidaten"].parent == contract.PREP["kataster"]
    assert f["streusiedlung_garten"].suffix == ".parquet"
