"""Jelen lezacy, gladki, zabawkowy: ta sama glowa, uszy, poroze i skala co jelen.py (S_STD); tulow lezy na stole, nogi podwiniete (przednie wysuniete do przodu,
tylne zgiete po bokach zadu), szyja wyprostowana. Uklad: x = przod, y = bok, z = gora; z = 0 to stol.
  python3 jelen_lezacy.py          -> out/jelen_lezacy.stl"""
import sys, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jelen import smin, cap, ell, glowa, uszy_poroze, head_xf, build, checks, S_STD, SM

HEAD_DX, HEAD_DZ = 0.0, -8.5      # glowa nizej niz u stojacego


def design(P):
    X, Y, Z = P
    Ph = head_xf(P, HEAD_DX, HEAD_DZ, pivot=(11.5, 23.0))                      # wspolrzedne glowy (glowa, uszy i poroze jak w jelen.py), pysk uniesiony
    D = ell(P, (-2.0, 0, 6.6), (15.0, 10.2, 8.2))                              # tulow (splaszczony przez stol -> duza plama styku)
    D = smin(D, ell(P, (7.0, 0, 9.5), (8.5, 9.0, 8.5)), 5 * SM)                # piers
    D = smin(D, ell(P, (-9.5, 0, 7.0), (8.0, 9.8, 7.2)), 5 * SM)               # zad
    D = smin(D, cap(P, (7.5, 0, 12.0), (11.5, 0, 23.0), 6.8, 5.9), 4.5 * SM)   # szyja wyprostowana
    D = glowa(D, Ph)
    D = smin(D, ell(P, (-17.0, 0, 8.0), (3.0, 2.6, 3.0)), 2.5 * SM)            # ogon
    for s in (-1.0, 1.0):
        D = smin(D, ell(P, (-6.5, s * 8.0, 7.0), (7.4, 4.2, 6.4)), 4 * SM)      # udo tylnej nogi
        D = smin(D, ell(P, (-0.5, s * 9.0, 3.0), (5.2, 3.2, 3.0)), 2.5 * SM)    # tylna stopa
        D = smin(D, cap(P, (6.0, s * 5.2, 6.0), (15.5, s * 5.6, 3.2), 4.0, 3.2), 3.5 * SM)  # przednia noga podwinieta do przodu
        D = smin(D, ell(P, (16.5, s * 5.8, 3.1), (3.6, 3.2, 3.1)), 2.0 * SM)    # przednie kopytko
        D = uszy_poroze(D, Ph, s)
    return D


if __name__ == "__main__":
    t0 = time.time()
    m = build(S_STD, name="jelen_lezacy.stl", fn=design, note="jelen lezacy, gladki, skala jak jelen_stojacy")
    ok = checks(m, label="jelen lezacy", height=None, min_feet=100.0)
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
