import numpy as np
from datetime import datetime
from celestialBody import CelestialBody, Planet, Moon, years_since_j2000, rotate_z_x
from planets_data import planets_data, sun_data

# ================== budowa układu ==================
# --- tworzymy Słońce jako główny obiekt ---
sun = CelestialBody(**sun_data)
solar_system = [Planet(parent=sun, **p) for p in planets_data]


# ================== przykład użycia ==================
now = datetime.utcnow()
t = years_since_j2000(now)
print(f"Czas od J2000: {t:.3f} lat ({now.date()})")

for planet in solar_system:
    pos = planet.position(t)
    print(f"{planet.name:8s}: {pos}")
    for moon in planet.moons:
        print(f"   {moon.name:8s}: {moon.position(t)}")


earth:Planet = Planet(parent=sun, **planets_data[2])  # Ziemia

print(f"{earth.name} - grawitacja powierzchniowa: {earth.gravity_surface():.2f} m/s²")
print(f"{earth.name} - prędkość ucieczki: {earth.escape_velocity()/1000:.2f} km/s")

moon:Moon = earth.moons[0]
print(f"{moon.name} - grawitacja powierzchniowa: {moon.gravity_surface():.2f} m/s²")
print(f"{moon.name} - prędkość ucieczki: {moon.escape_velocity()/1000:.2f} km/s")

sun_g = sun.gravity_surface()
sun_v = sun.escape_velocity()
print(f"{sun.name} - g = {sun_g:.1f} m/s², v_esc = {sun_v/1000:.1f} km/s")