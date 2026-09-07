#!/bin/bash
set -uo pipefail
cd /Users/jhurt/Documents/master_windkraft/abschichtung

OUT=docs/rewrite/nachweise/w13/vorgaenger_unversehrt.tsv
: > "$OUT"
printf 'zweitname\tsha256_vorher\tsha256_jetzt\tnlink_jetzt\tergebnis\n' >> "$OUT"

fail=0
while IFS=$'\t' read -r pfad groesse inode nlink sha zweitname; do
  if [ "$nlink" -lt 2 ] || [ -z "$zweitname" ]; then
    continue
  fi
  if [ ! -e "$zweitname" ]; then
    printf '%s\t%s\t%s\t%s\t%s\n' "$zweitname" "$sha" "FEHLT" "-" "FEHLER_DATEI_FEHLT" >> "$OUT"
    fail=1
    continue
  fi
  sha_now=$(shasum -a 256 "$zweitname" | awk '{print $1}')
  nlink_now=$(stat -f '%l' "$zweitname")
  ergebnis="ABWEICHUNG"
  if [ "$sha_now" = "$sha" ] && [ "$nlink_now" -eq 1 ]; then
    ergebnis="OK"
  else
    fail=1
  fi
  printf '%s\t%s\t%s\t%s\t%s\n' "$zweitname" "$sha" "$sha_now" "$nlink_now" "$ergebnis" >> "$OUT"
done < docs/rewrite/nachweise/w13/inventar_vorher.tsv

echo "fail=$fail"
echo "---summary---"
awk -F'\t' 'NR>1{c[$5]++} END{for(k in c) print k, c[k]}' "$OUT"
wc -l < "$OUT"
