"""N1_natur_ebenen: die UBA-Schutzgebietsebenen, die den Ausschluss Natur bilden.

ACHTUNG, Ausnahme von der TIF-only-Regel: die Gebietszahlen sind Zaehlungen im
prep-Produkt ``derived/prep/natur/schutzgebiete.parquet`` (Spalten ``layer``,
``KAT``, ``KAT_SUB``, ``quelle``, ``geometry``; eine Zeile je Quell-Feature mit
Originalgeometrie), das aus dem Datensatz Schutzgebiete Oesterreich (Umweltbundesamt,
SG_AT_2024, Stand April 2024) gebaut wird; keine TIF-Ergebnisse. Ob und wie solche
Eingabezaehlungen in ``make whitepaper`` laufen duerfen, ist noch nicht entschieden
(siehe ``docs/whitepaper/OFFENE_ZAHLEN.md``).

Ebenen und Teilmenge ergeben sich aus dem prep-Produkt (nur genutzte Ebenen, nur
verordnete S-Kategorien). Langnamen der KAT_SUB-Codes: UBA-Codeliste
``Schutzgebietskategorien_Oesterreich_Stand_April_2024.xlsx`` (Blatt mit Spalten
KAT/KAT_Name/SUB_KAT/SUB_KAT_Name), hier fest hinterlegt. Fehlt ein Name, steht
der Code in der Zelle.
"""
from __future__ import annotations

from pathlib import Path

from . import wp_common as wc
from . import zahlen as Z

HERKUNFT_MARKER = "## N1_natur_ebenen (UBA-Schutzgebietsebenen)"
QUELLE = "Umweltbundesamt [7]"

# Deutsche Ebenennamen (Praefix des Layernamens vor ``_AT_2024``).
LAYER_NAMES = {
    "NP": "Nationalparks",
    "NSG": "Naturschutzgebiete",
    "ESG": "Europaschutzgebiete (Natura 2000)",
    "RAMSAR": "Ramsar-Gebiete",
    "LSG": "Landschaftsschutzgebiete",
    "GLT": "Geschützte Landschaftsteile",
    "NDKM": "Naturdenkmäler",
    "S": "Sonstige Schutzgebiete (nur verordnete Kategorien)",
}

# Langnamen (Spalte SUB_KAT_Name der UBA-Codeliste, KAT = S).
KAT_SUB_NAMES = {
    "RG": "Ruhegebiet",
    "RZ": "Ruhezone",
    "PSG": "Pflanzenschutzgebiet",
    "SSG": "Sonderschutzgebiet",
    "SAFM": "§ 24 NSG: Schutz von Auwäldern, Feuchtgebieten und Magerwiesen",
    "SG §26": "§ 26 NSG: Schutzgebiete",
    "GB": "geschütztes Biotop",
    "GLR": "geschützter Landschaftsraum",
    "GNÖB": "geschütztes Naturgebilde von örtlicher Bedeutung",
    "ÖE": "Ökologische Entwicklungsfläche",
    "ÖSG": "Örtliche Schutzgebiete",
}


def layer_key(layer: str) -> str:
    return layer.removesuffix("_AT_2024").lower()


def layer_label(layer: str) -> str:
    return LAYER_NAMES.get(layer.removesuffix("_AT_2024"), layer)


def count_layers(gdf) -> list[dict]:
    """Je Ebene des prep-Produkts: Gebietszahl, Punkte (nur NDKM) und Teilzahlen je KAT_SUB (nur S).

    Das Produkt enthaelt nur die genutzten Ebenen und die gefilterten S-Zeilen; es wird
    deshalb nur gruppiert. Anzeigereihenfolge fest (LAYER_NAMES, KAT_SUB_NAMES), Unbekanntes
    folgt danach mit seinem Code als Namen (Warnung, kein Fehler)."""
    import warnings

    present = [str(x) for x in gdf["layer"].unique()]
    order = [f"{k}_AT_2024" for k in ("NP", "NSG", "ESG", "RAMSAR", "LSG", "GLT", "S", "NDKM")]
    unknown = sorted(set(present) - set(order))
    for u in unknown:
        warnings.warn(f"natur_ebenen: unbekannte Ebene {u!r}, Code dient als Name", stacklevel=2)
    out = []
    for layer in [x for x in order if x in present] + unknown:
        sub = gdf[gdf["layer"] == layer]
        entry = {"layer": layer, "n": int(len(sub)), "n_points": None, "subs": []}
        if layer == "S_AT_2024":
            vc = sub["KAT_SUB"].value_counts()
            codes = [c for c in KAT_SUB_NAMES if c in vc.index] + sorted(c for c in vc.index if c not in KAT_SUB_NAMES)
            entry["subs"] = [(c, int(vc[c])) for c in codes]
        if layer.startswith("NDKM"):
            entry["n_points"] = int(sub.geometry.geom_type.isin(["Point", "MultiPoint"]).sum())
        out.append(entry)
    return out


def build_rows(entries: list[dict]) -> list[list[str]]:
    rows = []
    for e in entries:
        art = layer_label(e["layer"])
        if e["n_points"] is not None:
            art += " (Flächen und Punkte)"
        rows.append([QUELLE, art, wc.de_int(e["n"]) + (
            f", davon {wc.de_int(e['n_points'])} Punkte" if e["n_points"] is not None else "")])
        for code, n in e["subs"]:
            rows.append(["", f"davon {KAT_SUB_NAMES.get(code, code)}", wc.de_int(n)])
    return rows


def run(out_root: Path, schutzgebiete: Path) -> list[dict]:
    from pipeline.runtime import read_vector

    entries = count_layers(read_vector(schutzgebiete))
    out_dir = Path(out_root) / "tabellen"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows(entries)
    prov = (f"{QUELLE}: Schutzgebiete Österreich (SG_AT_2024), Stand 03.04.2024; "
            "Gebietszahl = Datensätze je Ebene (Zählung der Eingabedaten, nicht aus dem TIF).")
    wc.write_markdown_table(out_dir / "N1_natur_ebenen.md", "N1", ["Quelle", "Schutzgebietsart", "Gebiete"],
                            rows, prov)
    # Titelzeile entfernen: die Tabelle wird per {{tab:...}} direkt eingebunden (wie S2)
    p = out_dir / "N1_natur_ebenen.md"
    p.write_text("\n".join(p.read_text(encoding="utf-8").split("\n")[2:]), encoding="utf-8")
    csv_rows = []
    for e in entries:
        csv_rows.append([e["layer"], "", e["n"], "" if e["n_points"] is None else e["n_points"]])
        csv_rows += [[e["layer"], c, n, ""] for c, n in e["subs"]]
    wc.write_csv_table(out_dir / "N1_natur_ebenen.csv", ["layer", "kat_sub", "gebiete", "davon_punkte"],
                       csv_rows, [prov])
    herk = out_dir / "HERKUNFT.md"
    base = herk.read_text(encoding="utf-8") if herk.exists() else "# HERKUNFT — White-Paper-Analyse\n"
    base = base.split(HERKUNFT_MARKER)[0]
    sec = [HERKUNFT_MARKER, "",
           f"- Eingabe: prep-Produkt `{wc.rel_path(schutzgebiete)}` (Original: Umweltbundesamt, "
           "Schutzgebiete Österreich SG_AT_2024, Stand 03.04.2024), nur gelesen",
           "- Ebenen und Teilmengen: wie im prep-Produkt enthalten (Gruppierung nach `layer`, bei S nach `KAT_SUB`)",
           "- AUSNAHME von der TIF-only-Regel: Zählung von Eingabedaten (Entscheidung Jan offen, "
           "siehe `OFFENE_ZAHLEN.md`)",
           "- Langnamen der KAT_SUB-Codes: UBA-Codeliste (Schutzgebietskategorien Österreich, Stand April 2024), "
           "fest in `natur_ebenen.py`", ""]
    herk.write_text(base.rstrip("\n") + "\n\n" + "\n".join(sec), encoding="utf-8")
    for e in entries:
        k = layer_key(e["layer"])
        Z.register(f"uba_n_{k}", e["n"], "Gebiete", "N1_natur_ebenen (Zählung UBA-Eingabedaten)")
        if e["n_points"] is not None:
            Z.register(f"uba_n_{k}_punkte", e["n_points"], "Punkte", "N1_natur_ebenen (Zählung UBA-Eingabedaten)")
        for code, n in e["subs"]:
            Z.register(f"uba_n_{k}_{Z.slug(code)}", n, "Gebiete", "N1_natur_ebenen (Zählung UBA-Eingabedaten)")
    return entries

