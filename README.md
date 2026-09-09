# Abschichtung Widmung v2

Berechnet die österreichweite Windkraft-Potentialfläche aus amtlichen
Widmungs- und Zonierungsdaten, OSM-Extrakten und Geodaten (Geländemodell,
Windatlas, Verwaltungsgrenzen). Das Verfahren wendet Ausschluss- und
Abstandskriterien für Mensch, Natur und Geografie schichtweise an —
„Abschichtung" — und weist am Ende die verbleibende Fläche aus.

Hauptergebnis ist ein **44-Band-GeoTIFF** samt maschinenlesbarem
Band-Manifest:

- `out/abschichtung.tif` — `uint8`, EPSG:31287, 25 m Pixelgröße
- `out/abschichtung.bands.json` — Sidecar-Manifest, Schema 2.2.0

Wer diese Dateien weiterverarbeitet (Dashboard, Viewer, Auswertung), findet
den Vertrag dafür in [`docs/HANDOFF.md`](docs/HANDOFF.md).

## Schnellstart

```bash
# 1. Systemvoraussetzung — nicht über uv/pip installierbar
brew install osmium-tool

# 2. Python-Abhängigkeiten
uv sync

# 3. Rohdaten nach data/ bringen (rund 13 GB, nicht Teil des Repos)
#    → Abschnitt "Rohdaten"

# 4. Wächter laufen lassen, bevor irgendetwas rechnet
make check-guards

# 5. Die volle Kette: prep → layers → finalize → export
make

# 6. Tests
make test
```

`make` ohne Argument ist identisch mit `make all`. Ein Kaltstart aus leerem
`derived/` dauert rund eine Stunde; ein zweiter Lauf mit unveränderten
Eingaben wenige Minuten (siehe „Wiederholbarkeit").

## Voraussetzungen

- **Python ≥ 3.10 und [uv](https://docs.astral.sh/uv/).** Abhängigkeiten und
  Interpreter-Version stehen in `pyproject.toml`, `uv.lock` fixiert die
  Versionen. Alle Kettenschritte laufen über `uv run python …`.
- **`osmium-tool`**, installiert außerhalb von uv/pip. Fehlt es, bricht der
  Lauf beim ersten OSM-Schritt mit `FileNotFoundError` ab — das ist der
  laute Fehlerfall. Der leise ist der gefährlichere, siehe „Rohdaten".
- **Rund 25 GB Plattenplatz:** `data/` ≈ 13 GB, `derived/` ≈ 12 GB,
  `out/` ≈ 150 MB. Alle drei Ordner sind gitignored; das Repo selbst ist
  rund 4 MB groß.

## Rohdaten

`data/` ist gitignored und wird **nicht** mitgeliefert. Bezugsquelle und
Provenienz jeder einzelnen Datei stehen in
[`docs/rohdaten.md`](docs/rohdaten.md) — vor dem ersten Lauf lesen.

> **Eine unvollständige `data/`-Kopie erzeugt ein plausibel aussehendes,
> aber falsches TIF, ohne dass irgendwo ein Fehler erscheint.**

Die Kette bricht bei fehlenden Rohdaten in den meisten Fällen nicht ab,
sondern rechnet mit leeren oder degenerierten Eingaben weiter. Welche
Datei welchen Fallback auslöst, steht in der Tabelle in `docs/rohdaten.md`.

`data/` wird ausschließlich gelesen. Kein Codepfad darf hierher schreiben —
das wird mechanisch geprüft (siehe „Rohdaten-Wächter").

## Die Kette

Fünf Stufen, jede darf nur aus der vorigen lesen:

```
data/   →   derived/prep/   →   derived/layers/   →   out/
 Roh          Prep                Layer            Finalize + Export
```

| Ziel | Was es tut |
|---|---|
| `make prep` | Überführt Rohdaten aus `data/` nach `derived/prep/` — neun Domänen (`admin`, `adressen`, `gelaende`, `kataster`, `natur`, `noe_sekrop`, `osm`, `widmung`, `zonen`), drei davon intern zweistufig: zwölf einzeln überspringbare Stufen. |
| `make layers` | Baut die **39 Checkpoint-Layer** in `derived/layers/`, in der Reihenfolge `hig` → `osm` → `geo`. |
| `make finalize` | Komponiert daraus das 44-Band-GeoTIFF plus Manifest nach `out/` (rund drei Minuten). |
| `make export` | Die fünf Export-Ziele `dashboard`, `viewer`, `gemeinden`, `wka_bestand`, `layer_md`. |
| `make all` (= `make`) | `prep` → `layers` → `finalize` → `export`. |
| `make validate PAKET=<name>` | Vergleicht ein finalisiertes TIF bandweise gegen ein Vergleichsraster (`ABSCHICHTUNG_RUN1`) und bewertet jede Abweichung. Bewusst **nicht** Teil von `make all` — siehe `make/validate/README.md`. |
| `make test` | `uv run pytest tests/ -v` |
| `make check-guards` | Beide Rohdaten-Wächter. |
| `make worktree PAKET=<name>` | Legt neben dem Repo ein Arbeitsverzeichnis mit `data/` und `derived/` als Symlinks an, um parallel arbeiten zu können, ohne Rohdaten zu kopieren. |

Jede Stufe hat ihr eigenes Unterverzeichnis unter `make/` mit einer
`.mk`-Datei je Domäne, die das `Makefile` per `-include` einliest. Die
Konvention steht in der jeweiligen `make/<stufe>/README.md`.

### Die sechs Endprodukte

Alle unter `out/`, alle gitignored:

| Datei | Inhalt |
|---|---|
| `abschichtung.tif` | Das 44-Band-Raster (≈ 153 MB). |
| `abschichtung.bands.json` | Das Sidecar-Manifest, Schema 2.2.0. |
| `dashboard/` | Kartenansicht: `index.html` mit Leaflet über OSM, ein PNG-Overlay je Band, dazu `report.json` mit Kennzahlen je Band. |
| `gemeinden.geojson` | Gemeindegrenzen im Rasterbezug (≈ 27 MB). |
| `wka_bestand_punkte.geojson` | Bestehende Windkraftanlagen aus OSM als Punkte (1 595 Anlagen). |
| `LAYER.md` | Bandbeschreibungen für Konsumenten in lesbarer Form. |

## Wiederholbarkeit

**Die Prep-Stufe ist vollständig wiederholbar.** Jede der zwölf Prep-Stufen
prüft über `pipeline/fingerprint.py`, ob ihre Eingaben *und ihr eigener
Quelltext* unverändert sind und ihre Ausgabe vorliegt, und überspringt sich
dann sichtbar. Der Kataster-Schritt allein dauert 45–70 Minuten — deshalb
lohnt sich das.

**Die Layer-Stufe prüft nur teilweise.** `geo` überspringt vollständig,
`osm` einen Teil, `hig` baut bei jedem Lauf neu.

> ⚠️ **Der Fingerabdruck der Layer-Stufe erfasst den eigenen Quelltext
> nicht.** Wer Logik in `pipeline/layers/` oder `calc/` ändert, kann von
> `make layers` ein `[skip] … already done` und ein TIF **ohne** seine
> Änderung bekommen. Ein frischer Klon ohne Checkpoints ist nicht betroffen;
> bei inkrementellen Läufen nach Codeänderungen `derived/layers/` löschen.

`make finalize` und `make export` haben keine Fingerabdruckprüfung und
laufen immer vollständig durch.

> ⚠️ **Ein grünes `make validate` heißt „bitgleich wie die Referenz", nicht
> „bandweise geprüft".** Stimmt der `sha256` des TIF mit der hinterlegten
> Referenz überein, nimmt `validate` den Schnellweg und vergleicht keine
> Bänder. Der bandweise Vergleich läuft nur bei Abweichung.

## Umgebungsvariablen

| Variable | Wirkung |
|---|---|
| `ABSCHICHTUNG_ROOT` | Überschreibt die Repo-Wurzel, aus der `pipeline/contract.py` alle Pfade ableitet. Vorgabe: das Repo selbst. |
| `ABSCHICHTUNG_RUN1` | Pfad zu einem Vergleichsraster für `make validate` und die Referenztests. Ohne die Variable wird der bandweise Vergleich **sichtbar übersprungen**, nicht abgebrochen. |
| `ABSCHICHTUNG_VERTRAGSTEST=1` | Schaltet die Langläufer in `tests/test_referenz_tif.py` frei: ein bandweiser Vergleich über rund 25 GB I/O und eine vollständige Finalisierung. |

## Projektstruktur

```
data/       Rohdaten — nur lesen, per Wächter gesichert
derived/    Zwischenstände: prep/ und layers/ — jederzeit löschbar
out/        die sechs Endprodukte
pipeline/   die Kette: contract.py, prep/, layers/, finalize.py, validate.py, export/
calc/       die Rechenlogik
make/       ein Unterverzeichnis je Stufe, eine .mk-Datei je Domäne
tools/      die beiden Rohdaten-Wächter
tests/      Unit-, Äquivalenz- und Vertragstests
docs/       Dokumentation
config.json Schwellwerte, Puffer, Windparameter
```

- **`pipeline/contract.py`** ist **der eine Pfadvertrag** für Rohpfade,
  Prep-Ausgaben, Layernamen und Produktpfade. Wer einen Pfad braucht,
  importiert ihn von hier, statt ihn ein zweites Mal hinzuschreiben.
- **`pipeline/prep/`** — neun Domänen. `kataster/` läuft zweistufig
  (`a_noe_polygonize.py`, dann `b_export_parquet.py`), `osm.py` und
  `noe_sekrop.py` haben je zwei intern geprüfte Stufen.
- **`pipeline/layers/`** — `hig.py`, `osm.py`, `geo.py`, zusammen die
  39 Checkpoints.
- **`pipeline/finalize.py`** — komponiert GeoTIFF plus Manifest.
- **`pipeline/validate.py`** — bandweiser Vergleich gegen ein
  Vergleichsraster. Bewertet, entscheidet nicht.
- **`pipeline/export/`** — `dashboard.py`, `viewer.py`, `gemeinden.py`,
  `wka_bestand.py`.
- **`calc/`** — Kernberechnungen (`abschichtung_common.py`,
  `distance_engine.py`, `band_manifest.py`, `config.py`), `noe/` für
  niederösterreich-spezifische Quellenaufbereitung, `viz/band_metadata.py`
  für Farben, Kategorien und Sichtbarkeit der Bänder.
- **`config.json`** — die eine Konfigurationsdatei. Rohpfade stehen dort
  **nicht** als Literal: `calc/config.py:load_config()` befüllt
  `cfg["paths"]` beim Laden aus `pipeline/contract.py`. Schwellwerte,
  Bundesland-Puffer und Windparameter bleiben Literal.

## Das Band-Manifest

Ein Raster mit 44 Bändern ist ohne Angabe, was Band 17 bedeutet, nicht
auswertbar. Konsumenten, die Bandnamen und Reihenfolge selbst nachbauen,
driften früher oder später vom tatsächlichen Raster weg, ohne dass es
auffällt.

Deshalb schreibt `pipeline/finalize.py` über `calc/band_manifest.py` direkt
nach dem GeoTIFF das Sidecar `out/abschichtung.bands.json` — aus genau den
Werten, die der Schreibvorgang ohnehin kennt, ohne das fertige Raster
erneut zu öffnen. Bandzahl, -namen und -reihenfolge sind damit **per
Konstruktion** identisch mit dem TIF. Farben, Kategorien und
Default-Sichtbarkeit kommen aus `calc/viz/band_metadata.py`.

**Nie das eine ohne das andere entgegennehmen.** Der vollständige Vertrag
steht in [`docs/HANDOFF.md`](docs/HANDOFF.md); die Bandbeschreibungen in
lesbarer Form liegen nach `make export` unter `out/LAYER.md`.

### Referenzausgabe

| | |
|---|---|
| Bänder | 44 |
| Manifest | Schema 2.2.0 |
| `sha256` | `99d522239dc499b833cab3080c810b9568ac3078a66b81a470e37228b55a96ac` |
| Größe | 152 656 278 Bytes |

Verdrahtet in `pipeline/validate.py` und `tests/test_referenz_tif.py`; läuft
bei jedem `make test` mit. Die Kette ist deterministisch: gleiche Rohdaten,
gleicher Code, gleiches TIF, bitgleich.

## Rohdaten-Wächter

```bash
make check-hardlinks   # Dateisystem: keine Datei unter data/ mit Link-Count > 1
make check-raw-only    # Code (per AST): kein Schreibpfad nach data/
make check-guards      # beide zusammen
```

**Nach jedem neu hinzugefügten Datensatz ausführen.** Ein Schreibvorgang auf
eine hardgelinkte Datei kürzt den geteilten Inode und verändert damit still
jede andere Datei, die auf denselben Inode zeigt — auch außerhalb dieses
Repos. Der eine Wächter prüft die Tatsache am Dateisystem, der andere den
Code, der sie herbeiführen könnte. Beide laufen in Sekunden und ohne
Abhängigkeiten. Begründung und Details:
[`docs/rohdaten.md`](docs/rohdaten.md), Abschnitt 9.

## Tests

```bash
make test
```

Stand: **245 bestanden, 3 übersprungen**, null Fehlschläge. Die drei
übersprungenen sind Langläufer beziehungsweise Vergleiche, die nur mit
gesetzter `ABSCHICHTUNG_RUN1` oder `ABSCHICHTUNG_VERTRAGSTEST=1` laufen.
`tests/conftest.py` zieht eine Untergrenze für die Zahl gesammelter Tests
ein — ein stillschweigend verschwundener Test lässt die Session abbrechen.

## Bekannte Einschränkungen

- **Layer-Fingerabdruck ohne Quelltext** — siehe „Wiederholbarkeit". Nach
  Codeänderungen in der Layer-Stufe `derived/layers/` löschen.
- **`wka_bestand_punkte.geojson`:** `operator`,
  `generator:output:electricity` und `start_date` sind in allen Anlagen
  leer. Die Tags werden beim PBF-Export nicht mitgezogen; der
  Auswertungscode steht bereits und füllt sich, sobald sie es werden.
- **Tunnelausschluss** der Verkehrsbänder (Straße, Bahn, Seilbahn) prüft nur
  den OSM-Tag `tunnel`, nicht `layer<0`. Wirkung nach oben abgeschätzt unter
  0,7 % der Potenzialfläche.

## Dokumentation

- [`docs/HANDOFF.md`](docs/HANDOFF.md) — Vertrag für Konsumenten des GeoTIFF
  und seines Manifests.
- [`docs/rohdaten.md`](docs/rohdaten.md) — Bezugsquelle und Provenienz jeder
  Datei unter `data/`, inklusive der stillen Fallbacks.
- `out/LAYER.md` — Beschreibung aller 44 Bänder, entsteht bei `make export`.
- [`docs/dataflow/`](docs/dataflow/) — Datenfluss-Diagramm der Kette.
- `make/<stufe>/README.md` — Konventionen je Kettenstufe.
