"""Gemeinsame Hilfsfunktionen fuer die White-Paper-Analyseskripte.

Eigenstaendig: keine Importe aus ``pipeline.*`` oder ``calc.*``. Wiederver-
wendet nur Logik (nicht Code) aus den Referenzskripten ``exklusiv.py`` /
``kriterien.py`` (Scratch-Verzeichnis) und aus
``pipeline/analysis/flaechenanteile.py`` (dort read-only gelesen, siehe
HERKUNFT.md) fuer die Bundesland-Maskierung.

Enthaelt:
- Manifest laden, Baender per Name aufloesen.
- Bundeslandgrenzen aus der Rohquelle laden (Dissolve nach ``BL``) und
  Zellmittelpunkt-Rasterisierung (``all_touched=False``), exakt wie
  ``pipeline/prep/admin.py`` (Dissolve) und
  ``pipeline/analysis/flaechenanteile.py`` (Rasterisierung) es tun.
- Regionenreihenfolge B, K, N, O, S, ST, T, V, W und volle Namen.
- Deutsche Zahlenformatierung (Dezimalkomma, NBSP als Tausendertrennzeichen).
- Herkunfts-Datensatz (TIF-Hash, Schema, Datum, Bezugsflaeche).
- Markdown-/CSV-Schreiber mit Quellenzeile bzw. Kommentarzeilen.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.windows import Window, transform as window_transform

# --- Region-Reihenfolge und volle Namen ------------------------------------

# Dieselbe Reihenfolge wie ``pipeline/analysis/flaechenanteile.py:STATE_CODES``
# (Dict-Reihenfolge dort ist bereits B, K, N, O, S, ST, T, V, W), hier als
# eigenstaendige Konstante, damit nichts importiert werden muss.
STATE_CODES: dict[str, str] = {
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

REGION_ORDER: list[str] = list(STATE_CODES.values())  # ["B","K","N","O","S","ST","T","V","W"]
REGION_ORDER_AT: list[str] = REGION_ORDER + ["AT"]

FULL_NAMES: dict[str, str] = {code: name for name, code in STATE_CODES.items()}
FULL_NAMES["AT"] = "Österreich"

TARGET_CRS = "EPSG:31287"

# Kanonische Labels fuer die drei Ueberschneidungs-Paarklassen. Reihenfolge der
# Paare folgt immer der Kategorienreihenfolge Mensch -> Natur -> Geografie
# (Textautor-Vorgabe 28.09.). Ueberall (Legenden, Klassenbeschriftungen,
# Tabellenzeilen, CSV-Labels, K-Texte) exakt so verwenden, siehe HERKUNFT.md.
LABEL_MENSCH_NATUR = "Mensch & Natur"
LABEL_MENSCH_GEOGRAFIE = "Mensch & Geografie"
LABEL_NATUR_GEOGRAFIE = "Natur & Geografie"


# --- Manifest / Baender -----------------------------------------------------

def load_manifest(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def band_index(manifest: dict, name: str) -> int:
    """Loest einen Bandindex ausschliesslich ueber den Namen im Manifest auf.

    Bricht mit einer klaren Fehlermeldung ab, wenn das Band fehlt.
    """
    for b in manifest["bands"]:
        if b["name"] == name:
            return int(b["index"])
    available = ", ".join(sorted(b["name"] for b in manifest["bands"]))
    raise KeyError(
        f"Band {name!r} nicht im Manifest gefunden. Vorhandene Baender: {available}"
    )


def band_by_index(manifest: dict, index: int) -> dict:
    for b in manifest["bands"]:
        if b["index"] == index:
            return b
    raise KeyError(f"Band-Index {index} nicht im Manifest gefunden.")


def family_member_indices(manifest: dict, familie: str, category: str) -> list[int]:
    """Alle Bandindizes einer Familie (z. B. 'verkehr'), sortiert.

    Wird fuer die Familien-Vereinigungen verkehr/luftfahrt/schutzgebiet
    verwendet - Aufloesung ausschliesslich ueber Manifest-Metadaten
    (``familie``/``category``), keine hartkodierten Indexlisten.
    """
    members = sorted(
        b["index"] for b in manifest["bands"]
        if b.get("familie") == familie and b.get("category") == category
    )
    if not members:
        raise KeyError(f"Familie {familie!r} (Kategorie {category!r}) hat keine Baender im Manifest.")
    return members


def zone_bands_for_categories(manifest: dict, categories: set[str]) -> list[dict]:
    """Alle Baender mit stufe == 'zone' in den angegebenen Kategorien, nach Index sortiert."""
    bands = [b for b in manifest["bands"] if b.get("stufe") == "zone" and b.get("category") in categories]
    bands.sort(key=lambda b: b["index"])
    return bands


# --- Hash / Datei-Helfer ----------------------------------------------------

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sha256(path: Path, expected: str | None) -> str:
    """Berechnet den sha256 und prueft ihn optional gegen ``expected``.

    Bricht mit klarer Fehlermeldung ab, wenn er nicht passt.
    """
    actual = sha256_of(path)
    if expected is not None and actual != expected:
        raise SystemExit(
            f"sha256-Mismatch fuer {path}: erwartet {expected}, tatsaechlich {actual}"
        )
    return actual


# --- Bundeslandgrenzen: Rohquelle laden, dissolvieren, rasterisieren -------

def load_bundeslaender(vgd_shp_path: Path) -> list[tuple[str, str, object]]:
    """Laedt die VGD-Rohquelle und dissolviert sie nach 'BL' - dieselbe

    Operation, die ``pipeline/prep/admin.py`` beim Bau von
    ``bundesland_masken.gpkg`` einmalig ausfuehrt (siehe dessen Quellcode,
    hier nachgebildet statt importiert). Liefert eine Liste
    ``(code, voller_name, geometry)`` in fester Reihenfolge B, K, N, O, S,
    ST, T, V, W.
    """
    vgd_shp_path = Path(vgd_shp_path)
    if not vgd_shp_path.is_file():
        raise FileNotFoundError(f"Bundeslandgrenzen-Rohquelle fehlt: {vgd_shp_path}")
    gdf = gpd.read_file(vgd_shp_path)
    if "BL" not in gdf.columns:
        raise ValueError(f"{vgd_shp_path}: erwartete Spalte 'BL' fehlt.")
    if gdf.crs is None or str(gdf.crs).upper() != TARGET_CRS:
        gdf = gdf.to_crs(TARGET_CRS)

    dissolved = gdf.dissolve(by="BL").reset_index()[["BL", "geometry"]]

    regions_by_code: dict[str, tuple[str, str, object]] = {}
    seen: set[str] = set()
    for name, geom in zip(dissolved["BL"], dissolved.geometry, strict=True):
        name = str(name)
        if name not in STATE_CODES:
            raise ValueError(f"Unbekannter Bundeslandname in {vgd_shp_path}: {name!r}.")
        if name in seen:
            raise ValueError(f"Bundesland kommt mehrfach vor: {name!r}.")
        if geom is None or geom.is_empty or not geom.is_valid:
            raise ValueError(f"Ungueltige oder leere Geometrie fuer {name!r}.")
        seen.add(name)
        code = STATE_CODES[name]
        regions_by_code[code] = (code, name, geom)

    if seen != set(STATE_CODES):
        missing = sorted(set(STATE_CODES) - seen)
        raise ValueError(f"{vgd_shp_path}: erwartet 9 Bundeslaender; fehlend: {', '.join(missing)}.")

    return [regions_by_code[code] for code in REGION_ORDER]


def make_region_raster(regions, shape, transform) -> tuple[np.ndarray, dict[int, tuple[str, str]]]:
    """Rasterisiert die 9 Bundeslaender nach Zellmittelpunkt (all_touched=False).

    ``codes``: raster_code (1..9) -> (region_code, voller_name), in der
    Reihenfolge von ``regions`` (also B..W). 0 = ausserhalb aller Laender.
    """
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


def iter_windows(height: int, width: int, block_rows: int):
    """Blockweise Fenster ueber die volle Rasterbreite, Zeilen von oben nach unten."""
    for row_off in range(0, height, block_rows):
        h = min(block_rows, height - row_off)
        yield row_off, h, Window(0, row_off, width, h)


def block_transform(dataset_transform, window):
    return window_transform(window, dataset_transform)


# --- Deutsche Zahlenformatierung --------------------------------------------

NBSP = " "


def de_num(x: float, decimals: int = 1) -> str:
    """Deutsche Zahl: Dezimalkomma, NBSP als Tausendertrennzeichen."""
    if x != x:  # NaN
        return "–"
    sign = "-" if x < 0 else ""
    x = abs(x)
    s = f"{x:,.{decimals}f}"  # z. B. "83,879.05" (en-US-Gruppierung)
    integer_part, _, frac_part = s.partition(".")
    integer_part = integer_part.replace(",", NBSP)
    return f"{sign}{integer_part},{frac_part}" if decimals else f"{sign}{integer_part}"


def de_int(x: int) -> str:
    s = f"{int(x):,d}"
    return s.replace(",", NBSP)


# --- Herkunft ---------------------------------------------------------------

@dataclass
class Provenance:
    tif_path: Path
    tif_sha256: str
    manifest_schema_version: str
    manifest_band_schema: str
    tif_date: str  # YYYY-MM-DD
    tif_date_source: str  # "manifest:generated_at" oder "mtime"
    reference_area_cells: int
    reference_area_km2: float
    grenzen_path: Path
    pixel_area_m2: float

    def reference_area_text(self) -> str:
        km2 = de_num(self.reference_area_km2, 2)
        return f"Summe der Bundesland-Masken (Zellmittelpunkt), {km2} km²"

    def source_line(self) -> str:
        sha_short = self.tif_sha256[:12]
        return (
            f"Quelle: Abschichtung, TIF sha256 {sha_short}…, Stand {self.tif_date}. "
            f"Bezugsflaeche: {self.reference_area_text()}."
        )

    def figure_source_line(self) -> str:
        sha_short = self.tif_sha256[:12]
        return f"Daten: Abschichtung, TIF sha256 {sha_short}, Stand {self.tif_date}"

    def as_dict(self) -> dict:
        return {
            "tif_path": str(self.tif_path),
            "tif_sha256": self.tif_sha256,
            "tif_sha256_short": self.tif_sha256[:12],
            "manifest_schema_version": self.manifest_schema_version,
            "manifest_band_schema": self.manifest_band_schema,
            "tif_date": self.tif_date,
            "tif_date_source": self.tif_date_source,
            "reference_area_cells": self.reference_area_cells,
            "reference_area_km2": self.reference_area_km2,
            "grenzen_path": str(self.grenzen_path),
            "pixel_area_m2": self.pixel_area_m2,
        }


def build_provenance(
    tif_path: Path,
    manifest: dict,
    grenzen_path: Path,
    reference_area_cells: int,
    pixel_area_m2: float,
    tif_sha256: str,
) -> Provenance:
    generated_at = manifest.get("generated_at")
    if generated_at:
        tif_date = str(generated_at)[:10]
        tif_date_source = "manifest:generated_at"
    else:
        import datetime

        mtime = Path(tif_path).stat().st_mtime
        tif_date = datetime.date.fromtimestamp(mtime).isoformat()
        tif_date_source = "mtime"

    return Provenance(
        tif_path=Path(tif_path),
        tif_sha256=tif_sha256,
        manifest_schema_version=str(manifest.get("schema_version", "")),
        manifest_band_schema=str(manifest.get("band_schema", "")),
        tif_date=tif_date,
        tif_date_source=tif_date_source,
        reference_area_cells=reference_area_cells,
        reference_area_km2=reference_area_cells * pixel_area_m2 / 1e6,
        grenzen_path=Path(grenzen_path),
        pixel_area_m2=pixel_area_m2,
    )


# --- Markdown-/CSV-Schreiber -------------------------------------------------

def write_markdown_table(
    out_path: Path,
    title: str,
    header: list[str],
    rows: list[list[str]],
    source_line: str,
    intro_lines: list[str] | None = None,
) -> None:
    lines = [f"# {title}", ""]
    if intro_lines:
        lines.extend(intro_lines)
        lines.append("")
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append(f"*Quelle: {source_line}*")
    lines.append("")
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")


def write_csv_table(
    out_path: Path,
    header: list[str],
    rows: list[list],
    comment_lines: list[str],
) -> None:
    with Path(out_path).open("w", newline="", encoding="utf-8") as fh:
        for c in comment_lines:
            fh.write(f"# {c}\n")
        w = csv.writer(fh)
        w.writerow(header)
        for row in rows:
            w.writerow(row)


# --- Determinismus -----------------------------------------------------------

MPL_SVG_HASHSALT = "abschichtung-whitepaper-2026"
