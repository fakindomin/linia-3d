import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from parts import surf_tree, to_global
from render import render, section_img
from PIL import Image
LD = lambda n: trimesh.load(OUT + "/" + n + ".stl")
zs = [0.0, 20.0, 53.0, 82.0, 107.0]
names = ["choinka_podstawa", "choinka_1", "choinka_2", "choinka_3", "choinka_4"]
meshes = []
for n, z in zip(names, zs):
    m = LD(n); m.apply_translation([0, 0, z]); meshes.append(m)
fr = Frame(np.array([0.0, 2.5, 129.0]), (1, 0, 0), (0, 0, 1), (0, -1, 0))
star = to_global(LD("choinka_gwiazda"), fr)
meshes.append(star)
ifs = [20.0, 53.0, 82.0, 107.0, 129.0]
print("== czopy / gniazda ==")
for i, zi in enumerate(ifs):
    lo, up = meshes[i], meshes[i + 1]
    V = lo.vertices if i < 4 else star.vertices
    host = up if i < 4 else meshes[4]
    t = surf_tree(host if i < 4 else meshes[4], 500000)
    if i < 4:
        peg = lo.vertices[lo.vertices[:, 2] > zi + 0.3]
        d, _ = surf_tree(up, 500000).query(peg)
    else:
        peg = star.vertices[star.vertices[:, 2] < zi - 0.3]
        d, _ = surf_tree(meshes[4], 500000).query(peg)
    print(f"  {names[i] if i < 4 else 'gwiazda'} -> {names[i+1] if i < 4 else 'choinka_4'}: czop-gniazdo min. odl. {d.min():.2f} mm | czop {peg[:,2].max()-peg[:,2].min():.1f} mm")
allm = trimesh.util.concatenate(meshes)
print("calkowita wysokosc:", round(float(allm.bounds[1][2]), 1), "| szerokosc:", np.round(allm.extents[:2], 1))
SC = 4.6
a = render(meshes, 0, 8, 420, 760, ext=SC, center=(0, 75))
b = section_img(meshes, 420, 760, ext=SC, center=(0, 75))
c = render(meshes, 55, 12, 420, 760, ext=SC, center=(0, 75))
o = Image.new("RGB", (1260, 760), "white")
for i, t in enumerate((a, b, c)): o.paste(t, (i * 420, 0))
o.save(OUT + "/_prev_B5.png"); print(o.size)
