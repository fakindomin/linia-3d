import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
from PIL import Image, ImageDraw
from lib import *
from parts import *
from render import render
import build_snowman as SN
import build_pumpkin as PK
from shapes import Z_CAP0

SC = 5.4            # px na mm (wspolna skala dla wszystkich)
W, H = 560, 860
cz = 76.0

def tile(meshes, label, yaw=0, pitch=7, colors=None, w=W):
    im = render(meshes, yaw, pitch, w, H, ext=SC, center=(0, cz), colors=colors)
    d = ImageDraw.Draw(im); d.text((10, 8), label, fill=(70, 70, 70))
    return im

L = lambda n: trimesh.load(OUT + "/" + n)
krol, ren = L("krolik_calosc.stl"), L("renifer_calosc.stl")
sn_body = L("balwan.stl"); nose = L("balwan_nos.stl"); broom = L("balwan_miotla.stl")
SN_all = [sn_body, to_global(nose, SN.FR_NOSE), to_global(broom, SN.FR_BROOM)]
cup = L("jajko_miseczka.stl"); cap = L("jajko_czapka_uszy.stl"); cap.apply_translation([0, 0, Z_CAP0])
sdf = local_sdf(lambda X, Y, Z: PK.pumpkin_F(X, Y, Z, PK.S_FINE, "fine"), PK.P_STEM + [0, 0, 4], (14, 14, 12), 0.1)
stem = local_mesh(PK.stem_fn(sdf), (-12, 12), (-9, PK.STEM_H + 1), (-9, 14), 0.2)
pump = L("dynia_korpus.stl"); pump_l = L("dynia_korpus_platy.stl")
PK_all = [pump, to_global(stem, PK.FR_STEM)]
PK_l = [pump_l, to_global(stem, PK.FR_STEM)]
tiles = [tile([krol], "krolik 150 mm"), tile([ren], "renifer 150 mm"),
         tile(SN_all, "balwan 150 mm", w=700), tile([cup, cap], "jajko ~118 mm"),
         tile(PK_all, "dynia 100 x 65 (+ogonek)", w=700), tile(PK_l, "dynia - 36 platow", w=700)]
tw = sum(t.width for t in tiles)
out = Image.new("RGB", (tw, H), (255, 255, 255))
x = 0
for t in tiles:
    out.paste(t, (x, 0)); x += t.width
out.save(OUT + "/linia_razem.png")
print(out.size)
