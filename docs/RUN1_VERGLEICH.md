# Vergleich: erster vollständiger Kettenlauf (run1) gegen Referenz-TIF

Gemessen am 06.09.2026, ein Lauf auf einer Maschine (keine Garantie für
andere Umgebungen). Referenz: `output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2.tif`
(unangetastet). Neu: `output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.tif`.

## 1. Ergebnis des Laufs

Alle fünf Stufen liefen ohne Fehler durch (`exit_code: 0` in jeder Zeile),
`run_chain.sh` endete mit `run_chain.sh completed successfully`, `05_validate.py`
meldete `PASS=8 | FAIL=0 | SKIP=0 | MISSING=0`.

## 2. Laufzeiten

| Stufe | Skript | Dauer |
| --- | --- | --- |
| 1 build_official_zoning_layers | `01_build_official_zoning_layers.py` | 49 s |
| 2 build_hig_sources | `02_build_hig_sources.py` | 143 s (2 min 23 s) |
| 3 build_osm_layers | `03_build_osm_layers.py` | 375 s (6 min 15 s) |
| 4 create_distance_zones | `04_create_distance_zones.py` | 298 s (4 min 58 s) |
| 5 validate | `05_validate.py` | 1 s |
| **Gesamt** | | **866 s (14 min 26 s)** |

Wichtiger Befund: Die im README zuvor stehende Schätzung „mehrere Stunden“
trifft für **diesen** Lauf nicht zu. Grund vermutlich: warme Caches beim
Start — die Adressregister-Parquets unter `data/adressregister/` waren
bereits vom 23./24. Juli vorhanden und wurden von Stufe 2 nicht neu
geschrieben (siehe Abschnitt 6), und der OSM-PBF-Extract-Cache unter
`output/abschichtung/osm_pbf_layers/` war beim Start bereits teilweise
befüllt. Ein Kaltstart ohne diese Caches dürfte deutlich länger dauern.

## 3. Struktur

- Bandanzahl: Referenz 38, neu 38 — identisch.
- Alle 38 Bandnamen stimmen positionsgenau überein (Reihenfolge 1:1
  identisch, keine einzige Abweichung). Vollständige Liste (Index, Name):

| # | Bandname |
| - | --- |
| 1 | official_settlement_source |
| 2 | settlement_buffer |
| 3 | haeuser_im_gruenen_ferienhaus |
| 4 | haeuser_im_gruenen_widmung |
| 5 | haeuser_im_gruenen_streusiedlung |
| 6 | haeuser_im_gruenen_noe_pdf |
| 7 | haeuser_im_gruenen |
| 8 | nonresidential_hulls_source |
| 9 | nonresidential_hulls_buffer |
| 10 | cableway_buildings_source |
| 11 | cableway_buildings_buffer |
| 12 | general_buildings_source |
| 13 | general_buildings_buffer |
| 14 | road_motorway_trunk |
| 15 | road_federal_state |
| 16 | rail_main |
| 17 | cableway_people_150m |
| 18 | military_restricted_area |
| 19 | airport_area_major |
| 20 | airport_runway_corridor_5km |
| 21 | nature_protection_areas |
| 22 | osm_nature_protection_areas |
| 23 | geography_slope_too_steep |
| 24 | geography_elevation_too_high |
| 25 | geography_wind_too_low |
| 26 | geography_water_bodies |
| 27 | exclusion_human |
| 28 | exclusion_nature |
| 29 | exclusion_geography |
| 30 | all_exclusions |
| 31 | available_after_all_exclusions_raw |
| 32 | available_cleaned_min_10ha |
| 33 | available_blur_sigma_100m |
| 34 | available_blur_sigma_200m |
| 35 | available_blur_sigma_250m |
| 36 | available_blur_sigma_300m |
| 37 | official_wind_zoning |
| 38 | wka_bestand_ausserhalb_zonen |

- dtype (beide `uint8`), shape (14001 × 24001), CRS (EPSG:31287) und
  Affine-Transform sind bei beiden Rastern identisch.

## 4. Globale Tags

26 Tag-Schlüssel, **alle identisch** in Wert zwischen Referenz und neuem
Lauf: `AIRPORT_CORRIDOR_HALF_ANGLE_DEG`, `AIRPORT_CORRIDOR_LENGTH_M`,
`AREA_OR_POINT`, `BAND_SCHEMA`, `BEWOHNTE_EINZELLAGEN`,
`CABLEWAY_BUILDING_BUFFER_M`, `DISTANCE_ENGINE`, `DROPPED_HUMAN_BANDS`,
`GENERAL_BUILDING_BUFFER_M`, `HIG_CHAIN_M`, `HIG_FAMILY_BUFFER_M`,
`HIG_MIN_ADRESSEN`, `HIG_SOURCE`, `MIN_FRAGMENT_AREA_HA`,
`NONRESIDENTIAL_HULL_BUFFER_M`, `PIPELINE`, `POWER_LINES`,
`SETTLEMENT_BUFFER_BY_BL`, `SETTLEMENT_BUFFER_VARIANTS`,
`UNCERTAINTY_BLUR_SIGMAS_M`, `UNCERTAINTY_BLUR_SOURCE`, `WATER_MIN_AREA_HA`,
`WICHTIGE_OBJEKTE`, `WIEN`, `WKA_CLUSTER_CHAIN_M`, `WKA_HULL_MARGIN_M`.

Keine abweichenden Werte, keine Schlüssel, die nur in einer der beiden
Dateien vorkommen.

**Unerwarteter Befund:** Laut Auftrag sollte `SETTLEMENT_BUFFER_VARIANT_NAMES`
in der Referenz fehlen (impliziert: in der neuen Datei vorhanden). Tatsächlich
fehlt dieser Schlüssel als GDAL-Tag in **beiden** TIFs — weder Referenz noch
run1 tragen ihn auf Raster-Tag-Ebene. Er taucht nur im `parameters`-Objekt
des `run1`-Manifests (JSON, s. u.) als leerer String auf, nicht als Tag im
TIF selbst.

`AREA_OR_POINT` (der von GDAL automatisch gesetzte Schlüssel): in der
Referenz `Area`, in run1 ebenfalls `Area` — vorhanden und identisch in
beiden, keine Abweichung.

## 5. Pixelzählung pro Band (Set-Pixel, ungleich Null)

| # | Band | Referenz | run1 | Diff (abs) | Diff (%) |
| - | --- | ---: | ---: | ---: | ---: |
| 1 | official_settlement_source | 6.071.385 | 6.071.380 | −5 | −0,0001 % |
| 2 | settlement_buffer | 73.657.495 | 73.657.495 | 0 | 0,0000 % |
| 3 | haeuser_im_gruenen_ferienhaus | 47.345 | 47.345 | 0 | 0,0000 % |
| 4 | haeuser_im_gruenen_widmung | 376.976 | 376.973 | −3 | −0,0008 % |
| 5 | haeuser_im_gruenen_streusiedlung | 984.118 | 984.105 | −13 | −0,0013 % |
| 6 | haeuser_im_gruenen_noe_pdf | 19.021.507 | 19.021.507 | 0 | 0,0000 % |
| 7 | haeuser_im_gruenen | 65.438.466 | 65.438.452 | −14 | −0,0000 % |
| 8 | nonresidential_hulls_source | 547.366 | 547.350 | −16 | −0,0029 % |
| 9 | nonresidential_hulls_buffer | 975.961 | 975.940 | −21 | −0,0022 % |
| 10 | cableway_buildings_source | 30.337 | 30.336 | −1 | −0,0033 % |
| 11 | cableway_buildings_buffer | 157.175 | 157.172 | −3 | −0,0019 % |
| 12 | general_buildings_source | 1.844.308 | 1.844.269 | −39 | −0,0021 % |
| 13 | general_buildings_buffer | 4.196.094 | 4.196.028 | −66 | −0,0016 % |
| 14 | road_motorway_trunk | 1.375.022 | 1.375.022 | 0 | 0,0000 % |
| 15 | road_federal_state | 18.032.559 | 18.032.559 | 0 | 0,0000 % |
| 16 | rail_main | 3.088.276 | 3.088.276 | 0 | 0,0000 % |
| 17 | cableway_people_150m | 1.138.218 | 1.138.218 | 0 | 0,0000 % |
| 18 | military_restricted_area | 537.291 | 537.291 | 0 | 0,0000 % |
| 19 | airport_area_major | 30.892 | 30.892 | 0 | 0,0000 % |
| 20 | airport_runway_corridor_5km | 187.506 | 187.506 | 0 | 0,0000 % |
| 21 | nature_protection_areas | 23.247.789 | 23.247.789 | 0 | 0,0000 % |
| 22 | osm_nature_protection_areas | 18.387.599 | 18.387.599 | 0 | 0,0000 % |
| 23 | geography_slope_too_steep | 59.450.943 | 59.450.943 | 0 | 0,0000 % |
| 24 | geography_elevation_too_high | 4.115.709 | 4.115.709 | 0 | 0,0000 % |
| 25 | geography_wind_too_low | 222.044.710 | 222.044.710 | 0 | 0,0000 % |
| 26 | geography_water_bodies | 1.969.388 | 1.969.387 | −1 | −0,0001 % |
| 27 | exclusion_human | 90.789.073 | 90.789.044 | −29 | −0,0000 % |
| 28 | exclusion_nature | 27.657.268 | 27.657.268 | 0 | 0,0000 % |
| 29 | exclusion_geography | 73.927.677 | 73.927.676 | −1 | −0,0000 % |
| 30 | all_exclusions | 127.420.725 | 127.420.720 | −5 | −0,0000 % |
| 31 | available_after_all_exclusions_raw | 6.853.412 | 6.853.417 | +5 | +0,0001 % |
| 32 | **available_cleaned_min_10ha** | 5.853.871 | 5.853.876 | **+5** | **+0,0001 %** |
| 33 | available_blur_sigma_100m | 21.856.795 | 21.856.795 | 0 | 0,0000 % |
| 34 | available_blur_sigma_200m | 32.433.497 | 32.433.497 | 0 | 0,0000 % |
| 35 | available_blur_sigma_250m | 36.822.227 | 36.822.227 | 0 | 0,0000 % |
| 36 | available_blur_sigma_300m | 40.835.277 | 40.835.277 | 0 | 0,0000 % |
| 37 | official_wind_zoning | 633.891 | 633.891 | 0 | 0,0000 % |
| 38 | wka_bestand_ausserhalb_zonen | 276.218 | 276.218 | 0 | 0,0000 % |

**Einordnung (Vermutung, keine Erklärung, die die Abweichungen wegdiskutiert):**

- 20 der 38 Bänder sind pixelgenau identisch (Diff = 0).
- Die Bänder mit Abweichungen liegen alle in der Human-Exclusion-Kette
  (Bänder 1, 4, 5, 7–13) plus einem Einzelpixel bei `geography_water_bodies`
  (26) und den daraus abgeleiteten Summenbändern 27, 29, 30, 31, 32. Die
  reinen OSM-/Infrastruktur-Bänder (14–25, 33–38) sind alle exakt gleich.
- Größenordnung der Abweichungen: durchgängig < 0,004 % der jeweiligen
  Bandfläche, absolut zwischen 1 und 66 Pixeln (bei 25 m Rasterweite je
  Pixel ≙ 625 m² — 66 Pixel ≈ 4,1 ha bei `general_buildings_buffer`).
- **Band 32 (`available_cleaned_min_10ha`, veröffentlichte Potenzialfläche):
  +5 Pixel (+0,0001 %)** — technisch eine Abweichung, praktisch im Rauschen.
- Gruppensummen: Band 27 (`exclusion_human`) −29, Band 30
  (`all_exclusions`) −5, Band 31 (`available_after_all_exclusions_raw`) +5.
  Alle drei ebenfalls < 0,0001 %.
- Mögliche legitime Ursachen (laut Auftrag zu nennen, nicht zu bestätigen):
  neuere Rohdaten zwischen den beiden Läufen, der 4-Konnektivitäts-Fix im
  `min_area_filter`, der OSM-Cache-Key-Fix. Welche davon tatsächlich
  ursächlich ist, wurde hier nicht weiter untersucht — das war nicht
  Teil dieses Beobachtungsauftrags.

## 6. Adressregister-Caches (Stufe 2)

`data/adressregister/bev_gebaeude_31287.parquet` (mtime 24.07., 00:11) und
`data/adressregister/adressen_31287.parquet` (mtime 23.07., 20:18) wurden
von Stufe 2 (`02_build_hig_sources.py`) **nicht neu geschrieben** — mtime und
Größe vor und nach dem Lauf sind identisch. Die Staleness-Prüfung in
`bev_register.py` hat die vorhandenen Dateien offenbar als aktuell genug
akzeptiert und keinen Rebuild ausgelöst.

## 7. Manifest-Vergleich (`..._run1.bands.json` gegen das zuvor generierte
Referenz-Manifest)

Referenz-Manifest: `.../scratchpad/osm_wka_distance_zones_widmung_v2.bands.json`
(generiert 2026-09-06T11:53:59Z aus der Referenz-TIF).
Neues Manifest: `output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.bands.json`
(vom Lauf selbst geschrieben, `generated_at` 2026-09-06T15:53:17Z).

**Vertragsfelder — Verdikt: bestehen.**

- `band_count`: 38 in beiden — identisch.
- `bands[].index` und `bands[].name`: für alle 38 Einträge positionsgenau
  identisch zwischen Referenz-Manifest und run1-Manifest. Keine einzige
  Abweichung gefunden.
- Alle weiteren Pro-Band-Felder (soweit vorhanden) stimmen ebenfalls
  überein — keine Feld-Diffs unterhalb der Bandebene.

**Legitime Unterschiede (erwartet):**

- `generated_at`: Referenz `2026-09-06T11:53:59Z`, neu `2026-09-06T15:53:17Z`
  — Zeitstempel des jeweiligen Manifest-Laufs, erwartungsgemäß verschieden.
- `raster_file`: Referenz `osm_wka_distance_zones_widmung_v2.tif`, neu
  `osm_wka_distance_zones_widmung_v2_run1.tif` — erwartungsgemäß verschieden.
- `parameters`: inhaltlich bis auf einen zusätzlichen Schlüssel identisch
  (Werte aller gemeinsamen Schlüssel stimmen überein, nur die
  Objekt-Reihenfolge unterscheidet sich, was in JSON keine semantische
  Bedeutung hat). Der neue Lauf trägt zusätzlich
  `SETTLEMENT_BUFFER_VARIANT_NAMES: ""` (leerer String) — dieser Schlüssel
  fehlt im Referenz-Manifest komplett. Das deckt sich mit der im Auftrag
  genannten Erwartung, dass dieser Name im Referenz-Artefakt fehlt —
  wichtig für die Einordnung: als GDAL-Raster-Tag existiert er in **keinem**
  der beiden TIFs (siehe Abschnitt 4), er wird offenbar nur vom
  Manifest-Emitter mit Default-Wert `""` ergänzt.

**Nicht als „legitim“ im Auftrag genannt, aber inhaltlich plausibel und hier
als Befund gemeldet, nicht weggeklärt:**

- `caveats`: unterscheiden sich inhaltlich. Referenz-Manifest hat einen
  Caveat-Eintrag (`noe_dkm_reconstructed`) mit kürzerem `text_de`. Das
  run1-Manifest hat denselben Caveat mit **erweitertem** Text (zusätzlicher
  Absatz zum Wirkungspfad über Band 12/13 in die Summenbänder 27/30/31/32
  und weiter in die Unschärfebänder 33–36) **und einen zusätzlichen zweiten
  Caveat-Eintrag** `blur_bands_bleed_across_border` (Bänder 33–36), der im
  Referenz-Manifest komplett fehlt. Das ist eine Änderung im
  Manifest-Emitter/Caveat-Text zwischen den beiden Generierungszeitpunkten,
  keine Abweichung der Rasterdaten selbst — aber ein Unterschied, den
  Konsumenten des Manifests bemerken werden.

## 8. Speicherplatz

Wächter-Schwelle 5 GiB wurde nicht erreicht — kein einziger Messwert lag
unter der Schwelle, der Lauf wurde nicht abgebrochen.

Verlauf während der Beobachtung (Volume `/System/Volumes/Data`):

| Zeitpunkt | frei | belegt % | Stufe |
| --- | ---: | ---: | --- |
| 15:43:27 (Start Beobachtung) | 41 GiB (44.103.294.976 B) | 96 % | Stufe 3 |
| Minimum während Lauf | 38 GiB (40.342.515.712 B) | 96 % | Stufe 4 |
| 15:51:54 (letzte Messung vor Abschluss) | 39 GiB (41.383.378.944 B) | 96 % | Stufe 4 |
| nach Laufende (Endzustand) | 38 GiB (~41.304.436.736 B) | 96 % | — |

Laut Auftraggeber lagen beim Start des Laufs (PID 29989) 47 GiB frei bei
95 % Belegung vor — die erste eigene Messung dieser Beobachtung (5 Minuten
später) zeigte bereits 41 GiB bei 96 %. Der Rückgang von 47 auf ~41 GiB
in den ersten Minuten liegt vermutlich an anderen Prozessen auf derselben
Maschine, nicht zwingend an diesem Lauf allein — das wurde nicht isoliert
geprüft.

`output/`-Gesamtgröße nach Laufende: **11 GB**, aufgeschlüsselt:

| Verzeichnis | Größe |
| --- | --- |
| `output/kataster` | 5,0 GB |
| `output/abschichtung` (davon `osm_pbf_layers/`-Cache: 4,6 GB) | 4,6 GB |
| `output/abschichtung_widmung_v2` | 1,0 GB |
| `output/noe` | 34 MB |

Innerhalb von `output/abschichtung_widmung_v2/`: `zoning_vectors` 733 MB,
`osm_wka_distance_zones_widmung_v2_run1.tif` 129 MB (Referenz-TIF zum
Vergleich: 119 MB — Größenunterschied wird durch das Manifest bzw.
Kompression erklärt, nicht untersucht), `distance_layers` 40 MB,
`hig_huellen.gpkg` 20 MB.

## 9. Integrität

- Referenz-TIF-Inode in diesem Repo vor und nach dem Lauf: **unverändert**
  (`139711915`), Größe unverändert (124.686.003 Bytes), mtime unverändert
  (06.09.2026 14:16:52) — die Referenz-TIF wurde vom Lauf nicht angefasst.
- SHA-256 der Referenz-TIF in diesem Repo:
  `9cf3d5f1097830c3e5752b9f43abf3b76cc3f7c2f25a3d437baa710e700eafbb`
- SHA-256 der Kopie in `windkraft_ö_karten` (Alt-Repo, read-only):
  identischer Wert `9cf3d5f1097830c3e5752b9f43abf3b76cc3f7c2f25a3d437baa710e700eafbb`
  — `cmp` bestätigt byte-identisch. (Unterschiedliche Inodes, 137771182 im
  Alt-Repo vs. 139711915 hier — also keine Hardlink-Kopplung zwischen den
  Repos bei dieser Datei, aber inhaltlich exakt gleich.)
- `git -C /Users/jhurt/Documents/windkraft_ö_karten status --short`: leere
  Ausgabe — Alt-Repo unverändert.
- `make check-hardlinks`:
  `OK: 79 Dateien geprüft (77 unter output/, 2 deklarierte Schreibziele
  unter data/) — keine Hardlink-Verstöße gefunden.`

## 10. Rangliste aller gefundenen Abweichungen

1. **Laufzeit weicht stark von der bisherigen README-Angabe ab**: ~14,5
   Minuten gemessen statt der dokumentierten „mehrere Stunden“ — vermutlich
   warme Caches, nicht untersucht, im README jetzt vermerkt.
2. **`caveats` im Manifest inhaltlich unterschiedlich** (erweiterter Text
   bei `noe_dkm_reconstructed`, zusätzlicher Caveat
   `blur_bands_bleed_across_border`) — Emitter-/Dokumentationsänderung
   zwischen den beiden Generierungszeitpunkten, nicht rasterdatenbezogen.
3. **Pixel-Abweichungen in 18 von 38 Bändern** (Human-Exclusion-Kette,
   inkl. Band 32 mit +5 Pixel und den Summenbändern 27/30/31), alle
   < 0,004 % — plausibel, aber nicht abschließend auf eine Ursache
   zurückgeführt.
4. **`SETTLEMENT_BUFFER_VARIANT_NAMES` fehlt als Raster-Tag in beiden
   TIFs**, obwohl der Auftrag erwartete, dass er zumindest in der neuen
   Datei als Tag vorhanden ist — er taucht nur im Manifest-JSON als leerer
   String auf, nicht im TIF selbst.
5. Größenunterschied Referenz-TIF (119 MB) vs. run1-TIF (129 MB) trotz
   identischer Bandanzahl/Auflösung/dtype — nicht untersucht, vermutlich
   Kompressionsartefakt.

Alles Übrige (Bandnamen/-reihenfolge, 20 von 38 Bändern pixelgenau,
alle 26 globalen Tags, Vertragsfelder des Manifests, Referenz-TIF-Integrität,
Adressregister-Caches, Hardlink-Sicherheit) ist ohne Befund identisch bzw.
wie erwartet.
