import numpy as np
import matplotlib.pyplot as plt

# Stała grawitacji
G = 6.67430e-11  # [m^3 / (kg * s^2)]

# Dane ciał niebieskich
m_sun     = 1.989e30   # kg
m_earth   = 5.972e24   # kg
m_moon    = 7.348e22   # kg

# Odległości początkowe (względem Słońca)
r_earth0  = np.array([1.496e11, 0.0])  # 1 AU
r_moon0   = r_earth0 + np.array([3.844e8, 0.0])  # 384 400 km od Ziemi
r_sun0    = np.array([0.0, 0.0])

# Prędkości początkowe (orbitalne, prostopadłe do promienia)
v_earth0  = np.array([0.0, 29_780.0])   # m/s
v_moon0   = v_earth0 + np.array([0.0, 1022.0])  # m/s wokół Ziemi
v_sun0    = np.array([0.0, 0.0])

# Tablice pozycji i prędkości
r = np.array([r_sun0, r_earth0, r_moon0])
v = np.array([v_sun0, v_earth0, v_moon0])
m = np.array([m_sun, m_earth, m_moon])

# Parametry symulacji
dt = 3600 * 6   # krok czasu: 6 godzin
steps = 1500    # liczba kroków (~1 rok)
pos_history = np.zeros((steps, 3, 2))

def compute_accelerations(r, m):
    """Zwraca przyspieszenia dla wszystkich ciał."""
    n = len(r)
    a = np.zeros_like(r)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            diff = r[j] - r[i]
            dist3 = np.linalg.norm(diff)**3 + 1e-9  # unikamy dzielenia przez 0
            a[i] += G * m[j] * diff / dist3
    return a

# Główna pętla symulacji (Velocity Verlet)
a = compute_accelerations(r, m)
for t in range(steps):
    pos_history[t] = r
    # 1. Zaktualizuj pozycje
    r_new = r + v * dt + 0.5 * a * dt**2
    # 2. Oblicz nowe przyspieszenia
    a_new = compute_accelerations(r_new, m)
    # 3. Zaktualizuj prędkości
    v_new = v + 0.5 * (a + a_new) * dt
    # 4. Przepisz
    r, v, a = r_new, v_new, a_new

# Wizualizacja trajektorii
plt.figure(figsize=(8, 8))
plt.plot(pos_history[:,0,0], pos_history[:,0,1], 'yo', label='Sun', markersize=6)
plt.plot(pos_history[:,1,0], pos_history[:,1,1], 'b-', label='Earth', lw=0.8)
plt.plot(pos_history[:,2,0], pos_history[:,2,1], 'gray', lw=0.5, label='Moon')

plt.gca().set_aspect('equal', adjustable='box')
plt.xlabel('x [m]')
plt.ylabel('y [m]')
plt.title('Symulacja Słońce–Ziemia–Księżyc (Newtonowska grawitacja)')
plt.legend()
plt.show()
