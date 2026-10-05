"""Grupa A - figurki cale (przytopione elementy) na korpusie bazowym + pisklo na jajku.
 mis_calosc, kot_calosc, lis_calosc (ogon), sowa_calosc (oczy, dziob, pioropusze), aniol_calosc (aureola, skrzydla),
 jajko_czapka_pisklo (oczy, dziob, pioropusz)."""
import sys, math, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from parts import *
from shapes import *
from build_figurki import FRb, FRe, add_local
from ears_A import SPECS, a_range
import build_egg as EG

VOX = 0.4
HC = np.array([0.0, 0.0, HEAD_ZC])
RH = HEAD_R
T0 = time.time()


def sstep(z, z0, z1):
    t = np.clip((z - z0) / (z1 - z0), 0, 1)
    return t * t * (3 - 2 * t)


def smooth_poly(pts, n=14):
    """zamknieta krzywa Catmull-Rom przez punkty kontrolne -> wielokat"""
    P = np.asarray(pts, float)
    N = len(P)
    out = []
    for i in range(N):
        p0, p1, p2, p3 = P[(i - 1) % N], P[i], P[(i + 1) % N], P[(i + 2) % N]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return [tuple(p) for p in out]


def fuse_ears(F, axes, name):
    fac, L = SPECS[name]
    for s in (+1, -1):
        fp = fac(s < 0)
        F = add_local(F, axes, FRb[s], part_fn(fp, None, peg=False, plate_b0=-4.5), a_rng=a_range(s), b_rng=(-9, L + 3))
    return F


# ---------- lis: puszysty zebrowany ogon ----------
def tail_F(X, Y, Z, P=(0.0, 12.0, 14.0), alpha=math.radians(46), Lt=44.0, Rm=7.8, N=16):
    d = np.array([0.0, math.sin(alpha), math.cos(alpha)])
    e1 = np.array([1.0, 0.0, 0.0])
    e2 = np.cross(d, e1)
    rx, ry, rz = X - P[0], Y - P[1], Z - P[2]
    s = rx * d[0] + ry * d[1] + rz * d[2]
    u1 = rx * e1[0] + ry * e1[1] + rz * e1[2]
    u2 = rx * e2[0] + ry * e2[1] + rz * e2[2]
    rho = np.sqrt(u1 ** 2 + u2 ** 2)
    th = np.arctan2(u2, u1)
    u = np.clip(s / Lt, 0, 1)
    R = Rm * np.clip(4 * u * (1 - u), 0, None) ** 0.72
    amp = RIB_AMP * np.clip((R - 1.2) / 2.8, 0, 1)
    rib = np.cos(N * th)
    rib = np.sign(rib) * np.abs(rib) ** 0.8
    F = (R + amp * rib - 1e-3) - rho
    return np.minimum(F, np.minimum(s + 3.0, Lt - s)).astype(np.float32)


# ---------- sowa: oczy (kopulki na sferze glowy) + dziob ----------
def eye_cap_F(X, Y, Z, sx, dz=2.2, ax=6.3, th_e=0.37, th_p=0.17, top=RH + 1.9, top_p=RH + 3.1):
    e = np.array([sx * ax, -math.sqrt(RH ** 2 - ax ** 2 - dz ** 2), dz])
    e /= np.linalg.norm(e)
    rx, ry, rz = X - HC[0], Y - HC[1], Z - HC[2]
    r = np.sqrt(rx ** 2 + ry ** 2 + rz ** 2) + 1e-6
    ang = np.arccos(np.clip((rx * e[0] + ry * e[1] + rz * e[2]) / r, -1, 1))
    disc = np.minimum((th_e - ang) * RH, top - r)
    pup = np.minimum((th_p - ang) * RH, top_p - r)
    return np.maximum(disc, pup).astype(np.float32)


def beak_F(X, Y, Z, zc, s_surf, length=4.2, hw=3.2, hh=3.0, back=4.0):
    """dziob (stozek eliptyczny) wzdluz -y; s = -y; podstawa na s_surf, wierzcholek s_surf+length"""
    s = -Y
    t = (s_surf + length - s) / length
    q = np.sqrt((X / hw) ** 2 + ((Z - zc) / hh) ** 2)
    return np.minimum((t - q) * min(hw, hh), np.minimum(s_surf + length - s, s - (s_surf - back))).astype(np.float32)


# ---------- aniol: aureola + skrzydla ----------
def halo_F(X, Y, Z, zc=139.0, ro=10.5, ri=6.8, T=3.6, z_stem0=117.0, sw=2.3):
    rho2 = np.sqrt(X ** 2 + (Z - zc) ** 2)
    ring = np.minimum(np.minimum(ro - rho2, rho2 - ri), T / 2 - np.abs(Y))
    stem = np.minimum(np.minimum(sw - np.abs(X), Z - z_stem0), np.minimum((zc - ro + 2.5) - Z, T / 2 - np.abs(Y)))
    return np.maximum(ring, stem).astype(np.float32)


def wing_flat(res=0.1):
    pts = [(12, 6), (20, 6), (26, 10), (33, 17), (38, 27), (41, 38), (41, 48), (37, 57), (31, 62), (26, 56), (22, 46), (18, 36), (12, 28)]
    poly = smooth_poly(pts, 16)
    cv = Canvas(8, 52, -4, 68, res=res)
    cv.poly(poly)
    cv.close_(1.5)
    cv.open_(1.2)
    gr = Canvas(8, 52, -4, 68, res=res)
    for ang, ln in ((50, 26), (68, 31), (84, 34)):                       # rysy piorek rozchodzace sie od nasady
        a0, b0 = 21.0, 24.0
        gr.line((a0, b0), (a0 + ln * math.cos(math.radians(ang)) * 0.62, b0 + ln * math.sin(math.radians(ang))), 1.0)
    return FlatPart(cv, 3.4, w=1.0, k=1.5, groove_mask=gr.mask(), groove_d=0.8)


def wing_frames(phi_deg=35.0, z_r=50.0, T=3.4):
    ph = math.radians(phi_deg)
    out = {}
    for s in (+1, -1):
        A = np.array([s * math.cos(ph), math.sin(ph), 0.0])
        B = np.array([0.0, 0.0, 1.0])
        C = np.array([s * math.sin(ph), -math.cos(ph), 0.0])
        out[s] = Frame(np.array([0.0, 0.0, z_r]) - C * (T / 2), A, B, C)
    return out


# ---------- budowa ----------
def build_body(name):
    xh, ylo, yhi = 21, -21, 21
    if name == "lis":
        yhi = 52
    if name == "aniol":
        xh, yhi = 38, 28
    axes, (X, Y, Z) = make_grid(-xh, xh, ylo, yhi, -1.0, 153.0, VOX)
    F = bunny_F(X, Y, Z)
    if name in ("mis", "kot", "lis", "sowa"):
        F = fuse_ears(F, axes, name)
    if name == "lis":
        F = np.maximum(F, tail_F(X, Y, Z))
    if name == "sowa":
        for sx in (+1, -1):
            F = np.maximum(F, eye_cap_F(X, Y, Z, sx))
        F = np.maximum(F, beak_F(X, Y, Z, zc=HEAD_ZC - 4.2, s_surf=15.9))
    if name == "aniol":
        F = np.maximum(F, halo_F(X, Y, Z))
        fw = wing_flat()
        for s, fr in wing_frames().items():
            fp = FlatPart(fw.cv, 3.4, w=1.0, k=1.5, groove_mask=None, mirror=False)
            F = add_local(F, axes, fr, lambda a, b, c, fw=fw: fw.F(a, b, c), a_rng=(8, 52), b_rng=(-4, 68), c_rng=(-1, 5))
    return axes, F


def run_body(name):
    t = time.time()
    axes, F = build_body(name)
    m = mesh_from_F(F, axes, VOX)
    save(m, f"{name}_calosc.stl", True, "korpus bazowy + elementy przytopione")
    print(f"  {name}: {time.time() - t:.0f} s")
    return m


# ---------- pisklo na jajku ----------
def leaf_flat(L=10.0, hw=3.0, res=0.1):
    cv = Canvas(-6, 6, -4.5, L + 2, res=res)
    bs = np.linspace(-3.0, L, 120)

    def w(b):
        u = max(b, 0) / L
        return 2.6 + (hw - 2.6) * math.sin(math.pi * min(u / 0.45, 1) / 2) if u < 0.45 else hw * max(1 - ((u - 0.45) / 0.55) ** 1.8, 0) ** (1 / 1.8)
    cv.poly([(w(b), b) for b in bs] + [(-w(b), b) for b in bs[::-1]])
    cv.open_(0.8)
    return FlatPart(cv, 3.0, w=0.8, k=1.1)


def chick_cap():
    ztop = 101.0
    axes, (X, Y, Z), Fcup, Fcap, Fcav_cup, Fcav_cap, sock = EG.fields(False, ztop=ztop)
    F = Fcap.copy()
    feat = np.full(F.shape, -9.0, np.float32)
    # oczy: elipsoidy na powierzchni jajka
    ze, ph = 63.0, math.radians(38)
    rs = float(egg_R(ze))
    for sx in (+1, -1):
        phi = math.radians(-90) + sx * ph
        cx, cy = (rs + 0.2) * math.cos(phi), (rs + 0.2) * math.sin(phi)
        u = (X - cx) * math.cos(phi) + (Y - cy) * math.sin(phi)
        v = -(X - cx) * math.sin(phi) + (Y - cy) * math.cos(phi)
        ell = (1 - np.sqrt((u / 2.4) ** 2 + (v / 2.7) ** 2 + ((Z - ze) / 2.7) ** 2)) * 2.4
        feat = np.maximum(feat, ell.astype(np.float32))
    # dziob: stozek eliptyczny wzdluz -y, nieco ponizej oczu
    zb = 56.0
    rb_ = float(egg_R(zb))
    feat = np.maximum(feat, beak_F(X, Y, Z, zc=zb, s_surf=rb_ + 0.6, length=4.8, hw=3.6, hh=3.0, back=5.0))
    F = np.maximum(F, feat)
    # pioropusz: 3 listki na szczycie
    zt = float(egg_R(0) * 0 + 85.5)
    for g_deg, xo in ((-26, -1.4), (0, 0.0), (26, 1.4)):
        g = math.radians(g_deg)
        B = np.array([math.sin(g), 0.0, math.cos(g)])
        C = np.array([0.0, -1.0, 0.0])
        A = np.cross(B, C)
        fr = Frame(np.array([xo, 1.5, zt]), A, B, C)
        fp = leaf_flat(11.0 if g_deg == 0 else 9.0, 3.0)
        F = add_local(F, axes, fr, lambda a, b, c, fp=fp: np.minimum(fp.F(a, b, c), b + 4.0), a_rng=(-6, 6), b_rng=(-5, 13), c_rng=(-1, 4))
    # wnetrze czapki nietkniete (cechy tylko na zewnatrz)
    F = np.minimum(np.minimum(F, -Fcav_cap), Z - Z_CAP0).astype(np.float32)
    m = mesh_from_F(F, axes, EG.VOX)
    m = decimate(m, 220000, label="czapka-pisklo")
    save(m, "jajko_czapka_pisklo.stl", True, "otworem do dolu; pisklo (oczy, dziob, pioropusz) przytopione")
    return m


if __name__ == "__main__":
    which = sys.argv[1:] or ["mis", "kot", "lis", "sowa", "aniol", "pisklo"]
    for nm in which:
        if nm == "pisklo":
            chick_cap()
        else:
            run_body(nm)
    print(f"czas {time.time() - T0:.0f} s")
