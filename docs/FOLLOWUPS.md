# Follow-ups aus der Übernahme

Der Umzug in dieses Repo war bewusst verhaltenserhaltend: jede Auffälligkeit,
jeder Bug und jede Altlast, die dabei auffiel, wurde hier festgehalten statt
sofort behoben. Ein Fix während des Umzugs wäre selbst eine
Verhaltensänderung gewesen und hätte den späteren numerischen Abgleich gegen
das alte Repo (`windkraft_ö_karten`) wertlos gemacht — der Abgleich muss
zeigen, dass neu und alt exakt dasselbe tun, nicht dass neu bereits besser
ist. Fixes gehören deshalb in eigene, spätere Commits mit eigener
Verifikation. Zeilennummern beziehen sich, sofern nicht anders vermerkt, auf
dieses Repo (`/Users/jhurt/Documents/master_windkraft/abschichtung`).

## Pfad-/Konfigurationsfragen

- `windkraft/config.py:22-26` löst Pfade relativ zum Config-Verzeichnis auf
  statt zum Repo-Root (`config_dir = path.parent`, dann `paths.*` relativ
  dazu). Sauberes Ziel: Resolver auf Repo-Root umstellen, dann `config.json`
  nach `config/` verschieben — eigener Commit, eigene Verifikation, nicht
  während des Umzugs. Stand jetzt: `config.json` liegt (wieder) im
  Wurzelverzeichnis (siehe `docs/MIGRATION_MAP.tsv`, Zeile mit der
  KORREKTUR-Anmerkung) — das war ein Rücksetzer auf den Altrepo-Zustand, kein
  Fix von `config.py` selbst. Die eigentliche Kopplung von Pfadauflösung an
  den Speicherort der Config-Datei besteht unverändert fort und ist damit
  weiterhin offen, falls `config.json` je wieder verschoben werden soll.

- `docs/analysis/streusiedlung_knee.py:53` — `from cluster_knee import (...)`.
  `cluster_knee.py` lag im alten Repo unter `windkraft/calc/cluster_knee.py`
  und wurde auftragsgemäß nach `docs/analysis/cluster_knee.py` verschoben,
  ist also kein Paketmodul mehr. Der Import funktioniert nur noch, weil
  Python beim Direktaufruf (`python docs/analysis/streusiedlung_knee.py`)
  automatisch das Skriptverzeichnis in `sys.path[0]` aufnimmt; bei jeder
  anderen Aufrufart (z. B. `python -m`, Import aus einem Test) läuft er ins
  Leere. Nicht gefixt: ein robuster Import wäre keine rein mechanische
  Änderung mehr.

- `windkraftzonen_shapefile_2024.json` und `zonierung_noe.json` haben
  dieselbe Byte-Länge (600.056), unterscheiden sich aber in 11 Bytes.
  Ungeklärt, welche Datei maßgeblich ist. Beide wurden übernommen; die Frage
  ist inhaltlich und darf nicht als Nebenprodukt eines Umzugs entschieden
  werden.

## Stille Fallbacks und Drift

- `windkraft/calc/kataster_layers.py:876` (Alt-Repo) fängt bei fehlendem
  `osmium-tool` den `CalledProcessError` und fällt still auf leere Masken
  (`np.zeros`) zurück. Nicht repariert, dokumentiert. Siehe auch
  `README.md` (Voraussetzungen) für die Konsequenz: ein Lauf ohne
  `osmium-tool` sieht erfolgreich aus, ist aber falsch.

- Die Checkpoints für Infra, Airport, Natur, Geografie und Zonierung tragen
  kein `SOURCE_FINGERPRINT`: neue Rohdaten invalidieren einen veralteten
  Checkpoint nicht, nur ein manuelles `--force-layers` tut das. Folge: ein
  Lauf kann still alte und neue Daten mischen und meldet trotzdem Erfolg.

## Altlasten im übernommenen Code

- `layer_color()` in `windkraft/viz/band_metadata.py` verweist byte-wörtlich
  noch auf die beim Ausdünnen entfernten Schlüssel
  `settlement_cluster_buffer` und `settlement_v2_buffer`. Für die aktuellen
  38 Bänder unerreichbar, aber ein Legacy-Name würde dort einen `KeyError`
  auslösen statt auf `FALLBACK_COLOR` zu fallen — eine Verhaltensänderung,
  die aus der angeordneten Ausdünnung folgt. Nicht angefasst, da der Auftrag
  das Trimmen ausdrücklich auf `DEFAULT_COLORS` beschränkte, `layer_color()`
  selbst aber byte-exakt verbatim bleiben sollte.

- `CATEGORY_TOTALS` in `windkraft/viz/band_metadata.py` trägt weiterhin alle
  acht Einträge aus der Altdatei, darunter vier Legacy-Namen des
  "vereinfachten Exports" (`tot_exclusion_human`, `tot_exclusion_nature`,
  `tot_exclusion_geography`, `tot_exclusion_all`), die im aktuellen
  38-Bänder-Schema nicht vorkommen. Harmlos (die Dict-Zugehörigkeitsprüfung
  greift für aktuelle Bänder nie), aber Kandidat für ein späteres Aufräumen,
  falls der Geltungsbereich von `band_metadata.py` je konsequent auf das
  Clean-Schema verengt wird.

- `windkraft/calc/distance_engine.py` — `fft_circle_dilation` bricht bei
  `tile_size <= 0` mit `SystemExit("--kataster-fft-tile-size must be
  positive")` ab: eine CLI-Fehlermeldung, fest eingebacken in eine
  ansonsten reine Zahlenfunktion. Byte-exakt wie im Altrepo übernommen; ein
  künftiges Aufräumen könnte hier ein einfaches `ValueError` mit
  bibliotheksgerechter Meldung erwägen, losgelöst vom alten
  Argparse-Flag-Namen.

- `windkraft/calc/distance_engine.py` — `fft_circle_dilation` protokolliert
  Fortschritt über `log(...)`, das auf einen modulweiten
  `START_TIME = time.perf_counter()` zurückgreift. Byte-exakt als echte
  Abhängigkeit mitübernommen (die Funktion ruft `log(...)` zweimal auf). Der
  Import von `distance_engine` startet damit seine eigene, vom Altmodul
  unabhängige Stoppuhr — folgenlos für die Berechnung selbst, betrifft nur
  das kosmetische Elapsed-Seconds-Präfix in Log-Zeilen, aber relevant, falls
  Log-Zeitstempel je zwischen alter und neuer Pipeline verglichen werden.

- `windkraft/calc/distance_engine.py` — `ns_kind`s numerisches Parsen
  (`str(int(float(ns_text)))`) akzeptiert stillschweigend ungewöhnliche, aber
  numerisch gültige Strings wie `"41.9"` → `"41"` (Trunkierung über `int()`)
  oder `"1e1"` → `"10"`. Unverändertes Altverhalten, hier nicht vertieft
  geprüft; Hinweis für den Fall, dass ein künftiger Aufrufer verrauschtere
  Daten liefert, als es die alte Kataster-Pipeline je tat.

- `tests/test_distance_engine_equivalence.py` vergleicht gegen das Alt-Repo
  unter absolutem Pfad und hört auf zu funktionieren, sobald dieses
  verschwindet. Verifikationsartefakt des Umzugs, kein dauerhafter
  Unit-Test — vor dem Abschalten des Alt-Repos bewusst entscheiden, was
  damit geschieht.

## Aufräumarbeiten

- `scripts/analysis/build_v2_dashboard_data.py:170-172` bricht am aktuellen
  TIF hart ab, weil `EXCLUSION_LAYERS` sieben Bandnamen aus dem
  Pre-Clean-Schema nennt. Wird durch das Band-Manifest adressiert (siehe
  `README.md`), aber das Skript selbst ist noch nicht angepasst.

- `windkraft/util/admin.py` (ganze Datei) wird von keinem übernommenen Modul
  importiert. Stand auf der Kopierliste, deshalb trotzdem übernommen — toter
  Code, Kandidat zum späteren Entfernen.

- `Makefile:2` — `CONFIG = config.json` (vor der Korrektur:
  `config/config.json`) wird von keinem der fünf `widmung-v2-*`-Targets
  benutzt, keines übergibt `--config`. Auftragsgemäß beibehalten statt
  gelöscht.

- `pyproject.toml:2` — `name = "windkraft"` bewusst NICHT auf `abschichtung`
  umbenannt, weil `uv.lock` (`source = { virtual = "." }`) den Projektnamen
  bindet; eine Umbenennung hätte die verbatim übernommene Lockfile entwertet
  und ein Re-Lock ausgelöst. Zielkonflikt zwischen gewünschtem neuem
  Projektnamen und verbatim übernommener Lockfile — menschliche Entscheidung
  nötig.

- `pyproject.toml:24-25` — `[project.scripts] windkraft =
  "windkraft.__main__:main"` zeigt ins Leere, `windkraft/__main__.py` wurde
  bewusst nicht übernommen. Folgenlos, solange das Projekt virtuell bleibt
  (kein Build), aber ein toter Entry-Point.

- `pyproject.toml:6-17` — Abhängigkeiten auftragsgemäß nicht getrimmt.
  Kandidaten für ein späteres Trimmen: `matplotlib` und `Pillow` werden von
  der eigentlichen v2-Kette nicht gebraucht (nur von Preprocessing- und
  `docs/analysis`-Skripten), `PyMuPDF` nur von `scripts/noe/`.

- `windkraft/calc/wind_zones.py:155` — `source_path =
  "output/steiermark_zonen/sapro2026/sapro2026_zonen.geojson"`. Erzeugt wird
  diese Datei im alten Repo von `scripts/analysis/extract_sapro2026_overview.py`
  bzw. `optimize_sapro2026_warp.py`; beide wurden nicht übernommen. Die
  Steiermark-SAPRO-2026-Zone hat in diesem Repo aktuell keinen Erzeuger.

- `windkraft/calc/abschichtung_common.py:967` (`power_path`) und
  `config.json` (`paths.powerlines_gpkg`) — `powerlines_gpkg` wird weiterhin
  gelesen, obwohl das daraus gebaute Band laut eigenem `_comment` seit dem
  Clean-Schema nicht mehr gespeichert wird. Toter Lesepfad, unverändert
  übernommen.

- `config.json` (`raster`-Block sowie `buffers.settlement` /
  `buffers.individual_objects`) — laut eigenen `_comment`-Feldern von der
  v2-Kette ignoriert; wirksam sind stattdessen `SETTLEMENT_BUFFER_BY_BL` /
  `INDIVIDUAL_BUFFER_BY_BL` in `windkraft/calc/abschichtung_common.py`. Die
  Legacy-Ketten, die diese Blöcke einst lasen, gibt es in diesem Repo nicht
  mehr — die Blöcke sind damit vollständig tot.

- `scripts/widmung_v2/03_build_osm_layers.py:232` und
  `scripts/widmung_v2/04_create_distance_zones.py:377` — Default
  `--osm-pbf-cache-dir output/abschichtung/osm_pbf_layers`, laut Hilfetext
  "geteilt mit create_osm_wka_distance_zones.py". Dieses Skript existiert in
  diesem Repo nicht; der Cache-Ordnername referenziert nur noch die
  Legacy-Kette im Altrepo.

- Veraltete Doku-/Kommentar-Verweise auf `scripts/main/` bzw. alte
  Dateinamen, die es in diesem Repo nicht mehr gibt — bewusst byte-identisch
  belassen, damit der spätere numerische Abgleich gegen die alte
  Implementierung sauber bleibt:
  `windkraft/calc/abschichtung_common.py:3,5,6,428`;
  `windkraft/calc/widmung_sources.py:6,22`;
  `windkraft/calc/hig_source_masks.py:3`; `windkraft/calc/wind_zones.py:6`;
  `scripts/widmung_v2/01_build_official_zoning_layers.py:3,4,18,38,41-46`;
  `scripts/widmung_v2/02_build_hig_sources.py:26,27,192-194`;
  `scripts/widmung_v2/03_build_osm_layers.py:6,36,109`;
  `scripts/widmung_v2/04_create_distance_zones.py:62-63,236`;
  `scripts/widmung_v2/05_validate.py:25,26`;
  `docs/widmung_v2_provenance.md:12,223,228,240,245,305,310,354,359,620-622`;
  `docs/analysis/streusiedlung_knee.py` (Run-Zeilen im Docstring).

- Kommentar zur ursprünglichen Commit-Nachricht der `distance_engine.py`-
  Extraktion: das alte Modul `kataster_layers.py` hat ca. 1303 LoC, nicht die
  an anderer Stelle kursierende Zahl "~1987 LoC" — jene Zahl bezog sich auf
  die von seinen unbedingten Modul-Imports mitgezogenen Ballast-Module
  (terrain/siedlung_method/util-admin) zusammengenommen, nicht auf die Datei
  selbst. Nur hier vermerkt, keine Code-Änderung.

## ⚠️ Datenmigration per Hardlink — Schreibzugriff auf `data/` verändert das Alt-Repo

**`data/` und die übernommenen `output/`-Artefakte sind per Hardlink mit
`windkraft_ö_karten` verbunden; ein In-place-Schreibzugriff auf eine dieser
Dateien verändert auch das Alt-Repo. Solange das Alt-Repo als Sicherheitsnetz
dient, darf in `data/` ausschließlich gelesen werden; neue oder ersetzte
Dateien müssen neu angelegt statt überschrieben werden.**

Konkret gefundene Gefahrenstelle (nicht gefixt, nur dokumentiert): die
Widmung-v2-Kette schreibt unter genau einer Bedingung standardmäßig in
`data/` hinein. `windkraft/calc/bev_register.py` (`load_address_points`,
`load_building_points`) legt einen Parquet-Cache unter
`(cache_dir or data_dir) / ADDRESS_CACHE_NAME` bzw. `.../BUILDING_CACHE_NAME`
per `to_parquet()` an — ein In-place-Schreibzugriff, kein Neuanlegen unter
neuem Namen. `scripts/widmung_v2/02_build_hig_sources.py:199` setzt
`--cache-dir` standardmäßig auf `data/adressregister` (identisch mit
`--address-dir`). Solange die per Hardlink übernommenen Caches
(`adressen_31287.parquet`, `bev_gebaeude_31287.parquet`) vorhanden bleiben
und `rebuild=False` (Default) gilt, liest der Code nur — schreibt aber genau
dann in die Hardlink-Datei hinein (und damit ins Alt-Repo), wenn einer der
beiden Caches fehlt, gelöscht oder mit `rebuild=True`/einem expliziten
`--cache-dir data/adressregister`-Aufruf neu gebaut wird. Sonst wurde bei
dieser Prüfung kein weiterer Schreibzugriff der Referenzkette auf `data/`
gefunden (`windkraft/calc/widmung_sources.py::_ensure_ktn_gpkg` und die
OSM-PBF-Caches in `abschichtung_common.py` schreiben beide unter
`output/…`, nicht unter `data/…`). Sauberer Fix (nicht während der
Migration umgesetzt): `--cache-dir` in `02_build_hig_sources.py` auf einen
Pfad unter `output/` umstellen, damit `data/` beschreibungsgemäß
ausschließlich Lesezugriffe sieht.

## Vergleichstests gegen das Alt-Repo

- `tests/test_distance_engine_equivalence.py` vergleicht gegen ein zweites
  Repo, das ebenfalls ein Top-Level-Paket `windkraft` definiert. Der Test
  sichert und restauriert deshalb `sys.modules` um den Import der
  Alt-Implementierung herum. Ohne das löst deren eigenes
  `from windkraft.calc... import ...` gegen das bereits importierte **neue**
  Paket auf — der Test vergleicht dann neu gegen neu und ist grün, ohne
  etwas zu prüfen. Wer einen weiteren Vergleichstest schreibt, muss dieselbe
  Vorkehrung treffen.

## Schreibziel-Audit über die migrierte Kette (`windkraft/`, `scripts/`, `Makefile`, `config.json`)

Vollständige Erfassung aller Schreibziele der migrierten Kette (Job 2, im
Anschluss an den `bev_register.py`-Fix aus Job 1). Ursprüngliches Kriterium
war „schreibt unter `data/`?“; das griff zu kurz, weil `output/kataster/`
und `output/noe/` ebenfalls per Hardlink mit `windkraft_ö_karten` geteilt
sind. Maßgeblich ist deshalb **nicht das Verzeichnis, sondern der Link-Count**
der tatsächlich getroffenen Datei. Ermittelt per
`find data output -type f -links +1` (rein lesend) im Ziel-Repo, 68 Treffer.

Die Tabelle ist so sortiert, dass die **Schnittmenge aus Schreibziel und
Hardlink-Liste ganz oben steht** — das sind die scharfen Waffen: ein einziger
Lauf kürzt dort den geteilten Inode und beschädigt beide Repos gleichzeitig,
ohne Fehlermeldung. Danach folgt alles außerhalb der Schnittmenge, dokumentiert
aber nicht angefasst.

| Datei:Zeile | Schreibziel | Auslösebedingung | Risiko | hardgelinkt? |
|---|---|---|---|---|
| `scripts/noe/extract_noe_vector_layers.py:251-252` (`export_layer`) | `output/noe/pdf_750m_{geb,gwr,gruenland_widmung}.geojson` (+ `_wgs84`-Geschwister, diese nicht hardgelinkt) | **jeder Lauf** von `extract_noe_vector_layers.py` — kein Overwrite-Schutz im Code | Überschreibt beim ersten Lauf drei geteilte Dateien; kürzt den gemeinsamen Inode in beiden Repos gleichzeitig, ohne Fehlermeldung | **ja** (3 von 6 Zieldateien) |
| `windkraft/noe/pdf_hig_sources.py:101-102` (`derive_layer_files`, aufgerufen aus `extract_noe_vector_layers.py:286` und `scripts/noe/derive_pdf_hig_sources.py:28`) | `output/noe/pdf_hig_source_{geb,gwr,gruenland_widmung}.geojson` (+ `_wgs84`) | **jeder Lauf** eines der beiden aufrufenden Skripte — kein Overwrite-Schutz | wie oben | **ja** (3 von 6) |
| `scripts/noe/align_pdf_shapefile.py:174` (Default-Ziel: `OUT = Path("output/noe")` Z.31, `DEFAULT_OUT_JSON` Z.36) | `output/noe/alignment_mindestabstand.json` | nur mit explizitem `--overwrite` — das Skript selbst bricht sonst per `SystemExit` ab, wenn die Zieldatei existiert (Z. 54-58, bereits vorhandener Schutz im Code) | mit `--overwrite`: echter In-place-Schreibzugriff auf die Hardlink-Datei | **ja** (durch bestehenden Schutz entschärft, aktiv nur bei explizitem Flag) |
| `scripts/preprocessing/export_at_dkm_geoparquet.py:262` (`GeoParquetBatchWriter.__init__` → `pq.ParquetWriter`); Default `output_path` Z. 65/895 | `output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet` | nur mit explizitem `--overwrite` — `main()` bricht sonst per `SystemExit` ab, wenn `output_path` existiert (Z. 923-925, bereits vorhandener Schutz im Code) | mit `--overwrite`: In-place-Schreibzugriff auf die Hardlink-Datei | **ja** (entschärft, aktiv nur bei explizitem Flag) |
| `windkraft/calc/bev_register.py:113-141` + `scripts/widmung_v2/02_build_hig_sources.py:199` | *(vor Fix)* `data/adressregister/{adressen_31287,bev_gebaeude_31287}.parquet` | *(vor Fix)* `rebuild=True` (das war zuvor sogar der effektive Default über `--cache-dir data/adressregister`) oder explizites `--cache-dir data/adressregister` | *(vor Fix)* In-place-Schreibzugriff auf zwei Hardlink-Dateien | war **ja** — **GEFIXT in Job 1** (Commit `8054844`): Default-Schreibziel jetzt `output/adressregister_cache`, bestehender Legacy-Cache unter `data/adressregister` bleibt lesbar. Für den Standardfall jetzt **nein**; **ja** bleibt es nur bei weiterhin explizitem `--cache-dir data/adressregister` (bewusst nicht verändertes Verhalten, siehe Job-1-Bericht) |
| `windkraft/calc/widmung_sources.py:387-394` (`_ensure_ktn_gpkg`) | `output/abschichtung_widmung_v2/zoning_vectors/_cache/flawi_ktn_gpkg.gpkg` (Default über `01_build_official_zoning_layers.py:122,131`) | jeder Lauf ohne vorhandenen Cache | schreibt eine neue Datei in einem neuen Output-Verzeichnis | nein |
| `windkraft/calc/abschichtung_common.py:457,489` (`pbf_for_bounds`, `osm_layer_path`) | `output/abschichtung/osm_pbf_layers/*.osm.pbf`, `*.geojsonseq` (Default über `03_build_osm_layers.py:232`, `04_create_distance_zones.py:379`) | jeder Lauf ohne Cache-Treffer | neue Dateien in neuem Output-Verzeichnis | nein |
| `windkraft/calc/abschichtung_common.py:1443-1444` (`write_layer`) und `:1487,1578` (`compose_exclusion_geotiff`/`output_profile`) | `output/abschichtung_widmung_v2/distance_layers/*.tif`, `output/abschichtung_widmung_v2/osm_wka_distance_zones_widmung_v2.tif` (Default über `--layer-dir`/`--output` in `02..05_*.py`) | jeder Pipeline-Lauf | neuer Output-Baum | nein |
| `windkraft/calc/band_manifest.py:516-517` (`write_band_manifest`) | `<tif-stem>.bands.json` neben `args.output` (`output/abschichtung_widmung_v2/...tif`) | jeder Lauf von `04_create_distance_zones.py` | neuer Output-Baum | nein |
| `scripts/widmung_v2/01_build_official_zoning_layers.py:113-114` (`write_bucket`) | `output/abschichtung_widmung_v2/zoning_vectors/*.gpkg` (Default `--out-dir`) | jeder Lauf | neuer Output-Baum | nein |
| `scripts/widmung_v2/02_build_hig_sources.py:173-174` | `output/abschichtung_widmung_v2/{HULL_GPKG_NAME}` (Default `--out-dir`) | jeder Lauf ohne `--skip-gpkg` | neuer Output-Baum | nein |
| `scripts/analysis/build_v2_dashboard_data.py:330-331` | `output/abschichtung_widmung_v2/dashboard_data.json` (Default `--out`) | jeder Lauf | neuer Output-Baum | nein |
| `scripts/webmap/build_layer_viewer.py:262,326` (+ `mkdir` Z. 87,282) | `output/abschichtung/viewer/{index.html,manifest.json}` (Default `--output`) | jeder Lauf | neuer Output-Baum | nein |
| `scripts/preprocessing/export_at_dkm_geoparquet.py:399,424` (`extract_layer_shapefiles[_from_members]`) | System-Temp via `tempfile.TemporaryDirectory(dir=args.temp_dir)`, Default `None` | jeder Lauf | System-Temp, außerhalb von `data/`/`output/` | nein |
| `scripts/preprocessing/export_at_dkm_geoparquet.py:797` (Summary-CSV) und `:889` (Overview-MD) | `output/kataster/at_dkm_gst_nfl_epsg31287_{summary.csv,overview.md}` (Default `DEFAULT_SUMMARY_CSV`/`DEFAULT_OVERVIEW_MD`) | nur mit explizitem `--overwrite` bei vorhandener Datei, sonst Erstanlage (gleicher Schutz wie Z. 262) | Erstanlage unkritisch; Überschreiben nur eigener, nicht hardgelinkter Dateien | nein (nicht in der Hardlink-Liste) |
| `scripts/preprocessing/create_noe_dkm_polygon_fill_map.py:561-563` (`write_bounds_cache`) | `output/kataster/diagnostics/noe_dkm_bounds_*.csv` (Default `--bounds-cache`) | jeder Lauf mit Bounds-Cache | neues, nicht hardgelinktes Diagnose-Verzeichnis | nein |
| `scripts/preprocessing/create_noe_dkm_polygon_fill_map.py:1278,1352,1385,1900,1903` | `output/kataster/diagnostics/{output_prefix}_*.{png,csv}` (Default `--output-prefix`, `OUT_DIR` Z. 53) | nur mit `--diagnostics`/`--boundary-diagnostics` | neues, nicht hardgelinktes Diagnose-Verzeichnis | nein |
| `scripts/noe/align_pdf_shapefile.py:253` (`fig.savefig`) | `output/noe/alignment_check_pdf_vs_shapefile.png` (neben `args.out`) | jeder Lauf | neue, nicht hardgelinkte Datei | nein |

**OPEN QUESTIONS (Schnittmenge, nicht gefixt):**

1. **`extract_noe_vector_layers.py` / `pdf_hig_sources.py` (Zeilen 251-252 bzw. 101-102).**
   Dies sind die einzigen zwei Treffer in der Schnittmenge **ohne jeden
   bestehenden Schutz** — sie schreiben bei jedem Lauf bedingungslos. Trotzdem
   nicht gefixt, weil kein minimaler, eindeutig verhaltensneutraler Patch
   existiert: `output/noe` ist in dieser Mini-Kette (`align_pdf_shapefile.py`
   schreibt `alignment_mindestabstand.json` → `extract_noe_vector_layers.py`
   liest es über die fest verdrahtete Konstante `ALIGN_PATH` und schreibt
   `pdf_750m_*.geojson` in dasselbe Verzeichnis → `pdf_hig_sources.py` liest
   genau diese Dateien aus demselben Verzeichnis zurück und schreibt
   `pdf_hig_source_*.geojson` wieder dorthin) sowohl Lese- als auch
   Schreibziel für mehrere Stufen, jeweils über fest verdrahtete
   Pfadkonstanten in drei verschiedenen Dateien (`ALIGN_PATH`, `OUT_DIR`
   zweimal, `DEFAULT_OUT_JSON`). Eine reine Schreibziel-Verlegung (wie bei
   `bev_register.py`) würde die Downstream-Lesepfade brechen, wenn sie nicht
   koordiniert mitgeändert wird — und ein Legacy-Fallback wie bei
   `bev_register.py` ("existierende Datei am alten Ort weiter lesen") ist
   hier nicht so einfach zu bauen, weil dieselben Dateien innerhalb *eines*
   Laufs sowohl frisch geschrieben als auch sofort wieder gelesen werden.
   Alternative wäre ein reiner Overwrite-Schutz nach dem Vorbild von
   `align_pdf_shapefile.py`/`export_at_dkm_geoparquet.py` — das ändert aber
   nicht nur das Schreibziel, sondern fügt neues Abbruch-Verhalten hinzu, was
   über den erlaubten Minimal-Fix hinausgeht. Empfehlung: menschliche
   Entscheidung, welche der beiden Strategien (koordinierte Verlegung aller
   drei Pfadkonstanten inkl. Legacy-Fallback, oder Overwrite-Schutz
   ergänzen) gewünscht ist.
2. **`align_pdf_shapefile.py:174` und `export_at_dkm_geoparquet.py:262`.**
   Beide haben bereits einen eingebauten Schutz (`SystemExit`, falls Ziel
   existiert und `--overwrite` fehlt) — der Standardlauf ist damit sicher,
   das Risiko besteht nur bei explizitem `--overwrite`. Das ist strukturell
   dasselbe Restrisiko, das Job 1 bei `bev_register.py` für ein explizites
   `--cache-dir data/adressregister` bewusst unangetastet gelassen hat
   (explizite Nutzer-Übersteuerung, keine Default-Gefahr). Aus Konsistenz
   dazu ebenfalls nicht gefixt. Zusätzlich hängt `export_at_dkm_geoparquet.py`
   an einer Verkettung: sein Default-Output wird in
   `02_build_hig_sources.py:197` (`--dkm-parquet`) als Default-Leseziel exakt
   wiederverwendet — eine Verlegung des Schreibziels müsste diesen zweiten
   Ort mit ändern, sonst liest die Widmungs-v2-Kette künftig ins Leere. Auch
   hier: menschliche Entscheidung statt Rateversuch.

**Hinweis (kein aktiver Schreibpfad, nur zur Vollständigkeit):** Die
Hardlink-Liste enthält sechs weitere `output/noe/alignment_*.json`-Dateien
(`industrieviertel`, `landschaftsraum`, `mostviertel`, `naturschutz`,
`waldviertel`, `weinviertel`). Keines der migrierten Skripte schreibt sie —
laut Kommentaren in `windkraft/noe/pdf_align.py:29` und `:41` stammen sie von
Alignment-Skripten (`align_naturschutz.py`, `combine_all_layers.py`), die
(noch) nicht in dieses Repo migriert wurden. Sollten sie migriert werden,
gilt für sie exakt dieselbe Gefährdung wie für `alignment_mindestabstand.json`
oben.

### Rechte/`chflags` schützen `data/` NICHT

Rechte und `chflags` taugen **nicht** als Schutz für `data/`. Beide hängen am
Inode, nicht am Verzeichniseintrag: ein `chmod -w` oder `uchg` im neuen Repo
würde dieselben Dateien auch im Alt-Repo schreibgeschützt machen und dessen
eigene Läufe brechen. Umgekehrt schützt ein schreibgeschütztes Verzeichnis
nicht vor dem Überschreiben bestehenden Dateiinhalts, weil Verzeichnisrechte
nur das Anlegen und Entfernen von Einträgen steuern. Der einzige wirksame
Schutz ist, dass kein Code unter `data/` schreibt.

Ergänzend, aus der Hardlink-Prüfung dieses Audits: dieselbe Überlegung gilt
für `output/kataster/` und `output/noe/`, weil auch dort einzelne Dateien per
Hardlink geteilt sind (siehe Tabelle oben) — Rechte/`chflags` auf
Verzeichnisebene schützen auch dort nicht vor In-place-Überschreiben der
betroffenen Dateien.

**Grundregel für künftige Migrationen:** Jede Datei, die irgendein Codepfad
schreiben kann, ist eine echte Kopie — nie ein Hardlink. Unabhängig von
Größe, Verzeichnis und davon, ob im Code ein Guard existiert. Ein Artefakt,
das die Kette selbst schreibt, darf nie hardgelinkt sein — sonst wird aus
einer harmlosen Neuberechnung ein stiller Doppel-Schaden. Die in der
Tabelle oben als „hardgelinkt: ja" markierten `output/`-Dateien (drei
`pdf_750m_*`, drei `pdf_hig_source_*`, `alignment_mindestabstand.json`,
`at_dkm_gst_nfl_epsg31287.geoparquet`) waren laut dieser Regel fehlerhaft
verlinkt — inzwischen behoben, siehe Abschnitt unten.

## Regel: die Hardlink-Invariante

**Jede Datei, die irgendein Codepfad schreiben kann, ist eine echte
Kopie — nie ein Hardlink. Unabhängig von Größe, Verzeichnis und davon, ob
ein Guard existiert.** Quelldaten unter `data/`, die die Kette
ausschließlich liest, bleiben davon unberührt: per Hardlink mit
`windkraft_ö_karten` verbunden ist für sie richtig, kostet keinen Speicher.
Ein Schreibvorgang auf eine hardgelinkte Datei kürzt den geteilten Inode
und zerstört dieselbe Datei im Alt-Repo im selben Moment, ohne
Fehlermeldung.

Die Vorgängerformulierung dieser Regel lautete „Eingaben hardlinken,
Ausgaben kopieren" — schwächer, und auf eine Art, die den eigentlichen
Fehler verdeckt hat: sie verlangt eine **Einordnung** (Eingabe oder
Ausgabe?), und genau diese Einordnung schlug fehl, obwohl sie korrekt war.
Die betroffenen `output/`-Dateien und die Adressregister-Parquet-Caches
unter `data/adressregister/` wurden zu Recht als „Artefakte, die (auch)
gelesen werden" eingestuft — sie werden tatsächlich als Zwischenergebnis
bzw. Cache gelesen. Nur schreibt dieselbe Kette eben auch in sie hinein.
Eine Regel, die bei einer korrekten Einordnung trotzdem zum falschen
Ergebnis führt, ist die falsche Regel. Die neue Formulierung braucht keine
Einordnung mehr, nur eine mechanisch prüfbare Tatsache: den Link-Count.

**Bekannter Verstoß — behoben.** Während der Migration wurden mehrere
echte Ketten-Ausgaben per Hardlink statt per Kopie übernommen: alle
Dateien unter `output/noe/` (13 Stück — die 7 tatsächlichen Schreibziele
aus der Tabelle oben sowie 6 weitere `alignment_*.json`, die aktuell zwar
von keinem migrierten Skript geschrieben werden, aber unter demselben
Verzeichnis liegen und derselben Invariante unterliegen), das Geoparquet
unter `output/kataster/` (`at_dkm_gst_nfl_epsg31287.geoparquet`,
≈ 5,0 GB) sowie die beiden Adressregister-Caches unter
`data/adressregister/` (`adressen_31287.parquet`,
`bev_gebaeude_31287.parquet`). Alle 16 Dateien sind jetzt echte Kopien:
per `cp`/`mv` neu angelegt (nie in die bestehende Datei hineingeschrieben,
das hätte den geteilten Inode gekürzt), Link-Count 1, eigener Inode,
Inhalt byteidentisch zum Alt-Repo geprüft (`cmp`). Das Alt-Repo ist davon
unberührt — sein eigener Link-Count auf dieselben Dateien ist ebenfalls
auf 1 zurückgefallen. `tools/check_hardlink_safety.py`
(`make check-hardlinks`) weist die Invariante jetzt mechanisch nach: kein
File unter `output/` darf Link-Count > 1 haben (Regel A, ausnahmslos), und
eine explizit deklarierte Liste bekannter Schreibziele unter `data/`
(aktuell die beiden Adressregister-Caches) muss Link-Count 1 haben
(Regel B). Damit hängt die Prüfung nicht mehr an einer Einordnung, die
wieder falsch liegen könnte.
