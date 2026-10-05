"""10 platkow sniegu: plaskie 3 mm, ok. 90 mm, uszko Ø3 do zawieszenia, symetria 6-krotna."""
import sys, time, math
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from render import render, grid
from PIL import Image, ImageDraw

T0 = time.time()
THK = 3.0
RES = 0.1
HALF = 54.0


def rot(v, u, phi):
    c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    return (v * c - u * s, v * s + u * c)


class Sym:
    """rysowanie jednego ramienia (v poprzecznie, u wzdluz) z kopiowaniem na 6 ramion"""
    def __init__(self):
        self.cv = Canvas(-HALF, HALF, -HALF, HALF, RES)
        self.gr = Canvas(-HALF, HALF, -HALF, HALF, RES)

    def path(self, pts, w, v=255, groove=False, arms=range(6), mirror=False):
        for k in arms:
            for s in ((1, -1) if mirror else (1,)):
                P = [rot(s * a, b, 60 * k) for a, b in pts]
                (self.gr if groove else self.cv).path(P, w, v)

    def poly(self, pts, v=255, mirror=False):
        for k in range(6):
            for s in ((1, -1) if mirror else (1,)):
                self.cv.poly([rot(s * a, b, 60 * k) for a, b in pts], v)

    def ring(self, u, ro, ri, arms=range(6)):
        for k in arms:
            cx, cy = rot(0, u, 60 * k)
            self.cv.ellipse(cx, cy, ro, ro, 255)
            self.cv.ellipse(cx, cy, ri, ri, 0)

    def hexagon(self, r, w=None, v=255, rot_deg=0):
        pts = [(r * math.cos(math.radians(90 + rot_deg + 60 * i)), r * math.sin(math.radians(90 + rot_deg + 60 * i))) for i in range(6)]
        if w is None:
            self.cv.poly(pts, v)
        else:
            self.cv.path(pts + [pts[0]], w, v)

    def disc(self, r, v=255):
        self.cv.ellipse(0, 0, r, r, v)


def branch(S, u0, L, ang, w, s_both=True, v0=0.0):
    a = math.radians(ang)
    S.path([(v0, u0), (v0 + L * math.sin(a), u0 + L * math.cos(a))], w, mirror=s_both)


# ---------------- projekty ----------------
def f01(S):       # klasyczny
    R = 44
    S.path([(0, 0), (0, R)], 3.6)
    for u0, L in ((14, 11.5), (25, 9.5), (34, 6.5)):
        branch(S, u0, L, 50, 3.0)
    S.hexagon(7)
    return R


def f02(S):       # paproc (dendryt)
    R = 44
    S.path([(0, 0), (0, R)], 3.4)
    for u0, L in ((11, 12), (18.5, 10.5), (26, 9), (33, 7), (39.5, 4.5)):
        branch(S, u0, L, 55, 2.7)
    S.hexagon(6)
    return R


def f03(S):       # szesciokatna tarcza (koronka)
    R = 44
    S.path([(0, 0), (0, R)], 3.4)
    S.hexagon(33, 3.4)
    S.hexagon(19, 3.2)
    S.hexagon(7)
    for k in range(6):
        p = rot(0, 33, 60 * k)
        S.cv.ellipse(p[0], p[1], 4.6, 4.6, 255)       # kropki w wierzcholkach
    S.path([(0, 36), (0, R)], 3.4)
    return R


def f04(S):       # gwiazda: szerokie rombowe ramiona z wycieciem
    R = 44
    S.poly([(0, 6), (7.5, 18), (0, R), (-7.5, 18)])
    S.poly([(0, 14), (2.6, 20), (0, 33), (-2.6, 20)], v=0)       # wyciecie (koronka)
    S.hexagon(8)
    S.disc(0.0)
    return R


def f05(S):       # zebrowany: szerokie ramiona z rowkami (jak zebra linii)
    R = 44
    S.path([(0, 0), (0, R - 3)], 9.0)
    S.cv.ellipse(0, 0, 0.1, 0.1, 255)
    for k in range(6):
        p = rot(0, R - 3, 60 * k)
        S.cv.ellipse(p[0], p[1], 4.5, 4.5, 255)
    S.hexagon(10)
    for off in (-2.7, 0.0, 2.7):
        S.path([(off, 13), (off, R - 6)], 0.7, groove=True)
    return R + 1.5


def f06(S):       # kolka
    R = 44
    S.path([(0, 0), (0, 36)], 3.4)
    S.ring(39.5, 6.2, 3.0, arms=range(1, 6))
    branch(S, 12, 12.5, 50, 3.0)
    branch(S, 24, 9.5, 50, 3.0)
    S.hexagon(6.5)
    return 40.0


def f07(S):       # romby
    R = 44
    S.path([(0, 0), (0, 40)], 3.2)
    for u in (15, 28):
        S.poly([(0, u - 7.5), (6.0, u), (0, u + 7.5), (-6.0, u)])
    S.poly([(0, 34), (4.0, 40), (0, 46), (-4.0, 40)])
    S.hexagon(6)
    return 46


def f08(S):       # podwojny szesciokat
    R = 44
    S.hexagon(44, 3.2)
    S.hexagon(29, 3.2)
    S.hexagon(13, 3.0)
    S.path([(0, 0), (0, 44)], 3.2)
    for k in range(6):                                  # krotkie laczniki miedzy pierscieniami w polowie bokow
        p1 = rot(0, 29, 60 * k)
        p2 = rot(0, 29, 60 * (k + 1))
        m = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        S.cv.path([m, (m[0] * 44 / 29, m[1] * 44 / 29)], 3.0)
    return 44


def f09(S):       # tarcza z zebrami (jak linia) + ramiona z widelcem
    R = 44
    S.disc(15)
    for i in range(24):
        a = math.radians(i * 15)
        S.gr.line((4.5 * math.cos(a), 4.5 * math.sin(a)), (13.2 * math.cos(a), 13.2 * math.sin(a)), 0.9)
    S.path([(0, 12), (0, 36)], 3.4)
    S.path([(0, 30), (-8, 40), (-8, R)], 3.0, mirror=False)
    S.path([(0, 30), (8, 40), (8, R)], 3.0, mirror=False)
    S.path([(0, 30), (0, R)], 3.4)
    return R


def f10(S):       # strzalki
    R = 44
    S.path([(0, 0), (0, 40)], 3.4)
    for u0, L in ((21, 9), (31, 7.5)):
        branch(S, u0, L, 42, 3.0)
    S.poly([(0, 34), (5.0, 39), (0, 45), (-5.0, 39)])
    S.hexagon(7)
    return 45


DESIGNS = [("01_klasyczny", f01), ("02_paproc", f02), ("03_szesciokat", f03), ("04_gwiazda", f04), ("05_zebrowany", f05),
           ("06_kolka", f06), ("07_romby", f07), ("08_podwojny_szesciokat", f08), ("09_tarcza_zebra", f09), ("10_strzalki", f10)]


def build(name, fn):
    S = Sym()
    R_tip = fn(S)
    cv = S.cv
    # uszko u gory: stozek-lacznik + pierscien Ø8,4 z otworem Ø3
    rb = R_tip + 1.0
    cv.path([(0, R_tip - 4.0), (0, rb)], 3.6)
    cv.ellipse(0, rb, 4.2, 4.2, 255)
    cv.ellipse(0, rb, 1.5, 1.5, 0)
    hole_mask = Canvas(-HALF, HALF, -HALF, HALF, RES)
    cv.close_(0.6)
    cv.ellipse(0, rb, 1.5, 1.5, 0)
    m = cv.mask()
    # kontrola: spojnosc i minimalny detal
    lab, n = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, n + 1))
    if n > 1:
        keep = 1 + int(np.argmax(sizes))
        print(f"  {name}: {n} skladowych -> zostawiam najwieksza (reszta {int(sizes.sum() - sizes.max())} px)")
        cv._set(lab == keep)
        m = cv.mask()
    op = ndi.binary_opening(m, structure=np.ones((1, 1)), iterations=1)
    r_px = int(round(0.7 / RES))
    er = ndi.distance_transform_edt(np.pad(m, 1))[1:-1, 1:-1] > r_px
    dil = ndi.distance_transform_edt(~er) <= r_px
    lost = float((m & ~dil).sum()) * RES * RES                          # detale cienkie < 1,4 mm
    gaps_c = ndi.distance_transform_edt(~m) * RES <= 0.7
    er2 = ndi.distance_transform_edt(np.pad(gaps_c, 1, constant_values=True))[1:-1, 1:-1] * RES > 0.7
    filled = float(((er2 | m) & ~m).sum()) * RES * RES                   # szczeliny < 1,4 mm
    ys, xs = np.where(m)
    ext = ((xs.max() - xs.min()) * RES, (ys.max() - ys.min()) * RES)
    print(f"  {name}: rozmiar maski {ext[0]:.1f} x {ext[1]:.1f} mm | cienkie detale (<1,4 mm): {lost:.1f} mm2 | waskie szczeliny: {filled:.1f} mm2")
    ring = None
    fp = FlatPart(cv, THK, w=1.2, k=2.0, groove_mask=(S.gr.mask() & m) if S.gr.mask().any() else None, groove_d=0.9)
    fn_ = lambda a, b, c: fp.F(a, b, c)
    mesh = local_mesh(fn_, (-HALF + 2, HALF - 2), (-HALF + 2, HALF - 2), (-0.6, THK + 0.8), vox=0.2)
    mesh = decimate(mesh, 70000, label=name)
    return mesh


if __name__ == "__main__":
    meshes, names = [], []
    for nm, fn in DESIGNS:
        mesh = build(nm, fn)
        save(mesh, f"platek_{nm}.stl", False, "plaski 3 mm; druk na stole, otwor Ø3 u gory")
        meshes.append(mesh); names.append(nm)
    imgs = [render([m], 0, 90, 440, 480, ext=480 / 100, center=(0, 0)) for m in meshes]
    big = grid(imgs, 5, labels=[n.replace("_", " ") for n in names])
    big.save(OUT + "/platki_przeglad.png")
    json.dump(REPORT, open(OUT + "/_raport.json", "w"), indent=1, ensure_ascii=False)
    print(f"czas {time.time() - T0:.0f} s")
