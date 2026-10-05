"""Grupa B - bombki zebrowane: kule 60/80/100 mm i kropla (~120 mm), plaski spod (ciecie kuli pod katem 37 st. = nawis 53 st. od pionu),
szyjka + uszko (plaski pierscien, otwor kroplowy).
 bombka_okragla_60.stl, bombka_okragla_80.stl, bombka_okragla_100.stl, bombka_kropla.stl"""
import sys, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rev import *

CUT = 37.0                  # kat ciecia spodu (od bieguna dolnego): sciana 37 st. od poziomu -> nawis 53 st. od pionu
R_COL = 6.5                 # promien szyjki
COL_H = 4.5                 # szyjka ponad biegunem
LOOP_RO, LOOP_RH, LOOP_T = 6.0, 2.9, 3.2


def sphere_pts(R, th0, th1, n):
    zc = R * math.cos(math.radians(CUT))
    out = []
    for th in np.linspace(math.radians(th0), math.radians(th1), n):
        out.append((zc - R * math.cos(th), R * math.sin(th)))
    return out, zc


def loop_F(X, Y, Z, zl):
    """uszko: plaski pierscien w plaszczyznie x-z (grubosc LOOP_T w y), otwor kroplowy (czubek do gory pod 45 st.)"""
    rr = np.sqrt(X ** 2 + (Z - zl) ** 2)
    ring = np.minimum(LOOP_RO - rr, LOOP_T / 2 - np.abs(Y))
    r = LOOP_RH
    circ = r - rr
    zt = zl + r * math.sqrt(2)
    wedge = np.minimum((zt - Z - np.abs(X)) / math.sqrt(2), Z - (zl + r * math.sqrt(0.5)))
    hole = np.maximum(circ, wedge)
    return np.minimum(ring, -hole).astype(np.float32)


def collar_tail(z_int, z_top):
    """koncowka profilu: szyjka R_COL od przeciecia z kula do z_top + COL_H"""
    return [(z_int + 0.8, R_COL), (z_top + COL_H, R_COL)]


def build_round(D, vox):
    R = D / 2.0
    pts, zc = sphere_pts(R, CUT, 180.0 - math.degrees(math.asin(R_COL / R)) - 2.0, 60)
    z_top = zc + R
    z_int = pts[-1][0]
    prof = pts + collar_tail(z_int, z_top)
    Ro = Prof(with_top_fillet(prof, 1.0))
    name = f"bombka_okragla_{int(D)}"
    check_profile(Ro, None, name)
    zl = z_top + COL_H + LOOP_RO - 2.8
    N = n_ribs(R)
    axes, (X, Y, Z) = rev_grid(R + 0.8, zl + LOOP_RO + 1.5, vox)
    F = rev_F(X, Y, Z, Ro, [N], [], [(z_int - 4.0, 200)], zlo=0.0, zhi=Ro.z1)
    F = np.maximum(F, loop_F(X, Y, Z, zl)).astype(np.float32)
    return finish(F, axes, vox, f"{name}.stl", f"kula {D:.0f} mm, N={N}; plaski spod; uszko na gorze (otwor kroplowy)", target=300000)


def build_drop(vox=0.4):
    R = 30.0
    pts, zc = sphere_pts(R, CUT, 90.0, 40)
    up = [(zc + 8, 28.6), (zc + 26, 23.0), (zc + 48, 14.0), (zc + 68, 8.6), (zc + 78, 7.0), (zc + 84, R_COL)]
    z_top = zc + 84 - COL_H
    prof = pts + up + [(zc + 84 + COL_H, R_COL)]
    Ro = Prof(with_top_fillet(prof, 1.0))
    check_profile(Ro, None, "bombka_kropla")
    zl = Ro.z1 + LOOP_RO - 2.8
    axes, (X, Y, Z) = rev_grid(R + 0.8, zl + LOOP_RO + 1.5, vox)
    F = rev_F(X, Y, Z, Ro, [56, 28, 14], [(zc + 12, zc + 34), (zc + 50, zc + 68)], [(zc + 72, 300)], zlo=0.0, zhi=Ro.z1)
    F = np.maximum(F, loop_F(X, Y, Z, zl)).astype(np.float32)
    return finish(F, axes, vox, "bombka_kropla.stl", "kropla; plaski spod; zebra 56 -> 28 -> 14; uszko na gorze", target=300000)


if __name__ == "__main__":
    T0 = time.time()
    which = sys.argv[1:] or ["60", "80", "100", "kropla"]
    for w in which:
        t = time.time()
        if w == "kropla":
            build_drop()
        else:
            build_round(int(w), {"60": 0.35, "80": 0.4, "100": 0.4}[w])
        print(f"  {w}: {time.time() - t:.0f} s")
    print(f"czas {time.time() - T0:.0f} s")
