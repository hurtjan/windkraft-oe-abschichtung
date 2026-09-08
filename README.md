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
  Datenaufbereitung). `analysis/` und `webmap/` enthielten je ein
  Auswertungs-/Inspektionswerkzeug (Dashboard-Daten, Layer-Viewer) — beide
  erwiesen sich als toter Code und wurden in W1.5 gelöscht; `analysis/`
  existiert seither nicht mehr, `webmap/` ist leer.
- `docs/` — Nachschlagedokumentation: `widmung_v2.md` (Referenzkarte der
  Kette), `widmung_v2_provenance.md` (Provenienz), `FOLLOWUPS.md` (offene
  Beobachtungen aus der Übernahme), `MIGRATION_MAP.tsv` (alte → neue Pfade),
  `analysis/` (Herleitungs-Dokumentation einzelner Verfahren).
- `tests/` — Unit- und Äquivalenztests.
- `config.json` — die eine Konfigurationsdatei im Wurzelverzeichnis. Die
  Rohpfade (`vgd`, `osm_dir`, `wind_pd_150`, `wind_pd_100`, `dgm`,
  `nsg_zip`, `powerlines_gpkg`) stehen dort nicht mehr als Literal:
  `windkraft/config.py:load_config()` befüllt `cfg["paths"]` beim Laden aus
  dem Pfadvertrag `pipeline/contract.py` (`windkraft/config.py:8, 35-45`);
  alles andere (Schwellwerte, Bundesland-Puffer, Windparameter usw.) bleibt
  Literal in `config.json`.
- `data/` und `output/` — beide gitignored (siehe `.gitignore`), seit W1.2
  ohne jede Ausnahme: die Provenienz-Dokumentation für `data/` lag früher
  als `data/README.md` selbst im Ordner und war deshalb versioniert; sie
  liegt jetzt als [`docs/rohdaten.md`](docs/rohdaten.md) außerhalb davon.

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

  In diesem Repo gilt das Gegenteil dessen, was das Altrepo einmal tat:
  `_run_osmium()` (`windkraft/calc/abschichtung_common.py:413-414`,
  `subprocess.run(cmd, check=True)`) fängt keine Exception ab — ein
  fehlendes `osmium-tool` lässt den Lauf sofort mit `FileNotFoundError`
  abbrechen. Der in `docs/FOLLOWUPS.md`, Abschnitt „Stille Fallbacks und
  Drift“, dokumentierte stille Fallback (`CalledProcessError` abfangen,
  auf leere Masken zurückfallen) lebte in `kataster_layers.py:876` des
  Altrepos und wurde nicht mit übernommen. Still bleibt dagegen ein
  anderer, leicht zu verwechselnder Fall: **fehlende OSM-Rohdaten** (nicht
  das Tool) — `osm_layer_path()` (`abschichtung_common.py:470-511`) weicht
  dann auf Alt-Shapefile-Pfade oder einen Platzhalterpfad aus, und
  `read_layer()` (`abschichtung_common.py:517-519`) liefert für einen
  fehlenden Pfad klaglos eine leere GeoDataFrame zurück. Ein Lauf mit
  lückenhaften OSM-Daten (Tool installiert) sieht also weiterhin
  erfolgreich aus, ist aber inhaltlich falsch — ein Lauf ganz ohne
  `osmium-tool` dagegen bricht hier laut ab.
- **Speicherbedarf:** `data/` und `output/` zusammen ≈ 24 GB (`du -sch data
  output`, gemessen 07.09.2026: 13 GB + 11 GB — Momentaufnahme, kein
  Fixwert). `output/` ist seit der ursprünglich nach der Migration
  gemessenen 5,1 GB gewachsen: `output/kataster` (5,0 GB, aus
  `scripts/preprocessing/export_at_dkm_geoparquet.py`) und der erste
  vollständige Kettenlauf (`docs/RUN1_VERGLEICH.md`) sind dazugekommen.
  Beide Ordner sind gitignored, keiner enthält eine versionierte Datei.

## Daten besorgen

`data/` ist gitignored und wird nicht mit diesem Repo mitgeliefert.
Provenienz und Bezugsquelle jeder einzelnen Datei stehen in
[`docs/rohdaten.md`](docs/rohdaten.md) — vor dem ersten Lauf lesen,
insbesondere Abschnitt „Warnung: stille Fallbacks bei fehlenden Rohdaten“:

> Eine unvollständige `data/`-Kopie erzeugt ein plausibel aussehendes, aber
> falsches TIF, ohne dass irgendwo ein Fehler erscheint.

Die Kette bricht bei fehlenden Rohdaten in den meisten Fällen **nicht** ab,
sondern rechnet mit leeren oder degenerierten Eingaben weiter — siehe die
Fallback-Tabelle in `docs/rohdaten.md` für die einzelnen Mechanismen.

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

Daneben kennt das `Makefile` inzwischen ein Fünf-Stufen-Modell (Roh -> Prep
-> Layer -> Finalize -> verify, `Makefile:46-60`): `make` ohne Argument ist
seit `.DEFAULT_GOAL := widmung-v2` (`Makefile:16`) identisch mit
`make widmung-v2` — **ohne** dieses `.DEFAULT_GOAL` würde `make(1)` das
erste im File stehende Ziel nehmen, `widmung-v2-zoning` (nur Stufe 1 von
5). `make prep` existiert als Ziel, tut aber noch nichts (`Makefile:56-57`,
Platzhalter bis Welle 1 die Prep-Pakete liefert). `make all` hängt `prep`
und `widmung-v2` aneinander (`Makefile:60`) und ist deshalb aktuell
dasselbe wie `make`. `make test` führt `uv run pytest tests/ -v` aus
(`Makefile:65-66`). `make worktree PAKET=<paket>` legt neben dem Repo ein
einsatzfähiges Arbeitsverzeichnis für ein Paket an (`Makefile:68-137`).

`make widmung-v2` führt alle fünf nacheinander aus. Laufzeit, gemessen am
06.09.2026 auf einer Maschine mit bereits vorhandenen Caches/Checkpoints
(Adressregister-Parquets, teilweise befüllter OSM-PBF-Extract-Cache) —
**ein** gemessener Lauf auf **einer** Maschine, keine Garantie für andere
Umgebungen oder einen Kaltstart ohne Caches (vollständige Methodik und
Bandvergleich gegen die Referenz-TIF aus `windkraft_ö_karten`:
`docs/RUN1_VERGLEICH.md`):

| Stufe | Skript | Dauer |
| --- | --- | --- |
| 1 build_official_zoning_layers | `01_build_official_zoning_layers.py` | 49 s |
| 2 build_hig_sources | `02_build_hig_sources.py` | 143 s (2 min 23 s) |
| 3 build_osm_layers | `03_build_osm_layers.py` | 375 s (6 min 15 s) |
| 4 create_distance_zones | `04_create_distance_zones.py` | 298 s (4 min 58 s) |
| 5 validate | `05_validate.py` | 1 s |
| **Gesamt** | | **866 s (14 min 26 s)** |

Wichtiger Vorbehalt zu Stufe 1: `01_build_official_zoning_layers.py`
verarbeitet in diesen 49 s ein bereits fertiges Kataster-GeoParquet
(`output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet`), **nicht** die
9,1 GB rohen DKM-Archive unter `data/kataster/` (`docs/MIGRATION_MAP.tsv:70`).
Die Vorverarbeitung, die dieses GeoParquet erst erzeugt
(`scripts/preprocessing/export_at_dkm_geoparquet.py`), ist in dieser
Tabelle nicht enthalten und wurde in diesem Repo bislang nirgends gemessen
(siehe `docs/rewrite/FORTSCHRITT.md`, Abschnitt „Gemessene Laufzeiten”).

Bei einem Kaltstart ohne vorhandene Caches (insbesondere ein leerer
OSM-PBF-Extract-Cache unter `output/abschichtung/osm_pbf_layers/`, ca. 4,6 GB)
ist mit deutlich längerer Laufzeit zu rechnen als hier gemessen — vor
diesem Lauf war die Kette in diesem Repo noch kein einziges Mal end-to-end
ausgeführt worden (siehe Abschnitt „Status”).
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
Zeitpunkten. Sichtbarste Konsequenz war `scripts/analysis/build_v2_dashboard_data.py`:
es brach am aktuellen TIF hart ab, weil sein `EXCLUSION_LAYERS` acht
Bandnamen aus dem Pre-Clean-Schema nannte, die es nicht mehr gibt (siehe
`docs/FOLLOWUPS.md`) — als toter Code in W1.5 gelöscht.

**Umgesetzt:** der Writer-Schritt (`scripts/widmung_v2/04_create_distance_zones.py`)
schreibt seit `windkraft/calc/band_manifest.py` (`write_band_manifest()`)
direkt nach dem Komponieren des GeoTIFF ein Sidecar `<stem>.bands.json`
neben die Datei — aus genau den Werten, die der Writer ohnehin schon kennt
(Bandnamenliste, Datei-Tags), ohne das fertige Raster erneut zu öffnen.
Bandzahl, -namen und -reihenfolge im Manifest sind damit per Konstruktion
identisch mit dem TIF. Farben, Kategorien und Default-Sichtbarkeit kommen
aus der gemeinsamen Quelle `windkraft/viz/band_metadata.py`. Der Vertrag,
den ein Konsument gegen dieses Manifest einhalten muss, steht in
[`docs/HANDOFF.md`](docs/HANDOFF.md). Der End-to-End-Lauf, der den Emitter
tatsächlich in Produktion schreiben lässt, hat inzwischen stattgefunden
(06.09.2026, `docs/RUN1_VERGLEICH.md`) — Bandzahl, -namen, -reihenfolge und
alle Vertragsfelder des Manifests stimmen mit dem zuvor generierten
Referenz-Manifest exakt überein; offen sind nur inhaltliche
Detailabweichungen (Caveat-Texte, 18 von 38 Bändern mit Pixelabweichungen
< 0,004 %, siehe Abschnitt „Status” und `docs/RUN1_VERGLEICH.md`, Abschnitt
10). `docs/HANDOFF.md` ist seit W4.3 aktuell: es zieht die neue Referenz
(`sha256 fb57c41d…232c30`, `schema_version` `2.0.0`) und dokumentiert die
18 von `run1` abweichenden Bänder aus zwei am 08.09.2026 vom Nutzer
entschiedenen Ursachen: der Bodensee-Korrektur (Punkt 33, Bänder 26 und
29) und dem Wegfall adressloser DKM-Großflächen (Punkt 34, Bänder 5,
7–13 und 27); die Bänder 30–36 tragen beide Ursachen überlagert. Am
Endergebnis wirken sie gegeneinander: Band 32
(`available_cleaned_min_10ha`) liegt netto 847,6 ha (8,48 km²) unter
`run1`.

## Was dieses Repo nicht ist

- **Keine Widmung v1.** Die alte, 54-bändige Widmung-Kette
  (`scripts/main/create_widmung_wka_distance_zones.py` im alten Repo) wurde
  nicht übernommen und ist hier nicht lauffähig.
- **Keine eigenständige OSM-Kette.** `scripts/main/create_osm_wka_distance_zones.py`
  (reine OSM-Abstandszonen ohne Widmung) ist nicht Teil dieses Repos.
- **Kataster-Kette ist migriert, aber noch nicht an `make` angebunden.**
  `scripts/preprocessing/export_at_dkm_geoparquet.py` erzeugt
  `output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet` (gelesen von Stufe
  2, `02_build_hig_sources.py:197`, über `--dkm-parquet`), und
  `create_noe_dkm_polygon_fill_map.py` liefert dafür das
  NÖ-DXF-Vorprodukt — beides läuft seit der Code-Übernahme in diesem Repo,
  nicht mehr im alten. Kein `make`-Target ruft die beiden Skripte bisher
  auf; `make prep` ist noch ein Platzhalter (`Makefile:56-57`) — bis Welle
  1 die Prep-Pakete liefert, müssen sie von Hand aufgerufen werden.
- **Keine Präsentations-/Auswertungsskripte** über die Kette hinaus —
  insbesondere keine Dashboards. `scripts/analysis/build_v2_dashboard_data.py`
  existierte bei der Übernahme, brach aber am aktuellen 38-Band-TIF hart ab
  (`EXCLUSION_LAYERS` nannte acht Bandnamen aus dem Pre-Clean-Schema, die es
  nicht mehr gibt — siehe Abschnitt „Das Band-Manifest" oben) und wurde als
  toter Code in W1.5 gelöscht; `scripts/analysis/` existiert seither nicht
  mehr. Der ebenfalls mitübernommene Layer-Viewer
  (`scripts/webmap/build_layer_viewer.py`, unter „Struktur“ oben erwähnt)
  war unabhängig davon durch einen `NameError` bei jedem Aufruf tot und
  wurde im selben Paket gelöscht.

Für all das ist `windkraft_ö_karten` weiterhin die Quelle der Wahrheit.

## Hardlink-Sicherheit prüfen

Bis W1.3 war `data/` überwiegend echtes, per Hardlink aus
`windkraft_ö_karten` übernommenes Quellmaterial. Seit W1.3 (07.09.2026)
gilt das nicht mehr: alle 48 verbliebenen Hardlinks unter `data/` sind
aufgelöst, der Ordner besteht komplett aus echten Kopien — auch dort, wo
die Kette nur liest. Für jede Datei, die irgendein Codepfad **schreibt**,
galt ohnehin schon vorher: sie muss eine echte Kopie sein, nie ein
Hardlink. Ein Schreibvorgang auf eine hardgelinkte Datei kürzt den
geteilten Inode und zerstört dieselbe Datei im Alt-Repo im selben Moment,
ohne Fehlermeldung.

```
make check-hardlinks
```

**Nach dem Hinzufügen jedes neuen Datensatzes ausführen.** Das Werkzeug
(`tools/check_hardlink_safety.py`) prüft mechanisch, ohne Abhängigkeiten
und in Sekunden: kein File unter `output/` darf einen Link-Count > 1 haben
(ausnahmslos), und seit W1.3 gilt dieselbe Ausnahmslosigkeit für `data/` —
*jede* Datei dort muss Link-Count 1 haben, nicht mehr nur eine deklarierte
Liste bekannter Schreibziele. Ergänzend prüft `make check-raw-only`
(`tools/check_raw_only.py`, seit W1.4) statisch, dass kein Codepfad
überhaupt erst nach `data/` schreiben *kann* — beide zusammen über
`make check-guards`. Details, Begründung und die Historie des behobenen
Verstoßes: [`docs/rohdaten.md`](docs/rohdaten.md), Abschnitt 9, und
[`docs/FOLLOWUPS.md`](docs/FOLLOWUPS.md), Abschnitt „Regel: die
Hardlink-Invariante".

## Verweise

- [`docs/rohdaten.md`](docs/rohdaten.md) — Provenienz jeder Datei unter `data/`.
- [`docs/FOLLOWUPS.md`](docs/FOLLOWUPS.md) — bei der Übernahme beobachtete,
  bewusst nicht behobene Bugs und Altlasten.
- [`docs/MIGRATION_MAP.tsv`](docs/MIGRATION_MAP.tsv) — alte Pfade in
  `windkraft_ö_karten` → neue Pfade in diesem Repo, mit Begründung.
- [`docs/widmung_v2.md`](docs/widmung_v2.md) — Referenzkarte der Kette.
- [`docs/HANDOFF.md`](docs/HANDOFF.md) — Vertrag für Konsumenten des
  GeoTIFF und seines Band-Manifests.
- [`docs/RUN1_VERGLEICH.md`](docs/RUN1_VERGLEICH.md) — Methodik und
  Ergebnis des ersten End-to-End-Laufs, Quelle der Laufzeiten oben.

## Status

Erledigt: Code-Übernahme der Widmung-v2-Kette, `windkraft/`-Paket,
`scripts/`, Tests, `config.json` im Wurzelverzeichnis, gemeinsame
Bandmetadaten (`windkraft/viz/band_metadata.py`), der Band-Manifest-Emitter
(`windkraft/calc/band_manifest.py`), Migrations- und
Follow-up-Dokumentation. Der mitübernommene Layer-Viewer
(`scripts/webmap/build_layer_viewer.py`) erwies sich als toter Code
(`NameError` bei jedem Aufruf) und wurde in W1.5 gelöscht.

Erledigt seit dem 06.09.2026 zusätzlich: ein erster vollständiger
End-to-End-Lauf der Kette in diesem Repo, verglichen gegen die aus
`windkraft_ö_karten` übernommene Referenz-TIF (SHA-256-geprüft, Altrepo
dabei unverändert) — siehe `docs/RUN1_VERGLEICH.md`. Bandzahl (38),
Bandnamen/-reihenfolge, alle 26 globalen Tags und alle Vertragsfelder des
Band-Manifests stimmen exakt überein; 20 von 38 Bändern sind pixelgenau
identisch mit der Referenz. Offen bleibt: 18 von 38 Bändern
(Human-Exclusion-Kette) weichen um < 0,004 % der jeweiligen Bandfläche ab,
ohne dass die Ursache abschließend geklärt wurde, ebenso ein
Größenunterschied der TIF-Datei (119 MB vs. 129 MB) und geänderte
Caveat-Texte im Manifest (vollständige Rangliste aller Abweichungen:
`docs/RUN1_VERGLEICH.md`, Abschnitt 10). Ob das für die Ablösung des alten
Repos ausreicht, ist damit noch nicht entschieden — das ist eine
inhaltliche Frage, keine, die sich aus dem Lauf allein beantwortet.
Ebenfalls offen: die in `docs/FOLLOWUPS.md` gesammelten Entscheidungen (u. a.
`config.py`-Pfadauflösung, Projektname/Entry-Point in `pyproject.toml`). Die
dort ebenfalls vermerkte veraltete `EXCLUSION_LAYERS`-Liste im
Dashboard-Skript ist durch dessen Löschung in W1.5 gegenstandslos
geworden — `docs/FOLLOWUPS.md` selbst nennt diesen Punkt weiterhin als
offen und wäre bei Gelegenheit zu bereinigen.
