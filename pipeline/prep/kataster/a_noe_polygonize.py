#!/usr/bin/env python3
"""Prep Kataster, Stufe a: NÖ-DXF-Polygonisierung (docs/rewrite/PLAN.md §4/§7,
Paket W1.P2).

Niederösterreich liegt nur als DXF-Linienwerk vor (kein ``GST_V2``-
Parzellenlayer). Diese Stufe rekonstruiert daraus Polygone: Kachelung mit
Halo, Linienverschmelzung + ``shapely.ops.polygonize`` je Kachel, und eine
Mehrheitsabstimmung über benachbarte NS-Symbolpunkte (``STRtree``) je
Polygon. Das ist die teuerste Stufe der ganzen Kette (docs/rewrite/PLAN.md
§4) - deshalb von Stufe b (billiger Export der übrigen acht Bundesländer +
Zusammenführung) getrennt: ein Rerun von b liest dieses Ergebnis, statt die
Polygonisierung zu wiederholen.

Verschoben, unverändert in der Verarbeitungslogik, aus
``scripts/preprocessing/export_at_dkm_geoparquet.py``
(``export_noe_dxf``/``export_noe_tile``/``build_noe_tile_jobs``). Die reinen
DXF-/Geometrie-Hilfsfunktionen kommen aus
``pipeline.prep.kataster.diagnostics`` (selbst verschoben aus
``scripts/preprocessing/create_noe_dkm_polygon_fill_map.py`` - identischer
Import wie im Original, nur der Pfad hat sich geändert).

Ausgabe: ein eigenständiges GeoParquet mit demselben 17-Spalten-Schema wie
das kombinierte Endergebnis (``pipeline.prep.kataster.common.FIELD_NAMES``),
nur mit den NÖ-Zeilen, unter
``contract.PREP["kataster"]["a_noe_polygonize"]``.

Fachliche Auffälligkeit, NICHT verändert (PLAN.md §8 Regel 4 - siehe Bericht
zu W1.P2): ``--noe-min-area-m2`` (Default 4.0 m²) und die
Mehrheitsabstimmung sind unverändert aus dem migrierten Code übernommen.
Laut docs/rohdaten.md sind rund 29 % der NÖ-Polygone als ``ambiguous`` oder
``unassigned`` markiert - eine bekannte Unsicherheit der Rekonstruktion,
die nur Niederösterreich betrifft.
"""
from __future__ import annotations

import argparse
import math
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from shapely.geometry import Point, box
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree
from shapely import set_precision

from pipeline import contract, fingerprint, runtime
from pipeline.prep.kataster.common import (
    GeoParquetBatchWriter,
    NsLookup,
    Summary,
    TARGET_CRS_LABEL,
    emit_cleaned_feature,
    write_overview_md,
    write_summary_csv,
)
from pipeline.prep.kataster.diagnostics import (
    bounds_intersect,
    choose_raw_crs,
    make_tile_jobs,
    parse_dxf,
    parse_dxf_bounds_fast,
    polygons_from_geometry,
    transform_bounds,
    transform_line,
)

RAW_STRIP_TO_CRS = {"M31": "EPSG:31255", "M34": "EPSG:31256"}

PREP_DIR = contract.PREP["kataster"]["a_noe_polygonize"]
DEFAULT_OUTPUT = PREP_DIR / "noe_dxf_polygonized.geoparquet"
DEFAULT_SUMMARY_CSV = PREP_DIR / "noe_dxf_polygonized_summary.csv"
DEFAULT_OVERVIEW_MD = PREP_DIR / "noe_dxf_polygonized_overview.md"


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


def export_noe_dxf(
    *,
    noe_dxf_zip: Path,
    noe_line_layers: str,
    noe_limit_files: int,
    noe_tile_size_m: float,
    noe_tile_halo_m: float,
    noe_precision_m: float,
    noe_min_area_m2: float,
    lookup: NsLookup,
    writer: GeoParquetBatchWriter,
    summary: Summary,
) -> None:
    if not noe_dxf_zip.exists():
        summary.note(f"Niederoesterreich DXF archive is missing: {noe_dxf_zip}")
        return

    line_layers = {item.strip() for item in noe_line_layers.split(",") if item.strip()}
    bundesland = "Niederoesterreich"
    source_layer = "NFL_DXF_POLYGONIZED"
    print(f"NOE DXF: {noe_dxf_zip.name}", flush=True)
    t0 = time.time()

    with zipfile.ZipFile(noe_dxf_zip) as zf:
        names = sorted(n for n in zf.namelist() if n.lower().endswith(".dxf"))
        if noe_limit_files:
            names = names[:noe_limit_files]
        summary.inc_quality(bundesland, source_layer, "source_dxf_files", len(names))

        tile_jobs = build_noe_tile_jobs(zf, names, line_layers, noe_tile_size_m, noe_tile_halo_m)
        summary.inc_quality(bundesland, source_layer, "tiles_total", len(tile_jobs))
        if not tile_jobs:
            summary.note("No Niederoesterreich DXF tile jobs were generated.")
            return

        for tile_index, job in enumerate(tile_jobs, 1):
            emitted = export_noe_tile(
                zf,
                job,
                line_layers,
                noe_precision_m,
                noe_min_area_m2,
                lookup,
                writer,
                summary,
                noe_dxf_zip.name,
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


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT), help="GeoParquet output path")
    ap.add_argument("--summary-csv", default=str(DEFAULT_SUMMARY_CSV), help="CSV summary output path")
    ap.add_argument("--overview-md", default=str(DEFAULT_OVERVIEW_MD), help="Markdown overview output path")
    ap.add_argument("--noe-limit-files", type=int, default=0, help="Smoke-test limit for NOE DXF files")
    ap.add_argument("--noe-line-layers", default="GG,NG,KG", help="Comma-separated DXF line layers for NOE polygonization")
    ap.add_argument("--noe-tile-size-m", type=float, default=20_000.0, help="NOE tile interior size in EPSG:31287 metres")
    ap.add_argument("--noe-tile-halo-m", type=float, default=2_000.0, help="NOE tile halo in EPSG:31287 metres")
    ap.add_argument("--noe-precision-m", type=float, default=0.01, help="NOE line precision before polygonize")
    ap.add_argument("--noe-min-area-m2", type=float, default=4.0, help="Minimum NOE polygon area")
    ap.add_argument("--batch-size", type=int, default=50_000, help="Rows per Parquet write batch")
    ap.add_argument("--compression", default="zstd", help="Parquet compression codec")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite output files if they exist")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    output_path = runtime.ensure_parent(Path(args.output))
    summary_csv = Path(args.summary_csv)
    overview_md = Path(args.overview_md)
    noe_dxf_zip = contract.RAW["kataster"]["noe_dxf_zip"]
    symbol_csv = contract.RAW["kataster"]["symbol_csv"]

    # Selbst-Ueberspringer, gleiches Muster wie pipeline/prep/osm.py
    # (run_extract/run_layers): ein wiederholter `make all` ohne
    # Eingabeaenderung soll diese teuerste Prep-Stufe nicht neu rechnen,
    # statt hart abzubrechen (Punkt 52, docs/rewrite/PLAN.md).
    if (
        not args.overwrite
        and not args.noe_limit_files
        and output_path.exists()
        and summary_csv.exists()
        and overview_md.exists()
        and fingerprint.matches(PREP_DIR, [noe_dxf_zip, symbol_csv])
    ):
        print(f"[skip]  prep-kataster-a: Fingerabdruck unveraendert -> {output_path}", flush=True)
        return

    # Kein "already exists"-Abbruch mehr an dieser Stelle (vor Punkt 52
    # `raise SystemExit(... pass --overwrite)`): der Selbst-Ueberspringer
    # oben hat bereits entschieden, ob ein Neulauf noetig ist - wer bis
    # hierher kommt, WILL neu rechnen (geaenderter Fingerabdruck,
    # --overwrite, oder ein Teillauf per --noe-limit-files), und genau das
    # ist der Zweck von "make all laeuft wiederholt ohne manuelles
    # Eingreifen" (Punkt 52). Ein zusaetzlicher, manueller --overwrite waere
    # hier ein Widerspruch zum Selbst-Ueberspringer, keine zusaetzliche
    # Sicherheit.
    t0 = time.time()
    summary = Summary()
    lookup = NsLookup(symbol_csv)
    writer = GeoParquetBatchWriter(output_path, args.batch_size, args.compression)
    try:
        export_noe_dxf(
            noe_dxf_zip=noe_dxf_zip,
            noe_line_layers=args.noe_line_layers,
            noe_limit_files=args.noe_limit_files,
            noe_tile_size_m=args.noe_tile_size_m,
            noe_tile_halo_m=args.noe_tile_halo_m,
            noe_precision_m=args.noe_precision_m,
            noe_min_area_m2=args.noe_min_area_m2,
            lookup=lookup,
            writer=writer,
            summary=summary,
        )
    finally:
        writer.close()

    runtime_s = time.time() - t0
    write_summary_csv(summary, summary_csv)
    limit_notes = [f"NOE DXF limited to {args.noe_limit_files} DXF files."] if args.noe_limit_files else []
    write_overview_md(summary, overview_md, output_path, runtime_s, limit_notes=limit_notes)
    print(f"wrote {output_path} rows={writer.row_count}", flush=True)
    print(f"wrote {summary_csv}", flush=True)
    print(f"wrote {overview_md}", flush=True)

    # Fingerabdruck erst nach erfolgreichem Schreiben (Entscheidung (c),
    # PLAN.md §5): b_export_parquet prüft damit, ob diese Stufe seither neu
    # gelaufen ist.
    if not args.noe_limit_files:
        fingerprint.write(PREP_DIR, [noe_dxf_zip, symbol_csv])
    else:
        print(
            "Fingerabdruck NICHT geschrieben: --noe-limit-files ist gesetzt "
            "(Smoke-Test/Teillauf) - ein voller Lauf ohne dieses Flag muss "
            "den Fingerabdruck erst herstellen, bevor b_export_parquet ihn "
            "als vollständig ansehen darf.",
            flush=True,
        )


if __name__ == "__main__":
    main()
