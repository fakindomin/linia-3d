import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from lib import *
from parts import *
# blok z gniazdem 5,4 x 5,4 x 9 mm pochylonym o 14 st. (druk pionowo) + czop (druk na plasko) = probka pasowania
fr = mount_frame(+1, np.array([0.0, 0.0, 16.0]))
axes, (X, Y, Z) = make_grid(-12, 12, -12, 12, -1.0, 16.5, 0.2)
F = rbox_F(X, Y, Z, (-11, -11, 0.0), (11, 11, 16.0), 1.5)
F = np.minimum(F, Z)
a, b, c = fr.to_local(X, Y, Z)
F = np.minimum(F, -socket_F(a, b, c)).astype(np.float32)
blk = mesh_from_F(F, axes, 0.2)
save(blk, "test_gniazdo_blok.stl", True, "probka pasowania: gniazdo 14 st.")

def peg_fn(a, b, c):
    plate = rbox_F(a, b, c, (-8, 1.0, 0.0), (8, 9.0, 5.5), 1.0)
    return np.maximum(plate, peg_ext_F(a, b, c)).astype(np.float32)
pg = local_mesh(peg_fn, (-10, 10), (-9, 10), (-0.6, 6.5), 0.2)
save(pg, "test_czop.stl", False, "probka pasowania: czop 5x5x8 na plytce, druk na plasko")
