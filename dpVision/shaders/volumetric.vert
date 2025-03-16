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
