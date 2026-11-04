"""Miska-choinka wg oryginalu 'Plätzchen-Schalen' (105 x 141 x 21 mm): zebrowana (standard linii) i gladka.
Domyslnie WIERNY obrys oryginalu (smukly, 3 pietra, polki, pien) w skali SCALE_OUT = 0.8 (84 x 113 x 17 mm), tak zeby na stole 256 x 256 mieszcza sie
3-4 szt. Bryla: dno 1,2 mm, sciany skosne FLARE od pionu (bez podpor), wnetrze = obrys cofniety o grubosc scianki, zebra standardowe (+-0,8, rozstaw ok. 3,4 mm,
szczyty na wierzcholkach, zanik przy wierzcholkach). Wymiary w mm; z = 0 to stol.
Opcja `--ring N` (tryb pierscienia): choinka poszerzona tak, ze N szt. zamyka okrag (narozniki pieter na liniach klinow 360/N, szczelina GAP) - jest wtedy grubsza
(N = 6: 145 x 118); N = 9 daje prawie oryginalna sylwetke.
  python3 choinka_miska.py [zebra] [gladka] [--ring N]
  choinka_miska_zebra.stl, choinka_miska_gladka.stl (+ choinka_miska_p{N}_*.stl i out/choinka_pierscien.png dla --ring)"""
import sys, math, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rev import *
import shapely
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely import affinity

# ---- parametry (jedna definicja; Python = zrodlo prawdy) ----
SCALE_OUT = 0.8                  # skala obrysu i wysokosci wzgledem oryginalu (oryginal 105 x 141 x 21,2 mm -> 84 x 113 x 17)
H_ORIG = 21.2                    # wysokosc oryginalu
FLOOR = 1.2                      # dno (oryginal 1,2; nie skalowane)
FLARE = 15.0                     # odchylenie scian od pionu (oryginal ok. 15 st.; nawis 15 st. - bez podpor)
WALL_RIB, WALL_PLAIN = 2.6, 1.6  # grubosc scianki (normalna) w szczycie zebra / wariant gladki; w dolince zebra: -1,6 mm (nie skalowane)
VOX = 0.3
FADE0, FADE1 = 0.8, 3.0          # zanik zeber przy wierzcholkach obrysu [mm]
BED = 256.0                      # stol drukarki (P1S) [mm]
# obrys oryginalu (prawa polowka, 100%): (polszerokosc, glebokosc od czubka); polki poziome, mala pionowa kreska przy narozniku i w kacie polki
ORIG_RIGHT = [(29.6, 49.0), (29.6, 50.0), (20.8, 50.0), (20.8, 52.6),
              (40.8, 87.7), (40.8, 88.7), (32.0, 88.7), (32.0, 91.3),
              (52.0, 126.1), (52.0, 127.1), (24.1, 127.1), (24.1, 141.2)]
# tryb pierscienia
N_RING, SCALE_RING, BETA, GAP = 6, 0.85, 40.0, 1.2
D_ORIG = (48.7, 86.8, 125.2)     # glebokosc naroznikow pieter od czubka w oryginale
TRUNK_HW, TRUNK_L = 24.1, 12.0   # polszerokosc i dlugosc pnia w oryginale


def orig_outline(scale=SCALE_OUT):
    """wierny obrys oryginalu w skali scale, czubek do gory, srodek ramki w (0,0)"""
    right = [(x * scale, -d * scale) for x, d in ORIG_RIGHT]
    verts = [(0.0, 0.0)] + right + [(-x, y) for x, y in reversed(right)]
    poly = Polygon(verts)
    assert poly.is_valid, "obrys nieprawidlowy"
    cy = (poly.bounds[1] + poly.bounds[3]) / 2
    return affinity.translate(poly, 0, -cy)


def tree_outline(N=N_RING, scale=SCALE_RING, beta=BETA, gap=GAP, d=D_ORIG, trunk_hw=TRUNK_HW, trunk_l=TRUNK_L):
    """tryb pierscienia: obrys na brzegu w ukladzie okregu: srodek kola (0,0), os drzewka +y, czubek przy y = r0, pien na zewnatrz"""
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
    # przy wierzcholkach zebra zanikaja (0,8 -> 3,0 mm): ostry naroznik pietra zostaje pelny
    # (w ostrych wierzcholkach < 80 st. strefa zaniku rosnie ~1/sin(kat/2): czubek nie jest sciety zebrami)
    fade = np.ones(X.shape, np.float32)
    n = len(V)
    for i in range(n):
        vx, vy = V[i]
        u, w = V[i - 1] - V[i], V[(i + 1) % n] - V[i]
        cosang = float(np.dot(u, w) / (np.linalg.norm(u) * np.linalg.norm(w) + 1e-12))
        ang = math.acos(max(-1.0, min(1.0, cosang)))
        k = 1.0 / math.sin(ang / 2) if ang < math.radians(80) else 1.0
        dv = np.hypot(X - vx, Y - vy)
        fade = np.minimum(fade, sstep(dv, FADE0 * k, FADE1 * k).astype(np.float32))
    off = off * fade
    inside = shapely.contains_xy(poly, X, Y)
    sd = np.where(inside, np.sqrt(best), -np.sqrt(best)).astype(np.float32)
    return sd, off


def bowl_F(poly, ribbed, H, vox=VOX):
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


def build(ribbed, ring=None, vox=VOX):
    """zwraca (mesh, info, srodek_kola, H, nazwa); srodek kola tylko w trybie pierscienia"""
    if ring:
        poly, info = tree_outline(N=ring)
        H = H_ORIG
        up = affinity.rotate(poly, 180, origin=(0, 0))          # czubek w gore, srodek kola w (0,0), potem przesuniecie
        cy = (up.bounds[1] + up.bounds[3]) / 2
        up = affinity.translate(up, 0, -cy)
        center = (0.0, -cy)
        base = f"choinka_miska_p{ring}"
        note = f"miska-choinka do okregu {ring} szt."
    else:
        up = orig_outline()
        info, center = {}, None
        H = round(H_ORIG * SCALE_OUT, 1)
        base = "choinka_miska"
        note = f"miska-choinka wg oryginalu x{SCALE_OUT}"
    F, axes = bowl_F(up, ribbed, H, vox)
    name = f"{base}_{'zebra' if ribbed else 'gladka'}.stl"
    note += f"; {'zebra +-0,8' if ribbed else 'gladka'}; sciana {FLARE:.0f} st., dno {FLOOR} mm"
    m = finish(F, axes, vox, name, note, target=300000)
    return m, info, center, H, name


def ring_check_mesh(m, center, H, N=N_RING, gap=GAP, label=""):
    """tryb pierscienia, na GOTOWYM STL: przekroj tuz pod brzegiem, N kopii obroconych o 360/N wokol srodka kola (center, w ukladzie pliku) ->
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


def wall_check_mesh(m, H, label="", min_wall=0.9):
    """grubosc scianki (poziomo) na gotowym STL: odleglosc obrysu wneki od obrysu zewnetrznego na 4 wysokosciach (wymog standardu >= 0,8 mm;
    tu z zapasem 0,1 na skos); pojemnosc wneki (calka z przekrojow)"""
    z0 = m.bounds[0][2]
    wmin = 1e9
    for z in (4.0, 8.0, H - 4.0, H - 0.5):
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


def size_check(m, H, label=""):
    """wymiary gotowego STL = oryginal x SCALE_OUT (+-1 mm) i ile sztuk miesci sie na stole BED x BED (siatka, odstep 4 mm, obie orientacje)"""
    w, d, h = (float(v) for v in m.extents)
    want = (104.2 * SCALE_OUT, 141.3 * SCALE_OUT, H)
    cap = max((int((BED + 4) // (a + 4)) * int((BED + 4) // (b + 4))) for a, b in ((w, d), (d, w)))
    ok = abs(w - want[0]) <= 1.5 and abs(d - want[1]) <= 1.5 and abs(h - want[2]) <= 0.3 and cap >= 3
    print(f"  wymiary {label}: {w:.1f} x {d:.1f} x {h:.1f} mm (oryginal x{SCALE_OUT}: {want[0]:.1f} x {want[1]:.1f} x {want[2]:.1f}) | na stole {BED:.0f} x {BED:.0f} miesci sie {cap} szt. -> {'PASS' if ok else 'FAIL'}")
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
    args = sys.argv[1:]
    ring = None
    if "--ring" in args:
        i = args.index("--ring")
        ring = int(args[i + 1])
        del args[i:i + 2]
    which = args or ["zebra", "gladka"]
    allok = True
    for w in which:
        t = time.time()
        m, info, c, H, name = build(w == "zebra", ring=ring)
        if ring:
            ok, cp, c = ring_check_mesh(m, c, H, N=ring, label=w)
            allok &= ok
            if w == "zebra":
                ring_preview(cp, c, os.path.join(OUT, "choinka_pierscien.png"))
        else:
            allok &= size_check(m, H, label=w)
        allok &= wall_check_mesh(m, H, label=w)
        print(f"  {w}: {time.time() - t:.0f} s")
    print(f"czas {time.time() - T0:.0f} s | {'PASS' if allok else 'FAIL'}")
    sys.exit(0 if allok else 1)
