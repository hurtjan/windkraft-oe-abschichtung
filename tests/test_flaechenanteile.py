from __future__ import annotations

import csv
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

from pipeline.analysis import flaechenanteile as fa


def _inputs(tmp_path, *, values=None, transform=Affine(1, 0, 0, 0, -1, 3)):
    names = list(fa.STATE_CODES)
    geoms = [box(x, 2 - y, x + 1, 3 - y) for y in range(3) for x in range(3)]
    boundaries = tmp_path / "bundesland_masken.gpkg"
    gpd.GeoDataFrame({"BL": names}, geometry=geoms, crs=fa.TARGET_CRS).to_file(boundaries, driver="GPKG")
    layer_paths = {}
    default = np.zeros((3, 3), dtype="uint8")
    values = values or {}
    for criterion in fa.BASE_CRITERIA + (fa.GENERAL_BUILDINGS_CRITERION,):
        path = tmp_path / f"{criterion.layer}.tif"
        arr = np.array(values.get(criterion.name, default), dtype="uint8")
        with rasterio.open(
            path, "w", driver="GTiff", height=3, width=3, count=1,
            dtype="uint8", crs=fa.TARGET_CRS, transform=transform, nodata=0,
        ) as ds:
            ds.write(arr, 1)
        layer_paths[criterion.layer] = path
    return boundaries, layer_paths


def _row(csv_path, code, unit, group, criterion):
    with csv_path.open(encoding="utf-8", newline="") as handle:
        return next(row for row in csv.DictReader(handle)
                    if (row["region_code"], row["analysis_unit"], row["group"], row["criterion"])
                    == (code, unit, group, criterion))


def test_group_union_does_not_double_count_and_austria_sums_states(tmp_path):
    settlement = np.zeros((3, 3), dtype="uint8")
    houses = np.zeros((3, 3), dtype="uint8")
    settlement[0, 0] = houses[0, 0] = 1
    slope = np.zeros((3, 3), dtype="uint8")
    slope[0, 1] = 1
    boundaries, layers = _inputs(tmp_path, values={
        "settlement_buffer": settlement,
        "haeuser_im_gruenen": houses,
        "slope_too_steep": slope,
    })
    csv_path, json_path = fa.analyze(
        regions_path=boundaries, layer_paths=layers, output_dir=tmp_path / "out", block_rows=1
    )

    union = _row(csv_path, "B", "group_union", "siedlung", "OR-Union")
    assert union["denominator_cells"] == "1"
    assert union["excluded_cells"] == "1"  # beide Einzelkriterien markieren dieselbe Zelle
    at_union = _row(csv_path, "AT", "group_union", "siedlung", "OR-Union")
    assert at_union["denominator_cells"] == "9"
    assert at_union["excluded_cells"] == "1"
    geography = _row(csv_path, "AT", "group_union", "geographie", "OR-Union")
    assert geography["excluded_cells"] == "1"
    metadata = json.loads(json_path.read_text(encoding="utf-8"))
    assert metadata["aggregation"].startswith("OR innerhalb jeder Gruppe")
    assert "nicht von fehlender Datenabdeckung" in metadata["unknown_data"]["limitation"]


def test_general_buildings_is_opt_in(tmp_path):
    buildings = np.zeros((3, 3), dtype="uint8")
    buildings[0, 0] = 1
    boundaries, layers = _inputs(tmp_path, values={"general_buildings_buffer": buildings})
    csv_default, _ = fa.analyze(
        regions_path=boundaries, layer_paths=layers, output_dir=tmp_path / "default"
    )
    csv_enabled, meta_enabled = fa.analyze(
        regions_path=boundaries, layer_paths=layers, output_dir=tmp_path / "enabled",
        include_general_buildings=True,
    )
    assert not any(row["criterion"] == "general_buildings_buffer"
                   for row in csv.DictReader(csv_default.open(encoding="utf-8")))
    assert _row(csv_enabled, "B", "criterion", "siedlung", "general_buildings_buffer")["excluded_cells"] == "1"
    assert json.loads(meta_enabled.read_text(encoding="utf-8"))["general_buildings_buffer_included"] is True


def test_missing_input_and_grid_mismatch_fail_clearly(tmp_path):
    boundaries, layers = _inputs(tmp_path)
    missing = dict(layers)
    missing["settlement_buffer"] = tmp_path / "missing.tif"
    with pytest.raises(FileNotFoundError, match="Checkpoint.*fehlen"):
        fa.analyze(regions_path=boundaries, layer_paths=missing, output_dir=tmp_path / "missing-out")

    mismatch = tmp_path / "mismatch.tif"
    with rasterio.open(
        mismatch, "w", driver="GTiff", height=3, width=3, count=1,
        dtype="uint8", crs=fa.TARGET_CRS, transform=Affine(1, 0, 0.1, 0, -1, 3), nodata=0,
    ) as ds:
        ds.write(np.zeros((3, 3), dtype="uint8"), 1)
    layers["haeuser_im_gruenen"] = mismatch
    with pytest.raises(ValueError, match="Rastertransformation"):
        fa.analyze(regions_path=boundaries, layer_paths=layers, output_dir=tmp_path / "grid-out")


def test_out_of_domain_raster_values_are_rejected(tmp_path):
    bad = np.zeros((3, 3), dtype="uint8")
    bad[0, 0] = 2
    boundaries, layers = _inputs(tmp_path, values={"settlement_buffer": bad})
    with pytest.raises(ValueError, match="binäre Werte"):
        fa.analyze(regions_path=boundaries, layer_paths=layers, output_dir=tmp_path / "bad-out")


def test_area_analysis_requires_projected_area_crs(tmp_path):
    boundaries, layers = _inputs(tmp_path)
    wrong_crs = tmp_path / "wrong-crs.tif"
    with rasterio.open(
        wrong_crs, "w", driver="GTiff", height=3, width=3, count=1,
        dtype="uint8", crs="EPSG:4326", transform=Affine(1, 0, 0, 0, -1, 3), nodata=0,
    ) as ds:
        ds.write(np.zeros((3, 3), dtype="uint8"), 1)
    layers["settlement_buffer"] = wrong_crs
    with pytest.raises(ValueError, match="benötigen EPSG:31287"):
        fa.analyze(regions_path=boundaries, layer_paths=layers, output_dir=tmp_path / "wrong-crs-out")
