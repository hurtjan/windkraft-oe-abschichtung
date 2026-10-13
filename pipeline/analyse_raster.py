"""Zweites Produkt: ``out/abschichtung_analyse.tif`` + ``.bands.json``.

Nur Analyse, nicht Teil des Konsumentenvertrags (kein Viewer, Dashboard oder
Export liest es). Sieben uint8-Bänder (0/1) mit Kataster-Nutzungsklassen auf
EXAKT dem Raster von ``out/abschichtung.tif`` (CRS, Transform, Breite, Höhe,
Kachelung, Kompression werden aus dessen Profil übernommen).

Quelle: ``derived/prep/kataster/at_dkm_gst_nfl_epsg31287.geoparquet``
(Digitale Katastralmappe BEV, Benützungsarten/Nutzungen), nur ``source_layer``
``NFL_V2`` und ``NFL_DXF_POLYGONIZED``. Rasterung nach Zellmittelpunkt-Regel
(``all_touched=False``). Die beiden Quellebenen überschneiden sich nicht
(NFL_DXF_POLYGONIZED = nur Niederösterreich, NFL_V2 = übrige Länder; geprüft:
0 gemeinsame Zellen), eine Priorität ist daher nicht nötig. Die Bänder sind
unabhängig voneinander; überlappen sich Klassen in den Quelldaten, setzen
beide ihre Bänder.

Speicher: Zeilengruppen werden einzeln gelesen und gefiltert, je Band wird nur
das Fenster um die Geometrien gerastert; im Speicher liegt der Bandstapel
(7 x 14001 x 24001 uint8, ca. 2,3 GB).
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow.compute as pc
import pyarrow.parquet as pq
import rasterio
import shapely
from rasterio import features
from rasterio.windows import Window

from pipeline import contract, fingerprint

SCHEMA_VERSION = "1.0.0"
SOURCE_LAYERS = ["NFL_V2", "NFL_DXF_POLYGONIZED"]
QUELLE = "Digitale Katastralmappe BEV, Benützungsarten/Nutzungen"

# (Name, Label, ns-Codes, Beschreibung ohne Quelle/Codes)
BANDS = [
    ("kataster_wald", "Wald", ("56", "55"), "Waldflächen laut Kataster."),
    ("kataster_forststrassen", "Forststraßen", ("58",), "Forststraßen laut Kataster."),
    ("kataster_aecker_wiesen_weiden", "Äcker, Wiesen, Weiden", ("48",), "Äcker, Wiesen und Weiden laut Kataster."),
    ("kataster_alpen", "Alpen", ("54",), "Alpen (Almflächen) laut Kataster."),
    ("kataster_sonstige_landwirtschaft", "Sonstige Landwirtschaft", ("40", "53", "57"), "Sonstige landwirtschaftlich genutzte Flächen laut Kataster."),
    ("kataster_gaerten", "Gärten", ("52",), "Gärten laut Kataster."),
    ("kataster_bauflaechen", "Bauflächen", ("41", "83"), "Bauflächen laut Kataster."),
]
NS_TO_BANDS: dict[str, list[int]] = {}
for _i, (_n, _l, _codes, _d) in enumerate(BANDS):
    for _c in _codes:
        NS_TO_BANDS.setdefault(_c, []).append(_i)
ALL_CODES = sorted(NS_TO_BANDS)

MAIN_TIF = contract.PRODUCTS["abschichtung_tif"]
OUT_TIF = contract.PRODUCTS["abschichtung_analyse_tif"]
OUT_JSON = contract.PRODUCTS["abschichtung_analyse_bands_json"]
SOURCE = contract.PREP_FILES["kataster"]["at_dkm_gst_nfl"]


def band_indices(ns_values) -> list[list[int]]:
    """Je ns-Code die Liste der Bandindizes (0-basiert); unbekannt -> []."""
    return [NS_TO_BANDS.get(str(n), []) for n in ns_values]


def burn_geometries(stack: np.ndarray, geoms, ns_values, transform) -> None:
    """Rastert Geometrien (Zellmittelpunkt-Regel) je ns-Klasse in ``stack``
    (Form (Bänder, H, W)), jeweils nur im Fenster um die Geometrien."""
    _, height, width = stack.shape
    by_band: dict[int, list] = {}
    for g, idxs in zip(geoms, band_indices(ns_values)):
        if g is None or g.is_empty:
            continue
        for b in idxs:
            by_band.setdefault(b, []).append(g)
    for b, gl in by_band.items():
        minx, miny, maxx, maxy = shapely.total_bounds(np.array(gl, dtype=object))
        col0 = max(int(np.floor((minx - transform.c) / transform.a)) - 1, 0)
        col1 = min(int(np.ceil((maxx - transform.c) / transform.a)) + 1, width)
        row0 = max(int(np.floor((transform.f - maxy) / -transform.e)) - 1, 0)
        row1 = min(int(np.ceil((transform.f - miny) / -transform.e)) + 1, height)
        if col1 <= col0 or row1 <= row0:
            continue
        win = Window(col0, row0, col1 - col0, row1 - row0)
        wt = rasterio.windows.transform(win, transform)
        r = features.rasterize(((g, 1) for g in gl), out_shape=(row1 - row0, col1 - col0),
                               transform=wt, fill=0, dtype="uint8", all_touched=False)
        np.maximum(stack[b, row0:row1, col0:col1], r, out=stack[b, row0:row1, col0:col1])


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(profile: dict, bounds, main_tif: Path, main_sha: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "product": "abschichtung_analyse",
        "hinweis": "Nur Analyse, nicht Teil des Konsumentenvertrags.",
        "raster_file": OUT_TIF.name,
        "band_count": len(BANDS),
        "raster": {
            "crs": "EPSG:31287",
            "width": profile["width"],
            "height": profile["height"],
            "pixel_size_m": abs(float(profile["transform"].a)),
            "bounds": [float(x) for x in bounds],
            "dtype": "uint8",
            "nodata": 0,
            "nodata_meaning": "0 bedeutet: Klasse trifft nicht zu; 1: Zellmittelpunkt liegt in einer Fläche dieser Klasse",
        },
        "referenz": {
            "raster_file": main_tif.name,
            "sha256": main_sha,
            "hinweis": "Gleiches Raster (CRS, Transform, Breite, Höhe) wie diese Datei.",
        },
        "bands": [
            {
                "index": i + 1,
                "name": name,
                "label_de": label,
                "description_de": (
                    f"{desc} Quelle: {QUELLE}, Nutzungscodes {', '.join(codes)}; "
                    "Stand der Katasterdaten siehe docs/rohdaten.md. "
                    "Zellen, deren Mittelpunkt in einer solchen Fläche liegt."
                ),
                "ns_codes": list(codes),
            }
            for i, (name, label, codes, desc) in enumerate(BANDS)
        ],
    }


def main(force: bool = False) -> Path:
    inputs = [SOURCE, MAIN_TIF, Path(__file__)]
    fp_dir = contract.DERIVED_ANALYSE_RASTER
    if not force and OUT_TIF.exists() and OUT_JSON.exists() and fingerprint.matches(fp_dir, inputs):
        print(f"[skip]  analyse-raster: Fingerabdruck unveraendert -> {OUT_TIF}", flush=True)
        return OUT_TIF

    with rasterio.open(MAIN_TIF) as src:
        profile = src.profile.copy()
        bounds = src.bounds
    profile["count"] = len(BANDS)
    transform = profile["transform"]
    height, width = profile["height"], profile["width"]

    stack = np.zeros((len(BANDS), height, width), dtype=np.uint8)
    pf = pq.ParquetFile(SOURCE)
    for i in range(pf.num_row_groups):
        t = pf.read_row_group(i, columns=["source_layer", "ns", "geometry"])
        mask = pc.and_(pc.is_in(t["source_layer"], pa_array(SOURCE_LAYERS)), pc.is_in(t["ns"], pa_array(ALL_CODES)))
        t = t.filter(mask)
        if t.num_rows:
            geoms = shapely.from_wkb(t["geometry"].to_numpy(zero_copy_only=False))
            burn_geometries(stack, geoms, t["ns"].to_pylist(), transform)
        if i % 50 == 0:
            print(f"  Zeilengruppe {i}/{pf.num_row_groups}", flush=True)

    OUT_TIF.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(OUT_TIF, "w", **profile) as dst:
        for b in range(len(BANDS)):
            dst.write(stack[b], b + 1)
            dst.set_band_description(b + 1, BANDS[b][0])
    manifest = build_manifest(profile, bounds, MAIN_TIF, _sha256(MAIN_TIF))
    OUT_JSON.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fingerprint.write(fp_dir, inputs)
    print(f"[done]  analyse-raster -> {OUT_TIF}", flush=True)
    return OUT_TIF


def pa_array(values):
    import pyarrow as pa

    return pa.array(values, type=pa.string())


if __name__ == "__main__":
    main(force="--force" in sys.argv[1:])
