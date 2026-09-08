"""Prep: Gelände und Wind (docs/rewrite/PLAN.md §7 W1.P6, Auflösung in §13.5).

Widerspruch im Plan: §4 sagt, die Domäne ``gelaende`` brauche "kein Prep".
§7 sieht trotzdem dieses Paket vor. §13.5 löst das auf: **keine Umformung,
aber eine Prüfstufe**. Die beiden Rohraster (``DGM_R25.tif``,
``AUT_power-density_150m.tif``) liegen laut Anmerkung in §4 "bereits im
Zielgitter" - diese Stufe prüft, ob das tatsächlich stimmt, bevor die
Layer-Stufe es stillschweigend annimmt. Genau diese Sorte Annahme war in
diesem Projekt schon mehrfach unbemerkt falsch (§13.5).

Diese Stufe schreibt deshalb **keinen umgeformten Datensatz** - kein
Resampling, keine Reprojektion, kein neues TIF -, sondern einen
menschenlesbaren Prüfbericht (``pruefbericht.md``) und den gemeinsamen
Fingerabdruck (``pipeline/fingerprint.py``) nach
``contract.PREP["gelaende"]``. Weicht ein Raster vom Zielgitter ab, ist
das laut Auftrag ein **Befund, kein Fehler**: der Bericht hält die
Abweichung fest, diese Stufe ändert an den Rohdaten nichts und entscheidet
auch nicht, was mit der Abweichung geschieht - das ist laut Auftrag Sache
von Welle 2 (der Layer-Stufe, die die Raster tatsächlich liest). Diese
Stufe bricht deshalb bei einer Gitterabweichung NICHT ab - anders als der
Wortlaut der Abnahme-Spalte in PLAN.md §7 ("Bricht ab, wenn Gitter oder
CRS abweichen") nahelegt; siehe Bericht zu W1.P6 für die Einordnung dieses
Unterschieds. Ein Lesefehler (Datei fehlt, Raster nicht öffenbar) ist
dagegen ein echter Fehler dieser Stufe und bricht sehr wohl ab.

Zielgitter (PLAN.md §13.5): EPSG:31287, 25 m, 24001 × 14001 Zellen. Das
ist keine freie Erfindung dieser Datei - im heutigen Code
(``calc/abschichtung_common.py:load_grid``) IST ``DGM_R25.tif``
selbst die Vorlage, aus der die gesamte Kette ihr Rasterraster ableitet;
das Zielgitter ist also per Definition das Gitter der DGM-Datei. Diese
Konstanten hier sind der Schnappschuss dieses Gitters, damit die Prüfung
nicht bei jedem Lauf erneut gegen "sich selbst" prüft, sondern gegen einen
festgeschriebenen Sollwert.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import rasterio

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import contract, fingerprint, runtime  # noqa: E402

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


def build_report(profiles: dict[str, RasterProfile]) -> str:
    any_mismatch = any(not all(grid_matches_target(p).values()) for p in profiles.values())
    header = [
        "# Prüfbericht: Gelände und Wind (W1.P6)",
        "",
        (
            "Prüfstufe ohne Umformung (docs/rewrite/PLAN.md §13.5): kein "
            "Resampling, keine Reprojektion. Diese Stufe stellt die "
            "tatsächlich gemessenen Gitter-Eigenschaften der beiden "
            "Rohraster gegen das Zielgitter (EPSG:31287, 25 m, "
            f"{TARGET_WIDTH} × {TARGET_HEIGHT} Zellen)."
        ),
        "",
    ]
    if any_mismatch:
        header.append(
            "**Mindestens ein Raster weicht vom Zielgitter ab.** Das ist "
            "laut Auftrag ein Befund, kein Fehler: die Rohdaten wurden "
            "nicht verändert. Was mit der Abweichung geschieht (z. B. "
            "Reprojektion beim Lesen), entscheidet die Layer-Stufe "
            "(Welle 2) - siehe Abschnitt unten je Raster."
        )
    else:
        header.append("Beide Raster passen vollständig zum Zielgitter.")
    header.append("")

    sections = [_profile_section(label, p) for label, p in profiles.items()]
    return "\n".join(header) + "\n" + "\n".join(sections)


def run(force: bool = False) -> Path:
    """Liest beide Rohraster aus ``contract.RAW["gelaende"]``, schreibt den
    Prüfbericht und den Fingerabdruck nach ``contract.PREP["gelaende"]``.

    Schreibt nirgends nach ``data/`` - nur lesender Zugriff auf die
    Rohraster, alle Schreibzugriffe gehen nach ``derived/prep/gelaende/``.

    Selbst-Ueberspringer, gleiches Muster wie pipeline/prep/osm.py
    (run_extract/run_layers): ein wiederholter `make all` ohne
    Eingabeaenderung soll diese Stufe nicht neu rechnen (Punkt 52,
    docs/rewrite/PLAN.md). `force=True` (CLI: `--force`) erzwingt einen
    Neulauf.
    """
    out_dir = contract.PREP["gelaende"]
    runtime.ensure_dir(out_dir)

    inputs = {
        "DGM_R25.tif (Digitales Geländemodell)": contract.RAW["gelaende"]["dgm"],
        "AUT_power-density_150m.tif (Leistungsdichte 150 m)": contract.RAW["gelaende"]["wind_pd_150"],
    }
    input_paths = list(inputs.values())
    report_path = out_dir / REPORT_FILENAME

    if not force and report_path.exists() and fingerprint.matches(out_dir, input_paths):
        print(f"[skip]  prep-gelaende: Fingerabdruck unveraendert -> {out_dir}", flush=True)
        return report_path

    profiles = {label: read_profile(path) for label, path in inputs.items()}

    report_text = build_report(profiles)
    report_path.write_text(report_text, encoding="utf-8")

    fingerprint.write(out_dir, input_paths)

    return report_path


if __name__ == "__main__":
    path = run(force="--force" in sys.argv[1:])
    print(f"Prüfbericht geschrieben: {path}")
