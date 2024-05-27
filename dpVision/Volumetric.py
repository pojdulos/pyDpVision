from math import *
from dpVision.Globals import AP
from .Object import Object
from PyQt5.QtGui import *
from OpenGL.GL import *
import numpy as np
import matplotlib.pyplot as plt
from dpVision.Shaders import Volumetric_vertex_shader_code, Volumetric_fragment_shader_code, compile_shader

vertex_shader_code = """
#version 330 core
layout (location = 0) in float aCol;

uniform mat4 modelviewMatrix;
uniform mat4 projectionMatrix;

uniform float minColor;
uniform float maxColor;

uniform vec3 f[7];
uniform vec3 fcolors[7];

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

vec3 get_filter(int i, float nCol)
{
	if (f[i][2] > f[i][1])
	{
		nCol = nCol - f[i][1];
		nCol = nCol / (f[i][2] - f[i][1]);
		return fcolors[i] * vec3(nCol);
	}
	else
		return fcolors[i];
}

void main()
{
	if (aCol >= minColor && aCol <= maxColor)
	{
		int aPosY = int( float(gl_VertexID) / sizeX );
		int aPosX = gl_VertexID - ( aPosY * sizeX );

		vout.vScale = voxelSize * factor;
		vout.vPos = imagePosition + ( vout.vScale *  vec3(aPosX, aPosY, 0.0) );	
		vout.modelviewMatrix = modelviewMatrix;
		vout.projectionMatrix = projectionMatrix;
		
		float nCol = aCol;

		for (int i=0; i<7; i++)
		{
			if (f[i][0] != 0.0 && aCol >= f[i][1] && aCol <= f[i][2])
			{
				vout.color = get_filter(i, nCol);

				vout.isValid = true;
				return;
			}
		}

		if (f[6][0] == 0)
		{
			if (maxColor > minColor)
			{
				nCol = nCol - minColor;
				nCol = nCol / (maxColor - minColor);
				vout.color = vec3(nCol);
			}
			else
				vout.color = vec3(1.0, 1.0, 1.0);
			vout.isValid = true;
		}
		else
		{
			vout.isValid = false;
		}
	}
	else
	{
		vout.isValid = false;
	}
}
"""

vertex_shader_code_backup = """
#version 330 core
layout (location = 0) in float aCol;

uniform mat4 modelviewMatrix;
uniform mat4 projectionMatrix;

uniform float minColor;
uniform float maxColor;

uniform vec3 f[7];

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

vec3 get_filter(int i, float nCol)
{
	vec3 colors[7];
	colors[0] = vec3(1.0, 1.0, 1.0);
	colors[1] = vec3(1.0, 0.0, 0.0);
	colors[2] = vec3(0.0, 1.0, 0.0);
	colors[3] = vec3(0.0, 0.0, 1.0);
	colors[4] = vec3(1.0, 1.0, 0.0);
	colors[5] = vec3(0.0, 1.0, 1.0);
	colors[6] = vec3(1.0, 0.0, 1.0);

	if (f[i][2] > f[i][1])
	{
		nCol = nCol - f[i][1];
		nCol = nCol / (f[i][2] - f[i][1]);
		return colors[i] * vec3(nCol);
	}
	else
		return colors[i];
}

void main()
{
	if (aCol >= minColor && aCol <= maxColor)
	{
		int aPosY = int( float(gl_VertexID) / sizeX );
		int aPosX = gl_VertexID - ( aPosY * sizeX );

		vout.vScale = voxelSize * factor;
		vout.vPos = imagePosition + ( vout.vScale *  vec3(aPosX, aPosY, 0.0) );	
		
		float nCol = aCol;

		if (f[0][0] == 0.0 && f[1][0] == 0.0 && f[2][0] == 0.0 && f[3][0] == 0.0 && f[4][0] == 0.0 && f[5][0] == 0.0 && f[6][0] == 0.0) 
		{
			if (maxColor > minColor)
			{
				nCol = nCol - minColor;
				nCol = nCol / (maxColor - minColor);
				vout.color = vec3(nCol);
			}
			else
				vout.color = vec3(1.0, 1.0, 1.0);
			
			vout.modelviewMatrix = modelviewMatrix;
			vout.projectionMatrix = projectionMatrix;
			vout.isValid = true;
			return;
		}
		else
		{
			for (int i=0; i<7; i++)
			{
				if (f[i][0] != 0.0 && aCol >= f[i][1] && aCol <= f[i][2])
				{
					vout.color = get_filter(i, nCol);

					vout.modelviewMatrix = modelviewMatrix;
					vout.projectionMatrix = projectionMatrix;
        			vout.isValid = true;
					return;
				}
			}
			vout.isValid = false;
		}
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

class SliceMetadata():
	def __init__(self):
		self.image_position_patient = [0.0,0.0,0.0]
		self.slice_location = 0.0
		self.pixel_spacing = 1.0
		self.slice_thickness = 1.0
		self.gantry_detector_tilt = 0.0
	
	def __str__(self):
		txt  = f"SliceMetadata"
		txt += f"( gantry_detector_tilt = {self.gantry_detector_tilt}"
		txt += f", slice_thickness = {self.slice_thickness}"
		txt += f", slice_location = {self.slice_location}"
		txt += f", pixel_spacing = {self.pixel_spacing}"
		txt += f", image_position_patient = {self.image_position_patient} )"
		return txt
	
	def __repr__(self):
		return self.__str__()
	
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

		self.m_filters = [
			[0,  -100,   799],
			[0, -9999, 99999],
			[0, -9999, 99999],
			[0, -9999,  4000],
			[0, -9999, 99999],
			[0, -9999, 99999],
			[0,   800,  4095]]
		
		self.m_fcolors = [
			[1.0, 0.0, 0.0],
			[0.0, 1.0, 0.0],
			[0.0, 0.0, 1.0],
			[1.0, 1.0, 0.0],
			[0.0, 1.0, 1.0],
			[1.0, 0.0, 1.0],
			[1.0, 1.0, 1.0]]
		
	def aply_window(self, x, c, w, ymin=0.0, ymax=1.0):
		'''	windowing C.11.2.1.2.1 Default LINEAR Function
			c - window center, w - window width
			ymin, ymax - destination data intensity range
		'''
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

	def create_program(self):
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


	def renderSelf(self):
		glEnable(GL_PROGRAM_POINT_SIZE)
		if self.shader_program is None:
			self.create_program()

		# Używanie programu shaderów
		glUseProgram(self.shader_program)

		if self.v_vbo is None:
			self.v_vbo = glGenBuffers(1)

		glBindBuffer(GL_ARRAY_BUFFER, self.v_vbo)
		
		# Konfiguracja atrybutów wierzchołka
		glEnableVertexAttribArray(0)  # np. dla pozycji wierzchołka
		glVertexAttribPointer(0, 1, GL_FLOAT, GL_FALSE, 0, None)

		modelview = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float32)
		modelview_loc = glGetUniformLocation(self.shader_program, "modelviewMatrix")
		glUniformMatrix4fv(modelview_loc, 1, GL_FALSE, modelview)

		projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32)
		projection_loc = glGetUniformLocation(self.shader_program, "projectionMatrix")
		glUniformMatrix4fv(projection_loc, 1, GL_FALSE, projection)

		minColor_loc = glGetUniformLocation(self.shader_program, "minColor")
		glUniform1f( minColor_loc, self.m_minDisplWin )

		maxColor_loc = glGetUniformLocation(self.shader_program, "maxColor")
		glUniform1f( maxColor_loc, self.m_maxDisplWin )

		f_loc = glGetUniformLocation(self.shader_program, "f")
		glUniform3fv(f_loc, 7, self.m_filters)

		fcolors_loc = glGetUniformLocation(self.shader_program, "fcolors")
		glUniform3fv(fcolors_loc, 7, self.m_fcolors)

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

			imagePosition = [ metadata.image_position_patient[0], metadata.image_position_patient[1], metadata.image_position_patient[2] ]
			voxel_size = [ metadata.pixel_spacing[0], metadata.pixel_spacing[1], metadata.slice_thickness ]

			imagePosition_loc = glGetUniformLocation(self.shader_program, "imagePosition")
			glUniform3fv( imagePosition_loc, 1, imagePosition )
			
			voxelSize_loc = glGetUniformLocation(self.shader_program, "voxelSize")
			glUniform3fv( voxelSize_loc, 1, voxel_size )

			glDrawArrays(GL_POINTS, 0, colors.shape[0])

		glBindBuffer(GL_ARRAY_BUFFER, 0)
		glUseProgram(0) # Wyłączenie programu shaderów
		glDisable(GL_PROGRAM_POINT_SIZE)
