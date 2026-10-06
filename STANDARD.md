# STANDARD LINII v1.0 — żebra (rb) i lowpoly (lp)

Jedno źródło prawdy dla całej linii: **`standard.py`** (stałe, reguły, narzędzia obu stylów, kontrola), dane pięciu modeli kluczowych w **`models.py`**,
wzór nowego modelu w **`new_model_template.py`**, automatyczna kontrola w **`verify_all.py`** (5 modeli) i `verify_set()` (dowolny nowy model).
Kto pisze nowy model, importuje tylko `from standard import *` — nie czyta niczego z królika, jajka, dyni ani bałwana.

Modele kluczowe: królik/renifer, jajko, dynia, bałwan — każdy w dwóch stylach (żebra, lowpoly), części wymienne pasują między stylami.

---------------------------------------------------------------------------------------------------

## 1. Zasady (kontrakt)

| # | Reguła | Wartość | Gdzie w kodzie |
|---|---|---|---|
| 1 | Układ współrzędnych | mm, z = 0 stół, płaska podstawa, bez podpór | — |
| 2 | Nawis | ≤ 55° od pionu na rzeczywistej siatce (lowpoly: profil ≤ 52°, `LP_SLOPE` = 1,30); poziome mostki/półki ≤ 12 mm | `OVERHANG_DEG`, `LP_SLOPE`, `overhang_check` |
| 3 | Czop | 5 × 5 × 8 mm (+2 mm w spoinę części) | `PEG_W`, `PEG_L`, `PEG_EXT` |
| 4 | Gniazdo | 5,4 × 5,4 × 9 mm (luz 0,2/stronę), sięga 1,5 mm nad P0 | `SOCK_W`, `SOCK_D`, `SOCK_OVER` |
| 5 | Kształt czopa/gniazda | żebra: zaokrąglenia r 1,0 / 1,25; lowpoly: fazy 1,0 / 0,7 wzdłuż wszystkich krawędzi. Luz każdej z 4 par (rb/lp × rb/lp) ≥ 0,15 (wyliczone: 0,179 / 0,200 / 0,199 / 0,200) | `lp_peg`, `lp_socket`, `peg_socket_matrix` |
| 6 | Uszy / poroże | pochylenie 14° na zewnątrz, x = ±6, y = 0,25 od osi | `TILT`, `EAR_X`, `EAR_Y`, `ear_ports` |
| 7 | **P0 i układ portu** | wyznacza **idealny, gładki profil** modelu (ten sam dla obu stylów) | `Port`, `port_on_profile` |
| 8 | **Koperta** | idealny obrys + normalny pad `max(0,9·max(nρ,0), 0,25)` + luz 0,3 → jedna część pasuje do ciała żebrowanego i lowpoly | `Envelope`, `ENV_PAD`, `PAD_MIN`, `GAP` |
| 9 | Żebra | amplituda ±0,8 mm (pełna od r = 10 mm, zero przy r ≤ 4 mm), profil `sign(cos)·|cos|^0,8`, rozstaw 3,0–3,8 mm w każdej bryle; nowe modele: N = round(2π·Rmax/3,4) | `ribbed_F`, `ribbed_sections_F`, `rib_sections`, `n_ribs` |
| 10 | Lowpoly | M = 2·floor(R/4 + 0,5) boków (min. 8) w każdej sekcji; pierścienie z `auto_rings` (tolerancja 0,6 mm, krok ≤ 12 mm, min. 1 mm); fasety ~12 mm; pierścień portu z fasetą wycentrowaną na osi portu | `facet_M`, `lp_section_rings`, `LP_TOL` |
| 11 | Wnęki i sufity | |dr/dz| ≤ 1,30 w obu stylach (czapka jajka: stożek 52°) | `LP_SLOPE`, `build_egg.CONE_DR_DZ` |
| 12 | Nazwy plików | małe litery/cyfry/`_`, lowpoly z prefiksem `lp_`, rozmiary `_S/_M/_L` | `NAME_RE` |
| 13 | Orientacja druku | korpusy stoją na płaskiej podstawie; części wymienne leżą na plecach (c = 0); ogonek dyni do góry nogami; czapka jajka otworem w dół | `emit(upright=…)` |
| 14 | Wysokość figurki | 150 mm (królik, renifer, bałwan) — `TOTAL_H` | `TOTAL_H` |

Wszystkie liczby są stałymi w `standard.py` (sekcja 1) — zmiana tam zmienia wszystko, a `verify_all.py` pokaże, co przestało pasować.

---------------------------------------------------------------------------------------------------

## 2. Układ portu

Port = punkt mocowania `P0` na idealnym profilu + ramka `(a, b, c)`:
`b` — oś czopu (na zewnątrz), `c` — płaska strona części (druk na plecach: c = 0 na stole), `a` — poprzecznie.
Gniazdo: przekrój 5,4 × 5,4 wokół osi c = 2,5, b od −9 do +1,5.

* uszy/poroże: `ear_ports(R, z_lo, z_hi)` → `{"ear_R", "ear_L"}` (P0 leży tam, gdzie R(z) = hypot(6; 0,25)),
* inne porty (ogonek, nos, miotła): `Port(nazwa, P0, socket_frame(P0, B=…, A=…, C=…), rodzaj)`.

Tolerancja kontroli: |P0 − powierzchnia| ≤ 0,9 mm (żebra: amplituda 0,8; lowpoly: wierzchołki faset). Zmierzone: królik 0,09/0,12, jajko 0,23/0,31, dynia 0,21, bałwan nos 0,34 / miotła 0,06.

## 3. Koperta (części wymienne dla obu stylów)

`Model.env` = `Envelope(outline, pad)`. Część wymienna jest przycinana do koperty (`rb_trims` dla żeber, `lp_trim` dla lowpoly), więc:

* podstawa części nie zachodzi w żaden korpus (żebrowany ani lowpoly) — interferencja ≤ 0,01 mm³, luz podstawy ≥ 0,41 mm, luz czopa na siatkach ≥ 0,15 mm,
* ta sama część pasuje do obu stylów (48 par krzyżowych w `verify_all.py`),
* uwaga: dzięki temu uszy żebrowane **podążają za obrysem koperty, a nie za żebrami** (podstawa gładka, nie karbowana).

Wyjątek: dynia — koperta z `pad = 1,8` (amplituda wariantu „36 płatów”).

## 4. Styl żebrowany (rb)

```python
F = ribbed_sections_F(R, z0, z1, cuts=(z_talii, ...))      # N żeber per sekcja; zanik ±3,5 mm wokół talii
axes, (X, Y, Z) = make_grid(-30, 30, -30, 30, -1.0, H + 1.5, 0.35)
Fv = F(X, Y, Z); Fv = min(Fv, -socket_F(...)) dla każdego portu       # gniazda
body = decimate(mesh_from_F(Fv, axes, 0.35), 220000)
emit(body, "nazwa.stl", True, style="rb", ports=[...])
part = part_mesh(ear_flat(L), rb_trims([(MODEL, "ear_R")]), True, (-10, 10), (-9, L + 3), 0.2)
```

Voxel 0,35 mm, decymacja do ≤ 220 000 trójkątów (odchylka maks. ~0,003 mm). Pięć modeli kluczowych ma własne pola (`shapes.py`, `build_pumpkin.py`, `build_snowman.py`) z zamrożonym N: królik 36, jajko 48, dynia 92 (36 płatów w wariancie `_platy`), bałwan 52/42/32/24.

## 5. Styl lowpoly (lp)

```python
secs = [lp_section_rings(R, 0.0, z_talii - 0.4),                          # M z promienia sekcji
        lp_section_rings(R, z_talii + 0.4, H, port_zs=[zport], apex_top=True)]
solid = lp_revolve(secs)                                                   # bryła obrotowa, trójkąty „na przemian”
body  = cut_ports(solid, MODEL)                                            # gniazda 5,4 × 5,4 × 9 ze skosami
part  = lp_trim(ear_leaf(L, -3.0), [(MODEL, "ear_R")])                     # część przycięta do koperty + czop 5×5×8
```

Reguły wbudowane w narzędzia: pierścienie na przemian przesunięte o pół kroku (pas trójkątów), faza „same” przy dz < 2 mm (brak piły), pierścienie bliższe niż 1,5 mm
są odsuwane, nie kasowane (tolerancja 0,6 mm zostaje zachowana), podstawa stożkowa `clamp_overhang`, boolean przez manifold3d z kontrolą szczelności po rzutowaniu na float32.
Fasetowe odchylenie od profilu idealnego: objętość lowpoly / idealna 0,98–1,00.

## 6. Przepis: nowy model w 8 krokach

1. Skopiuj `new_model_template.py`.
2. Zdefiniuj **jeden** profil `R(z)` (gładki, z = 0 na stole; podstawa: Z₁/R₁ ≤ 0,82, by nawis ≤ 55°). Granice brył = „talie” (`cuts`).
3. `ports = ear_ports(R, z_lo, z_hi)` albo własne `Port(...)`. `Model(nazwa, outline_R(R, 0, H), ports, ribbed_F=ribbed_sections_F(...))`.
4. Żebra: pole `ribbed_sections_F`, siatka, gniazda, `emit(..., style="rb")`.
5. Lowpoly: `lp_section_rings` per sekcja → `lp_revolve` → `cut_ports` → `emit(..., style="lp")`.
6. Części wymienne: `part_mesh(..., rb_trims([...]))` oraz `lp_trim(..., [...])` — zawsze przycinaj do **koperty modelu**.
7. `verify_set(MODEL, BODIES, PARTS, solids=…, rib_z=…)` — musi dać 0 FAIL (szablon: 31 PASS, w tym 4 pary krzyżowe).
8. Dopisz model do `models.py` (`MODELS`) i do list w `verify_all.py`, jeśli ma wejść do linii kluczowej.

## 7. Kontrola

`python3 verify_all.py` (~2 min) sprawdza na gotowych plikach `out/*.stl` 9 grup: stałe i luz czop–gniazdo (4 pary), zgodność P0, nazwy i komplet 38 plików,
siatki (szczelność, 1 składowa, nawis), korpus w kopercie (±0,1 mm), odległość P0–powierzchnia, **macierz pasowania** część × korpus (rb i lp, każdy z każdym: interferencja ≤ 1 mm³, luz ≥ 0,15 mm),
wysokości i wymiary rb vs lp, widmo żeber (FFT: N, rozstaw, amplituda), reguły M i pierścieni lowpoly. Wynik: `out/_verify_report.json`, kod wyjścia 1 przy błędzie.

Stan: **210 PASS, 0 FAIL** (`verify_all.py`, z samokontrolą testera druku) oraz **97 z 97 plików PASS** w `verify_print.py out/` i 24 z 24 w eksporcie z podglądu.

### 7a. Kontrola druku — szczelność i poprawność każdego STL (`verify_print.py`)

Każdy plik do druku (Python z `out/` **i** eksport z podglądu) przechodzi tę samą kontrolę; `FAIL` = nie drukować. `python3 verify_print.py out/` (ok. 2 min, 2 procesy), `python3 verify_print.py --selftest` (tester testera: znane dobre i złe siatki), `python3 test_artifact.py --print` (16 modeli z podglądu → STL → ta sama kontrola).

| # | Sprawdzenie | Próg |
|---|---|---|
| 1 | szczelność: każda krawędź w dokładnie 2 trójkątach (brak dziur, brak krawędzi nieregularnych) | 0 / 0 |
| 2 | spójna orientacja trójkątów, objętość > 0 (normalne na zewnątrz) | 0 niespójnych |
| 3 | brak trójkątów zdegenerowanych (pole < 1e-8 mm²), powtórzonych, NaN/Inf | 0 |
| 4 | liczba składowych = oczekiwana (domyślnie 1: bez pyłków i wysp), parzysta liczba Eulera | 1 |
| 5 | brak wierzchołków „ściśniętych” (dwie powierzchnie stykające się w punkcie — niejednoznaczne dla slicera) | 0 |
| 6 | brak samoprzecięć (pary trójkątów przecinających się wzajemnie; styk brzegowy < 0,2% trójkąta nie liczy się) | 0 |
| 7 | płaska podstawa na stole (z = 0, pole styku ≥ 20 mm² dla części stojących) | ostrzeżenie |
| 8 | ścianka wnęk (czapki, miseczki, doniczki, wazony): wiązka 7 promieni od strony wnęki, mediana; ≥ 0,8 mm (2 ścieżki dyszy 0,4) | ostrzeżenie, gdy > 0,5% powierzchni |

Dlaczego tak: żeberka mają z natury ostre grzbiety węższe niż 0,8 mm, więc cienkość mierzymy **od strony wnęk**, nie na grzbietach żeber (pojedynczy promień w poprzek żebra dawał fałszywe alarmy).

Jak pliki powstają szczelne:
* `lib.save` (a przez nią `standard.emit`/`save_lp`) przed zapisem zaokrągla wierzchołki do float32 (to, co zapisze STL) i **zwija mikro-trójkąty** (`meshclean.clean_degenerate`: zwinięcie najkrótszej krawędzi z warunkiem „link condition”, a dla igieł — przekłucie najdłuższej krawędzi; bez zmiany topologii, zmiana objętości < 1e-4 mm³). Istniejące pliki: `python3 clean_stl.py` (czyści w miejscu i sprawdza szczelność).
* Podgląd (surface nets) ma **siatkę rozmaitościową**: tablica `MN_BAD` wykrywa komórki z szachownicą ścian lub rozłączonym wnętrzem/zewnętrzem i odwraca znak jednego narożnika (`manifoldGrid`), a `dropSpecks` usuwa pyłki (< 0,1% trójkątów największej składowej). Zakładka Zapis pokazuje raport `meshCheck` dla każdej części (brzegowe/nieregularne krawędzie, składowe, objętość).

## 8. Znane odchylenia (jawnie)

* Żebrowany bałwan: dolna kula ma Z₁/R₁ = 0,87 → pierwsze ~2 mm podstawy ma nawis ~60° (≈ 0,4 % powierzchni, mieści się w progu szumu voxeli 1 %; wymaga dobrze przylegającej pierwszej warstwy, podpór nie trzeba).
* Żebrowany szum voxeli: do 1 % powierzchni może być oznaczone jako „nawis” przy 55° (schodki siatki); lowpoly: 0.
* Pole `dynia_korpus_platy` (36 płatów) ma inny rozstaw niż 3,4 mm (płaty, nie żebra) — kontrola dopuszcza.
* Miotła bałwana: grzbiet unosi się nad powierzchnią 0,65–1,2 mm między podstawą a czopem (pasowanie na czopie, luz podstawy ≥ 0,4).
* Nowe stałe N dla pięciu modeli kluczowych są zamrożone (nie wynikają ze wzoru na N), nowe modele liczą N ze wzoru.
* Lowpoly bałwan: M = 14/10/10/8 w czterech sekcjach (kula, kula, głowa, kapelusz); sekcje łączą pasy trójkątów 0,8 mm.
* Stare skrypty lowpoly (przed standardem) przeniesione do `legacy/`; grupy A/B (czapki, bombki, wazony…) mają jeszcze stożek sufitu 55° — przebudowa: `build_egg.py` + skrypty grupy.

## 9. Podgląd w przeglądarce (artefakt „Żebrowana kolekcja”)

Zasada: **Python = jedyne źródło prawdy; pliki do druku powstają wyłącznie ze skryptów.** Artefakt to podgląd/edytor: jego stałe, profile, pasma żeber i porty
pochodzą z `line.json`, generowanego z `standard.py`/`models.py`/`shapes.py`/`build_*.py`.

```bash
python3 export_line_json.py     # standard.py + modele → line.json (odcisk źródeł source_sha1, kontrole: profil < 0,01 mm, pasma bałwana = snow_F)
python3 build_artifact.py       # artifact/zebrowana_kolekcja.src.html + line.json + line_core.js → .html (testy) i .page.html (do publikacji)
python3 test_artifact.py        # JS (Node) kontra Python: profile, porty, pola 3D (królik, dynia, bałwan), dym 16 modeli; kod 1 przy rozbieżności
# publikacja: Artifact publish artifact/zebrowana_kolekcja.page.html (ten sam url → ta sama strona)
```

Zmiana stałej/profilu: edytuj Python → `export_line_json.py` → `build_artifact.py` → `test_artifact.py` → publikacja. Test sprawdza też odcisk źródeł (kod = line.json = HTML).

* Siatki STL z przeglądarki (zakładka Zapis) są szczelne (rozmaitościowe surface nets, raport `meshCheck` w zakładce Zapis, `test_artifact.py --print` puszcza je przez `verify_print.py`), ale mają rozdzielczość 0,35–0,5 mm i inne rozdzielczości siatki niż Python; **do druku seryjnego używać plików z `out/`** (Python = źródło prawdy, wynik pojedynczego wariantu z podglądu jest tylko podglądem).
* Dynia w artefakcie: N = 92, zanik żeber (12, 28) — odchylenie jak w skrypcie `build_pumpkin.py` (profil grzbietu `Rp`, a≈50, vs profil pola S_FINE, a≈49,2).
* Miotła bałwana jest tylko w Pythonie (nie ma jej w podglądzie).
* Dynia w podglądzie ma osobną szerokość (po grzbietach żeber) i wysokość bryły; profil jest skalowany osobno w poziomie i w pionie, N żeber rośnie z szerokością (rozstaw 3,4 mm zostaje), port ogonka jedzie z górą bryły. Domyślnie (100 × 65 mm) = skrypt Pythona; inne rozmiary istnieją tylko w podglądzie (siatka robocza).
* Jajko w podglądzie: **wnętrze i szew są stałe, obrys jest swobodny.** Wnęka miseczki i czapki, szew, kołnierz, sufit (52°) liczą się z powłoki odniesienia (domyślny kształt jajka), a nie z obrysu. Obrys (szerokość, wysokość, wysokość najszerszego miejsca, pełność dołu i góry) = `max(kształt, wnętrze + ścianka)`: miseczka ≥ `wallCup`, czapka ≥ 2,6 mm, kołnierz ≥ 2,0 mm, dobudowa ze spadkiem ≤ 1,3 (bez ostrzejszych nawisów); gdy kształt jest za chudy, podgląd ostrzega. Wniosek: jajko niespodzianka 44 × 68 mm pasuje tak samo w każdym wariancie, a miseczki i czapki różnych wariantów są wymienne. Test: `test_artifact.py` (wnęka identyczna z domyślną, ścianka ≥ minimum). Skrypty Pythona mają jeden obrys (standardowy).

## 10. Pliki

Żebra (19): `korpus_bazowy`, `krolik_calosc`, `renifer_calosc`, `ucho_prawe/lewe`, `ucho_dlugie_prawe/lewe`, `poroze_prawe/lewe`, `jajko_miseczka`, `jajko_czapka_gniazda`,
`jajko_czapka_uszy`, `jajko_czapka_uszy_dlugie`, `dynia_korpus`, `dynia_korpus_platy`, `dynia_ogonek`, `balwan`, `balwan_nos`, `balwan_miotla` — plus dodatkowe uszy `ucho_{mis,kot,lis,sowa}_{prawe,lewe}`.
Lowpoly (19): te same nazwy z prefiksem `lp_` (np. `lp_krolik_calosc.stl`, `lp_balwan.stl`).

Skrypty: `standard.py`, `models.py`, `lp.py`, `lp_parts.py`, `meshclean.py` + `clean_stl.py` (czyszczenie mikro-trójkątów), `verify_print.py` (kontrola druku), `build_std_lowpoly.py` (wszystkie lp_*.stl), `build_std_ribbed_parts.py` (części żebrowane),
`build_egg.py` + `build_dlugie.py` (czapki jajka), `build_figurki.py`/`build_pumpkin.py`/`build_snowman.py` (korpusy żebrowane), `verify_all.py`, `new_model_template.py`.
Podgląd: `export_line_json.py` (→ `line.json`), `build_artifact.py` + `artifact/` (`zebrowana_kolekcja.src.html`, `line_core.js`), `test_artifact.py` + `test_artifact.js`.
