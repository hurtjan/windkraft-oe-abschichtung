"""Prep: Gelände und Wind (docs/rewrite/PLAN.md §7 W1.P6, Auflösung in §13.5).

Seit der prep-Grenze (CLAUDE.md) ist diese Stufe der EINZIGE Leser der beiden
Rohraster (``DGM_R25.tif``, ``AUT_power-density_150m.tif``) und liefert der
Layer-Stufe zwei GeoTIFFs exakt auf dem Zielraster (EPSG:31287, 25 m,
24001 x 14001 Zellen, Transform/Ausdehnung des DGM):

- ``dgm.tif`` - das Geländemodell. Das Zielraster ist per Definition das
  Gitter der DGM-Rohdatei; ``load_grid()`` (calc/abschichtung_common.py) liest
  Transform/Form/CRS jetzt aus dieser Datei, nicht mehr aus ``data/``.
- ``wind_pd_150.tif`` - die Leistungsdichte 150 m. Die Rohdatei liegt in
  EPSG:4326 (0,0025 Grad), also NICHT auf dem Zielraster; sie wird hier
  einmal nach EPSG:31287 gebracht.

Beide Produkte entstehen mit exakt derselben Resampling-Logik, die vorher bei
jedem Layer-Lauf in ``_read_raster_on_grid()`` steckte (``rasterio.warp.
reproject``, bilinear, ``src_nodata`` = Nodata der Quelle, ``dst_nodata`` =
NaN, float32). Die Layer-Stufe bekommt dadurch dieselben Arrays wie früher
(Voraussetzung für die Byte-Identität von ``out/abschichtung.tif``). Nodata
wird als NaN im Produkt gespeichert; Kompression: Deflate + Gleitkomma-
Prädiktor, verlustfrei.

Zielgitter (PLAN.md §13.5): EPSG:31287, 25 m, 24001 × 14001 Zellen. Das
ist keine freie Erfindung - ``DGM_R25.tif`` IST die Vorlage, aus der die
gesamte Kette ihr Rasterraster ableitet. Die Konstanten unten sind der
festgeschriebene Sollwert; weicht das DGM davon ab, bricht diese Stufe ab
(anders als bis W1.P6, wo die Abweichung nur ein Befund im Bericht war: seit
die Stufe selbst auf das Zielgitter bringt, wäre ein abweichendes DGM-Gitter
ein stiller Gitterwechsel der ganzen Kette). Daneben schreibt die Stufe den
Prüfbericht ``pruefbericht.md`` und den Fingerabdruck
(``pipeline/fingerprint.py``) nach ``contract.PREP["gelaende"]``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import contract, fingerprint, runtime  # noqa: E402
from pipeline.prep.share import skip_without_raw

REPORT_FILENAME = "pruefbericht.md"

# Zielgitter, siehe Moduldocstring.
TARGET_CRS = "EPSG:31287"
TARGET_RESOLUTION_M = 25.0
TARGET_WIDTH = 24001
TARGET_HEIGHT = 14001
# Ausdehnung des heutigen DGM_R25.tif (das Gitter, aus dem die Kette ihr
# Zielraster tatsächlich ableitet) - als Referenz mitgeführt, weil CRS +
# Auflösung + Zellenzahl allein den Ursprung (Nordwest-Ecke) nicht
# festlegen; zwei Raster können dieselben drei Werte haben und trotzdem
# gegeneinander verschoben sein.
TARGET_BOUNDS_M = (99987.5, 249987.5, 700012.5, 600012.5)
_BOUNDS_TOLERANCE_M = 0.01


@dataclass(frozen=True)
class RasterProfile:
    """Tatsächlich gemessene Eigenschaften einer Rasterdatei."""

    path: Path
    crs: str | None
    resolution: tuple[float, float]
    width: int
    height: int
    bounds: tuple[float, float, float, float]
    band_count: int
    dtypes: tuple[str, ...]
    nodata: float | None


def read_profile(path: Path) -> RasterProfile:
    """Öffnet ``path`` und liest CRS, Auflösung, Ausdehnung, Bandzahl,
    Datentyp und Nodata. Ein Lesefehler hier ist ein echter Fehler dieser
    Stufe (Datei fehlt oder ist kein gültiges Raster) und propagiert."""
    with rasterio.open(path) as ds:
        return RasterProfile(
            path=path,
            crs=ds.crs.to_string() if ds.crs else None,
            resolution=(float(ds.res[0]), float(ds.res[1])),
            width=ds.width,
            height=ds.height,
            bounds=(
                float(ds.bounds.left),
                float(ds.bounds.bottom),
                float(ds.bounds.right),
                float(ds.bounds.top),
            ),
            band_count=ds.count,
            dtypes=tuple(ds.dtypes),
            nodata=ds.nodata,
        )


def _close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def grid_matches_target(p: RasterProfile) -> dict[str, bool]:
    """Vergleicht die gemessenen Gitter-Eigenschaften gegen das Zielgitter.

    Nur die drei in §13.5 genannten Merkmale (CRS, Auflösung, Zellenzahl)
    plus die Ausdehnung (siehe TARGET_BOUNDS_M-Kommentar) fließen in
    "passt/passt nicht" ein - Bandzahl, Datentyp und Nodata werden im
    Bericht nur mitgeteilt, das Zielgitter aus §13.5 macht dazu keine
    Vorgabe.
    """
    return {
        "crs": p.crs == TARGET_CRS,
        "resolution": (
            _close(p.resolution[0], TARGET_RESOLUTION_M, 1e-6)
            and _close(p.resolution[1], TARGET_RESOLUTION_M, 1e-6)
        ),
        "width": p.width == TARGET_WIDTH,
        "height": p.height == TARGET_HEIGHT,
        "bounds": all(
            _close(a, b, _BOUNDS_TOLERANCE_M) for a, b in zip(p.bounds, TARGET_BOUNDS_M)
        ),
    }


def _fmt_num(x: float) -> str:
    return f"{x:.6g}"


def _profile_section(label: str, p: RasterProfile) -> str:
    checks = grid_matches_target(p)
    all_ok = all(checks.values())
    status = "passt zum Zielgitter" if all_ok else "WEICHT vom Zielgitter ab"
    # Einheit hängt vom gemessenen CRS ab - EPSG:31287 misst in Metern,
    # ein geografisches CRS (z. B. EPSG:4326) in Grad. Auflösung und
    # Ausdehnung eines geografischen Rasters als "m" auszuweisen wäre
    # falsch, auch wenn die Zahl selbst korrekt gemessen ist.
    unit = "m" if p.crs == TARGET_CRS else "Einheiten des Quell-CRS (kein Meter!)"
    lines = [
        f"### {label}",
        "",
        f"Datei: `{p.path}`",
        "",
        f"**Ergebnis: {status}**",
        "",
        "| Merkmal | gemessen | Zielgitter | passt? |",
        "|---|---|---|---|",
        f"| CRS | {p.crs} | {TARGET_CRS} | {'ja' if checks['crs'] else 'NEIN'} |",
        (
            f"| Auflösung (x, y) | "
            f"{_fmt_num(p.resolution[0])} {unit}, {_fmt_num(p.resolution[1])} {unit} | "
            f"{TARGET_RESOLUTION_M:g} m | {'ja' if checks['resolution'] else 'NEIN'} |"
        ),
        f"| Breite (Zellen) | {p.width} | {TARGET_WIDTH} | {'ja' if checks['width'] else 'NEIN'} |",
        f"| Höhe (Zellen) | {p.height} | {TARGET_HEIGHT} | {'ja' if checks['height'] else 'NEIN'} |",
        (
            f"| Ausdehnung (l, b, r, o), {unit} | "
            f"{', '.join(_fmt_num(v) for v in p.bounds)} | "
            f"{', '.join(_fmt_num(v) for v in TARGET_BOUNDS_M)} (m) | "
            f"{'ja' if checks['bounds'] else 'NEIN'} |"
        ),
        "",
        "Nur informativ, kein Sollwert in §13.5:",
        "",
        f"- Bänder: {p.band_count}",
        f"- Datentyp je Band: {', '.join(p.dtypes)}",
        f"- Nodata: {p.nodata!r}",
        "",
    ]
    return "\n".join(lines)


def build_report(
    profiles: dict[str, RasterProfile], products: dict[str, RasterProfile] | None = None
) -> str:
    header = [
        "# Prüfbericht: Gelände und Wind (W1.P6)",
        "",
        (
            "Diese Stufe bringt die beiden Rohraster auf das Zielgitter "
            f"(EPSG:31287, 25 m, {TARGET_WIDTH} × {TARGET_HEIGHT} Zellen) und "
            "schreibt sie als GeoTIFF (`dgm.tif`, `wind_pd_150.tif`) nach "
            "`derived/prep/gelaende/`. Resampling: bilinear, wie früher beim "
            "Lesen in der Layer-Stufe; Nodata = NaN. Abschnitt 1: die Rohraster, "
            "Abschnitt 2: die Produkte."
        ),
        "",
    ]
    if any(not all(grid_matches_target(p).values()) for p in profiles.values()):
        header.append(
            "Mindestens ein Rohraster liegt nicht auf dem Zielgitter (erwartet "
            "für die Leistungsdichte: EPSG:4326, 0,0025 Grad) und wurde "
            "deshalb hier umgerechnet."
        )
    else:
        header.append("Beide Rohraster liegen bereits auf dem Zielgitter.")
    header.append("")

    parts = ["\n".join(header), "## 1. Rohraster\n"]
    parts += [_profile_section(label, p) for label, p in profiles.items()]
    if products:
        parts.append("## 2. Produkte (derived/prep/gelaende/)\n")
        parts += [_profile_section(label, p) for label, p in products.items()]
    return "\n".join(parts)


def resample_to_grid(path: Path, transform, crs, shape: tuple[int, int]) -> np.ndarray:
    """Bringt Band 1 von ``path`` auf das Zielraster - exakt die Logik des
    früheren ``abschichtung_common._read_raster_on_grid()`` (bilinear,
    src_nodata = Nodata der Quelle, dst_nodata = NaN, float32)."""
    arr = np.full(shape, np.nan, dtype=np.float32)
    with rasterio.open(path) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=arr,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=crs,
            resampling=Resampling.bilinear,
            src_nodata=src.nodata,
            dst_nodata=np.nan,
        )
    return arr


def write_target_raster(path: Path, arr: np.ndarray, transform, crs) -> None:
    """Schreibt ``arr`` (float32, NaN = Nodata) als verlustfrei komprimiertes,
    gekacheltes GeoTIFF auf das Zielraster."""
    runtime.ensure_parent(path)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=arr.shape[0],
        width=arr.shape[1],
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=np.nan,
        tiled=True,
        blockxsize=256,
        blockysize=256,
        compress="zstd",
        predictor=3,
    ) as dst:
        dst.write(arr, 1)


def build_products(dgm_raw: Path, wind_raw: Path, dgm_out: Path, wind_out: Path) -> None:
    """Erzeugt dgm.tif und wind_pd_150.tif. Das Zielraster (Transform, CRS,
    Form) ist das der DGM-Rohdatei."""
    with rasterio.open(dgm_raw) as tmpl:
        transform, crs, shape = tmpl.transform, tmpl.crs, (tmpl.height, tmpl.width)
    for raw, out in ((dgm_raw, dgm_out), (wind_raw, wind_out)):
        arr = resample_to_grid(raw, transform, crs, shape)
        write_target_raster(out, arr, transform, crs)
        del arr
        print(f"[done]  prep-gelaende: {out}", flush=True)


def run(force: bool = False) -> Path:
    """Liest beide Rohraster aus ``contract.RAW["gelaende"]``, schreibt
    ``dgm.tif`` und ``wind_pd_150.tif`` (auf dem Zielraster), den Prüfbericht
    und den Fingerabdruck nach ``contract.PREP["gelaende"]``.

    Schreibt nirgends nach ``data/`` - nur lesender Zugriff auf die
    Rohraster, alle Schreibzugriffe gehen nach ``derived/prep/gelaende/``.

    Selbst-Ueberspringer, gleiches Muster wie pipeline/prep/osm.py
    (run_extract/run_layers): ein wiederholter `make all` ohne
    Eingabeaenderung soll diese Stufe nicht neu rechnen (Punkt 52,
    docs/rewrite/PLAN.md). `force=True` (CLI: `--force`) erzwingt einen
    Neulauf.
    """
    out_dir = contract.PREP["gelaende"]
    if not force and skip_without_raw(
        "gelaende", list(contract.RAW["gelaende"].values()), hint="data/gelaende/ (DGM_R25.tif, AUT_power-density_150m.tif)"
    ):
        return out_dir / REPORT_FILENAME
    runtime.ensure_dir(out_dir)
    dgm_out = contract.PREP_FILES["gelaende"]["dgm"]
    wind_out = contract.PREP_FILES["gelaende"]["wind_pd_150"]

    inputs = {
        "DGM_R25.tif (Digitales Geländemodell)": contract.RAW["gelaende"]["dgm"],
        "AUT_power-density_150m.tif (Leistungsdichte 150 m)": contract.RAW["gelaende"]["wind_pd_150"],
    }
    # Path(__file__) zaehlt zum Fingerabdruck mit (W6.4, Punkt 45): eine
    # Aenderung an dieser Datei soll den Selbst-Ueberspringer aufheben, nicht
    # nur eine Aenderung an data/. Konservativ - nur die eigene Quelldatei,
    # nicht die Importe (siehe pipeline/fingerprint.py). Nicht Teil von
    # ``inputs`` (das ist die beschriftete Anzeige-Zuordnung fuer den
    # Bericht), sondern erst in ``input_paths``, dem tatsaechlichen
    # Fingerabdruck-Datensatz.
    input_paths = list(inputs.values()) + [Path(__file__)]
    report_path = out_dir / REPORT_FILENAME

    if (
        not force
        and report_path.exists()
        and dgm_out.exists()
        and wind_out.exists()
        and fingerprint.matches(out_dir, input_paths)
    ):
        print(f"[skip]  prep-gelaende: Fingerabdruck unveraendert -> {out_dir}", flush=True)
        return report_path

    profiles = {label: read_profile(path) for label, path in inputs.items()}
    dgm_profile = profiles["DGM_R25.tif (Digitales Geländemodell)"]
    if not all(grid_matches_target(dgm_profile).values()):
        raise SystemExit(
            f"[fehler] {dgm_profile.path} weicht vom Zielgitter ab "
            f"({grid_matches_target(dgm_profile)}) - das Zielraster der ganzen Kette "
            "wäre damit ein anderes. Abbruch."
        )

    build_products(
        contract.RAW["gelaende"]["dgm"], contract.RAW["gelaende"]["wind_pd_150"], dgm_out, wind_out
    )

    products = {
        "dgm.tif (Produkt)": read_profile(dgm_out),
        "wind_pd_150.tif (Produkt)": read_profile(wind_out),
    }
    report_text = build_report(profiles, products)
    report_path.write_text(report_text, encoding="utf-8")

    fingerprint.write(out_dir, input_paths)

    return report_path


if __name__ == "__main__":
    path = run(force="--force" in sys.argv[1:])
    print(f"Prüfbericht geschrieben: {path}")
