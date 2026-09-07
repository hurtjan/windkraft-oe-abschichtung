# Plan: Umbau der Abschichtungskette

Diese Datei ist in sich geschlossen — wer nur sie liest, braucht keine
andere Quelle im Repo, um den Plan zu verstehen. Maschinenlesbare Details
und interaktive Ansichten sind am Ende verlinkt.

## 1. Stand

**W0.1 abgeschlossen und nachgewiesen** (§11.5). Nächstes Paket: W0.2,
Pfadvertrag. Die übrigen 28 Pakete sind unberührt.

Sicherungspunkte auf Zweig `docs/audit-und-plan`: `e98530a`, `ab2db12`
(Planung), `5aab405` (W0.1). **`data/` ist gitignoriert** — dort ersetzt ein
Inventar aus Größe, Inode und Prüfsumme das fehlende Netz (§11.3).

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
   einem Skript geschrieben. 10 Themengruppen, ~11 GB.
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
  <10 Themengruppen>/     ~11 GB
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
| Kataster | 8 × DKM-SHP-ZIP + NÖ-DXF + Symbol-CSV | 7,8 GB | kataster/a_noe_polygonize → kataster/b_export_parquet | nonresidential_hulls_source; general_buildings_source; hig_hulls_source; bewohnt_einzellage_source | 8–13 | NÖ liefert nur Linienwerk; die Polygone werden per Kachelung und Mehrheitsvotum rekonstruiert. Teuerste Stufe der Kette. |
| Adressregister | BEV Adresse, Stichtagsdaten | 484 MB | adressen | hig_hulls_source | 12–13 | Speist die Streusiedlungserkennung: ≥5 adressierte Objekte in 200-m-Verkettung ergeben eine Hülle. |
| Flächenwidmung | 9 Bundesland-Quellen, GPKG und SHP | 1,6 GB | widmung | official_settlement_source; official_hig_source; ferienhaus_tourismus_source | 1–5 | Niederösterreich ist das einzige Land mit 1200 m Siedlungspuffer statt 1000 m. |
| OSM | austria.osm.pbf | 760 MB | osm/a_extract → osm/b_layers | roads; rail; cableway; water_bodies; nature_osm; military; airport; wka_bestand | 14–22, 26, 38 | Zwei Stufen, weil die osmium-Extraktion teuer ist und die Layer-Ableitung oft wiederholt wird. |
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
| **(a) Ausschlusszonen — beides entfällt.** `WINDKRAFT_AUSSCHLUSSZONE.zip` wird gelöscht, die Steiermark-SAPRO-Domäne wird gar nicht erst angelegt: kein PDF aus dem Vorgängerprojekt, `Stmk2026Aus` verschwindet aus `wind_zones.py`. | Band 37 behält die steirischen *Positiv*zonen aus `luca_zonen/Stmk.shp` und verliert nur die SAPRO-2026-*Ausschluss*zonen. Nebeneffekt zum Guten: die einzige nicht bitgleich reproduzierbare Farbextraktion fällt aus der Kette, PyMuPDF wird nur noch für Niederösterreich gebraucht. |
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
Abschichtung ein. Für Band 37 gilt zusätzlich: der Wegfall der steirischen
SAPRO-2026-Ausschlusszonen ist eine **beschlossene inhaltliche Änderung**
und keine Abweichung — er wird einmal vermessen und im Register vermerkt,
löst aber keine Ampel aus.

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
| 4 | Prüfung | 3 | ja — gleichzeitig |
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
| W2.1 | 2 | Layer | Layer: Widmung | `pipeline/layers/widmung.py` | Welle 1 | Erzeugte Layer bitgleich zu den bestehenden Checkpoints. |
| W2.2 | 2 | Layer | Layer: Häuser im Grünen | `pipeline/layers/hig.py` | Welle 1 | Bitgleich; die NÖ-Ausmaskierung bleibt unverändert erhalten. |
| W2.3 | 2 | Layer | Layer: OSM und Infrastruktur | `pipeline/layers/osm.py` | Welle 1 | Bitgleich; Wiederaufsetzen überspringt vorhandene Layer nachweislich korrekt. |
| W3.1 | 3 | Finalisierung | Finalisierung und Manifest-Vertrag | `pipeline/finalize.py`; `windkraft/calc/band_manifest.py` | Welle 2 | 38 Bänder, Manifest mit Nummer, Name, Rolle, Puffer und Quelle je Band; Schema versioniert. |
| W3.2 | 3 | Finalisierung | Validierung | `pipeline/validate.py` | W3.1 | Prüft das TIF gegen run1 nach der Ampel aus Abschnitt 6 und schreibt `abweichungen.tsv`. |
| W4.1 | 4 | Prüfung | Dashboard neu | `pipeline/verify/dashboard.py`; `out/dashboard/` | W3.1 | Liest ausschließlich das Manifest; keine Bandnamen im Code. Läuft gegen ein Manifest mit geänderter Bandzahl ohne Anpassung. |
| W4.2 | 4 | Prüfung | Gemeindegrenzen-Export | `pipeline/verify/gemeinden.py`; `out/gemeinden.geojson` | W1.P1 | Grenzen im Rasterbezug; Deckungsabweichung gegen das TIF ausgewiesen und unter Schwellwert. |
| W4.3 | 4 | Prüfung | Tests verdrahten | `tests/**`; `Makefile` (nur das test-Ziel) | Welle 3 | `make test` läuft die acht vorhandenen Tests plus die neuen Vertragstests; grün. |
| W5.1 | 5 | Beweis | Beweislauf aus Rohdaten | — (nur Ausführung) | Wellen 0–4 | `rm -rf build && make all` erzeugt das TIF vollständig neu; Abnahmebedingung erfüllt; Laufzeiten je Stufe protokolliert. |

## 8. Regeln der Parallelität

1. **Ein Pfad, ein Besitzer.** Jeder Pfad im Repo steht in genau einem
   Paket. Wer eine Datei anfassen will, die ihm nicht gehört, meldet das,
   statt sie zu ändern — sonst entstehen genau die stillen
   Überschreibungen, die dieses Repo ohnehin plagen.
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

**W0.2** — Pfadvertrag anlegen. W0.1 ist abgeschlossen (§11.5); der
Zielbaum aus §11.2 steht und ist die Grundlage, gegen die der Vertrag
geschrieben wird.

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

## Maschinensichten

- [`domains.tsv`](domains.tsv) / `domains.json` — Domänenmatrix, maschinenlesbar (`src/extract_domains.py`).
- [`packages.tsv`](packages.tsv) / `packages.json` — Paketmatrix aller 30 Arbeitspakete, maschinenlesbar (`src/extract_packages.py`).
- [`../dataflow/nodes.tsv`](../dataflow/nodes.tsv) — Knoten des Datenflussgraphen.
- [`../dataflow/edges.tsv`](../dataflow/edges.tsv) — Kanten des Datenflussgraphen, jede mit Fundstelle.

## HTML-Ansichten

- [`zielbild.html`](zielbild.html) — interaktive Ansicht auf das Zielbild.
- [`umsetzung.html`](umsetzung.html) — interaktive Ansicht auf Wellen, Pakete und Abnahmebedingung.
- [`../dataflow/flow_diagram.html`](../dataflow/flow_diagram.html) — interaktive Ansicht auf den Datenflussgraphen.
