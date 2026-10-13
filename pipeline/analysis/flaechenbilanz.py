"""Flaechenbilanz: eine feste Liste von Kennzahlen je Bundesland und AT,
gerechnet auf dem 45-Band-Abschichtungs-GeoTIFF (und robust auch auf
aelteren 38-/54-Band-Stufen: Baender werden ausschliesslich ueber ihren
Namen aufgeloest, nie ueber eine feste Bandnummer).

CLI:
    python -m pipeline.analysis.flaechenbilanz \\
        --tif <path> [--bands-json <path>] [--wka <geojson>] \\
        --out <tsv> [--trailer]

Regionen: Bundesland-Masken nach Zellmittelpunkt, exakt wie in
``pipeline.analysis.flaechenanteile._load_regions`` /
``_make_region_raster`` (all_touched=False, feste Bundeslandreihenfolge).
AT ist die Summe der 9 Masken - nicht das volle Rastergitter.

Bandaufloesung ausschliesslich ueber den Namen: zuerst das Sidecar-Manifest
(``--bands-json``, sonst ``<tif-stem>.bands.json`` daneben, falls
vorhanden), sonst die GDAL-Banddeskriptionen im TIF selbst
(``rasterio.open(...).descriptions``). Fehlt ein benoetigtes Band in beiden
Quellen, bleiben dessen Zellen fuer alle Regionen leer und eine
``# fehlt: <kennzahl> (<bandname>)``-Kommentarzeile wird geschrieben - der
Lauf bricht dafuer nicht ab. Das ist bewusst so, weil dieses Werkzeug auch
auf aelteren TIFs (38, 54 Baender) laufen soll, denen einzelne Baender noch
fehlen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Callable

import numpy as np
import rasterio
from rasterio.windows import Window, transform as window_transform

# ---------------------------------------------------------------------------
# Projekt-Root relativ zu dieser Datei (<repo>/pipeline/analysis/), wie in
# flaechenanteile.py.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import contract  # noqa: E402
from pipeline.analysis import flaechenanteile as fa  # noqa: E402
from calc.band_manifest import manifest_path_for  # noqa: E402

BLOCK_ROWS = 1000
PIXEL_AREA_M2 = 625.0
PIXEL_AREA_KM2 = PIXEL_AREA_M2 / 1e6

STATE_ORDER = list(fa.STATE_CODES.values())  # B K N O S ST T V W, feste Reihenfolge
REGION_ORDER = STATE_ORDER + ["AT"]

Mask = Callable[[dict], np.ndarray]

# ---------------------------------------------------------------------------
# Kennzahlen, in fester Reihenfolge. Jede Zeile: (key, benoetigte Baender,
# compute(bb) -> bool-Array). "bb" ist ein dict {bandname: bool-Array} fuer
# genau die hier gelisteten Namen.
# ---------------------------------------------------------------------------

AREA_KENNZAHLEN: list[tuple[str, tuple[str, ...], Mask]] = [
    ("ergebnis.ausschluss_gesamt", ("all_exclusions",),
     lambda bb: bb["all_exclusions"]),
    ("ergebnis.frei_roh", ("available_after_all_exclusions_raw",),
     lambda bb: bb["available_after_all_exclusions_raw"]),
    ("ergebnis.kleinflaechen", ("available_after_all_exclusions_raw", "available_cleaned_min_10ha"),
     lambda bb: bb["available_after_all_exclusions_raw"] & ~bb["available_cleaned_min_10ha"]),
    ("ergebnis.eignung_10ha", ("available_cleaned_min_10ha",),
     lambda bb: bb["available_cleaned_min_10ha"]),

    ("kategorie.mensch", ("exclusion_human",), lambda bb: bb["exclusion_human"]),
    ("kategorie.natur", ("exclusion_nature",), lambda bb: bb["exclusion_nature"]),
    ("kategorie.geografie", ("exclusion_geography",), lambda bb: bb["exclusion_geography"]),

    ("exklusiv.nur_mensch", ("exclusion_human", "exclusion_nature", "exclusion_geography"),
     lambda bb: bb["exclusion_human"] & ~bb["exclusion_nature"] & ~bb["exclusion_geography"]),
    ("exklusiv.nur_natur", ("exclusion_human", "exclusion_nature", "exclusion_geography"),
     lambda bb: ~bb["exclusion_human"] & bb["exclusion_nature"] & ~bb["exclusion_geography"]),
    ("exklusiv.nur_geografie", ("exclusion_human", "exclusion_nature", "exclusion_geography"),
     lambda bb: ~bb["exclusion_human"] & ~bb["exclusion_nature"] & bb["exclusion_geography"]),
    ("exklusiv.mensch_natur", ("exclusion_human", "exclusion_nature", "exclusion_geography"),
     lambda bb: bb["exclusion_human"] & bb["exclusion_nature"] & ~bb["exclusion_geography"]),
    ("exklusiv.mensch_geografie", ("exclusion_human", "exclusion_nature", "exclusion_geography"),
     lambda bb: bb["exclusion_human"] & ~bb["exclusion_nature"] & bb["exclusion_geography"]),
    ("exklusiv.natur_geografie", ("exclusion_human", "exclusion_nature", "exclusion_geography"),
     lambda bb: ~bb["exclusion_human"] & bb["exclusion_nature"] & bb["exclusion_geography"]),
    ("exklusiv.alle_drei", ("exclusion_human", "exclusion_nature", "exclusion_geography"),
     lambda bb: bb["exclusion_human"] & bb["exclusion_nature"] & bb["exclusion_geography"]),

    ("kriterium.mensch.siedlung", ("settlement_buffer",), lambda bb: bb["settlement_buffer"]),
    ("kriterium.mensch.haeuser_im_gruenen", ("haeuser_im_gruenen",), lambda bb: bb["haeuser_im_gruenen"]),
    ("kriterium.mensch.nichtwohn_huellen", ("nonresidential_hulls_buffer",),
     lambda bb: bb["nonresidential_hulls_buffer"]),
    ("kriterium.mensch.seilbahn_gebaeude", ("cableway_buildings_buffer",),
     lambda bb: bb["cableway_buildings_buffer"]),
    ("kriterium.mensch.gebaeude", ("general_buildings_buffer",), lambda bb: bb["general_buildings_buffer"]),
    ("kriterium.mensch.verkehr",
     ("road_motorway_trunk", "road_federal_state", "rail_main", "cableway_people_150m"),
     lambda bb: bb["road_motorway_trunk"] | bb["road_federal_state"] | bb["rail_main"] | bb["cableway_people_150m"]),
    ("kriterium.mensch.verkehr.autobahn", ("road_motorway_trunk",), lambda bb: bb["road_motorway_trunk"]),
    ("kriterium.mensch.verkehr.bundes_landesstrassen", ("road_federal_state",),
     lambda bb: bb["road_federal_state"]),
    ("kriterium.mensch.verkehr.bahn", ("rail_main",), lambda bb: bb["rail_main"]),
    ("kriterium.mensch.verkehr.seilbahn_personen", ("cableway_people_150m",),
     lambda bb: bb["cableway_people_150m"]),
    ("kriterium.mensch.freileitungen", ("power_lines_110kv_plus",),
     lambda bb: bb["power_lines_110kv_plus"]),
    ("kriterium.mensch.militaer", ("military_restricted_area",), lambda bb: bb["military_restricted_area"]),
    ("kriterium.mensch.luftfahrt", ("airport_area_major", "airport_runway_corridor_5km"),
     lambda bb: bb["airport_area_major"] | bb["airport_runway_corridor_5km"]),
    ("kriterium.mensch.luftfahrt.flughafen", ("airport_area_major",), lambda bb: bb["airport_area_major"]),
    ("kriterium.mensch.luftfahrt.anflugkorridor", ("airport_runway_corridor_5km",),
     lambda bb: bb["airport_runway_corridor_5km"]),

    # Nur amtliche Schutzgebiete sind Ausschlusskriterium (== kategorie.natur);
    # das OSM-Band 22 ist reine Information und fliesst NICHT in die Elternzeile.
    ("kriterium.natur.schutzgebiet", ("nature_protection_areas",), lambda bb: bb["nature_protection_areas"]),
    ("kriterium.natur.schutzgebiet.amtlich", ("nature_protection_areas",), lambda bb: bb["nature_protection_areas"]),
    ("info.natur.schutzgebiet.osm", ("osm_nature_protection_areas",),
     lambda bb: bb["osm_nature_protection_areas"]),

    ("kriterium.geografie.hangneigung", ("geography_slope_too_steep",), lambda bb: bb["geography_slope_too_steep"]),
    ("kriterium.geografie.seehoehe", ("geography_elevation_too_high",),
     lambda bb: bb["geography_elevation_too_high"]),
    ("kriterium.geografie.wind", ("geography_wind_too_low",), lambda bb: bb["geography_wind_too_low"]),
    ("kriterium.geografie.gewaesser", ("geography_water_bodies",), lambda bb: bb["geography_water_bodies"]),

    ("referenz.amtliche_zonen", ("official_wind_zoning",), lambda bb: bb["official_wind_zoning"]),
    ("referenz.wka_ausserhalb_zonen", ("wka_bestand_ausserhalb_zonen",),
     lambda bb: bb["wka_bestand_ausserhalb_zonen"]),
]

# WKA-Zaehl-Kennzahlen: kommen aus dem --wka-GeoJSON, nicht aus dem Raster.
WKA_KENNZAHLEN = [
    "referenz.wka.anlagen",
    "referenz.wka.in_zonen",
    "referenz.wka.ausserhalb",
    "referenz.wka.parks",
]

ALL_KENNZAHLEN_ORDER = [key for key, _bands, _fn in AREA_KENNZAHLEN] + WKA_KENNZAHLEN


# ---------------------------------------------------------------------------
# Bandaufloesung ausschliesslich ueber den Namen
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _default_bands_json(tif_path: Path) -> Path:
    return manifest_path_for(tif_path)


def resolve_band_names(ds: rasterio.io.DatasetReader, bands_json: Path | None):
    """(name -> index, manifest-dict oder None). Nie ueber Bandnummern."""
    if bands_json is not None and bands_json.is_file():
        manifest = json.loads(bands_json.read_text(encoding="utf-8"))
        name_to_index = {b["name"]: b["index"] for b in manifest.get("bands", [])}
        return name_to_index, manifest
    # Fallback: GDAL-Banddeskriptionen direkt aus dem TIF - ebenfalls
    # namensbasiert, keine Bandnummer wird hier "geraten".
    name_to_index: dict[str, int] = {}
    for i, desc in enumerate(ds.descriptions, start=1):
        if desc:
            name_to_index[desc] = i
    return name_to_index, None


def resolve_schema(manifest: dict | None, ds: rasterio.io.DatasetReader) -> str:
    if manifest and manifest.get("band_schema"):
        return str(manifest["band_schema"])
    tags = ds.tags()
    if tags.get("BAND_SCHEMA"):
        return str(tags["BAND_SCHEMA"])
    return "unknown"


# ---------------------------------------------------------------------------
# WKA-Zaehlung aus dem GeoJSON (Punkt-in-Polygon gegen dieselben
# Bundeslandmasken-Geometrien, die auch die Rasterisierung benutzt)
# ---------------------------------------------------------------------------

def _load_wka_points(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    points = []
    for feat in data["features"]:
        props = feat.get("properties", {})
        x, y = feat["geometry"]["coordinates"]
        points.append({
            "x": x, "y": y,
            "in_zone": bool(props.get("in_zone")),
            "hull_id": props.get("hull_id"),
        })
    return points


def _assign_wka_regions(points: list[dict], regions) -> list[dict]:
    """Punkt-in-Polygon je Bundesland (dieselben Geometrien wie beim
    Rasterisieren); Reihenfolge der Regionen ist fest, daher deterministisch
    bei Punkten exakt auf einer gemeinsamen Grenze (nimmt die erste, die
    zutrifft - analog zur festen Bundeslandreihenfolge bei der
    Zellmittelpunkt-Regel)."""
    from shapely.geometry import Point
    from shapely.prepared import prep

    prepared = [(code, prep(geom)) for code, _name, geom in regions]
    out = []
    for p in points:
        pt = Point(p["x"], p["y"])
        region = None
        for code, pgeom in prepared:
            if pgeom.contains(pt):
                region = code
                break
        out.append({**p, "region": region})
    return out


def compute_wka_counts(points: list[dict]) -> dict[str, dict[str, int]]:
    """{region_or_AT: {"anlagen":.., "in_zonen":.., "ausserhalb":.., "parks":..}}

    "parks" je Region ist die Zahl der unterschiedlichen hull_id unter den
    dieser Region zugeordneten Punkten mit in_zone=False (hull_id=None zaehlt
    nicht als eigener Park). AT.parks ist die Zahl unterschiedlicher hull_id
    unter ALLEN Punkten mit in_zone=False landesweit - das ist NICHT
    zwangslaeufig die Summe der Regionswerte, wenn eine Park-Huelle ueber
    eine Bundeslandgrenze reicht (ihre Punkte koennten unterschiedlichen
    Regionen zugeordnet sein). Das betrifft nur "anzahl"-Zeilen, nicht die
    "zellen"-Summenpruefung der Flaechenzeilen.
    """
    out = {code: {"anlagen": 0, "in_zonen": 0, "ausserhalb": 0} for code in STATE_ORDER}
    hulls_by_region: dict[str, set] = {code: set() for code in STATE_ORDER}
    at = {"anlagen": 0, "in_zonen": 0, "ausserhalb": 0}
    hulls_at: set = set()

    for p in points:
        at["anlagen"] += 1
        if p["in_zone"]:
            at["in_zonen"] += 1
        else:
            at["ausserhalb"] += 1
            if p["hull_id"] is not None:
                hulls_at.add(p["hull_id"])
        code = p["region"]
        if code is None:
            continue
        out[code]["anlagen"] += 1
        if p["in_zone"]:
            out[code]["in_zonen"] += 1
        else:
            out[code]["ausserhalb"] += 1
            if p["hull_id"] is not None:
                hulls_by_region[code].add(p["hull_id"])

    for code in STATE_ORDER:
        out[code]["parks"] = len(hulls_by_region[code])
    at["parks"] = len(hulls_at)
    out["AT"] = at
    return out


# ---------------------------------------------------------------------------
# Hauptberechnung
# ---------------------------------------------------------------------------

def compute_bilanz(tif_path: Path, bands_json: Path | None, wka_path: Path | None,
                    block_rows: int = BLOCK_ROWS, regions_path: Path | None = None):
    """``regions_path`` ist optional (Default: die echten Bundeslandmasken aus
    ``pipeline.contract``) - so injizieren Tests eine winzige synthetische
    Bundeslandmaske, ohne echte Repo-Daten zu brauchen (wie
    ``flaechenanteile.analyze(regions_path=...)``)."""
    tif_sha256 = _sha256(tif_path)

    ds = rasterio.open(tif_path)
    name_to_index, manifest = resolve_band_names(ds, bands_json)
    schema = resolve_schema(manifest, ds)
    band_count = ds.count

    regions_path = regions_path or contract.PREP_FILES["admin"]["bundesland_masken"]
    regions = fa._load_regions(Path(regions_path))
    state_codes = [code for code, _name, _geom in regions]
    assert state_codes == STATE_ORDER, (
        f"Unerwartete Bundeslandreihenfolge aus {regions_path}: {state_codes}"
    )

    # Welche Kennzahlen sind rechenbar (alle Baender vorhanden)?
    missing_report: list[tuple[str, list[str]]] = []
    computable: list[tuple[str, tuple[str, ...], Mask]] = []
    needed_names: set[str] = set()
    for key, bands, fn in AREA_KENNZAHLEN:
        missing = [b for b in bands if b not in name_to_index]
        if missing:
            missing_report.append((key, missing))
        else:
            computable.append((key, bands, fn))
            needed_names.update(bands)

    needed_indices = sorted(name_to_index[n] for n in needed_names)
    index_to_name = {name_to_index[n]: n for n in needed_names}

    height, width = ds.height, ds.width
    counters: dict[str, dict[str, int]] = {key: {code: 0 for code in state_codes} for key, _b, _f in computable}
    region_cells = {code: 0 for code in state_codes}
    n_codes = len(state_codes) + 1

    for row_off in range(0, height, block_rows):
        h = min(block_rows, height - row_off)
        window = Window(0, row_off, width, h)
        w_transform = window_transform(window, ds.transform)
        region_raster, raster_codes = fa._make_region_raster(regions, (h, width), w_transform)
        region_flat = region_raster.ravel()
        denom_counts = np.bincount(region_flat, minlength=n_codes)
        raster_code_to_state = {i + 1: code for i, code in enumerate(state_codes)}
        for code in range(1, n_codes):
            region_code = raster_code_to_state.get(code)
            if region_code is not None:
                region_cells[region_code] += int(denom_counts[code])

        if needed_indices:
            stack = ds.read(indexes=needed_indices, window=window)
            band_bool = {index_to_name[idx]: (stack[pos] == 1) for pos, idx in enumerate(needed_indices)}
        else:
            band_bool = {}

        for key, _bands, fn in computable:
            mask = fn(band_bool)
            counts = np.bincount(region_flat, weights=mask.ravel(), minlength=n_codes)
            for code in range(1, n_codes):
                region_code = raster_code_to_state.get(code)
                if region_code is not None:
                    counters[key][region_code] += int(round(counts[code]))

    ds.close()

    at_cells = sum(region_cells.values())

    # --- WKA-Zaehlung ---
    wka_counts = None
    if wka_path is not None:
        points = _load_wka_points(wka_path)
        assigned = _assign_wka_regions(points, regions)
        wka_counts = compute_wka_counts(assigned)

    return dict(
        tif_sha256=tif_sha256,
        schema=schema,
        band_count=band_count,
        region_cells=region_cells,
        at_cells=at_cells,
        counters=counters,
        missing_report=missing_report,
        wka_counts=wka_counts,
        state_codes=state_codes,
    )


# ---------------------------------------------------------------------------
# TSV-Ausgabe
# ---------------------------------------------------------------------------

def _fmt_km2(cells: int) -> str:
    return f"{cells * PIXEL_AREA_KM2:.2f}"


def _fmt_pct(cells: int, denom: int) -> str:
    if not denom:
        return ""
    return f"{cells / denom * 100:.3f}"


def write_tsv(data: dict, out_path: Path) -> None:
    lines = []
    lines.append("# flaechenbilanz v1")
    lines.append(f"# tif_sha256={data['tif_sha256']}")
    lines.append(f"# schema={data['schema']}")
    lines.append(f"# band_count={data['band_count']}")
    lines.append("# bezug=bundesland_maske_zellmitte zelle_m2=625")
    for key, missing in data["missing_report"]:
        lines.append(f"# fehlt: {key} ({', '.join(missing)})")

    lines.append("kennzahl\tregion\tzellen\tkm2\tprozent\tanzahl")

    region_cells = data["region_cells"]
    at_cells = data["at_cells"]
    counters = data["counters"]
    missing_keys = {key for key, _m in data["missing_report"]}

    for key, _bands, _fn in AREA_KENNZAHLEN:
        for region in REGION_ORDER:
            if key in missing_keys:
                lines.append(f"{key}\t{region}\t\t\t\t")
                continue
            if region == "AT":
                cells = sum(counters[key].values())
                denom = at_cells
            else:
                cells = counters[key][region]
                denom = region_cells[region]
            lines.append(f"{key}\t{region}\t{cells}\t{_fmt_km2(cells)}\t{_fmt_pct(cells, denom)}\t")

    wka_counts = data["wka_counts"]
    wka_key_map = {
        "referenz.wka.anlagen": "anlagen",
        "referenz.wka.in_zonen": "in_zonen",
        "referenz.wka.ausserhalb": "ausserhalb",
        "referenz.wka.parks": "parks",
    }
    for key in WKA_KENNZAHLEN:
        field = wka_key_map[key]
        for region in REGION_ORDER:
            if wka_counts is None:
                lines.append(f"{key}\t{region}\t\t\t\t")
            else:
                anzahl = wka_counts[region][field]
                lines.append(f"{key}\t{region}\t\t\t\t{anzahl}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_trailer(data: dict) -> None:
    at_cells = data["at_cells"]
    counters = data["counters"]
    missing_keys = {key for key, _m in data["missing_report"]}

    def at_pct(key: str) -> str:
        if key in missing_keys or not at_cells:
            return "n/a"
        cells = sum(counters[key].values())
        return f"{cells / at_cells * 100:.2f}"

    def at_km2(key: str) -> str:
        if key in missing_keys:
            return "n/a"
        cells = sum(counters[key].values())
        return f"{cells * PIXEL_AREA_KM2:.1f}"

    print(f"Flaechenbilanz-TIF: {data['tif_sha256'][:12]}")
    print(
        f"Flaechenbilanz-AT: eignung {at_km2('ergebnis.eignung_10ha')} km2 "
        f"{at_pct('ergebnis.eignung_10ha')} % | "
        f"ausschluss {at_pct('ergebnis.ausschluss_gesamt')} % | "
        f"mensch {at_pct('kategorie.mensch')} % | "
        f"natur {at_pct('kategorie.natur')} % | "
        f"geografie {at_pct('kategorie.geografie')} %"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tif", required=True, type=Path)
    parser.add_argument("--bands-json", type=Path, default=None)
    parser.add_argument("--wka", type=Path, default=None)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--trailer", action="store_true")
    args = parser.parse_args(argv)

    tif_path = args.tif
    if not tif_path.is_file():
        print(f"flaechenbilanz: Fehler: TIF fehlt: {tif_path}", file=sys.stderr)
        return 2

    bands_json = args.bands_json
    if bands_json is None:
        candidate = _default_bands_json(tif_path)
        if candidate.is_file():
            bands_json = candidate
    elif not bands_json.is_file():
        print(f"flaechenbilanz: Fehler: --bands-json fehlt: {bands_json}", file=sys.stderr)
        return 2

    wka_path = args.wka
    if wka_path is not None and not wka_path.is_file():
        print(f"flaechenbilanz: Fehler: --wka fehlt: {wka_path}", file=sys.stderr)
        return 2

    data = compute_bilanz(tif_path, bands_json, wka_path)
    write_tsv(data, args.out)
    print(f"[done] flaechenbilanz -> {args.out}")
    if args.trailer:
        print_trailer(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
