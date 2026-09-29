"""Tests fuer pipeline/analysis/whitepaper/zaehlen.py auf einem winzigen

synthetischen 3x3-Raster mit 9 Bundeslaendern (ein Pixel je Bundesland).
Deckt ab: die 8 Klassen (7 exklusive Ueberschneidungen + frei) summieren zu
den Zellen je Region, und ein absichtlich kaputtes all_exclusions-Band wird
erkannt und bricht den Lauf ab. Schnell, ohne echtes TIF.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from affine import Affine
from shapely.geometry import box

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.analysis.whitepaper import wp_common as wc
from pipeline.analysis.whitepaper import zaehlen

TRANSFORM = Affine(1, 0, 0, 0, -1, 3)

# Reihenfolge der 9 Boxen entspricht Zeile/Spalte im 3x3-Raster:
# Zeile 0: B, K, N   Zeile 1: O, S, ST   Zeile 2: T, V, W
STATE_NAMES_IN_GRID_ORDER = list(wc.STATE_CODES)  # Burgenland, Kaernten, ...


def _write_boundaries(tmp_path: Path) -> Path:
    geoms = [box(x, 2 - y, x + 1, 3 - y) for y in range(3) for x in range(3)]
    path = tmp_path / "bundesland_masken.gpkg"
    gpd.GeoDataFrame(
        {"BL": STATE_NAMES_IN_GRID_ORDER}, geometry=geoms, crs=wc.TARGET_CRS,
    ).to_file(path, driver="GPKG")
    return path


def _zone_band(index: int, name: str, category: str, familie: str | None = None) -> dict:
    band = {"name": name, "index": index, "category": category, "stufe": "zone"}
    if familie is not None:
        band["familie"] = familie
    return band


def _build_manifest() -> dict:
    bands = []
    # 18 Zonen-Baender: 6 Mensch, 6 Natur, 6 Geografie (Baender 1..18).
    idx = 1
    for i in range(6):
        familie = "verkehr" if i == 0 else ("luftfahrt" if i == 1 else None)
        bands.append(_zone_band(idx, f"zone_mensch_{i}", "Mensch", familie))
        idx += 1
    for i in range(6):
        familie = "schutzgebiet" if i == 0 else None
        bands.append(_zone_band(idx, f"zone_natur_{i}", "Natur", familie))
        idx += 1
    for i in range(6):
        bands.append(_zone_band(idx, f"zone_geo_{i}", "Geografie", None))
        idx += 1
    assert idx - 1 == 18

    # Kategorie-/Ergebnis-/Referenz-Baender (19..26), kein stufe="zone".
    extra_names = [
        "exclusion_human", "exclusion_nature", "exclusion_geography",
        "all_exclusions", "available_after_all_exclusions_raw",
        "available_cleaned_min_10ha", "official_wind_zoning",
        "wka_bestand_ausserhalb_zonen",
    ]
    for name in extra_names:
        bands.append({"name": name, "index": idx, "category": "sonstige", "stufe": "ergebnis"})
        idx += 1
    assert idx - 1 == 26

    return {
        "schema_version": "test",
        "band_schema": "test",
        "generated_at": "2020-01-01T00:00:00Z",
        "raster": {"pixel_size_m": 1},
        "bands": bands,
    }


def _write_tif(tmp_path: Path, manifest: dict, *, broken_all: bool = False) -> Path:
    zeros = np.zeros((3, 3), dtype="uint8")

    H = zeros.copy()
    H[0, 0] = 1  # Burgenland
    N = zeros.copy()
    N[0, 1] = 1  # Kaernten
    G = zeros.copy()
    G[0, 2] = 1  # Niederoesterreich

    ALL = (H | N | G).astype("uint8")
    if broken_all:
        # Absichtlich kaputt: all_exclusions stimmt nicht mit H|N|G ueberein.
        ALL = zeros.copy()

    RAW = (1 - (H | N | G)).astype("uint8")  # frei = NICHT (H ODER N ODER G)
    CLEAN = RAW.copy()
    CLEAN[1, 0] = 0  # Oberoesterreich wird zu Kleinflaeche (< 10 ha)

    OFFICIAL = zeros.copy()
    OFFICIAL[1, 1] = 1
    WKA_OUT = zeros.copy()
    WKA_OUT[2, 2] = 1

    arrays_by_name = {
        "exclusion_human": H,
        "exclusion_nature": N,
        "exclusion_geography": G,
        "all_exclusions": ALL,
        "available_after_all_exclusions_raw": RAW,
        "available_cleaned_min_10ha": CLEAN,
        "official_wind_zoning": OFFICIAL,
        "wka_bestand_ausserhalb_zonen": WKA_OUT,
    }

    tif_path = tmp_path / "test.tif"
    n_bands = len(manifest["bands"])
    with rasterio.open(
        tif_path, "w", driver="GTiff", height=3, width=3, count=n_bands,
        dtype="uint8", crs=wc.TARGET_CRS, transform=TRANSFORM, nodata=0,
    ) as ds:
        for band in manifest["bands"]:
            arr = arrays_by_name.get(band["name"], zeros)
            ds.write(arr, band["index"])
    return tif_path


def _write_manifest(tmp_path: Path, manifest: dict) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _build_inputs(tmp_path: Path, *, broken_all: bool = False):
    manifest = _build_manifest()
    tif_path = _write_tif(tmp_path, manifest, broken_all=broken_all)
    manifest_path = _write_manifest(tmp_path, manifest)
    grenzen_path = _write_boundaries(tmp_path)
    return tif_path, manifest_path, grenzen_path


def test_eight_classes_sum_to_region_cells_and_checks_pass(tmp_path):
    tif_path, manifest_path, grenzen_path = _build_inputs(tmp_path)
    cache_dir = zaehlen.run(tif_path, manifest_path, grenzen_path, expected_sha256=None, cache_root=tmp_path)

    checks = json.loads((cache_dir / "checks.json").read_text(encoding="utf-8"))
    assert checks["sum7_plus_frei_equals_region_cells"] is True
    assert checks["hng_union_equals_all_exclusions_mismatches"] == 0
    assert checks["frei_equals_raw_mismatches"] == 0
    assert checks["cleaned_subset_of_raw_violations"] == 0
    assert checks["regions_sum_to_AT_all_items"] is True

    counts = json.loads((cache_dir / "counts.json").read_text(encoding="utf-8"))
    region_cells = counts["region_cells"]
    counters = counts["counters"]
    # Unabhaengige Gegenprobe (nicht nur die im Code hinterlegte Selbstpruefung):
    # 7 exklusive Klassen + frei muessen je Region exakt die Zellenzahl ergeben.
    for code in wc.REGION_ORDER:
        total = sum(counters[k][code] for k in zaehlen.CLASS_KEYS) + counters["frei"][code]
        assert total == region_cells[code] == 1

    # Konkrete Zuordnung entsprechend der konstruierten Eingabe:
    assert counters["nur_mensch"]["B"] == 1
    assert counters["nur_natur"]["K"] == 1
    assert counters["nur_geografie"]["N"] == 1
    for code in ("O", "S", "ST", "T", "V", "W"):
        assert counters["frei"][code] == 1
    assert counters["kleinflaechen"]["O"] == 1
    assert counters["available_cleaned_min_10ha"]["O"] == 0

    # J5: all_exclusions und available_after_all_exclusions_raw sind hier per
    # Konstruktion komplementaer ueber das ganze 3x3-Raster -> Vereinigung
    # deckt alle 9 Zellen ab, Schnittmenge ist leer.
    assert counts["full_grid_union_cells"] == 9
    assert checks["full_grid_union_intersection_cells"] == 0


def test_broken_all_exclusions_band_is_detected_and_aborts(tmp_path):
    tif_path, manifest_path, grenzen_path = _build_inputs(tmp_path, broken_all=True)
    with pytest.raises(zaehlen.SelfCheckError, match="all_exclusions"):
        zaehlen.run(tif_path, manifest_path, grenzen_path, expected_sha256=None, cache_root=tmp_path)


# ---------------------------------------------------------------------------
# J5: volle Staatsgebietsmaske (Vereinigung all_exclusions ∪
# available_after_all_exclusions_raw), Selbstpruefung auf leere Schnittmenge.
# ---------------------------------------------------------------------------

def test_full_grid_union_counts_on_tiny_raster():
    all_mask = np.array([[True, False], [False, True]])
    raw_mask = np.array([[False, True], [True, False]])
    union, intersection = zaehlen.full_grid_union_counts(all_mask, raw_mask)
    assert union == 4
    assert intersection == 0


def test_full_grid_union_counts_detects_overlap():
    all_mask = np.array([[True, True]])
    raw_mask = np.array([[True, False]])
    union, intersection = zaehlen.full_grid_union_counts(all_mask, raw_mask)
    assert union == 2
    assert intersection == 1


def _write_boundaries_with_outside_row(tmp_path: Path) -> Path:
    """Wie ``_write_boundaries``, aber auf einem 4x3-Raster: Zeilen 0..2

    tragen die 9 Bundeslaender (wie im 3x3-Fall, nur um eine Zeile nach oben
    verschoben), Zeile 3 gehoert zu keinem Bundesland (region_code 0). So
    laesst sich ein Ueberlappungsfehler ausserhalb der Bundesland-Maske
    erzeugen, ohne die anderen (auf ``inside`` beschraenkten) Selbstpruefungen
    auszuloesen.
    """
    geoms = [box(x, 3 - y, x + 1, 4 - y) for y in range(3) for x in range(3)]
    path = tmp_path / "bundesland_masken_4row.gpkg"
    gpd.GeoDataFrame(
        {"BL": STATE_NAMES_IN_GRID_ORDER}, geometry=geoms, crs=wc.TARGET_CRS,
    ).to_file(path, driver="GPKG")
    return path


def _write_tif_with_outside_overlap(tmp_path: Path, manifest: dict) -> Path:
    """4x3-Raster: Zeilen 0..2 wie ``_write_tif`` (konsistent), Zeile 3 liegt

    ausserhalb aller Bundeslaender; dort werden all_exclusions UND
    available_after_all_exclusions_raw beide auf 1 gesetzt (Dateninkonsistenz,
    die nur die volle Staatsgebietsmaske - nicht die Bundesland-gebundenen
    Pruefungen - erkennen kann).
    """
    zeros = np.zeros((4, 3), dtype="uint8")

    H = zeros.copy()
    H[0, 0] = 1
    N = zeros.copy()
    N[0, 1] = 1
    G = zeros.copy()
    G[0, 2] = 1

    ALL = (H | N | G).astype("uint8")
    RAW = (1 - (H | N | G)).astype("uint8")
    CLEAN = RAW.copy()

    # Zeile 3 (ausserhalb aller Bundeslaender): Ueberlappung erzwingen.
    ALL[3, 0] = 1
    RAW[3, 0] = 1

    OFFICIAL = zeros.copy()
    WKA_OUT = zeros.copy()

    arrays_by_name = {
        "exclusion_human": H,
        "exclusion_nature": N,
        "exclusion_geography": G,
        "all_exclusions": ALL,
        "available_after_all_exclusions_raw": RAW,
        "available_cleaned_min_10ha": CLEAN,
        "official_wind_zoning": OFFICIAL,
        "wka_bestand_ausserhalb_zonen": WKA_OUT,
    }

    tif_path = tmp_path / "test_overlap.tif"
    n_bands = len(manifest["bands"])
    with rasterio.open(
        tif_path, "w", driver="GTiff", height=4, width=3, count=n_bands,
        dtype="uint8", crs=wc.TARGET_CRS, transform=Affine(1, 0, 0, 0, -1, 4), nodata=0,
    ) as ds:
        for band in manifest["bands"]:
            arr = arrays_by_name.get(band["name"], zeros)
            ds.write(arr, band["index"])
    return tif_path


def test_full_grid_overlap_outside_bundesland_mask_is_detected_and_aborts(tmp_path):
    manifest = _build_manifest()
    tif_path = _write_tif_with_outside_overlap(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    grenzen_path = _write_boundaries_with_outside_row(tmp_path)
    with pytest.raises(zaehlen.SelfCheckError, match="ueberschneiden sich"):
        zaehlen.run(tif_path, manifest_path, grenzen_path, expected_sha256=None, cache_root=tmp_path)


def test_missing_band_name_for_full_grid_raises_clear_error(tmp_path):
    manifest = _build_manifest()
    manifest["bands"] = [
        b for b in manifest["bands"] if b["name"] != "available_after_all_exclusions_raw"
    ]
    manifest_path = _write_manifest(tmp_path, manifest)
    tif_path = tmp_path / "dummy.tif"
    tif_path.write_bytes(b"dummy-bytes-fuer-sha256")
    grenzen_path = _write_boundaries(tmp_path)
    with pytest.raises(KeyError, match="available_after_all_exclusions_raw.*nicht im Manifest"):
        zaehlen.run(tif_path, manifest_path, grenzen_path, expected_sha256=None, cache_root=tmp_path)
