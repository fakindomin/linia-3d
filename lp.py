"""Linia lowpoly - narzedzia: bryly z pierscieni (naprzemiennie przesunietych -> trojkaty), hulle (czesci wypukle),
operacje boolowskie (manifold3d), offset, rzut promienia, zapis. Wymiary w mm, z = 0 to stol."""
import sys, math
import numpy as np
import trimesh
import manifold3d as m3d
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *


# ---------- konwersje i boolean ----------
def MF(mesh):
    mesh = mesh.copy()
    trimesh.repair.fix_normals(mesh)
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32), tri_verts=np.asarray(mesh.faces, np.uint32)))


def _f32_ok(m):
    """czy siatka zostaje szczelna po zapisie do STL (float32) i ponownym wczytaniu (to widzi slicer)"""
    if len(m.faces) == 0:
        return False
    r = trimesh.Trimesh(np.asarray(m.vertices, np.float32).astype(float), m.faces, process=True)
    return bool(r.is_watertight) and len(r.faces) > 0


def TM(man):
    """Manifold -> Trimesh. Preferuje wersje ze sklejonymi wierzcholkami bliskimi na 1e-4 mm (slivery zanikaja spojnie),
    ale tylko jesli jest szczelna takze po rzutowaniu na float32; inaczej zwraca surowy wynik manifold3d."""
    mm = man.to_mesh()
    raw = trimesh.Trimesh(np.asarray(mm.vert_properties[:, :3], float), np.asarray(mm.tri_verts), process=False)
    m = raw.copy()
    m.merge_vertices(digits_vertex=4)
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    if m.is_watertight and _f32_ok(m):
        return m
    return raw


def union(*ms):
    out = MF(ms[0])
    for m in ms[1:]:
        out = out + MF(m)
    return TM(out)


def diff(a, *bs):
    out = MF(a)
    for b in bs:
        out = out - MF(b)
    return TM(out)


def inter(a, b):
    return TM(MF(a) ^ MF(b))


def offset(mesh, d, n=8):
    """offset (Minkowski z kulka o promieniu d): gladki, odporny; do luzu miedzy czescia a korpusem"""
    return TM(MF(mesh).minkowski_sum(m3d.Manifold.sphere(d, n)))


# ---------- ksztalty ----------
def kM(M):
    """promien wierzcholkowy / promien kola o tym samym polu dla foremnego M-kata"""
    return math.sqrt(2 * math.pi / (M * math.sin(2 * math.pi / M)))


def hull(points):
    return trimesh.convex.convex_hull(np.asarray(points, float))


def revolve_rings(zr, M, phase=0.0, eqarea=True, j0=0):
    """bryla obrotowa z pierscieni (z, r[, p]) rosnaco. Pierscienie naprzemiennie przesuniete o pi/M (pas trojkatow);
    p = 0/1 wymusza faze, 'same' = jak poprzedni (pas prostych scian = graniastoslup); r <= 0 na koncu/poczatku -> wierzcholek;
    inaczej plaska podstawa/wieko (wachlarz do srodka). j0 - parzystosc pierwszego pierscienia (dla czesci scietych w szwie)."""
    k = kM(M) if eqarea else 1.0
    ph = []
    for j, e in enumerate(zr):
        p = e[2] if len(e) > 2 else None
        if p is None:
            p = (j0 % 2) if j == 0 else 1 - ph[-1]
        elif p == "same":
            p = ph[-1]
        ph.append(int(p))
    V, rings = [], []
    for j, e in enumerate(zr):
        z, r = e[0], e[1]
        if r <= 1e-9:
            V.append((0.0, 0.0, z)); rings.append([len(V) - 1]); continue
        ang = phase + ph[j] * math.pi / M + 2 * math.pi * np.arange(M) / M
        idx = []
        for a in ang:
            V.append((r * k * math.cos(a), r * k * math.sin(a), z)); idx.append(len(V) - 1)
        rings.append(idx)
    F = []
    for j in range(len(zr) - 1):
        A, B = rings[j], rings[j + 1]
        if len(A) == 1:                       # apex na dole
            for k_ in range(M):
                F.append((A[0], B[(k_ + 1) % M], B[k_]))
        elif len(B) == 1:                     # apex na gorze
            for k_ in range(M):
                F.append((A[k_], A[(k_ + 1) % M], B[0]))
        elif ph[j] == 0 and ph[j + 1] == 1:
            for k_ in range(M):
                F.append((A[k_], A[(k_ + 1) % M], B[k_]))
                F.append((A[(k_ + 1) % M], B[(k_ + 1) % M], B[k_]))
        else:                                 # 1 -> 0 albo ta sama faza (prostokaty dzielone na 2 trojkaty)
            for k_ in range(M):
                F.append((A[k_], A[(k_ + 1) % M], B[(k_ + 1) % M]))
                F.append((A[k_], B[(k_ + 1) % M], B[k_]))
    for ring, top in ((rings[0], False), (rings[-1], True)):      # zaslepki
        if len(ring) > 1:
            V.append((0.0, 0.0, V[ring[0]][2])); c = len(V) - 1
            for k_ in range(M):
                F.append((c, ring[k_], ring[(k_ + 1) % M]) if top else (c, ring[(k_ + 1) % M], ring[k_]))
    m = trimesh.Trimesh(np.array(V), np.array(F), process=False)
    m.merge_vertices()
    trimesh.repair.fix_normals(m)
    if m.volume < 0:
        m.invert()
    return m


def prism(M, r, z0, z1, phase=0.0, eqarea=True):
    """graniastoslup foremny (M-kat) o r rownowaznym polu kola"""
    return revolve_rings([(z0, r, 0), (z1, r, "same")], M, phase, eqarea)


def loft(rings, apex=None, cap_start=True):
    """zamknieta bryla z kolejnych obrysow (kazdy: K wierzcholkow, wypukly, ta sama kolejnosc); koniec: wierzcholek apex albo zaslepka"""
    V, idx = [], []
    for r in rings:
        idx.append(list(range(len(V), len(V) + len(r)))); V.extend([tuple(map(float, p)) for p in r])
    K = len(rings[0])
    F = []
    for A, B in zip(idx[:-1], idx[1:]):
        for k in range(K):
            k1 = (k + 1) % K
            F.append((A[k], A[k1], B[k1])); F.append((A[k], B[k1], B[k]))
    if cap_start:
        for k in range(1, K - 1):
            F.append((idx[0][0], idx[0][k + 1], idx[0][k]))
    if apex is None:
        for k in range(1, K - 1):
            F.append((idx[-1][0], idx[-1][k], idx[-1][k + 1]))
    else:
        V.append(tuple(map(float, apex))); ap = len(V) - 1
        for k in range(K):
            F.append((idx[-1][k], idx[-1][(k + 1) % K], ap))
    m = trimesh.Trimesh(np.array(V), np.array(F), process=False)
    m.merge_vertices()
    trimesh.repair.fix_normals(m)
    if m.volume < 0:
        m.invert()
    return m


def chamfer_box(lo, hi, ch):
    """prostopadloscian ze sfazowanymi krawedziami (convex hull): kazdy naroznik rozbity na 3 punkty przesuniete o ch wzdluz krawedzi"""
    pts = []
    xs, ys, zs = (lo[0], hi[0]), (lo[1], hi[1]), (lo[2], hi[2])
    for ix, x in enumerate(xs):
        for iy, y in enumerate(ys):
            for iz, z in enumerate(zs):
                dx = ch if ix == 0 else -ch
                dy = ch if iy == 0 else -ch
                dz = ch if iz == 0 else -ch
                pts += [(x + dx, y, z), (x, y + dy, z), (x, y, z + dz)]
    return hull(pts)


def pillow_box(a0, a1, b0, b1, T, wall=1.0, ch=1.2):
    """plyta do druku na plecach (c = 0): pionowa scianka do c = wall, potem sciecie ch do c = T (gora faseta)"""
    pts = []
    for (a, b) in ((a0, b0), (a1, b0), (a1, b1), (a0, b1)):
        pts += [(a, b, 0.0), (a, b, wall)]
        da = ch if a == a0 else -ch
        db = ch if b == b0 else -ch
        pts += [(a + da, b + db, T)]
    return hull(pts)


def to_global(m, fr):
    g = m.copy(); g.apply_transform(fr.matrix()); return g


def to_local(m, fr):
    g = m.copy(); g.apply_transform(np.linalg.inv(fr.matrix())); return g


def top_z_at(mesh, x, y):
    """najwyzsze z powierzchni siatki nad punktem (x, y) (test trojkatow w rzucie)"""
    tri = mesh.triangles
    p = np.array([x, y])
    a, b, c = tri[:, 0, :2], tri[:, 1, :2], tri[:, 2, :2]
    v0, v1, v2 = b - a, c - a, p - a
    d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1)
    d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    ok = np.abs(den) > 1e-12
    den = np.where(ok, den, 1.0)
    u = (d11 * d20 - d01 * d21) / den
    v = (d00 * d21 - d01 * d20) / den
    w = 1 - u - v
    inside = ok & (u >= -1e-9) & (v >= -1e-9) & (w >= -1e-9)
    z = w * tri[:, 0, 2] + u * tri[:, 1, 2] + v * tri[:, 2, 2]
    return float(z[inside].max())


def flat_view(m):
    """kopia z rozdzielonymi wierzcholkami (plaskie cieniowanie w podgladzie)"""
    f = m.faces
    return trimesh.Trimesh(m.vertices[f].reshape(-1, 3), np.arange(3 * len(f)).reshape(-1, 3), process=False)


def save_lp(m, name, upright=True, note=""):
    m = m.copy()
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    trimesh.repair.fix_normals(m)
    return save(m, name, upright, note)


# =====================================================================================================
# STANDARD LOWPOLY: pierscienie o dowolnej liczbie wierzcholkow (zipper po katach), auto-dobor pierscieni
# =====================================================================================================
def ring_regular(z, r, M, half=0, eqarea=True):
    """pierscien foremny M-kat o polu kola r; half = 1 -> przesuniecie o pol kroku (pas trojkatow z poprzednim)"""
    k = kM(M) if eqarea else 1.0
    ang = (half * 0.5 + np.arange(M)) * 2 * math.pi / M
    return dict(z=float(z), ang=ang, rad=np.full(M, r * k), apex=r <= 1e-9, half=half, M=M)


def ring_lobed(z, r, N, depth, half=0):
    """pierscien 2N-katny: grzbiety (promien r) i rowki (r - depth) naprzemiennie (N platow)"""
    ang = (half * 0.5 + np.arange(2 * N)) * math.pi / N
    rad = np.where(np.arange(2 * N) % 2 == 0, r, r - depth)
    return dict(z=float(z), ang=ang, rad=rad.astype(float), apex=r <= 1e-9, half=half, M=2 * N)


def _zip_strip(A, B, F, tie="chevron"):
    """trojkaty miedzy dwoma pierscieniami (listy indeksow wierzcholkow + katy rosnace w [0, 2pi)); zipper po katach"""
    ia, aa = A
    ib, ab = B
    na, nb = len(ia), len(ib)
    a0 = aa[0]
    # B: najwiekszy kat <= a0 (cyklicznie)
    jb = max((j for j in range(nb) if ab[j] <= a0 + 1e-9), default=nb - 1)
    i = 0
    j = jb
    ang_a = lambda i_: aa[i_ % na] + 2 * math.pi * (i_ // na)
    ang_b = lambda j_: ab[j_ % nb] + 2 * math.pi * ((j_ - jb) // nb if False else (j_ // nb))
    # ustaw wspolna oś: kat B_jb moze byc <= a0 (lub poprzedni obrot)
    if ab[jb] > a0 + 1e-9:
        base_b = -2 * math.pi
    else:
        base_b = 0.0
    ang_b = lambda j_: ab[j_ % nb] + base_b + 2 * math.pi * (j_ // nb) if j_ >= 0 else ab[j_ % nb] + base_b
    end_i, end_j = na, jb + nb
    while i < end_i or j < end_j:
        na_ = ang_a(i + 1) if i < end_i else 1e9
        nb_ = ang_b(j + 1) if j < end_j else 1e9
        if abs(na_ - nb_) < 1e-7 and i < end_i and j < end_j:
            adv_a = (i % 2 == 1) if tie == "chevron" else True     # remis: przekatna zalezna od parzystosci (jodelka)
        else:
            adv_a = na_ < nb_
        if adv_a:
            F.append((ia[i % na], ia[(i + 1) % na], ib[j % nb]))
            i += 1
        else:
            F.append((ia[i % na], ib[(j + 1) % nb], ib[j % nb]))
            j += 1


def revolve_polys(rings, tie="chevron"):
    """bryla obrotowa z pierscieni (ring_regular / ring_lobed) rosnaco po z (moga byc tez malejace: zaglebienie);
    pierscien z apex=True -> pojedynczy wierzcholek; pierwszy i ostatni pierscien (nie apex) zamykane wachlarzem"""
    V, ids = [], []
    for rg in rings:
        if rg["apex"]:
            V.append((0.0, 0.0, rg["z"])); ids.append(([len(V) - 1], np.array([0.0])))
            continue
        idx = []
        for a, r in zip(rg["ang"], rg["rad"]):
            V.append((r * math.cos(a), r * math.sin(a), rg["z"])); idx.append(len(V) - 1)
        ids.append((idx, np.mod(rg["ang"], 2 * math.pi)))
    # kolejnosc po katach rosnaco (ang jest rosnace od half*0.5*step; po mod moze nie byc posortowane przy half) -> posortuj
    srt = []
    for idx, ang in ids:
        if len(idx) > 1:
            o = np.argsort(ang); srt.append(([idx[k] for k in o], ang[o]))
        else:
            srt.append((idx, ang))
    ids = srt
    F = []
    for j in range(len(rings) - 1):
        A, B = ids[j], ids[j + 1]
        if len(A[0]) == 1:
            for k in range(len(B[0])):
                F.append((A[0][0], B[0][(k + 1) % len(B[0])], B[0][k]))
        elif len(B[0]) == 1:
            for k in range(len(A[0])):
                F.append((A[0][k], A[0][(k + 1) % len(A[0])], B[0][0]))
        else:
            _zip_strip(A, B, F, tie)
    for pos, top in ((0, False), (-1, True)):
        idx = ids[pos][0]
        if len(idx) > 1:
            V.append((0.0, 0.0, V[idx[0]][2])); c = len(V) - 1
            for k in range(len(idx)):
                F.append((c, idx[k], idx[(k + 1) % len(idx)]) if top else (c, idx[(k + 1) % len(idx)], idx[k]))
    m = trimesh.Trimesh(np.array(V), np.array(F), process=False)
    m.merge_vertices()
    trimesh.repair.fix_normals(m)
    if m.volume < 0:
        m.invert()
    return m


def facet_M(R, div=4.0, mn=8):
    """STANDARD: liczba bokow wielokata dla promienia R [mm]: M = 2 * floor(R / 4 + 0.5), min 8 (fasety ~ 12 mm w kazdym modelu)"""
    return max(mn, 2 * int(math.floor(R / div + 0.5)))


def auto_rings(R, z0, z1, tol=0.35, dz_max=8.0, dz_min=0.8, slope_max=1.30, forced=(), local=()):
    """STANDARD: dobor wysokosci pierscieni dla profilu R(z) (promien rownowazny): najwiekszy krok, przy ktorym odchylka profilu od cieciwy
    <= tol [mm], krok <= dz_max, a cieciwa zwrocona w dol (r rosnie z z) ma nachylenie <= slope_max (nawis ~52 st. od pionu).
    forced = z, ktore musza byc pierscieniami (zalamania profilu); local = [(za, zb, dz)] - gestsze pierscienie przy punktach mocowania."""
    forced = sorted(f for f in forced if z0 + 1e-6 < f < z1 - 1e-6) + [z1]
    zs = [z0]
    z = z0
    Rf = lambda x: float(R(np.float64(x)))
    while z < z1 - 1e-9:
        zmax = min(z + dz_max, forced[0] if forced[0] > z + 1e-9 else z1)
        for za, zb, dz in local:
            if za - dz <= z <= zb:
                zmax = min(zmax, z + dz)
        zmax = min(zmax, z1)
        best = None
        n = 0
        lo = z + dz_min if z + dz_min < zmax else zmax
        zn = zmax
        # od najwiekszego kroku w dol, az spelni tolerancje
        while zn >= lo - 1e-9:
            zz = np.linspace(z, zn, 11)[1:-1]
            chord = np.interp(zz, [z, zn], [Rf(z), Rf(zn)])
            dev = np.abs(np.array([Rf(x) for x in zz]) - chord).max() if len(zz) else 0.0
            if dev <= tol:
                best = zn
                break
            zn -= 0.1
        if best is None:
            best = lo
        z = best
        zs.append(z)
        while forced and z >= forced[0] - 1e-9 and len(forced) > 1:
            forced.pop(0)
    return zs
