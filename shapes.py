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


# parametry korpusu (u krolika i renifera 'bazowego' = stale powyzej; nowe pola maja wartosci neutralne, wiec dawne ksztalty sie nie zmieniaja)
BODY_DEFAULTS = dict(bodyW=2 * BODY_R, bodyHz=BODY_HZ, bodyN=BODY_N, bodyNu=BODY_N, bellyDz=0.0, headR=HEAD_R, headZ=HEAD_ZC, headK=1.0,
                     neckR=0.0, blend=SMOOTH_P, ribs=N_BUNNY)


def body_params(**kw):
    """pelny zestaw parametrow korpusu: domyslne (krolik) + nadpisania; klucze jak w suwakach podgladu"""
    d = dict(BODY_DEFAULTS)
    bad = set(kw) - set(d)
    assert not bad, f"nieznane parametry korpusu: {bad}"
    d.update(kw)
    return d


def bunny_profile(z, p=None):
    """promien korpusu na wysokosci z = trzy czlony p-normy (wykladnik blend): brzuch (nadelipsoida, dol i gora z osobnymi wykladnikami
    bodyN / bodyNu, najszersze miejsce na z = 0,8 bodyHz + bellyDz), glowa (elipsoida: promien headR, os pionowa headR * headK) i szyja
    (walec o promieniu neckR miedzy brzuchem a srodkiem glowy; 0 = brak). Dla p=None dokladnie dawny profil krolika."""
    p = BODY_DEFAULTS if p is None else p
    HZ, ZC = p["bodyHz"], -CUT_U * p["bodyHz"] + p["bellyDz"]
    u = (z - ZC) / HZ
    ub = np.clip(np.abs(u), 0, 1)
    N = p["bodyN"] if p["bodyNu"] == p["bodyN"] else np.where(u < 0, p["bodyN"], p["bodyNu"])
    rb = (p["bodyW"] / 2) * np.clip(1 - ub ** N, 0, None) ** (1 / N)
    rb = np.where(np.abs(u) <= 1, rb, 0.0)
    HR, K = p["headR"], p["headK"]
    v = np.clip((z - p["headZ"]) / (HR * K), -1, 1)
    rh = HR * np.sqrt(np.clip(1 - v ** 2, 0, None))
    sp = p["blend"]
    s = rb ** sp + rh ** sp
    NR = min(p["neckR"], 0.95 * HR)
    if NR > 0:
        s = s + np.where((z >= ZC) & (z <= p["headZ"]), NR, 0.0) ** sp
    return s ** (1 / sp)


def bunny_F(X, Y, Z, p=None, n=None):
    rho = np.sqrt(X ** 2 + Y ** 2)
    th = np.arctan2(Y, X)
    n = int(round(BODY_DEFAULTS["ribs"] if p is None else p["ribs"])) if n is None else int(round(n))
    return np.minimum(ribbed_F(bunny_profile(Z, p), n, th, rho), Z).astype(np.float32)


def bunny_P0(side, p=None, ear_x=None):
    """punkt mocowania poroza / ucha na szczycie glowy (x = +-EAR_X, y = Y0); dla elipsoidy glowy z uwzglednieniem headK"""
    p = BODY_DEFAULTS if p is None else p
    ex = EAR_X if ear_x is None else ear_x
    rho0 = math.hypot(ex, Y0)
    return np.array([side * ex, Y0, p["headZ"] + p["headK"] * math.sqrt(p["headR"] ** 2 - rho0 ** 2)])


def head_port(side, p, polar_deg, T=5.5):
    """punkt na powierzchni glowy pod katem polar_deg od pionu (do bocznych uszy-lisci); y tak, by plaskie ucho grubosci T lezalo symetrycznie
    wzgledem plaszczyzny y = 0 (ramka mocowania ma poczatek 2,5 mm za P0, wiec y = T/2 - 2,5; dla T = 5,5 daje standardowe y = 0,25)"""
    ph = math.radians(polar_deg)
    return np.array([side * p["headR"] * math.sin(ph), T / 2.0 - 2.5, p["headZ"] + p["headR"] * p["headK"] * math.cos(ph)])


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
