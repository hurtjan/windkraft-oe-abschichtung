"""Contract tests for the authoritative WKA inventory preparation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import contract  # noqa: E402
from pipeline.prep import windkraft  # noqa: E402


def test_delivered_source_is_rfc7946_points_without_a_legacy_crs_member():
    raw = json.loads(contract.RAW["windkraft"]["standorte"].read_text(encoding="utf-8"))
    assert raw["type"] == "FeatureCollection"
    assert "crs" not in raw
    assert len(raw["features"]) == windkraft.EXPECTED_RAW_FEATURES
    assert {f["geometry"]["type"] for f in raw["features"]} == {"Point"}


def test_normalize_assigns_rfc7946_wgs84_reprojects_and_deduplicates():
    prepared = windkraft.normalize()
    assert prepared.crs is not None and prepared.crs.to_epsg() == windkraft.TARGET_EPSG
    assert len(prepared) == windkraft.EXPECTED_UNIQUE_COORDINATES
    assert prepared[windkraft.ID_COLUMN].is_unique
    assert prepared[windkraft.ID_COLUMN].str.startswith("wka_at_").all()
    assert (prepared.geometry.geom_type == "Point").all()
    # A projected Austrian coordinate cannot be raw longitude/latitude.
    assert prepared.geometry.x.between(0, 1_000_000).all()
    assert prepared.geometry.y.between(0, 1_000_000).all()


def test_non_point_source_is_rejected_before_preparation(tmp_path):
    source = tmp_path / "not-points.geojson"
    source.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": [[16, 48], [16.1, 48.1]]}}
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must be a Point"):
        windkraft.normalize(source)


def test_prepared_inventory_is_readable_and_matches_validation_counts():
    prepared = windkraft.load_prepared()
    assert len(prepared) == windkraft.EXPECTED_UNIQUE_COORDINATES
    assert prepared.crs is not None and prepared.crs.to_epsg() == windkraft.TARGET_EPSG
