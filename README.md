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
./build_all.sh                    # wszystko od zera + verify_all.py (10-15 min)
python3 verify_all.py             # 209 kontroli na gotowych plikach out/*.stl
python3 export_line_json.py       # line.json: stałe, profile i porty dla artefaktu „Żebrowana kolekcja”
```

## Układ repozytorium

| Plik | Rola |
|---|---|
| `standard.py` | **STANDARD v1.0**: stałe, porty, koperta, narzędzia rb i lp, kontrole, `emit`, `verify_set` |
| `models.py` | dane 5 modeli kluczowych (profile, porty) + budowniczowie lowpoly |
| `lib.py`, `parts.py`, `shapes.py` | rdzeń stylu żebrowanego (siatka voxelowa + marching cubes, części płaskie, uchwyty) |
| `lp.py`, `lp_parts.py` | rdzeń lowpoly (pierścienie, boolean przez manifold3d, liść, poroże) |
| `build_*.py`, `ears_A.py` | skrypty budujące STL (kolejność w `build_all.sh`) |
| `verify_all.py` | kontrola standardu na 38 plikach (siatki, nawisy, koperty, pasowanie 2×4, żebra, M) |
| `new_model_template.py` | wzór nowego modelu (kopiuj i zmień sekcję „DANE MODELU”) |
| `export_line_json.py` | stałe/profile/porty → `line.json` dla artefaktu (przeglądarkowy edytor) |
| `legacy/` | stare skrypty lowpoly sprzed standardu (nieużywane) |

Pliki STL nie leżą w repozytorium (ribbed ~ 11 MB każdy): są w **Releases** (`v1.0`) albo powstają z `build_all.sh`.
