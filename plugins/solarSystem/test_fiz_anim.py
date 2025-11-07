import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

G = 6.67430e-11

m_sun   = 1.989e30
m_earth = 5.972e24
m_moon  = 7.348e22

# --- Pozycje początkowe ---
r_sun0   = np.array([0.0, 0.0])
r_earth0 = np.array([1.496e11, 0.0])
r_moon0  = r_earth0 + np.array([3.844e8, 0.0])

# --- Prędkości początkowe ---
#v_earth0 = np.array([0.0, 29_780.0])  # ruch orbitalny wokół Słońca
v_earth0 = np.array([0.0, 8000.0])  # ruch orbitalny wokół Słońca
#v_moon_rel = np.array([0.0, 1022.0])  # prędkość wokół Ziemi
v_moon_rel = np.array([0.0, 0.0])  # prędkość wokół Ziemi

# Korekta: dodaj ruch Ziemi, ale odejmij drobną poprawkę za środek masy
v_moon0  = v_earth0 + v_moon_rel * (m_earth / (m_earth + m_moon))
v_earth0 = v_earth0 - v_moon_rel * (m_moon / (m_earth + m_moon))

r = np.array([r_sun0, r_earth0, r_moon0])
v = np.array([[0,0], v_earth0, v_moon0])
m = np.array([m_sun, m_earth, m_moon])

dt = 3600 * 1  # 6 godzin
steps = 60000

def compute_acc(r, m):
	n = len(r)
	a = np.zeros_like(r)
	for i in range(n):
		for j in range(n):
			if i == j:
				continue
			diff = r[j] - r[i]
			dist3 = np.linalg.norm(diff)**3 + 1e-9
			a[i] += G * m[j] * diff / dist3
	return a

# Inicjalizacja
a = compute_acc(r, m)
positions = []

for t in range(steps):
	positions.append(r.copy())
	r_new = r + v * dt + 0.5 * a * dt**2
	a_new = compute_acc(r_new, m)
	v_new = v + 0.5 * (a + a_new) * dt
	r, v, a = r_new, v_new, a_new

positions = np.array(positions)

# --- ANIMACJA ---
fig, ax = plt.subplots(figsize=(8,8))
ax.set_aspect('equal')
ax.set_facecolor('black')
ax.set_xlim(-2e11, 2e11)
ax.set_ylim(-2e11, 2e11)

sun, = ax.plot([], [], 'yo', markersize=12)
earth, = ax.plot([], [], 'bo', markersize=6)
moon, = ax.plot([], [], 'o', color='lightgray', markersize=5)

trail, = ax.plot([], [], 'b-', lw=0.5)

def init():
	sun.set_data([], [])
	earth.set_data([], [])
	moon.set_data([], [])
	trail.set_data([], [])
	return sun, earth, moon, trail

def update(frame):
	r_sun, r_earth, r_moon = positions[frame]
	sun.set_data([r_sun[0]], [r_sun[1]])
	earth.set_data([r_earth[0]], [r_earth[1]])
	moon.set_data([r_moon[0]], [r_moon[1]])
	trail.set_data(positions[:frame,1,0], positions[:frame,1,1])

	# center = r_earth
	# ax.set_xlim(center[0] - 5e9, center[0] + 5e9)
	# ax.set_ylim(center[1] - 5e9, center[1] + 5e9)

	return sun, earth, moon, trail

ani = FuncAnimation(fig, update, frames=len(positions), init_func=init,
					interval=1, blit=True, repeat=True)

plt.title('Symulacja Słońce–Ziemia–Księżyc')
plt.show()
