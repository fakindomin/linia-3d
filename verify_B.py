import sys, os
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
from lib import OUT, n_ribs, overhang_report
names = ["wazon_butelka","wazon_owal","wazon_walec","swiecznik_tealight","swiecznik_swieca",
         "doniczka_S","doniczka_M","doniczka_L","podstawka_S","podstawka_M","podstawka_L","sloik","sloik_pokrywa","sloik_galka",
         "jajko_M_miseczka","jajko_M_czapka","jajko_S_miseczka","jajko_S_czapka",
         "bombka_okragla_60","bombka_okragla_80","bombka_okragla_100","bombka_kropla",
         "choinka_podstawa","choinka_1","choinka_2","choinka_3","choinka_4","choinka_gwiazda"]
print(f"{'plik':28s} {'wymiary [mm]':24s} {'trojk.':>8s} {'MB':>5s} wt    spojn skl obj[cm3]")
bad = 0
for n in names:
    f = f"{OUT}/{n}.stl"
    m = trimesh.load(f, process=True)
    comps = len(m.split(only_watertight=False))
    e = m.extents
    ok = m.is_watertight and m.is_winding_consistent and comps == 1 and m.volume > 0 and os.path.getsize(f) < 25e6 and m.bounds[0][2] > -0.01 and m.bounds[0][2] < 0.01
    bad += (not ok)
    print(f"{n+'.stl':28s} {e[0]:6.1f} x {e[1]:5.1f} x {e[2]:5.1f}  {len(m.faces):8,d} {os.path.getsize(f)/1e6:5.1f}  {str(m.is_watertight):5s} {str(m.is_winding_consistent):5s} {comps:2d} {m.volume/1000:8.1f}  {'OK' if ok else 'PROBLEM'}")
print("problemy:", bad)

def rib_check(name, z, expect, label=""):
    m = trimesh.load(f"{OUT}/{name}.stl", process=True)
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    lines = sorted(sec.discrete, key=lambda l: -np.mean(np.hypot(np.array(l)[:, 0], np.array(l)[:, 1])))
    pts = np.array(lines[0])[:, :2]
    th = np.arctan2(pts[:, 1], pts[:, 0]); r = np.hypot(pts[:, 0], pts[:, 1])
    o = np.argsort(th); th, r = th[o], r[o]
    grid = np.linspace(-np.pi, np.pi, 4096, endpoint=False)
    rg = np.interp(grid, th, r, period=2 * np.pi)
    sp = np.abs(np.fft.rfft(rg - rg.mean()))
    k = int(np.argmax(sp[5:200]) + 5)
    F = np.fft.rfft(rg); F[: max(k // 2, 1)] = 0
    rr = np.fft.irfft(F, 4096)
    pp = np.percentile(rr, 99) - np.percentile(rr, 1)
    rm = rg.mean()
    flag = "OK" if (k == expect and 1.2 <= pp <= 1.75) else "SPRAWDZ"
    print(f"{name:22s} z={z:6.1f}: zeber {k:3d} (oczek. {expect:3d}) | rozstaw {2*np.pi*rm/k:4.2f} mm | ampl. p-p {pp:4.2f} mm | R sr. {rm:5.1f}  {flag} {label}")
print("\nzebra (amplituda +-0,8 => p-p ~1,6):")
for args in [("wazon_butelka", 30, 60), ("wazon_butelka", 125, 20), ("wazon_owal", 30, 64), ("wazon_owal", 108, 32), ("wazon_walec", 20, 60), ("wazon_walec", 70, 60),
             ("swiecznik_tealight", 3, 54), ("swiecznik_tealight", 22, 27), ("swiecznik_tealight", 49, 54),
             ("swiecznik_swieca", 4, 54), ("swiecznik_swieca", 19, 27), ("swiecznik_swieca", 38, 36),
             ("doniczka_S", 25, 50), ("doniczka_M", 35, 64), ("doniczka_L", 45, 80), ("podstawka_M", 5, 76), ("sloik", 35, 66), ("sloik_pokrywa", 2, 66), ("sloik_galka", 9, 22),
             ("jajko_M_miseczka", 12, 40), ("jajko_M_czapka", 20, 40), ("jajko_S_miseczka", 10, 30), ("jajko_S_czapka", 14, 30),
             ("bombka_okragla_60", 24, 55), ("bombka_okragla_80", 32, 74), ("bombka_okragla_100", 40, 92), ("bombka_kropla", 24, 56),
             ("choinka_podstawa", 2.5, 39), ("choinka_1", 14, 52), ("choinka_2", 12, 43), ("choinka_3", 10, 35), ("choinka_4", 8, 27)]:
    try:
        rib_check(*args)
    except Exception as ex:
        print(args, "blad", ex)
# gladki pas wazonu walec
m = trimesh.load(f"{OUT}/wazon_walec.stl")
sec = m.section(plane_origin=[0, 0, 44], plane_normal=[0, 0, 1]); l = max(sec.discrete, key=lambda l: len(l)); r = np.hypot(l[:, 0], l[:, 1])
print(f"wazon_walec gladki pas z=44: R {r.min():.2f}..{r.max():.2f} (zebra znikaja)")
