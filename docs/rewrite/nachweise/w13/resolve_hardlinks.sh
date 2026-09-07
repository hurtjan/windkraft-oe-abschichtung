#!/bin/bash
# W1.3 -- Hardlinks unter data/ aufloesen.
# Verfahren: neue Datei danebenlegen (cp quelle->tmp), Pruefsumme vergleichen,
# dann per rename() (mv tmp->ziel) den Verzeichniseintrag ersetzen.
# Der alte Inode (und damit die Datei im Vorgaengerprojekt) wird dabei nie
# zum Schreiben geoeffnet.
set -euo pipefail

cd /Users/jhurt/Documents/master_windkraft/abschichtung

INVENTAR="docs/rewrite/nachweise/w13/inventar_vorher.tsv"
LOG="docs/rewrite/nachweise/w13/aufloesung_log.tsv"

: > "$LOG"
printf 'pfad\tvorher_sha256\tnachher_sha256\tergebnis\n' >> "$LOG"

while IFS=$'\t' read -r pfad groesse inode nlink sha zweitname; do
  if [ "$nlink" -lt 2 ]; then
    continue
  fi
  dir=$(dirname "$pfad")
  base=$(basename "$pfad")
  tmp="${dir}/.${base}.tmp.$$"

  # 1. neue Datei danebenlegen (liest quelle nur lesend, schreibt NUR die neue tmp-Datei)
  cp -p "$pfad" "$tmp"

  # 2. Pruefsumme VOR dem mv vergleichen
  tmp_sha=$(shasum -a 256 "$tmp" | awk '{print $1}')

  if [ "$tmp_sha" != "$sha" ]; then
    printf '%s\t%s\t%s\tFEHLER_PRUEFSUMME\n' "$pfad" "$sha" "$tmp_sha" >> "$LOG"
    echo "FEHLER: Pruefsumme stimmt nicht ueberein bei $pfad -- breche ab, mv wird NICHT ausgefuehrt." >&2
    rm -f "$tmp"
    exit 1
  fi

  # 3. Verzeichniseintrag ersetzen (rename, fasst alten Inode nicht an)
  mv "$tmp" "$pfad"

  printf '%s\t%s\t%s\tOK\n' "$pfad" "$sha" "$tmp_sha" >> "$LOG"
  echo "OK: $pfad"
done < "$INVENTAR"

echo "Fertig."
