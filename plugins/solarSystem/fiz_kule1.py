import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# =========================
# Parametry globalne
# =========================
DT = 1e-3          # krok czasu [s]
GRAV = np.array([0.0, -9.81])  # grawitacja
BOX = np.array([(-5.0, 5.0), (0.0, 10.0)])  # min/max x, min/max y

# Parametry kontaktu (miękkie ciała DEM)
KN = 5e6          # sztywność normalna (twardość)
KT = 2e5          # sztywność styczna
CN = 80.0         # tłumienie normalne
CT = 20.0         # tłumienie styczne
MU = 0.6          # tarcie Coulomba
E_WALL = 0.6      # restytucja ścian (dla prostego odbicia)

RNG = np.random.default_rng(1)

class Bodies:
    def __init__(self, N):
        self.N = N
        self.pos = np.zeros((N,2))
        self.vel = np.zeros((N,2))
        self.ang = np.zeros(N)         # kąt (niekonieczne, ale zostawiamy)
        self.ang_vel = np.zeros(N)     # prędkość kątowa
        self.rad = np.zeros(N)
        self.mass = np.zeros(N)
        self.inertia = np.zeros(N)     # bezwładność dysku: I = 1/2 m r^2
        self.color = []
        # Pamięć śledzenia przemieszczenia stycznego w kontaktach:
        # klucz: (i,j) z i<j → wektor xi_t
        self.tang_mem = {}

    def add_disk(self, pos, vel, r, rho=1000.0, color='tab:blue'):
        i = np.nonzero(self.mass == 0.0)[0][0] if np.any(self.mass==0.0) else None
        if i is None:
            raise RuntimeError("Brak wolnych slotów na ciała")
        self.pos[i] = np.array(pos, dtype=float)
        self.vel[i] = np.array(vel, dtype=float)
        self.rad[i] = float(r)
        area = np.pi * r * r
        m = rho * area   # 2D „gęstość powierzchniowa”
        self.mass[i] = m
        self.inertia[i] = 0.5 * m * r * r
        self.color.append(color)

def make_pack(N=20):
    B = Bodies(N)
    # Rozmieszczenie startowe i losowe prędkości
    for i in range(N):
        r = RNG.uniform(0.15, 0.35)
        x = RNG.uniform(BOX[0,0]+r, BOX[0,1]-r)
        y = RNG.uniform(BOX[1,0]+r, BOX[1,1]-r)
        vx = RNG.normal(0.0, 0.5)
        vy = RNG.normal(0.0, 0.5)
        col = f"C{RNG.integers(0,10)}"
        B.add_disk((x,y), (vx,vy), r, rho=800.0, color=col)
    return B

def unit(vec):
    n = np.linalg.norm(vec)
    if n == 0: return vec, 0.0
    return vec / n, n

def step_dem(B: Bodies):
    N = B.N
    # Siły i momenty zerujemy
    F = np.zeros((N,2))
    Tau = np.zeros(N)

    # Grawitacja
    F += B.mass[:,None] * GRAV[None,:]

    # Kontakty dysk–dysk
    # O(N^2) – wystarczy do ~200 dysków; dla większych użyj siatki/haszowania
    for i in range(N):
        for j in range(i+1, N):
            rij = B.pos[j] - B.pos[i]
            n, dist = unit(rij)
            r_sum = B.rad[i] + B.rad[j]
            overlap = r_sum - dist
            if overlap <= 0: 
                # Brak kontaktu: wyzeruj pamięć tarcia, jeśli była
                B.tang_mem.pop((i,j), None)
                continue

            # Prędkość względna punktów kontaktu (tu bez rotacji – uproszczenie)
            v_rel = B.vel[j] - B.vel[i]
            v_n = np.dot(v_rel, n) * n
            v_t = v_rel - v_n

            # Siła normalna sprężyna–tłumik
            Fn = KN * overlap * n - CN * v_n
            # Pamiętane przemieszczenie styczne
            xi_t = B.tang_mem.get((i,j), np.zeros(2))
            xi_t = xi_t + v_t * DT  # integracja przesunięcia stycznego
            Ft_elas = -KT * xi_t
            Ft_damp = -CT * v_t
            Ft = Ft_elas + Ft_damp

            # Ograniczenie Coulomba
            Fn_mag = max(0.0, np.dot(Fn, n))  # normalna tylko odpycha
            Ft_lim = MU * Fn_mag
            Ft_mag = np.linalg.norm(Ft)
            if Ft_mag > Ft_lim and Ft_mag > 0:
                Ft = Ft * (Ft_lim / Ft_mag)
                # Poślizg -> reset sprężyny stycznej do wartości granicznej
                xi_t = -(Ft - Ft_damp) / KT if KT > 0 else np.zeros(2)

            # Zapisz zaktualizowaną pamięć
            B.tang_mem[(i,j)] = xi_t

            # Sumuj akcja-reakcja
            F[i] -= (Fn + Ft)
            F[j] += (Fn + Ft)

            # (Opcjonalnie) momenty od sił stycznych na krawędziach dysków
            # \tau = r * (n × Ft) w 2D to skalar:
            # weź r_i i r_j, wektor dźwigni ~ prostopadły do n
            ti = np.array([-n[1], n[0]])  # jednostkowy styczny
            Tau[i] -= B.rad[i] * np.dot(Ft, ti)
            Tau[j] += B.rad[j] * np.dot(Ft, ti)

    # Kontakty ze ścianami (proste odbicie + tłumik/sprężyna w normalnej)
    for i in range(N):
        x, y = B.pos[i]
        vx, vy = B.vel[i]
        r = B.rad[i]
        m = B.mass[i]

        # Lewa/Prawa (oś X)
        # Lewa
        if x - r < BOX[0,0]:
            overlap = BOX[0,0] - (x - r)
            n = np.array([1.0, 0.0])
            v_n = np.dot(B.vel[i], n)
            Fn = KN * overlap - CN * v_n
            Fn = max(Fn, 0.0)
            F[i] += Fn * n
            # prosty „bounce” (opcjonalnie)
            if v_n < 0: B.vel[i] -= (1+E_WALL) * v_n * n

        # Prawa
        if x + r > BOX[0,1]:
            overlap = (x + r) - BOX[0,1]
            n = np.array([-1.0, 0.0])
            v_n = np.dot(B.vel[i], n)
            Fn = KN * overlap - CN * v_n
            Fn = max(Fn, 0.0)
            F[i] += Fn * n
            if v_n < 0: B.vel[i] -= (1+E_WALL) * v_n * n

        # Dół (oś Y)
        if y - r < BOX[1,0]:
            overlap = BOX[1,0] - (y - r)
            n = np.array([0.0, 1.0])
            v_n = np.dot(B.vel[i], n)
            Fn = KN * overlap - CN * v_n
            Fn = max(Fn, 0.0)
            F[i] += Fn * n
            if v_n < 0: B.vel[i] -= (1+E_WALL) * v_n * n

        # Góra
        if y + r > BOX[1,1]:
            overlap = (y + r) - BOX[1,1]
            n = np.array([0.0, -1.0])
            v_n = np.dot(B.vel[i], n)
            Fn = KN * overlap - CN * v_n
            Fn = max(Fn, 0.0)
            F[i] += Fn * n
            if v_n < 0: B.vel[i] -= (1+E_WALL) * v_n * n

    # Integracja (semi-implicit Euler)
    B.vel += (F / B.mass[:,None]) * DT
    B.ang_vel += (Tau / (B.inertia + 1e-12)) * DT
    B.pos += B.vel * DT
    B.ang += B.ang_vel * DT

def run_sim():
    B = make_pack(N=10)

    fig, ax = plt.subplots(figsize=(7,7))
    ax.set_aspect('equal')
    ax.set_xlim(BOX[0,0], BOX[0,1])
    ax.set_ylim(BOX[1,0], BOX[1,1])
    ax.set_title("Dyski z kontaktem DEM (sprężyna–tłumik + tarcie)")

    patches = []
    for i in range(B.N):
        c = plt.Circle(B.pos[i], B.rad[i], fc=B.color[i], ec='k', alpha=0.9)
        ax.add_patch(c)
        patches.append(c)

    def init():
        for i in range(B.N):
            patches[i].center = B.pos[i]
            patches[i].radius = B.rad[i]
        return patches

    def update(_):
        # kilka małych kroków na klatkę dla stabilności
        substeps = 10
        for _ in range(substeps):
            step_dem(B)
        for i in range(B.N):
            patches[i].center = B.pos[i]
        return patches

    anim = FuncAnimation(fig, update, init_func=init, interval=1, blit=True)
    plt.show()

if __name__ == "__main__":
    run_sim()
