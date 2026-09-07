# Plan: Umbau der Abschichtungskette

Diese Datei ist in sich geschlossen — wer nur sie liest, braucht keine
andere Quelle im Repo, um den Plan zu verstehen. Maschinenlesbare Details
und interaktive Ansichten sind am Ende verlinkt.

## 1. Stand

**Geplant, nicht begonnen.** Kein Paket ist angefangen, kein Code
geändert, keine Datei außerhalb von `docs/` angefasst.

Sicherungspunkt: Commit `e98530a` auf Zweig `docs/audit-und-plan`.

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
| W0.1 | 0 | Daten | Rohdaten nach Thema sortieren | `data/**` (nur Verschiebungen); `windkraft/calc/wind_zones.py` (hartkodierte Pfade) | — | Alte Kette läuft unverändert; Finalisierung aus vorhandenen Layern liefert bitgleiches TIF. |
| W0.2 | 0 | Daten | Pfadvertrag anlegen | `pipeline/contract.py` (neu); `config.json` | W0.1 | Jeder Rohpfad, jede Prep-Ausgabe, jeder Layername und jeder Produktpfad ist genau einmal deklariert und importierbar. |
| W0.3 | 0 | Daten | Verzeichnisgerüst und Make-Ziele | `build/` `out/` `pipeline/` (neu); `.gitignore`; `Makefile` | W0.2 | `make` · `make prep` · `make all` · `make test` existieren; `make` läuft die heutige Kette unverändert. |
| W1.1 | 1 | Aufräumen | Adress-Cache-Weiche entfernen | `windkraft/calc/bev_register.py` | W0.3 | `cache_dir` wirkt tatsächlich; Cache landet unter `build/`, nicht in `data/`. |
| W1.2 | 1 | Aufräumen | Tote Daten löschen | `data/osm_power_lines.gpkg`; `data/windkraftzonen_shapefile_2024.json`; `data/…/Aktualitaetsstand.txt`; `data/…/.claude/`; `data/WINDKRAFT_AUSSCHLUSSZONE.zip`; `data/README.md` | W0.3 | Sechs Pfade weg; TIF unverändert (keiner erreichte ein Band). |
| W1.3 | 1 | Daten | Hardlinks auflösen | `data/**` (nur Inodes, kein Inhalt) | W0.3 | `find data -type f -links +1` liefert nichts; Prüfsummen vorher/nachher identisch; ~13 GB mehr belegt. |
| W1.4 | 1 | Aufräumen | Wächter für Rohdaten | `tools/check_raw_only.py` (neu); `tools/check_hardlink_safety.py` | W0.3 | Bricht ab, wenn in `data/` etwas Abgeleitetes liegt oder eine Datei Link-Count > 1 hat. |
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

**W0.1** — Rohdaten nach Thema sortieren.

## Maschinensichten

- [`domains.tsv`](domains.tsv) / `domains.json` — Domänenmatrix, maschinenlesbar (`src/extract_domains.py`).
- [`packages.tsv`](packages.tsv) / `packages.json` — Paketmatrix aller 30 Arbeitspakete, maschinenlesbar (`src/extract_packages.py`).
- [`../dataflow/nodes.tsv`](../dataflow/nodes.tsv) — Knoten des Datenflussgraphen.
- [`../dataflow/edges.tsv`](../dataflow/edges.tsv) — Kanten des Datenflussgraphen, jede mit Fundstelle.

## HTML-Ansichten

- [`zielbild.html`](zielbild.html) — interaktive Ansicht auf das Zielbild.
- [`umsetzung.html`](umsetzung.html) — interaktive Ansicht auf Wellen, Pakete und Abnahmebedingung.
- [`../dataflow/flow_diagram.html`](../dataflow/flow_diagram.html) — interaktive Ansicht auf den Datenflussgraphen.
