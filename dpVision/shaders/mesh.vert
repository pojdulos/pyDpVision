#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec4 aColor;
layout (location = 2) in vec3 aNormal;
layout (location = 3) in vec2 aTexCoord;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

uniform bool useVColors;
uniform bool useVNormals;
uniform bool useTexture;

uniform vec4 myColor;

out vec3 smoothVertexNormal;
flat out vec3 flatVertexNormal;
out vec4 vertexColor;
out vec2 TexCoord; // Wysyłanie współrzędnych tekstury do fragment shadera
out vec3 FragPos;  // Pozycja wierzchołka w przestrzeni świata

void main()
{
	vec4 worldPos = model * vec4(aPos, 1.0);
	FragPos = worldPos.xyz;
	gl_Position = projection * view * worldPos;

	mat3 normalMatrix = transpose(inverse(mat3(model)));
	if (useVNormals)
	{
		smoothVertexNormal = flatVertexNormal = normalMatrix * aNormal;
	}
	else
	{
		smoothVertexNormal = flatVertexNormal = normalMatrix * vec3(0,0,1);
	}
	
	if (useVColors)
	{
		vertexColor = aColor;
	}
	else
	{
		vertexColor = myColor;
	}

    if (useTexture)
    {
		TexCoord = aTexCoord; // Przekazanie współrzędnych tekstury
	}
}
