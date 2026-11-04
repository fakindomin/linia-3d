"""Jelen siedzacy, gladki, zabawkowy: to samo co jelen.py (glowa, uszy, poroze, skala S_STD), inny tulow: siedzisko na ziemi, tulow pochylony do przodu,
tylne lapy wysuniete do przodu po bokach, przednie nogi proste. Uklad: x = przod, y = bok, z = gora; z = 0 to stol.
  python3 jelen_siedzacy.py          -> out/jelen_siedzacy.stl"""
import sys, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jelen
from jelen import smin, cap, ell, glowa, uszy_poroze, build, checks, S_STD, SM

HEAD_DX, HEAD_DZ = -0.5, -3.5     # przesuniecie glowy wzgledem stojacego (glowa nizej: tulow siedzacego jest nizszy)


def design(P):
    X, Y, Z = P
    Ph = (X - HEAD_DX, Y, Z - HEAD_DZ)                                         # wspolrzedne glowy (glowa, uszy i poroze identyczne jak w jelen.py)
    D = ell(P, (-5.5, 0, 6.3), (10.5, 10.2, 8.2))                              # siedzisko (splaszczone przez stol -> plama styku)
    D = smin(D, cap(P, (-4.0, 0, 10.5), (6.0, 0, 24.0), 9.6, 8.0), 5 * SM)    # tulow pochylony do przodu
    D = smin(D, ell(P, (7.0, 0, 22.5), (7.2, 8.2, 8.4)), 5 * SM)               # piers
    D = smin(D, cap(P, (7.8, 0, 23.5), (11.0, 0, 28.0), 6.2, 5.8), 4.5 * SM)   # szyja
    D = glowa(D, Ph)
    D = smin(D, ell(P, (-16.0, 0, 6.0), (3.0, 2.6, 3.2)), 2.5 * SM)            # ogon
    for s in (-1.0, 1.0):
        D = smin(D, ell(P, (-2.5, s * 6.2, 8.5), (7.6, 4.2, 7.2)), 4 * SM)      # udo
        D = smin(D, cap(P, (0.0, s * 7.2, 7.5), (3.4, s * 9.0, 3.2), 4.0, 3.3), 3.5 * SM)   # podudzie wysuniete do przodu
        D = smin(D, ell(P, (3.8, s * 9.4, 3.0), (4.6, 3.2, 3.0)), 2.5 * SM)     # lapa
        D = smin(D, cap(P, (10.0, s * 5.4, 16.0), (14.0, s * 5.8, 0.0), 4.3, 3.5), 3 * SM)   # przednia noga prosta
        D = uszy_poroze(D, Ph, s)
    return D


if __name__ == "__main__":
    t0 = time.time()
    m = build(S_STD, name="jelen_siedzacy.stl", fn=design, note="jelen siedzacy, gladki, skala jak jelen_stojacy")
    ok = checks(m, label="jelen siedzacy", height=None, min_feet=100.0)
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
