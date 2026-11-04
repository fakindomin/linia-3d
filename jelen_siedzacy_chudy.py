"""Jelen siedzacy 'chudy': to samo co jelen_siedzacy.py, ale szczuplejszy (tulow, udo, nogi wezsze), dluzsza cienka szyja i glowa wyzej - jak jelen_stojacy_chudy.py;
ta sama glowa, uszy, poroze, uniesiony pysk i skala S_CH (glowa jak u chudego stojacego). Uklad: x = przod, y = bok, z = gora; z = 0 to stol.
  python3 jelen_siedzacy_chudy.py          -> out/jelen_siedzacy_chudy.stl"""
import sys, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jelen import smin, cap, ell, glowa, uszy_poroze, head_xf, build, checks, SM
from jelen_chudy import S_CH, HEAD_PITCH

HEAD_DX, HEAD_DZ = -0.5, 0.7        # glowa wyzej niz w jelen_siedzacy.py (dluga szyja)
NECK_TOP = (10.5, 30.0)             # koniec szyi (x, z): os obrotu glowy


def design(P):
    X, Y, Z = P
    Ph = head_xf(P, HEAD_DX, HEAD_DZ, HEAD_PITCH, NECK_TOP)
    D = ell(P, (-5.5, 0, 6.0), (9.8, 8.8, 8.0))                                # siedzisko (splaszczone przez stol -> plama styku)
    D = smin(D, cap(P, (-4.0, 0, 10.0), (6.0, 0, 25.0), 8.2, 6.6), 5 * SM)    # tulow pochylony do przodu, szczuply
    D = smin(D, ell(P, (7.0, 0, 23.5), (6.6, 7.0, 7.6)), 5 * SM)                # piers
    D = smin(D, cap(P, (7.8, 0, 24.5), (NECK_TOP[0], 0, NECK_TOP[1]), 5.4, 4.5), 4.5 * SM)   # szyja dluga i cienka
    D = glowa(D, Ph)
    D = smin(D, ell(P, (-15.5, 0, 6.0), (3.0, 2.6, 3.2)), 2.5 * SM)            # ogon
    for s in (-1.0, 1.0):
        D = smin(D, ell(P, (-2.5, s * 5.6, 8.0), (7.0, 3.6, 6.6)), 4 * SM)      # udo
        D = smin(D, cap(P, (0.0, s * 6.6, 7.0), (3.2, s * 8.2, 3.0), 3.4, 2.9), 3.5 * SM)    # podudzie wysuniete do przodu
        D = smin(D, ell(P, (3.6, s * 8.6, 2.9), (4.2, 2.9, 2.9)), 2.5 * SM)     # lapa
        D = smin(D, cap(P, (10.5, s * 5.0, 17.0), (13.5, s * 5.4, 0.0), 3.7, 3.1), 3 * SM)   # przednia noga prosta
        D = uszy_poroze(D, Ph, s)
    return D


if __name__ == "__main__":
    t0 = time.time()
    m = build(S_CH, name="jelen_siedzacy_chudy.stl", fn=design, zhi=62.0, note="jelen siedzacy chudy, skala jak jelen_stojacy_chudy")
    ok = checks(m, label="jelen siedzacy chudy", height=None, min_feet=60.0)
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
