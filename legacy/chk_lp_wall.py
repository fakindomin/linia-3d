import sys, pickle
sys.path.insert(0, "/home/claude/linia")
from lp_parts import *
from scipy.spatial import cKDTree
E = pickle.load(open(OUT + "/_lp_egg.pkl", "rb"))
def walls(cav, outer, zmin, zmax, label):
    pc = trimesh.sample.sample_surface(cav, 400000, seed=3)[0]
    pc = pc[(pc[:, 2] > zmin) & (pc[:, 2] < zmax)]
    po = trimesh.sample.sample_surface(outer, 600000, seed=4)[0]
    d, _ = cKDTree(po).query(pc)
    z = pc[:, 2]
    # tylko punkty wewnatrz zewnetrznej bryly
    print(f"{label}: min sciana {d.min():.2f} mm (z={z[np.argmin(d)]:.1f}) | 1-percentyl {np.percentile(d, 1):.2f} | mediana {np.median(d):.2f}")
    # po przedzialach z
    for lo in range(int(zmin), int(zmax), 10):
        m = (z >= lo) & (z < lo + 10)
        if m.any(): print(f"     z {lo}-{lo+10}: min {d[m].min():.2f}")
cup_outer = union(E["cup_out"], egg_lip())
walls(E["cav_cup"], cup_outer, FLOOR + 0.2, 34.0, "miseczka (do z=34)")
walls(E["cav_body"], E["cap_out"], 36.0, CEIL - 0.1, "czapka")
