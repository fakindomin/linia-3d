"""Grupa B - jajka-matrioszki: parametryczne jajko-pojemnik (miseczka + czapka z kolnierzem) jak jajko L z shapes/build_egg,
skalowane tak, by M miescilo sie w L, a S w M (luz zmierzony na przekroju osiowym)."""
import sys, math, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rev import *
import shapes as SH
from shapely.geometry import Polygon
from shapely import affinity

from standard import LP_SLOPE
CONE = LP_SLOPE                                # |dr/dz| sufitu = 1,3 (52 st. od pionu) - STANDARD v1.0, jak w pozostalych czapkach
R_TOP = 5.0
VOX = 0.35


class Egg:
    def __init__(self, s, wall_cup, rcav_off, floor, lip_wall, lip_h, ceil_off, wall_cap_min, N=None, clear_r=0.25, clear_z=0.2):
        self.s = s
        self.RMAX = 28.0 * s
        self.ZM = 34.0 * s
        self.H = 89.5 * s
        self.A_LOW = self.ZM / 0.9
        self.A_UP = self.H - self.ZM
        self.wall_cup, self.floor = wall_cup, floor
        self.R_CAV = self.RMAX - rcav_off
        self.lip_wall, self.lip_h = lip_wall, lip_h
        self.R_LIP = self.R_CAV + lip_wall
        self.R_BORE = self.R_LIP + clear_r
        self.ZS = self.ZM
        self.Z_CAP0 = self.ZS + clear_z
        self.ZL = self.ZS + lip_h
        self.CEIL = self.H - ceil_off
        self.wall_cap_min = wall_cap_min
        self.Z_A = self.CEIL - (self.R_CAV - R_TOP) / CONE
        self.N = N or n_ribs(self.RMAX)

    def R(self, z):
        z = np.asarray(z, dtype=np.float32)
        ul = np.clip((self.ZM - z) / self.A_LOW, 0, 1)
        uu = np.clip((z - self.ZM) / self.A_UP, 0, 1)
        low = self.RMAX * np.clip(1 - ul ** 2.2, 0, None) ** (1 / 2.2)
        up = self.RMAX * np.clip(1 - uu ** 1.9, 0, None) ** (1 / 1.9)
        return np.where(z <= self.ZM, low, up)

    def cup_r(self, z):
        r = np.minimum(self.R(z) - self.wall_cup, self.R_CAV)
        return np.where((z >= self.floor) & (z <= self.ZL + 0.01), r, -1.0)

    def cap_body_r(self, z):
        cone = self.R_CAV - np.clip(z - self.Z_A, 0, None) * CONE
        return np.minimum(np.minimum(self.R_CAV, self.R(z) - self.wall_cap_min), cone)

    def cap_r(self, z):
        body = np.where((z >= self.ZL) & (z < self.CEIL), self.cap_body_r(z), -1.0)
        bore = np.where((z >= self.Z_CAP0) & (z <= self.ZL + 0.5), self.R_BORE, -1.0)
        return np.maximum(body, bore)

    # ---- profil 2D ----
    def outer_polygon(self, z0=0.0):
        z = np.linspace(0, self.H, 900)
        r = self.R(z) + rib_amp(self.R(z))                      # grzbiety zeber
        pts = [(0.0, 0.0)] + [(float(a), float(b)) for a, b in zip(r, z)] + [(0.0, self.H)]
        return affinity.translate(Polygon(pts), 0, z0)

    def cavity_polygon(self):
        zc = np.linspace(self.floor, self.ZL, 400)
        zb = np.linspace(self.ZL, self.CEIL, 400)
        pts = [(0.0, self.floor)]
        pts += [(float(self.cup_r(z)), float(z)) for z in zc]
        pts += [(float(self.cap_body_r(z)), float(z)) for z in zb[1:]]
        pts += [(0.0, self.CEIL)]
        return Polygon(pts)

    def check_ceiling(self):
        zb = np.linspace(self.ZL, self.CEIL - 0.05, 3000)
        r = self.cap_body_r(zb)
        d = np.gradient(r, zb)
        return float(d.min()), float(r[-1])

    # ---- pola 3D ----
    def fields(self):
        axes, (X, Y, Z) = make_grid(-(self.RMAX + 3), self.RMAX + 3, -(self.RMAX + 3), self.RMAX + 3, -2.5 * VOX, self.H + 2.5, VOX)
        rho = np.sqrt(X ** 2 + Y ** 2)
        th = np.arctan2(Y, X)
        Fout = ribbed_F(self.R(Z), self.N, th, rho).astype(np.float32)
        # miseczka: jajko do z = ZS (plaszczyzna), nad nia kolnierz (rura R_LIP) do z = ZL; wneka z plaskim dnem w z = floor
        Fcup_out = np.maximum(np.minimum(Fout, self.ZS - Z), np.minimum(self.R_LIP - rho, Z - (self.ZS - 1.0)))
        rc = np.minimum(self.R(Z) - self.wall_cup, self.R_CAV)
        cav_cup = np.minimum(rc - rho, Z - self.floor)
        Fcup = np.minimum(np.minimum(Fcup_out, -cav_cup), np.minimum(Z, self.ZL - Z)).astype(np.float32)
        # czapka: wneka = korpus (od ZL do sufitu) + gardziel R_BORE (od dolu do ZL + 0,5); wszystkie granice to plaszczyzny
        cav_body = np.minimum(np.minimum(self.cap_body_r(Z) - rho, Z - self.ZL), self.CEIL - Z)
        cav_bore = np.minimum(self.R_BORE - rho, (self.ZL + 0.5) - Z)
        cav_cap = np.maximum(cav_body, cav_bore)
        Fcap = np.minimum(np.minimum(Fout, -cav_cap), Z - self.Z_CAP0).astype(np.float32)
        return axes, Fcup, Fcap


def egg_L():
    return Egg(1.0, wall_cup=SH.WALL_CUP, rcav_off=4.0, floor=SH.FLOOR, lip_wall=SH.LIP_WALL, lip_h=SH.LIP_H,
               ceil_off=SH.H_EGG - SH.CEIL_Z, wall_cap_min=SH.WALL_CAP_MIN, N=SH.N_EGG)


def make_M(s):
    return Egg(s, wall_cup=3.0, rcav_off=3.4, floor=3.8, lip_wall=1.1, lip_h=6.0, ceil_off=12.0, wall_cap_min=2.5)


def make_S(s):
    return Egg(s, wall_cup=2.8, rcav_off=3.2, floor=3.2, lip_wall=1.0, lip_h=5.0, ceil_off=10.5, wall_cap_min=2.4)


def gap(host, guest):
    """luz [mm] miedzy zewnetrznym obrysem goscia (grzbiety zeber) a wneka gospodarza; ujemny, gdy sie nie miesci"""
    cav = host.cavity_polygon()
    g = guest.outer_polygon(host.floor + 0.8)
    from shapely.geometry import LineString
    boundary = LineString(list(cav.exterior.coords)[:-1])          # bez krawedzi na osi
    if not cav.buffer(1e-6).contains(g):
        return -boundary.distance(g)
    gb = LineString(list(g.exterior.coords)[:-1])
    return float(boundary.distance(gb))


def solve_scale(host, maker, target=0.8):
    lo, hi = 0.3, 0.98
    for _ in range(40):
        mid = (lo + hi) / 2
        if gap(host, maker(mid)) >= target - 1e-4:
            lo = mid
        else:
            hi = mid
    return math.floor(lo * 400) / 400.0           # w dol do 0,0025


if __name__ == "__main__":
    L = egg_L()
    # kontrola zgodnosci z shapes/build_egg
    z = np.linspace(0, SH.H_EGG, 500)
    print("zgodnosc R(z) z shapes.egg_R:", float(np.abs(L.R(z) - SH.egg_R(z)).max()))
    sM = solve_scale(L, make_M, 0.8)
    M = make_M(sM)
    sS = solve_scale(M, make_S, 0.8)
    S = make_S(sS)
    for nm, e, host in (("M", M, L), ("S", S, M)):
        print(f"{nm}: skala {e.s:.4f} | wys. {e.H:.1f} | srednica {2*(e.RMAX+0.8):.1f} | N zeber {e.N} | wneka R {e.R_CAV:.1f} | luz do gospodarza {gap(host, e):.2f} mm | "
              f"sufit: min dr/dz {e.check_ceiling()[0]:.2f} (limit -1,30)")
