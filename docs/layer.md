# Layer-Beschreibung Abschichtung Widmung v2 (Stand Schema 2.1.0 + geplante Bänder 39–44)

Dieses Dokument beschreibt jede der 44 Bänder des geplanten Widmung-v2-Layer-Sets, ein Abschnitt pro Layer. Die Bänder 1–38 existieren bereits im Bänder-Manifest `abschichtung.bands.json` (Schema 2.1.0); ihre Texte (Label, Beschreibung, Puffer, Quellen, Abgeleitet-von, Rolle, Caveats) sind wortwörtlich aus dem Manifest übernommen. Die Bänder 39–44 sind Teil des Umbau-Vorschlags v4 vom 2026-09-09 und existieren noch nicht im Manifest; ihre Beschreibungen sind deshalb als geplant gekennzeichnet. Die Spalte „Sichtbar beim Laden“ gibt den geplanten v4-Standard wieder, nicht das `default_visible` des Manifests.

## Stufen-Vokabular

| Stufe | Bedeutung |
|---|---|
| roh | Rohdatensatz, nur wo wirklich verschiedene Quellen zusammenfließen |
| quelle | Quell-Layer, ungepuffert |
| aggregat | Vereinigung der Quellen einer Familie, ungepuffert |
| zone | gepufferte Ausschlussfläche |
| summe_quellen | ODER aller Quellen einer Kategorie |
| summe_zonen | ODER aller Zonen einer Kategorie |
| ergebnis | Verfügbarkeitsbänder |

## Mensch

### Siedlung

#### official_settlement_source

| Feld | Wert |
|---|---|
| Index | 1 |
| Stufe | quelle |
| Label | Amtliches Wohnbauland (Quelle) |
| Beschreibung | Amtliches Wohn-/Misch-/Kern-/Dorfgebiet, alle 9 Bundesländer (build_official_zoning_layers.py) |
| Puffer | keiner |
| Quellen | flaechenwidmung_bgld: data/widmung/burgenland/WIDMUNGSFLAECHEN.zip (Stand Dateidatum 22.06.); flaechenwidmung_ktn: data/widmung/kaernten/flawi_ktn_gpkg.zip (Stand Dateidatum 12.07.); flaechenwidmung_noe: data/widmung/niederoesterreich/RRU_WI_HUELLE.gpkg (Stand Dateidatum 10.07.); flaechenwidmung_ooe: data/widmung/oberoesterreich/FLWI_WIDMUNGEN_F.zip (Stand Dateidatum 10.07.); flaechenwidmung_sbg: data/widmung/salzburg/Flaechenwidmung_Shapefile.zip (Stand Dateidatum 12.07.); flaechenwidmung_stmk: data/widmung/steiermark/Bauland.zip + data/widmung/steiermark/Flaewi.shp.zip (Stand Dateidatum 10.07. / 22.06.); flaechenwidmung_tirol: data/widmung/tirol/FLW_Flaechenwidmung_*.gpkg (Stand Dateidatum 12.07.); flaechenwidmung_vbg: data/widmung/vorarlberg/fwp_flaeche.gpkg (Stand Dateidatum 12.07.); flaechenwidmung_wien: data/widmung/wien/genflwidmung_wien.geojson (Stand Dateidatum 29.07.) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | nein |

#### settlement_buffer

| Feld | Wert |
|---|---|
| Index | 2 |
| Stufe | zone |
| Label | Siedlungsabstand (NÖ 1.200 m, sonst 1.000 m) |
| Beschreibung | Siedlungsabstand um official_settlement_source (NÖ 1.200 m, sonst 1.000 m) |
| Puffer | Bundeslandabhängig (SETTLEMENT_BUFFER_BY_BL): 1.200 m in Niederösterreich, sonst einheitlich 1.000 m. |
| Quellen | verwaltungsgrenzen_vgd: data/admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp (Stand 02.10.2022) |
| Abgeleitet von | official_settlement_source |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

### Häuser im Grünen

#### haeuser_im_gruenen_ferienhaus

| Feld | Wert |
|---|---|
| Index | 3 |
| Stufe | quelle |
| Label | Ferienhaus / Tourismus (Quelle) |
| Beschreibung | HiG-Familie: Ferienhaus-/Tourismusgebiete (B 10030/10007/10017, T Tourismusgebiet § 40 (4)) |
| Puffer | keiner |
| Quellen | flaechenwidmung_bgld: data/widmung/burgenland/WIDMUNGSFLAECHEN.zip (Stand Dateidatum 22.06.); flaechenwidmung_ktn: data/widmung/kaernten/flawi_ktn_gpkg.zip (Stand Dateidatum 12.07.); flaechenwidmung_noe: data/widmung/niederoesterreich/RRU_WI_HUELLE.gpkg (Stand Dateidatum 10.07.); flaechenwidmung_ooe: data/widmung/oberoesterreich/FLWI_WIDMUNGEN_F.zip (Stand Dateidatum 10.07.); flaechenwidmung_sbg: data/widmung/salzburg/Flaechenwidmung_Shapefile.zip (Stand Dateidatum 12.07.); flaechenwidmung_stmk: data/widmung/steiermark/Bauland.zip + data/widmung/steiermark/Flaewi.shp.zip (Stand Dateidatum 10.07. / 22.06.); flaechenwidmung_tirol: data/widmung/tirol/FLW_Flaechenwidmung_*.gpkg (Stand Dateidatum 12.07.); flaechenwidmung_vbg: data/widmung/vorarlberg/fwp_flaeche.gpkg (Stand Dateidatum 12.07.); flaechenwidmung_wien: data/widmung/wien/genflwidmung_wien.geojson (Stand Dateidatum 29.07.) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | nein |

#### haeuser_im_gruenen_widmung

| Feld | Wert |
|---|---|
| Index | 4 |
| Stufe | quelle |
| Label | Amtliche HiG-Widmung (Quelle, ohne NÖ) |
| Beschreibung | HiG-Familie: amtliche Häuser-im-Grünen-Widmung (Hofstellen, Camping, Golf, Kleingarten, Auffüllungsgebiete); ohne NÖ - dort trägt die PDF-Grünland-Klasse den Abstand |
| Puffer | keiner |
| Quellen | flaechenwidmung_bgld: data/widmung/burgenland/WIDMUNGSFLAECHEN.zip (Stand Dateidatum 22.06.); flaechenwidmung_ktn: data/widmung/kaernten/flawi_ktn_gpkg.zip (Stand Dateidatum 12.07.); flaechenwidmung_noe: data/widmung/niederoesterreich/RRU_WI_HUELLE.gpkg (Stand Dateidatum 10.07.); flaechenwidmung_ooe: data/widmung/oberoesterreich/FLWI_WIDMUNGEN_F.zip (Stand Dateidatum 10.07.); flaechenwidmung_sbg: data/widmung/salzburg/Flaechenwidmung_Shapefile.zip (Stand Dateidatum 12.07.); flaechenwidmung_stmk: data/widmung/steiermark/Bauland.zip + data/widmung/steiermark/Flaewi.shp.zip (Stand Dateidatum 10.07. / 22.06.); flaechenwidmung_tirol: data/widmung/tirol/FLW_Flaechenwidmung_*.gpkg (Stand Dateidatum 12.07.); flaechenwidmung_vbg: data/widmung/vorarlberg/fwp_flaeche.gpkg (Stand Dateidatum 12.07.); flaechenwidmung_wien: data/widmung/wien/genflwidmung_wien.geojson (Stand Dateidatum 29.07.); verwaltungsgrenzen_vgd: data/admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp (Stand 02.10.2022) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | nein |

#### haeuser_im_gruenen_streusiedlung

| Feld | Wert |
|---|---|
| Index | 5 |
| Stufe | quelle |
| Label | Streusiedlungs-Hüllen (Quelle, ohne NÖ) |
| Beschreibung | HiG-Familie: bewohnte Streusiedlungs-Hüllen (>= 5 adressierte Objekte, 200-m-Verkettung); ohne NÖ - dort gilt die amtliche PDF-Quelle |
| Puffer | keiner |
| Quellen | bev_adressregister: data/adressen/ (Stand Stichtag 01.10.2025); dkm_geoparquet: output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet (Stand Dateidatum 15.05.; erzeugtes Artefakt aus BEV-DKM); verwaltungsgrenzen_vgd: data/admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp (Stand 02.10.2022) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | nein |

#### haeuser_im_gruenen_noe_pdf

| Feld | Wert |
|---|---|
| Index | 6 |
| Stufe | quelle |
| Label | NÖ-SekROP-750-m-Zonen |
| Beschreibung | HiG-Familie: NÖ-SekROP-750-m-Zonen (Gebäude/GWR/Grünland-Widmung) - enthalten den 750-m-Puffer bereits |
| Puffer | 750 m bereits im Quellband enthalten - die NÖ-SekROP-PDF-Zonen liefern Objekt und Abstand zusammen, kein zweiter Puffer hier. |
| Quellen | noe_sekrop_mindestabstandszonen: data/noe_sekrop/TeilC_3_2_Karte_Mindestabstandszonen_A0_20240402.pdf (Stand Karten-Stand 02.04.2024 (Dateidatum 29.03.2026)) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | nein |

#### haeuser_im_gruenen_source (geplant, nicht im Manifest 2.1.0)

| Feld | Wert |
|---|---|
| Index | 39 |
| Stufe | aggregat |
| Label | Häuser im Grünen (Quelle, Aggregat) |
| Beschreibung | Vereinigung der drei Quellen Ferienhaus/Tourismus, amtliche HiG-Widmung und Streusiedlungs-Hüllen, ungepuffert und ohne NÖ. Die NÖ-SekROP-Zonen sind nicht enthalten, weil sie den 750-m-Puffer bereits tragen. Entspricht dem Zwischenergebnis, das der Produzent heute intern vor dem 750-m-Puffer bildet. |
| Puffer | keiner |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | haeuser_im_gruenen_ferienhaus, haeuser_im_gruenen_widmung, haeuser_im_gruenen_streusiedlung |
| Rolle | bedingung |
| Caveats | noch nicht zugeordnet |
| Sichtbar beim Laden | nein |

#### haeuser_im_gruenen

| Feld | Wert |
|---|---|
| Index | 7 |
| Stufe | zone |
| Label | Häuser im Grünen (750 m) |
| Beschreibung | Aggregat: 750 m um Ferienhaus + Widmung + Streusiedlung, vereinigt mit den NÖ-PDF-Zonen |
| Puffer | 750 m |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | haeuser_im_gruenen_ferienhaus, haeuser_im_gruenen_widmung, haeuser_im_gruenen_streusiedlung, haeuser_im_gruenen_noe_pdf |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

### Nicht-Wohn-Hüllen

#### nonresidential_hulls_source

| Feld | Wert |
|---|---|
| Index | 8 |
| Stufe | quelle |
| Label | Nicht-Wohn-Hüllen (Quelle) |
| Beschreibung | Industriegebietartige und unbewohnte DKM-Hüllen |
| Puffer | keiner |
| Quellen | dkm_geoparquet: output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet (Stand Dateidatum 15.05.; erzeugtes Artefakt aus BEV-DKM); osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | noe_dkm_reconstructed |
| Sichtbar beim Laden | nein |

#### nonresidential_hulls_buffer

| Feld | Wert |
|---|---|
| Index | 9 |
| Stufe | zone |
| Label | Nicht-Wohn-Hülle (25 m) |
| Beschreibung | 25 m um nonresidential_hulls_source (praktisch nur der Fußabdruck) |
| Puffer | 25 m |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | nonresidential_hulls_source |
| Rolle | bedingung |
| Caveats | noe_dkm_reconstructed |
| Sichtbar beim Laden | ja |

### Seilbahn-Gebäude

#### cableway_buildings_source

| Feld | Wert |
|---|---|
| Index | 10 |
| Stufe | quelle |
| Label | Seilbahn-Gebäude (Quelle) |
| Beschreibung | OSM-Gebäude nahe einer Aerialway-Linie (Liftstationen etc.) |
| Puffer | keiner |
| Quellen | osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026); dkm_geoparquet: output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet (Stand Dateidatum 15.05.; erzeugtes Artefakt aus BEV-DKM) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | nein |

#### cableway_buildings_buffer

| Feld | Wert |
|---|---|
| Index | 11 |
| Stufe | zone |
| Label | Seilbahn-Gebäude (50 m) |
| Beschreibung | 50 m um cableway_buildings_source |
| Puffer | 50 m |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | cableway_buildings_source |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

### Gebäude

#### general_buildings_roh_osm (geplant, nicht im Manifest 2.1.0)

| Feld | Wert |
|---|---|
| Index | 40 |
| Stufe | roh |
| Label | Sonstige Gebäude – OSM-Rohdaten |
| Beschreibung | OSM-Gebäude (building=*), die weder Seilbahn-Gebäude sind noch von einer amtlichen Widmungs- oder HiG-Fläche abgedeckt werden; der OSM-Anteil von general_buildings_source vor der Vereinigung mit den Kataster-Footprints. |
| Puffer | keiner |
| Quellen | osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | noch nicht zugeordnet |
| Sichtbar beim Laden | nein |

#### general_buildings_roh_dkm (geplant, nicht im Manifest 2.1.0)

| Feld | Wert |
|---|---|
| Index | 41 |
| Stufe | roh |
| Label | Sonstige Gebäude – Kataster-Rohdaten (DKM) |
| Beschreibung | Kataster-Footprints (DKM) bewohnter Einzellagen unter fünf Adressen sowie die Hüllen innerhalb Niederösterreichs; der Kataster-Anteil von general_buildings_source. |
| Puffer | keiner |
| Quellen | dkm_geoparquet: output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet (Stand Dateidatum 15.05.; erzeugtes Artefakt aus BEV-DKM); bev_adressregister: data/adressen/ (Stand Stichtag 01.10.2025) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | noch nicht zugeordnet |
| Sichtbar beim Laden | nein |

#### general_buildings_source

| Feld | Wert |
|---|---|
| Index | 12 |
| Stufe | quelle |
| Label | Sonstige Gebäude + Einzellagen (Quelle) |
| Beschreibung | Übrige OSM-Gebäude (Garagen, Schuppen, Ställe, Industrie, untypisiert) + bewohnte Einzellagen und NÖ-Streusiedlungs-Bauflächen (DKM/BEV) |
| Puffer | keiner |
| Quellen | osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026); dkm_geoparquet: output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet (Stand Dateidatum 15.05.; erzeugtes Artefakt aus BEV-DKM); bev_adressregister: data/adressen/ (Stand Stichtag 01.10.2025) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | noe_dkm_reconstructed |
| Sichtbar beim Laden | nein |

#### general_buildings_buffer

| Feld | Wert |
|---|---|
| Index | 13 |
| Stufe | zone |
| Label | Sonstige Gebäude (25 m) |
| Beschreibung | 25 m um general_buildings_source (praktisch nur der Fußabdruck) |
| Puffer | 25 m |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | general_buildings_source |
| Rolle | bedingung |
| Caveats | noe_dkm_reconstructed |
| Sichtbar beim Laden | ja |

### Verkehr

#### road_motorway_trunk

| Feld | Wert |
|---|---|
| Index | 14 |
| Stufe | zone |
| Label | Autobahn / Schnellstraße (150 m) |
| Beschreibung | 150 m buffer around motorway/trunk roads, tunnels excluded |
| Puffer | 150 m |
| Quellen | osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

#### road_federal_state

| Feld | Wert |
|---|---|
| Index | 15 |
| Stufe | zone |
| Label | Bundes- / Landesstraße (150 m) |
| Beschreibung | 150 m buffer around primary/secondary/tertiary roads, tunnels excluded |
| Puffer | 150 m |
| Quellen | osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

#### rail_main

| Feld | Wert |
|---|---|
| Index | 16 |
| Stufe | zone |
| Label | Hauptbahn (150 m) |
| Beschreibung | 150 m buffer around normal/narrow-gauge railway, tunnels excluded |
| Puffer | 150 m |
| Quellen | osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

#### cableway_people_150m

| Feld | Wert |
|---|---|
| Index | 17 |
| Stufe | zone |
| Label | Personenseilbahn (150 m) |
| Beschreibung | 150 m buffer around OSM people-carrying aerialways/lifts |
| Puffer | 150 m |
| Quellen | osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

### Militär

#### military_restricted_area

| Feld | Wert |
|---|---|
| Index | 18 |
| Stufe | zone |
| Label | Militärisches Sperrgebiet |
| Beschreibung | OSM military/landuse=military area polygons rasterized without extra buffer |
| Puffer | keiner |
| Quellen | osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

### Luftfahrt

#### airport_area_major

| Feld | Wert |
|---|---|
| Index | 19 |
| Stufe | zone |
| Label | Hauptflughafen-Areal |
| Beschreibung | Areal der Hauptflughäfen (config buffers.major_airport_osm_ids), OSM-Aerodrome-Polygone ohne Zusatzpuffer |
| Puffer | keiner |
| Quellen | osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

#### airport_runway_corridor_5km

| Feld | Wert |
|---|---|
| Index | 20 |
| Stufe | zone |
| Label | An-/Abflugkorridor (5 km) |
| Beschreibung | An-/Abflugkorridore der Hauptflughäfen: 5 km ab beiden Landebahn-Enden, ±15° um die verlängerte Bahnachse |
| Puffer | Kein isotroper Puffer: Korridor 5.000 m ab beiden Landebahn-Enden (AIRPORT_CORRIDOR_LENGTH_M), ±15° Halbwinkel um die verlängerte Bahnachse (AIRPORT_CORRIDOR_HALF_ANGLE_DEG). |
| Quellen | osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

### Σ Mensch

#### sources_human (geplant, nicht im Manifest 2.1.0)

| Feld | Wert |
|---|---|
| Index | 42 |
| Stufe | summe_quellen |
| Label | Σ Quellen Mensch (ungepuffert) |
| Beschreibung | ODER aller ungepufferten Quellen der Kategorie Mensch: Wohnbauland, die vier HiG-Quellen, Nicht-Wohn-Hüllen, Seilbahn-Gebäude, sonstige Gebäude, Militärflächen und Flughafen-Areale, dazu Autobahnen/Schnellstraßen, Bundes-/Landesstraßen, Hauptbahnen und Personenseilbahnen als ungepufferte Linien (0 m statt 150 m). Der An-/Abflugkorridor hat keine Objektquelle und ist nicht enthalten. |
| Puffer | keiner |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | official_settlement_source, haeuser_im_gruenen_ferienhaus, haeuser_im_gruenen_widmung, haeuser_im_gruenen_streusiedlung, haeuser_im_gruenen_noe_pdf, nonresidential_hulls_source, cableway_buildings_source, general_buildings_source, military_restricted_area, airport_area_major (plus Linien aus den Prep-Dateien) |
| Rolle | aggregat_kategorie |
| Caveats | noch nicht zugeordnet |
| Sichtbar beim Laden | nein |

#### exclusion_human

| Feld | Wert |
|---|---|
| Index | 27 |
| Stufe | summe_zonen |
| Label | Σ Ausschluss Mensch |
| Beschreibung | ODER-Verknüpfung aller Mensch-Ausschlüsse (Bänder 2, 7, 9, 11, 13, 14-20), auf das Staatsgebiet zugeschnitten. |
| Puffer | keiner |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | settlement_buffer, haeuser_im_gruenen, nonresidential_hulls_buffer, cableway_buildings_buffer, general_buildings_buffer, road_motorway_trunk, road_federal_state, rail_main, cableway_people_150m, military_restricted_area, airport_area_major, airport_runway_corridor_5km |
| Rolle | aggregat_kategorie |
| Caveats | noe_dkm_reconstructed |
| Sichtbar beim Laden | nein |

## Natur

### Schutzgebiete

#### nature_protection_areas

| Feld | Wert |
|---|---|
| Index | 21 |
| Stufe | zone |
| Label | Naturschutzgebiete (amtlich) |
| Beschreibung | Official protection areas: NP, NSG, ESG/Natura2000, Ramsar |
| Puffer | keiner |
| Quellen | naturschutzgebiete: data/natur/SG_AT_2024_v_April_Stand_3_April_2024.zip (Stand 03.04.2024) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

#### osm_nature_protection_areas

| Feld | Wert |
|---|---|
| Index | 22 |
| Stufe | zone |
| Label | Naturschutzgebiete (OSM) |
| Beschreibung | OSM protected/nature areas |
| Puffer | keiner |
| Quellen | osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

### Σ Natur

#### sources_nature (geplant, nicht im Manifest 2.1.0)

| Feld | Wert |
|---|---|
| Index | 43 |
| Stufe | summe_quellen |
| Label | Σ Quellen Natur (ungepuffert) |
| Beschreibung | ODER der Natur-Quellen nature_protection_areas und osm_nature_protection_areas. In der Kategorie Natur gibt es keine Puffer, das Band ist inhaltsgleich mit exclusion_nature und existiert nur, damit jede Kategorie denselben Aufbau hat. |
| Puffer | keiner |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | nature_protection_areas, osm_nature_protection_areas |
| Rolle | aggregat_kategorie |
| Caveats | noch nicht zugeordnet |
| Sichtbar beim Laden | nein |

#### exclusion_nature

| Feld | Wert |
|---|---|
| Index | 28 |
| Stufe | summe_zonen |
| Label | Σ Ausschluss Natur |
| Beschreibung | ODER der Natur-Bänder (21-22), auf das Staatsgebiet zugeschnitten. |
| Puffer | keiner |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | nature_protection_areas, osm_nature_protection_areas |
| Rolle | aggregat_kategorie |
| Caveats | keine |
| Sichtbar beim Laden | nein |

## Geografie

### Kriterien

#### geography_slope_too_steep

| Feld | Wert |
|---|---|
| Index | 23 |
| Stufe | zone |
| Label | Hangneigung zu steil |
| Beschreibung | Slope above configured exclusion threshold |
| Puffer | keiner |
| Quellen | dgm_25m: data/gelaende/DGM_R25.tif (Stand 30.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

#### geography_elevation_too_high

| Feld | Wert |
|---|---|
| Index | 24 |
| Stufe | zone |
| Label | Seehöhe zu hoch |
| Beschreibung | Elevation above configured exclusion threshold |
| Puffer | keiner |
| Quellen | dgm_25m: data/gelaende/DGM_R25.tif (Stand 30.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

#### geography_wind_too_low

| Feld | Wert |
|---|---|
| Index | 25 |
| Stufe | zone |
| Label | Windhöffigkeit zu gering |
| Beschreibung | Power density below configured wind threshold |
| Puffer | keiner |
| Quellen | wind_leistungsdichte_150m: data/gelaende/AUT_power-density_150m.tif (Stand 29.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

#### geography_water_bodies

| Feld | Wert |
|---|---|
| Index | 26 |
| Stufe | zone |
| Label | Größere Gewässer |
| Beschreibung | Größere Wasserkörper (Seen/Stauseen/Flüsse) aus OSM, verbundene Flächen >= WATER_MIN_AREA_HA |
| Puffer | keiner |
| Quellen | osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026) |
| Abgeleitet von | – |
| Rolle | bedingung |
| Caveats | keine |
| Sichtbar beim Laden | ja |

### Σ Geografie

#### sources_geography (geplant, nicht im Manifest 2.1.0)

| Feld | Wert |
|---|---|
| Index | 44 |
| Stufe | summe_quellen |
| Label | Σ Quellen Geografie (ungepuffert) |
| Beschreibung | ODER der Geografie-Kriterien Hangneigung, Seehöhe, Windhöffigkeit und Gewässer. Es gibt keine Puffer, das Band ist inhaltsgleich mit exclusion_geography und existiert nur der Einheitlichkeit halber. |
| Puffer | keiner |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | geography_slope_too_steep, geography_elevation_too_high, geography_wind_too_low, geography_water_bodies |
| Rolle | aggregat_kategorie |
| Caveats | noch nicht zugeordnet |
| Sichtbar beim Laden | nein |

#### exclusion_geography

| Feld | Wert |
|---|---|
| Index | 29 |
| Stufe | summe_zonen |
| Label | Σ Ausschluss Geografie |
| Beschreibung | ODER der Geografie-Bänder (23-26), auf das Staatsgebiet zugeschnitten. |
| Puffer | keiner |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | geography_slope_too_steep, geography_elevation_too_high, geography_wind_too_low, geography_water_bodies |
| Rolle | aggregat_kategorie |
| Caveats | keine |
| Sichtbar beim Laden | nein |

## Ergebnis

#### all_exclusions

| Feld | Wert |
|---|---|
| Index | 30 |
| Stufe | summe_zonen |
| Label | Σ Ausschluss gesamt |
| Beschreibung | ODER von 27-29: alles, was ausgeschlossen ist. |
| Puffer | keiner |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | exclusion_human, exclusion_nature, exclusion_geography |
| Rolle | aggregat_gesamt |
| Caveats | noe_dkm_reconstructed |
| Sichtbar beim Laden | nein |

#### available_after_all_exclusions_raw

| Feld | Wert |
|---|---|
| Index | 31 |
| Stufe | ergebnis |
| Label | Verfügbare Fläche, roh |
| Beschreibung | Das Negativ von all_exclusions - verfügbare Fläche ohne Mindestgrößen-Filter. |
| Puffer | keiner |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | all_exclusions |
| Rolle | verfuegbarkeit_roh |
| Caveats | noe_dkm_reconstructed |
| Sichtbar beim Laden | nein |

#### available_cleaned_min_10ha

| Feld | Wert |
|---|---|
| Index | 32 |
| Stufe | ergebnis |
| Label | Verfügbare Fläche, bereinigt (≥ 10 ha) |
| Beschreibung | Das Endergebnis: die rohe verfügbare Fläche, bereinigt um Splitter - nur zusammenhängende Flächen ab 10 ha (4er-Nachbarschaft). |
| Puffer | keiner |
| Quellen | keine (abgeleitet) |
| Abgeleitet von | available_after_all_exclusions_raw |
| Rolle | verfuegbarkeit_bereinigt |
| Caveats | noe_dkm_reconstructed |
| Sichtbar beim Laden | ja |

## Referenz

#### official_wind_zoning

| Feld | Wert |
|---|---|
| Index | 37 |
| Stufe | zone |
| Label | Amtliche Windkraft-Zonen |
| Beschreibung | Alle amtlichen Windkraft-Positivzonen der Länder in einem Band: NÖ Zonierung (71 Zonen, LGBl. 47/2024), Steiermark SAPRO Vorrang-/Eignungszonen, Salzburg Vorrangzonen, Burgenland Eignungszonen, Kärnten RED-III-Beschleunigungszonen. Dient dem Soll-Ist-Vergleich mit der Abschichtung, ist selbst kein Ausschluss. |
| Puffer | keiner |
| Quellen | amtliche_windzonen_noe: data/zonen/zonierung_noe.json (Stand LGBl. 47/2024, 71 Zonen (Dateidatum 30.04.2026)); amtliche_windzonen_bgld: data/zonen/WK_Eignungszonen.zip (Stand EXPORT_DAT 20260721); amtliche_windzonen_ktn: data/zonen/RED_III_Windkraftbeschleunigungszone.zip (Stand unbekannt — zu klären); amtliche_windzonen_stmk_sbg: data/zonen/luca_zonen/Stmk.shp, data/zonen/luca_zonen/Sbg.shp (Stand unbekannt — zu klären (handdigitalisiert, nicht amtlich bezogen)); verwaltungsgrenzen_vgd: data/admin/VGD_Oesterreich_gen_50_20221002/VGD_50_generalisiert.shp (Stand 02.10.2022) |
| Abgeleitet von | – |
| Rolle | referenz |
| Caveats | keine |
| Sichtbar beim Laden | ja |

#### wka_bestand_ausserhalb_zonen

| Feld | Wert |
|---|---|
| Index | 38 |
| Stufe | zone |
| Label | WKA-Bestand außerhalb der Zonen |
| Beschreibung | Bestehende Windräder aus OSM, die AUSSERHALB der amtlichen Zonen stehen, zu Park-Hüllen zusammengefasst (Anlagen mit < 750 m Abstand bilden einen Park; konvexe Hülle + 200 m Rand). Referenzband, kein Ausschluss.

**Geplante Änderung:** Die Park-Hüllen werden nach dem Bilden gegen official_wind_zoning abgezogen, sodass das Band ausschließlich außerhalb der amtlichen Zonen liegt (heute können Hülle + 200 m Rand in Zonen hineinragen). |
| Puffer | keiner |
| Quellen | osm_pbf: data/osm/austria-260330.osm.pbf (Stand 30.03.2026) |
| Abgeleitet von | official_wind_zoning |
| Rolle | referenz |
| Caveats | keine |
| Sichtbar beim Laden | ja |

## Anhang: ausgeblendete Bänder

Die vier Unschärfebänder sind Zwischenprodukte der räumlichen Glättung von `available_cleaned_min_10ha` mit unterschiedlichen Sigma-Werten und standardmäßig ausgeblendet.

| Index | Name | Label | Beschreibung |
|---|---|---|---|
| 33 | available_blur_sigma_100m | Unschärfe σ 100 m | Gauß-geglättete Eignungsfläche (Werte 0-100 %): der gewichtete Anteil verfügbarer Fläche in der Umgebung jeder Zelle, Glättungsradius Sigma 100 m. Basis ist die ROHE verfügbare Fläche, daher sind auch Flächen unter der Mindestgrößen-Schwelle sichtbar. 100 = tief in einer großen Zone, ~50 = an der Kante, schmale Splitter verwaschen. |
| 34 | available_blur_sigma_200m | Unschärfe σ 200 m | Gauß-geglättete Eignungsfläche (Werte 0-100 %): der gewichtete Anteil verfügbarer Fläche in der Umgebung jeder Zelle, Glättungsradius Sigma 200 m. Basis ist die ROHE verfügbare Fläche, daher sind auch Flächen unter der Mindestgrößen-Schwelle sichtbar. 100 = tief in einer großen Zone, ~50 = an der Kante, schmale Splitter verwaschen. |
| 35 | available_blur_sigma_250m | Unschärfe σ 250 m | Gauß-geglättete Eignungsfläche (Werte 0-100 %): der gewichtete Anteil verfügbarer Fläche in der Umgebung jeder Zelle, Glättungsradius Sigma 250 m. Basis ist die ROHE verfügbare Fläche, daher sind auch Flächen unter der Mindestgrößen-Schwelle sichtbar. 100 = tief in einer großen Zone, ~50 = an der Kante, schmale Splitter verwaschen. |
| 36 | available_blur_sigma_300m | Unschärfe σ 300 m | Gauß-geglättete Eignungsfläche (Werte 0-100 %): der gewichtete Anteil verfügbarer Fläche in der Umgebung jeder Zelle, Glättungsradius Sigma 300 m. Basis ist die ROHE verfügbare Fläche, daher sind auch Flächen unter der Mindestgrößen-Schwelle sichtbar. 100 = tief in einer großen Zone, ~50 = an der Kante, schmale Splitter verwaschen. |

## Herkunft dieses Dokuments

Dieses Dokument wurde am 2026-09-09 aus `abschichtung.bands.json` (Schema 2.1.0, 38 Bänder) sowie dem Umbau-Vorschlag v4 vom selben Tag generiert (Bänder 39–44, noch nicht im Manifest). Es ist als Vorlage gedacht, die der Produzent künftig direkt aus dem Manifest neu generieren kann, sobald die geplanten Bänder dort ergänzt wurden.
