import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

DT = 0.01
g = 9.81

def R(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c,-s],[s,c]])

class Segment:
    def __init__(self, l, w, m, theta_deg, color):
        self.l = l
        self.w = w
        self.m = m
        self.theta = np.deg2rad(theta_deg)
        self.omega = 0.0
        self.color = color
        I_cm = (1/12)*m*((2*l)**2 + (2*w)**2)
        self.I = I_cm + m*(l**2)

    def corners(self, anchor):
        center = anchor + R(self.theta) @ np.array([self.l, 0])
        rot = R(self.theta)
        c = np.array([[ self.l, self.w],
                      [-self.l, self.w],
                      [-self.l,-self.w],
                      [ self.l,-self.w]])
        return center + c @ rot.T

class Chain:
    def __init__(self, anchor, segments):
        self.anchor = np.array(anchor,float)
        self.segments = segments

    def fk(self):
        pts = [self.anchor]
        for s in self.segments:
            pts.append(pts[-1] + R(s.theta) @ np.array([2*s.l,0]))
        return pts

def step(chain):
    for s in chain.segments:
        tau = -s.m * g * s.l * np.cos(s.theta)
        s.omega += (tau / s.I) * DT
        s.omega *= 0.998
        s.theta += s.omega * DT

def run():
    chain = Chain([0,9], [
        Segment(1.,0.1, 3.0,  45, 'C0'),
        Segment(1.,0.1, 5.0, -30, 'C1'),
        Segment(1.,0.1, 7.0,  30, 'C2')
    ])

    fig, ax = plt.subplots(figsize=(7,7))
    ax.set_xlim(-6,6)
    ax.set_ylim(0,10)
    ax.set_aspect('equal')

    polys = []
    for s in chain.segments:
        poly = plt.Polygon(np.zeros((4,2)), fc=s.color, ec='k')
        ax.add_patch(poly)
        polys.append(poly)

    def update(_):
        step(chain)
        pts = chain.fk()
        for s, poly, anchor in zip(chain.segments, polys, pts):
            poly.set_xy(s.corners(anchor))
        return polys

    anim = FuncAnimation(fig, update, interval=10, blit=True)
    plt.show()

run()
