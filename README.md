# Abschichtung Widmung v2

## Zweck

Dieses Repo berechnet aus amtlichen Widmungs-/Zonierungsdaten, OSM-Extrakten
und Geodaten (DGM, Windatlas, Verwaltungsgrenzen) die österreichweite
Windkraft-Potentialfläche nach dem Widmung-v2-Verfahren (Ausschluss- und
Abstandskriterien für Mensch, Natur und Geografie). Es ist die additive
Neufassung der Widmung-v2-Kette aus dem alten, gewachsenen Repo
`windkraft_ö_karten` — das alte Repo bleibt unangetastet als Sicherheitsnetz
bestehen und war bis zum ersten verifizierten Lauf dieses Repos die Quelle
der Wahrheit. Hauptergebnis der Kette ist ein 38-Band-GeoTIFF
(`out/abschichtung.tif`) plus das dazugehörige Sidecar-Manifest
`out/abschichtung.bands.json`; wer dieses Ergebnis konsumiert, findet den
Vertrag dafür in [`docs/HANDOFF.md`](docs/HANDOFF.md).

## Struktur

Das Repo ist seit Welle 5/6 nach den fünf Stufen der Kette benannt, nicht
mehr nach der ursprünglichen Übernahme aus `windkraft_ö_karten`:

```
data/       Rohdaten (unveränderlich, per Wächter gesichert)
derived/    Zwischenstände — prep/ und layers/
out/        die vier Endprodukte
pipeline/   die Kette: prep/ → layers/ → finalize.py → validate.py → export/
calc/       die Rechenlogik (vormals windkraft/)
make/ tools/ tests/ docs/
```

Im Einzelnen:

- `data/` — Rohdaten, gitignored, seit W1.2 ohne jede versionierte
  Ausnahme (Provenienz je Datei: [`docs/rohdaten.md`](docs/rohdaten.md)).
  Seit W1.3 besteht der Ordner ausschließlich aus echten Kopien, kein
  Hardlink mehr auf `windkraft_ö_karten` (siehe „Hardlink-Sicherheit
  prüfen" unten). Kein Codepfad darf hierher schreiben — mechanisch
  geprüft über `make check-guards`.
- `derived/` — gitignored, jederzeit löschbar. `derived/prep/` sind die
  Prep-Ausgaben der neun Prep-Domänen (`make prep`, Zieldateien je Domäne
  in `pipeline.contract.PREP`), `derived/layers/` die 33 Checkpoint-Layer der
  Layer-Stufe (`make layers`), aus denen `pipeline/finalize.py` das
  GeoTIFF komponiert.
- `out/` — gitignored, die vier Endprodukte: `abschichtung.tif` (38-Band-
  GeoTIFF), `abschichtung.bands.json` (Sidecar-Manifest, siehe unten),
  `dashboard/` (manifest-getriebener Prüfbericht über die Bänder,
  `pipeline/export/dashboard.py`, JSON + HTML) und `gemeinden.geojson`
  (Gemeindegrenzen im Rasterbezug, `pipeline/export/gemeinden.py`). Der
  eigentliche interaktive Viewer für das Ergebnis lebt nicht in diesem
  Repo, sondern auf der Konsumentenseite — siehe
  [`docs/HANDOFF.md`](docs/HANDOFF.md).
- `pipeline/` — die Kette selbst: `contract.py` (der eine Pfadvertrag für
  Rohpfade, Prep-Ausgaben, Layernamen und Produktpfade — „wird gelesen,
  nicht kopiert"), `prep/` (neun Domänen, drei davon zweistufig —
  `kataster/` mit `a_noe_polygonize.py` dann `b_export_parquet.py`, sowie
  `osm.py` und `noe_sekrop.py` mit je zwei intern geprüften Stufen),
  `layers/` (`hig.py`,
  `osm.py`, `geo.py` — die 33 Checkpoints), `finalize.py` (komponiert das
  GeoTIFF plus Manifest), `validate.py` (bandweiser Vergleich gegen die
  Vergleichsbasis `run1`, bewertet, entscheidet nicht — siehe
  `make/validate/README.md`) und `export/` (`dashboard.py`,
  `gemeinden.py`). `runtime.py` und `fingerprint.py` sind gemeinsame
  Hilfsmodule (Verzeichnisanlage bzw. Datei-Fingerprinting für die
  Wiederholbarkeit von `make prep`, siehe unten).
- `calc/` — das Python-Paket mit der eigentlichen Berechnungslogik
  (vormals `windkraft/`): `calc/` selbst für die Kernberechnungen
  (z. B. `abschichtung_common.py`, `distance_engine.py`,
  `band_manifest.py`, `config.py`), `noe/` für niederösterreich-
  spezifische Quellenaufbereitung, `viz/band_metadata.py` für
  Darstellungs-/Bandmetadaten. `windkraft/scripts/` und ein separates
  `util/` gibt es seit dem Umbau nicht mehr.
- `make/` — je Kettenstufe ein Unterverzeichnis mit `.mk`-Dateien, die das
  `Makefile` per `-include` einliest (`make/prep/`, `make/layers/`,
  `make/finalize/`, `make/validate/`, `make/export/`), damit parallele
  Pakete nicht dieselbe Zeile im `Makefile` ändern müssen — siehe die
  jeweiligen `make/<stufe>/README.md`.
- `tools/` — `check_hardlink_safety.py` und `check_raw_only.py`, die
  beiden Rohdaten-Wächter (siehe unten).
- `tests/` — Unit-, Äquivalenz- und Vertragstests, `pytest tests/`
  sammelt rekursiv alles darunter ein.
- `docs/` — Nachschlagedokumentation: `widmung_v2.md` (Referenzkarte der
  ursprünglich übernommenen Kette), `widmung_v2_provenance.md`
  (Provenienz), `FOLLOWUPS.md` (offene Beobachtungen aus der Übernahme),
  `MIGRATION_MAP.tsv` (alte → neue Pfade), `rohdaten.md` (Provenienz von
  `data/`), `HANDOFF.md` (Vertrag für Konsumenten), `RUN1_VERGLEICH.md`
  (erster End-to-End-Lauf), `analysis/` (Herleitungs-Dokumentation
  einzelner Verfahren), `dataflow/` (Datenfluss-Diagramm) und
  `rewrite/` (Plan, Fortschrittsprotokoll und Nachweise des Umbaus
  selbst, u. a. `PLAN.md` und `FORTSCHRITT.md`).
- `config.json` — die eine Konfigurationsdatei im Wurzelverzeichnis. Die
  tatsächlich gelesenen Rohpfade (`vgd`, `osm_dir`, `wind_pd_150`,
  `wind_pd_100`, `dgm`, `nsg_zip`) stehen dort nicht mehr als Literal:
  `calc/config.py:load_config()` befüllt `cfg["paths"]` beim Laden aus dem
  Pfadvertrag `pipeline/contract.py`; alles andere (Schwellwerte,
  Bundesland-Puffer, Windparameter usw.) bleibt Literal in `config.json`.

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

  `_run_osmium()` (`calc/abschichtung_common.py:419`,
  `subprocess.run(cmd, check=True)`) fängt keine Exception ab — ein
  fehlendes `osmium-tool` lässt den Lauf sofort mit `FileNotFoundError`
  abbrechen. Still bleibt dagegen ein anderer, leicht zu verwechselnder
  Fall: **fehlende OSM-Rohdaten** (nicht das Tool) — Details dazu und zum
  in `docs/FOLLOWUPS.md` dokumentierten stillen Fallback des Altrepos:
  Abschnitt „Daten besorgen" unten und `docs/FOLLOWUPS.md`.
- **Speicherbedarf:** `data/`, `derived/` und `out/` zusammen ≈ 24 GB
  (`du -sh data derived out`, selbst gemessen 08.09.2026: 13 GB + 11 GB +
  145 MB — Momentaufnahme nach einem vollständigen Lauf, kein Fixwert;
  alle drei Ordner sind gitignored, keiner enthält eine versionierte
  Datei).

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

`make` ohne Argument baut seit W6.1 die **neue**, umgebaute Kette — es gibt
kein zweites, altes Ziel mehr, das `make(1)` mangels `.DEFAULT_GOAL`
stattdessen träfe. `.DEFAULT_GOAL := all` (`Makefile:15`) macht `make` und
`make all` zu Synonymen.

Fünf-Stufen-Modell, jede Stufe darf nur aus der vorigen lesen:

1. `make prep` — überführt Rohdaten aus `data/` in `derived/prep/`, neun
   Domänen (je eine Datei `make/prep/*.mk`, per `-include` eingelesen),
   von denen drei — `kataster`, `osm`, `noe_sekrop` — intern je zwei
   eigenständig fingerabdruckgeprüfte Stufen haben
   (`pipeline.contract.PREP`): macht zwölf einzeln überspringbare Stufen
   in der Praxis, nicht neun.
2. `make layers` — baut die 33 Checkpoint-Layer in `derived/layers/`
   (`hig`, `osm`, `geo`).
3. `make finalize` — komponiert daraus das 38-Band-GeoTIFF plus Manifest
   nach `out/`.
4. `make validate` — vergleicht ein finalisiertes TIF bandweise gegen die
   Vergleichsbasis `run1` und bewertet jede Abweichung nach der Ampel aus
   `docs/rewrite/PLAN.md` §6. Verlangt ein Pflichtargument `PAKET` und ist
   **bewusst nicht** Teil von `make all` — siehe die Begründung im
   `Makefile` selbst und `make/validate/README.md`.
5. `make export` — die beiden Export-Pakete `dashboard` und `gemeinden`,
   die die restlichen zwei der vier Endprodukte schreiben.

`make all` (= `make`) hängt `prep`, `layers`, `finalize` und `export`
aneinander, **ohne** `validate` (Begründung siehe Stufe 4 oben).

**Die Prep-Stufe ist wiederholbar.** Jede der zwölf Prep-Stufen prüft über
`pipeline/fingerprint.py`, ob ihre Eingaben unverändert sind und ihre
Ausgabe bereits vorliegt, und überspringt sich dann sichtbar statt neu zu
rechnen — das ist der Unterschied zum ursprünglichen 66-Minuten-Kaltstart.
Die Layer-Stufe prüft das nur teilweise: `pipeline/layers/geo.py`
überspringt vollständig, `pipeline/layers/osm.py` überspringt einen Teil
(Infrastruktur- und Flughafenkorridor-Masken) und baut den Rest
(OSM-Gebäudeklassifikation) bei jedem Lauf neu, `pipeline/layers/hig.py`
prüft gar nicht und baut alle sieben HiG-Checkpoints bei jedem Lauf neu.
`make finalize` und `make export` haben keine Fingerabdruckprüfung und
laufen immer vollständig durch. Selbst gemessen an diesem Repo-Stand
(08.09.2026, `time make all`, zweiter Lauf ohne geänderte Eingaben):
Gesamtdauer **5 min 39 s** (`user 321 s`, `sys 29 s`) — deutlich mehr als
die rund 3 Minuten, die `docs/rewrite/FORTSCHRITT.md` (Abschnitt zu Paket
W6.2) für einen früheren zweiten Lauf nennt; die dortigen 66 Minuten für
den Kaltstart habe ich nicht nachgemessen.

`make test` führt `uv run pytest tests/ -v` aus.

`make check-hardlinks`, `make check-raw-only` und zusammen
`make check-guards` — siehe „Hardlink-Sicherheit prüfen" unten.

`make worktree PAKET=<paket>` legt neben dem Repo ein einsatzfähiges
Arbeitsverzeichnis für ein Paket an: `data/`, `derived/prep/` und
`derived/layers/` werden dorthin als Symlinks (read-only) verlinkt, `out/`
ist ein echtes, privates Verzeichnis mit `abschichtung.tif` und
`abschichtung.bands.json` als Symlinks auf ein bereits im Hauptrepo
finalisiertes Ergebnis, falls vorhanden. Details und Warnungen (geteilte,
nur lesend gedachte Verzeichnisse) stehen im `Makefile` selbst.

**Es gibt keine zweite Kette und kein `scripts/` mehr.** Die alte,
fünfstufige Kette (`scripts/widmung_v2/01…05_*.py`) ist seit W6.1 aus
diesem Repo entfernt (letzter Stand im Commit `f1d00f7`). Ihr letztes
Ergebnis `run1.tif` und die alten Zwischenstände liegen seither außerhalb
des Repos unter `~/Documents/master_windkraft/archiv/` (siehe die
`README.md` dort). `run1` bleibt die unveränderliche Diagnose-
Vergleichsbasis für `make validate`; `pipeline/contract.py:RUN1_TIF` löst
seinen Pfad optional über die Umgebungsvariable `ABSCHICHTUNG_RUN1` auf
(Vorgabe `None` — ohne gesetzte Variable überspringen `validate.py` und
`tests/test_referenz_tif.py` den bandweisen Vergleich sichtbar, statt
abzubrechen):

```
export ABSCHICHTUNG_RUN1=~/Documents/master_windkraft/archiv/run1.tif
```

## Das Band-Manifest — Begründung und Stand

Downstream-Artefakte kannten die Bandnamen und die Bandreihenfolge des
finalen GeoTIFF bisher nur, indem sie sie selbst nachbauten — mit der Folge,
dass sie vom tatsächlichen Raster wegdriften konnten, ohne dass es jemandem
auffiel. Die Belege dafür liegen vor: `dashboard_data.json` trug 63 Bänder
vom 06.08., `viewer/manifest.json` 39 Layer vom 10.08., das aktuelle TIF hat
38 Bänder — drei verschiedene Zählungen zu drei verschiedenen Zeitpunkten.
Sichtbarste Konsequenz war das ursprünglich übernommene
`scripts/analysis/build_v2_dashboard_data.py`: es brach am aktuellen TIF
hart ab, weil sein `EXCLUSION_LAYERS` acht Bandnamen aus dem
Pre-Clean-Schema nannte, die es nicht mehr gibt — als toter Code in W1.5
gelöscht, `scripts/` gibt es seit W6.1 ohnehin nicht mehr.

**Umgesetzt:** `pipeline/finalize.py` schreibt über `calc/band_manifest.py`
(`write_band_manifest()`) direkt nach dem Komponieren des GeoTIFF ein
Sidecar `out/abschichtung.bands.json` neben die Datei — aus genau den
Werten, die der Schreibvorgang ohnehin schon kennt (Bandnamenliste,
Datei-Tags), ohne das fertige Raster erneut zu öffnen. Bandzahl, -namen
und -reihenfolge im Manifest sind damit per Konstruktion identisch mit dem
TIF. Farben, Kategorien und Default-Sichtbarkeit kommen aus der
gemeinsamen Quelle `calc/viz/band_metadata.py`. Der Vertrag, den ein
Konsument gegen dieses Manifest einhalten muss, steht in
[`docs/HANDOFF.md`](docs/HANDOFF.md).

Die aktuelle Referenz: 38 Bänder, Manifest-`schema_version` `2.1.0`,
`sha256 fb57c41dca0642225a8115e3ed95297ede47b56d56c00fdddf8caa445e232c30`
für `out/abschichtung.tif` — verdrahtet in `tests/test_referenz_tif.py`,
läuft bei jedem `make test` mit. Diese Referenz hat sich seit dem ersten
End-to-End-Lauf (`docs/RUN1_VERGLEICH.md`) zweimal geändert, aus zwei am
08.09.2026 vom Nutzer entschiedenen Ursachen (Bodensee-Korrektur und
Wegfall adressloser DKM-Großflächen) — vollständige Herleitung und die
Bänder, die dadurch von `run1` abweichen: `docs/HANDOFF.md` und
`docs/rewrite/FORTSCHRITT.md`.

## Was dieses Repo nicht ist

- **Keine Widmung v1.** Die alte, 54-bändige Widmung-Kette
  (`scripts/main/create_widmung_wka_distance_zones.py` im alten Repo
  `windkraft_ö_karten`) wurde nicht übernommen und ist hier nicht
  lauffähig.
- **Keine eigenständige OSM-Kette.** `scripts/main/create_osm_wka_distance_zones.py`
  im alten Repo (reine OSM-Abstandszonen ohne Widmung) ist nicht Teil
  dieses Repos.
- **Keine Präsentations-/Auswertungsskripte über die Kette hinaus.** Der
  ursprünglich mitübernommene Dashboard-Builder
  (`scripts/analysis/build_v2_dashboard_data.py`) brach am aktuellen
  38-Band-TIF hart ab (siehe Abschnitt „Das Band-Manifest" oben) und wurde
  als toter Code in W1.5 gelöscht; der ebenfalls mitübernommene
  Layer-Viewer (`scripts/webmap/build_layer_viewer.py`) war unabhängig
  davon durch einen `NameError` bei jedem Aufruf tot und wurde im selben
  Paket gelöscht. `scripts/` existiert seit W6.1 ohnehin nicht mehr.
  `pipeline/export/dashboard.py` (`out/dashboard/`, eines der vier
  Endprodukte) ist **kein** Ersatz für diese Werkzeuge, sondern ein
  manifest-getriebener Prüfbericht (liest ausschließlich
  `out/abschichtung.bands.json`, nie eine fest verdrahtete Bandliste); der
  eigentliche interaktive Viewer bleibt außerhalb dieses Repos, siehe
  [`docs/HANDOFF.md`](docs/HANDOFF.md).

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
und in Sekunden: kein File darf einen Link-Count > 1 haben (ausnahmslos),
und dieselbe Ausnahmslosigkeit gilt für `data/` — *jede* Datei dort muss
Link-Count 1 haben, nicht mehr nur eine deklarierte Liste bekannter
Schreibziele. Ergänzend prüft `make check-raw-only`
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
- [`docs/widmung_v2.md`](docs/widmung_v2.md) — Referenzkarte der
  ursprünglich übernommenen Kette.
- [`docs/HANDOFF.md`](docs/HANDOFF.md) — Vertrag für Konsumenten des
  GeoTIFF und seines Band-Manifests.
- [`docs/RUN1_VERGLEICH.md`](docs/RUN1_VERGLEICH.md) — Methodik und
  Ergebnis des ersten End-to-End-Laufs.
- [`docs/rewrite/PLAN.md`](docs/rewrite/PLAN.md) und
  [`docs/rewrite/FORTSCHRITT.md`](docs/rewrite/FORTSCHRITT.md) — Plan und
  Fortschrittsprotokoll des Umbaus von der ursprünglich übernommenen Kette
  auf die heutige Struktur.

## Status

Der Umbau in fünf Stufen (`data/` → `derived/prep/` → `derived/layers/` →
`out/` über `pipeline/finalize.py` und `pipeline/export/`) ist
abgeschlossen: `make test` läuft grün (**213 passed, 4 skipped**), `make`
ohne Argument baut alle vier Endprodukte end-to-end, die Prep-Stufe ist
beim zweiten Lauf vollständig wiederholbar (alle zwölf Prep-Stufen
übersprungen — Details und Einschränkungen der übrigen Stufen siehe „Die
Kette" oben), und `out/abschichtung.tif` ist per `sha256` gegen die
Referenz (`fb57c41d…232c30`) verifiziert.

Offen bleibt eine inhaltliche Frage, keine technische: ob die 18 von 38
Bändern (Human-Exclusion-Kette), die aus zwei am 08.09.2026 vom Nutzer
bereits entschiedenen Ursachen von `run1` abweichen, für die Ablösung des
alten Repos `windkraft_ö_karten` ausreichen — siehe `docs/HANDOFF.md` und
`docs/rewrite/FORTSCHRITT.md` für die vollständige Rangliste der
Abweichungen.
