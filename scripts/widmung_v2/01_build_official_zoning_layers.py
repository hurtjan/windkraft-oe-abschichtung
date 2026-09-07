"""Merge official per-Bundesland Flächenwidmung sources into three combined vector
layers for the Widmung-based Abschichtung pipeline (script 1 of 3, see
scripts/main/build_widmung_osm_layers.py /
scripts/main/build_widmung_v2_layers.py and the create_*_distance_zones scripts):

  wohn_misch_combined.gpkg         - gewidmetes Wohnbauland + Mischnutzung, 9 BL
  haeuser_im_gruenen_combined.gpkg - Hofstellen, Camping, Golf, Kleingarten und
                                     Ferienhaus-/Tourismusgebiete, 9 BL
  industrie_negativ_combined.gpkg  - Betriebs-/Industriegebiete, 9 BL

Alle 9 Bundesländer haben eine Quelle (siehe windkraft/calc/widmung_sources.py,
DATASETS); Wien liefert seit 2026-07-29 die generalisierte Flächenwidmung
(WFS ogdwien:GENFLWIDMUNGOGD, 26.419 Flächen) und wird wie die anderen acht
Bundesländer über die Kategorien-Registry in wohn_misch/haeuser_im_gruenen/
industrie_negativ eingeordnet - kein Ganzflächen-Ausschluss mehr.

Der dritte Bucket `industrie_negativ` ist **kein eigener Ausschluss**, sondern eine
Negativmaske: er verhindert in scripts/main/build_hig_sources.py, dass
industriegebietartige Gebäude-Hüllen als "bewohnt" (750 m) eingestuft werden.

Die Quellen-Registry (Pfade, Spalten, Kategorienzuordnung) liegt in
windkraft/calc/widmung_sources.py und wird von
scripts/analysis/audit_bauland_kategorien.py mitgelesen - eine Kategorie kann
daher nicht hier zugeordnet und dort unbekannt sein.

Steiermarks Grünland-/Freizeit-Codes (afg/klg/Ca) stecken nicht in
data/widmung/steiermark/Bauland.zip (nur Bauland) - dafür wird
zusätzlich data/widmung/steiermark/Flaewi.shp.zip gelesen (Layer FWP_NUTZ,
EPSG:4258, 645k Features, ~410MB - die einzige Ausnahme von der sonstigen
data/widmung-only-Regel für diese Pipeline). Wohn/Misch für die Steiermark
kommt weiterhin aus Bauland.zip.

Jede Quelle wird NICHT dissolved: rasterize() (Script 3) behandelt überlappende/
angrenzende Polygone identisch vor und nach einem dissolve, ein dissolve hier
würde also nur Zeit kosten und die Pro-Feature-Provenienz (bundesland/
source_layer/category) verlieren.

Run:  uv run python scripts/main/build_official_zoning_layers.py
Output: output/abschichtung_widmung_v2/zoning_vectors/{wohn_misch,haeuser_im_gruenen,industrie_negativ}_combined.gpkg

Der Default zeigt auf die v2-Kette (die Referenzkarte). Für die alte v1-Kette
muss `--out-dir output/abschichtung_widmung/zoning_vectors` gesetzt werden - das
ist der Ordner, aus dem build_widmung_osm_layers.py liest. Die beiden Ketten
teilen sich dieses Skript, aber nicht ihre Ordner; ein Lauf in den falschen
Ordner ist genau der Fehler, der in der v2-Entwicklung einen stillen
Schwachfilter-Lauf verursacht hat (578k statt 254k Kandidaten).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windkraft.calc.widmung_sources import (  # noqa: E402
    BUCKETS,
    DATASETS,
    WORK_CRS,
    bundesland_of,
    read_dataset,
    source_mask,
    sources_for_dataset,
)

OUT_DIR = PROJECT_ROOT / "output" / "abschichtung_widmung_v2" / "zoning_vectors"

EMPTY_COLUMNS = {"bundesland": [], "source_layer": [], "category": []}


def build_all_buckets(cache_dir: Path, bl_filter: set[str] | None = None,
                      buckets: tuple[str, ...] = BUCKETS) -> dict[str, gpd.GeoDataFrame]:
    """Materialize every requested bucket in ONE pass over the datasets.

    Iterating datasets (not sources) keeps each OGD file to a single read even
    though e.g. Oberösterreich feeds seven different source entries across all
    three buckets - the previous per-source reader opened that 138 MB shapefile
    once per entry.
    """
    frames: dict[str, list[gpd.GeoDataFrame]] = {b: [] for b in buckets}
    for dataset_key in DATASETS:
        wanted = [s for s in sources_for_dataset(dataset_key, bl_filter=bl_filter) if s["bucket"] in buckets]
        if not wanted:
            continue
        gdf = read_dataset(dataset_key, cache_dir)
        for src in wanted:
            selected = gdf[source_mask(gdf, src)]
            if selected.empty:
                print(f"[warn]  {src['key']}: source filter returned no features")
                continue
            frame = gpd.GeoDataFrame(geometry=selected.geometry.reset_index(drop=True), crs=WORK_CRS)
            frame["bundesland"] = bundesland_of(src)
            frame["source_layer"] = src["key"]
            frame["category"] = src["category"]
            frames[src["bucket"]].append(frame)
            print(f"[{src['key']}] {bundesland_of(src)} / {src['category']}: {len(frame):,} Flächen")

    out: dict[str, gpd.GeoDataFrame] = {}
    for bucket, parts in frames.items():
        if parts:
            out[bucket] = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs=WORK_CRS)
        else:
            out[bucket] = gpd.GeoDataFrame(dict(EMPTY_COLUMNS), geometry=[], crs=WORK_CRS)
    return out


def write_bucket(gdf: gpd.GeoDataFrame, path: Path, layer_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, layer=layer_name, driver="GPKG")
    km2 = gdf.geometry.area.sum() / 1e6
    print(f"Wrote {path} (layer {layer_name}): {len(gdf):,} Flächen, {km2:,.1f} km²")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge official Bundesland Flächenwidmung sources into wohn_misch + haeuser_im_gruenen + industrie_negativ combined layers.")
    p.add_argument("--out-dir", default=str(OUT_DIR))
    p.add_argument("--cache-dir", default=None, help="Local extract cache (Kärnten GPKG). Default: <out-dir>/_cache")
    p.add_argument("--bl", action="append", default=None, help="Restrict to one Bundesland (repeatable). Default: all 8.")
    p.add_argument("--bucket", choices=list(BUCKETS), default=None, help="Restrict to one bucket. Default: all three.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    cache_dir = Path(args.cache_dir) if args.cache_dir else out_dir / "_cache"
    bl_filter = set(args.bl) if args.bl else None
    buckets = (args.bucket,) if args.bucket else BUCKETS
    built = build_all_buckets(cache_dir, bl_filter, buckets)
    for bucket in buckets:
        write_bucket(built[bucket], out_dir / f"{bucket}_combined.gpkg", bucket)


if __name__ == "__main__":
    main()
