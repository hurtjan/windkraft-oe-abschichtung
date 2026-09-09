# Abschichtung Widmung v2

Berechnet aus amtlichen Widmungs-/Zonierungsdaten, OSM-Extrakten und
Geodaten (DGM, Windatlas, Verwaltungsgrenzen) die österreichweite
Windkraft-Potentialfläche nach dem Widmung-v2-Verfahren — Ausschluss- und
Abstandskriterien für Mensch, Natur und Geografie.

Hauptergebnis ist ein **44-Band-GeoTIFF** (`out/abschichtung.tif`, `uint8`,
EPSG:31287, 25 m Pixelgröße) samt maschinenlesbarem Sidecar-Manifest
(`out/abschichtung.bands.json`, Schema 2.2.0). Wer dieses Ergebnis
weiterverarbeitet, findet den Vertrag dafür in
[`docs/HANDOFF.md`](docs/HANDOFF.md) — nicht in diesem README.

Das Repo ist die additive Neufassung der Widmung-v2-Kette aus dem alten,
gewachsenen Repo `windkraft_ö_karten`. Das alte Repo bleibt unangetastet als
Sicherheitsnetz bestehen und war bis zum ersten verifizierten Lauf hier die
Quelle der Wahrheit.

## Schnellstart

```bash
# 1. Systemvoraussetzung (nicht über uv/pip installierbar)
brew install osmium-tool

# 2. Abhängigkeiten
uv sync

# 3. Rohdaten nach data/ bringen — siehe "Daten besorgen", ohne sie
#    rechnet die Kette still falsch statt abzubrechen
#    (rund 13 GB, nicht im Repo enthalten)

# 4. Wächter, bevor irgendetwas läuft
make check-guards

# 5. Die volle Kette: prep -> layers -> finalize -> export
make

# 6. Tests
make test
```

`make` ohne Argument ist identisch mit `make all` (`.DEFAULT_GOAL := all`).
Ein Kaltstart aus leerem `derived/` dauert rund eine Stunde, ein zweiter
Lauf mit unveränderten Eingaben wenige Minuten — siehe „Die Kette“ unten für
die Details und die Grenzen dieser Wiederholbarkeit.

**Ohne `data/` ist nichts davon sinnvoll lauffähig.** Die Kette bricht bei
fehlenden Rohdaten in den meisten Fällen *nicht* ab, sondern erzeugt ein
plausibel aussehendes, falsches TIF.

## Voraussetzungen

- **Python ≥ 3.10 und [uv](https://docs.astral.sh/uv/)** — Abhängigkeiten und
  Interpreter-Version stehen in `pyproject.toml`, `uv.lock` fixiert die
  Versionen. Alle Kettenschritte laufen über `uv run python …` (siehe
  `Makefile`).
- **`osmium-tool` als harte Systemvoraussetzung**, installiert außerhalb von
  uv/pip (`brew install osmium-tool`). `_run_osmium()`
  (`calc/abschichtung_common.py`, `subprocess.run(cmd, check=True)`) fängt
  keine Exception ab — ein fehlendes `osmium-tool` lässt den Lauf sofort mit
  `FileNotFoundError` abbrechen. Das ist der *laute* Fehlerfall. Still
  bleibt dagegen der leicht zu verwechselnde andere: **fehlende
  OSM-Rohdaten** (nicht das Tool) — siehe unten.
- **Speicherbedarf: rund 25 GB.** Zuletzt gemessen: `data/` 13 GB,
  `derived/` 12 GB, `out/` 145 MB. Alle drei Ordner sind gitignored und
  enthalten keine einzige versionierte Datei; das Repo selbst ist rund
  3,6 MB groß.

## Daten besorgen

`data/` ist gitignored und wird **nicht** mit diesem Repo mitgeliefert.
Provenienz und Bezugsquelle jeder einzelnen Datei stehen in
[`docs/rohdaten.md`](docs/rohdaten.md) — vor dem ersten Lauf lesen,
insbesondere Abschnitt „Warnung: stille Fallbacks bei fehlenden Rohdaten“:

> Eine unvollständige `data/`-Kopie erzeugt ein plausibel aussehendes, aber
> falsches TIF, ohne dass irgendwo ein Fehler erscheint.

Die Kette rechnet bei fehlenden Eingaben mit leeren oder degenerierten Daten
weiter. Die Fallback-Tabelle in `docs/rohdaten.md` nennt die einzelnen
Mechanismen; `docs/FOLLOWUPS.md` dokumentiert den stillen Fallback, den das
Altrepo an derselben Stelle hatte.

## Die Kette

Fünf Stufen, jede darf nur aus der vorigen lesen:

```
data/  ->  derived/prep/  ->  derived/layers/  ->  out/
 Roh         Prep               Layer            Finalize + Export
```

| Ziel | Was es tut |
|---|---|
| `make prep` | Überführt Rohdaten aus `data/` nach `derived/prep/` — **neun Domänen** (`admin`, `adressen`, `gelaende`, `kataster`, `natur`, `noe_sekrop`, `osm`, `widmung`, `zonen`), von denen drei intern zweistufig sind: **zwölf einzeln überspringbare Stufen** in der Praxis. |
| `make layers` | Baut die **39 Checkpoint-Layer** in `derived/layers/` — `hig` → `osm` → `geo`. |
| `make finalize` | Komponiert daraus das 44-Band-GeoTIFF plus Manifest nach `out/` (rund 165 s). |
| `make validate` | Vergleicht ein finalisiertes TIF bandweise gegen die Vergleichsbasis `run1`. Verlangt `PAKET=<name>` und ist **bewusst nicht** Teil von `make all` — Begründung im `Makefile` und in `make/validate/README.md`. |
| `make export` | Die fünf Export-Ziele `dashboard`, `viewer`, `gemeinden`, `wka_bestand` und `layer_md`. |
| `make all` (= `make`) | `prep` → `layers` → `finalize` → `export`, **ohne** `validate`. |
| `make test` | `uv run pytest tests/ -v`. |
| `make check-guards` | Beide Rohdaten-Wächter, siehe unten. |
| `make worktree PAKET=<paket>` | Legt neben dem Repo ein einsatzfähiges Arbeitsverzeichnis für ein Paket an. |

### Die sechs Endprodukte

Alle unter `out/`, alle gitignored:

- **`abschichtung.tif`** — das 44-Band-Raster (152,7 MB).
- **`abschichtung.bands.json`** — das Sidecar-Manifest, Schema 2.2.0.
- **`dashboard/`** — die Kartenansicht: `index.html` mit Leaflet über OSM,
  ein PNG-Overlay je Band (44 Stück, rund 20 MB), dazu `report.json` aus der
  Prüfstufe. Erzeugt von `pipeline/export/dashboard.py` (Prüfbericht) und
  `pipeline/export/viewer.py` (Karte) in dieser Reihenfolge.
- **`gemeinden.geojson`** — Gemeindegrenzen im Rasterbezug (26,8 MB).
- **`wka_bestand_punkte.geojson`** — 1595 bestehende Windkraftanlagen als
  Punkte. *Drei Eigenschaften (`operator`, `generator:output:electricity`,
  `start_date`) sind derzeit in allen Datensätzen leer* — die Tags werden
  beim PBF-Export nicht mitgezogen (Registerpunkt 63).
- **`LAYER.md`** — Bandbeschreibungen für Konsumenten. *Derzeit eine Kopie
  der Handvorlage `docs/layer.md`, kein aus dem Manifest erzeugtes Produkt*
  (Registerpunkt 66).

### Wiederholbarkeit — und wo sie aufhört

**Die Prep-Stufe ist vollständig wiederholbar.** Jede der zwölf Prep-Stufen
prüft über `pipeline/fingerprint.py`, ob ihre Eingaben unverändert sind und
ihre Ausgabe vorliegt, und überspringt sich dann sichtbar. Seit W6.6 geht
die eigene Quelldatei per `sha256` in den Fingerabdruck ein: eine
Codeänderung wird bemerkt.

**Die Layer-Stufe prüft nur teilweise.** `pipeline/layers/geo.py`
überspringt vollständig, `pipeline/layers/osm.py` überspringt einen Teil,
`pipeline/layers/hig.py` prüft gar nicht und baut bei jedem Lauf neu.

> ⚠️ **Der Fingerabdruck der Layer-Stufe kennt den eigenen Quelltext nicht**
> (Registerpunkt 68). Wer Layer-Logik ändert, kann von `make layers` ein
> `[skip] … already done` und ein TIF **ohne** seine Änderung bekommen. Ein
> frischer Klon ohne Checkpoints ist nicht betroffen — es trifft
> ausschließlich inkrementelle Läufe, und der Nachweis läuft immer
> inkrementell. Im Zweifel `derived/layers/` löschen.

`make finalize` und `make export` haben keine Fingerabdruckprüfung und
laufen immer vollständig durch.

> ⚠️ **Ein grünes `make validate` heißt „bitgleich wie zuletzt akzeptiert“,
> nicht „geprüft“.** Sobald ein Hash Referenz ist, nimmt `validate` den
> Schnellweg und vergleicht *keine* Bänder mehr. Diese Verwechslung hat
> Registerpunkt 68 monatelang verdeckt.

### Umgebungsvariablen

| Variable | Wirkung |
|---|---|
| `ABSCHICHTUNG_ROOT` | Überschreibt die Repo-Wurzel, aus der `pipeline/contract.py` alle Pfade ableitet. Vorgabe: das Repo selbst. |
| `ABSCHICHTUNG_RUN1` | Pfad zur Vergleichsbasis `run1.tif`. Vorgabe `None` — ohne gesetzte Variable überspringen `pipeline/validate.py` und `tests/test_referenz_tif.py` den bandweisen Vergleich **sichtbar**, statt abzubrechen. |
| `ABSCHICHTUNG_VERTRAGSTEST=1` | Schaltet die gegateten Langläufer in `tests/test_referenz_tif.py` frei (bandweiser Vergleich über rund 25 GB I/O, dazu eine volle Finalisierung). |
| `ABSCHICHTUNG_ALTREPO` | Pfad zum Altrepo `windkraft_ö_karten` für den Äquivalenztest `tests/test_distance_engine_equivalence.py`. |

```bash
export ABSCHICHTUNG_RUN1=~/Documents/master_windkraft/archiv/run1.tif
```

## Struktur

```
data/       Rohdaten (unveränderlich, per Wächter gesichert)
derived/    Zwischenstände — prep/ und layers/
out/        die sechs Endprodukte
pipeline/   die Kette: prep/ -> layers/ -> finalize.py -> validate.py -> export/
calc/       die Rechenlogik
make/ tools/ tests/ docs/
```

- **`data/`** — gitignored, ohne jede versionierte Ausnahme (Provenienz je
  Datei: [`docs/rohdaten.md`](docs/rohdaten.md)). Besteht seit W1.3
  ausschließlich aus echten Kopien, kein Hardlink mehr auf
  `windkraft_ö_karten`. Kein Codepfad darf hierher schreiben — mechanisch
  geprüft über `make check-guards`.
- **`derived/`** — gitignored, jederzeit löschbar. `prep/` sind die
  Prep-Ausgaben der neun Domänen (Zieldateien in `pipeline.contract.PREP`),
  `layers/` die 39 Checkpoint-Layer, aus denen `pipeline/finalize.py` das
  GeoTIFF komponiert.
- **`pipeline/`** — die Kette selbst:
  - `contract.py` — **der eine Pfadvertrag** für Rohpfade, Prep-Ausgaben,
    Layernamen und Produktpfade. Wird gelesen, nicht kopiert: wer einen Pfad
    braucht, importiert ihn von hier, statt ihn ein zweites Mal
    hinzuschreiben.
  - `prep/` — neun Domänen, drei davon zweistufig (`kataster/` mit
    `a_noe_polygonize.py` dann `b_export_parquet.py`, sowie `osm.py` und
    `noe_sekrop.py` mit je zwei intern geprüften Stufen).
  - `layers/` — `hig.py`, `osm.py`, `geo.py`, zusammen die 39 Checkpoints.
  - `finalize.py` — komponiert GeoTIFF plus Manifest.
  - `validate.py` — bandweiser Vergleich gegen `run1`. **Bewertet,
    entscheidet nicht** (siehe `make/validate/README.md`).
  - `export/` — `dashboard.py`, `viewer.py`, `gemeinden.py`,
    `wka_bestand.py`.
  - `runtime.py`, `fingerprint.py` — gemeinsame Hilfsmodule
    (Verzeichnisanlage, Datei-Fingerprinting).
- **`calc/`** — das Python-Paket mit der Rechenlogik: `calc/` selbst für die
  Kernberechnungen (`abschichtung_common.py`, `distance_engine.py`,
  `band_manifest.py`, `config.py`), `noe/` für niederösterreich-spezifische
  Quellenaufbereitung, `viz/band_metadata.py` für Darstellungs- und
  Bandmetadaten.
- **`make/`** — je Kettenstufe ein Unterverzeichnis mit `.mk`-Dateien, die
  das `Makefile` per `-include` einliest (`prep/`, `layers/`, `finalize/`,
  `validate/`, `export/`), damit parallel laufende Pakete nicht dieselbe
  Zeile im `Makefile` ändern müssen. Konvention: siehe die jeweiligen
  `make/<stufe>/README.md`.
- **`tools/`** — `check_hardlink_safety.py` und `check_raw_only.py`, die
  beiden Rohdaten-Wächter.
- **`tests/`** — Unit-, Äquivalenz- und Vertragstests; `pytest tests/`
  sammelt rekursiv alles darunter ein.
- **`config.json`** — die eine Konfigurationsdatei. Die tatsächlich
  gelesenen Rohpfade stehen dort **nicht** als Literal:
  `calc/config.py:load_config()` befüllt `cfg["paths"]` beim Laden aus dem
  Pfadvertrag `pipeline/contract.py`. Alles andere (Schwellwerte,
  Bundesland-Puffer, Windparameter) bleibt Literal in `config.json`.

## Das Band-Manifest

Downstream-Artefakte kannten Bandnamen und Bandreihenfolge des finalen
GeoTIFF früher nur, indem sie sie selbst nachbauten — mit der Folge, dass
sie wegdriften konnten, ohne dass es auffiel. Die Belege liegen vor:
`dashboard_data.json` trug 63 Bänder, `viewer/manifest.json` 39 Layer, das
TIF 38 — drei Zählungen zu drei Zeitpunkten.

`pipeline/finalize.py` schreibt deshalb über `calc/band_manifest.py`
(`write_band_manifest()`) direkt nach dem Komponieren des GeoTIFF ein
Sidecar `out/abschichtung.bands.json` — aus genau den Werten, die der
Schreibvorgang ohnehin kennt, ohne das fertige Raster erneut zu öffnen.
Bandzahl, -namen und -reihenfolge sind damit **per Konstruktion** identisch
mit dem TIF; es gibt keinen zweiten Erzeugungspfad, der auseinanderlaufen
könnte. Farben, Kategorien und Default-Sichtbarkeit kommen aus der
gemeinsamen Quelle `calc/viz/band_metadata.py`.

**Nie das eine ohne das andere entgegennehmen.** Ein TIF ohne sein Manifest
hat keine maschinenlesbare Aussage mehr darüber, was Band 17 bedeutet. Der
vollständige Vertrag steht in [`docs/HANDOFF.md`](docs/HANDOFF.md).

### Die aktuelle Referenz

| | |
|---|---|
| Bänder | **44** |
| Manifest | Schema **2.2.0** |
| `sha256` | `99d522239dc499b833cab3080c810b9568ac3078a66b81a470e37228b55a96ac` |
| Größe | 152 656 278 Bytes |

Verdrahtet in `pipeline/validate.py` und `tests/test_referenz_tif.py`, läuft
bei jedem `make test` mit. Vorgänger als historische Zeugen: `a905c056…`
(W7.1, 44 Bänder) und `fb57c41d…` (Wellen 0–6, 38 Bänder). Die
Vergleichsbasis `run1` (`dc58b011…`, 38 Bänder) bleibt unverändert;
`pipeline/validate.py` verträgt seit W7.4 die abweichende Bandzahl und weist
die sechs neuen Bänder als „ohne Gegenstück“ aus, statt abzubrechen.

## Hardlink-Sicherheit prüfen

```bash
make check-hardlinks   # Dateisystem: kein Link-Count > 1 unter data/
make check-raw-only    # Code (per AST): kein Schreibpfad nach data/
make check-guards      # beide zusammen
```

**Nach dem Hinzufügen jedes neuen Datensatzes ausführen.** Ein
Schreibvorgang auf eine hardgelinkte Datei kürzt den geteilten Inode und
zerstört dieselbe Datei im Alt-Repo im selben Moment, ohne Fehlermeldung.
Seit W1.3 sind alle 48 verbliebenen Hardlinks unter `data/` aufgelöst; die
Link-Count-1-Regel gilt seither ausnahmslos für *jede* Datei dort, nicht
mehr nur für eine deklarierte Liste bekannter Schreibziele. Beide Wächter
laufen in Sekunden und ohne Abhängigkeiten.

Details und die Historie des behobenen Verstoßes:
[`docs/rohdaten.md`](docs/rohdaten.md) Abschnitt 9 und
[`docs/FOLLOWUPS.md`](docs/FOLLOWUPS.md), Abschnitt „Regel: die
Hardlink-Invariante“.

## Was dieses Repo nicht ist

- **Keine Widmung v1.** Die alte, 54-bändige Widmung-Kette
  (`scripts/main/create_widmung_wka_distance_zones.py` im Altrepo) wurde
  nicht übernommen und ist hier nicht lauffähig.
- **Keine eigenständige OSM-Kette.**
  `scripts/main/create_osm_wka_distance_zones.py` (reine OSM-Abstandszonen
  ohne Widmung) ist nicht Teil dieses Repos.
- **Keine zweite, alte Kette.** `scripts/widmung_v2/01…05_*.py` ist seit
  W6.1 entfernt (letzter Stand im Commit `f1d00f7`); das Ergebnis `run1.tif`
  und die alten Zwischenstände liegen außerhalb des Repos unter
  `~/Documents/master_windkraft/archiv/`. `scripts/` und `output/` gibt es
  nicht mehr.
- **Kein interaktiver Viewer für Endnutzer.** `out/dashboard/` ist eine
  Prüf- und Kartenansicht über die Bänder, kein Konsumentenprodukt — siehe
  [`docs/HANDOFF.md`](docs/HANDOFF.md).

Für all das bleibt `windkraft_ö_karten` die Quelle der Wahrheit.

## Verweise

- [`docs/HANDOFF.md`](docs/HANDOFF.md) — **Vertrag für Konsumenten** des
  GeoTIFF und seines Band-Manifests.
- [`docs/rohdaten.md`](docs/rohdaten.md) — Provenienz jeder Datei unter
  `data/`, inklusive der stillen Fallbacks.
- [`docs/layer.md`](docs/layer.md) — Bandbeschreibungen (Vorlage für
  `out/LAYER.md`).
- [`docs/FOLLOWUPS.md`](docs/FOLLOWUPS.md) — bei der Übernahme beobachtete,
  bewusst nicht behobene Bugs und Altlasten.
- [`docs/MIGRATION_MAP.tsv`](docs/MIGRATION_MAP.tsv) — alte Pfade im Altrepo
  → neue Pfade hier, mit Begründung.
- [`docs/widmung_v2.md`](docs/widmung_v2.md) — Referenzkarte der
  ursprünglich übernommenen Kette.
- [`docs/RUN1_VERGLEICH.md`](docs/RUN1_VERGLEICH.md) — Methodik und Ergebnis
  des ersten End-to-End-Laufs.
- [`docs/dataflow/`](docs/dataflow/) — Datenfluss-Diagramm.
- [`docs/rewrite/PLAN.md`](docs/rewrite/PLAN.md) und
  [`docs/rewrite/FORTSCHRITT.md`](docs/rewrite/FORTSCHRITT.md) — Plan und
  laufendes Protokoll des Umbaus, inklusive Register der offenen Punkte.

## Status

Der Umbau in fünf Stufen ist abgeschlossen — Welle 0 bis 6, 45 Pakete. Das
Zielbild ist am 08.09.2026 im Klontest abgenommen worden: ein frischer
`git clone`, `data/` als Symlink, `make` ohne Argument, durchgelaufen bis zu
den Endprodukten.

- `make test`: **245 bestanden, 3 übersprungen** (248 gesammelt), null
  Fehlschläge.
- `make` ohne Argument baut alle sechs Endprodukte end-to-end.
- `out/abschichtung.tif` ist per `sha256` gegen die Referenz verifiziert.
- Gegenüber `run1` bestehen **vier benannte Ursachen mit 19 betroffenen
  Bändern**, dazu sechs Bänder ohne Gegenstück. Alle in
  `docs/rewrite/abweichungen.tsv` mit Ursachentext, kein unerklärter Rest.

**Welle 7 läuft** (Layer-Struktur v4). Fertig sind W7.1 (Zuschnitt,
Punkte-Export, sechs neue Bänder, Manifest 2.2.0), W7.4 (`validate` verträgt
abweichende Bandzahl) und W7.5 (Personenseilbahnen auf `gondola`,
`cable_car`, `chair_lift`, `mixed_lift` eingeengt). Diese Pakete liegen auf
Feature-Zweigen, noch nicht auf `main`.

Die wichtigsten offenen Punkte — vollständig im Register in
`docs/rewrite/FORTSCHRITT.md`:

| # | Kurz |
|---|---|
| 68 | Der Fingerabdruck der Layer-Stufe kennt den eigenen Quelltext nicht — inkrementelle Läufe können eine Codeänderung still verschlucken. |
| 71 | Ein gegateter Vertragstest behauptet 18 abweichende Bänder; es sind 19. Läuft nur mit `ABSCHICHTUNG_VERTRAGSTEST=1`, `make test` bleibt deshalb grün. |
| 70 | Der Tunnelausschluss der Bänder 14–16 prüft nur den Tag `tunnel`, nicht `layer<0`. Wirkung höchstens 0,7 % der Potenzialfläche. |
| 66 | `out/LAYER.md` ist eine Handvorlage, kein aus dem Manifest erzeugtes Produkt. |
| 63 | Drei Eigenschaften des Punkte-Exports sind in allen 1595 Anlagen leer. |
