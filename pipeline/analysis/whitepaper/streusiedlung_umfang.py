"""Umfang der Streusiedlungs-Erkennung (Abschnitt 3.1.2) direkt aus dem TIF.

Eingaben: Haupt-TIF, sein Manifest und die Bundeslandgrenzen-Rohquelle (nur
Regionszuordnung), wie ``zaehlen.py``. Keine Importe aus ``pipeline.*`` /
``calc.*``: Kreis-Dilatation (FFT, Kern wie ``calc/distance_engine.py``) und
4er-Nachbarschafts-Filter sind hier nachgebildet; Selbstpruefungen belegen
die Gleichheit mit dem TIF (Band 7 und Band 30 zellgenau rekonstruiert).

Kennzahlen:
  * Gruppen: 8-zusammenhaengende Komponenten von ``haeuser_im_gruenen_streusiedlung``
  * Gruppenflaeche ohne Abstand (Band 5)
  * 750-m-Zone um Band 5 (auf Staatsgebiet = Band 30 | 31 zugeschnitten)
  * nur durch Streusiedlungen ausgeschlossen: ``all_exclusions`` ohne diese Zone
  * Eignung >= 10 ha ohne Streusiedlungen minus Band 32 (Gewinn, plus Prozent)
  * Haeuser im Gruenen gesamt (Band 7), je Bundesland die drei Zonenwerte
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window, transform as wtransform
from scipy import ndimage
from scipy.signal import fftconvolve

from . import wp_common as wc
from . import zahlen as Z

BUFFER_M = 750.0
MIN_HA = 10.0
TILE = 2048
QUELLE = "streusiedlung_umfang (TIF-Baender haeuser_im_gruenen_*, all_exclusions, available_*)"

# Reihenfolge der Zeilen in S2: nach "nur durch Streusiedlungen" absteigend (wie bisheriger Text)


class StreuCheckError(RuntimeError):
    pass


def circular_kernel(buffer_m: float, cell_m: float) -> np.ndarray:
    r = buffer_m / cell_m
    e = int(math.ceil(r))
    y, x = np.ogrid[-e:e + 1, -e:e + 1]
    return ((x * x + y * y) <= (r * r + 1e-9)).astype(np.float32)


def dilate(base: np.ndarray, buffer_m: float, cell_m: float, tile: int = TILE) -> np.ndarray:
    """Kreis-Dilatation per FFT-Faltung (kachelweise, mit Halo)."""
    out = np.zeros(base.shape, dtype=bool)
    if not base.any():
        return out
    kernel = circular_kernel(buffer_m, cell_m)
    halo = kernel.shape[0] // 2
    h, w = base.shape
    for y0 in range(0, h, tile):
        y1 = min(h, y0 + tile)
        yh0, yh1 = max(0, y0 - halo), min(h, y1 + halo)
        for x0 in range(0, w, tile):
            x1 = min(w, x0 + tile)
            xh0, xh1 = max(0, x0 - halo), min(w, x1 + halo)
            sub = base[yh0:yh1, xh0:xh1]
            if not sub.any():
                continue
            conv = fftconvolve(sub.astype(np.float32), kernel, mode="same")
            out[y0:y1, x0:x1] = conv[y0 - yh0:y1 - yh0, x0 - xh0:x1 - xh0] > 0.5
    return out


def min_area_filter(mask: np.ndarray, cell_m: float, min_ha: float) -> np.ndarray:
    """Zusammenhaengende Flaechen (4er-Nachbarschaft) mit >= min_ha behalten."""
    if not mask.any():
        return np.zeros(mask.shape, dtype=bool)
    min_cells = int(np.ceil(min_ha * 10_000.0 / (cell_m * cell_m)))
    labels, n = ndimage.label(mask, structure=ndimage.generate_binary_structure(2, 1))
    counts = np.bincount(labels.ravel())
    keep = counts >= min_cells
    keep[0] = False
    return keep[labels]


def human_zone_names(manifest: dict) -> list[str]:
    return [b["name"] for b in manifest["bands"]
            if b.get("category") == "Mensch" and b.get("stufe") == "zone"
            and b["name"] != "haeuser_im_gruenen" and not b.get("is_total")]


def compute(bands: dict[str, np.ndarray], human_names: list[str], cell_m: float,
            region_raster: np.ndarray | None = None, region_codes: list[str] | None = None,
            buffer_m: float = BUFFER_M, min_ha: float = MIN_HA, tile: int = TILE,
            strict: bool = True, inside: np.ndarray | None = None) -> dict:
    """Reine Rechenlogik auf booleschen Arrays (testbar ohne TIF).

    ``bands``: Namen -> bool-Arrays. ``region_raster``: Werte 1..len(region_codes), 0 = aussen.
    Gibt Zellzahlen/Flaechen zurueck; ``checks`` enthaelt die Selbstpruefungen.
    """
    cell_km2 = cell_m * cell_m / 1e6
    b5 = bands["haeuser_im_gruenen_streusiedlung"]
    b7 = bands["haeuser_im_gruenen"]
    b30, b31, b32 = bands["all_exclusions"], bands["available_after_all_exclusions_raw"], bands["available_cleaned_min_10ha"]
    valid = b30 | b31
    res: dict = {"checks": {}}

    # Staatsgebiet (Zellmittelpunkt in einem Bundesland, wie zaehlen.py): nur berichtete Werte
    # werden darauf beschnitten; die Selbstpruefungen laufen ueber das volle Raster.
    ins = inside if inside is not None else np.ones(b5.shape, bool)
    b5i = b5 & ins
    _lab, n8 = ndimage.label(b5i, structure=np.ones((3, 3), bool))
    del _lab
    res["gruppen"] = int(n8)
    res["gruppenflaeche_km2"] = float(b5i.sum()) * cell_km2
    res["hig_gesamt_km2"] = float((b7 & ins).sum()) * cell_km2

    zone_s = dilate(b5, buffer_m, cell_m, tile)
    b34 = bands["haeuser_im_gruenen_ferienhaus"] | bands["haeuser_im_gruenen_widmung"]
    b7o = dilate(b34, buffer_m, cell_m, tile) | bands["haeuser_im_gruenen_noe_pdf"]
    res["checks"]["band7_abweichung_zellen"] = int(((b7o | zone_s) != b7).sum())
    zone_s &= valid
    res["zone_km2"] = float((zone_s & ins).sum()) * cell_km2

    h = b7o
    for n in human_names:
        h |= bands[n]
    h |= bands["exclusion_nature"] | bands["exclusion_geography"]
    h &= valid
    all_o = h
    res["checks"]["all_exclusions_abweichung_zellen"] = int(((all_o | zone_s) != b30).sum())
    res["checks"]["ohne_s_nicht_in_b30_zellen"] = int((all_o & ~b30).sum())
    marg = b30 & ~all_o
    res["nur_km2"] = float((marg & ins).sum()) * cell_km2

    res["checks"]["b32_abweichung_zellen"] = int((min_area_filter(b31, cell_m, min_ha) != b32).sum())
    cl_o = min_area_filter(valid & ~all_o, cell_m, min_ha)
    gain = cl_o & ~b32
    res["eignung_mit_km2"] = float((b32 & ins).sum()) * cell_km2
    res["eignung_ohne_km2"] = float((cl_o & ins).sum()) * cell_km2
    res["gewinn_km2"] = float((gain & ins).sum()) * cell_km2
    res["gewinn_pct"] = res["gewinn_km2"] / res["eignung_mit_km2"] * 100.0 if (b32 & ins).any() else float("nan")
    res["checks"]["eignung_ohne_s_verliert_zellen"] = int((b32 & ~cl_o).sum())

    if region_raster is not None:
        res["land"] = {c: {"zone_km2": float(zone_s[region_raster == k].sum()) * cell_km2,
                           "nur_km2": float(marg[region_raster == k].sum()) * cell_km2,
                           "gewinn_km2": float(gain[region_raster == k].sum()) * cell_km2}
                       for k, c in enumerate(region_codes or [], start=1)}
    res["_masks"] = (zone_s, marg, gain)  # fuer blockweise Regionszuordnung in run()
    if strict:
        bad = {k: v for k, v in res["checks"].items() if v != 0}
        if bad:
            raise StreuCheckError(f"Selbstpruefung der Streusiedlungs-Rekonstruktion verletzt: {bad}")
    return res


def _fmt(x: float, d: int = 0) -> str:
    from .render import format_de
    return format_de(x, d)


def build_tables(res: dict, prov_line: str, out_dir: Path) -> None:
    """S1 (Kennzahlen) und S2 (je Bundesland) als MD + CSV."""
    out_dir = Path(out_dir)
    s1 = [
        ("Erkannte Streusiedlungen (außerhalb Niederösterreichs)", res["gruppen"], "Gruppen", 0),
        ("Gruppenfläche ohne Abstand", res["gruppenflaeche_km2"], "km²", 0),
        ("750-m-Zone um die Streusiedlungen", res["zone_km2"], "km²", 0),
        ("davon nur durch Streusiedlungen ausgeschlossen", res["nur_km2"], "km²", 0),
        ("Eignungsfläche ab 10 ha, die ohne Streusiedlungs-Erkennung hinzukäme", res["gewinn_km2"], "km²", 0),
        ("dasselbe in % der heutigen Eignungsfläche ab 10 ha", res["gewinn_pct"], "%", 0),
        ("Häuser im Grünen gesamt, mit Abstand (Band 7)", res["hig_gesamt_km2"], "km²", 0),
    ]
    with (out_dir / "S1_streusiedlung.csv").open("w", encoding="utf-8", newline="") as f:
        f.write(f"# {prov_line}\nKennzahl,Wert,Einheit\n")
        for lab, v, u, _d in s1:
            f.write(f'"{lab}",{v!r},{u}\n')
    md = ["# S1 — Umfang der Streusiedlungs-Erkennung", "", "| Kennzahl | Wert | Einheit |", "|---|---|---|"]
    md += [f"| {lab} | {_fmt(v, d)} | {u} |" for lab, v, u, d in s1]
    md += ["", f"*{prov_line}*", ""]
    (out_dir / "S1_streusiedlung.md").write_text("\n".join(md), encoding="utf-8")

    land = res["land"]
    order = sorted(land, key=lambda c: -land[c]["nur_km2"])
    with (out_dir / "S2_streusiedlung_land.csv").open("w", encoding="utf-8", newline="") as f:
        f.write(f"# {prov_line}\nland_code,land,zone_km2,nur_km2,gewinn_km2\n")
        for c in order:
            d = land[c]
            f.write(f"{c},{wc.FULL_NAMES[c]},{d['zone_km2']!r},{d['nur_km2']!r},{d['gewinn_km2']!r}\n")
    md = ["| Land | 750-m-Zone | nur durch Streusiedlungen ausgeschlossen | Eignungsgewinn ohne Erkennung |",
          "|---|---|---|---|"]
    for c in order:
        d = land[c]
        md.append(f"| {wc.FULL_NAMES[c]} | {_fmt(d['zone_km2'])} | {_fmt(d['nur_km2'])} | {_fmt(d['gewinn_km2'])} |")
    md += ["", f"*{prov_line}*", ""]
    (out_dir / "S2_streusiedlung_land.md").write_text("\n".join(md), encoding="utf-8")


def register(res: dict) -> None:
    for key, wert, u in (
        ("streu_gruppen", res["gruppen"], "Anzahl"),
        ("streu_gruppenflaeche_km2", res["gruppenflaeche_km2"], "km²"),
        ("streu_zone_km2", res["zone_km2"], "km²"),
        ("streu_nur_km2", res["nur_km2"], "km²"),
        ("streu_gewinn_km2", res["gewinn_km2"], "km²"),
        ("streu_gewinn_pct", res["gewinn_pct"], "%"),
        ("streu_eignung_mit_km2", res["eignung_mit_km2"], "km²"),
        ("streu_eignung_ohne_km2", res["eignung_ohne_km2"], "km²"),
        ("hig_gesamt_km2", res["hig_gesamt_km2"], "km²"),
    ):
        Z.register(key, wert, u, QUELLE)
    for c, d in res.get("land", {}).items():
        for k, u in (("zone_km2", "km²"), ("nur_km2", "km²"), ("gewinn_km2", "km²")):
            Z.register(f"streu_land_{c.lower()}_{k}", d[k], u, QUELLE + ", Zellmittelpunkt-Zuordnung")


def run(tif_path: Path, manifest_path: Path, grenzen_path: Path, out_root: Path,
        tif_sha256: str, tif_date: str) -> Path:
    manifest = wc.load_manifest(manifest_path)
    cell_m = float(manifest["raster"]["pixel_size_m"])
    human = human_zone_names(manifest)
    need = ["haeuser_im_gruenen_streusiedlung", "haeuser_im_gruenen", "haeuser_im_gruenen_ferienhaus",
            "haeuser_im_gruenen_widmung", "haeuser_im_gruenen_noe_pdf", "all_exclusions",
            "available_after_all_exclusions_raw", "available_cleaned_min_10ha",
            "exclusion_nature", "exclusion_geography", *human]
    print(f"[streusiedlung_umfang] lese {len(need)} Baender ...")
    with rasterio.open(tif_path) as ds:
        bands = {n: ds.read(wc.band_index(manifest, n)).astype(bool) for n in need}
        height, width, transform = ds.height, ds.width, ds.transform
        regions = wc.load_bundeslaender(grenzen_path)
        codes = [c for c, _n, _g in regions]
        print("[streusiedlung_umfang] rechne Dilatationen und Rekonstruktion (mehrere Minuten) ...")
        inside = np.zeros((height, width), dtype=bool)
        for r0 in range(0, height, 1000):
            h_ = min(1000, height - r0)
            rr, _ = wc.make_region_raster(regions, (h_, width), wtransform(Window(0, r0, width, h_), transform))
            inside[r0:r0 + h_] = rr != 0
        res = compute(bands, human, cell_m, tile=TILE, inside=inside)
        zone_s, marg, gain = res.pop("_masks")
        per = {c: [0, 0, 0] for c in codes}
        for r0 in range(0, height, 1000):
            h_ = min(1000, height - r0)
            tr = wtransform(Window(0, r0, width, h_), transform)
            rr, _ = wc.make_region_raster(regions, (h_, width), tr)
            sl = slice(r0, r0 + h_)
            for k, c in enumerate(codes, start=1):
                m = rr == k
                per[c][0] += int(zone_s[sl][m].sum())
                per[c][1] += int(marg[sl][m].sum())
                per[c][2] += int(gain[sl][m].sum())
    ck = cell_m * cell_m / 1e6
    res["land"] = {c: {"zone_km2": v[0] * ck, "nur_km2": v[1] * ck, "gewinn_km2": v[2] * ck} for c, v in per.items()}
    prov = f"Abschichtung, TIF sha256 {tif_sha256[:12]}…, Stand {tif_date}."
    out_dir = Path(out_root) / "tabellen"
    build_tables(res, prov, out_dir)
    register(res)
    print(f"[streusiedlung_umfang] Gruppen {res['gruppen']}, Zone {res['zone_km2']:.1f} km², "
          f"nur {res['nur_km2']:.1f} km², Gewinn {res['gewinn_km2']:.1f} km² ({res['gewinn_pct']:.1f} %); "
          f"Checks {res['checks']}")
    return out_dir
