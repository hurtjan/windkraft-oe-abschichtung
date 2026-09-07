# Umsetzungsplan: Umbau in sechs Wellen

**Stand: geplant, nicht begonnen.** Kein Paket ist angefangen, keine Datei
außerhalb von `docs/` wurde geändert.

Dreißig Arbeitspakete, verteilt auf sechs Wellen. Welle 0 friert die
Schnittstellen ein — Rohdatenpfade, Prep-Ausgaben, Layernamen, Produktpfade
an genau einer Stelle. Danach laufen 18 Pakete gleichzeitig, ohne sich zu
berühren, weil vorher feststeht, wem welche Datei gehört. Jedes Paket nennt
die Dateien, die es besitzt, seine Abnahmebedingung und den Weg zurück.

## Die eine Abnahmebedingung

Sie gilt für jedes Paket in jeder Welle und macht paralleles Arbeiten
überhaupt erst verantwortbar. Der Umbau ist eine Umstrukturierung, keine
fachliche Änderung.

```
für jedes Band b in 1..38:
    if b == 37:  Differenz nur innerhalb der Steiermark zulässig
    sonst:       bitgleich zum Referenz-TIF
```

Die einzige beabsichtigte inhaltliche Abweichung ist der Wegfall der
steirischen SAPRO-2026-Ausschlusszonen in Band 37. Jede andere Abweichung
ist ein Fehler, egal wie plausibel sie aussieht.

Das ist mechanisch prüfbar und braucht kein Fachwissen — deshalb kann es
nach jedem Paket laufen, nicht erst am Ende. Der schnelle Weg: Wellen 1 bis
3 lassen sich gegen die vorhandenen Checkpoint-Layer prüfen, indem nur die
Finalisierung neu läuft. Das dauert Minuten statt Stunden. Der vollständige
Lauf aus Rohdaten steht einmal am Schluss in Welle 5.

## Wellen

Zwischen den Wellen wird synchronisiert, innerhalb einer Welle nicht.

| Welle | Thema | Pakete | Parallel? |
|---|---|---|---|
| 0 | Schnittstellen | 3 | nein — nacheinander |
| 1 | Breite Arbeit | 18 | ja — gleichzeitig |
| 2 | Layer | 3 | ja — gleichzeitig |
| 3 | Finalisierung | 2 | nein — nacheinander |
| 4 | Prüfung | 3 | ja — gleichzeitig |
| 5 | Beweis | 1 | nein — nacheinander |

## Arbeitspakete

„Besitzt" heißt: nur dieses Paket darf diese Pfade anfassen. Zwei Pakete
derselben Welle teilen sich niemals eine Datei — das ist die Bedingung,
unter der die Parallelität hält. Dieselben Daten liegen maschinenlesbar in
`packages.tsv` / `packages.json` (siehe `src/extract_packages.py`).

| Paket | Welle | Gruppe | Titel | Besitzt | Braucht | Abnahme |
|---|---|---|---|---|---|---|
| W0.1 | 0 | Daten | Rohdaten nach Thema sortieren | data/** (nur Verschiebungen)<br>windkraft/calc/wind_zones.py (hartkodierte Pfade) | — | Alte Kette läuft unverändert; Finalisierung aus vorhandenen Layern liefert bitgleiches TIF. |
| W0.2 | 0 | Daten | Pfadvertrag anlegen | pipeline/contract.py (neu)<br>config.json | W0.1 | Jeder Rohpfad, jede Prep-Ausgabe, jeder Layername und jeder Produktpfad ist genau einmal deklariert und importierbar. |
| W0.3 | 0 | Daten | Verzeichnisgerüst und Make-Ziele | build/ out/ pipeline/ (neu)<br>.gitignore<br>Makefile | W0.2 | make · make prep · make all · make test existieren; make läuft die heutige Kette unverändert. |
| W1.1 | 1 | Aufräumen | Adress-Cache-Weiche entfernen | windkraft/calc/bev_register.py | W0.3 | cache_dir wirkt tatsächlich; Cache landet unter build/, nicht in data/. |
| W1.2 | 1 | Aufräumen | Tote Daten löschen | data/osm_power_lines.gpkg<br>data/windkraftzonen_shapefile_2024.json<br>data/…/Aktualitaetsstand.txt<br>data/…/.claude/<br>data/WINDKRAFT_AUSSCHLUSSZONE.zip<br>data/README.md | W0.3 | Sechs Pfade weg; TIF unverändert (keiner erreichte ein Band). |
| W1.3 | 1 | Daten | Hardlinks auflösen | data/** (nur Inodes, kein Inhalt) | W0.3 | find data -type f -links +1 liefert nichts; Prüfsummen vorher/nachher identisch; ~13 GB mehr belegt. |
| W1.4 | 1 | Aufräumen | Wächter für Rohdaten | tools/check_raw_only.py (neu)<br>tools/check_hardlink_safety.py | W0.3 | Bricht ab, wenn in data/ etwas Abgeleitetes liegt oder eine Datei Link-Count > 1 hat. |
| W1.5 | 1 | Aufräumen | Tote Skripte löschen | scripts/webmap/build_layer_viewer.py<br>scripts/analysis/build_v2_dashboard_data.py<br>scripts/noe/derive_pdf_hig_sources.py | W0.3 | Kein Verweis mehr im Repo; Kette läuft unverändert. |
| W1.6 | 1 | Aufräumen | NÖ-PDF-HiG-Sackgasse entfernen | scripts/widmung_v2/02_build_hig_sources.py<br>windkraft/calc/hig_source_masks.py | W0.3 | Checkpoint und harte Vorbedingung sind weg; TIF bitgleich — der Layer erreichte nachweislich kein Band. |
| W1.7 | 1 | Aufräumen | Ausschlusszonen entfernen | windkraft/calc/wind_zones.py | W0.1 | Stmk2026Aus und die AUSSCHLUSSZONE-Registrierung sind weg. Einzige zulässige Bandänderung: Band 37 in der Steiermark. |
| W1.8 | 1 | Aufräumen | Paketmetadaten bereinigen | pyproject.toml | W0.3 | Toter Entry-Point weg; PyMuPDF harte Abhängigkeit; Paket installierbar, sodass sys.path-Präambeln entfallen können. |
| W1.9 | 1 | Aufräumen | Doku-Widersprüche korrigieren | README.md | W0.3 | Status stimmt; die Behauptung, die Kataster-Kette laufe nur im Altrepo, ist entfernt. |
| W1.P1 | 1 | Prep | Prep: Verwaltungsgrenzen | pipeline/prep/admin.py | W0.2 | build/prep/admin/ enthält Gemeinden und Bundesländer in EPSG:31287; Fingerabdruck der Eingänge geschrieben. |
| W1.P2 | 1 | Prep | Prep: Kataster | pipeline/prep/kataster/<br>scripts/preprocessing/* (Umzug) | W0.2 | Geoparquet aus Rohdaten; Vorabprüfung mit einem Bundesland, dann voller Lauf. Feldschema identisch zum bestehenden. |
| W1.P3 | 1 | Prep | Prep: Adressregister | pipeline/prep/adressen.py | W0.2, W1.1 | Parquets unter build/prep/adressen/; Zeilenzahl identisch zum bisherigen Cache. |
| W1.P4 | 1 | Prep | Prep: Flächenwidmung | pipeline/prep/widmung.py | W0.2 | Drei Bündel als GeoPackage; Featurezahl je Bundesland identisch zum heutigen Zwischenstand. |
| W1.P5 | 1 | Prep | Prep: OSM, zwei Stufen | pipeline/prep/osm/ | W0.2 | Extraktion und Layerableitung getrennt; osmium als harte Vorbedingung statt stillem Fallback. |
| W1.P6 | 1 | Prep | Prep: Gelände und Wind | pipeline/prep/terrain.py | W0.2 | Nur Durchreichen und Gitterprüfung — kein Resampling. Bricht ab, wenn Gitter oder CRS abweichen. |
| W1.P7 | 1 | Prep | Prep: Naturschutz | pipeline/prep/natur.py | W0.2 | Schutzgebiete aus dem ZIP entpackt und reprojiziert; Featurezahl identisch. |
| W1.P8 | 1 | Prep | Prep: Windzonen | pipeline/prep/zonen.py | W0.2, W1.7 | Alle verbleibenden Zonenquellen als harte Vorbedingung — kein stiller Ausfall mehr bei fehlender Datei. |
| W1.P9 | 1 | Prep | Prep: NÖ-SekROP-PDF, zwei Stufen | pipeline/prep/noe/<br>scripts/noe/* (Umzug) | W0.2 | Alignment und Vektorisierung getrennt; erzeugte GeoJSON deckungsgleich mit den bestehenden. |
| W2.1 | 2 | Layer | Layer: Widmung | pipeline/layers/widmung.py | Welle 1 | Erzeugte Layer bitgleich zu den bestehenden Checkpoints. |
| W2.2 | 2 | Layer | Layer: Häuser im Grünen | pipeline/layers/hig.py | Welle 1 | Bitgleich; die NÖ-Ausmaskierung bleibt unverändert erhalten. |
| W2.3 | 2 | Layer | Layer: OSM und Infrastruktur | pipeline/layers/osm.py | Welle 1 | Bitgleich; Wiederaufsetzen überspringt vorhandene Layer nachweislich korrekt. |
| W3.1 | 3 | Finalisierung | Finalisierung und Manifest-Vertrag | pipeline/finalize.py<br>windkraft/calc/band_manifest.py | Welle 2 | 38 Bänder, Manifest mit Nummer, Name, Rolle, Puffer und Quelle je Band; Schema versioniert. |
| W3.2 | 3 | Finalisierung | Validierung | pipeline/validate.py | W3.1 | Prüft das TIF gegen sein eigenes Manifest und gegen die Referenz — die Abnahmebedingung aus Abschnitt 1 als Kommando. |
| W4.1 | 4 | Prüfung | Dashboard neu | pipeline/verify/dashboard.py<br>out/dashboard/ | W3.1 | Liest ausschließlich das Manifest; keine Bandnamen im Code. Läuft gegen ein Manifest mit geänderter Bandzahl ohne Anpassung. |
| W4.2 | 4 | Prüfung | Gemeindegrenzen-Export | pipeline/verify/gemeinden.py<br>out/gemeinden.geojson | W1.P1 | Grenzen im Rasterbezug; Deckungsabweichung gegen das TIF ausgewiesen und unter Schwellwert. |
| W4.3 | 4 | Prüfung | Tests verdrahten | tests/**<br>Makefile (nur das test-Ziel) | Welle 3 | make test läuft die acht vorhandenen Tests plus die neuen Vertragstests; grün. |
| W5.1 | 5 | Prüfung | Beweislauf aus Rohdaten | — (nur Ausführung) | Wellen 0–4 | rm -rf build && make all erzeugt das TIF vollständig neu; Abnahmebedingung erfüllt; Laufzeiten je Stufe protokolliert. |

## Regeln, die die Parallelität tragen

**Ein Pfad, ein Besitzer.** Jeder Pfad im Repo steht in genau einem Paket.
Wer eine Datei anfassen will, die ihm nicht gehört, meldet das, statt sie zu
ändern — sonst entstehen genau die stillen Überschreibungen, die dieses
Repo ohnehin plagen.

**Der Vertrag wird gelesen, nicht kopiert.** Nach Welle 0 kommt kein Pfad
und kein Layername mehr als Literal in ein Skript. Wer einen braucht,
importiert ihn. Damit ändert eine Umbenennung genau eine Datei statt
fünfzehn.

**Ein Zweig je Paket.** Achtzehn gleichzeitige Pakete in einem
Arbeitsverzeichnis kollidieren auch bei sauberer Pfadaufteilung — an
`uv.lock`, an `Makefile`, an der Zeilenzählung. Je Paket ein eigener Zweig
oder ein eigenes Worktree, Zusammenführung an der Wellengrenze.

**Kein Paket ändert Zahlen.** Puffer, Schwellwerte, Klassifikationen bleiben,
wie sie sind — auch wo sie fragwürdig aussehen. Wer beim Umbau eine
fachliche Auffälligkeit findet, schreibt sie auf und ändert sie nicht. Sonst
ist am Ende nicht mehr unterscheidbar, ob eine Abweichung Umbau oder Absicht
war.

## Eine Annahme, die nicht stimmte: Hardlinks blockieren das Löschen nicht

Angenommen war, in `data/` dürfe erst gelöscht werden, wenn die Hardlinks
aufgelöst sind. Das ist falsch: `rm` entfernt nur einen Verzeichniseintrag,
der Inode überlebt, solange der zweite Name im Vorgängerprojekt existiert.
Gefährlich ist allein das Überschreiben an Ort und Stelle. Damit sind
Löschen (W1.2) und Auflösen (W1.3) voneinander unabhängig und laufen in
derselben Welle — die Abhängigkeit, die zuerst gesehen wurde, gibt es nicht.

## Grundlage

Plan vom 7. September 2026, abgeleitet aus dem belegten Datenflussgraphen
unter `docs/dataflow/` und dem Zielbild unter `docs/rewrite/zielbild.html`.
`umsetzung.html` in diesem Verzeichnis ist die interaktive Ansicht auf
denselben Plan; `packages.tsv` / `packages.json` sind die maschinenlesbare
Paketmatrix daraus (`src/extract_packages.py`). Noch nicht begonnen: kein
Paket angefangen, keine Datei außerhalb von `docs/` geändert.
