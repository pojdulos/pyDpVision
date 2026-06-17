import numpy as np

class BaseVector3(np.ndarray):
	"""Bazowa klasa 3D (x,y,z) z kontrolą wymiaru i dostępem do współrzędnych."""
	_dtype = np.float32  # nadpisywana w podklasach

	def __new__(cls, x=0.0, y=0.0, z=0.0):
		obj = np.asarray([x, y, z], dtype=cls._dtype).view(cls)
		return obj

	def __array_finalize__(self, obj):
		if obj is None:
			return
		if self.shape != (3,):
			raise ValueError(f"{type(self).__name__}: wymagany wektor o długości 3.")

	# --- właściwości wspólne ---
	@property
	def x(self): return float(self[0])
	@x.setter
	def x(self, val): self[0] = val

	@property
	def y(self): return float(self[1])
	@y.setter
	def y(self, val): self[1] = val

	@property
	def z(self): return float(self[2])
	@z.setter
	def z(self, val): self[2] = val

	# def __str__(self):
	# 	cls = type(self).__name__
	# 	return f"{cls}({self[0]:.3f}, {self[1]:.3f}, {self[2]:.3f})"

	# def __repr__(self):
	# 	cls = type(self).__name__
	# 	return f"{cls}({self[0]:.3f}, {self[1]:.3f}, {self[2]:.3f})"


class Point3(BaseVector3):
	@classmethod
	def from_point(cls, p):
		"""Tworzy nowy obiekt klasy z innego punktu lub wierzchołka."""
		if isinstance(p, (Point3d, Vertex)):
			return cls(*p)
		else:
			return NotImplemented


class Vertex(Point3):
	"""Wektor 3D o typie float32 (np. dla OpenGL)."""
	_dtype = np.float32


class Point3d(Point3):
	"""Punkt 3D o podwójnej precyzji (float64)."""
	_dtype = np.float64

	def __add__(self, other):
		if isinstance(other, Vector3d):
			return Point3d(*(self + other))
		return NotImplemented

	def __iadd__(self, other):
		"""Obsługuje Point3d += Vector3d (modyfikacja in place)."""
		if isinstance(other, Vector3d):
			self[:] += other[:]   # modyfikacja danych w miejscu
			return self
		return NotImplemented

	def __sub__(self, other):
		if isinstance(other, Point3d):
			# punkt - punkt = wektor
			return Vector3d(*(self - other))
		elif isinstance(other, Vector3d):
			# punkt - wektor = punkt (przesunięcie w przeciwnym kierunku)
			return Point3d(*(self - other))
		return NotImplemented

	def __isub__(self, other):
		"""Obsługuje Point3d -= Vector3d."""
		if isinstance(other, Vector3d):
			self[:] -= other[:]
			return self
		return NotImplemented


class Vector3d(BaseVector3):
	"""Wektor 3D o podwójnej precyzji (float64)."""
	_dtype = np.float64

	def __add__(self, other):
		if isinstance(other, Vector3d):
			return Vector3d(*(self + other))
		elif isinstance(other, Point3d):
			# wektor + punkt = punkt przesunięty o wektor
			return Point3d(*(self + other))
		return NotImplemented

	def __radd__(self, other):
		# pozwala na Point3d + Vector3d
		if isinstance(other, Point3d):
			return other + self
		elif isinstance(other, Vector3d):
			return Vector3d(*(other + self))
		return NotImplemented

	def __sub__(self, other):
		if isinstance(other, Vector3d):
			return Vector3d(*(self - other))
		return NotImplemented

	@classmethod
	def from_points(cls, p1, p2):
		"""Wektor od punktu p1 do p2."""
		return cls(*(np.asarray(p2) - np.asarray(p1)))

	@classmethod
	def from_iterable(cls, iterable):
		"""Utwórz z listy/tupli/ndarray."""
		arr = np.asarray(iterable, dtype=cls._dtype)
		if arr.shape != (3,):
			raise ValueError("Oczekiwano sekwencji 3-elementowej.")
		return cls(*arr)

	@classmethod
	def from_vector(cls, v):
		"""Kopia innego wektora."""
		return cls(*v)

	# --- operacje geometryczne ---
	def length(self) -> float:
		return float(np.linalg.norm(self))

	def normalized(self):
		n = np.linalg.norm(self)
		if n == 0:
			return type(self)(0.0, 0.0, 0.0)
		return type(self)(*(self / n))

	def dot(self, other: np.ndarray) -> float:
		return float(np.dot(self, other))

	def cross(self, other: np.ndarray):
		return type(self)(*np.cross(self, other))

	# def __repr__(self):
	# 	return f"Vector3d[{self[0]:.3f}, {self[1]:.3f}, {self[2]:.3f}]"

	# def __str__(self):
	# 	return self.__repr__()

class VertexArray(np.ndarray):
	def __new__(cls, data):
		arr = np.asarray(data, dtype=np.float32)
		if arr.ndim != 2 or arr.shape[1] != 3:
			raise ValueError("VertexArray wymaga kształtu (N,3)")
		return arr.view(cls)

	def transform(self, matrix4x4):
		N = self.shape[0]
		v = np.hstack([self, np.ones((N,1), dtype=np.float32)])
		return (v @ matrix4x4.T)[:, :3].view(VertexArray)

if __name__ == "__main__":
	v = Vertex(1, 2, 3)
	print(v, v.dtype)     # Vertex(1.000, 2.000, 3.000) float32

	p = Point3d(1, 2, 3)
	print(p, p.dtype)     # Point3d(1.000, 2.000, 3.000) float64

	vec = Vector3d(0, 3, 4)
	print(vec.length())   # 5.0
	print(vec.normalized())  # Vector3d(0.000, 0.600, 0.800)
	print(vec.cross(Vector3d(1, 0, 0)))  # Vector3d(0.000, 4.000, -3.000)


	p1 = Point3d(1.0, 2.0, 3.0)
	p2 = Point3d(4.0, 6.0, 8.0)

	v1 = Vector3d()                      # (0,0,0)
	v2 = Vector3d(1, 2, 3)               # (1,2,3)
	v3 = Vector3d(p1, p2)                # (3,4,5)
	v4 = Vector3d(v3)                    # kopia
	v5 = Vector3d([0.5, 0.5, 1.5])       # z listy

	print(v1, v2, v3, v4, v5, sep="\n")

	print(f"domyślny wynik 'print()': {v1}")
	print(f"domyślny wynik 'print(repr())': {repr(v1)}")
