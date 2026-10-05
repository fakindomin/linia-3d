"""Przebudowa ZEBROWANYCH czesci wymiennych 5 modeli kluczowych wg STANDARD v1.0 (przyciecie do kopert, wspolne z lowpoly):
 ucho_{prawe,lewe}, ucho_dlugie_{prawe,lewe}, poroze_{prawe,lewe}, ucho_{mis,kot,lis,sowa}_{prawe,lewe}, dynia_ogonek, balwan_nos, balwan_miotla
Korpusy (zebra) bez zmian - kopertami sa tylko czesci."""
import sys, time
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models import *
from parts import ear_flat, antler_flat
import build_figurki as BF
import ears_A as EA
import build_snowman as BSN

T0 = time.time()
L_VIS = BF.L_VIS
for s, nm in ((+1, "prawe"), (-1, "lewe")):
    save(part_mesh(ear_flat(L_VIS), BF.TRIMS[s], True, (-10, 10), (-9, L_VIS + 3), 0.2), f"ucho_{nm}.stl", False, "druk na plecach (plaska strona do stolu)")
    save(part_mesh(ear_flat(L_LONG), BF.TRIMS[s], True, (-10, 10), (-9, L_LONG + 3), 0.2), f"ucho_dlugie_{nm}.stl", False, "druk na plecach; wersja dluga")
save(part_mesh(BF.ant_R, BF.TRIMS[+1], True, (-10, 21), (-9, L_VIS + 3), 0.2), "poroze_prawe.stl", False, "druk na plecach")
save(part_mesh(BF.ant_L, BF.TRIMS[-1], True, (-21, 10), (-9, L_VIS + 3), 0.2), "poroze_lewe.stl", False, "druk na plecach")
for nm in EA.SPECS:
    for s, side_nm in ((+1, "prawe"), (-1, "lewe")):
        save(EA.ear_mesh(nm, s), f"ucho_{nm}_{side_nm}.stl", False, "druk na plecach; czop 5x5x8")
# dynia: ogonek
import build_pumpkin as BP
stem = local_mesh(BP.stem_fn(PUMPKIN.env.sdf), (-12, 12), (-9, BP.STEM_H + 1), (-9, 14), 0.2)
stem_p = stem.copy()
stem_p.apply_transform(np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float))
save(stem_p, "dynia_ogonek.stl", True, "druk do gory nogami: koniec ogonka na stole, czop 5x5 sterczy do gory")
# balwan: nos, miotla
nose = local_mesh(BSN.nose_fn(SNOWMAN.env.sdf, BSN.FR_NOSE), (-6, 6), (-9, BSN.NOSE_L + 1), (-0.6, 9.5), 0.2)
save(nose, "balwan_nos.stl", False, "marchewka: plaski spod na stole, bez podpor")
bf = BSN.broom_flat()
FRB = BSN.FR_BROOM


def broom_fn(a, b, c):
    F_ = np.minimum(bf.F(a, b, c), b + 3.0)
    X_ = FRB.O[0] + a * FRB.A[0] + b * FRB.B[0] + c * FRB.C[0]
    Y_ = FRB.O[1] + a * FRB.A[1] + b * FRB.B[1] + c * FRB.C[1]
    Z_ = FRB.O[2] + a * FRB.A[2] + b * FRB.B[2] + c * FRB.C[2]
    F_ = np.minimum(F_, -(SNOWMAN.env.sdf(X_, Y_, Z_) + GAP))
    return np.maximum(F_, BSN.peg1_F(a, b, c)).astype(np.float32)


broom = local_mesh(broom_fn, (-12, 12), (-9, BSN.BR_TOTAL + 1), (-0.6, 7.0), 0.2)
save(broom, "balwan_miotla.stl", False, "druk na plasko; na wlasne gniazdo 55 st.")
print(f"czas {time.time() - T0:.0f} s")
