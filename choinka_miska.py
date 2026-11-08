"""Miska-choinka wg oryginalu 'Plätzchen-Schalen' (105 x 141 x 21 mm) - wariant GLADKI, wszystkie krawedzie zaokraglone.
Obrys oryginalu (smukly, 3 pietra, polki, pien) w skali 1,0 (104 x 140 x 21,2 mm) i 0,8 (83 x 112 x 17 mm: 3 szt. na stole 256 x 256); jedyne odstepstwo: czubek 60 st. (TIP_ANG; oryginal 62,3),
dzieki czemu 6 misek ulozonych czubkami do srodka styka sie krawedziami czubka bez nakladania.
Bryla: dno 1,2 mm, sciany skosne FLARE od pionu (bez podpor), scianka 1,6 mm, wnetrze = obrys cofniety o scianke.
Gladkie krawedzie: w planie zaokraglone wszystkie narozniki (wypukle R_CONVEX, wklesle R_REFLEX; na kazdej wysokosci osobno), brzeg gorny
(R_RIM po obu stronach scianki), krawedz dolna (R_BOT), styk scianki z dnem wewnatrz (R_FLOOR) - gladkie minimum (wielomianowe) pol odleglosci.
Zebra (wariant zebrowany) usuniete: w ostrych narozach pieter dawaly poszarpane przejscia na skosach (patrz STANDARD 9b).
Wymiary w mm; z = 0 to stol.
  python3 choinka_miska.py [--scale S ...]      domyslnie 1.0 i 0.8 -> out/choinka_miska_100.stl, out/choinka_miska_80.stl"""
import sys, math, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rev import *
import shapely
from shapely.geometry import Polygon, Point
from shapely import affinity
from scipy.spatial import cKDTree

# ---- parametry (jedna definicja; Python = zrodlo prawdy) ----
H_ORIG = 21.2                    # wysokosc oryginalu
FLOOR = 1.2                      # dno (oryginal 1,2; nie skalowane)
FLARE = 15.0                     # odchylenie scian od pionu (oryginal ok. 15 st.; nawis 15 st. - bez podpor)
WALL = 1.6                       # grubosc scianki (poziomo, w pionowym rownowazniku; 4 petle dyszy 0,4)
R_CONVEX, R_REFLEX = 1.2, 1.5    # zaokraglenie naroznikow w planie: wypukle (czubki pieter, kat pnia) / wklesle (katy polek)
R_CAVITY = 1.0                   # zaokraglenie naroznikow wneki w planie
R_RIM, R_BOT, R_FLOOR = 0.55, 0.4, 1.2   # promienie: brzeg gorny (obie krawedzie), krawedz dolna, styk scianki z dnem we wnetrzu
VOX = 0.25
BED = 256.0                      # stol drukarki (P1S) [mm]
SCALES = (1.0, 0.8)
TIP_ANG = 60.0                   # pelny kat czubka (oryginal 62,3 st.): 60 st. = 6 szt. stykajacych sie czubkami w okregu, krawedzie czubka na dwusiecznych klinow 60 st.
X1 = 49.0 * math.tan(math.radians(TIP_ANG / 2))   # polszerokosc pierwszego naroznika przy glebokosci 49,0 (oryginal 29,6; przy 60 st. = 28,29)
# obrys oryginalu (prawa polowka, 100%): (polszerokosc, glebokosc od czubka); polki poziome, mala pionowa kreska przy narozniku i w kacie polki
ORIG_RIGHT = [(X1, 49.0), (X1, 50.0), (20.8, 50.0), (20.8, 52.6),
              (40.8, 87.7), (40.8, 88.7), (32.0, 88.7), (32.0, 91.3),
              (52.0, 126.1), (52.0, 127.1), (24.1, 127.1), (24.1, 141.2)]
QS = 24                          # segmenty na cwiartke luku zaokraglenia


def k_of(r):
    """parametr gladkiego minimum dla promienia zaokraglenia r (krawedz prostopadla: r ~ 0,853 k)"""
    return r / 0.853


def smin(a, b, k):
    """gladkie minimum (wielomianowe, C1): zaokragla krawedz miedzy bryla a i b (promien ~0,85 k)"""
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def orig_outline(scale=1.0):
    """wierny obrys oryginalu w skali scale, czubek do gory, srodek ramki w (0,0)"""
    right = [(x * scale, -d * scale) for x, d in ORIG_RIGHT]
    verts = [(0.0, 0.0)] + right + [(-x, y) for x, y in reversed(right)]
    poly = Polygon(verts)
    assert poly.is_valid, "obrys nieprawidlowy"
    cy = (poly.bounds[1] + poly.bounds[3]) / 2
    return affinity.translate(poly, 0, -cy)


def round_poly(q, r_convex, r_reflex):
    """zaokragla wszystkie narozniki w planie: otwarcie (wypukle, r_convex), potem domkniecie (wklesle, r_reflex)"""
    if r_convex > 0:
        q = q.buffer(-r_convex, join_style=1, quad_segs=QS).buffer(r_convex, join_style=1, quad_segs=QS)
    if r_reflex > 0:
        q = q.buffer(r_reflex, join_style=1, quad_segs=QS).buffer(-r_reflex, join_style=1, quad_segs=QS)
    if q.geom_type == "MultiPolygon":
        q = max(q.geoms, key=lambda g: g.area)
    return q


def sdf_poly(poly, X, Y, step=0.03):
    """odleglosc ze znakiem (dodatnia w srodku) do obrysu: najblizszy punkt probkowanego brzegu (blad < 0,02 mm), znak z contains_xy"""
    seg = shapely.segmentize(poly, step)
    pts = [np.asarray(seg.exterior.coords)] + [np.asarray(i.coords) for i in seg.interiors]
    d, _ = cKDTree(np.concatenate(pts)).query(np.column_stack([X.ravel(), Y.ravel()]), workers=-1)
    d = d.reshape(X.shape).astype(np.float32)
    return np.where(shapely.contains_xy(poly, X, Y), d, -d)


def bowl_F(P, H, vox=VOX):
    """pole F (dodatnie w materiale) na siatce: obrys kazdej warstwy = rim cofniety o (H - z)*tg(FLARE), zaokraglony; wneka = warstwa cofnieta o scianke"""
    tf = math.tan(math.radians(FLARE))
    tw_h = WALL / math.cos(math.radians(FLARE))
    x0, y0, x1, y1 = P.bounds
    axes, _ = make_grid(x0 - 2.5, x1 + 2.5, y0 - 2.5, y1 + 2.5, -0.6, H + 0.6, vox)
    xs, ys, zs = axes
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Fo = np.empty((len(xs), len(ys), len(zs)), np.float32)
    Fc = np.empty_like(Fo)
    for k, z in enumerate(zs):
        d = max(H - float(z), 0.0) * tf
        S = round_poly(P.buffer(-d, join_style=2, mitre_limit=10) if d > 0 else P, R_CONVEX, R_REFLEX)
        C = round_poly(S.buffer(-tw_h, join_style=2, mitre_limit=10), R_CAVITY, R_CAVITY)
        Fo[:, :, k] = sdf_poly(S, X, Y)
        Fc[:, :, k] = sdf_poly(C, X, Y)
    z = zs[None, None, :]
    Fcav = smin(Fc, z - FLOOR, k_of(R_FLOOR))                    # wneka: sciana + dno, zaokraglone przejscie
    A = smin(Fo, H - z, k_of(R_RIM))                             # zewnetrzna krawedz brzegu
    A = smin(A, z, k_of(R_BOT))                                  # krawedz dolna
    B = smin(-Fcav, H - z, k_of(R_RIM))                          # wewnetrzna krawedz brzegu
    return np.minimum(A, B).astype(np.float32), axes


def build(scale=1.0, vox=VOX):
    """zwraca (mesh, H, nazwa)"""
    P = orig_outline(scale)
    H = round(H_ORIG * scale, 1)
    name = f"choinka_miska_{round(scale * 100)}.stl"
    F, axes = bowl_F(P, H, vox)
    note = f"miska-choinka wg oryginalu x{scale}; gladka, krawedzie zaokraglone; sciana {FLARE:.0f} st., dno {FLOOR} mm, scianka {WALL} mm"
    m = finish(F, axes, vox, name, note, target=300000)
    return m, H, name


def wall_check_mesh(m, H, label="", min_wall=0.9):
    """grubosc scianki (poziomo) na gotowym STL: odleglosc obrysu wneki od obrysu zewnetrznego na 4 wysokosciach (wymog standardu >= 0,8 mm;
    tu z zapasem 0,1 na skos); pojemnosc wneki (calka z przekrojow)"""
    z0 = m.bounds[0][2]
    wmin = 1e9
    for z in (4.0, 8.0, H - 4.0, H - 1.0):
        s = m.section(plane_origin=[0, 0, z0 + z], plane_normal=[0, 0, 1])
        loops = sorted([Polygon(seg[:, :2]).buffer(0) for seg in s.discrete if len(seg) >= 4], key=lambda q: -q.area)
        outer, inner = loops[0], loops[1]
        wmin = min(wmin, min(Point(c).distance(outer.exterior) for c in inner.exterior.coords))
    vol = 0.0
    for z in np.arange(FLOOR + 0.3, H, 1.0):
        s = m.section(plane_origin=[0, 0, z0 + z], plane_normal=[0, 0, 1])
        loops = sorted([Polygon(seg[:, :2]).buffer(0) for seg in s.discrete if len(seg) >= 4], key=lambda q: -q.area)
        vol += loops[1].area * 1.0
    ok = wmin >= min_wall
    print(f"  scianka {label}: min {wmin:.2f} mm (wymog >= {min_wall}) | pojemnosc wneki ok. {vol / 1000:.0f} ml -> {'PASS' if ok else 'FAIL'}")
    return ok


def nest_capacity(scale, gap=4.0):
    """ile sztuk miesci sie na stole, gdy choinki leza naprzemian czubkiem w gore i w dol (zazebiaja sie): rzedy po `pitch` w osi X"""
    P = orig_outline(scale)
    Q = affinity.rotate(P, 180, origin=P.centroid)
    cq = ((Q.bounds[1] + Q.bounds[3]) / 2) - ((P.bounds[1] + P.bounds[3]) / 2)
    Q = affinity.translate(Q, 0, -cq)                                  # ten sam srodek w osi Y
    w = P.bounds[2] - P.bounds[0]
    d = P.bounds[3] - P.bounds[1]
    lo, hi = 0.0, w + gap
    for _ in range(40):
        mid = (lo + hi) / 2
        if P.distance(affinity.translate(Q, mid, 0)) >= gap and Q.distance(affinity.translate(P, mid, 0)) >= gap:
            hi = mid
        else:
            lo = mid
    pitch = max(hi, (w + gap) / 2)
    n_row = 1 + int((BED - w) // pitch)
    n_rows = int((BED + gap) // (d + gap))
    return n_row * n_rows, n_row, n_rows, pitch


def size_check(m, H, label="", scale=1.0):
    """wymiary gotowego STL = oryginal x scale (obrys -2 mm: zaokraglenie czubkow) i ile sztuk miesci sie na stole BED x BED
    (siatka, odstep 4 mm, obie orientacje; oraz naprzemian czubek w gore/w dol). Dla skali <= 0,8 wymog >= 3 szt."""
    w, d, h = (float(v) for v in m.extents)
    want = (104.2 * scale, 141.3 * scale, H)
    cap = max((int((BED + 4) // (a + 4)) * int((BED + 4) // (b + 4))) for a, b in ((w, d), (d, w)))
    ncap, nrow, nrows, pitch = nest_capacity(scale)
    best = max(cap, ncap)
    ok = -2.0 <= w - want[0] <= 0.5 and -2.0 <= d - want[1] <= 0.5 and abs(h - want[2]) <= 0.3 and (best >= 3 or scale > 0.8 + 1e-9)
    print(f"  wymiary {label}: {w:.1f} x {d:.1f} x {h:.1f} mm (oryginal x{scale}: {want[0]:.1f} x {want[1]:.1f} x {want[2]:.1f}) | na stole {BED:.0f} x {BED:.0f}: "
          f"{cap} szt. w siatce, {ncap} szt. naprzemian ({nrow} w rzedzie co {pitch:.0f} mm x {nrows} rz.) -> {'PASS' if ok else 'FAIL'}")
    return ok


def smooth_check(m, label="", limit_deg=50.0, frac_max=2e-4):
    """gladkosc na gotowym STL: kat miedzy sasiednimi scianami trojkatow (kat dwuscienny); ostre krawedzie = kat > limit_deg.
    PASS gdy mniej niz frac_max wszystkich krawedzi jest ostrych (reszta to szum decymacji/siatki)"""
    ang = np.degrees(m.face_adjacency_angles)
    n_sharp = int((ang > limit_deg).sum())
    frac = n_sharp / len(ang)
    ok = frac <= frac_max
    print(f"  gladkosc {label}: krawedzi > {limit_deg:.0f} st.: {n_sharp} z {len(ang):,} ({frac * 100:.4f}%), maks. {ang.max():.0f} st., 99,9 pct {np.percentile(ang, 99.9):.0f} st. -> {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    T0 = time.time()
    args = sys.argv[1:]
    scales = []
    while "--scale" in args:
        i = args.index("--scale")
        scales.append(float(args[i + 1]))
        del args[i:i + 2]
    scales = scales or list(SCALES)
    allok = True
    for sc in scales:
        t = time.time()
        m, H, name = build(scale=sc)
        allok &= size_check(m, H, label=name, scale=sc)
        allok &= wall_check_mesh(m, H, label=name)
        allok &= smooth_check(m, label=name)
        print(f"  {name}: {time.time() - t:.0f} s")
    print(f"czas {time.time() - T0:.0f} s | {'PASS' if allok else 'FAIL'}")
    sys.exit(0 if allok else 1)
