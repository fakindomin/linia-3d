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
python3 gwiazda_choinkowa.py      # gwiazda na czubek choinki z tuleją; opcjonalnie średnica czubka w mm, np. `python3 gwiazda_choinkowa.py 14` (ok. 30 s)
python3 zawieszki.py              # 5 zawieszek na prezenty (DLA:/OD:); z imionami: `python3 zawieszki.py Ania Tomek` (kilka sekund)
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
| `foremki_piernik.py` | 5 foremek do pierników (`foremka_{choinka,renifer,balwan,ludzik,gwiazdka}.stl`): ścianka 1,2 mm, kołnierz do dociskania, ostrze 0,45 mm, druk kołnierzem do stołu bez podpór; obrysy 2D (`shape_*`) używa też `zawieszki.py` |
| `gwiazda_choinkowa.py` | gwiazda na czubek prawdziwej choinki: pięcioramienna, żebrowana, 77 × 25 × 73 mm, tuleja na czubek `TOP_D` (domyślnie 18 mm), druk stojący bez podpór |
| `zawieszki.py` | zawieszki na prezenty (prostokąt, bombka, choinka, gwiazdka, renifer): płytka 2 mm, ramka i napis „DLA:/OD:” lub podane imiona, otwór Ø 4,2 mm, druk na płasko |
| `verify_all.py` | kontrola standardu na 38 plikach (siatki, nawisy, koperty, pasowanie 2×4, żebra, M) |
| `verify_print.py` | kontrola druku każdego STL: szczelność, orientacja, zdegenerowane, pyłki, ściśnięte wierzchołki, samoprzecięcia, ścianki wnęk; `--selftest` |
| `meshclean.py`, `clean_stl.py` | usuwanie mikro-trójkątów bez otwierania siatki (wpięte w `lib.save`); `clean_stl.py` czyści istniejące pliki |
| `new_model_template.py` | wzór nowego modelu (kopiuj i zmień sekcję „DANE MODELU”) |
| `export_line_json.py` | stałe/profile/porty → `line.json` dla artefaktu (przeglądarkowy edytor) |
| `build_artifact.py`, `artifact/` | składanie strony podglądu (`.src.html` + `line_core.js` + `line.json`); STL z przeglądarki to siatki robocze |
| `test_artifact.py`, `test_artifact.js` | zgodność podglądu z Pythonem (Node ładuje rdzeń JS) |
| `legacy/` | stare skrypty lowpoly sprzed standardu (nieużywane) |

Pliki STL nie leżą w repozytorium (ribbed ~ 11 MB każdy): powstają z `build_all.sh` (10-15 min). Gotowe paczki `linia-v1.0_*.zip` można dołączyć ręcznie do Release `v1.0`.
