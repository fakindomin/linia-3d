"""Jelen stojacy, gladki, 'zabawkowy' (gruby tulow, duza glowa, krotkie grube nogi, zbite szerokie poroze), 50 mm.
Wlasny, oryginalny model z pol odleglosci (elipsoidy + kapsuly + gladkie sumy); proporcje wg zyczenia: wyzszy stosunek glowy/tulowia do nog,
poroze grube i zbite, nawisy <= 55 st. od pionu (bez podpor), stopy lacznie >= 100 mm2, srodek masy nad podstawa.
Uklad: x = przod, y = bok, z = gora; z = 0 to stol.
  python3 jelen.py          -> out/jelen_stojacy.stl"""
import sys, math, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rev import *
import trimesh
from scipy import ndimage as ndi
from shapely.geometry import MultiPoint, Point

HEIGHT = 50.0        # wysokosc calosci wraz z porozem [mm] (stojacy)
S_STD = 0.9225       # skala projektu -> mm stojacego (HEIGHT / wysokosc projektu); inne pozycje uzywaja tej samej skali: glowa i poroze tej samej wielkosci
VOX = 0.25
SM = 1.0             # mnoznik wygladzenia polaczen (wiekszy = bardziej miekko)


def smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def cap(P, a, b, ra, rb):
    """kapsula stozkowa od a (promien ra) do b (promien rb)"""
    X, Y, Z = P
    a = np.array(a, float); ab = np.array(b, float) - a
    t = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1] + (Z - a[2]) * ab[2]) / ab.dot(ab), 0, 1)
    return np.sqrt((X - a[0] - t * ab[0]) ** 2 + (Y - a[1] - t * ab[1]) ** 2 + (Z - a[2] - t * ab[2]) ** 2) - (ra + t * (rb - ra))


def ell(P, c, r):
    X, Y, Z = P
    r = np.array(r, float)
    q = np.sqrt(((X - c[0]) / r[0]) ** 2 + ((Y - c[1]) / r[1]) ** 2 + ((Z - c[2]) / r[2]) ** 2)
    return (q - 1.0) * r.min()


def ell_dir(P, c, u, a, b, t):
    """plaska elipsoida (ucho): os dluga u (polowa a), szerokosc b, grubosc t"""
    X, Y, Z = P
    u = np.array(u, float); u /= np.linalg.norm(u)
    w = np.cross(u, [1.0, 0.0, 0.0]); w /= np.linalg.norm(w)
    v = np.cross(w, u)
    d = (X - c[0], Y - c[1], Z - c[2])
    pu = d[0] * u[0] + d[1] * u[1] + d[2] * u[2]
    pv = d[0] * v[0] + d[1] * v[1] + d[2] * v[2]
    pw = d[0] * w[0] + d[1] * w[1] + d[2] * w[2]
    q = np.sqrt((pu / a) ** 2 + (pv / b) ** 2 + (pw / t) ** 2)
    return (q - 1.0) * min(a, b, t)


def glowa(D, P):
    """glowa + pysk + nos dodane do pola D (wspolna dla wszystkich pozycji; P = wspolrzedne z przesunieciem glowy)"""
    D = smin(D, ell(P, (13.5, 0, 33.0), (9.0, 7.6, 7.9)), 3.5 * SM)            # glowa
    D = smin(D, cap(P, (18.8, 0, 31.0), (24.4, 0, 29.4), 5.0, 3.9), 3 * SM)  # pysk
    D = smin(D, ell(P, (24.6, 0, 29.6), (2.5, 2.5, 2.3)), 1.5 * SM)          # nos
    return D


def uszy_poroze(D, P, s):
    """ucho i poroze jednej strony (s = -1 / +1) dodane do pola D (wspolne dla wszystkich pozycji)"""
    # uszy: plaskie "skrzydelka" w gore i na boki (nawis ok. 39 st. od poziomu)
    D = smin(D, ell_dir(P, (10.8, s * 10.8, 37.2), (-0.20, s * 0.765, 0.628), 6.6, 3.9, 1.8), 2.5 * SM)
    # poroze: gruba galaz + 2 odnogi w polowie + 2 koncowki (wszystko pod katem >= 40 st. od poziomu)
    B0 = np.array((12.5, s * 4.0, 38.5)); B1 = np.array((12.0, s * 18.4, 49.5))
    M = B0 + 0.45 * (B1 - B0)
    D = smin(D, cap(P, B0, B1, 2.7, 2.1), 1.8 * SM)
    D = smin(D, cap(P, M, M + np.array((6.0, s * 2.2, 6.2)), 2.1, 1.6), 1.6 * SM)       # odnoga do przodu
    D = smin(D, cap(P, M, M + np.array((-6.2, s * 2.0, 6.0)), 2.1, 1.6), 1.6 * SM)      # odnoga do tylu
    D = smin(D, cap(P, B1, B1 + np.array((3.4, s * 0.8, 3.2)), 2.1, 1.5), 1.4 * SM)     # koncowka przod
    D = smin(D, cap(P, B1, B1 + np.array((-3.4, s * 0.6, 3.2)), 2.1, 1.5), 1.4 * SM)    # koncowka tyl
    return D


def design(P):
    """pole odleglosci (ujemne w srodku) w jednostkach projektu (wysokosc ok. 50)"""
    D = ell(P, (-1.5, 0, 18.8), (14.5, 10.6, 10.4))                          # tulow
    D = smin(D, ell(P, (7.5, 0, 21.0), (9.0, 9.2, 9.6)), 5 * SM)           # barki
    D = smin(D, ell(P, (-9.5, 0, 19.3), (8.2, 9.6, 9.2)), 5 * SM)          # zad
    D = smin(D, cap(P, (5.0, 0, 22.0), (11.5, 0, 31.5), 6.6, 6.0), 4.5 * SM)   # szyja (gruba i krotka, glowa wyraznie nad barkami)
    D = glowa(D, P)
    D = smin(D, ell(P, (-17.5, 0, 22.0), (3.0, 2.6, 3.2)), 2.5 * SM)         # ogon
    for s in (-1.0, 1.0):
        # nogi: krotkie, grube kolki, stopy ok. o 7,4 mm
        D = smin(D, cap(P, (8.5, s * 5.6, 15.0), (9.5, s * 6.2, 0.0), 4.5, 3.6), 4 * SM)
        D = smin(D, cap(P, (-9.0, s * 6.0, 15.0), (-10.0, s * 6.8, 0.0), 4.6, 3.7), 4 * SM)
        D = uszy_poroze(D, P, s)
    return D


def build(S=1.0, vox=VOX, name="jelen_stojacy.stl", target=250000, fn=None, note="jelen stojacy, gladki, 50 mm"):
    """S = skala projektu -> mm; siatka w mm, pola liczone na (x/S, y/S, z/S) i mnozone przez S"""
    axes, (X, Y, Z) = make_grid(-25.0 * S, 31.0 * S, -26.0 * S, 26.0 * S, -0.6, 56.0 * S, vox)
    D = (fn or design)((X / S, Y / S, Z / S)) * S
    F = smin(-D, Z, 0.5).astype(np.float32)                        # plaskie dno, zaokraglona krawedz stop
    return finish(F, axes, vox, name, note, target=target)


def overhang_layers(m, h=0.16, ang=55.0):
    """nawisy tak jak widzi je slicer: dla kazdej warstwy obszar niepodparty przez warstwe nizej (cofnieta o h*tg(ang)); zwraca (suma pol [mm2],
    najszersze niepodparte miejsce [mm], z tego miejsca). Wzorzec (3 jelenie z MakerWorld, drukowane bez podpor): 68 / 54 / 7 mm2 i 3,9 / 2,2 / 0,7 mm"""
    from shapely.geometry import Polygon
    z0 = m.bounds[0][2]
    hs = np.concatenate([[z0 + 0.1], z0 + 0.2 + np.arange(1, int((m.extents[2] - 0.3) / h)) * h])
    secs = m.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=hs)
    L = []
    for z, sc in zip(hs, secs):
        u = None
        if sc is not None:
            for q in sorted([Polygon(p).buffer(0) for p in sc.discrete if len(p) >= 4], key=lambda q: -q.area):
                u = q if u is None else (u.difference(q) if u.contains(q) else u.union(q))
        L.append((z - z0, u))
    d = h * math.tan(math.radians(ang))
    tot, wmax, zmax = 0.0, 0.0, 0.0
    for (z1, a), (_, b) in zip(L[1:], L[:-1]):
        if a is None or b is None:
            continue
        U = a.difference(b.buffer(d)).buffer(-0.05).buffer(0.05)
        if U.is_empty:
            continue
        tot += U.area
        for g in (list(U.geoms) if hasattr(U, "geoms") else [U]):
            if g.area < 0.3:
                continue
            lo, hi = 0.0, 40.0
            for _ in range(16):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if not g.buffer(-mid).is_empty else (lo, mid)
            if 2 * lo > wmax:
                wmax, zmax = 2 * lo, z1
    return tot, wmax, zmax


def checks(m, label="jelen", height=HEIGHT, min_feet=100.0):
    """kontrole na gotowym STL: wysokosc, szczelnosc, nawisy, srodek masy vs stopy, laczna powierzchnia stop, elementy cienkie"""
    ok = True
    m = m.copy(); m.apply_translation([0, 0, -m.bounds[0][2]])
    h = float(m.extents[2])
    c1 = height is None or abs(h - height) <= 0.3
    nz = m.face_normals[:, 2]; A = m.area_faces; zc = m.triangles_center[:, 2]
    ov = float(A[(nz < -math.sin(math.radians(55))) & (zc > 0.5)].sum())   # powierzchnie zwrocone w dol bardziej niz 55 st. od pionu
    ov45 = float(A[(nz < -math.sin(math.radians(45))) & (zc > 0.5)].sum())  # to samo dla 45 st. (porownanie z DEER 1: 341 mm2)
    sl = m.section(plane_origin=[0, 0, 0.4], plane_normal=[0, 0, 1])
    polys = [p[:, :2] for p in sl.discrete if len(p) >= 4]
    from shapely.geometry import Polygon
    feet = sum(Polygon(p).buffer(0).area for p in polys)
    hull = MultiPoint(np.concatenate(polys)).convex_hull
    com = m.center_mass
    c2 = m.is_watertight and hull.contains(Point(com[:2]))
    c3 = feet >= min_feet
    vg = m.voxelized(0.25).fill().matrix
    r = int(round(1.0 / 0.25)); zz, yy, xx = np.mgrid[-r:r + 1, -r:r + 1, -r:r + 1]
    op = ndi.binary_opening(vg, structure=(zz ** 2 + yy ** 2 + xx ** 2) <= r * r)
    thin = 100.0 * (1 - op.sum() / vg.sum())                   # % objetosci w elementach cienszych niz 2 mm
    c4 = thin < 1.5
    ovl, ovw, ovz = overhang_layers(m)
    c5 = ovw <= 4.0                                           # najszersze niepodparte miejsce <= wzorca (3,9 mm)
    print(f"  nawis wg warstw (jak slicer, 55 st.): suma {ovl:.0f} mm2, najszersze niepodparte miejsce {ovw:.1f} mm na z = {ovz:.1f} mm (wymog <= 4,0 = wzorzec: {'ok' if c5 else 'ZLE'})")
    ok = c1 and c2 and c3 and c4 and c5
    print(f"  {label}: wysokosc {h:.1f} mm ({'ok' if c1 else 'ZLE'}), wymiary {np.round(m.extents, 1).tolist()}, szczelny {m.is_watertight}, srodek masy ({com[0]:.1f}, {com[1]:.1f}, {com[2]:.1f}) "
          f"{'nad podstawa' if c2 else 'POZA podstawa'}")
    print(f"  stopy lacznie {feet:.0f} mm2 (wymog >= {min_feet:.0f}: {'ok' if c3 else 'ZLE'}), nawis > 55 st.: {ov:.0f} mm2 ({100 * ov / m.area:.1f}% pow.), > 45 st.: {ov45:.0f} mm2, elementy < 2 mm: {thin:.2f}% objetosci ({'ok' if c4 else 'ZLE'}), objetosc {m.volume / 1000:.1f} cm3 -> {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    t0 = time.time()
    m = build(1.0, vox=0.3, name="_jelen_probny.stl", target=60000)              # przebieg 1: pomiar wysokosci projektu
    S = HEIGHT / float(m.extents[2])
    print(f"  skala projektu -> {S:.4f}" + ("" if abs(S - S_STD) < 2e-3 else f"  UWAGA: rozni sie od S_STD = {S_STD}, zaktualizuj stala"))
    m = build(S)
    ok = checks(m)
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
