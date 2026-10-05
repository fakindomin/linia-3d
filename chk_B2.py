import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from parts import surf_tree
from render import render, section_img
from PIL import Image, ImageDraw
L = lambda n: trimesh.load(OUT + "/" + n + ".stl")
def flip(m, c):
    g = m.copy(); g.vertices[:, 2] = c - g.vertices[:, 2]; g.invert(); return g
# ---- doniczka w podstawce ----
FL = 2.5
print("== doniczka + podstawka ==")
asm = {}
for k in "SML":
    pot, sau = L(f"doniczka_{k}"), L(f"podstawka_{k}")
    p = pot.copy(); p.apply_translation([0, 0, FL])
    tree = surf_tree(sau, 500000)
    V = p.vertices
    d, _ = tree.query(V)
    side = V[:, 2] > FL + 0.3          # poza stykiem z dnem
    print(f"  {k}: min. odl. doniczka-podstawka (bez dna) {d[side & (V[:,2] < 12)].min():.2f} mm | wysokosc razem {p.bounds[1][2]:.1f} | rozstaw dna do pierscienia")
    asm[k] = (p, sau)
# ---- sloik ----
print("== sloik + pokrywa + galka ==")
jar, lid, knob = L("sloik"), L("sloik_pokrywa"), L("sloik_galka")
HJ = 74.0
lid_a = flip(lid, HJ + 4.0)            # z' = HJ + 4 - z
knob_a = flip(knob, HJ + 4.0 + (knob.bounds[1][2] - 8.0 - 0.0) * 0)   # dopasowane nizej
Hk = knob.bounds[1][2] - 8.0           # wys. kuli (z plaskiej strony czopa)
knob_a = flip(knob, HJ + 4.0 + Hk)     # z' = HJ+4+Hk - z : plaska strona czopa (z=Hk) -> HJ+4
tj = surf_tree(jar, 500000)
V = lid_a.vertices
d, _ = tj.query(V)
lipm = V[:, 2] < HJ - 0.4
print(f"  pokrywa: kolnierz-sloik min. odl. {d[lipm].min():.2f} mm (nominalnie 0,3) | wys. razem z gałka {knob_a.bounds[1][2]:.1f}")
tl = surf_tree(lid_a, 500000)
V = knob_a.vertices
d, _ = tl.query(V)
peg = V[:, 2] < HJ + 4.0 - 0.3
print(f"  galka: czop-gniazdo min. odl. {d[peg].min():.2f} mm (nominalnie 0,2) | czop konczy sie na z={V[:,2].min():.1f}, dno gniazda na z={HJ+4-9:.1f}")
# ---- podglad ----
SC, H = 4.4, 640
tiles = []
for k in "SML":
    p, sau = asm[k]
    tiles.append(render([p, sau], 0, 8, 380, H, ext=SC, center=(0, 40)))
    tiles.append(section_img([p, sau], 380, H, ext=SC, center=(0, 40)))
tiles.append(render([jar, lid_a, knob_a], 0, 8, 380, H, ext=SC, center=(0, 40)))
tiles.append(section_img([jar, lid_a, knob_a], 380, H, ext=SC, center=(0, 40)))
tiles.append(render([jar, flip(lid, 200) if False else lid_a], -35, 18, 380, H, ext=SC, center=(0, 40)))
o = Image.new("RGB", (380 * len(tiles), H), "white")
for i, t in enumerate(tiles): o.paste(t, (i * 380, 0))
o.save(OUT + "/_prev_B2.png"); print(o.size)
