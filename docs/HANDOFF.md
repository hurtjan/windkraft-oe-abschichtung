# Handoff: das Widmung-v2-GeoTIFF für Konsumenten

Dieses Dokument richtet sich an alle, die das Ergebnis der Widmung-v2-Kette
weiterverarbeiten — Dashboard, Viewer, Auswertungsskripte, gleich welches
Repo. Es beschreibt den Vertrag, an den ihr euch halten könnt, und die
Grube, in die die letzte Umstellung (v1 → v2) bereits einmal geführt hat.

**Stand: 08.09.2026.** Anders als in der ersten Fassung dieses Dokuments ist
das hier beschriebene Artefakt **kein aus dem Vorgänger-Repo übernommenes
Referenzstück mehr, sondern die Ausgabe dieses Repos.** Die umgebaute Kette
(`make layers` → `make finalize`) hat es aus den 33 Checkpoint-Layern unter
`build/layers/` komponiert; `pipeline/finalize.py` ist der Erzeuger. Der
Vertrag unten gilt damit nicht mehr nur „für das Schema", sondern für eine
Datei, die dieses Repo reproduzierbar herstellt.

## Die zwei Dateien

Jeder Lauf von `pipeline/finalize.py` (`make -f make/finalize/finalize.mk
finalize`, bzw. `uv run python -m pipeline.finalize`) schreibt zwei Dateien,
die zusammengehören und nur zusammen ausgeliefert werden:

- **`out/abschichtung.tif`** — das eigentliche Raster, 45 Bänder, `uint8`,
  EPSG:31287, 25 m Pixelgröße.
- **`out/abschichtung.bands.json`** — das Sidecar-Manifest
  (`<stem>.bands.json`), geschrieben von `windkraft/calc/band_manifest.py`
  direkt im Anschluss an das GeoTIFF, aus denselben Werten (Bandnamenliste,
  Datei-Tags), ohne das Raster erneut zu öffnen. Bandzahl, -namen und
  -reihenfolge im Manifest sind deshalb per Konstruktion identisch mit dem
  TIF — es gibt keinen zweiten Erzeugungspfad, der auseinanderlaufen könnte.

Nehmt nie das eine ohne das andere entgegen. Ein TIF ohne sein Manifest hat
keine maschinenlesbare Aussage mehr darüber, was Band 17 bedeutet.

Beide Pfade sind in `pipeline/contract.py` als
`PRODUCTS["abschichtung_tif"]` und `PRODUCTS["abschichtung_bands_json"]`
deklariert — wer sie in diesem Repo braucht, importiert sie von dort, statt
den Pfad ein zweites Mal hinzuschreiben.

### Die aktuelle Referenzausgabe

| | |
|---|---|
| Datei | `out/abschichtung.tif` |
| `sha256` | `58caa8ffa69454fdc691fff96d5734f0820dfac07be11238d38330a720ee3a93` |
| Größe | 147.090.672 Bytes |
| Bänder | 45 |
| Manifest-`schema_version` | `2.3.0` |

Diese Prüfsumme ist verdrahtet: `tests/test_referenz_tif.py` prüft sie bei
jedem `make test` (siehe dort auch, wie der langlaufende Reproduktionstest
gezielt ausgeführt wird). Sie ändert sich nicht beiläufig — wenn doch,
gehört das gemessen, begründet und in `docs/rewrite/abweichungen.tsv`
eingetragen.

**Siebter Referenzwechsel (13.10.2026, Schutzgebiete nur verordnet):** Natur-Ausschluss (Band 28) = nur
amtliche Schutzgebiete (Band 21), die nach Naturschutzrecht der Länder per
Verordnung oder Bescheid festgelegt sind. Neu aus UBA: `GLT_AT_2024`,
`NDKM_AT_2024` (Naturdenkmäler, auch Punkte) und `S_AT_2024` (alle gültigen
`KAT_SUB`-Codes: RG, RZ, PSG, SSG, SAFM, `SG §26`, GB, GLR, GNÖB, ÖE, ÖSG). OSM-Schutzgebiete (Band 22)
bleiben als reine Information (ohne Naturpark/Biosphärenpark, ohne schwache
`protect_class` 5) und gehen weder in Band 28 noch in Band 43 ein. Bandzahl
bleibt 45. Vorwert: sha256 `bdf0e41104b83a81567b94138c52a199cd984161dcc315cf3a42f04bd68b890e`,
146.830.572 Bytes. Neuer Wert: sha256
`58caa8ffa69454fdc691fff96d5734f0820dfac07be11238d38330a720ee3a93`,
147.090.672 Bytes. Wirkung (AT, km2): Natur-Ausschluss (kategorie.natur)
24.023 -> 23.648; amtliche Schutzgebiete 22.581 -> 23.648; OSM-Schutzgebiete
(Information) 9.957 -> 6.664; Ausschluss gesamt 80.182 -> 80.169; Eignung >= 10 ha
3.171 -> 3.177. Größte Länderverschiebung: Vorarlberg Natur 765 -> 449 km2, Tirol
amtlich 2.545 -> 3.462 km2.

**Sechster Referenzwechsel (12.10.2026, Landschaftsschutzgebiete aus UBA):**
Landschaftsschutzgebiete kommen aus UBA (`LSG_AT_2024`), OSM liefert keinen
Landschaftsschutz mehr. Schema `2.3.0`, 45 Bänder. Vorwert: sha256
`b596fd021dbc42eb4bfa19b9caf8fead78cad6489f6f91e344dd3e645cf87700`,
154.134.192 Bytes. Neuer Wert: sha256
`bdf0e41104b83a81567b94138c52a199cd984161dcc315cf3a42f04bd68b890e`,
146.830.572 Bytes, 45 Bänder.

**Fünfter Referenzwechsel (30.09.2026, Freileitungen >= 110 kV):** neues Band 45
`power_lines_110kv_plus` (spannungsabhängig ab OSM-Leitungsachse: 116 m bei
110 kV, 136 m bei 220/380/400 kV; gemischte Leitungen erhalten den größeren
Puffer), Schema `2.3.0`,
`band_schema` `clean-45-freileitungen-110kv-sep-2026`. Vorwert: sha256
`bd5ddacc1d231cd43d507eece4536a6cfde57e5af912bdcbeec716212878bf1c`,
152.645.657 Bytes, 44 Bänder (Backup unter
`abschichtung_out_backup_2026-09-30/`). Bandweise bitgleich zum Vorwert sind
1–26, 28, 29 und 37–44; geändert nur 27, 30, 31, 32 und 33–36, und zwar
ausschließlich durch den Freileitungs-Zuwachs. Neuer Wert (Vektorpuffer): sha256
`b596fd021dbc42eb4bfa19b9caf8fead78cad6489f6f91e344dd3e645cf87700`,
154.134.192 Bytes, 45 Bänder. Das Band wurde am selben Tag zunächst nur für
>= 220 kV (136 m) gebaut (Zwischenstand sha256 `53cbc780…b653b6`, Backup unter
`abschichtung_out_220kv_2026-09-30/`) und dann auf >= 110 kV erweitert; ein erster >= 110-kV-Lauf mit Rasterpuffer
(Saatzellen + FFT-Dilation, sha256 `87649de3…e81194`, Backup unter
`abschichtung_out_110kv_raster_2026-09-30/`) verfehlte Zellen innerhalb des
Nennabstands und wurde durch den Vektorpuffer ersetzt.

**Vierter Referenzwechsel (Stand 22.09.2026 (neue WKA-Quelle), bestätigt
durch Neubau 28.09.2026):** `windkraft_standorte_at.geojson` (1.388 Punkte)
ersetzt die bisherige OSM-Ableitung als Windkraftanlagen-Standortquelle,
zusätzlich entfallen Technikbauten nahe Windkraftanlagen aus den
OSM-Gebäuden (Revision 7) — beides ändert Pixel in den WKA-bezogenen
Bändern. Ein Kaltstart-Neuaufbau am 28.09.2026 bestätigt den Lauf vom
22.09.2026 bitgleich (sha256 und Byte-Zahl identisch, ebenso identisch mit
dem Backup unter `backup/abschichtung_20260928/out/abschichtung.tif`). Der
vorherige Wert (`c1809c4c…16f37`) bleibt als historischer Zeuge
dokumentiert.

**Dritter Referenzwechsel (09.09.2026, Paket W7.1, Neuzuschnitt
„Layer-Struktur v4"):** zwei unabhängige Ursachen in einem Lauf. Erstens
ein Geometriefehler in Band 38 (`wka_bestand_ausserhalb_zonen`):
`build_wka_bestand_hulls()` rasterisierte die Park-Hüllen (konvexe Hülle
je Cluster außerhalb einer amtlichen Zone, plus 200 m Rand) bisher ohne
Abzug gegen `official_wind_zoning` — ein grenznaher Cluster konnte dadurch
in eine amtliche Zone hineinragen, obwohl jede einzelne Anlage laut
Punktabfrage außerhalb lag. Die Hülle wird jetzt explizit
`& ~official_wind_zoning` zugeschnitten. Zweitens sechs additiv angehängte
Bänder 39–44 (Schema `2.2.0`, historisch; aktuell 2.3.0 mit 45 Bändern, siehe unten) — Bedeutung und Index der
Bänder 1–38 bleiben unverändert. Der bandweise Vergleich der ersten 38
Bänder gegen die vorherige Referenz (`fb57c41d…232c30`) wird separat
nachgereicht (noch nicht Teil dieses Dokuments).

**Zweiter Referenzwechsel (08.09.2026, Punkt 34, Paket W5.P2):** ein
DKM-Kandidat mit Fußabdruck über `HIG_MAX_FOOTPRINT_M2` (10.000 m²), der
keine einzige BEV-Adresse im eigenen Polygon trägt, entfällt jetzt als
Kandidat vollständig statt wie bisher pauschal auf eine 5-m-Scheibe um
seinen Zentroid reduziert zu werden (Nutzerentscheidung, Punkt 34). Für
euch als Konsumenten heißt das: 514 von 806 betroffenen Riesenflächen
sind weggefallen, und Band 32 (`available_cleaned_min_10ha`, die
veröffentlichte Potenzialfläche) wächst dadurch netto um rund 98,4 ha
gegenüber der vorherigen Referenz (`4bdef6ad…6b1a13e`) — Details je Band
in `docs/rewrite/abweichungen.tsv` unter `paket = W5.P2`.

**Die Altkette existiert weiter** (historisch: `make widmung-v2`,
`scripts/widmung_v2/04_create_distance_zones.py`, Pfad aus dem Alt-Stand) und schreibt nach
`output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2.tif`.
Sie ist nicht das Auslieferungsartefakt. Wer aus einer älteren Integration
noch auf jenen Pfad zeigt, liest ein Ergebnis der alten Kette — siehe
„18 Bänder unterscheiden sich von `run1`" weiter unten.

## Zweites Produkt: abschichtung_analyse.tif, nur Analyse, nicht Teil des Konsumentenvertrags

`out/abschichtung_analyse.tif` und `out/abschichtung_analyse.bands.json`
(`pipeline/analyse_raster.py`, `make analyse-raster`, läuft in `all` nach
`finalize`) enthalten sieben Kataster-Nutzungsklassen (uint8 0/1) auf exakt dem
Raster von `abschichtung.tif`: Wald (ns 56, 55), Forststraßen (58), Äcker,
Wiesen, Weiden (48), Alpen (54), sonstige Landwirtschaft (40, 53, 57), Gärten
(52), Bauflächen (41, 83). Quelle: Digitale Katastralmappe BEV
(`NFL_V2`, `NFL_DXF_POLYGONIZED`, Zellmittelpunkt-Regel). Viewer, Dashboard und
Export lesen die Datei nicht; sie gehört nicht zum Konsumentenvertrag, und das
Hauptmanifest bleibt bei 45 Bändern. Aktueller sha256 der Analyse-TIF:
`89b89f1fb66684b5d3f4ac78022e31136f54d338837b82b5b1ee9e1ee4f02ef4` (Stand 13.10.2026). Das Manifest trägt sha256 und Dateiname der
Haupt-TIF, auf deren Raster es passt.

## Das Manifest-Schema, Feld für Feld

Ausschnitt aus dem tatsächlichen Manifest (nicht erfunden, generiert aus
`out/abschichtung.tif`, `schema_version` `2.0.0`):

```json
{
  "schema_version": "2.0.0",
  "generated_at": "2026-09-08T04:44:14Z",
  "pipeline": "widmung_v2",
  "band_schema": "clean-38-ohne-wichtige-objekte-aug-2026",
  "raster_file": "abschichtung.tif",
  "band_count": 38,
  "raster": {
    "crs": "EPSG:31287",
    "width": 24001,
    "height": 14001,
    "pixel_size_m": 25.0,
    "bounds": [99987.5, 249987.5, 700012.5, 600012.5],
    "dtype": "uint8",
    "nodata": 0,
    "nodata_meaning": "0 ist ein gueltiger Wert (Bedingung trifft nicht zu), kein echtes NoData"
  },
  "category_order": ["Mensch", "Natur", "Geografie", "Total & Ergebnis",
                      "Siedlungsabstand-Varianten",
                      "Referenz (Zonen & WKA-Bestand)", "Sonstige"],
  "bands": [
    {
      "index": 32,
      "name": "available_cleaned_min_10ha",
      "label_de": "Verfügbare Fläche, bereinigt (≥ 10 ha)",
      "description_de": "Das Endergebnis: die rohe verfügbare Fläche, bereinigt um Splitter - nur zusammenhängende Flächen ab 10 ha (4er-Nachbarschaft).",
      "category": "Total & Ergebnis",
      "value_type": "binary",
      "clipped_to_austria": true,
      "is_total": false,
      "color_rgba": [0, 255, 0, 185],
      "default_visible": true,
      "rolle": "verfuegbarkeit_bereinigt",
      "puffer_m": null,
      "puffer_hinweis": null,
      "quelle": [],
      "abgeleitet_von": ["available_after_all_exclusions_raw"]
    }
  ],
  "parameters": { "...": "26 Schlüssel, siehe unten" },
  "sources": { "...": "21 Einträge, Pfad/Stand/Rolle je Quelle" },
  "caveats": [ { "id": "noe_dkm_reconstructed", "...": "..." },
               { "id": "blur_bands_bleed_across_border", "...": "..." } ],
  "geography_water_bodies_wirkungspfad": ["geography_water_bodies", "... 9 Namen"]
}
```

Felderklärung:

| Feld | Bedeutung |
|---|---|
| `schema_version` | Version dieses Manifest-Schemas (semver), aktuell `2.0.0`. |
| `generated_at` | UTC-Zeitstempel des Schreibvorgangs. |
| `pipeline`, `band_schema` | aus den Datei-Tags des TIF übernommen (`PIPELINE`, `BAND_SCHEMA`); `band_schema` ist der Schema-Name, an dem ihr eine inkompatible Umstellung erkennt. |
| `raster_file` | Dateiname des TIF, zu dem dieses Manifest gehört (Basename, kein Pfad) — heute `abschichtung.tif`. |
| `band_count` | Anzahl Bänder — muss mit `dataset.count` des Rasters übereinstimmen. |
| `raster` | CRS, Auflösung, Bounds, `dtype`, `nodata` und `nodata_meaning` des Rasters. |
| `category_order` | Anzeigereihenfolge der Kategorien für UI-Gruppierung. |
| `bands[]` | Ein Eintrag pro Band, 1-indiziert wie GDAL/rasterio. |
| `bands[].index` | Band-Index (1-basiert). |
| `bands[].name` | Der stabile Bandname, z. B. `available_cleaned_min_10ha`. |
| `bands[].label_de`, `description_de` | Anzeigetext für UI, deutsch. |
| `bands[].category` | Gruppierung, siehe `category_order`. |
| `bands[].value_type` | `binary` (0/1-Maske) oder `percent_0_100` (nur die vier `available_blur_sigma_*`-Bänder). |
| `bands[].clipped_to_austria` | ob das Band mit `& valid_area` auf das Staatsgebiet geschnitten wurde. |
| `bands[].is_total` | ob es sich um ein Aggregatband handelt (z. B. `all_exclusions`). |
| `bands[].color_rgba`, `default_visible` | reine Darstellungs-Hinweise für den Viewer. |
| `parameters` | Kopie der GeoTIFF-Datei-Tags (Pipeline-Konfiguration zum Erzeugungszeitpunkt), 26 Schlüssel im aktuellen Manifest. |
| `sources` | Pfad/Stand/Rolle der Eingabedatensätze, 21 Einträge. |
| `caveats` | strukturierte, maschinell auflösbare Warnungen mit betroffenen Band-Indizes — siehe unten. |

### Neu in `2.0.0`: fünf Felder je Band und eine Liste oben

`1.0.0` beschrieb je Band nur, wie es **heißt und aussieht**. `2.0.0` sagt
zusätzlich, **was es ist und woher es kommt** — fünf Pflichtfelder je Band:

| Feld | Bedeutung |
|---|---|
| `rolle` | Pipeline-Rolle des Bandes, unabhängig von `category` (das ist reine Anzeige-Gruppierung). Sieben Werte: `bedingung` (Bänder 1–26), `aggregat_kategorie` (27–29), `aggregat_gesamt` (30), `verfuegbarkeit_roh` (31), `verfuegbarkeit_bereinigt` (32), `unschaerfe` (33–36), `referenz` (37–38). |
| `puffer_m` | Abstand in Metern (float) — nur gesetzt, wo ein einzelner, über ganz Österreich einheitlicher Wert existiert, sonst `null`. Beispiel: `general_buildings_buffer` → `25.0`, `haeuser_im_gruenen` → `750.0`. |
| `puffer_hinweis` | Freitext für die Fälle, die sich nicht in eine Zahl pressen lassen (`null` sonst). Drei Sorten: bundeslandabhängig (`settlement_buffer`: 1.200 m in NÖ, sonst 1.000 m), Korridor statt isotropem Puffer (`airport_runway_corridor_5km`), Puffer schon im Quellband enthalten. |
| `quelle` | Schlüssel in `sources` (Rohdatensätze), die **direkt** in dieses Band eingehen. Leer bei Aggregat- und Ergebnisbändern — die lesen keine Rohdaten. |
| `abgeleitet_von` | Namen der Bänder, aus denen dieses Band **rechnerisch** entsteht (ODER-Verknüpfung, Negation, Schwellwert-Filter, Gauß-Blur). Leer bei Bändern, die direkt aus `quelle` gelesen werden. |

Dazu ein neuer Schlüssel auf oberster Ebene:

- **`geography_water_bodies_wirkungspfad`** — Liste von neun Bandnamen: der
  transitive Abschluss über `abgeleitet_von`, beginnend bei
  `geography_water_bodies`. Er wird **berechnet, nicht gepflegt** (eine
  zweite, von Hand synchron zu haltende Liste wäre genau die stille Drift,
  die das Feld verhindern soll). Er deckt nur die Bodensee-Ursache ab. Wozu
  er gut ist, steht unten unter „18 Bänder unterscheiden sich von `run1`".

**Warum Haupt- und nicht Nebenversion**, obwohl die Änderung rein additiv
ist: ein Konsument, der die Feldmenge je Band exakt *zählt* oder auf
Gleichheit prüft, statt mit `in` nachzusehen, sieht sie als Bruch. Die
Versionsnummer soll den warnen, nicht ihn überraschen.

### `2.1.0` (Paket W5.P5) — die zweite Ursache bekommt ihr eigenes Feld

Die zweite, unabhängige Ursache aus dem Abschnitt „18 Bänder unterscheiden
sich von `run1`" unten (adresslose DKM-Großflächen, Punkt 34) hatte bis
`2.0.0` **kein** eigenes Manifestfeld — ihre Vorab-Nennung stand nur im
Messbericht des erzeugenden Pakets. Seit `2.1.0` trägt das Manifest dafür
einen zweiten Top-Level-Schlüssel:

- **`dkm_geoparquet_wirkungspfad`** — derselben Konvention wie oben, nur
  mit einem STARTKNOTENSATZ statt eines einzelnen Startbands: alle Bänder,
  deren `quelle` `dkm_geoparquet` referenziert, plus deren transitiver
  Abschluss über `abgeleitet_von`. Überschneidet sich mit
  `geography_water_bodies_wirkungspfad` an den gemeinsamen Aggregat-/
  Verfügbarkeitsbändern — beide Ursachen überlagern sich dort tatsächlich.

**Warum Neben- und nicht Hauptversion**, anders als bei `2.0.0`: die
Änderung fügt nur einen weiteren Top-Level-Schlüssel derselben, bereits
generisch entdeckbaren `..._wirkungspfad`-Konvention hinzu (ein Konsument,
der nach dem Namenssuffix statt nach einem festen Schlüsselnamen sucht,
findet ihn ohne Anpassung) — `bands[]` und jedes bestehende Feld je Band
bleiben unverändert. Genau die Fälle, die `2.0.0` zur Hauptversion machten
(Feldmenge je Band exakt zählen oder auf Gleichheit prüfen), sind hier
nicht betroffen.

### `2.2.0` (Paket W7.1, Struktur v4) — sechs neue Bänder, drei neue Felder je Band (historisch; aktuell 2.3.0, 45 Bänder)

**Nachgezogen (09.09.2026, Integration aller drei Bahnen von W7.1):** die
„Aktuelle Referenzausgabe"-Tabelle weiter oben zeigt jetzt die echten
Werte (`band_count: 44`, `schema_version: 2.2.0`, neuer `sha256`). Der
große JSON-Ausschnitt oben im Dokument (Abschnitt „Das Manifest-Schema,
Feld für Feld") bleibt bewusst die historische Momentaufnahme von
`2.0.0`, an der die dortige Felderklärung entstand — sie zeigt die
Struktur, nicht den aktuellen Stand; für die 44-Bänder-Liste selbst siehe
`out/abschichtung.bands.json` oder `out/LAYER.md` (seit W7.6 erzeugt aus
dem Manifest, `pipeline/export/layer_doc.py` - keine handgepflegte
Vorlage mehr, siehe unten). Der bandweise Vergleich der 18 (bzw.
jetzt ggf. mehr) abweichenden Bänder gegen `run1` unten („18 Bänder
unterscheiden sich von `run1`") bezieht sich inhaltlich weiterhin nur auf
Ursachen innerhalb der Bänder 1–38 (`run1` selbst hat und behält 38
Bänder). **Nachgezogen (W7.4):** der frühere Bandzahl-Guard in
`measure_bands()` — der bei 44 gegen 38 Bändern hart mit `ValueError`
abbrach — ist entfernt. `pipeline.validate` vergleicht seither nur die
namentlich überlappenden Bänder (1–38) gegen `run1` und weist die sechs
neuen Bänder 39–44 im Register (`docs/rewrite/abweichungen.tsv`) explizit
als eigenen Status „ohne Gegenstück in `run1`" aus, statt abzubrechen oder
sie stillschweigend zu übergehen.

(historisch, Schema 2.2.0; aktuell 45 Bänder, Schema 2.3.0) `band_count` steigt additiv von 38 auf 44: sechs neue Bänder 39–44
(`haeuser_im_gruenen_source`, `general_buildings_roh_osm`,
`general_buildings_roh_dkm`, `sources_human`, `sources_nature`,
`sources_geography`) werden ans Ende angehängt, Bedeutung und Index der
Bänder 1–38 ändern sich nicht. `band_schema` wechselt von
`clean-38-ohne-wichtige-objekte-aug-2026` auf
`clean-44-ohne-wichtige-objekte-aug-2026`. Details je neuem Band (Label,
Beschreibung, Quelle, `abgeleitet_von`) stehen im Manifest selbst, siehe
`calc/band_manifest.py`.

Drei neue Pflichtfelder je Band:

| Feld | Bedeutung |
|---|---|
| `familie` | Gruppierungsschlüssel innerhalb einer Kategorie (z. B. `siedlung`, `haeuser_im_gruenen`, `gebaeude`, `summe`). Reihenfolge und Anzeigelabel je Familie stehen im neuen Top-Level-Feld `familien`. |
| `stufe` | Pipeline-Stufe des Bandes, einer von sieben Werten (siehe `stufe_order`): `roh`, `quelle`, `aggregat`, `zone`, `summe_quellen`, `summe_zonen`, `ergebnis`. |
| `dashboard_layer` | `false` nur für die vier Unschärfebänder 33–36, sonst `true` — ob ein Band als eigener Layer im Dashboard auftauchen soll. |

Zwei neue Top-Level-Felder:

- **`stufe_order`** — die feste Stufenreihenfolge
  (`["roh","quelle","aggregat","zone","summe_quellen","summe_zonen","ergebnis"]`).
- **`familien`** — geordnetes Array `{key, category, label_de}`, ein
  Eintrag je Familie und Kategorie (der Schlüssel `summe` kommt bewusst
  dreimal vor, einmal je Kategorie Mensch/Natur/Geografie). Anzeigereihenfolge
  im Baum: Kategorie (`category_order`) → Familie (`familien`) → Stufe
  (`stufe_order`) → Index.

**`default_visible` ändert seine Herleitung**, nicht seine Bedeutung: ab
`2.2.0` gilt `default_visible = (stufe == "zone") oder name ==
"available_cleaned_min_10ha"` statt eines von Hand gepflegten Namenssets.
Praktisch heißt das: `all_exclusions` und die drei Kategorie-Summenbänder
(`exclusion_human`/`_nature`/`_geography`) sind ab `2.2.0` **nicht mehr**
`default_visible` (sie sind `summe_zonen`, keine `zone`) — wer sich beim
initialen Rendern auf `default_visible` statt auf eine eigene Layer-Auswahl
verlässt, sieht diese vier Bänder künftig nicht mehr automatisch.

Der Quellschlüssel `amtliche_windzonen_stmk_sbg` (in `sources`) ist in
`amtliche_windzonen_stmk` und `amtliche_windzonen_sbg` getrennt — Steiermark
und Salzburg sind zwei unterschiedliche Shapefiles.

`familie`, `stufe` und `dashboard_layer` sind **informativ**, wie `puffer_m`
und `quelle` — nicht Teil des Vertrags (siehe nächster Abschnitt).

### Inhaltliche Änderung innerhalb `2.2.0` (09.09.2026, W7.5): Personenseilbahnen enger gefasst (historisch)

Kein Schema-Wechsel (`band_count`/`schema_version` bleiben bei 44/`2.2.0`),
aber eine inhaltliche Änderung an drei Bändern: Nutzerentscheidung vom
09.09.2026, Personenseilbahnen sind genau vier OSM-`aerialway`-Typen —
`gondola`, `cable_car`, `chair_lift`, `mixed_lift`. Keine Schlepplifte
(`drag_lift`, `t-bar`, `j-bar`, `platter`, `rope_tow`), kein
`magic_carpet`, nichts aus `goods`/`zip_line`/`explosive`/`avalanche`/
`pylon`/`station`/`yes`/`proposed`/`abandoned`/`deflection_roller`. Betrifft:

- **Band 17** (`cableway_people_150m`) — filterte schon vorher auf
  personenbefördernde Typen, aber auf zehn statt vier (zusätzlich die fünf
  Schlepplift-Varianten und `magic_carpet`).
- **Band 10** (`cableway_buildings_source`) — filterte vorher **gar
  nicht**: jede `aerialway`-Geometrie (auch Punkte wie `station`/`pylon`)
  zählte für die Nähe-Zuordnung von OSM-Gebäuden zu einer Seilbahn. `docs/rewrite/FORTSCHRITT.md`,
  Paket W7.5, dokumentiert die tatsächlich gemessene Auswirkung dieses
  Filters auf Band 10 - eine Bergstation ist ein Gebäude, das dieses Band
  finden soll, das war ausdrücklich zu prüfen statt anzunehmen.
- **Band 42** (`sources_human`) — die `aerialways`-Teilmenge in der
  ungepufferten Quellsumme filterte vorher ebenfalls nicht.

Einzige Definitionsstelle: `calc.abschichtung_common.PEOPLE_CARRYING_AERIALWAY_TYPES`.

### `2.2.1` (Paket W7.6, 09.09.2026) — Kategorie-/Familien-/Stufentexte, drei neue Parameter, dritter Caveat (historisch)

Reine Textänderung, kein Pixel geändert (bandweise gemessen: `diff=0` über
alle 44 Bänder), `band_count` bleibt 44. Zwei neue Top-Level-Schlüssel,
`kategorien` (sieben Einträge, je `category_order`-Eintrag einer) und
`stufen` (sieben Einträge, deckt `stufe_order` vollständig ab); `familien[]`
bekommt `description_de` je Eintrag. Alle `label_de` folgen ab hier
ausnahmslos der Namensregel (nur Buchstaben, Leerzeichen, Bindestriche -
mechanisch geprüft, `tests/test_band_manifest.py`). Ein dritter
`caveats`-Eintrag (`tunnelfilter_unvollstaendig`). Fünf neue
`parameters`-Schlüssel (`SLOPE_MAX_DEG`, `ELEVATION_MAX_M`, `PD_MIN_W_M2`,
`PD_MIN_REFERENCE_HEIGHT_M`, `PD_MIN_AT_150M_W_M2`) - diese landen auch als
GeoTIFF-Datei-Tags, was die Datei-Prüfsumme des TIF ändert, obwohl kein
Pixel abweicht (siehe `tests/test_referenz_tif.py`, "Fünfter Wechsel").
Außerdem, noch innerhalb W7.6: `default_visible`/`dashboard_layer` sind ab
hier feste Namenslisten statt einer Ableitung aus `stufe` (`default_visible`
5 der 44 Bänder - die drei Kategoriesummen, die Eignungsflächen, die
amtlichen Zonen; `dashboard_layer` 23 der 44 Bänder).

**Siebtes Endprodukt:** `out/LAYER-MANIFEST.md` (Quelle `docs/LAYER-MANIFEST.md`,
`pipeline.contract.PRODUCTS["layer_manifest_md"]`) - der Vertrag, WIE dieses
Manifest zu lesen ist (Feldtabelle, Invarianten, Textkonventionen), kopiert
bei jedem `make export` neben `out/LAYER.md`. `out/LAYER.md` selbst wird ab
W7.6 nicht mehr aus einer handgepflegten Vorlage kopiert, sondern von
`pipeline/export/layer_doc.py` direkt aus `out/abschichtung.bands.json`
erzeugt - kein Bandname im Erzeuger-Code, zwei Läufe über dasselbe Manifest
liefern bytegleiche Ausgaben.

### `2.3.0` (30.09.2026) — Band 45, Freileitungen >= 110 kV

`band_count` steigt additiv von 44 auf 45; Bänder 1–44 behalten Name, Index und
Rolle. Neues Band 45 `power_lines_110kv_plus` (Familie `energieleitungen`,
Kategorie Mensch, Stufe `zone`, `dashboard_layer` true, `default_visible`
false, `puffer_m` 136 — numerisch das Maximum; bei 110 kV gelten 116 m, beide
Stufen nennt `description_de`). Neue Familie `energieleitungen` (`familien`: 17
Einträge). `dashboard_layer` gilt jetzt für 24 der 45 Bänder. `band_schema`
wechselt auf `clean-45-freileitungen-110kv-sep-2026`.

## Vertrag vs. Dokumentation

**Vertrag** — das dürft ihr euch verlassen, solange `schema_version`
gleich bleibt:

- `band_count`
- `bands[].index`
- `bands[].name`
- `bands[].rolle` (seit `2.0.0`)

Alles andere im Manifest ist **informativ** und kann sich ändern, ohne dass
das einen Konsumenten bricht, der sich an den Vertrag hält — Labels,
Farben, Beschreibungstexte, Kategorienamen, Reihenfolge der Kategorien,
Quellenliste, Caveat-Texte, `puffer_m`/`puffer_hinweis`, `quelle`,
`abgeleitet_von`.

Zu `quelle`/`abgeleitet_von` ausdrücklich: sie sind **Herkunftsauskunft,
kein Vertrag**. Wer daraus einen Graphen baut und ihn anzeigt, tut das
Richtige; wer eine Berechnung darauf stützt, die bei einer geänderten
Kante still falsch wird, nicht.

**`parameters` ist ausdrücklich NICHT Teil des Vertrags.** Es ist eine
Kopie der Pipeline-Konfiguration zum jeweiligen Erzeugungszeitpunkt, kein
festes Schema. Beleg dafür liefert die eigene Historie dieses Projekts: das
frühere Referenzmanifest (aus einem Artefakt der Altkette) trug
`SETTLEMENT_BUFFER_VARIANT_NAMES` **nicht**, dafür aber `AREA_OR_POINT` —
ein von GDAL selbst gesetztes Tag, das in keiner Code-Liste steht. Das
heutige Manifest trägt genau die 26 Schlüssel, die `pipeline/finalize.py`
in seinem `tags`-Dict deklariert, und `AREA_OR_POINT` nicht mehr. Dieselbe
Zahl, andere Menge. Jede Vollständigkeitsprüfung gegen eine feste
`parameters`-Schlüsselliste bricht folglich am eigenen Output dieses
Projekts, sobald sich die Erzeugerstufe ändert — das ist kein Rand-, sondern
der Normalfall bei einem Manifest, das nichts weiter tut als Datei-Tags zu
spiegeln.

## Wie ein Konsument korrekt prüft

1. **Bandzahl gegen das Raster prüfen:** `manifest["band_count"] ==
   dataset.count`. Weicht das ab, ist Manifest und TIF nicht dasselbe
   Artefakt — abbrechen, nicht weiterraten.
2. **Bänder über den Namen auflösen, nie über die Position.** Baut eine
   Lookup-Tabelle `name -> index` aus `bands[]` und lest darüber. Ein
   Band-Index ist zwischen Schema-Versionen nicht stabil (siehe nächster
   Abschnitt) — der Name ist es.
3. **Bei unbekanntem oder fehlendem Namen laut scheitern**, nicht auf eine
   geratene Position oder einen alten Index zurückfallen. Ein stiller
   Fallback ist genau der Fehler, den dieses Manifest verhindern soll.
4. **`schema_version` prüfen, bevor ihr auf ein `2.0.0`-Feld zugreift.**
   `rolle`, `puffer_m`, `puffer_hinweis`, `quelle` und `abgeleitet_von`
   fehlen in `1.0.0`-Manifesten vollständig.

Eine Referenzimplementierung dieses Vertrags existiert bereits auf der
Dashboard-Konsumentenseite: `scripts/band_manifest.py` (historisch) auf dem Branch
`feat/band-manifest` (dort, nicht in diesem Repo) — als Beschreibung dessen,
was existiert, nicht als hier geprüfter Code. Sie stammt aus der
`1.0.0`-Zeit und kennt die fünf neuen Felder nicht.

## Die Falle, die das hier schließen soll

Vor der Umstellung lasen Konsumenten Bänder über ihre **Position**, weil sie
die Bandreihenfolge selbst nachgebaut hatten. Das ist so lange unauffällig,
wie sich die Bandzahl und -reihenfolge nicht ändert — und genau das ist
zwischen v1 und v2 passiert:

- **v1 hat 54 Bänder, v2 hat 38.** Verifiziert per `rasterio` gegen die
  echten Dateien: `windkraft_ö_karten/output/abschichtung_widmung/
  osm_wka_distance_zones_widmung.tif` → `count = 54`; das v2-Artefakt
  dieses Repos → `count = 38`.
- **`available_cleaned_min_10ha` lag in v1 auf Index 29, liegt in v2 auf
  Index 32.** In v1 ist Band 29 tatsächlich `available_cleaned_min_10ha`
  (per `rasterio`-Bandbeschreibung geprüft). In v2 ist Band 29
  `exclusion_geography` — eine Ausschlussmaske für Geografie-Kriterien
  (ODER der Bänder 23-26: Hangneigung, Seehöhe, Windhöffigkeit, Gewässer),
  ebenfalls eine gültige `uint8`-0/1-Maske. `available_cleaned_min_10ha`
  liegt in v2 auf Index 32.

**Die Konsequenz:** ein Konsument, der Band 29 positionsbasiert als „die
verfügbare Potenzialfläche" liest, bekommt beim Wechsel von v1 auf v2 ohne
jede Fehlermeldung `exclusion_geography` zurück — beides sind plausible,
technisch valide 0/1-Masken, nur inhaltlich das genaue Gegenteil dessen,
was erwartet wurde. Genau diese Klasse von Fehler schließt das
namensbasierte Nachschlagen über `bands[].name` strukturell aus.

(Frühere, kursierende Zahlen — 63 Bänder in `dashboard_data.json`, 39 Layer
in `viewer/manifest.json` — sind ältere, jeweils zu ihrem eigenen Zeitpunkt
gültige Zählungen aus anderen Artefakten, siehe Root-`README.md`, Abschnitt
„Das Band-Manifest". Sie widersprechen der 54/38-Zahl nicht, zählen aber
etwas anderes; als Vergleichsbasis für v1 vs. v2 zählt ausschließlich die
oben verifizierte GeoTIFF-Bandzahl.)

## 18 Bänder unterscheiden sich von `run1`

Wer dieses Artefakt gegen ein älteres Ergebnis **derselben** v2-Kette
hält — namentlich gegen
`output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2_run1.tif`,
das letzte Ergebnis der Altkette in diesem Repo (`sha256`
`dc58b011…9e3df1`) —, findet genau **18** abweichende Bänder, aus **zwei
überlagerten Ursachen** (Punkt 33 und Punkt 34 der Offenen-Punkte-Liste in
`docs/rewrite/FORTSCHRITT.md`, beide vom Nutzer am 08.09.2026
entschieden). Das ist beabsichtigt und entschieden, kein Fehler:

| Gruppe | Band | Name |
|---|---|---|
| Nur Bodensee (Punkt 33) | 26 | `geography_water_bodies` |
| Nur Bodensee (Punkt 33) | 29 | `exclusion_geography` |
| Nur adresslose DKM-Großflächen (Punkt 34) | 5 | `haeuser_im_gruenen_streusiedlung` |
| Nur adresslose DKM-Großflächen (Punkt 34) | 7 | `haeuser_im_gruenen` |
| Nur adresslose DKM-Großflächen (Punkt 34) | 8 | `nonresidential_hulls_source` |
| Nur adresslose DKM-Großflächen (Punkt 34) | 9 | `nonresidential_hulls_buffer` |
| Nur adresslose DKM-Großflächen (Punkt 34) | 10 | `cableway_buildings_source` |
| Nur adresslose DKM-Großflächen (Punkt 34) | 11 | `cableway_buildings_buffer` |
| Nur adresslose DKM-Großflächen (Punkt 34) | 12 | `general_buildings_source` |
| Nur adresslose DKM-Großflächen (Punkt 34) | 13 | `general_buildings_buffer` |
| Nur adresslose DKM-Großflächen (Punkt 34) | 27 | `exclusion_human` |
| Beide Ursachen überlagert | 30 | `all_exclusions` |
| Beide Ursachen überlagert | 31 | `available_after_all_exclusions_raw` |
| Beide Ursachen überlagert | 32 | `available_cleaned_min_10ha` |
| Beide Ursachen überlagert | 33–36 | `available_blur_sigma_100m` … `_300m` |

Die übrigen 20 Bänder sind bitgleich.

**Ursache 1 (Punkt 33, Bänder 26, 29–36):** Die Altkette klippt per
`osmium extract --bbox` **vor** dem Tag-Filter. Bei einer großen
grenzüberschreitenden Relation kappt das Mitglieder außerhalb der Box, und
die Relation geht beim Export verloren — konkret der Bodensee. Die neue
Prep-Stufe filtert gegen die volle, ungeklippte Rohquelle und findet ihn.
**Die neue Kette hat recht**, und der Nutzer hat die Korrektur am
08.09.2026 angenommen (Punkt 33).

**Ursache 2 (Punkt 34, Bänder 5, 7–13, 27, 30–36):** Ein DKM-Kandidat mit
Fußabdruck über `HIG_MAX_FOOTPRINT_M2` (10.000 m²), der keine einzige
BEV-Adresse im eigenen Polygon trägt, entfällt jetzt als Kandidat
vollständig, statt wie bisher pauschal auf eine 5-m-Scheibe um seinen
Zentroid reduziert zu werden — 514 von 806 betroffenen Riesenflächen sind
davon betroffen. Fachliche Entscheidung des Nutzers am 08.09.2026 (Punkt
34), umgesetzt in `windkraft/calc/hig_detection.py:scan_dkm_candidates()`.

Die neun Bodensee-Bänder (Gruppen „Nur Bodensee" und „Beide Ursachen
überlagert") müsst ihr nicht abschreiben: sie stehen als
`geography_water_bodies_wirkungspfad` im Manifest und sind dort aus
`abgeleitet_von` berechnet — vor der Messung genannt, danach bestätigt.
Für die neun Bänder aus Ursache 2 gibt es **kein** entsprechendes
Manifestfeld; ihre Zahlen stehen ausschließlich in
`docs/rewrite/abweichungen.tsv` unter `paket = W5.P2`, Spalte `ursache`
nennt für jedes Band, welche der beiden Ursachen (oder beide) zutrifft.

Praktisch heißt das für euch: Band 32, die veröffentlichte
Potenzialfläche, verliert gegenüber `run1` **netto 13.562 Zellen (rund
847,6 ha bzw. 8,48 km²)** — nachgemessen direkt am TIF, nicht
ausgerechnet. Das ist kleiner als der reine Bodensee-Effekt (15.137
Zellen, rund 945,7 ha bzw. 9,46 km², die W3.1-Zahl von oben), weil Punkt
34 gegenläufig wirkt: 15.154 Zellen verlieren die Verfügbarkeit (weit
überwiegend die Bodensee-Korrektur), aber 1.592 Zellen gewinnen sie neu
hinzu (Flächen, die durch den Wegfall adressloser DKM-Großflächen nicht
mehr ausgeschlossen sind) — macht 15.154 − 1.592 = 13.562 Zellen netto.
Wer Flächenbilanzen gegen ältere Auswertungen vergleicht, findet den
Unterschied hier erklärt.

### Weitere Entscheidungen des Nutzers zu Punkt 34 (08.09.2026)

- **`HIG_MIN_ADRESSEN` bleibt bei 5.** Gemessen: 10.873 Streusiedlungen
  (≥ 5 Adressen, 750-m-Puffer) gegen 12.327 Einzellagen (< 5 Adressen,
  25-m-Puffer) — **kein Knie im Histogramm** an dieser Schwelle: bei
  Schwelle 3 wären es 68,2 % der Kandidaten, die als Streusiedlung
  gelten, bei Schwelle 7 nur 32,8 %. Der Wert 5 ist eine bewusste
  Setzung, keine aus den Daten abgelesene Bruchkante, und wird
  unverändert beibehalten.
- **Eine bekannte, einseitige Fehlklassifikation bleibt bestehen.** 249
  von 2.736 Industriehüllen (9,1 %) tragen selbst keine BEV-Adresse und
  werden deshalb auf den 25-m-Radius („Einzellage") herabgestuft, obwohl
  **207 davon (83,1 %)** in unmittelbarer Nähe Adress- oder
  Gartensignale tragen (Median 4 Adressen im Umfeld, **Maximum 1.089**).
  Die Richtung des Fehlers ist konservativ — er schließt zu wenig aus,
  nie zu viel —, deshalb bewusst **dokumentiert, nicht korrigiert**, auf
  Entscheidung des Nutzers.

## Caveats in Klartext

Zwei methodische Einschränkungen sind im Manifest unter `caveats[]`
strukturiert hinterlegt (mit betroffenen Band-Indizes in `affects.bands`),
hier in Worten:

- **NÖ-Rekonstruktion** (`noe_dkm_reconstructed`, Bänder 8, 9, 12, 13, 27,
  30, 31, 32, 33–36). Die DKM-Basis für Niederösterreich ist aus
  DXF-Linienwerk rekonstruiert, nicht amtlich flächig geliefert — rund 29 %
  der rekonstruierten Polygone sind mehrdeutig klassifiziert oder ohne
  Klassifikation verworfen. Der Wirkungspfad läuft von der
  DKM-Rekonstruktion über Band 12 (NÖ-Streusiedlungs-Hüllen) und dessen
  Pufferband 13 in die Gruppensummen 27/30/31 und weiter in Band **32 —
  die veröffentlichte Potenzialfläche selbst** — sowie in die
  Unschärfebänder 33-36. Wer mit Band 32 arbeitet, arbeitet also
  unvermeidlich mit dieser Rekonstruktion.
- **Unschärfe-Bänder bluten über die Grenze**
  (`blur_bands_bleed_across_border`, Bänder 33–36). Die vier
  `available_blur_sigma_*`-Bänder sind zwar als `clipped_to_austria: true`
  markiert, aber nur mittelbar: sie glätten ein bereits geschnittenes Band,
  wodurch die Gaußglocke geringfügig über die Staatsgrenze trägt. Wer
  daraus schließt, die Werte seien exakt auf Österreich beschnitten, und
  Flächen aufsummiert, rechnet leicht falsch.
- **`nodata=0` ist kein echtes NoData.** 0 ist ein gültiger Wert
  („Bedingung trifft nicht zu"), keine fehlende Beobachtung. Wer 0 als
  „keine Daten" behandelt und herausfiltert, verwirft echte, gültige
  Information. (Steht nicht als `caveats[]`-Eintrag, sondern als
  `raster.nodata_meaning`.)

## Was beim Konsumenten bleibt

Farben, Beschriftungen, UI-Reihenfolge und Kartendarstellung sind bewusst
nicht Teil dieses Vertrags. `color_rgba`, `label_de`, `default_visible` und
`category_order` im Manifest sind Vorschläge aus der gemeinsamen Quelle
`windkraft/viz/band_metadata.py` — Styling, Übersetzung und Layout bleiben
Sache des jeweiligen Frontends.

## Zwei inhaltliche Änderungen gegenüber v1

Zwei Änderungen sind nicht nur strukturell (Bandzahl/-index), sondern
inhaltlich — wer Beschreibungstexte aus der v1-Ära weiterverwendet, muss
sie an diesen Stellen anpassen. Beide sind gegen den Code verifiziert (die
Datei-Tags setzt heute `pipeline/finalize.py`, wörtlich übernommen aus (historisch)
`scripts/widmung_v2/04_create_distance_zones.py`):

- **Stromleitungen: seit 30.09.2026 wieder ein Ausschlusskriterium, als
  Band 45.** v1 kannte ein eigenes Band `power_380_400kv` (Band 11 in der
  54-Band-Liste, 150 m); das Clean-Schema Aug 2026 ließ es fallen. Seit
  Schema `2.3.0` gibt es `power_lines_110kv_plus`: OSM `power=line` mit
  110, 220, 380 oder 400 kV, spannungsabhängiger Puffer ab der Leitungsachse:
  110 kV 116 m (halber Rotordurchmesser der Referenzanlage V172 = 86 m, plus
  Sicherheitsabstand 20 m, plus 10 m von der Mastachse zum äußersten Leiter;
  garantiert mindestens 106 m zum Leiter), 220/380/400 kV 136 m (86 m plus
  30 m plus 20 m; mindestens 116 m zum Leiter). Leitungen mit mehreren
  Spannungsebenen (z. B. `220000;110000`) erhalten den größeren Puffer.
  Gepuffert wird als Vektor an der echten Liniengeometrie und mit allen
  berührten Zellen gerastert (jede Zelle innerhalb des Nennabstands ist
  ausgeschlossen, der Rand überschießt um höchstens eine Zelle); alle anderen
  Puffer bleiben Rastermethode. Mittelspannung (< 110 kV) ist nicht enthalten. Der Datei-Tag
  `POWER_LINES` beschreibt das Kriterium. Das Band geht in `exclusion_human`
  (27) und damit in 30–36 ein; `sources_human` (42) bleibt unverändert.
- **„Wichtige Objekte" sind in `haeuser_im_gruenen` (750 m) aufgegangen.**
  v1 führte sie als eigenes Band mit 250-m-Puffer (`important_objects_source`
  / `important_objects_buffer`, Bänder 3-4). Der Datei-Tag
  `WICHTIGE_OBJEKTE` sagt explizit `"in haeuser_im_gruenen (750 m); vorher
  eigenes 250-m-Band"`.
