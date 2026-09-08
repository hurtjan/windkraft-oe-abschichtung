"""Dashboard: manifest-getriebener Prüfbericht über die Bänder der
Abschichtung (Paket W4.1, docs/rewrite/PLAN.md §7).

## Was dieses Werkzeug ist - und was nicht

Der eigentliche interaktive Viewer für das Widmung-v2-Ergebnis lebt nicht
in diesem Repo, sondern auf der Konsumentenseite ("Dashboard-Repo",
``scripts/band_manifest.py`` auf Branch ``feat/band-manifest`` dort - siehe
``docs/HANDOFF.md``). Dieses Modul ist die **Prüfstufe** der Welle 4
(``pipeline/export/``): es liest ``out/abschichtung.bands.json`` und
schreibt einen Bericht (JSON + HTML) unter ``out/dashboard/``, der zeigt,
was im Manifest steht, gruppiert nach ``rolle`` (WAS ein Band ist -
Bedingung, Aggregat, Verfügbarkeit, Unschärfe, Referenz) und nach
``category`` (die Anzeige-Gruppierung des Manifests selbst, z. B. Mensch/
Natur/Geografie), und prüft das Manifest auf innere Widersprüche sowie
optional gegen den Kopf des zugehörigen GeoTIFF.

## Der eigentliche Auftrag: keine Bandnamen im Code

``docs/rewrite/PLAN.md`` §3 (Produkttabelle) über genau dieses Produkt:
"liest ausschließlich das Manifest, nie eine fest verdrahtete Bandliste.
Genau daran ist der heutige Dashboard-Builder gescheitert." Gemeint ist
``scripts/analysis/build_v2_dashboard_data.py`` (gelöscht in W1.5, siehe
Git-Historie) - dessen ``EXCLUSION_LAYERS``-Dict listet ~20 Bandnamen der
ALTEN 63-Band-Kette wörtlich im Code (``settlement_v2_buffer``,
``ferienhaus_tourismus_buffer``, ``wien_full_exclusion``,
``power_380_400kv``, ...). Keiner dieser Namen existiert im heutigen
38-Band-Schema - genau das Symptom, das §13.6 dieses Projekts meint: eine
Bandliste, die an zwei Stellen lebt (Code UND Manifest), läuft auseinander,
ohne dass es auffällt, bis ein Konsument bricht.

Dieses Modul enthält deshalb **keinen einzigen wörtlichen Bandnamen**.
Wo gruppiert wird, geschieht das über die ``rolle``-Werte aus dem
Manifest-Schema 2.0.0 (``bedingung``, ``aggregat_kategorie``,
``aggregat_gesamt``, ``verfuegbarkeit_roh``, ``verfuegbarkeit_bereinigt``,
``unschaerfe``, ``referenz``) - das sind Schema-Vokabular, keine Bandnamen,
genauso wie ``category`` und die ``_wirkungspfad``-Konvention (siehe
``_impact_path_keys()`` unten) Schema-Vokabular sind. Jeder Bandname, der
in diesem Modul vorkommt, kommt zur Laufzeit aus der geladenen JSON-Datei.
Beleg: eine Suche über dieses Modul nach den Bandnamen aus dem echten
Manifest findet keinen Treffer, und der Härtetest in der Abnahme (fremdes
Manifest, andere Bandzahl, andere Namen, unverändertes Modul) läuft durch.

## Bewusst NICHT aus dem alten Skript übernommen (mit Begründung)

``scripts/analysis/build_v2_dashboard_data.py`` (s.o.) konnte mehr als
dieses Modul. Bewusst nicht übernommen, weil es entweder hartes
Bandnamen-Wissen gebraucht hätte, eine fremde Zuständigkeit berührt, oder
eine externe Quelle brauchte, die hier nicht deklariert ist (Regel 4:
Zahlen unverändert übernehmen oder eben nicht neu erfinden):

- **Fläche je Band in km², gesamt und je Bundesland (63×9-Matrix).** Das
  alte Skript liest dafür jede Zelle des Rasters (voller Bandpass, ~37 s)
  und rastert zusätzlich die Verwaltungsgrenzen aus ``pipeline/prep/admin``
  (fremde Zuständigkeit, "Braucht", nicht "Besitzt" - siehe PLAN.md §7).
  Ohne Bundesland-Aufschlüsselung bräuchte dieses Modul nur den TIF-Kopf
  (Bandzahl/-namen), keinen vollen Pixel-Scan - genau das ist die
  Grenze, an der "liest ausschließlich das Manifest" (§3) endet und ein
  Pixel-Scan beginnt. Wer die Flächenzahlen braucht: die Fläche jedes
  Bandes lässt sich aus ``out/abschichtung.tif`` mit demselben
  Zählverfahren wie ``pipeline/validate.py:measure_bands`` ableiten - das
  Werkzeug existiert bereits (W3.2), muss hier nicht dupliziert werden.
- **Marginale Ausschlussfläche je Kriterium + 3er-Venn Mensch/Natur/
  Geografie.** Wäre über ``rolle`` und ``abgeleitet_von`` prinzipiell
  manifest-getrieben nachbaubar (die Mitglieder jeder Gruppe stehen im
  ``abgeleitet_von`` der ``aggregat_kategorie``-Bänder), bräuchte dafür
  aber ebenfalls einen vollen Pixel-Scan über alle Bedingungsbänder
  gleichzeitig - Analyse, keine Prüfung. Gehört eher zu einem künftigen
  ``scripts/analysis/``-Werkzeug als zur Verify-Stufe.
- **Vergleich mit der Energiewerkstatt/IG-Windkraft-Studie 2023**
  (``STUDY_KM2``, ``STUDY_MW``, feste Zahlen je Bundesland) und die
  Windkraft-Leistungsdichte aus ``config.json``. Externe Referenzwerte
  ohne Bezug zum Manifest - eine andere Zuständigkeit als "prüft das
  Manifest".
- **Turbinendichte (MW/km²) aus der Pipeline-Konfiguration.** Gehört zur
  Analyse-Ebene, nicht zur Struktur-Prüfung des Manifests.

Was dieses Modul stattdessen NEU kann, weil das Manifest es hergibt und das
alte Skript es nicht hatte (Schema 1.0.0 kannte weder ``rolle`` noch
``quelle``/``abgeleitet_von``): Gruppierung nach Pipeline-Rolle, eine
Referenz-Integritätsprüfung (jede ``quelle``, jedes ``abgeleitet_von``, jede
``*_wirkungspfad``-Liste und jeder ``caveats[].affects.bands``-Index muss
auf etwas zeigen, das im Manifest tatsächlich existiert) und optional ein
Kopf-Abgleich gegen das GeoTIFF (Bandzahl und Bandreihenfolge - der Fehler,
den ``docs/HANDOFF.md`` als "die Falle" beschreibt: Bänder positionsbasiert
statt namensbasiert lesen).

## Kopf-Abgleich, nicht Pixel-Scan

``cross_check_raster()`` öffnet das GeoTIFF nur für seine Kopfdaten
(``rasterio.open`` liest Metadaten - Bandzahl, Bandbeschreibungen,
CRS/Transform/Shape - ohne eine einzige Pixelzeile zu dekodieren). Das ist
dieselbe Prüfung, die ``docs/HANDOFF.md`` unter "Wie ein Konsument korrekt
prüft" als Schritt 1 verlangt, hier automatisiert. Ist der Rasterpfad nicht
vorhanden oder ``--skip-raster`` gesetzt, läuft der Bericht trotzdem durch
- der Manifest-Teil ist vollständig eigenständig, das ist der Kern des
Härtetests in der Abnahme.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import time
from pathlib import Path

from pipeline import contract

try:
    import rasterio
except ImportError:  # pragma: no cover - rasterio ist eine harte Abhängigkeit
    # dieses Projekts (siehe pyproject.toml); der Fallback erlaubt trotzdem,
    # den reinen Manifest-Pfad ohne Geo-Stack zu testen (siehe Härtetest).
    rasterio = None


# ---------------------------------------------------------------------------
# Manifest laden und auf innere Konsistenz prüfen - keine Bandnamen, nur
# Schema-Struktur (Schlüssel, die es in JEDEM Manifest dieses Formats gibt,
# unabhängig von Bandzahl oder -namen).
# ---------------------------------------------------------------------------

def load_manifest(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _validate_manifest_shape(manifest: dict) -> list[str]:
    """Formale Konsistenz: passt band_count zu bands[], sind die Indizes
    lückenlos, sind die Namen eindeutig. Reine Struktur, kein Bandwissen."""
    problems: list[str] = []
    bands = manifest.get("bands", [])
    declared = manifest.get("band_count")
    if declared != len(bands):
        problems.append(
            f"band_count ({declared!r}) stimmt nicht mit der Länge von bands[] ({len(bands)}) überein"
        )
    indices = [b.get("index") for b in bands]
    if indices != list(range(1, len(bands) + 1)):
        problems.append("bands[].index ist nicht lückenlos 1..N in Reihenfolge")
    names = [b.get("name") for b in bands]
    if len(set(names)) != len(names):
        problems.append("bands[].name enthält Duplikate")
    if any(not n for n in names):
        problems.append("mindestens ein Band hat keinen (oder leeren) name")
    return problems


def _impact_path_keys(manifest: dict) -> list[str]:
    """Alle Top-Level-Schlüssel, die der ``..._wirkungspfad``-Konvention aus
    dem Manifest-Schema folgen (siehe calc/band_manifest.py,
    Schema-Historie - Schema 2.0.0 führte den ersten dieser Schlüssel ein,
    2.1.0 einen zweiten; der heutige Manifest-Erzeuger trägt dort inzwischen
    zwei solcher Schlüssel ein). Über das Namens-SUFFIX gefunden, nicht über
    eine feste Anzahl oder einen konkreten Bandnamen - ein fremdes Manifest
    mit einem anders benannten Wirkungspfad-Schlüssel (z. B.
    ``irgendwas_wirkungspfad``) wird genauso gefunden, unabhängig davon, wie
    das Band heißt, um das es geht, und unabhängig davon, wie viele solcher
    Schlüssel es gibt."""
    return [k for k, v in manifest.items() if k.endswith("_wirkungspfad") and isinstance(v, list)]


def _validate_references(manifest: dict) -> list[str]:
    """Zeigt jede Querverweisung im Manifest auf etwas, das dort tatsächlich
    existiert? Prüft nur Struktur (Existenz einer Referenz), nie den Inhalt
    eines konkreten Bandnamens."""
    problems: list[str] = []
    bands = manifest.get("bands", [])
    names = {b.get("name") for b in bands}
    indices = {b.get("index") for b in bands}
    source_keys = set(manifest.get("sources", {}).keys())

    for b in bands:
        band_label = f"Band {b.get('index')!r} ({b.get('name')!r})"
        for src_key in b.get("quelle") or []:
            if src_key not in source_keys:
                problems.append(f"{band_label}: quelle-Schlüssel {src_key!r} fehlt in sources")
        for dep in b.get("abgeleitet_von") or []:
            if dep not in names:
                problems.append(f"{band_label}: abgeleitet_von-Eintrag {dep!r} ist kein bekannter Bandname")

    for key in _impact_path_keys(manifest):
        for n in manifest[key]:
            if n not in names:
                problems.append(f"{key}: Eintrag {n!r} ist kein bekannter Bandname")

    for c in manifest.get("caveats", []) or []:
        affects = c.get("affects", {}) if isinstance(c.get("affects"), dict) else {}
        for idx in affects.get("bands", []) or []:
            if idx not in indices:
                problems.append(f"Caveat {c.get('id')!r}: betrifft unbekannten Band-Index {idx!r}")

    return problems


# ---------------------------------------------------------------------------
# Gruppierung - ausschließlich über Schema-Vokabular (rolle, category), nie
# über einen konkreten Bandnamen.
# ---------------------------------------------------------------------------

UNKNOWN_ROLE = "(ohne rolle)"
UNKNOWN_CATEGORY = "(ohne category)"


def _band_summary(b: dict) -> dict:
    return {
        "index": b.get("index"),
        "name": b.get("name"),
        "label_de": b.get("label_de"),
        "rolle": b.get("rolle") or UNKNOWN_ROLE,
        "category": b.get("category") or UNKNOWN_CATEGORY,
        "puffer_m": b.get("puffer_m"),
        "puffer_hinweis": b.get("puffer_hinweis"),
        "quelle_count": len(b.get("quelle") or []),
        "abgeleitet_von_count": len(b.get("abgeleitet_von") or []),
    }


def group_by_role(bands: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for b in bands:
        groups.setdefault(b.get("rolle") or UNKNOWN_ROLE, []).append(_band_summary(b))
    return groups


def group_by_category(bands: list[dict], category_order: list[str]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {cat: [] for cat in category_order}
    for b in bands:
        cat = b.get("category") or UNKNOWN_CATEGORY
        groups.setdefault(cat, []).append(_band_summary(b))
    return groups


# ---------------------------------------------------------------------------
# Optionaler Kopf-Abgleich gegen das GeoTIFF - Metadaten, keine Pixel.
# ---------------------------------------------------------------------------

def cross_check_raster(manifest: dict, raster_path: Path) -> dict:
    if rasterio is None:
        return {"checked": False, "reason": "rasterio nicht installiert"}
    if not raster_path.exists():
        return {"checked": False, "reason": f"{raster_path} nicht gefunden"}

    with rasterio.open(raster_path) as src:
        raster_count = src.count
        raster_names = [d for d in src.descriptions]

    manifest_names = [b.get("name") for b in manifest.get("bands", [])]
    band_count_match = raster_count == manifest.get("band_count")

    mismatches = []
    for i, (rn, mn) in enumerate(zip(raster_names, manifest_names), start=1):
        if rn != mn:
            mismatches.append({"index": i, "raster_name": rn, "manifest_name": mn})
    if len(raster_names) != len(manifest_names):
        mismatches.append(
            {
                "index": None,
                "raster_name": f"<{len(raster_names)} Bänder>",
                "manifest_name": f"<{len(manifest_names)} Bänder>",
            }
        )

    return {
        "checked": True,
        "raster_path": str(raster_path),
        "raster_band_count": raster_count,
        "manifest_band_count": manifest.get("band_count"),
        "band_count_match": band_count_match,
        "names_match": not mismatches,
        "mismatches": mismatches,
    }


# ---------------------------------------------------------------------------
# Bericht zusammensetzen
# ---------------------------------------------------------------------------

def build_report(manifest: dict, raster_path: Path | None) -> dict:
    bands = manifest.get("bands", [])
    problems = _validate_manifest_shape(manifest) + _validate_references(manifest)
    category_order = manifest.get("category_order") or sorted(
        {b.get("category") or UNKNOWN_CATEGORY for b in bands}
    )

    role_groups = group_by_role(bands)
    category_groups = group_by_category(bands, category_order)

    if raster_path is not None:
        raster_check = cross_check_raster(manifest, raster_path)
    else:
        raster_check = {"checked": False, "reason": "--skip-raster gesetzt bzw. kein Rasterpfad übergeben"}

    return {
        "dashboard_generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_manifest": {
            "schema_version": manifest.get("schema_version"),
            "generated_at": manifest.get("generated_at"),
            "pipeline": manifest.get("pipeline"),
            "band_schema": manifest.get("band_schema"),
            "raster_file": manifest.get("raster_file"),
            "band_count": manifest.get("band_count"),
        },
        "raster_meta": manifest.get("raster", {}),
        "validation": {"ok": not problems, "problems": problems},
        "raster_check": raster_check,
        "role_counts": {rolle: len(items) for rolle, items in role_groups.items()},
        "roles": role_groups,
        "category_order": category_order,
        "categories": category_groups,
        "sources": manifest.get("sources", {}),
        "caveats": manifest.get("caveats", []),
        "impact_paths": {k: manifest[k] for k in _impact_path_keys(manifest)},
        "bands": [_band_summary(b) for b in bands],
    }


# ---------------------------------------------------------------------------
# Ausgabe: JSON (maschinenlesbar) + HTML (Übersicht für Menschen)
# ---------------------------------------------------------------------------

def write_json_report(out_dir: Path, report: dict) -> Path:
    out_path = out_dir / "report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def _e(value) -> str:
    return html.escape("" if value is None else str(value))


def _fmt_num(value) -> str:
    return "–" if value is None else _e(value)


def _render_validation_banner(report: dict) -> str:
    problems = report["validation"]["problems"]
    if not problems:
        return '<div class="banner ok">Manifest ist in sich konsistent — keine Probleme gefunden.</div>'
    items = "".join(f"<li>{_e(p)}</li>" for p in problems)
    return f'<div class="banner bad"><strong>{len(problems)} Problem(e) im Manifest:</strong><ul>{items}</ul></div>'


def _render_raster_check(report: dict) -> str:
    rc = report["raster_check"]
    if not rc.get("checked"):
        return f'<div class="banner neutral">Raster-Abgleich übersprungen: {_e(rc.get("reason"))}</div>'
    if rc["band_count_match"] and rc["names_match"]:
        return (
            f'<div class="banner ok">Raster-Kopf stimmt mit dem Manifest überein '
            f'({rc["raster_band_count"]} Bänder, Reihenfolge identisch): {_e(rc["raster_path"])}</div>'
        )
    rows = "".join(
        f"<tr><td>{_fmt_num(m['index'])}</td><td>{_e(m['raster_name'])}</td><td>{_e(m['manifest_name'])}</td></tr>"
        for m in rc["mismatches"]
    )
    return (
        f'<div class="banner bad"><strong>Raster und Manifest stimmen NICHT überein</strong> '
        f'({_e(rc["raster_path"])}): Raster hat {rc["raster_band_count"]} Bänder, '
        f'Manifest hat {rc["manifest_band_count"]}.'
        f'<table><tr><th>Index</th><th>Raster-Name</th><th>Manifest-Name</th></tr>{rows}</table></div>'
    )


def _render_role_table(report: dict) -> str:
    rows = "".join(
        f'<tr><td><code>{_e(rolle)}</code></td><td>{count}</td></tr>'
        for rolle, count in report["role_counts"].items()
    )
    return f'<table><tr><th>rolle</th><th>Bänder</th></tr>{rows}</table>'


def _render_bands_table(report: dict) -> str:
    rows = []
    for b in report["bands"]:
        rows.append(
            "<tr>"
            f'<td>{_fmt_num(b["index"])}</td>'
            f'<td>{_e(b["name"])}</td>'
            f'<td>{_e(b["label_de"])}</td>'
            f'<td><code>{_e(b["rolle"])}</code></td>'
            f'<td>{_e(b["category"])}</td>'
            f'<td>{_fmt_num(b["puffer_m"])}</td>'
            f'<td>{_e(b["puffer_hinweis"])}</td>'
            f'<td>{b["quelle_count"]}</td>'
            f'<td>{b["abgeleitet_von_count"]}</td>'
            "</tr>"
        )
    return (
        "<table><tr><th>#</th><th>name</th><th>label_de</th><th>rolle</th><th>category</th>"
        "<th>puffer_m</th><th>puffer_hinweis</th><th>#quelle</th><th>#abgeleitet_von</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _render_sources(report: dict) -> str:
    rows = "".join(
        f'<tr><td><code>{_e(k)}</code></td><td>{_e(v.get("pfad"))}</td>'
        f'<td>{_e(v.get("stand"))}</td><td>{_e(v.get("rolle"))}</td></tr>'
        for k, v in report["sources"].items()
    )
    return f'<table><tr><th>Schlüssel</th><th>Pfad</th><th>Stand</th><th>Rolle</th></tr>{rows}</table>'


def _render_caveats(report: dict) -> str:
    if not report["caveats"]:
        return "<p>Keine Caveats im Manifest.</p>"
    items = []
    for c in report["caveats"]:
        affects = c.get("affects", {})
        n_bands = len(affects.get("bands", [])) if isinstance(affects, dict) else 0
        items.append(
            f'<li><strong>{_e(c.get("id"))}</strong> '
            f'(<code>{_e(c.get("severity"))}</code>, betrifft {n_bands} Band/Bänder)<br>{_e(c.get("text_de"))}</li>'
        )
    return f'<ul class="caveats">{"".join(items)}</ul>'


def _render_impact_paths(report: dict) -> str:
    if not report["impact_paths"]:
        return "<p>Keine <code>*_wirkungspfad</code>-Felder im Manifest.</p>"
    items = []
    for key, names in report["impact_paths"].items():
        chips = "".join(f"<code>{_e(n)}</code>" for n in names)
        items.append(f"<li><strong>{_e(key)}</strong> ({len(names)} Bänder): {chips}</li>")
    return f'<ul>{"".join(items)}</ul>'


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Abschichtung — Manifest-Dashboard</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; margin: 2rem; color: #1a1a1a; }}
  h1, h2 {{ border-bottom: 1px solid #ddd; padding-bottom: .25rem; }}
  table {{ border-collapse: collapse; margin: .5rem 0 1.5rem; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: .25rem .5rem; text-align: left; font-size: .85rem; }}
  th {{ background: #f2f2f2; }}
  code {{ background: #f2f2f2; padding: 0 .25rem; border-radius: 3px; }}
  .banner {{ padding: .75rem 1rem; margin: .5rem 0 1rem; border-radius: 4px; }}
  .banner.ok {{ background: #e6f4ea; border: 1px solid #34a853; }}
  .banner.bad {{ background: #fce8e6; border: 1px solid #d93025; }}
  .banner.neutral {{ background: #f1f3f4; border: 1px solid #999; }}
  .meta {{ color: #555; font-size: .9rem; }}
  ul.caveats li {{ margin-bottom: .5rem; }}
</style>
</head>
<body>
<h1>Abschichtung — Manifest-Dashboard</h1>
<p class="meta">
  Erzeugt {generated_at} · Manifest-Schema {schema_version} · Pipeline {pipeline} / {band_schema} ·
  {band_count} Bänder · Raster {raster_file} ({crs}, {width}×{height}, {pixel_size} m)
</p>

<h2>Konsistenz des Manifests</h2>
{validation_banner}

<h2>Abgleich gegen das GeoTIFF</h2>
{raster_check}

<h2>Bänder nach rolle</h2>
{role_table}

<h2>Alle Bänder</h2>
{bands_table}

<h2>Caveats</h2>
{caveats}

<h2>Wirkungspfade (Felder auf *_wirkungspfad)</h2>
{impact_paths}

<h2>Quellen</h2>
{sources_table}

</body>
</html>
"""


def render_html(report: dict) -> str:
    raster_meta = report["raster_meta"]
    sm = report["source_manifest"]
    return HTML_TEMPLATE.format(
        generated_at=_e(sm.get("generated_at")),
        schema_version=_e(sm.get("schema_version")),
        pipeline=_e(sm.get("pipeline")),
        band_schema=_e(sm.get("band_schema")),
        band_count=_fmt_num(sm.get("band_count")),
        raster_file=_e(sm.get("raster_file")),
        crs=_e(raster_meta.get("crs")),
        width=_fmt_num(raster_meta.get("width")),
        height=_fmt_num(raster_meta.get("height")),
        pixel_size=_fmt_num(raster_meta.get("pixel_size_m")),
        validation_banner=_render_validation_banner(report),
        raster_check=_render_raster_check(report),
        role_table=_render_role_table(report),
        bands_table=_render_bands_table(report),
        caveats=_render_caveats(report),
        impact_paths=_render_impact_paths(report),
        sources_table=_render_sources(report),
    )


def write_html_report(out_dir: Path, report: dict) -> Path:
    out_path = out_dir / "index.html"
    out_path.write_text(render_html(report), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "W4.1: liest das Band-Manifest (nie eine fest verdrahtete Bandliste) und "
            "schreibt einen Pruefbericht (JSON + HTML) unter out/dashboard/. "
            "Siehe docs/rewrite/PLAN.md Paragraph 7 (W4.1) und Paragraph 3."
        )
    )
    p.add_argument("--manifest", default=None, help="Default: pipeline.contract.PRODUCTS['abschichtung_bands_json'].")
    p.add_argument("--raster", default=None, help="Default: pipeline.contract.PRODUCTS['abschichtung_tif'].")
    p.add_argument("--out", default=None, help="Default: pipeline.contract.PRODUCTS['dashboard_dir'].")
    p.add_argument(
        "--skip-raster",
        action="store_true",
        help="Raster-Kopf-Abgleich auslassen, auch wenn --raster bzw. der Default existiert.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest_path = Path(args.manifest) if args.manifest else contract.PRODUCTS["abschichtung_bands_json"]
    raster_path = Path(args.raster) if args.raster else contract.PRODUCTS["abschichtung_tif"]
    out_dir = Path(args.out) if args.out else contract.PRODUCTS["dashboard_dir"]

    if not manifest_path.exists():
        raise FileNotFoundError(f"{manifest_path} fehlt - 'make finalize' zuerst laufen lassen.")

    manifest = load_manifest(manifest_path)
    report = build_report(manifest, raster_path=None if args.skip_raster else raster_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = write_json_report(out_dir, report)
    html_path = write_html_report(out_dir, report)

    print(f"Manifest gelesen: {manifest_path} ({report['source_manifest']['band_count']} Bänder)")
    print("Bänder je rolle:")
    for rolle, count in report["role_counts"].items():
        print(f"  {rolle:<26} {count:>3}")
    rc = report["raster_check"]
    if rc.get("checked"):
        status = "OK" if rc["band_count_match"] and rc["names_match"] else "ABWEICHUNG"
        print(f"Raster-Abgleich: {status} ({rc['raster_path']})")
    else:
        print(f"Raster-Abgleich: übersprungen ({rc.get('reason')})")
    print(f"Geschrieben: {json_path}")
    print(f"Geschrieben: {html_path}")

    problems = report["validation"]["problems"]
    if problems:
        print(f"\n{len(problems)} Problem(e) im Manifest - siehe report.json['validation'].", file=sys.stderr)
        return 1
    if rc.get("checked") and not (rc["band_count_match"] and rc["names_match"]):
        print("\nRaster und Manifest stimmen nicht überein - siehe report.json['raster_check'].", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
