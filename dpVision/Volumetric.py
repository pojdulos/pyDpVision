from math import *
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

uniform mat4 modelviewMatrix;
uniform mat4 projectionMatrix;

uniform float minColor;
uniform float maxColor;

uniform vec3 f1;
uniform vec3 f2;
uniform vec3 f3;
uniform vec3 f4;
uniform vec3 f5;
uniform vec3 f6;

uniform vec3 voxelSize;
uniform vec3 imagePosition;

uniform int sizeX;
uniform int sizeY;

uniform int factor;

out VS_OUT{
	vec3 color;
	vec3 vPos;
	vec3 vScale;
	mat4 modelviewMatrix;
	mat4 projectionMatrix;
	bool isValid;
} vout;

void main()
{
	if (aCol >= minColor && aCol <= maxColor)
	{
		int aPosY = int( float(gl_VertexID) / sizeX );
		int aPosX = gl_VertexID - ( aPosY * sizeX );

		vec3 vScale = voxelSize * factor;
		vec3 vPos = imagePosition + ( vScale *  vec3(aPosX, aPosY, 0.0) );	
		
		float nCol = aCol;
		if (f1[0] != 0.0 && aCol >= f1[1] && aCol <= f1[2])
		{
			if (f1[2] > f1[1])
			{
				nCol = nCol - f1[1];
				nCol = nCol / (f1[2] - f1[1]);
	        	vout.color = vec3(1.0, 0.0, 0.0) * vec3(nCol);
			}
			else
        		vout.color = vec3(1.0, 0.0, 0.0);
		}
		else if (f2[0] != 0.0 && aCol >= f2[1] && aCol <= f2[2])
		{
			if (f2[2] > f2[1])
			{
				nCol = nCol - f2[1];
				nCol = nCol / (f2[2] - f2[1]);
        		vout.color = vec3(0.0, 1.0, 0.0) * vec3(nCol);
			}
			else
        		vout.color = vec3(0.0, 1.0, 0.0);
		}
		else if (f3[0] != 0.0 && aCol >= f3[1] && aCol <= f3[2])
		{
			if (f3[2] > f3[1])
			{
				nCol = nCol - f3[1];
				nCol = nCol / (f3[2] - f3[1]);
        		vout.color = vec3(0.0, 0.0, 1.0) * vec3(nCol);
			}
			else
        		vout.color = vec3(0.0, 0.0, 1.0);
		}
		else if (f4[0] != 0.0 && aCol >= f4[1] && aCol <= f4[2])
		{
			if (f4[2] > f4[1])
			{
				nCol = nCol - f4[1];
				nCol = nCol / (f4[2] - f4[1]);
        		vout.color = vec3(1.0, 1.0, 0.0) * vec3(nCol);
			}
			else
        		vout.color = vec3(1.0, 1.0, 0.0);
		}
		else if (f5[0] != 0.0 && aCol >= f5[1] && aCol <= f5[2])
		{
			if (f5[2] > f5[1])
			{
				nCol = nCol - f5[1];
				nCol = nCol / (f5[2] - f5[1]);
        		vout.color = vec3(0.0, 1.0, 1.0) * vec3(nCol);
			}
			else
        		vout.color = vec3(0.0, 1.0, 1.0);
		}
		else if (f6[0] != 0.0 && aCol >= f6[1] && aCol <= f6[2])
		{
			if (f6[2] > f6[1])
			{
				nCol = nCol - f6[1];
				nCol = nCol / (f6[2] - f6[1]);
        		vout.color = vec3(1.0, 0.0, 1.0) * vec3(nCol);
			}
			else
        		vout.color = vec3(1.0, 0.0, 1.0);
		}
		else
		{
			if (maxColor > minColor)
			{
				nCol = nCol - minColor;
				nCol = nCol / (maxColor - minColor);
				vout.color = vec3(nCol);
			}
			else
				vout.color = vec3(1.0, 1.0, 1.0);
		}

		vout.vPos = vPos;
		vout.modelviewMatrix = modelviewMatrix;
		vout.projectionMatrix = projectionMatrix;
		vout.vScale = vScale;
        vout.isValid = true;
	}
	else
	{
		vout.isValid = false;
	}
}
"""

geometry_shader_code = """
#version 330 core
layout(points) in;
layout(points, max_vertices = 1) out;

in VS_OUT{
	vec3 color;
	vec3 vPos;
	vec3 vScale;
	mat4 modelviewMatrix;
	mat4 projectionMatrix;
	bool isValid;
} gs_in[];

out vec3 vertexColor;

void main(void)
{
	if (gs_in[0].isValid)
	{
		vertexColor = gs_in[0].color;
		gl_Position = gs_in[0].projectionMatrix * gs_in[0].modelviewMatrix * vec4(gs_in[0].vPos, 1.0);

		EmitVertex();
		EndPrimitive();
	}
}
"""

# próba wyświetlania vokseli jako kostek zamiast pikseli
geometry_shader_code_boxes = """
#version 330 core
layout (points) in;
layout (triangle_strip, max_vertices = 36) out;

in VS_OUT {
    vec3 color;
	vec3 vPos;
	vec3 vScale;
	mat4 modelviewMatrix;
	mat4 projectionMatrix;
    bool isValid;
} gs_in[];

out vec3 vertexColor;

void main() {
    if (gs_in[0].isValid) {
        vertexColor = gs_in[0].color;

        // Pozycja wierzchołka (punkt)
        vec4 pointPos = vec4(gs_in[0].vPos, 1.0);

        // Wierzchołki tworzące ściany kostki
        vec4 vertices[8];

        // Obliczenia pozycji wierzchołków
        vec3 halfSize = 0.5 * gs_in[0].vScale; // Połowa długości boku kostki
		
		// Wierzchołki kostki
        vertices[0] = pointPos + vec4(-halfSize[0], -halfSize[1], -halfSize[2], 0.0); // Lewy dolny tylny
		vertices[1] = pointPos + vec4( halfSize[0], -halfSize[1], -halfSize[2], 0.0); // Prawy dolny tylny
		vertices[2] = pointPos + vec4(-halfSize[0],  halfSize[1], -halfSize[2], 0.0); // Lewy górny tylny
		vertices[3] = pointPos + vec4( halfSize[0],  halfSize[1], -halfSize[2], 0.0); // Prawy górny tylny
		vertices[4] = pointPos + vec4(-halfSize[0], -halfSize[1],  halfSize[2], 0.0); // Lewy dolny przedni
		vertices[5] = pointPos + vec4( halfSize[0], -halfSize[1],  halfSize[2], 0.0); // Prawy dolny przedni
		vertices[6] = pointPos + vec4(-halfSize[0],  halfSize[1],  halfSize[2], 0.0); // Lewy górny przedni
		vertices[7] = pointPos + vec4( halfSize[0],  halfSize[1],  halfSize[2], 0.0); // Prawy górny przedni

		// TO TRZEBA ROZRYSOWAC I SPRAWDZIC !!!:
		int indices[20];
		indices[0] = 0;
		indices[1] = 1;
		indices[2] = 2;
		indices[3] = 3;
		indices[4] = 6;
		indices[5] = 7;
		indices[6] = 4;
		indices[7] = 5;
		indices[8] = 0;
		indices[9] = 1;

		indices[10] = 1;
		indices[11] = 5;
		indices[12] = 3;
		indices[13] = 7;
		indices[14] = 2;
		indices[15] = 6;
		indices[16] = 0;
		indices[17] = 4;
		indices[18] = 1;
		indices[19] = 5;

        // Generowanie ścian kostki
        for (int i = 0; i < 10; ++i) {
			int idx = indices[i];
            gl_Position = gs_in[0].projectionMatrix * gs_in[0].modelviewMatrix * vertices[idx];
            EmitVertex();
        }
        EndPrimitive();
        for (int i = 10; i < 20; ++i) {
			int idx = indices[i];
            gl_Position = gs_in[0].projectionMatrix * gs_in[0].modelviewMatrix * vertices[idx];
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
		self.m_renderBoxes = False
		self.metadata = []
		self.m_minSlice = 0
		self.m_maxSlice = 0
		self.m_filters = [[0,-9999,99999],[1,0,400],[0,-9999,99999],[0,-9999,9999],[1,1500,4000],[0,-9999,99999],[0,-9999,99999]]

	def convert_to_HU(self, dcm, b=None, m=None):
		if b is None: b = float(getattr(dcm, 'RescaleIntercept', 0.0))
		if m is None: m = float(getattr(dcm, 'RescaleSlope', 1.0))
		x = m * dcm.pixel_array + b
		return x
	
	def aply_window(self, x, ymin=0.0, ymax=1.0, w=None, c=None):
		# windowing C.11.2.1.2.1 Default LINEAR Function
		#
		y = np.zeros_like(x)
		y[x <= (c - 0.5 - (w - 1) / 2)] = ymin
		y[x > (c - 0.5 + (w - 1) / 2)] = ymax
		y[(x > (c - 0.5 - (w - 1) / 2)) & (x <= (c - 0.5 + (w - 1) / 2))] = \
			((x[(x > (c - 0.5 - (w - 1) / 2)) & (x <= (c - 0.5 + (w - 1) / 2))] - (c - 0.5)) / (w - 1) + 0.5) * (
					ymax - ymin) + ymin
		return y

	def window_ct(self, dcm, ymin=0.0, ymax=1.0, w=None, c=None):
		y = self.convert_to_HU(dcm)
		# if w is None: w = dcm.WindowWidth
		# if c is None: c = dcm.WindowCenter
		# # print(f"win.center = {c}, win.width = {w}")
		# y = self.aply_window(y, ymin, ymax, w, c)
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

		print(self.m_dicom_files)
		# Tworzenie wolumetrycznego zestawu danych
		#self.m_volume = np.stack([file.pixel_array for file in self.m_dicom_files])
		self.m_volume = np.stack([self.window_ct(file) for file in self.m_dicom_files])
		#self.m_volume = np.stack([self.window_ct(file,w=4096.0,c=1024.0) for file in self.m_dicom_files])
		#self.m_volume = np.stack([self.window_ct(file,w=2048.0,c=2048.0) for file in self.m_dicom_files])
		#self.m_volume = np.stack([self.window_ct(file,w=4096,c=1024.0) for file in self.m_dicom_files])
		#self.m_volume = np.stack([self.window_ct(file,w=3064.0,c=0.0) for file in self.m_dicom_files])
		
		self.metadata = []
		for idx, file in enumerate(self.m_dicom_files):
			position_image = getattr(file, 'ImagePositionPatient', [0.0, 0.0, idx])
			pixel_spacing = getattr(file, 'PixelSpacing', [1.0, 1.0])
			rows, cols = getattr(file, 'Rows'), getattr(file, 'Columns')
			
			gantra = float(getattr(file, 'GantryDetectorTilt', 0.0))
			
			# korekcja polozenia w X i Y jesli zostało podane w pikselach zamiast milimetrach
			if abs(position_image[0]) >= cols/2 or abs(position_image[1]) >= rows/2:
				for i in range(2):
					position_image[i] = pixel_spacing[i] * position_image[i]

			# korekcja polozenia w X i Y jesli nie zostało ustawione
			# elif position_image[0] == 0 and position_image[1] == 0:
			# 	for i in range(2):
			# 		position_image[0] = - pixel_spacing[0] * cols/2
			# 		position_image[1] = - pixel_spacing[1] * rows/2


			if gantra != 0.0:
				dy = position_image[2] * tan(gantra)
				position_image[1] = position_image[1]+dy

			slice_thickness = getattr(file, 'SliceThickness', 1.0)

			mydict = {
				'ImagePositionPatient': position_image,
				'SliceLocation': getattr(file, 'SliceLocation', idx),
				'PixelSpacing': pixel_spacing,
				'SliceThickness': slice_thickness,
				'GantryDetectorTilt': gantra
			}
			
			print(f"file {idx}:")
			print(f"    GantryDetectorTilt = {mydict['GantryDetectorTilt']}")
			print(f"    SliceThickness = {mydict['SliceThickness']}")
			print(f"    SliceLocation = {mydict['SliceLocation']}")
			print(f"    PixelSpacing = {mydict['PixelSpacing']}")
			print(f"    ImagePositionPatient = {mydict['ImagePositionPatient']}")
			# print(f"PhotometricInterpretation = {getattr(file, 'PhotometricInterpretation')}")
			#print(f"PixelRepresentation = {getattr(file, 'PixelRepresentation')}")
			self.metadata.append(mydict)

		# print(self.metadata)

		self.m_min = np.min(self.m_volume)
		self.m_max = np.max(self.m_volume)
		print(f"wart.min = {self.m_min}, wart.maks = {self.m_max}")
		self.m_minDisplWin = self.m_min
		self.m_maxDisplWin = self.m_max

		self.m_minSlice = 0
		self.m_maxSlice = self.m_volume.shape[0]-1

		# self.show_histogram()


	def on_mouse_move(self, dx, dy):
		self.m_minDisplWin = self.m_minDisplWin + dx
		self.m_minDisplWin = self.m_minDisplWin + dy
		if self.m_minDisplWin < self.m_min:
			self.m_minDisplWin = self.m_min

		self.m_maxDisplWin = self.m_maxDisplWin - dx
		self.m_maxDisplWin = self.m_maxDisplWin + dy
		if self.m_maxDisplWin > self.m_max:
			self.m_maxDisplWin = self.m_max

		AP.updateProperties()
		AP.updateAllViews()
		#print(f"dx={dx}, dy={dy}")

	def remove_shader_program(self):
		glDeleteProgram(self.shader_program)
		self.shader_program = None

	def renderSelf(self):
		glEnable(GL_PROGRAM_POINT_SIZE)
		if self.shader_program is None:
			# Inicjalizacja i konfiguracja shaderów
			vertex_shader = compile_shader(vertex_shader_code, GL_VERTEX_SHADER)
			
			if self.m_renderBoxes:
				geometry_shader = compile_shader(geometry_shader_code_boxes, GL_GEOMETRY_SHADER)
			else:
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

		modelview_loc = glGetUniformLocation(self.shader_program, "modelviewMatrix")
		projection_loc = glGetUniformLocation(self.shader_program, "projectionMatrix")
		
		modelview = np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype=np.float32)
		projection = np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype=np.float32)

		glGetFloatv(GL_MODELVIEW_MATRIX, modelview)
		glGetFloatv(GL_PROJECTION_MATRIX, projection)
		
		glUniformMatrix4fv(modelview_loc, 1, GL_FALSE, modelview)
		glUniformMatrix4fv(projection_loc, 1, GL_FALSE, projection)

		minColor_loc = glGetUniformLocation(self.shader_program, "minColor")
		glUniform1f( minColor_loc, self.m_minDisplWin )

		maxColor_loc = glGetUniformLocation(self.shader_program, "maxColor")
		glUniform1f( maxColor_loc, self.m_maxDisplWin )

		f1_loc = glGetUniformLocation(self.shader_program, "f1")
		glUniform3f( f1_loc, self.m_filters[1][0], self.m_filters[1][1], self.m_filters[1][2] )

		f2_loc = glGetUniformLocation(self.shader_program, "f2")
		glUniform3f( f2_loc, self.m_filters[2][0], self.m_filters[2][1], self.m_filters[2][2] )

		f3_loc = glGetUniformLocation(self.shader_program, "f3")
		glUniform3f( f3_loc, self.m_filters[3][0], self.m_filters[3][1], self.m_filters[3][2] )

		f4_loc = glGetUniformLocation(self.shader_program, "f4")
		glUniform3f( f4_loc, self.m_filters[4][0], self.m_filters[4][1], self.m_filters[4][2] )

		f5_loc = glGetUniformLocation(self.shader_program, "f5")
		glUniform3f( f5_loc, self.m_filters[5][0], self.m_filters[5][1], self.m_filters[5][2] )

		f6_loc = glGetUniformLocation(self.shader_program, "f6")
		glUniform3f( f6_loc, self.m_filters[6][0], self.m_filters[6][1], self.m_filters[6][2] )

		factor = 4 if self.m_fastDraw or AP.mouse_key_pressed else 1
		factor_loc = glGetUniformLocation(self.shader_program, "factor")
		glUniform1i( factor_loc, factor )
		
		sizeX_loc = glGetUniformLocation(self.shader_program, "sizeX")
		glUniform1i( sizeX_loc, int(self.m_volume.shape[2]/factor) )

		sizeY_loc = glGetUniformLocation(self.shader_program, "sizeY")
		glUniform1i( sizeY_loc, int(self.m_volume.shape[1]/factor) )

		for z in range(factor*int(self.m_minSlice/factor), self.m_maxSlice+1, factor):
			colors = np.array(self.m_volume[z,::factor,::factor].flatten(), dtype=np.float32)
		
			glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
		
			metadata = self.metadata[z]

			voxel_size = [ metadata['PixelSpacing'][0], metadata['PixelSpacing'][1], metadata['SliceThickness'] ]
			#voxel_size = [0.4, 0.4, 1.25]
			
			voxelSize_loc = glGetUniformLocation(self.shader_program, "voxelSize")
			glUniform3f( voxelSize_loc, voxel_size[0], voxel_size[1], voxel_size[2] )

			imagePosition_loc = glGetUniformLocation(self.shader_program, "imagePosition")
			glUniform3f( imagePosition_loc, metadata['ImagePositionPatient'][0], metadata['ImagePositionPatient'][1], metadata['ImagePositionPatient'][2] )

			glDrawArrays(GL_POINTS, 0, colors.shape[0])

		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glUseProgram(0) # Wyłączenie programu shaderów
		glDisable(GL_PROGRAM_POINT_SIZE)
