# Nachweise W0.1 — Umbau von `data/`

Paket W0.1 hat die Verzeichnisstruktur unter `data/` umgeräumt (u. a.
`admin_boundaries/` → `admin/`, lose Rasterdateien in Unterordner wie
`gelaende/` verschoben) und anschließend die Pfade in `config.json` und im
Code nachgezogen. Die sechs Dateien in diesem Ordner sind die Belege dafür,
dass dieser Umbau **folgenlos** war: keine Datei verloren, keine Datei
verändert, keine tote Pfadreferenz übrig.

## Die Dateien

**`inventar_vorher.tsv`** und **`inventar_nachher.tsv`**
Vollständiges Inventar von `data/` vor bzw. nach dem Verschieben, je eine
Zeile pro Datei. Spalten: `pfad` (relativ zum Repo-Root), `groesse_bytes`,
`inode`, `linkcount`, `sha256` (Prüfsumme; bei Dateien über 50 MB leer, siehe
`verifikation.txt`). Erzeugt durch Durchlaufen von `data/` mit `find` +
`stat` + `sha256sum`, einmal vor und einmal nach dem `git mv`.

**`verifikation.txt`**
Die Auswertung der beiden Inventare: Dateizahl, Inode-Erhaltung, Linkcount-
Konstanz, sha256-Gleichheit (für die Dateien unter 50 MB) und Gesamtgröße,
jeweils vorher gegen nachher. Alle fünf Prüfungen sind bestanden (56 von 56
Dateien, identische Inodes, identische Prüfsummen, identische Gesamtgröße).
Das ist der eigentliche Befund: die Dateien selbst wurden nicht kopiert oder
neu geschrieben, sondern nur umbenannt/verschoben (gleiche Inode-Nummer
vorher wie nachher).

**`inode_abgleich.tsv`**
Bindeglied zwischen dem Inventar und den Pfaden, die in `config.json` und im
Code stehen. Spalten: `codestelle` (wo der Pfad referenziert wird),
`alter_pfad`, `neuer_pfad`, `inode_alt`, `inode_neu`, `gleich`. Zeigt für
jeden im Code verwendeten Pfad, ob der alte und der neue Pfad auf dieselbe
Datei (Inode) zeigen. Einträge mit `nicht_abbildbar` betreffen Pfade, die
schon vor dem Umbau nicht existierten (vorbestehende Lücken, kein Effekt des
Umbaus).

**`bandvergleich.tsv`**
Pixelgenauer Vergleich der Referenz-GeoTIFF (vor dem Umbau kopiert und
aufbewahrt) gegen das nach dem Umbau erzeugte Output-Raster, Band für Band.
Spalten: `band_nr`, `band_name`, `pixel_abs` (Anzahl abweichender Pixel),
`anteil_prozent` (Anteil an den in der Referenz gesetzten Pixeln),
`groesste_flaeche_ha` (größte zusammenhängende Abweichungsfläche). Erzeugt
mit `compare_bands.py` (nicht Teil dieses Nachweisordners). Alle 38 Bänder
zeigen `pixel_abs = 0`: der Kettenlauf nach dem Umbau produziert bit-für-bit
dasselbe Ergebnis wie vor dem Umbau.

**`pfadpruefung.py`**
Wegwerf-Prüfskript aus Paket W0.1b, **kein Werkzeug der Kette**. Es liegt
hier ausschließlich als Beleg dafür, was geprüft wurde, nicht zur
Wiederverwendung. Es prüft (1) jeden Wert im `paths`-Block von
`config.json` auf Existenz, (2) jede Codestelle mit einem funktionalen
Default-Pfad auf Existenz des dort gesetzten Werts, und (3) durchsucht alle
git-getrackten Dateien (ohne `.git/`, `docs/`, Scratchpad) nach Resten der
alten Verzeichnis-/Dateinamen. Der zugehörige Lauf fand keine Treffer.

## Zusammenfassung

Zusammen belegen die sechs Dateien: dieselben Dateien liegen nach dem Umbau
unter neuen Pfaden (Inode-Identität), die Konsumenten des Codes finden sie
dort auch (Pfadabgleich, Pfadprüfung), und die Kette rechnet mit den
umgezogenen Eingaben exakt dasselbe Ergebnis wie vorher (Bandvergleich). Der
Umbau von `data/` war damit strukturell und funktional folgenlos.
