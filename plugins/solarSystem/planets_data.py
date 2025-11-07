# ================================================================
# DANE UKŁADU SŁONECZNEGO – wersja wizualizacyjna zgodna z modelem
# ================================================================
# Wszystkie parametry orbitalne planet: epoka J2000 (01.01.2000 12:00 TT)
# Odległości księżyców podane w jednostkach astronomicznych (AU).
#
# Zasady:
# - obliquity_deg  → nachylenie osi planety względem ekliptyki
# - spin_node_deg  → orientacja osi planety względem osi odniesienia (zwykle 0)
# - dla księżyców:
#       incl_eq_deg → nachylenie orbity względem RÓWNIKA planety
#       node_eq_deg → długość węzła orbit księżyca względem równika planety
#       phase_deg   → faza startowa ustawiona tak, aby orbity nie nakładały się
#
# Źródła danych:
# - NASA Fact Sheets
# - Horizons JPL DE430
# - Wikipedia (weryfikacja wartości pomocniczych)
# ================================================================


planets_data = [

# ------------------------------------------------
# MERKURY
# ------------------------------------------------
{
  'body_type': 'planet',
  'name': "Merkury",
  'color': "#b6b1aa",
  'size': 2.6,
  'radius_km': 2439.7,
  'radius_AU': 2439.7 / 149597870,
  'mass_kg': 3.3011e23,
  'density': 5.43,
  'a': 0.387, 'e': 0.206, 'p': 0.241,
  'inc': 7.00, 'argPeri': 29.124, 'meanAnomaly0': 174.796, 'Omega': 48.331,
  'obliquity_deg': 0.03,
  'spin_node_deg': 0.0,
},


# ------------------------------------------------
# WENUS
# ------------------------------------------------
{
  'body_type': 'planet',
  'name': "Wenus",
  'color': "#d8a866",
  'size': 4.2,
  'radius_km': 6051.8,
  'radius_AU': 6051.8 / 149597870,
  'mass_kg': 4.8675e24,
  'density': 5.24,
  'a': 0.723, 'e': 0.007, 'p': 0.615,
  'inc': 3.39, 'argPeri': 54.884, 'meanAnomaly0': 50.115, 'Omega': 76.680,
  'obliquity_deg': 177.36,   # oś „do góry nogami”
  'spin_node_deg': 0.0,
},


# ------------------------------------------------
# ZIEMIA
# ------------------------------------------------
{
  'body_type': 'planet',
  'name': "Ziemia",
  'color': "#3a7bff",
  'size': 4.8,
  'radius_km': 6371.0,
  'radius_AU': 6371.0 / 149597870,
  'mass_kg': 5.9724e24,
  'density': 5.51,
  'a': 1.000, 'e': 0.017, 'p': 1.000,
  'inc': 0.00, 'argPeri': 102.937, 'meanAnomaly0': 357.517, 'Omega': -11.260,
  'obliquity_deg': 23.44,
  'spin_node_deg': 0.0,

  'moons': [
    {
      'body_type': 'moon',
      'name': "Księżyc",
      'color': "#dddddd",
      'size': 1.3,
      'radius_km': 1737.1,
      'radius_AU': 1737.1 / 149597870,
      'mass_kg': 7.3477e22,
      'density': 3.34,
      'd': 0.00257,
      'p': 0.0748,
      'eccentricity': 0.0549,
      'incl_eq_deg': 5.145,
      'node_eq_deg': 125.08,
      'phase_deg': 35.0
    }
  ]
},


# ------------------------------------------------
# MARS
# ------------------------------------------------
{
  'body_type': 'planet',
  'name': "Mars",
  'color': "#d45f36",
  'size': 3.8,
  'radius_km': 3389.5,
  'radius_AU': 3389.5 / 149597870,
  'mass_kg': 6.4171e23,
  'density': 3.93,
  'a': 1.524, 'e': 0.093, 'p': 1.881,
  'inc': 1.85, 'argPeri': 336.040, 'meanAnomaly0': 19.373, 'Omega': 49.558,
  'obliquity_deg': 25.19,
  'spin_node_deg': 0.0,

  'moons': [
    {
      'body_type': 'moon', 'name': "Phobos", 'color': "#bfa89a", 'size': 0.9,
      'radius_km': 11.3,
      'radius_AU': 11.3 / 149597870,
      'd': 0.000062, 'p': 0.3189,
      'incl_eq_deg': 1.08, 'node_eq_deg': 207.8, 'phase_deg': 0.0
    },
    {
      'body_type': 'moon', 'name': "Deimos", 'color': "#cab6a2", 'size': 0.8,
      'radius_km': 6.2,
      'radius_AU': 6.2 / 149597870,
      'd': 0.000157, 'p': 1.2624,
      'incl_eq_deg': 0.93, 'node_eq_deg': 24.0, 'phase_deg': 160.0
    }
  ]
},


# ------------------------------------------------
# JOWISZ
# ------------------------------------------------
{
  'body_type': 'planet',
  'name': "Jowisz",
  'color': "#f2d7a6",
  'size': 9.5,
  'radius_km': 69911,
  'radius_AU': 69911 / 149597870,
  'mass_kg': 1.8982e27,
  'density': 1.33,
  'a': 5.203, 'e': 0.049, 'p': 11.86,
  'inc': 1.31, 'argPeri': 14.753, 'meanAnomaly0': 20.020, 'Omega': 100.464,
  'obliquity_deg': 3.13,
  'spin_node_deg': 0.0,

  'moons': [
    { 'name':"Io", 'body_type':'moon', 'color':"#e6d7a6", 'size':1.3,
      'radius_km':1821.6, 'radius_AU':1821.6/149597870, 'd':0.00282, 'p':0.00485,
      'incl_eq_deg':0.04, 'node_eq_deg':43.97, 'phase_deg':  0.0 },
    { 'name':"Europa", 'body_type':'moon', 'color':"#cccccc", 'size':1.2,
      'radius_km':1560.8, 'radius_AU':1560.8/149597870, 'd':0.00449, 'p':0.0096,
      'incl_eq_deg':0.47, 'node_eq_deg':219.10,'phase_deg': 90.0 },
    { 'name':"Ganimedes", 'body_type':'moon', 'color':"#bfa77a", 'size':1.5,
      'radius_km':2634.1, 'radius_AU':2634.1/149597870, 'd':0.00715, 'p':0.019,
      'incl_eq_deg':0.20, 'node_eq_deg':63.55, 'phase_deg':190.0 },
    { 'name':"Kallisto", 'body_type':'moon', 'color':"#9b7a5a", 'size':1.4,
      'radius_km':2410.3, 'radius_AU':2410.3/149597870, 'd':0.0126, 'p':0.045,
      'incl_eq_deg':0.28, 'node_eq_deg':299.36,'phase_deg':285.0 }
  ]
},


# ------------------------------------------------
# SATURN
# ------------------------------------------------
{
  'body_type': 'planet',
  'name': "Saturn",
  'color': "#f1d58d",
  'size': 8.5,
  'radius_km': 58232,
  'radius_AU': 58232 / 149597870,
  'mass_kg': 5.6834e26,
  'density': 0.69,
  'a': 9.537, 'e': 0.057, 'p': 29.46,
  'inc': 2.49, 'argPeri': 92.431, 'meanAnomaly0': 317.020, 'Omega': 113.665,

  # pierścienie (promień wewn./zewn. w AU)
  'ring_inner_AU': 0.0004,
  'ring_outer_AU': 0.0008,

  'obliquity_deg': 26.73,
  'spin_node_deg': 0.0,

  'moons': [
    { 'name':"Mimas", 'body_type':'moon', 'color':"#dcdcdc", 'size':0.9,
      'radius_km':198.2, 'radius_AU':198.2/149597870, 'd':0.00124, 'p':0.00303,
      'incl_eq_deg':1.574, 'node_eq_deg':90.0, 'phase_deg':  15.0 },

    { 'name':"Enceladus",'body_type':'moon','color':"#f4f4ff", 'size':1.2,
      'radius_km':252.1, 'radius_AU':252.1/149597870, 'd':0.00159, 'p':0.00338,
      'incl_eq_deg':0.009, 'node_eq_deg':120.0,'phase_deg':  65.0 },

    { 'name':"Tethys", 'body_type':'moon', 'color':"#ffffff", 'size':1.3,
      'radius_km':531.1, 'radius_AU':531.1/149597870, 'd':0.00197, 'p':0.00437,
      'incl_eq_deg':1.091,'node_eq_deg':15.0, 'phase_deg':115.0 },

    { 'name':"Dione", 'body_type':'moon','color':"#dddddd", 'size':1.3,
      'radius_km':561.4,'radius_AU':561.4/149597870,'d':0.00252, 'p':0.00735,
      'incl_eq_deg':0.028,'node_eq_deg':240.0,'phase_deg':165.0 },

    { 'name':"Rhea", 'body_type':'moon','color':"#cccccc", 'size':1.4,
      'radius_km':763.8,'radius_AU':763.8/149597870,'d':0.00352, 'p':0.0119,
      'incl_eq_deg':0.345,'node_eq_deg':300.0,'phase_deg':215.0 },

    { 'name':"Tytan", 'body_type':'moon','color':"#e4b36b", 'size':1.6,
      'radius_km':2574.7,'radius_AU':2574.7/149597870,'d':0.00817, 'p':0.0295,
      'incl_eq_deg':0.348,'node_eq_deg':23.25,'phase_deg':265.0 },

    { 'name':"Iapetus", 'body_type':'moon','color':"#bba788", 'size':1.4,
      'radius_km':734.5,'radius_AU':734.5/149597870,'d':0.0238, 'p':0.0795,
      'incl_eq_deg':15.47,'node_eq_deg':75.0,'phase_deg':315.0 }
  ]
},


# ------------------------------------------------
# URAN
# ------------------------------------------------
{
  'body_type':'planet',
  'name':"Uran",
  'color':"#82e3f3",
  'size':6.5,
  'radius_km':25362,
  'radius_AU':25362/149597870,
  'mass_kg':8.6810e25,
  'density':1.27,
  'a':19.19,'e':0.046,'p':84.0,
  'inc':0.77,'argPeri':170.964,'meanAnomaly0':142.238,'Omega':74.006,
  'obliquity_deg':97.77,   # oś przewrócona
  'spin_node_deg':0.0,

  'moons': [
    { 'name':"Miranda", 'body_type':'moon','color':"#d9d7d0",'size':1.0,
      'radius_km':235.8,'radius_AU':235.8/149597870,'d':0.00013,'p':0.00436,
      'phase_deg':  0.0 },
    { 'name':"Ariel", 'body_type':'moon','color':"#e5e5e5",'size':1.2,
      'radius_km':578.9,'radius_AU':578.9/149597870,'d':0.00019,'p':0.00802,
      'phase_deg': 72.0 },
    { 'name':"Umbriel", 'body_type':'moon','color':"#c6c6c6",'size':1.1,
      'radius_km':584.7,'radius_AU':584.7/149597870,'d':0.00027,'p':0.0114,
      'phase_deg':144.0 },
    { 'name':"Titania", 'body_type':'moon','color':"#c2bfae",'size':1.3,
      'radius_km':788.9,'radius_AU':788.9/149597870,'d':0.00044,'p':0.01595,
      'phase_deg':216.0 },
    { 'name':"Oberon", 'body_type':'moon','color':"#b6b39e",'size':1.3,
      'radius_km':761.4,'radius_AU':761.4/149597870,'d':0.00058,'p':0.0220,
      'phase_deg':288.0 },
  ]
},


# ------------------------------------------------
# NEPTUN
# ------------------------------------------------
{
  'body_type': 'planet',
  'name': "Neptun",
  'color': "#4a7fff",
  'size': 6.2,
  'radius_km': 24622,
  'radius_AU': 24622 / 149597870,
  'mass_kg': 1.02413e26,
  'density': 1.64,
  'a': 30.07, 'e': 0.009, 'p': 164.8,
  'inc': 1.77, 'argPeri': 44.971, 'meanAnomaly0': 256.228, 'Omega': 131.784,
  'obliquity_deg': 28.32,
  'spin_node_deg': 0.0,

  'moons': [
    { 'name':"Triton", 'body_type':'moon','color':"#e4dcd0",'size':1.4,
      'radius_km':1353.4,'radius_AU':1353.4/149597870,'mass_kg':2.14e22,
      'd':0.00036,'p':0.0137,
      'incl_eq_deg':156.8,   # retrogradacja
      'node_eq_deg':200.0,
      'phase_deg': 40.0 }
  ]
},


# ------------------------------------------------
# PLUTON (dla kompletności wizualnej)
# ------------------------------------------------
{
  'body_type':'planet',
  'name':"Pluton",
  'color':"#c9c2bc",
  'size':2.2,
  'radius_km':1188.3,
  'radius_AU':1188.3/149597870,
  'mass_kg':1.303e22,
  'a':39.48,'e':0.244,'p':248.0,'inc':17.16,
  'argPeri':113.834,'meanAnomaly0':14.53,'Omega':110.299,
  'obliquity_deg':119.6,
  'spin_node_deg':0.0,

  'moons': [
    { 'name':"Charon", 'body_type':'moon','color':"#dddccc",'size':1.1,
      'radius_km':606.0,'radius_AU':606.0/149597870,'d':0.00008,'p':0.0175,
      'phase_deg': 0.0 }
  ]
},

]


# ------------------------------------------------
# SŁOŃCE
# ------------------------------------------------
sun_data = {
  'body_type': 'sun',
  'name': "Słońce",
  'color': "yellow",
  'size': 12.0,
  'radius_km': 695700,
  'radius_AU': 0.00465,
  'mass_kg': 1.9885e30,
  'density': 1.41,
  'luminosity_rel': 1.0,
  'temperature_K': 5778,
  'spectral_type': 'G2V'
}
