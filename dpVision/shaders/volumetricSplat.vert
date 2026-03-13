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

// parametry splatów
uniform float u_focal_y;
uniform float u_viewport_h;
uniform float u_splat_scale;

out vec3  v_color;
out float v_valid;

vec3 get_filter_color(int i, float nCol)
{
	if (f[i][2] > f[i][1])
	{
		nCol = (nCol - f[i][1]) / (f[i][2] - f[i][1]);
		return fcolors[i] * vec3(nCol);
	}
	else
		return fcolors[i];
}

void main()
{
	v_color      = vec3(0.0);
	v_valid      = 0.0;
	gl_PointSize = 1.0;
	gl_Position  = vec4(2.0, 2.0, 2.0, 1.0);  // domyślnie poza frustumem

	if (aCol < minColor || aCol > maxColor)
		return;

	// rekonstrukcja pozycji 2D z gl_VertexID (jak w volumetric.vert)
	int aPosY = int(float(gl_VertexID) / float(sizeX));
	int aPosX = gl_VertexID - aPosY * sizeX;

	vec3 scale    = voxelSize * float(factor);
	vec3 worldPos = imagePosition + scale * vec3(float(aPosX), float(aPosY), 0.0);

	vec4  eye_pos = modelviewMatrix * vec4(worldPos, 1.0);

	// promień splatu = połowa fizycznego rozmiaru woksela (mm) × factor × skala
	float world_radius = max(voxelSize.x, voxelSize.y) * float(factor) * 0.5 * u_splat_scale;

	// projectionMatrix[3][3] == 0 → perspektywa, == 1 → ortogonalna
	float size_px;
	if (projectionMatrix[3][3] == 0.0)
	{
		// perspektywa: rozmiar maleje z odległością
		float depth = max(-eye_pos.z, 0.001);
		size_px = u_focal_y * u_viewport_h * 0.5 * (2.0 * world_radius) / depth;
	}
	else
	{
		// ortogonalna: u_focal_y = 2/(top-bottom), bezpośrednie mapowanie na piksele
		size_px = u_focal_y * u_viewport_h * 0.5 * (2.0 * world_radius);
	}
	gl_PointSize = clamp(size_px, 1.0, 200.0);

	gl_Position = projectionMatrix * eye_pos;

	// kolor – ta sama logika filtrów co w volumetric.vert
	float nCol = aCol;

	for (int i = 0; i < 7; i++)
	{
		if (f[i][0] != 0.0 && aCol >= f[i][1] && aCol <= f[i][2])
		{
			v_color = get_filter_color(i, nCol);
			v_valid = 1.0;
			return;
		}
	}

	if (f[6][0] == 0.0)
	{
		if (maxColor > minColor)
		{
			nCol    = (nCol - minColor) / (maxColor - minColor);
			v_color = vec3(nCol);
		}
		else
			v_color = vec3(1.0);
		v_valid = 1.0;
	}
}
