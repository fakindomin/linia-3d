"""Jelen lezacy 'chudy': to samo co jelen_lezacy.py, ale szczuplejszy (tulow, piers, zad, nogi wezsze), dluzsza cienka szyja i glowa wyzej - jak jelen_stojacy_chudy.py;
ta sama glowa, uszy, poroze, uniesiony pysk i skala S_CH. Uklad: x = przod, y = bok, z = gora; z = 0 to stol.
  python3 jelen_lezacy_chudy.py          -> out/jelen_lezacy_chudy.stl"""
import sys, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jelen import smin, cap, ell, glowa, uszy_poroze, head_xf, build, checks, SM
from jelen_chudy import S_CH, HEAD_PITCH

HEAD_DX, HEAD_DZ = -0.5, -4.5       # glowa wyzej niz w jelen_lezacy.py (dluga szyja)
NECK_TOP = (11.0, 25.0)             # koniec szyi (x, z): os obrotu glowy


def design(P):
    X, Y, Z = P
    Ph = head_xf(P, HEAD_DX, HEAD_DZ, HEAD_PITCH, NECK_TOP)
    D = ell(P, (-2.0, 0, 6.2), (14.0, 8.6, 7.6))                               # tulow (splaszczony przez stol), szczuply
    D = smin(D, ell(P, (7.2, 0, 9.0), (7.6, 7.4, 7.8)), 5 * SM)                # piers
    D = smin(D, ell(P, (-9.0, 0, 6.6), (7.4, 8.4, 6.6)), 5 * SM)               # zad
    D = smin(D, cap(P, (7.5, 0, 11.0), (NECK_TOP[0], 0, NECK_TOP[1]), 5.6, 4.5), 4.5 * SM)   # szyja wyprostowana, dluga i cienka
    D = glowa(D, Ph)
    D = smin(D, ell(P, (-16.0, 0, 7.5), (3.0, 2.6, 3.0)), 2.5 * SM)            # ogon
    for s in (-1.0, 1.0):
        D = smin(D, ell(P, (-6.2, s * 6.6, 6.4), (6.8, 3.6, 5.8)), 4 * SM)      # udo tylnej nogi
        D = smin(D, ell(P, (-0.5, s * 7.6, 2.9), (4.8, 2.9, 2.8)), 2.5 * SM)    # tylna stopa
        D = smin(D, cap(P, (6.5, s * 5.0, 5.6), (15.0, s * 5.4, 3.0), 3.4, 2.8), 3.5 * SM)  # przednia noga podwinieta do przodu
        D = smin(D, ell(P, (16.0, s * 5.5, 2.9), (3.2, 2.9, 2.9)), 2.0 * SM)     # przednie kopytko
        D = uszy_poroze(D, Ph, s)
    return D


if __name__ == "__main__":
    t0 = time.time()
    m = build(S_CH, name="jelen_lezacy_chudy.stl", fn=design, zhi=62.0, note="jelen lezacy chudy, skala jak jelen_stojacy_chudy")
    ok = checks(m, label="jelen lezacy chudy", height=None, min_feet=100.0)
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
