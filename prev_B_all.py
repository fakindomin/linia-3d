import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from render import render
from matrioszka import egg_L, make_M, make_S, solve_scale
from PIL import Image, ImageDraw, ImageFont
LD = lambda n: trimesh.load(OUT + "/" + n + ".stl")
try:
    FONT = ImageFont.load_default(size=15)
except Exception:
    FONT = None
SC = 3.6
def flip(m, c):
    g = m.copy(); g.vertices[:, 2] = c - g.vertices[:, 2]; g.invert(); return g
def tile(meshes, label, w_mm, H, yaw=0, pad=26):
    W = max(int(w_mm * SC + 2 * pad), 340)
    cz = (H / 2 - 34) / SC
    im = render(meshes, yaw, 8, W, H, ext=SC, center=(0, cz))
    ImageDraw.Draw(im).text((8, H - 24), label, fill=(70, 70, 70), font=FONT)
    return im
def row(tiles):
    o = Image.new("RGB", (sum(t.width for t in tiles), tiles[0].height), "white"); x = 0
    for t in tiles: o.paste(t, (x, 0)); x += t.width
    return o
# --- zlozenia ---
Lg = egg_L(); Mg = make_M(solve_scale(Lg, make_M, 0.8)); Sg = make_S(solve_scale(Mg, make_S, 0.8))
def egg(cup, cap, e, dx=0.0):
    a, b = LD(cup), LD(cap); b.apply_translation([0, 0, e.Z_CAP0]); 
    for m in (a, b): m.apply_translation([dx, 0, 0])
    return [a, b]
eggs = egg("jajko_miseczka", "jajko_czapka_gniazda", Lg, -44) + egg("jajko_M_miseczka", "jajko_M_czapka", Mg, 0) + egg("jajko_S_miseczka", "jajko_S_czapka", Sg, 36)
pots = {}
for k in "SML":
    p = LD(f"doniczka_{k}"); p.apply_translation([0, 0, 2.5]); pots[k] = [p, LD(f"podstawka_{k}")]
jar, lid, knob = LD("sloik"), LD("sloik_pokrywa"), LD("sloik_galka")
Hk = knob.bounds[1][2] - 8.0
jarset = [jar, flip(lid, 74.0 + 4.0), flip(knob, 74.0 + 4.0 + Hk)]
zs = [0.0, 20.0, 53.0, 82.0, 107.0]
tree = []
for n, z in zip(["choinka_podstawa", "choinka_1", "choinka_2", "choinka_3", "choinka_4"], zs):
    m = LD(n); m.apply_translation([0, 0, z]); tree.append(m)
fr = Frame(np.array([0.0, 2.5, 129.0]), (1, 0, 0), (0, 0, 1), (0, -1, 0))
from parts import to_global
tree.append(to_global(LD("choinka_gwiazda"), fr))
H1, H2, H3 = 600, 410, 480
r1 = row([tile([LD("wazon_butelka")], "wazon_butelka  150 mm", 66, H1), tile([LD("wazon_owal")], "wazon_owal  120 mm", 71, H1),
          tile([LD("wazon_walec")], "wazon_walec  90 mm", 67, H1), tile([LD("swiecznik_tealight")], "swiecznik_tealight  58 mm", 58, H1),
          tile([LD("swiecznik_swieca")], "swiecznik_swieca  66 mm", 62, H1), tile(tree, "choinka_podstawa + 1..4 + gwiazda  151 mm", 58, H1)])
r2 = row([tile(pots["S"], "doniczka_S + podstawka_S  57 mm", 65, H2), tile(pots["M"], "doniczka_M + podstawka_M  75 mm", 85, H2),
          tile(pots["L"], "doniczka_L + podstawka_L  93 mm", 105, H2), tile(jarset, "sloik + pokrywa + galka  98 mm", 75, H2)])
r3 = row([tile(eggs, "jajko L (istniejace) > M > S  (zagniezdzone: M 70, S 52 mm)", 140, H3)] +
         [tile([LD(n)], f"{n}  {h} mm", w, H3) for n, h, w in (("bombka_okragla_60", 68, 62), ("bombka_okragla_80", 86, 82), ("bombka_okragla_100", 104, 102), ("bombka_kropla", 122, 62))])
W = max(r.width for r in (r1, r2, r3))
o = Image.new("RGB", (W, H1 + H2 + H3), "white")
y = 0
for r in (r1, r2, r3): o.paste(r, (0, y)); y += r.height
o.save(OUT + "/podglad_grupaB.png"); print(o.size)
