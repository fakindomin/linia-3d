"""Ksztalty korpusow (pola 3D) wspolne dla skryptow: krolik/renifer (korpus bazowy) i jajko."""
import math
import numpy as np
from lib import *

# ---------- korpus bazowy krolika / renifera ----------
BODY_R, BODY_HZ, BODY_N, CUT_U = 19.0, 52.0, 2.5, -0.8
BODY_ZC = -CUT_U * BODY_HZ
HEAD_R, HEAD_ZC, SMOOTH_P = 16.0, 105.0, 20.0
N_BUNNY = 36
Y0 = 0.25                      # srodek grubosci ucha lezy w y=0 (os czopu w y=+0,25)


def bunny_profile(z):
    u = (z - BODY_ZC) / BODY_HZ
    ub = np.clip(np.abs(u), 0, 1)
    rb = BODY_R * np.clip(1 - ub ** BODY_N, 0, None) ** (1 / BODY_N)
    rb = np.where(np.abs(u) <= 1, rb, 0.0)
    v = np.clip((z - HEAD_ZC) / HEAD_R, -1, 1)
    rh = HEAD_R * np.sqrt(np.clip(1 - v ** 2, 0, None))
    return (rb ** SMOOTH_P + rh ** SMOOTH_P) ** (1 / SMOOTH_P)


def bunny_F(X, Y, Z):
    rho = np.sqrt(X ** 2 + Y ** 2)
    th = np.arctan2(Y, X)
    return np.minimum(ribbed_F(bunny_profile(Z), N_BUNNY, th, rho), Z).astype(np.float32)


def bunny_P0(side):
    rho0 = math.hypot(EAR_X, Y0)
    return np.array([side * EAR_X, Y0, HEAD_ZC + math.sqrt(HEAD_R ** 2 - rho0 ** 2)])


# ---------- jajko (czapka) ----------
EGG_H, EGG_D = 68.0, 44.0
FLOOR = 4.5
R_CAV = EGG_D / 2 + 2.0
WALL_CUP = 3.3
RMAX = R_CAV + 4.0
LIP_WALL, LIP_H = 1.2, 7.0
CLEAR_R, CLEAR_Z = 0.25, 0.2
R_LIP = R_CAV + LIP_WALL
R_BORE = R_LIP + CLEAR_R
ZM = 34.0
H_EGG = 89.5                    # wierzcholek czapki (bez uszu)
A_LOW = ZM / 0.9
A_UP = H_EGG - ZM
N_LOW, N_UP = 2.2, 1.9
ZS = ZM
Z_CAP0 = ZS + CLEAR_Z
N_EGG = 48
WALL_CAP_MIN = 2.6
CEIL_Z = 76.0                   # plaski sufit wnetrza czapki


def egg_R(z):
    z = np.asarray(z, dtype=np.float32)
    ul = np.clip((ZM - z) / A_LOW, 0, 1)
    uu = np.clip((z - ZM) / A_UP, 0, 1)
    low = RMAX * np.clip(1 - ul ** N_LOW, 0, None) ** (1 / N_LOW)
    up = RMAX * np.clip(1 - uu ** N_UP, 0, None) ** (1 / N_UP)
    return np.where(z <= ZM, low, up)


def egg_F(X, Y, Z):
    """zewnetrzny ksztalt jajka ze zebrami (bez przycinania do dolu/gory)"""
    rho = np.sqrt(X ** 2 + Y ** 2)
    th = np.arctan2(Y, X)
    return ribbed_F(egg_R(Z), N_EGG, th, rho).astype(np.float32)


def egg_P0(side):
    rho0 = math.hypot(EAR_X, Y0)
    lo, hi = ZM, H_EGG
    for _ in range(80):
        mid = (lo + hi) / 2
        if egg_R(mid) > rho0:
            lo = mid
        else:
            hi = mid
    return np.array([side * EAR_X, Y0, (lo + hi) / 2])
