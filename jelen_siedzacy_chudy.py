"""Jelen siedzacy 'chudy': to samo co jelen_siedzacy.py, ale szczuplejszy (tulow, udo, nogi wezsze), dluzsza cienka szyja i glowa wyzej - jak jelen_stojacy_chudy.py;
wezsza glowa i mniejsze uszy (glowa_chuda, uszy_chude), to samo poroze, uniesiony pysk i skala S_CH (glowa jak u chudego stojacego). Uklad: x = przod, y = bok, z = gora; z = 0 to stol.
  python3 jelen_siedzacy_chudy.py          -> out/jelen_siedzacy_chudy.stl"""
import sys, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jelen import smin, cap, ell, glowa_chuda, uszy_poroze_chude, ogon_kulka, head_xf, build, checks, SM
from jelen_chudy import S_CH, HEAD_PITCH

HEAD_DX, HEAD_DZ = -0.5, 0.7        # glowa wyzej niz w jelen_siedzacy.py (dluga szyja)
NECK_TOP = (10.5, 30.0)             # koniec szyi (x, z): os obrotu glowy


def design(P):
    X, Y, Z = P
    Ph = head_xf(P, HEAD_DX, HEAD_DZ, HEAD_PITCH, NECK_TOP)
    D = ell(P, (-5.5, 0, 6.0), (9.6, 7.4, 8.2))                                # siedzisko (splaszczone przez stol -> plama styku), waskie
    D = smin(D, cap(P, (-4.0, 0, 10.0), (6.0, 0, 25.0), 7.2, 5.8), 5 * SM)    # tulow pochylony do przodu, waski, okragly grzbiet
    D = smin(D, ell(P, (7.0, 0, 23.5), (6.4, 6.2, 7.8)), 5 * SM)                # piers
    D = smin(D, cap(P, (7.8, 0, 24.5), (NECK_TOP[0], 0, NECK_TOP[1]), 4.9, 4.0), 4.5 * SM)   # szyja dluga i cienka
    D = glowa_chuda(D, Ph)
    D = ogon_kulka(D, P, (-16.2, 0, 3.4))                                   # ogon: pompon-kulka, lekko wciśnięty w stol
    for s in (-1.0, 1.0):
        D = smin(D, ell(P, (-2.5, s * 4.6, 8.0), (6.8, 3.2, 6.6)), 4 * SM)      # udo wpasowane w obrys tulowia
        D = smin(D, cap(P, (0.0, s * 5.6, 7.0), (3.2, s * 7.0, 3.0), 3.2, 2.7), 3.5 * SM)    # podudzie wysuniete do przodu
        D = smin(D, ell(P, (3.6, s * 7.2, 2.8), (4.2, 2.6, 2.8)), 2.5 * SM)     # lapa
        D = smin(D, cap(P, (10.5, s * 4.4, 17.0), (13.5, s * 4.8, 0.0), 3.5, 2.9), 3 * SM)   # przednia noga prosta
        D = uszy_poroze_chude(D, Ph, s)
    return D


if __name__ == "__main__":
    t0 = time.time()
    m = build(S_CH, name="jelen_siedzacy_chudy.stl", fn=design, zhi=62.0, note="jelen siedzacy chudy, skala jak jelen_stojacy_chudy")
    ok = checks(m, label="jelen siedzacy chudy", height=None, min_feet=60.0)
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
