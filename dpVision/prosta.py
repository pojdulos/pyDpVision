import numpy as np

class Prosta:
	def __init__(self, general=None, origdir=None):
		if general is not None:
			self.a, self.b, self.c, self.d = general
			self.recalc_origdir()
		elif origdir is not None:
			self.origin, self.dir = origdir
			self.recalc_general()

	# Gettery
	@property
	def general(self):
		return self.a, self.b, self.c, self.d

	@property
	def origdir(self):
		return self.origin, self.dir

	# Settery
	@general.setter
	def general(self, general):
		self.a, self.b, self.c, self.d = general
		self.recalc_origdir()

	@origdir.setter
	def origdir(self, origdir):
		self.origin, self.dir = origdir
		self.recalc_general()

	def find_general_equation_params(self, dir, orig):
		a, b, c = dir
		d = -np.dot(dir, orig)
		return a, b, c, d

	def find_direction_vector_and_point_closest_to_origin(self, a, b, c, d):
		direction_vector = np.array([a, b, c])
		# Obliczenie punktu na prostej leżącego najbliżej środka układu współrzędnych
		t = -d / np.linalg.norm(direction_vector)**2  # Współczynnik dla kierunku prostopadłego
		point_on_line = t * direction_vector
		return direction_vector, point_on_line

	def recalc_general(self):
		self.a, self.b, self.c, self.d = self.find_general_equation_params(self.dir, self.origin)

	def recalc_origdir(self):
		self.dir, self.origin = self.find_direction_vector_and_point_closest_to_origin(self.a, self.b, self.c, self.d)

	def to_general_form(self):
		return self.find_general_equation_params(self.dir, self.origin)

	def to_origdir_form(self):
		return self.find_direction_vector_and_point_closest_to_origin(self.a, self.b, self.c, self.d)

class Prosta3D:
    def __init__(self, direction_vector=None, point_on_line=None, normal_vector=None, d=None):
        """
        Inicjalizacja prostej w trójwymiarowej przestrzeni.

        Można zainicjalizować prostą podając jej wektor kierunkowy i punkt leżący na prostej,
        lub podając wektor normalny do płaszczyzny zawierającej prostą i stałą d.
        """
        if direction_vector is not None and point_on_line is not None:
            self.direction_vector = direction_vector
            self.point_on_line = point_on_line
            self.calculate_normal_vector()
            self.calculate_d()
        elif normal_vector is not None and d is not None:
            self.normal_vector = normal_vector
            self.d = d
            self.calculate_direction_vector()
            self.calculate_point_on_line()

    def calculate_normal_vector(self):
        """Oblicza wektor normalny do płaszczyzny zawierającej prostą."""
        self.normal_vector = self.direction_vector

    def calculate_d(self):
        """Oblicza stałą d równania płaszczyzny zawierającej prostą."""
        self.d = -sum(self.normal_vector[i] * self.point_on_line[i] for i in range(3))

    def calculate_direction_vector(self):
        """Oblicza wektor kierunkowy prostej z wektora normalnego."""
        self.direction_vector = self.normal_vector

    def calculate_point_on_line(self):
        """Oblicza punkt na prostej z wektora normalnego i stałej d."""
        t = -self.d / sum(vi**2 for vi in self.direction_vector)
        self.point_on_line = [t * vi for vi in self.direction_vector]


def intersection_point(plane, line_point, line_direction):
    # Równanie płaszczyzny: ax + by + cz = d
    a, b, c, d = plane

    # Punkt na linii: P0 = [x0, y0, z0]
    x0, y0, z0 = line_point

    # Kierunek linii: [a, b, c]
    l0, l1, l2 = line_direction

    # Oblicz parametr t
    t = (d - a*x0 - b*y0 - c*z0) / (a*l0 + b*l1 + c*l2)

    # Oblicz współrzędne punktu przecięcia
    x = x0 + l0*t
    y = y0 + l1*t
    z = z0 + l2*t

    return np.array([x, y, z])


def intersection_point2(plane, line):
    # Równanie płaszczyzny: ax + by + cz = d
    a, b, c, d = plane

    # Równanie linii: Ax + By + Cz + D = 0
    A, B, C, D = line

    # Punkt na linii: P0 = [x0, y0, z0]
    # Możemy przyjąć x0 = y0 = 0, a z0 = -D/C, jeżeli C != 0
    if C != 0:
        x0, y0, z0 = 0, 0, -D/C
    else:
        raise ValueError("C nie może być równa 0")

    # Kierunek linii: [A, B, C]
    l0, l1, l2 = A, B, C

    # Oblicz parametr t
    t = (d - a*x0 - b*y0 - c*z0) / (a*l0 + b*l1 + c*l2)

    # Oblicz współrzędne punktu przecięcia
    x = x0 + l0*t
    y = y0 + l1*t
    z = z0 + l2*t

    return np.array([x, y, z])

# # Przykładowe użycie klasy Prosta
# # Inicjalizacja prostej za pomocą równania ogólnego
# prosta1 = Prosta(a=2, b=3, c=6)
# print("Równanie ogólne prostej:", prosta1.to_general_form())

# # Konwersja na postać punktową
# punkty = prosta1.to_points_form()
# print("Punkty przecięcia z osiami układu współrzędnych:", punkty)

# # Inicjalizacja prostej za pomocą punktów przecięcia
# prosta2 = Prosta(p1=(2, 4), p2=(4, 6))
# print("Równanie ogólne prostej:", prosta2.to_general_form())


# # Przykładowe użycie klasy Prosta3D
# direction_vector = [2, 1, -1]
# point_on_line = [1, 2, 3]

# prosta = Prosta3D(direction_vector=direction_vector, point_on_line=point_on_line)

# print("Wektor kierunkowy prostej:", prosta.direction_vector)
# print("Punkt na prostej:", prosta.point_on_line)
# print("Wektor normalny do płaszczyzny zawierającej prostą:", prosta.normal_vector)
# print("Stała d równania płaszczyzny zawierającej prostą:", prosta.d)



# # Przykładowe dane
# plane = [1, 2, 3, 4]  # [a, b, c, d]
# line_point = [1, 1, 1]  # [x0, y0, z0]
# line_direction = [1, 2, 3]  # [a, b, c]

# print(intersection_point(plane, line_point, line_direction))

# # Przykładowe dane
# plane = [1, 2, 3, 4]  # [a, b, c, d]
# line = [1, 1, 1, -1]  # [A, B, C, D]

# print(intersection_point2(plane, line))

a = [1,2,4]
b = [8,4,2]
print( np.dot(a,b) )