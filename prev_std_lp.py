"""Podglad zbiorczy lowpoly (STANDARD v1.0): out/podglad_lowpoly_std.png"""
import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models import *
from render import render, grid
from PIL import Image

FV = lambda ms: [flat_view(m) for m in ms]
body = lp_bunny_solid()
parts, info = lp_ear_parts()
egg, eg = lp_egg_parts()
pk, pi = lp_pumpkin_parts()
sn, si = lp_snowman_parts()
G = lambda m, model, pn: to_global(m, model.ports[pn].frame)
fb = lambda nm: [G(parts[f"{nm}_prawe"], BUNNY, "ear_R"), G(parts[f"{nm}_lewe"], BUNNY, "ear_L")]
fe = lambda nm: [G(parts[f"{nm}_prawe"], EGG, "ear_R"), G(parts[f"{nm}_lewe"], EGG, "ear_L")]
bs = cut_ports(body, BUNNY)
R1 = lambda ms, yaw=25: render(FV(ms), yaw, 8, 380, 800, ext=800 / 165, center=(0, 75), dens=9)
leaf_f, ant_f = ear_leaf(info["L_SHORT"], -4.5), antler_solid(info["LAM"], -4.5)
kr = union(body, *[G(leaf_f, BUNNY, pn) for _, _, pn in SIDES])
re_ = union(body, G(ant_f, BUNNY, "ear_R"), G(mirror_a(ant_f), BUNNY, "ear_L"))
row1 = [R1([kr]), R1([re_]), R1([bs] + fb("lp_ucho")), R1([bs] + fb("lp_ucho_dlugie")), R1([bs] + fb("lp_poroze"))]
cup, cap, cap_e, cap_l = egg["lp_jajko_miseczka"], egg["lp_jajko_czapka_gniazda"], egg["lp_jajko_czapka_uszy"], egg["lp_jajko_czapka_uszy_dlugie"]
R2 = lambda ms, yaw=25: render(FV(ms), yaw, 8, 380, 800, ext=800 / 165, center=(0, 62), dens=9)
row2 = [R2([cup, cap_e]), R2([cup, cap_l]), R2([cup, cap] + fe("lp_ucho")), R2([cup, cap] + fe("lp_poroze"))]
stem_g = to_global(pi["stem_local"], PUMPKIN.ports["stem"].frame)
R3 = lambda ms, yaw=25: render(FV(ms), yaw, 22, 520, 520, ext=520 / 125, center=(0, 36), dens=9)
nose_g = G(sn["lp_balwan_nos"], SNOWMAN, "nose")
broom_g = G(sn["lp_balwan_miotla"], SNOWMAN, "broom")
R4 = lambda ms, yaw: render(FV(ms), yaw, 8, 520, 800, ext=800 / 165, center=(8, 75), dens=9)
row3 = [R3([cut_ports(pi["sm"], PUMPKIN), stem_g]), R3([cut_ports(pi["lb"], PUMPKIN), stem_g]),
        R4([sn["lp_balwan"], nose_g, broom_g], 25), R4([sn["lp_balwan"], nose_g, broom_g], -60)]
a, b, c = grid(row1, 5), grid(row2, 4), grid(row3, 4)
w = max(a.width, b.width, c.width)
out = Image.new("RGB", (w, a.height + b.height + c.height), (255, 255, 255))
out.paste(a, (0, 0)); out.paste(b, (0, a.height)); out.paste(c, (0, a.height + b.height))
out.save(OUT + "/podglad_lowpoly_std.png"); print(out.size)
