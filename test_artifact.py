"""Zgodnosc podgladu w przegladarce (artifact/zebrowana_kolekcja.html) ze skryptami Pythona (STANDARD v1.0).
Node ladowany jest rdzeniem podgladu (test_artifact.js); tu porownanie liczbowe: profile, porty, ramki, wneka jajka, POLA 3D (krolik, dynia,
balwan na siatce 1 mm) oraz test dymny wszystkich 16 modeli. Zwraca kod 1, gdy cos sie rozjezdza.
Uzycie:  python test_artifact.py [plik.html] [--print]
  --print: dodatkowo eksportuje wszystkie 16 modeli (24 pliki STL, siatka 0,5 mm) tak jak przycisk 'Zapisz' w podgladzie i puszcza je przez verify_print.py
           (szczelnosc, zdegenerowane, samoprzeciecia, sciany wnek) - ta sama kontrola, co pliki z Pythona.
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

_args = [a for a in sys.argv[1:] if not a.startswith("--")]
html = _args[0] if _args else os.path.join(HERE, "artifact", "zebrowana_kolekcja.html")
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

# --- jajko: warianty obrysu przy tym samym wnetrzu
print("jajko: warianty OBRYSU (wnetrze i szew stale):")
EV = J["egg_var"]; zv = np.array(EV["zs"]); d0 = EV["domyslny"]
cav0 = np.maximum(np.array(d0["cup"]), np.array(d0["cap"]))
zc = np.linspace(BE.FLOOR, BE.FLOOR + BE.EGG_H, 400)                                   # jajko niespodzianka 44 x 68 w wnece (jak w build_egg.py)
tt = np.clip(np.abs(zc - (BE.FLOOR + BE.EGG_H / 2)) / (BE.EGG_H / 2), 0, 1)
re_ = (BE.EGG_D / 2) * np.clip(1 - tt ** 2.3, 0, None) ** (1 / 2.3)
gap_py = float((np.maximum(BE.cav_cup_r(zc), BE.cav_cap_r(zc)) - re_).min())
for name, v in EV.items():
    if name == "zs": continue
    cup, cap, R = np.array(v["cup"]), np.array(v["cap"]), np.array(v["R"])
    check(f"  {name}: wneka miseczki i czapki identyczna z domyslna (max |d|)", float(max(np.abs(cup - np.array(d0["cup"])).max(), np.abs(cap - np.array(d0["cap"])).max())), 0.0)
    mcup = (zv >= v["floor"]) & (zv <= v["ZS"]); mcap = (zv >= v["Z0"]) & (zv < v["ceil"])
    check(f"  {name}: ujemny zapas scianki miseczki (min. grubosc >= {v['wallCup']})", float(max(0.0, v["wallCup"] - (R - cup)[mcup].min() - 1e-6)), 0.0)
    check(f"  {name}: ujemny zapas scianki czapki (min. grubosc >= 2,0)", float(max(0.0, 2.0 - (R - cap)[mcap].min() - 1e-6)), 0.0)
    dom = (R - np.array(v["Rshape"]) > 1e-6); dom = dom[1:] & dom[:-1]            # tylko odcinki, gdzie obrys dobudowuje wnetrze (bieguny jajka maja z natury strome zbocza)
    sl = np.abs(np.diff(R)) / np.diff(zv)
    check(f"  {name}: dobudowa obrysu bez uskokow i nawisow (max |dR/dz| <= 1,4)", float(sl[dom].max()) if dom.any() else 0.0, 1.4, "")
    cav = np.maximum(cup, cap)
    gap = float((cav[(zv >= BE.FLOOR) & (zv <= BE.FLOOR + BE.EGG_H)]).min())
    ok_nan = v["nan"] == 0 and v["tris"] > 1000
    ok &= ok_nan
    print(f"  {'PASS' if ok_nan else 'FAIL'}  {name}: {v['tris']} tr., {v['w']:.1f} x {v['h']:.1f} mm, deficyt obrysu {v['deficit']:.2f} mm, ostrzezenia: {v['warn'] or 'brak'}")
check("jajko: wariant domyslny bez ostrzezen", float(len(d0["warn"])), 0, "")
check("jajko: wariant domyslny: deficyt obrysu", d0["deficit"], 0.02)
check("jajko: wariant szeroki: szerokosc ~ eggW + rowek", abs(EV["szeroki"]["w"] - 66.8), 0.8)
check("jajko: wariant szeroki: wysokosc ~ eggH", abs(EV["szeroki"]["h"] - 100.0), 1.2)
check("jajko: wariant ostry: wysokosc ~ eggH", abs(EV["ostry"]["h"] - 110.0), 1.2)
check("jajko: min. luz jajka niespodzianki do scian (wnetrze JS vs Python, wszystkie warianty identyczne)",
      abs(float((cav0[(zv >= BE.FLOOR) & (zv <= BE.FLOOR + BE.EGG_H)]).min()) - float(np.maximum(BE.cav_cup_r(zv), BE.cav_cap_r(zv))[(zv >= BE.FLOOR) & (zv <= BE.FLOOR + BE.EGG_H)].min())), 1e-4)
print(f"  (min. luz 44 x 68 mm do scian wnetrza, Python: {gap_py:.2f} mm)")

# --- dynia: osobna szerokosc i wysokosc
print("dynia: szerokosc i wysokosc osobno:")
DV = J["dyn_var"]
for name, v in DV.items():
    wexp = v["P"].get("width", 100.0); hexp = v["P"].get("height", 65.0)
    check(f"  {name}: szerokosc korpusu = {wexp}", abs(v["w"] - wexp), 1.0)
    check(f"  {name}: wysokosc korpusu = {hexp}", abs(v["h"] - hexp), 1.0)
    ok &= not v["warn"]

# --- regresja: obciecie siatki obliczen (szeroki korpus / czapka musza byc symetryczne w X i w osi glebokosci)
print("regresja: brak obciecia szerokich korpusow i czapek:")
for k, v in J["clip"].items():
    check(f"  {k}: |szerokosc X - glebokosc| (obciecie siatki = dziura)", abs(v["xs"] - v["zs"]), 1.0)
check("  krolik_52: szerokosc ~ 52 + rowek", abs(J["clip"]["krolik_52"]["xs"] - 52.8), 1.0)
check("  krasnal_hat26: szerokosc czapki ~ 52 (hatRb 26, siatka 1 mm)", abs(J["clip"]["krasnal_hat26"]["xs"] - 52.0), 1.5)

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

if "--print" in sys.argv:
    import tempfile, glob
    import verify_print as VP
    tmp = tempfile.mkdtemp()
    t1 = time.time()
    subprocess.run(["node", os.path.join(HERE, "test_artifact.js"), html, "--stl", tmp, "all"], capture_output=True, check=True, text=True, timeout=1800)
    files = sorted(glob.glob(os.path.join(tmp, "*.stl")))
    print(f"eksport STL z podgladu: {len(files)} plikow, {time.time() - t1:.0f} s; kontrola druku (verify_print):")
    for f in files:
        r = VP.check(f)
        ok &= r["ok"]
        print(f"  {'PASS' if r['ok'] else 'FAIL'}  {r['file']:30s} {r['tris']:>7d} tr.  skl {r['components']}  brz/nm {r['boundary_edges']}/{r['nonmanifold_edges']}  scisk. {r.get('pinched_vertices', '-')}  "
              f"przeciecia {r.get('self_intersections', '-')}  scianka {r.get('wall_p1_mm')}" + "".join("  !! " + x for x in r["fail"]) + "".join("  ~ " + x for x in r["warn"]))

print("\nWYNIK:", "OK" if ok else "BLAD", f"({time.time() - t0:.0f} s)")
sys.exit(0 if ok else 1)
