# White Paper: Hilfen

## Abbildungen veroeffentlichen

`make whitepaper` erzeugt die Abbildungen in `docs/whitepaper/abb/` (nicht versioniert).
`make abb-publish` laedt sie als Assets des festen GitHub-Releases `abbildungen-latest`
in `hurtjan/windkraft-oe-abschichtung` hoch (ueberschreibt, kein Verlauf; mit `manifest.json`
aus TIF-Stand, Commit und Datei-Hashes).

- `make abb-publish` ist ein Trockenlauf: zeigt Plan und `gh`-Befehle, veroeffentlicht nichts.
- `make abb-publish CONFIRM=1` fuehrt aus (Release anlegen/aktualisieren, Upload, veraltete Assets loeschen).
- Voraussetzung: `brew install gh` und `gh auth login`.
- Feste URL: `https://github.com/hurtjan/windkraft-oe-abschichtung/releases/download/abbildungen-latest/<datei>`
