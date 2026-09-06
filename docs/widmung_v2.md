# Windkraft-Flächenanalyse Österreich — Widmungs-Abschichtung v2

**Dokumentation der Rasterdatei `osm_wka_distance_zones_widmung_v2.tif`** · Stand: August 2026

Die Datei ist das Ergebnis einer flächendeckenden **Abschichtung** für ganz
Österreich: Von der Staatsfläche werden nacheinander alle Bereiche
ausgeschlossen, die für Windkraftanlagen nicht in Frage kommen (Siedlungen und
ihre Schutzabstände, Gebäude, Infrastruktur, Schutzgebiete, ungeeignetes
Gelände, zu wenig Wind). Was übrig bleibt, ist die **potenziell verfügbare
Fläche**. Jeder Zwischenschritt ist als eigenes Rasterband gespeichert, sodass
jede Stufe der Rechnung einzeln sichtbar und überprüfbar ist.

> **Einordnung:** eine planerische Grobabschätzung, **kein rechtsverbindliches
> Dokument**. Nicht enthalten: luftfahrtrechtliche Einzelprüfungen,
> naturschutzfachliche Einzelfallprüfungen, Schall-/Schatten-/
> Sichtbarkeitsanalysen, Netzanschluss, Grundverfügbarkeit.

---

## 1. Ergebnis im Überblick

Bezogen auf die Staatsfläche von 83.921 km² (Stand des Rechenlaufs: 10. August 2026):

| | km² | Anteil |
|---|---:|---:|
| Ausschluss Mensch (Siedlung, Gebäude, Infrastruktur, Flughäfen) | 56.743 | 67,6 % |
| Ausschluss Natur (Schutzgebiete) | 17.286 | 20,6 % |
| Ausschluss Geografie (Hangneigung, Höhe, Windarmut, Gewässer) | 46.205 | 55,1 % |
| **Ausschluss gesamt** (Überlappungen nur einfach gezählt) | **79.638** | **94,9 %** |
| verfügbare Fläche, roh | 4.283 | 5,1 % |
| **verfügbare Fläche, bereinigt (nur Flächen ≥ 10 ha)** | **3.659** | **4,4 %** |
| zum Vergleich: amtliche Windkraft-Positivzonen der Länder | 396 | 0,5 % |

Die drei Ausschlussgruppen überlappen sich stark (ein steiler, windarmer Hang in
einem Schutzgebiet zählt in allen dreien) — sie summieren sich deshalb nicht zum
Gesamtausschluss.

## 2. Technische Eckdaten

| | |
|---|---|
| Datei | `osm_wka_distance_zones_widmung_v2.tif` |
| Format | GeoTIFF, **38 Bänder**, uint8, deflate-komprimiert, mit Übersichtspyramiden |
| Koordinatensystem | EPSG:31287 (MGI / Austria Lambert) |
| Auflösung | 25 m × 25 m (24.001 × 14.001 Zellen, ganz Österreich) |
| Werte | je Band 0/1: **1 = Bedingung trifft auf die Zelle zu**. Ausnahme Bänder 33–36 (`available_blur_sigma_*`): 0–100 (Prozent) |
| Bandnamen | als Band-Beschreibung in der Datei eingebettet |
| Parameter | alle Abstände und Schwellwerte als Metadaten-Tags in der Datei |
| Verwendung | z. B. QGIS („Rasterlayer hinzufügen", dann Band wählen) oder GDAL/rasterio; `gdalinfo` listet Bandnamen und Metadaten |

**Wichtig für Flächenauswertungen:** Die Bedingungsbänder 1–26 und die
Referenzbänder 37–38 sind über die volle Bounding Box gerechnet (Puffer laufen
über die Staatsgrenze hinaus). Nur die Aggregat- und Ergebnisbänder 27–32 sind
auf das Staatsgebiet zugeschnitten. Wer einzelne Bedingungsbänder in km²
auswertet, muss sie selbst mit der Staatsgrenze verschneiden.

## 3. Datenquellen

| Quelle | Liefert |
|---|---|
| **Flächenwidmung** aller 9 Bundesländer (offene Geodaten der Länder) | gewidmetes Wohnbauland, Ferienhaus-/Tourismusgebiete, Grünland-Sonderwidmungen |
| **NÖ SekROP** „Sektorales Raumordnungsprogramm Windkraftnutzung", Karte Mindestabstandszonen (Teil C 3.2, 02.04.2024) | die amtlichen NÖ-750-m-Zonen (Klassen Gebäude / GWR / Grünland-Widmung), georeferenziert aus der PDF-Karte extrahiert |
| **DKM** — Digitale Katastralmappe (BEV) | amtliche Gebäude-Grundrisse („Bauflächen") |
| **BEV-Adressregister** (Stand 10/2025, 2,52 Mio. Adresspunkte) | Bewohnt-Signal: welche Gebäude haben eine Adresse |
| **OpenStreetMap** (Österreich-Extrakt 03/2026) | Straßen, Bahn, Seilbahnen, Militärflächen, Flughäfen und Landebahnen, Gebäude ohne amtliche Abdeckung, Gewässer, ergänzende Schutzgebiete, Bestands-Windräder |
| **Schutzgebiets-Datenbank** (amtlich) | Nationalparks, Naturschutzgebiete, Europaschutzgebiete/Natura 2000, Ramsar |
| **Digitales Geländemodell** (25 m) | Geländehöhe und -neigung |
| **Global Wind Atlas** | Windleistungsdichte (W/m²) |
| **Amtliche Windzonen** der Länder | NÖ Zonierung (LGBl. 47/2024), Stmk SAPRO, Sbg Vorrangzonen, Bgld Eignungszonen, Ktn RED-III-Beschleunigungszonen |

## 4. Zentrale Begriffe und Methoden

**Hülle (Streusiedlungs-Erkennung).** Alle DKM-Bauflächen außerhalb des
gewidmeten Siedlungsraums werden verkettet: Gebäude mit weniger als **200 m**
Abstand zueinander bilden eine zusammenhängende Gruppe, um die ein Umriss
gezogen wird — die Hülle. Jede Hülle wird anschließend mit dem BEV-Adressregister
klassifiziert:

| Klassifikation der Hülle | Kriterium | Konsequenz |
|---|---|---|
| **Streusiedlungs-Gebiet** | bewohnt und **≥ 5 adressierte Objekte** | 750 m Abstand (Band 5 → 7) |
| **Bewohnte Einzellage** | bewohnt, aber < 5 adressierte Objekte | 25 m, über das Gebäudeband (Band 13) |
| **Nicht-Wohn-Hülle** | keine Wohnnutzung (BEV-Wohnanteil < 0,1) oder mehrheitlich Betriebs-/Industriewidmung | 25 m (Bänder 8–9) |

Dahinter steht eine ausdrückliche Politikentscheidung: **Gebiets- statt
Einzelobjekt-Schutz.** Voller Siedlungsabstand gilt nur für amtlich gewidmetes
Wohnbauland, bewohnte Streusiedlungs-**Gebiete** erhalten einheitlich 750 m,
einzelne Höfe darunter nur den 25-m-Fußabdruck.

**Puffer.** Alle Abstände werden als Kreispuffer um die Quellzellen auf dem
25-m-Raster gerechnet.

**Mindestfläche.** Für das bereinigte Ergebnis zählen nur zusammenhängende
Flächen ab **10 ha**; zusammenhängend heißt Kantenkontakt
(4er-Nachbarschaft) — eine bloße Eckberührung verbindet nicht.

## 5. Die 38 Bänder im Einzelnen

### Siedlung (Bänder 1–2)

| # | Band | Inhalt und Herkunft |
|---|---|---|
| 1 | `official_settlement_source` | Amtlich gewidmetes Wohn-, Dorf-, Kern- und Mischgebiet, zusammengeführt aus der Flächenwidmung aller 9 Bundesländer. |
| 2 | `settlement_buffer` | Siedlungsabstand um Band 1: NÖ 1.200 m, alle übrigen Bundesländer 1.000 m. |

### Häuser-im-Grünen-Familie (Bänder 3–7)

Bewohnte Nutzungen im Grünland, die nicht Wohnbauland sind. Jede Quelle hat ihr
eigenes Band; Band 7 ist das gemeinsame Abstands-Aggregat.

| # | Band | Inhalt und Herkunft |
|---|---|---|
| 3 | `haeuser_im_gruenen_ferienhaus` | Ferienhaus- und Tourismusgebiete aus der Flächenwidmung (z. B. Burgenland-Codes 10030/10007/10017, Tirol „Tourismusgebiet § 40 (4)"). |
| 4 | `haeuser_im_gruenen_widmung` | Amtliche Grünland-Sonderwidmungen für Wohnnutzungen: Hofstellen, Auffüllungsgebiete, Camping, Golf, Kleingärten (z. B. OÖ 13010/13020, Stmk afg/klg, Sbg GLCA/GLKG, Kärnten Hofstellen, Tirol § 44/§ 46, Vbg Camping/Golf/Kleingarten) — **ohne NÖ**: dort definiert allein die SekROP-Grünland-Klasse (Band 6) den Abstand um die Widmungen Gho/Gc/Gkg. |
| 5 | `haeuser_im_gruenen_streusiedlung` | Bewohnte Streusiedlungs-Hüllen (≥ 5 adressierte Objekte, 200-m-Verkettung) aus DKM + BEV-Adressregister — in 8 Bundesländern; **ohne NÖ**, dort ist die amtliche SekROP-Quelle maßgeblich (Band 6). |
| 6 | `haeuser_im_gruenen_noe_pdf` | Die amtlichen NÖ-SekROP-750-m-Zonen (Klassen Gebäude/GWR/Grünland-Widmung), aus der PDF-Karte georeferenziert. Diese Polygone **enthalten den 750-m-Abstand bereits** und fließen deshalb ungepuffert in Band 7 ein. |
| 7 | `haeuser_im_gruenen` | **Aggregat:** 750 m Abstand um die Bänder 3 + 4 + 5, vereinigt mit Band 6 (das schon gepuffert ist). |

### Gebäude und Hüllen (Bänder 8–13)

| # | Band | Inhalt und Herkunft |
|---|---|---|
| 8 | `nonresidential_hulls_source` | Unbewohnte bzw. industriegebietartige DKM-Hüllen (Almen, Ställe, Hallen, Betriebsareale): BEV-Wohnanteil < 0,1 oder ≥ 50 % der Gebäude in Betriebs-/Industriewidmung. |
| 9 | `nonresidential_hulls_buffer` | 25 m um Band 8 — reiner Objektschutz, kein Immissionsabstand. |
| 10 | `cableway_buildings_source` | OSM-Gebäude im 100-m-Umkreis einer Seilbahnlinie (Liftstationen etc.). |
| 11 | `cableway_buildings_buffer` | 50 m um Band 10. |
| 12 | `general_buildings_source` | Alle übrigen OSM-Gebäude (Garagen, Schuppen, Ställe, Industrie, untypisiert, auch Kirchen und Kapellen) **plus** die bewohnten Einzellagen (< 5 adressierte Objekte) aus DKM/BEV. Jedes OSM-Gebäude landet in genau einer der beiden Kategorien 10/12 — und nur, wenn es nicht schon von einer amtlichen Quelle (Bänder 1, 3–6, 8) abgedeckt ist. Windkraftanlagen, die in OSM zusätzlich als Gebäude eingetragen sind, werden vorab entfernt, damit sie nicht ihren eigenen Standort ausschließen. |
| 13 | `general_buildings_buffer` | 25 m um Band 12 — praktisch nur der Gebäude-Fußabdruck. |

### Infrastruktur (Bänder 14–18)

| # | Band | Inhalt und Herkunft |
|---|---|---|
| 14 | `road_motorway_trunk` | 150 m um Autobahnen und Schnellstraßen (OSM, Tunnelabschnitte ausgenommen). |
| 15 | `road_federal_state` | 150 m um das übrige überörtliche Straßennetz (primary/secondary/tertiary, Tunnel ausgenommen). |
| 16 | `rail_main` | 150 m um Normal- und Schmalspurbahnen (Tunnel ausgenommen). |
| 17 | `cableway_people_150m` | 150 m um personenbefördernde Seilbahnen und Lifte (OSM). |
| 18 | `military_restricted_area` | Militärische Sperr- und Übungsflächen (OSM), Fußabdruck ohne Zusatzabstand. |

Stromleitungen sind **kein** Ausschlusskriterium.

### Flughäfen (Bänder 19–20)

Nur die sechs Hauptflughäfen (Wien-Schwechat, Graz, Linz, Salzburg, Innsbruck,
Klagenfurt). Andere Flugplätze und Heliports sind kein Ausschlusskriterium.

| # | Band | Inhalt und Herkunft |
|---|---|---|
| 19 | `airport_area_major` | Betriebsflächen (Aerodrome-Polygone) der sechs Hauptflughäfen, Fußabdruck. |
| 20 | `airport_runway_corridor_5km` | An-/Abflugkorridore: an jedem Landebahn-Ende ein **5-km-Kreissektor, ±15°** um die verlängerte Bahnachse. Die Bahnachsen werden aus den OSM-Landebahn-Geometrien abgeleitet (segmentierte Linien werden verbunden, bei Flächen zählt die Längsachse des umschriebenen Rechtecks). |

### Natur (Bänder 21–22)

| # | Band | Inhalt und Herkunft |
|---|---|---|
| 21 | `nature_protection_areas` | Amtliche Schutzgebiete: Nationalparks, Naturschutzgebiete, Europaschutzgebiete/Natura 2000, Ramsar — Fußabdruck. |
| 22 | `osm_nature_protection_areas` | Ergänzende Schutz-/Naturflächen aus OSM (protected_area, national_park, nature_reserve u. ä.). |

### Geografie (Bänder 23–26)

| # | Band | Inhalt und Herkunft |
|---|---|---|
| 23 | `geography_slope_too_steep` | Hangneigung über **15°** (≙ 26,8 %), berechnet auf dem auf 100 m aggregierten Geländemodell. |
| 24 | `geography_elevation_too_high` | Geländehöhe über **2.500 m**. |
| 25 | `geography_wind_too_low` | Windleistungsdichte unter der Eignungsschwelle: **150 W/m² bezogen auf 130 m Nabenhöhe** (≙ 159,5 W/m² am 150-m-Raster des Global Wind Atlas). |
| 26 | `geography_water_bodies` | Größere Gewässer aus OSM (Seen, Stauseen, Flussläufe als Flächen), Fußabdruck; nur verbundene Wasserflächen ≥ 1 ha. |

### Aggregate und Ergebnis (Bänder 27–32)

Ab hier auf das Staatsgebiet zugeschnitten.

| # | Band | Inhalt |
|---|---|---|
| 27 | `exclusion_human` | ODER-Verknüpfung aller Mensch-Ausschlüsse (Bänder 2, 7, 9, 11, 13, 14–20). |
| 28 | `exclusion_nature` | ODER der Natur-Bänder (21–22). |
| 29 | `exclusion_geography` | ODER der Geografie-Bänder (23–26). |
| 30 | `all_exclusions` | ODER von 27–29: alles, was ausgeschlossen ist. |
| 31 | `available_after_all_exclusions_raw` | Das Negativ von Band 30 — verfügbare Fläche ohne Mindestgrößen-Filter. |
| 32 | `available_cleaned_min_10ha` | **Das Endergebnis:** Band 31, bereinigt um Splitter — nur zusammenhängende Flächen ≥ 10 ha (4er-Nachbarschaft). |

### Unsicherheits-Bänder (33–36)

| # | Band | Inhalt |
|---|---|---|
| 33–36 | `available_blur_sigma_100m/200m/250m/300m` | Gauß-geglättete Eignungsfläche (Werte 0–100 %): der gewichtete Anteil verfügbarer Fläche in der Umgebung jeder Zelle, mit Glättungsradius (Sigma) 100/200/250/300 m. Basis ist die **rohe** verfügbare Fläche (Band 31), daher sind auch Flächen unter der 10-ha-Schwelle sichtbar. 100 = tief in einer großen Zone, ~50 = an der Kante, schmale Splitter verwaschen. |

### Referenzbänder (37–38) — keine Ausschlüsse

| # | Band | Inhalt und Herkunft |
|---|---|---|
| 37 | `official_wind_zoning` | Alle amtlichen Windkraft-Positivzonen der Länder in einem Band: NÖ Zonierung (71 Zonen, LGBl. 47/2024), Steiermark SAPRO Vorrang-/Eignungszonen, Salzburg Vorrangzonen, Burgenland Eignungszonen, Kärnten RED-III-Beschleunigungszonen (Bärofen, Peterer Alpe, Soboth/Lavamünd, Steinberger Alpe). Dient dem Soll-Ist-Vergleich mit der Abschichtung. |
| 38 | `wka_bestand_ausserhalb_zonen` | Bestehende Windräder aus OSM, die **außerhalb** der Zonen aus Band 37 stehen, zu Park-Hüllen zusammengefasst (Anlagen mit < 750 m Abstand bilden einen Park; konvexe Hülle + 200 m Rand). Aktueller Stand: 1.595 Anlagen erfasst, davon 788 außerhalb der Zonen, gruppiert zu 183 Hüllen. |

## 6. Qualitätssicherung und Validierung

Jeder Rechenlauf wird an 8 fixen Testpunkten geprüft — charakteristischen
Fällen je Regel (NÖ-SekROP-Zone, Ferienhauswidmung, Industriehülle,
Tourismusgebiet, Streusiedlung in einem Widmungsdatenloch, bewohnte
Einzellage). Aktueller Lauf: alle 8 bestanden.

Darüber hinaus ist Niederösterreich das einzige Bundesland, für das eine
amtliche Abstandszone publiziert ist (SekROP Teil C 3.2). Damit lässt sich
prüfen, ob die Methode diese Zone aus ihren eigenen Quellen (Flächenwidmung,
DKM, BEV-Adressregister) rekonstruiert. Für diesen Test werden die
SekROP-Zonen selbst bewusst **nicht** verwendet — sonst wäre der Vergleich
zirkulär. Gemessen an der amtlichen Gesamt-Mindestabstandszone
(15.822 km² = 82 % von NÖ):

| Reproduktionsstufe | Abdeckung | verfehlt | Überstand | IoU* |
|---|---:|---:|---:|---:|
| nur amtliche Häuser-im-Grünen-Widmung ⊕ 750 m | 11,1 % | 14.058 km² | 0,5 km² | 11,1 % |
| + Streusiedlungs-Hüllen ⊕ 750 m | 29,1 % | 11.218 km² | 67 km² | 29,0 % |
| **Regel dieser Karte (Einzellage ⊕ 25 m) + Siedlung ⊕ 1.200 m** | **93,2 %** | **1.081 km²** | **101 km²** | **92,6 %** |
| dieselbe Kette, Einzellage ⊕ 750 m | 98,8 % | 186 km² | 297 km² | **97,0 %** |
| jedes Gebäude ⊕ 750 m | 99,3 % | 113 km² | 968 km² | 93,6 % |

\* IoU (Intersection over Union): Flächenübereinstimmung beider Zonen, 100 % = identisch.

Zwei Ergebnisse zählen. Erstens die Grünland-Widmungsklasse allein
(SekROP-Klasse „Widmung Gkg/Gc/Gho" = Kleingarten/Camping/Hofstelle): sie wird
aus denselben Codes der NÖ-Flächenwidmung zu 96,7 % getroffen (IoU 93,9 %), die
Restdifferenz ist ein rasterbedingter Saum plus rund ein Dutzend Einzelobjekte
mit unterschiedlichem Datenstand. Zweitens die Gesamtzone: mit der Politik des
Landes (jedes bewohnte Objekt im Grünland 750 m) erreicht die Methode IoU
97,0 % — die amtliche Zone ist also aus Widmung + DKM + BEV reproduzierbar.

Die verbleibende Lücke der hier verwendeten Regel (1.081 km², 5,6 % der
Landesfläche) ist keine Datenlücke, sondern die dokumentierte
Politikentscheidung, Einzellagen unter der Streusiedlungsschwelle nur 25 m zu
geben. In der Gegenrichtung ist die Methode sehr präzise: nur 101 km²
Ausschluss ohne amtliches Gegenstück.
