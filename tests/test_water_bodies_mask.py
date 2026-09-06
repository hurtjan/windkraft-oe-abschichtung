"""Größere Wasserkörper (Seen, Stauseen, Flussläufe) sind kein WKA-Standort.

`water_bodies_mask` rasterisiert OSM-Wasserpolygone und behält nur
zusammenhängende Wasserflächen ab `WATER_MIN_AREA_HA`. Die Schwelle wirkt auf
verbundene Rasterkomponenten, nicht pro Feature - OSM stückelt Flussufer in
viele kleine Teilpolygone, die erst verkettet "größer" sind.
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from affine import Affine
from shapely.geometry import LineString, Polygon

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windkraft.calc.abschichtung_common import TARGET_CRS, water_bodies_mask  # noqa: E402

CELL_M = 25.0
ORIGIN_X, ORIGIN_Y = 500_000.0, 400_000.0


def _grid(cells: int = 80) -> dict:
    """Minimal grid dict in the load_grid() shape: 80x80 cells at 25 m."""
    size = cells * CELL_M
    return {
        "shape": (cells, cells),
        "transform": Affine(CELL_M, 0.0, ORIGIN_X, 0.0, -CELL_M, ORIGIN_Y + size),
        "crs": TARGET_CRS,
        "bounds": (ORIGIN_X, ORIGIN_Y, ORIGIN_X + size, ORIGIN_Y + size),
    }


def _rect(x: float, y: float, w: float, h: float) -> Polygon:
    return Polygon([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])


def _water(*geoms) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"natural": ["water"] * len(geoms)}, geometry=list(geoms), crs=TARGET_CRS)


def test_keeps_lake_at_or_above_threshold():
    # Arrange - 200x200 m See = 4 ha, deutlich über 1 ha
    lake = _rect(ORIGIN_X + 500, ORIGIN_Y + 500, 200, 200)

    # Act
    mask = water_bodies_mask(_water(lake), _grid(), min_area_ha=1.0)

    # Assert
    assert mask.any()


def test_drops_pond_below_threshold():
    # Arrange - 50x50 m Teich = 0,25 ha
    pond = _rect(ORIGIN_X + 500, ORIGIN_Y + 500, 50, 50)

    # Act
    mask = water_bodies_mask(_water(pond), _grid(), min_area_ha=1.0)

    # Assert
    assert not mask.any()


def test_chained_riverbank_segments_count_as_one_water_body():
    # Arrange - drei aneinandergrenzende 30-m-breite Ufersegmente, je < 1 ha,
    # zusammen ein 1.200 m langer Flusslauf (3,6 ha verbunden)
    segments = [_rect(ORIGIN_X + 200 + i * 400, ORIGIN_Y + 900, 400, 30) for i in range(3)]

    # Act
    mask = water_bodies_mask(_water(*segments), _grid(), min_area_ha=1.0)

    # Assert - als verkettete Komponente über der Schwelle
    assert mask.any()


def test_ignores_waterway_centerlines():
    # Arrange - ein Bach als LineString (osmium exportiert offene Ways als Linien)
    brook = LineString([(ORIGIN_X, ORIGIN_Y + 100), (ORIGIN_X + 2_000, ORIGIN_Y + 100)])

    # Act
    mask = water_bodies_mask(_water(brook), _grid(), min_area_ha=1.0)

    # Assert
    assert not mask.any()


def test_empty_input_yields_empty_mask():
    # Arrange
    empty = gpd.GeoDataFrame({"natural": []}, geometry=[], crs=TARGET_CRS)

    # Act
    mask = water_bodies_mask(empty, _grid(), min_area_ha=1.0)

    # Assert
    assert mask.shape == _grid()["shape"] and not mask.any()


def test_does_not_mutate_the_input_geodataframe():
    # Arrange
    lake = _rect(ORIGIN_X + 500, ORIGIN_Y + 500, 200, 200)
    water = _water(lake, _rect(ORIGIN_X + 100, ORIGIN_Y + 100, 50, 50))

    # Act
    water_bodies_mask(water, _grid(), min_area_ha=1.0)

    # Assert - caller's frame is untouched (immutability rule)
    assert len(water) == 2
