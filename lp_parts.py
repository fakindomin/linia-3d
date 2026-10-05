"""Biblioteka czesci wymiennych lowpoly (uklad lokalny portu a,b,c; druk na plecach c = 0): ucho (lisc), poroze, belka.
Uzywa tylko standard.py. Czesc przycina sie do kopert modeli przez standard.lp_trim (dodaje tez czop 5x5x8)."""
import sys, math
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from standard import *

EAR_T_ = 5.5
ANT_T = 5.0
ANT_T_ = ANT_T
EAR_U = [0.0, 0.2, 0.38, 0.5, 0.62, 0.74, 0.86, 0.95]


def ear_hw(b, L):
    u = b / L
    if u < 0.5:
        return 4.2 + 2.8 * math.sin(math.pi / 2 * max(u, 0) / 0.5)
    t = (u - 0.5) / 0.5
    return 7.0 * max(1 - t ** 2.2, 0) ** (1 / 2.2)


def ear_ring(b, hw, T=EAR_T_):
    ht = max(hw - 2.6, 0.35 * hw)
    ct = min(T, 1.0 + 1.7 * (hw - ht))
    rg = 0.8
    return [(-hw, b, 0.0), (hw, b, 0.0), (hw, b, 1.0), (ht, b, ct), (0.0, b, ct + rg), (-ht, b, ct), (-hw, b, 1.0)]


def ear_leaf(L, b0=-3.0):
    """lisc: szyjka hw = 4,2 od b0 do 0, potem rozszerzenie do 7 mm w 0,5 L i zwezenie do czubka w b = L; grzbiet posrodku"""
    bs = [b0] + [u * L for u in EAR_U]
    rings = [ear_ring(b, ear_hw(max(b, 0.0), L)) for b in bs]
    return loft(rings, apex=(0.0, L, 1.5))


def path_rings(path, w, tw, T, wall=1.0, lam=1.0, tip=2.0):
    """belka pochylana wzdluz lamanej (a, b): obrys 6-katny (plecy plaskie, dach), apex na koncu"""
    P = np.array(path, float) * lam
    n = len(P)
    dirs = []
    for i in range(n - 1):
        d = P[i + 1] - P[i]; dirs.append(d / np.linalg.norm(d))
    rings = []
    for i in range(n):
        d = dirs[0] if i == 0 else (dirs[-1] if i == n - 1 else (dirs[i - 1] + dirs[i]) / np.linalg.norm(dirs[i - 1] + dirs[i]))
        nrm = np.array([-d[1], d[0]])
        sc = 1.0 if i in (0, n - 1) else 1.0 / max(np.dot(nrm, np.array([-dirs[i][1], dirs[i][0]])), 0.7)
        h, t = w / 2 * sc, tw * sc
        pts = [(-h, 0.0), (h, 0.0), (h, wall), (t, T), (-t, T), (-h, wall)]
        rings.append([(P[i][0] + s * nrm[0], P[i][1] + s * nrm[1], c) for s, c in pts])
    apex = (P[-1][0] + dirs[-1][0] * tip, P[-1][1] + dirs[-1][1] * tip, T * 0.45)
    return loft(rings, apex=apex)


def stretch(path, lam):
    """rozciaga czesc nad podstawa (b > 4) o lam wzdluz b; a bez zmian"""
    return [(a, b if b <= 4.0 else 4.0 + (b - 4.0) * lam) for a, b in path]


def antler_solid(lam=1.0, b0=-3.0):
    """prawe poroze (a > 0 na zewnatrz): galaz glowna + 2 odnogi + podstawa pod czop; lam rozciaga czesc nad podstawa"""
    main = [(0.0, b0), (0.3, 4.0), (0.4, 12.0), (0.0, 20.0), (-0.8, 26.5), (-1.2, 28.6)]
    low = [(0.5, 5.0), (4.5, 10.1), (8.5, 15.2)]
    up = [(0.3, 18.0), (4.3, 23.1), (8.3, 28.2)]
    base = pillow_box(-3.4, 3.4, b0, 4.0, ANT_T_, 1.0, 1.2)
    return union(base,
                 path_rings(stretch(main, lam), 4.2, 0.8, ANT_T_, tip=2.1),
                 path_rings(stretch(low, lam), 3.7, 0.5, ANT_T_, tip=1.85),
                 path_rings(stretch(up, lam), 3.7, 0.5, ANT_T_, tip=1.85))


def mirror_a(m):
    g = m.copy()
    g.vertices[:, 0] *= -1
    g.invert()
    trimesh.repair.fix_normals(g)
    return g
