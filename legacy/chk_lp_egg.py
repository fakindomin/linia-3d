import sys, pickle
sys.path.insert(0, "/home/claude/linia")
from lp_parts import *
from scipy.spatial import cKDTree
E = pickle.load(open(OUT + "/_lp_egg.pkl", "rb"))
cup, cap, cap_ears, cap_long = E["cup"], E["cap_sock"], E["cap_ears"], E["cap_long"]
# --- nawisy: klastry po z i kacie
for nm, m in (("miseczka", cup), ("czapka (pozycja zlozona, z=34,2 = stol)", cap)):
    n = m.face_normals; zc = m.triangles_center[:, 2]; A = m.area_faces
    low = n[:, 2] < -1e-3
    ang = np.degrees(np.arccos(np.clip(-n[:, 2], 0, 1)))          # kat normalnej od -z; od pionu = 90 - ang? (powierzchnia pozioma: normalna -z -> ang=0)
    # kat powierzchni od pionu = ang (0 = pozioma w dol -> 90 od pionu)
    fromvert = 90 - ang
    print(nm)
    horiz = low & (ang < 1.0)
    if horiz.any():
        zs = np.round(zc[horiz], 1)
        for z in np.unique(zs):
            print(f"   pozioma w dol z={z}: {A[horiz][zs == z].sum():.1f} mm2")
    inc = low & ~horiz
    if inc.any():
        i = np.argmax(fromvert * inc)
        print(f"   najwiekszy nawis nieposzly (nie-poziomy): {fromvert[inc].max():.1f} st. od pionu na z={zc[inc][np.argmax(fromvert[inc])]:.1f}")
        big = inc & (fromvert > 50)
        print(f"   powyzej 50 st.: {A[big].sum():.1f} mm2")
# --- Kinder egg 44 x 68 w pozycji zlozonej (FLOOR = 4,5)
zz = np.linspace(FLOOR, FLOOR + 68, 400); t = np.clip(np.abs(zz - (FLOOR + 34)) / 34, 0, 1)
rr = 22 * np.clip(1 - t ** 2.3, 0, None) ** (1 / 2.3)
egg = revolve_rings([(float(z), float(r)) for z, r in zip(zz[::4], rr[::4])] + [(zz[-1], 0.0)], 64, eqarea=False) if False else None
# powierzchnia jajka: probki punktow
th = np.linspace(0, 2 * np.pi, 180, endpoint=False)
pts = np.array([(r * np.cos(a), r * np.sin(a), z) for z, r in zip(zz, rr) for a in th])
pts = np.vstack([pts, [[0, 0, FLOOR], [0, 0, FLOOR + 68]]])
for nm, m in (("miseczka", cup), ("czapka", cap)):
    from trimesh.proximity import signed_distance
    sd = -signed_distance(m, pts)          # trimesh: dodatnie wewnatrz -> odwracamy: dodatnie = poza materialem... sprawdz
    print(nm, "signed_distance min/max:", round(float(signed_distance(m, pts).min()), 2), round(float(signed_distance(m, pts).max()), 2))
d_cup = signed_distance(cup, pts); d_cap = signed_distance(cap, pts)
inside = (d_cup > 0) | (d_cap > 0)
print("punkty jajka wewnatrz materialu:", int(inside.sum()))
tree = cKDTree(np.vstack([trimesh.sample.sample_surface(cup, 200000, seed=1)[0], trimesh.sample.sample_surface(cap, 200000, seed=1)[0]]))
dd, _ = tree.query(pts)
print(f"min. luz jajka do scian miseczki/czapki: {dd.min():.2f} mm; wysokosc nad jajkiem do sufitu: {CEIL - (FLOOR + 68):.1f} mm")
# --- miseczka vs czapka w pozycji zlozonej
print("wspolna objetosc miseczka/czapka:", round(abs(inter(cup, cap).volume), 3), "mm3")
tc = cKDTree(trimesh.sample.sample_surface(cup, 300000, seed=2)[0])
d2, _ = tc.query(cap.vertices)
print(f"min. odl. wierzcholkow czapki od miseczki: {d2.min():.2f} mm")
# --- grubosc scian: wneka vs zewnatrz
cu_out = E["cup_out"]; cap_out = E["cap_out"]
for nm, cav, outm, mask_z in (("miseczka", E["cav_cup"], cup, None), ("czapka", E["cav_body"], cap, None)):
    pc, _ = trimesh.sample.sample_surface(cav, 200000, seed=3)
    # tylko punkty wneki wewnatrz materialu czesci (poza otworem)
    to = cKDTree(trimesh.sample.sample_surface(outm, 400000, seed=4)[0])
    dist, _ = to.query(pc)
    print(f"{nm}: min. odl. powierzchni wneki od innej powierzchni czesci (sciany): {dist.min():.2f} mm")
# --- gniazdo - wneka czapki (grubosc sciany przy gniazdach)
print("gniazda: sciana miedzy gniazdem a wneka czapki:")
sock = [to_global(socket_solid(), trimesh.load(OUT + '/_lp_frames.pkl', 'rb') if False else None) for _ in ()]
