# Zielbild Abschichtungskette

Entwurf für den Umbau der Abschichtungs-Pipeline. Heute mischen sich in
`data/` und `output/` Rohquellen, Build-Caches und Artefakte aus dem
Vorgängerprojekt; sieben Skripte hängen an keinem Make-Target, 29 Dateien
werden erzeugt und nie gelesen. Der Entwurf trennt das in drei Bereiche mit
je einer klaren Regel und macht `rm -rf build && make all` zum Beweis, dass
die Kette wirklich aus Rohdaten läuft.

**Stand: Entwurf. Nichts davon ist umgesetzt — kein Code geschrieben, keine
Datei gelöscht, keine Hardlinks aufgelöst.**

## Die drei Bereiche

- **`data/`** ist unveränderlich und extern bezogen — read-only, nie von
  einem Skript geschrieben.
- **`build/`** ist jederzeit löschbar — Zwischenstand, gitignored.
- **`out/`** enthält genau vier Produkte — kein fünftes.

`rm -rf build && make all` ist der Beweislauf: er zeigt, dass die Kette
allein aus `data/` heraus die vier Endprodukte reproduziert.

## Die vier Endprodukte

| Pfad | Zweck |
|---|---|
| `out/abschichtung.tif` | Das eigentliche Ergebnis der Abschichtung: 38 Bänder, uint8, EPSG:31287, 25 m, 24001 × 14001. |
| `out/abschichtung.bands.json` | Vertrag: Bandnummer, Name, Rolle, Pufferdistanz, Quelle je Band — vom Schreiber selbst erzeugt. Die Datei, die das Dashboard-Repo konsumiert. |
| `out/dashboard/` | Prüfung/Neubau: liest ausschließlich das Manifest, nie eine fest verdrahtete Bandliste. Genau daran ist der heutige Dashboard-Builder gescheitert. |
| `out/gemeinden.geojson` | Prüfung/neu: Gemeindegrenzen im Rasterbezug, um die Deckung visuell zu prüfen — der heute fehlende Test gegen Georeferenzierungsfehler. |

## Die fünf Stufen der Eskalation

Jede Stufe darf nur aus der vorigen lesen — nie zwei überspringen, nie
zurück. Domänen mit aufwendiger Aufbereitung bekommen zwei Prep-Stufen statt
einer.

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
   Unschärfe, Referenzbänder. Schreibt TIF und Manifest in einem Zug. Danach
   `verify`: Dashboard und Gemeindegrenzen.

## Domänen, Rollen, Bänder

Jede Zeile ist ein Zuständigkeitsbereich mit genau einem Prep-Skript. Die
Bandnummern sind die tatsächlichen Deskriptoren des heutigen 38-Band-Rasters.
Dieselben Daten liegen maschinenlesbar in `domains.tsv` / `domains.json`
(siehe `src/extract_domains.py`).

| Domäne | Rohquelle | Größe | Prep | Erzeugte Layer | Bänder |
|---|---|---|---|---|---|
| Verwaltungsgrenzen | VGD 50 generalisiert (BEV) | — | admin | bundesland_masken, gemeinden | alle indirekt · out/gemeinden.geojson |
| Kataster | 8 × DKM-SHP-ZIP + NÖ-DXF + Symbol-CSV | 7,8 GB | kataster/a_noe_polygonize → kataster/b_export_parquet | nonresidential_hulls_source, general_buildings_source, hig_hulls_source, bewohnt_einzellage_source | 8–13 |
| Adressregister | BEV Adresse, Stichtagsdaten | 484 MB | adressen | hig_hulls_source | 12–13 |
| Flächenwidmung | 9 Bundesland-Quellen, GPKG und SHP | 1,6 GB | widmung | official_settlement_source, official_hig_source, ferienhaus_tourismus_source | 1–5 |
| OSM | austria.osm.pbf | 760 MB | osm/a_extract → osm/b_layers | roads, rail, cableway, water_bodies, nature_osm, military, airport, wka_bestand | 14–22, 26, 38 |
| Gelände & Wind | DGM_R25, Leistungsdichte 150 m | 757 MB | kein Prep | geography_slope, geography_elevation, geography_wind | 23–25 |
| Naturschutz | Schutzgebiete Österreich 2024 | 73 MB | natur | nature_protection_areas | 21 |
| Windzonen | luca_zonen, Eignungszonen, RED III, zonierung_noe | 4,9 MB | zonen | — | 37 |
| NÖ SekROP-PDF | Sektorales Raumordnungsprogramm, PDF-Karte | 16,6 MB | noe/a_align → noe/b_vectorize | noe_pdf_750m_zones | 6–7 |

Bandfamilien: 1–2 Widmung Wohn/Misch · 3–7 Häuser im Grünen · 8–13 Gebäude
aus dem Kataster · 14–17 Verkehr, je 150 m · 18–20 Militär und Luftfahrt ·
21–22 Naturschutz · 23–26 Gelände, Wind, Wasser · 27–30 Aggregate · 31–36
Verfügbarkeit und Unschärfe · 37–38 Referenz.

## Löschliste / Bilanz

Alle Zahlen stammen aus dem Datenflussgraphen unter `docs/dataflow/` und
sind dort mit Fundstelle belegt.

| Posten | Details | Zahl |
|---|---|---|
| Tote Konfiguration | `paths.osm_dir` zeigt auf einen nicht existierenden Pfad, dessen Zweig nie erreicht wird; `paths.wind_pd_100` wird nur aufgelöst, nie gelesen. | 2 |
| Tote Daten in `data/` | `osm_power_lines.gpkg` (Zweig tritt nie ein, Band existiert nicht mehr), `windkraftzonen_…json`, `Aktualitaetsstand.txt`, `.claude/`, zwei `.DS_Store`. | 6 |
| Build-Caches, die nach `build/` wandern | Die beiden Adressregister-Parquets, 81 MB. Erst die Weiche in `bev_register.py` entfernen, dann verschieben — sonst greift der Legacy-Zweig wieder. | 2 |
| Erzeugt und nie gelesen | 13 NÖ-Nebenprodukte, 9 Kataster-Diagnostikdateien, 4 Viewer-Pfade, `dashboard_data.json`, der Checkpoint `noe_pdf_hig_source`. Diagnostik wandert nach `build/`, der Rest entfällt. | 29 |
| Skripte ohne Zukunft | `build_layer_viewer.py` (bricht mit `NameError` ab, v1-Eingänge), `build_v2_dashboard_data.py` (8 veraltete Bandnamen), `derive_pdf_hig_sources.py` (vollständig redundant). | 3 |
| Code, der bleibt | Alle fünf Stufe-0-Erzeuger sind byte-identisch zum Vorgängerprojekt und funktionieren — sie werden nur umgehängt, nicht neu geschrieben. Die Bibliothek `windkraft/` behält ihre Rolle. | unverändert |
| Ausschlusszonen, entschieden | `WINDKRAFT_AUSSCHLUSSZONE.zip` entfällt, die Steiermark-SAPRO-Domäne wird gar nicht erst angelegt, `Stmk2026Aus` verschwindet aus `wind_zones.py`. Kein PDF-Import aus dem Vorgängerprojekt. | 1 Domäne |
| Hardlinks aufgelöst | 52 Dateien werden zu echten Kopien. `data/` ist danach unabhängig, das Vorgängerprojekt löschbar. | +13 GB |
| Was dazukommt | Der Gemeindegrenzen-Export; das neue Dashboard gegen das Manifest; `make test` — die acht vorhandenen Tests hängen heute an keinem Target. | 3 |

## Getroffene Entscheidungen

Vier Punkte hingen an fachlichem Wissen, nicht am Code. Alle vier sind
entschieden.

**(a) Ausschlusszonen — beides entfällt.** `WINDKRAFT_AUSSCHLUSSZONE.zip`
wird gelöscht, und die Steiermark-SAPRO-Domäne wird gar nicht erst angelegt:
kein PDF aus dem Vorgängerprojekt, `Stmk2026Aus` verschwindet aus
`wind_zones.py`.
Folge: Band 37 behält die steirischen *Positiv*zonen aus
`luca_zonen/Stmk.shp` und verliert nur die SAPRO-2026-*Ausschluss*zonen.
Nebeneffekt zum Guten: die einzige nicht bitgleich reproduzierbare
Farbextraktion fällt aus der Kette, und PyMuPDF wird nur noch für
Niederösterreich gebraucht.

**(b) Hardlinks — echte Kopien.** Die 52 hardgelinkten Dateien werden zu
eigenständigen Kopien, Kosten rund 13 GB.
Folge: `data/` ist danach unabhängig, das Vorgängerprojekt lässt sich
löschen, ohne dass hier etwas verschwindet. `tools/check_hardlink_safety.py`
wird dabei von „Schreibziele müssen Link-Count 1 haben" auf „*alle* Dateien
müssen Link-Count 1 haben" verschärft — aus der Warnung wird eine Invariante.

**(c) Prep — nicht im Standardlauf.** `make` baut nur Layer und Finalize.
`make prep` ist ein bewusster, separater Aufruf. `make all` hängt beides
zusammen.
Folge: Der Alltagslauf rechnet nicht versehentlich fünf Stunden Kataster
neu, aber `make all` bleibt der Beweis, dass die Kette aus Rohdaten läuft.
Damit das nicht auseinanderläuft, schreibt jede Prep-Stufe einen
Fingerabdruck ihrer Eingänge — passt er nicht mehr, bricht der Layer-Bau ab,
statt mit veralteten Zwischenständen weiterzurechnen.

**(d) Adressregister — Graph korrigiert.** Die Lücke wird nicht als
Einzelfall geflickt, sondern an der Ursache: wo ein Bibliotheksmodul im
Auftrag eines Skripts liest oder schreibt, bekommt der Graph eine
abgeleitete Kante vom Modul zum Skript.
Folge: Der Pfad vom BEV-Adressregister zu den Streusiedlungs-Hüllen ist
wieder durchgängig, und dieselbe Korrektur schließt zugleich die Pfade der
Referenzbänder. Abgeleitete Kanten sind als solche markiert und bleiben von
den belegten unterscheidbar.

## Grenzen des Modells

Der Graph ist ein Werkzeug, keine Wahrheit. Zwei Stellen haben zu falschen
Schlüssen geführt — eine wurde behoben, die andere bleibt und muss bekannt
sein.

**Behoben: Bibliotheks-I/O riss den Pfad ab.** Ein Teil der Datei-Zugriffe
passiert nicht im Skript, sondern in einem Modul des `windkraft`-Pakets, und
Skripte sind mit Modulen nur über Import-Kanten verbunden, die bewusst nicht
als Datenfluss zählen. Dadurch endete der Pfad Rohdatei → Modul im Nichts —
weshalb eine Auswertung behauptete, das Adressregister erreiche keinen
einzigen Layer. Die Korrektur setzt an der Ursache an und gilt für alle
betroffenen Module, nicht nur für dieses eine.

**Bleibt: Referenzbänder haben keinen Layer-Knoten.** Die Bänder 37 und 38
entstehen direkt in der Finalisierung, ohne Checkpoint dazwischen. Eine
Quelle, die nur ein Referenzband speist, hat deshalb keinen `layer:`-Knoten
im Pfad — und darf nicht allein deshalb als Sackgasse gelten. Wer eine
Löschliste aus dem Graphen ableitet, muss diesen Fall ausnehmen.

## Umsetzungsplan

Wie aus diesem Zielbild wird, steht in [`UMSETZUNG.md`](UMSETZUNG.md):
dreißig Arbeitspakete in sechs Wellen, mit Besitz je Pfad, Abhängigkeiten
und Abnahmebedingung je Paket. `umsetzung.html` ist die interaktive Ansicht
darauf; `packages.tsv` / `packages.json` sind die maschinenlesbare
Paketmatrix daraus (`src/extract_packages.py`). Stand: geplant, noch nicht
begonnen.

## Grundlage

Faktengrundlage ist der belegte Datenflussgraph unter `docs/dataflow/`
(`docs/dataflow/flow_graph.json` — 220 Knoten, 348 Kanten, jede mit
Fundstelle im Code). `zielbild.html` in diesem Verzeichnis ist die
interaktive Ansicht auf denselben Entwurf; `domains.tsv` / `domains.json`
sind die maschinenlesbare Domänenmatrix daraus.
