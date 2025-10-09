# ==================== PLANETY UKŁADU SŁONECZNEGO ====================
# Wszystkie wartości oparte na epokę J2000 (01.01.2000 12:00 TT)
# Źródła: NASA/JPL DE430 + Wikipedia

# Każdy wpis to słownik opisujący planetę:
#   name           : nazwa planety
#   color          : kolor używany w wizualizacji
#   size           : wizualny rozmiar planety (piksele, dowolny)
#   radius_km      : rzeczywisty promień planety [km]
#   radius_rel_sun : promień w stosunku do promienia Słońca (= radius_km / 695700)
#   radius_AU      : promień w jednostkach astronomicznych (= radius_km / 149597870)
#   mass_kg        : masa planety [kg]
#   density        : gęstość średnia [g/cm³]
#   a              : półoś wielka orbity [AU]
#   e              : mimośród orbity
#   p              : okres orbitalny [lata ziemskie]
#   inc            : inklinacja orbity względem ekliptyki [°]
#   argPeri        : argument peryhelium (ω) [°]
#   meanAnomaly0   : średnia anomalia w epoce J2000 [°]
#   Omega          : długość węzła wstępującego (Ω) [°] (domyślnie 0 jeśli brak)
#   moons          : lista słowników opisujących księżyce planety

planets_data = [
  { 'name':"Merkury", 'color':"#b6b1aa", 'size':2.6,
    'radius_km':2439.7, 'radius_rel_sun':0.0035, 'radius_AU':1.63e-5,
    'mass_kg':3.3011e23, 'density':5.43,
    'a':0.387, 'e':0.206, 'p':0.241, 'inc':7.00,
    'argPeri':29.124, 'meanAnomaly0':174.796, 'Omega':48.331 },

  { 'name':"Wenus", 'color':"#d8a866", 'size':4.2,
    'radius_km':6051.8, 'radius_rel_sun':0.0087, 'radius_AU':4.05e-5,
    'mass_kg':4.8675e24, 'density':5.24,
    'a':0.723, 'e':0.007, 'p':0.615, 'inc':3.39,
    'argPeri':54.884, 'meanAnomaly0':50.115, 'Omega':76.680 },

  { 'name':"Ziemia", 'color':"#3a7bff", 'size':4.8,
    'radius_km':6371.0, 'radius_rel_sun':0.0092, 'radius_AU':4.26e-5,
    'mass_kg':5.9724e24, 'density':5.51,
    'a':1.000, 'e':0.017, 'p':1.000, 'inc':0.00,
    'argPeri':102.937, 'meanAnomaly0':357.517, 'Omega':-11.260,
    'moons':[
      { 'name':"Księżyc", 'color':"#dddddd", 'size':1.3,
        'radius_km':1737.1, 'radius_rel_sun':0.0025, 'radius_AU':1.16e-5,
        'mass_kg':7.3477e22, 'density':3.34,
        'd':0.00257,  # średnia odległość od Ziemi [AU]
        'p':0.0748 }  # okres orbitalny [lata ziemskie]
    ]},

  { 'name':"Mars", 'color':"#d45f36", 'size':3.8,
    'radius_km':3389.5, 'radius_rel_sun':0.0049, 'radius_AU':2.26e-5,
    'mass_kg':6.4171e23, 'density':3.93,
    'a':1.524, 'e':0.093, 'p':1.881, 'inc':1.85,
    'argPeri':336.040, 'meanAnomaly0':19.373, 'Omega':49.558,
    'moons':[
      { 'name':"Phobos", 'color':"#bfa89a", 'size':0.9,
        'radius_km':11.3, 'radius_rel_sun':1.6e-5, 'radius_AU':7.6e-8,
        'mass_kg':1.07e16, 'density':1.88,
        'd':0.000062, 'p':0.3189 },
      { 'name':"Deimos", 'color':"#cab6a2", 'size':0.8,
        'radius_km':6.2, 'radius_rel_sun':8.9e-6, 'radius_AU':4.1e-8,
        'mass_kg':1.48e15, 'density':1.47,
        'd':0.000157, 'p':1.2624 }
    ]},

  { 'name':"Jowisz", 'color':"#f2d7a6", 'size':9.5,
    'radius_km':69911, 'radius_rel_sun':0.150, 'radius_AU':4.67e-4,
    'mass_kg':1.8982e27, 'density':1.33,
    'a':5.203, 'e':0.049, 'p':11.86, 'inc':1.31,
    'argPeri':14.753, 'meanAnomaly0':20.020, 'Omega':100.464,
    'moons':[
      { 'name':"Io", 'color':"#e6d7a6", 'size':1.3,
        'radius_km':1821.6, 'radius_rel_sun':0.0026, 'radius_AU':1.22e-5,
        'mass_kg':8.93e22, 'density':3.53,
        'd':0.00282, 'p':0.00485 },
      { 'name':"Europa", 'color':"#cccccc", 'size':1.2,
        'radius_km':1560.8, 'radius_rel_sun':0.0022, 'radius_AU':1.04e-5,
        'mass_kg':4.80e22, 'density':3.01,
        'd':0.00449, 'p':0.0096 },
      { 'name':"Ganimedes", 'color':"#bfa77a", 'size':1.5,
        'radius_km':2634.1, 'radius_rel_sun':0.0038, 'radius_AU':1.76e-5,
        'mass_kg':1.48e23, 'density':1.94,
        'd':0.00715, 'p':0.019 },
      { 'name':"Kallisto", 'color':"#9b7a5a", 'size':1.4,
        'radius_km':2410.3, 'radius_rel_sun':0.0035, 'radius_AU':1.61e-5,
        'mass_kg':1.08e23, 'density':1.83,
        'd':0.0126, 'p':0.045 }
    ]},

  { 'name':"Saturn", 'color':"#f1d58d", 'size':8.5,
    'radius_km':58232, 'radius_rel_sun':0.130, 'radius_AU':3.89e-4,
    'mass_kg':5.6834e26, 'density':0.69,
    'a':9.537, 'e':0.057, 'p':29.46, 'inc':2.49,
    'argPeri':92.431, 'meanAnomaly0':317.020, 'Omega':113.665,
    'moons':[
      { 'name':"Tytan", 'color':"#e4b36b", 'size':1.4,
        'radius_km':2574.7, 'radius_rel_sun':0.0037, 'radius_AU':1.72e-5,
        'mass_kg':1.35e23, 'density':1.88,
        'd':0.00817, 'p':0.0295 },
      { 'name':"Rhea", 'color':"#cccccc", 'size':1.2,
        'radius_km':763.8, 'radius_rel_sun':0.0011, 'radius_AU':5.11e-6,
        'mass_kg':2.31e21, 'density':1.23,
        'd':0.00352, 'p':0.0119 }
    ]},

  { 'name':"Uran", 'color':"#82e3f3", 'size':6.5,
    'radius_km':25362, 'radius_rel_sun':0.054, 'radius_AU':1.70e-4,
    'mass_kg':8.6810e25, 'density':1.27,
    'a':19.19, 'e':0.046, 'p':84.0, 'inc':0.77,
    'argPeri':170.964, 'meanAnomaly0':142.238, 'Omega':74.006 },

  { 'name':"Neptun", 'color':"#4a7fff", 'size':6.2,
    'radius_km':24622, 'radius_rel_sun':0.052, 'radius_AU':1.64e-4,
    'mass_kg':1.02413e26, 'density':1.64,
    'a':30.07, 'e':0.009, 'p':164.8, 'inc':1.77,
    'argPeri':44.971, 'meanAnomaly0':256.228, 'Omega':131.784 }
]

# ==================== DANE SŁOŃCA ====================
sun_data = {
    'name': "Słońce",
    'color': "yellow",
    'size': 12.0,             # rozmiar wizualny (np. w pikselach)
    'radius_km': 695700,      # rzeczywisty promień Słońca [km]
    'radius_rel_sun': 1.0,    # 1.0 = odniesienie dla reszty planet
    'radius_AU': 0.00465,     # przeliczenie na jednostki astronomiczne
    'mass_kg': 1.9885e30,     # masa Słońca [kg]
    'density': 1.41,          # średnia gęstość [g/cm³]
    'luminosity_rel': 1.0,    # jasność względna (może się przydać)
    'temperature_K': 5778,    # temperatura efektywna [K]
    'spectral_type': 'G2V'    # typ widmowy (żółty karzeł)
}
