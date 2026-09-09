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
| `out/dashboard/` | Prüfung/Neubau: liest ausschließlich das Manifest, nie eine fest verdrahtete Bandliste. Genau daran war der alte Dashboard-Builder gescheitert — `scripts/analysis/build_v2_dashboard_data.py`, **seit W1.5 gelöscht**, mit rund zwanzig wörtlich verdrahteten Bandnamen der alten 63-Band-Kette, von denen heute keiner mehr existiert. Seit W4.1 prüft die Stufe zusätzlich jede Querverweisung im Manifest gegen sich selbst. |
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
Ausschlusszonen erreichten nie ein Band. Die Ausnahme entfiel ersatzlos:
alle 38 Bänder mussten bitgleich zu `run1` sein, ohne Sonderfall.

#### Die Referenz hat sich am 08.09.2026 zweimal geändert

Der Satz oben galt bis Welle 3. An **einem Tag** hat der Nutzer zwei
fachliche Entscheidungen getroffen, und jede hat die Referenz verschoben:

| Stand | `sha256` | Anlass | Unterschied zum Vorgänger |
|---|---|---|---|
| `run1` | `dc58b011…9e3df1` | die alte Kette | — |
| Welle 3 | `4bdef6ad…6b1a13e` | **Punkt 33**, Bodensee-Korrektur angenommen | neun Bänder: 26, 29, 30–36 |
| **heute** | **`fb57c41d…232c30`** | **Punkt 34**, adresslose Großflächen entfallen | 16 Bänder: 5, 7–13, 27, 30–36 |

**Gegenüber `run1` weichen damit 18 der 38 Bänder ab**, aus zwei
benannten Ursachen — und sieben Bänder (30–36) tragen beide zugleich.
`abweichungen.tsv` führt das getrennt, damit die Überlagerung sichtbar
bleibt statt zu verschmelzen.

Die beiden Wechsel sind **nicht gleichrangig**, und das gehört
festgehalten: Der erste war eine **Korrektur** — die neue Kette hatte
recht, die alte unrecht, dreifach belegt. Der zweite ist eine **fachliche
Änderung** — beide Zustände sind vertretbar, der Nutzer hat einen gewählt.
Wer später fragt, warum das Ergebnis von `run1` abweicht, bekommt zwei
verschiedene Antworten, und nur die erste ist ein Fehlerbefund.

Die Ampel bleibt unverändert in Kraft; nur ihr Bezugspunkt wandert. **Ab
jetzt gilt wieder: jede Abweichung von der Referenz ist ein Fehler** —
diesmal von `fb57c41d…`. Die Zeilen in `abweichungen.tsv` sind kein
offener Posten mehr, sondern der dokumentierte Grund für die Wechsel.

Was das **nicht** aufhebt: `output/…_run1.tif` bleibt unangetastet und
behält seine Prüfsumme. Es ist der einzige erhaltene Zeuge dafür, was die
alte Kette gerechnet hat, und nach Regel 8 muss der Rückweg offen
bleiben.

#### Zwei Lücken, die W3.2 beim Implementieren schließen musste

Die Ampel war als Text gemeint und ist jetzt Code. Dabei ist
herausgekommen, dass sie an zwei Stellen nicht entscheidbar war.

**Der Nenner.** „≤ 0,01 % der gesetzten Pixel" — gesetzt *wo*? W2.4 hatte
gegen die Gesamtzellzahl 336 038 001 gerechnet und kam für
`geography_water_bodies` auf 0,16 %; gegen die gesetzten Pixel des
**Referenzbands** sind es **27,58 %**. Ein Faktor 170 zwischen zwei
Lesarten desselben Satzes. **Verbindlich ist ab jetzt: gesetzte Pixel des
Referenzbands aus `run1`.** `pipeline/validate.py` führt die Zahl gegen
die Gesamtzellzahl als Kontrollwert mit und druckt sie, schreibt aber den
Registerwert nach dieser Definition.

**Die Referenzbänder.** Die Ampeltabelle hat zwei Spalten, für Bänder 1–26
und 27–36. Für 37 und 38 gibt es keinen grünen oder gelben Korridor —
sie stehen in keiner Spalte. Zusammen mit dem Satz oben („alle 38 Bänder
müssen bitgleich sein, ohne Sonderfall") heißt das: **Bei 37 und 38 ist
jede Abweichung Rot, unabhängig von ihrer Größe.** So implementiert; in
der Praxis bisher nicht ausgelöst, weil beide bitgleich sind.

**Bestätigt hat sich dagegen die Behauptung von oben**, die dritte
Kennzahl sei die aussagekräftigste. Über alle neun abweichenden Bänder
war die **größte zusammenhängende Fläche** die bindende Schranke — die
Nennerfrage mit ihrem Faktor 170 hat **keine einzige** Ampelfarbe
verändert. Ein verstreutes Prozent und ein zusammenhängendes Prozent sind
verschiedene Dinge, und die Ampel misst das richtige.

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

**Zu `schwerpunkt_bundesland` ein Vorbehalt aus der ersten Befüllung:**
Die Spalte nennt für alle neun Zeilen Vorarlberg — richtig, aber ohne
Kontext irreführend. **487 877 der 543 106 abweichenden Zellen von Band 26
(89,83 %) liegen außerhalb aller neun Bundesländer**, weil das
Rasterfenster über die Staatsgrenze in den Bodensee hinausreicht. Nur
55 229 Zellen (rund 35 km²) fallen auf österreichisches Gebiet, und die
liegen tatsächlich **ausschließlich** in Vorarlberg — null in den anderen
acht. Die Spalte beantwortet „wo in Österreich am meisten", nicht „wo
überhaupt"; wer sie liest, muss das wissen.

**Ein Nenner, der nicht als Vorbehalt taugt:** Band 26 trägt das Attribut
`clipped_to_austria: false`, und das Rasterfenster reicht mit rund 13 km
Marge nach Bayern, Slowenien, Tschechien, Ungarn und in die Schweiz. Schon
`run1` führte dort **202 736** Wasserzellen — echtes ausländisches Wasser,
das mit der Bbox-Lücke nichts zu tun hat. Wer den Anteil „außerhalb
Österreichs" über **alle gesetzten** Zellen bildet statt über die
abweichenden, misst deshalb etwas ganz anderes (27,49 % statt 89,83 %).
Beide Zahlen sind richtig, beide beschreiben verschiedene Mengen — und
nur die zweite sagt etwas über die Korrektur aus.

## 7. Wellen und Pakete

Zwischen den Wellen wird synchronisiert, innerhalb einer Welle nicht.

| Welle | Thema | Pakete | Parallel? |
|---|---|---|---|
| 0 | Schnittstellen | 3 | nein — nacheinander |
| 1 | Breite Arbeit | 18 | ja — gleichzeitig |
| 2 | Layer | 3 | ja — gleichzeitig |
| 3 | Finalisierung | 2 | nein — nacheinander |
| 4 | Prüfung | 4 | Vorfeld zuerst, dann drei gleichzeitig |
| 5 | Beweis | 7 | Vorfeld in sechs Stufen, dann der Lauf |
| 6 | Aufräumen und Abschluss | 7 | nein — nacheinander, weil nichts kollidiert und nichts sich beschleunigen lässt |
| 7 | Layer-Struktur v4 | 2 | ja — drei Bahnen im Produzentenpaket und das Dashboard gleichzeitig; siehe den Nachtrag zum Neuzuschnitt |

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
| W4.3 | 4 | Prüfung | Tests verdrahten **und Vertragsschluss** | `tests/**`; **`docs/rewrite/abweichungen.tsv`** (von W3.2 übernommen, dort erledigt) und **`docs/HANDOFF.md`** (Punkt 9) — **nicht mehr `Makefile`**, das `test`-Ziel zieht W4.P0 vor | W4.P0 | `make test` läuft die acht vorhandenen Tests plus die neuen Vertragstests; grün. Dazu die Umsetzung der Nutzerentscheidung zu Punkt 33: `ursache`-Spalte gefüllt, jede Sollwertbehauptung auf die neue Referenz gezogen. |
| W5.P0 | 5 | Beweis | Vorfeld des Beweislaufs | `Makefile` (nur das `all`-Ziel); `docs/RUN1_VERGLEICH.md` (nur ein datierter Nachtrag) | Welle 4 | `make -n` für jedes bestehende Ziel byte-identisch; `make all` läuft nachweislich die **neue** Kette. Nach Regel 9 (§13.10). **Gefunden und behoben: `all: prep widmung-v2` rief die alte Kette auf** — Welle 5 hätte den Vorgänger bewiesen und den Umbau nie berührt. |
| W5.P1 | 5 | Beweis | Die letzte `output/`-Abhängigkeit | `pipeline/layers/geo.py`; `make/layers/geo.mk`; `make/layers/osm.mk` | W5.P0 | Kein Modul unter `pipeline/` liest mehr unbedingt aus `output/`. Nachweis über einen Lauf mit **leerem** Quellverzeichnis: kein Rückfall, Verzeichnis bleibt leer, alle 17 Layer pixelgleich. Die Layer-Reihenfolge **hig → osm → geo** ist im Make-Graphen verdrahtet statt alphabetisch. Behebt Punkt 42, der W2.4 gehört hätte. |
| W5.P2 | 5 | Beweis | Adresslose Großflächen entfallen | `windkraft/calc/hig_detection.py`; `pipeline/layers/hig.py`; `tests/test_hig_addressless_candidates.py` (neu); `pipeline/validate.py` und `tests/test_referenz_tif.py` (nur das Hash-Literal); `docs/rewrite/abweichungen.tsv`; `docs/HANDOFF.md` | W5.P1 | Umsetzung der Nutzerentscheidung zu Punkt 34 (3). Ein Kandidat über `HIG_MAX_FOOTPRINT_M2` **ohne eigene BEV-Adresse** entfällt; mit Adresse bleibt die Zentroidscheibe unverändert. **Kein anderer Schwellwert wird angefasst.** Nachzuweisen sind: die Zahl der entfallenen Kandidaten, die pixelweise geänderten Checkpoints, die geänderten Bänder gegen die Zwischenreferenz, die Flächenwirkung auf `haeuser_im_gruenen_streusiedlung` **und** ob eine Hülle zerfällt. |
| W5.P3 | 5 | Beweis | Die vier Nachzügler aus W5.P2 | `docs/rewrite/abweichungen.tsv`; `tests/test_referenz_tif.py`; `docs/HANDOFF.md`; `README.md` | W5.P2 | Vier Stellen, die seit `f592e75` etwas Falsches behaupten: der Ursache-Text im Register (drei Gruppen statt einer), der gegatete Vertragstest (18 Bänder statt neun), der HANDOFF-Abschnitt gleichen Inhalts, und ein veralteter Hash im README. Dazu die Dokumentation von Punkt 34 (1) und (2). |
| W5.P4 | 5 | Beweis | Das Register kennt nur eine Ursache | `docs/rewrite/abweichungen.tsv` (nur `ampel`); `README.md` (Zeile 191) | W5.P3 | Schlüsselwort „angenommen"/„entschieden" repariert, `validate.py` real gelaufen, `ampel` zeigt den tatsächlichen Zustand; README-Zahl auf 18/zwei Ursachen nachgezogen; zweiter gegateter Langläufer real gelaufen. **Der Wirkungspfad-Wächter selbst blieb fest auf Wasser verdrahtet** — Zuschnitt größer als ein Nachmittag, an W5.P5 zurückgegeben. |
| W5.P5 | 5 | Beweis | Wirkungspfad-Wächter generalisieren | `windkraft/calc/band_manifest.py`; `pipeline/validate.py` | W5.P4 | Der Wächter aus §13.9 prüft jede Zeile gegen den Wirkungspfad **ihrer eigenen** `ursache`, nicht mehr fest gegen `geography_water_bodies_wirkungspfad`. Dafür muss das Manifest einen Wirkungspfad für die DKM-Ursache (Punkt 34) hergeben — dazu erst die fehlende `OFFICIAL_COVER_LAYERS`-Kante (HIG-Zwischenschicht in `pipeline/layers/osm.py`) im Manifest-Graphen nachbilden. Abnahme: Bänder 5, 7–13, 27 werden bei akzeptierter Ursache korrekt grün/akzeptiert, kein anderer Wirkungspfad ändert sich. **So nicht eingetroffen, und die Abnahmebedingung war der Fehler, nicht das Paket:** „akzeptiert" setzt das Schlüsselwort „angenommen" voraus, die Punkt-34-Texte sagen „entschieden" (Punkt 46), und die Bänder 7, 8, 9 überschreiten das Budget der Sache nach. Gemessen: 5 gelb, 7/8/9 rot, 10 grün, 11–13 gelb, 27 gelb. Der zweite Halbsatz — kein anderer Wirkungspfad ändert sich — traf zu. |
| W5.1 | 5 | Beweis | Beweislauf aus Rohdaten | — (nur Ausführung) | W5.P5 | `rm -rf build && make all` erzeugt das TIF vollständig neu; Abnahmebedingung erfüllt; Laufzeiten je Stufe protokolliert. |

### Welle 6 — Aufräumen und Abschluss

**Beauftragt am 08.09.2026.** Die Welle steht hier, weil das Zielbild aus §3
seit Beginn ein aufgeräumtes Repo verlangt und §7 bis eben mit W5.1
endete — es gab kein Paket, das dorthin führt, und keine
Abnahmebedingung für „aufgeräumt". Diese Lücke ist genau die Sorte, die
Regel 7 (§13.8) finden soll: die Paketliste stimmte mit sich selbst
überein, nicht mit dem Ziel.

Grundlage ist eine Bestandsaufnahme vom 08.09.2026 (Protokoll in
`FORTSCHRITT.md`). Ihr wichtigster Befund widerlegt eine Annahme, die ich
bis dahin für gesichert hielt: **`scripts/widmung_v2/` ist nicht tot.** Die
fünf Skripte sind das `make`-Standardziel (`Makefile:18`,
`.DEFAULT_GOAL := widmung-v2`) und werden von `tests/test_contract.py`
direkt importiert. Der Beweislauf hat gezeigt, dass die *neue* Kette aus
Rohdaten allein läuft — er sagt nichts darüber, ob die *alte* noch
gebraucht wird. Das ist eine Architekturentscheidung, kein Aufräumen, und
sie gehört dem Nutzer.

### Die Entscheidungen des Nutzers, 08.09.2026

Ich hatte acht Pakete und fünf Entscheidungen vorgelegt. Der Nutzer hat
den Zuschnitt in drei Fragen auf die Hälfte gekürzt, und jede der drei war
berechtigt.

**„Wieso dauert Aufräumen 5 h?"** — Zwei Drittel meiner Schätzung waren
Bürokratie. Die Wellen-Disziplin (ein Pfad ein Besitzer, Abnahme je Paket)
gibt es, damit **parallel** arbeitende Agenten kollidieren können und ein
Umbau, der Zahlen ändert, nicht unbemerkt driftet. Hier arbeitet niemand
parallel, und **kein einziger Zahlenwert ändert sich** — alles, was
entfernt wird, hat nachweislich keinen Leser. Sechsmal dieselbe Abnahme zu
fahren ist Ritual, kein Nachweis. Dazu hatte ich den vollen Beweislauf
angesetzt (75 min), obwohl die Vorverarbeitung von keiner Änderung berührt
wird: `rm -rf build/layers out && make all` unter Wiederverwendung von
`build/prep/` prüft dasselbe in **9 Minuten**. Und in derselben Datei, in
der mein Korrekturfaktor von −49 % steht, hatte ich eine ungerechnete Zahl
hingeschrieben.

**„Aber hast du nicht gerade den Rewrite vollendet?"** — Ja. Was übrig
ist, ist Löschen, und Löschen dauert Sekunden. Was dauert, ist Beweisen —
aber eben einmal, nicht sechsmal.

**„Für was muss `run1` erhalten bleiben?"** — Mein „dringend" war
überzogen. Das Register dokumentiert einen **abgeschlossenen** Übergang,
den der Nutzer selbst abgenommen hat. Die Auflösung liegt in seinem
eigenen Grundsatz: *nicht Platz sparen, sondern Struktur.* `run1` muss
nicht gelöscht werden, um `output/` aus dem Baum zu bekommen — es muss nur
**heraus**. Es liegt seither in `~/Documents/master_windkraft/archiv/`,
zusammen mit den alten Caches, die der Nutzer erhalten wissen wollte.
Damit bleibt alles nachmessbar und die Struktur ist trotzdem sauber.

**Entschieden:**

| | |
|---|---|
| `scripts/widmung_v2/` | **entfernt** — nicht umgezogen. Die Historie behält den Quelltext; die Zitatkommentare nennen künftig Commit `f1d00f7` statt eines Pfades. |
| `run1.tif` und die alten Caches | **ins Archiv neben dem Repo**, nicht gelöscht |
| `output/` | **aus dem Baum**, restlos |
| `main` | bekommt die Arbeit, als letzter Schritt |
| Doku | **hinten nach** — eigenes Paket, blockiert nichts |

**Drei Namen, vom Nutzer angestoßen.** Er hat drei Verzeichnisnamen als
schlecht bezeichnet, und alle drei zu Recht:

- **`windkraft/`** sagt in einem Windkraft-Repo genau so viel wie
  `stuff/`. Der richtige Name lag längst eine Ebene tiefer: `windkraft/calc/`.
  → **`calc/`**, innere Ebene aufgelöst.
- **`build/`** verspricht das Falsche. Da wird nichts kompiliert, da liegen
  abgeleitete Daten — und der Name liest sich wie „gefahrlos wegwerfbar",
  während darin **66 Minuten Kataster-Vorverarbeitung** stecken. Dass in
  diesem Plan ein eigener Satz „`build/` bleibt" mit Begründung nötig war,
  ist der Beweis. → **`derived/`**, in der Kette `data/ → derived/ → out/`.
- **`verify/`** verifiziert nichts. Darin liegen `dashboard.py` und
  `gemeinden.py` — sie **erzeugen zwei der vier Endprodukte**. Der Name
  stammt aus der Zeit, als das Dashboard zum Draufschauen gedacht war;
  inzwischen ist es Liefergegenstand. Daneben prüft `validate.py`
  tatsächlich. Zwei fast gleichbedeutende Wörter für zwei völlig
  verschiedene Aufgaben. → **`export/`**, `validate.py` bleibt.

Danach liest sich die Kette von selbst:
`prep/ → layers/ → finalize.py → validate.py → export/`.

| Paket | Welle | Gruppe | Titel | Besitzt | Braucht | Abnahme |
|---|---|---|---|---|---|---|
| W6.1 | 6 | Abschluss | Die alte Kette entfällt | löschen: `scripts/**` (komplett), `windkraft/util/` · herausbewegen: `output/**` → `~/Documents/master_windkraft/archiv/` · ändern: `Makefile` (`.DEFAULT_GOAL`, die fünf `widmung-v2-*`-Ziele), `pipeline/layers/geo.py`, `pipeline/layers/osm.py`, `pipeline/contract.py`, `pipeline/validate.py`, `pipeline/finalize.py` (nur Zitatkommentare), `tests/test_contract.py`, `tests/test_referenz_tif.py`, `docs/analysis/streusiedlung_knee.py`, `.gitignore` | W5.1 | Ein Paket statt sechs, weil nichts parallel läuft und keine Zahl sich ändert. **Sicherheitsnetz zuerst:** `output/` wird verschoben, nicht gelöscht — ein Umbenennen auf derselben Platte, sofort und umkehrbar. Der Rückfall auf `output/` in den Layer-Modulen wird **lauter Abbruch** statt stillem Nichts. `run1` bleibt über `ABSCHICHTUNG_RUN1` erreichbar — dasselbe Muster, das `test_distance_engine_equivalence.py` für `ABSCHICHTUNG_ALTREPO` benutzt —, damit `validate.py` und der 18-Bänder-Test wieder laufen, wenn jemand die Datei aus dem Archiv zurückholt. Abnahme: `rm -rf build/layers out && make all` (**9 min**, `build/prep/` unberührt) → TIF bitgleich `fb57c41d…232c30`, alle 38 Bänder, vier Produkte, Tests grün mit **benannter Begründung je Testdifferenz**, keine Zeichenkette `output/` mehr unter `pipeline/`, `windkraft/`, `tests/`, `make/`, und `make` ohne Argument baut die neue Kette. |
| W6.2 | 6 | Abschluss | Drei Namen, die die Struktur erklären | `windkraft/` → `calc/`; `build/` → `derived/`; `pipeline/verify/` → `pipeline/export/`; dazu jeder Importpfad im Repo, `pipeline/contract.py`, `pyproject.toml`, `.gitignore`, `make/**`, `Makefile` | W6.1 | Reines Umbenennen, kein Zahlenwert ändert sich. Nach W6.1, nicht davor — sonst würden Dateien umbenannt, die zwei Minuten später gelöscht werden, und der Diff wäre unlesbar. Der Pfadvertrag aus W0.2 macht `build/` → `derived/` zu einer Zeile in `contract.py`; teuer ist nur `windkraft/` → `calc/`, weil es jeden Import berührt. Abnahme wie W6.1, plus: kein Vorkommen von `windkraft.`, `build/` oder `verify` mehr als Pfad oder Modulname, außer in erklärten historischen Erwähnungen. |
| W6.3 | 6 | Abschluss | README auf den neuen Baum, dann Zusammenführung nach `main` | `README.md`, `main` | W6.2 | Punkt 51. Ein frischer Klon von `main` plus `data/` läuft `make` ohne Argument bis zu den vier Produkten durch. **Das ist die Abnahmebedingung für das Zielbild aus §3** — und die erste, die es je gab. **Die Zusammenführung gelang (`65b97ac`, Fast-Forward), der Klontest nicht** — er übersprang nichts und richtete dabei Schaden am geteilten `derived/prep/` an (Punkt 55). Die Abnahme wanderte deshalb nach W6.4. |
| W6.4 | 6 | Abschluss | Der Fingerabdruck wird ortsunabhängig | `pipeline/fingerprint.py`; die zehn Prep-Einstiegsmodule unter `pipeline/prep/` | W6.3 | Punkt 53 und Punkt 45. Schlüssel relativ zu `contract.ROOT` statt absolut; jedes Prep-Modul nimmt seine eigene Quelldatei in den Abdruck auf. Abnahme: voller `make all` mit stehengelassenem `derived/prep/` → TIF `fb57c41d…232c30` (**heilt zugleich Punkt 55, weil ein abweichender Wert bewiese, dass der Rückschrieb aus W6.3 den Zwischenstand verändert hat**), zweiter Lauf überspringt alle zehn Stufen, Klontest mit echter Kopie statt Symlink. **Eingetroffen bis auf den Klontest** — siehe den Nachtrag §13.11. |
| W6.6 | 6 | Abschluss | Drei Einzeiler, die Welle 6 selbst hinterlassen hat | `pipeline/fingerprint.py`; die zehn Prep-Einstiegsmodule; `tests/test_contract.py`; die Stelle, an der die Test-Untergrenze sitzt (`tests/conftest.py` oder `make/`) | W6.4 | Punkt 56, 57 und 54. **Die Nummer sagt, wann das Paket geschnitten wurde, nicht wann es läuft** — es läuft vor W6.5, damit die Doku den Endzustand beschreibt. (1) Der Fingerabdruck nimmt versionierte **Quelldateien über `sha256`** statt über Größe und Zeitstempel auf; Rohdaten bleiben bei `_stat()`. (2) Die `skipif`-Bedingung von `test_layer_names_match_existing_checkpoints` zeigt auf `derived/layers/` statt auf das archivierte `output/…/distance_layers`. (3) `make test` bekommt eine **Untergrenze für die Zahl gesammelter Tests**. Abnahme: voller `make all` → TIF `fb57c41d…232c30` (**Halt bei Abweichung**), zweiter Lauf überspringt alle zehn Stufen, **Klontest überspringt jetzt ebenfalls** (das ist der Zweck von Punkt 56 und die Abnahme, die W6.4 schuldig geblieben ist), `make test` meldet **214 + 3** statt 213 + 4, und die Untergrenze wird **dynamisch gegengeprüft** — einmal so verstellt, dass sie auslöst, dann zurück. **Vollständig eingetroffen** (`ffca628`): Klontest **8:38 statt 62:49**, `sha256` exakt, `make test` 214 + 3. Eine der zehn Stufen übersprang nicht — `prep-natur` liest `config.json`, das außerhalb der Erkennung „`.py` unter `pipeline`/`calc`/`tools`" liegt. Punkt 60. |
| W6.7 | 6 | Abschluss | Der Kartenviewer über OSM | neu: `pipeline/export/viewer.py`; ändern: `pipeline/export/dashboard.py`, `pipeline/contract.py`, `make/`, `tests/` | W6.6 | **Vom Nutzer am 08.09.2026 verlangt:** unter `out/dashboard/` soll nicht die Übersichtstabelle liegen, sondern „die simple Visualisierung der Layer in einer Website über einem OSM-Layer". **Rollenteilung, als Annahme gesetzt und umkehrbar:** Der Viewer übernimmt `out/dashboard/index.html`, die Prüfstufe `dashboard.py` behält `report.json`. Damit bleibt `out/dashboard/` das vierte vertraglich zugesagte Endprodukt und die bestehenden Tests gelten weiter. **Das Verfahren ist nicht neu, sondern zurückgeholt:** Das Vorgängerprojekt hat es zwanzigmal so gebaut (`windkraft/viz/raster_overlay.py`, Leaflet 1.9.4, ein PNG je Band als `L.imageOverlay` über OSM), und dieses Repo hatte das Skript als `scripts/webmap/build_layer_viewer.py`, gelöscht in `9c64a85b`. Je Band: Reprojektion nach EPSG:3857, Herunterskalieren auf `--max-size` (Default 3000), transparentes PNG. **34 der 38 Bänder sind binär, vier sind 0–100 %** (`available_blur_sigma_*`) und brauchen eine Farbskala — die Unterscheidung kommt aus `band_value_type()`, nicht aus einer Liste im Code. Abnahme: kein Bandname im Quelltext (Härtetest gegen ein Fremdmanifest wie in W4.1), `make all` erzeugt den Viewer mit, die Seite zeigt alle 38 Bänder über OSM, und die Gesamtgröße von `out/dashboard/` wird **gemessen und berichtet**, nicht geschätzt. |
| W6.5 | 6 | Doku | Die Doku beschreibt den neuen Baum | `docs/rohdaten.md`; `docs/dataflow/**`; `docs/rewrite/README.md`; `docs/rewrite/packages.tsv`/`.json`; `docs/rewrite/UMSETZUNG.md`; `docs/FOLLOWUPS.md`; `docs/widmung_v2_provenance.md`; `docs/widmung_v2.md` | W6.6 | **Vom Nutzer bewusst nach hinten gestellt** („Struktur und Doku dann hinten nach") — es blockiert nichts und ist Prosa, kein Aufräumen. `docs/rohdaten.md` behauptet in Zeile 365–420, `data/widmung/` existiere nicht; es existiert seit W0.1 mit neun Domänen. `docs/dataflow/` bildet 417-mal `scripts/` ab und **kein einziges Mal** `pipeline/`, wird aber von `docs/rewrite/README.md` als „Faktengrundlage" zitiert — nach W6.1 beschreibt es einen Baum, den es nicht mehr gibt. `packages.tsv` kennt 30 Pakete. Abnahme: keine Doku behauptet mehr etwas, das die laufende Kette widerlegt; jede gelöschte Datei hat einen benannten Ersatz oder einen niedergeschriebenen Grund. **`docs/rohdaten.md` wird korrigiert, nicht gelöscht** — es ist die einzige Provenienz- und Lizenzangabe der Rohdaten im Repo. **Entschieden für `docs/dataflow/`: datiert einfrieren, nicht neu erzeugen und nicht löschen.** Es ist ein aus dem alten Code erzeugter Befund über die alte Kette — dieselbe Gattung wie `docs/RUN1_VERGLEICH.md`, das nach Punkt 3 ausdrücklich eingefroren bleibt. Gefährlich ist nicht sein Inhalt, sondern sein **Etikett**: `docs/rewrite/README.md` zitiert es als „Faktengrundlage" für ein Repo, das es nicht mehr beschreibt. Also bekommt das Verzeichnis einen datierten Kopf („beschreibt die Kette vor dem Umbau, Stand `f1d00f7`") und das Zitat im README wird entsprechend umgeschrieben. Eine Neuerzeugung gegen `pipeline/` bleibt möglich und wird als eigener Registerpunkt eröffnet — sie ist ein Paket für sich, nicht ein Nebensatz in einem Doku-Paket. |

### Welle 7 — Layer-Struktur v4

**Beauftragt am 09.09.2026, und nicht von hier.** Der Auftrag kam über eine
zweite Claude-Sitzung (`mwk-fable`) im Namen des Nutzers, mit eigenem
Umsetzungsplan, eigenen Abnahmekriterien und eigener Paketbenennung A, B,
C. Er steht trotzdem in diesem Plan, weil zwei der drei Pakete in diesem
Repo arbeiten — und weil die Ergänzung zu Regel 7 (§13.11) genau das
verlangt: **ein Paket bekommt seine Nummer im Plan zuerst.** Die Zuordnung
ist **A = W7.1, B = W7.2, C = W7.3**; Meldungen aus der anderen Sitzung
kommen unter den Buchstaben herein und werden hier unter der Nummer
gebucht.

**Diese Welle setzt Regel 4 außer Kraft, und das ist ihr Zweck.** Regel 4
— „kein Paket ändert Zahlen" — galt für einen Umbau, der beweisen musste,
dass er nichts verändert. Welle 7 ist kein Umbau, sondern eine fachliche
Änderung: Band 38 wird gegen Band 37 zugeschnitten, sechs Bänder kommen
hinzu. Die Regel wird deshalb **begrenzt, nicht gestrichen** (Regel 8,
§13.9): Sie gilt weiter für alles, was nicht ausdrücklich in der
Abnahmebedingung eines Welle-7-Pakets als geänderte Zahl benannt ist. Wer
hier eine Abweichung findet, die in keiner Abnahme steht, hat einen Fehler
gefunden, keine Absicht.

**Der Referenz-Hash fällt, zweimal.** `fb57c41dca0642225a8115e3ed95297ede47b56d56c00fdddf8caa445e232c30`
(124 597 421 Bytes, 38 Bänder, Manifest 2.1.0) war vom 07. bis 09.09.2026
der Anker, an dem die Wellen 0 bis 6 nachgewiesen haben, dass sie nichts
verändern. W7.1 ändert Pixel, W7.2 die Bandzahl — der Wert **muss** fallen,
zweimal, und jeder neue Wert wird in der Commit-Message seines Pakets
**neben dem abgelösten** genannt. Die auftraggebende Seite hat bestätigt,
dass außerhalb dieses Repos nichts automatisch dagegen prüft: im Dashboard
vergleicht `verify_raster()` nur `band_count`, der Hash steht dort als
Dokumentation und wird in W7.3 nachgezogen. Der alte Wert bleibt hier
stehen, mit Datum und Grund. **Was damit endet, ist nicht der Nachweis,
sondern seine Bezugsgröße** — die Kette „vier Produkte reproduzierbar" wird
gegen den jeweils neuen Wert neu abgenommen, nicht ersatzlos aufgegeben.

**Aus vier Endprodukten werden fünf.** `out/wka_bestand_punkte.geojson`
kommt in W7.1 hinzu und ist ab dann vertraglich zugesagt wie die anderen
vier. Das Zielbild in §3 nennt vier; es wird mit W7.1 auf fünf gezogen. Eine
Produktliste, die nach dem Paket noch vier sagt, ist falsch, nicht bloß
veraltet.

**Eine Frage war vor Beginn offen und ist beantwortet.** Der fremde Plan
beschreibt für das neue Band 39 eine Einfügestelle *mitten* in
`contract.LAYER_NAMES`, zwischen `haeuser_im_gruenen_noe_pdf` und
`haeuser_im_gruenen` — während dieselbe Auftragslage verlangt, dass die
bestehenden 38 Bänder Name und Index behalten. Beides zusammen geht nicht: Eine Einfügung an dieser
Stelle verschöbe alles Nachfolgende.

**Nachtrag aus der Umsetzung, weil beide Seiten es sich zu einfach gemacht
haben.** Die auftraggebende Seite schrieb, `LAYER_NAMES` **sei** die
Bandreihenfolge, 1-basiert; ich habe das ungeprüft in diesen Plan
übernommen. Es stimmt nicht. `LAYER_NAMES` ist die Registry der
**Checkpoints** unter `derived/layers/` und zählt 33 Einträge, nicht 38 —
zehn der 38 Bänder (die drei Kategorie-Aggregate, `all`/`raw`/`cleaned` und
die vier Unschärfebänder) sind reine Rechenergebnisse und haben nie einen
Checkpoint gehabt. Die Bandreihenfolge entsteht erst in `finalize.py`: 26
Bedingungsbänder, die berechneten 27–36, dann eine Liste **nachlaufender**
Bänder, über die heute schon 37 und 38 durchgereicht werden. Genau dort
hängen die sechs neuen an. **Die Entscheidung „anhängen statt einfügen"
bleibt richtig — die Begründung, die beide Seiten dafür genannt haben, war
es nicht.** Die auftraggebende Seite hat die
Dokumentstelle als veraltet zurückgezogen; es wird **angehängt**, 39 bis 44
in der Reihenfolge `haeuser_im_gruenen_source`,
`general_buildings_roh_osm`, `general_buildings_roh_dkm`, `sources_human`,
`sources_nature`, `sources_geography`. Braucht ein angehängtes Band Eingänge
aus einem früheren Builder, wird es **dort** gerechnet und unter dem
angehängten Namen als Checkpoint geschrieben. Maßgeblich ist der Code, nicht
das Dokument — das ist derselbe Vorrang wie in §13.11.

**Die Testzahl im fremden Plan ist eine Welle alt.** Er verlangt „alle 217+
Tests grün"; 217 war der Stand nach W6.6 (214 + 3). Seit W6.7 sammelt
`make test` **226** (223 + 3). Die Untergrenze in `tests/conftest.py`
(`MIN_COLLECTED_TESTS = 210`) bricht dadurch nicht — sie ist eine
Untergrenze —, wird in W7.2 aber nachgezogen, sonst schützt sie nach dem
Zuwachs weniger als vorher.

### Neuzuschnitt am selben Tag — zwei Stunden statt sechs bis acht

**Wenige Minuten nach dem Start von W7.1 kam über dieselbe Sitzung eine
Änderung der Arbeitsweise:** Ziel ist Fertigstellung in **rund zwei Stunden
Wanduhr**. A und B werden **ein** Produzentenpaket mit **einem** Lauf, **einem**
Commit und **einem** neuen Referenz-Hash; im Produzenten arbeiten drei
Bahnen nach Dateien getrennt gleichzeitig; das Dashboard beginnt **sofort**
gegen einen selbstgebauten 2.2.0-Stub, statt auf das echte Manifest zu
warten. W7.1 wurde dafür nach wenigen Minuten angehalten. **Meine Angabe
dazu war falsch:** Ich hatte notiert, der Agent sei „noch beim Lesen"
gewesen — er hatte tatsächlich bereits `pipeline/layers/geo.py` und
`calc/band_manifest.py` im Arbeitsbaum geändert. Nichts davon war
committet; Bahn 1 hat beides vor dem Start verworfen und den Zweig neu
angelegt. Verloren ging nichts, aber die Aussage stimmte nicht, und die
Lehre ist banal: **abgebrochen heißt nicht folgenlos** — der Zustand des
Arbeitsbaums wird nachgesehen, nicht aus der Abbruchmeldung geschlossen.

**Was der Zusammenschluss kostet, gehört genannt.** Der Pixelbefund (Hüllen
zuschneiden) und die Schemaänderung (sechs Bänder) landen damit in
**demselben** Hash-Schritt. Zeigt das neue TIF eine unerwartete
Bandabweichung, lässt sie sich nicht mehr **von der Struktur her** einer der
beiden Ursachen zuordnen — genau die Trennschärfe, für die dieses Repo in
den Wellen 3 bis 5 teuer bezahlt hat. Der Ausgleich kostet keinen zweiten
Lauf: Die integrierende Bahn nimmt den **bandweisen** Vergleich gegen das
TIF von `b8af5fd` auf und ordnet **jedes** geänderte Band in der
Commit-Message entweder dem Zuschnitt oder dem Schema zu. Die Zuordnung
wandert damit aus dem Commit-Graphen in den Commit-Text: schwächer, aber
nicht verloren. **Das ist eine Abweichung nach Regel 8** — erklärt,
mitgeführt, umkehrbar.

**Regel 9, angewandt: die fremde Aufteilung war nach Themen geschnitten,
und Themen kollidieren in Dateien.** Zwei Überschneidungen sind vor dem
Start aufgelöst, und zwar **nach Datei, nicht nach Begriff**:

- Der Schema-String `clean-38-…` steht in `pipeline/finalize.py`,
  `pipeline/layers/geo.py`, `calc/band_manifest.py` und in Tests. Er gehört
  nicht *einer* Bahn — ihn ändert, **wem die Datei gehört**.
- `pipeline/contract.py` trägt `LAYER_NAMES` **und** `PRODUCTS`, die im
  fremden Schnitt in zwei verschiedenen Bahnen lagen. Die Datei bekommt
  **einen** Besitzer, Bahn 1, samt der beiden neuen Produkteinträge.

| Bahn | Besitzt |
|---|---|
| **1 — Builder** | `pipeline/layers/geo.py` (Zuschnitt, `hig_family` als Band 39, die drei `sources_*`), `pipeline/layers/osm.py` (Bänder 40/41), `pipeline/contract.py` (`LAYER_NAMES` **und** `PRODUCTS`), `pipeline/finalize.py` (`BANDS`, Schema-String an dieser Stelle) |
| **2 — Metadaten** | `calc/band_manifest.py` (Felder, Familien, `stufe_order`, Beschreibungen 39–44, Schema-String dort), `calc/viz/band_metadata.py`, `pipeline/validate.py` (die hartkodierten Indexbereiche), `tests/test_band_manifest.py`, `tests/test_band_metadata.py`, `tests/test_export_dashboard.py`, `tests/test_export_viewer.py`, `tests/conftest.py`, `docs/HANDOFF.md` |
| **3 — Exporte** | neu `pipeline/export/wka_bestand.py`, neu `pipeline/export/layer_doc.py`, die zugehörigen neuen Testdateien, `make/export/**` |
| **4 — Dashboard** | fremdes Repo, siehe W7.3 — läuft von Anfang an mit |

**Zwei Regeln für das Zeitfenster, in dem drei Bahnen denselben Baum
bearbeiten.** Erstens: **Niemand fährt `make` oder die volle Suite**,
solange nicht alle drei fertig sind — das Repo ist in diesem Fenster
absichtlich widersprüchlich, und ein Test, der die Datei einer fremden Bahn
nennt, ist **erwartetes Verhalten und wird gemeldet, nicht repariert**.
Zweitens: **`schnittstelle-manifest-2.2.md` ist verbindlich für beide
Seiten.** Das Dashboard entwickelt gegen ein Manifest, das es noch nicht
gibt — jede Abweichung des Produzenten von dieser Schnittstelle wird
**gemeldet, nie stillschweigend übernommen**, sonst arbeitet eine Bahn
zwei Stunden gegen einen Vertrag, den die andere längst verlassen hat.

`layer_doc.py` liegt **nicht** auf dem kritischen Pfad: verzögert es, wird
`LAYER.md` aus der Vorlage übernommen und der Generator als Registerpunkt
notiert.

| Paket | Welle | Gruppe | Titel | Besitzt | Braucht | Abnahme |
|---|---|---|---|---|---|---|
| W7.1 | 7 | Struktur v4 | **Der Produzent in einem Zug** — Zuschnitt, Punkte-Export, sechs Bänder, Manifest 2.2.0 (Besitz je Bahn: siehe die Tabelle im Neuzuschnitt) | neu: `pipeline/export/wka_bestand.py`, `tests/test_export_wka_bestand.py`, `make/export/wka_bestand.mk` · ändern: `pipeline/layers/geo.py` (nur `build_wka_bestand_hulls`), `calc/band_manifest.py` (nur die Beschreibung von Band 38), `pipeline/contract.py` (nur `PRODUCTS`), `docs/HANDOFF.md`, `tests/test_referenz_tif.py` und `pipeline/validate.py` (nur das Hash-Literal) | W6.7 | Wörtlich aus dem Auftrag: „Band 38 AND Band 37 = leer; jede Anlage mit `in_zone=false` liegt außerhalb Band 37; Anzahl Hüllen und Anlagen im Report." Dazu aus diesem Plan: Der Befund, den das Paket behebt, ist ein **Geometriefehler, kein Zählfehler** — `geo.py:556` prüft „in Zone" als Punktabfrage am Raster, die konvexe Hülle plus 200-m-Rand wird danach ohne `difference()` gegen `official_wind_zoning` rasterisiert (`geo.py:567-576`), sodass ein grenznaher Cluster in eine amtliche Zone hineinragen kann, obwohl jede einzelne Anlage außerhalb liegt. Lauf: `make layers finalize validate export`, kein voller `make all`. Zu berichten sind die drei Zählungen gegen die Referenz **1595 gesamt / 807 in Zone / 788 außerhalb** und der **neue Referenz-Hash neben dem alten**. |
| ~~W7.2~~ | 7 | Struktur v4 | ~~Sechs Bänder und Manifest 2.2.0~~ — **in W7.1 aufgegangen** (Neuzuschnitt oben). Die Zeile bleibt vollständig stehen, weil sie die Arbeit beschreibt, die W7.1 jetzt mitträgt — nach Regel 8 wird eine erklärte Abweichung mitgeführt, nicht gelöscht | `pipeline/contract.py` (`LAYER_NAMES`), `pipeline/finalize.py` (`BANDS`), `calc/band_manifest.py`, `calc/viz/band_metadata.py` (`CATEGORY_TOTALS`, Farben), `pipeline/layers/geo.py`, `pipeline/layers/osm.py`, `pipeline/validate.py` (die hartkodierten Indexbereiche in Zeile 44, 108–121, 473) · neu: `pipeline/export/layer_doc.py` → `out/LAYER.md`, Kopie `docs/layer.md` · Tests: `test_band_metadata.py`, `test_band_manifest.py`, `test_export_dashboard.py`, `test_export_viewer.py`, `conftest.py` · `docs/HANDOFF.md` | W7.1 | Wörtlich aus dem Auftrag: „44 Bänder, Manifest validiert, alle 217+ Tests grün, `LAYER.md` listet 44 Bänder." Dazu aus diesem Plan: **217 ist der Stand vor W6.7 — die Abnahme läuft gegen 226 gesammelte Tests**, und die Untergrenze in `conftest.py` wird mitgezogen. Die sechs Bänder entstehen aus bereits vorhandenen In-Memory-Arrays (`hig_family` liegt als lokale Variable in `geo.py:393` und wird heute nur gepuffert weiterverwendet), es wird **kein neuer Rohdatenzugriff** eröffnet. Der Schema-String `clean-38-…` trägt die Bandzahl im Namen und muss an allen vier Fundstellen mit — wer ihn stehen lässt, hat ein Manifest, das sich selbst widerspricht. **Zweiter neuer Referenz-Hash, wieder neben dem abgelösten.** |
| W7.3 | 7 | Struktur v4 | Das Dashboard baut den Baum aus dem Manifest — **ab 09.09.2026 nicht mehr hier.** Die zweite Sitzung führt es selbst aus und arbeitet dabei parallel zum Produzenten; diese Seite fasst `winddashboard/` **nicht** an und schuldet nur das Paar aus TIF, Manifest und Punktdatei. Die Abnahme unten bleibt stehen, weil sie beschreibt, wogegen unser Manifest sich bewähren muss | **Fremdes Repo** `~/Documents/master_windkraft/winddashboard`, Zweig `feat/manifest-integration` (`c69121c`): `src/lib/config/bands.ts`, `src/lib/config/legend.ts`, `src/lib/components/MapControlPanel.svelte`, `src/routes/methodik/+page.svelte`, `scripts/extract_band_geojson.py`, `scripts/extract_possible_zones.py`, neu `scripts/merge_turbine_attributes.py`, `PIPELINE.md`, die neue Punktdatei unter `geodata/` | W7.2 | Wörtlich aus dem Auftrag: „40 Layer im Baum, Reihenfolge wie v4, Bestandsanlagen außerhalb überlappen weder Band 37 noch die Vektor-Zonen sichtbar, keine neuen svelte-check-Fehler." Dazu aus diesem Plan: Das Paket arbeitet **außerhalb dieses Repos** — Regel 10 (Plandateien nach jedem Paket committen) betrifft nur diese Seite, und nichts unter `geodata/` wird gelöscht. Es ist zugleich die Gegenprobe auf W7.2: Die 16 Handeinträge entfallen ersatzlos, der Baum kommt aus `familie`/`stufe`/`dashboard_layer`. Fällt dabei ein Band durch, ist der Fehler im Manifest, nicht im Dashboard. |

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
   **Nachtrag nach dem zweiten Vorfall (W5.P4):** Diese Regel verbietet
   das *Bearbeiten* und schützt deshalb nicht vor `git add -A`. Was
   unversioniert im Arbeitsbaum liegt, sammelt ein fremdes Paket
   mit ein, ohne die Regel zu brechen. Deshalb gilt zusätzlich —
   **Regel 10: die beiden Plandateien werden nach jedem Paket
   committet**, von mir beauftragt und in einem eigenen Commit, der
   nichts anderes enthält. Ein sauberer Arbeitsbaum ist der mechanische
   Schutz, den eine Prosa-Regel nicht leisten kann. Pakete stagen
   ausschließlich mit namentlich genannten Pfaden, nie mit `-A`, `.`
   oder `commit -a`.

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
W2.P0, W2.4, dem später nachgezogenen W4.P0 (§13.10) sowie W5.P0 bis
W5.P5 sind es **39**, und `packages.tsv`/`packages.json` sind entsprechend
veraltet — dieselbe Baustelle wie Punkt 16.

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

**Die drei verlorenen Zeilen sind namentlich bekannt.** 128 028 gegen
128 025 — der Unterschied besteht aus genau zwei OSM-Objekten:

| `@id` | Objekt | Fehlende Zeilen |
|---|---|---:|
| 1156846 | **Bodensee**, `natural=water` / `water=lake`, MultiPolygon-Relation, ~531,35 km² | 1 |
| 1473483026 | `natural=shoal` — eine **Sandbank von 1448 m²**, Way, in Linien- und Flächenform exportiert | 2 |

Die Bounding Box der Sandbank liegt **vollständig innerhalb** der des
Bodensees: kein zweiter, andernorts liegender Fall, sondern ein
Sub-Feature derselben Stelle, vom selben Schnitt mitgerissen. Die
Zusammenhangsanalyse der 543 106 Zellen bestätigt es unabhängig — **fünf
Komponenten, davon eine mit 543 095 Zellen (99,998 %)** und vier Reste von
zusammen 11 Zellen.

**Damit ist die letzte offene Hälfte von Punkt 33 beantwortet: Nein,
weitere Gewässer sind nicht betroffen.** Die Frage, die einmal „wie viel
wissen wir nicht" hieß, endet bei zwei benannten OSM-Objekten.

**Der Zustand war bewusst nicht entschieden, sondern dokumentiert.** Ob
die Korrektur übernommen wird oder der alte Zustand als Soll gilt, war
eine fachliche Frage und gehörte dem Nutzer (Punkt 33). **Am 08.09.2026
hat er sie angenommen** — die Begründung dafür steht in §6. Bis dahin
galt, und für den nächsten Fall dieser Art gilt weiterhin:

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

**Bei Welle 5 hat sie das Teuerste überhaupt gefunden.** Welle 5 ist *ein*
Paket, seriell, und bringt keine neue Dateiart hervor — nach dem Buchstaben
der Regel hätte sie kein Vorfeld gebraucht. Die Prüffrage lautet aber
„wem gehört die Zeile, die alles zusammenhält", und die Zeile war hier
`all:` im `Makefile`. Sie stand seit W0.3 auf `prep widmung-v2` und rief
damit die **alte** Kette auf, die keines der vier Endprodukte schreibt.
**Der Beweislauf hätte den Vorgänger bewiesen und den Umbau nie
berührt** — und weil er grün gewesen wäre, hätte es niemand gemerkt.
W5.P0 hat es in einer Zeile behoben, mit `make -n` über 36 Ziele als
Gegennachweis, und nebenbei Punkt 37 aufgelöst.

**W5.P1 kam obendrauf, weil W5.P0 beim Hinsehen eine zweite Lücke fand:**
`geo.py` las acht Checkpoints unbedingt aus `output/`, ohne Rückfall, und
die Layer-Reihenfolge stand alphabetisch statt nach Abhängigkeit. Auch das
hätte der Beweislauf nicht gemeldet, sondern still aus einem Altbestand
bedient. Damit sind es **35 Pakete** — und die Regel hat in zwei von zwei
Anwendungen etwas gefunden, das kein Test und kein Merge je gemeldet
hätte.

**Nachtrag: zwei weitere Pakete, aus einem anderen Grund.** W5.P2 setzt
eine Nutzerentscheidung um, W5.P3 räumt hinter W5.P2 auf — damit **37**.
Das zweite ist die eigentliche Lehre: W5.P2 hat drei Stellen im Repo
zurückgelassen, die seither etwas Falsches behaupten, und **alle drei
selbst gemeldet, statt sie stillschweigend mitzunehmen oder eigenmächtig
zu ändern**. Dazu kam eine vierte, die mein Fehler war — ich hatte einen
`ursache`-Text für alle neuen Registerzeilen diktiert, obwohl das Werkzeug
gegen `run1` vergleicht und deshalb auch unveränderte Bänder mit ausgibt.

**Nachtrag zum Nachtrag: ein fünftes und sechstes Paket, aus demselben
Muster.** W5.P4 hat den Registerfehler (Schlüsselwort, `ampel`-Auffrischung,
README) behoben, aber den eigentlichen Entwurfsfehler — den fest auf
Wasser verdrahteten Wirkungspfad-Wächter — bewusst nicht angefasst, weil
die saubere Lösung eine fehlende Kante im Manifest-Graphen zuerst
nachbilden müsste. Genau dafür jetzt **W5.P5**: damit **39**. Auch das ist
kein Rückschlag, sondern dieselbe Regel wieder bestätigt — ein Paket, das
anhält statt zu improvisieren, erzeugt ein sauber benanntes Folgepaket
statt eines stillen Fehlers im Register.

> **Ergänzung zu Regel 9.** Ein Paket, das die **Referenz verschiebt**,
> erzeugt zwangsläufig Folgearbeit an jeder Stelle, die die alte Referenz
> zitiert — Tests, Handreichungen, README, Register. Diese Stellen sind
> selten alle im Besitz desselben Pakets. Sie gehören **vorher gezählt**
> und **danach in einem eigenen Paket** abgeräumt, nicht in dem, das die
> Änderung macht. Sonst entsteht genau das Muster aus §13.6: eine
> Entscheidung, an vier Orten verschieden nachgezogen.

### 13.11 Das Zielbild ist abgenommen — und die Wellenzählung war zwei Dateien lang uneins

**Zuerst das Ergebnis, weil es das größte des Projekts ist.** §7 gibt W6.3
die Abnahmebedingung für das Zielbild aus §3: *„Ein frischer Klon von
`main` plus `data/` läuft `make` ohne Argument bis zu den vier Produkten
durch."* Diese Bedingung ist am 08.09.2026 im Klontest von W6.4
**erfüllt** — ein `git clone --local` von `main`, `data/` als Symlink,
`make` ohne Argument, 62:49 Laufzeit, und am Ende
`sha256 fb57c41d…232c30`, exakt die Referenz.

Sie ist nicht so erfüllt worden, wie ich es mir gedacht hatte: Der Klon
sollte den vorhandenen Zwischenstand wiederverwenden und in Minuten fertig
sein; stattdessen hat er alles neu gerechnet. **Aber die Bedingung sagt
„läuft durch", nicht „läuft schnell durch"** — und der Weg, den sie
absichern soll, ist `[Rohdaten] → [Skripte] → [Ergebnisse]` ohne Reste des
Vorgängerprojekts. Genau der ist damit an einem zweiten Ort im Dateisystem
belegt, mit anderen Zeitstempeln, aus derselben Historie. Die
Geschwindigkeit ist eine eigene Frage; sie steht als Punkt 56 im Register
und ist keine Bedingung dieses Plans.

**Und der Fehler in der Buchführung, weil er zu §13.6 gehört.** Die
Pakettabelle oben führte W6.4 als Doku-Paket, während `FORTSCHRITT.md`
W6.4 als Fingerabdruck-Paket führte und die Doku als W6.5. Beide Dateien
schreibe ich, beide beschreiben dieselben Pakete, und sie waren eine
ganze Welle lang uneins — **dieselbe Entscheidung, an zwei Orten
verschieden nachgezogen**, nur diesmal nicht im Code, sondern in meiner
eigenen Planung. Ursache: Der Fingerabdruck-Befund entstand *während*
der Welle (Punkt 53, aus dem gescheiterten Klontest in W6.3) und bekam
seine Nummer im Fortschritt, nicht im Plan. Der Plan ist jetzt
nachgezogen; die Welle hat fünf Pakete statt vier.

> **Ergänzung zu Regel 7.** Wächst eine Welle während ihrer Ausführung um
> ein Paket, bekommt das Paket seine Nummer **im Plan zuerst**. Der
> Fortschritt schreibt fort, was der Plan festlegt — nicht umgekehrt.
> Sonst hat dieselbe Welle zwei Nummerierungen, und die spätere Lesart
> hängt davon ab, welche Datei jemand zuerst öffnet.

## Maschinensichten

- [`domains.tsv`](domains.tsv) / `domains.json` — Domänenmatrix, maschinenlesbar (`src/extract_domains.py`).
- [`packages.tsv`](packages.tsv) / `packages.json` — Paketmatrix aller 30 Arbeitspakete, maschinenlesbar (`src/extract_packages.py`).
- [`../dataflow/nodes.tsv`](../dataflow/nodes.tsv) — Knoten des Datenflussgraphen.
- [`../dataflow/edges.tsv`](../dataflow/edges.tsv) — Kanten des Datenflussgraphen, jede mit Fundstelle.

## HTML-Ansichten

- [`zielbild.html`](zielbild.html) — interaktive Ansicht auf das Zielbild.
- [`umsetzung.html`](umsetzung.html) — interaktive Ansicht auf Wellen, Pakete und Abnahmebedingung.
- [`../dataflow/flow_diagram.html`](../dataflow/flow_diagram.html) — interaktive Ansicht auf den Datenflussgraphen.
