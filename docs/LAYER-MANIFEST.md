# Layer-Manifest: wie `abschichtung.bands.json` das Dashboard steuert

Verbindliche Beschreibung, Stand 2026-09-09. Sie gilt für das Bänder-Manifest des
Produzenten und für seine Verwendung im Dashboard. Die Quelle dieses Dokuments
liegt beim Produzenten (`docs/LAYER-MANIFEST.md`), das Erzeugnis wird mit jedem
Export nach `out/LAYER-MANIFEST.md` kopiert und als fünfte Datei übergeben.

Dieses Dokument enthält die Regeln. Die daraus abgeleiteten, fertigen Texte für
alle 47 Bänder, die Kategorien, die Familien, die Stufen, die Schwellenwerte und
den Tunnel-Vorbehalt stehen zum Einsetzen in `MANIFEST-TEXTE.md`.

## Datierter Kopf (Paket W7.6, 09.09.2026 — hier eingefügt, im Original nicht vorhanden)

Diese Datei ist wortgleich aus dem Dashboard-Repo übernommen (dort entfernt,
nichts verweist mehr darauf), mit drei Korrekturen gegen den produzierten
Stand: die Kategorietexte-Tabelle in Abschnitt 5 fehlte für zwei der sieben
Kategorien (siehe dortige Anmerkung), und Abschnitt 8 beschrieb zwei
Arbeitsschritte als offen, die inzwischen (noch am 09.09.2026, Paket W7.6)
erledigt sind. Beide Korrekturen sind unten an Ort und Stelle markiert, nichts
wurde kommentarlos verändert.

**Zwei Zustände sind zu unterscheiden**, wie das Original selbst schon sagt
(unten, Zeile "Zwei Zustände..."): Abschnitte 1 bis 4a beschreiben den
Produzenten-Vertrag unabhängig von der Bandzahl und gelten unverändert.
Abschnitt 5 (Kategorie-, Familien- und Stufentexte) ist mit W7.6 **bereits
ausgeliefert** — Schema 2.2.1, alle sieben Kategorien, alle 16 Familien, alle
sieben Stufen tragen `description_de`, zeichengleich mit den Tabellen unten.
Abschnitte 6 und 7 (das 17-Layer-Set des End-Dashboards, die Bänder 45–47)
beschreiben weiterhin den **Zielzustand nach W7.8** — heute (Schema 2.2.1)
existieren nur 44 Bänder, nicht 47.

**Eine Abweichung vom in Abschnitt 8 beschriebenen Fahrplan:** `dashboard_layer`
und `default_visible` sind mit W7.6 bereits gesetzt, nicht erst mit den Bändern
45–47 (Nutzerentscheidung 09.09.2026 nachmittags, vorgezogen aus W7.8, weil
beide Felder nachweislich nicht an den neuen Bändern hängen). Das sind **nicht**
die 17/30-Werte aus Abschnitt 6 — die brauchen weiterhin die Bänder 45–47 —,
sondern ein Zwischenstand für die heutigen 44 Bänder: `dashboard_layer: true`
für 23 Bänder (2, 7, 9, 11, 13, 14, 15, 16, 17, 18, 19, 20, 23, 24, 25, 26, 27,
28, 29, 30, 32, 37, 38), `default_visible: true` für 5 Bänder (27, 28, 29, 32,
37 — die drei Kategoriesummen, die Eignungsflächen, die amtlichen Zonen).

Zwei Zustände sind zu unterscheiden. **Heute** liefert der Produzent Schema 2.2.0
mit 44 Bändern, davon 40 im Dashboard sichtbar. **Ziel** ist Schema 2.2.x mit 47
Bändern und 17 sichtbaren Layern; die Abschnitte 5 bis 7 beschreiben den
Zielzustand, die Abschnitte 1 bis 4 gelten für beide.

> Anmerkung (W7.6): der Satz oben ("Heute liefert der Produzent Schema 2.2.0
> mit 44 Bändern, davon 40 im Dashboard sichtbar") ist der Stand VOR diesem
> Paket und bewusst unverändert stehen gelassen (Original-Wortlaut). Der
> tatsächliche Stand nach W7.6 ist Schema **2.2.1**, `dashboard_layer: true`
> für **23** (nicht mehr 40) der 44 Bänder — siehe datierter Kopf oben.

## 1. Übergabe

| Datei | Ziel im Dashboard | committet |
|---|---|---|
| `abschichtung.tif` | `scripts/raster/abschichtung.tif` | nein, gitignored; Prüfsumme steht in PIPELINE.md |
| `abschichtung.bands.json` | `scripts/raster/` **und** `src/lib/data/abschichtung.bands.json` | ja, die Kopie unter `src/lib/data/` |
| `wka_bestand_punkte.geojson` | `scripts/raster/` | nein; daraus entsteht `geodata/existing_turbines.geojson` (committet) |
| `LAYER.md` | `src/lib/data/LAYER.md` | ja |
| `LAYER-MANIFEST.md` | nur gelesen, nicht kopiert | nein |

Die Kopie unter `src/lib/data/` ist die einzige Quelle für Namen, Texte, Farben,
Reihenfolge und Startsichtbarkeit. Im Dashboard steht keine zweite Layer-Liste.

Jede Übergabe nennt: Branch, Commit, Prüfsumme des TIF, die Pfade, die Zählungen
der Punkte-Datei, das Testergebnis und die Laufzeit. Werden mehrere Prüfsummen
genannt, ist genau eine als die einzutragende markiert.

## 2. Aufbau des Manifests

**Vertragsfelder**, deren Änderung ein Schemabruch ist: `band_count`,
`bands[].index` (1-basiert, gleich der Bandnummer im TIF), `bands[].name`
(eindeutig, stabil, nur `[a-z0-9_]`), `bands[].rolle`.

**Informative Felder**, die das Dashboard auswertet:

| Feld | Ebene | Verwendung |
|---|---|---|
| `schema_version` | oben | Verträglichkeitsprüfung, muss `2.x` sein |
| `category_order` | oben | Reihenfolge der Kategorien |
| `kategorien[]` | oben | `key`, `category`, `label_de`, `description_de` je Kategorie |
| `familien[]` | oben | geordnetes Array `{key, category, label_de, description_de}`; Array-Reihenfolge = Anzeigereihenfolge in der Kategorie |
| `stufe_order` | oben | Reihenfolge der Stufen innerhalb einer Familie |
| `stufen[]` | oben | `{key, label_de, description_de}`, erklärt das Stufen-Vokabular |
| `parameters` | oben | Schwellenwerte und Kennzahlen für die Methodik-Seite, maschinenlesbar |
| `sources`, `raster` | oben | Datenstände, Gitter (25 m, EPSG:31287) auf der Methodik-Seite |
| `caveats[]` mit `affects.bands` | oben | Vorbehalte, erscheinen an jedem betroffenen Layer |
| `category` | Band | Zuordnung zur Kategorie, muss in `category_order` stehen |
| `familie` | Band | Zuordnung zur Familie, `(familie, category)` muss in `familien` stehen |
| `stufe` | Band | eine der Stufen aus `stufe_order` |
| `dashboard_layer` | Band | `false` blendet das Band vollständig aus, fehlt das Feld, gilt `true` |
| `default_visible` | Band | Sichtbarkeit beim Laden der Karte |
| `label_de` | Band | Anzeigename des Layers |
| `description_de` | Band | Beschreibung im Tooltip und in der Methodik-Tabelle |
| `puffer_m`, `puffer_hinweis` | Band | Kurzhinweis neben dem Namen, Erläuterung im Tooltip |
| `color_rgba` | Band | Layerfarbe `[r, g, b, a]` |
| `quelle[]`, `abgeleitet_von[]` | Band | Quellenangabe im Tooltip, aufgelöst über `sources` |

Alles Weitere wird ignoriert und darf frei ergänzt werden.

> Geprüft gegen `out/abschichtung.bands.json` (Schema 2.2.1, W7.6): jedes
> Feld dieser Tabelle ist tatsächlich vorhanden, kein erfundenes und keines
> fehlt. Keine Korrektur nötig.

## 3. Wie aus dem Manifest Layer werden

1. **Layer-Menge:** jedes Band mit `dashboard_layer != false`.
2. **Identität:** der Bandname ist zugleich Dateiname der extrahierten GeoJSON,
   Layername in den Vektor-Tiles, `source-layer` in der Karte und Schlüssel im
   Sichtbarkeits-Speicher. Es gibt keine Dashboard-eigenen Kurznamen.
3. **Anzeige:** Name aus `label_de`, Text aus `description_de`, Farbe aus
   `color_rgba`, Kurzhinweis aus `puffer_m`, Startzustand aus `default_visible`.
4. **Baum:** `category_order` → `familien` → `stufe_order` → `index`. Überschrift
   und Info-Text der Kategorie aus `kategorien[]`, der Familie aus `familien[]`.
   Die Familienüberschrift entfällt, wenn die Familie nur einen Layer hat.
5. **Bestandsanlagen** sind keine Bänder, sondern Punkte aus
   `wka_bestand_punkte.geojson` mit dem Merkmal `in_zone`. Sie erscheinen unter
   Referenz als zwei Schalter, außerhalb der Zonen beim Laden an, innerhalb aus.
6. **Fehlerverhalten:** fehlt ein Band im TIF oder umgekehrt, bricht die
   Extraktion ab. Fehlt `label_de`, zeigt das Dashboard den Bandnamen. Unbekannte
   Stufe oder Familie landet am Ende der Liste, unbekannte Kategorie unter
   „Sonstige".

> Dieser Abschnitt beschreibt die Dashboard-Ableitung, nicht den Produzenten —
> nicht das Territorium von W7.6. Nicht korrigiert, nur gegen den Produzenten
> gegengelesen; Befunde dazu stehen im Bericht zu W7.6, nicht hier.

## 4. Regeln für Änderungen

Grundsatz: alles wird im Produzenten definiert, das Dashboard folgt ohne
Codeänderung. Wer umbenennen, beschreiben, umsortieren oder ausblenden will,
ändert das Manifest, nicht den Dashboard-Code.

| Änderung | Folgen im Dashboard | Version |
|---|---|---|
| Text (`label_de`, `description_de`, `puffer_hinweis`, Kategorie- und Familientexte) | nur Manifest kopieren, kein Kachelbau, TIF und Prüfsumme unverändert | Patch |
| Farbe, `default_visible`, Reihenfolge | Manifest kopieren | Patch |
| `dashboard_layer` umstellen | Manifest kopieren und Kacheln neu bauen, die Layer-Menge ändert sich | Patch |
| neues informatives Feld | keine, bis das Dashboard es auswertet | Minor |
| Band anhängen | neuer Index = bisheriges `band_count` + 1, neuer Schema-Name, neue Prüfsumme, Kacheln neu | Minor |
| Band umbenennen | Kachel- und Dateinamen ändern sich, Kacheln neu, gespeicherte Sichtbarkeit im Browser verfällt | Minor |
| Band entfernen oder Indizes verschieben | Schemabruch, alles neu | Major |
| neue Kategorie oder Familie | Eintrag in `category_order`, `familien` und `kategorien` **vor** dem ersten Band, das ihn nutzt | Minor |
| Pixel ändern bei gleichem Schema | TIF, Prüfsumme und Kacheln neu | Patch |

**Invarianten**, die jedes gültige Manifest erfüllt:

- `band_count == len(bands)`, `bands[i].index == i + 1`, Bandzahl im TIF gleich
  `band_count`.
- Bandnamen eindeutig; jede `category` in `category_order`; jedes
  `(familie, category)` in `familien`; jede `stufe` in `stufe_order`.
- Jede Kategorie aus `category_order` hat genau einen Eintrag in `kategorien`;
  `key`-Werte sind Kleinbuchstaben-Schlüssel, `category` ist der Anzeige-String.
- `default_visible` ist eine Produzenten-Entscheidung, das Dashboard setzt keine
  eigenen Vorgaben.
- Kein Text behauptet einen Filter, den der Code nicht ausführt.

> Geprüft gegen `out/abschichtung.bands.json` (W7.6): alle fünf Invarianten
> halten — `band_count == 44 == len(bands)`, Indizes lückenlos 1..44,
> Bandzahl im TIF ebenfalls 44 (rasterio `count`), 44 eindeutige Namen, jede
> `category` in `category_order`, jedes `(familie, category)`-Paar in
> `familien`, jede `stufe` in `stufe_order`, genau 7 `kategorien`-Einträge für
> 7 `category_order`-Einträge, `key` durchgehend Kleinbuchstaben. Keine
> Korrektur nötig.

## 4a. Textkonventionen

**`label_de` benennt, mehr nicht.** Keine Meterangabe, kein Schwellenwert, keine
Aufzählung, kein Klammerzusatz, keine Bandnummer, kein Summenzeichen. Erlaubt
sind Buchstaben, Leerzeichen und Bindestriche; Umlaute und ß zählen als
Buchstaben. Zwei bis drei Wörter sind das Ziel, der Name muss in einer schmalen
Layerliste lesbar bleiben. Ein automatischer Test prüft das für **alle** Bänder,
auch die ausgeblendeten. Wo bisher eine Zahl die Identität trug, tritt ein Wort
an ihre Stelle: die vier Unschärfebänder heißen nach ihrer Stärke, ihr
Sigma-Wert steht in der Beschreibung. Wo Quelle und Zone derselben Familie sonst
gleich hießen, trägt die Zone das Wort „Ausschluss" voran.

**`description_de` trägt alles Quantitative und jede Aufzählung.** Ein bis drei
ganze Sätze auf Deutsch, in der Reihenfolge: was ausgeschlossen wird, mit welchem
Abstand, aus welcher Quelle, welche Sonderfälle gelten. Zahlen mit Einheit
ausschreiben.

**Verboten in beiden Feldern:** interne Bandnamen, Konfigurationsschlüssel,
Skriptnamen, Bandnummern als Verweis, englische Sätze, Abkürzungen ohne
Auflösung.

**Zahlen kommen aus der Konfiguration**, nie aus einem Vorschlag. Wer eine
Beschreibung schreibt, setzt den Wert ein, den die Kette rechnet, und nennt Datei
und Zeile. Weicht der Code von einer bisherigen Aussage ab, ist das ein Befund.

**Wirkungslose Filter werden nicht wegformuliert.** Existiert ein Filter, läuft
aber ins Leere, beschreibt der Text die tatsächliche Wirkung **und** das Band
bekommt einen Vorbehalt in `caveats[]` mit der Nummer des Registerpunkts. Eine
still angepasste Beschreibung würde den Defekt zur Entwurfsentscheidung erklären.

**Puffer doppelt führen:** `puffer_m` maschinenlesbar (null, wenn kein isotroper
Puffer), `puffer_hinweis` für Sonderfälle wie bundeslandabhängige Werte,
Korridorgeometrie oder einen Puffer, der bereits im Quellband steckt.

> Geprüft gegen `out/abschichtung.bands.json` (W7.6): ein mechanischer Test
> (`tests/test_band_manifest.py`) liest jedes `label_de` aller 44 Bänder und
> lässt nur Buchstaben, Leerzeichen und Bindestriche zu — 0 Verstöße. Kein
> Text behauptet einen Tunnelfilter, den der Code nicht ausführt: Band 17
> (`cableway_people_150m`) nennt keinen Tunnel-Halbsatz, weil
> `aerialways.parquet` keine `tunnel`-Spalte führt und der Code dort keinen
> Filter versucht; die Bänder 14–16 nennen ihn korrekt, weil er dort läuft
> (siehe `_non_tunnel_mask()`, `calc/abschichtung_common.py`).

## 5. Kategorie-, Familien- und Stufentexte

Form im Manifest:

```json
"kategorien": [
  {"key": "mensch",    "category": "Mensch",                         "label_de": "Mensch",    "description_de": "…"},
  {"key": "natur",     "category": "Natur",                          "label_de": "Natur",     "description_de": "…"},
  {"key": "geo",       "category": "Geografie",                      "label_de": "Geografie", "description_de": "…"},
  {"key": "ergebnis",  "category": "Total & Ergebnis",               "label_de": "Ergebnis",  "description_de": "…"},
  {"key": "varianten", "category": "Siedlungsabstand-Varianten",     "label_de": "Varianten", "description_de": "…"},
  {"key": "referenz",  "category": "Referenz (Zonen & WKA-Bestand)", "label_de": "Referenz",  "description_de": "…"},
  {"key": "sonstige",  "category": "Sonstige",                       "label_de": "Sonstige",  "description_de": "…"}
]
```

`category` ist der Verbindungs-String zu `category_order` und `bands[].category`
und wird zeichengleich übernommen; `key` ist der kurze Maschinenschlüssel,
`label_de` die sichtbare Überschrift. Sieben Einträge, weil `category_order`
sieben Kategorien führt: „Siedlungsabstand-Varianten" und „Sonstige" sind
derzeit leer, brauchen aber einen Eintrag, damit die Invariante hält.

Die ausformulierten Texte für alle Bänder, Kategorien, Familien und Stufen samt
Schwellenwerten stehen in `MANIFEST-TEXTE.md`.

**Kategorietexte**

> Korrektur (W7.6): die Original-Tabelle führte nur fünf der sieben
> `kategorien`-Einträge (Varianten und Sonstige fehlten, obwohl der
> JSON-Ausschnitt oben sie zeigt). Gegen `out/abschichtung.bands.json`
> ergänzt — zeichengleich mit dem produzierten Manifest.

| Titel | Beschreibung |
|---|---|
| Mensch | Ausschlüsse wegen Nähe zu Menschen und ihrer Infrastruktur: Siedlungen, Häuser im Grünen, Gebäude, Verkehrswege, militärische Sperrgebiete und Luftfahrt. Quellen sind die Flächenwidmungen der neun Bundesländer, Kataster und Adressregister, OpenStreetMap sowie die niederösterreichischen Mindestabstandszonen. |
| Natur | Amtliche Schutzgebiete und Schutzgebiete aus OpenStreetMap gelten als Ausschluss. In dieser Kategorie gibt es keine Abstandspuffer, Quellen und Zonen fallen daher zusammen. |
| Geografie | Physische Kriterien aus Geländemodell, Windatlas und OpenStreetMap: Hangneigung, Seehöhe, Windleistungsdichte und größere Gewässer. Jedes Kriterium ist ein Schwellenwert, keine Abstandsregel. |
| Ergebnis | Die Vereinigung aller Ausschlüsse und ihr Gegenstück, die verbleibende Fläche. Die um Splitter bereinigte Fläche ist das Endergebnis der Abschichtung. |
| Varianten | Alternative Siedlungsabstände zum Vergleich mit dem Regelwert. Derzeit ist keine Variante konfiguriert, die Kategorie bleibt leer. |
| Referenz | Kein Ausschluss, sondern Vergleichsmaßstab: die amtlichen Windkraft-Zonen der Länder und die bestehenden Windräder. |
| Sonstige | Auffangkategorie für Bänder ohne eigene Zuordnung. Derzeit leer. |

**Familientexte** (`familien[].description_de`, Titel ist `label_de`)

| Titel | Beschreibung |
|---|---|
| Siedlung | Abstand um amtlich gewidmetes Wohnbauland. |
| Häuser im Grünen | Abstand um bewohnte Einzellagen außerhalb des Baulands. |
| Nicht-Wohn-Hüllen | Unbewohnte und industrieartige Kataster-Hüllen mit ihrem Fußabdruck. |
| Seilbahn-Gebäude | Liftstationen und andere Gebäude an Seilbahnlinien. |
| Gebäude | Übrige Gebäude aus OpenStreetMap und Kataster mit ihrem Fußabdruck. |
| Verkehr | Abstand entlang Straßen, Bahnen und Personenseilbahnen. |
| Militär | Militärische Sperrgebiete. |
| Luftfahrt | Flughafenareale und ihre An- und Abflugkorridore. |
| Gesamt Mensch | Alle Quellen und alle Ausschlussflächen der Kategorie Mensch, je als ein Band. |
| Schutzgebiete | Amtliche und offene Schutzgebietsdaten, ohne Abstandspuffer. |
| Gesamt Natur | Quellen und Ausschluss der Kategorie Natur, deckungsgleich, weil ohne Puffer. |
| Kriterien | Schwellenwerte für Gelände, Wind und Gewässer. |
| Gesamt Geografie | Quellen und Ausschluss der Kategorie Geografie, deckungsgleich, weil ohne Puffer. |
| Ergebnis | Gesamtausschluss sowie verfügbare Fläche, roh und bereinigt. |
| Amtliche Zonen | Windkraft-Positivzonen der Bundesländer. |
| WKA-Bestand | Bestehende Windräder als Park-Hüllen und als Einzelpunkte. |

**Stufentexte** (`stufen[]`)

| Schlüssel | Titel | Beschreibung |
|---|---|---|
| roh | Rohdaten | Rohdatensatz vor der Vereinigung, nur wo verschiedene Quellen in ein Band fließen. |
| quelle | Quelle | Objekte einer Quelle, ohne Abstandspuffer. |
| aggregat | Aggregat | Vereinigung der Quellen einer Familie, ohne Abstandspuffer. |
| zone | Zone | Ausschlussfläche mit Abstand, geht in die Summe ein. |
| summe_quellen | Summe Quellen | Vereinigung aller Quellen einer Kategorie. |
| summe_zonen | Summe Ausschluss | Vereinigung aller Ausschlussflächen einer Kategorie. |
| ergebnis | Ergebnis | Verfügbare Fläche nach Abzug aller Ausschlüsse. |

> Alle drei Tabellen dieses Abschnitts sind gegen `out/abschichtung.bands.json`
> (Schema 2.2.1) geprüft: 7 `kategorien`, 16 `familien`, 7 `stufen`, jede
> Beschreibung zeichengleich mit `description_de` im produzierten Manifest.

## 6. Layer-Set des End-Dashboards

**Zielzustand nach W7.8 — heute (Schema 2.2.1, 44 Bänder) noch nicht
erreicht.** Die Bänder 45–47 existieren noch nicht; `dashboard_layer` und
`default_visible` sind mit W7.6 zwar schon gesetzt (siehe datierter Kopf), aber
auf den heutigen 44-Bänder-Zustand (23 bzw. 5 Bänder), nicht auf das 17-Layer-
Set unten.

Regel: **je Familie ein zusammenfassender Layer**, keine Quell-, Roh-, Aggregat-
oder Detailzonen in der Karte. Alle Bänder bleiben im TIF und im Manifest, die
Methodik-Seite listet weiterhin alle. Wo es je Familie kein zusammenfassendes
Band gab, hängt der Produzent eines an: `gebaeude_zone` (45, Vereinigung von 9,
11 und 13), `verkehr_zone` (46, aus 14 bis 17), `luftfahrt_zone` (47, aus 19 und
20). Geografie bleibt vierfach, weil Hangneigung, Seehöhe, Wind und Gewässer vier
verschiedene Gründe sind und nicht vier Quellen desselben Grundes.

17 Layer, dazu die Bestandsanlagen als Punkte. „Start" ist `default_visible`.

| Kategorie | Band | `label_de` | Start |
|---|---|---|---|
| Mensch | 2 `settlement_buffer` | Siedlungsabstand | aus |
| Mensch | 7 `haeuser_im_gruenen` | Häuser im Grünen | aus |
| Mensch | 45 `gebaeude_zone` | Gebäude und Anlagen | aus |
| Mensch | 46 `verkehr_zone` | Verkehr | aus |
| Mensch | 18 `military_restricted_area` | Militärisches Sperrgebiet | aus |
| Mensch | 47 `luftfahrt_zone` | Luftfahrt | aus |
| Mensch | 27 `exclusion_human` | Ausschluss Mensch | **an** |
| Natur | 28 `exclusion_nature` | Ausschluss Natur | **an** |
| Geografie | 23 `geography_slope_too_steep` | Hangneigung zu steil | aus |
| Geografie | 24 `geography_elevation_too_high` | Seehöhe zu hoch | aus |
| Geografie | 25 `geography_wind_too_low` | Wind zu gering | aus |
| Geografie | 26 `geography_water_bodies` | Größere Gewässer | aus |
| Geografie | 29 `exclusion_geography` | Ausschluss Geografie | **an** |
| Ergebnis | 30 `all_exclusions` | Ausschluss gesamt | aus |
| Ergebnis | 32 `available_cleaned_min_10ha` | Eignungsflächen | **an** |
| Referenz | 37 `official_wind_zoning` | Amtliche Windkraft-Zonen | **an** |
| Referenz | 38 `wka_bestand_ausserhalb_zonen` | WKA-Bestand außerhalb der Zonen | aus |

Nicht in der Karte (`dashboard_layer: false`, 30 Bänder): 1, 3, 4, 5, 6, 39
(Quellen und Aggregat Häuser im Grünen); 8, 9, 10, 11, 12, 13, 40, 41 (Quellen,
Rohdaten und Detailzonen der Gebäude); 14, 15, 16, 17 (Detailzonen Verkehr); 19,
20 (Detailzonen Luftfahrt); 21, 22 (Schutzgebiete einzeln); 31 (verfügbare Fläche
roh); 33 bis 36 (Unschärfe); 42, 43, 44 (Summe Quellen).

Hinweis für den Kachelbau: `sources_human` (42) besteht aus ungepufferten Linien
und zerfällt bei 25 m Auflösung in Millionen Einzelpolygone; es ist als Vektor
nicht ausleitbar. Als Rasterband ist es unauffällig. Bänder aus 0-m-Linien sind
generell keine Kandidaten für einen Vektor-Export.

## 7. Zieltexte der sichtbaren Layer

**Zielzustand nach W7.8**, ebenso wie Abschnitt 6 — die Bänder 45–47 fehlen
heute noch. Die Zeilen für bereits existierende Bänder (2, 7, 18, 27, 23, 24,
25, 26, 29, 30, 32, 37, 38) sind dagegen schon mit W7.6 ausgeliefert und
zeichengleich mit `out/abschichtung.bands.json`.

Schwellenwerte gelesen aus `config.json` und `calc/config.py`, Stand 2026-09-09.

| Band | `label_de` | `description_de` |
|---|---|---|
| 2 | Siedlungsabstand | Abstand von 1.000 m um amtliches Wohn-, Misch-, Kern- und Dorfgebiet aller neun Bundesländer; in Niederösterreich 1.200 m. |
| 7 | Häuser im Grünen | Abstand von 750 m um bewohnte Einzellagen außerhalb des Baulands: Ferienhaus- und Tourismusgebiete, amtliche Widmungen für Hofstellen, Camping, Golf, Kleingärten und Auffüllungsgebiete sowie Streusiedlungen. In Niederösterreich gelten stattdessen die Mindestabstandszonen des Sektoralen Raumordnungsprogramms, die den Abstand bereits enthalten. |
| 45 | Gebäude und Anlagen | Fußabdrücke aller übrigen Gebäude mit ihrem Abstand: unbewohnte und industrieartige Kataster-Hüllen sowie sonstige Gebäude und Einzellagen mit je 25 m, Seilbahn-Gebäude mit 50 m. |
| 46 | Verkehr | Abstand von 150 m beiderseits von Autobahnen und Schnellstraßen, Bundes- und Landesstraßen, Hauptbahnen und Personenseilbahnen. Schlepplifte und Materialseilbahnen zählen nicht als Personenseilbahn. |
| 18 | Militärisches Sperrgebiet | Militärische Sperrgebiete, ohne zusätzlichen Abstand. |
| 47 | Luftfahrt | Areale der Hauptflughäfen sowie ihre An- und Abflugkorridore: 5 km ab beiden Landebahn-Enden, ±15° um die verlängerte Bahnachse. |
| 27 | Ausschluss Mensch | Vereinigung aller Ausschlüsse der Kategorie Mensch: Siedlungsabstand, Häuser im Grünen, Gebäude und Anlagen, Verkehr, Militär und Luftfahrt; auf das Staatsgebiet zugeschnitten. |
| 28 | Ausschluss Natur | Amtliche Schutzgebiete, also Nationalparks, Naturschutzgebiete, Europaschutzgebiete nach Natura 2000 und Ramsar-Gebiete, sowie Schutzgebiete aus OpenStreetMap, vereinigt und auf das Staatsgebiet zugeschnitten. Ohne Abstandspuffer. |
| 23 | Hangneigung zu steil | Hangneigung über 15 Grad, ermittelt aus dem Geländemodell mit 25 m Auflösung. |
| 24 | Seehöhe zu hoch | Seehöhe über 2.500 m, ermittelt aus dem Geländemodell mit 25 m Auflösung. |
| 25 | Wind zu gering | Windleistungsdichte in 150 m Höhe unter rund 160 W/m², aus dem Globalen Windatlas. Der Grenzwert entspricht 150 W/m² in 130 m Höhe, mit dem Windprofil auf 150 m hochgerechnet. |
| 26 | Größere Gewässer | Seen, Stauseen und Flüsse aus OpenStreetMap, zusammenhängende Wasserflächen ab 1 ha. |
| 29 | Ausschluss Geografie | Vereinigung der Kriterien Hangneigung, Seehöhe, Wind und Gewässer; auf das Staatsgebiet zugeschnitten. |
| 30 | Ausschluss gesamt | Vereinigung der Ausschlüsse aus Mensch, Natur und Geografie: alles, was ausgeschlossen ist. |
| 32 | Eignungsflächen | Das Endergebnis: die nach Abzug aller Ausschlüsse verbleibende Fläche, bereinigt um Splitter; nur zusammenhängende Flächen ab 10 ha. |
| 37 | Amtliche Windkraft-Zonen | Alle amtlichen Windkraft-Positivzonen der Länder in einem Layer: Zonierung Niederösterreich, Vorrang- und Eignungszonen Steiermark, Vorrangzonen Salzburg, Eignungszonen Burgenland, Beschleunigungszonen Kärnten. Dient dem Vergleich mit der Abschichtung und ist selbst kein Ausschluss. |
| 38 | WKA-Bestand außerhalb der Zonen | Bestehende Windräder aus OpenStreetMap außerhalb der amtlichen Zonen, zu Park-Hüllen zusammengefasst: Anlagen mit weniger als 750 m Abstand bilden einen Park, dessen Hülle 200 m Rand erhält. Referenz, kein Ausschluss. |

Die drei Schwellenwerte der Kategorie Geografie stehen heute nur im Quelltext.
Sie kommen zusätzlich maschinenlesbar nach `parameters`, im dort vorhandenen Stil
aus Großbuchstaben und Unterstrichen: `SLOPE_MAX_DEG`, `ELEVATION_MAX_M`,
`PD_MIN_W_M2` mit `PD_MIN_REFERENCE_HEIGHT_M` und `PD_MIN_AT_150M_W_M2`. Damit
muss das Dashboard keine Zahl aus einem Satz lesen.

> Erledigt (W7.6): die fünf Parameter stehen bereits in `parameters`, mit den
> gemessenen Werten `SLOPE_MAX_DEG=15.0`, `ELEVATION_MAX_M=2500.0`,
> `PD_MIN_W_M2=150.0`, `PD_MIN_REFERENCE_HEIGHT_M=130.0`,
> `PD_MIN_AT_150M_W_M2=159.4971` — der Satz oben ("stehen heute nur im
> Quelltext") ist damit überholt, absichtlich unverändert stehen gelassen
> (Original-Wortlaut), siehe datierten Kopf.

Die ausgeblendeten Bänder werden mitbenannt, nicht ausgenommen. Wo Quelle und
Zone derselben Familie sonst gleich hießen, trägt die Zone das Wort „Ausschluss"
voran; die Unschärfebänder heißen nach ihrer Stärke statt nach ihrem Sigma-Wert;
die Summenbänder 42 bis 44 heißen „Quellen Mensch", „Quellen Natur" und „Quellen
Geografie". Der vollständige Satz steht in `MANIFEST-TEXTE.md`, Abschnitt 1, mit
einer Gegenüberstellung alt gegen neu in Abschnitt 2.

## 8. Stand und offene Punkte

> Zwei Punkte unten sind mit W7.6 erledigt, nicht mehr offen — im
> Original-Wortlaut stehen gelassen und hier markiert, nicht gelöscht
> (dieselbe Regel wie oben).

- Der Zielzustand aus den Abschnitten 5 bis 7 ist noch nicht ausgeliefert. Er
  entsteht in zwei Schritten: zuerst alle Texte für bestehende Bänder, ohne
  Änderung am TIF; danach die drei neuen Bänder samt `dashboard_layer` und
  `default_visible`, mit neuem Schema-Namen und neuer Prüfsumme. Beide Schritte
  sind textlich fertig ausformuliert und warten nur auf den Einbau.
  **→ Erledigt (W7.6): der erste Schritt (Abschnitt 5, alle Bandtexte) ist
  ausgeliefert, Schema 2.2.1. Nur der zweite Schritt (Bänder 45–47) steht noch
  aus, für W7.8.**
- Der erste Schritt ist reine Textarbeit: `kategorien`, `stufen`, die
  Familienbeschreibungen, fünf neue Einträge in `parameters`, ein dritter
  Vorbehalt und neue Werte für `label_de` und `description_de`. Er ändert kein
  Pixel, braucht keinen Kachelbau und keine neue Prüfsumme.
  **→ Erledigt (W7.6), siehe oben. Bestätigt: kein Pixel geändert (bandweiser
  Vergleich, 0 abweichende Zellen über alle 44 Bänder), aber die
  Datei-Prüfsumme des TIF ändert sich doch — die fünf neuen
  `parameters`-Werte werden auch als GeoTIFF-Datei-Tags geschrieben, das
  ändert Metadaten-Bytes, keine Pixel. Wer nur die Datei-Prüfsumme prüft, sieht
  fälschlich eine Änderung; maßgeblich ist der bandweise Pixelvergleich.**
- Der Tunnelfilter bei Autobahnen, Bundes- und Landesstraßen sowie Hauptbahnen
  prüft nur ein Merkmal und übersieht Objekte, die anders als unterirdisch
  ausgezeichnet sind. Betroffen sind 144 Objekte, die Flächenwirkung liegt unter
  0,7 Prozent der Potenzialfläche. Die Beschreibungen sagen die tatsächliche
  Wirkung, die drei Bänder tragen einen gemeinsamen Vorbehalt. Ob der Filter
  ergänzt wird, ist offen und bräuchte einen neuen Datenauszug.
- Die amtlichen Zonen werden im Dashboard derzeit zweimal gezeichnet, als
  Manifest-Layer und als älterer, immer sichtbarer Vektor-Layer. Einer von beiden
  sollte entfallen.
- `LAYER.md` ist beim Produzenten noch handgepflegt; ein Generator aus dem
  Manifest steht aus.
  **→ Erledigt (W7.6): `pipeline/export/layer_doc.py` erzeugt `out/LAYER.md`
  jetzt aus `out/abschichtung.bands.json`, kein Bandname mehr im Code, kein
  Kopierziel mehr. `docs/layer.md` (die handgepflegte Vorlage) ist entfernt,
  siehe Bericht zu W7.6.**
- Die Punkte der Bestandsanlagen führen Betreiber, Leistung und Inbetriebnahme
  nicht, weil die Aufbereitung diese Merkmale nicht ausliest. Das Dashboard
  ergänzt sie aus einer kuratierten Datei über den nächsten Nachbarn.
