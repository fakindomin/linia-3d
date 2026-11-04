"""Miska-choinka do ukladu w okregu (6 szt.) - wersja linii wg oryginalu 'Plätzchen-Schalen'.
Obrys z pietrami (jak oryginal), ale rozszerzony tak, zeby 6 miseczek zamknelo okrag: naroznik kazdego pietra lezy na linii klina 360/N
(odstep od sasiadki = GAP), skosy pietr maja kat BETA od osi, polki poziome (ok. 8,5 mm jak w oryginale), pien na zewnatrz, czubek do srodka.
Bryla: dno 1,2 mm, sciany skosne FLARE od pionu (bez podpor), wnetrze = obrys cofniety o grubosc scianki; wariant zebrowany (standard linii:
amplituda +-0,8, rozstaw ok. 3,4 mm, zeby zawsze w szczytach na wierzcholkach obrysu, wiec narozniki styka sie z sasiadka tak samo)
i gladki. Wymiary w mm; z = 0 to stol.
  choinka_miska_zebra.stl, choinka_miska_gladka.stl (+ out/choinka_pierscien.png: podglad 6 szt. z przekrojow gotowych STL)"""
import sys, math, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rev import *
import shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import affinity

# ---- parametry (jedna definicja; Python = zrodlo prawdy) ----
N_RING = 6                       # liczba miseczek w okregu (360/N = kat klina)
SCALE = 0.85                     # skala glebokosci pieter wzgledem oryginalu (oryginal: 105 x 142 mm)
BETA = 40.0                      # kat skosu pietra od osi (oryginal: 30 st. przy klinie 41 st.; tu polki ~8,5 mm jak w oryginale 8,8)
GAP = 1.2                        # szczelina miedzy sasiadkami na brzegu [mm]
D_ORIG = (48.7, 86.8, 125.2)     # glebokosc naroznikow pieter od czubka w oryginale
TRUNK_HW, TRUNK_L = 24.1, 12.0   # polszerokosc i dlugosc pnia w oryginale
H = 21.2                         # wysokosc miski (oryginal 21,2)
FLOOR = 1.2                      # dno (oryginal 1,2)
FLARE = 15.0                     # odchylenie scian od pionu (oryginal ok. 15 st.; nawis 15 st. - bez podpor)
WALL_RIB, WALL_PLAIN = 2.6, 1.6  # grubosc scianki (normalna) w szczycie zebra / wariant gladki; w dolince zebra: -1,6 mm
VOX = 0.3
FADE0, FADE1 = 0.8, 3.0                # zanik zeber przy wierzcholkach obrysu [mm]


def tree_outline(N=N_RING, scale=SCALE, beta=BETA, gap=GAP, d=D_ORIG, trunk_hw=TRUNK_HW, trunk_l=TRUNK_L):
    """obrys na brzegu (szczyty zeber) w ukladzie okregu: srodek kola (0,0), os drzewka +y, czubek przy y = r0, pien na zewnatrz"""
    psi = math.pi / N
    tp, tb = math.tan(psi), math.tan(math.radians(beta))
    off = gap / 2 / math.cos(psi)                        # odsuniecie naroznika od linii klina (szczelina gap)
    dd = [x * scale for x in d]
    r0 = (dd[0] * tb + off) / tp - dd[0]                 # odleglosc czubka od srodka kola (pierwsze pietro ma kat beta)
    W = [(r0 + x) * tp - off for x in dd]                # polszerokosci naroznikow pieter (na linii klina)
    hw = trunk_hw * scale ** 0.5
    right = []
    for i in range(len(dd)):
        right.append((W[i], r0 + dd[i]))
        right.append((W[i + 1] - tb * (dd[i + 1] - dd[i]) if i + 1 < len(dd) else hw, r0 + dd[i]))
    right.append((hw, r0 + dd[-1] + trunk_l))
    verts = [(0.0, r0)] + right + [(-x, y) for x, y in reversed(right)]
    poly = Polygon(verts)
    assert poly.is_valid, "obrys nieprawidlowy"
    return poly, dict(r0=r0, W=W, ledge=[(tb - tp) * (dd[i + 1] - dd[i]) for i in range(len(dd) - 1)], R_out=r0 + dd[-1] + trunk_l)


def poly_sdf_rib(poly, xs, ys, amp, pitch=RIB_PITCH):
    """odleglosc ze znakiem (dodatnia w srodku) do obrysu + przesuniecie zebrowe (<= 0): w kazdej krawedzi calkowita liczba zeber,
    szczyty (przesuniecie 0) na wierzcholkach; krawedzie < 3 mm bez zeber"""
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    V = np.array(poly.exterior.coords)[:-1]
    best = np.full(X.shape, np.inf)
    off = np.zeros(X.shape, np.float32)
    for i in range(len(V)):
        a, b = V[i], V[(i + 1) % len(V)]
        e = b - a
        L = float(np.hypot(*e))
        if L < 1e-6:
            continue
        px, py = X - a[0], Y - a[1]
        t = np.clip((px * e[0] + py * e[1]) / (L * L), 0.0, 1.0)
        dx, dy = px - t * e[0], py - t * e[1]
        d2 = dx * dx + dy * dy
        m = d2 < best
        n = int(round(L / pitch)) if L >= 3.0 else 0
        if amp > 0 and n > 0:
            c = np.cos(2 * np.pi * n * t)
            r = (amp * np.sign(c) * np.abs(c) ** 0.8 - amp).astype(np.float32)
            off = np.where(m, r, off)
        else:
            off = np.where(m, np.float32(0.0), off)
        best = np.where(m, d2, best)
    # przy wierzcholkach zebra zanikaja (0,8 -> 3,0 mm): ostry naroznik pietra zostaje pelny i styka sie z sasiadka tak jak w obrysie
    dv = np.full(X.shape, np.inf)
    for vx, vy in V:
        dv = np.minimum(dv, np.hypot(X - vx, Y - vy))
    off = off * sstep(dv, FADE0, FADE1).astype(np.float32)
    inside = shapely.contains_xy(poly, X, Y)
    sd = np.where(inside, np.sqrt(best), -np.sqrt(best)).astype(np.float32)
    return sd, off


def bowl_F(poly, ribbed, vox=VOX):
    """pole F (dodatnie w materiale): skosne sciany, dno, zebra na zewnatrz"""
    amp = RIB_AMP if ribbed else 0.0
    wall = WALL_RIB if ribbed else WALL_PLAIN
    tf = math.tan(math.radians(FLARE))
    tw_h = wall / math.cos(math.radians(FLARE))
    x0, y0, x1, y1 = poly.bounds
    axes, _ = make_grid(x0 - 2.5, x1 + 2.5, y0 - 2.5, y1 + 2.5, -0.6, H + 0.6, vox)
    xs, ys, zs = axes
    sd, off = poly_sdf_rib(poly, xs, ys, amp)
    z = zs[None, None, :]
    d = np.maximum(H - z, 0.0) * tf                              # cofniecie obrysu na wysokosci z (skos)
    sd3, off3 = sd[:, :, None], off[:, :, None]
    Fo = sd3 - d + off3                                          # bryla zewnetrzna (dodatnie w srodku)
    Fc = np.minimum(sd3 - d - tw_h, z - FLOOR)                   # wneka: obrys cofniety o scianke, dno plaskie
    F = np.minimum(np.minimum(Fo, -Fc), np.minimum(z, H - z))
    return F.astype(np.float32), axes


def build(ribbed, vox=VOX):
    poly, info = tree_outline()
    # ukad pliku: czubek w gore (os +y), srodek miski w (0,0): obrot o 180 st. wokol srodka kola, potem przesuniecie
    up = affinity.rotate(poly, 180, origin=(0, 0))
    cy = (up.bounds[1] + up.bounds[3]) / 2
    up = affinity.translate(up, 0, -cy)
    F, axes = bowl_F(up, ribbed, vox)
    name = "choinka_miska_zebra.stl" if ribbed else "choinka_miska_gladka.stl"
    note = f"miska-choinka do okregu {N_RING} szt.; {'zebra +-0,8' if ribbed else 'gladka'}; sciana {FLARE:.0f} st., dno {FLOOR} mm"
    m = finish(F, axes, vox, name, note, target=300000)
    return m, info, (0.0, -cy)               # srodek kola w ukladzie pliku


def ring_check_mesh(m, center, N=N_RING, gap=GAP, label=""):
    """kontrola na GOTOWYM STL: przekroj tuz pod brzegiem, N kopii obroconych o 360/N wokol srodka kola (center, w ukladzie pliku) ->
    najmniejsza odleglosc miedzy sasiadkami, nachodzenie"""
    s = m.section(plane_origin=[0, 0, m.bounds[0][2] + H - 0.4], plane_normal=[0, 0, 1])
    rim = unary_union([Polygon(seg[:, :2]).buffer(0) for seg in s.discrete if len(seg) >= 4])
    rim = max(rim.geoms, key=lambda g: g.area) if rim.geom_type == "MultiPolygon" else rim
    cy = center[1]
    best, ov = 1e9, 0.0
    cp = [affinity.rotate(rim, k * 360.0 / N, origin=(0.0, cy)) for k in range(N)]
    for i in range(N):
        best = min(best, cp[i].distance(cp[(i + 1) % N]))
        ov += cp[i].intersection(cp[(i + 1) % N]).area
    ok = ov < 1e-3 and gap - 0.35 <= best <= gap + 1.6      # ostre narozniki pieter zaokraglaja sie o ok. 0,5 mm (siatka, cofniecie obrysu na skosie)
    print(f"  pierscien {N} szt. {label}: min szczelina {best:.2f} mm (projekt {gap}, dopuszczalnie {gap-0.35:.2f}..{gap+1.6:.2f}), nachodzenie {ov:.4f} mm2 -> {'PASS' if ok else 'FAIL'}")
    return ok, cp, (0.0, cy)


def wall_check_mesh(m, label="", min_wall=0.9):
    """grubosc scianki (poziomo) na gotowym STL: odleglosc obrysu wneki od obrysu zewnetrznego na 4 wysokosciach (wymog standardu >= 0,8 mm;
    tu z zapasem 0,1 na skos); pojemnosc wneki (calka z przekrojow)"""
    from shapely.geometry import Point
    z0 = m.bounds[0][2]
    wmin = 1e9
    for z in (4.0, 10.0, 18.0, H - 0.5):
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


def ring_preview(cp, center, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 8))
    for i, p in enumerate(cp):
        xs, ys = p.exterior.xy
        ax.fill(xs, ys, color="#8a9a7b" if i % 2 == 0 else "#a9b497", ec="#333", lw=0.7)
        for h in p.interiors:
            hx, hy = h.xy
            ax.fill(hx, hy, color="white")
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(f"{len(cp)} miseczek w okregu (przekroj przy brzegu, szczelina {GAP} mm)", fontsize=10)
    plt.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    T0 = time.time()
    which = sys.argv[1:] or ["zebra", "gladka"]
    allok = True
    for w in which:
        t = time.time()
        m, info, c = build(w == "zebra")
        ok, cp, c = ring_check_mesh(m, c, label=w)
        allok &= ok
        allok &= wall_check_mesh(m, label=w)
        if w == "zebra":
            ring_preview(cp, c, os.path.join(OUT, "choinka_pierscien.png"))
        print(f"  {w}: {time.time() - t:.0f} s")
    print(f"czas {time.time() - T0:.0f} s | {'PASS' if allok else 'FAIL'}")
    sys.exit(0 if allok else 1)
