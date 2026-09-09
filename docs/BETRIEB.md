# Betrieb und Entwicklung

Alles, was man braucht, um die Kette zu betreiben, zu verändern und ihr
Ergebnis zu prüfen. Was das Projekt tut und wie man es zum Laufen bringt,
steht in der [README](../README.md); dieses Dokument setzt dort an, wo
`make` einmal durchgelaufen ist.

## Die Kette im Detail

Fünf Stufen, jede darf nur aus der vorigen lesen:

```
data/   →   derived/prep/   →   derived/layers/   →   out/
 Roh          Prep                Layer            Finalize + Export
```

| Ziel | Was es tut |
|---|---|
| `make prep` | Überführt Rohdaten aus `data/` nach `derived/prep/` — neun Domänen (`admin`, `adressen`, `gelaende`, `kataster`, `natur`, `noe_sekrop`, `osm`, `widmung`, `zonen`), drei davon intern zweistufig: zwölf einzeln überspringbare Stufen. |
| `make layers` | Baut die 39 Checkpoint-Layer in `derived/layers/`, in der Reihenfolge `hig` → `osm` → `geo`. |
| `make finalize` | Komponiert daraus das 44-Band-GeoTIFF plus Manifest nach `out/` (rund drei Minuten). |
| `make export` | Die Export-Ziele `dashboard`, `viewer`, `gemeinden`, `wka_bestand`, `layer_md`. |
| `make all` (= `make`) | `prep` → `layers` → `finalize` → `export`. |
| `make validate PAKET=<name>` | Vergleicht ein finalisiertes TIF bandweise gegen ein Vergleichsraster (`ABSCHICHTUNG_RUN1`) und bewertet jede Abweichung. Bewusst **nicht** Teil von `make all` — siehe `make/validate/README.md`. |
| `make test` | `uv run pytest tests/ -v` |
| `make check-guards` | Beide Rohdaten-Wächter (siehe unten). |
| `make worktree PAKET=<name>` | Legt neben dem Repo ein Arbeitsverzeichnis mit `data/` und `derived/` als Symlinks an, um parallel arbeiten zu können, ohne Rohdaten zu kopieren. |

Jede Stufe hat ihr eigenes Unterverzeichnis unter `make/` mit einer
`.mk`-Datei je Domäne, die das `Makefile` per `-include` einliest. Die
Konvention steht in der jeweiligen `make/<stufe>/README.md`.

### Die sechs Endprodukte

Alle unter `out/`, alle gitignored:

| Datei | Inhalt |
|---|---|
| `abschichtung.tif` | Das 44-Band-Raster, `uint8`, EPSG:31287, 25 m (≈ 153 MB). |
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
steht in [`HANDOFF.md`](HANDOFF.md).

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
Abhängigkeiten. Begründung und Details: [`rohdaten.md`](rohdaten.md),
Abschnitt 9.

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
