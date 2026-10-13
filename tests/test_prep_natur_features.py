"""prep/natur: eine Zeile je Quell-Feature, Spalte layer, Original-Geometrietypen."""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPoint, Point, box

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.prep.natur import build_schutzgebiete  # noqa: E402


def _gdf(geoms, **cols):
    return gpd.GeoDataFrame(cols, geometry=geoms, crs="EPSG:3035")


def test_one_row_per_feature_layer_column_and_geometry_types():
    frames = {
        "NP_AT_2024": _gdf([box(0, 0, 1, 1), box(0, 0, 1, 1)], KAT=["NP", "NP"]),  # identische Geometrie: kein Dissolve
        "S_AT_2024": _gdf([box(2, 2, 3, 3), box(4, 4, 5, 5), box(6, 6, 7, 7)],
                          KAT=["S"] * 3, KAT_SUB=["RG", "XX", "GB"]),
        "NDKM_AT_2024": _gdf([Point(1, 1), MultiPoint([(2, 2), (3, 3)]), box(0, 0, 1, 1)], KAT=["NDKM"] * 3),
    }
    out = build_schutzgebiete(frames, {"S_AT_2024": {"KAT_SUB": ["RG", "GB"]}})
    counts = out["layer"].value_counts().to_dict()
    assert counts == {"NP_AT_2024": 2, "S_AT_2024": 2, "NDKM_AT_2024": 3}
    assert (out["layer"] == out["quelle"]).all()
    assert {"KAT", "KAT_SUB", "quelle", "layer", "geometry"} <= set(out.columns)
    ndkm = out[out["layer"] == "NDKM_AT_2024"].geometry.geom_type.tolist()
    assert ndkm == ["Point", "MultiPoint", "Polygon"]  # Punkte unverändert, nicht gepuffert
    assert out.crs.to_epsg() == 3035
