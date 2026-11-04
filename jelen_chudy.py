"""Jelen stojacy 'chudy': proporcje bardziej wg wzorca DEER 1 - szczuplejszy, nizszy tulow, nogi rozstawione szerzej (wyzej i dalej od siebie, na brzegu tulowia),
dluga i cienka szyja unoszaca glowe; glowa, uszy i poroze (te same funkcje) jak w jelen.py. Skala S liczona z wysokosci 50 mm (dwa przebiegi).
Uklad: x = przod, y = bok, z = gora; z = 0 to stol.
  python3 jelen_chudy.py          -> out/jelen_stojacy_chudy.stl"""
import sys, math, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jelen import smin, cap, ell, glowa, uszy_poroze, head_xf, build, checks, HEIGHT, SM

S_CH = 0.84                    # skala projektu -> mm (ustawiana tak, by wysokosc = 50 mm; sprawdzana w przebiegu 2)
HEAD_PITCH = 22.0              # glowa uniesiona (pysk do gory) o tyle stopni wokol konca szyi: spod pyska rosnie ku nosowi, jak we wzorcu
PIVOT = (9.0, 36.5)            # os obrotu glowy (x, z) = koniec szyi
HEAD_DX, HEAD_DZ = -3.0, 7.2   # przesuniecie glowy wzgledem jelen.py: wyzej (dluga szyja) i do tylu (pysk nie wystaje dalej niz we wzorcu)
# --- tulow (jednostki projektu) ---
BODY = dict(c=(0.0, 0.0, 14.3), r=(13.0, 9.7, 10.5))       # glowna elipsoida tulowia: szczuply; dol nisko (dolna czesc i tak obcina nawisy.carve: namiot miedzy nogami)
SHOULD = dict(c=(8.0, 0.0, 15.5), r=(7.0, 8.8, 9.7))
RUMP = dict(c=(-8.0, 0.0, 15.0), r=(6.8, 9.2, 9.5))
NECK = ((6.0, 0.0, 19.0), (9.0, 0.0, 36.5), 6.4, 4.6)       # dluga cienka szyja, prawie pionowa
LEG_X, LEG_Y_TOP, LEG_Y_FOOT, LEG_R = 10.8, 6.6, 8.0, (4.2, 3.7)   # nogi: rozstaw przod-tyl +-LEG_X, na boki od LEG_Y_TOP (u gory) do LEG_Y_FOOT (stopy)


def design(P):
    X, Y, Z = P
    Ph = head_xf(P, HEAD_DX, HEAD_DZ, HEAD_PITCH, PIVOT)
    D = ell(P, BODY["c"], BODY["r"])
    D = smin(D, ell(P, SHOULD["c"], SHOULD["r"]), 4.0 * SM)
    D = smin(D, ell(P, RUMP["c"], RUMP["r"]), 4.0 * SM)
    D = smin(D, cap(P, NECK[0], NECK[1], NECK[2], NECK[3]), 4.5 * SM)
    D = glowa(D, Ph)
    D = smin(D, ell(P, (-14.5, 0, 19.5), (3.0, 2.6, 3.2)), 2.5 * SM)         # ogon
    for s in (-1.0, 1.0):
        D = smin(D, cap(P, (LEG_X, s * LEG_Y_TOP, 14.5), (LEG_X + 0.5, s * LEG_Y_FOOT, 0.0), LEG_R[0], LEG_R[1]), 4 * SM)
        D = smin(D, cap(P, (-LEG_X, s * LEG_Y_TOP, 14.5), (-LEG_X - 0.7, s * LEG_Y_FOOT, 0.0), LEG_R[0] + 0.1, LEG_R[1] + 0.1), 4 * SM)
        D = uszy_poroze(D, Ph, s)
    return D


if __name__ == "__main__":
    t0 = time.time()
    kw = dict(fn=design, box=(-25.0, 31.0, -26.0, 26.0), zhi=66.0)
    m = build(1.0, vox=0.3, name="_chudy_probny.stl", target=60000, note="probny", **kw)    # przebieg 1: pomiar wysokosci projektu
    S = HEIGHT / float(m.extents[2])
    print(f"  skala projektu -> {S:.4f} (S_CH = {S_CH})")
    m = build(S, name="jelen_stojacy_chudy.stl", note="jelen stojacy chudy (proporcje wg wzorca), 50 mm", **kw)
    ok = checks(m, label="jelen chudy", height=HEIGHT, min_feet=100.0)
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
