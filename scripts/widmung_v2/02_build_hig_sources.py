"""Häuser-im-Grünen-Quellen v2 aus amtlichen Daten (Plan Phase 1).

Ersetzt den OSM-Adress-Cluster-Pfad der v1-Pipeline durch Flächenwidmung +
NÖ-SekROP-PDF-Zonen + DKM-Kataster + BEV-Adressregister. Ablauf siehe
windkraft/calc/hig_detection.py (Stufen A-C).

Geschriebene Checkpoint-Raster (25 m, Pipeline-Lattice):

  official_settlement_source     amtl. Wohnbauland/Mischnutzung, 9 BL
  ferienhaus_tourismus_source    Ferienhaus-/Tourismusgebiete (eigene 750-m-Kategorie)
  official_hig_source            amtl. HiG-Widmung ohne Ferienhaus
  noe_pdf_750m_zones             NÖ-SekROP-Zonen, BEREITS Objekt + 750 m (nur
                                 Kandidatenfilter/Abdeckung, kein Quellband)
  noe_pdf_hig_source             rekonstruierte SekROP-QUELLOBJEKTE (Erosion
                                 um 750−50 m); Puffer entsteht im Aggregat
  hig_hulls_source               STREUSIEDLUNGS-Hüllen: bewohnt UND >= 5
                                 adressierte Objekte, 200-m-Verkettung (750 m)
  bewohnt_einzellage_source      bewohnte Hüllen UNTER der Schwelle (25 m) -
                                 bewusste Politikentscheidung, siehe Knie-Analyse
  nonresidential_hulls_source    industriegebietartige + unbewohnte Hüllen (25 m)

Dazu output/<out-dir>/hig_huellen.gpkg mit einer Zeile je Hülle (klasse,
ist_streusiedlung, n_bauflaechen, n_adressen, n_bev, wohnanteil, area_ha,
bundesland).

Run:  uv run python scripts/main/build_hig_sources.py
      uv run python scripts/main/build_hig_sources.py --bl Burgenland --bbox ...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windkraft.config import load_config  # noqa: E402
from windkraft.calc.abschichtung_common import (  # noqa: E402
    HIG_ADDRESS_RADIUS_M,
    HIG_CHAIN_M,
    HIG_FILTER_BUFFER_M,
    HIG_GARDEN_RADIUS_M,
    HIG_INDUSTRIE_WIDMUNG_MIN_SHARE,
    HIG_MAX_FOOTPRINT_M2,
    HIG_MIN_ADRESSEN,
    HIG_WOHNANTEIL_MIN_SHARE,
    ensure_group_layers,
    load_grid,
    timed,
)
from windkraft.calc.bev_register import load_address_points, load_building_points  # noqa: E402
from windkraft.calc.hig_detection import (  # noqa: E402
    HULL_CLASS_BEWOHNT,
    HULL_CLASS_INDUSTRIE,
    HULL_CLASS_UNBEWOHNT,
    aggregate_hulls,
    build_hulls,
    building_signals,
    class_masks,
    dominant_bundesland,
    hull_polygons,
    label_mask,
    sample_labels,
    scan_dkm_candidates,
)
from windkraft.calc.streusiedlung import chain_hull_params  # noqa: E402
from windkraft.calc.hig_source_masks import (  # noqa: E402
    candidate_filter_mask,
    noe_pdf_mask,
    noe_pdf_source_mask,
    widmung_seed,
    zoning_masks,
)

SOURCE_LAYER_NAMES = [
    "official_settlement_source",
    "ferienhaus_tourismus_source",
    "official_hig_source",
    "noe_pdf_750m_zones",
    "noe_pdf_hig_source",
    "hig_hulls_source",
    "bewohnt_einzellage_source",
    "nonresidential_hulls_source",
]

HULL_GPKG_NAME = "hig_huellen.gpkg"


def build_sources(cfg: dict, grid: dict, args: argparse.Namespace) -> dict[str, np.ndarray]:
    """Stufen A-C; gibt die Checkpoint-Masken zurück und schreibt hig_huellen.gpkg."""
    zoning_dir = Path(args.zoning_dir)
    with timed("Stufe A: Widmungsmasken"):
        zoning = zoning_masks(zoning_dir, grid)
        noe_pdf = noe_pdf_mask(Path(args.noe_dir), grid)
        noe_pdf_source = noe_pdf_source_mask(Path(args.noe_dir), grid)

    with timed(f"Stufe A: Kandidaten-Filter (+{args.filter_buffer_m:g} m)"):
        # NÖ-PDF-Zonen sind schon 750-m-Zonen; sie filtern ohne weitere Aufweitung.
        filter_mask = candidate_filter_mask(zoning, noe_pdf, args.filter_buffer_m, grid)
        print(
            f"[info]  Filter: Widmung {int(widmung_seed(zoning).sum()):,} Zellen -> "
            f"{int(filter_mask.sum()):,} Filterzellen (inkl. NÖ-PDF)",
            flush=True,
        )

    bl_filter = set(args.bl) if args.bl else None
    hull_dilate_m, hull_erode_m = chain_hull_params(args.chain_m)
    with timed("Stufe B: DKM-Scan"):
        scan = scan_dkm_candidates(
            Path(args.dkm_parquet), grid, filter_mask, args.max_footprint_m2, bl_filter=bl_filter,
            margin_m=hull_dilate_m,
        )
        print(
            f"[info]  Bauflächen {scan.n_buildings_total:,} | gefiltert {scan.n_filtered:,} "
            f"({100 * scan.n_filtered / max(scan.n_buildings_total, 1):.1f}%) | "
            f"Kandidaten {len(scan):,} | >1ha-Fix {scan.n_oversized:,} | "
            f"Garten-Punkte {len(scan.garden_xy):,}",
            flush=True,
        )

    with timed(f"Stufe B: Hüllenbildung ({args.chain_m:g}-m-Verkettung)"):
        hull_mask, labels, n_labels = build_hulls(
            scan.geometries, grid, hull_dilate_m, hull_erode_m,
        )
        print(f"[info]  Hüllen: {n_labels:,} ({int(hull_mask.sum()):,} Zellen)", flush=True)

    with timed("Stufe C: Signale + Klassifikation"):
        address_dir = Path(args.address_dir)
        address_xy = load_address_points(address_dir, cache_dir=Path(args.cache_dir))
        bev_buildings = load_building_points(address_dir, cache_dir=Path(args.cache_dir))
        signals = building_signals(
            scan, address_xy, bev_buildings, args.address_radius_m, args.garden_radius_m,
            industrie_widmung_mask=zoning["industrie_negativ"], grid=grid,
        )
        hull_label = sample_labels(labels, scan.centroids, grid)
        hull_frame = aggregate_hulls(
            hull_label, signals, n_labels,
            args.wohnanteil_min_share, args.industrie_widmung_min_share,
        )
        # Streusiedlungs-Regel (Knie-Analyse): bewohnte Hüllen mit >= min_adressen
        # adressierten Objekten sind GEBIETE (750 m); bewohnte darunter sind
        # Einzellagen und werden als eigene Klasse ausgewiesen (25 m) - sichtbar,
        # nicht stillschweigend verworfen.
        ist_bewohnt = hull_frame["klasse"].eq(HULL_CLASS_BEWOHNT)
        ist_streusiedlung = ist_bewohnt & (hull_frame["n_adressen"] >= args.min_adressen)
        hull_frame["ist_streusiedlung"] = ist_streusiedlung.astype(np.int8)
        counts = hull_frame["klasse"].value_counts().to_dict()
        print(
            f"[info]  Klassen: bewohnt={counts.get(HULL_CLASS_BEWOHNT, 0):,} "
            f"(davon Streusiedlung={int(ist_streusiedlung.sum()):,}, "
            f"Einzellage={int((ist_bewohnt & ~ist_streusiedlung).sum()):,}), "
            f"industriegebietartig={counts.get(HULL_CLASS_INDUSTRIE, 0):,}, "
            f"unbewohnt={counts.get(HULL_CLASS_UNBEWOHNT, 0):,}",
            flush=True,
        )

    streusiedlung_mask = label_mask(
        labels, hull_frame.loc[ist_streusiedlung, "label"].to_numpy(), n_labels)
    einzellage_mask = label_mask(
        labels, hull_frame.loc[ist_bewohnt & ~ist_streusiedlung, "label"].to_numpy(), n_labels)
    masks = class_masks(labels, hull_frame, n_labels)

    if not args.skip_gpkg:
        with timed("Hüllen-GPKG schreiben"):
            hulls = hull_polygons(labels, hull_mask, hull_frame, grid)
            if not hulls.empty:
                hulls["bundesland"] = dominant_bundesland(hull_label, scan.bundesland, hulls["label"].to_numpy())
            out_path = Path(args.out_dir) / HULL_GPKG_NAME
            out_path.parent.mkdir(parents=True, exist_ok=True)
            hulls.to_file(out_path, driver="GPKG", layer="hig_huellen")
            print(f"Wrote {out_path}: {len(hulls):,} Hüllen", flush=True)

    return {
        "official_settlement_source": zoning["official_settlement_source"],
        "ferienhaus_tourismus_source": zoning["ferienhaus_tourismus_source"],
        "official_hig_source": zoning["official_hig_source"],
        "noe_pdf_750m_zones": noe_pdf,
        "noe_pdf_hig_source": noe_pdf_source,
        "hig_hulls_source": streusiedlung_mask,
        "bewohnt_einzellage_source": einzellage_mask,
        "nonresidential_hulls_source": masks[HULL_CLASS_INDUSTRIE] | masks[HULL_CLASS_UNBEWOHNT],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Häuser-im-Grünen-Quellen v2 aus Widmung + DKM + BEV-Adressregister.")
    p.add_argument("--config", default="config.json")
    # v2-Zoning-Verzeichnis (8 BL inkl. Burgenland + industrie_negativ-Bucket).
    # Das v1-Verzeichnis output/abschichtung_widmung/zoning_vectors wäre ein
    # stiller Fehler: schwächerer Filter, keine Industrie-Negativmaske.
    p.add_argument("--zoning-dir", default="output/abschichtung_widmung_v2/zoning_vectors", help="Output von build_official_zoning_layers.py")
    p.add_argument("--noe-dir", default="output/noe", help="Verzeichnis der pdf_750m_*.geojson")
    p.add_argument("--dkm-parquet", default="output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet")
    p.add_argument("--address-dir", default="data/adressregister")
    p.add_argument("--cache-dir", default="output/adressregister_cache", help="Ablage der BEV-Parquet-Caches")
    p.add_argument("--layer-dir", default="output/abschichtung_widmung_v2/distance_layers")
    p.add_argument("--out-dir", default="output/abschichtung_widmung_v2")
    p.add_argument("--bbox", default=None, help="EPSG:31287 bbox minx,miny,maxx,maxy für Smoke-Tests")
    p.add_argument("--bl", action="append", default=None, help="Nur diese Bundesländer scannen (wiederholbar)")
    p.add_argument("--filter-buffer-m", type=float, default=HIG_FILTER_BUFFER_M)
    p.add_argument("--chain-m", type=float, default=HIG_CHAIN_M,
                   help="Verkettungsdistanz des Closings (Knie-Analyse: 200 m)")
    p.add_argument("--min-adressen", type=int, default=HIG_MIN_ADRESSEN,
                   help="Streusiedlungs-Schwelle: adressierte Objekte je bewohnter Hülle")
    p.add_argument("--address-radius-m", type=float, default=HIG_ADDRESS_RADIUS_M)
    p.add_argument("--garden-radius-m", type=float, default=HIG_GARDEN_RADIUS_M)
    p.add_argument("--max-footprint-m2", type=float, default=HIG_MAX_FOOTPRINT_M2)
    p.add_argument("--wohnanteil-min-share", type=float, default=HIG_WOHNANTEIL_MIN_SHARE)
    p.add_argument("--industrie-widmung-min-share", type=float, default=HIG_INDUSTRIE_WIDMUNG_MIN_SHARE)
    p.add_argument("--force-layers", action="store_true")
    p.add_argument("--skip-gpkg", action="store_true", help="Nur Raster-Checkpoints, kein hig_huellen.gpkg")
    return p.parse_args(argv)


def _params_tag(args: argparse.Namespace) -> dict[str, str]:
    return {
        "HIG_FILTER_BUFFER_M": f"{args.filter_buffer_m:g}",
        "HIG_CHAIN_M": f"{args.chain_m:g}",
        "HIG_MIN_ADRESSEN": str(args.min_adressen),
        # Input-Provenienz: ohne diesen Tag würde ein Lauf gegen das falsche
        # Zoning-Verzeichnis (z. B. v1 statt v2) als "aktuell" durchgehen.
        "HIG_ZONING_DIR": str(args.zoning_dir),
        "HIG_ADDRESS_RADIUS_M": f"{args.address_radius_m:g}",
        "HIG_GARDEN_RADIUS_M": f"{args.garden_radius_m:g}",
        "HIG_MAX_FOOTPRINT_M2": f"{args.max_footprint_m2:g}",
        "HIG_WOHNANTEIL_MIN_SHARE": f"{args.wohnanteil_min_share:g}",
        "HIG_INDUSTRIE_WIDMUNG_MIN_SHARE": f"{args.industrie_widmung_min_share:g}",
    }


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    with timed("load config/grid"):
        cfg = load_config(args.config)
        grid = load_grid(cfg, args.bbox)
    layer_dir = Path(args.layer_dir)
    tags = _params_tag(args)

    def _tags_ok(existing: dict) -> bool:
        return all(existing.get(k) == v for k, v in tags.items())

    with timed("build/update HiG checkpoint layers"):
        ensure_group_layers(
            layer_dir,
            SOURCE_LAYER_NAMES,
            "Häuser-im-Grünen-Quellen v2",
            lambda: build_sources(cfg, grid, args),
            grid,
            args.force_layers,
            extra_ok=_tags_ok,
            extra_tags=tags,
        )
    print(f"Checkpoint layers updated in {layer_dir}.")


if __name__ == "__main__":
    main()
