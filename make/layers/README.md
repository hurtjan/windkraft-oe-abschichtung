# make/layers/ — Konvention für die drei Layer-Pakete

Vorpaket **W2.P0** (`docs/rewrite/PLAN.md` §13.8) hat dieses Verzeichnis
angelegt, damit die drei parallelen Layer-Pakete (W2.1, W2.3, W2.4) nicht
alle dieselbe Zeile im `Makefile` ändern müssen. Das `Makefile` liest
`make/layers/*.mk` per `-include` ein — drei verschiedene Dateien statt
drei Änderungen an einer. Genau dasselbe Muster wie bei `make/prep/` (siehe
`make/prep/README.md`) — nicht ähnlich, sondern dasselbe.

## Konvention

- Dein Make-Ziel heißt `layer-<domäne>` (z. B. `layer-hig`, `layer-osm`,
  `layer-geo`) und steht in `make/layers/<domäne>.mk` — sonst nirgends.
  `<domäne>` ist der Name deines Moduls unter `pipeline/layers/` ohne
  `.py` (also `hig`, `osm` bzw. `geo` — siehe `docs/rewrite/PLAN.md` §7,
  Spalte "Ort" für W2.1/W2.3/W2.4).
- Deine Checkpoint-Namen und -Pfade stehen bereits in
  `pipeline/contract.py:LAYERS` (33 Einträge, dort vorab erklärt) —
  importieren, nicht neu erklären. Beispiel:

  ```python
  from pipeline import contract
  out_path = contract.LAYERS["haeuser_im_gruenen"]
  ```

  Die Prep-Ausgaben, gegen die deine Layer-Stufe prüft, stehen ebenso
  bereits in `pipeline/contract.py:PREP` und liegen unter `build/prep/`
  (siehe `make/prep/README.md`).
- `make layers` ruft am Ende alle vorhandenen `layer-*`-Ziele auf. Das
  geschieht automatisch über `LAYER_TARGETS` im `Makefile` (aus den
  Dateinamen unter `make/layers/` abgeleitet) — du musst `layers:` selbst
  nicht anfassen, nur dein eigenes `layer-<domäne>:` deklarieren.
- Deklariere dein Ziel als `.PHONY` **in deiner eigenen Datei**, nicht im
  Haupt-`Makefile` (das trägt `LAYER_TARGETS` bereits automatisch in
  `.PHONY` ein, schadet aber nicht, wenn du es zusätzlich in deiner Datei
  tust).

## Minimalbeispiel

Siehe `_beispiel.mk.txt` in diesem Verzeichnis — die Endung `.mk.txt`
(nicht `.mk`) ist Absicht: sie wird von `-include make/layers/*.mk` nicht
eingelesen, dient nur als Vorlage zum Kopieren.

```make
.PHONY: layer-hig
layer-hig:
	uv run python -m pipeline.layers.hig
```

## Worktree: build/prep/ ist schon da

`make worktree PAKET=<dein-paket>` verlinkt seit W2.P0 auch `build/prep/`
in dein Worktree hinein (read-only, geteilt über alle Layer-Worktrees —
siehe die Warnung im `worktree`-Ziel selbst). Du musst die Prep-Stufe in
deinem Worktree also nicht neu rechnen, um gegen ihre Ausgaben zu prüfen.

## Warum diese Datei existiert

`docs/rewrite/PLAN.md` §13.8: Konflikte werden vorher verhindert, nicht
nachher aufgelöst. Ohne diese Konvention hätte jedes der drei Pakete
sowohl `pipeline/contract.py:LAYERS` als auch `Makefile` ändern müssen —
zwei garantierte Konflikte an je einer Stelle, genau wie bei den neun
Prep-Paketen zuvor (siehe `make/prep/README.md`).
