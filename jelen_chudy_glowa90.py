"""Jelen stojacy chudy ze skreconym lbem (domyslnie 90 st. w lewo): ten sam tulow, nogi, szyja i skala co jelen_chudy.py, glowa z uszami i porozem obrocona wokol pionu
przez koniec szyi (pysk zadarty jak w jelen_chudy.py). Uklad: x = przod, y = lewo, z = gora; z = 0 to stol.
  python3 jelen_chudy_glowa90.py          -> out/jelen_stojacy_chudy_glowa90.stl"""
import sys, time
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jelen import build, checks
import jelen_chudy as C

TURN = 90.0     # skret glowy [st.], dodatni = w lewo, ujemny = w prawo


def design(P):
    return C.design(P, turn=TURN)


if __name__ == "__main__":
    t0 = time.time()
    m = build(C.S_CH, name="jelen_stojacy_chudy_glowa90.stl", fn=design, box=(-25.0, 36.0, -26.0, 30.0), zhi=66.0,
              note="jelen stojacy chudy, glowa skrecona o 90 st., skala jak jelen_stojacy_chudy")
    ok = checks(m, label="jelen chudy, glowa 90", height=None, min_feet=100.0)
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
