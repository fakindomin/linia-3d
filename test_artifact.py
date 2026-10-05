"""Zgodnosc podgladu w przegladarce (artifact/zebrowana_kolekcja.html) ze skryptami Pythona (STANDARD v1.0).
Node ladowany jest rdzeniem podgladu (test_artifact.js); tu porownanie liczbowe: profile, porty, ramki, wneka jajka, POLA 3D (krolik, dynia,
balwan na siatce 1 mm) oraz test dymny wszystkich 16 modeli. Zwraca kod 1, gdy cos sie rozjezdza.
Uzycie:  python test_artifact.py [plik.html]
"""
import sys, os, json, base64, subprocess, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import standard as S
import models as MD
import shapes as SH
import build_pumpkin as BP
import build_snowman as BS
import build_egg as BE
import export_line_json as EX

html = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "artifact", "zebrowana_kolekcja.html")
t0 = time.time()
raw = subprocess.run(["node", os.path.join(HERE, "test_artifact.js"), html], capture_output=True, check=True, text=True, timeout=900).stdout
J = json.loads(raw)
print(f"node: {time.time() - t0:.1f} s, wynik {len(raw) / 1e6:.1f} MB")

ok = True


def check(name, val, tol, unit="mm"):
    global ok
    good = val <= tol
    ok &= good
    print(f"  {'PASS' if good else 'FAIL'}  {name}: {val:.4g} {unit} (limit {tol})")


def grid_py(g):
    x = g["x0"] + g["v"] * np.arange(g["nx"])
    y = g["y0"] + g["v"] * np.arange(g["ny"])
    z = g["z0"] + g["v"] * np.arange(g["nz"])
    Z, Y, X = np.meshgrid(z, y, x, indexing="ij")
    F = np.frombuffer(base64.b64decode(g["F"]), np.float32).reshape(g["nz"], g["ny"], g["nx"])
    return X, Y, Z, F


def cmp_field(name, g, Fpy, H, band=1.0):
    """pola F obcinane do [-band, band] (z gniazd Python liczy odleglosc globalnie, JS tylko w pudelku wokol gniazda: ten sam zbior zerowy);
    porownanie w 0 <= z <= H (poza zakresem F = odleglosc od plaszczyzny albo pochodna ucietego profilu: poza bryla)"""
    X, Y, Z, F = grid_py(g)
    cj, cp = np.clip(F, -band, band), np.clip(Fpy, -band, band)
    m = ((np.abs(cj) < band) | (np.abs(cp) < band)) & (Z >= 0) & (Z <= H)
    d = np.abs(cj - cp)[m]
    check(f"pole {name}: max |dF| w pasie powierzchni ({int(m.sum())} wezlow)", float(d.max()), 0.03)
    check(f"pole {name}: 99,9 percentyl |dF|", float(np.percentile(d, 99.9)), 0.012)
    sign = int((((F > 0) != (Fpy > 0)) & (np.abs(Fpy) > 1e-3) & (Z >= 0) & (Z <= H)).sum())
    check(f"pole {name}: wezly po innej stronie powierzchni (0 <= z <= H)", float(sign), 0, "")
    return d


# --- stan zrodel: line.json i HTML musza pochodzic z biezacego kodu
cur = EX.build()["source_sha1"]
lj = json.load(open(os.path.join(HERE, "line.json")))["source_sha1"]
import re
emb = re.search(r'"source_sha1":"([0-9a-f]+)"', open(html, encoding="utf8").read()).group(1)
print(f"zrodla: kod {cur} | line.json {lj} | html {emb}")
if not (cur == lj == emb):
    ok = False
    print("  FAIL  line.json / podglad nie odpowiadaja biezacym zrodlom: python export_line_json.py && python build_artifact.py")
else:
    print("  PASS  odcisk zrodel zgodny")

# --- krolik: profil, P0, ramki
zs = np.array(J["bun"]["zs"])
check("krolik: profil R(z) JS vs shapes.bunny_profile", float(np.abs(np.array(J["bun"]["prof"]) - SH.bunny_profile(zs)).max()), 1e-4)
for i, side in enumerate((+1, -1)):
    port = MD.BUNNY.ports["ear_R" if side > 0 else "ear_L"]
    check(f"krolik: P0 {'prawe' if side > 0 else 'lewe'}", float(np.abs(np.array(J["bun"]["P0"][i]) - port.P0).max()), 1e-3)
    fj = J["bun"]["frames"][i]
    dm = max(float(np.abs(np.array(fj[k]) - getattr(port.frame, k)).max()) for k in "OABC")
    check(f"krolik: ramka mocowania {'prawe' if side > 0 else 'lewe'} (O,A,B,C)", dm, 1e-6)

# --- jajko: profil, wneka kubka i czapki (z sufitem 52 st.), P0
ze = np.array(J["egg"]["zs"])
check("jajko: R(z) JS vs shapes.egg_R", float(np.abs(np.array(J["egg"]["R"]) - SH.egg_R(ze)).max()), 1e-4)
check("jajko: wneka miseczki JS vs build_egg.cav_cup_r", float(np.abs(np.array(J["egg"]["cup"]) - BE.cav_cup_r(ze)).max()), 1e-4)
check("jajko: wneka czapki JS vs build_egg.cav_cap_r (sufit 52 st.)", float(np.abs(np.array(J["egg"]["cap"]) - BE.cav_cap_r(ze)).max()), 1e-4)
check("jajko: poczatek stozka sufitu Z_A", abs(J["egg"]["ZA"] - BE.Z_A), 1e-6)
check("jajko: nachylenie sufitu = LP_SLOPE", abs(J["egg"]["cone"] - S.LP_SLOPE), 1e-9, "")
for i, side in enumerate((+1, -1)):
    check(f"jajko: P0 {'prawe' if side > 0 else 'lewe'}", float(np.abs(np.array(J["egg"]["P0"][i]) - SH.egg_P0(side)).max()), 1e-3)

# --- pola 3D
g = J["grid_krolik"]
X, Y, Z, F = grid_py(g)
cmp_field("krolik (bunny_F)", g, SH.bunny_F(X, Y, Z), 121.0)

g = J["grid_dynia"]
X, Y, Z, F = grid_py(g)
Fp = BP.pumpkin_F(X, Y, Z, BP.S_FINE, "fine")
a, b, c = BP.FR_STEM.to_local(X, Y, Z)
Fp = np.minimum(Fp, -S.socket_F(a, b, c))
cmp_field("dynia (pumpkin_F + gniazdo ogonka)", g, Fp, BP.H_TOP)

g = J["grid_balwan"]
X, Y, Z, F = grid_py(g)
Fp = BS.snow_F(X, Y, Z)
for fr in (BS.FR_NOSE, BS.FR_BROOM):
    a, b, c = fr.to_local(X, Y, Z)
    Fp = np.minimum(Fp, -S.socket_F(a, b, c))
cmp_field("balwan (snow_F + gniazda nosa i miotly)", g, Fp, BS.TOTAL)

# --- dym: wszystkie modele
print("test dymny (szkic 1 mm):")
for k, v in J["smoke"].items():
    good = v["tris"] > 100 and v["nan"] == 0 and not v["warn"]
    ok &= good
    print(f"  {'PASS' if good else 'FAIL'}  {k:14s} {v['tris']:>7d} tr.  {v['w']:.1f} x {v['h']:.1f} x {v['d']:.1f} mm  {v['ms']} ms  {v['files']}{'  OSTRZEZENIE: ' + str(v['warn']) if v['warn'] else ''}")
sm = J["smoke"]
check("balwan: wysokosc korpusu+nosa", abs(sm["balwan"]["h"] - 150.0), 0.6)
check("dynia: szerokosc (100 mm + zebra)", abs(sm["dynia"]["w"] - 100.0), 1.0)
check("krolik: wysokosc calosci (150 mm)", abs(sm["krolik"]["h"] - 150.0), 1.0)

print("\nWYNIK:", "OK" if ok else "BLAD", f"({time.time() - t0:.0f} s)")
sys.exit(0 if ok else 1)
