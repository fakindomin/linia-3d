"""Wspolne czesci wymienne: ucho, poroze (plaskie), czopy, ramki montazowe, kontrola pasowania."""
import math
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from lib import *

GAP = 0.30           # luz miedzy podstawa ucha a glowa [mm]
PEG_EXT = 2.0        # czop wchodzi 2 mm w plaskownik ucha (spoina)


def ear_flat(L, res=0.1):
    """ucho: liscie ~14 mm szerokosci, widoczna dlugosc L (od plaszczyzny b=0), z wypuklym owalem"""
    cv = Canvas(-9, 9, -4.5, L + 2, res=res)

    def hw(b):
        u = b / L
        if u < 0.5:
            return 4.2 + 2.8 * math.sin(math.pi / 2 * max(u, 0) / 0.5)
        t = (u - 0.5) / 0.5
        return 7.0 * max(1 - t ** 2.2, 0) ** (1 / 2.2)
    bs = np.linspace(-3, L, 200)
    cv.poly([(hw(b), b) for b in bs] + [(-hw(b), b) for b in bs[::-1]])
    ring = Canvas(-9, 9, -4.5, L + 2, res=res)
    ring.ellipse(0, 0.55 * L, 3.5, 0.34 * L, 255)
    ring.ellipse(0, 0.55 * L, 2.6, 0.34 * L - 0.9, 0)
    return FlatPart(cv, EAR_T, w=1.0, k=1.5, ring_mask=ring.mask(), ring_h=RING_H)


def antler_flat(res=0.1, mirror=False):
    """poroze (prawe, a>0 = na zewnatrz): galaz glowna + 2 odnogi, grubosc 5 mm, min. szerokosc 3,7 mm, fillet 2 mm"""
    cv = Canvas(-8, 20, -4.5, 36, res=res)
    main = [(0.0, -3.0), (0.3, 4.0), (0.4, 12.0), (0.0, 20.0), (-0.8, 26.5), (-1.2, 28.6)]
    cv.path(main, 4.2)
    cv.rect(-3.4, 3.4, -3.0, 4.0)                              # podstawa pod czop
    cv.path([(0.5, 5.0), (4.5, 10.1), (8.5, 15.2)], 3.7)       # odnoga dolna (elewacja globalna ~38 st.)
    cv.path([(0.3, 18.0), (4.3, 23.1), (8.3, 28.2)], 3.7)      # odnoga gorna
    cv.close_(2.0)
    cv.open_(1.2)
    return FlatPart(cv, ANT_T, w=1.0, k=2.2, mirror=mirror)


def peg_ext_F(a, b, c):
    return rbox_F(a, b, c, (-PEG_W / 2, -PEG_L, 0.0), (PEG_W / 2, PEG_EXT, PEG_W), PEG_R)


def mount_frame(side, P0, tilt=TILT):
    """uklad lokalny czesci wymiennej: side=+1 prawa (x>0), -1 lewa; b = os gniazda (do gory, pochylona na zewnatrz),
    c = -y (przod), a = b x c. Poczatek tak, by os czopu (c=2,5) przechodzila przez P0."""
    B = np.array([side * math.sin(tilt), 0.0, math.cos(tilt)])
    C = np.array([0.0, -1.0, 0.0])
    A = np.cross(B, C)
    return socket_frame(P0, B, A, C)


def _global_xyz(fr, a, b, c):
    X = fr.O[0] + a * fr.A[0] + b * fr.B[0] + c * fr.C[0]
    Y = fr.O[1] + a * fr.A[1] + b * fr.B[1] + c * fr.C[1]
    Z = fr.O[2] + a * fr.A[2] + b * fr.B[2] + c * fr.C[2]
    return X, Y, Z


def local_sdf(inside_fn, center, half, vox=0.1):
    """przyblizone SDF bryly (dodatnie wewnatrz, mm) na drobnej siatce wokol 'center' +- 'half'; zwraca funkcje (X,Y,Z)->sdf"""
    center, half = np.asarray(center, float), np.asarray(half, float)
    axes, (X, Y, Z) = make_grid(center[0] - half[0], center[0] + half[0], center[1] - half[1], center[1] + half[1],
                                center[2] - half[2], center[2] + half[2], vox)
    ins = inside_fn(X, Y, Z) > 0
    din = ndi.distance_transform_edt(ins) - 0.5
    dout = ndi.distance_transform_edt(~ins) - 0.5
    sdf = np.where(ins, din, -dout) * vox
    x, y, z = axes

    def f(Xq, Yq, Zq):
        shp = np.broadcast(Xq, Yq, Zq).shape
        Xq, Yq, Zq = (np.broadcast_to(v, shp).ravel() for v in (Xq, Yq, Zq))
        coords = np.vstack([(Xq - x[0]) / vox, (Yq - y[0]) / vox, (Zq - z[0]) / vox])
        v = ndi.map_coordinates(sdf, coords, order=1, mode="nearest")
        return v.reshape(shp)
    return f


def part_fn(fp, trims=None, peg=True, gap=GAP, plate_b0=-3.0):
    """pole czesci w ukladzie lokalnym. trims = [(ramka_korpusu, sdf_korpusu), ...]: podstawa przycieta do ksztaltu
    kazdego z korpusow (z luzem 'gap'), czyli czesc pasuje do wszystkich wymienionych korpusow."""
    def fn(a, b, c):
        F = np.minimum(fp.F(a, b, c), b - plate_b0)
        for fr, sdf in (trims or []):
            X, Y, Z = _global_xyz(fr, a, b, c)
            F = np.minimum(F, -(sdf(X, Y, Z) + gap))
        if peg:
            F = np.maximum(F, peg_ext_F(a, b, c))
        return F.astype(np.float32)
    return fn


def part_mesh(fp, trims=None, peg=True, a_rng=(-10, 10), b_rng=(-9, 36), vox=0.2, plate_b0=-3.0):
    fn = part_fn(fp, trims, peg, plate_b0=plate_b0)
    return local_mesh(fn, a_rng, b_rng, (-0.6, 7.2), vox=vox)


def to_global(m, fr):
    g = m.copy()
    g.apply_transform(fr.matrix())
    return g


def surf_tree(mesh, n=400000, seed=1):
    pts, _ = trimesh.sample.sample_surface(mesh, n, seed=seed)
    return cKDTree(pts)


def clearance(part_global, tree, inside_fn=None):
    d, _ = tree.query(part_global.vertices)
    return float(d.min())
