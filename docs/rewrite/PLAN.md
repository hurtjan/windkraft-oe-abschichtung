# Plan: Umbau der Abschichtungskette

Diese Datei ist in sich geschlossen — wer nur sie liest, braucht keine
andere Quelle im Repo, um den Plan zu verstehen. Maschinenlesbare Details
und interaktive Ansichten sind am Ende verlinkt.

**Der Plan sagt, was zu tun ist. Was davon getan ist, steht in
[`FORTSCHRITT.md`](FORTSCHRITT.md)** — Status je Paket, Abnahmen,
gemessene Laufzeiten, offene Punkte. Belege unter `nachweise/`.

## 1. Stand

**Welle 0 vollständig, der Aufräumteil der Welle 1 ebenfalls.** Neun von
30 Paketen sind abgeschlossen und zusammengeführt: W0.1, W0.2, W0.3, W1.7,
W1.1, W1.5, W1.8, W1.9, W1.6. Alle bitgleich zu `run1`, 130 Tests grün.

**Nächstes Paket: W1.2** — das Datenfenster (§12.2), danach W1.3 und W1.4.
Was davon getan ist, steht in [`FORTSCHRITT.md`](FORTSCHRITT.md); die im
Betrieb korrigierten Regeln in §13.

Zweig `docs/audit-und-plan`, kein Remote. **`data/` ist gitignoriert** —
dort ersetzt ein Inventar aus Größe, Inode und Prüfsumme das fehlende Netz
(§11.3).

## 2. Ausgangslage

Kernbefunde des Audits, in Zahlen:

| Befund | Zahl |
|---|---|
| Knoten im Datenflussgraphen | 220 |
| Kanten im Datenflussgraphen | 372 |
| Zwischenergebnisse ohne Erzeuger | 4 |
| Erzeugte und nie gelesene Artefakte | 29 |
| Unerreichbare Skripte | 12 (davon 8 Tests ohne `make test`) |
| Am Code belegte tote Pfade | 13 |
| Dateien in `data/` hardgelinkt | 52 von 56 |

## 3. Zielbild

### Drei Bereichsregeln

- **`data/`** ist unveränderlich und extern bezogen — read-only, nie von
  einem Skript geschrieben.
- **`build/`** ist jederzeit löschbar — Zwischenstand, gitignored.
- **`out/`** enthält genau vier Produkte — kein fünftes.

`rm -rf build && make all` ist der Beweislauf: er zeigt, dass die Kette
allein aus `data/` heraus die vier Endprodukte reproduziert.

### Die vier Endprodukte

| Pfad | Zweck |
|---|---|
| `out/abschichtung.tif` | Das eigentliche Ergebnis der Abschichtung: 38 Bänder, uint8, EPSG:31287, 25 m, 24001 × 14001. |
| `out/abschichtung.bands.json` | Vertrag: Bandnummer, Name, Rolle, Pufferdistanz, Quelle je Band — vom Schreiber selbst erzeugt. Die Datei, die das Dashboard-Repo konsumiert. |
| `out/dashboard/` | Prüfung/Neubau: liest ausschließlich das Manifest, nie eine fest verdrahtete Bandliste. Genau daran ist der heutige Dashboard-Builder gescheitert. |
| `out/gemeinden.geojson` | Prüfung/neu: Gemeindegrenzen im Rasterbezug, um die Deckung visuell zu prüfen — der heute fehlende Test gegen Georeferenzierungsfehler. |

### Die fünf Stufen der Eskalation

Jede Stufe darf nur aus der vorigen lesen — nie zwei überspringen, nie
zurück. Domänen mit aufwendiger Aufbereitung bekommen zwei Prep-Stufen
statt einer.

1. **Roh** (`data/`) — read-only, extern bezogen oder händisch, nie von
   einem Skript geschrieben. 10 Themengruppen, ~12 GB.
   `tools/check_raw_only.py` bricht den Build ab, wenn hier etwas
   Abgeleitetes liegt.
2. **Prep** (`build/prep/<domäne>/`) — ein Skript je Domäne: entpacken,
   reprojizieren, filtern, in ein einheitliches Format. Ergebnis immer
   GeoParquet oder GeoJSON in EPSG:31287. Teuer und selten: läuft nicht bei
   jedem Kettenlauf mit.
3. **Prep II** (`build/prep/<domäne>/b_…`) — nur wo nötig: OSM, Kataster,
   NÖ-PDF, Steiermark-PDF. Trennt teure Extraktion von billiger Ableitung,
   damit ein Parameterwechsel nicht 5 GB neu rechnet.
4. **Layer** (`build/layers/*.tif`) — Rasterisierung auf das 25-m-Gitter,
   ein Checkpoint je Quellklasse. Wiederaufsetzbar: vorhandene Layer werden
   übersprungen. Harte Vorbedingungen statt stiller Fallbacks.
5. **Finalize** (`out/`) — Komposition: Puffer, Aggregate, Varianten,
   Unschärfe, Referenzbänder. Schreibt TIF und Manifest in einem Zug.
   Danach `verify`: Dashboard und Gemeindegrenzen.

### Verzeichnisbaum

```
data/                    read-only, extern bezogen, nie geschrieben
  <10 Themengruppen>/     ~12 GB
build/                   jederzeit löschbar, gitignored
  prep/<domäne>/          Ausgabe der Prep-Stufe(n)
  layers/*.tif            Checkpoints je Quellklasse
out/                     genau vier Produkte
  abschichtung.tif
  abschichtung.bands.json
  dashboard/
  gemeinden.geojson
pipeline/                neuer Code: contract, prep/, layers/, finalize.py, validate.py, verify/
tools/                   Wächter: check_raw_only.py, check_hardlink_safety.py
tests/
```

## 4. Domänen

Jede Zeile ist ein Zuständigkeitsbereich mit genau einem Prep-Skript. Die
Bandnummern sind die tatsächlichen Deskriptoren des heutigen 38-Band-Rasters.

| Domäne | Rohquelle | Größe | Prep | Erzeugte Layer | Bänder | Anmerkung |
|---|---|---|---|---|---|---|
| Verwaltungsgrenzen | VGD 50 generalisiert (BEV) | — | admin | bundesland_masken; gemeinden | alle indirekt · `out/gemeinden.geojson` | Basis für die bundeslandweisen Puffer und für die neue Deckungsprüfung. |
| Kataster | 8 × DKM-SHP-ZIP + NÖ-DXF + Symbol-CSV | 9,1 GB | kataster/a_noe_polygonize → kataster/b_export_parquet | nonresidential_hulls_source; general_buildings_source; hig_hulls_source; bewohnt_einzellage_source | 8–13 | NÖ liefert nur Linienwerk; die Polygone werden per Kachelung und Mehrheitsvotum rekonstruiert. Teuerste Stufe der Kette. |
| Adressregister | BEV Adresse, Stichtagsdaten | 484 MB | adressen | hig_hulls_source | 12–13 | Speist die Streusiedlungserkennung: ≥5 adressierte Objekte in 200-m-Verkettung ergeben eine Hülle. |
| Flächenwidmung | 9 Bundesland-Quellen, GPKG und SHP | 1,6 GB | widmung | official_settlement_source; official_hig_source; ferienhaus_tourismus_source | 1–5 | Niederösterreich ist das einzige Land mit 1200 m Siedlungspuffer statt 1000 m. |
| OSM | austria.osm.pbf | 760 MB | osm/a_extract → osm/b_layers | buildings; roads; railways; powerlines; transport; aerialways; military; nature; windpower; water | 14–22, 26, 38 | **Zehn** Objektgruppen, nicht acht: die Namen sind die Schlüssel aus `OSM_PBF_FILTERS`, nicht Bandnamen. `buildings` ist mit 8,5 Mio Objekten die größte und fehlte hier ganz. `powerlines` wird extrahiert, seine Maske `power_380_400kv` steht aber seit dem Clean-Schema nicht mehr in `INFRA_LAYER_NAMES` und wird nie persistiert (Punkt 27). Drei weitere Schlüssel — `landuse`, `places`, `addresses` — sind deklariert und tot (Punkt 26). Zwei Stufen, weil die osmium-Extraktion teuer ist (**gemessen 286 s**) und die Layer-Ableitung oft wiederholt wird. |
| Gelände & Wind | DGM_R25, Leistungsdichte 150 m | 757 MB | kein Prep | geography_slope; geography_elevation; geography_wind | 23–25 | Bereits Raster im Zielgitter — kein Prep nötig, direkt in die Layer-Stufe. |
| Naturschutz | Schutzgebiete Österreich 2024 | 73 MB | natur | nature_protection_areas | 21 | Amtliche Quelle; Band 22 stammt aus OSM und dient dem Abgleich. |
| Windzonen | luca_zonen, Eignungszonen, RED III, zonierung_noe | 4,9 MB | zonen | — | 37 | Referenzband, geht nicht in die Abschichtung ein. Die steirischen Positivzonen bleiben erhalten (`luca_zonen/Stmk.shp`); die SAPRO-2026-Ausschlusszonen entfallen laut Entscheidung. Die beiden Quellen, die heute bei Fehlen still ausfallen, werden zur harten Vorbedingung. |
| NÖ SekROP-PDF | Sektorales Raumordnungsprogramm, PDF-Karte | 16,6 MB | noe/a_align → noe/b_vectorize | noe_pdf_750m_zones | 6–7 | Trägt in Niederösterreich allein den 750-m-Abstand; die Kataster-Hüllen sind dort ausmaskiert. |

Bandfamilien: 1–2 Widmung Wohn/Misch · 3–7 Häuser im Grünen · 8–13 Gebäude
aus dem Kataster · 14–17 Verkehr, je 150 m · 18–20 Militär und Luftfahrt ·
21–22 Naturschutz · 23–26 Gelände, Wind, Wasser · 27–30 Aggregate · 31–36
Verfügbarkeit und Unschärfe · 37–38 Referenz.

## 5. Getroffene Entscheidungen

Vier Punkte hingen an fachlichem Wissen, nicht am Code. Alle vier sind
entschieden.

| Entscheidung | Folge |
|---|---|
| **(a) Ausschlusszonen — beides entfällt.** `WINDKRAFT_AUSSCHLUSSZONE.zip` wird gelöscht, die Steiermark-SAPRO-Domäne wird gar nicht erst angelegt: kein PDF aus dem Vorgängerprojekt, `Stmk2026Aus` verschwindet aus `wind_zones.py`. **Gemessen in W1.7: Band 37 ändert sich überhaupt nicht.** Die Annahme, es verliere die SAPRO-2026-Ausschlusszonen, war falsch — `load_wind_exclusion_zones()` wird im ganzen Repo nirgends aufgerufen, und ein Band `official_wind_exclusion_zoning` existiert im 38-Band-Schema nicht. Die Ausschlusszonen erreichten nie ein Band. Die Entfernung bleibt richtig (Code, der nichts tut, gehört weg), ist aber folgenlos. Nebeneffekt zum Guten: die einzige nicht bitgleich reproduzierbare Farbextraktion fällt aus der Kette, PyMuPDF wird nur noch für Niederösterreich gebraucht. |
| **(b) Hardlinks — echte Kopien.** Die 52 hardgelinkten Dateien werden zu eigenständigen Kopien, Kosten rund 13 GB. | `data/` ist danach unabhängig, das Vorgängerprojekt lässt sich löschen, ohne dass hier etwas verschwindet. `tools/check_hardlink_safety.py` wird von „Schreibziele müssen Link-Count 1 haben" auf „*alle* Dateien müssen Link-Count 1 haben" verschärft — aus der Warnung wird eine Invariante. |
| **(c) Prep — nicht im Standardlauf.** `make` baut nur Layer und Finalize. `make prep` ist ein bewusster, separater Aufruf. `make all` hängt beides zusammen. | Der Alltagslauf rechnet nicht versehentlich fünf Stunden Kataster neu, aber `make all` bleibt der Beweis, dass die Kette aus Rohdaten läuft. Jede Prep-Stufe schreibt einen Fingerabdruck ihrer Eingänge — passt er nicht mehr, bricht der Layer-Bau ab, statt mit veralteten Zwischenständen weiterzurechnen. |
| **(d) Adressregister — Graph korrigiert.** Die Lücke wird an der Ursache behoben: wo ein Bibliotheksmodul im Auftrag eines Skripts liest oder schreibt, bekommt der Graph eine abgeleitete Kante vom Modul zum Skript. | Der Pfad vom BEV-Adressregister zu den Streusiedlungs-Hüllen ist wieder durchgängig, und dieselbe Korrektur schließt zugleich die Pfade der Referenzbänder. Abgeleitete Kanten sind als solche markiert und bleiben von den belegten unterscheidbar. |

## 6. Abnahmebedingung

Ersetzt die frühere Fassung „Band 1–38 bitgleich, einzige Ausnahme Band 37
in der Steiermark". Entscheidung des Nutzers: bitgleich bleibt das Ziel,
ist aber kein Abbruchkriterium. Kleine Abweichungen werden dokumentiert und
im Nachhinein bewertet.

### Vergleichsbasis

Verglichen wird gegen **`osm_wka_distance_zones_widmung_v2_run1.tif`** —
das letzte Ergebnis *dieses* Repos — und **nicht** gegen das aus dem
Vorgängerprojekt kopierte Referenz-TIF.

Begründung: zwischen run1 und der Referenz bestehen bereits dokumentierte
Abweichungen (u. a. −66 px auf `general_buildings_buffer`, +5 px auf
Band 32). Gegen die Referenz zu prüfen würde diese Alt-Abweichungen mit den
neuen vermischen. Gegen run1 misst man ausschließlich das, was der Umbau
verursacht hat.

### Drei Kennzahlen je Band

1. **Abweichende Pixel**, absolut.
2. **Anteil** an den gesetzten Pixeln des Bandes.
3. **Größte zusammenhängende Abweichungsfläche** in Hektar.

Die dritte Kennzahl ist die aussagekräftigste: 500 verstreute Einzelpixel
sind Rasterisierungsrauschen, 500 Pixel an einer Stelle sind ein verlorener
oder verschobener Layer.

### Ampel

| Stufe | Bänder 1–26 (Quellen und Puffer) | Bänder 27–36 (Aggregate und Verfügbarkeit) |
|---|---|---|
| **Bitgleich** | keine Abweichung | keine Abweichung |
| **Grün** — weiter, nur Protokollzeile | ≤ 0,01 % der gesetzten Pixel **und** größte Fläche ≤ 1 ha | ≤ 1 km² von 83.921 km² |
| **Gelb** — weiter, Eintrag mit Ursachenvermerk | ≤ 0,1 % **und** größte Fläche ≤ 25 ha | ≤ 10 km² |
| **Rot** — anhalten und nachfragen | darüber | darüber |

Die Bänder 27–36 bekommen ihr Budget in km², weil das die Einheit des
Endergebnisses ist. Dort summiert sich alles Vorgelagerte; die Fläche
zählt, nicht die Pixelzahl.

Die Bänder 37 und 38 sind Referenzbänder und gehen nicht in die
Abschichtung ein.

Für Band 37 war eine Ausnahme vorgesehen: der Wegfall der steirischen
SAPRO-2026-Ausschlusszonen galt als beschlossene inhaltliche Änderung.
**W1.7 hat gemessen, dass es diese Änderung nicht gibt** — die
Ausschlusszonen erreichten nie ein Band. Die Ausnahme entfällt ersatzlos:
**alle 38 Bänder müssen bitgleich zu `run1` sein**, ohne Sonderfall.

### Ablauf je Paket

1. Zuerst **bitgleich anstreben**.
2. Bleibt nach *einem* gezielten Korrekturversuch eine Abweichung im
   grünen oder gelben Bereich: protokollieren und weiterarbeiten.
3. **Rot hält an.** Dann Rückfrage, keine eigenmächtige Fortsetzung.

### Warum nach jedem Paket

Nur so ist jede Abweichung genau **einem** Paket zuzuordnen. Wird erst am
Ende verglichen, gibt es für jede Differenz dreißig Kandidaten und die
Ursache ist nicht mehr feststellbar — auch nicht nachträglich durch den
Nutzer.

Praktisch: die Wellen 1 bis 3 werden gegen die vorhandenen
Checkpoint-Layer geprüft, indem nur die Finalisierung neu läuft. Das
dauert Minuten. Der vollständige Lauf aus Rohdaten steht einmal in
Welle 5.

### Abweichungsregister

`pipeline/validate.py` schreibt selbst, maschinell, nach
`docs/rewrite/abweichungen.tsv`. Eine Zeile je (Paket, Band) mit
Abweichung, tabgetrennt, grep-tauglich:

    paket · band_nr · band_name · pixel_abs · anteil_prozent · groesste_flaeche_ha ·
    schwerpunkt_bundesland · ampel · ursache

`ursache` wird von der Person eingetragen, die das Paket abschließt — eine
Zeile, kein Fließtext. Alle übrigen Spalten erzeugt das Werkzeug.

Aus dieser Datei entscheidet der Nutzer im Nachhinein, welche Abweichungen
akzeptiert werden.

## 7. Wellen und Pakete

Zwischen den Wellen wird synchronisiert, innerhalb einer Welle nicht.

| Welle | Thema | Pakete | Parallel? |
|---|---|---|---|
| 0 | Schnittstellen | 3 | nein — nacheinander |
| 1 | Breite Arbeit | 18 | ja — gleichzeitig |
| 2 | Layer | 3 | ja — gleichzeitig |
| 3 | Finalisierung | 2 | nein — nacheinander |
| 4 | Prüfung | 4 | Vorfeld zuerst, dann drei gleichzeitig |
| 5 | Beweis | 1 | nein — nacheinander |

„Besitzt" heißt: nur dieses Paket darf diese Pfade anfassen. Zwei Pakete
derselben Welle teilen sich niemals eine Datei.

| Paket | Welle | Gruppe | Titel | Besitzt | Braucht | Abnahme |
|---|---|---|---|---|---|---|
| W0.1 | 0 | Daten | Rohdaten nach Thema sortieren | `data/**` (Verschiebungen); die zwölf Dateien mit funktionalem `data/`-Pfad und die drei mit nur dokumentarischem (§11); `config.json` (nur die Werte im `paths`-Block) | — | Zweistufig: (1) jeder funktionale Pfad löst auf eine existierende Datei auf; (2) Finalisierung aus vorhandenen Layern liefert bitgleiches TIF. |
| W0.2 | 0 | Daten | Pfadvertrag anlegen | `pipeline/contract.py` (neu); `config.json` | W0.1 | Jeder Rohpfad, jede Prep-Ausgabe, jeder Layername und jeder Produktpfad ist genau einmal deklariert und importierbar. |
| W0.3 | 0 | Daten | Verzeichnisgerüst und Make-Ziele | `build/` `out/` `pipeline/` (neu); `.gitignore`; `Makefile` | W0.2 | `make` · `make prep` · `make all` · `make test` existieren; `make` läuft die heutige Kette unverändert. |
| W1.1 | 1 | Aufräumen | Adress-Cache-Weiche entfernen | `windkraft/calc/bev_register.py` | W0.3 | `cache_dir` wirkt tatsächlich; Cache landet unter `build/`, nicht in `data/`. |
| W1.2 | 1 | Aufräumen | Tote Daten löschen, Provenienz retten | löschen: `data/osm_power_lines.gpkg`; `data/windkraftzonen_shapefile_2024.json`; `data/**/.DS_Store`; `data/**/.claude/`; `data/WINDKRAFT_AUSSCHLUSSZONE.zip` · verschieben: `data/README.md` → `docs/rohdaten.md`; `.gitignore` | W0.3 | Fünf Pfade weg, Provenienz erhalten; TIF unverändert (keiner erreichte ein Band). |
| W1.3 | 1 | Daten | Hardlinks auflösen | `data/**` (nur Inodes, kein Inhalt) | W0.3 | `find data -type f -links +1` liefert nichts; Prüfsummen vorher/nachher identisch; ~13 GB mehr belegt. |
| W1.4 | 1 | Aufräumen | Wächter für Rohdaten | `tools/check_raw_only.py` (neu); `tools/check_hardlink_safety.py` | W0.3, **W1.1**, **W1.2** | Bricht ab, wenn in `data/` etwas Abgeleitetes liegt oder eine Datei Link-Count > 1 hat. |
| W1.5 | 1 | Aufräumen | Tote Skripte löschen | `scripts/webmap/build_layer_viewer.py`; `scripts/analysis/build_v2_dashboard_data.py`; `scripts/noe/derive_pdf_hig_sources.py` | W0.3 | Kein Verweis mehr im Repo; Kette läuft unverändert. |
| W1.6 | 1 | Aufräumen | NÖ-PDF-HiG-Sackgasse entfernen | `scripts/widmung_v2/02_build_hig_sources.py`; `windkraft/calc/hig_source_masks.py` | W0.3 | Checkpoint und harte Vorbedingung sind weg; TIF bitgleich — der Layer erreichte nachweislich kein Band. |
| W1.7 | 1 | Aufräumen | Ausschlusszonen entfernen | `windkraft/calc/wind_zones.py` | W0.1 | `Stmk2026Aus` und die AUSSCHLUSSZONE-Registrierung sind weg. Einzige zulässige Bandänderung: Band 37 in der Steiermark. |
| W1.8 | 1 | Aufräumen | Paketmetadaten bereinigen | `pyproject.toml` | W0.3 | Toter Entry-Point weg; PyMuPDF harte Abhängigkeit; Paket installierbar, sodass sys.path-Präambeln entfallen können. |
| W1.9 | 1 | Aufräumen | Doku-Widersprüche korrigieren | `README.md` | W0.3 | Status stimmt; die Behauptung, die Kataster-Kette laufe nur im Altrepo, ist entfernt. |
| W1.P1 | 1 | Prep | Prep: Verwaltungsgrenzen | `pipeline/prep/admin.py` | W0.2 | `build/prep/admin/` enthält Gemeinden und Bundesländer in EPSG:31287; Fingerabdruck der Eingänge geschrieben. |
| W1.P2 | 1 | Prep | Prep: Kataster | `pipeline/prep/kataster/`; `scripts/preprocessing/*` (Umzug) | W0.2 | Geoparquet aus Rohdaten; Vorabprüfung mit einem Bundesland, dann voller Lauf. Feldschema identisch zum bestehenden. |
| W1.P3 | 1 | Prep | Prep: Adressregister | `pipeline/prep/adressen.py` | W0.2, W1.1 | Parquets unter `build/prep/adressen/`; Zeilenzahl identisch zum bisherigen Cache. |
| W1.P4 | 1 | Prep | Prep: Flächenwidmung | `pipeline/prep/widmung.py` | W0.2 | Drei Bündel als GeoPackage; Featurezahl je Bundesland identisch zum heutigen Zwischenstand. |
| W1.P5 | 1 | Prep | Prep: OSM, zwei Stufen | `pipeline/prep/osm/` | W0.2 | Extraktion und Layerableitung getrennt; osmium als harte Vorbedingung statt stillem Fallback. |
| W1.P6 | 1 | Prep | Prep: Gelände und Wind | `pipeline/prep/terrain.py` | W0.2 | Nur Durchreichen und Gitterprüfung — kein Resampling. Bricht ab, wenn Gitter oder CRS abweichen. |
| W1.P7 | 1 | Prep | Prep: Naturschutz | `pipeline/prep/natur.py` | W0.2 | Schutzgebiete aus dem ZIP entpackt und reprojiziert; Featurezahl identisch. |
| W1.P8 | 1 | Prep | Prep: Windzonen | `pipeline/prep/zonen.py` | W0.2, W1.7 | Alle verbleibenden Zonenquellen als harte Vorbedingung — kein stiller Ausfall mehr bei fehlender Datei. |
| W1.P9 | 1 | Prep | Prep: NÖ-SekROP-PDF, zwei Stufen | `pipeline/prep/noe/`; `scripts/noe/*` (Umzug) | W0.2 | Alignment und Vektorisierung getrennt; erzeugte GeoJSON deckungsgleich mit den bestehenden. |
| W2.P0 | 2 | Layer | Vorfeld der Layer-Welle | `pipeline/layers/__init__.py`; `make/layers/README.md`; `Makefile` (nur `-include` und `worktree`) | Welle 1 | `make -n` für jedes bestehende Ziel byte-identisch; ein Wegwerf-Worktree sieht `build/prep/` und schreibt nicht hinein. |
| W2.1 | 2 | Layer | Layer: Widmung und Häuser im Grünen | `pipeline/layers/hig.py` | W2.P0 | Bitgleich; die NÖ-Ausmaskierung bleibt unverändert erhalten. **W2.2 ist hier aufgegangen** — Begründung in §13.8. |
| W2.3 | 2 | Layer | Layer: OSM und Infrastruktur | `pipeline/layers/osm.py` | W2.P0 | Bitgleich; Wiederaufsetzen überspringt vorhandene Layer nachweislich korrekt. |
| W2.4 | 2 | Layer | Layer: Natur, Gelände, Zonen und Puffer | `pipeline/layers/geo.py` | W2.P0 | Bitgleich für **alle 17** Checkpoints aus `04_create_distance_zones.py`; die Geometrietyp-Empfindlichkeit gegen den GPKG-Promotionseffekt geprüft und beantwortet. |
| W3.1 | 3 | Finalisierung | Finalisierung und Manifest-Vertrag | `pipeline/finalize.py`; `windkraft/calc/band_manifest.py` | Welle 2 | 38 Bänder, Manifest mit Nummer, Name, Rolle, Puffer und Quelle je Band; Schema versioniert. **Nicht mehr bitgleich zu `run1`:** Abweichungen sind **ausschließlich** in den Bändern zulässig, die aus `geography_water_bodies` gespeist werden (§13.9) — welche das sind, ist Teil des Nachweises. Jede andere ist ein Fehler. |
| W3.2 | 3 | Finalisierung | Validierung | `pipeline/validate.py`; `docs/rewrite/abweichungen.tsv`; `make/validate/*`; `Makefile` (nur die beiden `-include`-Zeilen für `finalize` und `validate`) | W3.1 | Prüft das TIF gegen run1 nach der Ampel aus Abschnitt 6 und schreibt `abweichungen.tsv`. **Das Werkzeug bewertet, es entscheidet nicht:** Rot hält an und wird gemeldet (§6, Punkt 33). Die neun Bänder aus §13.9 müssen im Register stehen, jedes weitere ist ein Fehler. |
| W4.P0 | 4 | Prüfung | Vorfeld der Prüfwelle | `pipeline/verify/__init__.py`; `make/verify/README.md`; **`Makefile` — als einziges Paket der Welle 4** (`-include make/verify/*.mk`, das `test`-Ziel für W4.3, und `build/layers/` samt fertigem TIF im `worktree`-Ziel) | Welle 3 | `make -n` für jedes bestehende Ziel byte-identisch; ein Wegwerf-Worktree sieht `build/layers/` **und** ein finalisiertes TIF, ohne beides neu zu rechnen, und schreibt in keines von beiden. Nach Regel 9 (§13.10). |
| W4.1 | 4 | Prüfung | Dashboard neu | `pipeline/verify/dashboard.py`; `out/dashboard/` | W4.P0 | Liest ausschließlich das Manifest; keine Bandnamen im Code. Läuft gegen ein Manifest mit geänderter Bandzahl ohne Anpassung. |
| W4.2 | 4 | Prüfung | Gemeindegrenzen-Export | `pipeline/verify/gemeinden.py`; `out/gemeinden.geojson` | W4.P0, W1.P1 | Grenzen im Rasterbezug; Deckungsabweichung gegen das TIF ausgewiesen und unter Schwellwert. |
| W4.3 | 4 | Prüfung | Tests verdrahten | `tests/**` — **nicht mehr `Makefile`**, das `test`-Ziel zieht W4.P0 vor | W4.P0 | `make test` läuft die acht vorhandenen Tests plus die neuen Vertragstests; grün. |
| W5.1 | 5 | Beweis | Beweislauf aus Rohdaten | — (nur Ausführung) | Wellen 0–4 | `rm -rf build && make all` erzeugt das TIF vollständig neu; Abnahmebedingung erfüllt; Laufzeiten je Stufe protokolliert. |

## 8. Regeln der Parallelität

1. **Ein Pfad, ein Besitzer — für Code.** Jeder Pfad im Repo steht in genau
   einem Paket. Wer eine Datei anfassen will, die ihm nicht gehört, meldet
   das, statt sie zu ändern — sonst entstehen genau die stillen
   Überschreibungen, die dieses Repo ohnehin plagen. **Ausgenommen:
   `pipeline/contract.py`**, das ein Register ist und von jedem Paket für
   seine eigenen Einträge fortgeschrieben wird — siehe §13.1.
2. **Der Vertrag wird gelesen, nicht kopiert.** Nach Welle 0 kommt kein
   Pfad und kein Layername mehr als Literal in ein Skript. Wer einen
   braucht, importiert ihn. Damit ändert eine Umbenennung genau eine Datei
   statt fünfzehn.
3. **Ein Zweig je Paket.** Achtzehn gleichzeitige Pakete in einem
   Arbeitsverzeichnis kollidieren auch bei sauberer Pfadaufteilung — an
   `uv.lock`, an `Makefile`, an der Zeilenzählung. Je Paket ein eigener
   Zweig oder ein eigenes Worktree, Zusammenführung an der Wellengrenze.
4. **Kein Paket ändert Zahlen.** Puffer, Schwellwerte, Klassifikationen
   bleiben, wie sie sind — auch wo sie fragwürdig aussehen. Wer beim Umbau
   eine fachliche Auffälligkeit findet, schreibt sie auf und ändert sie
   nicht. Sonst ist am Ende nicht mehr unterscheidbar, ob eine Abweichung
   Umbau oder Absicht war.
5. **Der geteilte Checkpoint-Ordner wird nur allein verändert.** Lesen ist
   jederzeit frei, Löschen und Ersetzen nur, wenn kein anderes Paket
   gleichzeitig rechnet — siehe §13.2.
6. **Die Fortschrittsdatei schreibt niemand außer mir.**
   `docs/rewrite/FORTSCHRITT.md` und `docs/rewrite/PLAN.md` sind für Pakete
   tabu; sie berichten stattdessen. Zwei parallele Pakete, die beide ins
   Protokoll schreiben, kollidieren an der Wellengrenze garantiert.

## 9. Bekannte Grenzen

- **Referenzbänder 37/38 ohne Layer-Knoten.** Die Bänder 37 und 38
  entstehen direkt in der Finalisierung, ohne Checkpoint dazwischen. Eine
  Quelle, die nur ein Referenzband speist, hat deshalb keinen `layer:`-
  Knoten im Pfad — und darf nicht allein deshalb als Sackgasse gelten. Wer
  eine Löschliste aus dem Graphen ableitet, muss diesen Fall ausnehmen.
- **Abgeleitete `provides`-Kanten im Graphen.** Ein Teil der Datei-Zugriffe
  passiert nicht im Skript, sondern in einem Modul des `windkraft`-Pakets;
  Skripte sind mit Modulen nur über Import-Kanten verbunden, die bewusst
  nicht als Datenfluss zählen. Die Korrektur fügt abgeleitete Kanten vom
  Modul zum Skript hinzu, markiert sie als solche und hält sie von den
  belegten unterscheidbar — sonst endet der Pfad Rohdatei → Modul im
  Nichts.
- **Hardlink-Richtigstellung.** Angenommen war, in `data/` dürfe erst
  gelöscht werden, wenn die Hardlinks aufgelöst sind. Das ist falsch: `rm`
  entfernt nur einen Verzeichniseintrag, der Inode überlebt, solange der
  zweite Name im Vorgängerprojekt existiert. Gefährlich ist allein das
  Überschreiben an Ort und Stelle. Damit sind Löschen (W1.2) und Auflösen
  (W1.3) voneinander unabhängig und laufen in derselben Welle.

## 10. Nächster Schritt

**W1.2** — tote Daten löschen und die Provenienz retten. Der gesamte
Aufräumteil der Welle 1 ist zusammengeführt; als Nächstes kommt das
Datenfenster aus §12.2, in dem nichts anderes rechnen darf.

**Eine Abweichung vom Plan, bewusst:** W1.2 und W1.3 bekommen **kein
eigenes Worktree**. Regel 3 verlangt eines je Paket, aber `data/` ist in
jedes Worktree nur hineinverlinkt — eine Löschung dort wirkt ohnehin
global. Ein Worktree gäbe hier also **falsche Sicherheit** statt echter
Isolation und würde die Handlung zusätzlich schwerer nachvollziehbar
machen. Beide Pakete laufen deshalb direkt im Hauptrepo, seriell, mit
Inventar vorher und nachher als Netz.

## 11. Nachträge aus der Aufklärung zu W0.1

Vor Beginn wurden drei Fragen geklärt, die den Zuschnitt von W0.1 ändern:
welche Rohdatei zu welcher Domäne gehört, welche Codestellen einen
`data/`-Pfad wirklich *öffnen*, und was davon nur Text ist. Die Befunde
korrigieren den Plan an vier Stellen.

### 11.1 Nur 26 der 86 Fundstellen sind funktional

Eine Textsuche findet 86 Vorkommen von `data/` in 17 Dateien. Verfolgt man
jeden Wert bis zu seiner Verwendung, bleiben:

| Klasse | Zahl | Bedeutung |
|---|---|---|
| **F — funktional** | 26 | Der Wert wird geöffnet, geprüft oder entpackt. Bricht beim Verschieben. |
| **D — dokumentarisch** | 32 | Fließt nur als Text in eine Ausgabe. Wird falsch, nicht kaputt. |
| **K — Kommentar/Docstring** | 27 | Geht nirgendwo hin. |
| **U — unklar** | 1 | `config.json:wind_pd_100` — deklariert, kein Konsument, Datei existiert nicht. |

Die zwölf Dateien mit mindestens einem funktionalen Pfad — nur diese können
die Kette brechen:

`config.json` (6) · `windkraft/calc/wind_zones.py` (4) ·
`scripts/preprocessing/create_noe_dkm_polygon_fill_map.py` (3) ·
`scripts/widmung_v2/04_create_distance_zones.py` (3) ·
`scripts/preprocessing/export_at_dkm_geoparquet.py` (3) ·
`scripts/noe/extract_noe_vector_layers.py` (2) · `windkraft/noe/pdf_align.py` (1) ·
`scripts/widmung_v2/03_build_osm_layers.py` (1) ·
`scripts/widmung_v2/02_build_hig_sources.py` (1) ·
`windkraft/calc/widmung_sources.py`, `tools/check_hardlink_safety.py`,
`scripts/noe/align_pdf_shapefile.py` (zusammengesetzte Pfade, s. u.).

Drei Wege setzen den Pfad zusammen, statt ihn zu schreiben, und werden von
einer Suche nach `data/` deshalb nicht gefunden:
`widmung_sources.py:39-40` (`ROOT / "data" / …`), `check_hardlink_safety.py:146`
(`repo_root / "data"`), `align_pdf_shapefile.py:28-30` (`DATA = Path("data")`).
Wer die Trefferliste für vollständig hält, übersieht genau diese drei.

Rein dokumentarisch, aber trotzdem nachzuziehen, damit das Manifest nicht
lügt: `band_manifest.py` (20 Herkunftsangaben, landen im Feld `sources` der
`*.bands.json` und werden nachweislich von niemandem zurückgelesen),
`widmung_sources.py` (10 tote `"source"`-Felder), `check_hardlink_safety.py` (2
Meldungstexte).

### 11.2 Zielbaum

Neun Verzeichnisse, eines je Domäne, ohne Umlaute:

```
data/
  admin/        Verwaltungsgrenzen (VGD 50)          ←  admin_boundaries/
  kataster/     8 DKM-Archive + Symbol-CSV           ←  unverändert
  adressen/     BEV-Adressregister                   ←  adressregister/
  widmung/      9 Bundesländer, je ein Verzeichnis   ←  flächenwidmungen/ + new_widmungs_data/
  osm/          austria-260330.osm.pbf               ←  Wurzel
  gelaende/     DGM_R25.tif, AUT_power-density_150m  ←  Wurzel
  natur/        Schutzgebiete 2024                   ←  naturschutzgebiete/
  zonen/        luca_zonen/, zonierung_noe.json,     ←  Wurzel + luca_zonen/
                WK_Eignungszonen.zip, RED_III_*.zip
  noe_sekrop/   SekROP-Karte (PDF)                   ←  nö_zonierung/
```

Die **Zwei-Ordner-Falle der Widmung** wird dabei aufgelöst.
`flächenwidmungen/` und `new_widmungs_data/` sind kein Alt- und Neustand: die
Steiermark bezieht Bauland aus dem einen und Grünland/Freizeit aus dem
anderen, Burgenland liegt allein im ersten. Künftig steht beides unter
`data/widmung/steiermark/`. Das ist die einzige Änderung in W0.1, die über
reines Verschieben hinausgeht — `widmung_sources.py` verliert seine zwei
Wurzeln `NEW`/`OLD` und bekommt eine.

**Vier Dateien bleiben liegen, wo sie sind**, weil W1.2 sie ohnehin entfernt:
`osm_power_lines.gpkg`, `windkraftzonen_shapefile_2024.json`,
`WINDKRAFT_AUSSCHLUSSZONE.zip`, `README.md`. Sie jetzt zu verschieben hieße,
Literale für Dateien nachzuziehen, die in derselben Welle verschwinden.

### 11.3 Vier Korrekturen am Plan

| # | Befund | Änderung |
|---|---|---|
| 1 | `data/README.md` ist die einzige Provenienzdokumentation im Repo — 48 K, neun Abschnitte, Herkunft und Lizenz je Quelle, einzige Ausnahme vom `.gitignore`. Sie beantwortet die Zwei-Ordner-Falle, den ungeklärten Status der Ausschlusszonen und die Build-Caches autoritativer als der Code. | W1.2 **verschiebt** sie nach `docs/rohdaten.md`, statt sie zu löschen. `adressregister/Aktualitaetsstand.txt` (186 B) bleibt: kein Leser, aber es hält den Stichtag der BEV-Lieferung fest. |
| 2 | In `data/` liegen zwei **abgeleitete** Dateien: `adressen_31287.parquet` (40 M) und `bev_gebaeude_31287.parquet` (41 M), Build-Caches von `bev_register.py`. Bei einem Cache-Fehlschlag schreibt das Modul still dorthin. | Reihenfolge korrigiert: **W1.4 setzt W1.1 und W1.2 voraus.** Sonst schlägt der neue Wächter am ersten Tag auf zwei Dateien an, die dort noch legitim liegen. |
| 3 | Der Zuschnitt „`data/**` und `wind_zones.py`" hätte die Kette an elf weiteren Stellen zerbrochen. | W0.1 besitzt zusätzlich die elf übrigen Dateien mit funktionalem Pfad und die drei mit rein dokumentarischem. Zulässig, weil Welle 0 sequenziell läuft — es gibt keinen Nebenläufer, dem eine Datei entzogen wird. `config.json` geht danach an W0.2 über. |
| 4 | **`data/` ist gitignoriert.** Ein Fehlgriff im 13-GB-Baum ist nicht per `git checkout` rückholbar. 52 der 56 Dateien sind zusätzlich ins Vorgängerprojekt verlinkt und darüber wiederherstellbar — vier nicht. | Vor der ersten Verschiebung wird ein Inventar mit Größe, Inode und Prüfsumme geschrieben und danach verglichen. Die vier nicht verlinkten Dateien werden vorab benannt und einzeln geprüft. |

### 11.4 Abnahme von W0.1

Zwei Stufen, weil ein Lauf allein nicht alles erreicht:

1. **Statisch — vollständig.** Jeder der 26 funktionalen Pfade plus die drei
   zusammengesetzten Wurzeln lösen auf eine existierende Datei auf. Das deckt
   auch Kataster, Widmung und Adressen ab, die ein Finalisierungslauf nicht
   anfasst.
2. **Dynamisch — stichprobenartig, aber scharf.** Die Finalisierung aus den
   vorhandenen Checkpoint-Layern liefert ein bitgleiches TIF. Sie liest
   `zonen/`, `osm/` und `gelaende/` und prüft damit die tatsächlich bewegten
   Pfade.

Tritt hier schon eine Abweichung auf, stimmt etwas am Verschieben nicht.
Dann wird angehalten, nicht die Ampel bemüht.

### 11.5 Ergebnis von W0.1

Commit `5aab405`. Vier Nachweise, in dieser Reihenfolge geführt:

| Nachweis | Ergebnis |
|---|---|
| **Inodes über das Verschieben** | 56 vorher, 56 nachher, jeder genau einmal wiedergefunden; Linkcounts und Prüfsummen unverändert, Gesamtgröße auf das Byte gleich. `mv` innerhalb eines Dateisystems hat nur umbenannt — nichts wurde kopiert, nichts verlor seinen Hardlink. Dauer: 2,5 Minuten für 13 GB. |
| **Pfadauflösung** | 35 funktionale Pfade lösen auf eine existierende Datei auf. Die zwei bekannten Leerläufer fehlen erwartungsgemäß. Alle 15 geänderten Python-Dateien kompilieren, `config.json` ist gültig. |
| **Bitgleichheit** | Finalisierung aus 34 vorhandenen Checkpoint-Layern in 167 s; Ergebnis `sha256`-identisch zu `run1` — 124.685.819 Bytes, 38 Bänder. |
| **Inode-Abgleich alt gegen neu** | 30 von 30 abbildbaren Codestellen zeigen auf **dieselbe** Inode wie vor dem Umbau. Null Vertauschungen, kein verwaister und kein neu getroffener Inode. |

Der vierte Nachweis war nötig, weil die ersten drei eine Lücke lassen: der
Bitgleichheitslauf hat **drei der neun Verzeichnisse gar nicht angefasst**
(`zonen/`, `osm/`, `natur/` — ihre Checkpoints lagen vor), und die
Pfadprüfung belegt nur, dass *eine* Datei am neuen Ort liegt, nicht dass es
dieselbe ist. Ein Pfad, der nach dem Umbau auf eine andere vorhandene Datei
zeigt, wäre durch beide Prüfungen gerutscht und hätte still falsche Inhalte
geliefert. Der Inode-Abgleich schließt das vollständig und in Sekunden —
insbesondere für die beiden steirischen Widmungsquellen, die jetzt im selben
Verzeichnis liegen und deren Vertauschung an keiner Fehlermeldung und an
keiner Bandzahl aufgefallen wäre.

**Nebenbefund mit Folgen für Welle 2:** `layer_done()` erkennt einen Layer
als fertig, wenn Form, CRS, Transform und Bandname des vorhandenen
Checkpoints passen — die Rohquelle sieht die Prüfung nicht an. Man kann also
eine Rohdatei austauschen, und die Kette rechnet mit dem alten Layer weiter.
Entscheidung (c) sieht einen Fingerabdruck der Eingänge für die Prep-Stufen
vor; derselbe Mechanismus wird auch auf der **Layer**-Stufe gebraucht. Das
gehört in W2.1–W2.3, nicht nur in die Prep-Pakete.

**Nachzügler:** `docs/analysis/streusiedlung_knee.py:71` zeigte noch auf
`data/adressregister`. Das Skript ist kettenfremd und wird von keinem
Make-Ziel aufgerufen, es bricht bei Direktaufruf also laut statt still —
aber W0.1 hat es zerbrochen, also hat W0.1 es repariert.

## 12. Zuschnitt der Welle 1

Achtzehn Pakete sind formal parallel. Zwei Sachverhalte verbieten es
trotzdem, sie alle gleichzeitig loszulassen — beide beim Durchdenken nach
Welle 0 aufgefallen, keiner steht in §7.

### 12.1 Erledigt: die Vergleichsbasis wechselt doch nicht

Ursprünglich stand hier, W1.7 verschiebe die Basis: Band 37 verliere die
steirischen Ausschlusszonen, also müsse ein neuer Vergleichsstand `run2`
erzeugt werden, sonst melde jedes folgende Paket eine Abweichung, die es
nicht verursacht hat.

**Die Prämisse war falsch, und W1.7 hat es gemessen.**
`load_wind_exclusion_zones()` wird im ganzen Repo nirgends aufgerufen; ein
Band `official_wind_exclusion_zoning` gibt es im 38-Band-Schema nicht. Die
Ausschlusszonen erreichten nie ein Band. `run2.tif` ist bitgleich zu
`run1.tif` — dieselbe `sha256`, alle 38 Bänder.

**Folge: `run1` bleibt für das gesamte Projekt die Vergleichsbasis.** Kein
Wechsel, kein Sonderfall in Band 37, keine Ausnahme in der Ampel. Das ist
eine Fehlerquelle weniger für die verbleibenden Pakete.

Die Reihenfolge W1.7 vor W1.2 bleibt trotzdem richtig — Code entfernen,
bevor die Datei verschwindet, ist unabhängig vom Messergebnis die saubere
Richtung.

### 12.2 W1.2 und W1.3 fassen den geteilten Rohbaum an

`make worktree` verlinkt `data/` in jedes Arbeitsverzeichnis. Das ist
gefahrlos, solange der Baum unveränderlich ist — genau das sind diese beiden
Pakete aber nicht: W1.3 ersetzt 52 Dateien durch echte Kopien, W1.2 löscht
fünf Einträge. Ein Abnahmelauf, der währenddessen liest, kann eine Datei
halb ersetzt sehen.

**Beide bekommen ein eigenes Zeitfenster, in dem sonst nichts rechnet.** Und
die Reihenfolge darin ist nicht beliebig: **W1.7 muss die Codestelle
entfernt haben, bevor W1.2 die Datei löscht.** Sonst liegt dazwischen ein
Zustand, in dem `wind_zones.py` eine fehlende Datei still überspringt und
Band 37 sich ändert, ohne dass es jemand beschlossen hätte — der stille
Fallback, den dieses Projekt ohnehin loswerden will, würde ausgerechnet die
Abnahme verfälschen.

### 12.3 Reihenfolge

| Stufe | Pakete | gleichzeitig? |
|---|---|---|
| 1 | W1.7 → `run2` als neue Basis | allein |
| 2 | W1.1, W1.5, W1.6, W1.8, W1.9 | ja, fünf |
| 3 | W1.2, dann W1.3 | allein, nichts sonst rechnet |
| 4 | W1.4 (Wächter) | allein — braucht W1.1 und W1.2 |
| 5 | W1.P1 – W1.P9 | ja, aber gedrosselt: schwere Läufe konkurrieren um Platte und Kerne |

## 13. Nachträge aus der Welle 1

Drei Regeln haben sich im Betrieb als unvollständig erwiesen. Alle drei
Korrekturen stammen aus Befunden der Pakete selbst, nicht aus Theorie.

### 13.1 Regel 1 gilt für Code, nicht für das Register

**Beobachtung:** `pipeline/contract.py` gehört laut §7 dem Paket W0.2. Zwei
Pakete haben es trotzdem geändert — W1.7 (`9475f6c`) und W1.6 (`e3d3655`),
beide, weil sie einen Layer entfernt haben, der dort eingetragen war. Beide
haben es gemeldet. Regel 1 ist damit faktisch zweimal gebrochen, und beim
dritten Mal wäre es Gewohnheit.

**Die Regel war falsch formuliert, nicht die Pakete.** Der Vertrag ist ein
*Register*, kein Modul: jedes Paket, das eine Quelle oder einen Layer
hinzufügt oder entfernt, **muss** dort eintragen oder austragen. Ein
Register mit einem Alleinbesitzer wäre nach Welle 0 sofort veraltet.

**Neue Fassung von Regel 1:**

> Ein Pfad, ein Besitzer — **für Code**. `pipeline/contract.py` ist davon
> ausgenommen: es ist ein Register, das jedes Paket für **seine eigenen**
> Einträge fortschreibt. Wer dort etwas ändert, ändert ausschließlich die
> Einträge, die zu seinem Paket gehören, zieht die Zählzusicherungen in
> `tests/test_contract.py` mit und nennt beides im Bericht. Alles andere in
> der Datei bleibt unangetastet.

Die Alternative — ein „Contract-Pflege"-Paket je Welle — wäre teurer und
langsamer: sie würde jedes Paket auf einen Sammeltermin warten lassen, für
eine Änderung von zwei Zeilen.

### 13.2 Der geteilte Checkpoint-Ordner ist beschreibbar, und das ist gefährlich

**Beobachtung:** W1.6 hat `distance_layers/noe_pdf_hig_source.tif` gelöscht
— zu Recht, denn der Layer existiert nicht mehr und ein Test hätte ihn
sonst weiter erwartet. Aber dieser Ordner ist per Symlink in **jedes**
Worktree eingehängt und wird von jedem Nachweislauf gelesen. Eine Löschung
dort wirkt sofort auf alle.

Im konkreten Fall war es harmlos, weil W1.6 allein lief. In einem
Parallelbatch hätte es die Nachweisgrundlage der anderen Pakete unter ihnen
weggezogen — und zwar lautlos, weil ein fehlender Checkpoint nicht als
Fehler auffällt, sondern als „muss neu gerechnet werden".

**Neue Regel 5:**

> **Der geteilte Checkpoint-Ordner wird nur allein verändert.** Löschen oder
> Ersetzen einer Datei in
> `output/abschichtung_widmung_v2/distance_layers/` ist eine
> Datenfenster-Handlung wie W1.2 und W1.3: erlaubt nur, wenn kein anderes
> Paket gleichzeitig rechnet. Lesen bleibt jederzeit frei. Wer dort löscht,
> nennt im Bericht die Datei, den Grund und die Zahl der verbliebenen
> Checkpoints.

### 13.3 Zusammenführen ist ein Arbeitsschritt, kein Nebenprodukt

**Beobachtung:** Beim Zusammenführen der vier parallelen Welle-1-Zweige hat
Git ohne einen einzigen Konfliktmarker drei falsche README-Aussagen
erzeugt. Jede Einzeländerung war korrekt; erst gemeinsam wurden sie falsch,
weil ein Paket eine Datei löschte, über die ein anderes eine Aussage
korrigiert hatte.

**Konsequenz für jede künftige Wellengrenze:**

> Überschneiden sich die Dateimengen zweier zusammengeführter Pakete, wird
> die zusammengeführte Fassung danach **inhaltlich gegen den Code geprüft**
> — nicht nur auf Konfliktfreiheit. Für Prosa leistet das kein Werkzeug.
> Kalkuliert wird dafür rund die Hälfte der durch Parallelität gesparten
> Zeit.

### 13.4 Konflikte werden vorher verhindert, nicht nachher aufgelöst

§13.3 hält fest, was ein Zusammenführen mit überlappenden Dateimengen
kostet. Die Prep-Welle zeigt, dass man diesen Preis oft **gar nicht zahlen
muss** — wenn man die Überschneidung vorher wegkonstruiert.

Neun Prep-Pakete laufen parallel. Jedes bräuchte einen Eintrag in
`pipeline/contract.py:PREP` und ein Ziel im `Makefile`: zwei garantierte
neunfache Konflikte an je einer Stelle. Bei Prosa kostet das
Nachprüfungszeit; bei einem `Makefile` kostet es einen kaputten Build.

**Neues Vorgehen, ab der Prep-Welle verbindlich:**

> Bevor ein Batch von mehr als drei Paketen startet, prüfe ich, welche
> Dateien **alle** anfassen müssten. Für jede solche Datei gilt: entweder
> sie wird **vorher** in einem Vorpaket fertig deklariert, oder die
> Struktur wird so geändert, dass jedes Paket eine **eigene** Datei
> bekommt. Erst dann startet der Batch.

Konkret für die Prep-Welle (Paket **W1.P0**): Alle neun Prep-Pfade werden
im Vertrag vorab erklärt, und das `Makefile` bekommt einmalig
`-include make/prep/*.mk`. Jedes Prep-Paket legt danach `make/prep/<domäne>.mk`
an — neun verschiedene Dateien statt neun Änderungen an einer.

Das kostet zwanzig Minuten vorher und spart eine Zusammenführung, die nach
der gemessenen Regel aus §13.3 sonst über eine Stunde gekostet hätte.

### 13.5 Auflösung des Widerspruchs zu `gelaende`

W1.P0 hat einen echten Widerspruch in diesem Plan gefunden: **§4 sagt, die
Domäne `gelaende` brauche kein Prep. §7 sieht trotzdem ein Paket W1.P6 mit
eigenem Prep-Modul dafür vor.** Beides kann nicht wörtlich stimmen.

**Beides stimmt, sobald man „Prep" genauer fasst.** Die beiden Dateien
(`DGM_R25.tif`, `AUT_power-density_150m.tif`) sind bereits Raster im
Zielformat — sie brauchen keine **Umformung**. Was sie brauchen, ist eine
**Prüfung**: dass Gitter, Auflösung und CRS wirklich zu EPSG:31287, 25 m,
24001 × 14001 passen, bevor die Layer-Stufe das stillschweigend annimmt.
Genau diese Annahme ist die Sorte, die in diesem Projekt schon mehrfach
unbemerkt falsch war.

**Verbindliche Fassung:**

> Die Domäne `gelaende` durchläuft **keine Umformung**, aber eine
> Prep-Stufe wie alle anderen. W1.P6 schreibt keinen umgeformten Datensatz,
> sondern einen **Prüfbericht und einen Fingerabdruck** nach
> `build/prep/gelaende/`. Damit hat jede der neun Domänen dieselbe Form —
> eine Stufe, eine Ausgabe, ein Fingerabdruck — und die Kette hat keine
> Sonderfälle. Der Eintrag `PREP["gelaende"]` bleibt.

Der Satz in §4 ist damit als „keine Umformung nötig" zu lesen, nicht als
„keine Stufe nötig".

**Nachtrag: die Abbruchbedingung entfällt.** §7 nennt in der
Abnahme-Spalte zu W1.P6 „Bricht ab, wenn Gitter oder CRS abweichen". W1.P6
hat gemessen, dass das Windraster in **allen vier** geprüften Merkmalen
abweicht — EPSG:4326 statt 31287, 0,0025 Grad statt 25 Meter, 3069 × 1076
statt 24001 × 14001. Eine abbrechende Prüfung würde also die **heute
funktionierende Kette anhalten**.

Sie tut es zu Unrecht: `abschichtung_common.py` reprojiziert beide Raster
ohnehin bilinear auf das DGM-Gitter. Die Abweichung ist keine Störung,
sondern der erwartete Zustand einer fremden Quelle.

> **Verbindlich:** Die Prüfstufe `gelaende` **berichtet und bricht nie ab.**
> Sie schreibt die gemessenen Werte gegen die Sollwerte in einen
> Prüfbericht. Ob eine Abweichung toleriert oder behoben wird, entscheidet
> die Layer-Stufe in Welle 2 — dort, wo das Wissen darüber sitzt, was mit
> dem Raster geschieht.

Die allgemeine Lehre: **Eine Prüfung, die abbricht, muss wissen, was
richtig ist.** Diese hier wusste es nicht — der Sollwert stammte aus meiner
Annahme, nicht aus einer Messung. Eine berichtende Prüfung ist in so einem
Fall nicht die schwächere Wahl, sondern die einzig ehrliche.

### 13.6 Gemeinsame Entscheidungen sind gefährlicher als gemeinsame Dateien

§13.4 sucht vor einem Batch nach Dateien, die mehrere Pakete anfassen
müssten. W1.P0 hat gezeigt, dass das nicht reicht.

`pipeline/fingerprint.py` wäre von keinem Paket geteilt worden: Jedes der
neun hätte seinen Fingerabdruck in **seiner eigenen** Datei implementiert.
Kein Konflikt, kein Merge-Problem, keine Warnung — und am Ende neun leicht
verschiedene Antworten auf dieselbe Frage. Aufgefallen wäre das erst, wenn
Welle 5 sich darauf verlässt, dass Fingerabdrücke vergleichbar sind.

**Ergänzung zur Regel aus §13.4:**

> Vor einem Batch frage ich nicht nur „welche Datei fassen alle an", sondern
> auch: **„welche Frage muss jedes Paket beantworten?"** Jede Antwort, die
> für alle gleich ausfallen soll — ein Fingerabdruck, ein Namensschema, ein
> Fehlerverhalten, ein Ausgabeformat — wird **vorher einmal** entschieden
> und als gemeinsames Modul bereitgestellt. Sonst driften neun Pakete
> auseinander, ohne je zu kollidieren.

### 13.7 Der Nachweislauf gehört nicht in jedes Paket

Bis einschließlich W1.P2 hat **jedes** Paket den vollen Nachweislauf
ausgeführt: `04_create_distance_zones.py` gegen die geteilten
Checkpoint-Layer, rund 165 Sekunden, Prüfsumme gegen `run1`. Für die
Aufräum- und Datenpakete war das richtig — sie haben Code angefasst, den
die Kette liest.

**Für die Prep-Welle ist es Verschwendung.** Eine Prep-Stufe schreibt nach
`build/prep/`; die Kette liest heute noch die Rohdatei und wird erst in
Welle 2 umgestellt. Der Nachweislauf kann also gar nichts über die
Prep-Stufe aussagen — er belegt nur, dass nichts *anderes* kaputtging.
Neun Mal dieselbe Aussage, bei drei gleichzeitigen Paketen zusätzlich
verlangsamt durch Konkurrenz um dieselbe Platte.

Dazu kommt ein praktisches Problem: Der Lauf ist lang genug, dass Agenten
ihn in den Hintergrund schieben und sich dann auf eine Benachrichtigung
schlafen legen, die in diesem Setup nicht ankommt. Das ist bisher **fünfmal**
passiert. Jedes Mal war der Lauf längst fertig.

**Neue Regelung ab W1.P3:**

> Ein Prep-Paket führt **keinen** eigenen Nachweislauf durch. Seine Abnahme
> besteht aus `make test`, `make check-guards`, dem Lauf seines eigenen
> `prep-<domäne>`-Ziels und seinem fachlichen Gleichheitsnachweis. **Ein**
> Nachweislauf findet an der Wellengrenze statt, nach dem Zusammenführen
> aller Prep-Pakete — dort ist er aussagekräftig, weil er alle Änderungen
> zugleich prüft.

Aus neun Läufen wird einer. Der Nebeneffekt ist der wichtigere: Die
häufigste Fehlerquelle dieser Sitzung verschwindet aus neun Aufträgen.

### 13.8 Eine Konfliktprüfung findet keine Lücke

§13.4 verlangt vor jedem Batch, die geteilten Dateien vorab zu erklären.
Vor Welle 2 habe ich das getan — und die Prüfung hat meinen Verdacht
sauber widerlegt: die Funktionsblöcke von HiG (769–958) und OSM
(958–1154) in `abschichtung_common.py` sind disjunkt, und `contract.py`
führt alle 33 Layernamen bereits vollständig. Zwei befürchtete
Konfliktherde existieren nicht.

**Gefunden wurde etwas anderes, und es war schwerer.** Der Test
`tests/test_contract.py:280-302` setzt die Sollmenge der Checkpoints aus
**vier** Skripten zusammen; mein §7 beauftragte **drei**. Die 17 Layer aus
`04_create_distance_zones.py` — Puffer, Naturschutz, Gelände, offizielle
Windzonen, WKA-Bestand — hatten keinen Besitzer. Nach Welle 2 hätte ein
Viertel der Kette gefehlt.

> **Regel 7.** Vor jeder Welle wird die Paketliste **gegen das Ziel**
> geprüft, nicht gegen sich selbst. Die Frage lautet nicht nur „welche
> Datei fassen zwei Pakete an", sondern „welcher Teil des Ziels gehört
> **keinem**". Die Sollmenge kommt dabei aus Vertrag und Tests, nicht aus
> meiner eigenen Tabelle — sonst prüfe ich die Quelle des Fehlers gegen
> sich selbst.

Der Unterschied ist grundsätzlich: Eine Konfliktprüfung sucht
Überschneidungen. Eine Lücke *ist* keine Überschneidung. Kein Merge, kein
Test und kein Wächter meldet sie, denn es fehlt nichts, was jemand
versprochen hätte — und kein Paket meldet sie, weil keines dafür
zuständig ist. Sie fällt erst am fertigen Ergebnis auf.

**Drei Folgen für den Zuschnitt der Welle 2:**

**W2.2 geht in W2.1 auf.** `hig_source_masks.py:70-75` verundet in
`widmung_seed()` die drei Widmungs-Layer, und das Ergebnis geht als
Eingabefilter in `candidate_filter_mask()`, die die Hüllenerkennung
einschränkt. Die HiG-Layer sind heute ohne die Widmungs-Layer nicht
berechenbar — beide entstehen in einem einzigen
`ensure_group_layers()`-Aufruf. Getrennt blieben nur zwei Wege:
`widmung_seed()` verdoppeln, also genau die stille Drift aus §13.6, oder
eine Datei zu zweit besitzen, was Regel 1 verbietet. Meine
„Braucht"-Spalte sagte für beide „Welle 1"; richtig wäre eine Kante
zwischen ihnen gewesen. Ein Paket ist sauberer als eine Kante.

**W2.4 ist neu** und übernimmt die 17 herrenlosen Checkpoints. §3 sagt,
Stufe 4 gelte für jede Domäne; dann muss sie auch für jede beauftragt
sein. Die Alternative — sie in W3.1 aufgehen zu lassen — widerspräche §3,
das die Finalisierung als reine Komposition aus vorhandenen Checkpoints
beschreibt.

**W2.P0 ist neu** und richtet das Vorfeld ein, wie W1.P0 es für die
Prep-Welle tat. Drei Dinge gehören hinein, jedes davon sonst ein
Dreifachkonflikt oder Schlimmeres:

1. `pipeline/layers/__init__.py` — sonst legt es an, wer zuerst kommt.
2. `-include make/layers/*.mk` im `Makefile`, analog zum Prep-Muster.
   Ohne das schreiben drei Pakete ihre Ziele in dieselbe Datei.
3. **`build/prep/` ins `worktree`-Ziel**, als Symlink wie `data/` und
   `distance_layers/`. Das ist der teuerste der drei Punkte: Heute
   verlinkt `Makefile:163-174` nur diese beiden. Drei Layer-Worktrees
   hätten die Prep-Stufe je einzeln neu gerechnet — Kataster allein 45 bis
   70 Minuten, dreifach. Und eine Kopie von Hand zerrisse die
   mtime-basierten Fingerabdrücke aus `fingerprint.py:33-35`, was
   folgenlos aussieht und stille Neuberechnungen auslöst.

**Die gefährlichste Stelle der Welle** liegt ausgerechnet im bislang
herrenlosen Block. `layer_done()` (`abschichtung_common.py:1421-1439`)
prüft Form, CRS, Transform und Bandname — **nicht die Eingabe**. Trifft
das auf den GPKG-Promotionseffekt aus Punkt 20 (zweimal belegt: 383 von
920 bei Naturschutz, 49 von 71 bei den NÖ-Zonen), schreibt sich ein
falscher Wert ins Band und wird beim nächsten Lauf als „fertig"
akzeptiert. Ab Welle 2 wird jede Abweichung zur Frage — hier ist die
Stelle, an der sie niemand stellt. Deshalb steht die
Geometrietyp-Prüfung ausdrücklich in der Abnahme von W2.4.

**Nachtrag:** Die Maschinensichten unten nennen 30 Arbeitspakete. Mit
W2.P0, W2.4 und dem später nachgezogenen W4.P0 (§13.10) sind es 33, und
`packages.tsv`/`packages.json` sind entsprechend veraltet — dieselbe
Baustelle wie Punkt 16.

### 13.9 Die erste Abweichung ist eine Korrektur

Bis Welle 2 galt: Jede Abweichung von `run1` ist ein Fehler. Das war
richtig, solange nur umgebaut und nichts neu berechnet wurde. Mit W2.4
ist der erste Fall aufgetreten, in dem die **neue** Kette recht hat und
die alte unrecht.

`geography_water_bodies` weicht in 543 106 von 336 038 001 Zellen ab —
0,16 %, und **ausschließlich zusätzlich**. Ursache: Der alte Weg klippt
per `osmium extract --bbox` (Strategie „simple") **vor** dem Tag-Filter.
Bei einer großen grenzüberschreitenden Relation kappt das Mitglieder
außerhalb der Box, und die Relation geht beim Export verloren. Die
Prep-Stufe filtert gegen die volle, ungeklippte Rohquelle und findet den
Bodensee.

**Der Zustand ist bewusst nicht entschieden, sondern dokumentiert.** Ob
die Korrektur übernommen wird oder der alte Zustand als Soll gilt, ist
eine fachliche Frage und gehört dem Nutzer (Punkt 33). Bis dahin gilt:

> **Regel 8.** Eine erklärte Abweichung wird **weitergetragen, nicht
> weggemacht** — mit ihrer Zahl, ihrer Ursache und ihrer Richtung. Sie
> muss aber **umkehrbar bleiben**: Die Korrektur besteht allein darin,
> dass die Prep-Stufe ungeklippt filtert; ein Rückbau wäre eine lokale
> Änderung an einer Stelle. Solange das gilt, darf die Arbeit weiterlaufen,
> ohne der Entscheidung vorzugreifen.

Praktische Folge für Welle 3: Der Nachweislauf ergibt **nicht mehr**
`dc58b011…9e3df1`. Abweichen dürfen **ausschließlich** die Bänder, die
aus `geography_water_bodies` gespeist werden — wie viele das sind, weiß
ich nicht und will es als Teil des Nachweises wissen, denn ein
Kategorie- oder Aggregatband kann denselben Layer mitführen. **Jede
andere Abweichung ist ein Fehler** — und die
Vorhersagbarkeit ist hier der eigentliche Test: Eine Zahl, die man vorher
nennt und danach misst, beweist mehr als eine, die man hinterher erklärt.

**Beantwortet von W3.1: es sind neun.** Bänder 26, 29, 30, 31, 32 und
33–36; der neue `sha256` lautet `4bdef6ad…6b1a13e`. Die Liste stammt
nicht aus dem Vergleich, sondern aus dem Manifest — W3.1 hat sie über die
transitive Hülle von `abgeleitet_von` **vor** der Messung berechnet und
danach als Test verdrahtet. Die restlichen 29 Bänder sind bitgleich.

Und die Zahlen laufen nicht linear durch: Von 543 106 zusätzlichen
Wasserzellen erreichen nur **15 137 die Verfügbarkeitsbänder**, weil der
Rest ohnehin schon ausgeschlossen war — während die Weichzeichnungen
denselben Kern auf bis zu 47 023 Zellen **verstärken**. Eine Abweichung
schrumpft also auf dem Weg durch die Aggregate und wächst wieder in den
Unschärfebändern. **Das ist der Grund, warum §6 den Bändern 27–36 ein
Budget in km² gibt statt in Prozent** — die Prozentzahl der Quelle sagt
über die Wirkung am Ergebnis nichts aus. Der Entwurf der Ampel war an
dieser Stelle richtiger, als ich beim Schreiben wusste.

### 13.10 Jede Welle braucht ihr Vorfeld, auch die kleine

W1.P0 und W2.P0 waren eigene Pakete: gemeinsames Modul, `-include`-Zeile
im `Makefile`, Symlink im `worktree`-Ziel. Beide haben sich bezahlt
gemacht — vor Welle 2 verhinderte W2.P0 drei sichere Dreifachkonflikte,
und die anschließenden Merges liefen konfliktfrei.

**Welle 3 hat keines bekommen, und genau das Vorhersehbare ist passiert.**
W3.1 hat `make/finalize/finalize.mk` gebaut, durfte aber `Makefile` nicht
anfassen — das gehört keinem Paket der Welle 3. Also fehlt die eine
`-include`-Zeile, und **`make finalize` ist nicht erreichbar** (Punkt 36).
Kein Test schlägt an, kein Merge kollidiert, kein Wächter meldet etwas:
Die Datei ist da, das Ziel ist da, nur die Verdrahtung fehlt.

Meine Begründung, Welle 3 kein Vorfeld zu geben, war „nur zwei Pakete,
seriell, also kein Konfliktrisiko". Die Begründung stimmt sogar — es
*gab* keinen Konflikt. Sie beantwortet nur die falsche Frage. Das ist
Regel 7 an einer anderen Stelle: Ein Vorfeld verhindert nicht nur
Konflikte, es **weist das Gemeingut einem Besitzer zu**. Wo niemand es
besitzt, fasst es niemand an.

> **Regel 9.** Sobald eine Welle eine **neue Art von Datei** hervorbringt
> — ein Verzeichnis, eine Modulfamilie, eine Make-Fragmentgruppe —,
> gehört die gemeinsame Verdrahtung dafür **vor** die Welle und braucht
> einen benannten Besitzer, unabhängig von der Paketzahl und davon, ob
> die Pakete parallel laufen. Die Prüffrage ist nicht „kollidieren zwei
> Pakete", sondern „**wem gehört die Zeile, die alles zusammenhält**".

Der Preis war hier eine Zeile in W3.2. Bei Welle 4 wäre er höher, und die
Prüfung nach Regel 9 hat dort **sofort dasselbe Loch gefunden**: W4.1 und
W4.2 brauchen beide ein Make-Ziel unter `make/verify/`, aber die
`-include`-Zeile gehörte keinem der drei Pakete — während W4.3 das
`Makefile` für das `test`-Ziel bereits besaß. Zwei Pakete hätten dieselbe
Datei angefasst, das eine erlaubt, das andere unbeauftragt. Dazu kommt,
dass Welle 4 parallel läuft: Ohne `build/layers/` und ein fertiges TIF im
`worktree`-Ziel hätte jeder der drei Worktrees 33 Checkpoints plus 164 s
Finalisierung neu gerechnet — derselbe Fehler, den W2.P0 für `build/prep/`
schon einmal abgewendet hat.

**Deshalb ist W4.P0 neu**, besitzt `Makefile` als einziges Paket der
Welle 4, und W4.3 gibt das `test`-Ziel dorthin ab. Damit sind es
**33 Pakete**. Dass die Regel beim ersten Anwenden gleich etwas findet,
ist kein gutes Zeichen für den ursprünglichen Zuschnitt — aber genau der
Zweck einer Regel, die aus einem Fehler stammt.

## Maschinensichten

- [`domains.tsv`](domains.tsv) / `domains.json` — Domänenmatrix, maschinenlesbar (`src/extract_domains.py`).
- [`packages.tsv`](packages.tsv) / `packages.json` — Paketmatrix aller 30 Arbeitspakete, maschinenlesbar (`src/extract_packages.py`).
- [`../dataflow/nodes.tsv`](../dataflow/nodes.tsv) — Knoten des Datenflussgraphen.
- [`../dataflow/edges.tsv`](../dataflow/edges.tsv) — Kanten des Datenflussgraphen, jede mit Fundstelle.

## HTML-Ansichten

- [`zielbild.html`](zielbild.html) — interaktive Ansicht auf das Zielbild.
- [`umsetzung.html`](umsetzung.html) — interaktive Ansicht auf Wellen, Pakete und Abnahmebedingung.
- [`../dataflow/flow_diagram.html`](../dataflow/flow_diagram.html) — interaktive Ansicht auf den Datenflussgraphen.
