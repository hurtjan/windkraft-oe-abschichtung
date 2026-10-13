# White Paper: Hilfen

## Erzeugte Dateien

`README.md` (Repo-Wurzel) und `docs/whitepaper/paper.md` werden von `make whitepaper` aus den
Vorlagen `readme_vorlage.md` und `paper_vorlage.md` erzeugt. Nur die Vorlagen bearbeiten, nie die
erzeugten Dateien. Platzhalter: `{{z:KEY|fmt}}` (Zahl aus `tabellen/zahlen.json`), `{{s:KEY}}`
(Text, z. B. `tif_sha12`), `{{tab:NAME}}` (Tabelle aus `tabellen/`). In `paper.md` zeigen
Bildlinks auf den Release `abbildungen-latest`, weil `abb/` nicht im Repo liegt.

Die Zahlen stammen aus dem TIF und dem Manifest. Die Abbildungen und die Zaehlung der
Natur-Ebenen (N1) nutzen zusaetzlich Aufbereitungsprodukte (Kataster, Adressregister,
UBA-Schutzgebiete) und OSM-Kacheln.

## Abbildungen veroeffentlichen

`make whitepaper` erzeugt die Abbildungen in `docs/whitepaper/abb/` (nicht versioniert).
`make abb-publish` laedt sie als Assets des festen GitHub-Releases `abbildungen-latest`
in `hurtjan/windkraft-oe-abschichtung` hoch (ueberschreibt, kein Verlauf; mit `manifest.json`
aus TIF-Stand, Commit und Datei-Hashes).

- `make abb-publish` ist ein Trockenlauf: zeigt Plan und `gh`-Befehle, veroeffentlicht nichts.
- `make abb-publish CONFIRM=1` fuehrt aus (Release anlegen/aktualisieren, Upload, veraltete Assets loeschen).
- Voraussetzung: `brew install gh` und `gh auth login`.
- Feste URL: `https://github.com/hurtjan/windkraft-oe-abschichtung/releases/download/abbildungen-latest/<datei>`
