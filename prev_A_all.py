import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from parts import to_global
from shapes import Z_CAP0
from build_figurki import FRe
from render import render
from PIL import Image, ImageDraw
L = lambda n: trimesh.load(OUT + "/" + n)
SC = 4.3; H = 680; W = 330
def tile(meshes, label, cz=70, w=W, yaw=0):
    im = render(meshes, yaw, 6, w, H, ext=SC, center=(0, cz))
    d = ImageDraw.Draw(im); d.text((8, 8), label, fill=(70, 70, 70)); return im
body = L("korpus_bazowy.stl")
row1 = [tile([L("krolik_calosc.stl")], "krolik (wzor) 150", 76),
        tile([L("mis_calosc.stl")], "mis 129", 76), tile([L("kot_calosc.stl")], "kot 137", 76),
        tile([L("lis_calosc.stl")], "lis 144 + ogon", 76, 420, yaw=0), tile([L("sowa_calosc.stl")], "sowa 134", 76),
        tile([L("aniol_calosc.stl")], "aniol 150", 76, 520)]
for nm in ("krasnal", "mikolaj"):
    h = L(f"czapka_{nm}.stl"); h.apply_translation([0, 0, 106.6])
    row1.append(tile([body, h], f"{nm} (czapka wymienna) 150", 76))
cup = L("jajko_miseczka.stl")
def egg(cap_name, label, ears=None):
    c = L(cap_name); c.apply_translation([0, 0, Z_CAP0]); ms = [cup, c]
    if ears:
        for s, sn in ((+1, "prawe"), (-1, "lewe")):
            ms.append(to_global(L(f"ucho_{ears}_{sn}.stl"), FRe[s]))
    return tile(ms, label, 60)
row2 = [tile([L("duszek.stl")], "duszek 105", 52),
        egg("jajko_czapka_pisklo.stl", "jajko-pisklo 98"), egg("jajko_czapka_krasnal.stl", "jajko-krasnal 128"), egg("jajko_czapka_mikolaj.stl", "jajko-Mikolaj 118")]
for e in ("mis", "kot", "lis", "sowa"):
    row2.append(egg("jajko_czapka_gniazda.stl", f"jajko + uszy {e} (wymienne)", ears=e))
def rowimg(tiles):
    o = Image.new("RGB", (sum(t.width for t in tiles), H), "white"); x = 0
    for t in tiles: o.paste(t, (x, 0)); x += t.width
    return o
r1, r2 = rowimg(row1), rowimg(row2)
o = Image.new("RGB", (max(r1.width, r2.width), 2 * H), "white"); o.paste(r1, (0, 0)); o.paste(r2, (0, H))
o.save(OUT + "/podglad_grupaA.png"); print(o.size)
