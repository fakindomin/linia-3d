"""Jelen stojacy, gladki, 'zabawkowy' (gruby tulow, duza glowa, krotkie grube nogi, zbite szerokie poroze), 50 mm.
Wlasny, oryginalny model z pol odleglosci (elipsoidy + kapsuly + gladkie sumy); proporcje wg zyczenia: wyzszy stosunek glowy/tulowia do nog,
poroze grube i zbite, bez podpor (naprawa nawisow w nawisy.py: kazde zbocze w dol >= 35 st. od poziomu, nawis jak w Bambu <= 8 mm2 przy progu 25 st.),
stopy lacznie >= 100 mm2, srodek masy nad podstawa.
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


NOS_RUDOLF = ((23.8, 0.0, 30.4), 4.2)   # (srodek, promien) kulki-nosa [jedn. projektu]: wieksza od konca pyska (r 3,5), dolem styczna do spodu pyska, zeby nie wisiala


def ogon_kulka(D, P, c, R=3.5):
    """ogon-pompon: kulka o promieniu R ze srodkiem c, wtopiona w zad (linia 'chudy')"""
    return smin(D, ell(P, c, (R, R, R)), 2.2 * SM)


def glowa_chuda(D, P):
    """jak glowa(), ale smuklejsza: wezszy leb (+-6,4 zamiast 7,6) i krotszy, wezszy pysk; ten sam uklad, dlugosc i wysokosc (linia 'chudy')"""
    D = smin(D, ell(P, (13.5, 0, 33.0), (9.0, 6.4, 7.9)), 3.5 * SM)            # glowa
    D = smin(D, cap(P, (18.8, 0, 31.0), (22.8, 0, 29.9), 4.4, 3.7), 3 * SM)  # pysk (skrocony o ok. 1,5 mm: nos-kulka siedzi na jego koncu)
    D = smin(D, ell(P, NOS_RUDOLF[0], (NOS_RUDOLF[1],) * 3), 1.5 * SM)         # nos jak u Rudolfa: duza kulka na koncu pyska
    return D


def uszy_chude(D, P, s, k=0.78):
    """ucho linii 'chudy': ten sam kierunek (nawis ok. 39 st. od poziomu), ale mniejsze i blizej glowy (koniec ucha +-12 zamiast +-16)"""
    return smin(D, ell_dir(P, (10.6, s * 8.4, 36.8), (-0.20, s * 0.765, 0.628), 6.6 * k, 3.9 * k, 1.8 * 0.9), 2.5 * SM)


HEAD_PITCH = 22.0    # domyslne uniesienie glowy (pysk do gory) [st.]: spod pyska rosnie ku nosowi (>= 32 st.), wiec nic nie wisi w powietrzu


def head_xf(P, dx=0.0, dz=0.0, pitch=HEAD_PITCH, pivot=(11.5, 31.5)):
    """punkt swiata -> uklad glowy (ten sam ksztalt glowy/uszu/poroza we wszystkich pozycjach): obrot o -pitch wokol osi y przez pivot = (x, z) konca szyi
    (glowa unosi pysk), potem przesuniecie glowy o (dx, dz)"""
    X, Y, Z = P
    a = math.radians(pitch); c, sn = math.cos(a), math.sin(a)
    ddx, ddz = X - pivot[0], Z - pivot[1]
    return (pivot[0] + c * ddx + sn * ddz - dx, Y, pivot[1] - sn * ddx + c * ddz - dz)


def uszy(D, P, s, k=1.0):
    """ucho jednej strony (s = -1 / +1): plaskie "skrzydelko" w gore i na boki (nawis ok. 39 st. od poziomu); k = skala wielkosci (jelonek 1,2)"""
    return smin(D, ell_dir(P, (10.8, s * 10.8, 37.2), (-0.20, s * 0.765, 0.628), 6.6 * k, 3.9 * k, 1.8 * k), 2.5 * SM)


def poroze(D, P, s):
    """poroze jednej strony: gruba galaz + 2 odnogi w polowie + 2 koncowki (wszystko pod katem >= 40 st. od poziomu)"""
    B0 = np.array((12.5, s * 4.0, 38.5)); B1 = np.array((12.0, s * 18.4, 49.5))
    M = B0 + 0.45 * (B1 - B0)
    D = smin(D, cap(P, B0, B1, 2.7, 2.1), 1.8 * SM)
    D = smin(D, cap(P, M, M + np.array((6.0, s * 2.2, 6.2)), 2.1, 1.6), 1.6 * SM)       # odnoga do przodu
    D = smin(D, cap(P, M, M + np.array((-6.2, s * 2.0, 6.0)), 2.1, 1.6), 1.6 * SM)      # odnoga do tylu
    D = smin(D, cap(P, B1, B1 + np.array((3.4, s * 0.8, 3.2)), 2.1, 1.5), 1.4 * SM)     # koncowka przod
    D = smin(D, cap(P, B1, B1 + np.array((-3.4, s * 0.6, 3.2)), 2.1, 1.5), 1.4 * SM)    # koncowka tyl
    return D


def uszy_poroze(D, P, s):
    """ucho i poroze jednej strony dodane do pola D (wspolne dla wszystkich pozycji)"""
    return poroze(uszy(D, P, s), P, s)


def uszy_poroze_chude(D, P, s):
    """jak uszy_poroze(), ale z mniejszymi uszami (linia 'chudy'); poroze bez zmian"""
    return poroze(uszy_chude(D, P, s), P, s)


def design(P):
    """pole odleglosci (ujemne w srodku) w jednostkach projektu (wysokosc ok. 50)"""
    D = ell(P, (-1.5, 0, 17.4), (14.5, 10.6, 11.8))                          # tulow (dol nisko: nawisy.carve robi z niego namiot miedzy nogami)
    D = smin(D, ell(P, (7.5, 0, 21.0), (9.0, 9.2, 9.6)), 5 * SM)           # barki
    D = smin(D, ell(P, (-9.5, 0, 19.3), (8.2, 9.6, 9.2)), 5 * SM)          # zad
    D = smin(D, cap(P, (5.0, 0, 22.0), (11.5, 0, 31.5), 6.6, 6.0), 4.5 * SM)   # szyja (gruba i krotka, glowa wyraznie nad barkami)
    D = glowa(D, head_xf(P, 0.0, 0.0, HEAD_PITCH, (11.5, 31.5)))             # glowa z uniesionym pyskiem
    D = smin(D, ell(P, (-17.5, 0, 22.0), (3.0, 2.6, 3.2)), 2.5 * SM)         # ogon
    for s in (-1.0, 1.0):
        # nogi: krotkie, grube kolki, stopy ok. o 7,4 mm
        D = smin(D, cap(P, (8.5, s * 5.6, 15.0), (9.5, s * 6.2, 0.0), 4.5, 3.6), 4 * SM)
        D = smin(D, cap(P, (-9.0, s * 6.0, 15.0), (-10.0, s * 6.8, 0.0), 4.6, 3.7), 4 * SM)
        D = uszy_poroze(D, head_xf(P, 0.0, 0.0, HEAD_PITCH, (11.5, 31.5)), s)
    return D


NAWIS_ANG = 58.0     # kat zbocza od PIONU, do ktorego naprawiamy nawisy (58 st. -> kazde zbocze w dol >= 32 st. od poziomu; prog slicera u nas 25 st.)


def build(S=1.0, vox=VOX, name="jelen_stojacy.stl", target=250000, fn=None, note="jelen stojacy, gladki, 50 mm", fix=True, box=(-25.0, 31.0, -26.0, 26.0), zhi=56.0):
    """S = skala projektu -> mm; siatka w mm, pola liczone na (x/S, y/S, z/S) i mnozone przez S; fix = obciecie nawisow od dolu (nawisy.carve: brzuch jako namiot miedzy nogami, spod pyska rosnie ku nosowi);
    box = (xlo, xhi, ylo, yhi) i zhi = gorna granica siatki w jednostkach projektu (szersza dla glowy obroconej w bok, wyzsza dla dlugiej szyi)"""
    axes, (X, Y, Z) = make_grid(box[0] * S, box[1] * S, box[2] * S, box[3] * S, -0.6, zhi * S, vox)
    D = (fn or design)((X / S, Y / S, Z / S)) * S
    F = smin(-D, Z, 0.5).astype(np.float32)                        # plaskie dno, zaokraglona krawedz stop
    if fix:                                                        # obciecie nawisow od dolu: nic nie wisi w powietrzu (nawisy.carve)
        import nawisy
        F = nawisy.carve(F, vox, axes[2], ang=NAWIS_ANG, zmin=0.0)
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
    ov = float(A[(nz < -math.cos(math.radians(25))) & (zc > 0.5)].sum())   # powierzchnie zboczone < 25 st. od poziomu (prog Bambu u Dominika)
    ov45 = float(A[(nz < -math.cos(math.radians(32))) & (zc > 0.5)].sum())  # < 32 st. od poziomu (granica obciecia nawisy.carve, 58 st. od pionu)
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
    import nawisy
    sl = {t: nawisy.slicer_overhang(m, 0.2, t) for t in (25, 30, 35)}      # prog zbocza od poziomu: 25 = ustawienie Bambu u Dominika
    c6 = sl[25]["area"] <= 8.0 and sl[25]["floating"] <= 0.5 and sl[30]["area"] <= 10.0     # wzorzec: DEER 1 / 2 / 3 maja 47 / 27 / 1 mm2 nawisu i 0 wysp (brzuch to most miedzy nogami)
    print("  nawis jak w Bambu (warstwa 0,2; prog zbocza od poziomu): " + " | ".join(f"{t} st.: {v['area']:.1f} mm2, wyspy {v['floating']:.1f}" for t, v in sl.items())
          + f" (wymog 25 st. <= 8 mm2 i wyspy <= 0,5, 30 st. <= 10 mm2: {'ok' if c6 else 'ZLE'})")
    ok = c1 and c2 and c3 and c4 and c5 and c6
    print(f"  {label}: wysokosc {h:.1f} mm ({'ok' if c1 else 'ZLE'}), wymiary {np.round(m.extents, 1).tolist()}, szczelny {m.is_watertight}, srodek masy ({com[0]:.1f}, {com[1]:.1f}, {com[2]:.1f}) "
          f"{'nad podstawa' if c2 else 'POZA podstawa'}")
    print(f"  stopy lacznie {feet:.0f} mm2 (wymog >= {min_feet:.0f}: {'ok' if c3 else 'ZLE'}), zbocza < 25 st. od poziomu: {ov:.0f} mm2 ({100 * ov / m.area:.1f}% pow.), < 32 st.: {ov45:.0f} mm2, elementy < 2 mm: {thin:.2f}% objetosci ({'ok' if c4 else 'ZLE'}), objetosc {m.volume / 1000:.1f} cm3 -> {'PASS' if ok else 'FAIL'}")
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
