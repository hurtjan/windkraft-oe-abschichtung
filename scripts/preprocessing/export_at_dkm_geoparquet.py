#!/usr/bin/env python3
"""Export Austrian DKM GST/NFL data to one EPSG:31287 GeoParquet file.

The SHP source states are delivered as state ZIPs containing one ZIP per KG.
This script extracts only GST_V2 and NFL_V2 shapefile members from each inner
ZIP, normalizes geometries to Austria Lambert (EPSG:31287), and writes batches
as WKB GeoParquet.

Niederoesterreich is available here only as DXF linework. For that state the
script reuses the tile+halo polygonization helpers from
create_noe_dkm_polygon_fill_map.py and emits classified NFL-like polygons from
NS symbols. It does not create GST_V2 parcels for Niederoesterreich.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import sys
import tempfile
import time
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import geopandas as gpd
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pyproj import CRS
from shapely import make_valid, set_precision, to_wkb
from shapely.geometry import GeometryCollection, MultiPolygon, Point, Polygon, box
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_MPL_CACHE = Path(tempfile.gettempdir()) / "windkraft_matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

from create_noe_dkm_polygon_fill_map import (  # noqa: E402
    bounds_intersect,
    category_base,
    choose_raw_crs,
    make_tile_jobs,
    parse_dxf,
    parse_dxf_bounds_fast,
    polygons_from_geometry,
    transform_bounds,
    transform_line,
)

TARGET_CRS = CRS.from_epsg(31287)
TARGET_CRS_LABEL = "EPSG:31287"
DEFAULT_OUTPUT = ROOT / "output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet"
DEFAULT_SUMMARY_CSV = ROOT / "output/kataster/at_dkm_gst_nfl_epsg31287_summary.csv"
DEFAULT_OVERVIEW_MD = ROOT / "output/kataster/at_dkm_gst_nfl_epsg31287_overview.md"
DEFAULT_SYMBOL_CSV = ROOT / "data/kataster/BEV_DKM_DXF_Symbole_V2.6.csv"
DEFAULT_NOE_DXF_ZIP = ROOT / "data/kataster/KAT_DKM_Niederoesterreich_DXF_20230401.zip"

SHP_LAYER_NAMES = ("GST_V2", "NFL_V2")
REQUIRED_SHAPEFILE_EXTS = {".shp", ".shx", ".dbf", ".prj", ".cpg"}
RAW_STRIP_TO_CRS = {"M31": "EPSG:31255", "M34": "EPSG:31256"}
PRE_BURGENLAND_SHP_INPUT_REFERENCE = {"GST_V2": 6_198_160, "NFL_V2": 12_082_959}

FIELD_NAMES = [
    "feature_id",
    "bundesland",
    "source_format",
    "source_archive",
    "source_inner_zip",
    "source_layer",
    "source_crs",
    "target_crs",
    "kg",
    "gnr",
    "rstatus",
    "mst",
    "ns",
    "ns_recht",
    "ns_category",
    "ns_label",
    "geometry",
]


@dataclass(frozen=True)
class ArchiveSpec:
    bundesland: str
    filename: str
    fallback_crs: str


DEFAULT_SHP_ARCHIVES = (
    ArchiveSpec("Burgenland", "KAT_DKM_Burgenland_SHP_20210401.zip", "EPSG:31256"),
    ArchiveSpec("Tirol", "KAT_DKM_Tirol_SHP_20221001.zip", "EPSG:31254"),
    ArchiveSpec("Vorarlberg", "KAT_DKM_Vorarlberg_SHP_20221001.zip", "EPSG:31254"),
    ArchiveSpec("Oberoesterreich", "KAT_DKM_Oberoesterreich_SHP_20221001.zip", "EPSG:31255"),
    ArchiveSpec("Kaernten", "KAT_DKM_Kaernten_SHP_20221001.zip", "EPSG:31255"),
    ArchiveSpec("Salzburg", "KAT_DKM_Salzburg_SHP_20221001.zip", "EPSG:31255"),
    ArchiveSpec("Steiermark", "KAT_DKM_Steiermark_SHP_20221001.zip", "EPSG:31256"),
    ArchiveSpec("Wien", "KAT_DKM_Wien_SHP_20221001.zip", "EPSG:31256"),
)


def str_value(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def crs_label(crs: Any, fallback: str | None = None) -> str:
    if crs is None:
        return fallback or ""
    parsed = CRS.from_user_input(crs)
    authority = parsed.to_authority()
    if authority:
        return f"{authority[0]}:{authority[1]}"
    return parsed.to_string()


def normalize_ns_code(value: Any) -> str | None:
    raw = str_value(value)
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    if stripped.upper().startswith("FIG"):
        stripped = stripped[3:]
    try:
        number = int(float(stripped))
    except ValueError:
        return stripped
    return str(number)


@dataclass(frozen=True)
class NsInfo:
    ns: str | None
    category: str | None
    label: str | None


class NsLookup:
    def __init__(self, symbol_csv: Path):
        self.by_symbol: dict[str, NsInfo] = {}
        self.by_ns_code: dict[str, NsInfo] = {}
        self.by_vermv10: dict[str, NsInfo] = {}
        with symbol_csv.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f, delimiter=";"):
                if (row.get("layer") or "").strip() != "NS":
                    continue
                symbol = (row.get("symbol") or "").strip()
                if not symbol:
                    continue
                ns_code = normalize_ns_code(symbol)
                info = NsInfo(
                    ns=ns_code,
                    category=category_base(row.get("kategorie") or ""),
                    label=(row.get("bezeichnung") or "").strip() or None,
                )
                self.by_symbol[symbol.upper()] = info
                if ns_code:
                    self.by_ns_code[ns_code] = info
                vermv10 = normalize_ns_code(row.get("vermv10_nr"))
                if vermv10:
                    self.by_vermv10[vermv10] = info

    def decode_symbol(self, symbol: Any) -> NsInfo:
        raw = str_value(symbol)
        if raw is None:
            return NsInfo(None, None, None)
        info = self.by_symbol.get(raw.strip().upper())
        if info:
            return info
        code = normalize_ns_code(raw)
        return self.decode_ns(code)

    def decode_ns(self, ns: Any) -> NsInfo:
        code = normalize_ns_code(ns)
        if code is None:
            return NsInfo(None, None, None)
        info = self.by_ns_code.get(code) or self.by_vermv10.get(code)
        if info:
            return info
        return NsInfo(code, "Unbekannt", None)


class Summary:
    def __init__(self) -> None:
        self.feature_counts: Counter[tuple[str, str, str]] = Counter()
        self.area_m2: Counter[tuple[str, str, str]] = Counter()
        self.quality: Counter[tuple[str, str, str]] = Counter()
        self.bounds: dict[str, list[float]] = {}
        self.notes: list[str] = []
        self.unmapped_ns: Counter[tuple[str, str, str]] = Counter()

    def inc_quality(self, bundesland: str, source_layer: str, metric: str, value: int | float = 1) -> None:
        self.quality[(bundesland, source_layer, metric)] += value

    def note(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)

    def observe_feature(self, row: dict[str, Any], geom: Polygon) -> None:
        bundesland = row["bundesland"]
        source_layer = row["source_layer"]
        source_crs = row.get("source_crs") or ""
        category = row.get("ns_category") or ""
        self.feature_counts[(bundesland, source_layer, source_crs)] += 1
        self.area_m2[(bundesland, source_layer, category)] += float(geom.area)
        self.inc_quality(bundesland, source_layer, "output_features", 1)
        minx, miny, maxx, maxy = geom.bounds
        current = self.bounds.get(bundesland)
        if current is None:
            self.bounds[bundesland] = [minx, miny, maxx, maxy]
        else:
            current[0] = min(current[0], minx)
            current[1] = min(current[1], miny)
            current[2] = max(current[2], maxx)
            current[3] = max(current[3], maxy)

    def observe_unmapped(self, bundesland: str, source_layer: str, ns: str | None) -> None:
        self.unmapped_ns[(bundesland, source_layer, ns or "")] += 1


class GeoParquetBatchWriter:
    def __init__(self, path: Path, batch_size: int, compression: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        geo_metadata = {
            "version": "1.0.0",
            "primary_column": "geometry",
            "columns": {
                "geometry": {
                    "encoding": "WKB",
                    "crs": TARGET_CRS.to_json_dict(),
                    "geometry_types": ["Polygon"],
                }
            },
            "creator": {"library": Path(__file__).name},
        }
        fields = [(name, pa.binary() if name == "geometry" else pa.string()) for name in FIELD_NAMES]
        self.schema = pa.schema(fields).with_metadata({b"geo": json.dumps(geo_metadata).encode("utf-8")})
        self.writer = pq.ParquetWriter(path, self.schema, compression=compression)
        self.batch_size = batch_size
        self.columns: dict[str, list[Any]] = {name: [] for name in FIELD_NAMES}
        self.row_count = 0

    def add(self, row: dict[str, Any], geom: Polygon) -> None:
        for name in FIELD_NAMES:
            if name == "geometry":
                self.columns[name].append(to_wkb(geom))
            else:
                self.columns[name].append(str_value(row.get(name)))
        self.row_count += 1
        if len(self.columns["geometry"]) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        if not self.columns["geometry"]:
            return
        table = pa.table(self.columns, schema=self.schema)
        self.writer.write_table(table)
        self.columns = {name: [] for name in FIELD_NAMES}

    def close(self) -> None:
        self.flush()
        self.writer.close()


def polygon_parts(geom: Any) -> list[Polygon]:
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return [p for p in geom.geoms if not p.is_empty]
    if isinstance(geom, GeometryCollection):
        parts: list[Polygon] = []
        for child in geom.geoms:
            parts.extend(polygon_parts(child))
        return parts
    return []


def cleaned_polygon_parts(
    geom: Any,
    summary: Summary,
    bundesland: str,
    source_layer: str,
    min_area_m2: float = 0.0,
) -> list[Polygon]:
    summary.inc_quality(bundesland, source_layer, "input_features", 1)
    if geom is None or geom.is_empty:
        summary.inc_quality(bundesland, source_layer, "empty_input_geometries", 1)
        return []

    repaired = geom
    if not geom.is_valid:
        summary.inc_quality(bundesland, source_layer, "invalid_before_make_valid", 1)
        repaired = make_valid(geom)
        summary.inc_quality(bundesland, source_layer, "make_valid_calls", 1)

    if repaired is None or repaired.is_empty:
        summary.inc_quality(bundesland, source_layer, "empty_after_make_valid", 1)
        return []

    parts = polygon_parts(repaired)
    if not parts:
        summary.inc_quality(bundesland, source_layer, "nonpolygon_discarded", 1)
        return []

    if len(parts) > 1:
        summary.inc_quality(bundesland, source_layer, "multipart_features", 1)
        summary.inc_quality(bundesland, source_layer, "exploded_extra_parts", len(parts) - 1)

    cleaned: list[Polygon] = []
    for part in parts:
        if part.is_empty:
            summary.inc_quality(bundesland, source_layer, "empty_polygon_parts", 1)
            continue
        if part.area <= min_area_m2:
            summary.inc_quality(bundesland, source_layer, "small_polygon_parts_discarded", 1)
            continue
        final = part
        if not final.is_valid:
            summary.inc_quality(bundesland, source_layer, "invalid_parts_after_first_repair", 1)
            final = make_valid(final)
            for nested in polygon_parts(final):
                if nested.is_valid and not nested.is_empty and nested.area > min_area_m2:
                    cleaned.append(nested)
            continue
        cleaned.append(final)

    if not cleaned:
        summary.inc_quality(bundesland, source_layer, "empty_after_polygon_cleaning", 1)
    return cleaned


def emit_cleaned_feature(
    writer: GeoParquetBatchWriter,
    summary: Summary,
    row_base: dict[str, Any],
    geom: Any,
    feature_id_base: str,
    min_area_m2: float = 0.0,
) -> int:
    parts = cleaned_polygon_parts(
        geom,
        summary,
        row_base["bundesland"],
        row_base["source_layer"],
        min_area_m2=min_area_m2,
    )
    emitted = 0
    for part_index, part in enumerate(parts):
        row = dict(row_base)
        row["feature_id"] = feature_id_base if len(parts) == 1 else f"{feature_id_base}:part{part_index + 1}"
        writer.add(row, part)
        summary.observe_feature(row, part)
        emitted += 1
    return emitted


def extract_layer_shapefiles(raw_inner_zip: bytes, layers: Iterable[str], temp_root: Path) -> dict[str, Path]:
    layer_set = set(layers)
    out_dir = temp_root
    out_dir.mkdir(parents=True, exist_ok=True)
    found: dict[str, Path] = {}
    with zipfile.ZipFile(io.BytesIO(raw_inner_zip)) as inner:
        for member in inner.namelist():
            name = Path(member).name
            suffix = Path(name).suffix.lower()
            stem = Path(name).stem
            if suffix not in REQUIRED_SHAPEFILE_EXTS:
                continue
            layer = next((candidate for candidate in layer_set if stem.endswith(candidate)), None)
            if layer is None:
                continue
            target = out_dir / name
            target.write_bytes(inner.read(member))
            if suffix == ".shp":
                found[layer] = target
    return found


def extract_layer_shapefiles_from_members(
    outer: zipfile.ZipFile,
    members: Iterable[str],
    layers: Iterable[str],
    temp_root: Path,
) -> dict[str, Path]:
    layer_set = set(layers)
    temp_root.mkdir(parents=True, exist_ok=True)
    found: dict[str, Path] = {}
    for member in members:
        name = Path(member).name
        suffix = Path(name).suffix.lower()
        stem = Path(name).stem
        if suffix not in REQUIRED_SHAPEFILE_EXTS:
            continue
        layer = next((candidate for candidate in layer_set if stem.endswith(candidate)), None)
        if layer is None:
            continue
        target = temp_root / name
        target.write_bytes(outer.read(member))
        if suffix == ".shp":
            found[layer] = target
    return found


def read_layer(path: Path, source_crs: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path, engine="pyogrio")
    if gdf.crs is None:
        gdf = gdf.set_crs(source_crs, allow_override=True)
    return gdf


def process_shp_gdf(
    gdf: gpd.GeoDataFrame,
    archive: ArchiveSpec,
    source_archive: str,
    source_inner_zip: str,
    source_layer: str,
    lookup: NsLookup,
    writer: GeoParquetBatchWriter,
    summary: Summary,
) -> int:
    if gdf.empty:
        return 0

    source_crs = crs_label(gdf.crs, archive.fallback_crs)
    if source_crs != TARGET_CRS_LABEL:
        gdf = gdf.to_crs(TARGET_CRS)

    emitted = 0
    attrs = gdf.drop(columns=[gdf.geometry.name])
    records = attrs.to_dict("records")
    for row_index, (record, geom) in enumerate(zip(records, gdf.geometry.values), 1):
        ns_raw = str_value(record.get("NS"))
        ns_info = lookup.decode_ns(ns_raw) if source_layer == "NFL_V2" else NsInfo(None, None, None)
        if source_layer == "NFL_V2" and ns_info.category == "Unbekannt":
            summary.observe_unmapped(archive.bundesland, source_layer, ns_raw)

        row_base = {
            "bundesland": archive.bundesland,
            "source_format": "SHP_ZIP",
            "source_archive": source_archive,
            "source_inner_zip": source_inner_zip,
            "source_layer": source_layer,
            "source_crs": source_crs,
            "target_crs": TARGET_CRS_LABEL,
            "kg": str_value(record.get("KG")),
            "gnr": str_value(record.get("GNR")),
            "rstatus": str_value(record.get("RSTATUS")),
            "mst": str_value(record.get("MST")),
            "ns": ns_raw,
            "ns_recht": str_value(record.get("NS_RECHT")),
            "ns_category": ns_info.category,
            "ns_label": ns_info.label,
        }
        kg_label = row_base["kg"] or Path(source_inner_zip).stem
        feature_id = f"{archive.bundesland}:{source_layer}:{kg_label}:{row_index}"
        emitted += emit_cleaned_feature(writer, summary, row_base, geom, feature_id)
    return emitted


def selected_archives(args: argparse.Namespace) -> list[ArchiveSpec]:
    if not args.only_bundesland:
        return list(DEFAULT_SHP_ARCHIVES)
    wanted = {item.strip().lower() for item in args.only_bundesland.split(",") if item.strip()}
    return [spec for spec in DEFAULT_SHP_ARCHIVES if spec.bundesland.lower() in wanted]


def export_shp_archives(
    args: argparse.Namespace,
    lookup: NsLookup,
    writer: GeoParquetBatchWriter,
    summary: Summary,
) -> None:
    data_dir = Path(args.data_dir)
    layers = tuple(layer.strip() for layer in args.layers.split(",") if layer.strip())
    layers = tuple(layer for layer in layers if layer in SHP_LAYER_NAMES)
    if not layers:
        raise SystemExit("--layers must include GST_V2 and/or NFL_V2")

    for archive in selected_archives(args):
        archive_path = data_dir / archive.filename
        if not archive_path.exists():
            summary.note(f"Missing SHP archive for {archive.bundesland}: {archive_path}")
            continue

        print(f"SHP {archive.bundesland}: {archive.filename}", flush=True)
        archive_t0 = time.time()
        with zipfile.ZipFile(archive_path) as outer, tempfile.TemporaryDirectory(
            dir=args.temp_dir
        ) as temp_dir_name:
            temp_root = Path(temp_dir_name)
            inner_names = sorted(n for n in outer.namelist() if n.lower().endswith(".zip"))
            if inner_names:
                work_units = [("zip", inner_name, None) for inner_name in inner_names]
            else:
                kg_dirs = sorted(
                    {
                        member.split("/", 1)[0]
                        for member in outer.namelist()
                        if "/" in member and member.split("/", 1)[0].isdigit()
                    }
                )
                work_units = [
                    (
                        "members",
                        kg_dir,
                        [member for member in outer.namelist() if member.startswith(f"{kg_dir}/")],
                    )
                    for kg_dir in kg_dirs
                ]
            if args.max_inner_zips_per_archive:
                work_units = work_units[: args.max_inner_zips_per_archive]

            for inner_index, (unit_kind, inner_name, members) in enumerate(work_units, 1):
                with tempfile.TemporaryDirectory(prefix="dkm_kg_", dir=temp_root) as inner_temp_name:
                    if unit_kind == "zip":
                        layer_paths = extract_layer_shapefiles(outer.read(inner_name), layers, Path(inner_temp_name))
                    else:
                        layer_paths = extract_layer_shapefiles_from_members(
                            outer,
                            members or [],
                            layers,
                            Path(inner_temp_name),
                        )
                    for source_layer in layers:
                        shp_path = layer_paths.get(source_layer)
                        if shp_path is None:
                            summary.inc_quality(archive.bundesland, source_layer, "missing_inner_layers", 1)
                            continue
                        try:
                            gdf = read_layer(shp_path, archive.fallback_crs)
                        except Exception as exc:
                            summary.inc_quality(archive.bundesland, source_layer, "read_errors", 1)
                            print(f"WARN failed reading {archive.filename}/{inner_name}/{source_layer}: {exc}", flush=True)
                            continue
                        emitted = process_shp_gdf(
                            gdf,
                            archive,
                            archive.filename,
                            inner_name,
                            source_layer,
                            lookup,
                            writer,
                            summary,
                        )
                        summary.inc_quality(archive.bundesland, source_layer, "inner_layers_read", 1)
                        if emitted == 0:
                            summary.inc_quality(archive.bundesland, source_layer, "inner_layers_no_output", 1)

                if inner_index % 100 == 0 or inner_index == len(work_units):
                    print(
                        f"  {archive.bundesland} inner {inner_index}/{len(work_units)} rows={writer.row_count}",
                        flush=True,
                    )
        print(f"SHP {archive.bundesland} done in {time.time() - archive_t0:.1f}s", flush=True)


def build_noe_tile_jobs(
    zf: zipfile.ZipFile,
    names: list[str],
    line_layers: set[str],
    tile_size_m: float,
    tile_halo_m: float,
) -> list[tuple[int, tuple[float, float, float, float], tuple[float, float, float, float], list[str]]]:
    file_infos: list[tuple[str, tuple[float, float, float, float]]] = []
    overall = [math.inf, math.inf, -math.inf, -math.inf]
    for index, name in enumerate(names, 1):
        raw_bounds = parse_dxf_bounds_fast(zf.read(name), line_layers)
        target_bounds = transform_bounds(raw_bounds)
        if target_bounds:
            file_infos.append((name, target_bounds))
            overall[0] = min(overall[0], target_bounds[0])
            overall[1] = min(overall[1], target_bounds[1])
            overall[2] = max(overall[2], target_bounds[2])
            overall[3] = max(overall[3], target_bounds[3])
        if index % 250 == 0 or index == len(names):
            print(f"  NOE bounds {index}/{len(names)}", flush=True)
    if overall[0] == math.inf:
        return []
    return make_tile_jobs(file_infos, overall[0], overall[1], overall[2], overall[3], tile_size_m, tile_halo_m)


def export_noe_dxf(
    args: argparse.Namespace,
    lookup: NsLookup,
    writer: GeoParquetBatchWriter,
    summary: Summary,
) -> None:
    zip_path = Path(args.noe_dxf_zip)
    if not zip_path.exists():
        summary.note(f"Niederoesterreich DXF archive is missing: {zip_path}")
        return

    line_layers = {item.strip() for item in args.noe_line_layers.split(",") if item.strip()}
    bundesland = "Niederoesterreich"
    source_layer = "NFL_DXF_POLYGONIZED"
    print(f"NOE DXF: {zip_path.name}", flush=True)
    t0 = time.time()

    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(n for n in zf.namelist() if n.lower().endswith(".dxf"))
        if args.noe_limit_files:
            names = names[: args.noe_limit_files]
        summary.inc_quality(bundesland, source_layer, "source_dxf_files", len(names))

        tile_jobs = build_noe_tile_jobs(zf, names, line_layers, args.noe_tile_size_m, args.noe_tile_halo_m)
        summary.inc_quality(bundesland, source_layer, "tiles_total", len(tile_jobs))
        if not tile_jobs:
            summary.note("No Niederoesterreich DXF tile jobs were generated.")
            return

        for tile_index, job in enumerate(tile_jobs, 1):
            emitted = export_noe_tile(
                zf,
                job,
                line_layers,
                args.noe_precision_m,
                args.noe_min_area_m2,
                lookup,
                writer,
                summary,
                zip_path.name,
            )
            if emitted == 0:
                summary.inc_quality(bundesland, source_layer, "tiles_no_output", 1)
            if tile_index % 10 == 0 or tile_index == len(tile_jobs):
                print(
                    f"  NOE tiles {tile_index}/{len(tile_jobs)} rows={writer.row_count}",
                    flush=True,
                )

    summary.note("Niederoesterreich has no GST_V2 parcel layer in this export; NFL rows are DXF tile+halo polygonizations.")
    print(f"NOE DXF done in {time.time() - t0:.1f}s", flush=True)


def export_noe_tile(
    zf: zipfile.ZipFile,
    job: tuple[int, tuple[float, float, float, float], tuple[float, float, float, float], list[str]],
    line_layers: set[str],
    precision_m: float,
    min_area_m2: float,
    lookup: NsLookup,
    writer: GeoParquetBatchWriter,
    summary: Summary,
    source_archive: str,
) -> int:
    tile_id, inner_bounds, halo_bounds, file_names = job
    bundesland = "Niederoesterreich"
    source_layer = "NFL_DXF_POLYGONIZED"
    inner_box = box(*inner_bounds)
    lines = []
    ns_points: list[tuple[str, float, float, str, str, str]] = []

    for name in file_names:
        raw_lines, raw_points, raw_bounds = parse_dxf(zf.read(name), line_layers)
        if not raw_bounds:
            continue
        strip, transformer = choose_raw_crs(raw_bounds)
        source_crs = RAW_STRIP_TO_CRS.get(strip, strip)
        kg_code = Path(name).stem

        for raw_line in raw_lines:
            line = transform_line(raw_line, transformer)
            if line is not None and bounds_intersect(line.bounds, halo_bounds):
                lines.append(line)

        if raw_points:
            symbols = [point[0] for point in raw_points]
            xs = [point[1] for point in raw_points]
            ys = [point[2] for point in raw_points]
            tx, ty = transformer.transform(xs, ys)
            for symbol, x, y in zip(symbols, tx, ty):
                if halo_bounds[0] <= x <= halo_bounds[2] and halo_bounds[1] <= y <= halo_bounds[3]:
                    ns_points.append((symbol, x, y, kg_code, name, source_crs))

    summary.inc_quality(bundesland, source_layer, "tile_file_refs", len(file_names))
    summary.inc_quality(bundesland, source_layer, "tile_input_lines", len(lines))
    summary.inc_quality(bundesland, source_layer, "tile_input_ns_points", len(ns_points))
    if not lines:
        summary.inc_quality(bundesland, source_layer, "tiles_no_lines", 1)
        return 0
    if not ns_points:
        summary.inc_quality(bundesland, source_layer, "tiles_no_ns", 1)

    try:
        merged = unary_union([set_precision(line, precision_m) for line in lines])
        polys = [poly for poly in polygonize(merged) if poly.area >= min_area_m2 and poly.intersects(inner_box)]
    except Exception as exc:
        summary.inc_quality(bundesland, source_layer, "polygonize_errors", 1)
        print(f"WARN NOE tile {tile_id} polygonize failed: {exc}", flush=True)
        return 0

    summary.inc_quality(bundesland, source_layer, "polygonized_polygons", len(polys))
    if not polys:
        return 0

    tree = STRtree(polys)
    poly_votes: dict[int, Counter[tuple[str | None, str | None, str | None, str, str, str]]] = defaultdict(Counter)
    for symbol, x, y, kg_code, source_dxf, source_crs in ns_points:
        ns_info = lookup.decode_symbol(symbol)
        if ns_info.category == "Unbekannt":
            summary.observe_unmapped(bundesland, source_layer, symbol)
        point = Point(x, y)
        candidates = tree.query(point)
        best_i = None
        best_area = math.inf
        for candidate in candidates:
            poly_index = int(candidate)
            poly = polys[poly_index]
            if poly.covers(point) and poly.area < best_area:
                best_i = poly_index
                best_area = poly.area
        if best_i is not None:
            poly_votes[best_i][(ns_info.ns, ns_info.category, ns_info.label, kg_code, source_dxf, source_crs)] += 1
            if inner_bounds[0] <= x < inner_bounds[2] and inner_bounds[1] <= y < inner_bounds[3]:
                summary.inc_quality(bundesland, source_layer, "assigned_ns_points", 1)
        elif inner_bounds[0] <= x < inner_bounds[2] and inner_bounds[1] <= y < inner_bounds[3]:
            summary.inc_quality(bundesland, source_layer, "unassigned_ns_points", 1)

    emitted = 0
    for poly_index, poly in enumerate(polys):
        try:
            clipped = poly.intersection(inner_box)
        except Exception:
            summary.inc_quality(bundesland, source_layer, "clip_errors", 1)
            continue
        pieces = [piece for piece in polygons_from_geometry(clipped) if piece.area >= min_area_m2]
        if not pieces:
            continue

        votes = poly_votes.get(poly_index)
        if not votes:
            summary.inc_quality(bundesland, source_layer, "unassigned_polygons", len(pieces))
            summary.inc_quality(bundesland, source_layer, "unassigned_polygon_area_m2", sum(piece.area for piece in pieces))
            continue

        if len(votes) > 1:
            summary.inc_quality(bundesland, source_layer, "ambiguous_polygons", len(pieces))
        ns, category, label, kg_code, source_dxf, source_crs = votes.most_common(1)[0][0]
        row_base = {
            "bundesland": bundesland,
            "source_format": "DXF_POLYGONIZED",
            "source_archive": source_archive,
            "source_inner_zip": source_dxf,
            "source_layer": source_layer,
            "source_crs": source_crs,
            "target_crs": TARGET_CRS_LABEL,
            "kg": kg_code,
            "gnr": None,
            "rstatus": None,
            "mst": None,
            "ns": ns,
            "ns_recht": None,
            "ns_category": category,
            "ns_label": label,
        }
        for piece_index, piece in enumerate(pieces, 1):
            feature_id = f"{bundesland}:{source_layer}:tile{tile_id}:poly{poly_index + 1}:piece{piece_index}"
            emitted += emit_cleaned_feature(
                writer,
                summary,
                row_base,
                piece,
                feature_id,
                min_area_m2=min_area_m2,
            )
    return emitted


def write_summary_csv(summary: Summary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["section", "bundesland", "source_layer", "source_crs", "ns_category", "metric", "value"])
        for (bundesland, source_layer, source_crs), count in sorted(summary.feature_counts.items()):
            writer.writerow(["feature_counts", bundesland, source_layer, source_crs, "", "features", count])
        for (bundesland, source_layer, category), area in sorted(summary.area_m2.items()):
            writer.writerow(["areas", bundesland, source_layer, "", category, "area_m2", round(area, 2)])
            writer.writerow(["areas", bundesland, source_layer, "", category, "area_km2", round(area / 1_000_000, 6)])
        for bundesland, bounds in sorted(summary.bounds.items()):
            writer.writerow(["bounds", bundesland, "", TARGET_CRS_LABEL, "", "minx", round(bounds[0], 3)])
            writer.writerow(["bounds", bundesland, "", TARGET_CRS_LABEL, "", "miny", round(bounds[1], 3)])
            writer.writerow(["bounds", bundesland, "", TARGET_CRS_LABEL, "", "maxx", round(bounds[2], 3)])
            writer.writerow(["bounds", bundesland, "", TARGET_CRS_LABEL, "", "maxy", round(bounds[3], 3)])
        for (bundesland, source_layer, metric), value in sorted(summary.quality.items()):
            writer.writerow(["quality", bundesland, source_layer, "", "", metric, round(value, 2) if isinstance(value, float) else value])
        for (bundesland, source_layer, ns), count in sorted(summary.unmapped_ns.items()):
            writer.writerow(["unmapped_ns", bundesland, source_layer, "", ns, "count", count])
        for note in summary.notes:
            writer.writerow(["notes", "", "", "", "", "note", note])


def rows_for_markdown(headers: list[str], rows: Iterable[list[Any]]) -> str:
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        output.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(output)


def write_overview_md(summary: Summary, path: Path, output_path: Path, args: argparse.Namespace, runtime_s: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    count_rows = [
        [bundesland, layer, source_crs, count]
        for (bundesland, layer, source_crs), count in sorted(summary.feature_counts.items())
    ]
    area_rows = [
        [bundesland, layer, category or "(none)", round(area / 1_000_000, 4)]
        for (bundesland, layer, category), area in sorted(summary.area_m2.items())
    ]
    quality_rows = [
        [bundesland, layer, metric, value]
        for (bundesland, layer, metric), value in sorted(summary.quality.items())
        if metric
        in {
            "input_features",
            "output_features",
            "invalid_before_make_valid",
            "empty_input_geometries",
            "empty_after_make_valid",
            "nonpolygon_discarded",
            "multipart_features",
            "exploded_extra_parts",
            "unassigned_polygons",
            "ambiguous_polygons",
        }
    ]
    bounds_rows = [
        [bundesland, round(b[0], 2), round(b[1], 2), round(b[2], 2), round(b[3], 2)]
        for bundesland, b in sorted(summary.bounds.items())
    ]
    limit_notes = []
    if args.max_inner_zips_per_archive:
        limit_notes.append(f"SHP limited to {args.max_inner_zips_per_archive} inner ZIPs per archive.")
    if args.noe_limit_files:
        limit_notes.append(f"NOE DXF limited to {args.noe_limit_files} DXF files.")

    expected_lines = []
    for layer, expected in PRE_BURGENLAND_SHP_INPUT_REFERENCE.items():
        actual = sum(value for (bl, lyr, metric), value in summary.quality.items() if lyr == layer and metric == "input_features")
        expected_lines.append(
            f"- {layer}: observed {actual:,} input features; previous reference without Burgenland was {expected:,}."
        )

    parts = [
        "# AT DKM GST/NFL GeoParquet Export",
        "",
        f"- Output: `{output_path}`",
        f"- Target CRS: `{TARGET_CRS_LABEL}`",
        f"- Runtime: {runtime_s:.1f}s",
        f"- Feature rows written: {sum(summary.feature_counts.values()):,}",
        "",
        "## Notes",
        "",
    ]
    for note in [*summary.notes, *limit_notes]:
        parts.append(f"- {note}")
    if not summary.notes and not limit_notes:
        parts.append("- No special notes.")
    parts.extend(["", "## SHP Input Count Check", "", *expected_lines])
    parts.extend(["", "## Feature Counts", "", rows_for_markdown(["Bundesland", "Layer", "Source CRS", "Features"], count_rows or [["", "", "", 0]])])
    parts.extend(["", "## Area By Category", "", rows_for_markdown(["Bundesland", "Layer", "Category", "km2"], area_rows or [["", "", "", 0]])])
    parts.extend(["", "## Geometry Cleaning", "", rows_for_markdown(["Bundesland", "Layer", "Metric", "Value"], quality_rows or [["", "", "", 0]])])
    parts.extend(["", "## Bounds EPSG:31287", "", rows_for_markdown(["Bundesland", "minx", "miny", "maxx", "maxy"], bounds_rows or [["", 0, 0, 0, 0]])])
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default=str(ROOT / "data/kataster"), help="Directory containing DKM source archives")
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT), help="GeoParquet output path")
    ap.add_argument("--summary-csv", default=str(DEFAULT_SUMMARY_CSV), help="CSV summary output path")
    ap.add_argument("--overview-md", default=str(DEFAULT_OVERVIEW_MD), help="Markdown overview output path")
    ap.add_argument("--symbol-csv", default=str(DEFAULT_SYMBOL_CSV), help="BEV DKM symbol CSV path")
    ap.add_argument("--layers", default="GST_V2,NFL_V2", help="Comma-separated SHP layers to export")
    ap.add_argument("--only-bundesland", default="", help="Comma-separated subset of SHP Bundesland names")
    ap.add_argument("--max-inner-zips-per-archive", type=int, default=0, help="Smoke-test limit per SHP archive")
    ap.add_argument("--skip-shp", action="store_true", help="Skip SHP archives")
    ap.add_argument("--skip-noe-dxf", action="store_true", help="Skip Niederoesterreich DXF polygonization")
    ap.add_argument("--noe-dxf-zip", default=str(DEFAULT_NOE_DXF_ZIP), help="Niederoesterreich DXF ZIP path")
    ap.add_argument("--noe-limit-files", type=int, default=0, help="Smoke-test limit for NOE DXF files")
    ap.add_argument("--noe-line-layers", default="GG,NG,KG", help="Comma-separated DXF line layers for NOE polygonization")
    ap.add_argument("--noe-tile-size-m", type=float, default=20_000.0, help="NOE tile interior size in EPSG:31287 metres")
    ap.add_argument("--noe-tile-halo-m", type=float, default=2_000.0, help="NOE tile halo in EPSG:31287 metres")
    ap.add_argument("--noe-precision-m", type=float, default=0.01, help="NOE line precision before polygonize")
    ap.add_argument("--noe-min-area-m2", type=float, default=4.0, help="Minimum NOE polygon area")
    ap.add_argument("--batch-size", type=int, default=50_000, help="Rows per Parquet write batch")
    ap.add_argument("--compression", default="zstd", help="Parquet compression codec")
    ap.add_argument("--temp-dir", default=None, help="Optional temp directory for extracting inner SHP ZIPs")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite output files if they exist")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    summary_csv = Path(args.summary_csv)
    overview_md = Path(args.overview_md)
    for path in (output_path, summary_csv, overview_md):
        if path.exists() and not args.overwrite:
            raise SystemExit(f"{path} already exists; pass --overwrite")

    t0 = time.time()
    summary = Summary()
    lookup = NsLookup(Path(args.symbol_csv))
    writer = GeoParquetBatchWriter(output_path, args.batch_size, args.compression)
    try:
        if not args.skip_shp:
            export_shp_archives(args, lookup, writer, summary)
        if not args.skip_noe_dxf:
            export_noe_dxf(args, lookup, writer, summary)
    finally:
        writer.close()

    runtime_s = time.time() - t0
    write_summary_csv(summary, summary_csv)
    write_overview_md(summary, overview_md, output_path, args, runtime_s)
    print(f"wrote {output_path} rows={writer.row_count}", flush=True)
    print(f"wrote {summary_csv}", flush=True)
    print(f"wrote {overview_md}", flush=True)


if __name__ == "__main__":
    main()
