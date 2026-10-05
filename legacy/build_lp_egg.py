"""Lowpoly: pojemnik na jajko niespodzianke 44 x 68 (miseczka + czapka z gniazdami + czapki z uszami krotkimi / dlugimi).
 lp_jajko_miseczka.stl, lp_jajko_czapka_gniazda.stl, lp_jajko_czapka_uszy.stl, lp_jajko_czapka_uszy_dlugie.stl"""
import sys, time, pickle
import numpy as np
sys.path.insert(0, "/home/claude/linia")
from lp_parts import *

T0 = time.time()
P = pickle.load(open(OUT + "/_lp_frames.pkl", "rb"))
FRe, L_SHORT = P["FRe"], P["L_SHORT"]
L_LONG = 42.0

cup_out, cap_out = egg_outer_cup(), egg_outer_cap()
cav_cup = cavity_cup()
bore, cav_body = cavity_cap()

cup = diff(union(cup_out, egg_lip()), cav_cup)
save_lp(cup, "lp_jajko_miseczka.stl", upright=True, note="otworem do gory")

cap_core = diff(cap_out, bore, cav_body)
sockets = [to_global(socket_solid(), FRe[s]) for s in (+1, -1)]
cap_sock = diff(cap_core, *sockets)
save_lp(cap_sock, "lp_jajko_czapka_gniazda.stl", upright=True, note="otworem do dolu (brzeg na stole), gniazda na uszy")


def cap_with(leaf, nm, note):
    m = diff(union(cap_out, *[to_global(leaf, FRe[s]) for s in (+1, -1)]), bore, cav_body)
    save_lp(m, nm, upright=True, note=note)
    return m


cap_ears = cap_with(ear_leaf(L_SHORT, -4.5), "lp_jajko_czapka_uszy.stl", "otworem do dolu; uszy przytopione")
cap_long = cap_with(ear_leaf(L_LONG, -4.5), "lp_jajko_czapka_uszy_dlugie.stl", "otworem do dolu; dlugie uszy przytopione")
print("wierzch: krotkie", round(cap_ears.bounds[1][2], 2), "dlugie", round(cap_long.bounds[1][2], 2))

pickle.dump(dict(cup=cup, cap_sock=cap_sock, cap_ears=cap_ears, cap_long=cap_long, cav_cup=cav_cup, cav_body=cav_body, bore=bore,
                 cup_out=cup_out, cap_out=cap_out), open(OUT + "/_lp_egg.pkl", "wb"))
print(f"czas {time.time() - T0:.0f} s")
