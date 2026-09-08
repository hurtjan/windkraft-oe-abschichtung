"""W5.P2 (08.09.2026, Punkt 34): adresslose DKM-Grossflaechen entfallen.

Regel, wortgleich aus dem Auftrag:

* Ueber HIG_MAX_FOOTPRINT_M2 UND keine BEV-Adresse im eigenen Polygon
  -> Kandidat entfaellt vollstaendig (keine Scheibe, keine Huellen-
  Mitgliedschaft).
* Ueber der Schwelle MIT mindestens einer eigenen Adresse -> unveraendert:
  5-m-Scheibe um den Zentroid.
* Unter der Schwelle -> in jeder Hinsicht unveraendert, unabhaengig von
  Adressen.

Getestet direkt gegen scan_dkm_candidates() (calc/hig_detection.py)
- derselbe DKM-Scan, den pipeline/layers/hig.py::build_sources() aufruft,
  seit W5.P2 mit dem neuen address_xy-Parameter.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from affine import Affine
from shapely.geometry import Polygon

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from calc.abschichtung_common import TARGET_CRS  # noqa: E402
from calc.hig_detection import scan_dkm_candidates  # noqa: E402

CELL_M = 25.0
MAX_FOOTPRINT_M2 = 10_000.0  # HIG_MAX_FOOTPRINT_M2, unveraendert (Regel 4)


def _grid(cells: int = 60) -> dict:
    size = cells * CELL_M
    return {
        "shape": (cells, cells),
        "transform": Affine(CELL_M, 0.0, 500_000.0, 0.0, -CELL_M, 400_000.0 + size),
        "crs": TARGET_CRS,
        "bounds": (500_000.0, 400_000.0, 500_000.0 + size, 400_000.0 + size),
    }


def _square(cx: float, cy: float, side: float) -> Polygon:
    h = side / 2.0
    return Polygon([(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)])


def _write_dkm_parquet(path: Path, polygons: dict[str, Polygon]) -> None:
    """Minimal DKM-GeoParquet: source_layer/ns/ns_category/bundesland/geometry."""
    names = list(polygons)
    frame = pd.DataFrame({
        "bundesland": ["Niederoesterreich"] * len(names),
        "ns": ["41"] * len(names),
        "ns_category": ["Baufläche"] * len(names),
        "source_layer": ["NFL_V2"] * len(names),
        "geometry": [shapely.to_wkb(polygons[n]) for n in names],
    })
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, path)


def _scan(tmp_path: Path, polygons: dict[str, Polygon], address_xy: np.ndarray | None):
    parquet_path = tmp_path / "dkm.parquet"
    _write_dkm_parquet(parquet_path, polygons)
    grid = _grid()
    filter_mask = np.zeros(grid["shape"], dtype=bool)  # nichts amtlich erfasst -> alles Kandidat
    return scan_dkm_candidates(
        parquet_path, grid, filter_mask, MAX_FOOTPRINT_M2, address_xy=address_xy,
    )


def test_oversized_without_own_address_is_dropped_entirely(tmp_path):
    # Arrange - 120x120 m = 14 400 m^2 > 10 000 m^2, keine BEV-Adresse in der Naehe
    oversized_addressless = _square(500_160, 400_160, 120.0)
    address_xy = np.zeros((0, 2))  # kein BEV-Adressbestand ueberhaupt

    # Act
    scan = _scan(tmp_path, {"oversized_addressless": oversized_addressless}, address_xy)

    # Assert - kein Kandidat mehr, weder als Scheibe noch sonst
    assert len(scan) == 0
    assert scan.n_oversized == 1
    assert scan.n_addressless_dropped == 1


def test_oversized_with_own_address_keeps_5m_disc_around_centroid(tmp_path):
    # Arrange - dieselbe Grossflaeche, diesmal mit einer BEV-Adresse im eigenen Polygon
    oversized_addressed = _square(500_160, 400_160, 120.0)
    address_xy = np.array([[500_160.0, 400_160.0]])  # im Zentrum des Polygons

    # Act
    scan = _scan(tmp_path, {"oversized_addressed": oversized_addressed}, address_xy)

    # Assert - Kandidat bleibt erhalten, heutiges Verhalten unveraendert: 5-m-Scheibe um Zentroid
    assert len(scan) == 1
    assert scan.n_oversized == 1
    assert scan.n_addressless_dropped == 0
    result_geom = scan.geometries[0]
    centroid = shapely.centroid(result_geom)
    assert abs(centroid.x - 500_160.0) < 1e-6
    assert abs(centroid.y - 400_160.0) < 1e-6
    # 5-m-Scheibe -> Flaeche ~ pi * 5^2, klar kleiner als die urspruengliche Riesenflaeche
    assert shapely.area(result_geom) < 100.0
    assert shapely.area(result_geom) > 50.0


def test_under_threshold_candidate_is_unchanged_regardless_of_address(tmp_path):
    # Arrange - 50x50 m = 2 500 m^2 < 10 000 m^2, keine BEV-Adresse in der Naehe
    small = _square(500_725, 400_725, 50.0)
    address_xy = np.zeros((0, 2))

    # Act
    scan = _scan(tmp_path, {"small": small}, address_xy)

    # Assert - unter der Schwelle: unveraendert, weder Scheibe noch Wegfall
    assert len(scan) == 1
    assert scan.n_oversized == 0
    assert scan.n_addressless_dropped == 0
    assert shapely.equals(scan.geometries[0], small)


def test_mixed_batch_drops_only_the_addressless_oversized_one(tmp_path):
    # Arrange - alle drei Faelle zusammen in einem Scan, wie es der echte DKM-Scan liefert
    oversized_addressless = _square(500_160, 400_160, 120.0)
    oversized_addressed = _square(500_460, 400_460, 120.0)
    small = _square(500_725, 400_725, 50.0)
    address_xy = np.array([[500_460.0, 400_460.0]])  # nur im zweiten Polygon

    # Act
    scan = _scan(
        tmp_path,
        {
            "oversized_addressless": oversized_addressless,
            "oversized_addressed": oversized_addressed,
            "small": small,
        },
        address_xy,
    )

    # Assert
    assert scan.n_oversized == 2
    assert scan.n_addressless_dropped == 1
    assert len(scan) == 2  # oversized_addressless ist weg, die anderen beiden bleiben
    areas = sorted(float(shapely.area(g)) for g in scan.geometries)
    assert areas[0] < 100.0  # die 5-m-Scheibe des adressierten Riesen-Footprints
    assert abs(areas[1] - 2_500.0) < 1e-6  # die unveraenderte kleine Flaeche
