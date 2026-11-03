"""Wspolne czesci wymienne: ucho, poroze (plaskie), czopy, ramki montazowe, kontrola pasowania."""
import math
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from lib import *

GAP = 0.30           # luz miedzy podstawa ucha a glowa [mm]
PEG_EXT = 2.0        # czop wchodzi 2 mm w plaskownik ucha (spoina)


def ear_flat(L, res=0.1, W=14.0):
    """ucho: liscie o szerokosci W (14 mm = ucho krolika), widoczna dlugosc L (od plaszczyzny b=0), z wypuklym owalem.
    Dla W != 14 wszystko skaluje sie poprzecznie (hb = 0,6 hm, owal 3,5 k), tak samo jak w podgladzie (earSpec 'rab')."""
    hm = W / 2.0
    hb, A, k = 4.2 * hm / 7.0, hm + 2.0, hm / 7.0
    cv = Canvas(-A, A, -4.5, L + 2, res=res)

    def hw(b):
        u = b / L
        if u < 0.5:
            return hb + (hm - hb) * math.sin(math.pi / 2 * max(u, 0) / 0.5)
        t = (u - 0.5) / 0.5
        return hm * max(1 - t ** 2.2, 0) ** (1 / 2.2)
    bs = np.linspace(-3, L, 200)
    cv.poly([(hw(b), b) for b in bs] + [(-hw(b), b) for b in bs[::-1]])
    ring = Canvas(-A, A, -4.5, L + 2, res=res)
    ring.ellipse(0, 0.55 * L, 3.5 * k, 0.34 * L, 255)
    ring.ellipse(0, 0.55 * L, 2.6 * k, max(0.34 * L - 0.9, 0.1), 0)
    return FlatPart(cv, EAR_T, w=1.0, k=1.5, ring_mask=ring.mask(), ring_h=RING_H)


ANT_TINE = math.hypot(8.0, 10.2)                    # dlugosc odnogi przy antTine = 1 (dawne poroze: odnoga (8; 10,2))
ANT_ANGLE = math.atan2(8.0, 10.2) * 180 / math.pi   # 38,12 st. od osi galezi glownej
ANT_BEAM = [(0.0, -3.0), (0.3, 4.0), (0.4, 12.0), (0.0, 20.0), (-0.8, 26.5), (-1.2, 28.6)]


def antler_geom(levels=2, spacing=13.0, tine=1.0, angle=ANT_ANGLE, s=1.0):
    """geometria poroza w ukladzie plaskim (a, b): galaz glowna + 'levels' odnog co 'spacing' mm (pierwsza w b = 5), kazda odchylona o 'angle'
    od osi galezi, dlugosci 12,965 * tine. Trzon galezi jest rozciagniety tak, by ostatnia odnoga trafiala w koronie (b > 18 bez zmian).
    Zwraca dict(beam, tines, A0, A1, Lc, ar) - to samo liczy podglad (earSpec 'ant'); levels=2, spacing=13, tine=1, angle=38,12 to dawne poroze."""
    nL = max(1, int(round(levels)))
    ang = math.radians(angle)
    Lt = ANT_TINE * tine
    dx, dy = Lt * math.sin(ang), Lt * math.cos(ang)
    last = 5.0 + (nL - 1) * spacing

    def g(b):
        return -3.0 + (b + 3.0) * (last + 3.0) / 21.0 if b <= 18 else last + (b - 18.0)
    beam = [(a, g(b)) for a, b in ANT_BEAM]
    tines = [[(0.5 - 0.2 * i, 5.0 + i * spacing), (0.5 - 0.2 * i + dx / 2, 5.0 + i * spacing + dy / 2),
              (0.5 - 0.2 * i + dx, 5.0 + i * spacing + dy)] for i in range(nL)]
    A1 = max(20.0, 0.5 + dx + 4.0) * s
    Lc = round(max(36.0, max(last + 10.6, last + dy) + 7.4), 6) * s
    AR = max(21.0, 22.0 * s, (0.5 + dx + 5.0) * s)
    return dict(beam=beam, tines=tines, A0=-8.0 * s, A1=A1, Lc=Lc, AR=AR, levels=nL)


def antler_flat(res=0.1, mirror=False, levels=2, spacing=13.0, tine=1.0, angle=ANT_ANGLE, s=1.0, w=1.0, T=ANT_T):
    """poroze (prawe, a>0 = na zewnatrz): galaz glowna + odnogi (domyslnie 2), grubosc 5 mm, szerokosc galezi 4,2 w, odnog 3,7 w (min. 3,7 mm przy w = 1), fillet 2 mm.
    s = skala (rozmiar poroza), w = grubosc galezi, T = grubosc plaskownika (5 mm)."""
    G = antler_geom(levels, spacing, tine, angle, s)
    sc = lambda pts: [(a * s, b * s) for a, b in pts]
    cv = Canvas(G["A0"], G["A1"], -4.5, G["Lc"], res=res)
    cv.path(sc(G["beam"]), 4.2 * w)
    cv.rect(-3.4 * s, 3.4 * s, -3.0 * s, 4.0 * s)                  # podstawa pod czop
    for t in G["tines"]:
        cv.path(sc(t), 3.7 * w)
    cv.close_(2.0)
    cv.open_(1.2)
    return FlatPart(cv, T, w=1.0, k=2.2, mirror=mirror)


def leaf_flat(L, W, T, res=0.1):
    """boczne ucho-lisc renifera: ostry czubek (wykladnik 1,2), bez owalu, grubosc T; widoczna dlugosc L, szerokosc W (jak earSpec 'leaf' w podgladzie)"""
    hm = W / 2.0
    hb, A, q = 0.55 * hm, hm + 2.0, 1.2
    cv = Canvas(-A, A, -4.5, L + 2, res=res)

    def hw(b):
        u = b / L
        if u < 0.4:
            return hb + (hm - hb) * math.sin(math.pi / 2 * max(u, 0) / 0.4)
        t = (u - 0.4) / 0.6
        return hm * max(1 - t ** q, 0) ** (1 / q)
    bs = np.linspace(-3, L, 200)
    cv.poly([(hw(b), b) for b in bs] + [(-hw(b), b) for b in bs[::-1]])
    return FlatPart(cv, T, w=0.8, k=1.2)


def peg_ext_F(a, b, c):
    return rbox_F(a, b, c, (-PEG_W / 2, -PEG_L, 0.0), (PEG_W / 2, PEG_EXT, PEG_W), PEG_R)


def mount_frame(side, P0, tilt=TILT, pitch=0.0):
    """uklad lokalny czesci wymiennej: side=+1 prawa (x>0), -1 lewa; b = os gniazda (do gory, pochylona na zewnatrz o 'tilt'),
    c = -y (przod), a = b x c. Poczatek tak, by os czopu (c=2,5) przechodzila przez P0.
    pitch > 0 pochyla czesc do przodu (-y), pitch < 0 do tylu (obrot wokol osi a); pitch = 0 daje dawny uklad."""
    B = np.array([side * math.sin(tilt), 0.0, math.cos(tilt)])
    C = np.array([0.0, -1.0, 0.0])
    if pitch:
        sp, cp = math.sin(pitch), math.cos(pitch)
        B, C = B * cp + C * sp, C * cp - B * sp
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
