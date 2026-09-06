"""Wind turbines must never be classified as buildings in the Abschichtung.

OSM carries `building=yes` on the same way as `power=generator` +
`generator:source=wind` for a handful of Austrian turbines. Without the filter
under test they land in `general_buildings_source` and exclude their own site.
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, Polygon

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windkraft.calc.abschichtung_common import TARGET_CRS, drop_wind_power_buildings  # noqa: E402


def _square(x: float, y: float, size: float = 7.0) -> Polygon:
    """Building-sized square footprint anchored at (x, y), in EPSG:31287 metres."""
    return Polygon([(x, y), (x + size, y), (x + size, y + size), (x, y + size)])


def _buildings(*geoms) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"building": ["yes"] * len(geoms)}, geometry=list(geoms), crs=TARGET_CRS)


def _wind(*geoms) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"generator:source": ["wind"] * len(geoms)}, geometry=list(geoms), crs=TARGET_CRS)


def test_removes_building_that_is_actually_a_wind_turbine():
    # Arrange - the turbine way and the building way are the SAME geometry in OSM
    turbine = _square(500_000, 400_000)
    buildings = _buildings(turbine, _square(600_000, 400_000))

    # Act
    kept = drop_wind_power_buildings(buildings, _wind(turbine))

    # Assert
    assert len(kept) == 1
    assert kept.geometry.iloc[0].equals(_square(600_000, 400_000))


def test_keeps_ordinary_buildings_far_from_any_turbine():
    # Arrange
    buildings = _buildings(_square(500_000, 400_000), _square(500_100, 400_000))

    # Act
    kept = drop_wind_power_buildings(buildings, _wind(_square(510_000, 400_000)))

    # Assert
    assert len(kept) == 2


def test_returns_input_unchanged_when_no_wind_objects_present():
    # Arrange
    buildings = _buildings(_square(500_000, 400_000))
    empty_wind = gpd.GeoDataFrame(geometry=[], crs=TARGET_CRS)

    # Act
    kept = drop_wind_power_buildings(buildings, empty_wind)

    # Assert
    assert len(kept) == 1


def test_does_not_mutate_the_input_geodataframe():
    # Arrange
    turbine = _square(500_000, 400_000)
    buildings = _buildings(turbine, _square(600_000, 400_000))

    # Act
    drop_wind_power_buildings(buildings, _wind(turbine))

    # Assert - caller's frame is untouched (immutability rule)
    assert len(buildings) == 2


def test_matches_node_turbines_sitting_inside_a_building_footprint():
    # Arrange - some turbines are mapped as a node on top of a mapped footprint
    footprint = _square(500_000, 400_000)
    buildings = _buildings(footprint)

    # Act
    kept = drop_wind_power_buildings(buildings, _wind(Point(500_003, 400_003)))

    # Assert
    assert len(kept) == 0
