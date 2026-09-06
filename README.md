# Abschichtung Widmung v2

## Zweck

Dies ist ein neues, eigenständiges Repo für die Widmung-v2-Kette der
Windkraft-Potentialberechnung. Es wurde additiv neben dem alten, gewachsenen
Repo `windkraft_ö_karten` angelegt — das alte Repo bleibt unangetastet als
Sicherheitsnetz bestehen, bis dieses Repo einen verifizierten Lauf hinter
sich hat. Bis dahin ist `windkraft_ö_karten` die Quelle der Wahrheit.

## Struktur

- `windkraft/` — das Python-Paket mit der eigentlichen Berechnungslogik
  (`calc/` für die Kernberechnungen, `noe/` für niederösterreich-spezifische
  Quellenaufbereitung, `util/` für Hilfsfunktionen, `viz/` für
  Darstellungs-/Bandmetadaten wie `band_metadata.py`).
- `scripts/` — dünne CLI-Einstiegspunkte, die auf das Paket aufsetzen:
  `widmung_v2/` (die fünf nummerierten Kettenschritte), `noe/`
  (Niederösterreich-Datenaufbereitung), `preprocessing/` (einmalige
  Datenaufbereitung), `analysis/` und `webmap/` (Auswertungs- und
  Inspektionswerkzeuge, z. B. der Layer-Viewer).
- `docs/` — Nachschlagedokumentation: `widmung_v2.md` (Referenzkarte der
  Kette), `widmung_v2_provenance.md` (Provenienz), `FOLLOWUPS.md` (offene
  Beobachtungen aus der Übernahme), `MIGRATION_MAP.tsv` (alte → neue Pfade),
  `analysis/` (Herleitungs-Dokumentation einzelner Verfahren).
- `tests/` — Unit- und Äquivalenztests.
- `config.json` — die eine Konfigurationsdatei im Wurzelverzeichnis; siehe
  Hinweis zu `windkraft/config.py` unten.
- `data/` und `output/` — beide gitignored (siehe `.gitignore`). Die einzige
  Ausnahme ist `data/README.md`: sie ist die Provenienz-Dokumentation für
  jede Datei unter `data/` und wird deshalb versioniert, obwohl der Ordner
  selbst es nicht ist.

## Voraussetzungen

- Python ≥ 3.10 und [uv](https://docs.astral.sh/uv/) — Abhängigkeiten und
  Interpreter-Version sind in `pyproject.toml` deklariert, `uv.lock` fixiert
  die Versionen. Alle Kettenschritte laufen über `uv run python ...`
  (siehe `Makefile`).
- **`osmium-tool` als harte Systemvoraussetzung**, installiert außerhalb von
  uv/pip. Auf macOS:

  ```
  brew install osmium-tool
  ```

  Unmissverständlich: ein fehlendes `osmium-tool` führt **nicht** zu einem
  Abbruch. Der OSM-Extraktionsschritt fängt den resultierenden Fehler ab und
  fällt still auf leere Masken zurück (siehe `docs/FOLLOWUPS.md`,
  Abschnitt „Stille Fallbacks und Drift“). Ein Lauf ohne `osmium-tool` sieht
  danach erfolgreich aus, ist aber inhaltlich falsch — es gibt keine
  Warnung.

## Die Kette

Die Widmung-v2-Kette besteht aus fünf `make`-Targets, die in dieser
Reihenfolge laufen müssen:

1. `make widmung-v2-zoning` — baut die amtlichen Widmungs-/Zonierungsvektoren.
2. `make widmung-v2-hig` — leitet die HIG-Quellen (Häuser im Grünen) aus den
   Zonierungsvektoren ab.
3. `make widmung-v2-osm` — extrahiert die OSM-Distanzlayer (benötigt
   `osmium-tool`, siehe oben).
4. `make widmung-v2-tif` — kombiniert alle Layer zum finalen GeoTIFF.
5. `make widmung-v2-validate` — validiert das GeoTIFF gegen die Testpunkte.

`make widmung-v2` führt alle fünf nacheinander aus (mehrstündig). Wichtig:
die Kopplung zwischen den Schritten läuft über Dateien im gemeinsamen
Ausgabeordner (`output/abschichtung_widmung_v2/...`), nicht über
Make-Abhängigkeiten — die Targets selbst kennen sich gegenseitig nicht, ein
Schritt scheitert erst zur Laufzeit, wenn eine erwartete Datei fehlt.
Details und Hintergrund: `docs/widmung_v2.md`.

## Das Band-Manifest — Begründung (geplant, noch nicht umgesetzt)

Downstream-Artefakte kennen die Bandnamen und die Bandreihenfolge des
finalen GeoTIFF bisher nur, indem sie sie selbst nachbauen — mit der Folge,
dass sie vom tatsächlichen Raster wegdriften können, ohne dass es jemandem
auffällt. Die Belege dafür liegen bereits vor: `dashboard_data.json` trägt
63 Bänder vom 06.08., `viewer/manifest.json` 39 Layer vom 10.08., das
aktuelle TIF hat 38 Bänder vom 04.09. — drei verschiedene Zählungen zu drei
verschiedenen Zeitpunkten. Sichtbarste Konsequenz:
`scripts/analysis/build_v2_dashboard_data.py` bricht am aktuellen TIF hart
ab, weil sein `EXCLUSION_LAYERS` noch sieben Bandnamen aus dem
Pre-Clean-Schema nennt (siehe `docs/FOLLOWUPS.md`).

Geplante Lösung: der Writer-Schritt (`04_create_distance_zones.py`) soll
künftig neben dem GeoTIFF ein Sidecar `<stem>.bands.json` schreiben — ein
vom Erzeuger selbst stammendes Manifest mit Bandnamen, Reihenfolge und
Kategorie. Das behebt diese Drift-Klasse strukturell, weil Erzeuger und
Beschreibung dann nicht mehr auseinanderlaufen können; jeder Konsument liest
das Manifest statt es zu erraten. **Der Emitter ist noch nicht eingebaut** —
`windkraft/viz/band_metadata.py` liefert bereits die gemeinsamen
Farb-/Kategorie-/Sichtbarkeits-Tabellen für Writer und Viewer, aber kein
Modul schreibt bislang das Manifest selbst.

## Verweise

- [`data/README.md`](data/README.md) — Provenienz jeder Datei unter `data/`.
- [`docs/FOLLOWUPS.md`](docs/FOLLOWUPS.md) — bei der Übernahme beobachtete,
  bewusst nicht behobene Bugs und Altlasten.
- [`docs/MIGRATION_MAP.tsv`](docs/MIGRATION_MAP.tsv) — alte Pfade in
  `windkraft_ö_karten` → neue Pfade in diesem Repo, mit Begründung.
- [`docs/widmung_v2.md`](docs/widmung_v2.md) — Referenzkarte der Kette.

## Status

Erledigt: Code-Übernahme der Widmung-v2-Kette, `windkraft/`-Paket,
`scripts/`, Tests, `config.json` im Wurzelverzeichnis, Layer-Viewer
(`scripts/webmap/build_layer_viewer.py`), gemeinsame Bandmetadaten
(`windkraft/viz/band_metadata.py`), Migrations- und Follow-up-Dokumentation.

Fehlt: ein tatsächlich verifizierter Lauf der vollständigen Kette gegen
`windkraft_ö_karten` (Voraussetzung dafür, dass das alte Repo abgelöst werden
kann), der Band-Manifest-Emitter, sowie die in `docs/FOLLOWUPS.md`
gesammelten offenen Entscheidungen (u. a. `config.py`-Pfadauflösung,
Projektname/Entry-Point in `pyproject.toml`, veraltete
`EXCLUSION_LAYERS`-Liste im Dashboard-Skript).
