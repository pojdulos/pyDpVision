import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


def anim_2d(system, scale):
	pass
	# -----------------------------------------------------
	# Animacja
	# -----------------------------------------------------
	fig, ax = plt.subplots(figsize=(16, 16))
	ax.set_aspect('equal')
	ax.set_facecolor('black')

	artists = {}
	for b in system.bodies:
		(p,) = ax.plot([], [], 'o', color=b.color, markersize=b.size)
		(trail,) = ax.plot([], [], '-', color=b.color, lw=0.6, alpha=0.5)
		artists[b.name] = (p, trail)

	ax.set_xlim(-scale, scale)
	ax.set_ylim(-scale, scale)

	def init():
		for b in system.bodies:
			artists[b.name][0].set_data([], [])
			artists[b.name][1].set_data([], [])
		return sum(artists.values(), ())

	def update(frame):
		system.step()
		print(f"dt = {system.dt:.3f}, total energy = {system.total_energy():.6e} J")
		for b in system.bodies:
			artists[b.name][0].set_data([b.r[0]], [b.r[1]])
			trail = np.array(b.trail[-1000:])  # ogranicz długość ścieżki
			if len(trail) > 0:
				artists[b.name][1].set_data(trail[:, 0], trail[:, 1])
		return sum(artists.values(), ())

	ani = FuncAnimation(fig, update, frames=1500, init_func=init, interval=1, blit=True)
	plt.show()

def anim_3d(system, scale):
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

	ax.set_xlim(-scale, scale)
	ax.set_ylim(-scale, scale)
	ax.set_zlim(-scale, scale)

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

	ani = FuncAnimation(fig, update, frames=1500, init_func=init, interval=1, blit=True)
	plt.show()






G = 6.67430e-11

# -----------------------------------------------------
# Klasa opisująca ciało niebieskie
# -----------------------------------------------------
class Body:
	def __init__(self, name, mass, position, velocity, color='white', size=4):
		self.name = name
		self.mass = mass
		self.mu = G * mass
		self.r = np.array(position, dtype=float)
		self.v = np.array(velocity, dtype=float)
		self.color = color
		self.size = size
		self.trail = []  # historia pozycji (do rysowania ścieżki)

# -----------------------------------------------------
# Klasa systemu planetarnego
# -----------------------------------------------------
class SystemSimulator:
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

	def total_energy(self):
		KE = sum(0.5*b.mass*np.dot(b.v,b.v) for b in self.bodies)
		PE = 0.0
		for i in range(len(self.bodies)):
			for j in range(i+1, len(self.bodies)):
				r = np.linalg.norm(self.bodies[i].r - self.bodies[j].r)
				PE -= G * self.bodies[i].mass * self.bodies[j].mass / r
		return KE + PE

	def compute_accelerations(self):
		n = len(self.bodies)
		a = [np.zeros(3) for _ in range(n)]
		for i in range(n):
			for j in range(n):
				if i == j:
					continue
				diff = self.bodies[j].r - self.bodies[i].r
				dist3 = np.linalg.norm(diff)**3 + 1e-9
				a[i] += self.bodies[j].mu * diff / dist3
		return a

	def step(self):
		# --- oblicz aktualne przyspieszenia ---
		a = self.compute_accelerations()

		# --- adaptacyjny krok czasowy ---
		max_a = max(np.linalg.norm(ai) for ai in a)
		if max_a > 0:
			# typowy czas reakcji dynamiki układu (czas charakterystyczny)
			t_dyn = np.sqrt(1.0 / max_a)

			# współczynnik bezpieczeństwa
			eta = 100.0   # im większy, tym dłuższe kroki (skalowanie dla SI)
			dt_new = eta * t_dyn
		else:
			dt_new = self.dt

		# ograniczenie zmian (żeby dt nie skakał gwałtownie)
		dt_new = np.clip(dt_new, self.dt * 0.5, self.dt * 1.5)

		# fizyczne granice kroków czasowych (0.001 s–50 s)
		self.dt = float(np.clip(dt_new, 0.001, 3600.0))

		# --- velocity-verlet integrator ---
		dt = self.dt
		new_r = []
		for i, body in enumerate(self.bodies):
			r_new = body.r + body.v * dt + 0.5 * a[i] * dt**2
			body.trail.append(body.r.copy())
			new_r.append(r_new)

		for i, body in enumerate(self.bodies):
			body.r = new_r[i]

		a2 = self.compute_accelerations()
		for i, body in enumerate(self.bodies):
			body.v += 0.5 * (a[i] + a2[i]) * dt

def pulsar_system():
	system = SystemSimulator(dt=50)  # krok 10 sekund!

	M_A = 1.989e30 # mniej wiecej masa Słońca
	M_B = 1.989e30 * 0.8 # nieco mniejsza masa
	r_sep = 1e9  # 1 mln km
	v_A = np.sqrt(G * M_A / (4 * r_sep))  # ~1.82e5 m/s dla masy równej masie Słońca
	v_B = np.sqrt(G * M_B / (4 * r_sep))  # odpowiednio dla masy Pulsara B

	system.add_body("Pulsar A", M_A, [-0.5*r_sep, 0, 0], [0,  v_A, 0], color='yellow', size=12)
	system.add_body("Pulsar B", M_B, [ 0.5*r_sep, 0, 0], [0, -v_B, 0], color='red', size=12)

	system.add_body("Earth", 5.972e24, [2e9, 0, 0], [-100000, 400000, 0], color='white', size=8)

	system.stabilize_barycenter()

	view_size = 3.5e9
	return system, view_size

def solar_system():
	system = SystemSimulator(dt=3600*3)
	system.add_body("Sun",   1.989e30, [0, 0, 0], [0, 0, 0], color='yellow', size=10)
	system.add_body("Earth", 5.972e24, [1.496e11, 0, 0], [0, 29780, 0], color='blue', size=5)
	#system.add_body("Moon",  7.348e22, [1.496e11+3.84e8, 0, 0], [0, 29780+1022, 0], color='gray', size=3)
	#system.add_body("Mars", 6.39e23, [2.279e11, 0, 0], [0, 24070, 0], color='red', size=4)
	# system.add_body("Jupiter", 1.898e27, [7.78e11, 0, 0], [0, 13000, 0], color='orange', size=7)
	# system.add_body("Retro", 5e24, [1.2e11, 0, 0], [0, -29000, 0], color='orange')

	#system.add_body("Asteroid", 1e15, [1.0e11, 1.0e11, 0], [-20000, 10000, 5000], color='white', size=2)

	system.stabilize_barycenter()

	view_size = 2.5e11
	return system, view_size


def rocket_system():
    system = SystemSimulator(dt=10)
    M_earth = 5.972e24
    M_rocket = 7.348e6
    R_earth = 6.371e6
    altitude = 1000e3

    r = R_earth + altitude
    v = np.sqrt(G * M_earth / r)  # prędkość orbitalna

    # Ziemia w środku
    system.add_body("Earth", M_earth, [0, 0, 0], [0, 0, 0], color='blue', size=50)

    # Rakieta: pozycja w dół od środka, prędkość w bok
    pos = [0, -r, 0]
    vel = [v, 0, 0]

    system.add_body("Rocket", M_rocket, pos, vel, color='gray', size=10)

    return system, 2.5e7



#system, scale = solar_system()
system, scale = pulsar_system()
anim_2d(system, scale)

