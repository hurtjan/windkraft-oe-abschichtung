# make/prep/ — Konvention für die Prep-Pakete

Vorpaket **W1.P0** (`docs/rewrite/PLAN.md` §13.4) hat dieses Verzeichnis
angelegt, damit die parallelen Prep-Pakete nicht alle
dieselbe Zeile im `Makefile` ändern müssen. Das `Makefile` liest
`make/prep/*.mk` per `-include` ein — getrennte Dateien statt mehrfacher
Änderungen an einer.

## Konvention

- Dein Make-Ziel heißt `prep-<domäne>` (z. B. `prep-admin`,
  `prep-kataster`, `prep-noe_sekrop`) und steht in
  `make/prep/<domäne>.mk` — sonst nirgends. `<domäne>` ist der
  Schlüsselname aus `pipeline.contract.RAW` bzw. `PREP`, also das
  Unterverzeichnis von `data/`, das deine Prep-Stufe liest.
- Deine Ausgabepfade stehen bereits in `pipeline/contract.py:PREP`
  (Paket W1.P0 und spätere Erweiterungen haben die Domänen dort erklärt) — importieren,
  nicht neu erklären. Beispiel:

  ```python
  from pipeline import contract
  out_dir = contract.PREP["admin"]
  ```

  `contract.PREP["<domäne>"]` ist flach (`derived/prep/<domäne>/`); die
  einzelnen Endprodukte stehen in `contract.PREP_FILES`, Zwischenstände
  und Caches gehören nach `contract.WORK["<domäne>"]` (`derived/work/`).
  Endprodukte: Vektor = GeoParquet EPSG:31287, Raster = GeoTIFF auf dem
  25-m-Zielgitter.
- `make prep` ruft am Ende alle vorhandenen `prep-*`-Ziele auf. Das
  geschieht automatisch über `PREP_TARGETS` im `Makefile` (aus den
  Dateinamen unter `make/prep/` abgeleitet) — du musst `prep:` selbst
  nicht anfassen, nur dein eigenes `prep-<domäne>:` deklarieren.
- Deklariere dein Ziel als `.PHONY` **in deiner eigenen Datei**, nicht im
  Haupt-`Makefile` (das trägt `PREP_TARGETS` bereits automatisch in
  `.PHONY` ein, schadet aber nicht, wenn du es zusätzlich in deiner
  Datei tust).

## Minimalbeispiel

Siehe `_beispiel.mk.txt` in diesem Verzeichnis — die Endung `.mk.txt`
(nicht `.mk`) ist Absicht: sie wird von `-include make/prep/*.mk` nicht
eingelesen, dient nur als Vorlage zum Kopieren.

```make
.PHONY: prep-admin
prep-admin:
	uv run python -m pipeline.prep.admin
```

## Warum diese Datei existiert

`docs/rewrite/PLAN.md` §13.4: Konflikte werden vorher verhindert, nicht
nachher aufgelöst. Ohne diese Konvention müsste jedes Paket sowohl
`pipeline/contract.py:PREP` als auch `Makefile` ändern — mehrfacher
Konflikt an je einer Stelle.
