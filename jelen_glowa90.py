"""Jelen stojacy z glowa obrocona w bok (domyslnie 90 st. w lewo): tulow, nogi, skala S_STD jak w jelen.py; glowa, uszy i poroze (te same funkcje) obrocone
wokol pionowej osi na koncu szyi. Uklad: x = przod, y = lewo, z = gora; z = 0 to stol.
  python3 jelen_glowa90.py          -> out/jelen_stojacy_glowa90.stl"""
import sys, math, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jelen import smin, cap, ell, glowa, uszy_poroze, build, checks, S_STD, SM

TURN = 90.0                 # obrot glowy [st.], dodatni = w lewo (pysk w strone +y)
PIVOT = (10.5, 0.0)         # os obrotu glowy (pion przez koniec szyi), jednostki projektu


def head_coords(P, turn=TURN, pivot=PIVOT):
    """wspolrzedne punktu w ukladzie glowy (taka sama glowa jak w jelen.py): obrot odwrotny o 'turn' wokol pionu przez 'pivot'"""
    X, Y, Z = P
    a = math.radians(turn); c, s = math.cos(a), math.sin(a)
    dx, dy = X - pivot[0], Y - pivot[1]
    return (pivot[0] + c * dx + s * dy, pivot[1] - s * dx + c * dy, Z)


def design(P):
    X, Y, Z = P
    Ph = head_coords(P)
    D = ell(P, (-1.5, 0, 18.8), (14.5, 10.6, 10.4))                          # tulow
    D = smin(D, ell(P, (7.5, 0, 21.0), (9.0, 9.2, 9.6)), 5 * SM)           # barki
    D = smin(D, ell(P, (-9.5, 0, 19.3), (8.2, 9.6, 9.2)), 5 * SM)          # zad
    D = smin(D, cap(P, (5.0, 0, 22.0), (11.5, 0, 31.5), 6.6, 6.0), 4.5 * SM)   # szyja
    D = glowa(D, Ph)                                                         # glowa obrocona
    D = smin(D, ell(P, (-17.5, 0, 22.0), (3.0, 2.6, 3.2)), 2.5 * SM)         # ogon
    for s in (-1.0, 1.0):
        D = smin(D, cap(P, (8.5, s * 5.6, 15.0), (9.5, s * 6.2, 0.0), 4.5, 3.6), 4 * SM)
        D = smin(D, cap(P, (-9.0, s * 6.0, 15.0), (-10.0, s * 6.8, 0.0), 4.6, 3.7), 4 * SM)
        D = uszy_poroze(D, Ph, s)
    return D


if __name__ == "__main__":
    t0 = time.time()
    m = build(S_STD, name="jelen_stojacy_glowa90.stl", fn=design, note="jelen stojacy, glowa obrocona o 90 st., skala S_STD", box=(-25.0, 40.0, -26.0, 30.0))
    ok = checks(m, label="jelen stojacy, glowa 90", height=None, min_feet=100.0)
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
