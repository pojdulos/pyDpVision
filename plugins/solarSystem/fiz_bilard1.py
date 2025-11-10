import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

DT = 1e-4
SUBSTEPS = 8
GRAV = np.array([0.0, -9.81])
BOX = np.array([(-5.0, 5.0), (0.0, 10.0)])

E = 0.9     # współczynnik restytucji
MU = 0.05   # tarcie Coulomba

RNG = np.random.default_rng(2)

class Bodies:
	def __init__(self, N):
		self.N = N
		self.pos = np.zeros((N,2))
		self.vel = np.zeros((N,2))
		self.ang = np.zeros(N)
		self.ang_vel = np.zeros(N)
		self.rad = np.zeros(N)
		self.mass = np.zeros(N)
		self.inertia = np.zeros(N)
		self.color = []

	def add_disk(self, pos, vel, r, rho=1000.0, color='tab:blue'):
		i = np.nonzero(self.mass==0)[0][0]
		self.pos[i]=pos
		self.vel[i]=vel
		self.rad[i]=r
		A = np.pi*r*r
		m = rho*A
		self.mass[i]=m
		self.inertia[i]=0.5*m*r*r
		self.color.append(color)

def make_pack(N=15):
	B = Bodies(N)
	for _ in range(N):
		r = RNG.uniform(0.25, 0.45)
		x = RNG.uniform(BOX[0,0]+r, BOX[0,1]-r)
		y = RNG.uniform(BOX[1,0]+r, BOX[1,1]-r)
		v = RNG.normal(0,0.8,2)
		col = f"C{RNG.integers(0,10)}"
		B.add_disk((x,y), v, r, rho=900, color=col)
	return B

def step_impulse(B: Bodies):
	N=B.N
	# grawitacja
	B.vel += GRAV * DT

	# detekcja i reakcja na zderzenia (dysk–dysk)
	for i in range(N):
		for j in range(i+1,N):
			rij = B.pos[j]-B.pos[i]
			dist = np.linalg.norm(rij)
			rsum = B.rad[i]+B.rad[j]
			if dist >= rsum:
				continue
			n = rij/dist
			ti = np.array([-n[1], n[0]])
			# punkt kontaktu – prędkości w punkcie
			vpi = B.vel[i] + B.ang_vel[i]*B.rad[i]*ti
			vpj = B.vel[j] - B.ang_vel[j]*B.rad[j]*ti
			vrel = vpj - vpi

			# składniki
			vn = np.dot(vrel,n)
			vt = np.dot(vrel,ti)

			if vn > 0:
				continue

			denom = (1/B.mass[i] + 1/B.mass[j] +
					(B.rad[i]**2)/B.inertia[i] +
					(B.rad[j]**2)/B.inertia[j])

			jn = -(1+E)*vn/denom
			# tarcie
			jt = -vt/denom
			jt = np.clip(jt, -MU*abs(jn), MU*abs(jn))

			impulse = jn*n + jt*ti

			# translacja
			B.vel[i] -= impulse/B.mass[i]
			B.vel[j] += impulse/B.mass[j]

			# rotacja
			B.ang_vel[i] -= (jt*B.rad[i])/B.inertia[i]
			B.ang_vel[j] += (jt*B.rad[j])/B.inertia[j]

			# minimalne „wypchnięcie” (separacja)
			# corr = 0.5*(rsum-dist)
			# B.pos[i] -= corr*n
			# B.pos[j] += corr*n

			penetration = rsum - dist
			correction = 0.8 * penetration   # współczynnik 0.2–0.8
			B.pos[i] -= correction * n * (1 / B.mass[i]) / (1 / B.mass[i] + 1 / B.mass[j])
			B.pos[j] += correction * n * (1 / B.mass[j]) / (1 / B.mass[i] + 1 / B.mass[j])


	# zderzenia ze ścianami
	for i in range(N):
		x,y = B.pos[i]
		vx,vy = B.vel[i]
		r = B.rad[i]
		if x-r<BOX[0,0]: B.pos[i][0]=BOX[0,0]+r; B.vel[i][0]*=-E
		if x+r>BOX[0,1]: B.pos[i][0]=BOX[0,1]-r; B.vel[i][0]*=-E
		if y-r<BOX[1,0]: B.pos[i][1]=BOX[1,0]+r; B.vel[i][1]*=-E
		if y+r>BOX[1,1]: B.pos[i][1]=BOX[1,1]-r; B.vel[i][1]*=-E

	# aktualizacja pozycji
	B.pos += B.vel*DT
	B.ang += B.ang_vel*DT


def run():
	B = make_pack(5)
	fig,ax = plt.subplots(figsize=(7,7))
	ax.set_aspect('equal')
	ax.set_xlim(*BOX[0])
	ax.set_ylim(*BOX[1])

	circles=[]
	for i in range(B.N):
		c=plt.Circle(B.pos[i], B.rad[i], fc=B.color[i], ec='k')
		ax.add_patch(c)
		circles.append(c)

	def init():
		for i in range(B.N):
			circles[i].center = B.pos[i]
		return circles

	def update(frame):
		# wykonujemy kilka kroków fizyki na każdą klatkę
		for _ in range(SUBSTEPS):
			step_impulse(B)

		# aktualizujemy pozycje obiektów rysunkowych
		for i in range(B.N):
			circles[i].center = B.pos[i]

		return circles

	anim = FuncAnimation(fig, update, init_func=init, interval=1, blit=True)

	plt.show()

if __name__=="__main__":
	run()
