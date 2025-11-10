import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# ===== USTAWIENIA =====
DT = 0.002
G = 9.81
DAMP_JOINT = 0.02   # lepkość w przegubach (Nm*s/rad), dodawana jako -D*qdot
ANCHOR = np.array([0.0, 9.0])  # punkt zakotwienia (x,y)
AX = [(-6, 6), (0, 10)]        # granice wykresu

# ===== POMOCNICZE =====
def R(a):
	c, s = np.cos(a), np.sin(a)
	return np.array([[c, -s],[s, c]])

def z_perp(v):  # ẑ × v (obrót o +90°)
	return np.array([-v[1], v[0]])

# ===== MODEL ŁAŃCUCHA =====
class Chain:
	"""
	Planarny łańcuch n łączników z przegubami obrotowymi.
	Każdy segment i ma:
	- pełną długość Li (render), środek masy w odległości li = Li/2 od przegubu
	- szerokość (render) Wi (nie wpływa na dynamikę)
	- masę mi
	- moment bezwładności wokół COM: Ii (dla pręta 2li x Wi: Icm ~ (1/12) m*( (2li)^2 + Wi^2 ))
	"""
	def __init__(self, lengths, widths, masses, I_com=None, theta_deg=None, colors=None):
		self.n = len(lengths)
		self.L = np.asarray(lengths, float)              # pełne długości render
		self.l = self.L * 0.5                            # od przegubu do COM
		self.W = np.asarray(widths, float)               # szerokości (render)
		self.m = np.asarray(masses, float)
		if I_com is None:
			# inercja wokół COM dla prostokąta 2l x W
			I_com = (1.0/12.0) * self.m * ((2*self.l)**2 + (self.W)**2)
		self.Ic = np.asarray(I_com, float)

		self.q = np.zeros(self.n) if theta_deg is None else np.deg2rad(theta_deg).astype(float)

		self.qd = np.zeros(self.n)
		self.colors = colors or [f"C{i%10}" for i in range(self.n)]

	# --- Kinematyka przód: pozycje przegubów i COM-ów ---
	def joints_world(self, anchor=ANCHOR):
		pts = [np.array(anchor, float)]
		ang = 0.0
		for i in range(self.n):
			ang += self.q[i]
			pts.append(pts[-1] + R(ang) @ np.array([self.L[i], 0.0]))
		return pts  # len = n+1 (J0..Jn)

	def com_world(self, anchor=ANCHOR):
		pts = [np.array(anchor, float)]
		ang = 0.0
		res = []
		for i in range(self.n):
			base = pts[-1]
			ang += self.q[i]
			com = base + R(ang) @ np.array([self.l[i], 0.0])
			res.append(com)
			pts.append(base + R(ang) @ np.array([self.L[i], 0.0]))
		return res  # len = n

	# --- Jacobiany prędkości liniowej COM-ów (2 x n) oraz kątowy (1 x n) ---
	def jacobians(self, anchor=ANCHOR):
		Jv_list = []
		Jw_list = []
		joints = self.joints_world(anchor)
		coms   = self.com_world(anchor)
		for i in range(self.n):
			Jv = np.zeros((2, self.n))
			# pozycja COM i-tego
			p_ci = coms[i]
			# dla każdego przegubu j ≤ i, kolumna to ẑ × (p_ci - p_j)
			for j in range(i+1):
				r = p_ci - joints[j]
				Jv[:, j] = z_perp(r)
			# Jacobian kątowy (planarnie: z prędkością kątową ω działa 1 dla każdej osi do i-tej)
			Jw = np.zeros((1, self.n))
			Jw[0, :i+1] = 1.0
			Jv_list.append(Jv)
			Jw_list.append(Jw)
		return Jv_list, Jw_list

	# --- Macierz masy M(q) ---
	def mass_matrix(self, anchor=ANCHOR):
		Jv_list, Jw_list = self.jacobians(anchor)
		M = np.zeros((self.n, self.n))
		for i in range(self.n):
			m_i = self.m[i]
			Jv = Jv_list[i]
			Jw = Jw_list[i]
			M += m_i * (Jv.T @ Jv) + self.Ic[i] * (Jw.T @ Jw)
		return M

	# --- Siła grawitacji w uogólnionych współrzędnych (G(q)) ---
	def gravity(self, anchor=ANCHOR):
		Jv_list, _ = self.jacobians(anchor)
		g_vec = np.array([0.0, -G])
		Gq = np.zeros(self.n)
		for i in range(self.n):
			Gq += (Jv_list[i].T @ (self.m[i] * g_vec))
		return Gq

	# --- Człon C(q,qd)qd z numerycznych pochodnych Christoffela ---
	def coriolis_qdot(self, anchor=ANCHOR, eps=1e-6):
		# C(q,qd)qd = b(q,qd), gdzie b_k = 0.5 * sum_{i,j} (dM_kj/dq_i + dM_ki/dq_j - dM_ij/dq_k) * qd_i * qd_j
		q = self.q
		qd = self.qd
		M = self.mass_matrix(anchor)
		n = self.n
		# numeryczne pochodne M względem q_k
		dM_dq = np.zeros((n, n, n))
		for k in range(n):
			q_save = q[k]
			self.q[k] = q_save + eps
			Mp = self.mass_matrix(anchor)
			self.q[k] = q_save - eps
			Mm = self.mass_matrix(anchor)
			self.q[k] = q_save
			dM_dq[k] = (Mp - Mm) / (2*eps)

		b = np.zeros(n)
		for k in range(n):
			acc = 0.0
			for i in range(n):
				for j in range(n):
					Gamma = 0.5 * ( dM_dq[i,k,j] + dM_dq[j,k,i] - dM_dq[k,i,j] )
					acc += Gamma * qd[i] * qd[j]
			b[k] = acc
		return b

# ===== RENDER =====
def draw_boxes(ax, chain: Chain, patches, anchor=ANCHOR):
	joints = chain.joints_world(anchor)
	ang = 0.0
	base = np.array(anchor, float)
	for i in range(chain.n):
		ang += chain.q[i]
		# środek prostokąta
		center = base + R(ang) @ np.array([chain.L[i]*0.5, 0.0])
		# wierzchołki prostokąta 2l x W
		rot = R(ang)
		w = chain.L[i]*0.5
		h = chain.W[i]*0.5
		local = np.array([[ w,  h],
						[-w,  h],
						[-w, -h],
						[ w, -h]])
		# pts = center + local @ rot.T
		# patches[i].set_xy(pts)
		pts = center + local @ rot.T
		pts[:,1] = 2*ANCHOR[1] - pts[:,1]   # odbicie lustrzane względem poziomej osi anchor.y
		patches[i].set_xy(pts)

		base = joints[i+1]

# ===== SYMULATOR =====
def simulate():
	# Przykład: 3 segmenty (łatwo zmienić na N)
	N = 3
	lengths = [2.0, 2.0, 2.0]     # pełne długości
	widths  = [0.3, 0.3, 0.3]
	masses  = [5.0, 5.0, 5.0]
	thetas  = [15.0, -10.0, 20.0]  # kąty startowe (deg)

	chain = Chain(lengths, widths, masses, theta_deg=thetas)

	fig, ax = plt.subplots(figsize=(7,7))
	ax.set_aspect('equal')
	ax.set_xlim(*AX[0]); ax.set_ylim(*AX[1])
	ax.plot([ANCHOR[0]], [ANCHOR[1]], 'ko', ms=5)

	patches = []
	for i in range(chain.n):
		poly = plt.Polygon(np.zeros((4,2)), fc=chain.colors[i], ec='k')
		ax.add_patch(poly)
		patches.append(poly)

	# ---------- Równania ruchu: M(q) qdd = tau - C(q,qd)qd - G(q) - D*qd ----------
	D = DAMP_JOINT * np.eye(chain.n)  # lepkość w przegubach
	tau = np.zeros(chain.n)           # brak napędów (pasywnie)

	def step():
		# składniki dynamiki
		M  = chain.mass_matrix(ANCHOR)
		bC = chain.coriolis_qdot(ANCHOR)         # C(q,qd) qd
		Gq = chain.gravity(ANCHOR)               # G(q)

		rhs = tau - bC - Gq - D @ chain.qd
		# rozwiąż qdd
		qdd = np.linalg.solve(M, rhs)

		# integracja pół-implicytna
		chain.qd += qdd * DT
		chain.q  += chain.qd * DT

	def update(_):
		# kilka substepów dla stabilności
		for _ in range(3):
			step()
		draw_boxes(ax, chain, patches, ANCHOR)
		return patches

	anim = FuncAnimation(fig, update, interval=16, blit=False)
	plt.show()

if __name__ == "__main__":
	simulate()
