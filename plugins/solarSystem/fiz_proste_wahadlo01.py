import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# --- parametry wahadła ---
g = 9.81
DT = 0.005                 # krok czasu
ANG_DAMP = 0.05            # tłumienie kątowe (małe, żeby ładnie się bujało)

# rozmiar klocka (połowy boków)
w = 1.2                    # pół-szerokość (długi bok)
h = 0.3                    # pół-wysokość (krótki bok)
rho = 500.0                # "gęstość" (masa = rho * pole)
anchor = np.array([0.0, 9.0])   # punkt zawieszenia w świecie (x,y)

# masa i moment bezwładności względem przegubu (koniec klocka, środek boku)
area = (2*w)*(2*h)
m = rho * area
I_cm = (1/12)*m*((2*w)**2 + (2*h)**2)  # względem środka
I_pivot = I_cm + m*(w**2)              # tw. Steiner’a: o oś przez lewy koniec, wzdłuż krótkiego boku

# stan początkowy
theta0_deg = 15.0          # odchylenie początkowe (stopnie, dodatnie = lekko "do góry" na prawo)
theta = np.deg2rad(theta0_deg)
omega = 0.0

def R(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s], [s, c]])

def box_corners(center, angle):
    """Wierzchołki prostokąta (4x2) dla matplotlib.Polygon."""
    rot = R(angle)
    c = np.array([[ w,  h],
                  [-w,  h],
                  [-w, -h],
                  [ w, -h]])
    return center + c @ rot.T

# przygotowanie rysunku
fig, ax = plt.subplots(figsize=(7,7))
ax.set_aspect('equal')
ax.set_xlim(-6, 6)
ax.set_ylim(0, 10)
ax.set_title("Proste wahadło: klocek na przegubie")

# grafika: klocek i punkt zawieszenia
poly = plt.Polygon(np.zeros((4,2)), fc='C0', ec='k')
ax.add_patch(poly)
(anchor_dot,) = ax.plot([anchor[0]], [anchor[1]], 'ko')

# pomocnicza "cięciwa" od zawiasu do środka masy (ładniej widać ruch)
(chord,) = ax.plot([], [], 'k-', lw=1, alpha=0.4)

def init():
    # ustawienie początkowej pozycji środka: anchor + R(theta) @ (w,0)
    center = anchor + R(theta) @ np.array([w, 0.0])
    poly.set_xy(box_corners(center, theta))
    chord.set_data([anchor[0], center[0]], [anchor[1], center[1]])
    return poly, chord, anchor_dot

def update(_):
    global theta, omega

    # --- dynamika wahadła sztywnego pręta (prostokąt) o długości w do środka masy ---
    # wektor od przegubu do środka masy w lokalnych współrzędnych to (w, 0)
    # w świecie: r_c = R(theta) @ (w, 0)
    # moment grawitacyjny: tau = (r_c x F_g)_z = -m * g * (r_c.x)
    r_c_x = w * np.cos(theta)
    tau = -m * g * r_c_x

    # równanie ruchu: I * dω/dt = tau - c*ω
    domega = (tau / I_pivot) - ANG_DAMP * omega

    # pół-implicytna Eulera (stabilniejsza): najpierw ω, potem θ
    omega += domega * DT
    theta += omega * DT

    # aktualizacja geometrii
    center = anchor + R(theta) @ np.array([w, 0.0])
    poly.set_xy(box_corners(center, theta))
    chord.set_data([anchor[0], center[0]], [anchor[1], center[1]])

    return poly, chord, anchor_dot

anim = FuncAnimation(fig, update, init_func=init, interval=16, blit=False)
plt.show()
