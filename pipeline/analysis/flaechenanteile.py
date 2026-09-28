"""Flächenanteile der Ausschlusskriterien je Bundesland und österreichweit.

Die Analyse liest ausschließlich ``contract.LAYERS`` und die in Prep
erzeugten Bundeslandgrenzen. Sie zählt Pixel auf dem gemeinsamen Checkpoint-
Gitter, weist Kriterien einzeln sowie als OR-Union innerhalb der drei
Fachgruppen aus und schreibt CSV plus Methodik-Metadaten nach
``out/analysis/flaechenanteile/``.

Die vorhandenen Ausschluss-Checkpoints sind sparse binäre Raster mit
``nodata=0``: der Wert 1 markiert eine Ausschlusszelle; 0 wird deshalb als
"kein Ausschluss markiert" interpretiert. Diese Datenstruktur kann eine
fehlende Abdeckung nicht von einer gültigen Null unterscheiden. Das wird in
den Metadaten ausdrücklich festgehalten; unbekannte Zellen sind für diese
Layer nicht belastbar quantifizierbar.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from affine import Affine  # noqa: E402
from rasterio.features import rasterize  # noqa: E402
from rasterio.windows import Window, transform as window_transform  # noqa: E402

from pipeline import contract  # noqa: E402
from pipeline.prep import admin as prep_admin  # noqa: E402

TARGET_CRS = "EPSG:31287"
BLOCK_ROWS = 256
STATE_CODES = {
    "Burgenland": "B",
    "Kärnten": "K",
    "Niederösterreich": "N",
    "Oberösterreich": "O",
    "Salzburg": "S",
    "Steiermark": "ST",
    "Tirol": "T",
    "Vorarlberg": "V",
    "Wien": "W",
}


@dataclass(frozen=True)
class Criterion:
    name: str
    group: str
    layer: str


BASE_CRITERIA = (
    Criterion("settlement_buffer", "siedlung", "settlement_buffer"),
    Criterion("haeuser_im_gruenen", "siedlung", "haeuser_im_gruenen"),
    Criterion("slope_too_steep", "geographie", "geography_slope_too_steep"),
    Criterion("wind_too_low", "geographie", "geography_wind_too_low"),
    Criterion("nature_protection_areas", "naturschutz", "nature_protection_areas"),
    Criterion("osm_nature_protection_areas", "naturschutz", "osm_nature_protection_areas"),
)
GENERAL_BUILDINGS_CRITERION = Criterion(
    "general_buildings_buffer", "siedlung", "general_buildings_buffer"
)

CSV_FIELDS = (
    "region_code",
    "region_name",
    "analysis_unit",
    "group",
    "criterion",
    "denominator_cells",
    "excluded_cells",
    "unknown_cells",
    "land_area_km2",
    "excluded_area_km2",
    "excluded_pct",
    "unknown_area_km2",
    "unknown_pct",
    "pixel_area_m2",
)


def _criteria(include_general_buildings: bool) -> tuple[Criterion, ...]:
    if include_general_buildings:
        return BASE_CRITERIA + (GENERAL_BUILDINGS_CRITERION,)
    return BASE_CRITERIA


def _load_regions(path: Path) -> list[tuple[str, str, object]]:
    if not path.is_file():
        raise FileNotFoundError(f"Bundeslandgrenzen fehlen: {path} (zuerst make prep-admin ausführen).")
    gdf = gpd.read_file(path)
    if "BL" not in gdf.columns:
        raise ValueError(f"{path}: erwartete Spalte 'BL' fehlt.")
    if gdf.crs is None:
        raise ValueError(f"{path}: CRS fehlt; Bundeslandgrenzen können nicht sicher rasterisiert werden.")
    if gdf.crs.to_string().upper() != TARGET_CRS:
        gdf = gdf.to_crs(TARGET_CRS)
    regions = []
    seen: set[str] = set()
    for name, geom in zip(gdf["BL"], gdf.geometry, strict=True):
        name = str(name)
        if name not in STATE_CODES:
            raise ValueError(f"Unbekannter Bundeslandname in {path}: {name!r}.")
        if name in seen:
            raise ValueError(f"Bundesland kommt mehrfach in {path} vor: {name!r}.")
        if geom is None or geom.is_empty or not geom.is_valid:
            raise ValueError(f"Ungültige oder leere Geometrie für {name!r} in {path}.")
        seen.add(name)
        regions.append((STATE_CODES[name], name, geom))
    if seen != set(STATE_CODES):
        missing = sorted(set(STATE_CODES) - seen)
        raise ValueError(f"{path}: erwartet 9 Bundesländer; fehlend: {', '.join(missing)}.")
    return sorted(regions, key=lambda row: list(STATE_CODES.values()).index(row[0]))


def _grid_signature(ds: rasterio.io.DatasetReader) -> dict:
    if ds.crs is None:
        raise ValueError(f"Raster-CRS fehlt: {ds.name}")
    if ds.count != 1:
        raise ValueError(f"{ds.name}: erwartet ein Einband-Raster, gefunden: {ds.count}.")
    tr = ds.transform
    area = abs(tr.a * tr.e - tr.b * tr.d)
    if not math.isfinite(area) or area <= 0:
        raise ValueError(f"{ds.name}: ungültige Rastertransformation {tr}.")
    return {
        "shape": (ds.height, ds.width),
        "crs": ds.crs,
        "transform": tr,
        "pixel_area_m2": area,
    }


def _check_same_grid(path: Path, ds: rasterio.io.DatasetReader, reference: dict) -> None:
    grid = _grid_signature(ds)
    if grid["shape"] != reference["shape"]:
        raise ValueError(f"{path}: Rasterdimensionen {grid['shape']} stimmen nicht mit Referenz {reference['shape']} überein.")
    if grid["crs"] != reference["crs"]:
        raise ValueError(f"{path}: CRS {grid['crs']} stimmt nicht mit Referenz {reference['crs']} überein.")
    if not np.allclose(tuple(grid["transform"]), tuple(reference["transform"]), rtol=0, atol=1e-9):
        raise ValueError(f"{path}: Rastertransformation stimmt nicht mit dem gemeinsamen Gitter überein.")


def _make_region_raster(regions, shape, transform: Affine) -> tuple[np.ndarray, dict[int, tuple[str, str]]]:
    codes = {i + 1: (code, name) for i, (code, name, _geom) in enumerate(regions)}
    arr = rasterize(
        ((geom, raster_code) for raster_code, (_code, _name, geom) in zip(codes, regions, strict=True)),
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype="uint8",
        all_touched=False,
    )
    return arr, codes


def _add(counter: dict, region_key, denominator: int, excluded: int, unknown: int | None) -> None:
    entry = counter.setdefault(region_key, {"denominator": 0, "excluded": 0, "unknown": 0, "unknown_known": True})
    entry["denominator"] += int(denominator)
    entry["excluded"] += int(excluded)
    if unknown is None:
        entry["unknown_known"] = False
    else:
        entry["unknown"] += int(unknown)


def _record_group_rows(counter, regions, criteria):
    # Counters use (region_code, analysis_unit, group, criterion).
    result = []
    regions_with_at = [(code, name) for code, name, _ in regions] + [("AT", "Österreich")]
    for code, name in regions_with_at:
        for criterion in criteria:
            result.append((code, name, "criterion", criterion.group, criterion.name,
                           counter.get((code, "criterion", criterion.group, criterion.name))))
        groups = sorted({criterion.group for criterion in criteria})
        for group in groups:
            result.append((code, name, "group_union", group, "OR-Union", 
                           counter.get((code, "group_union", group, "OR-Union"))))
    return result


def analyze(
    *,
    regions_path: Path | None = None,
    layer_paths: dict[str, Path] | None = None,
    output_dir: Path | None = None,
    include_general_buildings: bool = False,
    block_rows: int = BLOCK_ROWS,
) -> tuple[Path, Path]:
    """Berechnet die Auswertung blockweise; optionale Pfade erleichtern Tests."""
    regions_path = regions_path or (contract.PREP["admin"] / prep_admin.BUNDESLAND_MASKEN_FILENAME)
    output_dir = output_dir or (contract.OUT / "analysis" / "flaechenanteile")
    criteria = _criteria(include_general_buildings)
    paths = layer_paths or {criterion.layer: contract.LAYERS[criterion.layer] for criterion in criteria}
    regions = _load_regions(Path(regions_path))
    missing = [str(paths.get(c.layer, contract.LAYERS[c.layer])) for c in criteria
               if not Path(paths.get(c.layer, contract.LAYERS[c.layer])).is_file()]
    if missing:
        raise FileNotFoundError("Benötigte Ausschluss-Checkpoint(s) fehlen: " + ", ".join(missing))
    if block_rows < 1:
        raise ValueError("block_rows muss mindestens 1 sein.")

    datasets = {}
    metadata_layers = {}
    try:
        for criterion in criteria:
            path = Path(paths.get(criterion.layer, contract.LAYERS[criterion.layer]))
            ds = rasterio.open(path)
            datasets[criterion.layer] = ds
            if criterion is criteria[0]:
                reference = _grid_signature(ds)
                if reference["crs"].to_string().upper() != TARGET_CRS:
                    raise ValueError(
                        f"{ds.name}: Flächenanteile benötigen {TARGET_CRS} für km²; "
                        f"gefunden: {reference['crs']}."
                    )
            else:
                _check_same_grid(path, ds, reference)
            metadata_layers[criterion.layer] = {
                "path": str(path),
                "nodata": ds.nodata,
                "dtype": list(ds.dtypes),
                "crs": ds.crs.to_string(),
                "shape": [ds.height, ds.width],
                "transform": list(ds.transform),
            }

        # Das für jedes Gebiet identische Gitter wird je Kachel auf genau eine
        # Region codiert. Gemeinsame Randzellen werden über all_touched=False
        # und die feste Bundeslandreihenfolge deterministisch zugeordnet.
        counter = {}
        for row_off in range(0, reference["shape"][0], block_rows):
            height = min(block_rows, reference["shape"][0] - row_off)
            window = Window(0, row_off, reference["shape"][1], height)
            transform = window_transform(window, reference["transform"])
            region_raster, raster_codes = _make_region_raster(regions, (height, reference["shape"][1]), transform)
            masks = {}
            unknown_masks = {}
            for criterion in criteria:
                ds = datasets[criterion.layer]
                values = ds.read(1, window=window)
                if not np.isin(values, (0, 1)).all():
                    observed = np.unique(values)
                    raise ValueError(f"{ds.name}: erwartet binäre Werte 0/1; gefunden u.a. {observed[:10].tolist()}.")
                masks[criterion.name] = values == 1
                # nodata=0 ist die bestehende sparse-mask-Konvention und
                # erlaubt keine separate Aussage zu fehlender Datenabdeckung.
                unknown_masks[criterion.name] = None if ds.nodata == 0 else (values == ds.nodata)

            for raster_code, (region_code, _region_name) in raster_codes.items():
                inside = region_raster == raster_code
                denominator = int(inside.sum())
                if not denominator:
                    continue
                for criterion in criteria:
                    excluded_mask = masks[criterion.name] & inside
                    unknown_mask = unknown_masks[criterion.name]
                    unknown = None if unknown_mask is None else int((unknown_mask & inside & ~excluded_mask).sum())
                    _add(counter, (region_code, "criterion", criterion.group, criterion.name),
                         denominator, int(excluded_mask.sum()), unknown)
                for group in sorted({c.group for c in criteria}):
                    group_criteria = [c for c in criteria if c.group == group]
                    union = np.zeros(inside.shape, dtype=bool)
                    for criterion in group_criteria:
                        union |= masks[criterion.name]
                    excluded_mask = union & inside
                    if any(unknown_masks[c.name] is None for c in group_criteria):
                        unknown = None
                    else:
                        unknown_union = np.zeros(inside.shape, dtype=bool)
                        for criterion in group_criteria:
                            unknown_union |= unknown_masks[criterion.name]
                        unknown = int((unknown_union & inside & ~excluded_mask).sum())
                    _add(counter, (region_code, "group_union", group, "OR-Union"),
                         denominator, int(excluded_mask.sum()), unknown)

        # Österreich ist die Summe der 9 disjunkt zugeordneten Bundesländer.
        state_codes = [code for code, _name, _geom in regions]
        keys = list(counter)
        for unit_key in sorted({key[1:] for key in keys}):
            rows = [counter[(state, *unit_key)] for state in state_codes if (state, *unit_key) in counter]
            if not rows:
                continue
            counter[("AT", *unit_key)] = {
                "denominator": sum(row["denominator"] for row in rows),
                "excluded": sum(row["excluded"] for row in rows),
                "unknown": sum(row["unknown"] for row in rows),
                "unknown_known": all(row["unknown_known"] for row in rows),
            }

        rows_out = []
        for region_code, region_name, unit, group, criterion, stats in _record_group_rows(counter, regions, criteria):
            if not stats:
                continue
            denom = stats["denominator"]
            unknown = stats["unknown"] if stats["unknown_known"] else None
            area_km2 = reference["pixel_area_m2"] / 1_000_000
            rows_out.append({
                "region_code": region_code,
                "region_name": region_name,
                "analysis_unit": unit,
                "group": group,
                "criterion": criterion,
                "denominator_cells": denom,
                "excluded_cells": stats["excluded"],
                "unknown_cells": unknown,
                "land_area_km2": round(denom * area_km2, 6),
                "excluded_area_km2": round(stats["excluded"] * area_km2, 6),
                "excluded_pct": round(stats["excluded"] / denom * 100, 6) if denom else None,
                "unknown_area_km2": round(unknown * area_km2, 6) if unknown is not None else None,
                "unknown_pct": round(unknown / denom * 100, 6) if unknown is not None and denom else None,
                "pixel_area_m2": reference["pixel_area_m2"],
            })

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "flaechenanteile.csv"
        json_path = output_dir / "flaechenanteile.json"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows_out)

        metadata = {
            "title": "Flächenanteile der Ausschlusskriterien",
            "crs": reference["crs"].to_string(),
            "grid_shape": list(reference["shape"]),
            "grid_transform": list(reference["transform"]),
            "pixel_area_m2": reference["pixel_area_m2"],
            "boundary_source": str(regions_path),
            "boundary_feature_count": len(regions),
            "boundary_rasterization": "all_touched=false; jedes Pixelzentrum wird höchstens einem Bundesland zugeordnet; feste Bundeslandreihenfolge löst Rand- bzw. Überlappungsties deterministisch auf",
            "denominator": "Rasterzellen, deren Zentren im rasterisierten Bundesland liegen; Österreich ist die Summe der disjunkten 9 Bundeslandzuordnungen",
            "criteria": [
                {"name": c.name, "group": c.group, "layer": c.layer,
                 "path": str(Path(paths.get(c.layer, contract.LAYERS[c.layer])))}
                for c in criteria
            ],
            "layers": metadata_layers,
            "aggregation": "OR innerhalb jeder Gruppe, jede Zelle höchstens einmal je Gruppen-Union; Gruppen werden nicht gegeneinander bereinigt; Einzelkriterien können sich überlappen",
            "unknown_data": {
                "csv_unknown_cells": "null, wenn die Maske nodata=0 verwendet",
                "limitation": "Die vorhandenen Checkpoints sind sparse binäre Ausschlussmasken (1=markierter Ausschluss, 0/nodata=kein Ausschlussmarker). Diese Kodierung trennt geeignete Zellen nicht von fehlender Datenabdeckung. Deshalb wird 0 als nicht ausgeschlossen gezählt und für diese Raster kein unbekannter Flächenanteil behauptet.",
            },
            "general_buildings_buffer_included": include_general_buildings,
            "outputs": {"csv": str(csv_path), "metadata_json": str(json_path)},
        }
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        return csv_path, json_path
    finally:
        for ds in datasets.values():
            ds.close()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-general-buildings",
        action="store_true",
        help="general_buildings_buffer zusätzlich in der Gruppe siedlung auswerten (default: aus).",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--block-rows", type=int, default=BLOCK_ROWS)
    args = parser.parse_args(argv)
    try:
        csv_path, json_path = analyze(
            output_dir=args.output_dir,
            include_general_buildings=args.include_general_buildings,
            block_rows=args.block_rows,
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"flaechenanteile: Fehler: {exc}", file=sys.stderr)
        return 2
    print(f"[done] flaechenanteile -> {csv_path} und {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
