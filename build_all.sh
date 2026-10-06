#!/usr/bin/env bash
# Pelna przebudowa linii od zera (zebra + lowpoly) i kontrola standardu. Wyniki: out/*.stl, out/_verify_report.json
# Czas ok. 15-20 min (siatki zebrowane ~ 0,35 mm voxel). Dowolny krok mozna uruchomic osobno.
set -euo pipefail
cd "$(dirname "$0")"
python3 build_figurki.py            # korpus_bazowy, krolik_calosc, renifer_calosc, ucho_*, poroze_*
python3 build_pumpkin.py            # dynia_korpus, dynia_korpus_platy, dynia_ogonek
python3 build_snowman.py            # balwan, balwan_nos, balwan_miotla
python3 build_egg.py                # jajko_miseczka, jajko_czapka_gniazda, jajko_czapka_uszy
python3 build_dlugie.py             # ucho_dlugie_*, jajko_czapka_uszy_dlugie
python3 ears_A.py                   # ucho_{mis,kot,lis,sowa}_{prawe,lewe}
# --- grupy A/B (figurki, czapki, naczynia, ozdoby): sufity wnek 52 st. (LP_SLOPE), czyszczenie siatek w lib.save
python3 build_A_czapki.py           # czapka_krasnal/mikolaj (na glowe korpusu), jajko_czapka_krasnal/mikolaj
python3 build_A_fused.py mis kot lis sowa pisklo   # mis/kot/lis/sowa_calosc, jajko_czapka_pisklo
python3 build_aniol.py              # aniol_calosc (skrzydla z pior; build_A_fused.py ma starsza wersje - nie uruchamiac z 'aniol')
python3 build_A_duszek.py           # duszek
python3 build_B_matrioszki.py       # jajko_M_*, jajko_S_*
python3 build_B_wazony.py           # wazon_walec/owal/butelka, swiecznik_tealight/swieca
python3 build_B_doniczki.py         # doniczka_S/M/L, podstawka_S/M/L, sloik, sloik_pokrywa, sloik_galka
python3 build_B_bombki.py           # bombka_okragla_60/80/100, bombka_kropla
python3 build_B_choinka.py          # choinka_1..4, choinka_podstawa, choinka_gwiazda
python3 build_flakes.py             # platek_01..10
python3 build_test.py               # test_czop, test_gniazdo_blok (probka pasowania na drukarke)
python3 build_std_ribbed_parts.py   # STANDARD v1.0: czesci zebrowane przyciete do koperty (nadpisuje wersje powyzej)
python3 build_std_lowpoly.py        # wszystkie lp_*.stl
python3 verify_all.py               # kontrola standardu (kod wyjscia 1 przy bledzie)
python3 verify_print.py out/        # kontrola druku kazdego STL: szczelnosc, zdegenerowane, samoprzeciecia, sciany wnek (kod 1 przy bledzie), ok. 2 min
python3 export_line_json.py         # line.json dla podgladu w przegladarce
python3 build_artifact.py           # artifact/zebrowana_kolekcja.page.html
python3 test_artifact.py --print    # podglad kontra Python + STL wyeksportowane z podgladu przez verify_print (kod wyjscia 1 przy rozbieznosci)
