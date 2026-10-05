"""Grupa B - jajka-matrioszki M i S (wchodza do jajka L = jajko_miseczka + dowolna czapka jajka, M do L, S do M).
 jajko_M_miseczka.stl, jajko_M_czapka.stl, jajko_S_miseczka.stl, jajko_S_czapka.stl"""
import sys, time
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matrioszka import *

T0 = time.time()
L = egg_L()
sM = solve_scale(L, make_M, 0.8)
M = make_M(sM)
sS = solve_scale(M, make_S, 0.8)
S = make_S(sS)
for nm, e in (("M", M), ("S", S)):
    t = time.time()
    axes, Fcup, Fcap = e.fields()
    print(f"{nm}: skala {e.s:.4f}, N={e.N}, kolizja miseczka/czapka (siatka): {int(((Fcup > 0) & (Fcap > 0)).sum())} vox")
    cup = decimate(mesh_from_F(Fcup, axes, VOX), 200000, label=f"{nm}-miseczka")
    cap = decimate(mesh_from_F(Fcap, axes, VOX), 200000, label=f"{nm}-czapka")
    save(cup, f"jajko_{nm}_miseczka.stl", True, "otworem do gory; kolnierz")
    save(cap, f"jajko_{nm}_czapka.stl", True, "otworem do dolu (brzeg na stole)")
    print(f"  {nm}: {time.time() - t:.0f} s")
print(f"czas {time.time() - T0:.0f} s")
