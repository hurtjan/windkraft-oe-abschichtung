# Abschichtung Widmung v2

## Zweck

Dieses Repo berechnet aus amtlichen Widmungs-/Zonierungsdaten, OSM-Extrakten
und Geodaten (DGM, Windatlas, Verwaltungsgrenzen) die österreichweite
Windkraft-Potentialfläche nach dem Widmung-v2-Verfahren (Ausschluss- und
Abstandskriterien für Mensch, Natur und Geografie). Es ist die additive
Neufassung der Widmung-v2-Kette aus dem alten, gewachsenen Repo
`windkraft_ö_karten` — das alte Repo bleibt unangetastet als Sicherheitsnetz
bestehen, bis dieses Repo einen verifizierten Lauf hinter sich hat, und ist
bis dahin die Quelle der Wahrheit. Ergebnis der Kette ist ein 38-Band-GeoTIFF
(`output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2.tif`) plus
das dazugehörige Sidecar-Manifest `<stem>.bands.json`; wer dieses Ergebnis
konsumiert, findet den Vertrag dafür in [`docs/HANDOFF.md`](docs/HANDOFF.md).

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
- **Speicherbedarf:** `data/` und `output/` zusammen ≈ 18 GB (`du -sch data
  output`: 13 GB + 5,1 GB, Stand nach der Migration in dieses Repo). Beide
  Ordner sind gitignored; nur `data/README.md` ist versioniert.

## Daten besorgen

`data/` ist gitignored und wird nicht mit diesem Repo mitgeliefert.
Provenienz und Bezugsquelle jeder einzelnen Datei stehen in
[`data/README.md`](data/README.md) — vor dem ersten Lauf lesen, insbesondere
Abschnitt „Warnung: stille Fallbacks bei fehlenden Rohdaten“:

> Eine unvollständige `data/`-Kopie erzeugt ein plausibel aussehendes, aber
> falsches TIF, ohne dass irgendwo ein Fehler erscheint.

Die Kette bricht bei fehlenden Rohdaten in den meisten Fällen **nicht** ab,
sondern rechnet mit leeren oder degenerierten Eingaben weiter — siehe die
Fallback-Tabelle in `data/README.md` für die einzelnen Mechanismen.

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

`make widmung-v2` führt alle fünf nacheinander aus. Laufzeit: mehrere
Stunden, in diesem Repo nie verifiziert — die Kette wurde in diesem Repo
noch kein einziges Mal end-to-end ausgeführt (siehe Abschnitt „Status“).
Wichtig: die Kopplung zwischen den Schritten läuft über Dateien im
gemeinsamen Ausgabeordner (`output/abschichtung_widmung_v2/...`), nicht über
Make-Abhängigkeiten — die Targets selbst kennen sich gegenseitig nicht, ein
Schritt scheitert erst zur Laufzeit, wenn eine erwartete Datei fehlt.
Details und Hintergrund: `docs/widmung_v2.md`.

## Das Band-Manifest — Begründung und Stand

Downstream-Artefakte kannten die Bandnamen und die Bandreihenfolge des
finalen GeoTIFF bisher nur, indem sie sie selbst nachbauten — mit der Folge,
dass sie vom tatsächlichen Raster wegdriften konnten, ohne dass es jemandem
auffiel. Die Belege dafür liegen vor: `dashboard_data.json` trug 63 Bänder
vom 06.08., `viewer/manifest.json` 39 Layer vom 10.08., das aktuelle TIF hat
38 Bänder vom 04.09. — drei verschiedene Zählungen zu drei verschiedenen
Zeitpunkten. Sichtbarste Konsequenz: `scripts/analysis/build_v2_dashboard_data.py`
bricht am aktuellen TIF hart ab, weil sein `EXCLUSION_LAYERS` noch sieben
Bandnamen aus dem Pre-Clean-Schema nennt (siehe `docs/FOLLOWUPS.md`).

**Umgesetzt:** der Writer-Schritt (`scripts/widmung_v2/04_create_distance_zones.py`)
schreibt seit `windkraft/calc/band_manifest.py` (`write_band_manifest()`)
direkt nach dem Komponieren des GeoTIFF ein Sidecar `<stem>.bands.json`
neben die Datei — aus genau den Werten, die der Writer ohnehin schon kennt
(Bandnamenliste, Datei-Tags), ohne das fertige Raster erneut zu öffnen.
Bandzahl, -namen und -reihenfolge im Manifest sind damit per Konstruktion
identisch mit dem TIF. Farben, Kategorien und Default-Sichtbarkeit kommen
aus der gemeinsamen Quelle `windkraft/viz/band_metadata.py`. Der Vertrag,
den ein Konsument gegen dieses Manifest einhalten muss, steht in
[`docs/HANDOFF.md`](docs/HANDOFF.md) — **noch nicht verifiziert ist nur der
End-to-End-Lauf, der den Emitter tatsächlich in Produktion schreiben lässt**
(siehe „Status“); das Referenz-Manifest in `docs/HANDOFF.md` stammt aus
einem älteren Artefakt.

## Was dieses Repo nicht ist

- **Keine Widmung v1.** Die alte, 54-bändige Widmung-Kette
  (`scripts/main/create_widmung_wka_distance_zones.py` im alten Repo) wurde
  nicht übernommen und ist hier nicht lauffähig.
- **Keine eigenständige OSM-Kette.** `scripts/main/create_osm_wka_distance_zones.py`
  (reine OSM-Abstandszonen ohne Widmung) ist nicht Teil dieses Repos.
- **Keine Kataster-Kette.** Die Erzeugung von `at_dkm_gst_nfl_epsg31287.geoparquet`
  und der übrigen Kataster-Layer läuft weiterhin ausschließlich im alten
  Repo; dieses Repo liest ihr Ergebnis nur als Eingabedatensatz.
- **Keine Präsentations-/Auswertungsskripte** über den unter „Struktur“
  genannten Layer-Viewer hinaus — insbesondere keine Dashboards.

Für all das ist `windkraft_ö_karten` weiterhin die Quelle der Wahrheit.

## Hardlink-Sicherheit prüfen

`data/` ist überwiegend echtes, per Hardlink aus `windkraft_ö_karten`
übernommenes Quellmaterial — rein lesend, das kostet keinen Speicher und
ist korrekt so. Für jede Datei, die irgendein Codepfad **schreibt**, gilt
das Gegenteil: sie muss eine echte Kopie sein, nie ein Hardlink. Ein
Schreibvorgang auf eine hardgelinkte Datei kürzt den geteilten Inode und
zerstört dieselbe Datei im Alt-Repo im selben Moment, ohne Fehlermeldung.

```
make check-hardlinks
```

**Nach dem Hinzufügen jedes neuen Datensatzes ausführen.** Das Werkzeug
(`tools/check_hardlink_safety.py`) prüft mechanisch, ohne Abhängigkeiten
und in Sekunden: kein File unter `output/` darf einen Link-Count > 1 haben
(ausnahmslos), und eine explizit deklarierte Liste bekannter Schreibziele
unter `data/` (aktuell die beiden Adressregister-Parquet-Caches) muss
Link-Count 1 haben. Details, Begründung und die Historie des behobenen
Verstoßes: [`data/README.md`](data/README.md), Abschnitt 9, und
[`docs/FOLLOWUPS.md`](docs/FOLLOWUPS.md), Abschnitt „Regel: die
Hardlink-Invariante".

## Verweise

- [`data/README.md`](data/README.md) — Provenienz jeder Datei unter `data/`.
- [`docs/FOLLOWUPS.md`](docs/FOLLOWUPS.md) — bei der Übernahme beobachtete,
  bewusst nicht behobene Bugs und Altlasten.
- [`docs/MIGRATION_MAP.tsv`](docs/MIGRATION_MAP.tsv) — alte Pfade in
  `windkraft_ö_karten` → neue Pfade in diesem Repo, mit Begründung.
- [`docs/widmung_v2.md`](docs/widmung_v2.md) — Referenzkarte der Kette.
- [`docs/HANDOFF.md`](docs/HANDOFF.md) — Vertrag für Konsumenten des
  GeoTIFF und seines Band-Manifests.

## Status

Erledigt: Code-Übernahme der Widmung-v2-Kette, `windkraft/`-Paket,
`scripts/`, Tests, `config.json` im Wurzelverzeichnis, Layer-Viewer
(`scripts/webmap/build_layer_viewer.py`), gemeinsame Bandmetadaten
(`windkraft/viz/band_metadata.py`), der Band-Manifest-Emitter
(`windkraft/calc/band_manifest.py`), Migrations- und
Follow-up-Dokumentation.

Fehlt: ein tatsächlich verifizierter Lauf der vollständigen Kette gegen
`windkraft_ö_karten` (Voraussetzung dafür, dass das alte Repo abgelöst werden
kann) — die Kette wurde in diesem Repo noch kein einziges Mal end-to-end
ausgeführt, das ist die einzige echte Absicherung, dass Code-Übernahme und
Emitter zusammen tatsächlich funktionieren. Ebenfalls offen: die in
`docs/FOLLOWUPS.md` gesammelten Entscheidungen (u. a.
`config.py`-Pfadauflösung, Projektname/Entry-Point in `pyproject.toml`,
veraltete `EXCLUSION_LAYERS`-Liste im Dashboard-Skript).
