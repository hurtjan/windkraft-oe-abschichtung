# make/prep/ — Konvention für die neun Prep-Pakete

Vorpaket **W1.P0** (`docs/rewrite/PLAN.md` §13.4) hat dieses Verzeichnis
angelegt, damit die neun parallelen Prep-Pakete (W1.P1–W1.P9) nicht alle
dieselbe Zeile im `Makefile` ändern müssen. Das `Makefile` liest
`make/prep/*.mk` per `-include` ein — neun verschiedene Dateien statt
neun Änderungen an einer.

## Konvention

- Dein Make-Ziel heißt `prep-<domäne>` (z. B. `prep-admin`,
  `prep-kataster`, `prep-noe_sekrop`) und steht in
  `make/prep/<domäne>.mk` — sonst nirgends. `<domäne>` ist der
  Schlüsselname aus `pipeline.contract.RAW` bzw. `PREP`, also das
  Unterverzeichnis von `data/`, das deine Prep-Stufe liest.
- Deine Ausgabepfade stehen bereits in `pipeline/contract.py:PREP`
  (Paket W1.P0 hat alle neun Domänen dort vorab erklärt) — importieren,
  nicht neu erklären. Beispiel:

  ```python
  from pipeline import contract
  out_dir = contract.PREP["admin"]
  ```

  Bei den drei zweistufigen Domänen (`kataster`, `osm`, `noe_sekrop`)
  ist `contract.PREP["<domäne>"]` selbst ein dict mit den Schlüsseln
  `a_...`/`b_...` — siehe die Kommentare dort.
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
nachher aufgelöst. Ohne diese Konvention hätte jedes der neun Pakete
sowohl `pipeline/contract.py:PREP` als auch `Makefile` ändern müssen —
zwei garantierte neunfache Konflikte an je einer Stelle.
