"""Aniol v2: korpus bazowy + aureola + skrzydla z pojedynczych pior (wachlarz), plyta skrzydla za plecami.
 aniol_calosc.stl (zastepuje wersje z gladkim liściem)"""
import sys, math, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from parts import *
from shapes import *
from build_figurki import add_local
from build_A_fused import halo_F, VOX

T0 = time.time()
TW = 3.2                      # grubosc plyty skrzydla
PIV = (14.5, 12.0)            # srodek wachlarza (a, b) - wewnatrz korpusu
# (kat od poziomu [st.], dlugosc od srodka [mm], polszerokosc [mm]); najnizsze pioro >= 38 st. (nawis <= 52 st. od pionu)
FEATHERS = [(38, 41.0, 3.9), (46, 44.0, 3.9), (54, 45.5, 3.9), (62, 45.0, 3.8), (70, 42.5, 3.7), (78, 38.5, 3.5), (86, 33.0, 3.3)]


def feather_poly(L, hw, n=60):
    us = np.linspace(0, 1, n)

    def w(u):
        if u < 0.18:
            return 2.2 + (hw - 2.2) * math.sin(math.pi / 2 * u / 0.18)
        if u < 0.62:
            return hw
        t = (u - 0.62) / 0.38
        return hw * math.sqrt(max(1 - t ** 2.0, 0.0))
    left = [(u * L, w(u)) for u in us]
    right = [(u * L, -w(u)) for u in us[::-1]]
    return left + right


def wing_flat(res=0.1, feathers=FEATHERS, piv=PIV, T=TW):
    cv = Canvas(0, 62, -4, 62, res=res)
    gr = Canvas(0, 62, -4, 62, res=res)
    for ang, L, hw in feathers:
        th = math.radians(ang)
        c, s = math.cos(th), math.sin(th)
        pts = [(piv[0] + u * c - v * s, piv[1] + u * s + v * c) for u, v in feather_poly(L, hw)]
        cv.poly(pts)
        # rowek wzdluz stosiny pioraska
        p0 = (piv[0] + 0.22 * L * c, piv[1] + 0.22 * L * s)
        p1 = (piv[0] + 0.86 * L * c, piv[1] + 0.86 * L * s)
        gr.line(p0, p1, 0.9)
    cv.rect(1.0, 14.0, 10.0, 22.0)                      # nasada: laczy skrzydlo z korpusem (zaglebiona w plecy)
    cv.close_(0.7)
    cv.open_(0.7)
    return FlatPart(cv, T, w=0.9, k=1.4, groove_mask=gr.mask(), groove_d=0.7)


def wing_frames(phi_deg=16.0, z_r=60.0, y0=8.0, T=TW):
    ph = math.radians(phi_deg)
    out = {}
    for s in (+1, -1):
        A = np.array([s * math.cos(ph), math.sin(ph), 0.0])
        B = np.array([0.0, 0.0, 1.0])
        C = np.array([s * math.sin(ph), -math.cos(ph), 0.0])
        out[s] = Frame(np.array([0.0, y0, z_r]) - C * (T / 2), A, B, C)
    return out


def build(phi=16.0, z_r=60.0, y0=8.0):
    axes, (X, Y, Z) = make_grid(-52, 52, -21, 40, -1.0, 153.0, VOX)
    F = bunny_F(X, Y, Z)
    F = np.maximum(F, halo_F(X, Y, Z))
    fw = wing_flat()
    for s, fr in wing_frames(phi, z_r, y0).items():
        F = add_local(F, axes, fr, lambda a, b, c, fw=fw: fw.F(a, b, c), a_rng=(0, 62), b_rng=(-4, 62), c_rng=(-1, 5))
    return axes, F


if __name__ == "__main__":
    if "2d" in sys.argv:
        fw = wing_flat()
        m = (fw.top > 0.05) & (fw.d > 0)
        from PIL import Image
        Image.fromarray((np.clip(fw.top / TW, 0, 1) * 255).astype(np.uint8)[::-1]).save("/tmp/claude-0/-home-claude/db1eb572-0fd4-5725-b9c8-f07e7256a189/scratchpad/wing2d.png")
        print("2d ok", m.sum() * 0.01, "mm2")
        sys.exit()
    axes, F = build()
    m = mesh_from_F(F, axes, VOX)
    save(m, "aniol_calosc.stl", True, "korpus bazowy + aureola + skrzydla z pior")
    print(f"czas {time.time() - T0:.0f} s")
