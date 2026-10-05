"""STANDARD LINII v1.0 - JEDNO ZRODLO PRAWDY dla modeli zebrowanych (rb) i lowpoly (lp).

Kazdy nowy model (zebra albo lowpoly) pisze sie WYLACZNIE przez ten modul (+ models.py jako wzor danych):

    from standard import *

Tu sa: stale, reguly, narzedzia obu stylow, porty (czop/gniazdo), koperta (envelope) dla czesci wymiennych, kontrole, zapis.
Nic nie trzeba odczytywac z innych modeli. Opis i przepis krok po kroku: STANDARD.md, szablon: new_model_template.py.

KONTRAKT (wszystko ponizej jest sprawdzane przez verify_all.py):
 1. Wymiary mm, z = 0 to stol, plaska podstawa, bez podpor, nawis <= 55 st. od pionu (lowpoly: rzeczywiste fasety <= 55, profil <= 52).
 2. Czop 5x5x8 (+2 mm w spoine), gniazdo 5,4x5,4x9 (luz 0,2/strone), pochylenie ucha/poroza 14 st., ucha w x = +-6, y = 0,25.
    Zebra: rzeczywiste narozniki zaokraglone (czop r 1,0 / gniazdo r 1,25); lowpoly: fazy (czop 1,0 / gniazdo 0,7). Wszystkie 4 pary pasuja (luz >= 0,15).
 3. PUNKT MOCOWANIA P0 i uklad lokalny porta wyznacza IDEALNY (gladki) profil modelu - ten sam dla zebra i lowpoly.
 4. Czesc wymienna przycieta do KOPERTY modelu: idealny profil + ENV_PAD (promieniowo) + GAP 0,3 -> ta sama czesc pasuje do KAZDEGO stylu.
 5. Zebra: amplituda +-0,8, rozstaw ~3,4 mm w kazdej czesci (N = round(2 pi Rmax / 3,4)).  Lowpoly: M = 2*floor(R/4+0,5) (min 8) bokow w kazdej
    sekcji (fasety ~12 mm), pierscienie z auto_rings (tol 0,6 mm), pierscien przy porcie z wierzcholkiem na osi x/y portu.
 6. Nazwy: male litery/cyfry/_, lowpoly z prefiksem lp_; czesci wymienne zapisane w ukladzie druku (plecy c = 0 na stole).
 7. Wnetrza i sufity (wneki czapek itp.): nachylenie |dr/dz| <= LP_SLOPE = 1,30 (52 st. od pionu) w OBU stylach - zapas 3 st. na szum voxeli.
    Poziome mostki / polki dozwolone przy rozpietosci <= 12 mm (overhang_check).
 8. Nowy model = new_model_template.py (profil R(z) + porty -> ribbed_sections_F / lp_section_rings -> emit -> verify_set); 5 modeli kluczowych: models.py.
"""
import sys, math, json, os, time, pickle
import numpy as np
import trimesh
from scipy import ndimage as ndi
import shapely
import shapely.geometry as sg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lp import *                                   # lib.* (stale, ribbed_F, Frame, ...), MF/TM/union/diff/inter/offset, revolve_polys, auto_rings...
from parts import mount_frame, local_sdf, part_fn, part_mesh, surf_tree, GAP, PEG_EXT

VERSION = "1.0"

# =====================================================================================================
# 1. STALE (zebra i lowpoly)
# =====================================================================================================
EAR_Y = 0.25                 # y osi czopu ucha / poroza (srodek grubosci ucha lezy w y = 0)
SOCK_OVER = 1.5              # gniazdo siega 1,5 mm nad P0 (przebicie powierzchni), glebokosc 9 pod P0
LP_PEG_CH, LP_SOCK_CH = 1.0, 0.7     # fazy lowpoly: czop 1,0 / gniazdo 0,7 (zostawia luz >= 0,2 wobec zaokraglen zebrowanych)
ENV_PAD = 0.9                # koperta: idealny profil + 0,9 mm promieniowo (pokrywa grzbiety zeber 0,8 i wierzcholki faset)
PAD_MIN = 0.25               # koperta: minimalne przesuniecie normalne (blad pozycji plaskich powierzchni zebrowanych ~ voxel/2)
ENV_TOL = 0.10               # tolerancja kontroli 'korpus miesci sie w kopercie' (rastrowanie SDF 0,05; fasety/wierzcholki)
OVERHANG_DEG = 55.0          # maks. nawis od pionu (kontrola zebr. i lowpoly na rzeczywistej siatce)
LP_TOL = 0.6                 # lowpoly: maks. odchylka pierscieni od profilu idealnego [mm]
LP_DZ_MAX, LP_DZ_MIN = 12.0, 1.0
LP_SLOPE = 1.30              # lowpoly: maks. |dr/dz| profilu skierowanego w dol (52 st.)
FACET_DIV = 4.0              # M = 2*floor(R/4 + 0,5), min 8
FACET_MIN = 8
PORT_TOL = 0.9               # maks. odleglosc powierzchni od P0 [mm] (obie style; wynika z amplitudy zeber 0,8 / wierzcholkow faset)
MIN_CLEAR = 0.15             # minimalny luz czop-gniazdo / czesc-korpus [mm]
TOTAL_H = 150.0              # wysokosc calej figurki z uszami/porozem (krolik, renifer, bałwan z kapeluszem)
NAME_RE = r"^(lp_)?[a-z0-9]+(_([a-z0-9]+|[SML]))*\.stl$"

# =====================================================================================================
# 2. CZOP / GNIAZDO (lowpoly); wersje zebrowane: lib.peg_F / lib.socket_F / parts.peg_ext_F
# =====================================================================================================


def _oct(h, c, b, cz=2.5):
    """osmiokat (przekroj a-c) o polbokach h, sfazowanych narozach c (os c = cz), na wysokosci b"""
    q = [(-(h - c), -h), (h - c, -h), (h, -(h - c)), (h, h - c), (h - c, h), (-(h - c), h), (-h, h - c), (-h, -(h - c))]
    return [(a, b, cz + cc) for a, cc in q]


def lp_socket():
    """gniazdo lowpoly (ukl. portu): przekroj 5,4 x 5,4 ze SFAZOWANYMI KRAWEDZIAMI wzdluz b (faza LP_SOCK_CH), b od -9 do +1,5, os c = 2,5;
    dno sfazowane 1,0 (jak zaokraglenia zebrowane: wszystkie krawedzie, nie tylko narozniki)"""
    h = SOCK_W / 2
    pts = _oct(h - 1.0, 0.0, -SOCK_D) + _oct(h, LP_SOCK_CH, -SOCK_D + 1.0) + _oct(h, LP_SOCK_CH, SOCK_OVER)
    return hull(pts)


def lp_peg(ext=PEG_EXT):
    """czop lowpoly: przekroj 5 x 5 ze sfazowanymi krawedziami wzdluz b (LP_PEG_CH), b od -8 do +ext (ext wchodzi w czesc), koniec sfazowany 1,0"""
    h = PEG_W / 2
    pts = _oct(h - 1.0, 0.0, -PEG_L) + _oct(h, LP_PEG_CH, -PEG_L + 1.0) + _oct(h, LP_PEG_CH, ext)
    return hull(pts)


def _section_polys():
    """przekroje (a, c) czopow i gniazd obu stylow jako wielokaty shapely (do kontroli luzu)"""
    sq = lambda w, cx, cz: sg.box(cx - w / 2, cz - w / 2, cx + w / 2, cz + w / 2)

    def ch(w, cz, c):
        h = w / 2
        return sg.Polygon([(-h + c, cz - h), (h - c, cz - h), (h, cz - h + c), (h, cz + h - c), (h - c, cz + h), (-h + c, cz + h),
                           (-h, cz + h - c), (-h, cz - h + c)])
    rb_peg = sq(PEG_W - 2 * PEG_R, 0, 2.5).buffer(PEG_R, 32)
    rb_sock = sq(SOCK_W - 2 * SOCK_R, 0, 2.5).buffer(SOCK_R, 32)
    return dict(rb_peg=rb_peg, rb_sock=rb_sock, lp_peg=ch(PEG_W, 2.5, LP_PEG_CH), lp_sock=ch(SOCK_W, 2.5, LP_SOCK_CH))


def peg_socket_matrix():
    """luz czop-gniazdo dla 4 par (rb/lp x rb/lp) [mm]; czop musi lezec wewnatrz gniazda"""
    P = _section_polys()
    out = {}
    for pn in ("rb_peg", "lp_peg"):
        for sn in ("rb_sock", "lp_sock"):
            peg, sock = P[pn], P[sn]
            out[f"{pn}->{sn}"] = round(sock.exterior.distance(peg), 3) if sock.contains(peg) else -1.0
    return out


# =====================================================================================================
# 3. PORTY I MODELE
# =====================================================================================================
class Port:
    """punkt mocowania: P0 na IDEALNYM profilu, ramka (a,b,c): b = os czopu (na zewnatrz), c = plaska strona (druk na plecach c = 0)"""

    def __init__(self, name, P0, frame, kind="socket"):
        self.name, self.P0, self.frame, self.kind = name, np.asarray(P0, float), frame, kind

    @property
    def axis(self):
        return self.frame.B


def ear_port(side, P0):
    """port ucha / poroza: pochylenie 14 st. na zewnatrz (side = +1 prawe, -1 lewe)"""
    return Port("ear_" + ("R" if side > 0 else "L"), P0, mount_frame(side, np.asarray(P0, float)), "ear")


def port_on_profile(R, z_lo, z_hi, side, x=EAR_X, y=EAR_Y):
    """P0 ucha na idealnym profilu R(z) (malejacym w gore): punkt (side*x, y), gdzie R(z) = hypot(x, y)"""
    rho0 = math.hypot(x, y)
    lo, hi = z_lo, z_hi
    for _ in range(80):
        mid = (lo + hi) / 2
        if float(R(np.float64(mid))) > rho0:
            lo = mid
        else:
            hi = mid
    return np.array([side * x, y, (lo + hi) / 2])


def ear_ports(R, z_lo, z_hi):
    return {p.name: p for p in (ear_port(s, port_on_profile(R, z_lo, z_hi, s)) for s in (+1, -1))}


def outline_R(R, z0, z1, step=0.2, steps=()):
    """obrys (rho, z) od osi (dol) do osi (gora) dla profilu R(z); steps = z, w ktorych profil ma skok (np. gorna plaszczyzna ronda)"""
    f = lambda z: max(float(R(np.float64(z))), 0.0)
    sk = set(round(float(s), 6) for s in steps)
    allz = [(round(float(z), 6), "n") for z in np.arange(z0, z1, step) if round(float(z), 6) not in sk] + [(round(float(z1), 6), "n")]
    allz += [(s, "s") for s in sorted(sk)]
    pts = []
    for z, k in sorted(allz):
        if k == "n":
            pts.append((f(z), z))
        else:
            pts += [(f(z - 1e-4), z), (f(z + 1e-4), z)]
    return np.array([(0.0, z0)] + pts + [(0.0, z1)])


def _profile_path(poly):
    """sciezka konturu polowy rho >= 0 od punktu na osi (dol) do punktu na osi (gora)"""
    half = poly.intersection(sg.box(0, -1e4, 1e4, 1e4))
    if half.geom_type != "Polygon":
        half = max(half.geoms, key=lambda g: g.area)
    c = np.array(half.exterior.coords)[:-1]
    ax = np.where(c[:, 0] < 1e-7)[0]
    ib, it = ax[np.argmin(c[ax, 1])], ax[np.argmax(c[ax, 1])]
    n = len(c)

    def walk(step):
        i, out = ib, [c[ib]]
        while i != it:
            i = (i + step) % n
            out.append(c[i])
        return np.array(out)
    p1, p2 = walk(1), walk(-1)
    p = p1 if (p1[:, 0] > 1e-7).sum() > (p2[:, 0] > 1e-7).sum() else p2
    return np.array(sg.LineString(p).simplify(0.01).coords)


def revolve_profile(path, M=64):
    """bryla obrotowa z lamanej (rho, z) od osi do osi (z dowolnym przebiegiem z; rho = 0 -> wierzcholek); stala liczba bokow M"""
    V, rings = [], []
    ang = 2 * math.pi * np.arange(M) / M
    for r, z in path:
        if r < 1e-7:
            V.append((0.0, 0.0, float(z))); rings.append([len(V) - 1])
        else:
            idx = []
            for a in ang:
                V.append((r * math.cos(a), r * math.sin(a), float(z))); idx.append(len(V) - 1)
            rings.append(idx)
    F = []
    for A, B in zip(rings[:-1], rings[1:]):
        if len(A) == 1:
            F += [(A[0], B[(k + 1) % M], B[k]) for k in range(M)]
        elif len(B) == 1:
            F += [(A[k], A[(k + 1) % M], B[0]) for k in range(M)]
        else:
            for k in range(M):
                k1 = (k + 1) % M
                F += [(A[k], A[k1], B[k1]), (A[k], B[k1], B[k])]
    m = trimesh.Trimesh(np.array(V), np.array(F), process=False)
    m.merge_vertices()
    trimesh.repair.fix_normals(m)
    if m.volume < 0:
        m.invert()
    return m


class Envelope:
    """KOPERTA modelu (niezalezna od stylu): idealny obrys + ENV_PAD promieniowo. sdf() - odleglosc ze znakiem (dodatnia wewnatrz),
    mesh(gap) - bryla obrotowa obrysu powiekszonego o 'gap' (do przycinania czesci lowpoly)."""
    RES = 0.05

    def __init__(self, outline, pad=ENV_PAD):
        o = np.asarray(outline, float)
        keep = np.r_[True, np.hypot(*np.diff(o, axis=0).T) > 1e-9]       # usun powtorzone punkty (np. dwa razy wierzcholek na osi)
        self.outline = o[keep]
        self.pad = pad
        self.poly = sg.Polygon(self._padded(self.outline, pad)).buffer(0)
        self._sdf = None
        self._mesh = {}

    @staticmethod
    def _padded(o, pad):
        """kazdy wierzcholek obrysu przesuniety wzdluz normalnej na zewnatrz o max(pad * max(n_rho, 0), PAD_MIN): pokrywa promieniowe
        wystawanie zeber / wierzcholkow faset (pad) i blad pozycji plaskich powierzchni (PAD_MIN); zaglebienia i gory tylko PAD_MIN"""
        n = len(o)
        seg = np.diff(o, axis=0)
        ln = np.hypot(seg[:, 0], seg[:, 1])
        ns = np.zeros((n - 1, 2))
        last = np.array([1.0, 0.0])
        for i in range(n - 1):
            if ln[i] > 1e-9:
                last = np.array([seg[i, 1], -seg[i, 0]]) / ln[i]
            ns[i] = last
        pts = []
        for i in range(n):
            r, z = o[i]
            if r <= 1e-6:
                pts.append((r, z + (PAD_MIN if i == n - 1 else 0.0))); continue
            v = (ns[i - 1] if i > 0 else ns[0]) + (ns[i] if i < n - 1 else ns[-1])
            v = v / max(np.hypot(*v), 1e-9)
            mag = max(pad * max(v[0], 0.0), PAD_MIN)
            pts.append((r + mag * v[0], z + mag * v[1]))
        return pts

    def _raster(self):
        res = self.RES
        rmax = float(self.outline[:, 0].max() + self.pad + 5.0)
        z0, z1 = float(self.outline[:, 1].min() - 5.0), float(self.outline[:, 1].max() + 5.0)
        r0 = -6.0
        rr = r0 + res * np.arange(int((rmax - r0) / res) + 1)
        zz = z0 + res * np.arange(int((z1 - z0) / res) + 1)
        mir = shapely.union(self.poly, shapely.transform(self.poly, lambda c: c * np.array([-1.0, 1.0])))
        RR, ZZ = np.meshgrid(rr, zz, indexing="ij")
        ins = shapely.contains_xy(mir, RR, ZZ)
        d_in = ndi.distance_transform_edt(ins) - 0.5
        d_out = ndi.distance_transform_edt(~ins) - 0.5
        sdf = np.where(ins, d_in, -d_out) * res
        self._sdf = (sdf.astype(np.float32), r0, z0)

    def sdf_rz(self, rho, z):
        if self._sdf is None:
            self._raster()
        sdf, r0, z0 = self._sdf
        shp = np.broadcast(rho, z).shape
        rho, z = np.broadcast_to(rho, shp).ravel(), np.broadcast_to(z, shp).ravel()
        v = ndi.map_coordinates(sdf, np.vstack([(rho - r0) / self.RES, (z - z0) / self.RES]), order=1, mode="nearest")
        return v.reshape(shp)

    def sdf(self, X, Y, Z):
        return self.sdf_rz(np.sqrt(np.asarray(X) ** 2 + np.asarray(Y) ** 2), Z)

    def mesh(self, gap=GAP, M=64):
        key = (round(gap, 4), M)
        if key not in self._mesh:
            poly = self.poly.buffer(gap, 16)
            self._mesh[key] = revolve_profile(_profile_path(poly), M)
        return self._mesh[key]


class Model:
    """model = idealny obrys + porty (+ opcjonalnie pole zebrowane dla stylu rb)"""

    def __init__(self, name, outline, ports=None, ribbed_F=None, pad=ENV_PAD, note=""):
        self.name, self.outline, self.ports, self.ribbed_F, self.pad, self.note = name, np.asarray(outline, float), ports or {}, ribbed_F, pad, note
        self.H = float(self.outline[:, 1].max())
        self._env = None

    @property
    def env(self):
        if self._env is None:
            self._env = Envelope(self.outline, self.pad)
        return self._env

    def R(self, z):
        """promien idealnego obrysu na wysokosci z (po bocznej scianie, gorna galaz)"""
        o = self.outline
        return float(np.interp(z, o[:, 1], o[:, 0]))


def rb_trims(pairs):
    """trims dla czesci zebrowanej: pairs = [(model, nazwa_portu), ...] -> [(ramka, sdf_koperty)] do parts.part_fn / part_mesh"""
    return [(m.ports[pn].frame, m.env.sdf) for m, pn in pairs]


# =====================================================================================================
# 4. LOWPOLY: bryly obrotowe z sekcji (auto-pierscienie, M wg promienia, fazy przy portach)
# =====================================================================================================
def clamp_overhang(R, z0, slope=LP_SLOPE):
    """profil R(z) z podstawa 'stozkowa': ponizej punktu, w ktorym |dr/dz| <= slope, powierzchnia idzie stycznym stozkiem (nawis <= 52 st.)"""
    zz = np.arange(z0, z0 + 40, 0.05)
    rr = np.array([float(R(np.float64(z))) for z in zz])
    d = np.gradient(rr, zz)
    ok = np.where(d <= slope)[0]
    if len(ok) == 0 or ok[0] == 0:
        return R, z0
    zs = float(zz[ok[0]])
    rs = float(rr[ok[0]])
    cone = lambda z: rs - slope * (zs - z)
    return (lambda z: float(max(float(R(np.float64(z))), cone(z))) if z < zs else float(R(np.float64(z)))), zs


def section_M(R, z0, z1):
    zz = np.linspace(z0, z1, 200)
    return facet_M(max(float(R(np.float64(z))) for z in zz), FACET_DIV, FACET_MIN)


def _thin(zs, keep, dmin):
    """pilnuje minimalnego odstepu dmin miedzy pierscieniami (unika waskich pasow z pila fasetowa): wolny pierscien (poza keep)
    zbyt blisko sasiada jest odsuwany na odleglosc dmin (profil prawie sie nie zmienia), a dopiero gdy nie ma miejsca - usuwany"""
    zs = [float(z) for z in zs]
    K = lambda z: round(z, 4) in keep
    i = 0
    while i < len(zs) - 1:
        if zs[i + 1] - zs[i] >= dmin - 1e-9:
            i += 1
            continue
        done = False
        for j in (i, i + 1):
            if K(zs[j]) or j == 0 or j == len(zs) - 1:
                continue
            if j == i:
                new, third_ok = zs[i + 1] - dmin, (zs[i + 1] - dmin) - zs[i - 1] >= dmin - 1e-9
            else:
                new, third_ok = zs[i] + dmin, zs[i + 2] - (zs[i] + dmin) >= dmin - 1e-9
            if third_ok:
                zs[j] = round(new, 4)
            else:
                zs.pop(j)
            done = True
            break
        if not done:
            i += 1
    return zs


def lp_section_rings(R, z0, z1, M=None, forced=(), port_zs=(), port_ang=0.0, tol=LP_TOL, dz_max=LP_DZ_MAX, apex_top=False, same_dz=2.0):
    """pierscienie jednej sekcji lowpoly. z: auto_rings (tol, dz_max) + forced (zalamania profilu) + port_zs (pierscien na wysokosci P0 portu);
    M bokow (domyslnie facet_M wg najwiekszego promienia sekcji); pierscienie na przemian przesuniete o pol kroku (pas trojkatow), ale
    gdy dz < same_dz - ta sama faza (sciany pionowe/gesto: brak 'pily'); faza dobrana tak, by SRODEK FASETY pierscienia portu lezal
    na kacie port_ang [st.] (plaska faseta pod plytka czesci)."""
    zt = z1 - 0.001 if apex_top else z1
    keep = set(round(z, 4) for z in list(forced) + list(port_zs) + [z0, z1])
    zs = auto_rings(R, z0, zt, tol=tol, dz_max=dz_max, dz_min=LP_DZ_MIN, slope_max=LP_SLOPE, forced=list(forced) + list(port_zs))
    zs = sorted(set([round(z, 4) for z in zs]))
    if apex_top:
        zs[-1] = z1
        keep.add(round(z1, 4))
    zs = _thin(zs, keep, 1.5)
    M = M or section_M(R, z0, z1)
    h = [0]
    for j in range(1, len(zs)):
        h.append(h[-1] if zs[j] - zs[j - 1] < same_dz else 1 - h[-1])
    if port_zs:
        jp = int(np.argmin(np.abs(np.array(zs) - port_zs[0])))
        step = 360.0 / M
        want = int(round(2 * (port_ang / step - 0.5))) % 2        # faseta wyrownana do port_ang: wierzcholki w (half/2 + k) * step
        if h[jp] != want:
            h = [1 - x for x in h]
    rings = []
    for j, z in enumerate(zs):
        r = max(float(R(np.float64(z))), 0.0)
        rings.append(ring_regular(z, r, M, half=h[j]))
    return rings


def lp_revolve(sections):
    """sekcje: lista list pierscieni (kolejne po z; M moze sie zmieniac miedzy sekcjami) -> bryla"""
    rings = [r for s in sections for r in s]
    return revolve_polys(rings)


# =====================================================================================================
# 5. KONTROLE
# =====================================================================================================
def largest_component(m):
    comps = m.split(only_watertight=False)
    if len(comps) > 1:
        comps.sort(key=lambda c: -abs(c.volume))
    return comps[0]


def lp_trim(part_local, targets, peg=True, ext=PEG_EXT):
    """czesc lowpoly (ukl. lokalny portu) przycieta do kopert: targets = [(model, nazwa_portu), ...]; dodaje czop 5x5x8"""
    p = part_local
    for m, pn in targets:
        p = diff(p, to_local(m.env.mesh(GAP), m.ports[pn].frame))
    n = len(p.split(only_watertight=False))
    if n > 1:
        print(f"   (skladowe po przycieciu: {n}; zostaje najwieksza)")
        p = largest_component(p)
    return union(p, lp_peg(ext)) if peg else p


def ray_height(mesh, o, d):
    """odleglosc t do pierwszego trafienia promienia o + t d w siatke (Moller-Trumbore), albo None"""
    d = np.asarray(d, float) / np.linalg.norm(d)
    tri = mesh.triangles
    v0 = tri[:, 0]
    e1, e2 = tri[:, 1] - v0, tri[:, 2] - v0
    p = np.cross(d, e2)
    det = (e1 * p).sum(1)
    ok = np.abs(det) > 1e-12
    inv = 1.0 / np.where(ok, det, 1.0)
    s = np.asarray(o, float) - v0
    u = (s * p).sum(1) * inv
    q = np.cross(s, e1)
    v = (q @ d) * inv
    t = (e2 * q).sum(1) * inv
    hit = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 0)
    return float(t[hit].min()) if hit.any() else None


def port_deviation(solid, port, n=200000):
    """odleglosc P0 od powierzchni bryly (BEZ wyciecia gniazda) [mm] - lowpoly: <= (k-1) R ~ 0,9; zebra: amplituda 0,8"""
    tree = surf_tree(solid, n)
    return float(tree.query(port.P0)[0])


def overhang_check(m, ports=(), max_bridge=12.0, noise_frac=0.0):
    """nawisy > 55 st. od pionu (poza stolem). Wyjatki: wnetrza gniazd portow (mostek 5,4 mm) i POZIOME mostki/polki o rozpietosci
    (srednica najwiekszego wpisanego kola) <= max_bridge [mm] (np. plaski sufit czapki r = 5, polka gardzieli 1,5 mm).
    noise_frac: dopuszczalny ulamek pola (szum voxelowy siatek zebrowanych ~1%; lowpoly 0).
    Zwraca dict(steep_mm2 = pole sciany pochylonej > 55 st. (nie poziomej), bridges = [(z, rozpietosc, pole)], ok)"""
    n = m.face_normals
    zc = m.triangles_center[:, 2]
    steep = (n[:, 2] < -math.sin(math.radians(OVERHANG_DEG))) & (zc > 0.3)
    if len(ports):
        keep = np.zeros(len(m.faces), bool)
        for p in ports:
            a, b, c = p.frame.to_local(*m.triangles_center.T)
            keep |= ((np.abs(a) <= SOCK_W / 2 + 0.1) & (b >= -SOCK_D - 0.1) & (b <= SOCK_OVER + 0.1)
                     & (c >= 2.5 - SOCK_W / 2 - 0.1) & (c <= 2.5 + SOCK_W / 2 + 0.1))
        steep &= ~keep
    horiz = steep & (n[:, 2] < -0.97)                     # poziome (do 14 st. od poziomu): mostki / polki - ocena przez rozpietosc
    bad = float(m.area_faces[steep & ~horiz].sum())
    spans = []
    if horiz.any():
        idx = np.where(horiz)[0]
        zs = np.round(zc[idx], 0)
        for zl in np.unique(zs):
            tris = [sg.Polygon(m.triangles[i][:, :2]).buffer(1e-6) for i in idx[zs == zl]]
            u = shapely.union_all(tris)
            for g in (list(u.geoms) if hasattr(u, "geoms") else [u]):
                if g.area > 1e-6:
                    spans.append((float(zl), round(2 * shapely.length(shapely.maximum_inscribed_circle(g, 0.05)), 2), round(g.area, 1)))
    ok = bad <= max(1.0, noise_frac * float(m.area)) and all(sp <= max_bridge for _, sp, _ in spans)
    return dict(steep_mm2=round(bad, 2), bridges=spans, ok=bool(ok))


def mesh_report(m, upright=True, ports=(), noise_frac=0.0):
    """szczelnosc, skladowe, orientacja, nawis"""
    comps = len(m.split(only_watertight=False))
    row = dict(watertight=bool(m.is_watertight), winding=bool(m.is_winding_consistent), components=comps, volume=float(m.volume),
               ext=[round(float(v), 2) for v in m.extents], tris=int(len(m.faces)), zmin=round(float(m.bounds[0][2]), 3))
    if upright:
        row["overhang"] = overhang_check(m, ports, noise_frac=noise_frac)
    return row


def interference(part_global, body, min_vol=0.0):
    """objetosc wspolna czesci i korpusu [mm3] (czop w gniezdzie liczy sie, bo korpus ma wyciete gniazdo)"""
    try:
        v = MF(part_global) ^ MF(body)
        return float(v.volume())
    except Exception:
        return float("nan")


def surf_dist(part_global, body, base_only_frame=None, n=300000):
    """najmniejsza odleglosc wierzcholkow czesci od powierzchni korpusu (probki powierzchni); base_only_frame: tylko b > 0,4"""
    tree = surf_tree(body, n)
    V = part_global.vertices
    if base_only_frame is not None:
        a, b, c = base_only_frame.to_local(*V.T)
        V = V[b > 0.4]
    d, _ = tree.query(V)
    return float(d.min())


def envelope_excess(body, env):
    """maks. wystawanie wierzcholkow korpusu poza koperte [mm] (<= 0 = korpus miesci sie w kopercie)"""
    V = body.vertices
    s = env.sdf(V[:, 0], V[:, 1], V[:, 2])
    return float(-s.min())


def set_out(path):
    """przekierowuje zapis (lib.save / emit) do innego katalogu (np. dla szablonu / eksperymentow)"""
    import lib, lp
    os.makedirs(path, exist_ok=True)
    lib.OUT = lp.OUT = path
    globals()["OUT"] = path
    return path


def cut_ports(solid, model):
    """wycina gniazda wszystkich portow modelu (gniazdo 5,4x5,4x9 ze sfazowanymi krawedziami) z bryly lowpoly"""
    out = solid
    for p in model.ports.values():
        out = diff(out, to_global(lp_socket(), p.frame))
    return out


def emit(m, name, upright=True, note="", style=None, ports=()):
    """zapis do out/ z kontrola nazwy i siatki (szczelna, 1 skladowa, objetosc > 0, nawis); style: 'lp' (nazwa z prefiksem lp_) albo 'rb'
    (zebra: bez prefiksu, szum voxeli 1%); zwraca raport"""
    import re
    assert re.match(NAME_RE, name), f"nazwa niezgodna ze standardem: {name}"
    if style == "lp":
        assert name.startswith("lp_"), f"lowpoly musi miec prefiks lp_: {name}"
    if style == "rb":
        assert not name.startswith("lp_"), f"zebra nie moze miec prefiksu lp_: {name}"
    rep = mesh_report(m, upright, ports, noise_frac=0.01 if style == "rb" else 0.0)
    assert rep["watertight"] and rep["components"] == 1 and rep["volume"] > 0, f"{name}: siatka niezgodna ze standardem {rep}"
    if upright and not rep["overhang"]["ok"]:
        print(f"  !! {name}: nawis {rep['overhang']}")
    save_lp(m, name, upright=upright, note=note)
    r = trimesh.load(os.path.join(OUT, name), process=True)          # kontrola po zapisie (to, co zobaczy slicer)
    assert r.is_watertight and len(r.split(only_watertight=False)) == 1 and abs(abs(r.volume) / abs(m.volume) - 1) < 1e-3, f"{name}: plik po zapisie niezgodny"
    return rep

# =====================================================================================================
# 6. ZEBRA: pole zebrowane wielosekcyjne (stale N w kazdej bryle) i widmo zeber do kontroli
# =====================================================================================================
def _sstep(z, z0, z1):
    t = np.clip((np.asarray(z, np.float32) - z0) / (z1 - z0), 0, 1)
    return t * t * (3 - 2 * t)


def rib_sections(R, z0, z1, cuts=()):
    """sekcje zeber: [(za, zb, N)]; N = round(2 pi Rmax / 3,4) wg najwiekszego promienia sekcji (rozstaw ~3,4 mm w kazdej bryle).
    cuts = wysokosci 'talii' miedzy bryłami (kula/kula, korpus/glowa); z0..z1 = zakres modelu"""
    edges = [z0] + sorted(cuts) + [z1]
    out = []
    for za, zb in zip(edges[:-1], edges[1:]):
        zz = np.linspace(za, zb, 400)
        rmax = max(float(R(np.float64(z))) for z in zz)
        out.append((za, zb, n_ribs(rmax)))
    return out


def ribbed_sections_F(R, z0, z1, cuts=(), gap=3.5, band=2.0, shape=0.8, N=None):
    """STANDARD zebra dla modelu zlozonego z brył (kule, glowa + korpus): zwraca F(X, Y, Z) (dodatnie wewnatrz) dla profilu R(z)
    (R przyjmuje wektory np.float32/64). Zebra +-0,8 mm (zanikaja przy r < 10 mm), N zeber w kazdej sekcji wg rib_sections (albo N = lista),
    w pasie +-gap wokol kazdej 'talii' (cuts) zebra zanikaja gladko na dlugosci band (gladka szyja zamiast poszarpanego przejscia).
    Podstawa i gora plaskie (min(F, Z - z0, z1 - Z))."""
    secs = rib_sections(lambda z: float(np.max(R(np.asarray([z], np.float32)))), z0, z1, cuts)
    Ns = list(N) if N is not None else [s[2] for s in secs]
    cs = sorted(cuts)

    def F(X, Y, Z):
        rho = np.sqrt(X ** 2 + Y ** 2)
        th = np.arctan2(Y, X)
        Rz = R(np.asarray(Z, np.float32))
        mod = 0.0
        for i, n in enumerate(Ns):
            w = 1.0
            if i > 0:
                w = w * _sstep(Z, cs[i - 1] + gap, cs[i - 1] + gap + band)
            if i < len(cs):
                w = w * (1 - _sstep(Z, cs[i] - gap - band, cs[i] - gap))
            c = np.cos(n * th)
            mod = mod + w * np.sign(c) * np.abs(c) ** shape
        out = (Rz + rib_amp(Rz) * mod - 1e-3) - rho
        return np.minimum(np.minimum(out, Z - z0), z1 - Z).astype(np.float32)
    F.sections = secs
    return F


def rib_spectrum(mesh, z):
    """(N, rozstaw [mm], amplituda p-p [mm]) zeber w przekroju poziomym z siatki zebrowanej (FFT promienia po kacie)"""
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    lines = sorted(sec.discrete, key=lambda l: -np.mean(np.hypot(np.array(l)[:, 0], np.array(l)[:, 1])))
    pts = np.array(lines[0])[:, :2]
    th, r = np.arctan2(pts[:, 1], pts[:, 0]), np.hypot(pts[:, 0], pts[:, 1])
    o = np.argsort(th)
    th, r = th[o], r[o]
    grid_ = np.linspace(-np.pi, np.pi, 4096, endpoint=False)
    rg = np.interp(grid_, th, r, period=2 * np.pi)
    sp = np.abs(np.fft.rfft(rg - rg.mean()))
    k = int(np.argmax(sp[5:200]) + 5)
    Fq = np.fft.rfft(rg)
    Fq[: k // 2] = 0
    rr = np.fft.irfft(Fq, 4096)
    return k, 2 * np.pi * rg.mean() / k, float(np.percentile(rr, 99) - np.percentile(rr, 1))


# =====================================================================================================
# 7. KONTROLA NOWEGO MODELU (te same kryteria co verify_all.py, ale dla dowolnego Model + zbudowanych siatek)
# =====================================================================================================
def verify_set(model, bodies, parts, solids=None, rib_z=(), log=print):
    """bodies: {plik.stl: dict(mesh=Trimesh (uklad druku), dz=przesuniecie do ukladu modelu [mm], ports=[nazwy portow w korpusie], upright=True)}
    parts : {plik.stl: dict(mesh=Trimesh (uklad druku), port=nazwa portu, unrot=None | funkcja(mesh) -> mesh w ukladzie lokalnym portu)}
    solids: {'rb': siatka bez gniazd (opcjonalnie), 'lp': siatka bez gniazd} - do kontroli |P0 - powierzchnia| dla lowpoly
    rib_z : [(plik_korpusu, z, N_oczekiwane)] - kontrola FFT zeber
    Sprawdza: nazwy, siatki (szczelnosc, 1 skladowa, nawis), koperte, P0, pasowanie czesc x korpus (kazdy z kazdym, takze krzyzowo zebra/lowpoly),
    zeby. Zwraca (n_pass, [bledy])."""
    import re
    res = []

    def chk(name, ok, info=""):
        res.append((name, bool(ok)))
        log(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({info})" if info != "" else ""))

    mats = peg_socket_matrix()
    for k, v in mats.items():
        chk(f"luz czop->gniazdo {k}", v >= MIN_CLEAR, f"{v} mm")
    for fn in list(bodies) + list(parts):
        ok = bool(re.match(NAME_RE, fn)) and True
        chk(f"nazwa {fn}", ok)
    for fn, b in bodies.items():
        pr = [model.ports[p] for p in b.get("ports", ())]
        r = mesh_report(b["mesh"], b.get("upright", True), pr, noise_frac=0.0 if fn.startswith("lp_") else 0.01)
        ok = r["watertight"] and r["winding"] and r["components"] == 1 and r["volume"] > 0 and abs(r["zmin"]) < 0.05
        if "overhang" in r:
            ok = ok and r["overhang"]["ok"]
        chk(f"siatka {fn}", ok, f"{r['ext']} tri {r['tris']}" + (f" nawis {r['overhang']['steep_mm2']} mm2" if "overhang" in r else ""))
        V = b["mesh"].vertices
        ex = float(-model.env.sdf(V[:, 0], V[:, 1], V[:, 2] + b.get("dz", 0.0)).min())
        chk(f"koperta {fn}", ex <= ENV_TOL, f"wystawanie {ex:+.3f} mm (tol {ENV_TOL})")
    for fn, p in parts.items():
        r = mesh_report(p["mesh"], False)
        chk(f"siatka {fn}", r["watertight"] and r["winding"] and r["components"] == 1 and r["volume"] > 0, f"{r['ext']} tri {r['tris']}")
    if solids:
        for st, solid in solids.items():
            for pn, port in model.ports.items():
                d = port_deviation(solid, port)
                chk(f"{st} {model.name}/{pn}: |P0 - powierzchnia| <= {PORT_TOL}", d <= PORT_TOL, f"{d:.2f} mm")
    for pf, p in parts.items():
        port = model.ports[p["port"]]
        m = p["mesh"] if p.get("unrot") is None else p["unrot"](p["mesh"])
        g = to_global(m, port.frame)
        for bf, b in bodies.items():
            if p["port"] not in b.get("ports", ()):
                continue
            body = b["mesh"].copy()
            body.apply_translation([0, 0, b.get("dz", 0.0)])
            iv = interference(g, body)
            a_, b_, c_ = port.frame.to_local(*g.vertices.T)
            dd, _ = surf_tree(body, 400000).query(g.vertices)
            in_peg = (np.abs(a_) <= 2.51) & (c_ >= -0.01) & (c_ <= 5.01) & (b_ <= 2.01)
            d_base = float(dd[(b_ > 0.4) & ~in_peg].min())
            d_peg = float(dd[b_ < -0.5].min())
            cross = pf.startswith("lp_") != bf.startswith("lp_")
            chk(f"pasowanie {pf} -> {bf}" + ("  [KRZYZOWE]" if cross else ""), iv <= 1.0 and d_base >= MIN_CLEAR and d_peg >= MIN_CLEAR,
                f"interferencja {iv:.2f} mm3, podstawa {d_base:.2f}, czop {d_peg:.2f} mm")
    for bf, z, n_exp in rib_z:
        k, pitch, pp = rib_spectrum(bodies[bf]["mesh"], z)
        chk(f"zebra {bf} z={z}: N={k} (oczek. {n_exp}), rozstaw {pitch:.2f}", k == n_exp and 3.0 <= pitch <= 3.8 and 1.2 <= pp <= 2.1, f"p-p {pp:.2f}")
    for bf, b in bodies.items():
        if bf.startswith("lp_") and bf[3:] in bodies:
            e1, e2 = bodies[bf[3:]]["mesh"].extents, b["mesh"].extents
            chk(f"wymiary zebra vs lowpoly {bf[3:]}", abs(e1[2] - e2[2]) <= 1.0 and max(abs(e1[0] - e2[0]), abs(e1[1] - e2[1])) <= 3.0,
                f"dz {abs(e1[2] - e2[2]):.2f}, dxy {max(abs(e1[0] - e2[0]), abs(e1[1] - e2[1])):.2f} mm")
    bad = [n for n, ok in res if not ok]
    log(f"WYNIK verify_set: {len(res) - len(bad)} PASS, {len(bad)} FAIL" + (f": {bad}" if bad else ""))
    return len(res) - len(bad), bad
