"""Jelonek (mlody jelen), gladki, zabawkowy: ta sama glowa i skala co jelen.py (S_STD), ale mniejsze ciało, krotkie nogi, wieksze uszy, male paczki zamiast poroza.
Uklad: x = przod, y = bok, z = gora; z = 0 to stol.
  python3 jelen_jelonek.py          -> out/jelen_jelonek.stl"""
import sys, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jelen import smin, cap, ell, glowa, uszy, build, checks, S_STD, SM

HEAD_DX, HEAD_DZ = -2.0, -7.5     # glowa nizej i blizej tulowia niz u stojacego (szyja krotka)
LIFT = 2.0                        # tulow, glowa i uszy podniesione nad stol (dluzsze nogi): klin pod brzuchem (nawisy.py) nie dotyka stolu
EAR_K = 1.25                      # uszy wieksze niz u doroslego
BUDS = True                       # male paczki poroza (False = bez poroza)


def design(P):
    X, Y, Z0 = P
    Z = Z0 - LIFT                                                              # wspolrzedne tulowia (podniesionego o LIFT)
    P, Ph = (X, Y, Z), (X - HEAD_DX, Y, Z - HEAD_DZ)                           # Ph: wspolrzedne glowy (ta sama glowa i uszy co w jelen.py)
    D = ell(P, (-1.0, 0, 13.8), (11.5, 8.8, 8.8))                              # tulow (maly)
    D = smin(D, ell(P, (5.5, 0, 15.5), (7.5, 7.8, 8.0)), 4.5 * SM)             # barki
    D = smin(D, ell(P, (-7.0, 0, 14.0), (6.8, 8.0, 7.8)), 4.5 * SM)            # zad
    D = smin(D, cap(P, (4.0, 0, 16.0), (9.5, 0, 24.0), 6.2, 5.6), 4.0 * SM)    # szyja
    D = glowa(D, Ph)
    D = smin(D, ell(P, (-13.5, 0, 15.5), (2.6, 2.3, 2.8)), 2.5 * SM)           # ogon
    for s in (-1.0, 1.0):
        D = smin(D, cap((X, Y, Z0), (6.5, s * 5.6, 11.0 + LIFT), (7.3, s * 6.0, 0.0), 4.1, 3.4), 3.5 * SM)    # przednie nogi: krotkie kolki
        D = smin(D, cap((X, Y, Z0), (-6.5, s * 5.8, 11.0 + LIFT), (-7.3, s * 6.2, 0.0), 4.2, 3.5), 3.5 * SM)  # tylne
        D = uszy(D, Ph, s, EAR_K)
        if BUDS:                                                                 # paczki: krotkie, pod katem ok. 55 st. od poziomu
            D = smin(D, cap(Ph, (12.5, s * 3.4, 38.3), (12.9, s * 5.6, 41.6), 1.9, 1.4), 1.2 * SM)
    return D


if __name__ == "__main__":
    t0 = time.time()
    m = build(S_STD, name="jelen_jelonek.stl", fn=design, note="jelonek, gladki, skala glowy jak jelen_stojacy")
    ok = checks(m, label="jelonek", height=None, min_feet=100.0)
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
