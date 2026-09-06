# Handoff: das Widmung-v2-GeoTIFF für Konsumenten

Dieses Dokument richtet sich an alle, die das Ergebnis der Widmung-v2-Kette
weiterverarbeiten — Dashboard, Viewer, Auswertungsskripte, gleich welches
Repo. Es beschreibt den Vertrag, an den ihr euch halten könnt, und die
Grube, in die die letzte Umstellung (v1 → v2) bereits einmal geführt hat.

**Wichtig vorweg:** die Widmung-v2-Kette wurde in diesem Repo (`abschichtung`)
noch **kein einziges Mal end-to-end ausgeführt**. Das hier beschriebene
GeoTIFF und Manifest sind ein aus dem Vorgänger-Repo `windkraft_ö_karten`
übernommenes Referenzartefakt (Dateidatum 06.09., siehe Root-`README.md`,
Abschnitt „Status“), keine Ausgabe dieses Repos. Der Vertrag unten gilt für
das Schema, nicht als Zusicherung, dass dieses Repo es aktuell reproduziert.

## Die zwei Dateien

Jeder Lauf von `04_create_distance_zones.py` schreibt zwei Dateien, die
zusammengehören und nur zusammen ausgeliefert werden:

- **`osm_wka_distance_zones_widmung_v2.tif`** — das eigentliche Raster,
  38 Bänder, `uint8`, EPSG:31287, 25 m Pixelgröße.
- **`osm_wka_distance_zones_widmung_v2.bands.json`** — das Sidecar-Manifest
  (`<stem>.bands.json`), geschrieben von `windkraft/calc/band_manifest.py`
  direkt im Anschluss an das GeoTIFF, aus denselben Werten (Bandnamenliste,
  Datei-Tags), ohne das Raster erneut zu öffnen. Bandzahl, -namen und
  -reihenfolge im Manifest sind deshalb per Konstruktion identisch mit dem
  TIF — es gibt keinen zweiten Erzeugungspfad, der auseinanderlaufen könnte.

Nehmt nie das eine ohne das andere entgegen. Ein TIF ohne sein Manifest hat
keine maschinenlesbare Aussage mehr darüber, was Band 17 bedeutet.

## Das Manifest-Schema, Feld für Feld

Ausschnitt aus dem tatsächlichen Referenzmanifest (nicht erfunden, generiert
aus dem Real-TIF in diesem Repo, `schema_version` `1.0.0`):

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-09-06T11:53:59Z",
  "pipeline": "widmung_v2",
  "band_schema": "clean-38-ohne-wichtige-objekte-aug-2026",
  "raster_file": "osm_wka_distance_zones_widmung_v2.tif",
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
      "default_visible": true
    }
  ],
  "parameters": { "...": "26 Schlüssel, siehe unten" },
  "sources": { "...": "21 Einträge, Pfad/Stand/Rolle je Quelle" },
  "caveats": [ { "id": "noe_dkm_reconstructed", "...": "..." },
               { "id": "blur_bands_bleed_across_border", "...": "..." } ]
}
```

Felderklärung:

| Feld | Bedeutung |
|---|---|
| `schema_version` | Version dieses Manifest-Schemas (semver). |
| `generated_at` | UTC-Zeitstempel des Schreibvorgangs. |
| `pipeline`, `band_schema` | aus den Datei-Tags des TIF übernommen (`PIPELINE`, `BAND_SCHEMA`); `band_schema` ist der Schema-Name, an dem ihr eine inkompatible Umstellung erkennt. |
| `raster_file` | Dateiname des TIF, zu dem dieses Manifest gehört (Basename, kein Pfad). |
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
| `parameters` | Kopie der GeoTIFF-Datei-Tags (Pipeline-Konfiguration zum Erzeugungszeitpunkt), 26 Schlüssel im Referenzmanifest. |
| `sources` | Pfad/Stand/Rolle der Eingabedatensätze, aus `data/README.md` übernommen. |
| `caveats` | strukturierte, maschinell auflösbare Warnungen mit betroffenen Band-Indizes — siehe unten. |

## Vertrag vs. Dokumentation

**Vertrag** — das dürft ihr euch verlassen, solange `schema_version`
gleich bleibt:

- `band_count`
- `bands[].index`
- `bands[].name`

Alles andere im Manifest ist **informativ** und kann sich ändern, ohne dass
das einen Konsumenten bricht, der sich an den Vertrag hält — Labels,
Farben, Beschreibungstexte, Kategorienamen, Reihenfolge der Kategorien,
Quellenliste, Caveat-Texte.

**`parameters` ist ausdrücklich NICHT Teil des Vertrags.** Es ist eine
Kopie der Pipeline-Konfiguration zum jeweiligen Erzeugungszeitpunkt, kein
festes Schema. Beleg dafür liegt im eigenen Referenzmanifest: der
Writer-Code deklariert heute 26 Tag-Schlüssel in seinem `tags`-Dict
(`scripts/widmung_v2/04_create_distance_zones.py:472-499`), darunter seit
Zeile 494 `SETTLEMENT_BUFFER_VARIANT_NAMES`. Das Referenzmanifest — aus
einem älteren Artefakt erzeugt — trägt diesen Schlüssel **nicht**; dafür
enthält es `AREA_OR_POINT`, ein von GDAL selbst gesetztes Tag, das nicht in
der Code-Liste steht. Macht 25 von 26 heute deklarierten Schlüsseln, plus
einen zusätzlichen. Jede Vollständigkeitsprüfung gegen eine feste
`parameters`-Schlüsselliste bricht folglich am eigenen, aktuellen Output
dieses Projekts — das ist kein Rand- sondern der Normalfall bei einem
Manifest, das nichts weiter tut als Datei-Tags zu spiegeln.

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

Eine Referenzimplementierung dieses Vertrags existiert bereits auf der
Dashboard-Konsumentenseite: `scripts/band_manifest.py` auf dem Branch
`feat/band-manifest` (dort, nicht in diesem Repo) — als Beschreibung dessen,
was existiert, nicht als hier geprüfter Code.

## Die Falle, die das hier schließen soll

Vor der Umstellung lasen Konsumenten Bänder über ihre **Position**, weil sie
die Bandreihenfolge selbst nachgebaut hatten. Das ist so lange unauffällig,
wie sich die Bandzahl und -reihenfolge nicht ändert — und genau das ist
zwischen v1 und v2 passiert:

- **v1 hat 54 Bänder, v2 hat 38.** Verifiziert per `rasterio` gegen die
  echten Dateien: `windkraft_ö_karten/output/abschichtung_widmung/
  osm_wka_distance_zones_widmung.tif` → `count = 54`;
  `output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2.tif`
  (dieses Repo) → `count = 38`.
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

## Caveats in Klartext

Zwei methodische Einschränkungen sind im Manifest unter `caveats[]`
strukturiert hinterlegt (mit betroffenen Band-Indizes in `affects.bands`),
hier in Worten:

- **NÖ-Rekonstruktion.** Die DKM-Basis für Niederösterreich ist aus
  DXF-Linienwerk rekonstruiert, nicht amtlich flächig geliefert — rund 29 %
  der rekonstruierten Polygone sind mehrdeutig klassifiziert oder ohne
  Klassifikation verworfen. Der Wirkungspfad läuft von der
  DKM-Rekonstruktion über Band 12 (NÖ-Streusiedlungs-Hüllen) und dessen
  Pufferband 13 in die Gruppensummen 27/30/31 und weiter in Band **32 —
  die veröffentlichte Potenzialfläche selbst** — sowie in die
  Unschärfebänder 33-36. Wer mit Band 32 arbeitet, arbeitet also
  unvermeidlich mit dieser Rekonstruktion.
- **Unschärfe-Bänder bluten über die Grenze.** Die vier
  `available_blur_sigma_*`-Bänder (33-36) sind zwar als
  `clipped_to_austria: true` markiert, aber nur mittelbar: sie glätten ein
  bereits geschnittenes Band, wodurch die Gaußglocke geringfügig über die
  Staatsgrenze trägt. Wer daraus schließt, die Werte seien exakt auf
  Österreich beschnitten, und Flächen aufsummiert, rechnet leicht falsch.
- **`nodata=0` ist kein echtes NoData.** 0 ist ein gültiger Wert
  („Bedingung trifft nicht zu"), keine fehlende Beobachtung
  (`raster.nodata_meaning` im Manifest). Wer 0 als „keine Daten" behandelt
  und herausfiltert, verwirft echte, gültige Information.

## Was beim Konsumenten bleibt

Farben, Beschriftungen, UI-Reihenfolge und Kartendarstellung sind bewusst
nicht Teil dieses Vertrags. `color_rgba`, `label_de`, `default_visible` und
`category_order` im Manifest sind Vorschläge aus der gemeinsamen Quelle
`windkraft/viz/band_metadata.py` — Styling, Übersetzung und Layout bleiben
Sache des jeweiligen Frontends.

## Zwei inhaltliche Änderungen gegenüber v1

Zwei Änderungen sind nicht nur strukturell (Bandzahl/-index), sondern
inhaltlich — wer Beschreibungstexte aus der v1-Ära weiterverwendet, muss
sie an diesen Stellen anpassen. Beide sind gegen den Code verifiziert
(`scripts/widmung_v2/04_create_distance_zones.py`):

- **Stromleitungen sind kein Ausschlusskriterium mehr.** v1 kannte ein
  eigenes Band `power_380_400kv` (Band 11 in der 54-Band-Liste). In v2 gibt
  es kein solches Band mehr; der Datei-Tag `POWER_LINES` sagt explizit
  `"kein Ausschlusskriterium (Clean-Schema Aug 2026)"` (Zeile 487).
- **„Wichtige Objekte" sind in `haeuser_im_gruenen` (750 m) aufgegangen.**
  v1 führte sie als eigenes Band mit 250-m-Puffer (`important_objects_source`
  / `important_objects_buffer`, Bänder 3-4). Der Datei-Tag
  `WICHTIGE_OBJEKTE` sagt explizit `"in haeuser_im_gruenen (750 m); vorher
  eigenes 250-m-Band"` (Zeile 485).
