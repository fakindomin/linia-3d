"""Grupa A - krasnal i Mikolaj: zebrowane czapki.
 czapka_krasnal.stl, czapka_mikolaj.stl  - wymienne, osadzane na glowie korpusu (korpus_bazowy.stl); calosc 150 mm
 jajko_czapka_krasnal.stl, jajko_czapka_mikolaj.stl - czapki jajka z przytopiona czapka (gnom ~128,5 mm, Mikolaj ~118 mm)"""
import sys, math, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from parts import *
from shapes import *
import build_egg as EG

T0 = time.time()
VOX = 0.35


def sstep(z, z0, z1):
    t = np.clip((z - z0) / (z1 - z0), 0, 1)
    return t * t * (3 - 2 * t)


def rib(N, th):
    c = np.cos(N * th)
    return np.sign(c) * np.abs(c) ** 0.8


def cone_R(z, z0, z1, r0, r1, p):
    t = np.clip((z - z0) / (z1 - z0), 0, 1)
    return np.where((z >= z0) & (z <= z1), r1 + (r0 - r1) * (1 - t) ** p, 0.0)


def cuff_R(z, z0, h, Rc, rf=1.6):
    zz = z - z0
    lo = np.sqrt(np.clip(rf ** 2 - (rf - zz) ** 2, 0, None))
    hi = np.sqrt(np.clip(rf ** 2 - (rf - (h - zz)) ** 2, 0, None))
    edge = np.where(zz < rf, lo, np.where(zz > h - rf, hi, rf))
    return np.where((zz >= 0) & (zz <= h), Rc - rf + edge, 0.0)


def ball_R(z, zc, R):
    return np.sqrt(np.clip(R ** 2 - (z - zc) ** 2, 0, None))


class Hat:
    """profil obrotowy czapki: zb = dol, ztop = czubek; typ 'krasnal' (sam stozek) lub 'mikolaj' (mankiet + stozek + pompon)"""

    def __init__(self, kind, zb, ztop, Rb, N, chamfer=0.0, p=1.35):
        self.kind, self.zb, self.ztop, self.Rb, self.N, self.chamfer, self.p = kind, zb, ztop, Rb, N, chamfer, p
        if kind == "mikolaj":
            self.cuff_h = 8.0
            self.Rc = Rb + 1.0
            self.Rpom = 5.8
            self.zpom = ztop - self.Rpom
            self.zc0 = zb + self.cuff_h - 1.0
            self.zc1 = self.zpom + 1.0
            self.rb = Rb - 1.0
            self.rt = 3.2
            self.rib0 = zb + self.cuff_h + 0.5
            self.rib1 = zb + self.cuff_h + 3.0
            self.rib2 = self.zpom - 4.0
            self.rib3 = self.zpom - 1.5
        else:
            self.rt = 1.6
            self.rib0 = zb + 4.0 + chamfer
            self.rib1 = zb + 7.0 + chamfer

    def R(self, z):
        z = np.asarray(z, np.float32)
        if self.kind == "mikolaj":
            r = np.maximum(cuff_R(z, self.zb, self.cuff_h, self.Rc),
                           np.maximum(cone_R(z, self.zc0, self.zc1, self.rb, self.rt, 1.15), ball_R(z, self.zpom, self.Rpom)))
        else:
            r = cone_R(z, self.zb, self.ztop, self.Rb, self.rt, self.p)
        if self.chamfer > 0:
            ch = np.where((z >= self.zb - self.chamfer) & (z < self.zb), self.Rb - (self.zb - z), 0.0)   # 45 st. od korpusu do podstawy czapki
            r = np.maximum(r, ch)
        return r

    def w_rib(self, z):
        if self.kind == "mikolaj":
            return sstep(z, self.rib0, self.rib1) * (1 - sstep(z, self.rib2, self.rib3))
        return sstep(z, self.rib0, self.rib1)

    def F(self, X, Y, Z):
        rho = np.sqrt(X ** 2 + Y ** 2)
        th = np.arctan2(Y, X)
        R = self.R(Z)
        mod = rib_amp(R) * self.w_rib(Z) * rib(self.N, th)
        F = (R + mod - 1e-3) - rho
        zlo = self.zb - self.chamfer
        return np.minimum(np.minimum(F, Z - zlo), self.ztop - Z).astype(np.float32)


# ---------- czapka wymienna na glowe korpusu ----------
RCV = HEAD_R + RIB_AMP + 0.45          # wnetrze: kula wiekszej o szczyty zeber i luz 0,45 mm
ELEV = math.radians(35.0)


def cavity_F(X, Y, Z):
    rho = np.sqrt(X ** 2 + Y ** 2)
    z_t = HEAD_ZC + RCV * math.cos(ELEV)
    r_t = RCV * math.sin(ELEV)
    r_sph = np.sqrt(np.clip(RCV ** 2 - (Z - HEAD_ZC) ** 2, 0, None))
    r_cone = r_t - (Z - z_t) / math.tan(ELEV)          # sufit: stozek 35 st. nad poziomem (55 st. od pionu)
    rc = np.where(Z < z_t, r_sph, r_cone)
    rc = np.where(Z < z_t + math.tan(ELEV) * (r_t - 3.0), rc, -1.0)     # plaski sufit przy r = 3
    return (rc - rho).astype(np.float32)


def build_body_hat(kind):
    zb, ztop = HEAD_ZC + 1.5, 150.0
    Rb = 19.7 if kind == 'krasnal' else 20.5
    hat = Hat(kind, zb, ztop, Rb, n_ribs(Rb), p=1.1)
    axes, (X, Y, Z) = make_grid(-24, 24, -24, 24, zb - 1.0, ztop + 1.0, VOX)
    F = np.minimum(hat.F(X, Y, Z), -cavity_F(X, Y, Z)).astype(np.float32)
    m = mesh_from_F(F, axes, VOX)
    m = decimate(m, 250000, label=f"czapka-{kind}")
    return m, zb


def fit_body_hat(m, zb, name):
    body = trimesh.load(OUT + "/korpus_bazowy.stl")
    tree = surf_tree(body, 600000)
    d, _ = tree.query(m.vertices)
    V = m.vertices
    inside = int((bunny_F(V[:, 0], V[:, 1], V[:, 2]) > 0.02).sum())
    cav = m.vertices[m.vertices[:, 2] < HEAD_ZC + 20]
    print(f"   {name} na korpusie: min. odl. {d.min():.2f} mm | wierzcholki w korpusie {inside} | wierzch z={m.bounds[1][2]:.1f} | dol z={m.bounds[0][2]:.1f}")


# ---------- czapka jajka (przytopiona) ----------
def egg_hat_cap(kind):
    if kind == "krasnal":
        zh0, ztop, Rb = 66.0, 128.5, 24.2
    else:
        zh0, ztop, Rb = 66.0, 118.0, 24.2
    hat = Hat(kind, zh0, ztop, Rb, n_ribs(Rb - 1.0), chamfer=1.4)
    axes, (X, Y, Z), Fcup, Fcap, Fcav_cup, Fcav_cap, sock = EG.fields(False, ztop=ztop + 2.0)
    Fout = np.maximum(egg_F(X, Y, Z), hat.F(X, Y, Z))
    F = np.minimum(np.minimum(Fout, -Fcav_cap), Z - Z_CAP0).astype(np.float32)
    m = mesh_from_F(F, axes, EG.VOX)
    m = decimate(m, 240000, label=f"czapka-jajko-{kind}")
    save(m, f"jajko_czapka_{kind}.stl", True, "otworem do dolu; czapka krasnala/Mikolaja przytopiona")
    return m


if __name__ == "__main__":
    which = sys.argv[1:] or ["krasnal", "mikolaj", "jajko_krasnal", "jajko_mikolaj"]
    for w in which:
        if w in ("krasnal", "mikolaj"):
            m, zb = build_body_hat(w)
            fit_body_hat(m, zb, w)
            save(m, f"czapka_{w}.stl", True, "dolem na stol; osadzana na glowie korpusu")
        else:
            egg_hat_cap(w.split("_")[1])
    print(f"czas {time.time() - T0:.0f} s")
