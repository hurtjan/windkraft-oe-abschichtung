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
