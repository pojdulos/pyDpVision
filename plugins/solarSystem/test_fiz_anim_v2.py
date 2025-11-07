import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

G = 6.67430e-11

# -----------------------------------------------------
# Klasa opisująca ciało niebieskie
# -----------------------------------------------------
class Body:
	def __init__(self, name, mass, position, velocity, color='white', size=4):
		self.name = name
		self.mass = mass
		self.r = np.array(position, dtype=float)
		self.v = np.array(velocity, dtype=float)
		self.color = color
		self.size = size
		self.trail = []  # historia pozycji (do rysowania ścieżki)

# -----------------------------------------------------
# Klasa systemu planetarnego
# -----------------------------------------------------
class SolarSystem:
	def __init__(self, dt=3600):
		self.bodies = []
		self.dt = dt

	def stabilize_barycenter(self):
		total_mass = sum(b.mass for b in self.bodies)
		v_cm = sum(b.mass * b.v for b in self.bodies) / total_mass
		for b in self.bodies:
			b.v -= v_cm

	def add_body(self, name, mass, r, v, color='white', size=4):
		self.bodies.append(Body(name, mass, r, v, color, size))

	def compute_accelerations(self):
		n = len(self.bodies)
		a = [np.zeros(3) for _ in range(n)]
		for i in range(n):
			for j in range(n):
				if i == j:
					continue
				diff = self.bodies[j].r - self.bodies[i].r
				dist3 = np.linalg.norm(diff)**3 + 1e-9
				a[i] += G * self.bodies[j].mass * diff / dist3
		return a

	def step(self):
		dt = self.dt
		a = self.compute_accelerations()
		new_acc = []
		# velocity-verlet integrator
		for i, body in enumerate(self.bodies):
			r_new = body.r + body.v * dt + 0.5 * a[i] * dt**2
			body.trail.append(body.r.copy())
			new_acc.append(r_new)
		# now recompute accelerations using new positions
		for i, body in enumerate(self.bodies):
			body.r = new_acc[i]
		a2 = self.compute_accelerations()
		for i, body in enumerate(self.bodies):
			body.v += 0.5 * (a[i] + a2[i]) * dt

# -----------------------------------------------------
# Inicjalizacja systemu
# -----------------------------------------------------
system = SolarSystem(dt=3600*3)

system.add_body("Sun",   1.989e30, [0, 0, 0], [0, 0, 0], color='yellow', size=10)
system.add_body("Earth", 5.972e24, [1.496e11, 0, 0], [0, 29780, 0], color='blue', size=5)
system.add_body("Moon",  7.348e22, [1.496e11+3.84e8, 0, 0], [0, 29780+1022, 0], color='gray', size=3)
# możesz dodać np. Marsa:
system.add_body("Mars", 6.39e23, [2.279e11, 0, 0], [0, 24070, 0], color='red', size=4)
system.add_body("Jupiter", 1.898e27, [7.78e11, 0, 0], [0, 13000, 0], color='orange', size=7)
system.add_body("Retro", 5e24, [1.2e11, 0, 0], [0, -29000, 0], color='orange')

system.add_body("Asteroid", 1e15, [1.0e11, 1.0e11, 0], [-20000, 10000, 5000], color='white', size=2)

system.stabilize_barycenter()

# -----------------------------------------------------
# Animacja
# -----------------------------------------------------
from mpl_toolkits.mplot3d import Axes3D
fig = plt.figure(figsize=(8, 8))
ax = fig.add_subplot(111, projection='3d')
ax.set_aspect('equal')
ax.set_facecolor('black')

artists = {}
for b in system.bodies:
	(p,) = ax.plot([], [], 'o', color=b.color, markersize=b.size)
	(trail,) = ax.plot([], [], '-', color=b.color, lw=0.6, alpha=0.5)
	artists[b.name] = (p, trail)

ax.set_xlim(-1e12, 1e12)
ax.set_ylim(-1e12, 1e12)
ax.set_zlim(-1e12, 1e12)

def init():
	for b in system.bodies:
		artists[b.name][0].set_data([], [])
		artists[b.name][1].set_data([], [])
	return sum(artists.values(), ())

def update(frame):
	system.step()
	for b in system.bodies:
		# ustaw pozycję punktu 3D
		artists[b.name][0].set_data_3d([b.r[0]], [b.r[1]], [b.r[2]])
		
		# aktualizuj ślad
		trail = np.array(b.trail[-1000:])
		if len(trail) > 0:
			artists[b.name][1].set_data_3d(trail[:, 0], trail[:, 1], trail[:, 2])

	# opcjonalny obrót kamery (dla efektu)
	#ax.view_init(elev=25, azim=(frame / 2) % 360)
	return sum(artists.values(), ())

ani = FuncAnimation(fig, update, frames=1500, init_func=init, interval=1, blit=False)
plt.show()
