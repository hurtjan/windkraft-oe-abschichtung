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
| Abgeschlossen | 11 von 30 — Welle 0, Aufräumteil und **beide Datenfenster** der Welle 1 |
| Als Nächstes | W1.4, die Wächter — danach beginnt die Prep-Welle |
| `data/` | **hardlinkfrei**, 50 echte Dateien, per Wächter als Invariante gesichert |
| Zweig | `docs/audit-und-plan`, kein Remote |
| Abweichungen bisher | keine — alle Pakete bitgleich |

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
| W1.4 | Wächter für Rohdaten | offen | 25 min | | braucht W1.1, W1.2 |
| W1.P1 | Prep: Verwaltungsgrenzen | offen | 25 min | | |
| W1.P2 | Prep: Kataster | offen | 60 min | | **+ unbekannter Volllauf** |
| W1.P3 | Prep: Adressregister | offen | 40 min | | |
| W1.P4 | Prep: Flächenwidmung | offen | 45 min | | |
| W1.P5 | Prep: OSM, zwei Stufen | offen | 45 min | | |
| W1.P6 | Prep: Gelände und Wind | offen | 20 min | | |
| W1.P7 | Prep: Naturschutz | offen | 25 min | | |
| W1.P8 | Prep: Windzonen | offen | 30 min | | braucht W1.7 |
| W1.P9 | Prep: NÖ-SekROP-PDF, zwei Stufen | offen | 45 min | | |
| W2.1 | Layer: Widmung | offen | 40 min | | |
| W2.2 | Layer: Häuser im Grünen | offen | 40 min | | |
| W2.3 | Layer: OSM und Infrastruktur | offen | 45 min | | |
| W3.1 | Finalisierung und Manifest-Vertrag | offen | 45 min | | |
| W3.2 | Validierung | offen | 30 min | | schreibt `abweichungen.tsv` |
| W4.1 | Dashboard neu | offen | 40 min | | |
| W4.2 | Gemeindegrenzen-Export | offen | 30 min | | |
| W4.3 | Tests verdrahten | offen | 30 min | | |
| W5.1 | Beweislauf aus Rohdaten | offen | 15 min | | **+ Vorverarbeitung** |

## Zeitbilanz

| | |
|---|---|
| Gebraucht bisher | **3 h 19** für elf Pakete plus die Zusammenführung |
| davon Welle 0 | 1 h 30, seriell (49 + 28 + 12 min) |
| davon Welle 1, Aufräumen | 29 min (W1.7 seriell 15 min, dann vier parallel in 14 min) |
| davon Zusammenführung | 30 min — doppelt so lang wie geschätzt |
| Verbleibend, geschätzt | **rund 5 h** Wanduhrzeit |
| Davon unbekannt | die Kataster-Vorverarbeitung — keine Messung existiert |

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

Die 6 Stunden sind **nicht** die Summe der Einzelschätzungen (die ergäbe
gut 13 h), weil Pakete parallel laufen. Gerechnet ist je Stufe das längste
Paket plus Puffer für meine eigene Abnahme, die seriell bleibt:

| Stufe | Pakete | Dauer |
|---|---|---:|
| W1.7 allein | 1 | 25 min |
| Aufräumen, parallel | 5 | ~~25 min~~ · 4 davon in **14 min** gemessen |
| Datenfenster, seriell | 2 | 40 min |
| Wächter | 1 | 25 min |
| Prep, gedrosselt auf drei gleichzeitig | 9 | 2 h 25 |
| Welle 2, parallel | 3 | 45 min |
| Welle 3, seriell | 2 | 1 h 15 |
| Welle 4, parallel | 3 | 40 min |
| Welle 5 | 1 | 15 min + ? |

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

## Offene Punkte

| # | Punkt | Fällig |
|---|---|---|
| ~~1~~ | ~~Worktrees haben kein `data/`.~~ **Erledigt in W0.3**: `make worktree` verlinkt `data/` und die geteilten `distance_layers/` hinein. Im Parallelbatch bewährt. | — |
| ~~1b~~ | ~~Jedes Worktree ist von Geburt an schmutzig.~~ **Erledigt in `81849de`** — aber anders als hier vermutet: `--skip-worktree` allein reichte nicht, weil der Symlink `data` nie getrackt war und als `??` stehenblieb. Nötig war zusätzlich `/data` in `.git/info/exclude`. | — |
| 2 | Laufzeit der Kataster-Vorverarbeitung ist unbekannt. | W1.P2 |
| 5 | **`sys.path`-Präambeln.** W1.8 hat die Voraussetzung geschaffen (Paket ist jetzt installierbar), aber die Präambeln stehen noch in rund einem Dutzend Dateien unter `scripts/` und `tests/`. Zum Entfernen fehlt: `scripts/` ist kein Paket, Aufrufe müssten auf `python -m` umgestellt werden, und `tools/` bräuchte womöglich ebenfalls Paketstatus. Eigenes Paket wert, gehört nicht in W1.8. | Welle 4 oder später |
| 3 | `docs/widmung_v2_provenance.md` nennt Quellpfade, die es nicht mehr gibt. Unklar, ob eingefrorene Momentaufnahme wie `RUN1_VERGLEICH.md` oder lebende Doku. | Welle 1, Widmungspakete |
| 4 | `config.json:osm_dir` und `wind_pd_100` zeigen auf Dateien, die es nie gab. Mitgezogen, aber weiterhin tot. | W1.x |
| 6 | `describe_sources()` in `windkraft/calc/wind_zones.py` hat keinen Aufrufer. Von W1.5 bewusst nicht angetastet, weil außerhalb des Auftrags. | W1.x |
| ~~7~~ | ~~`streusiedlung.py` hat eine verdeckte Cache-Weiche.~~ **Von W1.6 untersucht, Entwarnung:** `cache_dir` ist Pflicht-Keyword (`streusiedlung.py:82`), wird an `bev_register.py` durchgereicht und dort seit W1.1 sauber aufgelöst. Keine zweite Weiche. Einziger Aufrufer ist `docs/analysis/streusiedlung_knee.py:217`, außerhalb der v2-Kette, Ziel nicht unter `data/`. | — |
| ~~8~~ | ~~Ungenutzter Import `admin_boundaries`.~~ **In W1.6 entfernt**, `ruff` sauber. | — |
| 9 | `docs/HANDOFF.md` trägt ein veraltetes Referenz-Manifest. Das README verweist nur darauf, dass es veraltet ist. Wer es aktualisiert, ist nicht festgelegt. | Welle 4 |
| 10 | Die 18 von 38 Bändern, die zwischen `run1` und der Referenz-TIF um < 0,004 % abweichen, sind laut `RUN1_VERGLEICH.md` **ungeklärt**. Das berührt die Projektfrage, ob `run1` das Vorgängerprojekt als Quelle der Wahrheit ablösen darf. Keine Textkorrektur, sondern eine Entscheidung. | Nutzer, vor Welle 5 |
| 11 | `docs/FOLLOWUPS.md` führt die veraltete `EXCLUSION_LAYERS`-Liste weiterhin als offenen Punkt, obwohl W1.5 das ganze Skript gelöscht hat. Im README nachgezogen, dort nicht — die Datei galt als eingefroren. Zu klären: eingefrorene Momentaufnahme oder lebende Liste? Dieselbe Frage wie Punkt 3. | mit Punkt 3 |
| 12 | **Sackgasse eine Ebene höher.** Nachdem W1.6 `noe_pdf_source_mask()` entfernt hat, erzeugt `windkraft/noe/pdf_hig_sources.py:derive_layer_files()` (aufgerufen in `scripts/noe/extract_noe_vector_layers.py:286`) `output/noe/pdf_hig_source_*.geojson`, die niemand mehr liest. Fremder Besitz, deshalb von W1.6 korrekt liegengelassen. | W1.P9 |
| 13 | Der `Run:`-Hinweis im Docstring von `scripts/widmung_v2/02_build_hig_sources.py:26-27` nennt den alten Pfad `scripts/main/build_hig_sources.py`. Vorbestehend. | Sammelposten |
| 14 | **`LEGACY_ENTFAELLT` ist jetzt leer**, und `test_legacy_entfaellt_path_exists` wird dadurch zu einem übersprungenen Platzhalter — ein Test, der nichts mehr prüft. Register bleibt laut §13.1 stehen; zu entscheiden ist, ob der Test bleibt, entfällt oder gegen die Leerheit prüft. | W1.4 |
| 15 | **`Path("").exists()` ist `True`.** Fällt `abschichtung_common.py:966` je in den PBF-Fallback, liefert `cfg["paths"].get("powerlines_gpkg", "")` jetzt einen leeren String, und `read_layer()` geht auf das Arbeitsverzeichnis statt auf eine GIS-Datei los. Randfall, tritt nur bei fehlendem OSM-PBF ein, aber die Fehlermeldung wäre irreführend. In `docs/rohdaten.md` §5 vermerkt. | W1.P5 |
| 16 | `docs/rewrite/UMSETZUNG.md` und `packages.json` beschreiben W1.2 anders als `PLAN.md` (sechs Pfade weg, inklusive `Aktualitaetsstand.txt`, das bleiben soll). Veraltete Planungsartefakte, die dem Plan widersprechen. Meine Dateien, nicht die der Pakete. | vor Welle 2 |
