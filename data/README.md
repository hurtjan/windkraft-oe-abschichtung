# data/ — Herkunft der Rohdaten

> **Dies ist eine Beschreibung, keine Kopie.** Die Rohdaten selbst liegen
> **nicht** in diesem Repo — `data/` ist per `.gitignore` vollständig
> ausgeschlossen (`/data/*`), nur diese Datei ist als Ausnahme eingecheckt
> (`!/data/README.md`). `output/` ist komplett `.gitignore`d, ohne Ausnahme.
> Ein neues Setup muss jeden Datensatz unten selbst von seiner Quelle
> beziehen bzw. — im gewöhnlichen Fall — per Hardlink aus dem alten Repo
> (`windkraft_ö_karten/`) übernehmen. Diese Datei ist die einzige
> Nachweiskette dafür, mit welchen Daten gerechnet wurde.
>
> **Dieses Dokument ist die Nachfolgeversion von
> `windkraft_ö_karten/source_data_README.md`**, neu geschrieben für die
> Abschichtung-Restrukturierung (`master_windkraft/abschichtung/`). Alle
> Pfade unten sind Zielpfade unter diesem `data/`, nicht die (teils
> historisch gewachsenen, uneinheitlichen) Pfade im alten Repo — diese sind
> als „Quellpfad (altes Repo)“ separat angegeben, weil die Migration per
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
| Dateien | `data/luca_zonen/Stmk.shp` (72 KB, 18 Features), `data/luca_zonen/Sbg.shp` (148 KB, 13 Features) |
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
- **Checkpoints prüfen keinen Rohdaten-Fingerprint.** Für Infrastruktur-,
  Flughafen-, Natur-, Geographie- und Zonierungs-Checkpoints wird **kein**
  `SOURCE_FINGERPRINT`-Tag angelegt (nur Gebäudebänder tragen
  `HIG_SOURCE_FINGERPRINT`). Ein neues OSM-PBF, neue Schutzgebiete, ein neues
  DGM oder geänderte `config.json`-Schwellen werden **ohne
  `--force-layers`** nicht erkannt — die Pipeline meldet `[keep]` und liefert
  wortlos veraltete Bänder.

Hart abgebrochen wird nur bei fehlenden **Zwischenprodukten der eigenen
Pipeline** (Stufe-2-Cover-Layer, Stufe-4-Pflicht-Checkpoints) — nicht bei
fehlenden Rohdaten. Faustregel: nach neuen Rohdaten oder geänderter Config
immer `--force-layers` auf Stufe 3 und 4 verwenden.

---

## 1. Verzeichnisstruktur (Zielpfade unter `data/`)

```
data/
├── DGM_R25.tif                     750 MB  Höhenmodell 25 m — definiert Grid/CRS/Transform
├── austria-260330.osm.pbf          760 MB  Geofabrik-PBF, speist viele Bänder
├── adressregister/                 484 MB  BEV-Adressregister (+ 2 Parquet-Caches)
├── admin_boundaries/
│   └── VGD_Oesterreich_gen_50_20221002/    20 MB  Verwaltungsgrenzen
├── AUT_power-density_150m.tif      6,6 MB  Global Wind Atlas
├── osm_power_lines.gpkg            13 MB   (gelesen, Band seit Clean-38 nicht mehr gespeichert)
├── naturschutzgebiete/
│   └── SG_AT_2024_v_April_Stand_3_April_2024.zip   73 MB
├── kataster/                       9,1 GB  DKM/BEV-Rohdaten, 9 Archive → Geoparquet (erzeugt, §4)
├── widmung/                        ~1,7 GB  Flächenwidmung, 9 Bundesländer (siehe §3.3)
├── zonierung_noe.json              588 KB  amtliche NÖ-Zonierung, 71 Zonen
├── luca_zonen/
│   ├── Stmk.shp                    72 KB   NICHT reproduzierbar, siehe §0.1
│   └── Sbg.shp                     148 KB  NICHT reproduzierbar, siehe §0.1
├── WK_Eignungszonen.zip            268 KB  Burgenland
├── RED_III_Windkraftbeschleunigungszone.zip   28 KB  Kärnten
├── WINDKRAFT_AUSSCHLUSSZONE.zip    4,4 MB
└── nö_zonierung/
    └── TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf   16 MB  (nur Precondition für pdf_750m-Layer)
```

`output/` (komplett `.gitignore`d, keine Ausnahme) enthält die **erzeugten**
Artefakte, insbesondere `output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet`
(5,0 GB) und `output/noe/alignment_mindestabstand.json` — siehe §4.

---

## 2. Rohdaten — Referenz-Grid, OSM, Adressen (Stufe 2–4)

| Datensatz | Zielpfad | Herkunft | Bezugsweg/URL | Stand | Größe | Lizenz | Neu beschaffbar |
|---|---|---|---|---|---|---|---|
| Höhenmodell 25 m | `data/DGM_R25.tif` | BEV / Land Austria | unbekannt — zu klären (manueller Download beim Arbeitsrechner-Stand) | 30.03.2026 | **750 MB** | unbekannt — zu klären | ja, eingeschränkt (Portal/Lizenz zu klären) |
| OSM Österreich (PBF) | `data/austria-260330.osm.pbf` | Geofabrik | https://download.geofabrik.de/europe/austria.html | 30.03.2026 | **760 MB** | ODbL 1.0 | ja |
| Adressregister | `data/adressregister/` | BEV | unbekannt — zu klären (manueller Download BEV-Portal) | Stichtag 01.10.2025 | **484 MB** (ZIP 93 MB + `ADRESSE.csv` 311 MB + 2 Parquet-Caches ~81 MB) | unbekannt — zu klären | ja, eingeschränkt |
| Leistungsdichte 150 m | `data/AUT_power-density_150m.tif` | Global Wind Atlas | https://globalwindatlas.info | 29.03.2026 | **6,6 MB** | unbekannt — zu klären | ja |
| Verwaltungsgrenzen | `data/admin_boundaries/VGD_Oesterreich_gen_50_20221002/` | BEV, generalisiert 1:50.000 | unbekannt — zu klären | 02.10.2022 | **20 MB** | unbekannt — zu klären | ja, eingeschränkt |
| Naturschutzgebiete | `data/naturschutzgebiete/SG_AT_2024_v_April_Stand_3_April_2024.zip` | Umweltbundesamt / DORIS (OGD) | unbekannt — zu klären | 03.04.2024 | **73 MB** | unbekannt — zu klären | ja, eingeschränkt |
| OSM-Stromleitungen | `data/osm_power_lines.gpkg` | abgeleitet aus Geofabrik-OSM | — (Export aus OSM-PBF) | 31.03.2026 | **13 MB** | ODbL 1.0 | ja |

**Wichtiger Hinweis zu `osm_power_lines.gpkg`:** Die Datei wird weiterhin
gelesen (Widmung-v2-Kette, `abschichtung_common.py` ~Zeile 934), das daraus
gebaute Band `power_380_400kv` ist im **Clean-38-Schema aber nicht mehr
enthalten** — Stromleitungen sind seit `build_widmung_v2_layers.py` kein
Ausschlusskriterium mehr. Die Datei bleibt also Teil der Kette, ohne dass
ihr Ergebnis noch ausgegeben wird. (Wörtlich aus dem Kommentar in
`config.json`: „Für v2 wirkungslos; weiterhin aktiv für die OSM-Kette und
Widmung v1.“)

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
| NÖ | `data/zonierung_noe.json` | data.gv.at, LGBl. 47/2024, 71 Zonen | https://www.data.gv.at | unbekannt — zu klären (Dateidatum 30.04.2026) | **588 KB** | im Code als „meist CC-BY“ vermerkt, **nicht verifiziert** → unbekannt — zu klären | ja |
| Stmk, Sbg | `data/luca_zonen/{Stmk,Sbg}.shp` | handdigitalisiert | **keine** — siehe §0.1 | unbekannt — zu klären | 72 KB / 148 KB | strukturell unklar, siehe §0.1 | **nein** |
| Bgld | `data/WK_Eignungszonen.zip` | Land Burgenland | unbekannt — zu klären | `EXPORT_DAT 20260721` | **268 KB** | unbekannt — zu klären | ja, eingeschränkt |
| Ktn | `data/RED_III_Windkraftbeschleunigungszone.zip` | Land Kärnten | unbekannt — zu klären | unbekannt — zu klären | **28 KB** | unbekannt — zu klären | ja, eingeschränkt |
| — | `data/WINDKRAFT_AUSSCHLUSSZONE.zip` | unbekannt — zu klären | unbekannt — zu klären | unbekannt — zu klären | **4,4 MB** | unbekannt — zu klären | unbekannt — zu klären |

**Datenqualitäts-Hinweis (verifiziert bei dieser Prüfung, weicht von der
Vorgabe-Annahme ab):** `data/windkraftzonen_shapefile_2024.json` (im alten
Repo, nicht migriert, siehe §5) wurde bislang als „byte-identisches
Duplikat“ von `zonierung_noe.json` beschrieben. Ein `cmp -l` zeigt: beide
Dateien sind exakt **600.056 Byte** groß, unterscheiden sich aber an
**11 Bytes** — sie sind **nicht** byte-identisch, wohl aber ein Nahe-Duplikat
(gleicher Inhalt, geringfügig abweichend, vermutlich Metadaten/Zeitstempel).
Das ändert nichts an der Entscheidung, `windkraftzonen_shapefile_2024.json`
nicht zu migrieren (§5) — nur die Begründung „byte-identisch“ war ungenau.

### 3.2 NÖ-SekROP, Mindestabstandszonen (Precondition)

| Datensatz | Zielpfad | Herkunft | Bezugsweg/URL | Stand | Größe | Lizenz | Neu beschaffbar |
|---|---|---|---|---|---|---|---|
| Mindestabstandszonen-Karte | `data/nö_zonierung/TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf` | Amt der NÖ Landesregierung | unbekannt — zu klären | 29.03.2026 (Dateidatum; Karten-Stand 02.04.2024) | **16 MB** | unbekannt — zu klären | ja, eingeschränkt |

Nur Precondition — erzeugt die `pdf_750m`-Layer und ist Grundlage für
`output/noe/alignment_mindestabstand.json` (§4.2). Kein direkter Rohdaten-
Input der Rasterbänder selbst.

### 3.3 Flächenwidmung, 9 Bundesländer

**Abweichung von der Vorgabe:** Die Task-Vorgabe nennt „8 Bundesländer“ —
tatsächlich liegen **9** vor, seit Wien am 29.07.2026 hinzukam. Gesamtgröße
der tatsächlich von der Referenzkette gelesenen Dateien: **≈ 1,7 GB**
(nachgemessen; die zuvor kolportierten „~1,76 GB“ treffen ungefähr zu).

| BL | Zielpfad (unter `data/widmung/`) | Quellpfad (altes Repo) | Herkunft | Stand (Dateidatum) | Größe | Lizenz | Neu beschaffbar |
|---|---|---|---|---|---|---|---|
| Bgld | `bgld/WIDMUNGSFLAECHEN.zip` | `data/flächenwidmungen/WIDMUNGSFLAECHEN.zip` | Land Burgenland (OGD) | 22.06. | **48 MB** | unbekannt — zu klären | ja |
| Ktn | `ktn/flawi_ktn_gpkg.zip` | `data/new_widmungs_data/kaernten/flawi_ktn_gpkg.zip` | Land Kärnten, KAGIS (OGD) | 12.07. | **142 MB** | unbekannt — zu klären | ja |
| NÖ | `noe/RRU_WI_HUELLE.gpkg` | `data/new_widmungs_data/niederoesterreich/RRU_WI_HUELLE.gpkg` | Amt der NÖ Landesregierung, NÖ Atlas (OGD) | 10.07. | **110 MB** | unbekannt — zu klären | ja |
| OÖ | `ooe/FLWI_WIDMUNGEN_F.zip` | `data/new_widmungs_data/oberoesterreich/FLWI_WIDMUNGEN_F.zip` | Land Oberösterreich, DORIS | 10.07. | **138 MB** | **CC-BY 4.0** | ja |
| Sbg | `sbg/Flaechenwidmung_Shapefile.zip` | `data/new_widmungs_data/salzburg/Flaechenwidmung_Shapefile.zip` | Land Salzburg, SAGIS (OGD) | 12.07. | **30 MB** | unbekannt — zu klären | ja |
| Stmk | `stmk/Bauland.zip` **+** `stmk/Flaewi.shp.zip` | `data/new_widmungs_data/steiermark/Bauland.zip` + `data/flächenwidmungen/Flaewi.shp.zip` | Land Steiermark (OGD) | 10.07. / 22.06. | **42 MB + 916 MB** | unbekannt — zu klären | ja |
| Tirol | `tirol/FLW_Flaechenwidmung_*.gpkg` | `data/new_widmungs_data/tirol/FLW_Flaechenwidmung_270349538825189369.gpkg` | Land Tirol, tiris | 12.07. | **106 MB** | **CC-BY 4.0** | ja |
| Vbg | `vlbg/fwp_flaeche.gpkg` | `data/new_widmungs_data/vorarlberg/fwp_flaeche.gpkg` | Land Vorarlberg, VoGIS (OGD) | 12.07. | **144 MB** | unbekannt — zu klären | ja |
| Wien | `wien/genflwidmung_wien.geojson` | `data/new_widmungs_data/wien/genflwidmung_wien.geojson` | Stadt Wien, WFS `ogdwien:GENFLWIDMUNGOGD` | 29.07. | **41 MB** | unbekannt — zu klären | ja (WFS, siehe unten) |

Wien-Bezugsweg (kein Abrufskript im Repo, manuell nachzuziehen):

```bash
curl "https://data.wien.gv.at/daten/geo?service=WFS&request=GetFeature&version=1.1.0&typeName=ogdwien:GENFLWIDMUNGOGD&srsName=EPSG:4326&outputFormat=json" \
  -o data/widmung/wien/genflwidmung_wien.geojson
```

**Zwei-Ordner-Falle im alten Repo (für die Migration wichtig):** Im alten
Repo liegen dieselben Daten auf **zwei** Verzeichnisse verteilt
(`data/new_widmungs_data/` für Ktn/NÖ/OÖ/Sbg/Stmk-Bauland/Tirol/Vbg/Wien,
`data/flächenwidmungen/` für Bgld und die **vollständige** Steiermark-Quelle
`Flaewi.shp.zip`). Wer nur eines der beiden Verzeichnisse kopiert, verliert
entweder Burgenland komplett oder die Steiermark-Grünland-/Freizeit-Flächen.
Die Zielstruktur oben (`data/widmung/<bl>/`) soll diese Falle beim Umzug
auflösen — sie existiert im alten Repo so **nicht**, ist ein Vorschlag für
den neuen Baum.

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

Herkunft: BEV-Katalog, manueller Download. Lizenz: unbekannt — zu klären.
Neu beschaffbar: ja, eingeschränkt (Portal/Lizenz zu klären).

Erzeugt wird das Geoparquet mit
`scripts/preprocessing/export_at_dkm_geoparquet.py` (im neuen Repo identisch
zum alten `scripts/main/export_at_dkm_geoparquet.py` — byteidentisch
geprüft). Wesentliche CLI-Optionen (per `argparse`):

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
aus dem Repo-Root:

```bash
uv run python scripts/preprocessing/export_at_dkm_geoparquet.py --overwrite
```

Niederösterreich liegt nur als DXF vor und wird über
`create_noe_dkm_polygon_fill_map.py`-Hilfsfunktionen (Tile+Halo-
Polygonisierung, NS-Symbole) zu klassifizierten NFL-ähnlichen Polygonen
verarbeitet — es entstehen dabei **keine** `GST_V2`-Parzellen für NÖ.

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

`load_config()` (`windkraft/config.py`) macht **genau 9 Pfad-Keys**
relativ zum Config-Verzeichnis absolut — verifiziert im Quellcode:
`data_dir`, `vgd`, `osm_dir`, `wind_pd_150`, `wind_pd_100`, `dgm`, `nsg_zip`,
`powerlines_gpkg`, `output_dir`. Zusätzlich berechnet es `_derived`
(PD-Verhältnis 150/130 m, Slope-Schwelle in %, Turbinendichte).

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
| `_problem/`-Unterordner bei den Flächenwidmungsdaten | Laut eigener `README.md` entbehrlich: kaputter, aber inhaltlich identischer Zweitdownload einer bereits vorhandenen Datei |
| `.claude`-Ordner unter `data/` | Werkzeug-/Session-Metadaten, kein Rohdatenbezug |
| Im Code unreferenzierte Dateien (`FLWI_WIDMUNGEN_L/`, `AUT_capacity-factor_IEC*.tif`, `rea_windrichtungen.grib`, `windkraftzonen_shapefile_2024.json`, `zonierung.qlr`) | Per Grep über alle `.py`-Dateien: kommen in keinem Skript der Referenzkette vor (Details und eine Einschränkung zu `FLWI_WIDMUNGEN_L` in §7) |

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
| `windkraftzonen_shapefile_2024.json` | **588 KB** | Nahe-Duplikat von `zonierung_noe.json` — **nicht** byteidentisch (11 Bytes Unterschied bei gleicher Dateigröße, siehe §3.1), aber redundant genug, um nicht zu migrieren |

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
