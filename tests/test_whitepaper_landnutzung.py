"""Tests fuer L1_landnutzung auf dem 3x3-Fixture (ein Pixel = 1 km2 je Land)."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_whitepaper_zaehlen import (TRANSFORM, _build_manifest, _write_boundaries,  # noqa: E402
                                      _write_manifest, _write_tif)

from pipeline.analysis.whitepaper import landnutzung, wp_common as wc  # noqa: E402


def _setup(tmp_path: Path, *, stale: bool = False, missing: bool = False):
    manifest = _build_manifest()
    manifest["raster"]["pixel_size_m"] = 1000  # 1 km2 je Zelle
    tif = _write_tif(tmp_path, manifest)
    mpath = _write_manifest(tmp_path, manifest)
    grenzen = _write_boundaries(tmp_path)
    sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    names = ["kataster_wald", "kataster_aecker_wiesen_weiden"]
    wald = np.zeros((3, 3), "uint8"); wald[1, 1] = 1; wald[2, 0] = 1   # S, T
    c48 = np.zeros((3, 3), "uint8"); c48[2, 2] = 1; c48[2, 1] = 1     # W, V
    atif = tmp_path / "analyse.tif"
    amani = tmp_path / "analyse.bands.json"
    if not missing:
        with rasterio.open(atif, "w", driver="GTiff", height=3, width=3, count=2, dtype="uint8",
                           crs=wc.TARGET_CRS, transform=TRANSFORM) as ds:
            ds.write(wald, 1); ds.write(c48, 2)
        amani.write_text(json.dumps({
            "referenz": {"sha256": "0" * 64 if stale else sha},
            "bands": [{"index": i + 1, "name": n} for i, n in enumerate(names)],
        }), encoding="utf-8")
    return tif, mpath, grenzen, atif, amani


def test_l1_numbers_and_shape(tmp_path):
    tif, mpath, grenzen, atif, amani = _setup(tmp_path)
    out = landnutzung.run(tif, mpath, grenzen, tmp_path / "wp", atif, amani)
    rows = list(csv.reader([l for l in (out / "L1_landnutzung.csv").read_text(encoding="utf-8").splitlines()
                            if not l.startswith("#")]))
    hdr, data = rows[0], rows[1:]
    assert data[0][1] == "Österreich" and len(data) == 10
    d = {r[0]: dict(zip(hdr, r)) for r in data}
    at = d["AT"]
    assert float(at["land_km2"]) == 9
    assert float(at["land_wald_km2"]) == 2 and float(at["land_c48_km2"]) == 2
    # Bestand = S (Wald) + W (C48); Potential = ST, T (Wald), V (C48); O ist Kleinflaeche
    assert float(at["bestand_km2"]) == 2 and float(at["bestand_wald_km2"]) == 1
    assert float(at["bestand_c48_km2"]) == 1
    assert float(at["pot_km2"]) == 3 and float(at["pot_wald_km2"]) == 1 and float(at["pot_c48_km2"]) == 1
    assert float(d["S"]["bestand_km2"]) == 1 and float(d["T"]["pot_wald_km2"]) == 1
    assert float(at["bestand_pct"]) == pytest.approx(2 / 9 * 100)
    assert float(at["bestand_wald_pct"]) == pytest.approx(50)
    md = (out / "L1_landnutzung.md").read_text(encoding="utf-8")
    assert "| Land | Landesfläche | Wald | C48 | Bestand | Wald | C48 | Potentialfläche | Wald | C48 |" in md
    assert "| Österreich | 9,0 (100,0 %) | 2,0 (22,2 %)" in md or "9,0 (100,0 %)" in md
    assert "(50 %)" in md and "Kataster-Nutzungscodes 56 und 55" in md and "Code 48" in md
    # Land mit Bestand 0 -> Basis < 0,5 km2 -> "–"
    assert "0,0 (0,0 %) | 0,0 (–)" in md
    # Reihenfolge: gleiche Landesflaeche -> stabil, AT zuerst
    assert md.index("Österreich") < md.index("Burgenland")


def test_l1_herkunft_has_both_hashes_and_is_idempotent(tmp_path):
    tif, mpath, grenzen, atif, amani = _setup(tmp_path)
    out = landnutzung.run(tif, mpath, grenzen, tmp_path / "wp", atif, amani)
    landnutzung.run(tif, mpath, grenzen, tmp_path / "wp", atif, amani)
    h = (out / "HERKUNFT.md").read_text(encoding="utf-8")
    assert h.count(landnutzung.HERKUNFT_MARKER) == 1
    assert hashlib.sha256(tif.read_bytes()).hexdigest() in h
    assert hashlib.sha256(atif.read_bytes()).hexdigest() in h


def test_l1_fails_on_stale_or_missing_analysis_raster(tmp_path):
    tif, mpath, grenzen, atif, amani = _setup(tmp_path, stale=True)
    with pytest.raises(landnutzung.AnalyseRasterError, match="veraltet"):
        landnutzung.run(tif, mpath, grenzen, tmp_path / "wp", atif, amani)
    t2 = tmp_path / "x"; t2.mkdir()
    tif, mpath, grenzen, atif, amani = _setup(t2, missing=True)
    with pytest.raises(landnutzung.AnalyseRasterError, match="fehlt"):
        landnutzung.run(tif, mpath, grenzen, t2 / "wp", atif, amani)
