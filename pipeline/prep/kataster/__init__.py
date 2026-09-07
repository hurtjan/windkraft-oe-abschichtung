"""Prep: Kataster (Paket W1.P2, docs/rewrite/PLAN.md §4/§7).

Zwei Stufen, weil die NÖ-Polygonisierung teuer ist und vom billigeren
Parquet-Export für die acht SHP-Bundesländer getrennt bleibt
(``pipeline.contract.PREP["kataster"]``, ein ``a_``/``b_``-Paar):

- ``a_noe_polygonize`` — liest ausschließlich die niederösterreichische
  DXF-Kette (``contract.RAW["kataster"]["noe_dxf_zip"]`` +
  ``symbol_csv``), rekonstruiert Polygone per Kachelung, Linienverschmelzung
  und NS-Symbol-Mehrheitsvotum und schreibt sie als eigenständiges
  GeoParquet nach ``contract.PREP["kataster"]["a_noe_polygonize"]``.
- ``b_export_parquet`` — liest die acht SHP-Archive der übrigen
  Bundesländer direkt aus ``contract.RAW["kataster"]`` sowie das Ergebnis
  von ``a_noe_polygonize`` (ohne es erneut zu berechnen) und vereinigt
  beides zum kombinierten Kataster-GeoParquet unter
  ``contract.PREP["kataster"]["b_export_parquet"]`` — Feldschema identisch
  zum bisherigen ``output/kataster/at_dkm_gst_nfl_epsg31287.geoparquet``.

``common.py`` enthält die von beiden Stufen geteilte Verarbeitungslogik
(NS-Symbol-Lookup, Geometriebereinigung, GeoParquet-Batch-Schreiber,
SHP-Verarbeitung), unverändert übernommen aus
``scripts/preprocessing/export_at_dkm_geoparquet.py`` (Umzug, siehe
PLAN.md §7 Spalte "Besitzt"). ``diagnostics.py`` ist der ebenfalls
verschobene, eigenständige Visualisierungs-/Diagnosepfad aus
``scripts/preprocessing/create_noe_dkm_polygon_fill_map.py`` — kein Teil
der GeoParquet-Erzeugung, aber Quelle der von ``a_noe_polygonize``
importierten reinen DXF-/Geometrie-Hilfsfunktionen (unverändert, nur der
Importpfad hat sich verschoben).

Kein Paket ändert Zahlen (PLAN.md §8 Regel 4): Puffer, Schwellwerte
(z. B. ``--noe-min-area-m2``) und Klassifikationslogik sind identisch zum
migrierten Code - siehe Bericht zu W1.P2 für fachliche Auffälligkeiten,
die dabei gefunden, aber bewusst nicht verändert wurden.
"""
