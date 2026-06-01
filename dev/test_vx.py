import numpy as np

class Vertex(np.ndarray):
	def __new__(cls, x=0.0, y=0.0, z=0.0):
		obj = np.asarray([x, y, z], dtype=np.float32).view(cls)
		return obj
	@property
	def x(self): return self[0]

	@x.setter
	def x(self,val): self[0]=val

	@property
	def y(self): return self[1]
	
	@y.setter
	def y(self,val): self[1]=val
	
	@property
	def z(self): return self[2]

	@z.setter
	def z(self,val): self[2]=val



v = Vertex(1,2,3)

print(v)

print(v.nbytes)

print(v.y)

v.y = 5

print(v)
