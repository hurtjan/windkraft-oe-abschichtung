"""Erzeugt alle White-Paper-Tabellen (Markdown + CSV) aus dem Zaehlen-Cache.

Liest ausschliesslich den von ``zaehlen.py`` geschriebenen Cache (Temp-
Verzeichnis). Alle Zahlen stammen ausschliesslich aus dem TIF plus Manifest;
die Bundeslandgrenzen-Rohquelle wird nur fuer die Zellmittelpunkt-Region-
Zuordnung (in ``zaehlen.py``/``wp_common.py``) und zum Zeichnen der
Kartenumrisse (``abbildungen.py``) verwendet. Schreibt Markdown- und
CSV-Dateien ausschliesslich nach ``docs/whitepaper/tabellen/``.
"""
from __future__ import annotations

from pipeline import contract as _contract

import json
import math
from pathlib import Path

from . import wp_common as wc

REGION_ORDER = wc.REGION_ORDER  # B K N O S ST T V W
REGION_ORDER_AT = wc.REGION_ORDER_AT


def load_cache(cache_dir: Path) -> tuple[dict, dict, dict]:
    cache_dir = Path(cache_dir)
    counts = json.loads((cache_dir / "counts.json").read_text(encoding="utf-8"))
    checks = json.loads((cache_dir / "checks.json").read_text(encoding="utf-8"))
    prov = json.loads((cache_dir / "provenance.json").read_text(encoding="utf-8"))
    return counts, checks, prov


def pct(cells: float, denom: float) -> float:
    return cells / denom * 100.0 if denom else float("nan")


def km2(cells: float, pixel_area_m2: float) -> float:
    return cells * pixel_area_m2 / 1e6


def item_row(counts: dict, key: str, decimals: int, as_km2: bool = False) -> list[str]:
    """Formatierte Werte je Region (B..W, AT) fuer einen Item-Key."""
    region_cells = counts["region_cells"]
    at_cells = counts["at_cells"]
    pixel_area_m2 = counts["pixel_area_m2"]
    counters = counts["counters"]
    at_counts = counts["at_counts"]
    out = []
    for code in REGION_ORDER:
        cells = counters[key][code]
        denom = region_cells[code]
        val = km2(cells, pixel_area_m2) if as_km2 else pct(cells, denom)
        out.append(wc.de_num(val, decimals))
    at_val = km2(at_counts[key], pixel_area_m2) if as_km2 else pct(at_counts[key], at_cells)
    out.append(wc.de_num(at_val, decimals))
    return out


# ---------------------------------------------------------------------------
# T1_haupttabelle
# ---------------------------------------------------------------------------

def build_t1(counts: dict, prov: dict, out_dir: Path) -> None:
    header = ["Groesse (% des Landes)"] + [wc.FULL_NAMES[c] for c in REGION_ORDER_AT]
    rows_md = []
    rows_csv = []

    def add_pct_row(label: str, key_or_fn):
        if isinstance(key_or_fn, str):
            vals_fmt = item_row(counts, key_or_fn, 1, as_km2=False)
            vals_raw = [
                pct(counts["counters"][key_or_fn][c], counts["region_cells"][c]) for c in REGION_ORDER
            ] + [pct(counts["at_counts"][key_or_fn], counts["at_cells"])]
        else:
            vals_raw = [key_or_fn(c) for c in REGION_ORDER_AT]
            vals_fmt = [wc.de_num(v, 1) for v in vals_raw]
        rows_md.append([label] + vals_fmt)
        rows_csv.append([label] + [f"{v:.6f}" for v in vals_raw])

    add_pct_row("Mensch", "exclusion_human")
    add_pct_row("nur Mensch", "nur_mensch")
    add_pct_row("Natur", "exclusion_nature")
    add_pct_row("nur Natur", "nur_natur")
    add_pct_row("Geografie", "exclusion_geography")
    add_pct_row("nur Geografie", "nur_geografie")
    add_pct_row("Ausschluss gesamt", "all_exclusions")
    add_pct_row("Eignung ≥ 10 ha", "available_cleaned_min_10ha")

    # zusaetzliche Zeile: Eignung in km^2
    def eign_km2(code):
        cells = counts["counters"]["available_cleaned_min_10ha"][code] if code != "AT" else counts["at_counts"]["available_cleaned_min_10ha"]
        return km2(cells, counts["pixel_area_m2"])

    vals_raw = [eign_km2(c) for c in REGION_ORDER_AT]
    rows_md.append(["Eignung in km²"] + [wc.de_num(v, 1) for v in vals_raw])
    rows_csv.append(["Eignung in km²"] + [f"{v:.6f}" for v in vals_raw])

    source_line = prov_source_line(prov)
    wc.write_markdown_table(
        out_dir / "T1_haupttabelle.md",
        "T1 — Haupttabelle: Ausschluss und Eignung je Bundesland",
        header, rows_md, source_line,
    )
    wc.write_csv_table(
        out_dir / "T1_haupttabelle.csv", header, rows_csv,
        comment_lines=[source_line],
    )


def prov_source_line(prov: dict) -> str:
    sha_short = prov["tif_sha256_short"]
    km2_txt = wc.de_num(prov["reference_area_km2"], 2)
    return (
        f"Abschichtung, TIF sha256 {sha_short}…, Stand {prov['tif_date']}. "
        f"Bezugsflaeche: Summe der Bundesland-Masken (Zellmittelpunkt), {km2_txt} km²."
    )


# ---------------------------------------------------------------------------
# K_kernzahlen
# ---------------------------------------------------------------------------

def build_k(counts: dict, prov: dict, out_dir: Path, zonen_km2: dict[str, float]) -> None:
    at_cells = counts["at_cells"]
    at_counts = counts["at_counts"]
    pixel_area_m2 = counts["pixel_area_m2"]
    region_cells = counts["region_cells"]
    counters = counts["counters"]

    rows = []  # (key, value_str, unit, note)

    ref_km2 = km2(at_cells, pixel_area_m2)
    rows.append(("Referenzflaeche AT", wc.de_num(ref_km2, 1), "km²",
                 "Summe der 9 Bundesland-Masken, Zellmittelpunkt"))

    eign_km2 = km2(at_counts["available_cleaned_min_10ha"], pixel_area_m2)
    eign_pct = pct(at_counts["available_cleaned_min_10ha"], at_cells)
    rows.append(("Eignung ≥ 10 ha", wc.de_num(eign_km2, 1), "km²", "AT"))
    rows.append(("Eignung ≥ 10 ha", wc.de_num(eign_pct, 1), "%", "AT, Anteil an Referenzflaeche"))

    ausschluss_km2 = km2(at_counts["all_exclusions"], pixel_area_m2)
    ausschluss_pct = pct(at_counts["all_exclusions"], at_cells)
    rows.append(("Ausschluss gesamt", wc.de_num(ausschluss_km2, 1), "km²", "AT"))
    rows.append(("Ausschluss gesamt", wc.de_num(ausschluss_pct, 1), "%", "AT, Anteil an Referenzflaeche"))

    frei_km2 = km2(at_counts["frei"], pixel_area_m2)
    frei_pct = pct(at_counts["frei"], at_cells)
    rows.append(("frei (roh, vor 10-ha-Filter)", wc.de_num(frei_km2, 1), "km²", "AT"))
    rows.append(("frei (roh, vor 10-ha-Filter)", wc.de_num(frei_pct, 1), "%", "AT, Anteil an Referenzflaeche"))

    klein_km2 = km2(at_counts["kleinflaechen"], pixel_area_m2)
    klein_pct = pct(at_counts["kleinflaechen"], at_cells)
    rows.append(("Kleinflaechen < 10 ha", wc.de_num(klein_km2, 1), "km²", "AT"))
    rows.append(("Kleinflaechen < 10 ha", wc.de_num(klein_pct, 1), "%", "AT, Anteil an Referenzflaeche"))

    # Abfolge, in % von AT
    nur_geografie_at = at_counts["nur_geografie"]
    frei_at = at_counts["frei"]
    union_hn_at = at_cells - nur_geografie_at - frei_at  # H union N, siehe Herleitung in HERKUNFT.md
    nach_mensch = 100.0 - pct(at_counts["exclusion_human"], at_cells)
    nach_natur = 100.0 - pct(union_hn_at, at_cells)
    nach_geografie = pct(at_counts["frei"], at_cells)
    nach_10ha = pct(at_counts["available_cleaned_min_10ha"], at_cells)
    rows.append(("Abfolge: nach Mensch", wc.de_num(nach_mensch, 1), "% von AT", "100 − Mensch"))
    rows.append(("Abfolge: nach Natur", wc.de_num(nach_natur, 1), "% von AT", "100 − (Mensch ∪ Natur)"))
    rows.append(("Abfolge: nach Geografie", wc.de_num(nach_geografie, 1), "% von AT", "= frei"))
    rows.append(("Abfolge: nach 10-ha-Filter", wc.de_num(nach_10ha, 1), "% von AT", "= Eignung"))

    # Anteil B+N an Eignungsflaeche
    eign_b = counters["available_cleaned_min_10ha"]["B"]
    eign_n = counters["available_cleaned_min_10ha"]["N"]
    share_bn = pct(eign_b + eign_n, at_counts["available_cleaned_min_10ha"])
    rows.append(("Anteil Burgenland + Niederoesterreich an Eignung", wc.de_num(share_bn, 1), "%",
                 "(Eignung_B + Eignung_N) / Eignung_AT"))

    # Anteil der Natur-Flaeche, die auch von Mensch oder Geografie ausgeschlossen ist
    natur_at = at_counts["exclusion_nature"]
    nur_natur_at = at_counts["nur_natur"]
    share_natur_overlap = pct(natur_at - nur_natur_at, natur_at)
    rows.append(("Anteil Natur auch durch Mensch/Geografie ausgeschlossen", wc.de_num(share_natur_overlap, 1), "%",
                 "(Natur − nur Natur) / Natur"))

    # Amtliche Windzonen
    for code in REGION_ORDER_AT:
        rows.append((f"Amtliche Windzone — {wc.FULL_NAMES[code]}", wc.de_num(zonen_km2[code], 1), "km²", "official_wind_zoning"))

    source_line = prov_source_line(prov)
    header = ["Kennzahl", "Wert", "Einheit", "Anmerkung"]
    wc.write_markdown_table(
        out_dir / "K_kernzahlen.md",
        "K — Kernzahlen",
        header, [list(r) for r in rows], source_line,
    )
    wc.write_csv_table(out_dir / "K_kernzahlen.csv", header, [list(r) for r in rows], comment_lines=[source_line])


# ---------------------------------------------------------------------------
# D1_exklusiv
# ---------------------------------------------------------------------------

D1_CLASS_KEYS = [
    "nur_mensch", "nur_natur", "nur_geografie",
    "mensch_natur", "mensch_geografie", "natur_geografie",
    "alle_drei", "frei",
]
D1_CLASS_LABELS = {
    "nur_mensch": "nur Mensch", "nur_natur": "nur Natur", "nur_geografie": "nur Geografie",
    "mensch_natur": wc.LABEL_MENSCH_NATUR, "mensch_geografie": wc.LABEL_MENSCH_GEOGRAFIE,
    "natur_geografie": wc.LABEL_NATUR_GEOGRAFIE, "alle_drei": "alle drei", "frei": "frei",
}


def build_d1(counts: dict, prov: dict, out_dir: Path) -> None:
    header = ["Klasse"] + [wc.FULL_NAMES[c] for c in REGION_ORDER_AT]

    pct_rows_md, pct_rows_csv = [], []
    km2_rows_md, km2_rows_csv = [], []
    for key in D1_CLASS_KEYS:
        label = D1_CLASS_LABELS[key]
        pvals_fmt = item_row(counts, key, 2, as_km2=False)
        pvals_raw = [pct(counts["counters"][key][c], counts["region_cells"][c]) for c in REGION_ORDER] + \
                    [pct(counts["at_counts"][key], counts["at_cells"])]
        pct_rows_md.append([label] + pvals_fmt)
        pct_rows_csv.append(["%", key, label] + [f"{v:.6f}" for v in pvals_raw])

        kvals_fmt = item_row(counts, key, 2, as_km2=True)
        kvals_raw = [km2(counts["counters"][key][c], counts["pixel_area_m2"]) for c in REGION_ORDER] + \
                    [km2(counts["at_counts"][key], counts["pixel_area_m2"])]
        km2_rows_md.append([label] + kvals_fmt)
        km2_rows_csv.append(["km2", key, label] + [f"{v:.6f}" for v in kvals_raw])

    source_line = prov_source_line(prov)
    lines = [
        f"# D1 — Exklusive 8-Klassen-Zerlegung je Bundesland", "",
        "## Anteil an der Landesflaeche (%)", "",
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
    ]
    for row in pct_rows_md:
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "## Flaeche (km²)", "",
              "| " + " | ".join(header) + " |",
              "|" + "|".join(["---"] * len(header)) + "|"]
    for row in km2_rows_md:
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", f"*Quelle: {source_line}*", ""]
    (out_dir / "D1_exklusiv.md").write_text("\n".join(lines), encoding="utf-8")

    csv_header = ["einheit", "klasse_key", "klasse_label"] + REGION_ORDER_AT
    wc.write_csv_table(
        out_dir / "D1_exklusiv.csv", csv_header, pct_rows_csv + km2_rows_csv,
        comment_lines=[source_line],
    )


# ---------------------------------------------------------------------------
# D2_kriterien
# ---------------------------------------------------------------------------

def build_d2(counts: dict, prov: dict, manifest: dict, out_dir: Path) -> None:
    zone_band_names = counts["zone_band_names"]
    by_name = {b["name"]: b for b in manifest["bands"]}

    items: list[tuple[str, str]] = [(n, str(by_name[n]["index"])) for n in zone_band_names]
    items += [
        ("verkehr", ",".join(str(i) for i in counts["fam_members"]["verkehr"])),
        ("luftfahrt", ",".join(str(i) for i in counts["fam_members"]["luftfahrt"])),
        ("schutzgebiet", ",".join(str(i) for i in counts["fam_members"]["schutzgebiet"])),
        ("exclusion_human", str(by_name["exclusion_human"]["index"])),
        ("exclusion_nature", str(by_name["exclusion_nature"]["index"])),
        ("exclusion_geography", str(by_name["exclusion_geography"]["index"])),
        ("all_exclusions", str(by_name["all_exclusions"]["index"])),
        ("frei", str(by_name["available_after_all_exclusions_raw"]["index"])),
        ("available_cleaned_min_10ha", str(by_name["available_cleaned_min_10ha"]["index"])),
    ]

    header = ["Band(er)", "Name"] + [wc.FULL_NAMES[c] for c in REGION_ORDER_AT]

    pct_rows_md, pct_rows_csv = [], []
    km2_rows_md, km2_rows_csv = [], []
    for key, band_col in items:
        pvals_fmt = item_row(counts, key, 2, as_km2=False)
        pvals_raw = [pct(counts["counters"][key][c], counts["region_cells"][c]) for c in REGION_ORDER] + \
                    [pct(counts["at_counts"][key], counts["at_cells"])]
        pct_rows_md.append([band_col, key] + pvals_fmt)
        pct_rows_csv.append(["%", band_col, key] + [f"{v:.6f}" for v in pvals_raw])

        kvals_fmt = item_row(counts, key, 2, as_km2=True)
        kvals_raw = [km2(counts["counters"][key][c], counts["pixel_area_m2"]) for c in REGION_ORDER] + \
                    [km2(counts["at_counts"][key], counts["pixel_area_m2"])]
        km2_rows_md.append([band_col, key] + kvals_fmt)
        km2_rows_csv.append(["km2", band_col, key] + [f"{v:.6f}" for v in kvals_raw])

    source_line = prov_source_line(prov)
    lines = ["# D2 — Bundesland x Kriterium (Einzelbaender, Familien, Kategorien, Ergebnis)", "",
             "## Anteil an der Landesflaeche (%)", "",
             "| " + " | ".join(header) + " |",
             "|" + "|".join(["---"] * len(header)) + "|"]
    for row in pct_rows_md:
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "## Flaeche (km²)", "",
              "| " + " | ".join(header) + " |",
              "|" + "|".join(["---"] * len(header)) + "|"]
    for row in km2_rows_md:
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", f"*Quelle: {source_line}*", ""]
    (out_dir / "D2_kriterien.md").write_text("\n".join(lines), encoding="utf-8")

    csv_header = ["einheit", "band", "name"] + REGION_ORDER_AT
    wc.write_csv_table(
        out_dir / "D2_kriterien.csv", csv_header, pct_rows_csv + km2_rows_csv,
        comment_lines=[source_line],
    )


# ---------------------------------------------------------------------------
# D3_eignung
# ---------------------------------------------------------------------------

def build_d3(counts: dict, prov: dict, out_dir: Path) -> None:
    header = ["Groesse"] + [wc.FULL_NAMES[c] for c in REGION_ORDER_AT]
    keys = [("Eignung ≥ 10 ha", "available_cleaned_min_10ha"),
            ("frei roh", "frei"),
            ("Kleinflaechen < 10 ha", "kleinflaechen")]

    pct_rows_md, km2_rows_md = [], []
    csv_rows = []
    for label, key in keys:
        pvals_fmt = item_row(counts, key, 2, as_km2=False)
        pvals_raw = [pct(counts["counters"][key][c], counts["region_cells"][c]) for c in REGION_ORDER] + \
                    [pct(counts["at_counts"][key], counts["at_cells"])]
        pct_rows_md.append([label] + pvals_fmt)
        csv_rows.append(["%", key, label] + [f"{v:.6f}" for v in pvals_raw])

        kvals_fmt = item_row(counts, key, 2, as_km2=True)
        kvals_raw = [km2(counts["counters"][key][c], counts["pixel_area_m2"]) for c in REGION_ORDER] + \
                    [km2(counts["at_counts"][key], counts["pixel_area_m2"])]
        km2_rows_md.append([label] + kvals_fmt)
        csv_rows.append(["km2", key, label] + [f"{v:.6f}" for v in kvals_raw])

    source_line = prov_source_line(prov)
    lines = ["# D3 — Eignung, frei roh, Kleinflaechen je Bundesland", "",
             "## Anteil an der Landesflaeche (%)", "",
             "| " + " | ".join(header) + " |",
             "|" + "|".join(["---"] * len(header)) + "|"]
    for row in pct_rows_md:
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "## Flaeche (km²)", "",
              "| " + " | ".join(header) + " |",
              "|" + "|".join(["---"] * len(header)) + "|"]
    for row in km2_rows_md:
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", f"*Quelle: {source_line}*", ""]
    (out_dir / "D3_eignung.md").write_text("\n".join(lines), encoding="utf-8")

    csv_header = ["einheit", "key", "label"] + REGION_ORDER_AT
    wc.write_csv_table(out_dir / "D3_eignung.csv", csv_header, csv_rows, comment_lines=[source_line])


# ---------------------------------------------------------------------------
# HERKUNFT.md
# ---------------------------------------------------------------------------

def build_herkunft(
    out_dir: Path,
    prov: dict,
    checks: dict,
    manifest_path: Path,
    grenzen_path: Path,
    at_full_grid_note: str,
) -> None:
    lines = ["# HERKUNFT — White-Paper-Analyse", ""]
    lines.append("## Eingaben")
    lines.append(f"- TIF: `{wc.rel_path(prov['tif_path'])}`, sha256 `{prov['tif_sha256']}`")
    lines.append(f"- Manifest: `{wc.rel_path(manifest_path)}` (schema_version {prov['manifest_schema_version']}, "
                 f"band_schema {prov['manifest_band_schema']})")
    lines.append(f"- Bundeslandgrenzen (prep-Produkt, nur fuer Regionszuordnung/Bezugsflaeche "
                 f"und Kartenumrisse): `{wc.rel_path(grenzen_path)}`")
    lines.append("")
    lines.append("## Bundeslandgrenzen (prep-Produkt)")
    lines.append(
        "Bundeslandgrenzen kommen aus dem prep-Produkt "
        "`derived/prep/admin/bundesland_masken.parquet` (`pipeline/prep/admin`, dissolve nach 'BL' "
        "aus der generalisierten Verwaltungsgrenzen-Datei VGD 50, BEV, Stand 02.10.2022, "
        "7850 Katastralgemeinde-Polygone, EPSG:31287, Spalte 'BL'). "
        "`pipeline/analysis/flaechenanteile.py:_load_regions/_make_region_raster` "
        "rasterisiert diese Maske per Zellmittelpunkt (all_touched=False). "
        "Diese Analyse liest das prep-Produkt direkt und "
        "bildet denselben Rasterisierungs-Schritt in `wp_common.py` eigenstaendig nach."
    )
    lines.append("")
    lines.append("## TIF-Datum")
    lines.append(
        f"Aus dem Manifest-Feld `generated_at` ({prov['tif_date_source']}): {prov['tif_date']} "
        "(stimmt mit dem Dateidatum des TIF ueberein)."
    )
    lines.append("")
    lines.append("## Bezugsflaeche")
    lines.append(
        f"Summe der Bundesland-Masken (Zellmittelpunkt): {wc.de_int(prov['reference_area_cells'])} Zellen "
        f"= {wc.de_num(prov['reference_area_km2'], 2)} km². {at_full_grid_note}"
    )
    lines.append("")
    lines.append("## Aufruf")
    lines.append("```")
    lines.append(
        "uv run python -m pipeline.analysis.whitepaper.run_all "
        f"--tif {wc.rel_path(prov['tif_path'])} --manifest {wc.rel_path(manifest_path)} "
        f"--grenzen {wc.rel_path(grenzen_path)}"
    )
    lines.append("```")
    lines.append("")
    lines.append("## Selbstpruefungen (zaehlen.py)")
    for k, v in checks.items():
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    (out_dir / "HERKUNFT.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------

def compute_official_zone_km2(counts: dict) -> dict[str, float]:
    pixel_area_m2 = counts["pixel_area_m2"]
    out = {}
    for code in REGION_ORDER:
        out[code] = km2(counts["counters"]["official_wind_zoning"][code], pixel_area_m2)
    out["AT"] = km2(counts["at_counts"]["official_wind_zoning"], pixel_area_m2)
    return out


def build_full_grid_note(counts: dict, manifest: dict) -> str:
    """J5: Text zur vollen Staatsgebietsmaske, berechnet aus dem TIF.

    Vereinigung der Baender ``all_exclusions`` und
    ``available_after_all_exclusions_raw`` (in ``zaehlen.py`` ueber das ganze
    Raster gebildet, mit Selbstpruefung, dass die Schnittmenge leer ist -
    siehe ``full_grid_union_intersection_cells`` unter Selbstpruefungen).
    """
    idx_all = wc.band_index(manifest, "all_exclusions")
    idx_raw = wc.band_index(manifest, "available_after_all_exclusions_raw")
    full_grid_cells = counts["full_grid_union_cells"]
    full_grid_km2 = km2(full_grid_cells, counts["pixel_area_m2"])
    return (
        f"Die volle Staatsgebietsmaske (all_touched-Zustandsmaske) wird aus dem TIF berechnet, "
        f"als Vereinigung von Band {idx_all} (all_exclusions) und Band {idx_raw} "
        f"(available_after_all_exclusions_raw); die Schnittmenge dieser beiden Baender ist "
        f"0 Zellen (Selbstpruefung, siehe unten). Ergebnis: "
        f"{wc.de_int(full_grid_cells)} Zellen = {wc.de_num(full_grid_km2, 2)} km²."
    )


def run(
    cache_dir: Path,
    manifest_path: Path,
    grenzen_path: Path,
    out_root: Path,
) -> Path:
    counts, checks, prov = load_cache(cache_dir)
    manifest = wc.load_manifest(manifest_path)

    tabellen_dir = Path(out_root) / "tabellen"
    tabellen_dir.mkdir(parents=True, exist_ok=True)

    zonen_km2 = compute_official_zone_km2(counts)

    build_t1(counts, prov, tabellen_dir)
    build_k(counts, prov, tabellen_dir, zonen_km2)
    build_d1(counts, prov, tabellen_dir)
    build_d2(counts, prov, manifest, tabellen_dir)
    build_d3(counts, prov, tabellen_dir)

    at_full_grid_note = build_full_grid_note(counts, manifest)
    build_herkunft(
        tabellen_dir, prov, checks, manifest_path, grenzen_path,
        at_full_grid_note,
    )

    print(f"[tabellen] geschrieben nach {tabellen_dir}")
    return tabellen_dir


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--grenzen", type=Path, default=_contract.PREP_FILES["admin"]["bundesland_masken"])
    ap.add_argument("--out-root", required=True, type=Path)
    args = ap.parse_args()
    run(args.cache_dir, args.manifest, args.grenzen, args.out_root)
