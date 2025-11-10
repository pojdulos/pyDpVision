import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

DT = 1e-3
E = 0.8   # restytucja
MU = 0.2  # tarcie
GRAV = np.array([0, -9.81])
BOX = np.array([(-6, 6), (0, 10)])

def R(a):
    ca, sa = np.cos(a), np.sin(a)
    return np.array([[ca,-sa],[sa,ca]])

class Box:
    def __init__(self, pos, vel, ang, ang_vel, w, h, rho=500, color='C0'):
        self.pos = np.array(pos,float)
        self.vel = np.array(vel,float)
        self.ang = ang
        self.ang_vel = ang_vel
        self.w, self.h = w, h
        m = rho*(2*w)*(2*h)
        self.mass = m
        self.inertia = (1/12)*m*((2*w)**2 + (2*h)**2)
        self.color=color

    def corners(self):
        Rm = R(self.ang)
        c = np.array([[ self.w, self.h],
                      [-self.w, self.h],
                      [-self.w,-self.h],
                      [ self.w,-self.h]])
        return self.pos + c @ Rm.T

def project(points, axis):
    proj = points @ axis
    return proj.min(), proj.max()

def overlap(a1, a2, b1, b2):
    return min(a2, b2) - max(a1, b1)

def collide(A:Box, B:Box):
    # SAT axes = normals osi obu boxów
    axes = []
    R1 = R(A.ang); R2 = R(B.ang)
    axes.append(R1[:,0]); axes.append(R1[:,1])
    axes.append(R2[:,0]); axes.append(R2[:,1])

    pA = A.corners()
    pB = B.corners()

    min_overlap = 1e9
    best_axis = None

    for ax in axes:
        ax = ax/np.linalg.norm(ax)
        a1,a2 = project(pA,ax)
        b1,b2 = project(pB,ax)
        o = overlap(a1,a2,b1,b2)
        if o < 0:
            return None  # brak kolizji
        if o < min_overlap:
            min_overlap=o
            best_axis=ax

    # kierunek od A do B
    d = B.pos - A.pos
    if np.dot(d,best_axis) < 0:
        best_axis = -best_axis

    return best_axis, min_overlap

def apply_impulse(A,B,n,contact_point):
    ra = contact_point - A.pos
    rb = contact_point - B.pos
    vA = A.vel + A.ang_vel*np.array([-ra[1],ra[0]])
    vB = B.vel + B.ang_vel*np.array([-rb[1],rb[0]])
    vrel = vB - vA

    vn = np.dot(vrel,n)
    if vn > 0: return

    denom = (1/A.mass + 1/B.mass +
             (np.cross(ra,n)**2)/A.inertia +
             (np.cross(rb,n)**2)/B.inertia)

    jn = -(1+E)*vn/denom

    # tarcie
    t = np.array([-n[1],n[0]])
    vt = np.dot(vrel,t)
    jt = -vt/denom
    jt = np.clip(jt, -MU*abs(jn), MU*abs(jn))

    J = jn*n + jt*t

    A.vel -= J/A.mass
    B.vel += J/B.mass
    A.ang_vel -= np.cross(ra,J)/A.inertia
    B.ang_vel += np.cross(rb,J)/B.inertia

def step(boxes):
    # grawitacja
    for b in boxes: b.vel += GRAV*DT

    # kolizje box–box
    for i in range(len(boxes)):
        for j in range(i+1,len(boxes)):
            C = collide(boxes[i], boxes[j])
            if C is None: continue
            n, o = C
            cp = (boxes[i].pos+boxes[j].pos)/2
            apply_impulse(boxes[i],boxes[j],n,cp)

            # korekcja pozycji
            corr = 0.5*o*n
            boxes[i].pos -= corr
            boxes[j].pos += corr

    # kolizje ze ścianami (pełny kontakt: impuls + korekcja)
    for b in boxes:
        # Oś X – lewa
        if b.pos[0] - b.w < BOX[0,0]:
            n = np.array([1.0, 0.0])
            penetration = BOX[0,0] - (b.pos[0] - b.w)
            b.pos[0] += penetration  # korekcja
            # impuls: odbicie
            vn = np.dot(b.vel, n)
            if vn < 0:
                b.vel -= (1+E)*vn*n

        # Oś X – prawa
        if b.pos[0] + b.w > BOX[0,1]:
            n = np.array([-1.0, 0.0])
            penetration = (b.pos[0] + b.w) - BOX[0,1]
            b.pos[0] -= penetration
            vn = np.dot(b.vel, n)
            if vn < 0:
                b.vel -= (1+E)*vn*n

        # Oś Y – dno
        if b.pos[1] - b.h < BOX[1,0]:
            n = np.array([0.0, 1.0])
            penetration = BOX[1,0] - (b.pos[1] - b.h)
            b.pos[1] += penetration
            vn = np.dot(b.vel, n)
            if vn < 0:
                b.vel -= (1+E)*vn*n

        # Oś Y – sufit
        if b.pos[1] + b.h > BOX[1,1]:
            n = np.array([0.0, -1.0])
            penetration = (b.pos[1] + b.h) - BOX[1,1]
            b.pos[1] -= penetration
            vn = np.dot(b.vel, n)
            if vn < 0:
                b.vel -= (1+E)*vn*n

    # # kolizje ze ścianami
    # for b in boxes:
    #     if b.pos[0]-b.w < BOX[0,0]: b.pos[0]=BOX[0,0]+b.w; b.vel[0]*=-E
    #     if b.pos[0]+b.w > BOX[0,1]: b.pos[0]=BOX[0,1]-b.w; b.vel[0]*=-E
    #     if b.pos[1]-b.h < BOX[1,0]: b.pos[1]=BOX[1,0]+b.h; b.vel[1]*=-E
    #     if b.pos[1]+b.h > BOX[1,1]: b.pos[1]=BOX[1,1]-b.h; b.vel[1]*=-E

    for b in boxes:
        b.pos += b.vel*DT
        b.ang += b.ang_vel*DT

def run():
    boxes=[
        Box((0,8),(2,-1),0,0,1.0,0.4,color='C0'),
        Box((-2,6),(-1,0),0.4,0,1.0,0.4,color='C1'),
        Box((2,6),(0,0),-0.3,0,1.0,0.4,color='C2'),
    ]

    fig,ax=plt.subplots(figsize=(8,8))
    ax.set_aspect('equal')
    ax.set_xlim(*BOX[0])
    ax.set_ylim(*BOX[1])

    polys=[]
    for b in boxes:
        p = b.corners()
        poly = plt.Polygon(p, fc=b.color, ec='k')
        ax.add_patch(poly)
        polys.append(poly)

    def update(_):
        for _ in range(6): step(boxes)
        for i,b in enumerate(boxes):
            polys[i].set_xy(b.corners())
        return polys

    anim=FuncAnimation(fig,update,interval=16,blit=False)
    plt.show()

if __name__=="__main__":
    run()
