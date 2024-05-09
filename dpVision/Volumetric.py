from dpVision.Globals import AP
from .Object import Object
from PyQt5.QtGui import *
from OpenGL.GL import *
import os
import concurrent.futures
from collections import defaultdict
import numpy as np
import pydicom
import time
import matplotlib.pyplot as plt
from dpVision.Shaders import Volumetric_vertex_shader_code, Volumetric_fragment_shader_code, compile_shader

vertex_shader_code = """
#version 330 core
layout (location = 0) in float aCol;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

uniform float minColor;
uniform float maxColor;

uniform int sizeX;
uniform int sizeY;
uniform int aPosZ;

uniform int rescale;

out vec3 FragPos;

out VS_OUT{
	vec3 color;
	vec3 worldPos;
	mat4 projectionMatrix;
	mat4 viewMatrix;
	float scale;
	bool validVoxel;
} vout;

void main()
{
	if (aCol >= minColor && aCol <= maxColor)
	{
		int aPosY = int( float(gl_VertexID) / sizeX );
		int aPosX = gl_VertexID - ( aPosY * sizeX );
		vec3 aPos = rescale * vec3(aPosX, aPosY, aPosZ);	

		vec4 worldPos = model * vec4(aPos, 1.0);
        //gl_Position = projection * view * worldPos;

        vout.color = vec3(aCol);
		vout.worldPos = worldPos.xyz;
		vout.projectionMatrix = projection;
		vout.viewMatrix = view;
		vout.scale = float(rescale);
        vout.validVoxel = true;

        FragPos = worldPos.xyz;		
	}
	else
	{
		vout.validVoxel = false;
	}
}
"""

geometry_shader_code = """
#version 330 core
layout(points) in;
layout(points, max_vertices = 1) out;

in VS_OUT{
	vec3 color;
	vec3 worldPos;
	mat4 projectionMatrix;
	mat4 viewMatrix;
	float scale;
	bool validVoxel;
} gs_in[];

out vec3 vertexColor;

void main(void)
{
	if (gs_in[0].validVoxel)
	{
		vertexColor = gs_in[0].color;
		gl_Position = gs_in[0].projectionMatrix * gs_in[0].viewMatrix * vec4(gs_in[0].worldPos, 0.1);
		//gl_Position = gl_in[0].gl_Position;
		//gl_PointSize = gl_in[0].gl_PointSize;

		EmitVertex();
		EndPrimitive();
	}
}
"""

# próba wyświetlania vokseli jako kostek zamiast pikseli
geometry_shader_code1 = """
#version 330 core
layout (points) in;
layout (triangle_strip, max_vertices = 36) out;

in VS_OUT {
    vec3 color;
	vec3 worldPos;
	mat4 projectionMatrix;
	mat4 viewMatrix;
	float scale;
    bool validVoxel;
} gs_in[];

out vec3 vertexColor;

void main() {
    if (gs_in[0].validVoxel) {
        vertexColor = gs_in[0].color;

        // Pozycja wierzchołka (punkt)
        //vec4 pointPos = gl_in[0].gl_Position;
        vec4 pointPos = vec4(gs_in[0].worldPos, 1.0);

        // Wierzchołki tworzące ściany kostki
        vec4 vertices[8];

        // Obliczenia pozycji wierzchołków
        float halfSize = 0.5 * gs_in[0].scale; // Połowa długości boku kostki

        // Wierzchołki kostki
        vertices[0] = pointPos + vec4(-halfSize, -halfSize, -halfSize, 0.0);
		vertices[1] = pointPos + vec4(halfSize, -halfSize, -halfSize, 0.0);  // Prawy dolny tylny
		vertices[2] = pointPos + vec4(-halfSize, halfSize, -halfSize, 0.0);  // Lewy górny tylny
		vertices[3] = pointPos + vec4(halfSize, halfSize, -halfSize, 0.0);   // Prawy górny tylny
		vertices[4] = pointPos + vec4(-halfSize, -halfSize, halfSize, 0.0);  // Lewy dolny przedni
		vertices[5] = pointPos + vec4(halfSize, -halfSize, halfSize, 0.0);   // Prawy dolny przedni
		vertices[6] = pointPos + vec4(-halfSize, halfSize, halfSize, 0.0);   // Lewy górny przedni
		vertices[7] = pointPos + vec4(halfSize, halfSize, halfSize, 0.0);    // Prawy górny przedni

        // Generowanie ścian kostki
        for (int i = 0; i < 8; ++i) {
            gl_Position = gs_in[0].projectionMatrix * gs_in[0].viewMatrix *vertices[i];
            EmitVertex();
        }
        EndPrimitive();
    }
}
"""

fragment_shader_code = """
#version 330 core
in vec3 vertexColor;
in vec3 FragPos; // Pozycja fragmentu/prymitywu w przestrzeni świata

out vec4 FragColor;

void main()
{
    vec3 viewPos = vec3(0, 0, 200);  // Pozycja obserwatora/kamery
    vec3 lightPos = viewPos;  // Pozycja światła od strony ekranu
    //vec3 lightPos = vec3(0, 100, 600);  // Pozycja światła
    vec3 lightColor = vec3(1.0, 1.0, 1.0);  // Kolor światła
    float ambientStrength = 0.6;
    float specularStrength = 0.5;  // Siła światła spekularnego
    float shininess = 32.0;  // Połysk (shininess)

    // Obliczenia oświetlenia (tutaj możesz dodać własną logikę)
    vec3 norm = vec3(0.0,0.0,1.0); //kierunek "do ekranu"
    vec3 lightDir = normalize(lightPos - FragPos);  // Poprawione obliczanie kierunku światła
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;

    vec3 viewDir = normalize(viewPos - FragPos);
    vec3 reflectDir = reflect(-lightDir, norm);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), shininess);
    vec3 specular = specularStrength * spec * lightColor;

    vec3 result = (ambientStrength * lightColor + diffuse + specular) * vertexColor.rgb;

    FragColor = vec4(result, 1.0);
}
"""

# Zaczątek klasy Volumetric opartej o bibliotekę pyDICOM.
# Pamiętajmy więc, że to prawdopodobnie jeszcze nie działa
# albo działa źle

def convert_to_np_array(key, list):
    return key, np.array(list, dtype=np.float32)

class Volumetric(Object):
	def __init__(self, parent=None):
		super( Volumetric, self ).__init__( parent )
		self.m_dicom_files = []
		self.m_volume = [[[]]]
		self.i = 0
		self.v_vbo = None
		self.shader_program = None
		self.m_minDisplWin = 0.0
		self.m_maxDisplWin = 1.0
		self.m_fastDraw = True

	def window_ct(self, dcm, ymin=0.0, ymax=1.0, w=None, c=None):
		"""Windows a CT slice.
		http://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.11.2.html

		Args:
			dcm (pydicom.dataset.FileDataset):
			w: Window Width parameter.
			c: Window Center parameter.
			ymin: Minimum output value.
			ymax: Maximum output value.

		Returns:
			Windowed slice.
		"""
		# print(dcm.file_meta)
		# print(dcm.pixel_array)
  
		# convert to HU
		b = float(getattr(dcm, 'RescaleIntercept', 0.0))
		m = float(getattr(dcm, 'RescaleSlope', 1.0))

		# print(f"m = {m}, b = {b}")
		x = m * dcm.pixel_array + b

		# print(f"slice.min = {np.min(x)}, slice.max = {np.max(x)}")

		if w is None: w = dcm.WindowWidth
		if c is None: c = dcm.WindowCenter

		# print(f"win.center = {c}, win.width = {w}")

		# windowing C.11.2.1.2.1 Default LINEAR Function
		#
		y = np.zeros_like(x)
		y[x <= (c - 0.5 - (w - 1) / 2)] = ymin
		y[x > (c - 0.5 + (w - 1) / 2)] = ymax
		y[(x > (c - 0.5 - (w - 1) / 2)) & (x <= (c - 0.5 + (w - 1) / 2))] = \
			((x[(x > (c - 0.5 - (w - 1) / 2)) & (x <= (c - 0.5 + (w - 1) / 2))] - (c - 0.5)) / (w - 1) + 0.5) * (
					ymax - ymin) + ymin

		return y

	def show_histogram(self):

		data = np.array(self.m_volume).flatten()

		#data = data.clip(lower=data.quantile(0.1), upper=data.quantile(0.9))
		#data = data.clip(lower=0, upper=4096)
		
		biny = np.round(np.arange(0, 1.01, 0.01),2)

		# wygeneruj histogram i zapisz wyniki
		counts, bins = np.histogram(data, bins=biny)

		# wypisz krawędzie binów i częstości
		for i in range(len(bins)-1):
			print(f"Bin: ({bins[i]}, {bins[i+1]}), Częstość: {counts[i]}")

		plt.hist(bins[:-1], bins, weights=counts)

		plt.title('Histogram')
		plt.xlabel('Wartości')
		plt.ylabel('Częstotliwość')
		plt.grid(axis='y', alpha=0.5)
		plt.show()

	def read_as_directory(self, folder_path):
		# Wczytanie wszystkich plików DICOM z folderu
		self.m_dicom_files = [pydicom.dcmread(os.path.join(folder_path, f)) for f in os.listdir(folder_path) if f.endswith('.dcm')]
		
		# Sortowanie plików DICOM w kolejności
		self.m_dicom_files.sort(key=lambda x: float(getattr(x, 'SliceLocation', float(getattr(x, 'ImagePositionPatient')[2]))))

		# Tworzenie wolumetrycznego zestawu danych
		#self.m_volume = np.stack([file.pixel_array for file in self.m_dicom_files])
		self.m_volume = np.stack([self.window_ct(file) for file in self.m_dicom_files])
		#self.m_volume = np.stack([self.window_ct(file,w=4096.0,c=1024.0) for file in self.m_dicom_files])
		#self.m_volume = np.stack([self.window_ct(file,w=2048.0,c=2048.0) for file in self.m_dicom_files])
		#self.m_volume = np.stack([self.window_ct(file,w=4096,c=1024.0) for file in self.m_dicom_files])
		#self.m_volume = np.stack([self.window_ct(file,w=3064.0,c=0.0) for file in self.m_dicom_files])
		
		self.m_min = np.min(self.m_volume)
		self.m_max = np.max(self.m_volume)
		print(f"wart.min = {self.m_min}, wart.maks = {self.m_max}")

		# self.show_histogram()


	def renderSelf(self):
		glEnable(GL_PROGRAM_POINT_SIZE)
		if self.shader_program is None:
			# Inicjalizacja i konfiguracja shaderów
			vertex_shader = compile_shader(vertex_shader_code, GL_VERTEX_SHADER)
			geometry_shader = compile_shader(geometry_shader_code, GL_GEOMETRY_SHADER)
			fragment_shader = compile_shader(fragment_shader_code, GL_FRAGMENT_SHADER)
			
			# Tworzenie programu shaderów
			self.shader_program = glCreateProgram()
			
			glAttachShader(self.shader_program, vertex_shader)
			glAttachShader(self.shader_program, geometry_shader)
			glAttachShader(self.shader_program, fragment_shader)
			
			glLinkProgram(self.shader_program)
			
			# Sprawdzanie, czy program został powiązany poprawnie
			if not glGetProgramiv(self.shader_program, GL_LINK_STATUS):
				print(glGetProgramInfoLog(self.shader_program))
				raise Exception("Error linking shaders")
			
			# Usuwanie shaderów (już nie są potrzebne po powiązaniu programu)
			glDeleteShader(vertex_shader)
			glDeleteShader(geometry_shader)
			glDeleteShader(fragment_shader)

		# Używanie programu shaderów
		glUseProgram(self.shader_program)

		if self.v_vbo is None:
			self.v_vbo = glGenBuffers(1)

		glBindBuffer(GL_ARRAY_BUFFER, self.v_vbo)
		

		# Konfiguracja atrybutów wierzchołka
		glEnableVertexAttribArray(0)  # np. dla pozycji wierzchołka
		glVertexAttribPointer(0, 1, GL_FLOAT, GL_FALSE, 0, None)

		model_loc = glGetUniformLocation(self.shader_program, "model")
		view_loc = glGetUniformLocation(self.shader_program, "view")
		projection_loc = glGetUniformLocation(self.shader_program, "projection")
		
		model = np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype=np.float32)
		projection = np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype=np.float32)
		view = np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype=np.float32)

		glGetFloatv(GL_MODELVIEW_MATRIX, model)
		glGetFloatv(GL_PROJECTION_MATRIX, projection)
		
		glUniformMatrix4fv(model_loc, 1, GL_FALSE, model)
		glUniformMatrix4fv(view_loc, 1, GL_FALSE, view)
		glUniformMatrix4fv(projection_loc, 1, GL_FALSE, projection)

		minColor_loc = glGetUniformLocation(self.shader_program, "minColor")
		glUniform1f( minColor_loc, self.m_minDisplWin )

		maxColor_loc = glGetUniformLocation(self.shader_program, "maxColor")
		glUniform1f( maxColor_loc, self.m_maxDisplWin )

		rescale_loc = glGetUniformLocation(self.shader_program, "rescale")
		if self.m_fastDraw or AP.mouse_key_pressed:
			my_data = self.m_volume[::4, ::4, ::4]
			glUniform1i( rescale_loc, 4 )
		else:
			my_data = self.m_volume
			glUniform1i( rescale_loc, 1 )
		
		sizeX_loc = glGetUniformLocation(self.shader_program, "sizeX")
		glUniform1i( sizeX_loc, my_data.shape[2] )

		sizeY_loc = glGetUniformLocation(self.shader_program, "sizeY")
		glUniform1i( sizeY_loc, my_data.shape[1] )

#		for z in range(int(my_data.shape[0]/2),int(my_data.shape[0]/2)+1):
		for z in range(my_data.shape[0]):
			colors = np.array(my_data[z,:,:].flatten(), dtype=np.float32)
		
			glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
		
			aPosZ_loc = glGetUniformLocation(self.shader_program, "aPosZ")
			glUniform1i( aPosZ_loc, z )

			glDrawArrays(GL_POINTS, 0, colors.shape[0])

		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glUseProgram(0) # Wyłączenie programu shaderów
		glDisable(GL_PROGRAM_POINT_SIZE)
