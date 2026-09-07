# Rohdaten — Herkunft von `data/`

> **Dies ist eine Beschreibung, keine Kopie.** Die Rohdaten selbst liegen
> **nicht** in diesem Repo — `data/` ist per `.gitignore` vollständig
> ausgeschlossen (`/data/*`), ohne Ausnahme. `output/` ebenso, komplett
> `.gitignore`d. Ein neues Setup muss jeden Datensatz unten selbst von
> seiner Quelle beziehen bzw. — im gewöhnlichen Fall — per Hardlink aus dem
> alten Repo (`windkraft_ö_karten/`) übernehmen. Diese Datei ist die
> einzige Nachweiskette dafür, mit welchen Daten gerechnet wurde.
>
> **Nachtrag (Paket W1.2):** Diese Datei lag ursprünglich unter
> `data/README.md` und war dort die einzige Ausnahme von `/data/*`
> (`!/data/README.md`). W1.2 hat sie nach `docs/rohdaten.md` verschoben,
> weil `data/` nach diesem Paket ausnahmslos Rohdatenbaum bleibt und keine
> versionierte Datei mehr enthält — siehe `tools/check_raw_only.py` (W1.4).
> Der `worktree`-Baustein im `Makefile`, der zuvor `data/README.md` per
> `git update-index --skip-worktree` behandelte, wurde entsprechend
> angepasst (siehe Bericht zu W1.2). Pfadangaben unten, die auf
> `data/README.md` verweisen, sind historisch und beziehen sich auf den
> Stand vor diesem Umzug.
>
> **Dieses Dokument ist die Nachfolgeversion von
> `windkraft_ö_karten/source_data_README.md`**, neu geschrieben für die
> Abschichtung-Restrukturierung (`master_windkraft/abschichtung/`). Alle
> Pfade unten sind Zielpfade unter `data/`, nicht die (teils historisch
> gewachsenen, uneinheitlichen) Pfade im alten Repo — diese sind als
> „Quellpfad (altes Repo)“ separat angegeben, weil die Migration per
> Hardlink noch aussteht und jemand sie nachvollziehen können muss.
>
> Stand der Prüfung: 2026-09-06, gegen den Datenbestand von
> `windkraft_ö_karten` (Arbeitsrechner-Stand). Größen sind mit `du -sh` neu
> gemessen, nicht aus der Vorgänger-Doku übernommen. OGD-Portale
> überschreiben Datensätze teils in place — ein späterer Download unter
> derselben Adresse kann daher abweichen. Die Angaben dokumentieren, was
> tatsächlich verwendet wurde, nicht eine garantiert wiederherstellbare
> Version.

**Lizenzen (kurz):** Belegt sind bislang OÖ und Tirol (**CC-BY 4.0**,
Flächenwidmung) sowie OSM/Geofabrik (**ODbL 1.0**). Für alle übrigen Quellen
ist die Lizenz **nicht** im Repo belegt und vor einer Veröffentlichung bei
der jeweiligen Landes-/Bundesstelle zu klären — überall dort steht unten
`unbekannt — zu klären`. Bei `luca_zonen` (Stmk, Sbg) ist der Fall anders
gelagert: strukturell unklar, siehe Block 1.

---

## 0. Die zwei wichtigsten Warnungen zuerst

### 1. `luca_zonen/Stmk.shp` und `luca_zonen/Sbg.shp` sind NICHT reproduzierbar

> **Diese beiden Dateien sind von Hand in einem GIS nachgezeichnet, nicht
> amtlich bezogen. Es gibt keine Download-Quelle, weil es keine gibt.**
> Laut Auskunft des Projektinhabers stammen sie von einer Person, die die
> steirischen und salzburgischen Windkraft-Vorrangzonen mit einem
> GIS-System **von Hand nachgezeichnet** hat.
>
> **Gehen `Stmk.shp` oder `Sbg.shp` verloren, sind sie nur durch erneutes
> Nachzeichnen wiederherstellbar — es gibt keinen Skript-Weg, keine
> Download-Adresse und keinen amtlichen Datensatz, der sie regeneriert.**
> Anders als `output/noe/alignment_mindestabstand.json` (siehe §4), das aus
> einem PDF neu erzeugbar ist, gibt es hierfür keinen Code-Fix.

| Eigenschaft | Wert |
|---|---|
| Dateien | `data/zonen/luca_zonen/Stmk.shp` (72 KB, 18 Features), `data/zonen/luca_zonen/Sbg.shp` (148 KB, 13 Features) |
| CRS | EPSG:25833 |
| Herkunft | Handdigitalisierte Nachzeichnung amtlicher Windkraft-Vorrangzonen; Auskunft des Projektinhabers über eine parallele Claude-Session — **nicht aus den Daten selbst belegbar** |
| Genauigkeit | Unbekannt — eine Nachzeichnung weicht in unbekanntem Ausmaß vom amtlichen Original ab (Digitalisierungsfehler, Generalisierung, veraltete Basis) |
| Lizenz | Strukturell unklar, nicht nur unrecherchiert: ein abgeleitetes Werk, dessen Status vom amtlichen Original **und** von der (unbekannten) Vereinbarung mit der zeichnenden Person abhängt → `unbekannt — zu klären`, aber aus anderem Grund als bei den übrigen Quellen |
| Neu beschaffbar | **Nein** — nur durch erneutes manuelles Nachzeichnen, kein Download möglich |
| Bekannte Digitalisierungsartefakte | In `Sbg.shp`: Feature `fid 10`/`fid 11` überlappen zu 93 % (IoU) — vermutlich Dublette; `fid 3`/`fid 4` berühren sich bei Distanz 0 ohne Flächenüberlappung — vermutlich eine beim Nachzeichnen getrennte Zone. Für Band 37 folgenlos (Zonen werden per OR zu einer Maske verschmolzen), betrifft nur die Feature-Zahl |

Verwendet für Band 37 (`official_wind_zoning`, rein referenziell, siehe §3).
Details und der korroborierende Befund: siehe Vorgängerdokument
`windkraft_ö_karten/source_data_README.md` Abschnitt 4, dort ungekürzt
erhalten.

---

### 2. Warnung: stille Fallbacks bei fehlenden Rohdaten

Die Widmung-v2-Kette bricht bei fehlenden Rohdaten **in den meisten Fällen
nicht ab**. Sie rechnet mit leeren oder degenerierten Eingaben weiter.

> **Eine unvollständige `data/`-Kopie erzeugt ein plausibel aussehendes,
> aber falsches TIF, ohne dass irgendwo ein Fehler erscheint.**

Verifiziert am Quellcode von `windkraft_ö_karten` (Stand dieser Prüfung):

| Mechanismus | Fundstelle | Verhalten |
|---|---|---|
| `wind_zones._resolve_path()` | `windkraft/calc/wind_zones.py:177-190` | Prüft `path.exists()`; fehlt die Datei, wird **nur** `[warn] wind zone source missing: <path>` geloggt und die Quelle übersprungen — kein Abbruch. Bei defektem ZIP ohne lesbares `.shp` ebenfalls nur `[warn]`, keine Exception |
| `osm_layer_path()` | `windkraft/calc/abschichtung_common.py:470-503` (zweite, ältere Kopie in `scripts/main/create_osm_wka_distance_zones.py:746`) | Fehlt das PBF, fällt die Funktion **kommentarlos** auf die Legacy-Shapefile-Namen zurück (`gis_osm_*_free_1.shp`); ist der Layer nicht in der Legacy-Fallback-Tabelle enthalten, wird der nicht existierende Pfad `Path("__missing_osm_layer__")` zurückgegeben — **kein Log an dieser Stelle** |
| `read_layer()` | `windkraft/calc/abschichtung_common.py:518-519` | Prüft nur `path.exists()`; fehlt die Datei (z. B. weil `osm_layer_path()` gerade `__missing_osm_layer__` geliefert hat oder die Legacy-Shapefile fehlt), wird ein **leerer** `GeoDataFrame` zurückgegeben — **komplett still, kein Log irgendeiner Art** |
| `kataster_layers.py` — osmium-Fallback | `windkraft/calc/kataster_layers.py`, `pbf_buffer_mask()` (Zeilen ~858–876) | Fehlt `osmium-tool` im PATH (`osmium_available()`, Zeile 826) oder schlägt der `osmium`-Aufruf fehl, wird `subprocess.CalledProcessError` gefangen; die Funktion loggt `WARN osmium filter failed …` bzw. `WARN osmium not found in PATH; PBF-only layers stay empty.` und liefert ein reines `np.zeros(shape, dtype=bool)` zurück — die betroffenen Bänder (Gas-Hochdruck, Seilbahn, Radar, Richtfunk, Militärflugplatz) werden lautlos komplett leer, die Pipeline läuft normal weiter |

**Weitere, im Zuge dieser Prüfung zusätzlich gefundene stille Fallbacks**
(über die drei oben genannten hinaus):

- `_build_official_nature_mask()` (`abschichtung_common.py:1167`): fehlt das
  Naturschutz-ZIP oder sind `nsg_gpkg`/`nsg_layers` in der Config leer, wird
  ohne Log übersprungen (Band 21 `nature_protection_areas` bleibt komplett
  0).
- Fehlendes DGM oder fehlende GWA-Leistungsdichte:
  `_read_raster_on_grid()`-Pfad um Zeile 1234 liefert bei fehlendem Rasterpfad
  ein reines NaN-Array **ohne Log**; Folge: `geography_wind_too_low` wird
  überall `True`, die verfügbare Fläche kollabiert auf ~0 km².
- Fehlende VGD-Grenzen: die Österreich-Clip-Maske liefert `np.ones(...)`
  zurück statt zu warnen — alles gilt als „in Österreich“, Aggregatbänder
  reichen dann über Nachbarländer hinaus.
- `major_airport_osm_ids` nicht im Transport-Layer gefunden
  (`abschichtung_common.py:1128-1132`): **einziger Fall mit sichtbarem
  Log** unter den geprüften Mechanismen — `[warn] airport corridors: … Fallback
  auf die N größten Aerodrome-Flächen` — andere Flughäfen als konfiguriert
  werden sonst ausgeschlossen.
- `wind_zones.py` zusätzlich: fehlende Bundesland-Zuordnung einer
  Windzonen-Quelle (Zone bleibt ungeclippt, nur `[warn]`), keine Fläche nach
  Filter/Clip übrig (`[warn] wind zone source '<key>' has no usable
  features`), keine Quelle überhaupt ladbar (`[warn] zones enabled but no
  source could be loaded`, liefert `None` statt zu werfen).
- **Checkpoints prüfen keinen Rohdaten-Fingerprint** für Infra-, Flughafen-,
  Natur-, Geographie-, Wasser- und Zonierungs-Bänder — siehe §0.3, eigene
  Warnung, weil die Konsequenz gravierender ist als bei den übrigen
  Fallbacks hier.

Hart abgebrochen wird nur bei fehlenden **Zwischenprodukten der eigenen
Pipeline** (Stufe-2-Cover-Layer, Stufe-4-Pflicht-Checkpoints) — nicht bei
fehlenden Rohdaten. Faustregel: nach neuen Rohdaten oder geänderter Config
immer `--force-layers` auf Stufe 3 und 4 verwenden.

---

### 3. Checkpoints ohne Rohdaten-Fingerprint — kein Fehlschlag, sondern stille Vermischung alt/neu

> **Man tauscht eine Quelldatei aus, lässt die Pipeline laufen, sie meldet
> Erfolg — und das Ergebnis mischt still alte und neue Daten.**

Das ist schlimmer als die übrigen unter §0.2 dokumentierten stillen
Fallbacks: Dort bleibt ein Band leer oder degeneriert — ein unvollständiges,
aber als solches erkennbares Ergebnis. Hier dagegen bleibt jedes einzelne
Band für sich genommen plausibel; nur die Kombination ist inkonsistent (ein
Teil der Bänder rechnet noch mit der alten Quelldatei, ein anderer Teil
schon mit der neuen), ohne dass die Pipeline dafür ein Signal liefert.

**Mechanismus, verifiziert im Quellcode von `windkraft_ö_karten`:**
`layer_done()` (`windkraft/calc/abschichtung_common.py:1421-1439`) hält
einen Checkpoint für gültig, sobald Shape/CRS/Transform/Bandname passen —
einen Fingerprint der Eingabedatei prüft es nur, wenn `ensure_group_layers()`
(`abschichtung_common.py:1458-1483`) ihm eine `extra_ok`-Funktion mitgibt.

Das geschieht **nicht** für folgende Gruppen (kein `extra_ok`/`extra_tags`
beim jeweiligen `ensure_group_layers()`-Aufruf):

| Gruppe | Fundstelle (kein Fingerprint) |
|---|---|
| Infrastruktur-Masken | `scripts/main/build_widmung_v2_layers.py:264` |
| Flughafen-Korridor-Masken | `scripts/main/build_widmung_v2_layers.py:265` |
| Natur-Masken | `scripts/main/create_widmung_v2_distance_zones.py:441` |
| Geographie-Masken | `scripts/main/create_widmung_v2_distance_zones.py:442` |
| Wasser-Masken | `scripts/main/create_widmung_v2_distance_zones.py:443` |
| Amtliche Windzonen-Referenz (Zonierung) | `scripts/main/create_widmung_v2_distance_zones.py:454` |

Zum Vergleich, wo es **wohl** einen Fingerprint gibt (`extra_tags` wird
gesetzt): Gebäudebänder tragen `HIG_SOURCE_FINGERPRINT`
(`scripts/main/build_widmung_v2_layers.py:246-249`), HiG-Familie und Puffer
tragen `SOURCE_FINGERPRINT` (`scripts/main/create_widmung_v2_distance_zones.py:240,394-406`).

**Abweichung von der Vorgabe-Annahme:** Die Vorgabe für diese Prüfung
nannte fünf betroffene Gruppen (Infra, Flughafen, Natur, Geographie,
Zonierung). Der Code zeigt eine **sechste, zusätzliche** Gruppe ohne
Fingerprint: die **Wasser-Masken** (`WATER_BANDS`,
`create_widmung_v2_distance_zones.py:443`) — oben mit aufgenommen, nicht nur
der Vorgabe halber weggelassen. Die Vorgabe-Bezeichnung „SOURCE_FINGERPRINT“
selbst stimmt; Gebäudebänder nutzen daneben die Variante
`HIG_SOURCE_FINGERPRINT` (siehe Vergleichstabelle oben).

Diese Einstufung deckt sich mit der Warm-Check-Matrix im Vorgängerdokument
(`windkraft_ö_karten/docs/README_widmung_v2_provenance.md`, Abschnitt 8,
Zeilen ~505-517): dort stehen exakt „Infra, Flughäfen“ (Stufe 3) und „Natur,
Geographie, Wasser, Zonierung“ (Stufe 4) als einzige Gruppen mit „wird nicht
erkannt: … nur `--force-layers`".

**Workaround:** Es gibt keinen automatischen Invalidierungsweg für diese
sechs Gruppen. Einzige Möglichkeit, einen veralteten Checkpoint zu
verwerfen, ist der manuelle Aufruf mit `--force-layers` (verifiziert u. a.
in `build_widmung_v2_layers.py:233`, `create_widmung_v2_distance_zones.py:378`
— beide definieren `--force-layers` als `argparse`-Flag, das
`ensure_group_layers()` den erzwungenen Neubau auslösen lässt). Ohne dieses
Flag meldet die Pipeline für die betroffene Gruppe `[skip]`/`[keep]` und
liefert wortlos die alten Bänder weiter — Faustregel siehe §0.2, Ende.

---

## 1. Verzeichnisstruktur (Zielpfade unter `data/`)

```
data/
├── gelaende/
│   ├── DGM_R25.tif                 750 MB  Höhenmodell 25 m — definiert Grid/CRS/Transform
│   └── AUT_power-density_150m.tif  6,6 MB  Global Wind Atlas
├── osm/
│   └── austria-260330.osm.pbf      760 MB  Geofabrik-PBF, speist viele Bänder
├── adressen/                       484 MB  BEV-Adressregister (+ 2 Parquet-Caches)
├── admin/
│   └── VGD_Oesterreich_gen_50_20221002/    20 MB  Verwaltungsgrenzen
├── natur/
│   └── SG_AT_2024_v_April_Stand_3_April_2024.zip   73 MB
├── kataster/                       9,1 GB  DKM/BEV-Rohdaten, 9 Archive → Geoparquet (erzeugt, §4)
├── widmung/                        ≈ 1,7 GB  Flächenwidmung, 9 Bundesländer, ein Verzeichnis je BL (siehe §3.3)
├── zonen/
│   ├── zonierung_noe.json          588 KB  amtliche NÖ-Zonierung, 71 Zonen
│   ├── luca_zonen/
│   │   ├── Stmk.shp                72 KB   NICHT reproduzierbar, siehe §0.1
│   │   └── Sbg.shp                 148 KB  NICHT reproduzierbar, siehe §0.1
│   ├── WK_Eignungszonen.zip        268 KB  Burgenland
│   └── RED_III_Windkraftbeschleunigungszone.zip   28 KB  Kärnten
└── noe_sekrop/
    └── TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf   16 MB  (nur Precondition für pdf_750m-Layer)
```

**Entfernt in Paket W1.2** (waren bis dahin an der Wurzel von `data/`, siehe
§2/§3.1 für den historischen Befund): `osm_power_lines.gpkg` (13 MB —
Codeleser `abschichtung_common.py:966` bestand nur als toter Fallback, der
nie griff, solange das OSM-PBF vorhanden ist, und dessen Ergebnisband
`power_380_400kv` seit dem Clean-38-Schema ohnehin nicht mehr gespeichert
wird), `WINDKRAFT_AUSSCHLUSSZONE.zip` (4,4 MB — kein Codeleser mehr, seit
W1.7 die Registrierung in `wind_zones.py` entfernt hat) und
`windkraftzonen_shapefile_2024.json` (588 KB — nie von einem Skript der
Referenzkette gelesen, siehe §3.1). `data/README.md` ist nach
`docs/rohdaten.md` verschoben (diese Datei hier). `.DS_Store` (zwei Stück)
und `data/adressen/.claude/` (Werkzeug-/Session-Metadaten) sind ebenfalls
entfernt.

Stand nach der Umsortierung des `data/`-Baums (Paket W0.1a), dem Nachziehen
der Codepfade (W0.1b) und dem Löschen der oben genannten toten Pfade
(W1.2); alte Verzeichnisnamen (`admin_boundaries/`, `adressregister/`,
`naturschutzgebiete/`, `nö_zonierung/`, `flächenwidmungen/`,
`new_widmungs_data/`) existieren nicht mehr, siehe §2/§3.

`output/` (komplett `.gitignore`d, keine Ausnahme) enthält die **erzeugten**
Artefakte, insbesondere `output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet`
(5,0 GB) und `output/noe/alignment_mindestabstand.json` — siehe §4.

---

## 2. Rohdaten — Referenz-Grid, OSM, Adressen (Stufe 2–4)

| Datensatz | Zielpfad | Herkunft | Bezugsweg/URL | Stand | Größe | Lizenz | Neu beschaffbar |
|---|---|---|---|---|---|---|---|
| Höhenmodell 25 m | `data/gelaende/DGM_R25.tif` | BEV / Land Austria | unbekannt — zu klären (manueller Download beim Arbeitsrechner-Stand) | 30.03.2026 | **750 MB** | unbekannt — zu klären | ja, eingeschränkt (Portal/Lizenz zu klären) |
| OSM Österreich (PBF) | `data/osm/austria-260330.osm.pbf` | Geofabrik | https://download.geofabrik.de/europe/austria.html | 30.03.2026 | **760 MB** | ODbL 1.0 | ja |
| Adressregister | `data/adressen/` | BEV | unbekannt — zu klären (manueller Download BEV-Portal) | Stichtag 01.10.2025 | **484 MB** (ZIP 93 MB + `ADRESSE.csv` 311 MB + 2 Parquet-Caches ~81 MB) | unbekannt — zu klären | ja, eingeschränkt |
| Leistungsdichte 150 m | `data/gelaende/AUT_power-density_150m.tif` | Global Wind Atlas | https://globalwindatlas.info | 29.03.2026 | **6,6 MB** | unbekannt — zu klären | ja |
| Verwaltungsgrenzen | `data/admin/VGD_Oesterreich_gen_50_20221002/` | BEV, generalisiert 1:50.000 | unbekannt — zu klären | 02.10.2022 | **20 MB** | unbekannt — zu klären | ja, eingeschränkt |
| Naturschutzgebiete | `data/natur/SG_AT_2024_v_April_Stand_3_April_2024.zip` | Umweltbundesamt / DORIS (OGD) | unbekannt — zu klären | 03.04.2024 | **73 MB** | unbekannt — zu klären | ja, eingeschränkt |
| OSM-Stromleitungen (**entfernt, Paket W1.2**) | war `data/osm_power_lines.gpkg` | abgeleitet aus Geofabrik-OSM | — (Export aus OSM-PBF) | 31.03.2026 | **13 MB** | ODbL 1.0 | entfällt |

**Entfernt in Paket W1.2 (war zuvor `data/osm_power_lines.gpkg`).** Die
Datei hatte einen einzigen Codeleser, `abschichtung_common.py:966`
(`build_infrastructure_masks()`, aufgerufen von
`scripts/widmung_v2/03_build_osm_layers.py`) — aber nur als Fallback, der
ausschließlich greift, wenn das konfigurierte OSM-PBF fehlt
(`pbf.exists()` ist `False`). Mit gepflegtem PBF (`data/osm/austria-260330.osm.pbf`,
Regelfall) wurde die Datei nie geöffnet. Das daraus gebaute Band
`power_380_400kv` ist zudem im **Clean-38-Schema nicht mehr enthalten** —
Stromleitungen sind seit `build_widmung_v2_layers.py` kein
Ausschlusskriterium mehr, das Ergebnis wäre also ohnehin verworfen worden.
Der Registereintrag `pipeline.contract.LEGACY_ENTFAELLT["powerlines_gpkg"]`
und der einzige Konsument dieses Eintrags,
`windkraft/config.py:load_config()`, sind mit W1.2 ebenfalls entfernt —
`cfg["paths"]` trägt seither keinen Schlüssel `powerlines_gpkg` mehr (siehe
§5).

**Was NICHT mitgezogen wird:** Der Legacy-Fallback
`austria-260328-free.shp/` bzw. `.zip` (Geofabrik-Shapefiles, 4,9 GB) wird
**bewusst nicht** nach `data/` migriert — er greift nur, wenn das PBF fehlt
(siehe §0.2, `osm_layer_path()`), und mit gepflegtem PBF ist er tote Last.
Siehe §5.

---

## 3. Rohdaten — Flächenwidmung, Windzonen, Naturschutz-Zonierung

### 3.1 Amtliche Windzonen (Band 37, rein referenziell)

Band 37 beeinflusst die Verfügbarkeitsrechnung (`available`) **nicht**,
sondern dient nur dem Soll/Ist-Vergleich. Zusammen unter 1 MB (ohne
`luca_zonen`, das separat in §0.1 behandelt ist).

| BL | Zielpfad | Herkunft | Bezugsweg/URL | Stand | Größe | Lizenz | Neu beschaffbar |
|---|---|---|---|---|---|---|---|
| NÖ | `data/zonen/zonierung_noe.json` | data.gv.at, LGBl. 47/2024, 71 Zonen | https://www.data.gv.at | unbekannt — zu klären (Dateidatum 30.04.2026) | **588 KB** | im Code als „meist CC-BY“ vermerkt, **nicht verifiziert** → unbekannt — zu klären | ja |
| Stmk, Sbg | `data/zonen/luca_zonen/{Stmk,Sbg}.shp` | handdigitalisiert | **keine** — siehe §0.1 | unbekannt — zu klären | 72 KB / 148 KB | strukturell unklar, siehe §0.1 | **nein** |
| Bgld | `data/zonen/WK_Eignungszonen.zip` | Land Burgenland | unbekannt — zu klären | `EXPORT_DAT 20260721` | **268 KB** | unbekannt — zu klären | ja, eingeschränkt |
| Ktn | `data/zonen/RED_III_Windkraftbeschleunigungszone.zip` | Land Kärnten | unbekannt — zu klären | unbekannt — zu klären | **28 KB** | unbekannt — zu klären | ja, eingeschränkt |
| — | **entfernt, Paket W1.2** (war `data/WINDKRAFT_AUSSCHLUSSZONE.zip`) | unbekannt — zu klären | unbekannt — zu klären | unbekannt — zu klären | **4,4 MB** | unbekannt — zu klären | entfällt |

**Datenqualitäts-Hinweis (verifiziert bei dieser Prüfung, weicht von der
Vorgabe-Annahme ab):** `data/windkraftzonen_shapefile_2024.json` wurde
bislang als „byte-identisches Duplikat“ von `zonierung_noe.json`
beschrieben. Ein `cmp -l` zeigt: beide Dateien sind exakt **600.056 Byte**
groß, unterscheiden sich aber an **11 Bytes** (Offsets 599964, 599966,
599967, 599970, 599972, 599973, 599975, 599976, 599978, 599979, 599980) —
sie sind **nicht** byte-identisch. Die Differenz ist trivial erklärt: alle
11 Bytes liegen innerhalb des `"timeStamp"`-Felds am Dateiende (WFS-
Exportzeitstempel `2026-04-30T10:27:19.593Z` in `zonierung_noe.json` gegen
`2026-03-29T19:46:44.865Z` in `windkraftzonen_shapefile_2024.json`) — alle
sonstigen Felder (`totalFeatures`, `numberMatched`, `numberReturned`, `crs`,
alle 71 Features) sind identisch. Es handelt sich also um zwei WFS-Exports
derselben 71 Zonen zu unterschiedlichen Zeitpunkten, kein inhaltlicher
Unterschied.

**Migrationsstatus (bei dieser Prüfung nachgemessen, ersetzt die Einstufung
in §6/§7):** Entgegen einer früheren Fassung dieses Dokuments (die behauptete,
`windkraftzonen_shapefile_2024.json` liege „nur unter
`windkraft_ö_karten/data/`, noch nicht unter `data/` im neuen Repo”, und
dass die Übernahme „ein späterer Migrationsschritt, hier nicht ausgeführt”
sei) zeigt `ls -la data/windkraftzonen_shapefile_2024.json` im neuen Repo:
die Datei liegt **bereits** dort, mit Link-Count 2 (also per Hardlink aus
`windkraft_ö_karten/data/` übernommen), 600.056 Byte — identisch zur
alten-Repo-Kopie. **Beide** Dateien (`zonierung_noe.json` und
`windkraftzonen_shapefile_2024.json`) liegen also bereits nebeneinander im
neuen Repo — die in §6/§7 dokumentierte Einstufung als „nicht migriert” ist
damit überholt. Welche der beiden Dateien als **autoritativ** gilt, ist bewusst **offen**
gelassen — das ist eine Datenfrage (welcher Exportzeitpunkt maßgeblich ist),
keine Migrationsfrage, und wird hier nicht entschieden. Band 37
(`official_wind_zoning`) liest per Default `data/zonierung_noe.json` —
verifiziert direkt im Quellcode:
`scripts/main/create_widmung_v2_distance_zones.py:363` definiert
`--official-zoning-geojson` mit Default `"data/zonierung_noe.json"`, dieser
Pfad speist `build_official_zoning_masks()` und damit `OFFICIAL_ZONING_BANDS`
(Band 37). `windkraftzonen_shapefile_2024.json` wird von keinem Skript der
Referenzkette gelesen (per Grep über alle `.py`-Dateien, siehe auch §6).

**Nachtrag (Paket W1.2):** Sowohl `data/windkraftzonen_shapefile_2024.json`
als auch `data/WINDKRAFT_AUSSCHLUSSZONE.zip` sind mit W1.2 aus `data/`
entfernt worden — der obige Befund zu fehlenden Codelesern ist damit die
Löschbegründung, nicht mehr nur eine Beobachtung. Für
`windkraftzonen_shapefile_2024.json` war das eine reine
Vorwärts-/Rückwärtssuche ohne Treffer (kein `.py`-Skript öffnet den Pfad,
auch nicht zusammengesetzt); für `WINDKRAFT_AUSSCHLUSSZONE.zip` hatte
bereits W1.7 den letzten Codeleser in `wind_zones.py` entfernt (siehe
dortige Modul-Docstring-Notiz zu `load_wind_exclusion_zones()`). Die
Autoritätsfrage zwischen `zonierung_noe.json` und
`windkraftzonen_shapefile_2024.json` (oben als „bewusst offen“
beschrieben) ist damit nicht mehr aktuell: Es existiert nur noch
`zonierung_noe.json`.

### 3.2 NÖ-SekROP, Mindestabstandszonen (Precondition)

| Datensatz | Zielpfad | Herkunft | Bezugsweg/URL | Stand | Größe | Lizenz | Neu beschaffbar |
|---|---|---|---|---|---|---|---|
| Mindestabstandszonen-Karte | `data/noe_sekrop/TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf` | Amt der NÖ Landesregierung | unbekannt — zu klären | 29.03.2026 (Dateidatum; Karten-Stand 02.04.2024) | **16 MB** | unbekannt — zu klären | ja, eingeschränkt |

Nur Precondition — erzeugt die `pdf_750m`-Layer und ist Grundlage für
`output/noe/alignment_mindestabstand.json` (§4.2). Kein direkter Rohdaten-
Input der Rasterbänder selbst.

### 3.3 Flächenwidmung, 9 Bundesländer

**Abweichung von der Vorgabe:** Die Task-Vorgabe nennt „8 Bundesländer“ —
tatsächlich liegen **9** vor, seit Wien am 29.07.2026 hinzukam. Gesamtgröße
der tatsächlich von der Referenzkette gelesenen Dateien: **≈ 1,7 GB**
(nachgemessen; die zuvor kolportierten „~1,76 GB“ treffen ungefähr zu).

**Tatsächliche Ablage (verifiziert gegen den Baum, nicht `data/widmung/`):**
Die Flächenwidmungsdaten liegen — sowohl im alten als auch im neuen Repo,
identisch — auf **zwei** Verzeichnisse verteilt, nicht unter einem
einheitlichen `data/widmung/<bl>/` (siehe Kasten am Ende dieses Abschnitts
zu diesem nie umgesetzten Vorschlag). Maßgeblich sind die Pfade, die
`windkraft/calc/widmung_sources.py` tatsächlich liest: die Konstanten
`NEW = ROOT / "data" / "new_widmungs_data"` und
`OLD = ROOT / "data" / "flächenwidmungen"` (Zeilen 38–40) sowie die
`source`-Felder im `DATASETS`-Dict (Zeilen 58–126), das für jedes der 9
Bundesländer den genauen Dateipfad und Layer/Spalten-Angaben trägt.
Nachgeprüft per `find`/`ls`/`du` gegen den aktuellen `data/`-Baum:

| BL | Tatsächlicher Pfad (altes UND neues Repo identisch) | Herkunft | Stand (Dateidatum) | Größe | Lizenz | Neu beschaffbar |
|---|---|---|---|---|---|---|
| Bgld | `data/flächenwidmungen/WIDMUNGSFLAECHEN.zip` | Land Burgenland (OGD) | 22.06. | **48 MB** | unbekannt — zu klären | ja |
| Ktn | `data/new_widmungs_data/kaernten/flawi_ktn_gpkg.zip` | Land Kärnten, KAGIS (OGD) | 12.07. | **142 MB** | unbekannt — zu klären | ja |
| NÖ | `data/new_widmungs_data/niederoesterreich/RRU_WI_HUELLE.gpkg` | Amt der NÖ Landesregierung, NÖ Atlas (OGD) | 10.07. | **110 MB** | unbekannt — zu klären | ja |
| OÖ | `data/new_widmungs_data/oberoesterreich/FLWI_WIDMUNGEN_F.zip` | Land Oberösterreich, DORIS | 10.07. | **138 MB** | **CC-BY 4.0** | ja |
| Sbg | `data/new_widmungs_data/salzburg/Flaechenwidmung_Shapefile.zip` | Land Salzburg, SAGIS (OGD) | 12.07. | **30 MB** | unbekannt — zu klären | ja |
| Stmk | `data/new_widmungs_data/steiermark/Bauland.zip` **+** `data/flächenwidmungen/Flaewi.shp.zip` | Land Steiermark (OGD) | 10.07. / 22.06. | **42 MB + 916 MB** | unbekannt — zu klären | ja |
| Tirol | `data/new_widmungs_data/tirol/FLW_Flaechenwidmung_*.gpkg` | Land Tirol, tiris | 12.07. | **106 MB** | **CC-BY 4.0** | ja |
| Vbg | `data/new_widmungs_data/vorarlberg/fwp_flaeche.gpkg` | Land Vorarlberg, VoGIS (OGD) | 12.07. | **144 MB** | unbekannt — zu klären | ja |
| Wien | `data/new_widmungs_data/wien/genflwidmung_wien.geojson` | Stadt Wien, WFS `ogdwien:GENFLWIDMUNGOGD` | 29.07. | **41 MB** | unbekannt — zu klären | ja (WFS, siehe unten) |

Wien-Bezugsweg (kein Abrufskript im Repo, manuell nachzuziehen):

```bash
curl "https://data.wien.gv.at/daten/geo?service=WFS&request=GetFeature&version=1.1.0&typeName=ogdwien:GENFLWIDMUNGOGD&srsName=EPSG:4326&outputFormat=json" \
  -o data/new_widmungs_data/wien/genflwidmung_wien.geojson
```

**Zwei-Ordner-Falle (gilt für alten UND neuen Baum, nicht nur für die
Migration):** Dieselben Daten liegen auf **zwei** Verzeichnisse verteilt
(`data/new_widmungs_data/` für Ktn/NÖ/OÖ/Sbg/Stmk-Bauland/Tirol/Vbg/Wien,
`data/flächenwidmungen/` für Bgld und die **vollständige** Steiermark-Quelle
`Flaewi.shp.zip`). Wer nur eines der beiden Verzeichnisse kopiert, verliert
entweder Burgenland komplett oder die Steiermark-Grünland-/Freizeit-Flächen.
Das gilt **unverändert auch im neuen Repo** — die Hardlink-Migration hat den
bestehenden Zwei-Ordner-Baum 1:1 übernommen, nicht die unten beschriebene
Zielstruktur.

> **Nicht umgesetzter Vorschlag — existiert NICHT auf der Platte:** Eine
> frühere Fassung dieses Dokuments beschrieb als Zielstruktur ein
> einheitliches `data/widmung/<bl>/` (z. B.
> `data/widmung/bgld/WIDMUNGSFLAECHEN.zip`,
> `data/widmung/wien/genflwidmung_wien.geojson`), um genau die oben
> beschriebene Zwei-Ordner-Falle beim Umzug aufzulösen. **Dieser Umzug
> wurde nie durchgeführt.** Weder im alten noch im neuen Repo existiert ein
> Verzeichnis `data/widmung/` — verifiziert per `find data -iname widmung`
> (kein Treffer in `master_windkraft/abschichtung/data/`) und durch Lesen
> von `windkraft/calc/widmung_sources.py`, das ausschließlich
> `data/flächenwidmungen/` und `data/new_widmungs_data/<land>/` liest (siehe
> Zeilenangaben oben). Die Hardlink-Migration ist dem tatsächlichen
> Code-Pfad gefolgt, nicht diesem Vorschlag. Sollte die Vereinheitlichung
> künftig gewünscht sein, ist sie ein eigener, bewusster Schritt (Dateien
> verschieben/neu hardlinken UND `widmung_sources.py` entsprechend
> anpassen) — nicht etwas, das die bestehende Migration schon erledigt hat.

**Nachtrag (Pakete W0.1a/W0.1b): Die Zwei-Ordner-Falle ist inzwischen
aufgelöst.** Der obige Befund („Tatsächliche Ablage“, die Zwei-Ordner-Falle
und der als „nicht umgesetzt“ beschriebene Vorschlag) beschreibt den Stand
**vor** dieser Restrukturierung und ist hier unverändert zur Nachvollziehbarkeit
stehen gelassen. Mit W0.1a wurde genau die oben skizzierte Zielstruktur
tatsächlich umgesetzt: alle 9 Bundesländer liegen jetzt unter einer
gemeinsamen Wurzel `data/widmung/<bundesland>/<datei>` (Burgenland:
`data/widmung/burgenland/WIDMUNGSFLAECHEN.zip`; Kärnten:
`data/widmung/kaernten/flawi_ktn_gpkg.zip`; Niederösterreich:
`data/widmung/niederoesterreich/RRU_WI_HUELLE.gpkg`; Oberösterreich:
`data/widmung/oberoesterreich/FLWI_WIDMUNGEN_F.zip`; Salzburg:
`data/widmung/salzburg/Flaechenwidmung_Shapefile.zip`; Steiermark:
`data/widmung/steiermark/Bauland.zip` **und**
`data/widmung/steiermark/Flaewi.shp.zip`, weiterhin beide nötig; Tirol:
`data/widmung/tirol/FLW_Flaechenwidmung_*.gpkg`; Vorarlberg:
`data/widmung/vorarlberg/fwp_flaeche.gpkg`; Wien:
`data/widmung/wien/genflwidmung_wien.geojson`). Mit W0.1b wurde
`windkraft/calc/widmung_sources.py` entsprechend nachgezogen: die beiden
Konstanten `NEW`/`OLD` aus dem obigen Zitat sind einer einzigen Wurzel
`WIDMUNG = ROOT / "data" / "widmung"` gewichen, `_read_raw()` bildet daraus
für jede der zehn Quellen den Pfad unter `data/widmung/<bundesland>/<datei>`.
Wer heute Burgenland oder die Steiermark-Grünland-/Freizeit-Flächen sucht,
findet sie nicht mehr unter `data/flächenwidmungen/`, sondern unter
`data/widmung/burgenland/` bzw. `data/widmung/steiermark/`.

**Steiermark braucht zwei Dateien gleichzeitig:** `Bauland.zip` liefert
Wohn-/Misch-/Industrieflächen, `Flaewi.shp.zip` (EPSG:4258, das einzige
geografische CRS unter allen 9 Ländern) liefert Grünland-/Freizeitflächen.
Beide werden von `windkraft/calc/widmung_sources.py` gelesen — keine der
beiden Dateien ist verzichtbar oder redundant zur anderen.

Welche Widmungscodes je Bundesland als Wohnbauland, Haus-im-Grünen oder
Industrie gelten, steht vollständig in `windkraft/calc/widmung_sources.py`
— nicht in `config/config.json`.

---

## 4. Erzeugte Artefakte (kein Rohdatum) — separat von §2/§3

### 4.1 DKM-Geoparquet — `output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet`

**Dies ist ein erzeugtes Artefakt, kein Rohdatum.** Es entsteht aus
`data/kataster/` (9,1 GB Rohdaten, 9 Archive à Bundesland, siehe unten) und
ist mit **5,0 GB** selbst größer als jedes einzelne Quell-Archiv.

> **Keine verlustfreie Umwandlung des 9,1-GB-Quellbestands.** Vollständige
> Übernahme zweier DKM-Ebenen (`GST_V2` Grundstücke, `NFL_V2`
> Nutzungsflächen) für acht Bundesländer, reprojiziert auf EPSG:31287 — plus
> eine Neu-Konstruktion für Niederösterreich aus DXF-Linienwerk, dort **ohne**
> Grundstücksebene. Sieben der neun Ebenen, die jede KG-Lieferung enthält
> (`FPT_V2, GNR_V2, NSL_V2, NSY_V2, SGG_V2, SSB_V2, VGG_V2` — verifiziert an
> einer KG aus `data/kataster/KAT_DKM_Vorarlberg_SHP_20221001.zip`, KG
> `90001`, die alle neun Ebenen enthält), werden nie gelesen. Die 9,1 GB
> unter `data/kataster/` sind deshalb keine bloße Zwischenkopie — sie
> enthalten Ebenen, die im Geoparquet gar nicht vorkommen.

**Lizenz — ungeklärt, vor jeder Weitergabe mit dem BEV zu klären.** Die
DKM-Lizenz ist im Repo nicht belegt (siehe bereits das Vorgängerdokument
`windkraft_ö_karten/source_data_README.md`, dortige Lizenz-Einleitung). Weil
`data/` per `.gitignore` vollständig ausgeschlossen ist, blockiert das den
Betrieb dieses Repos **nicht** — es blockiert aber die Weitergabe der
DKM-Rohdaten selbst **und** jeder daraus abgeleiteten Karte an Dritte, bis
die Lizenzfrage beim BEV geklärt ist.

| Bundesland | Archiv unter `data/kataster/` | Größe |
|---|---|---|
| Burgenland | `KAT_DKM_Burgenland_SHP_20210401.zip` | 789 MB |
| Kärnten | `KAT_DKM_Kaernten_SHP_20221001.zip` | 855 MB |
| Niederösterreich | `KAT_DKM_Niederoesterreich_DXF_20230401.zip` (DXF, **kein** SHP) | 1,4 GB |
| Oberösterreich | `KAT_DKM_Oberoesterreich_SHP_20221001.zip` | 1,5 GB |
| Salzburg | `KAT_DKM_Salzburg_SHP_20221001.zip` | 620 MB |
| Steiermark | `KAT_DKM_Steiermark_SHP_20221001.zip` | 1,9 GB |
| Tirol | `KAT_DKM_Tirol_SHP_20221001.zip` | 1,0 GB |
| Vorarlberg | `KAT_DKM_Vorarlberg_SHP_20221001.zip` | 525 MB |
| Wien | `KAT_DKM_Wien_SHP_20221001.zip` | 621 MB |
| (Symboltabelle) | `BEV_DKM_DXF_Symbole_V2.6.csv` | 8 KB — nur für NÖ-DXF nötig |

Stand der Archive (Dateidatum im Namen): überwiegend Oktober 2022 (Ktn, OÖ,
Sbg, Stmk, Tirol, Vlbg, Wien — `_20221001`), Burgenland April 2021
(`_20210401`), Niederösterreich April 2023 (`_20230401`). Herkunft:
BEV-Katalog, manueller Download — kein automatisierter Abrufweg im Repo.
Neu beschaffbar: ja, eingeschränkt (Portal/Lizenz zu klären).

**Was tatsächlich übernommen wird.** `SHP_LAYER_NAMES = ("GST_V2", "NFL_V2")`
(`scripts/main/export_at_dkm_geoparquet.py:71`, altes Repo, byteidentisch im
neuen Repo unter `scripts/preprocessing/export_at_dkm_geoparquet.py`) — nur
diese zwei der neun Ebenen werden je KG-Archiv extrahiert
(`extract_layer_shapefiles()`/`extract_layer_shapefiles_from_members()`,
`export_at_dkm_geoparquet.py:383-427`). Innerhalb dieser zwei Ebenen ist die
Übernahme für die acht SHP-Bundesländer (Bgld, Ktn, OÖ, Sbg, Stmk, Tirol,
Vlbg, Wien) tatsächlich vollständig — verifiziert gegen
`output/kataster/at_dkm_gst_nfl_epsg31287_summary.csv` (altes Repo):
**7.118.537** `GST_V2`-Features rein, 7.118.537 raus; **13.505.334**
`NFL_V2`-Features rein, 13.505.334 raus — kein Zeilenfilter.
`process_shp_gdf()` (`export_at_dkm_geoparquet.py:437-483`) übernimmt je
Zeile alle DBF-Attribute (`GST_V2`: `KG, GNR, RSTATUS, MST`; `NFL_V2`: `KG,
NS, NS_RECHT` — das ist bereits der volle DBF-Attributsatz dieser beiden
Ebenen, verifiziert an einer KG-Shapefile aus demselben Vorarlberg-Archiv).
Geometrien werden repariert statt verworfen: `cleaned_polygon_parts()`
(`export_at_dkm_geoparquet.py:304-355`) ruft `make_valid()` auf ungültige
Geometrien auf und zerlegt Multipart-Geometrien in einzelne Zeilen
(`multipart_features`/`exploded_extra_parts` in der Summary-CSV) — ohne
Geometrien zu verwerfen.

**Niederösterreich ist eine Neu-Konstruktion, keine Konvertierung — und NÖ
ist das wichtigste Bundesland dieses Projekts.** Seine Katasterbasis hat
deshalb eine andere Qualität als die der übrigen acht Bundesländer. NÖ liegt
nur als DXF-Linienwerk vor; es gibt **keine** `GST_V2`-Parzellenebene für NÖ
im Geoparquet (`export_at_dkm_geoparquet.py:657`, altes Repo: „Niederoesterreich
has no GST_V2 parcel layer in this export“). Statt einer Konvertierung baut
`export_noe_tile()` (`export_at_dkm_geoparquet.py:661-792`) Polygone per
Tile+Halo-Kachelung, `shapely.ops.polygonize` über die DXF-Linien und einer
Mehrheitsabstimmung (`Counter` über `STRtree`-Treffer benachbarter
NS-Symbolpunkte) je Polygon. Der Code selbst führt Buch über die
Unsicherheit dieser Rekonstruktion: von 3.491.407 erzeugten
NÖ-Polygonen sind **684.249 als `ambiguous_polygons`** markiert (mehr als
eine NS-Kategorie unter den Stimmen) und **338.674 als
`unassigned_polygons`** verworfen (keine NS-Stimme traf das Polygon) —
zusammen rund 29 % der NÖ-Polygone mit unsicherer oder fehlender
Klassifikation (Zahlen aus `at_dkm_gst_nfl_epsg31287_summary.csv`, altes
Repo). Polygone unter 4 m² werden verworfen (`--noe-min-area-m2`, Default
`4.0`, `export_at_dkm_geoparquet.py:910`). Diese Unsicherheit betrifft **nur**
Niederösterreich — bei den acht SHP-Bundesländern gibt es weder
Mehrheitsabstimmung noch Ambiguität, dort stammt jede Zeile 1:1 aus einer
amtlichen DBF-Zeile.

Erzeugt wird das Geoparquet mit
`scripts/preprocessing/export_at_dkm_geoparquet.py` (im neuen Repo identisch
zum alten `scripts/main/export_at_dkm_geoparquet.py` — byteidentisch
geprüft). Anders als bei der OSM-Kette gibt es hier **keine externe
Binärabhängigkeit** — kein `osmium` o. Ä., nur Python-Pakete. Wesentliche
CLI-Optionen (per `argparse`):

```
--data-dir            Default: <ROOT>/data/kataster
--output              Default: <ROOT>/output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet
--summary-csv         Default: <ROOT>/output/kataster/at_dkm_gst_nfl_epsg31287_summary.csv
--overview-md         Default: <ROOT>/output/kataster/at_dkm_gst_nfl_epsg31287_overview.md
--symbol-csv          Default: <ROOT>/data/kataster/BEV_DKM_DXF_Symbole_V2.6.csv
--layers              Default: GST_V2,NFL_V2 (Comma-separated SHP layers)
--only-bundesland     Comma-separated Teilmenge der SHP-Bundesländer
--max-inner-zips-per-archive   Smoke-Test-Limit pro Archiv
--skip-shp            SHP-Archive überspringen
--skip-noe-dxf        NÖ-DXF-Polygonisierung überspringen
--noe-dxf-zip         Default: <ROOT>/data/kataster/KAT_DKM_Niederoesterreich_DXF_20230401.zip
--noe-limit-files / --noe-line-layers / --noe-tile-size-m / --noe-tile-halo-m
--noe-precision-m / --noe-min-area-m2      NÖ-DXF-Polygonisierungsparameter
--batch-size          Default: 50000 (Zeilen je Parquet-Batch)
--compression         Default: zstd
--temp-dir            Optionales Temp-Verzeichnis für entpackte innere SHP-ZIPs
--overwrite           Zieldateien überschreiben, falls vorhanden
```

`ROOT` ist `Path(__file__).resolve().parents[2]` — vom neuen Skriptpfad
`scripts/preprocessing/export_at_dkm_geoparquet.py` aus ist das
`abschichtung/` selbst, die Defaults passen also unverändert. Beispielaufruf
aus dem Repo-Root (mit `--overwrite`, falls die Zieldatei schon existiert):

```bash
uv run python scripts/preprocessing/export_at_dkm_geoparquet.py --overwrite
```

Laufzeit: unbekannt, wird beim nächsten Lauf selbst protokolliert (das
Skript loggt Zeiten pro Abschnitt selbst, aber vom letzten tatsächlichen Lauf
ist keine Log-Ausgabe erhalten).

**Der Lesefilter stromabwärts ist eng — der Großteil des Geoparquets ist
Reserve, kein Arbeitsmaterial.** Zwei Stellen lesen das Geoparquet für die
Widmung-v2-Referenzkette, beide mit demselben engen Filter: nur die Spalten
`bundesland`, `ns`, `ns_category`, `geometry` (4 von 17 Feldern im Schema),
nur die Zeilen mit `source_layer` in `NFL_V2`/`NFL_DXF_POLYGONIZED`, und nur
NS-Codes `41/52/66/71` (bzw. deren Schreibvarianten) oder die Kategorien
„Baufläche“/„Garten“.

- `windkraft/calc/kataster_layers.py:411-424`, Funktion
  `load_kataster_symbols()` — **nur im alten Repo** (`windkraft_ö_karten`).
  Diese Datei ist **nicht** ins neue Repo migriert; sie existiert dort
  nicht (verifiziert per Suche unter `master_windkraft/abschichtung/`).
- `windkraft/calc/hig_detection.py:164-170` — identisch in beiden Repos
  vorhanden (alter Repo `windkraft_ö_karten/windkraft/calc/hig_detection.py`,
  neuer Repo `master_windkraft/abschichtung/windkraft/calc/hig_detection.py`;
  ein Diff der beiden Dateien zeigt nur eine Abweichung, Zeile 51: der
  Import von `fft_circle_dilation`/`ns_kind` kommt im neuen Repo aus
  `windkraft.calc.distance_engine` statt aus `windkraft.calc.kataster_layers`
  — die Lesefilter-Logik selbst, Zeilen 164-170, ist unverändert).

`GST_V2` (alle Grundstücke) und die meisten `NFL_V2`-Kategorien (Wald,
Landwirtschaft, Gewässer, Verkehrsfläche, Alpen, Weingarten, Sonstige
Nutzung — siehe die Flächentabelle in
`at_dkm_gst_nfl_epsg31287_overview.md`) werden von keinem Skript der
Referenzkette gelesen. Genau deshalb hat das Vorhalten der vollen 9,1-GB-
Quelle (statt nur des Geoparquets) einen Wert: Wer je einmal mehr als
Baufläche/Garten aus der DKM braucht, muss neu exportieren.

### 4.2 `output/noe/alignment_mindestabstand.json` — reproduzierbar, kein Rohdatum

Kein unersetzliches Artefakt: erzeugt durch
`uv run python scripts/noe/align_pdf_shapefile.py` aus dem NÖ-SekROP-PDF
(§3.2), bricht ohne `--overwrite` bei bereits existierender Zieldatei ab.
Die vier Georeferenzierungs-Eckkoordinaten stehen als Konstante
`GPTS_LATLON_MINDESTABSTAND` in `windkraft/noe/pdf_align.py`, primär direkt
aus dem PDF gelesen, nur beim Fehlen des PDFs als Literal-Fallback. Vier
Skripte importieren diese Konstante statt eigener Kopien
(`align_pdf_shapefile.py`, `align_naturschutz.py`, `align_landschaftsraum.py`,
`combine_all_layers.py`); neun weitere Skripte lesen die erzeugte JSON.

Der Pfad ist `output/noe/…`, nicht `data/…` — ein reproduzierbares
Zwischenprodukt der eigenen Pipeline, kein extern bezogenes Rohdatum.

---

## 5. `config/config.json` — was für die Referenzkette tatsächlich wirkt

`load_config()` (`windkraft/config.py`) macht **genau 8 Pfad-Keys**
relativ zum Config-Verzeichnis absolut — verifiziert im Quellcode:
`data_dir`, `vgd`, `osm_dir`, `wind_pd_150`, `wind_pd_100`, `dgm`, `nsg_zip`,
`output_dir`. Zusätzlich berechnet es `_derived` (PD-Verhältnis 150/130 m,
Slope-Schwelle in %, Turbinendichte).

**Nachtrag (Paket W1.2):** Bis zu diesem Paket waren es 9 Pfad-Keys,
zusätzlich `powerlines_gpkg` (`data/osm_power_lines.gpkg`, siehe §2). Mit
der Datei ist auch der Registereintrag
`pipeline.contract.LEGACY_ENTFAELLT["powerlines_gpkg"]` entfernt worden —
der Codepfad, der ihn nach `cfg["paths"]["powerlines_gpkg"]` kopierte, ist
mit ihm entfernt. `cfg["paths"]` liefert diesen Schlüssel seither nicht
mehr; `abschichtung_common.py:966` liest ihn per `cfg["paths"].get(...,
"")` und bekommt einen leeren Pfad statt eines Zeigers auf die entfernte
Datei. Das ist nur relevant, wenn das OSM-PBF fehlt (siehe §2) — ein Fall,
der außerhalb dieses Pakets liegt und hier nicht angefasst wurde.

**Wirksam für die Widmung-v2-Referenzkette:**
`exclusion.slope_max_deg`, `exclusion.elevation_max`, `wind.pd_min` /
`pd_min_height_m` / `shear_alpha`, `buffers.major_airport_osm_ids`, sowie
`paths.dgm` (definiert Grid/CRS/Transform für **alle** Stufen — ein anderes
DGM ändert die Rasterdefinition der gesamten Pipeline).

**Wirkungslos für v2** (im Code als Konstanten dupliziert, laut Kommentar
in `config/config.json` selbst): `buffers.settlement`,
`buffers.individual_objects` (stattdessen
`SETTLEMENT_BUFFER_BY_BL`/`INDIVIDUAL_BUFFER_BY_BL` in
`windkraft/calc/abschichtung_common.py:58-80`), `raster.crs`,
`raster.cellsize` (Grid kommt aus dem DGM). Eine Änderung dieser Keys hat
auf `output/abschichtung_widmung_v2/*.tif` **keine** Wirkung, bleibt aber
wirksam für die Legacy-Ketten (`python -m windkraft calc`, `viz/pdf_map.py`,
`scripts/main/calc_potential_energiewerkstatt_v2.py`,
`scripts/analysis/analyse_*.py`, `windkraft/placement/*`).

`config/config.json` im neuen Repo ist byteidentisch zum alten
`config.json` (Repo-Root im alten Baum) — geprüft per `diff`.

---

## 6. Was NICHT nach `data/` gehört

| Was | Warum ausschließen |
|---|---|
| BEV-Adressregister-Parquet-Caches (`adressen_31287.parquet`, `bev_gebaeude_31287.parquet`) | Build-Artefakte von `windkraft/calc/bev_register.py`; werden beim ersten Lauf automatisch neu erzeugt. (Zählen in §2 trotzdem zur Adressregister-Gesamtgröße, weil sie bereits vorliegen und einen Lauf ohne `ADRESSE.csv`/`GEBAEUDE.csv` ermöglichen.) |
| Entpackte Naturschutz-Ordner | Der Code entpackt das ZIP zur Laufzeit in ein `tempfile.TemporaryDirectory()` (`abschichtung_common.py:1131-1145`); bereits entpackte Ordner sind ungenutzte Zweitkopien |
| `_problem/`-Unterordner bei den Flächenwidmungsdaten | Laut eigener `README.md` entbehrlich: kaputter, aber inhaltlich identischer Zweitdownload einer bereits vorhandenen Datei. **Verifiziert bei dieser Prüfung:** `data/new_widmungs_data/_problem` existiert im neuen Repo tatsächlich **nicht** (`find`/`ls` liefern keinen Treffer), obwohl `new_widmungs_data/` als Ganzes hardlink-migriert wurde und die Ausnahme dort auf Unterordner-Ebene hätte greifen müssen — die Ausnahme wurde also korrekt umgesetzt. Im alten Repo liegt `data/new_widmungs_data/_problem` weiterhin, **28 MB**. `windkraft/calc/widmung_sources.py` referenziert `_problem` an keiner Stelle (per Grep) — der Ordner ist für die Referenzkette inert, unabhängig davon, ob er migriert wird. |
| `.claude`-Ordner unter `data/` | Werkzeug-/Session-Metadaten, kein Rohdatenbezug. **Nachtrag W1.2:** Ein solcher Ordner (`data/adressen/.claude/`) war tatsächlich vorhanden — vermutlich Nebenwirkung eines Werkzeuglaufs mit Arbeitsverzeichnis unter `data/adressen/` — und ist mit W1.2 entfernt worden (leer, kein Inhalt außer einem leeren `.cc-writes`-Unterordner). |
| Im Code unreferenzierte Dateien (`FLWI_WIDMUNGEN_L/`, `AUT_capacity-factor_IEC*.tif`, `rea_windrichtungen.grib`, `windkraftzonen_shapefile_2024.json`, `zonierung.qlr`) | Per Grep über alle `.py`-Dateien: kommen in keinem Skript der Referenzkette vor (Details und eine Einschränkung zu `FLWI_WIDMUNGEN_L` in §7). `windkraftzonen_shapefile_2024.json` war trotz dieser Einstufung tatsächlich unter `data/` gelandet (Hardlink, Link-Count 2) — siehe §3.1 — und ist mit **Paket W1.2 entfernt** worden, mangels Codeleser. Die übrigen vier genannten Dateien/Ordner fehlen weiterhin unter `data/` (verifiziert per `ls`). |

---

## 7. Was deliberat im alten Repo verblieben ist (nicht migriert)

Diese Dateien liegen unter `windkraft_ö_karten/data/`, wurden aber
**bewusst nicht** nach `master_windkraft/abschichtung/data/` übernommen.
Wer sie sucht, findet sie nur im alten Repo:

| Datei/Ordner | Größe (nachgemessen) | Grund |
|---|---|---|
| `austria-260328-free.shp/` + `.shp.zip` | 3,6 GB + 1,3 GB = **4,9 GB** | Nur PBF-Fallback (§0.2); mit gepflegtem PBF tote Last |
| `abschichtung_cutout.afdesign` + `.pdf` | 342 MB + 85 MB = **427 MB** | Design-/Layout-Datei, kein Pipeline-Input |
| `windatlas_*` (100/130/80 m TIFs, `_extracted/`, `_tifs/`) | 67+69+64+47+93 MB = **340 MB** | Nicht von der Referenzkette gelesen (die nutzt `AUT_power-density_150m.tif`) |
| `rea_windrichtungen.grib` (+ `.idx`) | 79 MB + 8,8 MB = **88 MB** | Nicht von der Referenzkette gelesen |
| `DGM_Rasterweite_50m_20180115.zip` | **118 MB** | Alternatives, ungenutztes DGM |
| `AUT_capacity-factor_IEC{1,2,3}.tif` | 3×~6,9 MB = **~21 MB** | Im Code unreferenziert |
| `AUT_power-density_100m.tif` | **6,8 MB** | GWA-100-m-Variante, verwendet wird die 150-m-Variante |
| `Birdlife_Zonierung_Wind_NOE_2024.zip` | **8,6 MB** | Nicht von der Referenzkette gelesen |
| `steiermark_zonen/` | **18 MB** | Nicht von der Referenzkette gelesen |
| `nö_zonierung/` (außer `TeilC_3_2_...pdf`, das migriert wird) | **~109 MB** (125 MB Ordner minus 16 MB PDF) | Weitere TeilC-PDFs, für v2 nicht relevant |
| `windkraftzonen_shapefile_2024.json` | **588 KB** | Nahe-Duplikat von `zonierung_noe.json` — **nicht** byteidentisch (11 Bytes Unterschied bei gleicher Dateigröße, siehe §3.1), aber redundant genug, um nicht zu migrieren. **Zwischenzeitlich überholt, jetzt wieder zutreffend:** Die Datei war entgegen dieser Einstufung eine Zeit lang zusätzlich unter `data/` im neuen Repo gelandet (per Hardlink, Link-Count 2 — siehe die Migrationsstatus-Notiz in §3.1), ist aber mit **Paket W1.2** dort wieder entfernt worden, mangels Codeleser. Sie liegt damit wieder ausschließlich im alten Repo, wie diese Tabelle es ursprünglich beschrieb. |

---

## 8. Bekannte Lücken

- **Lizenzlage** für die meisten OGD-Quellen (Ktn, NÖ, Sbg, Stmk, Vlbg,
  Bgld, Wien, DKM/BEV-Produkte, DGM, GWA, VGD, NSG, Windzonen Bgld/Ktn sowie
  NÖ abseits der Code-Vermutung) ist **nicht** belegt und muss vor einer
  Veröffentlichung bei den jeweiligen Landes-/Bundesstellen geklärt werden.
  Belegt sind bislang nur OÖ (CC-BY 4.0), Tirol (CC-BY 4.0) und OSM
  (ODbL 1.0).
- **Wien-Flächenwidmung** hat kein Abrufskript im Repo — muss manuell per
  WFS nachgezogen werden (Befehl siehe §3.3).
- **`luca_zonen` (Stmk, Sbg):** keine Quell-URL, weil es keine
  Download-Quelle gibt (§0.1) — nicht reproduzierbar, Genauigkeit unbekannt,
  Lizenz strukturell unklar. Offener Punkt: ob diese beiden Shapefiles
  künftig versioniert werden sollen (Ausnahme von der `.gitignore`-Regel),
  liegt beim Projektinhaber.
- **Exakte „Stand“-Daten** für die meisten Quellen sind nicht durch ein
  offizielles Änderungsdatum belegt, sondern durch das lokale Dateidatum
  approximiert — siehe Kopf-Hinweis zu in-place-Überschreibungen bei
  OGD-Portalen.
- **Alle mit `unbekannt — zu klären` markierten Felder** oben sind offene
  Rechercheposten, keine invertierten Annahmen.

---

## 9. Gesamtgröße

Gemessen (alter Repo, dieser Prüfung): `data/kataster/` allein **9,1 GB**;
alle übrigen migrierten Rohdaten (DGM, OSM-PBF, Adressregister, 9×
Flächenwidmung, Naturschutz, VGD, GWA-PD, Windzonen, NÖ-Zonierungs-PDF)
zusammen **≈ 3,9 GB**; `output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet`
**5,0 GB**; `output/noe/alignment_mindestabstand.json` vernachlässigbar
(4 KB).

**≈ 18 GB unter `data/` + `output/` nach dem Umzug** (≈ 3,9 GB + 9,1 GB +
5,0 GB ≈ 18,0 GB — Arithmetik stimmt mit der Vorgabe überein), **≈ 8,9 GB
ohne die Kataster-Rohdaten** (18,0 GB − 9,1 GB = 8,9 GB — stimmt ebenfalls).
Migration erfolgt per Hardlink (Zielverzeichnis auf demselben Volume wie
`windkraft_ö_karten/`); echter Mehrverbrauch nahe null, solange keine Datei
im neuen Baum modifiziert wird (Hardlinks teilen sich die Inode, ein Schreib-
zugriff auf eine Kopie würde — je nach Dateisystem — die andere mit
verändern oder Copy-on-Write auslösen; beides ist nicht getestet).

**Die Invariante (Stand zum Zeitpunkt der Migration, W0.1):** Jede Datei,
die irgendein Codepfad schreiben kann, ist eine echte Kopie — nie ein
Hardlink. Unabhängig von Größe, Verzeichnis und davon, ob im Code ein Guard
(Overwrite-Schutz) existiert. Quelldaten unter `data/`, die die Kette
ausschließlich liest, blieben davon zu diesem Zeitpunkt unberührt: per
Hardlink mit `windkraft_ö_karten` verbunden war für sie richtig, kostete
keinen Speicher.

**Überholt seit W1.3 (07.09.2026):** Diese Unterscheidung — Schreibziele
als echte Kopie, reine Leseware als Hardlink — gilt nicht mehr. Paket W1.3
hat alle verbliebenen 48 Hardlinks unter `data/` aufgelöst; der Ordner
besteht seither komplett aus echten Kopien, auch dort, wo die Kette nur
liest. `tools/check_hardlink_safety.py` prüft das seither als Invariante
für *jede* Datei unter `data/` (Regel B), nicht mehr nur für eine
deklarierte Teilmenge bekannter Schreibziele. Details: Bericht zu W1.3 in
`docs/rewrite/FORTSCHRITT.md`.

Die Vorgängerformulierung dieser Regel lautete „Eingaben hardlinken,
Ausgaben kopieren" — schwächer, und zwar auf eine Art, die den eigentlichen
Fehler verdeckt hat: sie verlangt eine **Einordnung** (ist diese Datei
Eingabe oder Ausgabe?), und genau diese Einordnung schlug fehl, obwohl sie
korrekt war. Die Adressregister-Parquet-Caches und die betroffenen
`output/`-Dateien wurden zu Recht als „Artefakte, die (auch) gelesen
werden" eingestuft — sie werden tatsächlich als Cache bzw. als
weiterverarbeitetes Zwischenergebnis gelesen. Nur schreibt dieselbe Kette
eben auch in sie hinein. Eine Regel, die bei einer korrekten Einordnung
trotzdem zum falschen Ergebnis führt, ist die falsche Regel. Die neue
Formulierung braucht keine Einordnung mehr, nur eine mechanisch prüfbare
Tatsache: den Link-Count. Ein Schreibvorgang auf eine hardgelinkte Datei
kürzt den geteilten Inode und zerstört dieselbe Datei im Alt-Repo im selben
Moment, ohne Fehlermeldung — das gilt unabhängig davon, wie die Datei
eingeordnet wurde.

**Bekannter Verstoß — behoben.** Bei der Migration wurden mehrere echte
Ketten-Ausgaben per Hardlink statt per Kopie übernommen: die Dateien unter
`output/noe/` (13 Stück, darunter die 7 tatsächlichen Schreibziele
`alignment_mindestabstand.json`, `pdf_750m_{geb,gwr,gruenland_widmung}.geojson`
und `pdf_hig_source_{geb,gwr,gruenland_widmung}.geojson`, sowie 6 weitere
`alignment_*.json`, die zwar aktuell von keinem migrierten Skript
geschrieben werden, aber unter demselben Verzeichnis liegen und derselben
Invariante unterliegen), das Geoparquet unter `output/kataster/`
(`at_dkm_gst_nfl_epsg31287.geoparquet`, ≈ 5,0 GB) sowie die beiden
Adressregister-Caches unter `data/adressen/`
(`adressen_31287.parquet`, `bev_gebaeude_31287.parquet`). Alle 16 Dateien
sind inzwischen echte Kopien: per `cp`/`mv` neu angelegt, Link-Count 1,
eigener Inode, Inhalt byteidentisch zum Alt-Repo geprüft (`cmp`). Das
Alt-Repo ist davon unberührt — sein eigener Link-Count auf dieselben
Dateien ist ebenfalls auf 1 zurückgefallen. `make check-hardlinks`
(`tools/check_hardlink_safety.py`) weist das jetzt mechanisch nach, statt
es einer Einordnung zu überlassen — siehe README.md, Abschnitt
„Hardlink-Sicherheit prüfen".
