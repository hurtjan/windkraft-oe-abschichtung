"""L1_landnutzung: Landnutzung (Kataster Wald / Aecker, Wiesen, Weiden) in
Landesflaeche, Bestand und Potentialflaeche je Bundesland und Oesterreich.

Zahlen ausschliesslich aus den TIFs plus Manifesten:
- Haupt-TIF ``out/abschichtung.tif`` (Baender per Name: official_wind_zoning,
  wka_bestand_ausserhalb_zonen, available_cleaned_min_10ha),
- Analyse-Raster ``out/abschichtung_analyse.tif`` (kataster_wald,
  kataster_aecker_wiesen_weiden), gleiches Raster wie das Haupt-TIF.
Einzige Vektorquelle: BEV-Laendergrenzen (Zellmittelpunkt-Zuordnung), wie in
den uebrigen White-Paper-Skripten.

Bestand = official_wind_zoning UND/ODER wka_bestand_ausserhalb_zonen.
Potentialflaeche = available_cleaned_min_10ha UND NICHT Bestand.
"""
from __future__ import annotations

from pipeline import contract as _contract

import json
from pathlib import Path

import numpy as np
import rasterio

from . import wp_common as wc

BLOCK_ROWS = 1000
HERKUNFT_MARKER = "## L1_landnutzung (Landnutzungs-Tabelle)"
NBSP = wc.NBSP

# Reihenfolge der Zaehlgroessen (Schluessel)
KEYS = ["land", "land_wald", "land_c48", "bestand", "bestand_wald", "bestand_c48",
        "pot", "pot_wald", "pot_c48"]
MIN_BASE_KM2 = 0.5


class AnalyseRasterError(RuntimeError):
    pass


def check_analysis_raster(main_tif: Path, main_sha256: str, analyse_tif: Path,
                          analyse_manifest: Path) -> dict:
    """Bricht klar ab, wenn Analyse-Raster/-Manifest fehlen oder veraltet sind."""
    analyse_tif, analyse_manifest = Path(analyse_tif), Path(analyse_manifest)
    for p in (analyse_tif, analyse_manifest):
        if not p.exists():
            raise AnalyseRasterError(
                f"Analyse-Raster fehlt: {p}. Erst `make analyse-raster` bzw. "
                "`uv run python -m pipeline.analyse_raster` ausfuehren."
            )
    am = json.loads(analyse_manifest.read_text(encoding="utf-8"))
    ref = am.get("referenz", {}).get("sha256")
    if ref != main_sha256:
        raise AnalyseRasterError(
            f"Analyse-Raster veraltet: Manifest {analyse_manifest.name} referenziert Haupt-TIF "
            f"sha256 {ref}, aktuelles {Path(main_tif).name} hat {main_sha256}. "
            "Analyse-Raster neu erzeugen."
        )
    return am


def count_cells(main_tif: Path, main_manifest: dict, analyse_tif: Path, analyse_manifest: dict,
                grenzen_path: Path) -> tuple[dict[str, dict[str, int]], float]:
    """Zellen je Land (Schluessel KEYS) und Pixelflaeche in m2."""
    i_off = wc.band_index(main_manifest, "official_wind_zoning")
    i_wka = wc.band_index(main_manifest, "wka_bestand_ausserhalb_zonen")
    i_clean = wc.band_index(main_manifest, "available_cleaned_min_10ha")
    j_wald = wc.band_index(analyse_manifest, "kataster_wald")
    j_c48 = wc.band_index(analyse_manifest, "kataster_aecker_wiesen_weiden")

    regions = wc.load_bundeslaender(grenzen_path)
    codes = [c for c, _n, _g in regions]
    counters = {k: {c: 0 for c in codes} for k in KEYS}
    pixel_area_m2 = float(main_manifest["raster"]["pixel_size_m"]) ** 2

    with rasterio.open(main_tif) as ds, rasterio.open(analyse_tif) as da:
        if (ds.height, ds.width, ds.transform) != (da.height, da.width, da.transform):
            raise AnalyseRasterError("Analyse-Raster hat nicht das Raster des Haupt-TIF.")
        n_codes = len(codes) + 1
        for _row_off, block_h, window in wc.iter_windows(ds.height, ds.width, BLOCK_ROWS):
            wt = wc.block_transform(ds.transform, window)
            region_raster, raster_codes = wc.make_region_raster(regions, (block_h, ds.width), wt)
            flat = region_raster.ravel()
            m = ds.read(indexes=[i_off, i_wka, i_clean], window=window) == 1
            a = da.read(indexes=[j_wald, j_c48], window=window) == 1
            wald, c48 = a[0], a[1]
            bestand = m[0] | m[1]
            pot = m[2] & ~bestand
            masks = {
                "land": np.ones_like(bestand), "land_wald": wald, "land_c48": c48,
                "bestand": bestand, "bestand_wald": bestand & wald, "bestand_c48": bestand & c48,
                "pot": pot, "pot_wald": pot & wald, "pot_c48": pot & c48,
            }
            for k, mask in masks.items():
                cnt = np.bincount(flat, weights=mask.ravel(), minlength=n_codes)
                for ci in range(1, n_codes):
                    code = raster_codes.get(ci, (None, None))[0]
                    if code is not None:
                        counters[k][code] += int(round(cnt[ci]))
    for k in KEYS:
        counters[k]["AT"] = sum(counters[k][c] for c in codes)
    return counters, pixel_area_m2


def _share(part: float, base: float) -> float:
    return part / base * 100.0 if base >= MIN_BASE_KM2 else float("nan")


def build_rows(counters: dict, pixel_area_m2: float) -> list[dict]:
    """Zeilen (Oesterreich zuerst, dann Laender nach Landesflaeche absteigend)."""
    codes = [c for c in counters["land"] if c != "AT"]
    order = ["AT"] + sorted(codes, key=lambda c: -counters["land"][c])
    rows = []
    for code in order:
        v = {k: counters[k][code] * pixel_area_m2 / 1e6 for k in KEYS}
        s = {
            "land_pct": _share(v["land"], v["land"]),
            "land_wald_pct": _share(v["land_wald"], v["land"]),
            "land_c48_pct": _share(v["land_c48"], v["land"]),
            "bestand_pct": _share(v["bestand"], v["land"]),
            "bestand_wald_pct": _share(v["bestand_wald"], v["bestand"]),
            "bestand_c48_pct": _share(v["bestand_c48"], v["bestand"]),
            "pot_pct": _share(v["pot"], v["land"]),
            "pot_wald_pct": _share(v["pot_wald"], v["pot"]),
            "pot_c48_pct": _share(v["pot_c48"], v["pot"]),
        }
        rows.append({"code": code, "name": wc.FULL_NAMES[code], "km2": v, "pct": s})
    return rows


def _cell(km2_val: float, pct_val: float, decimals: int) -> str:
    if pct_val != pct_val:
        p = "–"
    else:
        d = 2 if (decimals == 1 and 0 < pct_val < 0.1) else decimals
        p = wc.de_num(pct_val, d)
    suffix = f" ({p}{NBSP}%)" if p != "–" else f" ({p})"
    return wc.de_num(km2_val, 1) + suffix


def build_table(rows: list[dict], prov_line: str, out_dir: Path) -> None:
    header = ["Land", "Landesfläche", "Wald", "C48", "Bestand", "Wald", "C48",
              "Potentialfläche", "Wald", "C48"]
    spec = [("land", "land_pct", 1), ("land_wald", "land_wald_pct", 0), ("land_c48", "land_c48_pct", 0),
            ("bestand", "bestand_pct", 1), ("bestand_wald", "bestand_wald_pct", 0),
            ("bestand_c48", "bestand_c48_pct", 0), ("pot", "pot_pct", 1),
            ("pot_wald", "pot_wald_pct", 0), ("pot_c48", "pot_c48_pct", 0)]
    md_rows = [[r["name"]] + [_cell(r["km2"][k], r["pct"][p], d) for k, p, d in spec] for r in rows]
    legend = [
        "Bestand = amtliche Windzonen (`official_wind_zoning`) oder Bestandsanlagen außerhalb der Zonen "
        "(`wka_bestand_ausserhalb_zonen`); Potentialfläche = Eignung ≥ 10 ha (`available_cleaned_min_10ha`) "
        "ohne Bestand. Prozent bei Landesfläche, Bestand und Potentialfläche: Anteil an der Landesfläche; "
        "bei Wald und C48: Anteil der links stehenden Fläche (\"–\" bei Bezugsfläche < 0,5 km²).",
        "Wald = Kataster-Nutzungscodes 56 und 55 (`kataster_wald`); C48 = Kataster-Code 48, Äcker, Wiesen, "
        "Weiden (`kataster_aecker_wiesen_weiden`); Flächen in km² (Zelle 0,000625 km²).",
    ]
    wc.write_markdown_table(out_dir / "L1_landnutzung.md",
                            "L1 — Landnutzung in Landesfläche, Bestand und Potentialfläche",
                            header, md_rows, prov_line, intro_lines=None)
    # Legende unter der Tabelle (zwei Zeilen) -> an die Datei anhaengen
    p = out_dir / "L1_landnutzung.md"
    txt = p.read_text(encoding="utf-8").rstrip("\n")
    p.write_text(txt + "\n\n" + legend[0] + "\n\n" + legend[1] + "\n", encoding="utf-8")

    csv_header = ["land_code", "land"] + [f"{k}_km2" for k in KEYS] + [p_ for _k, p_, _d in spec]
    csv_rows = []
    for r in rows:
        csv_rows.append([r["code"], r["name"]] + [repr(r["km2"][k]) for k in KEYS]
                        + ["" if r["pct"][p_] != r["pct"][p_] else repr(r["pct"][p_]) for _k, p_, _d in spec])
    wc.write_csv_table(out_dir / "L1_landnutzung.csv", csv_header, csv_rows, comment_lines=[prov_line])


def write_herkunft_section(out_dir: Path, main_tif: Path, main_sha: str, analyse_tif: Path,
                           analyse_sha: str, analyse_manifest_path: Path) -> None:
    """Haengt den L1-Abschnitt an HERKUNFT.md an (ersetzt einen vorhandenen)."""
    p = Path(out_dir) / "HERKUNFT.md"
    base = p.read_text(encoding="utf-8") if p.exists() else "# HERKUNFT — White-Paper-Analyse\n"
    if HERKUNFT_MARKER in base:
        base = base.split(HERKUNFT_MARKER)[0]
    sec = [
        HERKUNFT_MARKER, "",
        f"- Haupt-TIF: `{wc.rel_path(main_tif)}`, sha256 `{main_sha}`",
        f"- Analyse-Raster: `{wc.rel_path(analyse_tif)}`, sha256 `{analyse_sha}`, Manifest `{wc.rel_path(analyse_manifest_path)}` "
        "(referenziert den sha256 des Haupt-TIF; Abbruch bei Abweichung)",
        "- Baender per Name: `official_wind_zoning`, `wka_bestand_ausserhalb_zonen`, "
        "`available_cleaned_min_10ha` (Haupt-TIF); `kataster_wald`, `kataster_aecker_wiesen_weiden` (Analyse-Raster)",
        "- Bestand = official_wind_zoning ODER wka_bestand_ausserhalb_zonen; "
        "Potentialfläche = available_cleaned_min_10ha UND NICHT Bestand",
        "- Länderzuordnung: Zellmittelpunkt, BEV-Ländergrenzen wie oben (einzige Vektorquelle)",
        "",
    ]
    p.write_text(base.rstrip("\n") + "\n\n" + "\n".join(sec), encoding="utf-8")


def run(main_tif: Path, main_manifest_path: Path, grenzen_path: Path, out_root: Path,
        analyse_tif: Path, analyse_manifest_path: Path, main_sha256: str | None = None) -> Path:
    main_tif, analyse_tif = Path(main_tif), Path(analyse_tif)
    main_sha = main_sha256 or wc.sha256_of(main_tif)
    am = check_analysis_raster(main_tif, main_sha, analyse_tif, analyse_manifest_path)
    mm = wc.load_manifest(main_manifest_path)
    print("[landnutzung] zaehle Kataster-Klassen in Landesflaeche/Bestand/Potential ...")
    counters, pix = count_cells(main_tif, mm, analyse_tif, am, grenzen_path)
    rows = build_rows(counters, pix)
    analyse_sha = wc.sha256_of(analyse_tif)
    out_dir = Path(out_root) / "tabellen"
    out_dir.mkdir(parents=True, exist_ok=True)
    prov = (f"Abschichtung, TIF sha256 {main_sha[:12]}…, Analyse-Raster sha256 {analyse_sha[:12]}…, "
            f"Stand {str(mm.get('generated_at', ''))[:10]}.")
    build_table(rows, prov, out_dir)
    write_herkunft_section(out_dir, main_tif, main_sha, analyse_tif, analyse_sha, analyse_manifest_path)
    print(f"[landnutzung] geschrieben nach {out_dir}")
    return out_dir


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--tif", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--analyse-tif", required=True, type=Path)
    ap.add_argument("--analyse-manifest", required=True, type=Path)
    ap.add_argument("--grenzen", type=Path, default=_contract.PREP_FILES["admin"]["bundesland_masken"])
    ap.add_argument("--out-root", required=True, type=Path)
    a = ap.parse_args()
    run(a.tif, a.manifest, a.grenzen, a.out_root, a.analyse_tif, a.analyse_manifest)
