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

Każdy plik do druku (Python z `out/` **i** eksport z podglądu) przechodzi tę samą kontrolę; `FAIL` = nie drukować. `python3 verify_print.py out/` (ok. 2 min, 2 procesy), `python3 verify_print.py --selftest` (tester testera: znane dobre i złe siatki), `python3 test_artifact.py --print` (17 modeli + 5 skrajnych wariantów renifera kręgla z podglądu → STL → ta sama kontrola).

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
| 9 | nawisy > 55° od pionu wg reguły standardu (`standard.overhang_check`: mostki ≤ 12 mm, szum voxeli 1% dla żeber, 0 dla lowpoly) — czyli druk bez podpór | ostrzeżenie |

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
* Stare skrypty lowpoly (przed standardem) przeniesione do `legacy/`. Grupy A/B (czapki na głowę, czapki jajka, matrioszki) mają już sufit wnęki 52° (`LP_SLOPE`, przebudowane), wszystkie 97 plików przechodzi regułę nawisów w `verify_print.py`.
* Duszek (falbana u dołu): 1,1 % powierzchni to płytkie stoki w pierwszych ~2 mm nad stołem i sklepienia łuków ≤ 6 mm; dozwolone 1,5 % (`OVERHANG_ALLOW` w `verify_print.py`), podpór nie trzeba.

## 9. Podgląd w przeglądarce (artefakt „Żebrowana kolekcja”)

Zasada: **Python = jedyne źródło prawdy; pliki do druku powstają wyłącznie ze skryptów.** Artefakt to podgląd/edytor: jego stałe, profile, pasma żeber i porty
pochodzą z `line.json`, generowanego z `standard.py`/`models.py`/`shapes.py`/`build_*.py`.

```bash
python3 export_line_json.py     # standard.py + modele → line.json (odcisk źródeł source_sha1, kontrole: profil < 0,01 mm, pasma bałwana = snow_F)
python3 build_artifact.py       # artifact/zebrowana_kolekcja.src.html + line.json + line_core.js → .html (testy) i .page.html (do publikacji)
python3 test_artifact.py        # JS (Node) kontra Python: profile, porty, pola 3D (królik, dynia, bałwan), dym 17 modeli; kod 1 przy rozbieżności
# publikacja: Artifact publish artifact/zebrowana_kolekcja.page.html (ten sam url → ta sama strona)
```

Zmiana stałej/profilu: edytuj Python → `export_line_json.py` → `build_artifact.py` → `test_artifact.py` → publikacja. Test sprawdza też odcisk źródeł (kod = line.json = HTML).

* Siatki STL z przeglądarki (zakładka Zapis) są szczelne (rozmaitościowe surface nets, raport `meshCheck` w zakładce Zapis, `test_artifact.py --print` puszcza je przez `verify_print.py`), ale mają rozdzielczość 0,35–0,5 mm i inne rozdzielczości siatki niż Python; **do druku seryjnego używać plików z `out/`** (Python = źródło prawdy, wynik pojedynczego wariantu z podglądu jest tylko podglądem).
* Dynia w artefakcie: N = 92, zanik żeber (12, 28) — odchylenie jak w skrypcie `build_pumpkin.py` (profil grzbietu `Rp`, a≈50, vs profil pola S_FINE, a≈49,2).
* Miotła bałwana jest tylko w Pythonie (nie ma jej w podglądzie).
* Dynia w podglądzie ma osobną szerokość (po grzbietach żeber) i wysokość bryły; profil jest skalowany osobno w poziomie i w pionie, N żeber rośnie z szerokością (rozstaw 3,4 mm zostaje), port ogonka jedzie z górą bryły. Domyślnie (100 × 65 mm) = skrypt Pythona; inne rozmiary istnieją tylko w podglądzie (siatka robocza).
* Jajko w podglądzie: **wnętrze i szew są stałe, obrys jest swobodny.** Wnęka miseczki i czapki, szew, kołnierz, sufit (52°) liczą się z powłoki odniesienia (domyślny kształt jajka), a nie z obrysu. Obrys (szerokość, wysokość, wysokość najszerszego miejsca, pełność dołu i góry) = `max(kształt, wnętrze + ścianka)`: miseczka ≥ `wallCup`, czapka ≥ 2,6 mm, kołnierz ≥ 2,0 mm, dobudowa ze spadkiem ≤ 1,3 (bez ostrzejszych nawisów); gdy kształt jest za chudy, podgląd ostrzega. Wniosek: jajko niespodzianka 44 × 68 mm pasuje tak samo w każdym wariancie, a miseczki i czapki różnych wariantów są wymienne. Test: `test_artifact.py` (wnęka identyczna z domyślną, ścianka ≥ minimum). Skrypty Pythona mają jeden obrys (standardowy).

## 9a. Korpus z parametrami: szyja, brzuch, głowa, poroże N poziomów, uszy-liście (renifer „kręgiel”)

Profil korpusu bazowego (`shapes.bunny_profile(z, p)`) ma dwa tryby; w obu głowa to elipsoida (promień `headR`, oś pionowa `headR·headK`, środek `headZ`), łączona z resztą p-normą (wykładnik `blend`):

* **Tryb p-normy** (`sil = 0`, domyślny: królik, kot, lis, miś, sowa, dawny renifer, anioł, krasnal, Mikołaj): brzuch to nadelipsoida (dół i góra z osobnymi wykładnikami `bodyN` / `bodyNu`, najszersze miejsce
  na `0,8·bodyHz + bellyDz`) i opcjonalna szyja (walec `neckR` od brzucha do środka głowy, 0 = brak). Wartości domyślne (`BODY_DEFAULTS`: `bodyNu = bodyN`, `bellyDz = 0`, `neckR = 0`, `headK = 1`) dają dokładnie
  dawny profil królika (różnica 0,0).
* **Tryb sylwetki** (`sil = 1`, renifer „kręgiel”): brzuch i szyja to **jedna krzywa przez punkty** (`shapes.sil_nodes` / `sil_radius`), a nie dwie bryły. Punkty (z, r) od dołu: podstawa `(0, baseR)`,
  brzuch `(bellyZ, bodyW/2)`, barki `(shZ, shR)`, szyja `(neckZ, neckR)` i góra szyi `(headZ, neckR)`. Krzywa to sześcienna krzywa Hermite'a typu PCHIP
  (nachylenia: 0 w lokalnych ekstremach, średnia harmoniczna ważona odstępami w środku, sieczna na początku, 0 na końcu), więc brzuch jest gładkim maksimum, szyja gładkim minimum, a nic nie przestrzela.
  Wysokości są wymuszane rosnąco (odstęp ≥ `SIL_EPS` = 1 mm), promień szyi nie przekracza 0,95 promienia głowy, powyżej góry szyi krzywa daje 0. Ten sam algorytm jest w `silSpec` / `silR` (podgląd); zgodność
  JS ↔ Python do 4e-15 mm. W podglądzie sylwetkę ustawia się, przeciągając punkty na rysunku (podstawa, brzuch, barki, szyja, głowa), albo suwakami Brzuch / Szyja / Głowa; oba sposoby zmieniają te same parametry.
  Wzór kręgla jest dopasowany do zdjęcia (odchylenie średnie 0,3 mm, maks. 0,7 mm).

Głowę podnosi/opuszcza `headZ`; w trybie sylwetki szyja idzie razem z nią (`neckZ`), więc głowa się nie odrywa (podgląd ostrzega, gdy przerwa jednak powstaje). Port poroża: `bunny_P0(side, p, earX)` (uwzględnia `headK`).

* Poroże (`parts.antler_geom` / `antler_flat`): gałąź główna + `antLv` odnóg (1–5) co `antSp` mm, każda o długości `12,963·antTine` pod kątem `antAng` od osi gałęzi; `antIn = 1` zwraca odnogi do środka (jak na zdjęciu, `renifer_kregiel.ant_part` / `ant_ar`); trzon gałęzi rozciąga się
  do ostatniej odnogi, korona zostaje. Domyślne (2, 13, 1, 38,108°) = dawne poroże (maska i pole `top` identyczne). `antS` = rozmiar, `antW` = grubość gałęzi, `earT` = grubość płaskownika.
* Kąty: `earTilt` (na zewnątrz, standard 14°), **`earPitch`** (do przodu +, do tyłu −; obrót ramki wokół osi a, `mount_frame(side, P0, tilt, pitch)`; 0 = dawna ramka), kąt odnóg `antAng`
  i kąt bocznych uszu `leafAng` (od pionu).
* Boczne ucho-liść (`parts.leaf_flat`, `shapes.head_port`): przytopione do głowy w punkcie pod kątem `leafPos` od czubka, ostry czubek, bez owalu, grubość `leafT`. Ucho leży **przed porożem**
  (y mniejsze): jego tylna ścianka ma odstęp `leafGap` (domyślnie 1 mm) od przedniej ścianki płaskownika poroża (`y = Y0 + 2,5 − earT − leafGap − leafT/2` to środek grubości ucha), więc ucho i poroże
  nie stykają się poza głową, a w rzucie z przodu ucho może zasłaniać podstawę poroża jak na zdjęciu. Bez `leafGap` w parametrach (dawne wywołania) ucho leży symetrycznie względem y = 0 (ramka: y = T/2 − 2,5).
  Kontrola: `renifer_kregiel.ear_antler_clearance` liczy najmniejszy odstęp ucho–poroże poza głową (EDT na siatce 0,25 mm; wymagane ≥ 0,6 mm; `build` i `verify_all`), a podgląd ostrzega („Ucho dotyka poroża”),
  gdy kąt poroża do przodu (`earPitch`) lub położenie ucha je zetknie. Kąt poroża `earTilt` ma zakres −20…+40° (minus = do środka), `antIn` zwraca odnogi do środka.
* Wzór ze zdjęcia: `renifer_kregiel.py` (parametry = suwaki podglądu; `export_line_json.py` eksportuje je do `line.json`, podgląd czyta stamtąd). Buduje `renifer_kregiel_calosc.stl` (poroże i uszy przytopione),
  `renifer_kregiel_korpus.stl` + `renifer_kregiel_poroze_{prawe,lewe}.stl` (poroże wymienne na czopie 5×5×8) i uruchamia `verify_set` (14 kontroli) na **nagim** korpusie bez uszu-liści:
  koperta modelu to bryła obrotowa, więc ucho-liść (element przytopiony) jest poza nią z definicji. Kontrola w `verify_all.py` (sekcja 10).
* Odchylenie: wysokość całości ok. 162 mm (nie 150): wymiary ze zdjęcia; przycisk „Dopasuj do 150 mm” w podglądzie skaluje poroże (`antS`).
* Nowe parametry mają testy zgodności JS ↔ Python (`test_artifact.py`): profil dla 6 wariantów (sylwetka kręgla, głowa wysoko, pełny brzuch, głowa elipsoidalna, wąska talia oraz dawna p-norma z szyją), porty, ramki z pochyleniem, pola części płaskich (poroże 1/2/3/5 poziomów, lustro, ucho-liść;
  rasteryzacja JS i PIL różni się do ~0,4 mm na zaokrąglonych złączach, więc tolerancja jest 2D ≤ 0,45 mm i zero punktów po przeciwnych stronach powierzchni z zapasem), a `--print` eksportuje 6 skrajnych wariantów
  (głowa wysoko, poroże 5 poziomów z kątami, wymienne, nisko, szeroki, wąska talia) i puszcza je przez `verify_print.py`.

## 9b. Miska-choinka wg „Plätzchen-Schalen” (`choinka_miska.py`)

* **Tylko wariant gładki, wszystkie krawędzie zaokrąglone** (decyzja użytkownika). Wersja żebrowana została usunięta: żebra liczone z odległości do najbliższej krawędzi obrysu miały nieciągłość na dwusiecznych narożników, która przy skosie ścianki 15° rosła w głąb (na dole ok. 5 mm od brzegu) i dawała poszarpane „klinki” na skosach pięter i przy czubku (widoczne w podglądzie slicera). Ten sam błąd miałby każdy model z żebrami na wielokącie ze skośną ścianką — nie łączyć „żeber z odległości do krawędzi” ze skosem na wielokącie; żebra są bezpieczne tylko na bryłach obrotowych (patrz sekcje wyżej).
* **Wierny obrys oryginału** (płaski obrys 104 × 141 × 21,2 mm: 3 piętra z poziomymi półkami, pień, ścianki skośne 15°, dno 1,2 mm): tabela `ORIG_RIGHT` (półszerokość, głębokość od czubka) pochodzi z pomiaru oryginału (narożniki (29,6; 49), (40,8; 87,7), (52,0; 126,1), końce półek 20,8 / 32,0, pień 24,1 do głębokości 141,2). Skale: **1,0 → 103 × 140 × 21,2 mm** (`choinka_miska_100.stl`) i **0,8 → 82 × 112 × 17 mm** (`choinka_miska_80.stl`, 6 szt. na stole 256 × 256). Skala dotyczy obrysu i wysokości; dno, ścianka i promienie zaokrągleń są bezwzględne. Nakładka na oryginał: IoU 0,975 (czubki skrócone o ok. 1 mm przez zaokrąglenie).
* Zaokrąglenia (stałe w nagłówku): w planie wypukłe `R_CONVEX` = 1,2 i wklęsłe `R_REFLEX` = 1,5 mm (otwarcie/domknięcie morfologiczne obrysu **na każdej wysokości osobno**, więc promień jest ten sam od dołu do góry), wnęka `R_CAVITY` = 1,0; brzeg górny `R_RIM` = 0,55 (obie krawędzie ścianki), krawędź dolna `R_BOT` = 0,4 (nawis ≤ 55° zachowany: kontrola `nawis>55: 0,0 mm2`), styk ścianki z dnem wewnątrz `R_FLOOR` = 1,2 mm. Krawędzie poziome przez gładkie minimum pól odległości (`smin`, promień ≈ 0,85 k).
* Bryła: obrys każdej warstwy = rim cofnięty o `(H − z)·tg 15°` (mitra) i zaokrąglony; wnęka = warstwa cofnięta o ściankę 1,6 mm (w pionowym ekwiwalencie 1,66); odległość ze znakiem z gęsto próbkowanego brzegu (błąd < 0,02 mm), siatka 0,25 mm. Pojemność wnęki ≈ 117 ml (100%) i 58 ml (80%).
* Kontrole w skrypcie (na gotowym STL, kod wyjścia 1 przy błędzie): wymiary (oryginał × skala, obrys −2…+0,5 mm) i liczba sztuk na stole (siatka i naprzemian czubek w górę/w dół), ścianka ≥ 0,9 mm na 4 wysokościach, pojemność, **gładkość** (kąt między sąsiednimi ścianami trójkątów > 50° tylko dla < 0,02% krawędzi; wynik 13 z 450 tys. — szum decymacji). `verify_print.py --fast` oraz samoprzecięcia (osobno) przechodzą; kontrola ścianek wnęk z `verify_print.py` (promienie) potrzebuje > 7 GB RAM dla siatki 300 tys. trójkątów i dla otwartej miski nic nie mierzy, więc zastępują ją przekroje z `wall_check_mesh`.
* Wariant pod okrąg 6 szt. (obrys poszerzony tak, że narożniki pięter leżą na liniach klinów 60°, szczelina 1,2 mm; 144 × 118 mm) był w commicie `3c636e6` (`--ring N`); smukła choinka domyka okrąg dopiero dla N = 9. Podgląd w przeglądarce dla tej miski nie istnieje.

## 10. Pliki

Żebra (19 + 4 renifer kręgiel: `renifer_kregiel_calosc/korpus/poroze_prawe/poroze_lewe`): `korpus_bazowy`, `krolik_calosc`, `renifer_calosc`, `ucho_prawe/lewe`, `ucho_dlugie_prawe/lewe`, `poroze_prawe/lewe`, `jajko_miseczka`, `jajko_czapka_gniazda`,
`jajko_czapka_uszy`, `jajko_czapka_uszy_dlugie`, `dynia_korpus`, `dynia_korpus_platy`, `dynia_ogonek`, `balwan`, `balwan_nos`, `balwan_miotla` — plus dodatkowe uszy `ucho_{mis,kot,lis,sowa}_{prawe,lewe}`.
Lowpoly (19): te same nazwy z prefiksem `lp_` (np. `lp_krolik_calosc.stl`, `lp_balwan.stl`).

Skrypty: `standard.py`, `models.py`, `lp.py`, `lp_parts.py`, `meshclean.py` + `clean_stl.py` (czyszczenie mikro-trójkątów), `verify_print.py` (kontrola druku), `build_std_lowpoly.py` (wszystkie lp_*.stl), `build_std_ribbed_parts.py` (części żebrowane),
`build_egg.py` + `build_dlugie.py` (czapki jajka), `build_figurki.py`/`build_pumpkin.py`/`build_snowman.py` (korpusy żebrowane), `renifer_kregiel.py` (renifer z parametrami wzoru), `verify_all.py`, `new_model_template.py`.
Miska-choinka: `choinka_miska.py` (`choinka_miska_100.stl`, `choinka_miska_80.stl`; gładka, krawędzie zaokrąglone).
Jeleń: `jelen.py` (`jelen_stojacy.stl`, 50 mm, gładki; wzorzec proporcji: zabawkowy jeleń z MakerWorld, własna geometria z pól odległości, nie kopia).
Podgląd: `export_line_json.py` (→ `line.json`), `build_artifact.py` + `artifact/` (`zebrowana_kolekcja.src.html`, `line_core.js`), `test_artifact.py` + `test_artifact.js`.
