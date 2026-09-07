"""Prep-Stufe der Kette (docs/rewrite/PLAN.md §3, §7 Pakete W1.P1-W1.P9).

Absichtlich fast leer: jedes der neun Prep-Pakete legt hier seine eigene
Datei an (``admin.py``, ``adressen.py``, ``widmung.py``, ``terrain.py``,
``natur.py``, ``zonen.py`` bzw. die drei Unterpakete ``kataster/``,
``osm/``, ``noe/`` für die zweistufigen Domänen) - genau eine Datei je
Domäne, keine zwei Pakete teilen sich eine.

Diese ``__init__.py`` selbst ist von keinem der neun Pakete "besessen"
(siehe PLAN.md §7, Spalte "Besitzt" - dort steht sie bei keinem). Ohne sie
vorab hätte jedes der neun Pakete beim Anlegen seiner eigenen Datei diese
hier miterzeugen müssen: ein neunfacher "wer legt die Paketmarkierung an"-
Konflikt derselben Art, die Paket W1.P0 laut PLAN.md §13.4 vermeiden soll.
Deshalb legt W1.P0 sie hier schon leer an.
"""
