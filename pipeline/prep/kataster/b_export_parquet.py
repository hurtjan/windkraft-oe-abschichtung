#!/usr/bin/env python3
"""Prep Kataster, Stufe b: SHP-Export der acht Bundesländer + Zusammenführung
mit Stufe a (docs/rewrite/PLAN.md §4/§7, Paket W1.P2).

Liest die acht DKM-SHP-Archive (Burgenland, Kärnten, Oberösterreich,
Salzburg, Steiermark, Tirol, Vorarlberg, Wien) direkt aus
``contract.RAW["kataster"]`` und übernimmt das Ergebnis von
``a_noe_polygonize`` unverändert (ohne die DXF-Polygonisierung zu
wiederholen - genau die Trennung, die PLAN.md §4 für diese Domäne nennt:
"billigerer Parquet-Export" getrennt von der teuren NÖ-Rekonstruktion).
Schreibt das kombinierte GeoParquet - Feldschema identisch zum bisherigen
``output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet`` - unter
``contract.PREP["kataster"]["b_export_parquet"]``.

Verschoben, unverändert in der Verarbeitungslogik, aus
``scripts/preprocessing/export_at_dkm_geoparquet.py`` (``main``/
``export_shp_archives`` liegen jetzt in ``pipeline.prep.kataster.common``,
von hier importiert).

Harte Vorbedingung statt stillem Fallback (PLAN.md §4 Prep-Beschreibung):
bricht ab, wenn Stufe a noch nicht gelaufen ist - anders als das
Originalskript, das NÖ bei fehlendem Archiv nur mit einer Notiz überging.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from pipeline import contract, fingerprint, runtime
from pipeline.prep.kataster.a_noe_polygonize import DEFAULT_OUTPUT as NOE_STAGE_OUTPUT
from pipeline.prep.kataster.a_noe_polygonize import PREP_DIR as NOE_STAGE_DIR
from pipeline.prep.kataster.common import (
    DEFAULT_SHP_ARCHIVES,
    FIELD_NAMES,
    GeoParquetBatchWriter,
    NsLookup,
    Summary,
    export_shp_archives,
    write_overview_md,
    write_summary_csv,
)

PREP_DIR = contract.PREP["kataster"]["b_export_parquet"]
# Gleicher Dateiname wie das bisherige Ziel (output/kataster/…) - nur der
# Ort hat sich geändert (PLAN.md §8 Regel 2: Prep-Ausgaben liegen unter
# build/prep/, nicht mehr unter output/).
DEFAULT_OUTPUT = PREP_DIR / "at_dkm_gst_nfl_epsg31287.geoparquet"
DEFAULT_SUMMARY_CSV = PREP_DIR / "at_dkm_gst_nfl_epsg31287_summary.csv"
DEFAULT_OVERVIEW_MD = PREP_DIR / "at_dkm_gst_nfl_epsg31287_overview.md"


def copy_noe_rows(source_path: Path, writer: GeoParquetBatchWriter, summary: Summary) -> int:
    """Kopiert die von a_noe_polygonize geschriebenen Zeilen unverändert in
    ``writer`` - Tabellen-Batches werden direkt durchgereicht (Schema
    identisch, siehe common.FIELD_NAMES), keine erneute Geometriebereinigung
    oder WKB-Neuserialisierung. Zählt für die eigene Summary nur
    Feature-Counts (bundesland/source_layer/source_crs) mit; Flächen-,
    Bounds- und Bereinigungsstatistik der NÖ-Zeilen stehen bereits in der
    Summary-CSV von a_noe_polygonize - hier nicht dupliziert."""
    pf = pq.ParquetFile(source_path)
    copied = 0
    count_columns = ["bundesland", "source_layer", "source_crs"]
    for batch in pf.iter_batches(batch_size=writer.batch_size, columns=FIELD_NAMES):
        # Zählspalten separat und ohne Geometrie in Pandas wandeln - billiger
        # als batch.to_pandas() über alle 17 Spalten inkl. WKB-Bytes.
        counts_df = pa.Table.from_batches([batch], schema=writer.schema).select(count_columns).to_pandas()
        for (bundesland, source_layer, source_crs), count in (
            counts_df.groupby(count_columns, dropna=False).size().items()
        ):
            summary.feature_counts[(bundesland, source_layer, source_crs or "")] += int(count)

        table = pa.Table.from_batches([batch], schema=writer.schema)
        writer.write_table(table)
        copied += table.num_rows
    return copied


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT), help="GeoParquet output path")
    ap.add_argument("--summary-csv", default=str(DEFAULT_SUMMARY_CSV), help="CSV summary output path")
    ap.add_argument("--overview-md", default=str(DEFAULT_OVERVIEW_MD), help="Markdown overview output path")
    ap.add_argument("--layers", default="GST_V2,NFL_V2", help="Comma-separated SHP layers to export")
    ap.add_argument("--only-bundesland", default="", help="Comma-separated subset of SHP Bundesland names")
    ap.add_argument("--max-inner-zips-per-archive", type=int, default=0, help="Smoke-test limit per SHP archive")
    ap.add_argument("--skip-shp", action="store_true", help="Skip SHP archives")
    ap.add_argument("--skip-noe", action="store_true", help="Skip copying stage-a NOE rows (smoke test only)")
    ap.add_argument("--noe-stage-output", default=str(NOE_STAGE_OUTPUT), help="GeoParquet written by a_noe_polygonize")
    ap.add_argument("--batch-size", type=int, default=50_000, help="Rows per Parquet write batch")
    ap.add_argument("--compression", default="zstd", help="Parquet compression codec")
    ap.add_argument("--temp-dir", default=None, help="Optional temp directory for extracting inner SHP ZIPs")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite output files if they exist")
    args = ap.parse_args()

    output_path = runtime.ensure_parent(Path(args.output))
    summary_csv = Path(args.summary_csv)
    overview_md = Path(args.overview_md)
    noe_stage_output = Path(args.noe_stage_output)
    symbol_csv = contract.RAW["kataster"]["symbol_csv"]
    shp_inputs = [contract.RAW["kataster"][archive.raw_key] for archive in DEFAULT_SHP_ARCHIVES]

    # Selbst-Ueberspringer, gleiches Muster wie pipeline/prep/osm.py
    # (run_extract/run_layers): ein wiederholter `make all` ohne
    # Eingabeaenderung soll diese Stufe nicht neu rechnen, statt hart
    # abzubrechen (Punkt 52, docs/rewrite/PLAN.md). Nur auf einem
    # vollstaendigen Lauf (keine der Teillauf-Flags) - ein Teillauf schreibt
    # ohnehin keinen Fingerabdruck (siehe unten).
    full_run = not (args.only_bundesland or args.max_inner_zips_per_archive or args.skip_shp or args.skip_noe)
    if (
        not args.overwrite
        and full_run
        and output_path.exists()
        and summary_csv.exists()
        and overview_md.exists()
        and fingerprint.matches(PREP_DIR, [*shp_inputs, symbol_csv, noe_stage_output])
    ):
        print(f"[skip]  prep-kataster-b: Fingerabdruck unveraendert -> {output_path}", flush=True)
        return

    # Kein "already exists"-Abbruch mehr an dieser Stelle (vor Punkt 52
    # `raise SystemExit(... pass --overwrite)`): der Selbst-Ueberspringer
    # oben hat bereits entschieden, ob ein Neulauf noetig ist - wer bis
    # hierher kommt, WILL neu rechnen (geaenderter Fingerabdruck,
    # --overwrite, oder ein Teillauf), und genau das ist der Zweck von
    # "make all laeuft wiederholt ohne manuelles Eingreifen" (Punkt 52). Ein
    # zusaetzlicher, manueller --overwrite waere hier ein Widerspruch zum
    # Selbst-Ueberspringer, keine zusaetzliche Sicherheit.

    if not args.skip_noe and not noe_stage_output.exists():
        raise SystemExit(
            f"Stufe a (a_noe_polygonize) ist noch nicht gelaufen - {noe_stage_output} fehlt. "
            "Harte Vorbedingung (docs/rewrite/PLAN.md §4): erst `prep-kataster-a`, dann diese "
            "Stufe. Mit --skip-noe testweise ohne NÖ-Zeilen exportieren."
        )
    if not args.skip_noe and not fingerprint.matches(
        NOE_STAGE_DIR, [contract.RAW["kataster"]["noe_dxf_zip"], contract.RAW["kataster"]["symbol_csv"]]
    ):
        print(
            "WARN: Fingerabdruck von Stufe a passt nicht mehr zu den aktuellen NÖ-Eingaben "
            "(fehlender oder veralteter Fingerabdruck, z.B. von einem --noe-limit-files-Lauf). "
            "b_export_parquet kopiert trotzdem die vorhandene Datei durch, aber sie ist "
            "möglicherweise nicht vollständig/aktuell.",
            flush=True,
        )

    t0 = time.time()
    summary = Summary()
    lookup = NsLookup(symbol_csv)
    writer = GeoParquetBatchWriter(output_path, args.batch_size, args.compression)
    try:
        if not args.skip_shp:
            export_shp_archives(
                only_bundesland=args.only_bundesland,
                layers=args.layers,
                max_inner_zips_per_archive=args.max_inner_zips_per_archive,
                temp_dir=args.temp_dir,
                lookup=lookup,
                writer=writer,
                summary=summary,
            )
        if not args.skip_noe:
            copied = copy_noe_rows(noe_stage_output, writer, summary)
            print(f"copied {copied} NOE rows from stage a ({noe_stage_output})", flush=True)
    finally:
        writer.close()

    runtime_s = time.time() - t0
    write_summary_csv(summary, summary_csv)
    limit_notes = []
    if args.max_inner_zips_per_archive:
        limit_notes.append(f"SHP limited to {args.max_inner_zips_per_archive} inner ZIPs per archive.")
    if args.only_bundesland:
        limit_notes.append(f"SHP limited to bundesland subset: {args.only_bundesland}.")
    if args.skip_noe:
        limit_notes.append("NOE rows from stage a were skipped (--skip-noe).")
    write_overview_md(summary, overview_md, output_path, runtime_s, limit_notes=limit_notes)
    print(f"wrote {output_path} rows={writer.row_count}", flush=True)
    print(f"wrote {summary_csv}", flush=True)
    print(f"wrote {overview_md}", flush=True)

    if not args.only_bundesland and not args.max_inner_zips_per_archive and not args.skip_shp and not args.skip_noe:
        fingerprint.write(PREP_DIR, [*shp_inputs, symbol_csv, noe_stage_output])
    else:
        print(
            "Fingerabdruck NICHT geschrieben: Teillauf (--only-bundesland / "
            "--max-inner-zips-per-archive / --skip-shp / --skip-noe gesetzt).",
            flush=True,
        )


if __name__ == "__main__":
    main()
