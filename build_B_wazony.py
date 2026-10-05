"""Grupa B - wazony (3 sylwetki) i swieczniki (tealight LED, swieca stozkowa). Bryly obrotowe ze zebrami (rozstaw ~3,4 mm).
 wazon_butelka.stl (150), wazon_owal.stl (120), wazon_walec.stl (90), swiecznik_tealight.stl (58), swiecznik_swieca.stl (66)"""
import sys, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rev import *

VOX = 0.35
T_WALL = 3.0           # nominalna grubosc scianki wazonu (w dolinie zeber ~2,2 mm)
FLOOR_V = 4.0


def vase(name, pts, Ns, trans, quiet, zf=FLOOR_V, label="", t=T_WALL, fil=1.0, build=True):
    Rb = Prof(pts)                                   # profil bazowy (bez zaokraglenia gornej krawedzi)
    Ro = Prof(with_top_fillet(pts, fil))
    Rin = offset_in(Rb, t, zf, Rb.z1, n_ext=2.0)
    check_profile(Ro, Rin, name)
    if not build:
        return Ro, Rin
    rmax = float(Ro(np.linspace(Ro.z0, Ro.z1, 3000)).max())
    axes, (X, Y, Z) = rev_grid(rmax, Ro.z1 + 1.5, VOX)
    F = rev_F(X, Y, Z, Ro, Ns, trans, quiet, zlo=0.0, zhi=Ro.z1)
    F = np.minimum(F, -cav_F(X, Y, Z, Rin, zf)).astype(np.float32)
    return finish(F, axes, VOX, f"{name}.stl", label)


def holder(name, pts, pocket_R, zf, Ns, trans, quiet, label="", fil=1.0, lead=0.9, build=True):
    Ro = Prof(with_top_fillet(pts, fil))
    ztop = Ro.z1
    Rin = Prof([(zf, pocket_R), (ztop - lead - 0.2, pocket_R), (ztop + 1.0, pocket_R + lead + 1.2)])    # lekki skos wejscia
    check_profile(Ro, Rin, name)
    if not build:
        return
    rmax = float(Ro(np.linspace(Ro.z0, Ro.z1, 3000)).max())
    axes, (X, Y, Z) = rev_grid(rmax, ztop + 1.5, VOX)
    F = rev_F(X, Y, Z, Ro, Ns, trans, quiet, zlo=0.0, zhi=ztop)
    F = np.minimum(F, -cav_F(X, Y, Z, Rin, zf)).astype(np.float32)
    return finish(F, axes, VOX, f"{name}.stl", label)


SPEC = {}

# ---------- wazon butelka H150 ----------
SPEC["wazon_butelka"] = dict(
    pts=[(0, 27.6), (1.6, 29.2), (8, 30.7), (30, 31.6), (48, 31.0), (64, 28.0), (80, 20.0), (92, 13.2), (102, 11.0), (116, 10.5), (150, 10.5)],
    Ns=[60, 20], trans=[(66, 94)], quiet=[(143, 152)], label="wazon na suche kwiaty; wneka otwarta u gory, dno 4 mm")
# ---------- wazon owal H120 ----------
SPEC["wazon_owal"] = dict(
    pts=[(0, 18.5), (1.6, 20.1), (12, 27.2), (26, 32.2), (44, 34.2), (60, 33.0), (78, 28.3), (96, 21.2), (110, 16.8), (120, 15.6)],
    Ns=[64, 32], trans=[(62, 90)], quiet=[], label="wazon na suche kwiaty; wneka otwarta u gory")
# ---------- wazon walec H90 ----------
SPEC["wazon_walec"] = dict(
    pts=[(0, 30.4), (1.6, 32.0), (88, 32.0), (90, 32.0)],
    Ns=[60], trans=[], quiet=[(41, 47)], label="wazon na suche kwiaty; gladki pas w polowie")

HOLD = {}
# ---------- swiecznik tealight (LED 38 mm) ----------
HOLD["swiecznik_tealight"] = dict(
    pts=[(0, 26.2), (1.5, 27.7), (5, 28.0), (9, 24.0), (13, 18.6), (17, 16.2), (28, 15.8), (36, 19.5), (44, 25.5), (52, 27.8), (58, 28.0)],
    pocket_R=19.8, zf=42.0, Ns=[54, 27, 54], trans=[(8, 16), (30, 42)], quiet=[(53, 60)],
    label="na tealight LED o srednicy do 39 mm; gniazdo 39,6 x 16 mm; tylko swiece LED")
# ---------- swiecznik swieca stozkowa ----------
HOLD["swiecznik_swieca"] = dict(
    pts=[(0, 27.8), (1.5, 29.3), (5, 29.8), (9, 24.0), (14, 15.8), (19, 13.4), (24, 14.6), (30, 18.8), (36, 20.5), (42, 19.6), (50, 17.2), (56, 16.4), (60, 17.0), (66, 17.6)],
    pocket_R=11.3, zf=48.0, Ns=[54, 27, 36], trans=[(8, 14), (21, 29)], quiet=[(61, 68)],
    label="na swiece o srednicy do 22,6 mm; gniazdo 18 mm; tylko swiece LED")

if __name__ == "__main__":
    T0 = time.time()
    names = [a for a in sys.argv[1:] if not a.startswith("-")]
    only_check = "-c" in sys.argv
    for nm in names or list(SPEC) + list(HOLD):
        t = time.time()
        if nm in SPEC:
            vase(nm, build=not only_check, **SPEC[nm])
        else:
            holder(nm, build=not only_check, **HOLD[nm])
        print(f"  {nm}: {time.time() - t:.0f} s")
    print(f"czas {time.time() - T0:.0f} s")
