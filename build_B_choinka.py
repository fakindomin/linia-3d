"""Grupa B - choinka ze stozkow na czop 5x5x8: podstawa (pien), 4 pietra, gwiazda (plaska, druk na lezaco).
 choinka_podstawa.stl, choinka_1..4.stl (spod: gniazdo 5,4x5,4x9 od stolu; gora: czop 5x5x8, a pietro 4 - gniazdo), choinka_gwiazda.stl
 skladana wysokosc ~150 mm"""
import sys, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rev import *
from parts import peg_ext_F, part_mesh

VOX = 0.35
BASE_H = 20.0
TIERS = {   # nr: (R_dol, R_gora, H)
    1: (28.0, 11.5, 33.0),
    2: (23.5, 10.0, 29.0),
    3: (19.0, 9.0, 25.0),
    4: (14.5, 8.0, 22.0),
}
STAR_RO, STAR_RI, STAR_T = 12.0, 5.2, 5.0
FR_UP = lambda z: Frame(np.array([0.0, 2.5, z]), (-1, 0, 0), (0, 0, -1), (0, -1, 0))     # czop do gory z plaszczyzny z
FR_DN0 = socket_frame(np.array([0.0, 0.0, 0.0]), B=(0, 0, -1), A=(-1, 0, 0), C=(0, -1, 0))    # gniazdo od stolu (z = 0) w gore


def tier_profile(Rb, Rt, H):
    us = [0.2, 0.4, 0.6, 0.8]
    pts = [(0.0, Rb - 1.2), (1.2, Rb)] + [(1.2 + u * (H - 1.2), Rb + (Rt - Rb) * u ** 1.12) for u in us] + [(H, Rt)]
    return Prof(with_top_fillet(pts, 0.8))


def build_base():
    pts = [(0.0, 19.6), (1.4, 21.0), (4.0, 21.0), (6.5, 14.0), (9.5, 8.6), (12.0, 8.0), (BASE_H, 8.0)]
    Ro = Prof(with_top_fillet(pts, 0.8))
    check_profile(Ro, None, "choinka_podstawa")
    axes, (X, Y, Z) = rev_grid(21.0 + 0.8, BASE_H + 11.0, VOX)
    F = rev_F(X, Y, Z, Ro, [39, 15], [(7.0, 12.0)], [], zlo=0.0, zhi=BASE_H)
    a, b, c = FR_UP(BASE_H).to_local(X, Y, Z)
    F = np.maximum(F, peg_ext_F(a, b, c)).astype(np.float32)
    return finish(F, axes, VOX, "choinka_podstawa.stl", "stopa + pien; czop 5x5x8 do gory")


def build_tier(k):
    Rb, Rt, H = TIERS[k]
    Ro = tier_profile(Rb, Rt, H)
    check_profile(Ro, None, f"choinka_{k}")
    axes, (X, Y, Z) = rev_grid(Rb + 0.8, H + 11.0, VOX)
    F = rev_F(X, Y, Z, Ro, [n_ribs(Rb)], [], [], zlo=0.0, zhi=H)
    a, b, c = FR_DN0.to_local(X, Y, Z)
    F = np.minimum(F, -socket_F(a, b, c))                       # gniazdo od dolu
    if k < 4:
        a, b, c = FR_UP(H).to_local(X, Y, Z)
        F = np.maximum(F, peg_ext_F(a, b, c))                   # czop do gory
    else:
        fr = socket_frame(np.array([0.0, 0.0, H]), B=(0, 0, 1), A=(1, 0, 0), C=(0, -1, 0))   # gniazdo od gory na gwiazde
        a, b, c = fr.to_local(X, Y, Z)
        F = np.minimum(F, -socket_F(a, b, c))
    F = F.astype(np.float32)
    note = "gniazdo od stolu; czop do gory" if k < 4 else "gniazdo od stolu i gniazdo na gwiazde u gory"
    return finish(F, axes, VOX, f"choinka_{k}.stl", note)


def star_flat(res=0.1):
    cb = 1.5 + STAR_RO * math.sin(math.radians(54)) + 0.0          # nizsze ramiona nad powierzchnia pietra
    cb = 1.5 + STAR_RO * 0.809
    cv = Canvas(-14, 14, -4.5, cb + STAR_RO + 2, res=res)
    pts = []
    for k in range(10):
        ang = math.radians(90 + k * 36)
        r = STAR_RO if k % 2 == 0 else STAR_RI
        pts.append((r * math.cos(ang), cb + r * math.sin(ang)))
    cv.poly(pts)
    cv.rect(-3.4, 3.4, -3.0, cb - STAR_RI + 1.5)               # nasada pod czop
    cv.close_(0.6)
    cv.open_(0.8)
    return FlatPart(cv, STAR_T, w=1.0, k=1.5), cb


def build_star():
    fp, cb = star_flat()
    m = part_mesh(fp, None, True, (-14, 14), (-9, cb + STAR_RO + 1), 0.2, plate_b0=0.2)
    save(m, "choinka_gwiazda.stl", False, "druk na plasko (plecy na stole); czop 5x5x8 w gniazdo pietra 4")
    print(f"  gwiazda: wysokosc nad pietrem {cb + STAR_RO:.1f} mm")
    return m


if __name__ == "__main__":
    T0 = time.time()
    which = sys.argv[1:] or ["podstawa", "1", "2", "3", "4", "gwiazda"]
    for w in which:
        t = time.time()
        {"podstawa": build_base, "gwiazda": build_star}.get(w, lambda w=w: build_tier(int(w)))()
        print(f"  {w}: {time.time() - t:.0f} s")
    print(f"czas {time.time() - T0:.0f} s")
