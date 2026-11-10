"""Zgodnosc rdzenia artefaktu (artifact/swieta_core.js) z Pythonem: etykieta.py, foremki_piernik.py, czubek_choinkowy.py.
Wymaga wczesniejszego `node artifact/test_swieta.js` (zapisuje out/js/*.stl i out/js/_info.json). Kontrola: objetosc (etykieta/czubek 0,3%, foremka 0,6%),
wymiary (0,15 mm), STL z przegladarki szczelny, 1 skladowa, verify_print bez bledow. Kod wyjscia 1 przy rozbieznosci."""
import os, sys, json, subprocess
import numpy as np
import trimesh
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
from shapely import affinity
import etykieta as ET, foremki_piernik as FP, czubek_choinkowy as CZ
import verify_print as VP

if "--run-node" in sys.argv:
    subprocess.run(["node", os.path.join(HERE, "test_swieta.js")], check=True)
info = json.load(open(os.path.join(ROOT, "out", "js", "_info.json")))
bad = 0


def cmp(name, py, tol, py_ext=None, ext_tol=0.15):
    global bad
    js = info[name]
    dv = abs(js["volume"] - py.volume) / py.volume
    ok = dv < tol
    if py_ext is not None:
        de = max(abs(a - b) for a, b in zip(js["extents"], py_ext))
        ok &= de < ext_tol
    else:
        de = 0
    stl = os.path.join(ROOT, "out", "js", name + ".stl")
    m = trimesh.load(stl)
    comps = len(m.split(only_watertight=False))
    r = VP.check(stl, expect_components=1, with_wall=False, with_selfint=(m.faces.shape[0] < 70000))
    ok &= m.is_watertight and comps == 1 and not r["fail"] and js["badEdges"] == 0
    print(f"{'PASS' if ok else 'FAIL'}  {name:30s} V js {js['volume']:10.1f} py {py.volume:10.1f} ({100 * dv:.3f}%), wymiary d = {de:.3f} mm, tri js {js['tris']:,} py {len(py.faces):,}, "
          f"szczelna {m.is_watertight}, skladowe {comps}, verify_print: {r['fail'] or 'ok'}{' warn ' + str(r['warn'])[:80] if r['warn'] else ''}")
    bad += (not ok)


font = ET.Font()
for n, cap, key in (("Ania", 11, "etykieta_Ania_11"), ("Łukasz", 11, "etykieta_Łukasz_11"), ("Babcia Ela", 11, "etykieta_Babcia_Ela_11"), ("Jan", 14, "etykieta_Jan_14")):
    m, _ = ET.build_label(n, cap, font)
    cmp(key, m, 0.003, m.extents)
for k in FP.SHAPES:
    cmp("foremka_" + k, FP.cutter(FP.dough(k)), 0.006, None)
FP.FL_W, FP.FL_T = 8.0, 3.0
S = affinity.scale(FP.dough("renifer"), 1.2, 1.2, origin=(0, 0))
cmp("foremka_renifer_FL8x3_s1.2", FP.cutter(S), 0.006, None)
FP.FL_W, FP.FL_T = 5.0, 2.0
for key, args in (("czubek_18_200_62", (18, 200, 62)), ("czubek_14_160_54", (14, 160, 54)), ("czubek_26_230_80", (26, 230, 80))):
    m, g, M = CZ.build(*args)
    cmp(key, m, 0.003, m.extents, 0.05)
print("ZGODNE" if not bad else f"ROZBIEZNOSCI: {bad}")
sys.exit(1 if bad else 0)
