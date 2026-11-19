# linia-3d

Własna linia modeli 3D do druku (japandi): **modele żebrowane** (`rb`, żebra ±0,8 mm, rozstaw ~3,4 mm) i **lowpoly** (`lp_*`),
generowane proceduralnie w Pythonie. Pięć modeli kluczowych: królik/renifer, jajko, dynia, bałwan. Części wymienne (uszy, poroże,
ogonek, nos, miotła) na czopach 5×5×8 pasują do obu stylów.

**Zasady, stałe i przepis na nowy model: [`STANDARD.md`](STANDARD.md)** (jedno źródło prawdy: `standard.py`).

## Szybki start

```bash
pip install -r requirements.txt
python3 new_model_template.py     # demo „gruszka” w obu stylach + kontrola (31 PASS), pliki w out_demo/
python3 build_std_lowpoly.py      # 19 plików lp_*.stl (kilka sekund)
python3 renifer_kregiel.py        # renifer „kręgiel”: całość, korpus z gniazdami, poroże wymienne + verify_set (ok. 30 s)
python3 choinka_miska.py          # miska-choinka wg oryginału, gładka, krawędzie zaokrąglone: 100% (103 × 140 × 21 mm) i 80% (82 × 112 × 17 mm); `--scale S` = własna skala (ok. 5 min)
python3 foremki_piernik.py        # 5 foremek do pierników: choinka, renifer, bałwan, piernikowy ludzik, gwiazdka (kilka sekund)
python3 czubek_choinkowy.py       # wydłużony czubek choinkowy: długa tuleja, pusta kula otwarta od dołu, iglica (240 mm); opcje `--top 14 --sleeve 62 --h 240 --bulb 62` (ok. 10 s)
python3 etykieta.py Ania Tomek    # poziome etykiety „Dla” + imię; `--cap 12` = wyższe litery (kilka sekund)
python3 taca.py                    # taca żebrowana 240 × 75 × 20 mm (prostokąt z zaokrąglonymi narożnikami, ścianka z żebrami, gładkie wnętrze) na 4 renifery kręgle i drobiazgi; `--wid`, `--len`, `--h`, `--rad` (ok. 10 s)
python3 jelen_knit.py             # jeleń „knitted” (faktura dzianiny: rzędy oczek zamiast żeber) 130 mm, bez podpór; `--h`, `--stitch`, `--row`, `--amp`, `--check` = porównanie nawisów z gładkim (ok. 3-5 min)
python3 renifer_kregiel_knit.py     # renifer kręgiel „knitted” (oczka zamiast żeber, poroże i uszy przytopione, 54,6 × 54,6 × 162 mm), bez podpór; `--stitch`, `--row`, `--amp`, `--check` (ok. 1 min)
python3 pikowany_pojemnik.py       # pojemnik pikowany „jak z materiału” 200 × 140 × 100 mm (poduszki z karbami, guziki, zwinięty brzeg, otwory na uchwyt), bez podpór; `--len`, `--wid`, `--h`, `--puff`, `--tuft`, `--row` (ok. 1 min)
python3 renifer_kregiel_knit.py --stitch 5.5 --row 4.4 --amp 0.7 --name renifer_kregiel_knit_gruby.stl   # to samo z grubszymi oczkami 5,5 × 4,5 mm
python3 artifact/build_swieta.py # składa artefakt „Świąteczne dodatki” (etykieta, czubek, foremki; STL w przeglądarce); testy: `node artifact/test_swieta.js`, `python3 artifact/test_swieta.py`, `python3 artifact/test_swieta_ui.py`
./build_all.sh                    # wszystko od zera + verify_all.py + verify_print.py (15-20 min)
python3 verify_all.py             # 217 kontroli standardu na gotowych plikach out/*.stl
python3 verify_print.py out/      # szczelność i poprawność druku każdego STL (dziury, zdegenerowane, samoprzecięcia, ścianki; ok. 2 min)
python3 export_line_json.py       # line.json: stałe, profile i porty dla artefaktu „Żebrowana kolekcja”
python3 build_artifact.py         # składa stronę podglądu (artifact/zebrowana_kolekcja.page.html) z line.json
python3 test_artifact.py          # podgląd (Node) kontra Python: profile, porty, pola 3D
```

## Układ repozytorium

| Plik | Rola |
|---|---|
| `standard.py` | **STANDARD v1.0**: stałe, porty, koperta, narzędzia rb i lp, kontrole, `emit`, `verify_set` |
| `models.py` | dane 5 modeli kluczowych (profile, porty) + budowniczowie lowpoly |
| `lib.py`, `parts.py`, `shapes.py` | rdzeń stylu żebrowanego (siatka voxelowa + marching cubes, części płaskie, uchwyty) |
| `lp.py`, `lp_parts.py` | rdzeń lowpoly (pierścienie, boolean przez manifold3d, liść, poroże) |
| `build_*.py`, `ears_A.py` | skrypty budujące STL (kolejność w `build_all.sh`) |
| `renifer_kregiel.py` | renifer z parametrami wzoru (sylwetka z punktów: podstawa, brzuch, barki, szyja, głowa; poroże N poziomów z odnogami do środka, uszy-liście); parametry = suwaki i punkty na rysunku w podglądzie |
| `jelen.py` | jeleń stojący (gładki, „zabawkowy”: gruby tułów, duża głowa, krótkie grube nogi, zbite szerokie poroże), 50 mm, z pól odległości; kontrole: wysokość, szczelność, środek masy nad podstawą, stopy ≥ 100 mm², nawisy (powierzchniowe i warstwowe jak slicer), elementy < 2 mm |
| `jelen_siedzacy.py` | jeleń siedzący: ta sama głowa, uszy, poroże i skala co `jelen.py` (`S_STD`), inny tułów; te same kontrole (w tym nawisy jak slicer) |
| `jelen_jelonek.py` | jelonek: ta sama głowa i skala, mały tułów, krótkie nogi, większe uszy, paczki zamiast poroża |
| `jelen_chudy_glowa90.py` | jeleń stojący chudy ze skręconą głową (`TURN` = 90°, `jelen_chudy.design(P, turn=...)`): to samo ciało, szyja i skala co `jelen_chudy.py`, głowa z uszami i porożem obrócona wokół pionu przez koniec szyi |
| `jelen_glowa90.py` | jeleń stojący z głową obróconą w bok (`TURN` = 90°, oś `PIVOT` na końcu szyi): ten sam tułów, nogi i skala, głowa/uszy/poroże obrócone; `build(..., box=...)` z szerszą siatką |
| `jelen_chudy.py` | jeleń stojący „chudy”: proporcje bliżej wzorca DEER 1 (tułów węższy i niższy, nogi rozstawione szerzej, długa cienka szyja, głowa wyżej i uniesiona); skala z wysokości 50 mm (dwa przebiegi, `S` ≈ 0,82); ta sama głowa, uszy i poroże |
| `jelen_lezacy.py` | jeleń leżący (tułów na stole, przednie nogi wysunięte); te same kontrole |
| `jelen_siedzacy_chudy.py` | jeleń siedzący „chudy”: węższy tułów, piersi i uda, cieńsze nogi, dłuższa cienka szyja, głowa wyżej i uniesiona; skala `S_CH` (głowa jak w `jelen_chudy.py`), 37 × 35 × 45 mm (v3: węższy tułów i uda wpasowane w obrys, okrągły grzbiet, węższa głowa i mniejsze uszy, nos jak u Rudolfa, ogon-pompon), 0 mm² nawisu i 0 wysp |
| `jelen_lezacy_chudy.py` | jeleń leżący „chudy”: węższy tułów, zad i nogi, dłuższa cienka szyja, głowa wyżej i uniesiona; skala `S_CH`, 38 × 35 × 41 mm (v3: tułów 14 zamiast 18 mm szerokości, uda wpasowane w obrys, okrągły grzbiet, węższa głowa i mniejsze uszy, nos jak u Rudolfa, ogon-pompon), 0 mm² nawisu i 0 wysp |
| `jajko_zamek_proba.py` | jajko niespodzianka: próbka łączenia na sztywny zatrzask (dolny pierścień + 3 górne o luzie 0,10 / 0,15 / 0,20 mm), skala 1:1 na średnicy szwu; przed przebudową jajka z porożem |
| `jajko_zamek_wycinek.py` | jajko niespodzianka: **wycinek do testu zamka** (miseczka + 3 czapki, prawdziwy obrys i sztywność jajka, luz 0,10 / 0,15 / 0,20 mm), 57 g, bez podpór |
| `jajko_renifer.py` | jajko niespodzianka **renifer**: miseczka + czapka z zamkiem nr 3 (luz 0,20 mm), poroże 3-poziomowe i uszy-liście z dużego modelu przytopione (ucho 1 mm przed porożem, uszy jak w `renifer_kregiel.stl` od Dominika: 21°, 16 × 10 mm), 127,8 mm, 65 g, bez podpór |
| `nawisy.py` | pod druk bez podpór: `carve` (od dołu: każda warstwa wystaje najwyżej o stały skos, nic nie wisi w powietrzu, brzuch = namiot z nóg, spód pyska rośnie ku nosowi) i `slicer_overhang` (miara jak w Bambu: warstwa 0,2, progi 25–40°, prawdziwe wyspy) |
| `choinka_miska.py` | miska-choinka wg „Plätzchen-Schalen”: obrys oryginału w skali 1,0 i 0,8 z czubkiem 60° (6 szt. styka się czubkami bez nakładania), wariant gładki ze wszystkimi krawędziami zaokrąglonymi (plan, brzeg, dno); parametry w nagłówku (promienie, ścianka, skos) |
| `foremki_piernik.py` | 5 foremek do pierników (`foremka_{choinka,renifer,balwan,ludzik,gwiazdka}.stl`): ścianka 1,2 mm, kołnierz do dociskania, ostrze 0,45 mm, druk kołnierzem do stołu bez podpór; obrysy 2D (`shape_*`) trafiają do artefaktu przez `--json`; kołnierz 5 × 2 mm jest stały w modelu (w artefakcie regulowany) |
| `czubek_choinkowy.py` | wydłużony czubek choinkowy (jak szklany): tuleja 62 mm, kula PUSTA i otwarta od dołu (czubek choinki wchodzi na ok. 112 mm), szyjka, iglica; żebrowany, bez podpór: 240 × 64 mm, tuleja na czubek `--top` (domyślnie 18 mm), ok. 60 g PETG |
| `etykieta.py` | pozioma etykieta na prezent: „Dla” + imię (Poppins Bold, polskie znaki), szerokość dopasowana do imienia, otwór Ø 4,2 mm, płytka 2 mm + napis 0,8 mm, druk na płasko; ten sam algorytm w artefakcie (`artifact/swieta_core.js`) |
| `taca.py` | żebrowana taca prostokątna 240 × 75 × 20 mm z zaokrąglonymi narożnikami (R 15, pionowe żebra po zewnętrznej ściance, gładkie wnętrze, dno 2,4 mm): 4 renifery kręgle w rzędzie z luzem 8,4 mm na rancie, 3 szt. na stole P1S, druk bez podpór; podgląd z góry i 3D |
| `knit.py` / `jelen_knit.py` | faktura dzianiny (oczka „V” w rzędach i kolumnach, wypukłość 0,5 mm) nakładana na dowolne pole odległości F; `jelen_knit.py` = własny jeleń 130 mm „knitted”, 0 mm² nawisu w slicerze (25°/30°), stopy jak w gładkim |
| `renifer_kregiel_knit.py` | duży renifer kręgiel w wersji „knitted” (faktura dzianiny z `knit.py` zamiast żeber): ten sam obrys i wymiar po grzbietach 54,6 mm (pasuje na tacę), poroże i uszy przytopione, 0 mm² nawisu w slicerze (25° / 30°) |
| `pikowany_pojemnik.py` | pojemnik pikowany (capitonné) 200 × 140 × 100 mm: okrągłe poduszki rozdzielone karbami w rombowej siatce, guziki z fałdkami, zwinięty brzeg, otwory na uchwyt; 0 mm² nawisu w slicerze (25° / 30°), ścianka ≥ 1,3 mm |
| `artifact/swieta.src.html` | artefakt „Świąteczne dodatki”: wpisujesz imię / ustawiasz rozmiar i pobierasz gotowy STL (w ZIP); geometria w `swieta_core.js`, zgodna z Pythonem co do objętości |
| `verify_all.py` | kontrola standardu na 38 plikach (siatki, nawisy, koperty, pasowanie 2×4, żebra, M) |
| `verify_print.py` | kontrola druku każdego STL: szczelność, orientacja, zdegenerowane, pyłki, ściśnięte wierzchołki, samoprzecięcia, ścianki wnęk; `--selftest` |
| `meshclean.py`, `clean_stl.py` | usuwanie mikro-trójkątów bez otwierania siatki (wpięte w `lib.save`); `clean_stl.py` czyści istniejące pliki |
| `new_model_template.py` | wzór nowego modelu (kopiuj i zmień sekcję „DANE MODELU”) |
| `export_line_json.py` | stałe/profile/porty → `line.json` dla artefaktu (przeglądarkowy edytor) |
| `build_artifact.py`, `artifact/` | składanie strony podglądu (`.src.html` + `line_core.js` + `line.json`); STL z przeglądarki to siatki robocze |
| `test_artifact.py`, `test_artifact.js` | zgodność podglądu z Pythonem (Node ładuje rdzeń JS) |
| `legacy/` | stare skrypty lowpoly sprzed standardu (nieużywane) |

Pliki STL nie leżą w repozytorium (ribbed ~ 11 MB każdy): powstają z `build_all.sh` (10-15 min). Gotowe paczki `linia-v1.0_*.zip` można dołączyć ręcznie do Release `v1.0`.
