"""Linia lowpoly (wersja 'fasetowana' linii zebrowanej: krolik / renifer / jajko) - wspolna geometria.
Te same wymiary glowne i ten sam interfejs czop 5x5x8 / gniazdo 5,4x5,4x9, pochylenie 14 st., x = +-6, calosc 150 mm."""
import sys, math
import numpy as np
sys.path.insert(0, "/home/claude/linia")
from lp import *
from parts import mount_frame
import shapes as SH

TILT_ = TILT
GAP_ = 0.30
# ---------- korpus krolika / renifera ----------
RINGS_B = [(0, 13.53), (9, 16.37), (22, 18.32), (40, 19.0), (52, 18.85), (64, 18.05), (74, 16.4), (83, 13.6), (91, 8.27),
           (98, 14.39), (105, 16.0), (112, 14.39), (118, 9.3), (121, 0.0)]
M_B = 10


def body_solid():
    return revolve_rings(RINGS_B, M_B)


# ---------- jajko ----------
M_E = 14
ZM, ZS, ZL = 34.0, 34.0, 41.0            # szew, kolnierz do z = 41
Z_CAP0 = 34.2
R_CAV, R_LIP, R_BORE = 24.0, 25.2, 25.45
FLOOR = 4.5
CEIL = 76.0
R_TOP = 5.0
WALL_CAP = 3.0                           # minimalna sciana czapki (nominalnie; fasety zmniejszaja do ~2,4)
CONE = 1.30                              # |dr/dz| sufitu stozkowego (52,4 st. od pionu; zapas na fasety)
H_EGG = SH.H_EGG
EGG_LOW = [0.0, 3.5, 8.0, 14.0, 21.0, 28.0, 34.0]
EGG_UP = [34.2, 40.0, 46.0, 52.0, 58.0, 64.0, 70.0, 75.0, 79.0, 83.0, 86.0, 88.5]


def egg_rings(zs):
    return [(z, float(SH.egg_R(z))) for z in zs]


def egg_outer_full():
    """cale jajko: pierscien z = 34,2 ma ta sama faze co z = 34 (jak w miseczce i czapce)"""
    zr = egg_rings(EGG_LOW) + [(EGG_UP[0], float(SH.egg_R(EGG_UP[0])), "same")] + egg_rings(EGG_UP[1:]) + [(H_EGG, 0.0)]
    return revolve_rings(zr, M_E)


def egg_outer_cup():
    return revolve_rings(egg_rings(EGG_LOW), M_E)


def egg_outer_cap():
    zr = egg_rings(EGG_UP) + [(H_EGG, 0.0)]
    # pierwszy pierscien czapki ma te sama faze co ostatni pierscien miseczki (z = 34)
    return revolve_rings(zr, M_E, j0=(len(EGG_LOW) - 1) % 2)


def r_cup_cav(z):
    return min(float(SH.egg_R(z)) - SH.WALL_CUP, R_CAV)


def cavity_cup():
    zr = [(FLOOR, r_cup_cav(FLOOR)), (9.0, r_cup_cav(9.0)), (15.0, r_cup_cav(15.0)), (24.0, R_CAV, 0),
          (30.0, R_CAV, "same"), (ZL + 1.0, R_CAV, "same")]
    return revolve_rings(zr, M_E)


def egg_lip():
    return prism(M_E, R_LIP, ZS - 1.0, ZL)


def cavity_cap():
    """gardziel (R_BORE do ZL + 0,5) + wneka czapki (R_CAV, potem R - 2,6, stozek sufitu, plaski sufit r = 5)"""
    bore = prism(M_E, R_BORE, Z_CAP0 - 0.8, ZL + 0.5)
    za = CEIL - (R_CAV - R_TOP) / CONE
    zr = [(ZL, R_CAV, 0), (47.0, R_CAV, "same")]
    for z in (53.0, 59.0, 63.0, 67.0, 71.0, 74.0):
        zr.append((z, min(float(SH.egg_R(z)) - WALL_CAP, R_CAV - max(z - za, 0.0) * CONE)))
    zr.append((CEIL, R_TOP))
    return bore, revolve_rings(zr, M_E)


# ---------- czop / gniazdo ----------
def socket_solid():
    return chamfer_box((-SOCK_W / 2, -SOCK_D, 2.5 - SOCK_W / 2), (SOCK_W / 2, 1.5, 2.5 + SOCK_W / 2), 1.0)


def peg_solid(ext=2.0):
    return chamfer_box((-PEG_W / 2, -PEG_L, 0.0), (PEG_W / 2, ext, PEG_W), 1.0)


def frame_at(side, mesh, y=SH.Y0):
    """ramka montazowa 14 st. w punkcie (+-6, y) na gorze bryly 'mesh'"""
    z = top_z_at(mesh, side * SH.EAR_X, y)
    return mount_frame(side, np.array([side * SH.EAR_X, y, z])), z
