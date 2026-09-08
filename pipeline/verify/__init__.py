"""Verify-Stufe der Kette (docs/rewrite/PLAN.md §3, §7 Pakete W4.1, W4.2).

Absichtlich fast leer: jedes der zwei Verify-Pakete legt hier seine eigene
Datei an (``dashboard.py``, ``gemeinden.py``) - genau eine Datei je Paket,
keine zwei Pakete teilen sich eine.

Diese ``__init__.py`` selbst ist von keinem der zwei Pakete "besessen"
(siehe PLAN.md §7, Spalte "Besitzt" - dort steht sie bei keinem). Ohne sie
vorab hätte jedes der zwei Pakete beim Anlegen seiner eigenen Datei diese
hier miterzeugen müssen: ein zweifacher "wer legt die Paketmarkierung an"-
Konflikt derselben Art, die Paket W4.P0 laut PLAN.md §13.10 (Regel 9)
vermeiden soll. Deshalb legt W4.P0 sie hier schon leer an - genau wie
W1.P0 es für ``pipeline/prep/__init__.py`` und W2.P0 es für
``pipeline/layers/__init__.py`` getan haben.
"""
