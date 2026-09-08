# docs/dataflow — kanonischer Datenfluss-Graph

> **Eingefrorener Altstand — beschreibt die Kette vor dem Welle-6-Umbau,
> nicht den heutigen Baum.** Dieses Verzeichnis (Graph, Fragmente, die
> Erzeugungsskripte unter `src/` und ihre Ausgaben) ist ein aus dem
> **damaligen** Code erzeugter Befund über die **damalige** Kette
> (`scripts/` → `windkraft/` → `build/` → `output/`, `pipeline/verify/`
> statt `pipeline/export/`), Stand Commit `f1d00f7`
> (2026-09-08, „W5.P5: §13.9-Wächter auf Startknotensätze generalisiert,
> DKM-Ursache bekommt eigenen Wirkungspfad"). Mit Welle 6 heißen `scripts/`
> und `output/` nicht mehr so (archiviert), `windkraft/` ist `calc/`,
> `build/` ist `derived/`, `pipeline/verify/` ist `pipeline/export/`. Der
> Graph wird **nicht** neu erzeugt und **nicht** gelöscht — er bleibt als
> datierter Befund über den Vorzustand stehen, in derselben Rolle wie
> `docs/RUN1_VERGLEICH.md`. Wer den heutigen Datenfluss braucht, liest
> `pipeline/`, `calc/`, `derived/` direkt.
>
> **Nebenbefund:** `src/1_merge.py` bildet u. a. den Pfad
> `data/adressregister/…` ab (Zeilen 88–89) — dieses Verzeichnis gibt es
> seit Paket W0.1 nicht mehr (siehe `docs/rohdaten.md`). Da dieses
> Verzeichnis eingefroren bleibt, wird `1_merge.py` selbst nicht
> angepasst; dieser Kopf deckt den veralteten Pfad mit ab, statt das
> Skript zu ändern oder neu laufen zu lassen.

**Interaktive Ansicht:** [`flow_diagram.html`](flow_diagram.html) — lokal per
Doppelklick im Browser öffnbar, keine Abhängigkeiten und keine
Netzwerkzugriffe außer dem Nachladen der Google-Fonts-Stylesheets.
Veröffentlichte Fassung: https://claude.ai/code/artifact/3299cc50-4e57-4dc8-a4bd-22fecbe2beea
`flow_graph.json` ist die Quelle der Wahrheit; `flow_diagram.html` ist eine
daraus erzeugte Momentaufnahme — wer den Graphen ändert, muss das HTML neu
erzeugen.

Dieser Graph fasst sechs unabhängig erstellte Graph-Fragmente
(`frag_A_widmung` .. `frag_F_control`, siehe `flow_graph.json` -> `meta.fragments`)
zu einem einzigen, dedupliziertem Datenfluss-Graphen der Windkraft-Pipeline
zusammen. Erzeugt von `src/1_merge.py` (siehe Abschnitt „Neu erzeugen" unten).

**Schema v2** (`meta.schema_version: 2`, siehe `meta.fixed_at`): Die sechs
Fragment-Agenten hatten keine verbindliche Kantenrichtungs-Konvention — manche
notierten `reads` als script→datei, andere als datei→script. Dadurch mischten
sich in `in_degree`/`out_degree` Produzenten- und Konsumentenkanten, und die
darauf basierende `dead_end`-Erkennung markierte 164 von 220 Nodes als
Sackgasse — praktisch wertlos. Schema v2 normalisiert jede Kante auf echte
Datenflussrichtung, berechnet `producers`/`consumers` ausschließlich daraus
und ersetzt `dead_end`/`orphan_source`/`stub` durch aussagekräftigere Flags
(unten). Erzeugt von `src/2_normalize.py` (siehe Abschnitt „Neu erzeugen" unten).

**Skript/Modul-Grenze (ebenfalls Schema v2, `src/2_normalize.py`):** Ein Teil
der Datei-Ein-/Ausgabe findet nicht in den Skripten selbst statt, sondern in
Modulen des `windkraft`-Pakets, die von Skripten (oder von anderen Modulen —
die Delegation kann mehrere Ebenen tief sein) importiert werden. `imports`-
Kanten tragen bewusst `flow: false` (sie modellieren Codeabhängigkeit, keinen
Datenfluss); dadurch riss der Datenflusspfad bislang an der Modulgrenze ab:
Rohdatei → Modul → (Abbruch), obwohl das Modul die Daten im Auftrag des
importierenden Akteurs liest/schreibt. `2_normalize.py` schließt diese Lücke
systematisch durch abgeleitete `provides`-Kanten (siehe Abschnitt „Kanten“
unten, `derived: true`). Ohne diese Kanten erschienen z. B. das
BEV-Adressregister-ZIP und die steirischen SAPRO-2026-Zonen fälschlich als
Sackgassen, obwohl beide tatsächlich einen Layer bzw. das finale GeoTIFF
erreichen (siehe dortige Pfade unten).

## Was ist ein Node?

Ein Node ist eine Datei, ein Skript/Modul, ein Checkpoint-Layer (Zwischen-
Raster unter `output/.../distance_layers/*.tif`, id-Form `layer:<name>`),
ein Config-Key aus `config.json` (id-Form `cfg:paths.<key>`), ein
Make-Target (`make:<target>`) oder ein externes Kommandozeilen-Tool
(`bin:<name>`). Node-ids sind, wo sinnvoll, repo-relative Pfade ohne
führendes `./`.

Felder je Node (siehe `nodes.tsv` / `flow_graph.json`):

- `kind` — file | script | module | dir | layer | config_key | make_target | external | unknown
- `layer` — grobe Herkunftsklasse: code | raw | intermediate | output | config
- `stage` — Pipelinestufe: `stage0` (scripts/noe, scripts/preprocessing +
  deren Outputs), `stage1`..`stage5` (scripts/widmung_v2/01..05 + deren
  Outputs), `downstream` (webmap/analysis/docs), `control`
  (Makefile/config/pyproject/tools/tests), `input` (data/* und rollenidentische
  Referenzdateien, auch wenn sie ausnahmsweise unter `output/` liegen — siehe
  Notiz auf `output/steiermark_zonen/sapro2026/sapro2026_zonen.geojson`),
  `library` (windkraft/*), **neu in v2:** `legacy_v1` (Altlasten der
  v1-Pipeline: `output/abschichtung/osm_wka_distance_zones.tif`,
  `output/abschichtung/simplified_150w.tif`), `container` (reine
  Verzeichnis-/Junk-Nodes ohne eigene Pipelinerolle: `output`,
  `output/.DS_Store`, `output/abschichtung`, `output/abschichtung_widmung_v2`)
- `raw_class` — manual | derived_elsewhere | derived_in_repo | raw | code |
  unknown. Beschreibt die **Herkunft der auf der Platte liegenden Bytes**,
  nicht die theoretische Reproduzierbarkeit: `raw` = extern bezogen und
  unverändert (auch bei manuellem Downloadweg); `manual` = händisch erstellt,
  nicht reproduzierbar (kein Download möglich, z. B. `luca_zonen`); `code` =
  Config-Key/Skript, keine eigenständigen Daten-Bytes;
  `derived_in_repo` = von einem Skript dieses Repos erzeugbar UND die
  vorliegenden Bytes stammen tatsächlich aus einem Lauf hier;
  `derived_elsewhere` = die vorliegenden Bytes stammen aus einem anderen
  Projekt (typischerweise per Hardlink/Kopie aus `windkraft_ö_karten`
  migriert), auch wenn ein Erzeugerskript hier existiert. Bei den 41 (von
  ursprünglich 42) in Schema v2 aufgelösten Konflikten steht die Begründung
  in `notes` (Marker `RAW_CLASS-ENTSCHEIDUNG:`); der einzige verbliebene,
  wirklich unentscheidbare Fall steht weiter in `conflicts` in
  `flow_graph.json` (`data/WINDKRAFT_AUSSCHLUSSZONE.zip` — Herkunft laut
  `data/README.md` §3.1 vollständig unbelegt).
- `in_degree` / `out_degree` — Anzahl eingehender/ausgehender Kanten nach
  Dedup, **über alle Kantenarten** (inkl. `imports`/`depends` und nicht
  aufgelöster Kanten) — unverändert gegenüber Schema v1, NICHT
  flow-gefiltert.
- **neu in v2:** `producers` / `consumers` — NUR über Kanten mit `flow: true`
  berechnet (siehe Abschnitt „Kanten“): `producers` = Zahl eingehender
  `writes`-Kanten, `consumers` = Zahl ausgehender `reads`-Kanten. Das ist die
  eigentliche Produzenten-/Konsumentenzahl; `in_degree`/`out_degree` bleiben
  zum Vergleich stehen, sagen aber nichts über echten Datenfluss.
- `flags` — kommagetrennt, jetzt ausschließlich aus `producers`/`consumers`
  bzw. empirischen Befunden abgeleitet (ersetzt die v1-Flags
  `orphan_source`/`stub` vollständig; `dead_end` selbst kehrt unten in
  korrigierter, flow-basierter Form zurück):
  - `unused` — Datei-/Layer-Node mit `producers >= 1` und `consumers == 0`:
    etwas wird erzeugt, das niemand liest. Die eigentlichen Sackgassen.
  - `external_input` — Datei-/Layer-Node mit `producers == 0`,
    `consumers >= 1` und `raw_class` NICHT in `{raw, manual}`: ein
    Zwischenergebnis, das ohne erkennbaren Erzeuger in diesem Repo konsumiert
    wird (Kernfrage dieses Audits).
  - `true_raw` — wie `external_input`, aber `raw_class` IN `{raw, manual}`:
    ein echtes, unverändert konsumiertes Rohdatum.
  - `terminal_product` — deklariertes Endprodukt (siehe unten); kann
    gleichzeitig `unused` sein (wird erzeugt, aber bewusst nicht
    weiterverarbeitet) — in den Beispiel-Greps unten deshalb immer explizit
    von `unused` abgegrenzt.
  - `unreachable` — Skript-Node, der (a) transitiv von keinem `make:*`-Target
    über `invokes`/`depends`-Kanten erreicht wird UND (b) dessen sämtliche
    (flow-)Schreibziele `consumers == 0` haben (oder das Skript schreibt gar
    nichts). Deckt u. a. auf: es gibt kein `make test`-Target, alle
    `tests/*.py` sind daher strukturell `unreachable`.
  - `verified_dead` — empirisch durch Code-Lektüre belegter Totfund (siehe
    `notes`, Marker `FAKTENCHECK verified_dead:`), unabhängig von der
    strukturellen Grad-Berechnung. Kann auch auf Nodes mit `consumers >= 1`
    stehen, wenn die lesende Kante zwar existiert, der Code-Pfad aber laut
    Beleg nie erreicht wird (z. B. `data/osm_power_lines.gpkg`,
    `output/noe/pdf_hig_source_*.geojson`).
  - `dead_end` — **neu, korrigierte Rückkehr des v1-Konzepts:** generalisiert
    über `file`/`layer`/`module`/`script` (nicht nur Dateien): mindestens
    eine eingehende, aber keine ausgehende `flow: true`-Kante, kein
    `terminal_product`. Zählt für `file`/`layer` rechnerisch dasselbe wie
    `unused` (`producers>=1`, `consumers==0`); der Mehrwert liegt bei
    `module`/`script`-Nodes, für die es vor Einführung der `provides`-Kanten
    (siehe unten) keine Sackgassen-Bewertung gab. Anders als das v1-`dead_end`
    (unkorrigierte Kantenrichtung, 164/220 Nodes betroffen) ist dieses hier
    auf der korrigierten Flussrichtung berechnet und daher aussagekräftig.

Endprodukte (`terminal_product: true`, nie in der `unused`-Problemliste ohne
gesonderten Hinweis): das finale GeoTIFF
(`output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2.tif` UND
`..._run1.tif`), deren `.bands.json`,
`output/abschichtung_widmung_v2/hig_huellen.gpkg`, sowie alle Berichte unter
`docs/*.md` (`docs/FOLLOWUPS.md`, `docs/RUN1_VERGLEICH.md`,
`docs/widmung_v2_provenance.md`).

## Bekannte Modellgrenze: Referenzbänder ohne Checkpoint-Layer

Die meisten der 26 Bedingungsbänder im finalen GeoTIFF laufen über das
Checkpoint-Raster-Muster (`<layer_dir>/<name>.tif`, geschrieben/gelesen über
`windkraft/calc/abschichtung_common.py:1417-1447` `layer_path()`/
`write_layer()`/`layer_done()`) — dafür gibt es je Band einen eigenen
`layer:*`-Node im Pfad. Zwei Referenzbänder weichen davon ab: **Band 37**
(`layer:official_wind_zoning`, amtliche Windzonen) und **Band 38**
(`layer:wka_bestand_ausserhalb_zonen`, WKA-Bestand außerhalb amtlicher Zonen)
werden direkt und ausschließlich innerhalb von
`scripts/widmung_v2/04_create_distance_zones.py` gelesen UND geschrieben —
im Graphen als Selbstschleife dieses einen Skripts sichtbar (`reads`/`writes`
auf denselben `layer:*`-Node), nicht als mehrstufige Checkpoint-Kette. Eine
Quelle, die (wie `data/luca_zonen/*.shp`, `data/zonierung_noe.json`,
`data/WK_Eignungszonen.zip` oder
`output/steiermark_zonen/sapro2026/sapro2026_zonen.geojson`) nur eines dieser
beiden Referenzbänder speist, hat deshalb **keinen eigenen Checkpoint-`layer:`-
Node** zwischen sich und Stufe 4 im Pfad. Das ist eine bewusste Modellgrenze,
kein Fehler in der Inventur — eine solche Quelle darf **nicht allein deshalb**
als Sackgasse gelten, weil ihr Pfad "nur" über ein Modul (`windkraft/calc/
wind_zones.py` bzw. `windkraft/calc/widmung_sources.py`) direkt in Stufe 4
mündet, statt über einen dedizierten Zwischen-Layer zu laufen.

## Kanten

Eine Zeile in `edges.tsv` je (from, to, kind) nach Dedup. `evidence` bündelt
alle Belegstellen aus allen Quellfragmenten (`;`-getrennt, `[frag_X] ...`
präfixiert). `optional=true` nur wenn *alle* beitragenden Fragmente die Kante
als optional einstuften; widerspricht auch nur ein Fragment, gilt die Kante
als erforderlich.

**Neu in v2 — `flow` und `reversed`:**

- `flow: true` heißt: diese Kante zählt in `producers`/`consumers` der
  beteiligten Datei-/Layer-Nodes. Das gilt für genau drei Muster:
  `writes` script/module → datei (Produzent), `reads` datei → script/module
  (Konsument; **158 von 348 Kanten** lagen in den Fragmenten in der
  falschen Richtung script→datei und wurden umgedreht — siehe `reversed`),
  und `invokes` make_target → script — sowie, seit der Skript/Modul-Grenzen-
  Korrektur, `provides` (siehe unten).
- `flow: false` gilt für alle „echten" `imports`-Kanten (importierendes Modul →
  importiertes Modul — modelliert Codeabhängigkeit, keinen Datenfluss),
  alle `depends`-Kanten (Make-Target-Sequencing, pyproject-Abhängigkeiten),
  alle `invokes`-Kanten außerhalb des make_target→script-Musters (z. B.
  Skript ruft Funktion in anderem Modul, Skript ruft externes Binary), sowie
  `reads`/`writes`-Kanten, an denen ein `config_key`-Node beteiligt ist (die
  modellieren Config-Auflösung, nicht direkten Datenfluss — der eigentliche
  Datenfluss Datei→Skript liegt i. d. R. zusätzlich als eigene `reads`-Kante
  vor, z. B. `cfg:paths.dgm` neben `windkraft/calc/abschichtung_common.py
  reads data/DGM_R25.tif`).
- `reversed: true` — Kante wurde gegenüber der Fragment-Notation
  umgedreht, weil ihre tatsächliche Richtung aus den Node-`kind`s der
  Endpunkte (script/module vs. file/dir/layer) folgt, nicht aus der
  Fragment-Konvention. Betroffen: ausschließlich `reads`-Kanten
  (158 von 159 flow-fähigen `reads`-Kanten; die eine bereits korrekt
  notierte ist `output/noe/alignment_*.json → scripts/noe/extract_noe_vector_layers.py`).
  `writes` und `invokes` (make_target→script) waren in allen Fragmenten
  bereits einheitlich in Produzentenrichtung notiert, dort gab es nichts
  umzudrehen.
- **neu — `derived: true` (Kante `kind: "provides"`):** schließt die
  Skript/Modul-Grenzen-Lücke (siehe oben). Für jede `imports`-Kante
  Importeur → Modul `M` des `windkraft`-Pakets, bei der `M` selbst
  mindestens eine eigene `reads`/`writes`-Kante mit `flow: true` hat (also
  selbst Datei-I/O macht — nicht nur weiterimportiert), fügt
  `2_normalize.py` eine abgeleitete Gegenkante `M → Importeur` ein:
  `kind: "provides"`, `flow: true`, `derived: true`, `evidence` = Evidenz der
  zugrundeliegenden `imports`-Kante, `note: "abgeleitet: Modul liest/schreibt
  im Auftrag des importierenden Skripts"`. „Importeur" ist dabei nicht auf
  Skripte beschränkt: module→module-Importe (z. B. `abschichtung_common.py`
  importiert `wind_zones.py`) bekommen dieselbe Behandlung, weil die
  Delegation mehrere Modul-Ebenen tief reichen kann, bevor sie wieder in
  einem Skript "auftaucht" — ohne diese Verallgemeinerung würde der Pfad
  z. B. bei `wind_zones.py → abschichtung_common.py` erneut abreißen. Diese
  Kanten sind **klar als `derived: true` markiert** (Spalte `derived` in
  `edges.tsv`, Feld `derived` in `flow_graph.json`) — im Unterschied zu allen
  anderen, in den Fragmenten belegten Kanten (`derived: false`) — zählen aber
  genauso in `producers`/`consumers`/Flags-Berechnung ein wie belegte Kanten.
  Insgesamt **24 abgeleitete Kanten** (Stand siehe `meta.derived_edge_count`
  in `flow_graph.json`). Sie sind ausdrücklich keine neue Erhebung, sondern
  eine strukturelle Schlussfolgerung aus bereits vorhandenen Kanten
  (`imports` + die eigenen `reads`/`writes` von `M`) — bei Codeänderungen an
  den Modulgrenzen (neue Importe, neue Lese-/Schreibpfade in `windkraft/*`)
  aktualisieren sie sich automatisch mit einem erneuten Lauf von
  `2_normalize.py`, ohne dass eine neue Fragment-Erhebung nötig wäre.
- `flow_graph.json` → `direction_unresolved` (14 Einträge): Kanten der Art
  `reads`/`writes`, bei denen **beide** Endpunkte derselben Gruppe angehören
  (beide Datei/Layer oder beide Skript/Modul) — ein Inventurfehler der
  Fragment-Agenten, keine echte Produzent/Konsument-Kante. Meist Fälle, in
  denen ein Fragment einen Code-Import oder eine reine Dokumenten-Referenz
  fälschlich als `reads` notiert hat (z. B. `tests/test_band_manifest.py`
  „reads“ `windkraft/calc/band_manifest.py` — tatsächlich ein Import/Test,
  kein Datenfluss). Diese Kanten bleiben unverändert mit `flow: false`
  stehen.

## Beispiel-Greps

Alle echten Sackgassen (erzeugt, aber von niemandem gelesen — ohne die
bewusst unverarbeiteten Endprodukte):

    awk -F'\t' 'NR>1 && $10 ~ /(^|,)unused(,|$)/ && $10 !~ /terminal_product/' docs/dataflow/nodes.tsv

Alle „external_input“-Nodes (konsumiert, aber ohne Erzeuger in diesem Repo —
die Kernfrage dieses Audits):

    awk -F'\t' 'NR>1 && $10 ~ /(^|,)external_input(,|$)/' docs/dataflow/nodes.tsv

Alle unerreichbaren Skripte (kein Make-Target ruft sie, niemand liest ihre
Outputs):

    awk -F'\t' 'NR>1 && $10 ~ /(^|,)unreachable(,|$)/' docs/dataflow/nodes.tsv

Alle empirisch verifizierten Totfunde (Faktencheck, nicht nur strukturell):

    awk -F'\t' 'NR>1 && $10 ~ /verified_dead/' docs/dataflow/nodes.tsv

Alle abgeleiteten (nicht durch ein Fragment belegten) Kanten der
Skript/Modul-Grenzen-Korrektur:

    awk -F'\t' 'NR>1 && $6=="true"' docs/dataflow/edges.tsv

Alle umgedrehten Kanten (Fragment-Konvention war script→datei statt
datei→script):

    awk -F'\t' 'NR>1 && $5=="true"' docs/dataflow/edges.tsv

Alle Kanten, die NICHT in die Grade zählen (`flow=false` — Imports,
Sequencing, Config-Auflösung, Nicht-make_target-Invokes):

    awk -F'\t' 'NR>1 && $4=="false"' docs/dataflow/edges.tsv

Alle Inputs, die NICHT roh sind (also abgeleitet/unklar, obwohl unter
data/ bzw. mit stage=input):

    awk -F'\t' 'NR>1 && $4=="input" && $5!="raw" && $5!="manual"' docs/dataflow/nodes.tsv

Alle Leser einer bestimmten Datei (z. B. `data/DGM_R25.tif`) — nach der
Richtungsnormalisierung ist die Datei jetzt die Quelle, nicht das Ziel:

    awk -F'\t' 'NR>1 && $1=="data/DGM_R25.tif"' docs/dataflow/edges.tsv

Alle Nodes mit noch unaufgelöstem raw_class-Konflikt (nach Schema v2 nur
noch der eine wirklich unentscheidbare Fall):

    python3 -c "import json; d=json.load(open('docs/dataflow/flow_graph.json')); [print(c) for c in d['conflicts']]"

Alle Kanten mit ungeklärter Richtung (Inventurfehler der Fragmente, beide
Endpunkte derselben Gruppe):

    python3 -c "import json; d=json.load(open('docs/dataflow/flow_graph.json')); [print(u['kind'], u['from'], '<->', u['to']) for u in d['direction_unresolved']]"

Alle Kanten aus einem bestimmten Make-Target (z. B. `make:widmung-v2`):

    awk -F'\t' 'NR>1 && $1=="make:widmung-v2"' docs/dataflow/edges.tsv

## Neu erzeugen

Die gesamte Erzeugungskette liegt unter `src/` und läuft vom Repo-Wurzel-
verzeichnis aus, in dieser Reihenfolge:

    python3 docs/dataflow/src/1_merge.py
    python3 docs/dataflow/src/2_normalize.py
    python3 docs/dataflow/src/3_inject.py

`1_merge.py` liest die sechs Roh-Inventuren aus `src/fragments/`, dedupliziert
sie zu einem Graphen und schreibt `flow_graph.json` + `nodes.tsv` + `edges.tsv`
**+ ein generisches `README.md`** (v1-Baseline, ohne die manuell/agentisch
gepflegten Schema-v2- und Skript/Modul-Grenzen-Abschnitte dieser Datei hier)
— aber nur, wenn dort noch kein `README.md` liegt. `2_normalize.py` repariert
die Kantenrichtung, berechnet `producers`/`consumers` neu, fügt die
abgeleiteten `provides`-Kanten der Skript/Modul-Grenzen-Korrektur ein und
trägt die verifizierten Totfunde ein (Schema v2) — liest und schreibt
dieselben drei Dateien (nicht `README.md`). `3_inject.py` reduziert
`flow_graph.json` auf ein kompaktes Objekt, injiziert es in `src/template.html`
anstelle von `__GRAPH_JSON__` und schreibt das Ergebnis als eigenständige
HTML-Seite nach `flow_diagram.html`.

**Vormals eine Fußangel, jetzt entschärft:** `1_merge.py` überschrieb früher
`README.md` bei *jedem* Lauf bedingungslos mit seiner generischen
v1-Baseline-Fassung und hat dabei schon einmal diese handgepflegte Datei
zerstört — die Abschnitte „Schema v2“, „Skript/Modul-Grenze“, „Bekannte
Modellgrenze“ und die `derived`/`provides`-Dokumentation sind manuell/
agentisch nachgepflegt und wurden dabei jedes Mal gelöscht. Seither schreibt
`1_merge.py` `README.md` **nur noch, wenn die Datei nicht existiert**, oder
wenn ausdrücklich `python3 docs/dataflow/src/1_merge.py --write-readme`
aufgerufen wird. Ein normaler Kettenlauf lässt `README.md` also unangetastet
(`2_normalize.py` und `3_inject.py` fassten es ohnehin nie an).

Die Fragmente unter `src/fragments/` sind die eingefrorenen Roh-Inventuren
vom 7. September 2026 — eine Momentaufnahme des Codes zu diesem Zeitpunkt,
nicht des Codes selbst. Der Graph altert mit dem Code: Bei Codeänderungen im
Repo (neue/entfernte Skripte, geänderte Lese-/Schreibpfade, neue Make-Targets)
müssen die Fragmente neu erhoben werden, bevor die Kette erneut sinnvolle
Ergebnisse liefert — die drei Skripte allein aktualisieren nur die Ableitung,
nicht die zugrundeliegende Inventur.
