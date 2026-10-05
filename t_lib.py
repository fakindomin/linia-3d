import numpy as np, math, time
from lib import *
# test: ucho (liść) + czop
def ear_canvas(L=31.0):
    cv = Canvas(-9, 9, -4, L+2, res=0.1)
    pts = []
    n = 120
    bs = np.linspace(-3, L, n)
    def hw(b):
        u = b / L
        if u < 0.5:
            return 4.2 + 2.8*math.sin(math.pi/2 * max(u,0)/0.5)
        t = (u-0.5)/0.5
        return 7.0*(1-t**2.2)**(1/2.2)
    right = [(hw(b), b) for b in bs]
    left = [(-hw(b), b) for b in bs[::-1]]
    cv.poly(right+left)
    return cv
t=time.time()
cv = ear_canvas()
ring = Canvas(-9, 9, -4, 33, res=0.1)
# pierscien owalu
ring.ellipse(0,17,3.5,10.5,255); ring.ellipse(0,17,2.6,9.6,0)
fp = FlatPart(cv, EAR_T, w=1.0, k=1.5, ring_mask=ring.mask(), ring_h=RING_H)
def field(a,b,c):
    Fe = np.minimum(fp.F(a,b,c), b+3.0)
    Fp = peg_F(a,b,c)
    return np.maximum(Fe,Fp)
m = local_mesh(field, (-9,9), (-9,34), (-0.5,6.5), vox=0.2)
print(time.time()-t, m.extents, m.is_watertight, len(m.faces))
save(m, "_test_ucho.stl", upright=True)
