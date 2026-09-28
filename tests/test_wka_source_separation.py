"""The WKA layer/export must share only the authoritative prepared source."""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.export import wka_bestand  # noqa: E402
from pipeline.layers import geo  # noqa: E402
from pipeline.prep import windkraft  # noqa: E402


def _authoritative_turbine() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {windkraft.ID_COLUMN: ["wka_at_sentinel"]},
        geometry=[Point(10, 10)],
        crs=windkraft.TARGET_CRS,
    )


def test_layer_and_export_share_the_prepared_inventory_not_osm(monkeypatch, tmp_path):
    authoritative = _authoritative_turbine()
    calls = []

    def load_authoritative():
        calls.append("prepared")
        return authoritative.copy()

    def osm_must_not_be_read(*args, **kwargs):
        raise AssertionError("OSM vector reader must not be a positive WKA source")

    monkeypatch.setattr(windkraft, "load_prepared", load_authoritative)
    monkeypatch.setattr(geo, "_read_prep_vector", osm_must_not_be_read)
    monkeypatch.setattr(geo, "layer_path", lambda *_: tmp_path / "official.tif")
    monkeypatch.setattr(geo, "read_layer_mask", lambda *_: np.zeros((2, 2), dtype=bool))
    # Put the sentinel in-zone: this exercises loading and classification but
    # avoids invoking hull rasterization in this isolated source test.
    monkeypatch.setattr(geo, "sample_mask_at_points", lambda *_: np.ones(1, dtype=bool))

    exported = wka_bestand.load_turbines()
    masks = geo.build_wka_bestand_hulls(
        {"shape": (2, 2), "bounds": (0, 0, 100, 100)},
        tmp_path,
        np.ones((2, 2), dtype=bool),
    )

    assert exported[windkraft.ID_COLUMN].tolist() == ["wka_at_sentinel"]
    assert calls == ["prepared", "prepared"]
    assert not masks[geo.WKA_BESTAND_BAND].any()
