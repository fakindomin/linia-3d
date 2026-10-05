"""Grupa A - duszek na Halloween: zebrowane przescieradlo z falbana (7 platow), twarz jako plytkie wglebienia (bez nawisow >55).
 duszek.stl  (calosc 105 mm, podstawa ~55 mm)"""
import sys, math, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

VOX = 0.35
H = 105.0
R_HEM = 27.5
R_D = 19.0                      # kopula glowy
Z_D = H - R_D                   # srodek kopuly
K_SC, H_SC = 7, 9.0             # liczba platow falbany, glebokosc wyciec
N_RIB = 46
T0 = time.time()


def sstep(z, z0, z1):
    t = np.clip((z - z0) / (z1 - z0), 0, 1)
    return t * t * (3 - 2 * t)


def R_prof(z):
    z = np.asarray(z, np.float32)
    flare = R_D + (R_HEM - R_D) * np.clip((Z_D - z) / Z_D, 0, 1) ** 1.4
    dome = np.sqrt(np.clip(R_D ** 2 - (z - Z_D) ** 2, 0, None))
    return np.where(z >= Z_D, dome, flare)


def pit_F(X, Y, Z, xc, zc, a, b, D):
    """wglebienie paraboloidalne w przedniej scianie (-y): stoki <= 53 st. od pionu u gory"""
    s = -Y
    R = R_prof(Z)
    s_surf = np.sqrt(np.clip(R ** 2 - X ** 2, 0, None))
    q2 = ((X - xc) / a) ** 2 + ((Z - zc) / b) ** 2
    q = np.sqrt(q2)
    depth = D * np.clip(1 - q2, 0, None)
    return np.minimum((1 - q) * min(a, b), s - (s_surf - depth) + 0.0 * s).astype(np.float32)


def ghost_F(X, Y, Z):
    rho = np.sqrt(X ** 2 + Y ** 2)
    th = np.arctan2(Y, X)
    R = R_prof(Z)
    rib = np.cos(N_RIB * th)
    rib = np.sign(rib) * np.abs(rib) ** 0.8
    F = (R + rib_amp(R) * rib - 1e-3) - rho
    # falbana u dolu: z_h(r, th) = H_SC (1 - cos K th) / 2, narastajaca od r = 6 do 15 (srodek plasko na stole)
    zh = H_SC * (1 - np.cos(K_SC * th)) / 2 * sstep(rho, 6.0, 15.0)
    F = np.minimum(F, Z - zh)
    F = np.minimum(F, H - Z)
    # twarz
    face = np.maximum(pit_F(X, Y, Z, -7.4, 88.5, 3.4, 5.5, 2.8), pit_F(X, Y, Z, 7.4, 88.5, 3.4, 5.5, 2.8))
    face = np.maximum(face, pit_F(X, Y, Z, 0.0, 70.5, 4.4, 5.4, 3.0))
    F = np.minimum(F, -face)
    return F.astype(np.float32)


if __name__ == "__main__":
    axes, (X, Y, Z) = make_grid(-30, 30, -30, 30, -1.0, H + 1.5, VOX)
    F = ghost_F(X, Y, Z)
    m = mesh_from_F(F, axes, VOX)
    m = decimate(m, 330000, label="duszek")
    save(m, "duszek.stl", True, "falbana na stole; twarz: wglebienia")
    print(f"czas {time.time() - T0:.0f} s")
