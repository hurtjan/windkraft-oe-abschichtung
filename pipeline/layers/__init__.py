"""Layer-Stufe der Kette (docs/rewrite/PLAN.md §3, §7 Pakete W2.1, W2.3, W2.4).

Absichtlich fast leer: jedes der drei Layer-Pakete legt hier seine eigene
Datei an (``hig.py``, ``osm.py``, ``geo.py``) - genau eine Datei je Paket,
keine zwei Pakete teilen sich eine.

Diese ``__init__.py`` selbst ist von keinem der drei Pakete "besessen"
(siehe PLAN.md §7, Spalte "Besitzt" - dort steht sie bei keinem). Ohne sie
vorab hätte jedes der drei Pakete beim Anlegen seiner eigenen Datei diese
hier miterzeugen müssen: ein dreifacher "wer legt die Paketmarkierung an"-
Konflikt derselben Art, die Paket W2.P0 laut PLAN.md §13.8 vermeiden soll.
Deshalb legt W2.P0 sie hier schon leer an - genau wie W1.P0 es für
``pipeline/prep/__init__.py`` getan hat.
"""
