import numpy as np
from math import cos, sin, radians

def A_classical(a, alpha_deg, d, theta_deg):
    th = radians(theta_deg); al = radians(alpha_deg)
    cth, sth = cos(th), sin(th)
    cal, sal = cos(al), sin(al)
    A = np.array([
        [ cth, -sth*cal,  sth*sal, a*cth ],
        [ sth,  cth*cal, -cth*sal, a*sth ],
        [  0 ,     sal ,    cal  ,  d    ],
        [  0 ,     0   ,    0    ,  1    ],
    ], dtype=float)
    return A

def forward_kinematics(dh_params):
    # dh_params = [(a,alpha_deg,d,theta_deg), ...] od i=1..n
    T = np.eye(4)
    origins = [T[:3,3].copy()]
    for (a,alpha,d,theta) in dh_params:
        A = A_classical(a, alpha, d, theta)
        T = T @ A   # T = T_0_i
        origins.append(T[:3,3].copy())
    return origins, T

# Przykład:
dh = [(10, 45, 10, 90)]            # single link: a=10, alpha=45°, d=10, theta=0
origins, T_end = forward_kinematics(dh)
print("Origins:", origins)        # origin 0 i origin 1
print("End effector:", T_end[:3,3])
