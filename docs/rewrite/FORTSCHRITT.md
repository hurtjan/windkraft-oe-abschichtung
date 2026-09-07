# Fortschritt des Umbaus

Laufendes Protokoll. Eine Zeile je Paket, ergänzt um einen Eintrag je
abgeschlossenem Paket. **Diese Datei wird nach jedem Paket fortgeschrieben**
— sie ist zusammen mit `PLAN.md` das, was einen Sitzungsabbruch überlebt.

Der Plan selbst steht in [`PLAN.md`](PLAN.md); Zuschnitt und Zielbaum von
W0.1 in dessen §11. Die Belege liegen unter
[`nachweise/`](nachweise/), die Abweichungen in `abweichungen.tsv`.

## Stand

| | |
|---|---|
| Abgeschlossen | **23 von 32** — Welle 0 und Welle 1 vollständig, beide Zusammenführungen, beide Nachzügler. Zwei Pakete sind neu dazugekommen (W2.P0, W2.4), eines ist entfallen (W2.2 → W2.1). |
| Als Nächstes | **W2.P0**, dann Welle 2 zu dritt — die erste Welle, die Bänder verändern darf |
| `data/` | **hardlinkfrei**, 48 echte Dateien, per Wächter als Invariante gesichert |
| Zweig | `docs/audit-und-plan`, Kopf `0b61884`, kein Remote |
| Worktrees | keine — alle neun abgebaut, alle Zweige mit `git branch -d` gelöscht |
| Abweichungen bisher | **keine** — alle Pakete bitgleich, `sha256` an der Wellengrenze bestätigt |

## Paketübersicht

Status: `offen` · `läuft` · `fertig` · `blockiert`

Die Schätzung wird **vor** dem Paket eingetragen und danach nicht mehr
geändert — nur so wird sichtbar, wo ich mich verschätze. „Gebraucht" ist
Wanduhrzeit von der Beauftragung bis zum Commit.

| Paket | Titel | Status | geschätzt | gebraucht | Abnahme |
|---|---|---|---:|---:|---|
| W0.1 | Rohdaten nach Thema sortieren | **fertig** | — | 49 min | bitgleich · 30/30 Inodes |
| W0.2 | Pfadvertrag anlegen | **fertig** | — | 28 min | bitgleich · 131 Tests |
| W0.3 | Verzeichnisgerüst und Make-Ziele | **fertig** | — | 12 min | 131 Tests · `make -n` gleich |
| W1.7 | Ausschlusszonen entfernen | **fertig** | 25 min | 15 min | bitgleich — *keine* Bandänderung |
| W1.1 | Adress-Cache-Weiche entfernen | **fertig** | 20 min | 8 min | bitgleich · 130 Tests · Cache echt geprüft |
| W1.5 | Tote Skripte löschen | **fertig** | 15 min | 14 min | bitgleich · 130 Tests |
| W1.6 | NÖ-PDF-HiG-Sackgasse entfernen | **fertig** | 25 min | 14 min | bitgleich · 130 Tests · Sackgasse belegt |
| W1.8 | Paketmetadaten bereinigen | **fertig** | 15 min | 8 min | bitgleich · 130 Tests |
| W1.9 | Doku-Widersprüche korrigieren | **fertig** | 15 min | 13 min | nur Doku · 130 Tests |
| — | Zusammenführung der vier Zweige | **fertig** | 15 min | 30 min | bitgleich · 130 Tests · 3 stille Fehler gefunden |
| W1.2 | Tote Daten löschen, Provenienz retten | **fertig** | 20 min | 22 min | bitgleich · 50/50 Inodes · 129+1 Tests |
| W1.3 | Hardlinks auflösen | **fertig** | 20 min | 14 min | 48/48 aufgelöst · Vorgänger 48/48 unversehrt |
| W1.4 | Wächter für Rohdaten | **fertig** | 25 min | 13 min | bitgleich · 129 → **136** Tests |
| W1.P0 | Vorfeld der Prep-Welle | **fertig** | 20 min | 13 min | bitgleich · 136 → **147** Tests |
| W1.P1 | Prep: Verwaltungsgrenzen | **fertig** | 25 min | 12 min | Bundesländer **0,0 m² Differenz** · 147 Tests |
| W1.P2 | Prep: Kataster | **fertig** | 60 min | 27 min | **Volllauf gemessen: 45–70 min statt 5 h** |
| W1.P3 | Prep: Adressregister | **fertig** | 40 min | 6 min | Parquets **bitgleich** · 147 Tests |
| W1.P4 | Prep: Flächenwidmung | **fertig** | 45 min | 8 min | **9/9 Länder Differenz 0** · 147 Tests |
| W1.P5 | Prep: OSM, zwei Stufen | **fertig** | 45 min | 26 min | 10/10 Gruppen exakt · Lauf **286 s** |
| W1.P6 | Prep: Gelände und Wind | **fertig** | 20 min | 19 min | Windraster weicht **vollständig** ab · 147 Tests |
| W1.P7 | Prep: Naturschutz | **fertig** | 25 min | 8 min | 920 Geometrien **WKB-bytegleich** · 147 Tests |
| W1.P8 | Prep: Windzonen | **fertig** | 30 min | 7 min | **0,0 m²** bei allen vier Quellen · 147 Tests |
| W1.P9 | Prep: NÖ-SekROP-PDF, zwei Stufen | **fertig** | 45 min | 20 min | **12/12 GeoJSON bytegleich** · Laufzeit halbiert |
| — | Zusammenführung der Prep-Welle | **fertig** | 25 min | 7 min | **9 Merges konfliktfrei** · `sha256` bitgleich · 147+1 Tests |
| — | Datenfenster: alte Adress-Parquets (Punkt 19) | **fertig** | 15 min | 4 min | Inode belegt `mv` · 147+1 Tests · Wächter 129 → 127 |
| — | Prep-Stufe für die fünfte Zonenquelle (Punkt 22) | **fertig** | 20 min | 8 min | **0,0 m²** · 71/71 Geometrien gleich · 147+1 Tests |
| W2.P0 | Vorfeld der Layer-Welle | offen | 25 min | | `build/prep/` ins Worktree |
| W2.1 | Layer: Widmung und Häuser im Grünen | offen | 60 min | | W2.2 hier aufgegangen |
| W2.3 | Layer: OSM und Infrastruktur | offen | 45 min | | |
| W2.4 | Layer: Natur, Gelände, Zonen und Puffer | offen | 50 min | | **17 herrenlose Checkpoints** |
| W3.1 | Finalisierung und Manifest-Vertrag | offen | 45 min | | |
| W3.2 | Validierung | offen | 30 min | | schreibt `abweichungen.tsv` |
| W4.1 | Dashboard neu | offen | 40 min | | |
| W4.2 | Gemeindegrenzen-Export | offen | 30 min | | |
| W4.3 | Tests verdrahten | offen | 30 min | | |
| W5.1 | Beweislauf aus Rohdaten | offen | 15 min | | **+ Vorverarbeitung** |

## Zeitbilanz

| | |
|---|---|
| Gebraucht bisher | **rund 4 h 45** Wanduhrzeit für 21 Pakete plus zwei Zusammenführungen |
| davon Welle 0 | 1 h 29, seriell (49 + 28 + 12 min) |
| davon Welle 1, Aufräumen | 29 min (W1.7 seriell 15 min, dann vier parallel in 14 min) |
| davon erste Zusammenführung | 30 min — doppelt so lang wie geschätzt |
| davon beide Datenfenster | 36 min, seriell (22 + 14) |
| davon Wächter und Vorfeld | 26 min (13 + 13) |
| davon Prep-Welle | rund 60 min für neun Pakete in Schüben (Summe der Einzelzeiten: 133 min) |
| davon zweite Zusammenführung | **7 min** |
| Verbleibend, geschätzt | **4 bis 5 ½ h** Wanduhrzeit |
| Davon unbekannt | **nichts mehr** — die Kataster-Vorverarbeitung ist von W1.P2 auf 45–70 min vermessen |

**Summe geschätzt gegen summe gebraucht**, über alle 20 Positionen mit
Schätzung (Welle 0 hatte keine): **550 min geschätzt, 297 min gebraucht —
minus 46 %.** Ich setze systematisch fast das Doppelte an. Genau zwei
Positionen liefen über: W1.2 mit +10 % und die erste Zusammenführung mit
+100 %.

Der erste echte Parallelbatch hat die Schätzung bestätigt und leicht
unterboten: vier Pakete, geschätzt 65 min in Summe, gebraucht 14 min
Wanduhrzeit. Der Gewinn ist nicht der Faktor vier, sondern der Faktor
gegenüber der **Summe** — die einzelnen Pakete waren zugleich schneller als
geschätzt (8, 8, 13, 14 statt 20, 15, 15, 15). Ich schätze Pakete dieser
Größe also systematisch zu hoch. Die Prep-Schätzungen lasse ich trotzdem
stehen: dort dominiert Rechenzeit, nicht Denkzeit, und die skaliert nicht
mit.

**Die Zusammenführung war der einzige Posten, den ich zu niedrig geschätzt
habe** — 15 min angesetzt, 30 gebraucht. Der Aufwand steckte nicht im
Mergen, sondern in der inhaltlichen Nachprüfung der zusammengeführten
Prosa. Das ist der Preis der Parallelität und gehört ab jetzt in die
Schätzung jeder Parallelstufe: **rund die Hälfte der eingesparten Zeit
kommt als Zusammenführung zurück, sobald sich Dateimengen überschneiden.**

Die Restdauer ist **nicht** die Summe der Einzelschätzungen (die ergäbe
gut 6 ¾ h), weil Pakete parallel laufen. Gerechnet ist je Stufe das längste
Paket plus Puffer für meine eigene Abnahme, die seriell bleibt:

| Stufe | Pakete | Wanduhr |
|---|---|---:|
| ~~W1.7 allein~~ | 1 | ~~25~~ · **15 min** |
| ~~Aufräumen, parallel~~ | 5 | ~~25~~ · **14 min** gemessen |
| ~~Datenfenster, seriell~~ | 2 | ~~40~~ · **36 min** |
| ~~Wächter und Vorfeld~~ | 2 | ~~25~~ · **26 min** |
| ~~Prep, gedrosselt~~ | 9 | ~~2 h 25~~ · **rund 60 min** |
| ~~Zusammenführung Prep~~ | — | ~~25~~ · **7 min** |
| ~~Zwei Nachzügler (Punkt 19, 22)~~ | 2 | ~~20~~ · **12 min** |
| Vorfeld W2.P0, seriell | 1 | 25 min |
| Welle 2, **drei** parallel | 3 | 60 min |
| Zusammenführung Welle 2 | — | 20 min |
| Welle 3, seriell | 2 | 1 h 15 |
| Welle 4, parallel | 3 | 40 min |
| Zusammenführung Welle 4 | — | 15 min |
| Welle 5, inklusive Kataster-Volllauf | 1 | 1 h 15 – 1 h 40 |
| **Restdauer** | **11** | **5 ¼ – 5 ½ h roh · 3 ½ – 4 h korrigiert** |

Die Korrektur wendet den gemessenen Faktor 0,55 nur auf die **Denkzeit**
an. Welle 5 bleibt unkorrigiert: dort dominiert Maschinenzeit, die nicht
mitschrumpft — 45–70 min Kataster-Vorverarbeitung plus 14:26 Kettenlauf.
Und die vier Zusammenführungen setze ich weiterhin großzügig an, obwohl die
letzte 7 min brauchte; der Grund dafür steht unten und gilt nicht
automatisch für Welle 2.

**Warum nicht alle achtzehn gleichzeitig:** Innerhalb eines Pakets ist
nichts parallel — schreiben, prüfen, beweisen bauen aufeinander auf. Die
schweren Prep-Läufe konkurrieren um Platte und Kerne; neun gleichzeitig
werden nicht neunmal schneller, sondern verdrängen einander. Und jede
Abnahme braucht eine Entscheidung, die seriell fällt.

## Gemessene Laufzeiten

Aus `docs/RUN1_VERGLEICH.md`, ein sequentieller Lauf am 06.09.2026 mit
warmem Cache:

| Stufe | Dauer |
|---|---:|
| `03_build_osm_layers.py` | 6:15 |
| `04_create_distance_zones.py` | 4:58 |
| `02_build_hig_sources.py` | 2:23 |
| `01_build_official_zoning_layers.py` | 0:49 |
| `05_validate.py` | 0:01 |
| **Kette gesamt** | **14:26** |

**Nicht enthalten und nirgends gemessen:** die Vorverarbeitung, die das
Kataster-GeoParquet erzeugt (`export_at_dkm_geoparquet.py` über acht
Landesarchive plus NÖ-Rekonstruktion aus DXF). Stufe 1 verarbeitet in
49 Sekunden bereits fertiges GeoParquet, nicht die 9,1 GB DKM-Archive. Das
Zielbild nennt dafür die Größenordnung fünf Stunden — eine Behauptung ohne
Messung. **W1.P2 misst sie**, bevor Welle 5 davon abhängt.

Aufwand je Paket, gemessen an W0.1: **53 Minuten** Wanduhrzeit, davon
2,5 Minuten Datenbewegung und der Rest Schreiben und Prüfen.

## Protokoll

### W0.1 — Rohdaten nach Thema sortieren · fertig

Commits `5aab405` (Umbau) und `3fd54a8` (Nachweise, Nachzügler).

`data/` ist in neun Domänenverzeichnisse gegliedert: `admin`, `kataster`,
`adressen`, `widmung`, `osm`, `gelaende`, `natur`, `zonen`, `noe_sekrop`.
Die Zwei-Ordner-Falle der Flächenwidmung ist aufgelöst —
`flächenwidmungen/` und `new_widmungs_data/` sind zu
`data/widmung/<bundesland>/` zusammengeführt, `widmung_sources.py` hat statt
zwei Wurzeln nur noch eine.

**Abnahme: bestanden, ohne Abweichung.** Vier Nachweise, Belege unter
`nachweise/w01/`:

1. 56 Inodes vor und nach dem Verschieben, jeder genau einmal
   wiedergefunden; Linkcounts und Prüfsummen unverändert.
2. 35 funktionale Pfade lösen auf; alle geänderten Dateien kompilieren.
3. Finalisierung aus 34 Checkpoint-Layern in 167 s → `sha256` identisch zu
   `run1`.
4. 30 von 30 Codestellen zeigen auf **dieselbe** Inode wie vorher.

Der vierte Nachweis war nötig, weil die ersten drei eine Lücke lassen: Der
Bitgleichheitslauf hat drei der neun Verzeichnisse gar nicht angefasst, und
„der Pfad existiert" ist schwächer als „es ist dieselbe Datei". Die beiden
steirischen Widmungsquellen liegen jetzt im selben Verzeichnis; eine
Vertauschung wäre weder an einer Fehlermeldung noch an der Bandzahl
aufgefallen.

**Gelernt, mit Folgen für spätere Pakete:**

- `layer_done()` prüft nur Form, CRS, Transform und Bandname des
  vorhandenen Checkpoints, **nicht die Rohquelle**. Eine ausgetauschte
  Rohdatei bleibt unbemerkt. Der Fingerabdruck der Eingänge gehört daher
  auch auf die Layer-Stufe (W2.1–W2.3), nicht nur ins Prep.
- Eine Textsuche nach `data/` findet nicht alles: drei Dateien setzen ihre
  Pfade zusammen (`ROOT / "data" / …`), eine weitere lag unter `docs/` und
  damit außerhalb der Suche. **Die Rückwärtssuche nach den alten Namen
  gehört in jedes Paket, das Pfade anfasst** — sie hat beide Lücken
  gefunden, die Vorwärtssuche keine.
- Ein Nachweis über Inodes ist stärker und billiger als ein Testlauf:
  Sekunden statt Stunden, und er belegt Identität statt nur Erfolg.

### W0.2 — Pfadvertrag · fertig

`pipeline/contract.py` ist die einzige Quelle für Pfade und Layernamen:
31 Rohpfade in neun Domänen, 34 Layernamen, 11 Prep-Ausgaben, vier
Endprodukte. Layernamen sind Bezeichner, aus denen der Dateipfad abgeleitet
wird — nicht beides nebeneinander. Kein Import aus `windkraft` oder
`scripts`, kein Dateizugriff beim Import; der Vertrag beschreibt, er prüft
nicht.

`config.json` hat seine sieben Pfadliterale abgegeben. `load_config()`
befüllt den `paths`-Block jetzt aus dem Vertrag, mit byte-identischen
Werten — kein heutiger Konsument von `cfg["paths"][…]` merkt etwas davon.
Die Nicht-Pfad-Parameter (`nsg_gpkg`, `nsg_layers`) bleiben in der JSON.

**Abnahme: bestanden, ohne Abweichung.** 48 Vertragstests, 131 Tests in der
gesamten Suite, keine Regression. Nachweislauf aus den 34 Checkpoints in
163 s → `sha256` identisch zu `run1`.

Der schärfste Test ist der auf Werttreue: er hält die alten Werte als
**Konstanten im Test** fest, statt sie aus dem Vertrag zu ziehen. Ein Test,
der beide Seiten aus derselben Quelle bezieht, prüft nichts.

**Zwei Entscheidungen beim Zuschnitt:**

- `osm_power_lines.gpkg` und `WINDKRAFT_AUSSCHLUSSZONE.zip` stehen **nicht**
  unter `RAW`, sondern in `LEGACY["entfaellt"]`. Beide werden heute gelesen,
  aber in Welle 1 entfernt. Wer `contract.RAW["osm"]` liest, darf dort keine
  Datei finden, die nächste Woche weg ist — `RAW` beschreibt den
  Zielzustand des unveränderlichen Baums, nicht den Übergang.
- Wo der Code ein **Verzeichnis** bekommt und den Dateinamen selbst bildet
  (Adressen per ZIP-Suche, Tirol per Stichtags-Glob, Luca-Zonen als
  `<dir>/<key>.shp`), deklariert der Vertrag das Verzeichnis — nicht einen
  erfundenen Einzeldateinamen.

**Schuld, bewusst eingegangen:** `load_config()` rechnet die absoluten
Vertragspfade per `os.path.relpath()` in relative Strings zurück, um die
Altwerte buchstäblich zu treffen. Das ist richtig, solange es Konsumenten
von `cfg["paths"]` gibt, und verschwindet mit dem letzten.

### W0.3 — Verzeichnisgerüst und Make-Ziele · fertig

`build/` und `out/` sind in `.gitignore`, entstehen zur Laufzeit über
`pipeline/runtime.py` und **nicht** beim Import des Vertrags — der
beschreibt und prüft, er legt nichts an. Keine leeren Unterpakete auf
Vorrat: `pipeline/prep/`, `layers/`, `verify/` entstehen mit den Paketen,
die sie füllen.

Vier Ziele stehen: `make` (heutige Kette, unverändert), `make prep` (sagt,
dass die Prep-Pakete erst in Welle 1 entstehen — kein stiller Erfolg),
`make all`, `make test`. Letzteres gab es bisher **gar nicht**, weshalb die
acht vorhandenen Tests als unerreichbar galten; sie laufen jetzt.

**Abnahme: bestanden.** 131 Tests grün. Die Gleichheit der Kette ist nicht
durch einen Lauf belegt, sondern durch `make -n`: die fünf Befehlszeilen des
heutigen Ziels und die des neuen Standardziels stehen Zeile für Zeile
nebeneinander und sind identisch. `git diff Makefile` zeigt ausschließlich
Hinzufügungen.

**Vorgefundener Fehler, nicht von diesem Paket verursacht:** `make` ohne
Argument lief bisher **nicht** die Kette, sondern nur Stufe 1 von 5. GNU
Make nimmt ohne `.DEFAULT_GOAL` das erste Ziel der Datei, und das war
`widmung-v2-zoning`. Wer der Dokumentation folgte und `make` tippte, bekam
ein Fünftel der Arbeit ohne jeden Hinweis. Gegen den sauberen HEAD
gegengeprüft, dann per `.DEFAULT_GOAL` behoben.

**`make worktree PAKET=<paket>`** ist die Voraussetzung für Welle 1: es legt
ein Worktree an, hängt `data/` als **Symlink** hinein (13 GB achtzehnmal zu
kopieren wäre absurd, ein Hardlink-Baum gefährlich) und teilt die 34
Checkpoint-Layer lesend, damit eine Abnahme drei statt vierzehn Minuten
kostet. Das Ziel warnt bei jedem Aufruf vor `--force-layers` — ein solcher
Lauf schriebe ins geteilte Layer-Verzeichnis und zerstörte die Arbeit aller
anderen Worktrees.

Beim Test aufgefallen: `data/README.md` ist die einzige versionierte Datei
unter `data/`, also legt `git worktree add` das Verzeichnis bereits an — und
`ln -s` hängt sich dann *hinein* statt es zu ersetzen. Ergebnis wäre
`data/data` gewesen. Behoben und mit einem Wegwerf-Worktree verifiziert.

### W1.7 — Ausschlusszonen entfernen · fertig

Entfernt: die Registrierung `Stmk2026Aus` (las eine SAPRO-2026-GeoJSON, für
die es in diesem Repo keinen Erzeuger gibt) und `OOe` (las
`WINDKRAFT_AUSSCHLUSSZONE.zip`). Dazu die Folgeaufräumung: die nur davon
benutzte Konstante `REGIME_ADVISORY` und der Kommentarblock, der
ausschließlich die SAPRO-Farbextraktion erklärte. Im Pfadvertrag ist der
Eintrag `ausschlusszone_zip` weg — die Datei bleibt, bis W1.2 sie löscht.

**Abnahme: bitgleich, 130 Tests grün.** Der Testzähler sinkt von 131 auf
130, weil eine parametrisierte Prüfung mit dem entfernten Vertragseintrag
wegfällt.

**Der eigentliche Befund ist ein anderer: die Änderung ist folgenlos.**
`load_wind_exclusion_zones()` wird im ganzen Repo **nirgends aufgerufen**,
und ein Band `official_wind_exclusion_zoning` existiert im 38-Band-Schema
nicht. Band 37 wird allein aus `load_wind_zones()` gebaut. Die
Ausschlusszonen erreichten also nie ein Band — `run2.tif` ist bitgleich zu
`run1.tif`, dieselbe `sha256`, alle 38 Bänder.

Damit sind zwei Annahmen im Plan widerlegt und dort korrigiert: Entscheidung
(a) behauptete, Band 37 verliere die SAPRO-Zonen, und §12.1 sah deshalb
einen Wechsel der Vergleichsbasis vor. **Beides entfällt: `run1` bleibt für
das gesamte Projekt die Basis, und alle 38 Bänder müssen bitgleich sein,
ohne Sonderfall.** Eine Fehlerquelle weniger für 26 verbleibende Pakete.

**Nachtrag für W1.5:** Was von der Ausschlusszonen-Mechanik übrig ist —
`load_wind_exclusion_zones()`, `WIND_EXCLUSION_ZONE_SOURCES` mit dem
verbliebenen Eintrag `BgldAus` — ist ebenfalls toter Code ohne Aufrufer.
`BgldAus` liest zwar eine bleibende Datei (`WK_Eignungszonen.zip`, dieselbe
wie die Positivzone `Bgld`, per Attributfilter getrennt), aber niemand ruft
die Funktion. Das gehört in W1.5 mit entfernt, nicht in dieses Paket — es
fällt nicht unter Entscheidung (a).

### W1.1 — Adress-Cache-Weiche entfernen · fertig

Commit `d29c801`, Zweig `w1.1`. Geschätzt 20 min, gebraucht 8.

Die Weiche war heimtückischer als aus dem Plan ersichtlich: Fand der Code
die Cache-Datei direkt in `data_dir`, überschrieb er den aus `cache_dir`
berechneten Pfad. Nach dem ersten produktiven Lauf existierte diese Datei
immer — der Parameter `cache_dir` war also nicht gelegentlich, sondern ab
dann grundsätzlich wirkungslos. Beide Funktionen (`load_address_points`,
`load_building_points`) lesen jetzt `cache_dir or contract.PREP["adressen"]`.

**Der Nachweis ist stärker als verlangt.** Statt eines Codetests hat der
Agent beide Funktionen gegen leeren Cache wirklich laufen lassen: 2.516.345
Adress- und 2.524.624 Gebäudepunkte, Cache entstand unter
`build/prep/adressen/`, und `data/adressen/*.parquet` blieb nach md5 und
Zeitstempel unangetastet. Damit ist in einem Schritt belegt, dass der
Vertragspfad greift **und** dass nicht mehr nach `data/` geschrieben wird.
Kosten: rund sechs Sekunden.

### W1.5 — Tote Skripte löschen · fertig

Commit `9c64a85`, Zweig `w1.5`. Geschätzt 15 min, gebraucht 14.

Drei Skripte gelöscht, jede Begründung vorher einzeln nachgeprüft und
bestätigt: `scripts/webmap/build_layer_viewer.py` benutzt zwei Namen, die
im ganzen Repo nirgends definiert werden (sicherer `NameError`);
`scripts/analysis/build_v2_dashboard_data.py` nennt acht Bandnamen, die im
kanonischen 38-Band-Schema fehlen; `scripts/noe/derive_pdf_hig_sources.py`
ruft nur eine Funktion auf, die `extract_noe_vector_layers.py:286` bereits
selbst aufruft.

Dazu der Nachtrag aus W1.7: `load_wind_exclusion_zones()`,
`WIND_EXCLUSION_ZONE_SOURCES` mit dem letzten Eintrag `BgldAus` und die
verwaiste Konstante `REGIME_FORBIDDEN` sind weg. Die Datei
`WK_Eignungszonen.zip` und die Positivzone `Bgld`, die dieselbe Datei per
Attributfilter liest, bleiben unberührt.

Fünf mitgezogene Verweise wurden **korrigiert statt gelöscht** — darunter
eine `FileNotFoundError`-Meldung, die auf ein nun fehlendes Skript zeigte.
Eine Fehlermeldung, die auf nichts verweist, ist schlimmer als keine.

**Abnahme: bitgleich, 130 Tests grün** — mit einer Einschränkung, die der
Agent selbst benannt hat: keiner der drei gelöschten Skriptpfade und keine
der Wind-Zonen-Änderungen liegt in der Bandkette. Die Bitgleichheit war
also zu erwarten und beweist hier wenig. Was wirklich trägt, ist die
Einzelprüfung der drei Löschbegründungen davor.

### W1.8 — Paketmetadaten bereinigen · fertig

Commit `63e7b8b`, Zweig `w1.8`. Geschätzt 15 min, gebraucht 8.

Drei vorbestehende Fehler, keiner davon durch diesen Umbau verursacht:

- `[project.scripts] windkraft = "windkraft.__main__:main"` verwies auf eine
  Datei, die es nicht gibt. Es war der einzige Einstiegspunkt.
- Es gab **gar keine** `[build-system]`-Sektion. Das Paket war nie
  installierbar; `uv sync` sagte das in einer Warnung, die niemand las.
  Jetzt hatchling, mit `windkraft` und `pipeline` im Wheel.
- PyMuPDF stand als optionales Extra, obwohl drei Dateien `fitz` hart
  importieren. Jetzt reguläre Abhängigkeit, das leere Extra entfällt.

In `uv.lock` wechselt die Wurzel dadurch von `virtual` auf `editable`; die
36 Auflösungen der Fremdpakete bleiben unverändert.

**Abnahme: bitgleich, 130 Tests grün.**

### W1.9 — Doku-Widersprüche korrigieren · fertig

Commit `89fad40`, Zweig `w1.9`. Geschätzt 15 min, gebraucht 13. Berührt nur
`README.md`.

Sieben falsche Aussagen, jede mit `datei:zeile` belegt. Die drei
folgenreichsten:

- Das README behauptete, die Kette sei „in diesem Repo noch kein einziges
  Mal end-to-end ausgeführt" worden — im Präsens, obwohl der Lauf vom
  06.09.2026 in `docs/RUN1_VERGLEICH.md` dokumentiert ist.
- Fehlendes `osmium-tool` falle „still auf leere Masken zurück". In diesem
  Repo bricht es mit `FileNotFoundError` ab; der stille Rückfall lebte nur
  im Vorgängerprojekt. Eine Aussage, die aus dem Alt-Repo mitgewandert ist,
  ohne dass jemand sie nachprüfte.
- Speicherbedarf mit 18 GB angegeben, gemessen sind 24.

Dazu ein toter Vorwärtsverweis („siehe Hinweis unten"), der auf keinen
Abschnitt zeigt, und die fehlende Erwähnung der W0.3-Make-Ziele.

**Kein Nachweislauf nötig, kein Code berührt. 130 Tests unverändert grün.**

### Zusammenführung der vier Zweige · fertig

Merge-Commits `cf09615` (w1.1), `3679935` (w1.8), `7bbdd1a` (w1.5),
`fa481ae` (w1.9), alle mit `--no-ff`. Nachkorrektur `c007fe4`,
Werkzeugreparatur `81849de`. Kopf: `81849de`.

**Der Merge war nicht trivial, und das war vorhersehbar.** `w1.5` hat drei
Skripte gelöscht, über die `w1.9` im README Aussagen korrigiert hatte. Git
hat beide Änderungen klaglos zusammengeführt — **ohne einen einzigen
Konfliktmarker** — und dabei drei Aussagen erzeugt, die einzeln aus
korrekten Änderungen stammen und gemeinsam falsch sind:

1. `w1.9` hatte den Satz „insbesondere keine Dashboards" als falsch
   markiert, weil `build_v2_dashboard_data.py` existierte. `w1.5` hat es
   gelöscht. Der ursprüngliche Satz ist damit wieder wahr, die Korrektur
   ihrerseits falsch. Neu formuliert, nicht der Alttext zurückgeholt.
2. Der Struktur-Abschnitt nannte `analysis/` und `webmap/` als aktive
   Werkzeuge. Beide Verzeichnisse sind jetzt leer bzw. weg.
3. Der Status-Abschnitt führte die veraltete `EXCLUSION_LAYERS`-Liste als
   offenen Punkt — das ganze Skript ist weg, der Punkt gegenstandslos.

**Die Lehre gilt über dieses Paket hinaus:** Ein sauberer Merge ist kein
Beweis für ein richtiges Ergebnis. Wo zwei parallele Pakete dieselbe Datei
aus verschiedenen Richtungen ändern, muss die zusammengeführte Fassung
danach **inhaltlich** gegen den Code geprüft werden. Für Prosa leistet das
kein Werkzeug. Ich schreibe diese Nachprüfung ab jetzt in jeden
Merge-Auftrag, bei dem sich Dateimengen überschneiden.

**Nebenbefund zur Werkzeugreparatur:** `git update-index --skip-worktree
data/README.md` allein reichte **nicht**. Es blendet nur den Indexeintrag
aus; der Symlink `data` war nie getrackt und blieb als `??` stehen. Erst der
zusätzliche Eintrag `/data` in `.git/info/exclude` (idempotent gesetzt)
macht ein frisches Worktree wirklich sauber. Am Wegwerf-Worktree
`repair-check` verifiziert.

Beim Abbau ließ sich keines der vier Worktrees mit `git worktree remove`
entfernen — dieselbe Symlink-Nebenwirkung. Der Agent hat **nicht** mit
`--force` gearbeitet, sondern in jedem Worktree den Symlink entfernt und
`data/README.md` wiederhergestellt; danach ging alles regulär. Vier Branches
mit `git branch -d`, keiner mit `-D`.

**Abnahme: bitgleich, 130 Tests grün, Arbeitsbaum sauber.**

### W1.6 — NÖ-PDF-HiG-Sackgasse entfernen · fertig

Commit `e3d3655`, Zweig `w1.6`. Geschätzt 25 min, gebraucht 14.

Der Checkpoint `noe_pdf_hig_source` (rekonstruierte SekROP-Quellobjekte,
Erosion 750 − 50 m) wurde erzeugt und von niemandem gelesen. Belegt auf drei
unabhängigen Wegen: repoweite Suche findet ihn nur noch in Doku, die
Layerlisten von Stufe 3 und 4 verwenden ausschließlich `noe_pdf_750m_zones`,
und der Datenflussgraph aus einer früheren Sitzung führt ihn bereits als
`verified_dead`. `LAYER_NAMES` schrumpft von 34 auf 33.

Mitentfernt: `noe_pdf_source_mask()` und `NOE_PDF_SOURCE_LAYER_NAMES` in
`hig_source_masks.py`, deren einziger Aufrufer die gestrichene Zeile war,
samt der harten `FileNotFoundError`-Vorbedingung.

**Was der Agent bewusst *nicht* gelöscht hat**, ist die wertvollere Hälfte
des Ergebnisses: `noe_pdf_750m_zones` und `noe_pdf_mask()` sehen genauso
nach Sackgasse aus, haben aber einen echten Abnehmer — Band
`haeuser_im_gruenen_noe_pdf` speist `haeuser_im_gruenen`. Wer die Namen nur
überflogen hätte, hätte hier ein Band zerstört.

**Zur Abnahme sagt der Agent selbst das Richtige:** Bitgleichheit war
garantiert, weil der entfernte Pfad nie in der Bandkette lag. Sie zeigt
nur, dass nichts *anderes* kaputtging. Der eigentliche Beweis ist die
Aufrufer-Analyse.

**Drei Befunde über das Paket hinaus** — behandelt in `PLAN.md` §13:
Register-Besitz (§13.1), Schreibzugriff auf den geteilten
Checkpoint-Ordner (§13.2), und eine Sackgasse eine Ebene höher
(`pdf_hig_sources.py` erzeugt jetzt GeoJSON, die niemand liest → Punkt 12).

### W1.2 — Tote Daten löschen, Provenienz retten · fertig

Commit `6f815d2`. Geschätzt 20 min, gebraucht 22 — das erste Paket, bei dem
ich nicht zu hoch lag. Das erste Datenfenster, ohne Worktree (§10 des
Plans), im Hauptrepo.

Gelöscht: `osm_power_lines.gpkg` (13,5 MB), `WINDKRAFT_AUSSCHLUSSZONE.zip`
(4,6 MB), `windkraftzonen_shapefile_2024.json` (0,6 MB), zwei `.DS_Store`
und ein leeres Werkzeugverzeichnis `adressen/.claude/`. Alle bis auf eine
mit Linkanzahl ≥ 2, also **umkehrbar** — der Inode überlebt im
Vorgängerprojekt. Die einzige mit Linkanzahl 1 war ein `.DS_Store`.

Der Fall `osm_power_lines.gpkg` ist der lehrreichste: Er **hat** einen
Codeleser, in `abschichtung_common.py:966`. Aber der Zweig greift nur, wenn
das OSM-PBF fehlt — bei gepflegtem PBF wird er nie erreicht, und das daraus
gebaute Band `power_380_400kv` steht im 38-Band-Schema ohnehin nicht. Ein
Leser, der nie liest.

**Der eigentliche Fund ist eine Falle, die ich übersehen hatte.**
`windkraft/config.py:42` griff **unbedingt** auf
`contract.LEGACY_ENTFAELLT["powerlines_gpkg"]` zu — bei jedem
`load_config()`. Das bloße Austragen des Registereintrags, genau das, was
§13.1 dem Paket erlaubt, hätte einen `KeyError` bei **jedem Pipelinelauf**
ausgelöst. Der Agent hat es vor dem Austragen bemerkt und `config.py`
mitgezogen. Ohne diesen Blick wäre die Kette beim nächsten Lauf gestorben,
und die Ursache hätte in einer Zeile gelegen, die aussieht wie
Buchhaltung.

**Das `worktree`-Ziel brach wie vorhergesagt — und schlimmer.** Ich hatte
mit einer wirkungslosen `skip-worktree`-Zeile gerechnet. Tatsächlich legt
`git worktree add` das Verzeichnis `data/` gar nicht mehr an, sobald keine
versionierte Datei mehr darin liegt; der alte Code lief damit in den Zweig
„weder Verzeichnis noch Symlink" und brach ab. Behoben durch einen dritten
Zweig, an einem Wegwerf-Worktree zweimal verifiziert (Erst- und Zweitlauf,
also auch die Idempotenz). Nebenbei hat der Agent einen eigenen Tippfehler
gefunden: ein `;` in einem mehrzeiligen Shell-Kommentar führte das Wort
`direkt` als Kommando aus.

`docs/rohdaten.md` (aus `data/README.md`) an sieben Stellen nachgezogen.

**Abnahme: bitgleich, 50 von 50 Inodes unverändert, 129 Tests grün plus 1
übersprungen.** Die Einschätzung des Agenten zur Beweiskraft ist richtig:
Der Lauf liest die Checkpoints, nicht `data/`. Er beweist, dass die
Vertrags- und Konfigänderung die Kette nicht zerstört hat — nicht, dass die
gelöschten Rohdateien wirkungslos waren. Das leistet die statische Suche.

### W1.3 — Hardlinks auflösen · fertig

Commit `1aaa1a3`. Geschätzt 20 min, gebraucht 14. Zweites Datenfenster, im
Hauptrepo.

Die einzige unumkehrbare Handlung des Projekts, und sie ist sauber
verlaufen. 48 von 50 Dateien hatten Linkanzahl ≥ 2; die zwei übrigen waren
die per `to_parquet()` erzeugten Adress-Caches und damit schon echte
Kopien.

**Drei Prüfungen, alle bestanden:**

| Prüfung | Ergebnis |
|---|---|
| Bei uns: Linkanzahl 1, neuer Inode, gleiche Größe, gleiche sha256 | 48/48 |
| **Beim Vorgängerprojekt: gleiche sha256 wie vorher** | **48/48** |
| Keine `.tmp`-Reste | keine |

Die mittlere Zeile ist der eigentliche Beweis. Sie zeigt, dass das
Verfahren — Kopie daneben, Prüfsumme *vor* dem Ersetzen, dann `mv` — den
alten Inode wirklich unangetastet gelassen hat. Kein einziger
Prüfsummenvergleich schlug fehl.

Der Platzbedarf war unkritischer als befürchtet: Datei für Datei
aufgelöst, der Spitzenbedarf lag bei der größten Einzeldatei (~2 GB), nicht
bei 13 GB. 55 GiB waren frei.

**Nebenbefund:** Das Vorgängerprojekt liegt unter
`/Users/jhurt/Documents/windkraft_ö_karten` — eine Ebene höher als in
meinem Auftrag geraten. Der Agent hat es über den Inode gefunden, statt sich
auf meinen Pfad zu verlassen. Genau richtig.

**Aus der Warnung wurde eine Invariante.** `tools/check_hardlink_safety.py`
prüfte Regel B bisher nur gegen eine fest deklarierte Liste bekannter
Schreibziele, mit der Begründung, `data/` sei überwiegend hardlink-basiert.
Das stimmt seit heute nicht mehr: Es gibt dort **keine Hardlinks mehr**.
Der Wächter prüft jetzt jede Datei unter `data/` — wie Regel A das für
`output/` längst tat. Live grün gegen 129 Dateien. Das war formal W1.4s
Gebiet, gehört aber hierher, weil W1.3 die Grundannahme geändert hat.

**Zur Ehrlichkeit des Berichts:** Der Agent hat von sich aus offengelegt,
dass er die Test-Ausgangszahl nicht unmittelbar vor dem Eingriff gemessen,
sondern aus W1.2 übernommen hat — mit der Begründung, kein Test lese
Dateiinhalte unter `data/`, was er per Suche belegt hat. Die Begründung
trägt, die Lücke bleibt eine Lücke. Dass er sie nennt, statt sie zu
glätten, ist mehr wert als die Lücke kostet.

**Abnahme: bitgleich, 129 Tests grün plus 1 übersprungen.**

### W1.4 — Wächter für Rohdaten · fertig

Commit `b26ce83`. Geschätzt 25 min, gebraucht 13. **Damit ist der
Aufräum- und Absicherungsteil der Welle 1 abgeschlossen.**

`tools/check_raw_only.py` ist ein AST-Wächter, kein Textsucher — und das
ist der Punkt. Er verfolgt das Pfadargument bekannter Schreibaufrufe
rückwärts durch Zuweisungen und erkennt dabei genau die drei Fallen, die
dieses Projekt schon gestellt hat: zusammengesetzte Pfade
(`ROOT / "data" / "x"`, ohne Teilstring `data/`), Vertragspfade
(`contract.RAW[...]`, wo im Code nirgends „data" steht) und
Parameter-Vorgabewerte, die erst greifen, wenn ein Argument fehlt — die
W1.1-Falle.

**Wichtiger als was er findet, ist was er zugibt nicht zu finden.** Der
Docstring nennt sechs Lücken, darunter die entscheidende: keine
funktionsübergreifende Verfolgung. Ein `data/`-Pfad, der als Parameter
hereingereicht wird und dessen Herkunft erst beim Aufrufer sichtbar ist,
entgeht ihm. Der Agent hat prompt ein Beispiel dafür gefunden
(`widmung_sources.py::_ensure_ktn_gpkg`) und es von Hand geprüft — der
Default beim einzigen Aufrufer ist unkritisch. Ein Wächter mit
dokumentierten Grenzen ist brauchbar; einer, der Vollständigkeit
vortäuscht, ist gefährlich.

Verdrahtet als `make check-raw-only`, zusammen mit dem Hardlink-Wächter
unter `make check-guards`. Beide grün gegen das echte Repo: 129 Dateien
hardlinkgeprüft, 31 Python-Dateien schreibgeprüft, kein Fund.

**Zusatzauftrag A, gut entschieden:** Der leere `LEGACY_ENTFAELLT`-Test
bleibt als Vorbereitung stehen, bekommt aber einen aktiven Partner, der
gegen die Leerheit prüft — statt dass ein „1 übersprungen" beiläufig
durchrutscht. Er schlägt fehl, sobald jemand einen Eintrag hinzufügt, ohne
die Zeile mitzuziehen.

**Abnahme: bitgleich, Tests von 129 auf 136 gestiegen** (Ausgangszahl per
`git stash -u` unmittelbar vor der Änderung selbst gemessen — die Lücke aus
W1.3 ist geschlossen).

### W1.P0 — Vorfeld der Prep-Welle · fertig

Commit `6a9e8a2`. Geschätzt 20 min, gebraucht 13. Tests von 136 auf 147.

Die beiden vorhergesehenen Konflikte sind entschärft: `PREP` deckt jetzt
alle neun Domänen ab (12 Blattpfade), und das `Makefile` liest Prep-Ziele
über `-include make/prep/*.mk` ein. Der Mechanismus wurde nicht behauptet,
sondern **belegt** — zwei echte `.mk`-Dateien angelegt, `make prep` rief
beide auf, danach entfernt und der No-op-Zustand erneut geprüft. `make -n`
für das Standardziel ist vor und nach der Änderung byte-identisch.

**Der Ertrag liegt aber in den zwei Dateien, die ich nicht auf der Liste
hatte:**

`pipeline/prep/__init__.py` — sobald das erste der neun Pakete eine Datei
unter `pipeline/prep/` anlegt, müsste es die Paketmarkierung mit anlegen.
Bei neun Paralleln ist das ein „wer war zuerst da"-Konflikt. Jetzt liegt sie
da.

`pipeline/fingerprint.py` — das ist der wertvollere Fund. Entscheidung (c)
des Plans verlangt von **jeder** Prep-Stufe einen Fingerabdruck ihrer
Eingaben. Ohne Vorbereitung hätte jedes der neun Pakete seine eigene,
leicht andere Logik erfunden. Das hätte **keine** Merge-Konflikte erzeugt —
jedes in seiner eigenen Datei — und wäre genau deshalb erst viel später
aufgefallen. Der Agent hat eine minimale gemeinsame Implementierung
geschrieben (Größe und mtime, kein teurer Inhalts-Hash), mit sieben Tests.

Das ist die Sorte Überschneidung, die meine Konfliktregel aus §13.4 **nicht**
findet: Sie sucht nach gemeinsamen Dateien, nicht nach gemeinsamen
Entscheidungen. Neun Pakete, die dieselbe Frage unabhängig beantworten,
kollidieren nie und driften trotzdem auseinander.

### W1.P0 — ursprüngliche Begründung

Kein Paket aus dem ursprünglichen Plan, sondern eine Reaktion auf die
gemessene Zusammenführungskosten-Regel (§13.3 des Plans).

**Das Problem:** Die neun Prep-Pakete laufen parallel. Jedes von ihnen
würde einen Eintrag in `pipeline/contract.py:PREP` und ein Ziel im
`Makefile` hinzufügen. Das sind **zwei garantierte neunfache Konflikte** an
derselben Stelle — genau die Sorte, die beim letzten Batch drei falsche
README-Aussagen erzeugt hat, nur schlimmer, weil `Makefile` und Vertrag
funktional sind und nicht nur Prosa.

**Die Lösung, vor dem Batch statt danach:** Ein kleines Vorpaket erklärt
alle neun Prep-Pfade im Vertrag und ersetzt die neun Makefile-Ziele durch
`-include make/prep/*.mk`. Danach schreibt jedes Prep-Paket sein Ziel in
**seine eigene Datei** `make/prep/<domäne>.mk` — neun verschiedene Dateien
statt neun Änderungen an einer. Der Konflikt entsteht gar nicht erst.

### W1.P1 — Prep: Verwaltungsgrenzen · fertig

Commit `b75f6c8`, Zweig `w1.p1`. Geschätzt 25 min, gebraucht 12. Erstes
Prep-Paket überhaupt.

`pipeline/prep/admin.py` liest die VGD-Rohquelle **einmal** und schreibt
zwei Ableitungen: `gemeinden.gpkg` (2093 politische Gemeinden) und
`bundesland_masken.gpkg` (9 Bundesländer). Letzteres ist genau die
Operation, die `abschichtung_common.py` heute bei **jedem** Aufruf von
`official_wind_zoning_mask` erneut rechnet — der erste sichtbare Beleg
dafür, wozu die Prep-Welle gut ist.

**Der Gleichheitsnachweis ist der beste bisher.** Nicht gegen eine
nachgebaute Formel verglichen, sondern gegen die **tatsächlich laufende
Funktion** `admin_boundaries()` plus dieselbe Dissolve-Zeile, die die Kette
heute ausführt. Ergebnis: maximale symmetrische Differenzfläche **0,0 m²**
über alle neun Länder.

Für die Gemeinden gibt es heute keinen Konsumenten — das Produkt entsteht
für W4.2. Statt Laufzeit-Äquivalenz hat der Agent deshalb **Verlustfreiheit**
belegt: Flächensumme vor und nach dem Dissolve identisch, GKZ-Menge
identisch, alle Attribute je GKZ konstant. Eine andere Frage, sauber als
solche benannt und passend beantwortet.

Drei Dinge deckt der Vergleich **nicht** ab, und der Agent sagt es selbst:
kein bounds-gefilterter Lauf, keine Prüfung auf Fließkommarauschen beim
GPKG-Rundtrip, keine Prüfung von Attributreihenfolge und -typen für die
Konsumenten der Welle 2.

**Abnahme: bitgleich, 147 Tests unverändert, Wächter grün.**

### W1.P6 — Prep: Gelände und Wind · fertig

Commit `eee51d4`, Zweig `w1.p6`. Geschätzt 20 min, gebraucht 19 — davon
rund sieben Minuten Schlaf auf dem eigenen Hintergrundlauf, die Regel §13.7
des Plans künftig einspart.

**Das Windraster weicht in allen vier geprüften Merkmalen ab:**

| | DGM_R25.tif | AUT_power-density_150m.tif | Ziel |
|---|---|---|---|
| CRS | EPSG:31287 ✓ | **EPSG:4326** | EPSG:31287 |
| Auflösung | 25 m ✓ | **0,0025°** — Grad, nicht Meter | 25 m |
| Größe | 24001 × 14001 ✓ | **3069 × 1076** | 24001 × 14001 |

Das Gelände passt exakt, das Windraster überhaupt nicht — und zwar nicht
knapp, sondern in einem anderen Koordinatensystem mit einer
Winkeleinheit statt einer Längeneinheit.

**Der Befund ist trotzdem harmlos, und das ist die eigentliche Aussage.**
`abschichtung_common.py` liest heute schon **beide** Raster per
`reproject()` bilinear auf das DGM-Gitter; der Windrohwert wird nirgends
übernommen. Die stillschweigende Annahme, vor der §13.5 warnt, existiert im
heutigen Produktivcode also **nicht**. Sie entstünde erst, wenn die neue
Layer-Stufe der Welle 2 diesen Reprojektionsschritt fallen ließe — und
genau davor schützt jetzt ein Prüfbericht, der die Abweichung in Zahlen
festhält, statt sie erst beim ersten falschen Ergebnis auffallen zu lassen.

`build/prep/gelaende/pruefbericht.md`, menschenlesbar, gemessen gegen Soll.
Kein Abbruch, keine Umformung, keine Datenänderung.

**Abnahme: bitgleich, 147 Tests unverändert, Wächter grün.**

### W1.P3 — Prep: Adressregister · fertig

Commit `61346b3`, Zweig `w1.p3`. Geschätzt 40 min, gebraucht **6** — die
größte Fehleinschätzung nach unten bisher. Grund: W1.1 hatte die Weiche
bereits beseitigt, das Paket musste den Schritt nur noch explizit machen,
statt ihn beiläufig beim ersten Kettenlauf entstehen zu lassen.

Der Gleichheitsnachweis ist vorbildlich geführt: Ausgabe umbenannt, dann
`load_address_points()` und `load_building_points()` **direkt** aufgerufen —
mit demselben `cache_dir`, den der echte Konsument per Vorgabewert benutzt
— und beide Parquet-Dateien per sha256 verglichen. **Bitgleich.**
2.516.345 und 2.524.624 Punkte, exakt die W1.1-Zahlen.

Die Handprüfung auf Schreibzugriffe nach `data/` lief über eine
Markierungsdatei und `find data -newer` — vor und nach dem Lauf, im
Worktree **und** über den Symlink im Hauptrepo. Bei genau dieser Domäne war
der historische Fehler; die Sorgfalt ist angemessen.

**Der Fund ist eine stille Falle im Rohdatenbaum.** In `data/adressen/`
liegen noch zwei Parquet-Dateien vom 23./24. Juli — die Artefakte genau
jenes Cache-Weichen-Fehlers, den W1.1 im Code behoben hat, ohne die bereits
entstandenen Dateien zu entfernen. Sie werden von niemandem mehr gelesen.
Aber die Rohquelle daneben hat Stichtag **1. Oktober 2025**: Wer je
versehentlich wieder von ihnen läse, bekäme **stillschweigend veraltete
Daten**, ohne Fehlermeldung. Der Wächter verhindert neue Schreibzugriffe,
nicht alte Überbleibsel. Punkt 19.

**Abnahme: 147 Tests unverändert, Wächter grün.** Erstes Paket ohne eigenen
Nachweislauf nach §13.7.

### W1.P7 — Prep: Naturschutz · fertig

Commit `7d81827`, Zweig `w1.p7`. Geschätzt 25 min, gebraucht 8.

Die Kette entpackt heute **bei jedem Lauf** das GeoPackage aus dem
ZIP-Archiv in ein Temp-Verzeichnis und liest daraus vier von zwanzig
Layern: Nationalparke (29), Naturschutzgebiete (499), Europaschutzgebiete
(368), Ramsar (24) — zusammen 920 Geometrien. Sämtliche Sachattribute
werden sofort verworfen, dann von EPSG:3035 nach 31287 reprojiziert.

**Der Gleichheitsnachweis geht bis auf die einzelne Geometrie:** Fläche
bit-für-bit identisch (22 928 877 990,127 45 m²), und alle 920 Geometrien
WKB-bytegleich. Die dafür nötige Normalisierung Polygon → MultiPolygon ist
ein reines Speicherformat-Artefakt — GeoPackage erlaubt je Layer nur einen
Geometrietyp und promoviert beim Schreiben 383 Polygone. Für den einzigen
Konsumenten, `rasterize`, nachweislich ohne Bedeutung. **Für Welle 2 aber
nicht unbedingt**, falls dort je geometrietyp-sensitiv gearbeitet wird —
Punkt 20.

Dass die Rohquelle Schutzkategorien, Gesetzesjahr und Flächenangaben
enthält, die vollständig verworfen werden, bevor sie je ein Band erreichen,
hat der Agent notiert und nach Regel 4 nicht angefasst. Richtig so — das
ist eine fachliche Entscheidung, keine Umbaufrage.

**Ein Unterschied zu W1.P1, der Erwähnung verdient:** Hier wurde gegen
einen **Nachbau derselben Schritte im selben Lauf** verglichen, nicht gegen
die laufende Funktion selbst — die ist privat und rasterisiert zugleich.
Das ist schwächer als W1.P1s Vergleich gegen `admin_boundaries()`, und der
Agent sagt es selbst. Tragfähig, weil Fläche und WKB übereinstimmen, aber
kein gleichwertiger Beleg.

**Abnahme: 147 Tests unverändert, Wächter grün.**

### W1.P8 — Prep: Windzonen · fertig

Commit `e967f48`, Zweig `w1.p8`. Geschätzt 30 min, gebraucht 7.

Vier Quellen, jede **einzeln** gegen die tatsächlich laufende Funktion
`load_zones()` geprüft — nicht als Summe:

| Quelle | Anzahl | Fläche | sym. Differenz |
|---|---:|---:|---:|
| Stmk | 18 | 46,426 km² | **0,0 m²** |
| Sbg | 13 | 17,238 km² | **0,0 m²** |
| Bgld | 40 | 24,685 km² | **0,0 m²** |
| RED3 | 4 | 7,400 km² | **0,0 m²** |

Verglichen wurde nicht nur Fläche und Anzahl, sondern die symmetrische
Differenz der Vereinigungsgeometrie — ordnungsunabhängig, und sie fängt
auch Verschiebungen, die eine Flächensumme unverändert ließe.

**Die Trennprüfung, die ich ausdrücklich verlangt hatte, ist sauber:** Das
Burgenland-Archiv enthält 71 Objekte in **einem** Layer — 40 Eignungszonen
und 31 Ausschlusszonen, getrennt allein durch einen String-Präfix auf dem
Attribut `Status`. Das Prep-Ergebnis enthält genau 40. Keine Ausschlusszone
rutscht durch. Der Agent nennt die Konstruktion selbst fragil und hat sie
nach Regel 4 unverändert übernommen — richtig.

**Der wichtigste Fund liegt außerhalb des Auftrags: eine fünfte Quelle.**
`data/zonen/zonierung_noe.json` mit 71 niederösterreichischen Zonen wird
**nicht** über `WIND_ZONE_SOURCES` gelesen, sondern über einen eigenen
Codepfad direkt in `abschichtung_common.py` (`--official-zoning-geojson`).
Weder meine Domänentabelle noch der Zuschnitt von W1.P8 erfasst sie. Soll
Band 37 in Welle 2 vollständig aus `build/prep/` gespeist werden, fehlt
dafür eine Stufe. Punkt 22 — und ein Zuschnittfehler von mir, kein
Agentenfehler.

**Abnahme: 147 Tests unverändert, Wächter grün.**

### W1.P2 — Prep: Kataster · fertig

Commit `e9f8fe9`, Zweig `w1.p2`. Geschätzt 60 min, gebraucht 27.

**Das wichtigste Ergebnis der ganzen Sitzung: die letzte Unbekannte ist
vermessen.** Der vollständige Kataster-Vorverarbeitungslauf dauert nach
Messung **45 bis 70 Minuten**, nicht die fünf Stunden aus dem Zielbild.

Und zwar nicht geschätzt, sondern hochgerechnet aus echten Läufen:

| Stufe | Messung | Hochrechnung |
|---|---|---|
| b — SHP-Export, 8 Länder | Vorarlberg **vollständig**: 50,5 s für 1 118 888 Zeilen | 15–16 min für 20 623 871 Zeilen |
| a — NÖ-Rekonstruktion aus DXF | 20 Dateien: 29,4 s · 300 Dateien: 272,1 s | 30–50 min für 3040 Dateien |

Stufe b ist belastbar — ein ganzes Bundesland gemessen, hochgerechnet über
die **exakt ausgezählten** Zeilenzahlen der übrigen sieben. Stufe a ist
unsicherer: Die Stichprobe ist alphabetisch, nicht räumlich repräsentativ,
und das Verhalten ist deutlich sublinear (15-fache Dateizahl, nur
9,3-fache Zeit). Zwei unabhängige Hochrechnungen konvergieren trotzdem.

**Der Vertragszuschnitt war falsch, und der Agent hat ihn nicht
schöngeredet.** `PREP["kataster"]` deklarierte zwei Stufen `a_`/`b_` — der
vorgefundene Code war **ein** Skript, das beides sequenziell in denselben
Writer schrieb, ohne Zwischenablage. Statt die Trennung zu behaupten, hat
er sie tatsächlich eingeführt: `a_noe_polygonize` schreibt ein eigenes
GeoParquet, `b_export_parquet` übernimmt es per Batch-Durchschreiben ohne
erneutes Geometrie-Parsen und bricht ab, wenn a noch nicht lief. Die
Übernahme ist als **bytegleich** verifiziert.

**Das vorhandene Produktions-GeoParquet ist nachweislich unangetastet** —
Größe, mtime und sha256 vor und nach dem Paket identisch. Das war die
strengste Auflage des Auftrags, weil es keine zweite Quelle dafür gibt.

Kein Volllauf, nur Teilläufe: `--noe-limit-files 20/300`,
`--only-bundesland Vorarlberg`, `--skip-shp`. Genau so beauftragt.

Zwei Doku-Fehler nebenbei: Plan §4 nennt 7,8 GB, gemessen sind **9,1 GB**.
Und `docs/rohdaten.md` beschreibt 338 674 verworfene Polygone bei
3 491 407 erzeugten — die Produktionsdatei enthält aber exakt 3 491 407
NÖ-Zeilen, nicht die Differenz. Vermutlich stammt sie aus einer älteren
Codefassung ohne diesen Filter. Punkt 23.

### W1.P4 — Prep: Flächenwidmung · fertig

Commit `e7ef6bd`, Zweig `w1.p4`. Geschätzt 45 min, gebraucht 8.

Neun Bundesländer, neun Formate, **jedes einzeln geprüft** — Differenz
exakt 0 bei allen neun. Zusammen 466 200 Flächen und
3 087 053 470,76 m². Die Einzelprüfung war der Punkt: Eine Gesamtsumme
hätte verborgen, wenn zwei Länder sich gegenläufig verschieben.

Nicht abgedeckt, und der Agent sagt es: Anzahl und Fläche je Land,
aggregiert über alle Buckets — **nicht** Geometrie für Geometrie und nicht
Attribut für Attribut.

**Die Liste der fachlichen Inkonsistenzen ist der eigentliche Ertrag** —
alle nach Regel 4 unangetastet:

- **Wien liefert seit 29.07.2026 nur noch die generalisierte statt der
  parzellenscharfen Widmung.** Eine strukturell andere Datenqualität als in
  den anderen acht Ländern, im Code als für ein 25-m-Raster unerheblich
  bewertet. Das ist eine Bewertung, keine Messung.
- Kärntens Kurgebiet bleibt im vollen Siedlungsabstand, während
  vergleichbare Kategorien anderswo in den 750-m-Bucket wandern — im Code
  ausdrücklich als offene Entscheidung vermerkt.
- Sehr ungleiche Kategorienabdeckung: Golf, Camping und Hofstelle gibt es
  in Tirol und Oberösterreich als eigene Kategorien, in Wien keine davon.
- Drei verschiedene Matching-Strategien je nach Feldqualität. Vorarlbergs
  Freitextfeld hat 1424 Suffix-Varianten; ein früherer `startswith`-Versuch
  traf dort wegen inkonsistenter Leerzeichen **null** Features — 3,4 km²
  stille Lücke, inzwischen im Code behoben.

**Und ein Cache-Muster, das ich schon kenne:** `_ensure_ktn_gpkg()` prüft
beim Wiederverwenden nur, **ob** die extrahierte Datei existiert — nicht,
ob das Quell-ZIP sich geändert hat. Dieselbe Bauart wie `layer_done()` und
wie die Weiche aus W1.1. Der Fingerabdruck der Prep-Stufe erfasst korrekt
das ZIP und würde eine Änderung erkennen; der Extraktions-Cache daneben
nicht. Punkt 24.

**Abnahme beider: 147 Tests unverändert, Wächter grün.**

### W1.P9 — Prep: NÖ-SekROP-PDF · fertig

Commit `70de2df`, Zweig `w1.p9`. Geschätzt 45 min, gebraucht 20.

**Der schärfste Gleichheitsnachweis der Prep-Welle:** Die alten Skripte
frisch laufen lassen, dann `cmp` gegen den neuen Prep-Lauf — **alle zwölf
GeoJSON-Dateien bytegleich**, sechs Layer je nativ und in WGS84.
Nebenbei halbiert sich die Laufzeit von 2:06 auf **1:04**, weil das
PDF-Rendering entfällt und `get_drawings()` nur noch einmal läuft.

Die Sackgasse aus W1.6 ist bestätigt, nicht geglaubt: repoweite Suche plus
Prüfung am Diff von `e3d3655`, der den letzten Leser entfernt hat.
`windkraft/noe/pdf_hig_sources.py` ist als ganzes Modul weg.

Und `noe_pdf_750m_zones` ist unangetastet — der Agent hat die
Konsumentendateien nicht einmal zum Schreiben geöffnet. Genau die
Zurückhaltung, um die ich gebeten hatte, denn daran hängt ein echtes Band.

Die Zahlen des PDF-Pfads, alle unverändert übernommen: Farbtoleranz 0,02,
acht Bézier-Schritte, 8 m Vereinfachung, sechs exakte RGB-Füllfarben,
Robust-Union mit Gitter 0,05.

**Der Herkunftsverdacht ist widerlegt.** Der Agent hatte berichtet, sein
Worktree sei von einem Stand vor der Welle-1-Zusammenführung abgezweigt.
Eine getrennte Prüfung aller neun Zweige zeigt: Jede Merge-Basis liegt
**auf** der Historie von `docs/audit-und-plan`, keine auf `main`, keine vor
der Zusammenführung. Die Herkunftsangabe des Agenten war falsch, seine
Testzahl richtig. `make worktree` verzweigt von `HEAD`, wie vorgesehen.

Die Prüfung war trotzdem richtig. Ein Zweig auf veralteter Basis hätte
fremde Arbeit **lautlos** zurückgedreht — ohne Konflikt, ohne Warnung, weil
Git das als legitime Änderung behandelt. Bei acht Zweigen hintereinander
wäre es erst viel später aufgefallen. Ein Bericht, dem man nicht glaubt,
kostet zwei Minuten Prüfung; ein Bericht, dem man zu Unrecht glaubt, kostet
eine Welle.

### Zweigbasen und Überschneidung, vor dem Zusammenführen geprüft

Neun Zweige, keiner dreht Arbeit zurück. Die Vorbereitung aus W1.P0 hat
gehalten: **Die einzige Datei, die mehr als ein Paket berührt, ist
`pipeline/contract.py`** — und dort ändern W1.P2 (Zeilen ~58–80) und W1.P9
(~149–157) weit auseinanderliegende Kommentare. Kein Zeilenüberlapp.

`tests/test_contract.py` fasst entgegen meiner Erwartung **kein** Paket an.
Ohne die neun `make/prep/<domäne>.mk`-Dateien und die vorab erklärten
Vertragspfade wären es zwei neunfache Konflikte gewesen.

### W1.P5 — Prep: OSM · fertig

Commit `51eb1f8`, Zweig `w1.p5`. Geschätzt 45 min, gebraucht 26. `osmium`
1.19.1 vorhanden. **Damit sind alle neun Prep-Pakete fertig.**

Der teuerste Schritt der Kette, jetzt gemessen: **286 Sekunden**. Er lief
bisher bei **jedem** Kettendurchgang neu.

Der Gleichheitsnachweis ist gegen die **echte Laufzeitfunktion** geführt,
nicht gegen einen Nachbau: für alle zehn Objektgruppen exakte
Featurezahl, bit-für-bit identische Gesamtfläche und Gesamtlänge, gleiches
CRS, und eine WKB-Stichprobe von bis zu 2000 Features je Gruppe — bei fünf
der zehn Gruppen damit vollständig. Nicht abgedeckt, und der Agent sagt es:
ein lückenloser WKB-Vergleich bei den sechs größten Gruppen. Bei 8,5
Millionen Gebäuden ist das eine vertretbare Grenze.

**Drei Befunde, die den Plan korrigieren:**

1. **Plan §4 nennt acht OSM-Layer, der Code liest zehn.** `buildings` und
   `powerlines` fehlen in meiner Domänentabelle vollständig — und
   `buildings` ist mit 8,5 Millionen Objekten die mit Abstand größte
   Gruppe. Punkt 25.
2. **Drei Objektgruppen sind toter Code:** `landuse`, `places`,
   `addresses` — Reste des in v2 abgeschafften OSM-Adress-Cluster-Pfads.
   Sie stehen in den Filtern, niemand liest sie. Punkt 26.
3. `powerlines` wird bei jedem Lauf extrahiert, obwohl die daraus gebaute
   Maske `power_380_400kv` in der v2-Kette **nirgends persistiert wird** —
   dieselbe Gruppe, deren Rohdatei W1.2 als toten Leser gelöscht hat.
   Reine Rechenverschwendung, nach Regel 4 unangetastet. Punkt 27.

**Abnahme: 147 Tests unverändert, Wächter grün vor und nach dem Lauf.**

### Zusammenführung der Prep-Welle · fertig

Neun Merge-Commits, alle mit `--no-ff`, in der geplanten Reihenfolge:
`556d238` (w1.p1), `54a77e3` (w1.p2), `d219adc` (w1.p3), `1755f1e` (w1.p4),
`8334021` (w1.p5), `a893ff2` (w1.p6), `197bf63` (w1.p7), `7b9fa48` (w1.p8),
`ca386b1` (w1.p9). Davor `4f10e9e` mit meinem Fortschrittsprotokoll.
Kopf: `ca386b1`. Geschätzt 25 min, gebraucht **7**.

**Kein einziger Konflikt.** Bei w1.p9 meldete Git „Auto-merging
`pipeline/contract.py`" — die eine Datei, die zwei Pakete anfassen —, und
die Zeilen lagen disjunkt, wie die Vorprüfung angekündigt hatte.

**Das ist der Ertrag von W1.P0, und er ist jetzt beziffert.** Die erste
Zusammenführung hatte vier Zweige, kostete 30 statt 15 Minuten und
erzeugte drei stille Fehler in der Prosa. Diese hatte **neun** Zweige und
kostete 7 Minuten. Der Unterschied ist nicht Glück: W1.P0 hat vorab alle
neun Vertragspfade erklärt und die neun Make-Ziele auf neun **eigene**
Dateien verteilt. Zwei garantierte neunfache Konflikte sind dadurch nie
entstanden. Ein Vorpaket von 13 Minuten hat mehr gespart, als es gekostet
hat — und die drei falschen Sätze des letzten Mal gab es diesmal nicht,
weil keine zwei Pakete dieselbe Prosa anfassten.

**Die vier inhaltlichen Nachprüfungen, die ich verlangt hatte:**

| Prüfung | Ergebnis |
|---|---|
| Alle neun Module unter `pipeline/prep/` da? | ja, inkl. Unterpaket `kataster/` mit fünf Dateien |
| Alle neun Ziele da und über `-include` auflösbar? | ja — `make -n prep` liefert **zehn** Aufrufe für neun Domänen |
| `pipeline/contract.py` nach beiden Merges konsistent? | ja, RAW- und PREP-Block deckungsgleich mit dem Code |
| Benutzen alle neun `pipeline/fingerprint.py` **gleich**? | ja — nur `write()`/`matches()`, keine Eigenbauten |

Die zehnte Zeile in `make -n prep` ist kein Fehler: Kataster ist als
einziges Paket wirklich in zwei Moduldateien getrennt
(`a_noe_polygonize`, `b_export_parquet`). `osm` und `noe_sekrop` sind
konzeptionell zweistufig, aber bewusst in **einer** Datei mit zwei
Funktionen implementiert — in `.mk`- und Vertragskommentar jeweils
ausdrücklich vermerkt. Der Zuschnitt ist damit uneinheitlich, aber
begründet und dokumentiert.

**Die vierte Prüfung war die wichtigste, und sie ist die einzige, die kein
Werkzeug erzwungen hätte.** Neun Pakete, die dieselbe Frage unabhängig
beantworten, kollidieren nie — sie driften still auseinander. Hier taten
sie es nicht, weil W1.P0 die Antwort vorgegeben hatte.

**Der Nachweislauf der Wellengrenze, der neun einzelne ersetzt:** `sha256`
`dc58b011…9e3df1`, **bitgleich**. Rund drei Minuten, aktiv mit
`pgrep`/`ls -l` in 20-Sekunden-Schritten verfolgt — kein Schlaf auf dem
eigenen Hintergrundlauf, zum ersten Mal nach fünf Vorfällen. Prüfdatei,
Sidecar und Log danach gelöscht.

**Abnahme: 147 Tests bestanden plus 1 übersprungen, unverändert vor und
nach den neun Merges. `make check-guards` grün** — 129 Dateien
hardlinkgeprüft, 41 Python-Dateien schreibgeprüft.

**Abbau ohne Gewalt:** neun Worktrees mit `git worktree remove`, neun
Zweige mit `git branch -d`. Kein `--force`, kein `-D`. Beim letzten Mal
ging das noch nicht — die Symlink-Nebenwirkung ist seit `81849de`
behoben.

### Datenfenster: verwaiste Adress-Parquets · fertig

Kein Commit — `data/` und `build/` sind vollständig gitignored, der
Arbeitsbaum blieb sauber. Der Agent hat das erkannt und **keinen leeren
Commit erzwungen**. Davor `d1a7d3d` mit meinen Plan-Korrekturen.
Geschätzt 15 min, gebraucht 4.

Die beiden Juli-Artefakte des W1.1-Weichenfehlers sind aus `data/` heraus:

| Datei | Größe | mtime | Inode |
|---|---:|---|---:|
| `adressen_31287.parquet` | 41 855 569 B | 23.07.2026 20:18 | 139716806 |
| `bev_gebaeude_31287.parquet` | 42 495 492 B | 24.07.2026 00:11 | 139716807 |

**Nicht gelöscht, sondern verschoben** — und die Inodes sind nach dem `mv`
unverändert, was belegt, dass es wirklich eine Verschiebung war und keine
Kopie. Das war nötig, weil diese beiden Dateien die **zwei Ausnahmen aus
W1.3** waren: die einzigen unter `data/`, die schon Linkanzahl 1 hatten,
weil sie per `to_parquet()` entstanden und nie im Vorgängerprojekt lagen.
Es gibt keine zweite Kopie, und ein Neulauf zöge die Oktober-Rohquelle und
ergäbe andere Dateien. Eine Löschung wäre die zweite unumkehrbare Handlung
des Projekts gewesen — für einen Aufräumschritt ist das zu viel Risiko.

**Der Beweis kam vor der Bewegung.** Alle vier Aufrufer von
`load_address_points`/`load_building_points` lösen `cache_dir` auf
`build/prep/adressen` oder `output/` auf, keiner auf `data/adressen`. Drei
Scheintreffer hat der Agent als solche entlarvt statt sie mitzuzählen: zwei
synthetische Test-Fixtures in Tempverzeichnissen und ein String-Alias in
einem Doku-Graphen.

**Danach der Gegenbeweis:** `load_address_points()` und
`load_building_points()` per echtem Vorgabewert aufgerufen, **ohne** die
verschobenen Dateien — 2 516 345 und 2 524 624 Punkte, frisch unter
`build/prep/adressen/` angelegt. Damit ist nicht nur behauptet, dass
niemand liest, sondern gezeigt, dass es ohne sie funktioniert.

Der Lauf dauerte 9,5 s statt der 6 s aus W1.1. Der Agent nennt eine
Erklärung (`GEBAEUDE.csv` wird aus dem ZIP statt aus Klartext gelesen) und
sagt im selben Atemzug, dass es eine Vermutung ist, kein Beweis. Genau
richtig — Sekunden statt Minuten sind kein Alarm, eine unbelegte Erklärung
als belegt auszugeben schon.

**Abnahme: 147 Tests plus 1 übersprungen, unverändert. Wächter grün, jetzt
gegen 127 statt 129 Dateien** — die erwartete Differenz von genau zwei.

**Grenze, vom Agenten selbst benannt:** reine Textsuche, keine Analyse
dynamischer Importe, und kein Blick in nicht versionierte Notebooks
außerhalb des Repos. Für ein `importlib`-Konstrukt gäbe es keinen Beleg.
Die Konstanten `ADDRESS_CACHE_NAME`/`BUILDING_CACHE_NAME` hat er zusätzlich
gegrept — ohne weitere Fundstellen.

### Prep-Stufe für die fünfte Zonenquelle · fertig

Commit `ba6f3a6`, Zweig `w1.p8b`, eingehängt als `0b61884`. Geschätzt
20 min, gebraucht 8. Der Nachtrag zu meinem eigenen Zuschnittfehler aus
W1.P8.

Die Basisprüfung vor dem Merge hat die Angabe des Agenten bestätigt statt
sie zu glauben: Merge-Basis `d1a7d3d`, nachweislich Vorfahre von
`docs/audit-und-plan` und **nach** allen neun Prep-Merges. Der Zweig fasst
ausschließlich `pipeline/prep/zonen.py` an (+89/−30) — `contract.py` und
`make/prep/zonen.mk` wirklich nicht, wie berichtet.

`pipeline/prep/zonen.py` hat einen fünften Loader `_load_noe()` bekommen —
**erweitert, nicht danebengebaut**. Er schreibt `NOE.gpkg` in denselben
`build/prep/zonen/`-Ordner wie die vier anderen Quellen und nimmt die
NÖ-Datei in den gemeinsamen Fingerabdruck auf.

**Weder `contract.py` noch `make/prep/zonen.mk` mussten angefasst werden** —
`PREP["zonen"]` war schon ein Verzeichnis, und das Make-Ziel ruft ohnehin
nur das Modul auf. Der Zuschnitt von W1.P0 trägt also auch für einen Fall,
den er nicht vorhergesehen hat.

**Der stärkere Nachweisweg war hier möglich, und der Agent hat ihn
genommen.** Die vier Quellen aus W1.P8 mussten gegen einen Nachbau
verglichen werden, weil ihre Loader privat sind. Die NÖ-Quelle läuft aber
über `read_layer()` aus `abschichtung_common.py` — öffentlich und einzeln
aufrufbar, genau wie `admin_boundaries()` bei W1.P1. Direkt importiert und
mit dem echten Pfad aufgerufen:

| Prüfung | Ergebnis |
|---|---|
| Anzahl | **71**, in Rohquelle, nach `read_layer()` und im Prep-Ergebnis |
| CRS | EPSG:4326 → 31287, beidseitig identisch |
| Symmetrische Differenz der Vereinigung | **0,0 m²** |
| Je Einzelgeometrie, über das Verlangte hinaus | **71/71 topologisch gleich** |

Die Einzelgeometrieprüfung war nicht beauftragt. Sie hat dabei den
GPKG-Promotionseffekt aus Punkt 20 ein zweites Mal sichtbar gemacht: 49 von
71 Polygonen werden beim Schreiben zu MultiPolygonen. Damit ist das kein
Einzelfall der Naturschutz-Domäne mehr, sondern eine Eigenschaft jeder
Prep-Stufe, die GPKG schreibt.

**Ein fachlicher Unterschied, sauber benannt und nach Regel 4 nicht
angetastet:** `read_layer()` bereinigt **keine** ungültigen, leeren oder
Null-Geometrien — anders als die vier `WIND_ZONE_SOURCES`-Loader. Auf den
heutigen Rohdaten macht das keinen Unterschied (0 gemessen), aber der Agent
hat bewusst keinen Bereinigungsschritt ergänzt, den die laufende Funktion
nicht hat. Das wäre eine Verbesserung gewesen, keine Überführung — und
hätte die Gleichheit zerstört, die er gerade beweisen sollte.

**Vier Grenzen, selbst benannt:** kein Fließkommarauschen über mehrere
GPKG-Rundtrips; die Sachattribute werden verworfen wie bei den anderen vier
(Problem nur, falls ein Welle-2-Konsument sie braucht); kein
bounds-gefilterter Lauf; keine Absicherung gegen künftige Schemaänderungen
der Rohquelle.

**Abnahme: 147 Tests plus 1 übersprungen, Baseline selbst gemessen. Wächter
grün vor und nach, `find -newer` gegenkontrolliert. Keine neuen Tests** —
das Verdrahten der Tests ist W4.3, nicht Sache dieses Nachtrags.

### Konfliktprüfung vor Welle 2 — und was sie nicht finden konnte

Kein Paket, sondern die Vorbereitung der Welle. Sie hat meinen Zuschnitt
an drei Stellen widerlegt und den Plan verändert; die Regel daraus steht
als §13.8 im Plan.

**Mein Verdacht war falsch, und das war die kleinere Nachricht.** Ich
hatte einen Dreifachkonflikt in `windkraft/calc/abschichtung_common.py`
erwartet. Die Funktionsblöcke sind aber disjunkt — HiG 769–958, OSM
958–1154 — und `pipeline/contract.py` führt alle 33 Layernamen bereits
vollständig. Zwei befürchtete Konfliktherde existieren nicht.

**Gefunden wurde eine Lücke, und die ist gefährlicher als jeder
Konflikt.** `tests/test_contract.py:280-302` setzt die Sollmenge der
Checkpoints aus **vier** Skripten zusammen; mein §7 beauftragte drei. Die
17 Layer aus `04_create_distance_zones.py` — Puffer, Naturschutz,
Gelände, offizielle Windzonen, WKA-Bestand — hatten keinen Besitzer. Wäre
Welle 2 wie geplant gelaufen, hätte danach ein Viertel der Kette gefehlt,
**und niemand hätte es gemeldet, weil kein Paket dafür zuständig gewesen
wäre, es zu melden.**

Das ist der Grund für Regel 7 im Plan: Eine Konfliktprüfung sucht
Überschneidungen, und eine Lücke ist keine. Die Sollmenge muss aus
Vertrag und Tests kommen, nicht aus meiner eigenen Tabelle — sonst prüfe
ich die Quelle des Fehlers gegen sich selbst.

**Drei Änderungen am Zuschnitt:**

| | |
|---|---|
| W2.2 geht in W2.1 auf | `widmung_seed()` (`hig_source_masks.py:70-75`) verundet die drei Widmungs-Layer und gibt das Ergebnis als Filter in die Hüllenerkennung. Getrennt hieße verdoppeln (§13.6) oder eine Datei zu zweit besitzen (Regel 1). |
| W2.4 neu | Die 17 herrenlosen Checkpoints. §3 sagt, Stufe 4 gelte für jede Domäne — dann muss sie für jede beauftragt sein. |
| W2.P0 neu | `pipeline/layers/__init__.py`, `-include make/layers/*.mk`, und **`build/prep/` ins `worktree`-Ziel**. |

Der dritte Punkt von W2.P0 ist der teuerste: `Makefile:163-174` verlinkt
heute nur `data/` und `distance_layers/`. Drei Layer-Worktrees hätten die
Prep-Stufe je einzeln neu gerechnet — Kataster allein 45 bis 70 Minuten,
dreifach. Eine Kopie von Hand wäre schlimmer: sie zerrisse die
mtime-basierten Fingerabdrücke und löste stille Neuberechnungen aus.

**Die gefährlichste Stelle der Welle** liegt ausgerechnet im bislang
herrenlosen Block: `layer_done()` prüft Form, CRS, Transform und
Bandname, nicht die Eingabe. Zusammen mit dem GPKG-Promotionseffekt aus
Punkt 20 schriebe sich ein falscher Wert ins Band und würde beim nächsten
Lauf als „fertig" akzeptiert. Deshalb steht die Geometrietyp-Prüfung
ausdrücklich in der Abnahme von W2.4.

## Offene Punkte

| # | Punkt | Fällig |
|---|---|---|
| ~~1~~ | ~~Worktrees haben kein `data/`.~~ **Erledigt in W0.3**: `make worktree` verlinkt `data/` und die geteilten `distance_layers/` hinein. Im Parallelbatch bewährt. | — |
| ~~1b~~ | ~~Jedes Worktree ist von Geburt an schmutzig.~~ **Erledigt in `81849de`** — aber anders als hier vermutet: `--skip-worktree` allein reichte nicht, weil der Symlink `data` nie getrackt war und als `??` stehenblieb. Nötig war zusätzlich `/data` in `.git/info/exclude`. | — |
| ~~2~~ | ~~Laufzeit der Kataster-Vorverarbeitung ist unbekannt.~~ **Von W1.P2 vermessen: 45–70 min**, nicht 5 h. Stufe b belastbar, Stufe a mit Stichprobenunsicherheit. | — |
| ~~22~~ | ~~Fünfte Zonenquelle ohne Prep-Stufe.~~ **Erledigt in `ba6f3a6`** — `_load_noe()` in `pipeline/prep/zonen.py`, 0,0 m² symmetrische Differenz, 71/71 Geometrien topologisch gleich. Vertrag und Make-Ziel blieben unberührt. | — |
| 23 | Zwei Doku-Fehler zum Kataster. **Erste Hälfte erledigt:** Plan §4 nennt jetzt 9,1 GB statt 7,8, und die davon abhängige Gesamtgröße von `data/` ist an beiden Fundstellen von ~11 auf ~12 GB nachgezogen. **Offen:** `docs/rohdaten.md` beschreibt 338 674 verworfene NÖ-Polygone, die Produktionsdatei enthält aber die volle Zahl 3 491 407 — vermutlich aus einer Codefassung vor dem Filter. | mit Punkt 3 |
| ~~25~~ | ~~Plan §4 nennt acht OSM-Layer, der Code liest zehn.~~ **Erledigt, nach Klärung eines scheinbaren Widerspruchs.** `OSM_PBF_FILTERS` deklariert **13** Schlüssel, gelesen werden **10**, tot sind **3**. Die acht im Plan waren zehn minus `buildings` und `powerlines` — die drei toten standen nie darin. Zwei Vergleichsachsen (Plan gegen Laufzeit; Deklaration gegen Laufzeit), die beide auf die Zahl zehn treffen. Die Zeile nennt jetzt alle zehn mit ihren Codeschlüsseln. | — |
| 26 | Drei OSM-Objektgruppen sind toter Code: `landuse`, `places`, `addresses` — Reste des in v2 abgeschafften Adress-Cluster-Pfads. Stehen in den Filtern, niemand liest sie. | Aufräumwelle |
| 27 | `powerlines` wird bei jedem OSM-Lauf extrahiert, obwohl die Maske `power_380_400kv` nirgends persistiert wird. Dieselbe Gruppe, deren Rohdatei W1.2 als toten Leser gelöscht hat. Reine Rechenverschwendung. | Welle 2 |
| 24 | **Dritter Fall desselben Cache-Musters:** `widmung_sources._ensure_ktn_gpkg()` prüft beim Wiederverwenden nur die Existenz der extrahierten Datei, nicht ob das Quell-ZIP sich geändert hat. Wie `layer_done()` und wie die W1.1-Weiche. Der Prep-Fingerabdruck erfasst das ZIP korrekt, der Extraktions-Cache daneben nicht. **Besitzer: W2.1** — `pipeline/prep/widmung.py:67` importiert `widmung_sources` und nutzt die Funktion weiter; ohne benannten Besitzer wäre auch das eine Lücke nach Regel 7. | W2.1 |
| 5 | **`sys.path`-Präambeln.** W1.8 hat die Voraussetzung geschaffen (Paket ist jetzt installierbar), aber die Präambeln stehen noch in rund einem Dutzend Dateien unter `scripts/` und `tests/`. Zum Entfernen fehlt: `scripts/` ist kein Paket, Aufrufe müssten auf `python -m` umgestellt werden, und `tools/` bräuchte womöglich ebenfalls Paketstatus. Eigenes Paket wert, gehört nicht in W1.8. | Welle 4 oder später |
| 3 | `docs/widmung_v2_provenance.md` nennt Quellpfade, die es nicht mehr gibt. **Entschieden: lebende Doku.** Sie behauptet, wo die Daten herkommen — ein veralteter Pfad darin führt aktiv in die Irre, anders als ein Laufbericht mit Datum. Von W2.1 mitzuziehen. Dieselbe Regel für `docs/FOLLOWUPS.md` (Punkt 11). **Eingefroren** bleibt allein `docs/RUN1_VERGLEICH.md`: ein datierter Messbericht, dessen Wert gerade darin liegt, dass er nicht nachgeführt wird. Meine Entscheidung, überstimmbar. | W2.1 |
| 4 | `config.json:osm_dir` und `wind_pd_100` zeigen auf Dateien, die es nie gab. Mitgezogen, aber weiterhin tot. | W1.x |
| 6 | `describe_sources()` in `windkraft/calc/wind_zones.py` hat keinen Aufrufer. Von W1.5 bewusst nicht angetastet, weil außerhalb des Auftrags. | W1.x |
| ~~7~~ | ~~`streusiedlung.py` hat eine verdeckte Cache-Weiche.~~ **Von W1.6 untersucht, Entwarnung:** `cache_dir` ist Pflicht-Keyword (`streusiedlung.py:82`), wird an `bev_register.py` durchgereicht und dort seit W1.1 sauber aufgelöst. Keine zweite Weiche. Einziger Aufrufer ist `docs/analysis/streusiedlung_knee.py:217`, außerhalb der v2-Kette, Ziel nicht unter `data/`. | — |
| ~~8~~ | ~~Ungenutzter Import `admin_boundaries`.~~ **In W1.6 entfernt**, `ruff` sauber. | — |
| 9 | `docs/HANDOFF.md` trägt ein veraltetes Referenz-Manifest. Das README verweist nur darauf, dass es veraltet ist. Wer es aktualisiert, ist nicht festgelegt. | Welle 4 |
| 10 | Die 18 von 38 Bändern, die zwischen `run1` und der Referenz-TIF um < 0,004 % abweichen, sind laut `RUN1_VERGLEICH.md` **ungeklärt**. Das berührt die Projektfrage, ob `run1` das Vorgängerprojekt als Quelle der Wahrheit ablösen darf. Keine Textkorrektur, sondern eine Entscheidung. | Nutzer, vor Welle 5 |
| 11 | `docs/FOLLOWUPS.md` führt die veraltete `EXCLUSION_LAYERS`-Liste weiterhin als offenen Punkt, obwohl W1.5 das ganze Skript gelöscht hat. **Mit Punkt 3 entschieden: lebende Liste.** Eine Liste offener Punkte, die geschlossene Punkte weiterführt, kostet jeden Leser die Prüfung, ob der Punkt noch existiert — das ist der Zweck der Liste, ins Gegenteil verkehrt. Wer einen Punkt schließt, streicht ihn dort. | W2.1 |
| ~~12~~ | ~~Sackgasse eine Ebene höher: `pdf_hig_sources.py` erzeugt GeoJSON, die niemand liest.~~ **Erledigt in W1.P9** — das Modul `windkraft/noe/pdf_hig_sources.py` ist als ganzes weg, die Sackgasse an `e3d3655` belegt statt geglaubt. | — |
| 13 | Der `Run:`-Hinweis im Docstring von `scripts/widmung_v2/02_build_hig_sources.py:26-27` nennt den alten Pfad `scripts/main/build_hig_sources.py`. Vorbestehend. | Sammelposten |
| 17 | `windkraft/util/admin.py` (`load_vgd`, `load_laender`, `load_bezirke`, `load_austria`) ist tot — nirgends importiert außer in einem Kommentar, der es ausdrücklich als „bewusst nicht mitgenommen" bezeichnet. | Aufräumwelle |
| 18 | Drei Skripte lesen die VGD-Rohdatei direkt und unabhängig von `admin_boundaries()`: `create_noe_dkm_polygon_fill_map.py`, `extract_noe_vector_layers.py`, `align_pdf_shapefile.py` — teils **ohne `to_crs`**. Die Annahme, die Rohdatei sei bereits EPSG:31287, stimmt hier zufällig. Bei der Umstellung auf `build/prep/admin/` zu prüfen. **Besitzer: W2.4** — dessen Block enthält `province_buffer_mask`, den einzigen Layer-Konsumenten der Verwaltungsgrenzen. | W2.4 |
| 20 | **GeoPackage promoviert Polygone zu MultiPolygonen.** Beim Schreiben nach GPKG werden gemischte Geometrietypen vereinheitlicht. **Zweimal unabhängig belegt:** 383 von 920 bei `natur` (W1.P7), 49 von 71 bei der NÖ-Zonenquelle (Punkt 22). Damit kein Einzelfall einer Domäne, sondern Eigenschaft **jeder** Prep-Stufe, die GPKG schreibt. Für `rasterize` folgenlos; für eine geometrietyp-sensitive Layer-Stufe nicht. | Welle 2 |
| 21 | 33 von 920 Schutzgebietsgeometrien sind laut GEOS ungültig. Der heutige Konsument prüft und repariert das ebenfalls nicht — deshalb nach Regel 4 unverändert. | fachlich, Nutzer |
| ~~19~~ | ~~Stille Falle: zwei Juli-Parquets unter `data/adressen/`.~~ **Erledigt im Datenfenster nach der Prep-Welle.** Nicht gelöscht, sondern in den Sitzungs-Scratchpad verschoben — es waren die zwei Dateien aus W1.3 ohne zweite Kopie im Vorgängerprojekt, und ein Neulauf ergäbe wegen des Oktober-Stichtags andere Dateien. Inode nach dem `mv` unverändert. | — |
| 28 | `docs/dataflow/src/1_merge.py` führt den Pfad `data/adressregister/…`, den es seit dem W0.1-Umbau nicht mehr gibt. Nur ein Alias in einer Doku-Tabelle, kein Datenzugriff — aber ein stiller falscher Pfad in **erzeugter** Doku, den keine Suche der Pfadpakete gefunden hat, weil er keinen Leser hat. | Sammelposten |
| 14 | **`LEGACY_ENTFAELLT` ist jetzt leer**, und `test_legacy_entfaellt_path_exists` wird dadurch zu einem übersprungenen Platzhalter — ein Test, der nichts mehr prüft. Register bleibt laut §13.1 stehen; zu entscheiden ist, ob der Test bleibt, entfällt oder gegen die Leerheit prüft. | W1.4 |
| 15 | **`Path("").exists()` ist `True`.** Fällt `abschichtung_common.py:966` je in den PBF-Fallback, liefert `cfg["paths"].get("powerlines_gpkg", "")` jetzt einen leeren String, und `read_layer()` geht auf das Arbeitsverzeichnis statt auf eine GIS-Datei los. Randfall, tritt nur bei fehlendem OSM-PBF ein, aber die Fehlermeldung wäre irreführend. In `docs/rohdaten.md` §5 vermerkt. | W1.P5 |
| 16 | `docs/rewrite/UMSETZUNG.md` und `packages.json` beschreiben W1.2 anders als `PLAN.md` (sechs Pfade weg, inklusive `Aktualitaetsstand.txt`, das bleiben soll). Veraltete Planungsartefakte, die dem Plan widersprechen. Meine Dateien, nicht die der Pakete. | vor Welle 2 |
