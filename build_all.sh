#!/usr/bin/env bash
# Pelna przebudowa linii od zera (zebra + lowpoly) i kontrola standardu. Wyniki: out/*.stl, out/_verify_report.json
# Czas ok. 10-15 min (siatki zebrowane ~ 0,35 mm voxel). Dowolny krok mozna uruchomic osobno.
set -euo pipefail
cd "$(dirname "$0")"
python3 build_figurki.py            # korpus_bazowy, krolik_calosc, renifer_calosc, ucho_*, poroze_*
python3 build_pumpkin.py            # dynia_korpus, dynia_korpus_platy, dynia_ogonek
python3 build_snowman.py            # balwan, balwan_nos, balwan_miotla
python3 build_egg.py                # jajko_miseczka, jajko_czapka_gniazda, jajko_czapka_uszy
python3 build_dlugie.py             # ucho_dlugie_*, jajko_czapka_uszy_dlugie
python3 ears_A.py                   # ucho_{mis,kot,lis,sowa}_{prawe,lewe}
python3 build_std_ribbed_parts.py   # STANDARD v1.0: czesci zebrowane przyciete do koperty (nadpisuje wersje powyzej)
python3 build_std_lowpoly.py        # wszystkie lp_*.stl
python3 verify_all.py               # kontrola standardu (kod wyjscia 1 przy bledzie)
python3 export_line_json.py         # line.json dla podgladu w przegladarce
python3 build_artifact.py           # artifact/zebrowana_kolekcja.page.html
python3 test_artifact.py            # podglad kontra Python (kod wyjscia 1 przy rozbieznosci)
