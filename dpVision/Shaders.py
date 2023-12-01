Mesh_vertex_shader_code = """
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec4 aColor;
layout (location = 2) in vec3 aNormal;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

uniform bool useVColors;
uniform bool useVNormals;

out vec3 vertexNormal;
out vec4 vertexColor;

void main()
{
	gl_Position = projection * view * model * vec4(aPos, 1.0);

	if (useVNormals)
	{
		mat3 normalMatrix = transpose(inverse(mat3(model * view)));
		vertexNormal = normalMatrix * aNormal;
		//vertexNormal = aNormal;
	}
	else
	{
		vertexNormal = vec3(0,0,1);
	}
	
	if (useVColors)
	{
		vertexColor = aColor;
	}
	else
	{
		vertexColor = vec4(0.6,0.6,0.6,1.0);
	}
}
"""

Mesh_fragment_shader_code = """
#version 330 core
in vec3 vertexNormal;
in vec4 vertexColor;
in vec3 FragPos; // Pozycja fragmentu/prymitywu w przestrzeni świata

//uniform vec3 lightPos; // Pozycja światła
//uniform vec3 viewPos; // Pozycja obserwatora/kamery
//uniform vec3 lightColor; // Kolor światła
//uniform float ambientStrength; // Siła światła otoczenia
//uniform float specularStrength; // Siła światła spekularnego
//uniform float shininess; // Połysk (shininess)

out vec4 FragColor;

void main()
{
	vec3 lightPos = vec3(0,100,600); // Pozycja światła
	vec3 viewPos = vec3(0,0,200); // Pozycja obserwatora/kamery
	vec3 lightColor = vec3(1.0, 1.0, 1.0); // biały światło
	float ambientStrength = 0.6;
	float specularStrength = 0.0; // Siła światła spekularnego
	float shininess = 0.0; // Połysk (shininess)

	// Normalizacja wektora normalnego
    vec3 norm = normalize(vertexNormal);

    // Obliczenie światła otoczenia
    vec3 ambient = ambientStrength * lightColor;

    // Obliczenie światła dyfuzyjnego
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;

    // Obliczenie światła spekularnego
    vec3 viewDir = normalize(viewPos - FragPos);
    vec3 reflectDir = reflect(-lightDir, norm);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), shininess);
    vec3 specular = specularStrength * spec * lightColor;

    // Sumowanie wszystkich składników oświetlenia
    vec3 result = (ambient + diffuse + specular) * vertexColor.rgb;
    FragColor = vec4(result, 1.0);
}
"""

from OpenGL.GL import *

def compile_shader(source, shader_type):
    shader = glCreateShader(shader_type)
    glShaderSource(shader, source)
    glCompileShader(shader)

    # Sprawdzenie, czy shader został skompilowany poprawnie
    if not glGetShaderiv(shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(shader).decode()
        print(f"Shader compilation error: {error}")
        glDeleteShader(shader)
        raise Exception("Shader compilation failed")
    return shader
