#!/usr/bin/env python3
"""Kennzahlen der Widmungs-Abschichtung v2 als JSON für das Dashboard.

Ein einziger Durchlauf über das v2-GeoTIFF liefert **alle** Zahlen, die das
Dashboard braucht:

  * Fläche je Band (alle 63) — exakt, nicht über Übersichtspyramiden geschätzt
  * dieselbe Fläche zusätzlich je Bundesland (63 × 9 Matrix)
  * **marginale** Ausschlussfläche je Kriterium und die 3er-Überschneidung
    Mensch/Natur/Geographie

Warum ein gemeinsamer Durchlauf: ein voller Band-Pass kostet auf dieser Datei
~37 s. Bandweise gelesen wären das ~40 min. `src.read(window=...)` ohne
Bandindex liefert pro Kachel *alle* Bänder auf einmal, und mit einem einmal
gerasterten Bundesland-Id-Raster fällt die BL-Aufschlüsselung im selben Pass
ohne zusätzliche I/O an.

Warum *marginale* Flächen: die Ausschlussgruppen überlappen stark (Summe der
drei Gruppen 120.792 km², Vereinigung nur 79.939 km²). Ein gestapeltes
Diagramm der Bruttoflächen würde eine Additivität behaupten, die es nicht
gibt. Die marginale Fläche — was ein Kriterium als **einziges** sperrt — ist
die Zahl, die die planerische Frage beantwortet: was gäbe dieses Kriterium
frei, wenn man es fallen ließe.

Run:  uv run python scripts/analysis/build_v2_dashboard_data.py
Out:  output/abschichtung_widmung_v2/dashboard_data.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from windkraft.calc.abschichtung_common import admin_boundaries  # noqa: E402
from windkraft.config import load_config  # noqa: E402

# Referenzwerte der Energiewerkstatt/IG-Windkraft-Studie 2023, identisch zu
# scripts/analysis/compare_widmung_with_study.py und docs/studienvergleich.md.
STUDY_KM2 = {
    "Burgenland": 359.0, "Kärnten": 190.0, "Niederösterreich": 1161.0,
    "Oberösterreich": 183.0, "Salzburg": 75.0, "Steiermark": 550.0,
    "Tirol": 79.0, "Vorarlberg": 31.0, "Wien": 2.0,
}
STUDY_MW = {
    "Burgenland": 6291, "Kärnten": 3329, "Niederösterreich": 20366,
    "Oberösterreich": 3210, "Salzburg": 1319, "Steiermark": 9646,
    "Tirol": 1382, "Vorarlberg": 550, "Wien": 38,
}
# Leistungsdichte der Studie (MW/km²) — das Projekt rechnet mit einem eigenen,
# höheren Wert aus config.json; das Dashboard zeigt beide.
STUDY_MW_PER_KM2 = 17.54

# Die Bänder, die tatsächlich sperren, gruppiert wie exclusion_human /
# _nature / _geography. Quell-Bänder (…_source) sind bewusst nicht dabei —
# gesperrt wird der Puffer, nicht das Objekt.
EXCLUSION_LAYERS = {
    "human": [
        ("settlement_v2_buffer", "Amtliche Siedlung (1.000–1.500 m)"),
        ("haeuser_im_gruenen_v2_buffer", "Häuser im Grünen / Streusiedlung (750 m)"),
        ("ferienhaus_tourismus_buffer", "Ferienhaus / Tourismus"),
        ("bewohnt_einzellage_buffer", "Bewohnte Einzellage (25 m)"),
        ("nonresidential_hulls_buffer", "Nicht-Wohn-Hülle (25 m)"),
        ("cableway_buildings_buffer", "Seilbahn-Gebäude"),
        ("general_buildings_buffer", "Sonstige Gebäude"),
        ("wien_full_exclusion", "Wien (amtliche Widmung)"),
        ("power_380_400kv", "380/400-kV-Leitung"),
        ("road_motorway_trunk", "Autobahn / Schnellstraße"),
        ("road_federal_state", "Bundes- / Landesstraße"),
        ("rail_main", "Hauptbahn"),
        ("cableway_people_150m", "Personenseilbahn (150 m)"),
        ("military_restricted_area", "Militärisches Sperrgebiet"),
        ("airport_area", "Flughafenfläche"),
        ("airport_lateral_check_6km", "Flughafen-Umfeld (6 km)"),
    ],
    "nature": [
        ("nature_protection_areas", "Naturschutzgebiete (amtlich)"),
        ("osm_nature_protection_areas", "Naturschutzgebiete (OSM)"),
    ],
    "geography": [
        ("geography_wind_too_low", "Windhöffigkeit zu gering"),
        ("geography_slope_too_steep", "Hangneigung zu steil"),
        ("geography_elevation_too_high", "Seehöhe zu hoch"),
    ],
}
GROUP_LABELS = {"human": "Mensch", "nature": "Natur", "geography": "Geographie"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default="config/config.json")
    p.add_argument("--tif", default="output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2.tif")
    p.add_argument("--out", default="output/abschichtung_widmung_v2/dashboard_data.json")
    return p.parse_args()


def bundesland_id_raster(cfg: dict, src: rasterio.DatasetReader) -> tuple[np.ndarray, list[str]]:
    """Vollauflösendes uint8-Raster mit 1..9 je Bundesland, 0 = außerhalb.

    Einmal gerastert statt kachelweise: 24001 × 14001 uint8 sind 336 MB, das
    ist deutlich billiger als 5.170 einzelne `rasterize`-Aufrufe.
    """
    admin = admin_boundaries(cfg, None)
    admin = admin[admin.geometry.notnull() & ~admin.geometry.is_empty].copy()
    admin = admin.to_crs("EPSG:31287")
    if "BL" not in admin.columns:
        raise SystemExit("Admin-Layer hat keine BL-Spalte")
    admin = admin.dissolve(by="BL", as_index=False)[["BL", "geometry"]].sort_values("BL")

    names = [str(v) for v in admin["BL"]]
    shapes = [(geom, i) for i, geom in enumerate(admin.geometry, 1)]
    ids = rasterize(shapes, out_shape=(src.height, src.width), transform=src.transform,
                    fill=0, dtype="uint8", all_touched=False)
    return ids, names


def scan_bands(src: rasterio.DatasetReader, bl_ids: np.ndarray, n_bl: int) -> tuple[np.ndarray, np.ndarray]:
    """Zellzahlen je Band (gesamt) und je Band × Bundesland, in einem Pass."""
    n_bands = src.count
    totals = np.zeros(n_bands, dtype=np.int64)
    by_bl = np.zeros((n_bands, n_bl + 1), dtype=np.int64)

    windows = [w for _, w in src.block_windows(1)]
    started = time.time()
    for done, win in enumerate(windows, 1):
        block = src.read(window=win)
        r0, c0 = int(win.row_off), int(win.col_off)
        bl_block = bl_ids[r0:r0 + int(win.height), c0:c0 + int(win.width)]
        for b in range(n_bands):
            mask = block[b] > 0
            if not mask.any():
                continue
            totals[b] += int(mask.sum())
            by_bl[b] += np.bincount(bl_block[mask], minlength=n_bl + 1)
        if done % 250 == 0 or done == len(windows):
            elapsed = time.time() - started
            eta = elapsed / done * (len(windows) - done)
            print(f"  Kachel {done}/{len(windows)}  {elapsed:6.0f}s verstrichen, ~{eta:5.0f}s offen", flush=True)
    return totals, by_bl


def scan_overlaps(src: rasterio.DatasetReader, bl_ids: np.ndarray) -> dict:
    """Marginale Sperrfläche je Kriterium plus 3er-Venn Mensch/Natur/Geographie.

    Marginal heißt: die Zelle ist von **genau einem** der gelisteten Kriterien
    gesperrt. Das ist die Fläche, die frei würde, ließe man dieses eine
    Kriterium fallen — im Gegensatz zur Bruttofläche, die sich mit anderen
    Kriterien überschneidet und sich deshalb nicht aufsummieren lässt.

    Alles wird auf Österreich maskiert. Notwendig, weil die Pipeline nur die
    Gruppenbänder (exclusion_human/_nature/_geography) auf das Staatsgebiet
    schneidet, die Einzelkriterien aber über den vollen Raster-Ausschnitt
    laufen: `geography_wind_too_low` allein misst ungeschnitten 138.778 km²
    und liegt damit größtenteils in Bayern, Ungarn und Tschechien.
    """
    idx = {desc: i for i, desc in enumerate(src.descriptions, 1)}
    flat = [(g, band, label) for g, items in EXCLUSION_LAYERS.items() for band, label in items]
    missing = [b for _, b, _ in flat if b not in idx]
    if missing:
        raise SystemExit(f"Bänder fehlen im GeoTIFF: {missing}")

    layer_idx = [idx[b] for _, b, _ in flat]
    group_idx = [idx[f"exclusion_{g}"] for g in ("human", "nature", "geography")]
    read_idx = layer_idx + group_idx
    n_layers = len(layer_idx)
    n_bl = int(bl_ids.max())
    stride = n_bl + 1

    marginal = np.zeros((n_layers, stride), dtype=np.int64)
    venn = np.zeros((8, stride), dtype=np.int64)
    union = np.zeros(stride, dtype=np.int64)

    windows = [w for _, w in src.block_windows(1)]
    started = time.time()
    for done, win in enumerate(windows, 1):
        r0, c0 = int(win.row_off), int(win.col_off)
        blk = bl_ids[r0:r0 + int(win.height), c0:c0 + int(win.width)]
        at = blk > 0
        if not at.any():
            continue
        block = (src.read(indexes=read_idx, window=win) > 0) & at
        layers = block[:n_layers]
        active = layers.sum(axis=0, dtype=np.int16)
        alone = active == 1
        union += np.bincount(blk[active > 0], minlength=stride)
        if alone.any():
            for j in range(n_layers):
                if layers[j].any():
                    marginal[j] += np.bincount(blk[layers[j] & alone], minlength=stride)

        h, n, g = block[n_layers], block[n_layers + 1], block[n_layers + 2]
        code = h.astype(np.uint8) | (n.astype(np.uint8) << 1) | (g.astype(np.uint8) << 2)
        # code und Bundesland in einen Index falten: ein bincount statt sieben
        venn += np.bincount((code.astype(np.int32) * stride + blk).ravel(),
                            minlength=8 * stride).reshape(8, stride)
        if done % 500 == 0 or done == len(windows):
            elapsed = time.time() - started
            print(f"  Überschneidungen: Kachel {done}/{len(windows)}  {elapsed:5.0f}s", flush=True)

    return {
        "layers": [
            {"band": band, "label": label, "group": group, "index": j}
            for j, (group, band, label) in enumerate(flat)
        ],
        "marginal_cells": marginal,
        "venn_cells": venn,
        "union_cells": union,
    }


def build_overlap_payload(raw: dict, band_by_bl: dict, bl_names: list[str], cell_km2: float) -> dict:
    """Rohzählungen der Überschneidungsanalyse in die JSON-Struktur bringen."""

    def spread(counts) -> dict:
        """Zellzahlen je Bundesland → km², plus Österreich-Summe."""
        return {bl: round(float(counts[j + 1] * cell_km2), 2) for j, bl in enumerate(bl_names)}

    layers = [
        {
            "band": item["band"],
            "label": item["label"],
            "group": item["group"],
            "group_label": GROUP_LABELS[item["group"]],
            "brutto_km2": round(sum(band_by_bl[item["band"]].values()), 2),
            "brutto_by_bl": band_by_bl[item["band"]],
            "marginal_km2": round(float(raw["marginal_cells"][item["index"]][1:].sum() * cell_km2), 2),
            "marginal_by_bl": spread(raw["marginal_cells"][item["index"]]),
        }
        for item in raw["layers"]
    ]
    # Venn-Codes: Bit 0 = Mensch, Bit 1 = Natur, Bit 2 = Geographie.
    # Code 0 (nichts gesperrt) ist die Rohfläche und gehört nicht in die
    # Zusammensetzung der Sperrfläche.
    venn_names = {
        1: "nur Mensch", 2: "nur Natur", 3: "Mensch + Natur", 4: "nur Geographie",
        5: "Mensch + Geographie", 6: "Natur + Geographie", 7: "alle drei",
    }
    return {
        "layers": sorted(layers, key=lambda x: -x["marginal_km2"]),
        "venn": [
            {
                "code": code,
                "label": label,
                "km2": round(float(raw["venn_cells"][code][1:].sum() * cell_km2), 2),
                "by_bl": spread(raw["venn_cells"][code]),
            }
            for code, label in venn_names.items()
        ],
        "union_km2": round(float(raw["union_cells"][1:].sum() * cell_km2), 2),
        "union_by_bl": spread(raw["union_cells"]),
    }


def build_payload(src, names, totals, by_bl, bl_names, cell_km2, turbine_density) -> dict:
    """JSON-Struktur aus den Rohzählungen — reine Umrechnung, kein I/O."""
    bands = [
        {
            "index": i + 1,
            "name": names[i],
            # km2 = voller Raster-Ausschnitt (Bounding Box, reicht über die
            # Staatsgrenze hinaus), km2_at = auf Österreich geschnitten.
            # Fürs Dashboard zählt km2_at.
            "km2": round(float(totals[i] * cell_km2), 2),
            "km2_at": round(float(by_bl[i][1:].sum() * cell_km2), 2),
            "by_bl": {
                bl: round(float(by_bl[i][j + 1] * cell_km2), 2)
                for j, bl in enumerate(bl_names)
            },
        }
        for i in range(len(names))
    ]
    return {
        "meta": {
            "tif": Path(src.name).name,
            "width": src.width,
            "height": src.height,
            "band_count": src.count,
            "crs": str(src.crs),
            "cell_size_m": abs(src.transform.a),
            "bounds": list(src.bounds),
            "turbine_density_mw_km2": round(turbine_density, 3),
            "study_mw_per_km2": STUDY_MW_PER_KM2,
        },
        "bundeslaender": bl_names,
        "bands": bands,
        "study": {"km2": STUDY_KM2, "mw": STUDY_MW},
    }


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    turbine_density = cfg["_derived"]["turbine_density"]

    with rasterio.open(args.tif) as src:
        cell_km2 = abs(src.transform.a * src.transform.e) / 1e6
        print(f"{args.tif}: {src.count} Bänder, {src.width} × {src.height}", flush=True)

        print("Bundesland-Id-Raster wird aufgebaut …", flush=True)
        bl_ids, bl_names = bundesland_id_raster(cfg, src)
        print(f"  {len(bl_names)} Bundesländer: {', '.join(bl_names)}", flush=True)

        print("Ein Pass über alle Bänder …", flush=True)
        totals, by_bl = scan_bands(src, bl_ids, len(bl_names))
        payload = build_payload(src, list(src.descriptions), totals, by_bl,
                                bl_names, cell_km2, turbine_density)

        print("Zweiter Pass: Überschneidung der Ausschlusskriterien …", flush=True)
        raw_overlap = scan_overlaps(src, bl_ids)

    band_km2 = {b["name"]: b["km2_at"] for b in payload["bands"]}
    band_by_bl = {b["name"]: b["by_bl"] for b in payload["bands"]}
    payload["overlap"] = build_overlap_payload(raw_overlap, band_by_bl, bl_names, cell_km2)
    payload["meta"]["austria_km2"] = round(float(int((bl_ids > 0).sum()) * cell_km2), 2)
    payload["meta"]["bl_km2"] = {
        bl: round(float(int((bl_ids == j + 1).sum()) * cell_km2), 2)
        for j, bl in enumerate(bl_names)
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"geschrieben: {out}")

    ov = payload["overlap"]
    print(f"\n  Österreich gesamt {payload['meta']['austria_km2']:>12,.0f} km²")
    print(f"  Vereinigung der Einzelkriterien {ov['union_km2']:>12,.0f} km²"
          f"   (Band all_exclusions: {band_km2['all_exclusions']:,.0f} km²)")

    print("\n  Marginale Sperrfläche — was NUR dieses Kriterium sperrt:")
    print(f"  {'Kriterium':<42} {'brutto':>10} {'marginal':>10}")
    for layer in ov["layers"]:
        print(f"  {layer['label']:<42} {layer['brutto_km2']:>10,.0f} {layer['marginal_km2']:>10,.0f}")

    print("\n  Überschneidung der drei Gruppen:")
    for part in ov["venn"]:
        print(f"  {part['label']:<24} {part['km2']:>12,.0f} km²")


if __name__ == "__main__":
    main()
